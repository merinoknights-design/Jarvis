"""
Pseudo-explosión de un ensamble en una COPIA (JRV-40, alternativa B). 2026-10-30.

Por qué no la explosión de Solid Edge: AssemblyDocument.AutoExplode existe en la API de SE 2026, pero desde
Python (enlace dinámico o temprano) devuelve DISP_E_TYPEMISMATCH con cualquier combinación de argumentos y
StartCommand no cambia al entorno Explosionar-Renderizar-Animar por automatización (2026-10-30). La explosión
"oficial", con líneas de flujo y guardada como configuración, la hace el usuario en la interfaz.

Qué hace: copia el ensamble con otro nombre (el original NO se toca), suprime todas sus relaciones salvo los
Fijar y separa cada pieza del centro del ensamble en proporción a su posición (factor), o a lo largo de un eje.
El resultado es un .asm aparte, útil para una vista de plano o una imagen; no es un mecanismo funcional.

Uso:  python -X utf8 explosion.py <ensamble.asm> <salida.asm> [--factor 1.8] [--eje x|y|z]
Última línea:  @@RESULTADO@@ {json}
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, r"C:\Jarvis")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import se_com_seguro as se  # noqa: E402
import acciones as A  # noqa: E402

MARCA = "@@RESULTADO@@"


def centro(occ):
    r = se._aplanar(occ.GetRangeBox([0.0] * 3, [0.0] * 3))
    pts = [x for x in r if isinstance(x, list) and len(x) == 3]
    return [(a + b) / 2 for a, b in zip(pts[0], pts[1])]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("asm")
    ap.add_argument("salida")
    ap.add_argument("--factor", type=float, default=1.8)
    ap.add_argument("--eje", choices=["x", "y", "z"])
    a = ap.parse_args()
    origen, salida = Path(a.asm), Path(a.salida)
    if salida.exists():
        raise ValueError("%s ya existe: elija otro nombre." % salida)
    se.guardia_disco()
    shutil.copy2(origen, salida)                      # el .asm guarda rutas ABSOLUTAS de las piezas: la copia sigue vinculada
    cfg = origen.with_suffix(".cfg")
    if cfg.exists() and not salida.with_suffix(".cfg").exists():
        shutil.copy2(cfg, salida.with_suffix(".cfg"))
    app = se.conectar()
    doc, mio = A.tomar_documento(app, str(salida))
    try:
        occs = [doc.Occurrences.Item(i) for i in range(1, doc.Occurrences.Count + 1)]
        centros = {o.Name: centro(o) for o in occs}
        c0 = [sum(c[k] for c in centros.values()) / len(centros) for k in range(3)]
        suprimidas = 0
        for i in range(1, doc.Relations3d.Count + 1):
            r = doc.Relations3d.Item(i)
            if r.Type != se.IG_GROUND_REL and not r.Suppress:
                r.Suppress = True
                suprimidas += 1
        movidas = 0
        k_eje = "xyz".index(a.eje) if a.eje else None
        for o in occs:
            if se.es_fija(o):
                continue
            d = [centros[o.Name][k] - c0[k] for k in range(3)]
            if k_eje is not None:
                d = [d[k] if k == k_eje else 0.0 for k in range(3)]
            M = se.matriz(o)
            for k in range(3):
                M[12 + k] += (a.factor - 1.0) * d[k]
            se.reintentar(o.PutMatrix, M, True)
            movidas += 1
        se.reintentar(doc.Save)
        return {"ok": True, "archivo": str(salida), "relaciones_suprimidas": suprimidas, "piezas_separadas": movidas,
                "factor": a.factor, "eje": a.eje or "radial",
                "nota": "Copia explosionada sin relaciones activas: solo para vistas e imágenes."}
    finally:
        if mio:
            A.cerrar(app, doc)


if __name__ == "__main__":
    try:
        res = main()
    except Exception as e:
        res = {"ok": False, "error": str(e) if isinstance(e, ValueError) else se.describir_error(e)}
    print(MARCA, json.dumps(res, ensure_ascii=False, default=str))
    sys.exit(0 if res.get("ok") else 1)
