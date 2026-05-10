# 📱 GUÍA: SUBIR A GITHUB

## ✅ ARCHIVOS QUE YA ESTÁN EN ESTA CARPETA

```
github-ready/
├── README.md              ✅ (creado)
├── requirements.txt       ✅ (creado)
├── .gitignore            ✅ (creado)
└── GUIA_GITHUB.md        ✅ (este archivo)
```

---

## 📋 ARCHIVOS QUE FALTA COPIAR (4 ARCHIVOS)

Necesitas copiar estos 4 archivos desde la carpeta SISTEMA_ERCA a esta carpeta (github-ready):

### 1️⃣ **main.py**
```
Desde: /Users/sebastianqa/Desktop/Apps/PROGRAMA ERCA/SISTEMA_ERCA/main.py
Hacia: /Users/sebastianqa/Desktop/Apps/PROGRAMA ERCA/SISTEMA_ERCA/github-ready/main.py
```

### 2️⃣ **index.html**
```
Desde: /Users/sebastianqa/Desktop/Apps/PROGRAMA ERCA/SISTEMA_ERCA/index.html
Hacia: /Users/sebastianqa/Desktop/Apps/PROGRAMA ERCA/SISTEMA_ERCA/github-ready/index.html
```

### 3️⃣ **INICIO_RAPIDO.md**
```
Desde: /Users/sebastianqa/Desktop/Apps/PROGRAMA ERCA/SISTEMA_ERCA/INICIO_RAPIDO.md
Hacia: /Users/sebastianqa/Desktop/Apps/PROGRAMA ERCA/SISTEMA_ERCA/github-ready/INICIO_RAPIDO.md
```

### 4️⃣ **INSTRUCCIONES_API.md**
```
Desde: /Users/sebastianqa/Desktop/Apps/PROGRAMA ERCA/SISTEMA_ERCA/INSTRUCCIONES_API.md
Hacia: /Users/sebastianqa/Desktop/Apps/PROGRAMA ERCA/SISTEMA_ERCA/github-ready/INSTRUCCIONES_API.md
```

### ➕ **BONUS - Deployment**
```
Desde: /Users/sebastianqa/Desktop/Apps/PROGRAMA ERCA/SISTEMA_ERCA/DEPLOYMENT_RENDER.md
Hacia: /Users/sebastianqa/Desktop/Apps/PROGRAMA ERCA/SISTEMA_ERCA/github-ready/DEPLOYMENT_RENDER.md
```

---

## 🖥️ CÓMO COPIAR (Elige una opción)

### Opción A: Terminal (Recomendado)

```bash
# Ir a la carpeta
cd "/Users/sebastianqa/Desktop/Apps/PROGRAMA ERCA/SISTEMA_ERCA"

# Copiar archivos
cp main.py github-ready/
cp index.html github-ready/
cp INICIO_RAPIDO.md github-ready/
cp INSTRUCCIONES_API.md github-ready/
cp DEPLOYMENT_RENDER.md github-ready/

# Verificar
ls -la github-ready/
```

Deberías ver 9 archivos.

### Opción B: Finder (Manual)

1. Abre Finder
2. Ve a: `PROGRAMA ERCA` → `SISTEMA_ERCA`
3. Selecciona:
   - main.py
   - index.html
   - INICIO_RAPIDO.md
   - INSTRUCCIONES_API.md
   - DEPLOYMENT_RENDER.md
4. Click derecho → Copiar
5. Entra a carpeta `github-ready`
6. Click derecho → Pegar

---

## ✨ VERIFICACIÓN

Una vez copiados, deberías tener:

```
github-ready/
├── main.py                      ✅
├── index.html                   ✅
├── requirements.txt             ✅
├── .gitignore                   ✅
├── README.md                    ✅
├── GUIA_GITHUB.md              ✅
├── INICIO_RAPIDO.md            ✅
├── INSTRUCCIONES_API.md        ✅
└── DEPLOYMENT_RENDER.md        ✅
```

**9 archivos totales**

---

## 🔗 PRÓXIMO PASO

Una vez que tengas todos los 9 archivos aquí:

```bash
# 1. Ir a la carpeta github-ready
cd "/Users/sebastianqa/Desktop/Apps/PROGRAMA ERCA/SISTEMA_ERCA/github-ready"

# 2. Inicializar Git
git init

# 3. Agregar archivos
git add .

# 4. Primer commit
git commit -m "SISTEMA ERCA v2.0 - Backend FastAPI + HTML Web App"

# 5. CREAR REPOSITORIO EN GITHUB (ver abajo)
```

---

## 📱 CREAR REPOSITORIO EN GITHUB

1. Abre https://github.com/new
2. Nombre: `sistema-erca`
3. Descripción: `Sistema de gestión de pacientes ERCA`
4. **Selecciona: "Public"** (para poder deployar gratis en Render)
5. Click "Create repository"

---

## 🚀 SUBIR A GITHUB (Final)

GitHub te dará un comando. Cópialo exactamente:

```bash
git branch -M main
git remote add origin https://github.com/TU_USUARIO/sistema-erca.git
git push -u origin main
```

(Reemplaza `TU_USUARIO` con tu usuario de GitHub)

---

## ✅ LISTO!

Una vez que hagas el push, tu código está en GitHub y puedes:
- Deployar en Render (ver DEPLOYMENT_RENDER.md)
- Compartir el repositorio
- Colaborar con otros

---

**Próximo paso:** Copiar los 4 archivos faltantes 👇
