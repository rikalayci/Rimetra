#!/bin/sh
set -e
cd /app
echo "[rimetra] Veritabanı şeması güncelleniyor..."
i=0
until alembic upgrade head; do
  i=$((i+1))
  if [ "$i" -ge 15 ]; then echo "[rimetra] Veritabanına bağlanılamadı."; exit 1; fi
  echo "[rimetra] Veritabanı bekleniyor ($i)..."; sleep 2
done
exec "$@"
