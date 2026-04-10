#!/usr/bin/env python3
import json
import gzip
import os
import csv
from datetime import datetime
import urllib.request

# Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API_URL = "https://autogestion-ehaedo.bertual.com.ar:8200/api"
LATEST_INDEX_FILE = os.path.join(BASE_DIR, "latest-json-filename.txt")
DATA_DIR = os.path.join(BASE_DIR, "data")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
ENV_FILE = os.path.join(BASE_DIR, ".env")

def load_env():
    env_vars = {}
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, "r") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    key, value = line.strip().split("=", 1)
                    env_vars[key] = value
    return env_vars

env = load_env()
CUIT = env.get("BERTUAL_CUIT")
PASSWORD = env.get("BERTUAL_PASSWORD")
CLIENT_ID = env.get("BERTUAL_CLIENT_ID")
MARKUP = float(env.get("PROFIT_MARKUP", 0.60))
IVA = float(env.get("IVA", 0.21))

if not all([CUIT, PASSWORD, CLIENT_ID]):
    print(f"Error: Credentials must be set in {ENV_FILE}")
    exit(1)

def load_current_data():
    if not os.path.exists(LATEST_INDEX_FILE): return {}
    with open(LATEST_INDEX_FILE, "r") as f: rel_path = f.read().strip()
    full_path = os.path.join(BASE_DIR, rel_path)
    if not os.path.exists(full_path): return {}
    try:
        with gzip.open(full_path, "rt", encoding="utf-8") as f:
            data = json.load(f)
            return {p["producto"]: p for p in data}
    except: return {}

def login():
    data = json.dumps({"cuit": CUIT, "password": PASSWORD}).encode("utf-8")
    req = urllib.request.Request(f"{API_URL}/login", data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as response:
        res_data = json.loads(response.read().decode())
        return res_data.get("token")

def fetch_products(token):
    url = f"{API_URL}/precios/?q=&f=&cl={CLIENT_ID}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req) as response:
        res_data = json.loads(response.read().decode())
        return res_data.get("data", [])

def calculate_price(neto):
    # FORMULA: Costo Neto * (1 + IVA) * (1 + Ganancia)
    return neto * (1 + IVA) * (1 + MARKUP)

def transform_item(api_item):
    neto = api_item.get("Precio_Neto", 0)
    final_price = calculate_price(neto)
    
    code = api_item.get("Articulo_Corto") or api_item.get("Articulo")
    moneda = "$" if api_item.get("Moneda") == "PES" else api_item.get("Moneda")
    
    return {
        "producto": code,
        "detalle": api_item.get("Descripcion"),
        "marca": api_item.get("Familia", "").strip(),
        "unidad": api_item.get("Unidad"),
        "moneda": moneda,
        "precio": "{:.2f}".format(final_price),
        "precio_resale": "{:.2f}".format(final_price * 0.8) # 20% discount for Ferreteria
    }

def generate_reports(items, changes):
    now_str = datetime.now().strftime('%Y-%m-%d_%H-%M')
    os.makedirs(REPORTS_DIR, exist_ok=True)
    
    # 1. Reporte de Cambios (Web)
    report_path = os.path.join(REPORTS_DIR, f"report_cambios_{now_str}.md")
    with open(report_path, "w") as f:
        f.write(f"# Reporte de Cambios {datetime.now().strftime('%Y-%m-%d')}\n\n")
        if changes["updated"]:
            f.write("## 📈 Precios Modificados\n| Producto | Viejo | Nuevo |\n| --- | --- | --- |\n")
            for c in changes["updated"]: f.write(f"| {c['code']} | {c['old']} | {c['new']} |\n")
    
    # 2. Lista Ferreteria (Excel/CSV)
    ferreteria_path = os.path.join(REPORTS_DIR, f"lista_ferreteria_{now_str}.csv")
    with open(ferreteria_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["Codigo", "Descripcion", "Marca", "Precio Publico", "Precio Ferreteria (-20%)"])
        for item in items:
            writer.writerow([item["producto"], item["detalle"], item["marca"], item["precio"], item["precio_resale"]])
    
    # Update quick access link
    with open(os.path.join(REPORTS_DIR, "ultimo_reporte.md"), "w") as f: f.write(f"Ultimo reporte generado: {now_str}")

def save_data(items):
    date_str = datetime.now().strftime("%y-%m-%d")
    filename = f"lista_precio_{date_str}_json_compres.gz"
    rel_path = os.path.join("data", filename)
    full_path = os.path.join(DATA_DIR, filename)
    
    # Remove internal fields before saving for the web
    web_data = []
    for item in items:
        web_item = item.copy()
        web_item.pop("precio_resale", None)
        web_data.append(web_item)
        
    with gzip.open(full_path, "wt", encoding="utf-8") as f: json.dump(web_data, f, indent=2, ensure_ascii=False)
    with open(LATEST_INDEX_FILE, "w") as f: f.write(rel_path)
    return rel_path

if __name__ == "__main__":
    try:
        old_data = load_current_data()
        token = login()
        api_data = fetch_products(token)
        new_items = [transform_item(i) for i in api_data]
        
        # Simple change detection
        changes = {"updated": [], "new": [], "removed": []}
        for item in new_items:
            code = item["producto"]
            if code in old_data and old_data[code]["precio"] != item["precio"]:
                changes["updated"].append({"code": code, "old": old_data[code]["precio"], "new": item["precio"]})
                
        generate_reports(new_items, changes)
        save_data(new_items)
        print("Success! Process complete.")
    except Exception as e: print(f"Error: {e}"); exit(1)
