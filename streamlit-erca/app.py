"""
SISTEMA ERCA — Streamlit v2.1
Gestión de Atención para Pacientes con Enfermedad Renal Crónica Avanzada
Requiere: streamlit>=1.36.0, plotly, pandas, fpdf2
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date
from typing import Optional
from sqlalchemy import create_engine, text

try:
    from fpdf import FPDF
    FPDF_OK = True
except ImportError:
    FPDF_OK = False

# ─────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="SISTEMA ERCA",
    page_icon="🩸",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# BASE DE DATOS — Supabase / PostgreSQL
# ─────────────────────────────────────────────
@st.cache_resource
def get_engine():
    """Motor SQLAlchemy compartido (una sola conexión para toda la sesión)."""
    url = st.secrets["supabase"]["db_url"]
    return create_engine(url, pool_pre_ping=True)


def init_db():
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS pacientes (
                dni TEXT PRIMARY KEY,
                paciente TEXT NOT NULL,
                edad INTEGER,
                dx TEXT,
                cap TEXT,
                fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS seguimiento (
                id_registro SERIAL PRIMARY KEY,
                dni_p TEXT NOT NULL REFERENCES pacientes(dni),
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
                notas TEXT
            )
        """))
        # Columnas que pueden faltar en BDs migradas
        for col, tipo in [("acr","REAL"),("tfg","REAL"),("estadio","TEXT"),
                          ("k","REAL"),("na","REAL"),("hb","REAL"),
                          ("notas","TEXT"),("asistio","TEXT")]:
            try:
                conn.execute(text(
                    f"ALTER TABLE seguimiento ADD COLUMN IF NOT EXISTS {col} {tipo}"
                ))
            except Exception:
                pass
        conn.commit()


def get_pacientes() -> pd.DataFrame:
    return pd.read_sql("SELECT * FROM pacientes ORDER BY paciente", get_engine())


def get_seguimiento(dni: Optional[str] = None) -> pd.DataFrame:
    if dni:
        return pd.read_sql(
            text("SELECT * FROM seguimiento WHERE dni_p = :dni ORDER BY fecha DESC"),
            get_engine(), params={"dni": dni}
        )
    return pd.read_sql("SELECT * FROM seguimiento ORDER BY fecha DESC", get_engine())


def registrar_paciente(dni, nombre, edad, dx, cap):
    try:
        with get_engine().connect() as conn:
            conn.execute(text("""
                INSERT INTO pacientes (dni, paciente, edad, dx, cap)
                VALUES (:dni, :nombre, :edad, :dx, :cap)
                ON CONFLICT (dni) DO UPDATE SET
                    paciente = EXCLUDED.paciente,
                    edad     = EXCLUDED.edad,
                    dx       = EXCLUDED.dx,
                    cap      = EXCLUDED.cap
            """), {"dni": dni, "nombre": nombre, "edad": int(edad), "dx": dx, "cap": cap})
            conn.commit()
        return True, "OK"
    except Exception as e:
        return False, str(e)


def registrar_evaluacion(dni_p, fecha, crea, urea, hb, k, na, acr, tfg, estadio, asistio, notas):
    try:
        with get_engine().connect() as conn:
            conn.execute(text("""
                INSERT INTO seguimiento
                    (dni_p, fecha, crea, urea, hb, k, na, acr, tfg, estadio, asistio, notas)
                VALUES
                    (:dni_p, :fecha, :crea, :urea, :hb, :k, :na, :acr, :tfg,
                     :estadio, :asistio, :notas)
            """), {
                "dni_p": dni_p, "fecha": str(fecha),
                "crea": float(crea), "urea": float(urea), "hb": float(hb),
                "k": float(k), "na": float(na), "acr": float(acr),
                "tfg": float(tfg), "estadio": estadio,
                "asistio": asistio, "notas": notas,
            })
            conn.commit()
        return True, "OK"
    except Exception as e:
        return False, str(e)

# ─────────────────────────────────────────────
# TFG — CKD-EPI
# ─────────────────────────────────────────────
def calcular_tfg(creatinina: float, edad: int, sexo: str) -> Optional[float]:
    if not creatinina or creatinina <= 0 or not edad or not sexo:
        return None
    kappa  = 0.7   if sexo == "Femenino" else 0.9
    alpha  = -0.329 if sexo == "Femenino" else -0.411
    factor = 1.018  if sexo == "Femenino" else 1.0
    cr_k   = creatinina / kappa
    base   = cr_k ** alpha if cr_k < 1 else cr_k ** -1.209
    return round(141 * base * (0.9929 ** edad) * factor, 1)


def estadio_desde_tfg(tfg: Optional[float]) -> str:
    if tfg is None or tfg <= 0: return "—"
    if tfg >= 90: return "G1 - Normal"
    if tfg >= 60: return "G2 - Leve"
    if tfg >= 45: return "G3a - Moderada"
    if tfg >= 30: return "G3b - Severa"
    if tfg >= 15: return "G4 - Muy Severa"
    return "G5 - Falla Renal"

# ─────────────────────────────────────────────
# PDF
# ─────────────────────────────────────────────
def _ascii(texto: str) -> str:
    """Reemplaza caracteres Unicode problemáticos por equivalentes ASCII para fpdf2."""
    return (str(texto)
            .replace("—", "-").replace("–", "-").replace("→", "->")
            .replace("✓", "OK").replace("✗", "X").replace("✅", "[OK]")
            .replace("❌", "[X]").replace("🔴", "[!]").replace("🟡", "[~]")
            .replace("á","a").replace("é","e").replace("í","i")
            .replace("ó","o").replace("ú","u").replace("ü","u")
            .replace("Á","A").replace("É","E").replace("Í","I")
            .replace("Ó","O").replace("Ú","U").replace("Ü","U")
            .replace("ñ","n").replace("Ñ","N")
            .replace("⁺","").replace("²","2").replace("³","3")
            .replace("’","'").replace("“",'"').replace("”",'"'))


