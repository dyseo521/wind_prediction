# 풍속 예측 통합 시스템

기상청 API 데이터를 활용하여 풍속을 예측하는 머신러닝 기반 웹 애플리케이션입니다. Python 백엔드와 React 프론트엔드로 구성되어 있습니다.


## 목차

- [주요 기능](#주요-기능)
- [시스템 아키텍처](#시스템-아키텍처)
- [기술 스택](#기술-스택)
- [설치 및 실행 방법](#설치-및-실행-방법)
- [API 설명](#api-설명)
- [사용 방법](#사용-방법)
- [문제 해결](#문제-해결)
- [풍속 단계 정보](#풍속-단계-정보)
- [참고자료](#참고자료)
- [라이센스](#라이센스)

## 주요 기능

- **풍속 예측**: 온도, 습도, 강수량 등의 기상 데이터를 입력하여 풍속 예측
- **실시간 날씨 기반 예측**: 기상청 API를 통해 현재 날씨 정보를 가져와 풍속 예측
- **모델 훈련**: CSV 데이터 파일을 업로드하여 새로운 예측 모델 생성
- **모델 관리**: 훈련된 모델 목록 확인 및 선택
- **날씨 예보**: 날씨 예보 데이터를 기반으로 특정 날짜와 장소의 풍속 예측
- **데이터 시각화**: 온도 변화에 따른 풍속 변화 그래프, 특성 중요도 등 시각화

## 시스템 아키텍처

본 시스템은 다음과 같은 구조로 구성되어 있습니다:

1. **프론트엔드 (React)**
   - 사용자 인터페이스 제공
   - 데이터 입력 및 시각화
   - API 클라이언트를 통한 백엔드 통신

2. **백엔드 (FastAPI)**
   - RESTful API 제공
   - 데이터 전처리 및 모델 훈련
   - 풍속 예측 엔진
   - 파일 업로드 및 처리
   - 기상청 API 연동

3. **데이터 저장소**
   - CSV 파일 저장
   - 훈련된 모델 저장 (Pickle 형식)
   - 캐시 데이터 저장

4. **Docker 컨테이너**
   - 프론트엔드 컨테이너 (Nginx)
   - 백엔드 컨테이너 (Python)

## 기술 스택

- **프론트엔드**:
  - React.js
  - Recharts (차트 라이브러리)
  - Tailwind CSS
  - Axios (HTTP 클라이언트)

- **백엔드**:
  - FastAPI (Python 웹 프레임워크)
  - Scikit-learn (머신러닝 라이브러리)
  - Pandas (데이터 처리)
  - NumPy (수치 계산)

- **인프라**:
  - Docker & Docker Compose
  - Nginx (웹 서버)
  - Uvicorn (ASGI 서버)

## 설치 및 실행 방법

### 사전 요구사항

- Docker 및 Docker Compose 설치
- 기상청 API 키 (공공데이터포털에서 발급)
- 4GB 이상 RAM
- 10GB 이상 여유 디스크 공간

### 설치 과정

1. 저장소 클론:
   ```bash
   git clone https://github.com/your-username/wind-prediction.git
   cd wind-prediction
   ```

2. 환경 변수 설정 (기상청 API 키 등):
   - `backend/.env` 파일에서 `KMA_SERVICE_KEY` 값을 본인의 API 키로 변경
   - `frontend/.env` 파일에서 필요에 따라 설정 변경

3. Docker Compose로 빌드 및 실행:
   ```bash
   docker-compose up -d --build
   ```

4. 웹 브라우저에서 접속:
   - 프론트엔드: http://localhost:3000
   - 백엔드 API: http://localhost:8000/api/health/

### 환경 변수 설정

#### 백엔드 환경 변수 (`backend/.env`)

```
KMA_API_URL=http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0
KMA_SERVICE_KEY=여기에_API_키_입력
FORECAST_NX=54
FORECAST_NY=124
UPLOAD_DIR=/app/uploads
MODEL_DIR=/app/models
CACHE_DIR=/app/cache
```

#### 프론트엔드 환경 변수 (`frontend/.env`)

```
REACT_APP_API_BASE_URL=http://localhost:8000/api
```

## API 설명

### 백엔드 API 엔드포인트

#### 예측 관련 API

- `GET /api/health/`: 서버 건강 확인
- `POST /api/predict/`: 입력 데이터 기반 풍속 예측
- `POST /api/predict/{model_id}`: 특정 모델로 풍속 예측
- `POST /api/predict/with-weather/`: 현재 날씨 기반 풍속 예측
- `POST /api/forecast/`: 날씨 예보 기반 풍속 예측

#### 모델 관련 API

- `POST /api/upload/`: 데이터 파일 업로드
- `POST /api/train/`: 모델 훈련 시작
- `GET /api/training_status/{model_id}`: 모델 훈련 상태 확인
- `GET /api/models/`: 훈련된 모델 목록 조회

#### 날씨 데이터 API

- `GET /api/weather/current`: 현재 날씨 정보 조회
- `GET /api/weather/forecast/short`: 단기 예보 조회
- `GET /api/weather/test-api-key`: API 키 유효성 테스트

## 사용 방법

### 1. 데이터 준비

필요한 CSV 파일 형식:
- `wind_data.csv`: 지점번호, 지점명, 일시, 평균풍속(m/s), 최대풍속(m/s) 등
- `humidity_data.csv`: 지점번호, 지점명, 일시, 평균습도(%rh), 최저습도(%rh)
- `temp_data.csv`: 지점번호, 지점명, 일시, 평균기온(℃), 최고기온(℃), 최저기온(℃) 등
- `rain_data.csv`: 지점번호, 지점명, 일시, 강수량(mm), 1시간최다강수량(mm) 등

### 2. 모델 훈련

1. '모델 훈련' 탭으로 이동
2. 각 데이터 파일 업로드
3. 훈련 설정 조정 (선택사항)
4. '모델 훈련 시작' 버튼 클릭
5. 훈련 완료 후 결과 확인

### 3. 풍속 예측

1. '풍속 예측' 탭으로 이동
2. 기상 데이터 입력
3. 사용할 모델 선택 (선택사항)
4. '풍속 예측하기' 버튼 클릭
5. 예측 결과 및 시각화 확인

### 4. 실시간 예측

1. '실시간 예측' 탭으로 이동
2. '새로고침' 버튼으로 현재 날씨 데이터 가져오기
3. 'API 키 테스트' 버튼으로 API 키 유효성 확인 (문제 해결 시 유용)
4. '현재 날씨로 풍속 예측하기' 버튼 클릭
5. 예측 결과 및 시각화 확인

### 5. 날씨 예보 기반 풍속 예측

1. '날씨 예보' 탭으로 이동
2. '예보 가져오기' 버튼으로 단기 예보 데이터 가져오기
3. 날짜, 지역, 예보 데이터 입력
4. '풍속 예측하기' 버튼 클릭
5. 해당 날짜 및 지역의 예상 풍속 확인

## 문제 해결

### 일반적인 문제

1. **컨테이너가 시작되지 않는 경우**
   ```bash
   docker-compose logs
   ```
   로그를 확인하여 문제를 진단하세요.

2. **기상청 API 연결 오류**
   - API 키가 올바르게 설정되었는지 확인
   - '실시간 예측' 탭의 'API 키 테스트' 버튼으로 API 키 유효성 확인
   - 오류가 지속되면 백엔드 로그 확인: `docker-compose logs backend`

3. **프론트엔드 빌드 오류**
   - React Hooks 규칙 위반 관련 오류가 발생할 수 있음
   - 모든 Hook은 함수 컴포넌트 내부에서 호출되어야 함
   - 함수 컴포넌트 외부에서 상태 관리 함수 직접 호출 금지

4. **파일 업로드 오류**
   - 파일 형식과 인코딩 확인 (EUC-KR 또는 UTF-8)
   - 파일 크기 제한 (10MB 이하 권장)

5. **예측 결과가 부정확한 경우**
   - 더 많은 훈련 데이터 사용
   - 다항식 차수 및 정규화 계수 조정

### 디버깅

백엔드 디버깅:
```bash
docker-compose exec backend sh
cat /var/log/backend.log  # 로그 확인
```

프론트엔드 디버깅:
```bash
docker-compose exec frontend sh
cd /app
```

## 풍속 단계 정보

| 풍속 (m/s) | 단계 | 설명 |
|------------|------|------|
| < 0.3 | 고요 | 바람이 거의 없음 |
| 0.3 - 1.5 | 미풍 | 가벼운 바람 |
| 1.6 - 3.3 | 약풍 | 잎이 살랑거림 |
| 3.4 - 5.4 | 남풍 | 나뭇잎과 작은 가지가 흔들림 |
| 5.5 - 7.9 | 창풍 | 작은 나무가 흔들림 |
| 8.0 - 10.7 | 질풍 | 큰 나뭇가지가 흔들림 |
| 10.8 - 13.8 | 강풍 | 나무 전체가 흔들림 |
| 13.9 - 17.1 | 폭풍 | 나뭇가지가 부러짐 |
| > 17.1 | 폭풍 이상 | 구조물 손상 가능성 |

## 참고자료

- [기상청 기상자료개방포털](https://data.kma.go.kr/)
- [기상청 단기예보 API 활용가이드](https://data.kma.go.kr/cmmn/static/staticPage.do?page=openAPI)
- [Beaufort 풍력 등급](https://ko.wikipedia.org/wiki/보퍼트_풍력_등급)
- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [React 공식 문서](https://reactjs.org/docs/getting-started.html)

## 라이센스

MIT License

Copyright (c) 2025 

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.