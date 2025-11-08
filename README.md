# ConTech PM API

## Descripción

**ConTech PM API** es un backend robusto diseñado para la gestión de proyectos en el sector de la construcción (Construction Technology). Proporciona una base sólida para desarrollar una aplicación completa de gestión, abarcando desde la administración de compañías y usuarios hasta el seguimiento detallado de tareas, finanzas y documentación.

La API está construida con FastAPI, lo que garantiza un alto rendimiento, una excelente documentación automática y un desarrollo moderno basado en estándares de Python.

## Características Principales

- **Autenticación y Autorización**: Sistema de login basado en tokens JWT (OAuth2) con diferentes roles de usuario (super_admin, user).
- **Gestión Multi-Compañía**: Un `super_admin` puede crear y gestionar múltiples compañías.
- **Gestión de Proyectos**: Creación y seguimiento de proyectos, asignados a una compañía específica.
- **Gestión de Tareas**: Sistema de tareas jerárquicas (subtareas) con fechas, prioridades y asignación de responsables.
- **Gestión Financiera**:
  - **Partidas de Trabajo (Work Items)**: Catálogo de conceptos de trabajo presupuestados.
  - **Contratistas**: Administración de un directorio de contratistas por compañía.
  - **Contratos**: Vinculación de contratistas y partidas de trabajo con montos y condiciones.
  - **Estimaciones**: Seguimiento de los pagos y avances financieros sobre los contratos.
- **Sistema de Gestión Documental (DMS)**:
  - Estructura de carpetas anidadas por proyecto.
  - Carga de documentos con versionamiento.
- **Importación/Exportación de Datos**: Funcionalidades para importar y exportar datos (tareas, contratistas, etc.) usando archivos Excel.

## Stack Tecnológico

- **Backend**: Python 3
- **Framework**: FastAPI
- **Base de Datos**: SQLAlchemy ORM (compatible con SQLite, PostgreSQL, etc.)
- **Validación de Datos**: Pydantic
- **Servidor ASGI**: Uvicorn
- **Autenticación**: Passlib (para hashing de contraseñas), Python-JOSE (para JWT)
- **Manipulación de Excel**: Openpyxl, Pandas

---

## Instalación y Puesta en Marcha

Sigue estos pasos para configurar y ejecutar el proyecto en tu entorno local.

### 1. Prerrequisitos

- **Python 3.10** o superior. Puedes descargarlo desde python.org.

### 2. Clonar el Repositorio

```bash
git clone <URL_DEL_REPOSITORIO>
cd bimproject
```

### 3. Crear y Activar un Entorno Virtual

Es una buena práctica aislar las dependencias del proyecto.

```bash
# En Windows
python -m venv .venv
.venv\Scripts\activate

# En macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 4. Instalar Dependencias

Crea un archivo `requirements.txt` en la raíz del proyecto con el siguiente contenido:

```txt
fastapi
uvicorn[standard]
sqlalchemy
passlib[bcrypt]
python-jose[cryptography]
python-multipart
openpyxl
pandas
```

Luego, instala las dependencias con pip:

```bash
pip install -r requirements.txt
```

### 5. Ejecutar la Aplicación

El servidor Uvicorn se encargará de ejecutar la aplicación FastAPI. El flag `--reload` reiniciará el servidor automáticamente cada vez que detecte un cambio en el código.

```bash
uvicorn app.main:app --reload
```

Una vez ejecutado, el servidor estará disponible en `http://127.0.0.1:8000`.

## Uso Básico

### Usuario Super Admin por Defecto

Al iniciar la aplicación por primera vez, se creará automáticamente un usuario `super_admin` con las siguientes credenciales. Úsalo para empezar a crear compañías y usuarios.

- **Email**: `admin@admin.com`
- **Contraseña**: `admin`

### Documentación Interactiva de la API

FastAPI genera automáticamente una documentación interactiva que te permite explorar y probar todos los endpoints de la API directamente desde tu navegador.

- **Swagger UI**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc