"""
전력 예측 라우터 - 풍력 및 지압 발전량 예측 API 엔드포인트
"""
from fastapi import APIRouter, HTTPException, Query, Path, Depends
from typing import List, Optional, Dict, Any
import numpy as np
from datetime import datetime, timedelta
import traceback
import pandas as pd
import pickle
import os
import json
from pydantic import BaseModel
from power_calculation import PowerCalculator

# 라우터 생성
router = APIRouter(prefix="/api/power", tags=["power"])

# 전력 계산기 인스턴스
power_calculator = PowerCalculator()

# 지원하는 위치 목록
SUPPORTED_LOCATIONS = ["5호관_60주년_사이", "인경호_앞", "하이데거숲"]

# 모델 캐시
_power_prediction_model = None

def get_power_prediction_model():
    """
    전력 예측 모델 로드 (필요시 학습)
    """
    global _power_prediction_model
    
    if _power_prediction_model is not None:
        return _power_prediction_model
    
    # 모델 파일 경로
    model_path = os.path.join(os.getenv("MODEL_DIR", "models"), "power_prediction_model.pkl")
    
    try:
        # 모델 파일이 있으면 로드
        if os.path.exists(model_path):
            with open(model_path, 'rb') as f:
                _power_prediction_model = pickle.load(f)
                return _power_prediction_model
    except Exception as e:
        print(f"모델 로드 오류: {e}")
    
    # 모델이 없거나 로드 실패 시 간단한 모델 생성
    from sklearn.ensemble import RandomForestRegressor
    
    # 간단한 샘플 데이터로 모델 학습
    # 특성: [풍속, 기온, 습도, 시간대(0-23), 인원수, 위치 인코딩]
    X_sample = []
    y_sample_wind = []
    y_sample_piezo = []
    
    # 위치별로 다른 계수
    location_encodings = {
        "5호관_60주년_사이": [1, 0, 0],
        "인경호_앞": [0, 1, 0],
        "하이데거숲": [0, 0, 1]
    }
    
    # 샘플 데이터 생성
    for location in SUPPORTED_LOCATIONS:
        for wind_speed in [1.5, 3.0, 5.5]:
            for temp in [5, 15, 25]:
                for hour in [6, 12, 18]:
                    for crowd_level in [0.5, 1.0, 1.5]:
                        # 위치별 평균 인원수
                        base_people = power_calculator.piezo_tile_settings[location]['avg_hourly_people']
                        people_count = int(base_people * crowd_level)
                        
                        # 특성 벡터 생성
                        features = [
                            wind_speed,
                            temp,
                            60,  # 습도 (고정)
                            hour,
                            people_count
                        ]
                        features.extend(location_encodings[location])
                        
                        # 발전량 계산
                        wind_power = power_calculator.calculate_wind_power(location, wind_speed, 1)
                        piezo_power = power_calculator.calculate_piezo_power(location, people_count, 1)
                        
                        # 약간의 노이즈 추가
                        wind_noise = np.random.normal(0, wind_power * 0.05)
                        piezo_noise = np.random.normal(0, piezo_power * 0.05)
                        
                        X_sample.append(features)
                        y_sample_wind.append(wind_power + wind_noise)
                        y_sample_piezo.append(piezo_power + piezo_noise)
    
    # 모델 생성 및 학습
    wind_model = RandomForestRegressor(n_estimators=100, random_state=42)
    wind_model.fit(X_sample, y_sample_wind)
    
    piezo_model = RandomForestRegressor(n_estimators=100, random_state=42)
    piezo_model.fit(X_sample, y_sample_piezo)
    
    # 모델 저장
    _power_prediction_model = {
        "wind_model": wind_model,
        "piezo_model": piezo_model,
        "location_encodings": location_encodings,
        "created_at": datetime.now().isoformat()
    }
    
    try:
        # 모델 파일 저장
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        with open(model_path, 'wb') as f:
            pickle.dump(_power_prediction_model, f)
    except Exception as e:
        print(f"모델 저장 오류: {e}")
    
    return _power_prediction_model

# 요청/응답 모델
class PowerPredictionRequest(BaseModel):
    location: str
    wind_speed: float
    temperature: float = 20.0
    humidity: float = 60.0
    hour: Optional[int] = None  # 현재 시간으로 설정
    people_count: Optional[int] = None  # 위치별 기본값 사용

class PowerPredictionResponse(BaseModel):
    location: str
    wind_power_wh: float
    piezo_power_wh: float
    total_power_wh: float
    streetlight_consumption_wh: float
    power_balance_wh: float
    is_sufficient: bool
    sufficiency_percentage: float
    prediction_time: str

