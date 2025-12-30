import os
import shutil
import uuid
import ifcopenshell
# import ifcopenshell.geom  <-- REMOVED: No visual geometry allowed
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse


router = APIRouter(
    prefix="/ifc",
    tags=["ifc"],
    responses={404: {"description": "Not found"}},
)
UPLOAD_DIR = "uploads/ifc"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Endpoint eliminado por reglas de negocio (No geometría visual en backend).
# Este router se mantiene para futura expansión de endpoints de datos (ej. propiedades).

