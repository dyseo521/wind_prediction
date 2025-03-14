# 빌드 단계
FROM node:16-alpine as build

WORKDIR /app

# 의존성 파일 복사 및 설치
COPY package.json ./
RUN npm install

# .env 파일 복사 (React 앱은 빌드 시점에 환경변수가 필요함)
COPY .env ./

# 소스 코드 복사 및 빌드
COPY . ./
RUN npm run build

# 서빙 단계
FROM nginx:alpine

# Nginx 설정 파일 복사
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 빌드 결과물 복사
COPY --from=build /app/build /usr/share/nginx/html

# 80 포트 노출
EXPOSE 80

# Nginx 실행
CMD ["nginx", "-g", "daemon off;"]