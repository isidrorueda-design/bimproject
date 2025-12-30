import subprocess
import os
import shutil

def convert_ifc_to_frag(ifc_path: str, output_dir: str):
    current_dir = os.getcwd()
    script_path = os.path.join(current_dir, "converter.mjs")
    
    if not os.path.exists(script_path):
        print(f"ERROR CRÍTICO: No se encuentra el script en: {script_path}")
        return False

    command = ["node", script_path, ifc_path, output_dir]
    
    try:
        print(f"--- STARTING CONVERSION ---")
        print(f"Script: {script_path}")
        print(f"Input: {ifc_path}")        
        result = subprocess.run(
            command, 
            check=True, 
            capture_output=True, 
            text=True
        )
        
        print("Output del convertidor:", result.stdout)
        return True

    except subprocess.CalledProcessError as e:
        print(f"Error en la conversión (Node.js falló):")
        print(f"STDERR: {e.stderr}")
        print(f"STDOUT: {e.stdout}")
        return False
    except Exception as e:
        print(f"Error inesperado ejecutando el subproceso: {e}")
        return False
