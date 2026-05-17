FROM python:3.13-slim

# 작업 디렉토리 설정
WORKDIR /app

# 필요 시스템 패키지 설치 (gcc는 일부 파이썬 패키지 빌드 시 필요할 수 있음)
ENV TZ=Asia/Seoul

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    gcc \
    git \
    openssh-client \
    python3-dev \
    tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone \
    && git config --global --add safe.directory /app \
    && rm -rf /var/lib/apt/lists/*

# 파이썬 의존성 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY . .

# 로그 및 데이터 파일 권한 설정
RUN touch trading.log trade_history.json && chmod 666 trading.log trade_history.json

# 프로그램 실행 (unbuffered 모드로 로그 즉시 출력)
CMD ["python", "-u", "autotrade.py"]
