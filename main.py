import os
import subprocess
import shutil
import uuid
import tempfile
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import requests

# Importar las clases de la biblioteca oficial de Supabase
from supabase import create_client, Client

# --- Cargar variables de entorno ---
load_dotenv()

# --- Configuración de FastAPI ---
app = FastAPI(
    title="API de Procesamiento de Imágenes con Python y PHP",
    description="API que utiliza FastAPI (Python) para orquestar el procesamiento de imágenes con iLoveIMG (PHP) y subir el resultado a Supabase Storage usando la biblioteca oficial `supabase-py`."
)

# --- Variables de Entorno (¡Simplificadas!) ---
# iLoveIMG
ILOVEIMG_PUBLIC_KEY = os.getenv("ILOVEIMG_PUBLIC_KEY")
ILOVEIMG_SECRET_KEY = os.getenv("ILOVEIMG_SECRET_KEY")

# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") # Esta debe ser tu 'service_role' key
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "images")

# --- Inicialización del Cliente de Supabase ---
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    # Manejar el caso en que las variables no estén al inicio
    supabase = None

# --- Verificación de variables de entorno al iniciar ---
@app.on_event("startup")
async def check_env_vars():
    if not supabase:
        raise HTTPException(
            status_code=500,
            detail="Variables de entorno de Supabase (URL y KEY) no configuradas correctamente."
        )
    if not ILOVEIMG_PUBLIC_KEY or not ILOVEIMG_SECRET_KEY:
        raise HTTPException(
            status_code=500,
            detail="Variables de entorno de iLoveIMG (PUBLIC_KEY y SECRET_KEY) no configuradas."
        )

# --- Endpoint de la API ---
@app.post("/process-image")
async def process_image_endpoint(
    image_file: UploadFile = File(...),
    output_filename: Optional[str] = Form(None)
):
    # Usar un archivo temporal seguro
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(image_file.filename)[1]) as temp_upload_file:
        shutil.copyfileobj(image_file.file, temp_upload_file)
        temp_upload_path = temp_upload_file.name
    
    try:
        # 1. Llamar al script PHP de procesamiento
        php_script_path = os.path.join(os.path.dirname(__file__), "iloveimg_processor.php")
        
        php_command = [
            "php", php_script_path,
            temp_upload_path, image_file.filename,
            ILOVEIMG_PUBLIC_KEY, ILOVEIMG_SECRET_KEY
        ]
        if output_filename:
            php_command.append(output_filename)

        process = subprocess.run(php_command, capture_output=True, text=True, check=True)

        iloveimg_download_url = process.stdout.strip()
        if not iloveimg_download_url:
            raise HTTPException(status_code=500, detail="El script PHP no devolvió una URL de descarga.")

        # 2. Descargar el archivo procesado de iLoveIMG
        response = requests.get(iloveimg_download_url, stream=True)
        response.raise_for_status()
        processed_image_content = response.content
        
        # Determinar el tipo de contenido de la respuesta para la subida
        content_type = response.headers.get('content-type', 'application/octet-stream')

        # 3. Subir a Supabase Storage usando la biblioteca oficial
        final_file_name_in_bucket = output_filename if output_filename else f"processed_{uuid.uuid4().hex}.png"

        supabase.storage.from_(SUPABASE_BUCKET).upload(
            path=final_file_name_in_bucket,
            file=processed_image_content,
            file_options={"content-type": content_type}
        )

        # 4. Obtener la URL pública
        public_url_response = supabase.storage.from_(SUPABASE_BUCKET).get_public_url(final_file_name_in_bucket)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Imagen procesada y subida a Supabase Storage con éxito.",
                "publicUrl": public_url_response
            }
        )

    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Error en el script PHP de iLoveIMG: {e.stderr.strip()}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ocurrió un error inesperado: {str(e)}")
    finally:
        # Limpiar el archivo temporal
        if os.path.exists(temp_upload_path):
            os.remove(temp_upload_path)