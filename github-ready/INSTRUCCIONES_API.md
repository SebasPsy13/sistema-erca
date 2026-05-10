# 🚀 GUÍA - Conectar HTML a FastAPI

## Paso 1: Instalar dependencias

```bash
pip install -r requirements.txt
```

## Paso 2: Ejecutar el Backend Localmente

```bash
python main.py
```

Verás:
```
╔════════════════════════════════════════╗
║   SISTEMA ERCA - Backend FastAPI      ║
║   Ejecutando en http://localhost:8000 ║
╚════════════════════════════════════════╝

Documentación API: http://localhost:8000/docs
Base de datos: sistema_erca.db
```

## Paso 3: Probar la API

### Opción A - Directamente en navegador:
- Abre http://localhost:8000
- Verás el HTML cargado perfectamente
- Haz clic en "Panel Principal" para verificar que el diseño es idéntico

### Opción B - Con Swagger UI (documentación):
- Ve a http://localhost:8000/docs
- Aquí ves todas las rutas API disponibles

## Paso 4: Modificar el JavaScript (IMPORTANTE)

El HTML actualmente usa **localStorage**. Necesitas reemplazarlo con llamadas a **API**:

### En el `<script>` del index.html, reemplaza estas funciones:

#### CREAR PACIENTE
**ANTES:**
```javascript
function guardarPaciente() {
    const pacientes = JSON.parse(localStorage.getItem('pacientes')) || [];
    pacientes.push({dni, nombre, edad, dx, cap});
    localStorage.setItem('pacientes', JSON.stringify(pacientes));
}
```

**DESPUÉS:**
```javascript
async function guardarPaciente() {
    const response = await fetch('/api/pacientes', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({dni, nombre, edad, dx, cap})
    });
    if (response.ok) {
        alert('Paciente creado exitosamente');
    }
}
```

#### CARGAR PACIENTES
**ANTES:**
```javascript
function cargarPacientes() {
    return JSON.parse(localStorage.getItem('pacientes')) || [];
}
```

**DESPUÉS:**
```javascript
async function cargarPacientes() {
    const response = await fetch('/api/pacientes');
    return await response.json();
}
```

#### GUARDAR EVALUACIÓN
**ANTES:**
```javascript
function guardarEvaluacion(dni, evaluacion) {
    const evaluaciones = JSON.parse(localStorage.getItem('evaluaciones')) || [];
    evaluaciones.push({dni_p: dni, ...evaluacion});
    localStorage.setItem('evaluaciones', JSON.stringify(evaluaciones));
}
```

**DESPUÉS:**
```javascript
async function guardarEvaluacion(dni, evaluacion) {
    const response = await fetch('/api/evaluaciones', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            dni_p: dni,
            fecha: evaluacion.fecha,
            crea: evaluacion.crea,
            urea: evaluacion.urea,
            hb: evaluacion.hb,
            k: evaluacion.k,
            na: evaluacion.na,
            acr: evaluacion.acr,
            tfg: evaluacion.tfg,
            estadio: evaluacion.estadio,
            asistio: evaluacion.asistio,
            notas: evaluacion.notas
        })
    });
    return response.ok;
}
```

#### CARGAR EVALUACIONES
**ANTES:**
```javascript
function cargarEvaluaciones(dni) {
    const evaluaciones = JSON.parse(localStorage.getItem('evaluaciones')) || [];
    return evaluaciones.filter(e => e.dni_p === dni);
}
```

**DESPUÉS:**
```javascript
async function cargarEvaluaciones(dni) {
    const response = await fetch(`/api/evaluaciones/${dni}`);
    return await response.json();
}
```

## ✅ Endpoints Disponibles

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/` | Sirve el HTML |
| GET | `/api/pacientes` | Obtener todos los pacientes |
| GET | `/api/pacientes/{dni}` | Obtener paciente por DNI |
| POST | `/api/pacientes` | Crear nuevo paciente |
| PUT | `/api/pacientes/{dni}` | Actualizar paciente |
| GET | `/api/evaluaciones/{dni_p}` | Obtener evaluaciones de paciente |
| POST | `/api/evaluaciones` | Registrar evaluación |
| GET | `/api/alertas` | Obtener pacientes en riesgo |
| GET | `/api/estadisticas` | Obtener estadísticas del sistema |
| GET | `/api/citas/{dni_p}` | Obtener citas del paciente |
| POST | `/api/citas` | Crear nueva cita |
| GET | `/api/health` | Verificar estado de la API |

## 🐛 Solucionar Problemas

### Error: "ModuleNotFoundError: fastapi"
```bash
pip install fastapi uvicorn
```

### Error: "Address already in use"
```bash
# El puerto 8000 está ocupado. Cambiar puerto:
python main.py --port 8001
```

### El HTML no carga
1. Verifica que `index.html` esté en la misma carpeta que `main.py`
2. Abre http://localhost:8000 (no 8001)
3. Verifica en la consola si hay errores

### Las APIs no responden
1. Abre http://localhost:8000/docs
2. Prueba hacer un GET a `/api/pacientes`
3. Si no funciona, verifica que el backend esté corriendo
