"""
PLANTILLA de receta de pieza para Jarvis (canal B). Cópiala, cambia `construir()` y `ESPERADO`, y ejecútala.

Demostración incluida: bloque 60 × 40 × 10 mm con un agujero pasante de Ø10 en el centro.

Uso:
  C:\\Jarvis\\venv\\Scripts\\python.exe -X utf8 plantilla_pieza.py --salida <ruta_nueva.par> [--cerrar]

Qué garantiza:
  - Modo ORDENADO, unidades internas en METROS (mm / 1000).
  - Tras cada operación comprueba su estado REAL (igFeatureOK); si falla, se detiene SIN guardar.
  - Verifica volumen y caja envolvente contra lo esperado (tolerancia del plano).
  - Guarda solo en una ruta que no existe (nunca sobrescribe) y anota todo en una bitácora CSV.
"""
import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, r"C:\Jarvis")
import se_com_seguro as se  # noqa: E402
from cad_atomic_lib import add_line, close_profile_keypoints  # noqa: E402

# Constantes verificadas en la type library de SE 2026 (constant.tlb)
IG_LEFT, IG_RIGHT, IG_SYMMETRIC = 1, 2, 3
IG_PROFILE_CLOSED = 1
FEATURE_OK, FEATURE_FAILED, FEATURE_WARNED, FEATURE_SUPPRESSED, FEATURE_ROLLEDBACK = (
    1216476310, 1216476311, 1216476312, 1216476313, 1216476314)
NOMBRE_ESTADO = {FEATURE_OK: "OK", FEATURE_FAILED: "FALLÓ", FEATURE_WARNED: "AVISO",
                 FEATURE_SUPPRESSED: "SUPRIMIDA", FEATURE_ROLLEDBACK: "RETROCEDIDA"}
MODO_ORDENADO = 2
PLANO_XY, PLANO_YZ, PLANO_XZ = 1, 2, 3   # doc.RefPlanes.Item(n): Superior, Derecho, Frontal

mm = 0.001
TOL_MM = 0.5            # tolerancia general del plano
TOL_VOL = 0.005         # 0,5 % de volumen

# Lo que debe medir la pieza terminada (sale de la hoja de cotas del plano).
ESPERADO = {
    "caja_mm": (60.0, 40.0, 10.0),                         # tamaños ordenados de mayor a menor no importan: se comparan ordenados
    "volumen_mm3": 60 * 40 * 10 - math.pi * 5 ** 2 * 10,
}


class Parada(RuntimeError):
    pass


def boceto(doc, plano):
    ps = se.reintentar(doc.ProfileSets.Add)
    return se.reintentar(ps.Profiles.Add, doc.RefPlanes.Item(plano))


def cerrar_boceto(prof):
    estado = prof.End(IG_PROFILE_CLOSED)
    if estado not in (0, None):
        raise Parada("El boceto no es un perfil cerrado válido (End devolvió %s)" % estado)
    prof.Visible = False


def rectangulo(prof, cx, cy, w, h):
    x0, x1, y0, y1 = cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2
    ls = [add_line(prof, x0, y0, x1, y0), add_line(prof, x1, y0, x1, y1),
          add_line(prof, x1, y1, x0, y1), add_line(prof, x0, y1, x0, y0)]
    close_profile_keypoints(prof, ls)
    return ls


def comprobar(feat, nombre, bit):
    st = feat.Status
    txt = NOMBRE_ESTADO.get(st, str(st))
    bit.anotar("pieza", "", "", nombre, "", txt)
    print("  %-28s %s" % (nombre, txt))
    if st != FEATURE_OK:
        raise Parada("La operación '%s' quedó en estado %s" % (nombre, txt))


