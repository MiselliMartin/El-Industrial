#!/usr/bin/env python3
import json
import gzip
import os
from datetime import datetime
import urllib.request

# Configuration
API_URL = "https://autogestion-ehaedo.bertual.com.ar:8200/api"
LATEST_INDEX_FILE = "latest-json-filename.txt"
ENV_FILE = ".env"

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
    print("Error: BERTUAL_CUIT, BERTUAL_PASSWORD, and BERTUAL_CLIENT_ID must be set in .env")
    exit(1)

def load_current_data():
    if not os.path.exists(LATEST_INDEX_FILE):
        return {}
    
    with open(LATEST_INDEX_FILE, "r") as f:
        filename = f.read().strip()
    
    if not os.path.exists(filename):
        print(f"File {filename} not found.")
        return {}
        
    print(f"Loading current data from {filename}...")
    try:
        with gzip.open(filename, "rt", encoding="utf-8") as f:
            data = json.load(f)
            # Map by product code for easy comparison
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
    
    # Use Articulo_Corto if available to match legacy data, otherwise fall back to Articulo
    code = api_item.get("Articulo_Corto") or api_item.get("Articulo")
    
    return {
        "producto": code,
        "detalle": api_item.get("Descripcion"),
        "marca": api_item.get("Familia", "").strip(),
        "packet": api_item.get("Empaque"), # Keep for potential future use or debugging
        "unidad": api_item.get("Unidad"),
        "moneda": moneda,
        "precio": precio_str
    }

def detect_changes(old_data, new_list):
    print("Detecting changes...")
    changes = {
        "updated": [],
        "new": [],
        "removed": []
    }
    
    new_codes = set()
    for item in new_list:
        code = item["producto"]
        new_codes.add(code)
        
        if code in old_data:
            old_item = old_data[code]
            if old_item["precio"] != item["precio"]:
                changes["updated"].append({
                    "code": code,
                    "desc": item["detalle"],
                    "old": old_item["precio"],
                    "new": item["precio"]
                })
        else:
            changes["new"].append({
                "code": code,
                "desc": item["detalle"],
                "price": item["precio"]
            })
            
    for code, item in old_data.items():
        if code not in new_codes:
            changes["removed"].append({
                "code": code,
                "desc": item["detalle"]
            })
            
    return changes

def generate_report(changes):
    print("Generating report_cambios.md...")
    report = f"# Reporte de Cambios de Precios - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
    
    if changes["updated"]:
        report += "## 📈 Precios Modificados\n"
        report += "| Producto | Descripción | Precio Anterior | Precio Nuevo | Cambio |\n"
        report += "| --- | --- | --- | --- | --- |\n"
        for c in changes["updated"]:
            old_p = float(c["old"])
            new_p = float(c["new"])
            diff = new_p - old_p
            percent = (diff / old_p * 100) if old_p != 0 else 0
            emoji = "🔴" if diff > 0 else "🟢"
            report += f"| {c['code']} | {c['desc']} | $ {c['old']} | $ {c['new']} | {emoji} {diff:+.2f} ({percent:+.2f}%) |\n"
        report += "\n"
        
    if changes["new"]:
        report += "## ✨ Productos Nuevos\n"
        report += "| Producto | Descripción | Precio |\n"
        report += "| --- | --- | --- |\n"
        for n in changes["new"]:
            report += f"| {n['code']} | {n['desc']} | $ {n['price']} |\n"
        report += "\n"
        
    if changes["removed"]:
        report += "## 🗑️ Productos Eliminados\n"
        report += "| Producto | Descripción |\n"
        report += "| --- | --- |\n"
        for r in changes["removed"]:
            report += f"| {r['code']} | {r['desc']} |\n"
        report += "\n"
        
    if not any(changes.values()):
        report += "No se detectaron cambios en la lista de precios.\n"
        
    with open("report_cambios.md", "w") as f:
        f.write(report)
        
    print(f"Summary: {len(changes['updated'])} updated, {len(changes['new'])} new, {len(changes['removed'])} removed.")

def save_and_update(transformed_data):
    now = datetime.now()
    date_str = now.strftime("%y-%m-%d")
    filename = f"lista_precio_{date_str}_json_compres.gz"
    
    print(f"Saving new data to {filename}...")
    json_str = json.dumps(transformed_data, indent=2, ensure_ascii=False)
    
    with gzip.open(filename, "wt", encoding="utf-8") as f:
        f.write(json_str)
        
    with open(LATEST_INDEX_FILE, "w") as f:
        f.write(filename)
        
    return filename

if __name__ == "__main__":
    try:
        old_data = load_current_data()
        token = login()
        api_data = fetch_products(token)
        new_list = [transform_item(item) for item in api_data]
        
        changes = detect_changes(old_data, new_list)
        generate_report(changes)
        
        new_filename = save_and_update(new_list)
        print(f"Successfully updated to {new_filename}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
