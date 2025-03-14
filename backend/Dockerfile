FROM python:3.10-slim

WORKDIR /app

# 환경변수 설정
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV HOST=0.0.0.0
ENV PORT=8000
ENV UPLOAD_DIR=/app/uploads
ENV MODEL_DIR=/app/models
ENV CACHE_DIR=/app/cache

# 필요한 패키지 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 필요한 디렉토리 생성
RUN mkdir -p /app/uploads /app/models /app/cache

# 의존성 파일 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY app.py .
COPY weather_router.py .

# .env 파일 복사 (존재하는 경우)
COPY .env .env

# 서버 실행
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]