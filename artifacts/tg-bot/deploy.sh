#!/bin/bash
# ============================================
# ДЕПЛОЙ БОТА "МИКРОКАПИТАЛИЗМ" НА VPS
# Запусти: bash deploy.sh
# ============================================

set -e

BOT_DIR="/root/microbot"
SERVICE_NAME="microbot"
PYTHON="python3"

echo "=================================="
echo "  Установка бота Микрокапитализм"
echo "=================================="

# 1. Обновляем систему
echo "[1/6] Обновление системы..."
apt-get update -qq
apt-get install -y python3 python3-pip python3-venv git curl

# 2. Создаём папку
echo "[2/6] Создание директории $BOT_DIR..."
mkdir -p "$BOT_DIR"
cd "$BOT_DIR"

# 3. Копируем файлы (если запущено из папки бота)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "[3/6] Копирование файлов из $SCRIPT_DIR..."
cp -r "$SCRIPT_DIR"/* "$BOT_DIR/" 2>/dev/null || true

# 4. Создаём виртуальное окружение и устанавливаем зависимости
echo "[4/6] Установка Python-зависимостей..."
python3 -m venv "$BOT_DIR/venv"
"$BOT_DIR/venv/bin/pip" install --quiet --upgrade pip
"$BOT_DIR/venv/bin/pip" install --quiet -r "$BOT_DIR/requirements.txt"

# 5. Проверяем токен
if [ -f "$BOT_DIR/.env" ]; then
    echo "[5/6] Файл .env найден."
else
    echo "[5/6] ВНИМАНИЕ: Файл .env не найден!"
    echo "      Создай файл: $BOT_DIR/.env"
    echo "      И вставь строку: TELEGRAM_BOT_TOKEN=твой_токен"
fi

# 6. Создаём systemd сервис
echo "[6/6] Настройка автозапуска (systemd)..."
cat > /etc/systemd/system/${SERVICE_NAME}.service << EOF
[Unit]
Description=Microbot Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=${BOT_DIR}
ExecStart=${BOT_DIR}/venv/bin/python3 ${BOT_DIR}/bot.py
EnvironmentFile=${BOT_DIR}/.env
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "$SERVICE_NAME"

echo ""
echo "=================================="
echo "  Установка завершена!"
echo "=================================="
echo ""
echo "  Следующий шаг — создай файл .env:"
echo "  nano $BOT_DIR/.env"
echo ""
echo "  Вставь:"
echo "  TELEGRAM_BOT_TOKEN=твой_токен"
echo ""
echo "  Затем запусти:"
echo "  systemctl start $SERVICE_NAME"
echo ""
echo "  Проверь статус:"
echo "  systemctl status $SERVICE_NAME"
echo "=================================="
