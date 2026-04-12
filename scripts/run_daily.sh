#!/bin/bash
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( dirname "$SCRIPT_DIR" )"
VENV_PATH="$PROJECT_ROOT/venv"
FILE_DATE=$(date +%y-%m-%d)

if [ -f "$PROJECT_ROOT/.env" ]; then
    export $(grep -v '^#' "$PROJECT_ROOT/.env" | xargs)
fi
cd "$PROJECT_ROOT" || exit
if [[ "$(hostname)" == *"mint"* ]]; then
    echo "Running as Secondary. Checking GitHub..."
    URL="https://raw.githubusercontent.com/MiselliMartin/El-Industrial/main/data/lista_precio_${FILE_DATE}_json_compres.gz"
    if curl --output /dev/null --silent --head --fail "$URL"; then
        echo "Already updated. Exiting."
        exit 0
    fi
fi
if [ -d "$VENV_PATH" ]; then source "$VENV_PATH/bin/activate"; fi
python3 "$SCRIPT_DIR/update_products.py"
if [ $? -eq 0 ]; then
    if [ ! -z "$GITHUB_TOKEN" ]; then
        git remote set-url origin "https://x-access-token:${GITHUB_TOKEN}@github.com/MiselliMartin/El-Industrial.git"
    fi
    git add .
    git commit -m "Actualización automática de precios: $(date +%d/%m/%Y) [$(hostname)]"
    git push origin HEAD:main
else
    exit 1
fi