@router.get("/")
async def get_power_info():
    """
    전력 예측 API 정보 조회
    """
    return {
        "name": "전력 예측 API",
        "version": "1.0.0",
        "supported_locations": SUPPORTED_LOCATIONS,
        "endpoints": [
            {"path": "/api/power/predict", "method": "POST", "description": "시간당 발전량 예측"},
            {"path": "/api/power/daily/{location}", "method": "GET", "description": "일일 발전량 예측"},
            {"path": "/api/power/weekly/{location}", "method": "GET", "description": "주간 발전량 예측"},
            {"path": "/api/power/monthly/{location}", "method": "GET", "description": "월간 발전량 예측"},
            {"path": "/api/power/annual/{location}", "method": "GET", "description": "연간 발전량 예측"}
        ]
    }

@router.post("/predict", response_model=PowerPredictionResponse)
async def predict_power(request: PowerPredictionRequest):
    """
    시간당 전력 발전량 예측
    """
    try:
        # 위치 유효성 검사
        if request.location not in SUPPORTED_LOCATIONS:
            raise HTTPException(status_code=400, detail=f"지원되지 않는 위치: {request.location}. 지원되는 위치: {SUPPORTED_LOCATIONS}")
        
        # 시간 설정 (None인 경우 현재 시간 사용)
        hour = request.hour if request.hour is not None else datetime.now().hour
        
        # 발전량 계산
        result = power_calculator.calculate_total_power(
            request.location,
            request.wind_speed,
            request.people_count,
            1  # 1시간
        )
        
        # ML 모델을 사용한 예측 추가 (선택적)
        try:
            model = get_power_prediction_model()
            
            # 특성 벡터 생성
            features = [
                request.wind_speed,
                request.temperature,
                request.humidity,
                hour,
                result['people_count']
            ]
            features.extend(model["location_encodings"][request.location])
            
            # 예측
            wind_prediction = model["wind_model"].predict([features])[0]
            piezo_prediction = model["piezo_model"].predict([features])[0]
            
            # 계산된 값과 예측값의 앙상블 (가중 평균)
            result['wind_power_wh'] = round((result['wind_power_wh'] * 0.7 + wind_prediction * 0.3), 2)
            result['piezo_power_wh'] = round((result['piezo_power_wh'] * 0.7 + piezo_prediction * 0.3), 2)
            result['total_power_wh'] = result['wind_power_wh'] + result['piezo_power_wh']
            result['power_balance_wh'] = result['total_power_wh'] - result['streetlight_consumption_wh']
            result['is_sufficient'] = result['power_balance_wh'] >= 0
            result['sufficiency_percentage'] = round((result['total_power_wh'] / max(0.1, result['streetlight_consumption_wh'])) * 100, 1)
            
        except Exception as e:
            # ML 예측 실패 시 원래 값 유지
            print(f"ML 예측 오류 (무시됨): {e}")
            traceback.print_exc()
        
        # 응답 생성
        response = PowerPredictionResponse(
            location=request.location,
            wind_power_wh=result['wind_power_wh'],
            piezo_power_wh=result['piezo_power_wh'],
            total_power_wh=result['total_power_wh'],
            streetlight_consumption_wh=result['streetlight_consumption_wh'],
            power_balance_wh=result['power_balance_wh'],
            is_sufficient=result['is_sufficient'],
            sufficiency_percentage=result['sufficiency_percentage'],
            prediction_time=datetime.now().isoformat()
        )
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"전력 예측 오류: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"전력 예측 중 오류 발생: {str(e)}")

