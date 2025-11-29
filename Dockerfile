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
    pip install --no-cache-dir -r requirements.txt

# Copia el resto de la aplicación
COPY app/ ./app/
COPY .env .

# Crea el directorio para las imágenes con permisos
RUN mkdir -p /securitybot/imagenes_recibidas && \
    chmod 755 /securitybot/imagenes_recibidas

# Crea un usuario no-root para seguridad
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /securitybot
USER appuser

# Expone el puerto en el que correrá FastAPI
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)" || exit 1

# Ejecuta el servidor Uvicorn con configuración optimizada
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--loop", "uvloop"]
