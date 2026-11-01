"""
Barrido de choques durante el giro de un mecanismo (JRV-32). 2026-11-01. Nunca guarda.

Una verificación de interferencia vale solo para la pose en que está el ensamble: en un mecanismo, una pieza puede
rozar a otra solo en parte de la vuelta. Esto gira la pieza motriz por pasos (PutMatrix, la técnica de motor.py), corre
el comando de interferencia de Solid Edge en cada posición (sobre la pose en memoria) y agrupa lo que encuentra en
tramos: qué pareja de piezas se toca, desde qué ángulo hasta cuál y dónde está el máximo.

Reglas:
  - Si el ensamble ya está abierto en Solid Edge, no lo toca: mover piezas cambiaría lo que el usuario está viendo.
  - Se detiene si una relación deja de estar resuelta o si la pieza motriz deja de girar, y entrega lo que alcanzó a medir.
  - Si el comando de interferencia falla en una posición, se detiene: un fallo no puede leerse como "sin choques".

Uso:
  python -X utf8 barrido_choques.py <ensamble.asm> --pieza "eje entrada.par:1" [--diametro 14] [--grados 360] [--cada 5]
         [--paso 30] [--umbral 1.0] [--aviso 0.2] [--esperado "Perno.par<>tuercaM3.par"] [--informe salida.json]
  --diametro: cilindro de la pieza motriz que define el eje de giro (por defecto, el de mayor área).
  --cada:     grados de la pieza motriz entre verificaciones. Con 5 se mide en cada paso que concede el solver (7-9° por
              paso en el Cardán, unos 5 min la vuelta, 6 s por verificación). Medir menos pierde el máximo: cada 8° dio
              33 posiciones y un pico de 1,97 mm³ donde hay 2,10; a 36°, 0,96 donde hay 2,15. Los valores y ángulos son
              los de las posiciones medidas: para afinar un tramo, baja --paso (el solver concede menos en cada uno).
  --umbral:   mm³ desde los que una pareja cuenta como choque. --aviso: mm³ desde los que se registra como roce.
  --esperado: pareja de PIEZAS cuyo solape es normal (rosca modelada); se cuenta aparte.
  --informe:  JSON con todas las posiciones (no sobrescribe: si existe, usa otro nombre).
Los ángulos son el giro acumulado de la pieza motriz desde la pose guardada.
Última línea:  @@RESULTADO@@ {json}
"""
import argparse
import json
import math
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, r"C:\Jarvis")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import se_com_seguro as se  # noqa: E402
import acciones as A  # noqa: E402
import interferencia as I  # noqa: E402
import motor as Mo  # noqa: E402

MARCA = "@@RESULTADO@@"
SIN_GIRO_GRADOS = 0.05     # por debajo, el paso no movió la pieza
PASOS_SIN_GIRO = 5
INCOMPLETO = 5             # código de estado de Solid Edge: análisis incompleto


