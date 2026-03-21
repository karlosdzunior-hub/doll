#!/bin/bash
# Скрипт для пуша в GitHub

echo "Добавляю файлы..."
git add .

echo "Коммичу..."
git commit -m "Update $(date '+%Y-%m-%d %H:%M')"

echo "Пушу в GitHub..."
git push origin master

echo "Готово!"
