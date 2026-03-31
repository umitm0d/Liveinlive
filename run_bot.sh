#!/bin/bash
# Ümitm0d AndroTV - 1 saatte bir çalışan döngü
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BOT="$SCRIPT_DIR/androtv_bot.py"

echo "Ümitm0d AndroTV Bot Servisi Başladı"
echo "Her 1 saatte bir güncelleme yapılacak."

while true; do
    echo ""
    echo "=== $(date '+%Y-%m-%d %H:%M:%S') - Güncelleme başlıyor ==="
    python3 "$BOT"
    echo "=== Bir sonraki güncelleme 1 saat sonra ==="
    sleep 3600
done