@router.get("/daily/{location}")
async def predict_daily_power(
    location: str = Path(..., description="위치 (5호관_60주년_사이, 인경호_앞, 하이데거숲)"),
    avg_wind_speed: float = Query(..., description="평균 풍속 (m/s)")
):
    """
    일일 전력 발전량 예측
    """
    try:
        # 위치 유효성 검사
        if location not in SUPPORTED_LOCATIONS:
            raise HTTPException(status_code=400, detail=f"지원되지 않는 위치: {location}. 지원되는 위치: {SUPPORTED_LOCATIONS}")
        
        # 시간별 풍속 생성 (간단한 모델)
        hourly_wind_speeds = []
        for hour in range(24):
            # 시간에 따른 풍속 변동 모델 (0-6시: -20%, 6-12시: 기준, 12-18시: +20%, 18-24시: 기준)
            if 0 <= hour < 6:
                hourly_wind_speeds.append(avg_wind_speed * 0.8)
            elif 6 <= hour < 12:
                hourly_wind_speeds.append(avg_wind_speed)
            elif 12 <= hour < 18:
                hourly_wind_speeds.append(avg_wind_speed * 1.2)
            else:
                hourly_wind_speeds.append(avg_wind_speed)
        
        # 시간별 인원 수 생성 (간단한 모델)
        avg_hourly_people = power_calculator.piezo_tile_settings[location]['avg_hourly_people']
        hourly_people_counts = []
        
        for hour in range(24):
            # 시간에 따른 인원 수 변동 모델
            if 0 <= hour < 6:  # 심야
                hourly_people_counts.append(int(avg_hourly_people * 0.1))
            elif 6 <= hour < 9:  # 출근 시간
                hourly_people_counts.append(int(avg_hourly_people * 1.5))
            elif 9 <= hour < 12:  # 오전
                hourly_people_counts.append(int(avg_hourly_people * 1.2))
            elif 12 <= hour < 14:  # 점심
                hourly_people_counts.append(int(avg_hourly_people * 1.8))
            elif 14 <= hour < 18:  # 오후
                hourly_people_counts.append(int(avg_hourly_people * 1.2))
            elif 18 <= hour < 21:  # 저녁
                hourly_people_counts.append(int(avg_hourly_people * 0.8))
            else:  # 야간
                hourly_people_counts.append(int(avg_hourly_people * 0.3))
        
        # 일일 발전량 예측
        result = power_calculator.predict_daily_power(location, hourly_wind_speeds, hourly_people_counts)
        
        # 시간별 결과 보강
        for i, hourly_result in enumerate(result['hourly_results']):
            hourly_result['hour'] = i
            hourly_result['formatted_hour'] = f"{i:02d}:00"
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"일일 전력 예측 오류: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"일일 전력 예측 중 오류 발생: {str(e)}")

@router.get("/weekly/{location}")
async def predict_weekly_power(
    location: str = Path(..., description="위치 (5호관_60주년_사이, 인경호_앞, 하이데거숲)"),
    avg_wind_speed: float = Query(..., description="평균 풍속 (m/s)")
):
    """
    주간 전력 발전량 예측
    """
    try:
        # 위치 유효성 검사
        if location not in SUPPORTED_LOCATIONS:
            raise HTTPException(status_code=400, detail=f"지원되지 않는 위치: {location}. 지원되는 위치: {SUPPORTED_LOCATIONS}")
        
        # 일별 풍속 생성 (간단한 변동)
        daily_wind_speeds = []
        for day in range(7):
            # 요일에 따른 약간의 변동 (-10% ~ +10%)
            variation = 0.1 * np.sin(day * np.pi / 3.5)
            daily_wind_speeds.append(avg_wind_speed * (1 + variation))
        
        # 주간 발전량 예측
        result = power_calculator.predict_weekly_power(location, daily_wind_speeds)
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"주간 전력 예측 오류: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"주간 전력 예측 중 오류 발생: {str(e)}")

@router.get("/monthly/{location}")
async def predict_monthly_power(
    location: str = Path(..., description="위치 (5호관_60주년_사이, 인경호_앞, 하이데거숲)"),
    avg_wind_speed: float = Query(..., description="평균 풍속 (m/s)"),
    min_temp: Optional[float] = Query(None, description="월 최저 기온 (℃)"),
    max_temp: Optional[float] = Query(None, description="월 최고 기온 (℃)")
):
    """
    월간 전력 발전량 예측
    """
    try:
        # 위치 유효성 검사
        if location not in SUPPORTED_LOCATIONS:
            raise HTTPException(status_code=400, detail=f"지원되지 않는 위치: {location}. 지원되는 위치: {SUPPORTED_LOCATIONS}")
        
        # 온도 범위 설정
        temp_range = None
        if min_temp is not None and max_temp is not None:
            temp_range = (min_temp, max_temp)
        
        # 월간 발전량 예측
        result = power_calculator.predict_monthly_power(location, avg_wind_speed, temp_range)
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"월간 전력 예측 오류: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"월간 전력 예측 중 오류 발생: {str(e)}")

