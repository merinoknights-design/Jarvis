"""
Fase 0 del Cardán — reconocimiento (NO modifica nada).
Crea un ensamble temporal SIN guardar, inserta una ocurrencia de cada pieza, vuelca
todas sus caras a inspeccion/<pieza>.json y lo cierra sin guardar.
Uso:  C:\\Jarvis\\venv\\Scripts\\python.exe inspeccionar_piezas.py [carpeta_piezas]
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import se_com_seguro as se

PIEZAS = ["soporte fijo", "Fork", "eje central", "Central Cruz", "eje entrada", "Eje de salida1",
          "Perno", "tuercaM3"]
AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
from rutas_cardan import CARPETA_PIEZAS  # JRV-69 (2026-10-28): rutas en un solo sitio
CARPETA = Path(sys.argv[1]) if len(sys.argv) > 1 else CARPETA_PIEZAS


def main():
    faltan = [p for p in PIEZAS if not (CARPETA / (p + ".par")).exists()]
    if faltan:
        raise SystemExit("Faltan piezas en %s: %s" % (CARPETA, faltan))
    salida = AQUI / "inspeccion"
    salida.mkdir(exist_ok=True)
    app = se.conectar()
    asm = se.reintentar(app.Documents.Add, "SolidEdge.AssemblyDocument")
    try:
        for nombre in PIEZAS:
            occ = se.insertar(asm, CARPETA / (nombre + ".par"))
            doc = occ.OccurrenceDocument
            model = doc.Models.Item(1)
            try:
                feats = [model.Features.Item(i).Name for i in range(1, model.Features.Count + 1)]
            except Exception:
                feats = []
            caras = []
            for i, c in enumerate(se.caras(occ), start=1):
                d = se.describir(c)
                d["i"] = i
                d["rango"] = se.rango_cara(c)
                d["pts"] = se.puntos_arista(c)[:6]
                caras.append(d)
            try:
                rb = se._aplanar(model.Body.GetRange([0.0] * 3, [0.0] * 3))
                rango = [x for x in rb if isinstance(x, list)]
            except Exception:
                rango = None
            info = {"pieza": nombre, "features": feats, "rango_cuerpo": rango,
                    "n_caras": len(caras), "caras": caras}
            (salida / (nombre + ".json")).write_text(json.dumps(info, indent=1), encoding="utf-8")
            tipos = {}
            for c in caras:
                tipos[c["tipo"]] = tipos.get(c["tipo"], 0) + 1
            print("%-15s caras=%4d %s features=%s" % (nombre, len(caras), tipos, feats))
    finally:
        asm.Close(False)
        print("Ensamble temporal cerrado SIN guardar.")


if __name__ == "__main__":
    main()
