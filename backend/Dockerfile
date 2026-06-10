FROM python:3.11-slim

# Atur lingkungan kerja langsung di root container agar struktur modul folder 'app' terjaga
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Menyalin folder app beserta seluruh isinya ke direktori /app/
COPY . .

# Jalankan uvicorn dengan memanggil modul app.main:app
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT