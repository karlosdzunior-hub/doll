#!/bin/bash
# ============================================
# ДЕПЛОЙ БОТА "МИКРОКАПИТАЛИЗМ" НА VPS
# Запусти на VPS от root:
#   curl -o deploy.sh https://raw.githubusercontent.com/karlosdzunior-hub/doll/main/artifacts/tg-bot/deploy.sh
#   bash deploy.sh
# ============================================

set -e

REPO_ZIP="https://raw.githubusercontent.com/karlosdzunior-hub/doll/main"
BOT_DIR="/root/microbot"
SERVICE_NAME="microbot"

echo "=================================="
echo "  Установка бота Микрокапитализм"
echo "=================================="

# 1. Обновляем систему
echo "[1/7] Обновление системы..."
apt-get update -qq
apt-get install -y python3 python3-pip python3-venv curl unzip

# 2. Скачиваем файлы бота
echo "[2/7] Скачивание файлов бота..."
mkdir -p "$BOT_DIR"
mkdir -p "$BOT_DIR/handlers"
mkdir -p "$BOT_DIR/services"

FILES=(
    "bot.py"
    "config.py"
    "db.py"
    "utils.py"
    "requirements.txt"
    ".env.example"
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
    echo "  Скачиваем $FILE..."
    curl -fsSL "$REPO_ZIP/artifacts/tg-bot/$FILE" -o "$BOT_DIR/$FILE"
done

# 3. Создаём виртуальное окружение
echo "[3/7] Создание виртуального окружения Python..."
python3 -m venv "$BOT_DIR/venv"

# 4. Устанавливаем зависимости
echo "[4/7] Установка зависимостей..."
"$BOT_DIR/venv/bin/pip" install --quiet --upgrade pip
"$BOT_DIR/venv/bin/pip" install --quiet -r "$BOT_DIR/requirements.txt"

# 5. Настраиваем .env
echo "[5/7] Настройка переменных окружения..."
if [ -f "$BOT_DIR/.env" ]; then
    echo "  Файл .env уже существует, пропускаем."
else
    cp "$BOT_DIR/.env.example" "$BOT_DIR/.env"
fi

# 6. Создаём systemd сервис
echo "[6/7] Настройка systemd сервиса..."
cat > /etc/systemd/system/${SERVICE_NAME}.service << EOF
[Unit]
Description=Microbot Telegram Bot - Микрокапитализм
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=${BOT_DIR}
ExecStart=${BOT_DIR}/venv/bin/python3 ${BOT_DIR}/bot.py
EnvironmentFile=${BOT_DIR}/.env
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "$SERVICE_NAME"

echo ""
echo "[7/7] Готово!"
echo ""
echo "=================================="
echo "  Следующие шаги:"
echo "=================================="
echo ""
echo "1. Запусти бота:"
echo "   systemctl start $SERVICE_NAME"
echo ""
echo "2. Проверь статус:"
echo "   systemctl status $SERVICE_NAME"
echo ""
echo "3. Смотри логи:"
echo "   journalctl -u $SERVICE_NAME -f"
echo ""
echo "=================================="
