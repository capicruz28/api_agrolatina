FROM python:3.10-bullseye

ENV ACCEPT_EULA=Y
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    curl \
    gnupg2 \
    unixodbc \
    unixodbc-dev \
    gcc \
    g++ \
    apt-transport-https \
    software-properties-common \
    lsb-release \
    && rm -rf /var/lib/apt/lists/*

# Agregar repositorio de Microsoft y instalar ODBC Driver
RUN curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-archive-keyring.gpg \
    && echo "deb [arch=amd64,armhf,arm64 signed-by=/usr/share/keyrings/microsoft-archive-keyring.gpg] https://packages.microsoft.com/debian/11/prod bullseye main" > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql17 \
    && rm -rf /var/lib/apt/lists/*

# Verificar instalación del driver y mostrar información de debug
RUN echo "=== VERIFICANDO INSTALACIÓN DEL DRIVER ===" \
    && odbcinst -q -d \
    && echo "=== LISTANDO ARCHIVOS DE DRIVER ===" \
    && find /opt/microsoft -name "*.so" 2>/dev/null || echo "Directorio /opt/microsoft no encontrado" \
    && echo "=== VERIFICANDO ODBC.INI ===" \
    && cat /etc/odbcinst.ini || echo "odbcinst.ini no encontrado" \
    && echo "=== FIN VERIFICACIÓN ==="

# Establecer directorio de trabajo
WORKDIR /app

# Instalar dependencias de Python
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente (excluyendo archivos sensibles)
COPY . .

# NOTA: El archivo JSON de Firebase NO debe estar en el repositorio Git
# Debe configurarse como variable de entorno FIREBASE_CREDENTIALS_PATH
# o FIREBASE_CREDENTIALS_JSON en la plataforma de despliegue

# Exponer el puerto
EXPOSE 10000

# Ejecutar la app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000", "--log-level", "info"]