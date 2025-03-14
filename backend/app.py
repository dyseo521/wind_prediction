from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import numpy as np
import pandas as pd
import joblib
import os
import shutil
import tempfile
import time
from datetime import datetime
import uuid
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
from sklearn.exceptions import NotFittedError
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import weather_router  
# FastAPI 애플리케이션 생성
app = FastAPI(title="풍속 예측 API", description="기상 데이터를 기반으로 풍속을 예측하는 API", version="1.0.0")

# CORS 설정 - React 앱과 통신 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(weather_router.router)

# 파일 경로 설정
UPLOAD_DIR = "uploads"
MODEL_DIR = "models"
CACHE_DIR = "cache"

# 디렉토리 생성
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

# 기본 모델 경로
DEFAULT_MODEL_PATH = os.path.join(MODEL_DIR, "wind_prediction_model.pkl")

# 예측 요청 모델
class PredictionRequest(BaseModel):
    avgHumidity: float
    minHumidity: float
    avgTemp: float
    maxTemp: float
    minTemp: float
    rainfall: float
    maxHourlyRainfall: float

# 학습 요청 모델
class TrainingRequest(BaseModel):
    wind_file_id: str
    humidity_file_id: str
    temp_file_id: str
    rain_file_id: str
    test_size: float = 0.2
    alpha: float = 0.1
    polynomial_degree: int = 2

# 예측 결과 모델
class PredictionResponse(BaseModel):
    predicted_wind_speed: float
    model_type: str
    confidence: float
    execution_time: float
    wind_level: str
    wind_description: str
    feature_importance: Dict[str, float]

# 학습 결과 모델
class TrainingResponse(BaseModel):
    model_id: str
    metrics: Dict[str, Any]
    feature_importance: List[Dict[str, Any]]
    training_time: float
    sample_predictions: List[Dict[str, float]]

# 풍속 단계 정의
def get_wind_level(speed: float) -> Dict[str, str]:
    if speed < 0.3:
        return {"level": "고요", "description": "바람이 거의 없음"}
    elif speed < 1.6:
        return {"level": "미풍", "description": "가벼운 바람"}
    elif speed < 3.4:
        return {"level": "약풍", "description": "잎이 살랑거림"}
    elif speed < 5.5:
        return {"level": "남풍", "description": "나뭇잎과 작은 가지가 흔들림"}
    elif speed < 8.0:
        return {"level": "창풍", "description": "작은 나무가 흔들림"}
    elif speed < 10.8:
        return {"level": "질풍", "description": "큰 나뭇가지가 흔들림"}
    elif speed < 13.9:
        return {"level": "강풍", "description": "나무 전체가 흔들림"}
    elif speed < 17.2:
        return {"level": "폭풍", "description": "나뭇가지가 부러짐"}
    else:
        return {"level": "폭풍 이상", "description": "구조물 손상 가능성"}

# 모델 로드 함수
def load_model(model_path: str = DEFAULT_MODEL_PATH):
    if not os.path.exists(model_path):
        # 기본 모델이 없으면 간단한 모델 생성
        return create_default_model()
    
    try:
        return joblib.load(model_path)
    except Exception as e:
        print(f"모델 로드 오류: {e}")
        return create_default_model()

