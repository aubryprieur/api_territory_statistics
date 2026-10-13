"""
Prépare les contours IRIS simplifiés à partir de l'export OpenDataSoft « georef-france-iris » (IGN / Insee,
découpage 2024, GeoJSON France entière, ~1,2 Go).

Source  : data/geography/iris/georef-france-iris.geojson
Sortie  : data/geography/iris/iris_geometries_2024.csv.gz
          (iris_code, com_code, com_parent, iris_name, iris_type, label_lon, label_lat = point intérieur pour
          l'étiquette, geometry = GeoJSON simplifié, WGS84, 5 décimales)

Lecture en flux (ijson) pour ne pas charger le fichier en mémoire ; simplification de Douglas-Peucker (shapely)
à ~10 m, suffisante pour une carte à l'échelle d'une commune. Les arrondissements de Paris, Lyon et Marseille
gardent leur code (com_code = 75101…) et le code de la commune entière (com_parent = 75056…).

Nécessite : pip install ijson shapely (une fois, hors venv de l'API si besoin). Le fichier produit est ensuite
importé par scripts/import_iris_geometries.py, qui n'a besoin que de pandas / psycopg2.

Usage :
    python scripts/build_iris_geometries.py
    # par tranches (environnement limité en durée), puis concaténation :
    python scripts/build_iris_geometries.py --start 0 --end 12500 --output part1.csv.gz
"""
import argparse
import csv
import gzip
import json
import logging
import ijson
from shapely.geometry import mapping, shape

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

SOURCE = "data/geography/iris/georef-france-iris.geojson"
OUTPUT = "data/geography/iris/iris_geometries_2024.csv.gz"
TOLERANCE = 0.0001  # degrés ≈ 7 à 11 m
ARM_PARENT = {"751": "75056", "693": "69123", "132": "13055"}


def first(v):
    return v[0] if isinstance(v, list) else v


def rounded(coords, nd=5):
    if isinstance(coords[0], (int, float)):
        return [round(coords[0], nd), round(coords[1], nd)]
    return [rounded(c, nd) for c in coords]


def main(source=SOURCE, output=OUTPUT, start=0, end=None, header=True):
    n = points_in = points_out = 0
    seen = set()
    index = -1
    with open(source, "rb") as f, gzip.open(output, "wt", newline="", encoding="utf-8") as out:
        w = csv.writer(out)
        if header:
            w.writerow(["iris_code", "com_code", "com_parent", "iris_name", "iris_type", "label_lon", "label_lat", "geometry"])
        for feat in ijson.items(f, "features.item", use_float=True):
            index += 1
            if index < start:
                continue
            if end is not None and index >= end:
                break
            p = feat["properties"]
            code = first(p.get("iris_code"))
            if not code or code in seen or not feat.get("geometry"):
                continue
            seen.add(code)
            com = first(p.get("com_arm_code")) or first(p.get("com_code"))
            parent = ARM_PARENT.get(com[:3], com) if com[:3] in ARM_PARENT and com not in ARM_PARENT.values() else com
            geom = shape(feat["geometry"])
            simple = geom.simplify(TOLERANCE, preserve_topology=True)
            if simple.is_empty:
                simple = geom
            gj = mapping(simple)
            gj = {"type": gj["type"], "coordinates": rounded(json.loads(json.dumps(gj["coordinates"])))}
            points_in += len(json.dumps(feat["geometry"]["coordinates"]))
            text = json.dumps(gj, separators=(",", ":"))
            points_out += len(text)
            label = geom.representative_point()  # point intérieur pour l'étiquette de la carte
            w.writerow([code, com, parent, first(p.get("iris_name")), first(p.get("iris_type")),
                        round(label.x, 5), round(label.y, 5), text])
            n += 1
            if n % 10000 == 0:
                logger.info(f"   {n:,} IRIS")
    logger.info(f"✅ {n:,} IRIS écrits dans {output} ; taille des géométries {points_in / 1e6:,.0f} Mo → {points_out / 1e6:,.1f} Mo")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", default=SOURCE)
    parser.add_argument("--output", default=OUTPUT)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--end", type=int, default=None)
    args = parser.parse_args()
    main(args.source, args.output, args.start, args.end, header=args.start == 0)
