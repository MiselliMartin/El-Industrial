#!/usr/bin/env python3
import json
import gzip
import os
from datetime import datetime
import urllib.request

# Configuration
# Hardcode path relative to this script's directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API_URL = "https://autogestion-ehaedo.bertual.com.ar:8200/api"
LATEST_INDEX_FILE = os.path.join(BASE_DIR, "latest-json-filename.txt")
DATA_DIR = os.path.join(BASE_DIR, "data")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")

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

if not all([CUIT, PASSWORD, CLIENT_ID]):
    print(f"Error: Credentials must be set in {ENV_FILE}")
    exit(1)

def load_current_data():
    if not os.path.exists(LATEST_INDEX_FILE):
        return {}
    
    with open(LATEST_INDEX_FILE, "r") as f:
        rel_path = f.read().strip()
    
    full_path = os.path.join(BASE_DIR, rel_path)
    
    if not os.path.exists(full_path):
        print(f"File {full_path} not found.")
        return {}
        
    print(f"Loading current data from {full_path}...")
    try:
        with gzip.open(full_path, "rt", encoding="utf-8") as f:
            data = json.load(f)
            return {p["producto"]: p for p in data}
    except Exception as e:
        print(f"Error loading current data: {e}")
        return {}

def login():
    print("Authenticating...")
    try:
        data = json.dumps({"cuit": CUIT, "password": PASSWORD}).encode("utf-8")
        req = urllib.request.Request(f"{API_URL}/login", data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode())
            if res_data.get("status") == "success":
                print("Authentication successful.")
                return res_data.get("token")
            else:
                raise Exception(f"Login failed: {res_data}")
    except Exception as e:
        print(f"Authentication error: {e}")
        raise

def fetch_products(token):
    print("Fetching product list from API...")
    url = f"{API_URL}/precios/?q=&f=&cl={CLIENT_ID}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req) as response:
        res_data = json.loads(response.read().decode())
        return res_data.get("data", [])

def transform_item(api_item):
    precio_val = api_item.get("Precio_Neto", 0)
    precio_str = "{:.2f}".format(precio_val)
    
    moneda = api_item.get("Moneda", "PES")
    if moneda == "PES":
        moneda = "$"
    
    code = api_item.get("Articulo_Corto") or api_item.get("Articulo")
    
    return {
        "producto": code,
        "detalle": api_item.get("Descripcion"),
        "marca": api_item.get("Familia", "").strip(),
        "unidad": api_item.get("Unidad"),
        "moneda": moneda,
        "precio": precio_str
    }

def detect_changes(old_data, new_list):
    print("Detecting changes...")
    changes = {"updated": [], "new": [], "removed": []}
    new_codes = set()
    for item in new_list:
        code = item["producto"]
        new_codes.add(code)
        if code in old_data:
            if old_data[code]["precio"] != item["precio"]:
                changes["updated"].append({"code": code, "desc": item["detalle"], "old": old_data[code]["precio"], "new": item["precio"]})
        else:
            changes["new"].append({"code": code, "desc": item["detalle"], "price": item["precio"]})
    for code, item in old_data.items():
        if code not in new_codes:
            changes["removed"].append({"code": code, "desc": item["detalle"]})
    return changes

def generate_report(changes):
    now_str = datetime.now().strftime('%Y-%m-%d_%H-%M')
    report_name = f"report_cambios_{now_str}.md"
    report_path = os.path.join(REPORTS_DIR, report_name)
    
    print(f"Generating {report_name}...")
    report = f"# Reporte de Cambios de Precios - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
    # (Simplified for brevity, similar to before but saving to report_path)
    if changes["updated"]:
        report += "## 📈 Precios Modificados\n| Producto | Descripción | Precio Anterior | Precio Nuevo |\n| --- | --- | --- | --- |\n"
        for c in changes["updated"]:
            report += f"| {c['code']} | {c['desc']} | $ {c['old']} | $ {c['new']} |\n"
    if changes["new"]:
        report += "\n## ✨ Productos Nuevos\n| Producto | Descripción | Precio |\n| --- | --- | --- |\n"
        for n in changes["new"]:
            report += f"| {n['code']} | {n['desc']} | $ {n['price']} |\n"
    if changes["removed"]:
        report += "\n## 🗑️ Productos Eliminados\n| Producto | Descripción |\n| --- | --- |\n"
        for r in changes["removed"]:
            report += f"| {r['code']} | {r['desc']} |\n"
    if not any(changes.values()):
        report += "No se detectaron cambios.\n"
        
    os.makedirs(REPORTS_DIR, exist_ok=True)
    with open(report_path, "w") as f:
        f.write(report)
        
    # Also create a symlink or a copy called "ultimo_reporte.md" for easy access
    latest_report_path = os.path.join(REPORTS_DIR, "ultimo_reporte.md")
    with open(latest_report_path, "w") as f:
        f.write(report)

def save_and_update(transformed_data):
    date_str = datetime.now().strftime("%y-%m-%d")
    filename = f"lista_precio_{date_str}_json_compres.gz"
    rel_path = os.path.join("data", filename)
    full_path = os.path.join(DATA_DIR, filename)
    
    print(f"Saving new data to {full_path}...")
    os.makedirs(DATA_DIR, exist_ok=True)
    json_str = json.dumps(transformed_data, indent=2, ensure_ascii=False)
    with gzip.open(full_path, "wt", encoding="utf-8") as f:
        f.write(json_str)
        
    with open(LATEST_INDEX_FILE, "w") as f:
        f.write(rel_path)
        
    return rel_path

if __name__ == "__main__":
    try:
        old_data = load_current_data()
        token = login()
        api_data = fetch_products(token)
        new_list = [transform_item(item) for item in api_data]
        changes = detect_changes(old_data, new_list)
        generate_report(changes)
        new_rel_path = save_and_update(new_list)
        print(f"Successfully updated to {new_rel_path}")
    except Exception as e:
        print(f"Error: {e}")
        exit(1)