# 기본 모델 생성 함수
# 기본 모델 생성 함수 수정
# 기본 모델 생성 함수 수정
# 기본 모델 생성 함수 수정
def create_default_model():
    # 간단한 샘플 데이터로 모델 학습
    X_sample = np.array([
        [60, 50, 20, 25, 15, 0, 0],  # 샘플 데이터 1
        [70, 60, 25, 30, 20, 5, 1],  # 샘플 데이터 2
        [50, 40, 15, 20, 10, 10, 2],  # 샘플 데이터 3
        [65, 55, 22, 27, 17, 2, 0.5]  # 샘플 데이터 4
    ])
    
    # 샘플 타겟 값 (예상 풍속)
    y_sample = np.array([5.2, 6.8, 4.5, 5.7])
    
    # 다항식 특성 변환기 생성 및 학습
    poly_features = PolynomialFeatures(degree=2, include_bias=False)
    poly_features.fit(X_sample)  # 학습
    X_sample_poly = poly_features.transform(X_sample)  # 변환
    
    # 모델 생성 및 학습
    linear_model = Ridge(alpha=0.1)
    linear_model.fit(X_sample, y_sample)  # 선형 모델 학습
    
    poly_model = Ridge(alpha=1.0)
    poly_model.fit(X_sample_poly, y_sample)  # 다항식 모델 학습
    
    # 계수
    coefficients = {
        "평균습도": 0.0294,
        "최저습도": 0.0035,
        "평균기온": -0.2236,
        "최고기온": 0.2556,
        "최저기온": -0.0788,
        "강수량": 0.0190,
        "최대시간강수량": -0.0078
    }
    
    # 학습된 계수로 업데이트 (선택적)
    feature_names = ["평균습도", "최저습도", "평균기온", "최고기온", "최저기온", "강수량", "최대시간강수량"]
    for i, name in enumerate(feature_names):
        if i < len(linear_model.coef_):
            coefficients[name] = float(linear_model.coef_[i])
    
    return {
        "linear_model": linear_model,
        "poly_model": poly_model,
        "poly_features": poly_features,
        "feature_names": feature_names,
        "coefficients": coefficients
    }

# 파일 업로드 API
@app.post("/api/upload/")
async def upload_file(file: UploadFile = File(...)):
    try:
        file_id = f"{uuid.uuid4().hex}_{file.filename}"
        file_path = os.path.join(UPLOAD_DIR, file_id)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        return {"file_id": file_id, "filename": file.filename, "status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 업로드 중 오류: {str(e)}")

