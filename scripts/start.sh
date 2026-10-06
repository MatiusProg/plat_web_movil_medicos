#!/usr/bin/env bash
# =========================================================================
#  Arranque del backend en producción (Railway).
#
#  Es un script y no una línea suelta en el panel de Railway a propósito: así
#  el comando de arranque vive en el repositorio, se revisa en un pull request
#  y no depende de que alguien recuerde qué escribió en una caja de texto.
#
#  Local NO usa esto: en desarrollo se corre `manage.py runserver`, que
#  recarga solo y sirve los estáticos sin `collectstatic`. Además gunicorn no
#  funciona en Windows.
# =========================================================================
set -euo pipefail

cd "$(dirname "$0")/../backend"

# Las migraciones corren en cada arranque. Es idempotente —Django aplica sólo
# lo que falta— y evita el problema clásico de desplegar código nuevo contra
# un esquema viejo. Con varias réplicas habría que moverlo a una fase previa,
# pero este proyecto corre una sola.
echo "==> Aplicando migraciones"
python manage.py migrate --noinput

# WhiteNoise sirve lo que deje acá. Falla ruidosamente si un archivo
# referencia a otro que no existe, que es lo que se quiere: mejor que no
# levante a que sirva un 404 en la demostración.
echo "==> Recolectando archivos estáticos"
python manage.py collectstatic --noinput --clear

# Copias automáticas (característica general 6): un proceso de fondo que da
# una vuelta por hora y respalda a quien le toca según su plan. Es idempotente
# y toma un candado por organización, así que el contenedor viejo y el nuevo
# conviviendo durante un despliegue no duplican copias. Se apaga con
# AUTOMATIC_BACKUPS=off. Ver backups/automatic.py.
echo "==> Lanzando las copias automáticas en segundo plano"
# -u: sin búfer. Escribiendo a un log y no a una terminal, Python junta la
# salida en bloques de 8 KB y las líneas de cada vuelta no aparecían en los
# logs de Railway: no se veía si las copias se estaban generando ni si fallaban.
python -u manage.py run_automatic_backups --loop &

echo "==> Levantando gunicorn en el puerto ${PORT:-8000}"
# exec: gunicorn reemplaza al script y recibe las señales de la plataforma
# directamente. Sin exec, un reinicio de Railway mata el shell y deja el
# proceso huérfano.
exec gunicorn config.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers "${WEB_CONCURRENCY:-2}" \
    --timeout 60 \
    --access-logfile - \
    --error-logfile -
