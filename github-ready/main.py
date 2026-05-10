"""
SISTEMA ERCA - Backend FastAPI
Conexión con Base de Datos SQLite + API REST + Servir HTML
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import sqlite3
import json
from datetime import datetime
import os
from pathlib import Path

app = FastAPI(title="SISTEMA ERCA API")

# ======================== CONFIG ========================
# Ruta a la base de datos existente en la raíz
DB_PATH = "sistema_erca.db"

# ======================== MODELOS ========================
class Paciente(BaseModel):
    dni: str
    nombre: str
    edad: int
    dx: str  # Estadio ERCA
    cap: str

class Evaluacion(BaseModel):
    dni_p: str
    fecha: str
    crea: float
    urea: float
    hb: float
    k: float
    na: float
    acr: float
    tfg: float
    estadio: str
    asistio: str
    notas: str

class Cita(BaseModel):
    dni_p: str
    fecha_cita: str
    tipo: str
    estado: str

# ======================== DATABASE MANAGER ========================
class DatabaseManager:
    """Gestiona todas las operaciones con la BD"""

    @staticmethod
    def init_db():
        """Crear tablas si no existen"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Tabla pacientes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pacientes (
                dni TEXT PRIMARY KEY,
                paciente TEXT NOT NULL,
                edad INTEGER,
                dx TEXT,
                cap TEXT,
                fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Tabla seguimiento
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS seguimiento (
                id_registro INTEGER PRIMARY KEY AUTOINCREMENT,
                dni_p TEXT NOT NULL,
                fecha TEXT,
                urea REAL,
                crea REAL,
                hb REAL,
                k REAL,
                na REAL,
                acr REAL,
                tfg REAL,
                estadio TEXT,
                asistio TEXT,
                notas TEXT,
                FOREIGN KEY (dni_p) REFERENCES pacientes(dni)
            )
        ''')

        # Tabla agenda
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agenda (
                id_cita INTEGER PRIMARY KEY AUTOINCREMENT,
                dni_p TEXT NOT NULL,
                fecha_cita TEXT,
                tipo TEXT,
                estado TEXT,
                FOREIGN KEY (dni_p) REFERENCES pacientes(dni)
            )
        ''')

        conn.commit()
        conn.close()

    @staticmethod
    def get_connection():
        """Obtener conexión a BD"""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def dict_from_row(row):
        """Convertir Row a dict"""
        return dict(row) if row else None

# Inicializar BD al startup
DatabaseManager.init_db()

# ======================== RUTAS API - PACIENTES ========================
@app.get("/api/pacientes")
def get_pacientes():
    """Obtener todos los pacientes"""
    conn = DatabaseManager.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pacientes ORDER BY paciente ASC")
    pacientes = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return pacientes

@app.get("/api/pacientes/{dni}")
def get_paciente(dni: str):
    """Obtener paciente por DNI"""
    conn = DatabaseManager.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pacientes WHERE dni = ?", (dni,))
    paciente = cursor.fetchone()
    conn.close()

    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    return dict(paciente)

@app.post("/api/pacientes")
def crear_paciente(paciente: Paciente):
    """Crear nuevo paciente"""
    conn = DatabaseManager.get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO pacientes (dni, paciente, edad, dx, cap)
            VALUES (?, ?, ?, ?, ?)
        ''', (paciente.dni, paciente.nombre, paciente.edad, paciente.dx, paciente.cap))
        conn.commit()
        conn.close()
        return {"mensaje": "Paciente creado", "dni": paciente.dni}
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="El DNI ya existe")

@app.put("/api/pacientes/{dni}")
def actualizar_paciente(dni: str, paciente: Paciente):
    """Actualizar paciente"""
    conn = DatabaseManager.get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE pacientes
        SET paciente=?, edad=?, dx=?, cap=?
        WHERE dni=?
    ''', (paciente.nombre, paciente.edad, paciente.dx, paciente.cap, dni))

    conn.commit()
    conn.close()
    return {"mensaje": "Paciente actualizado"}