# 예측 API
@app.post("/api/predict/", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    try:
        result = make_prediction(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 공통 예측 로직을 담당하는 내부 함수
def make_prediction(request_data, model_path=None):
    start_time = time.time()
    
    try:
        # 모델 로드
        model_data = load_model(model_path) if model_path else load_model()
        
        # 입력 특성 준비
        features = np.array([[
            request_data.avgHumidity,
            request_data.minHumidity,
            request_data.avgTemp,
            request_data.maxTemp,
            request_data.minTemp,
            request_data.rainfall,
            request_data.maxHourlyRainfall
        ]])
        
        # 모델 성분 확인
        poly_features = model_data["poly_features"]
        poly_model = model_data["poly_model"]
        
        # 모델이 학습되었는지 확인
        try:
            # poly_features 학습 검증
            poly_features_transformed = poly_features.transform(features)
            
            # Ridge 모델 학습 여부 검증 (미리 예측 시도)
            _ = poly_model.predict(poly_features_transformed)
            
        except (NotFittedError, ValueError, AttributeError) as e:
            print(f"모델 초기화 필요: {e}")
            # 현재 데이터로 간단히 학습
            sample_X = np.vstack([features, features * 0.9, features * 1.1])  # 약간 변형된 샘플 추가
            sample_y = np.array([5.0, 4.5, 5.5])  # 임의의 타겟값
            
            # 다항식 특성 재학습
            poly_features.fit(sample_X)
            poly_features_transformed = poly_features.transform(sample_X)
            
            # 모델 재학습
            poly_model.fit(poly_features_transformed, sample_y)
            
            # 업데이트된 모델 저장
            model_data["poly_features"] = poly_features
            model_data["poly_model"] = poly_model
            
            # 현재 요청 데이터 다시 변환
            poly_features_transformed = poly_features.transform(features)
        
        # 예측 수행 (이제 학습된 모델로)
        prediction = poly_model.predict(poly_features_transformed)[0]
        
        # 양수 값으로 보정 (풍속은 음수가 될 수 없음)
        predicted_wind_speed = max(0, prediction)
        
        # 풍속 단계 결정
        wind_level_info = get_wind_level(predicted_wind_speed)
        
        # 실행 시간 계산
        execution_time = time.time() - start_time
        
        # 결과 반환
        return {
            "predicted_wind_speed": float(predicted_wind_speed),
            "model_type": "polynomial",
            "confidence": 0.85,  # 예시 값
            "execution_time": execution_time,
            "wind_level": wind_level_info["level"],
            "wind_description": wind_level_info["description"],
            "feature_importance": model_data["coefficients"]
        }
    except Exception as e:
        raise Exception(f"예측 중 오류: {str(e)}")

# CSV 파일 읽기 함수
def read_csv_with_skip(file_path: str):
    """
    CP1252 인코딩의 CSV 파일을 읽고 필요한 데이터만 추출합니다.
    """
    try:
        # CP1252 인코딩으로 파일 읽기
        df = pd.read_csv(file_path, encoding='cp1252')
        
        # 열 이름 확인 및 필요한 열만 추출
        columns = df.columns.tolist()
        
        # 각 파일 유형에 따라 필요한 열 식별
        if 'ÀÏ½Ã' in columns:  # 일시 열 존재
            # 파일 유형에 따라 다른 처리
            if 'Æò±ÕÇ³¼Ó(m/s)' in columns:  # 풍속 데이터
                return df[['ÀÏ½Ã', 'Æò±ÕÇ³¼Ó(m/s)', 'ÃÖ´ëÇ³¼Ó(m/s)']]
                
            elif 'Æò±Õ½Àµµ(%rh)' in columns:  # 습도 데이터
                return df[['ÀÏ½Ã', 'Æò±Õ½Àµµ(%rh)', 'ÃÖÀú½Àµµ(%rh)']]
                
            elif 'Æò±Õ±â¿Â(¡É)' in columns:  # 온도 데이터
                return df[['ÀÏ½Ã', 'Æò±Õ±â¿Â(¡É)', 'ÃÖ°í±â¿Â(¡É)', 'ÃÖÀú±â¿Â(¡É)']]
                
            elif '°­¼ö·®(mm)' in columns:  # 강수량 데이터
                return df[['ÀÏ½Ã', '°­¼ö·®(mm)', '1½Ã°£ÃÖ´Ù°­¼ö·®(mm)']]
        
        # 열 이름을 찾을 수 없는 경우
        print(f"CSV 파일 '{file_path}'의 열 이름: {columns}")
        return df
        
    except Exception as e:
        print(f"CSV 파일 읽기 오류: {e}")
        raise e

# 데이터 병합 함수
def merge_data(wind_df, humidity_df, temp_df, rain_df):
    """
    여러 데이터프레임을 일시 기준으로 병합합니다.
    """
    # 열 이름 매핑 정의
    # 실제 깨진 한글 열 이름 -> 코드에서 사용할 열 이름
    column_mapping = {
        # 일시
        'ÀÏ½Ã': '일시',
        # 풍속 데이터
        'Æò±ÕÇ³¼Ó(m/s)': '평균풍속(m/s)',
        'ÃÖ´ëÇ³¼Ó(m/s)': '최대풍속(m/s)',
        # 습도 데이터
        'Æò±Õ½Àµµ(%rh)': '평균습도(%rh)',
        'ÃÖÀú½Àµµ(%rh)': '최저습도(%rh)',
        # 온도 데이터
        'Æò±Õ±â¿Â(¡É)': '평균기온(℃)',
        'ÃÖ°í±â¿Â(¡É)': '최고기온(℃)',
        'ÃÖÀú±â¿Â(¡É)': '최저기온(℃)',
        # 강수량 데이터
        '°­¼ö·®(mm)': '강수량(mm)',
        '1½Ã°£ÃÖ´Ù°­¼ö·®(mm)': '1시간최다강수량(mm)'
    }
    
    # 데이터프레임 열 이름 변경
    wind_df = wind_df.rename(columns=column_mapping)
    humidity_df = humidity_df.rename(columns=column_mapping)
    temp_df = temp_df.rename(columns=column_mapping)
    rain_df = rain_df.rename(columns=column_mapping)
    
    # 병합에 사용할 공통 키
    common_key = '일시'
    
    # 데이터 병합
    merged = wind_df.merge(humidity_df, on=common_key, how='left')
    merged = merged.merge(temp_df, on=common_key, how='left')
    merged = merged.merge(rain_df, on=common_key, how='left')
    
    # 결측치 처리
    merged = merged.fillna(0)
    
    print(f"병합된 데이터 열: {merged.columns.tolist()}")
    print(f"병합된 데이터 샘플:\n{merged.head()}")
    
    return merged

# 모델 훈련 작업
def train_model_task(
    wind_file_path: str,
    humidity_file_path: str,
    temp_file_path: str,
    rain_file_path: str,
    model_id: str,
    test_size: float = 0.2,
    alpha: float = 0.1,
    polynomial_degree: int = 2
):
    try:
        start_time = time.time()
        
        # CSV 파일 읽기
        wind_df = read_csv_with_skip(wind_file_path)
        humidity_df = read_csv_with_skip(humidity_file_path)
        temp_df = read_csv_with_skip(temp_file_path)
        rain_df = read_csv_with_skip(rain_file_path)
        
        # 데이터 병합
        merged_data = merge_data(wind_df, humidity_df, temp_df, rain_df)
        
        # 특성과 타겟 분리
        feature_columns = [
            '평균습도(%rh)', '최저습도(%rh)', 
            '평균기온(℃)', '최고기온(℃)', '최저기온(℃)',
            '강수량(mm)', '1시간최다강수량(mm)'
        ]
        
        # 필요한 열이 있는지 확인하고 없으면 대체
        available_columns = []
        for col in feature_columns:
            if col in merged_data.columns:
                available_columns.append(col)
            else:
                # 비슷한 이름의 열 찾기
                for existing_col in merged_data.columns:
                    if '습도' in col and '습도' in existing_col:
                        available_columns.append(existing_col)
                        break
                    elif '기온' in col and '기온' in existing_col:
                        available_columns.append(existing_col)
                        break
                    elif '강수량' in col and '강수량' in existing_col:
                        available_columns.append(existing_col)
                        break
        
        # 타겟 열 확인
        target_column = None
        for col in merged_data.columns:
            if '평균풍속' in col:
                target_column = col
                break
        
        if not target_column:
            raise ValueError("평균풍속 열을 찾을 수 없습니다.")
        
        X = merged_data[available_columns]
        y = merged_data[target_column]
        
        # 훈련/테스트 세트 분할
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42
        )
        
        # 1. 선형 회귀 모델 (릿지 회귀)
        linear_model = Ridge(alpha=alpha)
        linear_model.fit(X_train, y_train)
        
        # 2. 다항식 특성 + 릿지 회귀 모델
        poly_features = PolynomialFeatures(degree=polynomial_degree, include_bias=False)
        X_train_poly = poly_features.fit_transform(X_train)
        X_test_poly = poly_features.transform(X_test)
        
        poly_model = Ridge(alpha=alpha*10)
        poly_model.fit(X_train_poly, y_train)
        
        # 모델 평가
        linear_pred = linear_model.predict(X_test)
        poly_pred = poly_model.predict(X_test_poly)
        
        # 평가 지표
        metrics = {
            'linear': {
                'mse': float(mean_squared_error(y_test, linear_pred)),
                'rmse': float(np.sqrt(mean_squared_error(y_test, linear_pred))),
                'mae': float(mean_absolute_error(y_test, linear_pred)),
                'r2': float(r2_score(y_test, linear_pred))
            },
            'polynomial': {
                'mse': float(mean_squared_error(y_test, poly_pred)),
                'rmse': float(np.sqrt(mean_squared_error(y_test, poly_pred))),
                'mae': float(mean_absolute_error(y_test, poly_pred)),
                'r2': float(r2_score(y_test, poly_pred))
            }
        }
        
        # 특성 이름 가져오기
        feature_names = [col.split('(')[0] for col in available_columns]
        
        # 특성 중요도 계산 (선형 모델)
        feature_importance = [
            {"feature": name, "importance": float(abs(coef))}
            for name, coef in zip(feature_names, linear_model.coef_)
        ]
        feature_importance.sort(key=lambda x: x["importance"], reverse=True)
        
        # 계수 추출
        coefficients = {
            name: float(coef) for name, coef in zip(feature_names, linear_model.coef_)
        }
        
        # 샘플 예측
        sample_index = np.random.choice(len(X_test), min(5, len(X_test)), replace=False)
        sample_predictions = []
        for idx in sample_index:
            actual = float(y_test.iloc[idx])
            linear_predicted = float(linear_pred[idx])
            poly_predicted = float(poly_pred[idx])
            sample_predictions.append({
                "actual": actual,
                "linear_predicted": linear_predicted,
                "poly_predicted": poly_predicted,
                "linear_diff": abs(actual - linear_predicted),
                "poly_diff": abs(actual - poly_predicted)
            })
        
        # 모델 저장
        model_data = {
            "linear_model": linear_model,
            "poly_model": poly_model,
            "poly_features": poly_features,
            "feature_names": feature_names,
            "coefficients": coefficients,
            "metrics": metrics,
            "feature_importance": feature_importance,
            "created_at": datetime.now().isoformat(),
            "model_id": model_id
        }
        
        model_path = os.path.join(MODEL_DIR, f"{model_id}.pkl")
        joblib.dump(model_data, model_path)
        
        # 훈련 시간 계산
        training_time = time.time() - start_time
        
        # 결과 캐싱
        training_result = {
            "model_id": model_id,
            "metrics": metrics,
            "feature_importance": feature_importance,
            "training_time": training_time,
            "sample_predictions": sample_predictions,
            "status": "completed"
        }
        
        cache_path = os.path.join(CACHE_DIR, f"training_{model_id}.json")
        with open(cache_path, 'w') as f:
            import json
            json.dump(training_result, f)
        
        return training_result
    except Exception as e:
        print(f"모델 훈련 오류: {e}")
        
        # 오류 기록
        error_result = {
            "model_id": model_id,
            "status": "failed",
            "error": str(e)
        }
        
        cache_path = os.path.join(CACHE_DIR, f"training_{model_id}.json")
        with open(cache_path, 'w') as f:
            import json
            json.dump(error_result, f)
        
        return error_result

# 모델 훈련 API
@app.post("/api/train/")
async def train_model(
    background_tasks: BackgroundTasks,
    request: TrainingRequest
):
    try:
        # 파일 경로 생성
        wind_file_path = os.path.join(UPLOAD_DIR, request.wind_file_id)
        humidity_file_path = os.path.join(UPLOAD_DIR, request.humidity_file_id)
        temp_file_path = os.path.join(UPLOAD_DIR, request.temp_file_id)
        rain_file_path = os.path.join(UPLOAD_DIR, request.rain_file_id)
        
        # 파일 존재 여부 확인
        for file_path in [wind_file_path, humidity_file_path, temp_file_path, rain_file_path]:
            if not os.path.exists(file_path):
                raise HTTPException(status_code=404, detail=f"파일을 찾을 수 없습니다: {file_path}")
        
        # 모델 ID 생성
        model_id = f"model_{uuid.uuid4().hex}"
        
        # 백그라운드 작업으로 모델 훈련 시작
        background_tasks.add_task(
            train_model_task,
            wind_file_path,
            humidity_file_path,
            temp_file_path,
            rain_file_path,
            model_id,
            request.test_size,
            request.alpha,
            request.polynomial_degree
        )
        
        return {"model_id": model_id, "status": "training_started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"모델 훈련 요청 중 오류: {str(e)}")

# 훈련 상태 확인 API
@app.get("/api/training_status/{model_id}")
async def check_training_status(model_id: str):
    cache_path = os.path.join(CACHE_DIR, f"training_{model_id}.json")
    
    if not os.path.exists(cache_path):
        return {"model_id": model_id, "status": "training"}
    
    try:
        with open(cache_path, 'r') as f:
            import json
            result = json.load(f)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"훈련 상태 확인 중 오류: {str(e)}")

# 모델 목록 API
@app.get("/api/models/")
async def list_models():
    try:
        models = []
        for filename in os.listdir(MODEL_DIR):
            if filename.endswith(".pkl"):
                model_id = filename.split(".")[0]
                model_path = os.path.join(MODEL_DIR, filename)
                
                # 모델 메타데이터만 로드
                model_data = joblib.load(model_path)
                
                models.append({
                    "model_id": model_id,
                    "created_at": model_data.get("created_at", "알 수 없음"),
                    "metrics": model_data.get("metrics", {}),
                    "feature_names": model_data.get("feature_names", [])
                })
        
        return {"models": models}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"모델 목록 조회 중 오류: {str(e)}")

