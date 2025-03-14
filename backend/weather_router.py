from fastapi import APIRouter, HTTPException
import requests
from datetime import datetime, timedelta
import json

# 라우터 설정
router = APIRouter(prefix="/api/weather", tags=["weather"])

# 기상청 API 설정
KMA_API_URL = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0"
SERVICE_KEY = "여기에_발급받은_서비스키_입력"  # URL 인코딩된 키 사용

# 지역 설정 (인천광역시 미추홀구 용현1.4동)
NX = 54
NY = 124

@router.get("/current")
async def get_current_weather():
    """현재 날씨 정보를 조회합니다 (초단기실황)"""
    now = datetime.now()
    base_date = now.strftime("%Y%m%d")
    
    # 매시각 40분 이전이면 이전 시각의 발표 데이터 사용
    if now.minute < 40:
        now = now - timedelta(hours=1)
    
    base_time = now.strftime("%H00")
    
    try:
        # 초단기실황조회 API 호출
        url = f"{KMA_API_URL}/getUltraSrtNcst"
        params = {
            'serviceKey': SERVICE_KEY,
            'numOfRows': 10,
            'pageNo': 1,
            'dataType': 'JSON',
            'base_date': base_date,
            'base_time': base_time,
            'nx': NX,
            'ny': NY
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        if data['response']['header']['resultCode'] != '00':
            raise HTTPException(status_code=500, detail=data['response']['header']['resultMsg'])
        
        # 데이터 가공
        items = data['response']['body']['items']['item']
        result = {
            'location': '인천광역시 미추홀구 용현1.4동',
            'date': base_date,
            'time': base_time,
            'weather': {}
        }
        
        for item in items:
            category = item['category']
            value = item['obsrValue']
            
            # 카테고리별 처리
            if category == 'T1H':  # 기온
                result['weather']['temperature'] = float(value)
            elif category == 'RN1':  # 1시간 강수량
                result['weather']['rainfall'] = float(value)
            elif category == 'REH':  # 습도
                result['weather']['humidity'] = float(value)
            elif category == 'WSD':  # 풍속
                result['weather']['windSpeed'] = float(value)
            elif category == 'PTY':  # 강수형태
                result['weather']['precipitationType'] = get_precipitation_type(value)
            
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/forecast/short")
async def get_short_forecast():
    """단기예보를 조회합니다"""
    now = datetime.now()
    base_date = now.strftime("%Y%m%d")
    
    # 발표시각에 따른 base_time 설정
    hour = now.hour
    if hour < 2:
        base_time = "2300"
        # 전날 23시 발표 데이터 사용
        base_date = (now - timedelta(days=1)).strftime("%Y%m%d")
    elif hour < 5:
        base_time = "0200"
    elif hour < 8:
        base_time = "0500"
    elif hour < 11:
        base_time = "0800"
    elif hour < 14:
        base_time = "1100"
    elif hour < 17:
        base_time = "1400"
    elif hour < 20:
        base_time = "1700"
    elif hour < 23:
        base_time = "2000"
    else:
        base_time = "2300"
    
    try:
        # 단기예보조회 API 호출
        url = f"{KMA_API_URL}/getVilageFcst"
        params = {
            'serviceKey': SERVICE_KEY,
            'numOfRows': 1000,  # 충분히 큰 값으로 설정
            'pageNo': 1,
            'dataType': 'JSON',
            'base_date': base_date,
            'base_time': base_time,
            'nx': NX,
            'ny': NY
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        if data['response']['header']['resultCode'] != '00':
            raise HTTPException(status_code=500, detail=data['response']['header']['resultMsg'])
        
        # 데이터 가공
        items = data['response']['body']['items']['item']
        
        # 날짜-시간별로 데이터 그룹화
        forecast_data = {}
        for item in items:
            fcst_date = item['fcstDate']
            fcst_time = item['fcstTime']
            category = item['category']
            value = item['fcstValue']
            
            key = f"{fcst_date}-{fcst_time}"
            if key not in forecast_data:
                forecast_data[key] = {
                    'date': fcst_date,
                    'time': fcst_time,
                    'weather': {}
                }
            
            # 카테고리별 처리
            if category == 'TMP':  # 기온
                forecast_data[key]['weather']['temperature'] = float(value)
            elif category == 'REH':  # 습도
                forecast_data[key]['weather']['humidity'] = float(value)
            elif category == 'WSD':  # 풍속
                forecast_data[key]['weather']['windSpeed'] = float(value)
            elif category == 'SKY':  # 하늘상태
                forecast_data[key]['weather']['skyCondition'] = get_sky_condition(value)
            elif category == 'PTY':  # 강수형태
                forecast_data[key]['weather']['precipitationType'] = get_precipitation_type(value)
            elif category == 'POP':  # 강수확률
                forecast_data[key]['weather']['precipitationProbability'] = int(value)
            
        # 리스트로 변환하여 정렬
        result = {
            'location': '인천광역시 미추홀구 용현1.4동',
            'baseDate': base_date,
            'baseTime': base_time,
            'forecasts': sorted(list(forecast_data.values()), key=lambda x: f"{x['date']}{x['time']}")
        }
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 강수형태 코드 변환
def get_precipitation_type(code):
    code_map = {
        '0': '없음',
        '1': '비',
        '2': '비/눈',
        '3': '눈',
        '4': '소나기',
        '5': '빗방울',
        '6': '빗방울눈날림',
        '7': '눈날림'
    }
    return code_map.get(code, '알 수 없음')

# 하늘상태 코드 변환
def get_sky_condition(code):
    code_map = {
        '1': '맑음',
        '3': '구름많음',
        '4': '흐림'
    }
    return code_map.get(code, '알 수 없음')