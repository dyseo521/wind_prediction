from fastapi import APIRouter, HTTPException, Response
import requests
from datetime import datetime, timedelta, timezone
import json
import os
import time
import traceback
import xml.etree.ElementTree as ET
import urllib.parse
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# 라우터 설정
router = APIRouter(prefix="/api/weather", tags=["weather"])

# API 키 인코딩 문제를 해결하기 위한 함수
def fix_service_key_encoding(service_key):
    """
    API 키의 인코딩 문제를 해결하기 위한 함수
    '+' 문자가 '%2B'로 제대로 인코딩되도록 보장합니다.
    """
    # 이미 인코딩된 키에서 '+' 문자를 '%2B'로 변경
    fixed_key = service_key.replace('+', '%2B')
    return fixed_key


def mask_service_key(key, visible_chars=4):
    """API 키를 마스킹하여 반환합니다."""
    if not key:
        return ""
    
    if len(key) <= visible_chars * 2:
        return "****"  # 짧은 키는 완전히 마스킹
    
    # 앞뒤로 일부만 보여주고 나머지는 '*'로 마스킹
    prefix = key[:visible_chars]
    suffix = key[-visible_chars:]
    masked_length = len(key) - (visible_chars * 2)
    masked = '*' * min(masked_length, 8)  # 마스킹 문자 개수 제한
    
    return f"{prefix}{masked}{suffix}"
    
# 기상청 API 설정
KMA_API_URL = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0"
SERVICE_KEY = os.getenv("KMA_SERVICE_KEY", "")
SERVICE_KEY = fix_service_key_encoding(SERVICE_KEY)

# API 키가 비어있는지 확인하고 로그 출력
if not SERVICE_KEY:
    print("[WARNING] KMA_SERVICE_KEY is not set or empty!")

# 지역 설정 (인천광역시 미추홀구 용현1.4동)
NX = int(os.getenv("FORECAST_NX", "54"))  # 문자열로 기본값 설정
NY = int(os.getenv("FORECAST_NY", "124"))  # 문자열로 기본값 설정

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

# 날씨 데이터 캐시 - 모듈 레벨에서 명시적으로 초기화
current_weather_cache = None
forecast_cache = None
cache_timestamp = None
CACHE_TTL = 3600  # 1시간 (초 단위)

def get_korea_time():
    """한국 시간(UTC+9)을 반환합니다."""
    return datetime.now(timezone(timedelta(hours=9)))

def cache_is_valid():
    """캐시가 유효한지 확인합니다."""
    global cache_timestamp
    if cache_timestamp is None:
        return False
    elapsed = time.time() - cache_timestamp
    return elapsed < CACHE_TTL

def update_cache():
    """캐시 타임스탬프를 업데이트합니다."""
    global cache_timestamp
    cache_timestamp = time.time()

def safely_extract_data(data, keys_path, default=None):
    """중첩된 딕셔너리에서 안전하게 데이터를 추출합니다."""
    current = data
    for key in keys_path:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current