@router.get("/annual/{location}")
async def predict_annual_power(
    location: str = Path(..., description="위치 (5호관_60주년_사이, 인경호_앞, 하이데거숲)")
):
    """
    연간 전력 발전량 예측
    """
    try:
        # 위치 유효성 검사
        if location not in SUPPORTED_LOCATIONS:
            raise HTTPException(status_code=400, detail=f"지원되지 않는 위치: {location}. 지원되는 위치: {SUPPORTED_LOCATIONS}")
        
        # 월별 풍속 모델 (계절별 변동)
        monthly_avg_wind_speeds = [
            3.5,  # 1월
            3.8,  # 2월
            4.2,  # 3월
            4.0,  # 4월
            3.7,  # 5월
            3.2,  # 6월
            3.0,  # 7월
            3.3,  # 8월
            3.6,  # 9월
            3.9,  # 10월
            4.1,  # 11월
            3.7   # 12월
        ]
        
        # 월별 온도 범위 모델
        monthly_temp_ranges = [
            (-5, 5),    # 1월
            (-3, 8),    # 2월
            (2, 12),    # 3월
            (8, 18),    # 4월
            (13, 23),   # 5월
            (18, 28),   # 6월
            (22, 32),   # 7월
            (23, 33),   # 8월
            (18, 28),   # 9월
            (12, 22),   # 10월
            (5, 15),    # 11월
            (-2, 8)     # 12월
        ]
        
        # 연간 발전량 예측
        result = power_calculator.predict_annual_power(location, monthly_avg_wind_speeds, monthly_temp_ranges)
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"연간 전력 예측 오류: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"연간 전력 예측 중 오류 발생: {str(e)}")

@router.get("/realtime/{location}")
async def predict_realtime_power(
    location: str = Path(..., description="위치 (5호관_60주년_사이, 인경호_앞, 하이데거숲)"),
):
    """
    실시간 전력 발전량 예측 (기상청 API 데이터 활용)
    """
    try:
        # 위치 유효성 검사
        if location not in SUPPORTED_LOCATIONS:
            raise HTTPException(status_code=400, detail=f"지원되지 않는 위치: {location}. 지원되는 위치: {SUPPORTED_LOCATIONS}")
        
        # 기상청 API 데이터 가져오기 (별도의 모듈에서 구현 필요)
        try:
            from weather_router import get_current_weather
            weather_data = await get_current_weather()
            
            # 현재 풍속
            wind_speed = weather_data.get('weather', {}).get('windSpeed', 3.0)
            
            # 현재 시간
            current_hour = datetime.now().hour
            
            # 시간에 따른 인원 수 조정
            avg_hourly_people = power_calculator.piezo_tile_settings[location]['avg_hourly_people']
            if 0 <= current_hour < 6:  # 심야
                people_count = int(avg_hourly_people * 0.1)
            elif 6 <= current_hour < 9:  # 출근 시간
                people_count = int(avg_hourly_people * 1.5)
            elif 9 <= current_hour < 12:  # 오전
                people_count = int(avg_hourly_people * 1.2)
            elif 12 <= current_hour < 14:  # 점심
                people_count = int(avg_hourly_people * 1.8)
            elif 14 <= current_hour < 18:  # 오후
                people_count = int(avg_hourly_people * 1.2)
            elif 18 <= current_hour < 21:  # 저녁
                people_count = int(avg_hourly_people * 0.8)
            else:  # 야간
                people_count = int(avg_hourly_people * 0.3)
            
            # 발전량 계산
            result = power_calculator.calculate_total_power(location, wind_speed, people_count, 1)
            
            # 날씨 정보 추가
            result['weather'] = weather_data.get('weather', {})
            result['current_hour'] = current_hour
            result['prediction_time'] = datetime.now().isoformat()
            
            return result
            
        except Exception as e:
            # 기상청 API 호출 실패 시 기본값 사용
            print(f"기상청 API 호출 오류: {e}")
            
            # 기본 풍속 및 시간 설정
            wind_speed = 3.0
            current_hour = datetime.now().hour
            
            # 시간에 따른 인원 수 조정
            avg_hourly_people = power_calculator.piezo_tile_settings[location]['avg_hourly_people']
            if 0 <= current_hour < 6:  # 심야
                people_count = int(avg_hourly_people * 0.1)
            elif 6 <= current_hour < 9:  # 출근 시간
                people_count = int(avg_hourly_people * 1.5)
            elif 9 <= current_hour < 12:  # 오전
                people_count = int(avg_hourly_people * 1.2)
            elif 12 <= current_hour < 14:  # 점심
                people_count = int(avg_hourly_people * 1.8)
            elif 14 <= current_hour < 18:  # 오후
                people_count = int(avg_hourly_people * 1.2)
            elif 18 <= current_hour < 21:  # 저녁
                people_count = int(avg_hourly_people * 0.8)
            else:  # 야간
                people_count = int(avg_hourly_people * 0.3)
            
            # 발전량 계산
            result = power_calculator.calculate_total_power(location, wind_speed, people_count, 1)
            
            # 기본 날씨 정보 추가
            result['weather'] = {
                'temperature': 20,
                'humidity': 60,
                'windSpeed': wind_speed
            }
            result['current_hour'] = current_hour
            result['prediction_time'] = datetime.now().isoformat()
            result['api_error'] = str(e)
            
            return result
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"실시간 전력 예측 오류: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"실시간 전력 예측 중 오류 발생: {str(e)}")