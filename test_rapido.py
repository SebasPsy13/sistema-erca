import sqlite3
import csv
import os

def test():
    print("🎬 Iniciando prueba ultraligera...")
    
    # 1. Borrar si existe para empezar de cero
    if os.path.exists("sistema_erca.db"):
        os.remove("sistema_erca.db")
        print("🗑️ Base de datos vieja eliminada.")

    try:
        conn = sqlite3.connect("sistema_erca.db")
        cursor = conn.cursor()
        
        # Crear tabla
        cursor.execute("CREATE TABLE pacientes (dni TEXT, paciente TEXT, edad REAL, dx TEXT, cap TEXT)")
        
        # Leer CSV de forma nativa (sin pandas)
        with open('pacientes.csv', mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            datos = [(r['dni'], r['paciente'], r['edad'], r['dx'], r['cap']) for r in reader]
            
        # Insertar
        cursor.executemany("INSERT INTO pacientes VALUES (?,?,?,?,?)", datos)
        
        # Crear tablas extra
        cursor.execute("CREATE TABLE IF NOT EXISTS seguimiento (id_registro INTEGER PRIMARY KEY AUTOINCREMENT, dni_p TEXT, fecha TEXT, urea REAL, crea REAL, hb REAL, k REAL, na REAL, tfg REAL, asistio TEXT, notas TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS agenda (id_cita INTEGER PRIMARY KEY AUTOINCREMENT, dni_p TEXT, fecha_cita TEXT, tipo TEXT)")
        
        conn.commit()
        conn.close()
        print(f"✅ ¡TERMINADO! Se cargaron {len(datos)} pacientes en tiempo récord.")

    except Exception as e:
        print(f"❌ Falló: {e}")

if __name__ == "__main__":
    test()