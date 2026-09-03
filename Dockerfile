# portal-al-cielo - webcam -> portal al cielo (MediaPipe + Skyfield)
# Requiere: webcam /dev/video0 y acceso a X11 para la ventana OpenCV.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV QT_QPA_PLATFORM=xcb
ENV PYTHONPATH=/app/src

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml requirements.txt ./
RUN pip install --no-cache-dir -e . || pip install --no-cache-dir \
    opencv-python mediapipe numpy aiohttp skyfield

COPY . .

# Descarga modelos necesarios (hands, efemérides, catálogo estelar)
RUN python tools/download_models.py || true

EXPOSE 8080

CMD ["python", "-m", "app.main", "--no-tls"]
