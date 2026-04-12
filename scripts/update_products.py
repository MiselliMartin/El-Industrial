#!/usr/bin/env python3
import json
import gzip
import os
import csv
from datetime import datetime
import urllib.request
import requests
import xlsxwriter
from dotenv import load_dotenv
from bertual_api import BertualAPIClient

import sys
# Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LATEST_INDEX_FILE = os.path.join(BASE_DIR, "latest-json-filename.txt")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
DATA_DIR = os.path.join(BASE_DIR, "data")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
ENV_FILE = os.path.join(BASE_DIR, ".env")

# Asegurar que los módulos en el mismo directorio sean importables
if SCRIPT_DIR not in sys.path:
    sys.path.append(SCRIPT_DIR)

load_dotenv(ENV_FILE)

def load_config():
    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError(f"Configuration file {CONFIG_FILE} is missing. Please provide it so the bot doesn't hallucinate missing fallbacks.")
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

config = load_config()

# Telegram Credentials (Now from .env)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def get_ai_summary(changes):
    if not GEMINI_API_KEY:
        return "Resumen IA no disponible (falta GEMINI_API_KEY en .env)."
    
    print("Generando resumen ejecutivo con Gemini...")
    model_name = "gemini-2.0-flash" 
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
    
    # Preparamos un prompt conciso con los datos de cambios
    # Limitamos la cantidad de cambios enviados si son demasiados para no saturar
    short_changes = {
        "updated": changes["updated"][:50], # Top 50 si hay muchos
        "new": changes["new"][:20],
        "total_updated": len(changes["updated"]),
        "total_new": len(changes["new"])
    }
    
    prompt = f"""
    Eres un analista de precios experto en ferretería industrial. 
    Analiza estos cambios del día y genera un resumen ejecutivo MUY BREVE (máx 10 líneas) para el dueño.
    Dime qué marcas subieron más fuerte, si hay productos nuevos clave y cuál es la tendencia general.
    Cambios: {json.dumps(short_changes)}
    
    Escribe en español, de forma profesional y directa. No uses saludos, ve al grano.
    """
    
    headers = {'Content-Type': 'application/json'}
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 400
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        data = response.json()
        summary = data['candidates'][0]['content']['parts'][0]['text']
        return summary.strip()
    except Exception as e:
        print(f"Error llamando a Gemini: {e}")
        return "No se pudo generar el resumen automático debido a un error técnico."


MARKUP = config.get("markup", 0.0)
IVA = config.get("iva", 0.0)
RESALE_DISCOUNT = config.get("resale_discount", 0.20)

def send_telegram_file(file_path, caption):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram credentials missing in .env. Skipping.")
        return
        
    print(f"Sending {file_path} to Telegram...")
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"
        with open(file_path, 'rb') as f:
            # Better robust file sending with filename
            files = {'document': (os.path.basename(file_path), f)}
            data = {'chat_id': TELEGRAM_CHAT_ID, 'caption': caption}
            response = requests.post(url, files=files, data=data)
        
        if response.status_code == 200:
            print("Telegram message sent successfully.")
        else:
            print(f"Error sending Telegram: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Failed to send Telegram: {e}")

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

def calculate_price(neto):
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
    
    ferreteria_path = os.path.join(REPORTS_DIR, f"lista_ferreteria_{now_str}.xlsx")
    workbook = xlsxwriter.Workbook(ferreteria_path)
    worksheet = workbook.add_worksheet()
    headers = ["Producto", "Detalle", "Marca", "Unidad", "Moneda", "Precio"]
    for col, h in enumerate(headers): worksheet.write(0, col, h)
    for row, item in enumerate(items, 1):
        worksheet.write(row, 0, item["producto"])
        worksheet.write(row, 1, item["detalle"])
        worksheet.write(row, 2, item["marca"])
        u = item["unidad"]
        worksheet.write(row, 3, "Un" if u in ["UN", "Un"] else u)
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
    import sys
    if "--force-telegram" in sys.argv:
        import glob
        files = glob.glob(os.path.join(REPORTS_DIR, "lista_ferreteria_*.*"))
        if not files:
            print("No se encontraron exceles en la carpeta reports para enviar de prueba.")
            exit(1)
        latest_file = max(files, key=os.path.getctime)
        send_telegram_file(latest_file, "🚀 (TEST) Forzando el envío del último Excel disponible para verificar conectividad con Telegram.")
        print(f"Test de telegram finalizado, archivo enviado: {latest_file}.")
        exit(0)

    try:
        old_data = load_current_data()
        api_client = BertualAPIClient()
        api_data = api_client.fetch_products()
        new_items = [transform_item(i) for i in api_data]
        
        changes = {"updated": [], "new": []}
        for item in new_items:
            code = item["producto"]
            if code in old_data and old_data[code]["precio"] != item["precio"]:
                changes["updated"].append({"code": code, "old": old_data[code]["precio"], "new": item["precio"]})
            elif code not in old_data:
                changes["new"].append({"code": code, "new": item["precio"]})
                
        if changes["updated"] or changes["new"]:
            rep_file = generate_reports(new_items, changes)
            save_data(new_items)
            
            # Obtener Resumen IA
            ai_summary = get_ai_summary(changes)
            
            if not os.getenv("SKIP_TELEGRAM"):
                cap = f"🚀 Actualización - {datetime.now().strftime('%d/%m/%Y')}\n\n"
                cap += f"{ai_summary}\n\n"
                cap += f"📦 {len(changes['updated'])} cambios | {len(changes['new'])} nuevos"
                send_telegram_file(rep_file, cap)
            print("Process complete with changes.")
        else:
            print("No changes detected in prices or items. Skipping file updates and Telegram notification.")
    except Exception as e: print(f"Error: {e}"); exit(1)
