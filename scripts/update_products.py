#!/usr/bin/env python3
import json
import gzip
import os
import csv
from datetime import datetime
import urllib.request
import requests
import xlsxwriter

# Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API_URL = "https://autogestion-ehaedo.bertual.com.ar:8200/api"
LATEST_INDEX_FILE = os.path.join(BASE_DIR, "latest-json-filename.txt")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
DATA_DIR = os.path.join(BASE_DIR, "data")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
ENV_FILE = os.path.join(BASE_DIR, ".env")

# Telegram Default
TELEGRAM_TOKEN = "8174958315:AAFL8e_hBh0jsO1VpLiUp33mLRnji0gZ63g"
TELEGRAM_CHAT_ID = "6425231391"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {"markup": 0.0, "iva": 0.0, "resale_discount": 0.20}

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
config = load_config()

CUIT = env.get("BERTUAL_CUIT")
PASSWORD = env.get("BERTUAL_PASSWORD")
CLIENT_ID = env.get("BERTUAL_CLIENT_ID")

MARKUP = config.get("markup", 0.0)
IVA = config.get("iva", 0.0)
RESALE_DISCOUNT = config.get("resale_discount", 0.20)

def send_telegram_file(file_path, caption):
    print(f"Sending {file_path} to Telegram...")
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"
    try:
        with open(file_path, 'rb') as f:
            files = {'document': f}
            data = {'chat_id': TELEGRAM_CHAT_ID, 'caption': caption}
            response = requests.post(url, files=files, data=data)
            if response.status_code == 200:
                print("Telegram message sent successfully.")
            else:
                print(f"Error sending Telegram: {response.text}")
    except Exception as e:
        print(f"Telegram error: {e}")

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

def calculate_price(neto, alicuota_api=21):
    # If config IVA is 0, we trust the API might already have it or user wants Neto
    # But common logic: Price = Neto * (1 + IVA_API/100) if user wants 'Lista'
    # The user said 'tal cual el proveedor'. 
    return neto * (1 + IVA) * (1 + MARKUP)

def transform_item(api_item):
    neto = api_item.get("Precio_Neto", 0)
    final_price = calculate_price(neto)
    code = api_item.get("Articulo_Corto") or api_item.get("Articulo")
    
    # Currency Mapping
    moneda_raw = str(api_item.get("Moneda", "")).strip().upper()
    if moneda_raw in ["PES", "ARS"]: moneda = "$"
    elif moneda_raw in ["DOL", "USD"]: moneda = "U$S"
    else: moneda = moneda_raw
        
    return {
        "producto": code,
        "detalle": api_item.get("Descripcion"),
        "marca": api_item.get("Familia", "").strip(),
        "unidad": api_item.get("Unidad"),
        "moneda": moneda,
        "precio": "{:.2f}".format(final_price),
        "precio_resale": "{:.2f}".format(final_price * (1 - RESALE_DISCOUNT))
    }

def generate_reports(items, changes):
    now_str = datetime.now().strftime('%Y-%m-%d_%H-%M')
    os.makedirs(REPORTS_DIR, exist_ok=True)
    report_path = os.path.join(REPORTS_DIR, f"report_cambios_{now_str}.md")
    with open(report_path, "w") as f:
        f.write(f"# Reporte de Cambios {datetime.now().strftime('%Y-%m-%d')}\n\n")
        if changes["updated"]:
            f.write("## 📈 Precios Modificados\n| Producto | Viejo | Nuevo |\n| --- | --- | --- |\n")
            for c in changes["updated"]: f.write(f"| {c['code']} | {c['old']} | {c['new']} |\n")
        else: f.write("No se detectaron cambios de precios.\n")
    
    ferreteria_path = os.path.join(REPORTS_DIR, f"lista_ferreteria_{now_str}.xlsx")
    workbook = xlsxwriter.Workbook(ferreteria_path)
    worksheet = workbook.add_worksheet()
    headers = ["Producto", "Detalle", "Marca", "Unidad", "Moneda", "Precio"]
    for col, h in enumerate(headers): worksheet.write(0, col, h)
    for row, item in enumerate(items, 1):
        worksheet.write(row, 0, item["producto"])
        worksheet.write(row, 1, item["detalle"])
        worksheet.write(row, 2, item["marca"])
        worksheet.write(row, 3, "Un" if item["unidad"] == "UN" else item.get("unidad", "Un"))
        worksheet.write(row, 4, item["moneda"])
        worksheet.write(row, 5, float(item["precio_resale"]))
    workbook.close()
    return ferreteria_path

def save_data(items):
    date_str = datetime.now().strftime("%y-%m-%d")
    filename = f"lista_precio_{date_str}_json_compres.gz"
    rel_path = os.path.join("data", filename)
    full_path = os.path.join(DATA_DIR, filename)
    web_data = [ {k:v for k,v in item.items() if k != "precio_resale"} for item in items ]
    with gzip.open(full_path, "wt", encoding="utf-8") as f:
        json.dump(web_data, f, indent=2, ensure_ascii=False)
    with open(LATEST_INDEX_FILE, "w") as f: f.write(rel_path)
    return rel_path

if __name__ == "__main__":
    try:
        old_data = load_current_data()
        token = login()
        api_data = fetch_products(token)
        new_items = [transform_item(i) for i in api_data]
        changes = {"updated": [], "new": [], "removed": []}
        for item in new_items:
            code = item["producto"]
            if code in old_data and old_data[code]["precio"] != item["precio"]:
                changes["updated"].append({"code": code, "old": old_data[code]["precio"], "new": item["precio"]})
            elif code not in old_data:
                changes["new"].append({"code": code, "new": item["precio"]})
        
        rep_file = generate_reports(new_items, changes)
        save_data(new_items)
        
        # Always send the Excel file as requested
        if not os.getenv("SKIP_TELEGRAM"):
            cap = f"🚀 Lista de Ferretería Actualizada - {datetime.now().strftime('%d/%m/%Y')}"
            if changes["updated"] or changes["new"]:
                cap += f"\nSe detectaron {len(changes['updated'])} cambios y {len(changes['new'])} productos nuevos."
            else:
                cap += "\nNo se detectaron cambios de precio hoy (envío de lista actual)."
            
            send_telegram_file(rep_file, cap)
        
        print("Done.")
    except Exception as e: print(f"Error: {e}"); exit(1)
