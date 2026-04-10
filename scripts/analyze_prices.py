#!/usr/bin/env python3
import json
import gzip
import os
import csv
from datetime import datetime
from collections import Counter

# Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")

# Specific files for the big analysis (Sept 2025 vs Today)
OLD_FILE = os.path.join(DATA_DIR, "lista_precio_23-09-25_json_compres.gz")
# We'll try to find the newest 2026 file
NEW_FILE = os.path.join(DATA_DIR, f"lista_precio_{datetime.now().strftime('%y-%m-%d')}_json_compres.gz")

def load_gz_json(filename):
    if not os.path.exists(filename):
        print(f"File {filename} not found.")
        return []
    with gzip.open(filename, "rt", encoding="utf-8") as f:
        return json.load(f)

def run_analysis():
    print(f"Analyzing changes between {os.path.basename(OLD_FILE)} and {os.path.basename(NEW_FILE)}...")
    
    old_list = load_gz_json(OLD_FILE)
    new_list = load_gz_json(NEW_FILE)
    
    if not old_list or not new_list:
        print("Data missing for analysis.")
        return

    old_data = {p["producto"]: p for p in old_list}
    new_data = {p["producto"]: p for p in new_list}
    
    matches = []
    for code, new_item in new_data.items():
        if code in old_data:
            old_item = old_data[code]
            try:
                old_p = float(old_item["precio"])
                new_p = float(new_item["precio"])
                if old_p > 0:
                    percent_change = (new_p - old_p) / old_p * 100
                    matches.append({
                        "code": code,
                        "desc": new_item["detalle"],
                        "brand": new_item.get("marca", "Sin Marca"),
                        "old": old_p,
                        "new": new_p,
                        "change": percent_change
                    })
            except: continue

    if not matches:
        print("No products matched for analysis.")
        return

    total_matched = len(matches)
    all_changes = [m["change"] for m in matches]
    avg_increase = sum(all_changes) / total_matched
    rounded_changes = [round(c, 1) for c in all_changes]
    rate_counts = Counter(rounded_changes)
    top_rates = rate_counts.most_common(5)
    
    brand_stats = {}
    for m in matches:
        b = m["brand"]
        if b not in brand_stats: brand_stats[b] = []
        brand_stats[b].append(m["change"])
    
    brand_summary = sorted([{"brand": b, "avg_increase": sum(c)/len(c), "count": len(c)} for b, c in brand_stats.items()], key=lambda x: x["avg_increase"], reverse=True)

    timestamp = datetime.now().strftime("%Y-%m-%d")
    md_file = os.path.join(REPORTS_DIR, f"analisis_precios_{timestamp}.md")
    csv_file = os.path.join(REPORTS_DIR, f"analisis_precios_detallado_{timestamp}.csv")
    
    os.makedirs(REPORTS_DIR, exist_ok=True)
    
    print(f"Generating reports in {REPORTS_DIR}...")
    with open(md_file, "w") as f:
        f.write("# Análisis Estadístico de Cambio de Precios\n")
        f.write(f"**Periodo:** Septiembre 2025 ➔ {datetime.now().strftime('%B %Y')}\n\n")
        f.write(f"## 📊 Resumen Ejecutivo\n- **Productos Analizados:** {total_matched}\n- **Aumento Promedio Global:** {avg_increase:.2f}%\n- **Tasa más común:** {top_rates[0][0]:.1f}% ({top_rates[0][1]} productos)\n\n")
        f.write("## 🏷️ Aumento Promedio por Marca (Top 20)\n| Marca | Aumento | Cantidad |\n| --- | --- | --- |\n")
        for b in brand_summary[:20]:
            f.write(f"| {b['brand']} | {b['avg_increase']:.2f}% | {b['count']} |\n")

    with open(csv_file, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["Codigo", "Descripcion", "Marca", "Precio Viejo", "Precio Nuevo", "Cambio Pesos", "Cambio Porcentaje"])
        for m in sorted(matches, key=lambda x: x["change"], reverse=True):
            writer.writerow([m["code"], m["desc"], m["brand"], f"{m['old']:.2f}", f"{m['new']:.2f}", f"{(m['new']-m['old']):.2f}", f"{m['change']:.2f}%"])

    print(f"Success. Analysis reports saved to {REPORTS_DIR}")

if __name__ == "__main__":
    run_analysis()
