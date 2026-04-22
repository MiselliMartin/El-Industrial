import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from bertual_api import BertualAPIClient

client = BertualAPIClient()
products = client.fetch_products()
if products:
    print("CAMPOS DISPONIBLES EN UN PRODUCTO:")
    print(list(products[0].keys()))
    print("\nVALORES DE EJEMPLO (Primer producto):")
    for k, v in products[0].items():
        if "precio" in k.lower() or "bonif" in k.lower() or "dto" in k.lower():
            print(f"{k}: {v}")
else:
    print("No se obtuvieron productos.")
