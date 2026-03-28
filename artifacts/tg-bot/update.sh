#!/bin/bash
# ============================================
# ОБНОВЛЕНИЕ БОТА "МИКРОКАПИТАЛИЗМ" НА VPS
# Запусти: bash /root/microbot/update.sh
# ============================================

set -e

BOT_DIR="/root/microbot"
RAW="https://raw.githubusercontent.com/karlosdzunior-hub/doll/main"
SERVICE_NAME="microbot"

echo "=================================="
echo "  Обновление бота Микрокапитализм"
echo "=================================="

echo "[1/3] Скачиваем обновления..."

FILES=(
    "bot.py"
    "config.py"
    "db.py"
    "utils.py"
    "requirements.txt"
    "handlers/__init__.py"
    "handlers/main.py"
    "services/__init__.py"
    "services/chat.py"
    "services/credits.py"
    "services/energy.py"
    "services/events.py"
    "services/jackpot.py"
    "services/market.py"
    "services/notifications.py"
)

for FILE in "${FILES[@]}"; do
    echo "  $FILE"
    curl -fsSL "$RAW/$FILE" -o "$BOT_DIR/$FILE"
done

echo "[2/3] Устанавливаем новые зависимости (если есть)..."
"$BOT_DIR/venv/bin/pip" install --quiet -r "$BOT_DIR/requirements.txt"

echo "[3/3] Перезапускаем бота..."
systemctl restart "$SERVICE_NAME"

echo ""
echo "✅ Готово! Бот обновлён и перезапущен."
echo ""
echo "Проверь статус:"
echo "  systemctl status $SERVICE_NAME"
