#!/bin/bash
# Cargar variables si existen
source /home/jorge/El-Industrial/.env
MESSAGE=$1
curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_TOKEN/sendMessage"      -d chat_id="$TELEGRAM_CHAT_ID"      -d text="$MESSAGE" > /dev/null
