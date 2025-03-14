from fastapi import APIRouter, HTTPException, Response
import requests
from datetime import datetime, timedelta, timezone
import json
import os
import time
import traceback
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# 라우터 설정
router = APIRouter(prefix="/api/weather", tags=["weather"])

# 기상청 API 설정
KMA_API_URL = os.getenv("KMA_API_URL", "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0")
SERVICE_KEY = os.getenv("KMA_SERVICE_KEY", "")  # URL 인코딩된 키 사용

# 지역 설정 (인천광역시 미추홀구 용현1.4동)
NX = int(os.getenv("FORECAST_NX", 54))
NY = int(os.getenv("FORECAST_NY", 124))

# API 재시도 횟수 및 대기 시간 설정
MAX_RETRIES = 3
RETRY_DELAY = 1  # 초 단위

# 가상의 날씨 데이터 (API 호출이 실패했을 때 사용)
FALLBACK_WEATHER = {
    'location': '인천광역시 미추홀구 용현1.4동',
    'date': datetime.now().strftime("%Y%m%d"),
    'time': f"{datetime.now().hour:02d}00",
    'weather': {
        'temperature': 22.0,
        'humidity': 60.0,
        'rainfall': 0.0,
        'windSpeed': 2.5,
        'precipitationType': '없음'
    }
}

FALLBACK_FORECAST = {
    'location': '인천광역시 미추홀구 용현1.4동',
    'baseDate': datetime.now().strftime("%Y%m%d"),
    'baseTime': '0800',
    'forecasts': [
        {
            'date': datetime.now().strftime("%Y%m%d"),
            'time': '1200',
            'weather': {
                'temperature': 24.0,
                'humidity': 55.0,
                'windSpeed': 3.0,
                'skyCondition': '구름많음',
                'precipitationType': '없음',
                'precipitationProbability': 10
            }
        },
        {
            'date': datetime.now().strftime("%Y%m%d"),
            'time': '1500',
            'weather': {
                'temperature': 25.0,
                'humidity': 50.0,
                'windSpeed': 3.5,
                'skyCondition': '맑음',
                'precipitationType': '없음',
                'precipitationProbability': 0
            }
        }
    ]
}

# 날씨 데이터 캐시
current_weather_cache = None
forecast_cache = None
cache_timestamp = None
CACHE_TTL = 3600  # 1시간 (초 단위)

def get_korea_time():
    """한국 시간(UTC+9)을 반환합니다."""
    return datetime.now(timezone(timedelta(hours=9)))

def cache_is_valid():
    """캐시가 유효한지 확인합니다."""
    if cache_timestamp is None:
        return False
    elapsed = time.time() - cache_timestamp
    return elapsed < CACHE_TTL

def update_cache():
    """캐시 타임스탬프를 업데이트합니다."""
    global cache_timestamp
    cache_timestamp = time.time()

