# 1. Gunakan base image Python yang stabil dan ringan
FROM python:3.11-slim

# 2. Atur lingkungan kerja di dalam container
WORKDIR /app

# 3. Cegah Python menulis file .pyc dan aktifkan unbuffered logging untuk GCP Cloud Run
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 4. Install dependensi sistem yang dibutuhkan untuk kompilasi beberapa library
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /lib/apt/lists/*

# 5. Copy file requirements terlebih dahulu (optimasi layer caching Docker)
COPY requirements.txt .

# 6. Install library tanpa menyimpan cache biar ukuran image Docker kecil
RUN pip install --no-cache-dir -r requirements.txt

# 7. Copy seluruh kode aplikasi dari folder lokal ke dalam container
COPY ./app /app

# 8. Buka port 8080 (Port standar yang diminta oleh GCP Cloud Run)
EXPOSE 8080

# 9. Jalankan FastAPI menggunakan Uvicorn di port 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]