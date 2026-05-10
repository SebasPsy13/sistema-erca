import pandas as pd
import sqlite3

def sincronizar_base_de_datos():
    try:
        # 1. Conectar (o crear) la base de datos
        conn = sqlite3.connect("sistema_erca.db")
        
        # 2. Cargar pacientes desde el Excel
        # Asegúrate de que el archivo se llame pacientes.xlsx en tu carpeta
        df = pd.read_excel("pacientes.xlsx")
        df.columns = [c.lower().replace('.', '').strip() for c in df.columns]
        df.to_sql("pacientes", conn, if_exists="replace", index=False)
        
        # 3. RECONSTRUIR TABLA SEGUIMIENTO (La clave del error)
        # Borramos la tabla para asegurarnos que se cree con id_registro
        conn.execute("DROP TABLE IF EXISTS seguimiento")
        conn.execute('''CREATE TABLE seguimiento (
                            id_registro INTEGER PRIMARY KEY AUTOINCREMENT,
                            dni_p TEXT, 
                            fecha TEXT, 
                            urea REAL, 
                            crea REAL, 
                            hb REAL, 
                            k REAL, 
                            na REAL, 
                            tfg REAL, 
                            asistio TEXT, 
                            notas TEXT)''')
        
        conn.commit()
        conn.close()
        print("✅ ¡Sincronización Exitosa! La columna 'id_registro' ya existe.")
        
    except Exception as e:
        print(f"❌ Error al sincronizar: {e}")

if __name__ == "__main__":
    sincronizar_base_de_datos()