@router.get("/current")
async def get_current_weather():
    """현재 날씨 정보를 조회합니다 (초단기실황)"""
    global current_weather_cache
    
    try:
        # 한국 시간으로 설정
        now = get_korea_time()
        base_date = now.strftime("%Y%m%d")
        
        # 매시각 40분 이전이면 이전 시각의 발표 데이터 사용
        if now.minute < 40:
            now = now - timedelta(hours=1)
        
        base_time = now.strftime("%H00")
        
        print(f"[Current Weather] Request for base_date: {base_date}, base_time: {base_time}")
        
        # 재시도 메커니즘 구현
        for attempt in range(MAX_RETRIES):
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
                
                # 요청 URL 및 파라미터 로깅
                print(f"[Current Weather] API Request URL: {url}")
                print(f"[Current Weather] API Request Params: {params}")
                
                response = requests.get(url, params=params, timeout=10)
                
                # 응답 상태 코드 확인
                if response.status_code != 200:
                    print(f"[Current Weather] API Error: Status code {response.status_code}")
                    print(f"[Current Weather] Response text: {response.text}")
                    if attempt < MAX_RETRIES - 1:  # 마지막 시도가 아니면 재시도
                        time.sleep(RETRY_DELAY)
                        continue
                    raise Exception(f"기상청 API 응답 오류 (상태 코드: {response.status_code})")
                
                # 응답 내용 파싱
                try:
                    data = response.json()
                    print(f"[Current Weather] API Response (First 200 chars): {str(data)[:200]}...")
                except json.JSONDecodeError as e:
                    print(f"[Current Weather] JSON Decode Error: {e}")
                    print(f"[Current Weather] Response text: {response.text}")
                    if attempt < MAX_RETRIES - 1:  # 마지막 시도가 아니면 재시도
                        time.sleep(RETRY_DELAY)
                        continue
                    raise Exception("기상청 API 응답이 유효한 JSON 형식이 아닙니다.")
                
                # API 응답 결과 코드 확인
                result_code = data.get('response', {}).get('header', {}).get('resultCode')
                result_msg = data.get('response', {}).get('header', {}).get('resultMsg', '알 수 없는 오류')
                
                if result_code != '00':
                    print(f"[Current Weather] API Result Error: {result_code} - {result_msg}")
                    
                    # 특정 오류 코드에 대한 맞춤 대응
                    if result_code == '03':  # NODATA_ERROR
                        # 이전 시간대 데이터 시도
                        if attempt < MAX_RETRIES - 1:
                            now = now - timedelta(hours=1)
                            base_date = now.strftime("%Y%m%d")
                            base_time = now.strftime("%H00")
                            print(f"[Current Weather] Trying previous hour data: {base_date} {base_time}")
                            time.sleep(RETRY_DELAY)
                            continue
                    
                    # 재시도해도 계속 실패하면 캐시된 데이터 또는 대체 데이터 사용
                    if attempt >= MAX_RETRIES - 1:
                        if current_weather_cache is not None and cache_is_valid():
                            print("[Current Weather] Using cached data due to API error")
                            return current_weather_cache
                        print("[Current Weather] Using fallback data due to API error")
                        return FALLBACK_WEATHER
                    
                    # 그 외의 경우 재시도
                    time.sleep(RETRY_DELAY)
                    continue
                
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
                
                # 결과를 캐시에 저장
                current_weather_cache = result
                update_cache()
                
                return result
            
            except requests.RequestException as e:
                print(f"[Current Weather] Request Exception (Attempt {attempt+1}/{MAX_RETRIES}): {e}")
                if attempt < MAX_RETRIES - 1:  # 마지막 시도가 아니면 재시도
                    time.sleep(RETRY_DELAY)
                else:
                    if current_weather_cache is not None and cache_is_valid():
                        print("[Current Weather] Using cached data due to request exception")
                        return current_weather_cache
                    print("[Current Weather] Using fallback data due to request exception")
                    return FALLBACK_WEATHER
            except Exception as e:
                print(f"[Current Weather] Unexpected Exception: {e}")
                print(traceback.format_exc())  # 스택 트레이스 출력
                if attempt < MAX_RETRIES - 1:  # 마지막 시도가 아니면 재시도
                    time.sleep(RETRY_DELAY)
                else:
                    if current_weather_cache is not None and cache_is_valid():
                        print("[Current Weather] Using cached data due to unexpected exception")
                        return current_weather_cache
                    print("[Current Weather] Using fallback data due to unexpected exception")
                    return FALLBACK_WEATHER
    
    except Exception as e:
        # 모든 예외 처리
        print(f"[Current Weather] Critical Error: {e}")
        print(traceback.format_exc())  # 스택 트레이스 출력
        
        # 캐시된 데이터가 있으면 사용
        if current_weather_cache is not None and cache_is_valid():
            print("[Current Weather] Using cached data due to critical error")
            return current_weather_cache
        
        # 없으면 대체 데이터 사용
        print("[Current Weather] Using fallback data due to critical error")
        return FALLBACK_WEATHER

