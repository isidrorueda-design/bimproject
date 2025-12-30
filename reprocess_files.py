import os
import sys
sys.path.append(os.getcwd())
from app.utils import convert_ifc_to_frag
UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")
print(f"Checking for IFC files in: {UPLOAD_DIR}")
if not os.path.exists(UPLOAD_DIR):
    print("Uploads directory not found.")
    sys.exit(1)
files = [f for f in os.listdir(UPLOAD_DIR) if f.lower().endswith(".ifc")]
if not files:
    print("No IFC files found.")
    sys.exit(0)

print(f"Found {len(files)} IFC files. Starting conversion...")

success_count = 0
fail_count = 0

for f in files:
    ifc_path = os.path.join(UPLOAD_DIR, f)
    frag_path = os.path.splitext(ifc_path)[0] + ".frag"
    
    if os.path.exists(frag_path):
        print(f"Skipping {f} (already converted)")
        continue
        
    print(f"Converting {f}...")
    result = convert_ifc_to_frag(ifc_path, UPLOAD_DIR)
    
    if result:
        print(f" -> Success: {f}")
        success_count += 1
    else:
        print(f" -> FAILED: {f}")
        fail_count += 1

print(f"\nSummary: {success_count} converted, {fail_count} failed.")
