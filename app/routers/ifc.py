import os
import shutil
import uuid
import ifcopenshell
import ifcopenshell.geom
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

router = APIRouter(
    prefix="/ifc",
    tags=["ifc"],
    responses={404: {"description": "Not found"}},
)
UPLOAD_DIR = "uploads/ifc"
os.makedirs(UPLOAD_DIR, exist_ok=True)
def convert_ifc_to_obj(ifc_path: str, obj_path: str):
    try:
        model = ifcopenshell.open(ifc_path)
        settings = ifcopenshell.geom.settings()
        settings.set(settings.USE_WORLD_COORDS, True)        
        with open(obj_path, 'w') as f:
            f.write("# IFC to OBJ export\n")            
            vertex_offset = 1            
            for product in model.by_type("IfcProduct"):
                if product.Representation:
                    try:
                        shape = ifcopenshell.geom.create_shape(settings, product)
                        verts = shape.geometry.verts
                        faces = shape.geometry.faces                  
                        for i in range(0, len(verts), 3):
                            f.write(f"v {verts[i]} {verts[i+1]} {verts[i+2]}\n")                            
                        f.write(f"g {product.GlobalId}\n")
                        for i in range(0, len(faces), 3):
                            f.write(f"f {faces[i] + vertex_offset} {faces[i+1] + vertex_offset} {faces[i+2] + vertex_offset}\n")                            
                        vertex_offset += len(verts) // 3
                    except Exception as e:
                        print(f"Error processing product {product.GlobalId}: {e}")
                        continue                        
    except Exception as e:
        print(f"Conversion error: {e}")
        raise e

@router.post("/convert")
async def convert_ifc(file: UploadFile = File(...)):
    if not file.filename.endswith(".ifc"):
        raise HTTPException(status_code=400, detail="File must be an IFC file")        
    file_id = str(uuid.uuid4())
    ifc_filename = f"{file_id}.ifc"
    obj_filename = f"{file_id}.obj"    
    ifc_path = os.path.join(UPLOAD_DIR, ifc_filename)
    obj_path = os.path.join(UPLOAD_DIR, obj_filename)    
    with open(ifc_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)        
    try:
        convert_ifc_to_obj(ifc_path, obj_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")        
    return FileResponse(obj_path, filename=f"{file.filename}.obj")
