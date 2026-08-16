FROM python:3.11-slim

RUN apt-get update && apt-get install -y ffmpeg --no-install-recommends && apt-get clean && rm -rf /var/lib/apt/lists/* 

# 2. WORKDIR — where should you land inside the container?
WORKDIR /app

# 3. COPY your requirements file in, then pip install from it.
#    Why copy just requirements before the rest of the code? Think about
#    Docker layer caching — what gets rebuilt when you edit main.py?
COPY requirements.txt .
RUN pip install -r requirements.txt