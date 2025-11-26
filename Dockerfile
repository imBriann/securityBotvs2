# Usa una imagen base ligera con Python
FROM python:3.10-slim

# Establece variables para no tener que confirmar durante la instalación
ENV DEBIAN_FRONTEND=noninteractive

# Instala Tesseract OCR y dependencias básicas
RUN apt-get update && \
    apt-get install -y tesseract-ocr tesseract-ocr-spa tesseract-ocr-eng \
    libtesseract-dev libleptonica-dev poppler-utils build-essential \
    libglib2.0-0 libsm6 libxext6 libxrender-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /securitybot

# Copia los archivos de requerimientos primero (para caché de Docker)
COPY requirements.txt .

# Instala las dependencias de Python
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto de la aplicación
# Copiamos la carpeta 'app' y los archivos sueltos
COPY app/ ./app/
COPY .env .

# Crea el directorio para las imágenes
RUN mkdir -p /securitybot/imagenes_recibidas

# Expone el puerto en el que correrá FastAPI
EXPOSE 8000

# Ejecuta el servidor Uvicorn
# Apunta al objeto 'app' dentro del módulo 'app.main'
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]