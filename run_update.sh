#!/bin/bash
PROYECTO="/home/jorge/El-Industrial"
LOG="$PROYECTO/reports/cron_log.txt"
URL_QA="https://el-industrial.netlify.app"
URL_PROD="https://elindustrial.com.ar"
FECHA=$(date +%Y-%m-%d)

echo "[$(date)] --- INICIO PIPELINE QA -> PROD ---" >> $LOG
cd $PROYECTO

# 1. Validación de Sintaxis
python3 -m py_compile scripts/update_products.py || { $PROYECTO/scripts/notify.sh "🚨 QA FALLÓ: Error de sintaxis."; exit 1; }

# 2. Sincronizar local
git pull origin main >> $LOG 2>&1

# 3. Generar Datos
./venv/bin/python scripts/update_products.py >> $LOG 2>&1 || { $PROYECTO/scripts/notify.sh "🚨 QA FALLÓ: Error en generación de datos."; exit 1; }

# 4. DESPLIEGUE A QA (Tu Repo Personal)
git add .
git commit -m "qa: deploy ${FECHA}" >> $LOG 2>&1
echo "Desplegando a QA..." >> $LOG
git push personal master:main --force >> $LOG 2>&1

# 5. SMOKE TEST EN QA
echo "Esperando despliegue de Netlify (QA)..." >> $LOG
sleep 30 
STATUS_QA=$(curl -o /dev/null -s -w "%{http_code}" "$URL_QA/latest-json-filename.json")

if [ "$STATUS_QA" -eq 200 ]; then
    echo "✅ QA EXITOSO. Procediendo a Producción..." >> $LOG
    
    # 6. DESPLIEGUE A PRODUCCIÓN (Repo Martín)
    git push origin master:main >> $LOG 2>&1
    
    if [ $? -eq 0 ]; then
        echo "🚀 PRODUCCIÓN ACTUALIZADA EXITOSAMENTE." >> $LOG
        $PROYECTO/scripts/notify.sh "✅ El Industrial: Actualización diaria completada y validada en QA/Prod."
    else
        echo "❌ ERROR EN PUSH A PRODUCCIÓN." >> $LOG
        $PROYECTO/scripts/notify.sh "⚠️ QA pasó, pero falló el push a Producción de Martín."
    fi
else
    echo "🚨 FALLÓ SMOKE TEST EN QA (HTTP $STATUS_QA). ABORTANDO PRODUCCIÓN." >> $LOG
    $PROYECTO/scripts/notify.sh "🛑 BLOQUEADO: QA falló (HTTP $STATUS_QA). Producción NO fue tocada."
    exit 1
fi
