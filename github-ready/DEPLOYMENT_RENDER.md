# 🚀 DEPLOYMENT GRATIS en Render

## ¿Por qué Render?

✅ **Completamente gratis** (sin tarjeta de crédito)  
✅ **Incluye base de datos** SQLite  
✅ **SSL automático** (HTTPS)  
✅ **Deploy automático** desde GitHub  
✅ **URL pública** permanente  
✅ **0 configuración** necesaria

---

## 📋 Pasos de Deployment (10 minutos)

### **PASO 1: Subir a GitHub**

```bash
cd /Users/sebastianqa/Desktop/Apps/PROGRAMA\ ERCA/SISTEMA_ERCA

# Inicializar repositorio
git init
git add .
git commit -m "SISTEMA ERCA - Backend FastAPI + HTML"
git branch -M main
```

Luego sube a GitHub:
```bash
git remote add origin https://github.com/tuusuario/sistema-erca.git
git push -u origin main
```

**Si no tienes GitHub:**
1. Ve a https://github.com/signup
2. Crea cuenta (2 minutos)
3. Crea repositorio público "sistema-erca"
4. Ejecuta los comandos anteriores

---

### **PASO 2: Crear cuenta en Render**

1. Ve a https://render.com
2. Haz clic en **"Sign up"**
3. Conecta tu cuenta GitHub
4. Autoriza a Render para acceder a tus repositorios

---

### **PASO 3: Crear Web Service**

1. Dashboard de Render → **"New +"** → **"Web Service"**
2. Selecciona tu repositorio **"sistema-erca"**
3. Completa los campos:

| Campo | Valor |
|-------|-------|
| **Name** | `sistema-erca` |
| **Environment** | `Python 3` |
| **Region** | `Ohio` (más cercano a Latam) |
| **Branch** | `main` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn main:app --host 0.0.0.0 --port 8000` |

4. Haz clic en **"Create Web Service"**

**¡Listo!** El deploy comienza automáticamente.

---

### **PASO 4: Esperar 2-3 minutos**

Render construye la aplicación:
```
Building application...
Installing dependencies...
Deploying...
✅ Live!
```

Verás una URL como: `https://sistema-erca.onrender.com`

---

## ✅ Verificar que funciona

1. Abre tu URL: `https://sistema-erca.onrender.com`
2. Deberías ver el **HTML exactamente igual**
3. Prueba crear un paciente:
   - Click en "Registro de Pacientes"
   - Completa el formulario
   - Click en "Guardar"
4. Verifica que se guardó en "Panel Principal"

---

## 🔗 Endpoints en Producción

Tu aplicación estará en:
```
Frontend: https://sistema-erca.onrender.com
API Docs: https://sistema-erca.onrender.com/docs
API Health: https://sistema-erca.onrender.com/api/health
```

---

## ⚙️ Configuración Avanzada (Opcional)

### Agregar variables de entorno
1. En Render Dashboard → Selecciona tu servicio
2. **Settings** → **Environment**
3. Agregar nuevas variables (ej: `DEBUG=false`)

### Cambiar dominio personalizado
1. **Settings** → **Custom Domain**
2. Apunta tu dominio con CNAME a `onrender.com`

### Ver logs en vivo
1. **Logs** en el Dashboard
2. Verás todos los errores y requests en tiempo real

---

## 🆓 Plan Gratuito de Render

| Característica | Plan Gratis |
|---|---|
| Web Service | ✅ 1 incluido |
| Memoria RAM | ✅ 512 MB |
| CPU | ✅ Compartida |
| Almacenamiento BD | ✅ 1 GB SQLite |
| Uptime | ✅ ~99% |
| Custom Domain | ✅ Incluido |
| SSL/HTTPS | ✅ Automático |
| **Costo** | **$0/mes** |

---

## 🔄 Deploy Automático desde GitHub

Cada vez que hagas un `git push` a `main`:

```bash
git add .
git commit -m "Nuevas features"
git push origin main
```

Render **automáticamente**:
1. Detecta los cambios
2. Construye la aplicación
3. Deploya la versión nueva
4. Sin downtime

---

## 🚨 Solucionar Problemas en Render

### Aplicación no inicia
**Solución:** Ve a Logs y revisa el error
```
Error: No module named 'fastapi'
→ Verifica que requirements.txt esté en el root
```

### Errores de conexión BD
**Solución:** La BD se crea automáticamente en Render
```
Sistema crea sistema_erca.db la primera vez que inicia
```

### Aplicación es lenta
**Solución:** Plan gratuito tiene recursos compartidos
```
Para mejorar: Paga $7/mes → Plan Starter
```

---

## 📱 Próximas Mejoras (Opcional)

Después de que esté en producción, puedes:

1. **Agregar autenticación** (login de usuarios)
2. **Migrar a PostgreSQL** (BD mejor que SQLite)
3. **Agregar más validaciones** en el backend
4. **Crear panel de admin**
5. **Agregar backups automáticos**

---

## 📞 Soporte

- **Docs Render:** https://render.com/docs
- **Status Page:** https://render-status.com
- **Email:** support@render.com

---

**¡Tu aplicación está en línea! 🎉**

Comparte el URL: `https://sistema-erca.onrender.com`

A partir de ahora, el backend está corriendo 24/7 gratis en la nube.