def handle_api_response(response):
    """
    API 응답을 처리하는 함수. JSON 또는 XML 형식을 모두 처리할 수 있습니다.
    
    Parameters:
    response (requests.Response): API 응답 객체
    
    Returns:
    (dict, str): 처리된 데이터와 응답 형식 ('json' 또는 'xml')
    """
    try:
        # 먼저 JSON으로 파싱 시도
        data = response.json()
        return data, 'json'
    except json.JSONDecodeError:
        # JSON 파싱 실패 시 XML 파싱 시도
        try:
            # XML 응답 확인
            if response.text.strip().startswith('<'):
                # XML 파싱
                root = ET.fromstring(response.text)
                
                # 오류 확인
                error_node = root.find('.//returnAuthMsg')
                if error_node is not None and 'SERVICE_KEY' in error_node.text:
                    reason_code = root.find('.//returnReasonCode')
                    reason_code_value = reason_code.text if reason_code is not None else 'UNKNOWN'
                    
                    print(f"[API] SERVICE KEY ERROR: {error_node.text} (Code: {reason_code_value})")
                    print(f"[API] Please verify your service key encoding.")
                    
                    return {
                        'response': {
                            'header': {
                                'resultCode': reason_code_value,
                                'resultMsg': error_node.text
                            }
                        }
                    }, 'xml'
                
                # 실제 데이터 추출 - 초단기실황 API (UltraSrtNcst)
                items = root.findall('.//item')
                if items:
                    xml_data = {
                        'response': {
                            'header': {
                                'resultCode': '00',
                                'resultMsg': 'NORMAL_SERVICE'
                            },
                            'body': {
                                'items': {
                                    'item': []
                                }
                            }
                        }
                    }
                    
                    for item in items:
                        item_data = {}
                        for child in item:
                            item_data[child.tag] = child.text
                        xml_data['response']['body']['items']['item'].append(item_data)
                    
                    return xml_data, 'xml'
                else:
                    # 에러 응답이지만 특정 형식이 아닌 경우
                    return {
                        'response': {
                            'header': {
                                'resultCode': 'ERR',
                                'resultMsg': 'UNKNOWN_ERROR'
                            }
                        }
                    }, 'xml'
            else:
                # XML도 아닌 경우
                return {
                    'response': {
                        'header': {
                            'resultCode': 'ERR',
                            'resultMsg': 'INVALID_RESPONSE_FORMAT'
                        }
                    }
                }, 'unknown'
        except Exception as e:
            # XML 파싱 실패
            return {
                'response': {
                    'header': {
                        'resultCode': 'ERR',
                        'resultMsg': f'PARSING_ERROR: {str(e)}'
                    }
                }
            }, 'error'

