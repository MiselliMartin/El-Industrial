#!/usr/bin/env python3
import json, gzip, os, time, sys
from datetime import datetime
from dotenv import load_dotenv

try:
    from bertual_api import BertualAPIClient
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from bertual_api import BertualAPIClient

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
LATEST_INDEX_FILE = os.path.join(BASE_DIR, 'latest-json-filename.txt')
LATEST_INDEX_FILE_JSON = os.path.join(BASE_DIR, 'latest-json-filename.json')
DATA_DIR = os.path.join(BASE_DIR, 'data')
CONFIG_FILE = os.path.join(BASE_DIR, 'config.json')

load_dotenv(os.path.join(BASE_DIR, '.env'))

def load_config():
    if not os.path.exists(CONFIG_FILE): return {'markup': 0.0, 'iva': 0.0}
    try:
        with open(CONFIG_FILE, 'r') as f: return json.load(f)
    except: return {'markup': 0.0, 'iva': 0.0}

config = load_config()

def transform_item(i):
    neto = i.get('Precio') or i.get('Precio_Neto') or 0
    p = float(neto) * (1 + config.get('iva', 0)) * (1 + config.get('markup', 0))
    c = i.get('Articulo_Corto') or i.get('Articulo')
    m_raw = str(i.get('Moneda', '')).strip().upper()
    m = '$' if m_raw in ['PES', 'ARS'] else ('U' if m_raw in ['DOL', 'USD'] else m_raw)
    return {
        'producto': c,
        'detalle': i.get('Descripcion'),
        'marca': i.get('Familia', '').strip(),
        'unidad': i.get('Unidad'),
        'moneda': m,
        'precio': '{:.2f}'.format(p)
    }

if __name__ == '__main__':
    api_client = BertualAPIClient()
    api_data = api_client.fetch_products()
    if not api_data: sys.exit(1)
    
    new_items = [transform_item(i) for i in api_data]
    fecha_str = datetime.now().strftime('%y-%m-%d')
    fn = 'data/lista_precio_' + fecha_str + '_json_compres.gz'
    
    os.makedirs(DATA_DIR, exist_ok=True)
    with gzip.open(os.path.join(BASE_DIR, fn), 'wt', encoding='utf-8') as f: 
        json.dump(new_items, f, ensure_ascii=False)
    
    with open(LATEST_INDEX_FILE, 'w') as f: f.write(fn)
    with open(LATEST_INDEX_FILE_JSON, 'w') as f: json.dump({'filename': fn}, f)
