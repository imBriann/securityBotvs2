# Usa una imagen base ligera con Python
FROM python:3.11-slim

# Establece variables para no tener que confirmar durante la instalación
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Instala Tesseract OCR y dependencias básicas
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    tesseract-ocr tesseract-ocr-spa tesseract-ocr-eng \
    libtesseract-dev libleptonica-dev \
    build-essential \
    libglib2.0-0 libsm6 libxext6 libxrender-dev \
    libopencv-dev python3-opencv \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /securitybot

# Copia los archivos de requerimientos primero (para caché de Docker)
COPY requirements.txt .

# Instala las dependencias de Python
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir --upgrade scikit-learn==1.7.2

# Copia el resto de la aplicación
COPY app/ ./app/

# Crea el directorio para las imágenes con permisos
RUN mkdir -p /securitybot/imagenes_recibidas && \
    chmod 755 /securitybot/imagenes_recibidas

# Crea un usuario no-root para seguridad
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /securitybot
USER appuser

# Expone el puerto en el que correrá FastAPI (Cloud Run usa 8080)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import os,requests; requests.get('http://localhost:%s/health' % os.environ.get('PORT','8080'), timeout=5)" || exit 1

# Ejecuta el servidor Uvicorn con configuración optimizada
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1 --loop uvloop"]
