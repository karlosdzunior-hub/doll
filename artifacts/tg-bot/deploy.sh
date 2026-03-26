#!/bin/bash
# ============================================
# ДЕПЛОЙ БОТА "МИКРОКАПИТАЛИЗМ" НА VPS
# Запусти на VPS от root:
#   curl -o deploy.sh https://raw.githubusercontent.com/karlosdzunior-hub/doll/main/artifacts/tg-bot/deploy.sh
#   bash deploy.sh
# ============================================

set -e

REPO_URL="https://github.com/karlosdzunior-hub/doll.git"
BOT_DIR="/root/microbot"
BOT_SUBDIR="artifacts/tg-bot"
SERVICE_NAME="microbot"

echo "=================================="
echo "  Установка бота Микрокапитализм"
echo "=================================="

# 1. Обновляем систему
echo "[1/7] Обновление системы..."
apt-get update -qq
apt-get install -y python3 python3-pip python3-venv git curl

# 2. Клонируем репозиторий
echo "[2/7] Клонирование репозитория..."
if [ -d "$BOT_DIR" ]; then
    echo "  Папка уже существует — обновляем..."
    cd "$BOT_DIR"
    git pull
else
    git clone "$REPO_URL" /tmp/doll-repo
    mkdir -p "$BOT_DIR"
    cp -r /tmp/doll-repo/$BOT_SUBDIR/. "$BOT_DIR/"
    rm -rf /tmp/doll-repo
fi

cd "$BOT_DIR"

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
    echo "  Создаём .env из примера..."
    cp "$BOT_DIR/.env.example" "$BOT_DIR/.env"
    echo ""
    echo "  ⚠️  ВАЖНО: заполни файл .env перед запуском!"
    echo "  nano $BOT_DIR/.env"
    echo ""
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
echo "1. Заполни .env файл:"
echo "   nano $BOT_DIR/.env"
echo ""
echo "2. Запусти бота:"
echo "   systemctl start $SERVICE_NAME"
echo ""
echo "3. Проверь статус:"
echo "   systemctl status $SERVICE_NAME"
echo ""
echo "4. Смотри логи:"
echo "   journalctl -u $SERVICE_NAME -f"
echo ""
echo "=================================="
