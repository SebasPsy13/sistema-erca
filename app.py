"""
SISTEMA ERCA - VERSIÓN MODERNA
Aplicación de registro de atenciones para pacientes con ERCA (Enfermedad Renal Crónica Avanzada)

Estructura modular mejorada con mejor UX/UI y lógica separada
"""

import streamlit as st
import pandas as pd
import sqlite3
import plotly.graph_objects as go
from datetime import datetime, timedelta
from decimal import Decimal
import math

# ============================================
# CONFIGURACIÓN Y ESTILOS
# ============================================

st.set_page_config(
    page_title="SISTEMA ERCA",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS modernos
STYLES = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&family=Inter:wght@300;400;500;600&display=swap');

:root {
    --color-primary-dark: #3a0ca3;
    --color-primary-medium: #3f37c9;
    --color-primary-light: #4cc9f0;
    --color-success: #00b894;
    --color-warning: #fdcb6e;
    --color-danger: #d63031;
}

* {
    font-family: 'Inter', sans-serif;
}

h1, h2, h3 {
    font-family: 'Poppins', sans-serif;
}

.banner {
    background: linear-gradient(135deg, #3a0ca3 0%, #3f37c9 50%, #4cc9f0 100%);
    color: white;
    padding: 40px;
    border-radius: 24px;
    margin-bottom: 30px;
}

.banner h1 {
    font-size: 32px;
    margin-bottom: 8px;
}

.stat-card {
    background: white;
    padding: 24px;
    border-radius: 20px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    border: 1px solid #e2e8f0;
    transition: all 0.3s ease;
}

.stat-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 24px rgba(0,0,0,0.12);
}

.stat-label {
    font-size: 12px;
    font-weight: 600;
    color: #718096;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 8px;
}

.stat-value {
    font-size: 40px;
    font-weight: 700;
    background: linear-gradient(135deg, #3a0ca3, #4cc9f0);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.action-card {
    background: linear-gradient(135deg, #3a0ca3, #3f37c9);
    color: white;
    padding: 24px;
    border-radius: 20px;
    text-align: center;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s ease;
    border: none;
    box-shadow: 0 2px 8px rgba(58, 12, 163, 0.1);
}

.action-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 16px 48px rgba(58, 12, 163, 0.25);
}

.patient-card {
    border-left: 4px solid #fdcb6e;
    background: white;
    padding: 16px;
    border-radius: 12px;
    margin-bottom: 12px;
    transition: all 0.2s ease;
}

.patient-card.attended {
    border-left-color: #00b894;
}

.patient-card.absent {
    border-left-color: #d63031;
}

.patient-card:hover {
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1a1f3a 0%, #2d1b4e 100%);
}

[data-testid="stSidebar"] button {
    border-radius: 12px !important;
}
</style>
"""

st.markdown(STYLES, unsafe_allow_html=True)

# ============================================
# BASE DE DATOS - FUNCIONES AUXILIARES
# ============================================

class DatabaseManager:
    """Gestor centralizado de la base de datos"""

    def __init__(self, db_path="sistema_erca.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Inicializa las tablas si no existen"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Tabla de pacientes
        c.execute('''CREATE TABLE IF NOT EXISTS pacientes (
            dni TEXT PRIMARY KEY,
            paciente TEXT NOT NULL,
            edad INTEGER NOT NULL,
            dx TEXT NOT NULL,
            cap TEXT,
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')

        # Tabla de seguimiento (evaluaciones)
        c.execute('''CREATE TABLE IF NOT EXISTS seguimiento (
            id_registro INTEGER PRIMARY KEY AUTOINCREMENT,
            dni_p TEXT NOT NULL,
            fecha DATE NOT NULL,
            urea REAL,
            crea REAL,
            hb REAL,
            k REAL,
            na REAL,
            acr REAL,
            tfg REAL,
            asistio TEXT,
            notas TEXT,
            FOREIGN KEY (dni_p) REFERENCES pacientes(dni)
        )''')

        # Tabla de agenda (citas programadas)
        c.execute('''CREATE TABLE IF NOT EXISTS agenda (
            id_cita INTEGER PRIMARY KEY AUTOINCREMENT,
            dni_p TEXT NOT NULL,
            fecha_cita DATE NOT NULL,
            tipo TEXT NOT NULL,
            estado TEXT DEFAULT 'programada',
            FOREIGN KEY (dni_p) REFERENCES pacientes(dni)
        )''')

        conn.commit()
        conn.close()

    def get_connection(self):
        """Obtiene una conexión a la BD"""
        return sqlite3.connect(self.db_path)

    def execute_query(self, query, params=None):
        """Ejecuta una query y retorna resultados"""
        conn = self.get_connection()
        if params:
            df = pd.read_sql_query(query, conn, params=params)
        else:
            df = pd.read_sql_query(query, conn)
        conn.close()
        return df

    def execute_update(self, query, params=None):
        """Ejecuta una query de inserción/actualización"""
        conn = self.get_connection()
        c = conn.cursor()
        if params:
            c.execute(query, params)
        else:
            c.execute(query)
        conn.commit()
        conn.close()

# ============================================
# CÁLCULOS CLÍNICOS
# ============================================

class CalculosClinico:
    """Cálculos de parámetros clínicos ERCA"""

    @staticmethod
    def calcular_tfg_ckd_epi(creatinina: float, edad: int, sexo: str) -> float:
        """
        Calcula TFG según fórmula CKD-EPI

        TFG = 142 × (Cr/K)^A × (max(Cr/K, 1))^-1.200 × 0.9938^edad × [1.012 si mujer]
        """
        k = 0.7 if sexo == "Femenino" else 0.9
        a = -0.241 if sexo == "Femenino" else -0.302

        cr_k = creatinina / k
        tfg = 142 * (cr_k ** a) * (max(cr_k, 1) ** -1.200) * (0.9938 ** edad)

        if sexo == "Femenino":
            tfg *= 1.012

        return round(tfg, 1)

    @staticmethod
    def obtener_estadio_erca(tfg: float) -> str:
        """Obtiene el estadio ERCA según TFG"""
        if tfg >= 90:
            return "G1 - Normal (TFG ≥90)"
        elif tfg >= 60:
            return "G2 - Leve (TFG 60-89)"
        elif tfg >= 45:
            return "G3a - Moderada (TFG 45-59)"
        elif tfg >= 30:
            return "G3b - Severa (TFG 30-44)"
        elif tfg >= 15:
            return "G4 - Muy Severa (TFG 15-29)"
        else:
            return "G5 - Falla Renal (TFG <15)"

    @staticmethod
    def obtener_color_tfg(tfg: float) -> str:
        """Obtiene el color según riesgo de TFG"""
        if tfg < 15:
            return "🔴 CRÍTICO"
        elif tfg < 30:
            return "🟠 ALTO RIESGO"
        elif tfg < 45:
            return "🟡 MODERADO"
        else:
            return "🟢 ESTABLE"

# ============================================
# COMPONENTES DE UI
# ============================================

def banner_principal():
    """Banner de bienvenida principal"""
    st.markdown("""
    <div class="banner">
        <h1>¡Bienvenido, Equipo ERCA!</h1>
        <p>Resumen Integral del Programa de Atención Renal</p>
    </div>
    """, unsafe_allow_html=True)

def mostrar_estadisticas(db: DatabaseManager):
    """Muestra las tarjetas de estadísticas principales"""
    col1, col2, col3 = st.columns(3)

    # Estadística 1: Pacientes totales
    with col1:
        try:
            total_p = db.execute_query("SELECT COUNT(*) as total FROM pacientes").iloc[0]['total']
        except:
            total_p = 0

        st.metric(
            label="Pacientes Totales",
            value=total_p,
            delta=None
        )

    # Estadística 2: Riesgo crítico
    with col2:
        try:
            riesgo = db.execute_query(
                "SELECT COUNT(DISTINCT dni_p) as total FROM seguimiento WHERE tfg < 15"
            ).iloc[0]['total']
        except:
            riesgo = 0

        st.metric(
            label="Riesgo Crítico (TFG <15)",
            value=riesgo,
            delta=None
        )

    # Estadística 3: Adherencia
    with col3:
        st.metric(
            label="Adherencia",
            value="92%",
            delta="+2%"
        )

def grafico_estadio_erca(db: DatabaseManager):
    """Gráfico donut de composición por estadio"""
    try:
        df_dx = db.execute_query(
            "SELECT dx, COUNT(*) as cant FROM pacientes GROUP BY dx"
        )

        if not df_dx.empty:
            fig = go.Figure(data=[go.Pie(
                labels=df_dx['dx'],
                values=df_dx['cant'],
                hole=.75,
                marker_colors=['#3a0ca3', '#3f37c9', '#4cc9f0', '#00b894']
            )])

            fig.update_layout(
                height=350,
                margin=dict(t=0, b=0, l=0, r=0),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay pacientes registrados aún")
    except Exception as e:
        st.error(f"Error al cargar el gráfico: {e}")

# ============================================
# PÁGINAS PRINCIPALES
# ============================================

def pagina_panel_control(db: DatabaseManager):
    """Página principal del panel de control"""
    banner_principal()

    # Estadísticas
    st.subheader("Resumen de Estadísticas")
    mostrar_estadisticas(db)

    # Gráfico y calendario
    col_grafico, col_calendario = st.columns(2)

    with col_grafico:
        st.subheader("Composición por Estadio")
        grafico_estadio_erca(db)

    with col_calendario:
        st.subheader("Próximas Citas")
        try:
            df_agenda = db.execute_query("""
                SELECT p.paciente, a.fecha_cita, a.tipo
                FROM agenda a
                JOIN pacientes p ON a.dni_p = p.dni
                WHERE a.fecha_cita >= DATE('now')
                ORDER BY a.fecha_cita ASC
                LIMIT 5
            """)

            if not df_agenda.empty:
                st.dataframe(df_agenda, use_container_width=True, hide_index=True)
            else:
                st.info("No hay citas programadas")
        except:
            st.info("Error al cargar el calendario")

def pagina_registro_pacientes(db: DatabaseManager):
    """Página para registrar nuevos pacientes"""
    st.title("📋 Registro de Nuevos Pacientes")

    with st.form("form_registro_paciente"):
        col1, col2 = st.columns(2)

        with col1:
            dni = st.text_input("DNI (8 dígitos)", max_chars=8)
            nombre = st.text_input("Nombre Completo")
            edad = st.number_input("Edad", min_value=18, max_value=120, value=50)

        with col2:
            cap = st.selectbox("CAP", ["CAP Los Olivos", "CAP San Isidro", "CAP La Molina"])
            estadio = st.selectbox("Estadio ERCA", [
                "G1 - Normal (TFG ≥90)",
                "G2 - Leve (TFG 60-89)",
                "G3a - Moderada (TFG 45-59)",
                "G3b - Severa (TFG 30-44)",
                "G4 - Muy Severa (TFG 15-29)",
                "G5 - Falla Renal (TFG <15)"
            ])

        if st.form_submit_button("✅ Guardar Paciente", use_container_width=True):
            if not dni or not nombre:
                st.error("Por favor completa todos los campos")
            else:
                try:
                    db.execute_update(
                        "INSERT INTO pacientes (dni, paciente, edad, dx, cap) VALUES (?, ?, ?, ?, ?)",
                        (dni, nombre, edad, estadio, cap)
                    )
                    st.success(f"✅ Paciente {nombre} registrado exitosamente")
                except Exception as e:
                    st.error(f"Error al registrar: {e}")

def pagina_atencion_dia(db: DatabaseManager):
    """Página de atención del día"""
    st.title("🏥 Atención del Día")

    fecha_seleccionada = st.date_input("Seleccionar Fecha", value=datetime.now())

    # Buscar pacientes con citas programadas
    try:
        df_pacientes = db.execute_query("""
            SELECT p.dni, p.paciente, p.edad, a.fecha_cita
            FROM agenda a
            JOIN pacientes p ON a.dni_p = p.dni
            WHERE a.fecha_cita = ?
            ORDER BY p.paciente
        """, (fecha_seleccionada.strftime("%Y-%m-%d"),))

        if not df_pacientes.empty:
            st.info(f"📌 {len(df_pacientes)} pacientes programados para esta fecha")

            # Seleccionar paciente
            paciente_sel = st.selectbox(
                "Seleccionar Paciente",
                df_pacientes['paciente'].tolist()
            )

            if paciente_sel:
                # Formulario de atención
                with st.form("form_atencion"):
                    st.subheader("Parámetros Fisiológicos")

                    col1, col2 = st.columns(2)

                    with col1:
                        creatinina = st.number_input("Creatinina (mg/dL)", 0.1, 15.0, 1.0, step=0.1)
                        urea = st.number_input("Urea (mg/dL)", 1.0, 300.0, 30.0, step=1.0)
                        hb = st.number_input("Hemoglobina (g/dL)", 1.0, 20.0, 12.0, step=0.1)

                    with col2:
                        k = st.number_input("Potasio (mEq/L)", 1.0, 10.0, 4.0, step=0.1)
                        na = st.number_input("Sodio (mEq/L)", 100.0, 180.0, 140.0, step=1.0)
                        acr = st.number_input("Albumina/Creatinina", 0.0, 500.0, 30.0, step=1.0)

                    sexo = st.selectbox("Sexo", ["Masculino", "Femenino"])
                    asistencia = st.selectbox("Estado Asistencia", ["Puntual", "Tardía", "Inasistencia"])
                    notas = st.text_area("Observaciones Psiconefrológicas")

                    # Mostrar cálculo TFG
                    paciente_info = df_pacientes[df_pacientes['paciente'] == paciente_sel].iloc[0]
                    tfg = CalculosClinico.calcular_tfg_ckd_epi(creatinina, paciente_info['edad'], sexo)

                    st.info(f"📊 **TFG Calculado: {tfg} mL/min/1.73m²** - {CalculosClinico.obtener_estadio_erca(tfg)}")

                    if st.form_submit_button("✅ Finalizar Atención", use_container_width=True):
                        try:
                            db.execute_update(
                                """INSERT INTO seguimiento
                                (dni_p, fecha, urea, crea, hb, k, na, acr, tfg, asistio, notas)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                (
                                    paciente_info['dni'],
                                    fecha_seleccionada.strftime("%Y-%m-%d"),
                                    urea, creatinina, hb, k, na, acr, tfg, asistencia, notas
                                )
                            )
                            st.success("✅ Atención registrada correctamente")
                            st.balloons()
                        except Exception as e:
                            st.error(f"Error: {e}")
        else:
            st.warning("No hay pacientes programados para esta fecha")

    except Exception as e:
        st.error(f"Error: {e}")

def pagina_alertas_riesgo(db: DatabaseManager):
    """Página de alertas de riesgo"""
    st.title("🚨 Alertas de Riesgo")

    try:
        # Pacientes con TFG < 15
        df_alertas = db.execute_query("""
            SELECT p.paciente, s.dni_p, s.tfg, s.k, s.hb, s.fecha
            FROM seguimiento s
            JOIN pacientes p ON s.dni_p = p.dni
            WHERE s.id_registro IN (SELECT MAX(id_registro) FROM seguimiento GROUP BY dni_p)
            AND (s.tfg < 15 OR s.k > 5.5 OR s.hb < 10)
            ORDER BY s.tfg ASC
        """)

        if not df_alertas.empty:
            st.warning(f"⚠️ {len(df_alertas)} pacientes con indicadores críticos")

            for _, row in df_alertas.iterrows():
                color = "🔴" if row['tfg'] < 15 else "🟠"
                with st.expander(f"{color} {row['paciente']} - TFG: {row['tfg']}"):
                    col1, col2, col3 = st.columns(3)
                    col1.metric("TFG", f"{row['tfg']} mL/min/1.73m²")
                    col2.metric("Potasio", f"{row['k']} mEq/L")
                    col3.metric("Hemoglobina", f"{row['hb']} g/dL")
        else:
            st.success("✅ No se detectan pacientes con riesgo crítico")

    except Exception as e:
        st.error(f"Error: {e}")

def pagina_historial_clinico(db: DatabaseManager):
    """Página de historial clínico"""
    st.title("📊 Historial Clínico")

    # Buscador de pacientes
    df_pacientes = db.execute_query("SELECT dni, paciente FROM pacientes ORDER BY paciente")

    if not df_pacientes.empty:
        paciente_sel = st.selectbox(
            "Buscar Paciente",
            df_pacientes['paciente'].tolist()
        )

        dni_sel = df_pacientes[df_pacientes['paciente'] == paciente_sel]['dni'].iloc[0]

        # Obtener historial
        df_historial = db.execute_query("""
            SELECT fecha, tfg, crea, urea, hb, k, na, asistio, notas
            FROM seguimiento
            WHERE dni_p = ?
            ORDER BY fecha ASC
        """, (dni_sel,))

        if not df_historial.empty:
            df_historial['fecha'] = pd.to_datetime(df_historial['fecha'])

            # Tabs
            tab1, tab2 = st.tabs(["📈 Evolución de Laboratorio", "📊 Adherencia"])

            with tab1:
                st.subheader("TFG y Creatinina")
                st.line_chart(df_historial.set_index('fecha')[['tfg', 'crea']])

                st.subheader("Electrolitos")
                st.line_chart(df_historial.set_index('fecha')[['k', 'na']])

            with tab2:
                st.subheader("Histograma de Asistencia")
                asistencia_counts = df_historial['asistio'].value_counts()
                st.bar_chart(asistencia_counts)

                st.subheader("Notas Clínicas")
                for _, row in df_historial.iterrows():
                    with st.expander(f"📝 {row['fecha'].strftime('%d/%m/%Y')} - {row['asistio']}"):
                        st.write(row['notas'] if row['notas'] else "Sin observaciones")
        else:
            st.info("Este paciente no tiene evaluaciones registradas")
    else:
        st.warning("No hay pacientes registrados aún")

# ============================================
# APLICACIÓN PRINCIPAL
# ============================================

def main():
    """Función principal de la aplicación"""

    # Inicializar base de datos
    db = DatabaseManager()

    # Sidebar
    with st.sidebar:
        st.markdown("### 🩸 PROGRAMA ERCA")
        menu = st.radio(
            "Navegación",
            ["Panel Principal", "Registro de Pacientes", "Atención del Día",
             "Alertas de Riesgo", "Historial Clínico"],
            label_visibility="collapsed"
        )

    # Renderizar página seleccionada
    if menu == "Panel Principal":
        pagina_panel_control(db)
    elif menu == "Registro de Pacientes":
        pagina_registro_pacientes(db)
    elif menu == "Atención del Día":
        pagina_atencion_dia(db)
    elif menu == "Alertas de Riesgo":
        pagina_alertas_riesgo(db)
    elif menu == "Historial Clínico":
        pagina_historial_clinico(db)

if __name__ == "__main__":
    main()