@router.get("/forecast/short")
async def get_short_forecast():
    """단기예보를 조회합니다"""
    global forecast_cache
    
    try:
        # 한국 시간으로 설정
        now = get_korea_time()
        base_date = now.strftime("%Y%m%d")
        
        # 발표시각에 따른 base_time 설정
        # 0200, 0500, 0800, 1100, 1400, 1700, 2000, 2300
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
        
        print(f"[Short Forecast] Request for base_date: {base_date}, base_time: {base_time}")
        
        # 재시도 메커니즘 구현
        for attempt in range(MAX_RETRIES):
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
                
                # 요청 URL 및 파라미터 로깅
                print(f"[Short Forecast] API Request URL: {url}")
                print(f"[Short Forecast] API Request Params: {params}")
                
                response = requests.get(url, params=params, timeout=10)
                
                # 응답 상태 코드 확인
                if response.status_code != 200:
                    print(f"[Short Forecast] API Error: Status code {response.status_code}")
                    print(f"[Short Forecast] Response text: {response.text}")
                    if attempt < MAX_RETRIES - 1:  # 마지막 시도가 아니면 재시도
                        time.sleep(RETRY_DELAY)
                        continue
                    raise Exception(f"기상청 API 응답 오류 (상태 코드: {response.status_code})")
                
                # 응답 내용 파싱
                try:
                    data = response.json()
                    print(f"[Short Forecast] API Response (First 200 chars): {str(data)[:200]}...")
                except json.JSONDecodeError as e:
                    print(f"[Short Forecast] JSON Decode Error: {e}")
                    print(f"[Short Forecast] Response text: {response.text}")
                    if attempt < MAX_RETRIES - 1:  # 마지막 시도가 아니면 재시도
                        time.sleep(RETRY_DELAY)
                        continue
                    raise Exception("기상청 API 응답이 유효한 JSON 형식이 아닙니다.")
                
                # API 응답 결과 코드 확인
                result_code = data.get('response', {}).get('header', {}).get('resultCode')
                result_msg = data.get('response', {}).get('header', {}).get('resultMsg', '알 수 없는 오류')
                
                if result_code != '00':
                    print(f"[Short Forecast] API Result Error: {result_code} - {result_msg}")
                    
                    # 특정 오류 코드에 대한 맞춤 대응
                    if result_code == '03':  # NODATA_ERROR
                        # 이전 발표 시각으로 다시 시도
                        if attempt < MAX_RETRIES - 1:
                            # 이전 발표 시각으로 변경
                            if base_time == "0200":
                                base_time = "2300"
                                base_date = (datetime.strptime(base_date, "%Y%m%d") - timedelta(days=1)).strftime("%Y%m%d")
                            elif base_time == "0500":
                                base_time = "0200"
                            elif base_time == "0800":
                                base_time = "0500"
                            elif base_time == "1100":
                                base_time = "0800"
                            elif base_time == "1400":
                                base_time = "1100"
                            elif base_time == "1700":
                                base_time = "1400"
                            elif base_time == "2000":
                                base_time = "1700"
                            elif base_time == "2300":
                                base_time = "2000"
                            
                            print(f"[Short Forecast] Trying previous base_time: {base_date} {base_time}")
                            time.sleep(RETRY_DELAY)
                            continue
                    
                    # 재시도해도 계속 실패하면 캐시된 데이터 또는 대체 데이터 사용
                    if attempt >= MAX_RETRIES - 1:
                        if forecast_cache is not None and cache_is_valid():
                            print("[Short Forecast] Using cached data due to API error")
                            return forecast_cache
                        print("[Short Forecast] Using fallback data due to API error")
                        return FALLBACK_FORECAST
                    
                    # 그 외의 경우 재시도
                    time.sleep(RETRY_DELAY)
                    continue
                
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
                
                # 결과를 캐시에 저장
                forecast_cache = result
                update_cache()
                
                return result
            
            except requests.RequestException as e:
                print(f"[Short Forecast] Request Exception (Attempt {attempt+1}/{MAX_RETRIES}): {e}")
                if attempt < MAX_RETRIES - 1:  # 마지막 시도가 아니면 재시도
                    time.sleep(RETRY_DELAY)
                else:
                    if forecast_cache is not None and cache_is_valid():
                        print("[Short Forecast] Using cached data due to request exception")
                        return forecast_cache
                    print("[Short Forecast] Using fallback data due to request exception")
                    return FALLBACK_FORECAST
            except Exception as e:
                print(f"[Short Forecast] Unexpected Exception: {e}")
                print(traceback.format_exc())  # 스택 트레이스 출력
                if attempt < MAX_RETRIES - 1:  # 마지막 시도가 아니면 재시도
                    time.sleep(RETRY_DELAY)
                else:
                    if forecast_cache is not None and cache_is_valid():
                        print("[Short Forecast] Using cached data due to unexpected exception")
                        return forecast_cache
                    print("[Short Forecast] Using fallback data due to unexpected exception")
                    return FALLBACK_FORECAST
    
    except Exception as e:
        # 모든 예외 처리
        print(f"[Short Forecast] Critical Error: {e}")
        print(traceback.format_exc())  # 스택 트레이스 출력
        
        # 캐시된 데이터가 있으면 사용
        if forecast_cache is not None and cache_is_valid():
            print("[Short Forecast] Using cached data due to critical error")
            return forecast_cache
        
        # 없으면 대체 데이터 사용
        print("[Short Forecast] Using fallback data due to critical error")
        return FALLBACK_FORECAST

# API 키 테스트를 위한 엔드포인트
@router.get("/test-api-key")
async def test_api_key():
    """API 키가 유효한지 테스트합니다."""
    try:
        print(f"Testing API key: {SERVICE_KEY[:20]}...")
        url = f"{KMA_API_URL}/getUltraSrtNcst"
        params = {
            'serviceKey': SERVICE_KEY,
            'numOfRows': 1,
            'pageNo': 1,
            'dataType': 'JSON',
            'base_date': get_korea_time().strftime("%Y%m%d"),
            'base_time': "0600",  # 고정된 시간으로 테스트
            'nx': NX,
            'ny': NY
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code != 200:
            return {
                "status": "error",
                "message": f"API 응답 오류 (상태 코드: {response.status_code})",
                "response_text": response.text[:200]  # 첫 200자만 반환
            }
        
        try:
            data = response.json()
            result_code = data.get('response', {}).get('header', {}).get('resultCode')
            result_msg = data.get('response', {}).get('header', {}).get('resultMsg', '알 수 없는 오류')
            
            if result_code == '00':
                return {
                    "status": "success",
                    "message": "API 키가 유효합니다.",
                    "resultCode": result_code,
                    "resultMsg": result_msg
                }
            else:
                return {
                    "status": "error",
                    "message": f"API 키 오류: {result_code} - {result_msg}",
                    "resultCode": result_code,
                    "resultMsg": result_msg
                }
        except json.JSONDecodeError:
            return {
                "status": "error",
                "message": "API 응답이 유효한 JSON 형식이 아닙니다.",
                "response_text": response.text[:200]  # 첫 200자만 반환
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"API 키 테스트 중 오류 발생: {str(e)}",
            "error": str(e)
        }

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
    return code_map.get(str(code), '알 수 없음')

# 하늘상태 코드 변환
def get_sky_condition(code):
    code_map = {
        '1': '맑음',
        '3': '구름많음',
        '4': '흐림'
    }
    return code_map.get(str(code), '알 수 없음')