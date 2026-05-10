#!/bin/bash

# Script para copiar archivos a github-ready

echo "🔄 Copiando archivos..."

# Ir a la carpeta SISTEMA_ERCA
cd "$(dirname "$0")/.."

# Copiar archivos
cp main.py github-ready/ && echo "✅ main.py"
cp index.html github-ready/ && echo "✅ index.html"
cp INICIO_RAPIDO.md github-ready/ && echo "✅ INICIO_RAPIDO.md"
cp INSTRUCCIONES_API.md github-ready/ && echo "✅ INSTRUCCIONES_API.md"
cp DEPLOYMENT_RENDER.md github-ready/ && echo "✅ DEPLOYMENT_RENDER.md"

echo ""
echo "✨ Archivos copiados exitosamente!"
echo ""
echo "📁 Contenido de github-ready:"
ls -lh github-ready/ | tail -n +2 | awk '{print "   " $9 " (" $5 ")"}'
echo ""
echo "🎉 Listo para GitHub!"