def construir(doc, bit):
    """Secuencia de operaciones. Cambia SOLO esto (y ESPERADO) para una pieza nueva."""
    # 1. Forma base: rectángulo 60 × 40 en el plano superior, protrusión 10 mm
    prof = boceto(doc, PLANO_XY)
    rectangulo(prof, 0, 0, 60 * mm, 40 * mm)
    cerrar_boceto(prof)
    model = se.reintentar(doc.Models.AddFiniteExtrudedProtrusion, 1, [prof], IG_RIGHT, 10 * mm)
    comprobar(model.ExtrudedProtrusions.Item(1), "Protrusión base", bit)

    # 2. Agujero pasante Ø10 en el centro (corte simétrico, más largo que la pieza).
    #    ProfileSide = IG_LEFT quita el INTERIOR del círculo. Con IG_RIGHT quita el exterior y deja solo el
    #    cilindro, con Status OK (verificado el 2026-10-28): por eso se comprueba el volumen quitado.
    prof = boceto(doc, PLANO_XY)
    se.reintentar(prof.Circles2d.AddByCenterRadius, 0.0, 0.0, 5 * mm)
    cerrar_boceto(prof)
    antes = float(model.Body.Volume) * 1e9
    corte = se.reintentar(model.ExtrudedCutouts.AddFinite, prof, IG_LEFT, IG_SYMMETRIC, 30 * mm)
    comprobar(corte, "Agujero pasante Ø10", bit)
    comprobar_quitado(model, antes, math.pi * 5 ** 2 * 10, "Agujero pasante Ø10", bit)
    return model


def comprobar_quitado(model, antes_mm3, esperado_mm3, nombre, bit):
    """Un corte con Status OK puede haber quitado el lado equivocado: se mide cuánto volumen quitó."""
    quitado = antes_mm3 - float(model.Body.Volume) * 1e9
    ok = abs(quitado - esperado_mm3) <= TOL_VOL * max(esperado_mm3, 1.0) + 1.0
    bit.anotar("pieza", "", "", nombre + " (volumen quitado)", "", "ok" if ok else "fallo",
               "%.1f mm³ (esperado %.1f)" % (quitado, esperado_mm3))
    if not ok:
        raise Parada("'%s' quitó %.1f mm³ y debía quitar %.1f mm³ (¿lado del perfil invertido?)"
                     % (nombre, quitado, esperado_mm3))


def medir(model):
    body = model.Body
    vol_mm3 = float(body.Volume) * 1e9
    r = se._aplanar(body.GetRange([0.0] * 3, [0.0] * 3))       # ¡leer el RETORNO, no las listas pasadas!
    pts = [x for x in r if isinstance(x, list) and len(x) == 3]
    caja = tuple(round(abs(pts[1][i] - pts[0][i]) / mm, 3) for i in range(3)) if len(pts) >= 2 else None
    return vol_mm3, caja


def verificar(model, bit):
    vol, caja = medir(model)
    fallos = []
    if caja is None:
        fallos.append("no se pudo leer la caja envolvente")
    elif any(abs(a - b) > TOL_MM for a, b in zip(sorted(caja), sorted(ESPERADO["caja_mm"]))):
        fallos.append("caja %s mm ≠ esperada %s mm" % (caja, ESPERADO["caja_mm"]))
    if abs(vol - ESPERADO["volumen_mm3"]) > TOL_VOL * ESPERADO["volumen_mm3"]:
        fallos.append("volumen %.1f mm³ ≠ esperado %.1f mm³" % (vol, ESPERADO["volumen_mm3"]))
    print("  caja %s mm · volumen %.1f mm³ (esperado %.1f)" % (caja, vol, ESPERADO["volumen_mm3"]))
    bit.anotar("verificación", "", "", "caja/volumen", "", "ok" if not fallos else "fallo", "; ".join(fallos))
    if fallos:
        raise Parada("Verificación contra el plano: " + "; ".join(fallos))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", required=True, help="ruta .par NUEVA (no se sobrescribe nada)")
    ap.add_argument("--cerrar", action="store_true", help="cerrar el documento al terminar")
    a = ap.parse_args()
    salida = Path(a.salida)
    if salida.exists():
        print("PARADA: %s ya existe; elija otra ruta." % salida)
        return 2
    bit = se.Bitacora(salida.with_name(salida.stem + "_bitacora.csv"))
    app = se.conectar()
    doc = se.reintentar(app.Documents.Add, "SolidEdge.PartDocument")
    try:
        doc.ModelingMode = MODO_ORDENADO
        print("Construyendo %s" % salida.name)
        model = construir(doc, bit)
        verificar(model, bit)
        se.guardar_nuevo(doc, salida)
        bit.anotar("guardar", "", "", str(salida), "", "ok")
        print("OK: guardado en %s" % salida)
        return 0
    except (Parada, se.ErrorSolidEdge) as e:
        bit.anotar("PARADA", "", "", "", "", "detenido", str(e))
        print("PARADA: %s\nNo se guardó nada. El documento queda abierto para revisarlo." % e)
        return 1
    finally:
        if a.cerrar and not doc.Dirty:
            doc.Close(False)


if __name__ == "__main__":
    sys.exit(main())
