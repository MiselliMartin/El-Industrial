#!/usr/bin/env python3
import json
import gzip
import os
import csv
import socket
from datetime import datetime
import urllib.request
import requests
import xlsxwriter
from dotenv import load_dotenv

# Intentar importar BertualAPIClient
try:
    from bertual_api import BertualAPIClient
except ImportError:
    # Si falla, intentar añadir el directorio actual al path
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from bertual_api import BertualAPIClient

# --- Configuración de Rutas (Mejorada) ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
HOSTNAME = socket.gethostname()

LATEST_INDEX_FILE = os.path.join(PROJECT_ROOT, "latest-json-filename.txt")
CONFIG_FILE = os.path.join(PROJECT_ROOT, "config.json")
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
REPORTS_DIR = os.path.join(PROJECT_ROOT, "reports")
ENV_FILE = os.path.join(PROJECT_ROOT, ".env")

load_dotenv(ENV_FILE)

def load_config():
    if not os.path.exists(CONFIG_FILE):
        print(f"WARN: Archivo de configuración {CONFIG_FILE} no encontrado. Usando valores por defecto.")
        return {}
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

config = load_config()

# Telegram Credentials
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def get_ai_summary(changes):
    if not GEMINI_API_KEY:
        return "Resumen IA no disponible (falta GEMINI_API_KEY)."
    
    print(f"[{HOSTNAME}] Generando resumen ejecutivo con Gemini...")
    model_name = "gemini-3.1-flash-lite-preview" 
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
    
    short_changes = {
        "updated": changes["updated"][:50],
        "new": changes["new"][:20],
        "total_updated": len(changes["updated"]),
        "total_new": len(changes["new"])
    }
    
    prompt = f"""
    Eres un analista de precios experto en ferretería industrial. 
    Analiza estos cambios del día y genera un resumen ejecutivo MUY BREVE (máx 10 líneas).
    Dime qué marcas subieron más fuerte y cuál es la tendencia general.
    Cambios: {json.dumps(short_changes)}
    Escribe en español, profesional y directo.
    """
    
    try:
        response = requests.post(url, json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 400}
        }, timeout=30)
        data = response.json()
        return data['candidates'][0]['content']['parts'][0]['text'].strip()
    except Exception as e:
        return f"Error en resumen IA: {e}"

# --- Parámetros de Precios ---
MARKUP = config.get("markup", 0.0)
IVA = config.get("iva", 0.0)
RESALE_DISCOUNT = config.get("resale_discount", 0.20)

def send_telegram_file(file_path, caption):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"[{HOSTNAME}] Telegram credentials missing. Skipping.")
        return
        
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"
        with open(file_path, 'rb') as f:
            files = {'document': (os.path.basename(file_path), f)}
            data = {'chat_id': TELEGRAM_CHAT_ID, 'caption': caption}
            requests.post(url, files=files, data=data)
    except Exception as e:
        print(f"[{HOSTNAME}] Error enviando Telegram: {e}")

def load_current_data():
    if not os.path.exists(LATEST_INDEX_FILE): return {}
    with open(LATEST_INDEX_FILE, "r") as f: rel_path = f.read().strip()
    full_path = os.path.join(PROJECT_ROOT, rel_path)
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
    
    moneda_raw = str(api_item.get("Moneda", "")).strip().upper()
    moneda = "$" if moneda_raw in ["PES", "ARS"] else ("U$S" if moneda_raw in ["DOL", "USD"] else moneda_raw)
        
    return {
        "producto": code,
        "detalle": api_item.get("Descripcion"),
        "marca": api_item.get("Familia", "").strip(),
        "unidad": api_item.get("Unidad"),
        "moneda": moneda,
        "precio": "{:.2f}".format(final_price),
        "precio_resale": "{:.2f}".format(final_price * (1 - RESALE_DISCOUNT))
    }

def generate_reports(items):
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
        worksheet.write(row, 3, item["unidad"])
        worksheet.write(row, 4, item["moneda"])
        worksheet.write(row, 5, float(item["precio_resale"]))
    workbook.close()
    return ferreteria_path

def save_data(items):
    date_str = datetime.now().strftime("%y-%m-%d")
    filename = f"lista_precio_{date_str}_json_compres.gz"
    rel_path = os.path.join("data", filename)
    full_path = os.path.join(DATA_DIR, filename)
    os.makedirs(DATA_DIR, exist_ok=True)
    
    web_data = [ {k:v for k,v in item.items() if k != "precio_resale"} for item in items ]
    with gzip.open(full_path, "wt", encoding="utf-8") as f:
        json.dump(web_data, f, indent=2, ensure_ascii=False)
    with open(LATEST_INDEX_FILE, "w") as f: f.write(rel_path)
    return rel_path

if __name__ == "__main__":
    try:
        print(f"[{HOSTNAME}] Cargando datos actuales...")
        old_data = load_current_data()
        api_client = BertualAPIClient()
        api_data = api_client.fetch_products()
        
        if not api_data or len(api_data) < 100:
            raise Exception(f"API devolvió pocos productos ({len(api_data) if api_data else 0}).")

        new_items = [transform_item(i) for i in api_data]
        changes = {"updated": [], "new": []}
        
        for item in new_items:
            code = item["producto"]
            if code in old_data and old_data[code]["precio"] != item["precio"]:
                changes["updated"].append({"code": code, "old": old_data[code]["precio"], "new": item["precio"]})
            elif code not in old_data:
                changes["new"].append({"code": code, "new": item["precio"]})
                
        if changes["updated"] or changes["new"]:
            print(f"[{HOSTNAME}] Detectados {len(changes['updated'])} cambios y {len(changes['new'])} nuevos.")
            rep_file = generate_reports(new_items)
            save_data(new_items)
            
            ai_summary = get_ai_summary(changes)
            
            cap = f"🚀 Actualización - {datetime.now().strftime('%d/%m/%Y')}\n"
            cap += f"💻 Nodo: {HOSTNAME}\n\n"
            cap += f"{ai_summary}\n\n"
            cap += f"📦 {len(changes['updated'])} cambios | {len(changes['new'])} nuevos"
            
            send_telegram_file(rep_file, cap)
            print(f"[{HOSTNAME}] Proceso completado exitosamente.")
        else:
            print(f"[{HOSTNAME}] Sin cambios detectados.")
    except Exception as e:
        print(f"[{HOSTNAME}] ERROR: {e}")
        exit(1)
