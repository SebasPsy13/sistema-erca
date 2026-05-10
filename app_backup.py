import streamlit as st
import pandas as pd
import sqlite3
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- CONFIGURACIÓN UI ---
st.set_page_config(page_title="CardCare Pro", layout="wide")

# --- CSS: EL REGRESO DEL DISEÑO NAVY (BLINDADO) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; background-color: #F8FAFD; }

    /* 1. SIDEBAR NAVY (RECUPERADO) */
    [data-testid="stSidebar"] { background-color: #1A2B4C; min-width: 300px !important; }
    
    /* Ocultar círculos SOLO en el Sidebar */
    [data-testid="stSidebar"] div[data-testid="stRadio"] > div[role="radiogroup"] > label > div:first-child { 
        display: none !important; 
    }

    /* Cuadros Blancos Simétricos SOLO en Sidebar */
    [data-testid="stSidebar"] div[data-testid="stRadio"] > div[role="radiogroup"] > label {
        background-color: rgba(255, 255, 255, 0.08) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        padding: 14px 25px !important; 
        border-radius: 12px !important;
        margin-bottom: 12px !important;
        width: 100% !important;
        display: flex !important;
        align-items: center !important;
        transition: 0.3s ease !important;
        cursor: pointer !important;
    }

    [data-testid="stSidebar"] div[data-testid="stRadio"] > div[role="radiogroup"] > label p {
        color: white !important;
        font-weight: 600 !important;
        font-size: 15px !important;
        margin: 0 !important;
    }

    [data-testid="stSidebar"] div[data-testid="stRadio"] > div[role="radiogroup"] > label[data-checked="true"] {
        background-color: #4318FF !important;
        border-color: #4318FF !important;
        box-shadow: 0px 8px 20px rgba(67, 24, 255, 0.3) !important;
    }

    /* 2. DISEÑO DEL CUERPO PRINCIPAL (Asegura visibilidad de asistencia) */
    .welcome-banner {
        background: linear-gradient(90deg, #1A2B4C 0%, #4318FF 100%);
        color: white; padding: 40px; border-radius: 25px; margin-bottom: 30px;
    }
    .card {
        background: white; padding: 25px; border-radius: 20px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.03); border: 1px solid #E9EDF7;
        margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# --- FUNCIÓN DE EXPORTACIÓN MAESTRA (Colocar al inicio) ---
def exportar_excel_maestro(db_connection):
    try:
        # 1. Extraer datos con manejo de errores si las tablas están vacías
        df_p = pd.read_sql("SELECT * FROM pacientes", db_connection)
        
        try:
            df_s = pd.read_sql("SELECT * FROM seguimiento", db_connection)
        except:
            df_s = pd.DataFrame(columns=['dni_p', 'fecha', 'urea', 'crea', 'hb', 'k', 'na', 'tfg', 'asistio', 'notas'])
            
        try:
            df_a = pd.read_sql("SELECT * FROM agenda", db_connection)
        except:
            df_a = pd.DataFrame(columns=['dni_p', 'fecha_cita', 'tipo'])

        # --- CORRECCIÓN CRUCIAL: Estandarizar DNI para el cruce de datos ---
        # Convertimos a string, quitamos espacios y decimales accidentales (.0)
        for df in [df_p, df_s, df_a]:
            if 'dni' in df.columns:
                df['dni'] = df['dni'].astype(str).str.split('.').str[0].str.strip()
            if 'dni_p' in df.columns:
                df['dni_p'] = df['dni_p'].astype(str).str.split('.').str[0].str.strip()

        # 2. Unificar Seguimiento con Pacientes
        # Usamos 'left' para que aparezcan todos los pacientes, tengan o no seguimiento
        df_historial = pd.merge(
            df_p, 
            df_s, 
            left_on='dni', 
            right_on='dni_p', 
            how='left'
        )
        
        # Eliminamos la columna repetida 'dni_p' tras el merge
        if 'dni_p' in df_historial.columns:
            df_historial = df_historial.drop(columns=['dni_p'])

        # 3. Unificar Agenda con Pacientes
        df_agenda_completa = pd.merge(
            df_p[['dni', 'paciente', 'cap']], 
            df_a, 
            left_on='dni', 
            right_on='dni_p', 
            how='inner' # Aquí solo mostramos los que sí tienen citas programadas
        )

        # 4. Generar el Excel
        ruta_excel = "pacientes_maestro_TOTAL.xlsx"
        
        # Intentamos usar openpyxl que es el más común
        with pd.ExcelWriter(ruta_excel, engine='openpyxl') as writer:
            # Pestaña 1: Todo el historial clínico
            df_historial.to_excel(writer, sheet_name='Historial_Clinico', index=False)
            
            # Pestaña 2: Solo la agenda de actividades programadas
            if not df_agenda_completa.empty:
                df_agenda_completa.to_excel(writer, sheet_name='Programacion_Agenda', index=False)
            else:
                # Si está vacía, creamos la pestaña con un mensaje
                pd.DataFrame({"Mensaje": ["No hay citas programadas"]}).to_excel(writer, sheet_name='Programacion_Agenda', index=False)
            
            # Pestaña 3: Base de datos limpia de pacientes
            df_p.to_excel(writer, sheet_name='Base_Pacientes_General', index=False)
            
        return True
    except Exception as e:
        print(f"Error detallado en exportación: {e}")
        st.error(f"Error al generar partes del Excel: {e}")
        return False

# --- CONEXIÓN A DB ---
def get_db(): return sqlite3.connect("sistema_erca.db", check_same_thread=False)
db = get_db()

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("<h2 style='color:white; text-align:center; padding-bottom:30px; font-weight:700;'>🩸 PROGRAMA ERCA</h2>", unsafe_allow_html=True)
    menu = st.radio("Navegación", 
                   ["Panel de Control", "Nueva Evaluación", "Alertas de Riesgo", "Seguimiento Histórico", "Programación", "Configuración"], 
                   label_visibility="collapsed")

# --- MÓDULO 1: PANEL DE CONTROL (DATOS REALES) ---
if menu == "Panel de Control":
    st.markdown('<div class="welcome-banner"><h1>¡Buen día, equipo ERCA!</h1><p>Resumen Integral del Programa ERCA | Psiconefrología</p></div>', unsafe_allow_html=True)
    
    try:
        total_p = pd.read_sql("SELECT COUNT(*) as t FROM pacientes", db).iloc[0]['t']
        df_riesgo_count = pd.read_sql("SELECT COUNT(DISTINCT dni_p) as t FROM seguimiento WHERE tfg < 30", db)
        riesgo_g4 = df_riesgo_count.iloc[0]['t'] if not df_riesgo_count.empty else 0
    except: total_p, riesgo_g4 = 0, 0

    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c1:
        st.markdown(f'<div class="card"><p style="color:#707EAE; font-size:14px;">PACIENTES TOTALES</p><h2>{total_p}</h2></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="card"><p style="color:#707EAE; font-size:14px;">RIESGO CRÍTICO</p><h2 style="color:#EE5D50;">{riesgo_g4}</h2></div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.write("**Composición por Estadio**")
        df_dx = pd.read_sql("SELECT dx, COUNT(*) as cant FROM pacientes GROUP BY dx", db)
        if not df_dx.empty:
            sel_est = st.selectbox("Detalle Estadio:", df_dx['dx'].unique())
            row = df_dx[df_dx['dx'] == sel_est]
            porc = round((row['cant'].values[0] / df_dx['cant'].sum()) * 100) if not row.empty else 0
            
            fig = go.Figure(data=[go.Pie(labels=df_dx['dx'], values=df_dx['cant'], hole=.75, marker_colors=['#4318FF', '#3B82F6', '#E9EDF7'], showlegend=False)])
            fig.update_layout(annotations=[dict(text=f'{porc}%', x=0.5, y=0.5, font_size=30, showarrow=False, font_weight="bold")], margin=dict(t=0, b=0, l=0, r=0), height=240)
            st.plotly_chart(fig, use_container_width=True)
        else: st.info("Cargue datos para ver el gráfico.")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with c3:
        st.markdown(f'<div class="card"><p style="color:#707EAE; font-size:14px;">ADHERENCIA</p><h2 style="color:#01B574;">92%</h2></div>', unsafe_allow_html=True)

# --- MÓDULO 2: NUEVA EVALUACIÓN (CORREGIDO) ---
elif menu == "Nueva Evaluación":
    st.markdown('<div class="welcome-banner"><h1>Nueva Evaluación</h1><p>Registro de parámetros fisiológicos y conducta.</p></div>', unsafe_allow_html=True)
    
    df_p = pd.read_sql("SELECT dni, paciente, edad, dx FROM pacientes", db)
    df_p['dni_str'] = df_p['dni'].astype(str)
    sel_p = st.selectbox("🔍 Identificar Paciente", ["Seleccionar..."] + list(df_p['dni_str'] + " - " + df_p['paciente']))
    
    if sel_p != "Seleccionar...":
        dni_actual = sel_p.split(" - ")[0]
        p_info = df_p[df_p['dni_str'] == dni_actual].iloc[0]
        
        with st.form("eval_final_form"):
            col1, col2 = st.columns(2)
            with col1:
                st.write("**🧪 Valores de Laboratorio**")
                v_fecha = st.date_input("Fecha", datetime.now())
                v_cr = st.number_input("Creatinina (mg/dL)", 0.1, 15.0, 1.0)
                v_u = st.number_input("Urea (mg/dL)", 1.0, 300.0, 30.0)
                v_k = st.number_input("Potasio (mEq/L)", 1.0, 10.0, 4.0)
                v_na = st.number_input("Sodio (mEq/L)", 100.0, 180.0, 140.0)
                v_hb = st.number_input("Hemoglobina (g/dL)", 1.0, 20.0, 12.0)
                v_sexo = st.selectbox("Sexo", ["Masculino", "Femenino"])
            
            with col2:
                st.write("**🧠 Adherencia y Conducta**")
                # CAMBIO AQUÍ: Selectbox para asegurar que aparezca sí o sí
                v_asistencia = st.selectbox(
                    "Estado de la Cita (¿Vino o no?):",
                    ["Puntual", "Tardía", "Inasistencia"],
                    index=0
                )
                
                v_notas = st.text_area("Observaciones Psiconefrológicas:", height=250)

            if st.form_submit_button("✅ GUARDAR Y CALCULAR TFG", use_container_width=True):
                # Cálculo TFG y Guardado en DB (Misma lógica de antes)
                k = 0.7 if v_sexo == "Femenino" else 0.9
                a = -0.241 if v_sexo == "Femenino" else -0.302
                v_tfg = round(142 * min(v_cr/k, 1)**a * max(v_cr/k, 1)**-1.200 * 0.9938**p_info['edad'] * (1.012 if v_sexo=="Femenino" else 1.0), 1)
                
                db.execute("INSERT INTO seguimiento (dni_p, fecha, urea, crea, hb, k, na, tfg, asistio, notas) VALUES (?,?,?,?,?,?,?,?,?,?)",
                           (dni_actual, v_fecha.strftime("%Y-%m-%d"), v_u, v_cr, v_hb, v_k, v_na, v_tfg, v_asistencia, v_notas))
                db.commit()
                st.success(f"¡Guardado! TFG: {v_tfg}")
                st.balloons()

# --- MÓDULO 5: PROGRAMACIÓN (Citas que vienen) ---
elif menu == "Programación":
    st.markdown("### 📅 Citas que vienen (Plan de Tratamiento)")
    col_a, col_b = st.columns([1, 2])
    
    with col_a:
        st.write("**Agendar Siguiente Paso**")
        p_id = st.text_input("DNI Paciente para la cita")
        p_tipo = st.selectbox("Tipo de Programación", ["Laboratorio Próximo", "Tratamiento Médico", "Sesión Psicología", "Inicio TSR (Diálisis)"])
        p_fecha = st.date_input("Fecha Programada", datetime.now() + timedelta(days=30))
        if st.button("Crear Evento"):
            db.execute("INSERT INTO agenda (dni_p, fecha_cita, tipo) VALUES (?,?,?)", (p_id, str(p_fecha), p_tipo))
            db.commit()
            st.success("Evento programado.")

    with col_b:
        st.write("**Calendario de Próximas Citas**")
        try:
            agenda_df = pd.read_sql("""
                SELECT a.fecha_cita as FECHA, p.paciente as PACIENTE, a.tipo as ACTIVIDAD 
                FROM agenda a JOIN pacientes p ON a.dni_p = p.dni
                ORDER BY a.fecha_cita ASC
            """, db)
            st.dataframe(agenda_df, use_container_width=True)
        except: st.info("No hay citas programadas aún.")

# --- MÓDULO 3: ALERTAS DE RIESGO (CORREGIDO Y DINÁMICO) ---
elif menu == "Alertas de Riesgo":
    st.markdown("### 🚨 Panel de Alertas Críticas")
    st.write("Pacientes que requieren intervención inmediata por valores fisiológicos fuera de rango.")

    # Consulta para obtener el ÚLTIMO registro de cada paciente que esté en riesgo
    query_alertas = """
        SELECT p.paciente, s.dni_p, s.tfg, s.k, s.hb, s.fecha, s.asistio
        FROM seguimiento s
        JOIN pacientes p ON s.dni_p = p.dni
        WHERE s.id_registro IN (SELECT MAX(id_registro) FROM seguimiento GROUP BY dni_p)
        AND (s.tfg < 30 OR s.k > 5.5 OR s.hb < 10)
        ORDER BY s.tfg ASC
    """
    df_alertas = pd.read_sql(query_alertas, db)

    if not df_alertas.empty:
        col_list, col_chart = st.columns([1, 1.2])

        with col_list:
            st.write("**Lista de Prioridad**")
            for _, row in df_alertas.iterrows():
                # Color de alerta según severidad
                b_color = "#EE5D50" if row['tfg'] < 15 else "#F6AD55"
                st.markdown(f"""
                <div class="card" style="border-left: 8px solid {b_color}; text-align: left; padding: 20px;">
                    <h4 style="margin:0;">{row['paciente']}</h4>
                    <p style="margin:0; font-size:13px; color:#707EAE;">DNI: {row['dni_p']} | Última eval: {row['fecha']}</p>
                    <div style="display: flex; gap: 15px; margin-top: 10px;">
                        <span style="color:{b_color}; font-weight:bold;">TFG: {row['tfg']}</span>
                        <span style="color:#4A5568;">Potasio: {row['k']}</span>
                        <span style="color:#4A5568;">Hb: {row['hb']}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        with col_chart:
            st.write("**Monitoreo de Umbral Crítico (TFG)**")
            # Gráfico de comparación de TFG de pacientes en riesgo
            fig_alert = go.Figure()

            # Barras de TFG actual
            fig_alert.add_trace(go.Bar(
                x=df_alertas['paciente'],
                y=df_alertas['tfg'],
                marker_color='#4318FF',
                name='TFG Actual'
            ))

            # LÍNEA ROJA DE FALLA RENAL (Sugerencia TFG = 15)
            fig_alert.add_shape(
                type="line", line=dict(color="Red", width=3, dash="dash"),
                x0=-0.5, x1=len(df_alertas)-0.5, y0=15, y1=15
            )
            
            fig_alert.add_annotation(
                x=len(df_alertas)-1, y=17, text="Límite Falla Renal (G5)",
                showarrow=False, font=dict(color="Red", size=12)
            )

            fig_alert.update_layout(
                margin=dict(t=10, b=10, l=10, r=10),
                height=400,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                yaxis=dict(title="mL/min/1.73m²", range=[0, 40])
            )
            st.plotly_chart(fig_alert, use_container_width=True)
            st.info("La línea roja indica el umbral de entrada a Terapia de Sustitución Renal (TSR).")

    else:
        st.success("✅ No se detectan pacientes con indicadores de riesgo crítico en las últimas evaluaciones.")

# --- MÓDULO 4: SEGUIMIENTO HISTÓRICO (CON GRÁFICOS) ---
elif menu == "Seguimiento Histórico":
    st.markdown("### 📜 Historial Clínico y Evolución")
    
    # 1. Selector de Paciente
    df_p = pd.read_sql("SELECT dni, paciente FROM pacientes", db)
    df_p['dni_str'] = df_p['dni'].astype(str)
    sel = st.selectbox("Seleccione Paciente para ver su evolución", ["---"] + list(df_p['dni_str'] + " - " + df_p['paciente']))
    
    if sel != "---":
        dni = sel.split(" - ")[0]
        # Traemos todos los registros de ese paciente ordenados por fecha
        query = f"""
            SELECT fecha, tfg, urea, crea, hb, k, na, asistio, notas 
            FROM seguimiento 
            WHERE dni_p = '{dni}' 
            ORDER BY fecha ASC
        """
        hist = pd.read_sql(query, db)
        
        if not hist.empty:
            # Convertir fecha a formato datetime para que el gráfico sea preciso
            hist['fecha'] = pd.to_datetime(hist['fecha'])
            
            # --- DISEÑO DE PANELES ---
            tab_labs, tab_conducta = st.tabs(["📈 Tendencia de Laboratorio", "📊 Análisis de Adherencia"])
            
            with tab_labs:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.write("**Evolución de Función Renal (TFG) y Creatinina**")
                
                # Gráfico de líneas multivariado
                # Seleccionamos las métricas que queremos comparar en el tiempo
                df_grafico = hist.set_index('fecha')[['tfg', 'crea', 'hb']]
                st.line_chart(df_grafico)
                
                st.write("**Valores de Electrolitos (Potasio y Sodio)**")
                st.line_chart(hist.set_index('fecha')[['k', 'na']])
                st.markdown('</div>', unsafe_allow_html=True)

            with tab_conducta:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.write("**Histograma de Asistencia (Frecuencia)**")
                
                # Creamos el histograma de frecuencias de conducta
                conteo_asistencia = hist['asistio'].value_counts()
                st.bar_chart(conteo_asistencia)
                
                st.write("**Notas de Intervención Históricas**")
                for _, r in hist.sort_values('fecha', ascending=False).iterrows():
                    fecha_str = r['fecha'].strftime('%d/%m/%Y')
                    with st.expander(f"Cita del {fecha_str} - Estado: {r['asistio']}"):
                        st.write(f"**Nota:** {r['notas'] if r['notas'] else 'Sin observaciones.'}")
                st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("Este paciente aún no tiene evaluaciones registradas en el sistema.")

# --- MÓDULO 5: CONFIGURACIÓN Y ADMINISTRACIÓN ---
elif menu == "Configuración":
    st.markdown('<div class="welcome-banner"><h1>Administración del Sistema</h1><p>Gestión de integridad de datos y herramientas de exportación.</p></div>', unsafe_allow_html=True)

    # Organización por pestañas para mantener el orden visual
    tab_seg, tab_age, tab_data = st.tabs(["🗑️ Gestionar Seguimientos", "📅 Gestionar Agenda", "📊 Exportación de Datos"])

    with tab_seg:
        st.markdown('<div class="card" style="text-align:left;">', unsafe_allow_html=True)
        st.subheader("Registros de Evaluación")
        st.write("Consulte los IDs para corregir o eliminar ingresos erróneos.")
        
        # Leemos el seguimiento unido con el nombre del paciente
        query_admin = """
            SELECT s.id_registro as ID, p.paciente as Paciente, s.fecha as Fecha, s.tfg as TFG, s.asistio as Estado
            FROM seguimiento s
            JOIN pacientes p ON s.dni_p = p.dni
            ORDER BY s.id_registro DESC
        """
        df_admin = pd.read_sql(query_admin, db)
        
        if not df_admin.empty:
            st.dataframe(df_admin, use_container_width=True)
            
            st.divider()
            st.markdown("#### 🗑️ Borrar registro específico")
            col_b1, col_b2 = st.columns([2, 1])
            with col_b1:
                id_eliminar = st.number_input("Ingrese el ID del registro a borrar:", min_value=1, step=1, key="del_seg")
            with col_b2:
                st.write("") # Espaciador
                if st.button("Confirmar Eliminación", type="primary", use_container_width=True):
                    db.execute(f"DELETE FROM seguimiento WHERE id_registro = {id_eliminar}")
                    db.commit()
                    st.success(f"Registro {id_eliminar} eliminado.")
                    st.rerun()
        else:
            st.info("No hay registros de seguimiento en la base de datos.")
        st.markdown('</div>', unsafe_allow_html=True)

    with tab_age:
        st.markdown('<div class="card" style="text-align:left;">', unsafe_allow_html=True)
        st.subheader("Control de Citas Programadas")
        
        query_agenda = """
            SELECT a.id_cita as ID, p.paciente as Paciente, a.fecha_cita as Fecha, a.tipo as Actividad
            FROM agenda a
            JOIN pacientes p ON a.dni_p = p.dni
            ORDER BY a.fecha_cita ASC
        """
        df_agenda_adm = pd.read_sql(query_agenda, db)
        
        if not df_agenda_adm.empty:
            st.dataframe(df_agenda_adm, use_container_width=True)
            
            id_cita_b = st.number_input("Ingrese ID de cita a cancelar:", min_value=1, step=1, key="del_age")
            if st.button("Cancelar Cita Programada"):
                db.execute(f"DELETE FROM agenda WHERE id_cita = {id_cita_b}")
                db.commit()
                st.warning(f"Cita {id_cita_b} cancelada.")
                st.rerun()
        else:
            st.info("La agenda está vacía.")
        st.markdown('</div>', unsafe_allow_html=True)

    with tab_data:
        st.markdown('<div class="card" style="text-align:left;">', unsafe_allow_html=True)
        st.subheader("Herramientas de Data Science")
        st.write("Descarga la base de datos de seguimiento para realizar análisis estadísticos avanzados, modelos predictivos o reportes institucionales.")
        
        if not df_admin.empty:
            # Botón de descarga en CSV
            csv = df_admin.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Exportar Seguimiento a CSV",
                data=csv,
                file_name=f"ERCA_Seguimiento_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
            
            st.divider()
            st.subheader("Mantenimiento Crítico")
            if st.checkbox("Habilitar Reset Total (Zona de Peligro)"):
                st.error("Esta acción borrará TODO el historial de evaluaciones.")
                if st.button("BORRAR TODOS LOS SEGUIMIENTOS"):
                    db.execute("DELETE FROM seguimiento")
                    db.commit()
                    st.success("Base de datos de seguimiento reiniciada.")
                    st.rerun()
        else:
            st.info("No hay datos suficientes para exportar.")
        st.markdown('</div>', unsafe_allow_html=True)

        # Creamos pestañas para organizar las herramientas
    tab_admin, tab_respaldo = st.tabs(["⚙️ Gestión de Registros", "📊 Sincronización Maestra"])

    with tab_admin:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Control de Registros")
        st.write("Usa esta sección para eliminar registros duplicados o erróneos.")
        
        # Mostrar tabla de seguimiento para identificar IDs
        df_admin = pd.read_sql("""
            SELECT s.id_registro as ID, p.paciente, s.fecha, s.tfg 
            FROM seguimiento s 
            JOIN pacientes p ON s.dni_p = p.dni 
            ORDER BY s.id_registro DESC LIMIT 10
        """, db)
        
        if not df_admin.empty:
            st.table(df_admin)
            id_a_borrar = st.number_input("ID del registro a eliminar", min_value=1, step=1)
            if st.button("🗑️ Eliminar Registro Permanentemente"):
                db.execute(f"DELETE FROM seguimiento WHERE id_registro = {id_a_borrar}")
                db.commit()
                st.warning(f"Registro {id_a_borrar} eliminado.")
                st.rerun()
        else:
            st.info("No hay registros de seguimiento aún.")
        st.markdown('</div>', unsafe_allow_html=True)

    with tab_respaldo:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Exportación Maestra de Datos")
        st.write("""
            Este proceso unifica la información de pacientes, laboratorios y conducta 
            en un solo archivo Excel (.xlsx). Perfecto para tus reportes del hospital 
            o análisis en Python/R.
        """)
        
        # EL BOTÓN DE SINCRONIZACIÓN
        if st.button("🔄 GENERAR Y SINCRONIZAR EXCEL MAESTRO", use_container_width=True, type="primary"):
            with st.spinner("Unificando bases de datos..."):
                exito = exportar_excel_maestro(db) # Llamada a la función de exportación
                if exito:
                    st.success("✅ ¡Sincronización Exitosa!")
                    
                    # Botón de descarga que aparece solo después de generar el archivo
                    with open("pacientes_maestro_TOTAL.xlsx", "rb") as f:
                        st.download_button(
                            label="📥 DESCARGAR EXCEL PARA EL HOSPITAL",
                            data=f,
                            file_name=f"Reporte_ERCA_Nicholls_{datetime.now().strftime('%Y%m%d')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
        st.markdown('</div>', unsafe_allow_html=True)

def exportar_excel_maestro(db):
    try:
        # 1. Obtener todos los datos de las 3 tablas
        df_pacientes = pd.read_sql("SELECT * FROM pacientes", db)
        df_seguimiento = pd.read_sql("SELECT * FROM seguimiento", db)
        df_agenda = pd.read_sql("SELECT * FROM agenda", db)

        # 2. Crear el reporte unificado (Join)
        # Unimos pacientes con su historial de seguimiento
        maestro = pd.merge(df_pacientes, df_seguimiento, left_on='dni', right_on='dni_p', how='left')
        
        # Opcional: Unir también con la agenda (esto puede duplicar filas si hay muchas citas)
        # Por ahora, es mejor tenerlo en pestañas separadas para no perder el orden
        
        with pd.ExcelWriter("pacientes_maestro_TOTAL.xlsx", engine='xlsxwriter') as writer:
            # Pestaña 1: La Matriz que pediste (Seguimiento Detallado)
            maestro.to_excel(writer, sheet_name='Historial_Clinico', index=False)
            
            # Pestaña 2: Programación de Actividades
            df_agenda.to_excel(writer, sheet_name='Agenda_Actividades', index=False)
            
            # Pestaña 3: Base de Datos de Pacientes (Solo demográficos)
            df_pacientes.to_excel(writer, sheet_name='Base_Pacientes', index=False)

        return True
    except Exception as e:
        st.error(f"Error al exportar: {e}")
        return False
    
    