# app/cleanup_duplicates.py
import sys
import os

# Añadir el directorio padre al path para que encuentre los módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from app.database import DATABASE_URL
from app.models import Contract

def cleanup_duplicate_contracts():
    """
    Encuentra y elimina contratos duplicados, conservando el más reciente.
    Un duplicado se define por tener el mismo project_id y numero_contrato.
    """
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        print("Buscando contratos duplicados...")

        # Agrupar por project_id y numero_contrato para encontrar duplicados
        duplicate_groups = db.query(
            Contract.project_id,
            Contract.numero_contrato,
            func.count(Contract.id).label('count')
        ).group_by(
            Contract.project_id,
            Contract.numero_contrato
        ).having(func.count(Contract.id) > 1).all()

        if not duplicate_groups:
            print("No se encontraron contratos duplicados. ¡Todo limpio!")
            return

        print(f"Se encontraron {len(duplicate_groups)} grupos de contratos duplicados.")
        
        for group in duplicate_groups:
            print(f"Procesando duplicados para Proyecto ID: {group.project_id}, Contrato N°: '{group.numero_contrato}'")
            
            # Obtener todos los contratos del grupo duplicado, ordenados por ID descendente (el más nuevo primero)
            contracts_to_check = db.query(Contract).filter(
                Contract.project_id == group.project_id,
                Contract.numero_contrato == group.numero_contrato
            ).order_by(Contract.id.desc()).all()
            
            # Conservar el primero (el más nuevo) y eliminar el resto
            for contract_to_delete in contracts_to_check[1:]:
                print(f"  -> Eliminando contrato duplicado con ID: {contract_to_delete.id}")
                db.delete(contract_to_delete)
        
        db.commit()
        print("\nLimpieza de duplicados completada exitosamente.")

    except Exception as e:
        print(f"\nOcurrió un error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    # Ejecutar la función de limpieza
    cleanup_duplicate_contracts()