def verificar(ruta, carpeta, k):
    """Interferencia de la pose actual: (código de estado, [(ocurrencia_a, ocurrencia_b, mm3)]).
    Un informe por posición: si no hay interferencias no se escribe, y uno reutilizado traería datos de la anterior."""
    informe = carpeta / ("posicion_%04d.txt" % k)
    r = subprocess.run([str(I.EXE), str(ruta), "--informe", str(informe)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=900, creationflags=subprocess.CREATE_NO_WINDOW)
    linea = next((l for l in reversed(r.stdout.splitlines()) if l.startswith(MARCA)), None)
    if not linea:
        raise RuntimeError("El programa de interferencia no respondió: " + (r.stdout + r.stderr)[-400:])
    base = json.loads(linea[len(MARCA):])
    if not base.get("ok"):
        raise RuntimeError("Interferencia falló: %s" % base.get("error"))
    pares = I.leer_informe(informe.read_text(encoding="utf-8", errors="replace")) if informe.exists() else []
    return base.get("codigo_estado"), pares


def agrupar_tramos(posiciones, aviso, vuelta_completa):
    """Parejas de ocurrencias → tramos de posiciones consecutivas con volumen >= aviso."""
    por_pareja = {}
    for i, p in enumerate(posiciones):
        for a, b, v in p["pares"]:
            if v >= aviso:
                por_pareja.setdefault(tuple(sorted((a, b))), {})[i] = v
    tramos = []
    n = len(posiciones)
    for pareja, vols in por_pareja.items():
        grupos, actual = [], []
        for i in sorted(vols):
            if actual and i != actual[-1] + 1:
                grupos.append(actual)
                actual = []
            actual.append(i)
        grupos.append(actual)
        # La última posición de una vuelta completa es la primera otra vez: el tramo que cruza el inicio es uno solo
        cruza = vuelta_completa and len(grupos) > 1 and grupos[0][0] == 0 and grupos[-1][-1] == n - 1
        if cruza:
            grupos = [grupos[-1] + grupos[0]] + grupos[1:-1]
        for g in grupos:
            pico = max(g, key=lambda i: vols[i])
            tramos.append({"pareja": " <> ".join(pareja), "piezas": " <> ".join(sorted(I.pieza(x) for x in pareja)),
                           "desde_grados": posiciones[g[0]]["giro"], "hasta_grados": posiciones[g[-1]]["giro"],
                           "pico_grados": posiciones[pico]["giro"], "max_mm3": vols[pico], "posiciones": len(g),
                           "constante": len(g) == n})
    return sorted(tramos, key=lambda t: (0 if t["desde_grados"] > t["hasta_grados"] else 1, t["desde_grados"], t["pareja"]))


def resumir(posiciones, a, esperados, detenido):
    vuelta = bool(posiciones) and posiciones[-1]["giro"] >= 359.0
    tramos = agrupar_tramos(posiciones, a.aviso, vuelta)
    choques = [t for t in tramos if t["piezas"] not in esperados and t["max_mm3"] >= a.umbral]
    roces = [t for t in tramos if t["piezas"] not in esperados and t["max_mm3"] < a.umbral]
    aceptados = {}
    for t in tramos:
        if t["piezas"] in esperados:
            e = aceptados.setdefault(t["piezas"], {"parejas": 0, "max_mm3": 0.0})
            e["parejas"] += 1
            e["max_mm3"] = max(e["max_mm3"], t["max_mm3"])
    if detenido:
        veredicto = "INCOMPLETO: " + detenido
    elif choques:
        veredicto = "%d tramo(s) con choque real en %d posiciones" % (len(choques), len(posiciones))
    else:
        veredicto = "SIN CHOQUES REALES en %d posiciones" % len(posiciones)
    return {"giro_total_grados": posiciones[-1]["giro"] if posiciones else 0.0, "verificaciones": len(posiciones),
            "verificaciones_incompletas": sum(1 for p in posiciones if p["estado"] == INCOMPLETO),
            "umbral_mm3": a.umbral, "aviso_mm3": a.aviso, "choques": choques, "roces": roces,
            "esperados_aceptados": aceptados, "veredicto": veredicto}


def barrer(app, doc, ruta, carpeta, a, esperados):
    occ = {doc.Occurrences.Item(i).Name: doc.Occurrences.Item(i) for i in range(1, doc.Occurrences.Count + 1)}
    if a.pieza not in occ:
        raise ValueError("No existe la ocurrencia '%s'. Hay: %s" % (a.pieza, sorted(occ)[:20]))
    mot = occ[a.pieza]
    base_p, eje_p = Mo.eje_de(mot, a.diametro)
    M0 = se.matriz(mot)
    punto, u = se.a_ensamble_punto(M0, base_p), Mo._unit(se.a_ensamble_dir(M0, eje_p))
    se.reintentar(doc.Activate)

    posiciones = []

    def medir(k, giro):
        estado, pares = verificar(ruta, carpeta, k)
        posiciones.append({"giro": round(giro, 1), "estado": estado, "pares": pares})
        reales = sum(1 for p in pares if p[2] >= a.aviso and " <> ".join(sorted(I.pieza(x) for x in p[:2])) not in esperados)
        print("%7.1f°  interferencias %3d · sobre el aviso %d" % (giro, len(pares), reales), flush=True)

    medir(0, 0.0)
    acum = ultimo = 0.0
    Mprev = M0
    k = sin_giro = 0
    detenido = None
    while acum < a.grados:
        k += 1
        if k > a.max_pasos:
            detenido = "se alcanzó el máximo de %d pasos con %.1f° de giro" % (a.max_pasos, acum)
            break
        se.reintentar(mot.PutMatrix, Mo.girar_matriz(Mprev, punto, u, math.radians(a.paso)), True)
        Mk = se.matriz(mot)
        delta = Mo.angulo_alrededor(Mprev, Mk, eje_p, u)
        acum += delta
        Mprev = Mk
        malas = [i for i in range(1, doc.Relations3d.Count + 1) if doc.Relations3d.Item(i).Status != se.REL_SOLVED]
        if malas:
            detenido = "%d relación(es) sin resolver a %.1f° de giro" % (len(malas), acum)
            break
        sin_giro = sin_giro + 1 if abs(delta) < SIN_GIRO_GRADOS else 0
        if sin_giro >= PASOS_SIN_GIRO:
            detenido = "la pieza motriz dejó de girar a %.1f° (¿mecanismo bloqueado o sin grado de libertad?)" % acum
            break
        if acum - ultimo >= a.cada or acum >= a.grados:
            ultimo = acum
            medir(k, acum)
    res = resumir(posiciones, a, esperados, detenido)
    res.update(ok=detenido is None, ensamble=str(ruta), pieza=a.pieza, pasos=k)
    if a.informe:
        salida = se.ruta_libre(Path(a.informe))
        salida.write_text(json.dumps(posiciones, ensure_ascii=False, indent=1), encoding="utf-8")
        res["informe"] = str(salida)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("asm")
    ap.add_argument("--pieza", required=True)
    ap.add_argument("--diametro", type=float)
    ap.add_argument("--grados", type=float, default=360.0)
    ap.add_argument("--cada", type=float, default=5.0)
    ap.add_argument("--paso", type=float, default=30.0, help="giro pedido por paso; el solver concede menos")
    ap.add_argument("--max-pasos", type=int, default=300)
    ap.add_argument("--umbral", type=float, default=1.0)
    ap.add_argument("--aviso", type=float, default=0.2)
    ap.add_argument("--esperado", action="append", default=[])
    ap.add_argument("--informe")
    a = ap.parse_args()

    esperados = {" <> ".join(sorted(p.strip() for p in e.split("<>"))) for e in a.esperado}
    ruta = Path(a.asm).resolve()
    if not ruta.exists():
        raise ValueError("No existe %s" % ruta)
    se.guardia_disco()
    antes = se.sha256(ruta)
    t0 = time.time()
    app = se.conectar()
    doc, mio = A.tomar_documento(app, ruta)
    if not mio:
        raise ValueError("%s ya está abierto en Solid Edge: ciérralo (o pide al usuario que lo cierre) y repite. "
                         "Mover las piezas cambiaría lo que hay en pantalla." % ruta.name)
    carpeta = Path(tempfile.mkdtemp(prefix="jarvis_barrido_"))
    try:
        res = barrer(app, doc, ruta, carpeta, a, esperados)
    finally:
        A.cerrar(app, doc)     # SIN guardar: el archivo no cambia
        shutil.rmtree(carpeta, ignore_errors=True)
    res["original_sin_cambios"] = se.sha256(ruta) == antes
    res["duracion_s"] = round(time.time() - t0, 1)
    return res


if __name__ == "__main__":
    try:
        res = main()
    except Exception as e:
        res = {"ok": False, "error": str(e) if isinstance(e, (ValueError, RuntimeError)) else se.describir_error(e)}
    print(MARCA, json.dumps(res, ensure_ascii=False, default=str))
    sys.exit(0 if res.get("ok") else 1)
