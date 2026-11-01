"""
Inventario de tornillería y agujeros de un ensamble (JRV-15, parte de revisión). 2026-10-31. Nunca guarda.

Para no tener que revisar pieza por pieza cuando hay muchos tornillos, tuercas o agujeros distintos:
  - Por cada pieza distinta: cuántas veces aparece en el ensamble.
  - Tornillería (por nombre: perno, tornillo, tuerca, arandela, espárrago, pasador… o bolt/screw/nut/washer/pin):
    designación métrica DEDUCIDA de su geometría comparando con la tabla de roscas de la instalación
    (Preferences\\HOLES.TXT): un perno por su diámetro exterior (nominal), una tuerca por su agujero
    (diámetro menor o nominal); y su largo (lado mayor de la caja).
  - Agujeros con operación Agujero (diámetro y rosca guardada, p. ej. "M6") y roscas de cada pieza.
  - Cilindros de cada pieza agrupados por diámetro (para piezas importadas sin historial, como las del Cardán).
Una designación deducida es una SUGERENCIA para revisar, no una certeza (p. ej. un pasador liso de Ø3 sale "M3?").

Uso:  python -X utf8 tornilleria.py <ensamble.asm>
Última línea:  @@RESULTADO@@ {json}
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, r"C:\Jarvis")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import se_com_seguro as se  # noqa: E402
import acciones as A  # noqa: E402
import rutas_se  # noqa: E402
from cad_atomic_lib import bounding_box_mm  # noqa: E402

MARCA = "@@RESULTADO@@"
MM = 0.001
TABLA = str(rutas_se.tabla_roscas())
PATRONES = [("perno", r"perno|tornillo|bolt|screw|esp[aá]rrago|stud"), ("tuerca", r"tuerca|nut"),
            ("arandela", r"arandela|washer"), ("pasador", r"pasador|\bpin\b|chaveta|remache|rivet")]


def roscas_metricas():
    """[(nominal, menor, designación)] de la sección métrica gruesa (familia 'M') de HOLES.TXT."""
    out, metrica = [], False
    for linea in open(TABLA, encoding="latin-1"):
        t = linea.strip()
        if t.startswith("BeginMetric"):
            metrica = True
        elif t.startswith("EndMetric"):
            metrica = False
        elif metrica and not t.startswith("\\"):
            p = [x.strip() for x in t.split(";")]
            if len(p) >= 5 and p[4] == "M":
                out.append((float(p[0]), float(p[1]), p[3]))
    return out


def deducir(tipo, cilindros, tabla):
    """Designación probable a partir de los diámetros de cilindros (mm)."""
    if not cilindros:
        return None
    candidatos = []
    for d in cilindros:
        for nom, menor, des in tabla:
            if tipo == "tuerca":
                err = min(abs(d - menor), abs(d - nom))
            else:
                err = abs(d - nom)
            candidatos.append((err, des, d))
    err, des, d = min(candidatos)
    return {"designacion": des + ("?" if err > 0.15 else ""), "diametro_medido_mm": round(d, 3), "diferencia_mm": round(err, 3)}


def analizar_pieza(doc_pieza, tabla, nombre):
    tipo = next((t for t, pat in PATRONES if re.search(pat, nombre, re.I)), "pieza")
    model = doc_pieza.Models.Item(1)
    cil, area = [], Counter()
    fs = model.Body.Faces(1)
    for i in range(1, fs.Count + 1):
        d = se.describir(fs.Item(i))
        if d["tipo"] == "cilindro":
            diam = round(2 * d["radio"] / MM, 3)
            cil.append(diam)
            area[diam] += d["area"]
    agujeros = []
    try:
        for i in range(1, model.Holes.Count + 1):
            hd = model.Holes.Item(i).HoleData
            agujeros.append((hd.ThreadDescription or "Ø%.3f" % (hd.HoleDiameter / MM)))
    except Exception:
        pass
    roscas = []
    try:
        for i in range(1, model.Threads.Count + 1):
            roscas.append(model.Threads.Item(i).HoleData.ThreadDescription or "rosca")
    except Exception:
        pass
    caja = bounding_box_mm(model.Body)
    fila = {"tipo": tipo, "largo_mm": round(max(caja.values()), 2) if caja else None,
            "agujeros": dict(Counter(agujeros)), "roscas": dict(Counter(roscas)),
            "cilindros_por_diametro": dict(Counter(cil).most_common(8))}
    if tipo in ("perno", "tuerca", "arandela", "pasador"):
        base = cil
        if tipo == "perno" and cil:      # el vástago es el diámetro de MAYOR ÁREA (no el más repetido: la cabeza tiene detalles)
            base = [area.most_common(1)[0][0]]
        fila["sugerencia"] = deducir(tipo, base, tabla)
    return fila


def main(ruta):
    tabla = roscas_metricas()
    app = se.conectar()
    asm, mio = A.tomar_documento(app, ruta)
    try:
        por_archivo = Counter()
        docs = {}
        for i in range(1, asm.Occurrences.Count + 1):
            o = asm.Occurrences.Item(i)
            nombre = Path(o.OccurrenceFileName).name
            por_archivo[nombre] += 1
            if nombre not in docs:
                docs[nombre] = o.OccurrenceDocument
        piezas = {}
        for nombre, n in sorted(por_archivo.items()):
            fila = analizar_pieza(docs[nombre], tabla, nombre)
            fila["cantidad"] = n
            piezas[nombre] = fila
        resumen = Counter()
        for nombre, f in piezas.items():
            if f["tipo"] != "pieza":
                des = (f.get("sugerencia") or {}).get("designacion", "?")
                resumen["%s %s" % (f["tipo"], des)] += f["cantidad"]
            for des, k in f["agujeros"].items():
                resumen["agujero %s (en %s)" % (des, nombre)] += k * f["cantidad"]
        return {"ok": True, "ensamble": str(ruta), "ocurrencias": asm.Occurrences.Count, "piezas": piezas,
                "resumen_tornilleria": dict(resumen)}
    finally:
        if mio:
            A.cerrar(app, asm)


if __name__ == "__main__":
    try:
        res = main(sys.argv[1])
    except Exception as e:
        res = {"ok": False, "error": se.describir_error(e)}
    print(MARCA, json.dumps(res, ensure_ascii=False, default=str))
    sys.exit(0 if res.get("ok") else 1)