# ======================== RUTAS API - EVALUACIONES ========================
@app.get("/api/evaluaciones/{dni_p}")
def get_evaluaciones(dni_p: str):
    """Obtener evaluaciones de un paciente"""
    conn = DatabaseManager.get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM seguimiento
        WHERE dni_p = ?
        ORDER BY fecha DESC
    ''', (dni_p,))
    evaluaciones = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return evaluaciones

@app.post("/api/evaluaciones")
def crear_evaluacion(eval_data: Evaluacion):
    """Crear nueva evaluación"""
    conn = DatabaseManager.get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO seguimiento
            (dni_p, fecha, urea, crea, hb, k, na, acr, tfg, estadio, asistio, notas)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (eval_data.dni_p, eval_data.fecha, eval_data.urea, eval_data.crea,
              eval_data.hb, eval_data.k, eval_data.na, eval_data.acr,
              eval_data.tfg, eval_data.estadio, eval_data.asistio, eval_data.notas))
        conn.commit()
        conn.close()
        return {"mensaje": "Evaluación registrada"}
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=400, detail=str(e))

# ======================== RUTAS API - ALERTAS ========================
@app.get("/api/alertas")
def get_alertas():
    """Obtener pacientes en riesgo (TFG bajo)"""
    conn = DatabaseManager.get_connection()
    cursor = conn.cursor()

    # Obtener última evaluación de cada paciente
    cursor.execute('''
        SELECT p.dni, p.paciente, p.edad, p.dx,
               (SELECT tfg FROM seguimiento
                WHERE dni_p = p.dni
                ORDER BY fecha DESC LIMIT 1) as tfg_actual,
               (SELECT estadio FROM seguimiento
                WHERE dni_p = p.dni
                ORDER BY fecha DESC LIMIT 1) as estadio_actual
        FROM pacientes p
        WHERE (SELECT tfg FROM seguimiento
               WHERE dni_p = p.dni
               ORDER BY fecha DESC LIMIT 1) < 30
        ORDER BY tfg_actual ASC
    ''')

    alertas = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return alertas

# ======================== RUTAS API - ESTADÍSTICAS ========================
@app.get("/api/estadisticas")
def get_estadisticas():
    """Obtener estadísticas del sistema"""
    conn = DatabaseManager.get_connection()
    cursor = conn.cursor()

    # Total de pacientes
    cursor.execute("SELECT COUNT(*) as total FROM pacientes")
    total_pacientes = cursor.fetchone()["total"]

    # Pacientes por estadio
    cursor.execute('''
        SELECT dx, COUNT(*) as cantidad
        FROM pacientes
        GROUP BY dx
    ''')
    por_estadio = {row["dx"]: row["cantidad"] for row in cursor.fetchall()}

    # Evaluaciones este mes
    cursor.execute('''
        SELECT COUNT(*) as total FROM seguimiento
        WHERE strftime('%Y-%m', fecha) = strftime('%Y-%m', 'now')
    ''')
    evaluaciones_mes = cursor.fetchone()["total"]

    conn.close()

    return {
        "total_pacientes": total_pacientes,
        "por_estadio": por_estadio,
        "evaluaciones_mes": evaluaciones_mes
    }

# ======================== RUTAS API - CITAS ========================
@app.get("/api/citas/{dni_p}")
def get_citas(dni_p: str):
    """Obtener citas de un paciente"""
    conn = DatabaseManager.get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM agenda
        WHERE dni_p = ?
        ORDER BY fecha_cita DESC
    ''', (dni_p,))
    citas = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return citas

@app.post("/api/citas")
def crear_cita(cita: Cita):
    """Crear nueva cita"""
    conn = DatabaseManager.get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO agenda (dni_p, fecha_cita, tipo, estado)
        VALUES (?, ?, ?, ?)
    ''', (cita.dni_p, cita.fecha_cita, cita.tipo, cita.estado))

    conn.commit()
    conn.close()
    return {"mensaje": "Cita creada"}

# ======================== SERVIR HTML ========================
@app.get("/")
def serve_root():
    """Servir el archivo HTML principal"""
    return FileResponse("index.html", media_type="text/html")

@app.get("/index.html")
def serve_html():
    """Servir el archivo HTML"""
    return FileResponse("index.html", media_type="text/html")

# ======================== HEALTH CHECK ========================
@app.get("/api/health")
def health_check():
    """Verificar que la API está funcionando"""
    return {"status": "ok", "message": "SISTEMA ERCA API v2.0"}

# ======================== INSTRUCCIONES ========================
if __name__ == "__main__":
    import uvicorn
    print("""
    ╔════════════════════════════════════════╗
    ║   SISTEMA ERCA - Backend FastAPI      ║
    ║   Ejecutando en http://localhost:8000 ║
    ╚════════════════════════════════════════╝

    Documentación API: http://localhost:8000/docs
    Base de datos: sistema_erca.db
    """)
    uvicorn.run(app, host="0.0.0.0", port=8000)