# 특정 모델로 예측 API
@app.post("/api/predict/{model_id}")
async def predict_with_model(model_id: str, request: PredictionRequest):
    try:
        # 모델 경로 생성
        model_path = os.path.join(MODEL_DIR, f"{model_id}.pkl")
        
        if not os.path.exists(model_path):
            raise HTTPException(status_code=404, detail=f"모델을 찾을 수 없습니다: {model_id}")
        
        result = make_prediction(request, model_path)
        
        # R² 점수를 신뢰도로 사용 (모델 메타데이터에서 가져오기)
        model_data = joblib.load(model_path)
        confidence = model_data.get("metrics", {}).get("polynomial", {}).get("r2", 0.5)
        if confidence < 0:
            confidence = 0.5  # 음수 R² 값 처리
        
        # 신뢰도 업데이트
        result["confidence"] = confidence
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 날씨 예보 기반 풍속 예측 API
@app.post("/api/forecast/")
async def forecast_wind(
    date: str = Form(...),
    location: str = Form(...),
    avg_humidity: float = Form(...),
    avg_temp: float = Form(...),
    rainfall_prob: float = Form(...)
):
    try:
        # 기본 입력값 설정
        request = PredictionRequest(
            avgHumidity=avg_humidity,
            minHumidity=max(20, avg_humidity - 10),
            avgTemp=avg_temp,
            maxTemp=avg_temp + 5,
            minTemp=avg_temp - 5,
            rainfall=rainfall_prob / 10,  # 강수 확률을 강수량으로 변환
            maxHourlyRainfall=rainfall_prob / 20
        )
        
        # 예측 수행 - 직접 함수 호출로 변경
        prediction = make_prediction(request)
        
        # 예측 결과에 날짜와 위치 정보 추가
        result = dict(prediction)
        result["forecast_date"] = date
        result["location"] = location
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"예보 중 오류: {str(e)}")

@app.post("/api/predict/with-weather/")
async def predict_with_weather():
    """현재 날씨 데이터를 기반으로 풍속을 예측합니다."""
    try:
        # 현재 날씨 데이터 가져오기
        current_weather = await get_current_weather()
        
        # 날씨 데이터로 예측 요청 생성
        request = PredictionRequest(
            avgHumidity=current_weather['weather'].get('humidity', 60),
            minHumidity=max(20, current_weather['weather'].get('humidity', 60) - 10),
            avgTemp=current_weather['weather'].get('temperature', 20),
            maxTemp=current_weather['weather'].get('temperature', 20) + 5,
            minTemp=current_weather['weather'].get('temperature', 20) - 5,
            rainfall=current_weather['weather'].get('rainfall', 0),
            maxHourlyRainfall=current_weather['weather'].get('rainfall', 0) / 2
        )
        
        # 예측 수행
        result = make_prediction(request)
        
        # 결과에 현재 날씨 정보 추가
        result["currentWeather"] = current_weather
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"예측 중 오류: {str(e)}")

# 건강 확인 API
@app.get("/api/health/")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# 서버 시작 이벤트
@app.on_event("startup")
async def startup_event():
    # 기본 모델이 없으면 생성
    if not os.path.exists(DEFAULT_MODEL_PATH):
        default_model = create_default_model()
        joblib.dump(default_model, DEFAULT_MODEL_PATH)
        print(f"기본 모델 생성 완료: {DEFAULT_MODEL_PATH}")

# 메인 실행 블록
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)