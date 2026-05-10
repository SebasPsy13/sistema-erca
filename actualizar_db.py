import pandas as pd
import sqlite3
import os

def cargar_csv_a_db():
    # Nombre del archivo CSV que ya tienes
    archivo_csv = "pacientes.csv" 
    db_name = "sistema_erca.db"

    if not os.path.exists(archivo_csv):
        print(f"❌ Error: No encuentro el archivo '{archivo_csv}' en esta carpeta.")
        return

    try:
        # 1. Leer los datos
        print("📖 Leyendo datos del CSV...")
        df = pd.read_csv(archivo_csv)
        
        # Limpieza rápida: asegurar que los DNI sean texto para evitar errores de búsqueda
        df['dni'] = df['dni'].astype(str).str.split('.').str[0]
        
        # 2. Conectar a la base de datos
        conn = sqlite3.connect(db_name)
        
        # 3. Reemplazar SOLO la tabla de pacientes
        # Usamos 'replace' para que la estructura de columnas (como el CAP) se actualice
        df.to_sql("pacientes", conn, if_exists="replace", index=False)
        
        # 4. Asegurar que existan las tablas de trabajo (si no existen)
        conn.execute('''CREATE TABLE IF NOT EXISTS seguimiento (
                            id_registro INTEGER PRIMARY KEY AUTOINCREMENT,
                            dni_p TEXT, fecha TEXT, urea REAL, crea REAL, 
                            hb REAL, k REAL, na REAL, tfg REAL, 
                            asistio TEXT, notas TEXT)''')
        
        conn.execute('''CREATE TABLE IF NOT EXISTS agenda (
                            id_cita INTEGER PRIMARY KEY AUTOINCREMENT,
                            dni_p TEXT, fecha_cita TEXT, tipo TEXT)''')
        
        conn.commit()
        conn.close()
        
        print(f"✅ ¡Éxito! Se han cargado {len(df)} pacientes a '{db_name}'.")
        print("🚀 Ya puedes iniciar tu App de Streamlit.")

    except Exception as e:
        print(f"❌ Ocurrió un error: {e}")

if __name__ == "__main__":
    cargar_csv_a_db()