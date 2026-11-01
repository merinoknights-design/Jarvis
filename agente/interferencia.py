"""
Detección de choques (interferencia) de un ensamble (JRV-24 y JRV-32). 2026-10-31. Nunca guarda.

Cómo funciona: desde Python, CheckInterference falla siempre (DISP_E_TYPEMISMATCH), porque sus parámetros de
salida no se pueden pasar ni con enlace dinámico ni con makepy. Con el interop TIPADO que genera
csharp\\GenerarInterop.exe (TypeLibConverter de .NET, sin instalar nada), el programa csharp\\InterferenciaTipada.exe
la llama como las muestras oficiales de Siemens y escribe el informe de Solid Edge (nombres + volumen).
Este script lo ejecuta, lee el informe y separa:
  - CHOQUES: volumen de interferencia >= umbral (por defecto 1 mm³). Hay que corregirlos.
  - contactos: volumen < umbral. Ruido numérico de caras que se tocan (p. ej. 0,001 mm³ en el Cardán).

Uso:  python -X utf8 interferencia.py <ensamble.asm> [--umbral 1.0] [--ignorar-roscas]
Última línea:  @@RESULTADO@@ {json}
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, r"C:\Jarvis")
import se_com_seguro as se  # noqa: E402

MARCA = "@@RESULTADO@@"
EXE = Path(__file__).resolve().parent / "csharp" / "InterferenciaTipada.exe"
ESTADOS = {1: "sin interferencia", 2: "interferencia confirmada", 3: "interferencia probable",
           4: "confirmada y probable", 5: "análisis incompleto"}


def leer_informe(texto):
    """Pares (pieza_a, pieza_b, volumen_mm3) de la sección 'Interferencias:' del informe de Solid Edge."""
    pares = []
    if "Interferencias:" not in texto:
        return pares
    bloque = texto.split("Interferencias:", 1)[1]
    for m in re.finditer(r"\d+ de \d+\s*\n\s*(.+?)\s*\n\s*(.+?)\s*\n\s*Volumen de Interferencias\s+([\d.,]+)", bloque):
        pares.append((m.group(1).strip(), m.group(2).strip(), float(m.group(3).replace(".", "").replace(",", "."))
                      if m.group(3).count(",") == 1 and m.group(3).count(".") >= 1 else float(m.group(3).replace(",", "."))))
    return pares


def pieza(nombre_ocurrencia):
    return nombre_ocurrencia.rsplit(":", 1)[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("asm")
    ap.add_argument("--umbral", type=float, default=1.0, help="mm³ a partir de los cuales es un choque real")
    ap.add_argument("--ignorar-roscas", action="store_true")
    ap.add_argument("--esperado", action="append", default=[],
                    help='par de piezas cuyo solape es esperado, p. ej. "Perno.par<>tuercaM3.par" (ajuste de rosca)')
    a = ap.parse_args()
    esperados = {" <> ".join(sorted(p.strip() for p in e.split("<>"))) for e in a.esperado}
    ruta = Path(a.asm).resolve()
    antes = se.sha256(ruta)
    se.conectar()                                     # el programa en C# se engancha a una instancia abierta
    informe = Path(tempfile.mkdtemp(prefix="jarvis_interf_")) / "informe.txt"
    args = [str(EXE), str(ruta), "--informe", str(informe)] + (["--ignorar-roscas"] if a.ignorar_roscas else [])
    r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800,
                       creationflags=subprocess.CREATE_NO_WINDOW)
    linea = next((l for l in reversed(r.stdout.splitlines()) if l.startswith(MARCA)), None)
    if not linea:
        return {"ok": False, "error": "El programa de interferencia no respondió: " + (r.stdout + r.stderr)[-400:]}
    base = json.loads(linea[len(MARCA):])
    if not base.get("ok"):
        return base
    pares = leer_informe(informe.read_text(encoding="utf-8", errors="replace")) if informe.exists() else []
    choques, contactos, aceptados = defaultdict(list), defaultdict(list), defaultdict(list)
    for p1, p2, vol in pares:
        clave = " <> ".join(sorted([pieza(p1), pieza(p2)]))
        destino = contactos if vol < a.umbral else (aceptados if clave in esperados else choques)
        destino[clave].append({"a": p1, "b": p2, "volumen_mm3": vol})
    res = {
        "ok": True,
        "estado_solid_edge": ESTADOS.get(base["codigo_estado"], base["codigo_estado"]),
        "umbral_mm3": a.umbral,
        "ignorando_roscas": a.ignorar_roscas,
        "total_interferencias": len(pares),
        "choques": {k: {"cantidad": len(v), "volumen_max_mm3": max(x["volumen_mm3"] for x in v), "ejemplos": v[:5]}
                    for k, v in sorted(choques.items())},
        "contactos": {k: {"cantidad": len(v), "volumen_max_mm3": max(x["volumen_mm3"] for x in v)}
                      for k, v in sorted(contactos.items())},
        "esperados_aceptados": {k: {"cantidad": len(v), "volumen_max_mm3": max(x["volumen_mm3"] for x in v)}
                                for k, v in sorted(aceptados.items())},
        "veredicto": ("SIN CHOQUES REALES" if not choques else "%d choque(s) real(es) en %d par(es) de piezas"
                      % (sum(len(v) for v in choques.values()), len(choques))),
        "archivo_sin_cambios": se.sha256(ruta) == antes,
    }
    return res


if __name__ == "__main__":
    try:
        res = main()
    except Exception as e:
        res = {"ok": False, "error": se.describir_error(e)}
    print(MARCA, json.dumps(res, ensure_ascii=False, default=str))
    sys.exit(0 if res.get("ok") else 1)
