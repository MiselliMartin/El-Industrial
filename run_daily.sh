#!/bin/bash

# Navigate to the project directory
cd "/home/jorge/Documents/Github/El-Industrial" || exit

echo "--- Starting Price List Update ---"
echo "Date: $(date)"

# Run the update script
python3 update_products.py

if [ $? -eq 0 ]; then
    echo "Update successful. Pushing to repository..."
    
    # Git operations
    git add .
    git commit -m "Actualización automática de precios: $(date +%d/%m/%Y)"
    git push
    
    echo "--- Update Complete and Pushed ---"
    echo "Check report_cambios.md for details."
else
    echo "--- Update Failed ---"
    exit 1
fi
