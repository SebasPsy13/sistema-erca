# SISTEMA ERCA - Aplicación Web Moderna

## 📋 Descripción

SISTEMA ERCA es una aplicación web completa para gestionar pacientes con enfermedad renal crónica avanzada. 

**Características:**
- ✅ Interface moderna y responsiva
- ✅ Backend FastAPI con API REST
- ✅ Base de datos SQLite
- ✅ Cálculos clínicos automáticos (TFG CKD-EPI, ACR)
- ✅ Gestión integral de pacientes
- ✅ Panel de alertas de riesgo
- ✅ Historial clínico interactivo

---

## 🚀 Inicio Rápido

### Requisitos
- Python 3.8+
- pip

### Instalación Local (5 minutos)

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Ejecutar el backend
python main.py

# 3. Abrir en navegador
http://localhost:8000
```

Listo! La aplicación está corriendo 🎉

---

## 📁 Estructura

```
.
├── main.py                    # Backend FastAPI
├── index.html                 # Aplicación web (HTML5)
├── requirements.txt           # Dependencias Python
├── .gitignore                 # Configuración Git
├── README.md                  # Este archivo
├── INICIO_RAPIDO.md          # Guía de inicio
├── INSTRUCCIONES_API.md      # Documentación API
└── DEPLOYMENT_RENDER.md      # Cómo deployar
```

---

## 🎯 Funcionalidades

### 5 Páginas Principales

1. **Panel Principal** - Dashboard con estadísticas
2. **Registro de Pacientes** - Agregar nuevos pacientes
3. **Atención del Día** - Gestionar atenciones diarias
4. **Alertas de Riesgo** - Pacientes críticos
5. **Historial Clínico** - Histórico de evaluaciones

### Cálculos Clínicos

- **TFG (Tasa de Filtración Glomerular)** - Fórmula CKD-EPI
- **ERCA Staging** - Clasificación G1-G5
- **ACR** - Índice Albumina/Creatinina

---

## 🔌 API Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/pacientes` | Obtener todos los pacientes |
| POST | `/api/pacientes` | Crear nuevo paciente |
| GET | `/api/pacientes/{dni}` | Obtener paciente |
| GET | `/api/evaluaciones/{dni}` | Obtener evaluaciones |
| POST | `/api/evaluaciones` | Registrar evaluación |
| GET | `/api/alertas` | Obtener pacientes en riesgo |
| GET | `/api/estadisticas` | Estadísticas del sistema |
| GET | `/api/health` | Health check |

---

## 🌍 Deployment Gratuito

Deployar a **Render.com** (completamente gratis):

```bash
# 1. Subir a GitHub (ver pasos abajo)
# 2. Conectar Render con tu repo
# 3. Deploy automático en 2 minutos
```

Ver: `DEPLOYMENT_RENDER.md`

---

## 🛠️ Tecnologías

- **Frontend:** HTML5, CSS3, JavaScript vanilla
- **Backend:** Python + FastAPI
- **Base de datos:** SQLite
- **Deploy:** Render (gratis)

---

## 📞 Documentación

- `INICIO_RAPIDO.md` - Primeros pasos
- `INSTRUCCIONES_API.md` - Cómo usar la API
- `DEPLOYMENT_RENDER.md` - Cómo deployar a producción

---

## 📧 Autor

Email: ingexscience@gmail.com

---

## 📝 Licencia

Proyecto privado - SISTEMA ERCA

**Versión:** 2.0  
**Estado:** Producción ✅  
**Fecha:** 2026-05-10