@router.get("/current")
async def get_current_weather():
    """현재 날씨 정보를 조회합니다 (초단기실황)"""
    global current_weather_cache
    
    try:
        # 캐시가 유효하면 바로 반환
        if current_weather_cache is not None and cache_is_valid():
            print("[Current Weather] Using valid cache")
            return current_weather_cache
        
        # 한국 시간으로 설정
        now = get_korea_time()
        base_date = now.strftime("%Y%m%d")
        
        # 매시각 40분 이전이면 이전 시각의 발표 데이터 사용
        if now.minute < 40:
            now = now - timedelta(hours=1)
        
        base_time = now.strftime("%H00")
        
        print(f"[Current Weather] Request for base_date: {base_date}, base_time: {base_time}")
        
        # API 키 확인
        if not SERVICE_KEY:
            print("[Current Weather] ERROR: SERVICE_KEY is empty!")
            return FALLBACK_WEATHER
        
        # 인코딩된 SERVICE_KEY 확인
        print(f"[Current Weather] Using SERVICE_KEY: {SERVICE_KEY[:10]}...")
        print(f"[Current Weather] URL Encoded serviceKey: {urllib.parse.quote_plus(SERVICE_KEY)[:15]}...")
        
        # 재시도 메커니즘 구현
        for attempt in range(MAX_RETRIES):
            try:
                # 초단기실황조회 API 호출
                url = f"{KMA_API_URL}/getUltraSrtNcst"
                params = {
                    'serviceKey': urllib.parse.unquote(SERVICE_KEY),
                    'numOfRows': 10,
                    'pageNo': 1,
                    'dataType': 'JSON',
                    'base_date': base_date,
                    'base_time': base_time,
                    'nx': NX,
                    'ny': NY
                }
                
                # 요청 URL 및 파라미터 로깅 (SERVICE_KEY는 일부만 표시)
                masked_params = params.copy()
                if SERVICE_KEY:
                    masked_params['serviceKey'] = SERVICE_KEY[:10] + '...'
                print(f"[Current Weather] API Request URL: {url}")
                print(f"[Current Weather] API Request Params: {masked_params}")
                
                response = requests.get(url, params=params, timeout=10)
                
                # 응답 상태 코드 확인
                if response.status_code != 200:
                    print(f"[Current Weather] API Error: Status code {response.status_code}")
                    print(f"[Current Weather] Response text: {response.text[:200]}...")
                    if attempt < MAX_RETRIES - 1:  # 마지막 시도가 아니면 재시도
                        time.sleep(RETRY_DELAY)
                        continue
                    raise Exception(f"기상청 API 응답 오류 (상태 코드: {response.status_code})")
                
                # 응답 내용 파싱
                try:
                    data, response_type = handle_api_response(response)
                    print(f"[Current Weather] API Response Type: {response_type}")
                    
                    # API 응답 결과 코드 확인 - 안전하게 데이터 추출
                    result_code = safely_extract_data(data, ['response', 'header', 'resultCode'], '')
                    result_msg = safely_extract_data(data, ['response', 'header', 'resultMsg'], '알 수 없는 오류')
                    
                    if result_code != '00':
                        print(f"[Current Weather] API Result Error: {result_code} - {result_msg}")
                        
                        # 서비스 키 오류인 경우 특별 처리
                        if result_code == '30' or 'SERVICE_KEY' in result_msg:
                            print("[Current Weather] API KEY ERROR: Please check your service key")
                            if attempt < MAX_RETRIES - 1:
                                time.sleep(RETRY_DELAY)
                                continue
                            raise Exception("기상청 API 키가 유효하지 않습니다. 키를 확인하고 다시 시도하세요.")
                        
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
                    
                    # 안전하게 데이터 추출
                    items = safely_extract_data(data, ['response', 'body', 'items', 'item'], [])
                    if not items:
                        print("[Current Weather] No items found in response")
                        if attempt < MAX_RETRIES - 1:
                            time.sleep(RETRY_DELAY)
                            continue
                        return FALLBACK_WEATHER
                    
                    # 데이터 가공
                    result = {
                        'location': '인천광역시 미추홀구 용현1.4동',
                        'date': base_date,
                        'time': base_time,
                        'weather': {}
                    }
                    
                    for item in items:
                        category = item.get('category')
                        value = item.get('obsrValue')
                        
                        if not category or not value:
                            continue
                        
                        # 카테고리별 처리
                        try:
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
                        except ValueError as e:
                            print(f"[Current Weather] Value conversion error for {category}: {e}")
                    
                    # 필수 데이터가 모두 있는지 확인
                    required_fields = ['temperature', 'humidity', 'windSpeed']
                    missing_fields = [field for field in required_fields if field not in result['weather']]
                    
                    if missing_fields:
                        print(f"[Current Weather] Missing required fields: {missing_fields}")
                        if attempt < MAX_RETRIES - 1:
                            time.sleep(RETRY_DELAY)
                            continue
                        # 부족한 데이터는 대체 데이터로 채움
                        for field in missing_fields:
                            result['weather'][field] = FALLBACK_WEATHER['weather'][field]
                    
                    # 결과를 캐시에 저장
                    current_weather_cache = result
                    update_cache()
                    
                    return result
                
                except Exception as e:
                    print(f"[Current Weather] Data Processing Error: {e}")
                    print(traceback.format_exc())  # 스택 트레이스 출력
                    if attempt < MAX_RETRIES - 1:  # 마지막 시도가 아니면 재시도
                        time.sleep(RETRY_DELAY)
                        continue
                    raise
            
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
        # 캐시가 유효하면 바로 반환
        if forecast_cache is not None and cache_is_valid():
            print("[Short Forecast] Using valid cache")
            return forecast_cache
        
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
        
        # API 키 확인
        if not SERVICE_KEY:
            print("[Short Forecast] ERROR: SERVICE_KEY is empty!")
            return FALLBACK_FORECAST
        
        # 인코딩된 SERVICE_KEY 확인
        print(f"[Short Forecast] Using SERVICE_KEY: {SERVICE_KEY[:10]}...")
        print(f"[Short Forecast] URL Encoded serviceKey: {urllib.parse.quote_plus(SERVICE_KEY)[:15]}...")
        
        # 재시도 메커니즘 구현
        for attempt in range(MAX_RETRIES):
            try:
                # 단기예보조회 API 호출
                url = f"{KMA_API_URL}/getVilageFcst"
                params = {
                    'serviceKey': urllib.parse.unquote(SERVICE_KEY),
                    'numOfRows': 1000,  # 충분히 큰 값으로 설정
                    'pageNo': 1,
                    'dataType': 'JSON',
                    'base_date': base_date,
                    'base_time': base_time,
                    'nx': NX,
                    'ny': NY
                }
                
                # 요청 URL 및 파라미터 로깅 (SERVICE_KEY는 일부만 표시)
                masked_params = params.copy()
                if SERVICE_KEY:
                    masked_params['serviceKey'] = SERVICE_KEY[:10] + '...'
                print(f"[Short Forecast] API Request URL: {url}")
                print(f"[Short Forecast] API Request Params: {masked_params}")
                
                response = requests.get(url, params=params, timeout=10)
                
                # 응답 상태 코드 확인
                if response.status_code != 200:
                    print(f"[Short Forecast] API Error: Status code {response.status_code}")
                    print(f"[Short Forecast] Response text: {response.text[:200]}...")
                    if attempt < MAX_RETRIES - 1:  # 마지막 시도가 아니면 재시도
                        time.sleep(RETRY_DELAY)
                        continue
                    raise Exception(f"기상청 API 응답 오류 (상태 코드: {response.status_code})")
                
                # 응답 내용 파싱
                try:
                    data, response_type = handle_api_response(response)
                    print(f"[Short Forecast] API Response Type: {response_type}")
                    
                    # API 응답 결과 코드 확인 - 안전하게 데이터 추출
                    result_code = safely_extract_data(data, ['response', 'header', 'resultCode'], '')
                    result_msg = safely_extract_data(data, ['response', 'header', 'resultMsg'], '알 수 없는 오류')
                    
                    if result_code != '00':
                        print(f"[Short Forecast] API Result Error: {result_code} - {result_msg}")
                        
                        # 서비스 키 오류인 경우 특별 처리
                        if result_code == '30' or 'SERVICE_KEY' in result_msg:
                            print("[Short Forecast] API KEY ERROR: Please check your service key")
                            if attempt < MAX_RETRIES - 1:
                                time.sleep(RETRY_DELAY)
                                continue
                            raise Exception("기상청 API 키가 유효하지 않습니다. 키를 확인하고 다시 시도하세요.")
                        
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
                    
                    # 안전하게 데이터 추출
                    items = safely_extract_data(data, ['response', 'body', 'items', 'item'], [])
                    if not items:
                        print("[Short Forecast] No items found in response")
                        if attempt < MAX_RETRIES - 1:
                            time.sleep(RETRY_DELAY)
                            continue
                        return FALLBACK_FORECAST
                    
                    # 날짜-시간별로 데이터 그룹화
                    forecast_data = {}
                    for item in items:
                        fcst_date = item.get('fcstDate')
                        fcst_time = item.get('fcstTime')
                        category = item.get('category')
                        value = item.get('fcstValue')
                        
                        if not fcst_date or not fcst_time or not category or not value:
                            continue
                        
                        key = f"{fcst_date}-{fcst_time}"
                        if key not in forecast_data:
                            forecast_data[key] = {
                                'date': fcst_date,
                                'time': fcst_time,
                                'weather': {}
                            }
                        
                        # 카테고리별 처리
                        try:
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
                        except ValueError as e:
                            print(f"[Short Forecast] Value conversion error for {category}: {e}")
                    
                    # 데이터 검증
                    if not forecast_data:
                        print("[Short Forecast] No forecast data could be processed")
                        if attempt < MAX_RETRIES - 1:
                            time.sleep(RETRY_DELAY)
                            continue
                        return FALLBACK_FORECAST
                    
                    # 리스트로 변환하여 정렬
                    forecasts_list = list(forecast_data.values())
                    # 정렬 전에 date와 time이 유효한지 확인
                    valid_forecasts = [f for f in forecasts_list if 'date' in f and 'time' in f]
                    
                    result = {
                        'location': '인천광역시 미추홀구 용현1.4동',
                        'baseDate': base_date,
                        'baseTime': base_time,
                        'forecasts': sorted(valid_forecasts, key=lambda x: f"{x['date']}{x['time']}")
                    }
                    
                    # 결과를 캐시에 저장
                    forecast_cache = result
                    update_cache()
                    
                    return result
                
                except Exception as e:
                    print(f"[Short Forecast] Data Processing Error: {e}")
                    print(traceback.format_exc())
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_DELAY)
                        continue
                    return FALLBACK_FORECAST
            
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
        if not SERVICE_KEY:
            return {
                "status": "error",
                "message": "API 키가 설정되지 않았습니다."
            }
            
        print(f"Testing API key: {SERVICE_KEY[:10]}...")
        url = f"{KMA_API_URL}/getUltraSrtNcst"
        params = {
            'serviceKey':  urllib.parse.unquote(SERVICE_KEY),
            'numOfRows': 1,
            'pageNo': 1,
            'dataType': 'JSON',
            'base_date': get_korea_time().strftime("%Y%m%d"),
            'base_time': "0600",  # 고정된 시간으로 테스트
            'nx': NX,
            'ny': NY
        }

        # 인코딩된 키 디버깅 정보
        print(f"[API Test] SERVICE_KEY (masked): {mask_service_key(SERVICE_KEY)}")
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code != 200:
            return {
                "status": "error",
                "message": f"API 응답 오류 (상태 코드: {response.status_code})",
                "response_text": response.text[:200]  # 첫 200자만 반환
            }
        
        try:
            # JSON 또는 XML 응답 처리
            try:
                data = response.json()
                response_type = 'json'
            except json.JSONDecodeError:
                # XML 응답인지 확인
                if response.text.strip().startswith('<'):
                    try:
                        root = ET.fromstring(response.text)
                        error_node = root.find('.//returnAuthMsg')
                        reason_code = root.find('.//returnReasonCode')
                        
                        if error_node is not None and 'SERVICE_KEY' in error_node.text:
                            # 서비스 키 오류
                            return {
                                "status": "error",
                                "message": f"API 키 오류: {error_node.text}",
                                "resultCode": reason_code.text if reason_code is not None else 'UNKNOWN',
                                "resultMsg": error_node.text,
                                "debug_info": {
                                    "original_key": SERVICE_KEY,
                                    "encoded_key": urllib.parse.quote_plus(SERVICE_KEY)
                                }
                            }
                        else:
                            # 기타 XML 응답
                            return {
                                "status": "error",
                                "message": "API 응답이 XML 형식입니다.",
                                "response_text": response.text[:200],
                                "debug_info": {
                                    "original_key": SERVICE_KEY,
                                    "encoded_key": urllib.parse.quote_plus(SERVICE_KEY)
                                }
                            }
                    except ET.ParseError:
                        return {
                            "status": "error",
                            "message": "API 응답이 유효한 XML 형식이 아닙니다.",
                            "response_text": response.text[:200]
                        }
                else:
                    return {
                        "status": "error",
                        "message": "API 응답이 JSON 또는 XML 형식이 아닙니다.",
                        "response_text": response.text[:200]
                    }
            
            # JSON 응답 처리
            result_code = safely_extract_data(data, ['response', 'header', 'resultCode'], '')
            result_msg = safely_extract_data(data, ['response', 'header', 'resultMsg'], '알 수 없는 오류')
            
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
                    "resultMsg": result_msg,
                    "debug_info": {
                        "original_key": SERVICE_KEY,
                        "encoded_key": urllib.parse.quote_plus(SERVICE_KEY)
                    }
                }
        except Exception as e:
            return {
                "status": "error",
                "message": f"API 응답 처리 중 오류 발생: {str(e)}",
                "response_text": response.text[:200],
                "error": str(e)
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