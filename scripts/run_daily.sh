#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( dirname "$SCRIPT_DIR" )"

cd "$PROJECT_ROOT" || exit

echo "--- Starting Price List Update ---"
echo "Date: $(date)"

# Run the update script
python3 "$SCRIPT_DIR/update_products.py"

if [ $? -eq 0 ]; then
    echo "Update successful. Pushing to repository..."
    
    # Git operations
    git add .
    git commit -m "Actualización automática de precios: $(date +%d/%m/%Y)"
    git push
    
    echo "--- Update Complete and Pushed ---"
else
    echo "--- Update Failed ---"
    exit 1
fi