def generar_pdf(lista_pacientes: list, fecha) -> bytes:
    pdf = FPDF()
    pdf.add_page()

    # Cabecera
    pdf.set_fill_color(58, 12, 163)
    pdf.rect(0, 0, 210, 38, "F")
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", "B", 18)
    pdf.set_xy(10, 8)
    pdf.cell(0, 9, "SISTEMA ERCA", 0, 1, "C")
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 7, _ascii(f"Reporte de Atencion del Dia  {fecha}"), 0, 1, "C")

    # Resumen
    pdf.set_text_color(45, 55, 72)
    pdf.set_xy(10, 46)
    n_total     = len(lista_pacientes)
    n_atendidos = sum(1 for p in lista_pacientes if p["estado"] == "atendido")
    n_ausentes  = sum(1 for p in lista_pacientes if p["estado"] == "ausente")
    n_pend      = sum(1 for p in lista_pacientes if p["estado"] == "pendiente")

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Resumen del Dia", 0, 1)
    pdf.set_font("Arial", "", 10)
    pdf.set_fill_color(248, 250, 252)
    pdf.cell(45, 7, f"Total pacientes: {n_total}", 1, 0, "C", True)
    pdf.cell(45, 7, f"Atendidos: {n_atendidos}", 1, 0, "C", True)
    pdf.cell(45, 7, f"Ausentes: {n_ausentes}", 1, 0, "C", True)
    pdf.cell(45, 7, f"Pendientes: {n_pend}", 1, 1, "C", True)
    pdf.ln(4)

    # Tabla de pacientes
    pdf.set_fill_color(58, 12, 163)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", "B", 9)
    pdf.cell(10, 8, "#",       1, 0, "C", True)
    pdf.cell(58, 8, "Nombre",  1, 0, "C", True)
    pdf.cell(25, 8, "DNI",     1, 0, "C", True)
    pdf.cell(28, 8, "Estadio", 1, 0, "C", True)
    pdf.cell(28, 8, "Estado",  1, 0, "C", True)
    pdf.cell(0,  8, "CAP",     1, 1, "C", True)

    pdf.set_font("Arial", "", 9)
    for i, p in enumerate(lista_pacientes):
        fill = i % 2 == 0
        pdf.set_fill_color(248, 250, 252) if fill else pdf.set_fill_color(255, 255, 255)
        pdf.set_text_color(45, 55, 72)
        estado_s = ("Atendido" if p["estado"] == "atendido"
                    else "Ausente" if p["estado"] == "ausente" else "Pendiente")
        pdf.cell(10, 7, str(i + 1),                        1, 0, "C", fill)
        pdf.cell(58, 7, _ascii(p["nombre"][:32]),          1, 0, "",  fill)
        pdf.cell(25, 7, _ascii(p["dni"]),                  1, 0, "C", fill)
        pdf.cell(28, 7, _ascii(p.get("dx", "")[:16]),     1, 0, "",  fill)
        pdf.cell(28, 7, _ascii(estado_s),                  1, 0, "C", fill)
        pdf.cell(0,  7, _ascii(p.get("cap","")[:22]),     1, 1, "",  fill)

    # Evaluaciones del día (solo atendidos)
    atendidos_con_eval = [p for p in lista_pacientes if p["estado"] == "atendido"]
    if atendidos_con_eval:
        pdf.ln(6)
        pdf.set_font("Arial", "B", 12)
        pdf.set_text_color(45, 55, 72)
        pdf.cell(0, 8, "Detalle de Evaluaciones", 0, 1)
        pdf.set_font("Arial", "", 9)

        for p in atendidos_con_eval:
            fila = pd.read_sql(
                text("SELECT * FROM seguimiento WHERE dni_p = :dni ORDER BY fecha DESC LIMIT 1"),
                get_engine(), params={"dni": p["dni"]}
            )
            if not fila.empty:
                r = fila.iloc[0]
                tfg_str = f"{r['tfg']:.1f}" if r.get("tfg") and r["tfg"] > 0 else "—"
                pdf.set_fill_color(240, 240, 255)
                pdf.set_font("Arial", "B", 9)
                pdf.cell(0, 7, _ascii(f"  {p['nombre']} - DNI: {p['dni']}"), 1, 1, "", True)
                pdf.set_font("Arial", "", 8)
                row_text = _ascii(
                    f"  Crea: {r.get('crea','-')}  Urea: {r.get('urea','-')}  "
                    f"Hb: {r.get('hb','-')}  K: {r.get('k','-')}  "
                    f"Na: {r.get('na','-')}  ACR: {r.get('acr','-')}  TFG: {tfg_str}"
                )
                pdf.set_fill_color(255, 255, 255)
                pdf.cell(0, 6, row_text, 1, 1, "", True)
                if r.get("notas"):
                    notas_str = _ascii(str(r["notas"])[:100])
                    pdf.cell(0, 6, f"  Obs: {notas_str}", 1, 1, "", True)

    # Pie de página
    pdf.ln(8)
    pdf.set_font("Arial", "I", 8)
    pdf.set_text_color(113, 128, 150)
    pdf.cell(0, 5, _ascii(f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')} - SISTEMA ERCA v2.1"), 0, 1, "C")

    return bytes(pdf.output())

# ─────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&family=Inter:wght@300;400;500;600&display=swap');

#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }

html, body, [data-testid="stAppViewContainer"] {
    font-family: 'Inter', sans-serif !important;
    background-color: #f8fafc !important;
}
.main .block-container {
    padding: 28px 36px 40px 36px !important;
    max-width: 100% !important;
}

/* ── SIDEBAR ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1a1f3a 0%, #2d1b4e 100%) !important;
    min-width: 252px !important; max-width: 252px !important;
}
[data-testid="stSidebar"] > div:first-child { padding: 28px 14px 20px 14px; }
[data-testid="stSidebar"] .stButton > button {
    width: 100% !important;
    background: rgba(255,255,255,0.08) !important;
    border: 1px solid rgba(255,255,255,0.10) !important;
    color: #fff !important; border-radius: 12px !important;
    padding: 12px 16px !important; font-weight: 500 !important;
    font-size: 13px !important; text-align: left !important;
    margin-bottom: 5px !important; transition: all 180ms !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,0.14) !important;
    transform: translateX(4px) !important;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: #3a0ca3 !important; border-color: #3f37c9 !important;
    box-shadow: 0 6px 18px rgba(58,12,163,0.35) !important;
}
.sidebar-title {
    font-family: 'Poppins', sans-serif; font-size: 21px; font-weight: 700;
    margin-bottom: 24px;
    background: linear-gradient(135deg,#4cc9f0,#a78bfa);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
}

/* ── BANNER ── */
.banner {
    background: linear-gradient(135deg,#3a0ca3 0%,#3f37c9 50%,#4cc9f0 100%);
    border-radius: 20px; padding: 28px 36px; color: white; margin-bottom: 24px;
}
.banner h1 { font-family:'Poppins',sans-serif; font-size:26px; font-weight:700; margin:0 0 4px 0; color:white; }
.banner p  { font-size:14px; opacity:.92; margin:0; color:white; }

/* ── STAT CARDS ── */
.stat-card {
    background: white; border-radius: 16px; padding: 18px 20px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.07); border: 1px solid #e2e8f0;
    transition: transform 280ms, box-shadow 280ms;
}
.stat-card:hover { transform: translateY(-3px); box-shadow: 0 7px 20px rgba(0,0,0,0.11); }
.stat-label { font-size:11px; font-weight:600; color:#718096; text-transform:uppercase; letter-spacing:.6px; margin:0 0 5px 0; }
.stat-value { font-family:'Poppins',sans-serif; font-size:34px; font-weight:700;
    background: linear-gradient(135deg,#3a0ca3,#4cc9f0);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text; line-height:1.1; margin:0; }
.stat-value.danger  { background:linear-gradient(135deg,#d63031,#e17055); -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text; }
.stat-value.success { background:linear-gradient(135deg,#00b894,#55efc4); -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text; }
.stat-value.warning { background:linear-gradient(135deg,#fdcb6e,#e17055); -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text; }

/* ── CARD ── */
.card { background:white; border-radius:16px; padding:16px 20px; box-shadow:0 2px 8px rgba(0,0,0,0.07); border:1px solid #e2e8f0; margin-bottom:16px; }
.card h3 { font-family:'Poppins',sans-serif; font-size:15px; font-weight:600; margin:0 0 12px 0; color:#2d3748; }

/* ── PATIENT LIST ITEM ── */
.pac-item {
    display:flex; align-items:center; justify-content:space-between;
    background:white; border-radius:12px; padding:10px 14px;
    border:1px solid #e2e8f0; margin-bottom:6px;
    transition: box-shadow 180ms;
}
.pac-item:hover { box-shadow:0 3px 10px rgba(0,0,0,0.07); }
.pac-item-name  { font-weight:600; font-size:13px; color:#2d3748; margin:0 0 2px 0; }
.pac-item-info  { font-size:11.5px; color:#718096; margin:0; }

/* ── PATIENT CARDS (agenda) ── */
.patient-card { background:white; border-left:4px solid #fdcb6e; border-radius:12px;
    padding:10px 14px; margin-bottom:8px; border-top:1px solid #e2e8f0;
    border-right:1px solid #e2e8f0; border-bottom:1px solid #e2e8f0; }
.patient-card.attended { border-left-color:#00b894; }
.patient-card.absent   { border-left-color:#d63031; }
.patient-card-name { font-weight:600; font-size:13px; color:#2d3748; margin:0 0 3px 0; }
.patient-card-info { font-size:11.5px; color:#718096; margin:0; }

/* ── ALERT CARDS ── */
.alert-card { background:white; border-left:4px solid #d63031; border-radius:12px;
    padding:12px 16px; margin-bottom:8px; box-shadow:0 2px 6px rgba(0,0,0,0.05);
    border-top:1px solid #e2e8f0; border-right:1px solid #e2e8f0; border-bottom:1px solid #e2e8f0; }
.alert-card.warning-card { border-left-color:#fdcb6e; }
.alert-name  { font-weight:600; font-size:13.5px; color:#2d3748; margin:0 0 4px 0; }
.alert-info  { font-size:12px; color:#718096; margin:0 0 3px 0; }
.alert-badge { display:inline-block; padding:3px 10px; border-radius:20px; font-size:11px; font-weight:600; margin-top:4px; }
.badge-critical { background:#fff5f5; color:#d63031; border:1px solid #feb2b2; }
.badge-warning  { background:#fffaf0; color:#dd6b20; border:1px solid #fbd38d; }

/* ── MAIN BUTTONS ── */
.main .stButton > button {
    border-radius:14px !important; font-family:'Poppins',sans-serif !important;
    font-weight:600 !important; font-size:13.5px !important;
    padding:9px 20px !important; transition:transform 180ms, box-shadow 180ms !important;
}
.main .stButton > button[kind="primary"] {
    background:linear-gradient(135deg,#3a0ca3,#3f37c9) !important;
    border:none !important; color:white !important;
}
.main .stButton > button[kind="primary"]:hover {
    transform:translateY(-2px) !important; box-shadow:0 7px 20px rgba(58,12,163,0.26) !important;
}

/* ── INFO / COUNT / TFG BOXES ── */
.info-box { background:linear-gradient(135deg,rgba(76,201,240,.09),rgba(58,12,163,.07)); border-radius:13px; padding:14px 18px; margin-bottom:14px; }
.info-box-label { font-size:10.5px; font-weight:600; color:#718096; text-transform:uppercase; letter-spacing:.5px; margin:0 0 5px 0; }
.info-box-value { font-size:18px; font-weight:700; color:#3a0ca3; margin:0; font-family:'Poppins',sans-serif; }
.info-box-sub   { font-size:12px; color:#718096; margin:3px 0 0 0; }

.count-box { background:linear-gradient(135deg,rgba(76,201,240,.09),rgba(58,12,163,.07)); border-radius:13px; padding:12px; text-align:center; margin:12px 0; }
.count-value { font-family:'Poppins',sans-serif; font-size:36px; font-weight:700; color:#3a0ca3; margin:0; }
.count-label { font-size:11px; color:#718096; margin:2px 0 0 0; }

.tfg-box { background:linear-gradient(135deg,rgba(76,201,240,.09),rgba(58,12,163,.07)); border-radius:13px; padding:14px; text-align:center; margin-top:12px; }
.tfg-label   { font-size:11px; color:#718096; margin:0 0 5px 0; }
.tfg-value   { font-family:'Poppins',sans-serif; font-size:28px; font-weight:700; color:#3a0ca3; margin:0; }
.tfg-estadio { font-size:12px; color:#718096; margin:3px 0 0 0; }

/* ── MESSAGES ── */
.msg-success { background:#d4edda; border:1px solid #c3e6cb; color:#155724; padding:10px 14px; border-radius:12px; margin-bottom:12px; font-size:13.5px; }
.msg-error   { background:#f8d7da; border:1px solid #f5c6cb; color:#721c24; padding:10px 14px; border-radius:12px; margin-bottom:12px; font-size:13.5px; }

.section-divider { border:none; border-top:2px solid #e2e8f0; margin:20px 0; }

/* ── FORM SECTION TITLES ── */
.form-section-title {
    font-size:10.5px; font-weight:700; color:#a0aec0;
    text-transform:uppercase; letter-spacing:1px;
    margin:18px 0 6px 0; padding:0;
    border-bottom: 1.5px solid #edf2f7; padding-bottom:5px;
}
.form-section-title:first-child { margin-top:4px; }

/* ── PATIENT SELECTED CARD ── */
.pac-selected-card {
    background: linear-gradient(135deg,rgba(58,12,163,0.06),rgba(76,201,240,0.07));
    border: 1.5px solid rgba(58,12,163,0.18);
    border-radius: 14px; padding: 12px 16px; margin-bottom: 4px;
}
.pac-sel-tag  { font-size:10px; font-weight:700; color:#3a0ca3; text-transform:uppercase; letter-spacing:.7px; }
.pac-sel-name { font-family:'Poppins',sans-serif; font-size:16px; font-weight:700; color:#2d3748; margin:4px 0 3px 0; }
.pac-sel-info { font-size:12px; color:#718096; margin:0; }

/* ── TFG LIVE BOX ── */
.tfg-live-box {
    display:flex; align-items:center; justify-content:space-between;
    background:linear-gradient(135deg,rgba(58,12,163,0.06),rgba(76,201,240,0.08));
    border:1.5px solid rgba(58,12,163,0.15); border-radius:14px;
    padding:12px 18px; margin-top:14px;
}
.tfg-live-label  { font-size:10.5px; font-weight:700; color:#718096; text-transform:uppercase; letter-spacing:.6px; }
.tfg-live-value  { font-family:'Poppins',sans-serif; font-size:26px; font-weight:700; }
.tfg-live-unit   { font-size:12px; font-weight:400; color:#718096; }
.tfg-live-estadio{ font-size:13px; font-weight:600; color:#3a0ca3; }

/* ── INPUTS ── */
[data-testid="stTextInput"] input, [data-testid="stNumberInput"] input,
[data-testid="stTextArea"] textarea {
    border-radius:12px !important; border:2px solid #e2e8f0 !important;
    font-family:'Inter',sans-serif !important; font-size:13.5px !important;
}
[data-testid="stDataFrame"] { border-radius:13px; overflow:hidden; }
</style>
"""


def inject_css():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# HELPERS HTML
# ─────────────────────────────────────────────
def banner(title: str, subtitle: str):
    st.markdown(f'<div class="banner"><h1>{title}</h1><p>{subtitle}</p></div>', unsafe_allow_html=True)


def stat_card(label: str, value, style: str = "primary"):
    cls = f"stat-value {style}" if style != "primary" else "stat-value"
    st.markdown(f'<div class="stat-card"><p class="stat-label">{label}</p><p class="{cls}">{value}</p></div>', unsafe_allow_html=True)


def pac_card(nombre, info, status=""):
    st.markdown(f'<div class="patient-card {status}"><p class="patient-card-name">{nombre}</p><p class="patient-card-info">{info}</p></div>', unsafe_allow_html=True)


def alert_card(nombre, dni, tfg, dx, cap, fecha=None):
    critico   = tfg < 15
    card_cls  = "" if critico else "warning-card"
    badge_cls = "badge-critical" if critico else "badge-warning"
    badge_txt = "G5 - Falla Renal" if critico else "G4 - Muy Severa"
    est = estadio_desde_tfg(tfg)
    date_str = f" | Último: {fecha}" if fecha else ""
    st.markdown(
        f'<div class="alert-card {card_cls}">'
        f'<p class="alert-name">{nombre}</p>'
        f'<p class="alert-info">DNI: {dni} | {dx} | {cap}{date_str}</p>'
        f'<p class="alert-info">TFG: <strong>{tfg:.1f} mL/min/1.73m²</strong> — {est}</p>'
        f'<span class="alert-badge {badge_cls}">{badge_txt}</span></div>',
        unsafe_allow_html=True,
    )

# ─────────────────────────────────────────────
# FORMULARIO DE EVALUACIÓN (compartido entre dialogs)
# ─────────────────────────────────────────────
def _form_evaluacion(form_key: str, paciente_info: dict, fecha_default=None):
    """Renderiza el form de evaluación clínica. Retorna dict de datos."""

    # ── FECHA ──
    st.markdown('<p class="form-section-title">Fecha de Evaluación</p>', unsafe_allow_html=True)
    fecha_eval = st.date_input(
        "Fecha", value=fecha_default or date.today(),
        key=f"{form_key}_fecha", label_visibility="collapsed"
    )

    # ── LABORATORIO ──
    st.markdown('<p class="form-section-title">Parámetros de Laboratorio</p>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        crea = st.number_input("Creatinina (mg/dL)",   0.1, 15.0,  value=1.0,   step=0.1, format="%.1f", help="Ref: 0.6–1.2",   key=f"{form_key}_crea")
        hb   = st.number_input("Hemoglobina (g/dL)",   1.0, 20.0,  value=12.0,  step=0.1, format="%.1f", help="Ref: 12–17.5",   key=f"{form_key}_hb")
        na   = st.number_input("Sodio (mEq/L)",        100.0,160.0,value=140.0, step=1.0,               help="Ref: 136–145",   key=f"{form_key}_na")
    with c2:
        urea = st.number_input("Urea (mg/dL)",         1.0, 300.0, value=20.0,  step=1.0,               help="Ref: 7–20",      key=f"{form_key}_urea")
        k    = st.number_input("Potasio (mEq/L)",      1.0, 10.0,  value=4.0,   step=0.1, format="%.1f", help="Ref: 3.5–5.0",   key=f"{form_key}_k")
        acr  = st.number_input("Alb/Creat (mg/g)",     0.0, 500.0, value=0.0,   step=1.0,               help="Ref: 0–30",      key=f"{form_key}_acr")

    # ── TFG EN VIVO ──
    if crea and paciente_info.get("edad"):
        sexo_preview = st.session_state.get(f"{form_key}_sexo", "")
        if sexo_preview and sexo_preview in ("Masculino", "Femenino"):
            tfg_live = calcular_tfg(crea, paciente_info["edad"], sexo_preview)
            if tfg_live:
                est_live = estadio_desde_tfg(tfg_live)
                col_tfg = ("#d63031" if tfg_live < 15
                           else "#e17055" if tfg_live < 30
                           else "#dd6b20" if tfg_live < 60
                           else "#00b894")
                st.markdown(
                    f'<div class="tfg-live-box">'
                    f'<span class="tfg-live-label">TFG calculado (CKD-EPI)</span>'
                    f'<span class="tfg-live-value" style="color:{col_tfg}">{tfg_live:.1f}'
                    f'<span class="tfg-live-unit"> mL/min/1.73m²</span></span>'
                    f'<span class="tfg-live-estadio">{est_live}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    # ── DATOS CLÍNICOS ──
    st.markdown('<p class="form-section-title">Datos Clínicos</p>', unsafe_allow_html=True)
    sc1, sc2 = st.columns(2)
    with sc1:
        sexo = st.selectbox("Sexo biológico", ["", "Masculino", "Femenino"], key=f"{form_key}_sexo")
    with sc2:
        asistencia = st.selectbox("Estado de Asistencia", ["Puntual", "Tardía", "Inasistencia"], key=f"{form_key}_asist")

    # ── NOTAS ──
    st.markdown('<p class="form-section-title">Observaciones</p>', unsafe_allow_html=True)
    notas = st.text_area(
        "Notas", placeholder="Observaciones psiconefrológicas, adherencia al tratamiento...",
        height=80, key=f"{form_key}_notas", label_visibility="collapsed"
    )

    return dict(fecha=fecha_eval, crea=crea, urea=urea, hb=hb, k=k, na=na,
                acr=acr, sexo=sexo, asistencia=asistencia, notas=notas)

# ─────────────────────────────────────────────
# DIALOGS (requieren Streamlit ≥ 1.36)
# ─────────────────────────────────────────────

@st.dialog("Registrar Nuevo Paciente")
def dialog_registrar_paciente():
    c1, c2 = st.columns(2)
    with c1:
        dni    = st.text_input("DNI (8 dígitos)", max_chars=8)
        nombre = st.text_input("Nombre Completo")
    with c2:
        edad = st.number_input("Edad", min_value=18, max_value=120, step=1, value=None, placeholder="Ej: 45")
        cap  = st.text_input("CAP", placeholder="Ej: CAP San Isidro")

    estadio = st.selectbox("Estadio ERCA", [
        "", "G1 - Normal (TFG ≥90)", "G2 - Leve (TFG 60-89)",
        "G3a - Moderada (TFG 45-59)", "G3b - Severa (TFG 30-44)",
        "G4 - Muy Severa (TFG 15-29)", "G5 - Falla Renal (TFG <15)",
    ])

    bc1, bc2 = st.columns(2)
    with bc1:
        guardar = st.button("Guardar Paciente", type="primary", use_container_width=True)
    with bc2:
        if st.button("Cancelar", use_container_width=True):
            st.rerun()

    if guardar:
        if not dni or len(dni) != 8 or not dni.isdigit():
            st.error("DNI debe tener 8 dígitos numéricos.")
        elif not nombre.strip():
            st.error("Nombre obligatorio.")
        elif edad is None:
            st.error("Edad obligatoria.")
        elif not cap.strip():
            st.error("Ingresa el CAP.")
        elif not estadio:
            st.error("Selecciona estadio ERCA.")
        else:
            dx = estadio.split(" - ")[0]
            ok, msg = registrar_paciente(dni, nombre.strip(), int(edad), dx, cap)
            if ok:
                st.success(f"✅ {nombre.strip()} registrado correctamente.")
                st.rerun()
            else:
                st.error(msg)


@st.dialog("Alertas de Riesgo")
def dialog_alertas():
    df = pd.read_sql("""
        SELECT p.paciente, p.dni, p.dx, p.cap, s.tfg, s.fecha
        FROM pacientes p
        JOIN seguimiento s ON s.dni_p = p.dni
        INNER JOIN (
            SELECT dni_p, MAX(fecha) AS mf FROM seguimiento WHERE tfg > 0 GROUP BY dni_p
        ) lt ON s.dni_p = lt.dni_p AND s.fecha = lt.mf
        WHERE s.tfg < 30 AND s.tfg > 0
        ORDER BY s.tfg ASC
    """, get_engine())

    if df.empty:
        st.success("✅ Sin alertas críticas. No hay pacientes con TFG < 30.")
        return

    st.markdown(f"**{len(df)} paciente(s) requieren atención**")
    for _, row in df.iterrows():
        alert_card(row["paciente"], row["dni"], row["tfg"], row["dx"], row["cap"], row["fecha"])


@st.dialog("Historial Clinico")
def dialog_historial():
    pacientes_df = get_pacientes()
    busq = st.text_input("Buscar por DNI o Nombre")

    if busq:
        mask = (pacientes_df["dni"].str.contains(busq, case=False, na=False)
                | pacientes_df["paciente"].str.contains(busq, case=False, na=False))
        lista = pacientes_df[mask].drop_duplicates(subset=["dni"]).head(20)
    else:
        lista = pacientes_df.drop_duplicates(subset=["dni"]).head(20)

    if "dialog_hist_pac" not in st.session_state:
        st.session_state["dialog_hist_pac"] = None

    with st.container(height=220):
        for i, (_, row) in enumerate(lista.iterrows()):
            c1, c2 = st.columns([4, 1])
            c1.markdown(f"**{row['paciente']}** — DNI: {row['dni']}")
            if c2.button("Ver", key=f"dhpac_{row['dni']}_{i}"):
                st.session_state["dialog_hist_pac"] = row["dni"]

    pac_dni = st.session_state.get("dialog_hist_pac")
    if not pac_dni:
        st.info("Selecciona un paciente de la lista para ver su historial.")
        return

    pac_rows = pacientes_df[pacientes_df["dni"] == pac_dni]
    if pac_rows.empty:
        return
    pac = pac_rows.iloc[0]
    st.markdown(
        f'<div class="info-box"><p class="info-box-label">Paciente</p>'
        f'<p class="info-box-value">{pac["paciente"]}</p>'
        f'<p class="info-box-sub">DNI: {pac["dni"]} | {pac["edad"]} años | {pac["dx"]} | {pac["cap"]}</p></div>',
        unsafe_allow_html=True,
    )

    seg = get_seguimiento(pac_dni).sort_values("fecha")
    if seg.empty:
        st.info("Sin evaluaciones registradas.")
        return

    valid = seg[seg["tfg"] > 0]
    if not valid.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=valid["fecha"], y=valid["tfg"], mode="lines+markers",
            line=dict(color="#3a0ca3", width=3), marker=dict(size=8),
            fill="tozeroy", fillcolor="rgba(58,12,163,0.07)"))
        fig.update_layout(title="Evolución TFG (CKD-EPI)", height=230,
            paper_bgcolor="white", plot_bgcolor="#f8fafc",
            font=dict(family="Inter"), margin=dict(l=30,r=20,t=40,b=30))
        fig.update_xaxes(showgrid=True, gridcolor="#e2e8f0")
        fig.update_yaxes(showgrid=True, gridcolor="#e2e8f0")
        st.plotly_chart(fig, use_container_width=True)

    tbl = seg[["fecha","tfg","crea","urea","hb","k","na","asistio"]].copy()
    tbl.insert(2, "estadio", tbl["tfg"].apply(estadio_desde_tfg))
    tbl.columns = ["Fecha","TFG","Estadio","Crea","Urea","Hb","K","Na","Asistencia"]
    st.dataframe(tbl.sort_values("Fecha", ascending=False), use_container_width=True, hide_index=True)


@st.dialog("Evaluación Clínica")
def dialog_evaluar_atencion():
    p = st.session_state.get("eval_paciente")
    if not p:
        st.error("No hay paciente seleccionado.")
        return

    st.markdown(
        f'<div class="info-box"><p class="info-box-label">Paciente Seleccionado</p>'
        f'<p class="info-box-value">{p["nombre"]}</p>'
        f'<p class="info-box-sub">DNI: {p["dni"]} | {p["dx"]} | {p["cap"]}</p></div>',
        unsafe_allow_html=True,
    )

    datos = _form_evaluacion("atencion_eval", p)

    bc1, bc2 = st.columns(2)
    with bc1:
        if st.button("✅ Finalizar Atención", type="primary", use_container_width=True):
            if not datos["sexo"]:
                st.error("Selecciona el sexo.")
            else:
                tfg_val = calcular_tfg(datos["crea"], p.get("edad") or 50, datos["sexo"]) or 0
                est = estadio_desde_tfg(tfg_val)
                ok, msg = registrar_evaluacion(
                    p["dni"], datos["fecha"], datos["crea"], datos["urea"],
                    datos["hb"], datos["k"], datos["na"], datos["acr"],
                    tfg_val, est, datos["asistencia"], datos["notas"]
                )
                if ok:
                    idx = next((i for i, x in enumerate(st.session_state.atencion_lista) if x["dni"] == p["dni"]), None)
                    if idx is not None:
                        st.session_state.atencion_lista[idx]["estado"] = "atendido"
                    st.session_state.atencion_ok = f"✅ {p['nombre']} atendido. TFG: {tfg_val:.1f} mL/min/1.73m²"
                    st.session_state.eval_paciente = None
                    st.rerun()
                else:
                    st.error(f"Error: {msg}")
    with bc2:
        if st.button("Cancelar", use_container_width=True):
            st.session_state.eval_paciente = None
            st.rerun()

@st.dialog("Boton Maestro de Administracion")
def dialog_admin():
    st.markdown(
        '<p style="color:#718096;font-size:13px;">Esta accion eliminara <strong>todos los registros de laboratorio</strong> '
        '(tabla seguimiento) de forma permanente. Los datos de pacientes no se veran afectados.</p>',
        unsafe_allow_html=True,
    )
    pwd = st.text_input("Contrasena de administrador", type="password")

    bc1, bc2 = st.columns(2)
    with bc1:
        if st.button("Eliminar laboratorios", type="primary", use_container_width=True):
            if pwd == "SaludRenal2026":
                with get_engine().connect() as conn:
                    conn.execute(text("DELETE FROM seguimiento"))
                    conn.commit()
                conn.close()
                st.success("Todos los registros de laboratorio han sido eliminados.")
                st.rerun()
            else:
                st.error("Contrasena incorrecta.")
    with bc2:
        if st.button("Cancelar", use_container_width=True):
            st.rerun()


# ─────────────────────────────────────────────
# PÁGINA 1 — PANEL PRINCIPAL
# ─────────────────────────────────────────────
def page_panel():
    banner("¡Bienvenido, Equipo ERCA!", "Resumen Integral del Programa de Atención Renal")

    engine = get_engine()
    total     = int(pd.read_sql("SELECT COUNT(*) AS c FROM pacientes", engine)["c"].iloc[0])
    n_criticos= int(pd.read_sql("""
        SELECT COUNT(DISTINCT s.dni_p) AS c FROM seguimiento s
        INNER JOIN (SELECT dni_p, MAX(fecha) AS mf FROM seguimiento WHERE tfg>0 GROUP BY dni_p) lt
        ON s.dni_p=lt.dni_p AND s.fecha=lt.mf WHERE s.tfg < 15
    """, engine)["c"].iloc[0])
    mes       = datetime.now().strftime("%Y-%m")
    n_evals   = int(pd.read_sql(f"SELECT COUNT(*) AS c FROM seguimiento WHERE fecha LIKE '{mes}%'", engine)["c"].iloc[0])
    total_segs= int(pd.read_sql("SELECT COUNT(*) AS c FROM seguimiento", engine)["c"].iloc[0])

    c1, c2, c3 = st.columns(3)
    with c1: stat_card("Pacientes Totales", total, "primary")
    with c2: stat_card("Riesgo Crítico (TFG < 15)", n_criticos, "danger")
    with c3: stat_card("Evaluaciones Este Mes", n_evals, "success")

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    st.markdown('<div class="card"><h3>Acciones Rápidas</h3>', unsafe_allow_html=True)
    bc1, bc2, bc3 = st.columns(3)
    with bc1:
        if st.button("Registrar Paciente", use_container_width=True, type="primary"):
            dialog_registrar_paciente()
    with bc2:
        if st.button("Ver Alertas",        use_container_width=True):
            dialog_alertas()
    with bc3:
        if st.button("Ver Historial",      use_container_width=True):
            dialog_historial()
    st.markdown("</div>", unsafe_allow_html=True)

    # Botón maestro administración
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
    col_adm, _ = st.columns([1, 3])
    with col_adm:
        if st.button("Boton Maestro de Administracion", use_container_width=True):
            dialog_admin()
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    # Últimas evaluaciones
    st.markdown('<div class="card"><h3>Últimas Evaluaciones</h3>', unsafe_allow_html=True)
    recientes = pd.read_sql("""
        SELECT s.fecha AS Fecha, p.paciente AS Nombre, p.dni AS DNI,
               s.tfg AS TFG, s.asistio AS Asistencia
        FROM seguimiento s JOIN pacientes p ON s.dni_p=p.dni
        ORDER BY s.fecha DESC LIMIT 10
    """, get_engine())
    if recientes.empty:
        st.markdown('<p style="color:#718096;font-size:13.5px;">No hay evaluaciones registradas aún.</p>', unsafe_allow_html=True)
    else:
        recientes.insert(4, "Estadio", recientes["TFG"].apply(estadio_desde_tfg))
        st.dataframe(recientes, use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# PÁGINA 2 — REGISTRO DE PACIENTES
# ─────────────────────────────────────────────
def page_registro():
    banner("Registro de Nuevos Pacientes", "Completa los datos demográficos y clínicos del paciente")

    if st.session_state.get("reg_ok"):
        st.markdown(f'<div class="msg-success">✅ {st.session_state.reg_ok}</div>', unsafe_allow_html=True)
        del st.session_state["reg_ok"]
    if st.session_state.get("reg_err"):
        st.markdown(f'<div class="msg-error">❌ {st.session_state.reg_err}</div>', unsafe_allow_html=True)
        del st.session_state["reg_err"]

    st.markdown('<div class="card"><h3>Datos del Paciente</h3>', unsafe_allow_html=True)
    with st.form("form_registro", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            dni    = st.text_input("DNI (8 dígitos)", placeholder="Ej: 12345678", max_chars=8)
            nombre = st.text_input("Nombre Completo",  placeholder="Ej: Juan Pérez García")
        with c2:
            edad = st.number_input("Edad", min_value=18, max_value=120, step=1, value=None, placeholder="Ej: 45")
            cap  = st.text_input("Centro de Atención Primaria (CAP)", placeholder="Ej: CAP San Isidro")
        estadio = st.selectbox("Estadio ERCA", ["","G1 - Normal (TFG ≥90)","G2 - Leve (TFG 60-89)","G3a - Moderada (TFG 45-59)","G3b - Severa (TFG 30-44)","G4 - Muy Severa (TFG 15-29)","G5 - Falla Renal (TFG <15)"])

        col_s, _ = st.columns([1, 2])
        with col_s:
            submitted = st.form_submit_button("✅ Guardar Paciente", type="primary", use_container_width=True)

        if submitted:
            if not dni or len(dni) != 8 or not dni.isdigit(): st.session_state["reg_err"] = "DNI debe tener 8 dígitos."
            elif not nombre.strip():    st.session_state["reg_err"] = "Nombre obligatorio."
            elif edad is None:          st.session_state["reg_err"] = "Edad obligatoria."
            elif not cap:               st.session_state["reg_err"] = "Selecciona un CAP."
            elif not estadio:           st.session_state["reg_err"] = "Selecciona estadio ERCA."
            else:
                ok, msg = registrar_paciente(dni, nombre.strip(), int(edad), estadio.split(" - ")[0], cap)
                if ok: st.session_state["reg_ok"] = f"Paciente {nombre.strip()} (DNI: {dni}) registrado."
                else:  st.session_state["reg_err"] = msg
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="card"><h3>Pacientes Registrados</h3>', unsafe_allow_html=True)
    df = get_pacientes()
    if df.empty:
        st.markdown('<p style="color:#718096;font-size:13.5px;">No hay pacientes registrados aún.</p>', unsafe_allow_html=True)
    else:
        cols_disp = ["dni","paciente","edad","dx","cap"]
        if "fecha_registro" in df.columns:
            cols_disp.append("fecha_registro")
        df_show = df[cols_disp].copy()
        nombres = ["DNI","Nombre","Edad","Estadio","CAP"]
        if "fecha_registro" in df.columns:
            nombres.append("Fecha Registro")
        df_show.columns = nombres
        st.dataframe(df_show, use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# PÁGINA 3 — ATENCIÓN DEL DÍA
# ─────────────────────────────────────────────
def page_atencion():
    banner("Atención del Día", "Gestiona las atenciones de pacientes programados")

    if "atencion_lista" not in st.session_state:
        st.session_state.atencion_lista = []
    if "eval_paciente" not in st.session_state:
        st.session_state.eval_paciente = None

    pacientes_df = get_pacientes()

    # Abrir dialog de evaluación si hay paciente pendiente
    if st.session_state.eval_paciente:
        dialog_evaluar_atencion()

    col_izq, col_der = st.columns(2)

    # ── Panel izquierdo: lista de pacientes ──
    with col_izq:
        st.markdown('<div class="card"><h3>Agregar Pacientes al Día</h3>', unsafe_allow_html=True)
        if pacientes_df.empty:
            st.warning("No hay pacientes registrados.")
        else:
            busqueda = st.text_input("🔍 Filtrar por DNI o Nombre…", key="search_atencion", placeholder="Deja vacío para ver todos")
            if busqueda:
                mask = (pacientes_df["dni"].str.contains(busqueda, case=False, na=False)
                        | pacientes_df["paciente"].str.contains(busqueda, case=False, na=False))
                filtrados = pacientes_df[mask]
            else:
                filtrados = pacientes_df

            if filtrados.empty:
                st.info("Sin resultados para esa búsqueda.")
            else:
                # Deduplicar por DNI por si hay registros repetidos en la BD
                filtrados = filtrados.drop_duplicates(subset=["dni"])
                lista_container = st.container(height=340)
                with lista_container:
                    for i, (_, row) in enumerate(filtrados.iterrows()):
                        ya = any(p["dni"] == row["dni"] for p in st.session_state.atencion_lista)
                        r1, r2 = st.columns([5, 1])
                        with r1:
                            st.markdown(
                                f'<div class="pac-item">'
                                f'<div><p class="pac-item-name">{row["paciente"]}</p>'
                                f'<p class="pac-item-info">DNI: {row["dni"]} | {row["dx"]} | {row["cap"]}</p></div>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )
                        with r2:
                            if ya:
                                st.markdown('<p style="font-size:11px;color:#00b894;padding-top:10px;text-align:center;">✓</p>', unsafe_allow_html=True)
                            else:
                                if st.button("＋", key=f"add_{row['dni']}_{i}", use_container_width=True):
                                    st.session_state.atencion_lista.append({
                                        "dni": row["dni"], "nombre": row["paciente"],
                                        "edad": row["edad"], "dx": row["dx"],
                                        "cap": row["cap"], "estado": "pendiente",
                                    })
                                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Panel derecho: fecha y contadores ──
    with col_der:
        st.markdown('<div class="card"><h3>Fecha de Atención</h3>', unsafe_allow_html=True)
        fecha_dia = st.date_input("Seleccionar Fecha", value=date.today(), key="fecha_atencion")

        n_total = len(st.session_state.atencion_lista)
        n_atend = sum(1 for p in st.session_state.atencion_lista if p["estado"] == "atendido")
        n_aus   = sum(1 for p in st.session_state.atencion_lista if p["estado"] == "ausente")
        n_pend  = sum(1 for p in st.session_state.atencion_lista if p["estado"] == "pendiente")

        st.markdown(f'<div class="count-box"><p class="count-value">{n_total}</p><p class="count-label">pacientes en agenda</p></div>', unsafe_allow_html=True)

        if n_total > 0:
            st.markdown(
                f'<div style="display:flex;gap:8px;margin-top:10px;">'
                f'<div style="flex:1;background:#d4edda;border-radius:11px;padding:9px;text-align:center;"><div style="font-size:19px;font-weight:700;color:#155724;">{n_atend}</div><div style="font-size:10.5px;color:#155724;">Atendidos</div></div>'
                f'<div style="flex:1;background:#f8d7da;border-radius:11px;padding:9px;text-align:center;"><div style="font-size:19px;font-weight:700;color:#721c24;">{n_aus}</div><div style="font-size:10.5px;color:#721c24;">Ausentes</div></div>'
                f'<div style="flex:1;background:#fff3cd;border-radius:11px;padding:9px;text-align:center;"><div style="font-size:19px;font-weight:700;color:#856404;">{n_pend}</div><div style="font-size:10.5px;color:#856404;">Pendientes</div></div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

    # Mensaje de éxito post-evaluación
    if st.session_state.get("atencion_ok"):
        st.markdown(f'<div class="msg-success">{st.session_state["atencion_ok"]}</div>', unsafe_allow_html=True)
        del st.session_state["atencion_ok"]

    # ── Lista de pendientes ──
    pendientes = [p for p in st.session_state.atencion_lista if p["estado"] == "pendiente"]
    if pendientes:
        st.markdown('<div class="card"><h3>Pacientes Pendientes de Atención</h3>', unsafe_allow_html=True)
        for p in pendientes:
            c1, c2, c3, c4 = st.columns([4, 2, 2, 1])
            with c1:
                pac_card(p["nombre"], f'DNI: {p["dni"]} | {p["dx"]} | {p["cap"]}')
            with c2:
                if st.button("✅ Atender", key=f"atender_{p['dni']}", use_container_width=True, type="primary"):
                    st.session_state.eval_paciente = p
                    st.rerun()
            with c3:
                if st.button("❌ Ausente", key=f"ausente_{p['dni']}", use_container_width=True):
                    idx = next(i for i, x in enumerate(st.session_state.atencion_lista) if x["dni"] == p["dni"])
                    st.session_state.atencion_lista[idx]["estado"] = "ausente"
                    registrar_evaluacion(p["dni"], fecha_dia, 0, 0, 0, 0, 0, 0, 0, p["dx"], "Inasistencia", "Ausente")
                    st.rerun()
            with c4:
                if st.button("🗑", key=f"del_{p['dni']}", use_container_width=True):
                    st.session_state.atencion_lista = [x for x in st.session_state.atencion_lista if x["dni"] != p["dni"]]
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Atendidos ──
    atendidos = [p for p in st.session_state.atencion_lista if p["estado"] == "atendido"]
    if atendidos:
        st.markdown('<div class="card"><h3>Pacientes Atendidos ✅</h3>', unsafe_allow_html=True)
        for p in atendidos:
            pac_card(f'✅ {p["nombre"]}', f'DNI: {p["dni"]} | {p["dx"]} | Atendido', "attended")
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Ausentes ──
    ausentes = [p for p in st.session_state.atencion_lista if p["estado"] == "ausente"]
    if ausentes:
        st.markdown('<div class="card"><h3>Pacientes Ausentes ❌</h3>', unsafe_allow_html=True)
        for p in ausentes:
            pac_card(f'❌ {p["nombre"]}', f'DNI: {p["dni"]} | Inasistencia', "absent")
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Botones finalizar ──
    if st.session_state.atencion_lista:
        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
        bf1, bf2 = st.columns(2)
        with bf1:
            if st.button("🔄 Limpiar Día", use_container_width=True):
                st.session_state.atencion_lista = []
                st.session_state.eval_paciente  = None
                st.rerun()
        with bf2:
            if st.button("✅ Finalizar Atención del Día", use_container_width=True, type="primary"):
                if not FPDF_OK:
                    st.error("fpdf2 no está instalado. Ejecuta: pip install fpdf2")
                else:
                    pdf_bytes = generar_pdf(st.session_state.atencion_lista, fecha_dia)
                    n_a = sum(1 for p in st.session_state.atencion_lista if p["estado"] == "atendido")
                    n_t = len(st.session_state.atencion_lista)
                    st.success(f"🎉 Jornada finalizada — {n_a}/{n_t} pacientes atendidos. Descarga el reporte:")
                    st.download_button(
                        label="📄 Descargar Reporte PDF",
                        data=pdf_bytes,
                        file_name=f"ERCA_atencion_{fecha_dia}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                    )
    else:
        st.markdown(
            '<div class="card" style="text-align:center;padding:32px 20px;">'
            '<p style="color:#718096;font-size:13.5px;">🔍 Busca y agrega pacientes en el panel izquierdo para comenzar.</p>'
            '</div>',
            unsafe_allow_html=True,
        )

# ─────────────────────────────────────────────
# PÁGINA 4 — ALERTAS
# ─────────────────────────────────────────────
def page_alertas():
    banner("🚨 Alertas de Riesgo", "Pacientes que requieren intervención inmediata")

    alertas_df = pd.read_sql("""
        SELECT p.paciente, p.dni, p.dx, p.cap, p.edad, s.tfg, s.fecha, s.crea
        FROM pacientes p
        JOIN seguimiento s ON s.dni_p = p.dni
        INNER JOIN (
            SELECT dni_p, MAX(fecha) AS mf FROM seguimiento WHERE tfg > 0 GROUP BY dni_p
        ) lt ON s.dni_p = lt.dni_p AND s.fecha = lt.mf
        WHERE s.tfg < 30 AND s.tfg > 0
        ORDER BY s.tfg ASC
    """, get_engine())

    if alertas_df.empty:
        st.markdown(
            '<div class="card" style="text-align:center;padding:48px 20px;">'
            '<div style="font-size:48px;margin-bottom:14px;">✅</div>'
            '<h3 style="color:#00b894;margin-bottom:6px;">Sin Alertas Críticas</h3>'
            '<p style="color:#718096;font-size:13.5px;">No hay pacientes con TFG &lt; 30.</p></div>',
            unsafe_allow_html=True,
        )
        return

    alertas_df["estadio"] = alertas_df["tfg"].apply(estadio_desde_tfg)
    criticos    = alertas_df[alertas_df["tfg"] < 15]
    alto_riesgo = alertas_df[(alertas_df["tfg"] >= 15) & (alertas_df["tfg"] < 30)]

    c1, c2, c3 = st.columns(3)
    with c1: stat_card("Total en Riesgo",       len(alertas_df), "danger")
    with c2: stat_card("Estadio G5 (TFG < 15)", len(criticos),   "danger")
    with c3: stat_card("Estadio G4 (TFG 15-29)",len(alto_riesgo),"warning")

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    if not criticos.empty:
        st.markdown('<div class="card"><h3>Estadio G5 — Falla Renal (TFG &lt; 15)</h3>', unsafe_allow_html=True)
        for _, r in criticos.iterrows():
            alert_card(r["paciente"], r["dni"], r["tfg"], r["dx"], r["cap"], r["fecha"])
        st.markdown("</div>", unsafe_allow_html=True)

    if not alto_riesgo.empty:
        st.markdown('<div class="card"><h3>Estadio G4 — Muy Severo (TFG 15–29)</h3>', unsafe_allow_html=True)
        for _, r in alto_riesgo.iterrows():
            alert_card(r["paciente"], r["dni"], r["tfg"], r["dx"], r["cap"], r["fecha"])
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="card"><h3>Tabla Completa</h3>', unsafe_allow_html=True)
    tbl = alertas_df[["paciente","dni","tfg","estadio","dx","cap","fecha"]].copy()
    tbl.columns = ["Nombre","DNI","TFG","Estadio","Diagnóstico","CAP","Fecha"]
    st.dataframe(tbl, use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# PÁGINA 5 — HISTORIAL CLÍNICO
# ─────────────────────────────────────────────
def _plot_line(df, col, title, unit, color):
    valid = df[df[col] > 0].copy()
    if valid.empty: return None
    r, g, b = int(color[1:3],16), int(color[3:5],16), int(color[5:7],16)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=valid["fecha"], y=valid[col], mode="lines+markers",
        line=dict(color=color, width=3), marker=dict(size=8),
        fill="tozeroy", fillcolor=f"rgba({r},{g},{b},0.07)"))
    fig.update_layout(
        title=dict(text=f"{title} ({unit})", font=dict(family="Poppins", size=14, color="#2d3748")),
        xaxis_title="Fecha", yaxis_title=unit, height=240,
        paper_bgcolor="white", plot_bgcolor="#f8fafc",
        font=dict(family="Inter", size=11),
        margin=dict(l=36,r=16,t=44,b=32), showlegend=False,
    )
    fig.update_xaxes(showgrid=True, gridcolor="#e2e8f0")
    fig.update_yaxes(showgrid=True, gridcolor="#e2e8f0")
    return fig


def page_historial():
    banner("📊 Historial Clínico", "Consulta el histórico completo de pacientes")

    pacientes_df = get_pacientes()
    st.markdown('<div class="card"><h3>Buscar Paciente</h3>', unsafe_allow_html=True)

    if pacientes_df.empty:
        st.markdown('<p style="color:#718096;font-size:13.5px;">No hay pacientes.</p>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        return

    busqueda = st.text_input("🔍 Filtrar por DNI o Nombre…", key="search_historial",
                             placeholder="Deja vacío para ver todos")

    if busqueda:
        mask = (pacientes_df["dni"].str.contains(busqueda, case=False, na=False)
                | pacientes_df["paciente"].str.contains(busqueda, case=False, na=False))
        filtrados_h = pacientes_df[mask].drop_duplicates(subset=["dni"])
    else:
        filtrados_h = pacientes_df.drop_duplicates(subset=["dni"])

    if filtrados_h.empty:
        st.info("Sin resultados.")
    else:
        lista_h = st.container(height=300)
        with lista_h:
            for i, (_, row) in enumerate(filtrados_h.iterrows()):
                r1, r2 = st.columns([5, 1])
                with r1:
                    st.markdown(
                        f'<div class="pac-item"><div>'
                        f'<p class="pac-item-name">{row["paciente"]}</p>'
                        f'<p class="pac-item-info">DNI: {row["dni"]} | {row["dx"]} | {row["cap"]}</p>'
                        f'</div></div>',
                        unsafe_allow_html=True,
                    )
                with r2:
                    if st.button("Ver", key=f"hist_{row['dni']}_{i}", use_container_width=True):
                        st.session_state["historial_pac"] = row["dni"]
                        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    pac_sel = st.session_state.get("historial_pac")

    if not pac_sel: return

    pac = pacientes_df[pacientes_df["dni"] == pac_sel].iloc[0]
    st.markdown(
        f'<div class="info-box"><p class="info-box-label">Paciente</p>'
        f'<p class="info-box-value">{pac["paciente"]}</p>'
        f'<p class="info-box-sub">DNI: {pac["dni"]} | {pac["edad"]} años | {pac["dx"]} | {pac["cap"]}</p></div>',
        unsafe_allow_html=True,
    )

    seg = get_seguimiento(pac_sel).sort_values("fecha")
    if seg.empty:
        st.markdown('<div class="card" style="text-align:center;padding:28px;"><p style="color:#718096;">Sin evaluaciones registradas.</p></div>', unsafe_allow_html=True)
        return

    tab_lab, tab_adh = st.tabs(["📈 Evolución de Laboratorio", "📊 Adherencia"])

    with tab_lab:
        params = [("tfg","TFG (CKD-EPI)","mL/min/1.73m²","#3a0ca3"),
                  ("crea","Creatinina","mg/dL","#e17055"),
                  ("urea","Urea","mg/dL","#fdcb6e"),
                  ("hb","Hemoglobina","g/dL","#00b894")]
        gc1, gc2 = st.columns(2)
        for i, (c, t, u, col) in enumerate(params):
            fig = _plot_line(seg, c, t, u, col)
            if fig:
                with (gc1 if i % 2 == 0 else gc2):
                    st.plotly_chart(fig, use_container_width=True, key=f"ch_{c}_{pac_sel}")

        electro = seg[(seg["k"] > 0) | (seg["na"] > 0)]
        if not electro.empty:
            fig_e = go.Figure()
            if electro["k"].sum() > 0:
                fig_e.add_trace(go.Scatter(x=electro["fecha"], y=electro["k"], mode="lines+markers", name="Potasio (mEq/L)", line=dict(color="#e17055",width=2), marker=dict(size=7)))
            if electro["na"].sum() > 0:
                fig_e.add_trace(go.Scatter(x=electro["fecha"], y=electro["na"], mode="lines+markers", name="Sodio (mEq/L)", line=dict(color="#3f37c9",width=2), marker=dict(size=7)))
            fig_e.update_layout(title=dict(text="Electrolitos (K⁺ y Na⁺)", font=dict(family="Poppins",size=14,color="#2d3748")),
                height=240, paper_bgcolor="white", plot_bgcolor="#f8fafc",
                font=dict(family="Inter",size=11), margin=dict(l=36,r=16,t=44,b=32),
                legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1))
            fig_e.update_xaxes(showgrid=True, gridcolor="#e2e8f0")
            fig_e.update_yaxes(showgrid=True, gridcolor="#e2e8f0")
            st.plotly_chart(fig_e, use_container_width=True, key=f"ch_electro_{pac_sel}")

        st.markdown('<div class="card"><h3>Tabla de Registros</h3>', unsafe_allow_html=True)
        cols_b = ["fecha","tfg","crea","urea","hb","k","na","acr","asistio","notas"]
        tbl = seg[cols_b].copy()
        tbl.insert(2, "estadio", tbl["tfg"].apply(estadio_desde_tfg))
        tbl.columns = ["Fecha","TFG","Estadio","Crea","Urea","Hb","K","Na","ACR","Asistencia","Notas"]
        st.dataframe(tbl.sort_values("Fecha", ascending=False), use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with tab_adh:
        asist = seg["asistio"].value_counts()
        n_p = int(asist.get("Puntual", 0))
        n_t = int(asist.get("Tardía",  0))
        n_a = int(asist.get("Inasistencia", 0))
        n_tot = len(seg)
        pct = round(n_p / n_tot * 100) if n_tot > 0 else 0

        a1, a2 = st.columns(2)
        with a1:
            stat_card("Total Citas", n_tot, "primary")
            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
            st.markdown(
                f'<div class="card"><div style="display:flex;flex-direction:column;gap:9px;">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;background:#d4edda;border-radius:11px;padding:11px 14px;"><span style="font-weight:600;color:#155724;">✅ Puntual</span><span style="font-weight:700;color:#155724;font-size:20px;">{n_p}</span></div>'
                f'<div style="display:flex;justify-content:space-between;align-items:center;background:#fff3cd;border-radius:11px;padding:11px 14px;"><span style="font-weight:600;color:#856404;">⏰ Tardía</span><span style="font-weight:700;color:#856404;font-size:20px;">{n_t}</span></div>'
                f'<div style="display:flex;justify-content:space-between;align-items:center;background:#f8d7da;border-radius:11px;padding:11px 14px;"><span style="font-weight:600;color:#721c24;">❌ Inasistencia</span><span style="font-weight:700;color:#721c24;font-size:20px;">{n_a}</span></div>'
                f'</div><p style="font-size:12px;color:#718096;margin-top:10px;margin-bottom:0;">Tasa puntualidad: <strong style="color:#3a0ca3">{pct}%</strong></p></div>',
                unsafe_allow_html=True,
            )
        with a2:
            if n_tot > 0:
                fig_pie = go.Figure(data=[go.Pie(
                    labels=["Puntual","Tardía","Inasistencia"], values=[n_p,n_t,n_a],
                    hole=0.42, marker_colors=["#00b894","#fdcb6e","#d63031"])])
                fig_pie.update_layout(title=dict(text="Distribución de Asistencia", font=dict(family="Poppins",size=14)),
                    paper_bgcolor="white", font=dict(family="Inter",size=11),
                    margin=dict(l=16,r=16,t=44,b=16), height=290,
                    legend=dict(orientation="h",yanchor="bottom",y=-0.22))
                st.plotly_chart(fig_pie, use_container_width=True, key=f"pie_{pac_sel}")

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
PAGES = [
    ("panel",    "PANEL PRINCIPAL"),
    ("registro", "REGISTRO DE PACIENTES"),
    ("atencion", "ATENCION DEL DIA"),
    ("alertas",  "ALERTAS DE RIESGO"),
    ("historial","HISTORIAL CLINICO"),
]


def main():
    inject_css()
    init_db()

    if "page" not in st.session_state:           st.session_state.page = "panel"
    if "atencion_lista" not in st.session_state: st.session_state.atencion_lista = []
    if "eval_paciente"  not in st.session_state: st.session_state.eval_paciente  = None

    with st.sidebar:
        st.markdown('<div class="sidebar-title">🩸 ERCA</div>', unsafe_allow_html=True)
        for key, label in PAGES:
            t = "primary" if st.session_state.page == key else "secondary"
            if st.button(label, key=f"nav_{key}", use_container_width=True, type=t):
                st.session_state.page = key
                st.session_state.eval_paciente = None
                st.rerun()
        st.markdown(
            f'<hr style="border-color:rgba(255,255,255,0.1);margin-top:20px;">'
            f'<p style="color:rgba(255,255,255,0.32);font-size:10.5px;text-align:center;margin-top:8px;">'
            f'SISTEMA ERCA v2.1<br>{datetime.now().strftime("%d/%m/%Y")}</p>',
            unsafe_allow_html=True,
        )

    dispatch = {
        "panel": page_panel, "registro": page_registro,
        "atencion": page_atencion, "alertas": page_alertas, "historial": page_historial,
    }
    dispatch.get(st.session_state.page, page_panel)()


if __name__ == "__main__":
    main()
