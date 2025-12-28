# Usamos una imagen base de Python ligera (Debian Buster)
FROM python:3.10-slim-bookworm

# --- Instalación de PHP-CLI y Composer ---

# Actualizar la lista de paquetes e instalar PHP-CLI y extensiones necesarias
# php-cli: el ejecutable de PHP para línea de comandos
# php-curl: necesario para Composer y la biblioteca iLoveIMG
# php-json: necesario para Composer y la biblioteca iLoveIMG
# php-mbstring: necesario para Composer
RUN apt-get update && apt-get install -y \
    php-cli \
    php-curl \
    php-json \
    php-mbstring \
    unzip \
    git \
    ca-certificates \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Instalar Composer
COPY --from=composer:latest /usr/bin/composer /usr/local/bin/composer

# --- Configuración del entorno de Python ---

# Establecer el directorio de trabajo
WORKDIR /app

# Copiar el archivo de dependencias de Python e instalarlas
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Copiar código de la aplicación ---

# Copiar todos los archivos del proyecto al contenedor
COPY . .

# --- Configuración final ---

# Instalar dependencias de PHP usando Composer (para la biblioteca iLoveIMG)
# Aquí también aseguramos que composer.json y composer.lock existan antes de este paso
RUN apt-get update && apt-get install -y curl iputils-ping && \
    echo "--- Checking Composer Version ---" && \
    composer --version && \
    echo "--- Running Composer Diagnose ---" && \
    composer diagnose && \
    echo "--- Pinging Packagist ---" && \
    ping -c 4 repo.packagist.org && \
    echo "--- Curling Packagist ---" && \
    curl -vvv https://repo.packagist.org/packages.json && \
    echo "--- Attempting Composer Install ---" && \
    composer install --no-dev --optimize-autoloader --working-dir=.


# Crear el directorio 'output' para archivos temporales (si no existe)
# Aunque no guardaremos permanentemente, el script PHP podría necesitarlo.
RUN mkdir -p output && chmod 777 output

# Exponer el puerto que Uvicorn usará (por defecto 8000 para FastAPI)
EXPOSE 8000

# Comando para iniciar la aplicación con Uvicorn
# --host 0.0.0.0 es necesario para que sea accesible desde fuera del contenedor
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
