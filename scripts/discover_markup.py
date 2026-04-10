import json
import gzip
import os

OLD_FILE = "data/lista_precio_23-09-25_json_compres.gz"
NEW_FILE = "data/lista_precio_26-04-10_json_compres.gz"

def load_gz_json(filename):
    with gzip.open(filename, "rt", encoding="utf-8") as f:
        return json.load(f)

old_data = {p["producto"]: p for p in load_gz_json(OLD_FILE)}
new_data = {p["producto"]: p for p in load_gz_json(NEW_FILE)}

ratios = []
for code, old_item in old_data.items():
    if code in new_data:
        old_p = float(old_item["precio"])
        new_p = float(new_data[code]["precio"])
        if new_p > 0:
            ratios.append(old_p / new_p)

if ratios:
    avg_ratio = sum(ratios) / len(ratios)
    print(f"Average Ratio (Old/NewNeto): {avg_ratio:.4f}")
    # Show most common ratios
    from collections import Counter
    counts = Counter([round(r, 2) for r in ratios])
    print("Top 5 Ratios:", counts.most_common(5))
else:
    print("No matches found.")
