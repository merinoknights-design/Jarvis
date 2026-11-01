"""
Ejecutor de recetas de pieza (JRV-10, con JRV-14: material y propiedades). 2026-10-30.

Claude lee el plano y escribe una receta JSON en MILÍMETROS; este script la construye en Solid Edge en modo
ordenado, operación por operación, verificando cada una, y se detiene SIN GUARDAR al primer fallo.

Uso:  python -X utf8 receta_pieza.py <receta.json> [--cerrar]
      (o por la API de agentes: accion "receta", script "agente\\receta_pieza.py", args [ruta_json])
La última línea de la salida es  @@RESULTADO@@ {json}.

Formato de la receta (ejemplos probados en C:\\Jarvis\\pruebas\\recetas\\):
{
  "nombre": "Brida", "salida": "C:\\...\\Brida.par",
  "material": "Acero",                                  (opcional; nombre de la tabla de materiales)
  "propiedades": {"Title": "...", "Author": "...", "DocumentNumber": "...", "ProjectName": "..."},
  "esperado": {"caja_mm": [120, 120, 40], "volumen_mm3": 123.4, "tolerancia_mm": 0.5},   (opcional)
  "operaciones": [ {...}, ... ]
}
Operaciones (todas las cotas en mm; ángulos en grados):
  {"tipo": "protrusion", "plano": "xy|yz|xz", "perfil": [elementos], "distancia": 15, "direccion": "normal|inversa|simetrica"}
  {"tipo": "corte", "plano": ..., "perfil": [...], "pasante": true}            o  "profundidad": 5
  {"tipo": "revolucion", "plano": ..., "perfil": [... con {"eje": [x1,y1,x2,y2]}], "angulo": 360}
  {"tipo": "corte_revolucion", "plano": ..., "perfil": [... con "eje"], "angulo": 360}
  {"tipo": "redondeo", "radio": 2, "aristas": {selector}}
  {"tipo": "chaflan", "distancia": 1, "aristas": {selector}}
  {"tipo": "agujero", "plano": ..., "centros": [[x,y], ...], "diametro": 8 | "rosca": "M6", "pasante": true | "profundidad": 12}
  {"tipo": "patron", "de": "nombre de otra operación", "plano": ...,
     "circular": {"cantidad": 6, "centro": [0,0], "angulo": 360}   o   "rectangular": {"cantidad_x": 3, "cantidad_y": 2, "paso_x": 20, "paso_y": 60}}
Elementos de perfil (cada uno es un contorno cerrado; se dibujan en sentido antihorario):
  {"rect": [cx, cy, ancho, alto]}      {"circulo": [cx, cy, diametro]}      {"poligono": [[x,y], ...]}
  {"circulos_en_circulo": {"centro": [cx,cy], "diametro_pcd": 90, "n": 6, "diametro": 10, "angulo0": 0}}
  {"contorno": [{"linea": [x1,y1,x2,y2]}, {"arco": [cx,cy, x1,y1, x2,y2]}, ...]}   (arcos antihorarios)
  {"eje": [x1,y1,x2,y2]}               (solo para revoluciones)
Selector de aristas (se combinan con Y):
  {"en_plano": {"eje": "z", "valor": 40 | "max" | "min"}}   aristas contenidas en ese plano
  {"circulares": true}   aristas cerradas (círculos)      {"rectas": true}   aristas no cerradas
  {"paralelas_a": "z"}   aristas rectas paralelas a un eje
"""
import json
import math
import sys
import time
from pathlib import Path

import pythoncom

sys.path.insert(0, r"C:\Jarvis")
import se_com_seguro as se  # noqa: E402
import rutas_se  # noqa: E402
from cad_atomic_lib import (FEATURE_OK, FEATURE_WARNED, PROFILE_CLOSED, PROFILE_REF_AXIS_REQUIRED,  # noqa: E402
                            SE_LEFT, SE_RIGHT, SE_SYMMETRIC, add_arc_by_center, add_line, add_sketch_profile,
                            bounding_box_mm, close_profile_keypoints)

MARCA = "@@RESULTADO@@"
MM = 0.001
PLANOS = {"xy": 1, "superior": 1, "planta": 1, "yz": 2, "derecho": 2, "derecha": 2, "xz": 3, "frontal": 3, "alzado": 3}
PERFIL_ANIDADO = 8192  # igProfileAllowNested: agujeros dentro de un contorno en el mismo boceto
DIRECCION = {"normal": SE_RIGHT, "inversa": SE_LEFT, "simetrica": SE_SYMMETRIC}
EJES = {"x": 0, "y": 1, "z": 2}


class Parada(RuntimeError):
    pass


# ---------------------------------------------------------------- perfiles
def _area_firmada(pts):
    return 0.5 * sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1]
                     for i in range(len(pts)))


def _centroide(pts):
    a = _area_firmada(pts)
    cx = sum((pts[i][0] + pts[(i + 1) % len(pts)][0]) * (pts[i][0] * pts[(i + 1) % len(pts)][1] -
             pts[(i + 1) % len(pts)][0] * pts[i][1]) for i in range(len(pts))) / (6 * a)
    cy = sum((pts[i][1] + pts[(i + 1) % len(pts)][1]) * (pts[i][0] * pts[(i + 1) % len(pts)][1] -
             pts[(i + 1) % len(pts)][0] * pts[i][1]) for i in range(len(pts))) / (6 * a)
    return cx, cy


def _poligono(prof, pts, acotar_lados=0):
    """Polígono cerrado en sentido antihorario. Devuelve (área mm², centroide mm).
    acotar_lados = cuántos lados reciben cota de longitud (un rectángulo: 2, ancho y alto)."""
    if _area_firmada(pts) < 0:
        pts = list(reversed(pts))
    ls = [add_line(prof, pts[i][0] * MM, pts[i][1] * MM, pts[(i + 1) % len(pts)][0] * MM,
                   pts[(i + 1) % len(pts)][1] * MM) for i in range(len(pts))]
    close_profile_keypoints(prof, ls)
    for l in ls[:acotar_lados]:
        _acotar(prof.Dimensions.AddLength, l)
    return abs(_area_firmada(pts)), _centroide(pts)


def _circulo(prof, cx, cy, d, acotar=True):
    c = se.reintentar(prof.Circles2d.AddByCenterRadius, cx * MM, cy * MM, d / 2 * MM)
    if acotar:   # cota Ø en el boceto: el plano la recupera con RetrieveDimensions
        _acotar(prof.Dimensions.AddCircularDiameter, c)
    return math.pi * (d / 2) ** 2, (cx, cy)


def _acotar(metodo, elemento):
    try:
        cota = metodo(elemento)
        cota.Constraint = True   # cota que GOBIERNA: así editar_pieza.py puede cambiarla y la geometría la sigue
    except Exception:
        pass   # una cota que no se puede poner no impide el modelo; el plano mostrará menos cotas


def _contorno(prof, tramos):
    """Cadena de líneas y arcos (antihorarios). Área exacta: polígono de extremos + segmentos circulares."""
    elems, vertices, extra = [], [], 0.0
    for t in tramos:
        if "linea" in t:
            x1, y1, x2, y2 = t["linea"]
            elems.append(add_line(prof, x1 * MM, y1 * MM, x2 * MM, y2 * MM))
            vertices.append((x1, y1))
        elif "arco" in t:
            cx, cy, x1, y1, x2, y2 = t["arco"]
            elems.append(add_arc_by_center(prof, cx * MM, cy * MM, x1 * MM, y1 * MM, x2 * MM, y2 * MM))
            r = math.hypot(x1 - cx, y1 - cy)
            th = (math.atan2(y2 - cy, x2 - cx) - math.atan2(y1 - cy, x1 - cx)) % (2 * math.pi)
            extra += r * r / 2 * (th - math.sin(th))
            vertices.append((x1, y1))
        else:
            raise Parada("Tramo de contorno desconocido: %s" % t)
    close_profile_keypoints(prof, elems)
    area = abs(_area_firmada(vertices)) + extra
    return area, _centroide(vertices)


def dibujar_perfil(doc, plano, elementos):
    """Devuelve (perfil, lista de (área mm², centroide mm), línea de eje o None)."""
    if plano not in PLANOS:
        raise Parada("Plano desconocido '%s' (use xy, yz o xz)" % plano)
    _, prof = add_sketch_profile(doc, PLANOS[plano])
    regiones, eje = [], None
    for e in elementos:
        if "rect" in e:
            cx, cy, w, h = e["rect"]
            regiones.append(_poligono(prof, [(cx - w / 2, cy - h / 2), (cx + w / 2, cy - h / 2),
                                             (cx + w / 2, cy + h / 2), (cx - w / 2, cy + h / 2)], acotar_lados=2))
        elif "circulo" in e:
            regiones.append(_circulo(prof, *e["circulo"]))
        elif "poligono" in e:
            regiones.append(_poligono(prof, [tuple(p) for p in e["poligono"]]))
        elif "circulos_en_circulo" in e:
            c = e["circulos_en_circulo"]
            cx, cy = c["centro"]
            for k in range(int(c["n"])):
                a = math.radians(c.get("angulo0", 0) + 360.0 * k / int(c["n"]))
                regiones.append(_circulo(prof, cx + c["diametro_pcd"] / 2 * math.cos(a),
                                         cy + c["diametro_pcd"] / 2 * math.sin(a), c["diametro"], acotar=(k == 0)))
        elif "contorno" in e:
            regiones.append(_contorno(prof, e["contorno"]))
        elif "eje" in e:
            x1, y1, x2, y2 = e["eje"]
            eje = add_line(prof, x1 * MM, y1 * MM, x2 * MM, y2 * MM)
        else:
            raise Parada("Elemento de perfil desconocido: %s" % e)
    return prof, regiones, eje


def _extremos(linea):
    try:
        a = [x for x in se._aplanar(linea.GetStartPoint(0.0, 0.0)) if isinstance(x, float)]
        b = [x for x in se._aplanar(linea.GetEndPoint(0.0, 0.0)) if isinstance(x, float)]
        return (a[0] / MM, a[1] / MM), (b[0] / MM, b[1] / MM)
    except Exception:
        return None


def acotar_revolucion(prof, eje, eje_pts):
    """En un perfil de revolución, cada tramo paralelo al eje (y fuera de él) recibe su Ø simétrico respecto del eje y
    su longitud, como cotas que gobiernan: así el plano de un eje sale con Ø30, Ø20, 40, 60…  Devuelve cuántas puso."""
    (ax1, ay1), (ax2, ay2) = eje_pts
    largo_eje = math.hypot(ax2 - ax1, ay2 - ay1)
    ux, uy = (ax2 - ax1) / largo_eje, (ay2 - ay1) / largo_eje
    mx_eje, my_eje = (ax1 + ax2) / 2, (ay1 + ay2) / 2
    puestas = 0
    for i in range(1, prof.Lines2d.Count + 1):
        linea = prof.Lines2d.Item(i)
        ext = _extremos(linea)
        if not ext:
            continue
        (x1, y1), (x2, y2) = ext
        L = math.hypot(x2 - x1, y2 - y1)
        if L < 1e-6 or abs((x2 - x1) * uy - (y2 - y1) * ux) / L > 1e-6:
            continue                                            # no es paralela al eje
        if abs((x1 - ax1) * uy - (y1 - ay1) * ux) < 1e-6:
            continue                                            # está sobre el eje (o es el eje)
        diametro = 2 * abs((x1 - ax1) * uy - (y1 - ay1) * ux)
        pe, pl = (mx_eje * MM, my_eje * MM, 0.0), ((x1 + x2) / 2 * MM, (y1 + y2) / 2 * MM, 0.0)
        # Ø simétrico: el orden de los argumentos no está documentado y uno de ellos dio "Ø200" en un eje de Ø30
        # (2026-10-31). Se prueba y se comprueba el valor contra el diámetro real; si no coincide, se borra.
        for o1, p1, o2, p2 in ((linea, pl, eje, pe), (eje, pe, linea, pl)):
            try:
                c = prof.Dimensions.AddSymmetricalDiameter(o1, *p1, True, o2, *p2, True)   # keyPoint=True (con False da 0)
                if abs(c.Value / MM - diametro) < 0.01:
                    c.Constraint = True
                    puestas += 1
                    break
                c.Delete()
            except Exception:
                pass
        try:
            c = prof.Dimensions.AddLength(linea)
            c.Constraint = True
            puestas += 1
        except Exception:
            pass
    return puestas


def cerrar_perfil(prof, validacion):
    st = prof.End(validacion | PERFIL_ANIDADO)
    if st not in (0, None):
        raise Parada("El perfil no es válido (Profile.End devolvió %s): revise que cada contorno esté cerrado." % st)
    prof.Visible = False


# ---------------------------------------------------------------- operaciones
def volumen_mm3(model):
    return float(model.Body.Volume) * 1e9 if model is not None else 0.0


def estado_ok(feat, nombre):
    st = feat.Status
    if st not in (FEATURE_OK, FEATURE_WARNED):
        raise Parada("La operación '%s' falló (estado %s)." % (nombre, st))
    return "ok" if st == FEATURE_OK else "aviso"


def _extension_mm(model):
    caja = bounding_box_mm(model.Body) if model is not None else None
    return max(caja.values()) if caja else 1000.0


def op_protrusion(doc, model, op, n):
    prof, reg, _ = dibujar_perfil(doc, op["plano"], op["perfil"])
    cerrar_perfil(prof, PROFILE_CLOSED)
    antes = volumen_mm3(model)
    lado = DIRECCION.get(op.get("direccion", "normal"))
    if lado is None:
        raise Parada("direccion debe ser normal, inversa o simetrica")
    nuevo = se.reintentar(doc.Models.AddFiniteExtrudedProtrusion, 1, [prof], lado, float(op["distancia"]) * MM)
    model = model or nuevo
    feat = model.Features.Item(model.Features.Count)
    est = estado_ok(feat, n)
    agregado = volumen_mm3(model) - antes
    if agregado <= 1e-6:
        raise Parada("'%s' no añadió material (¿perfil dentro de la pieza o dirección equivocada?)." % n)
    return model, {"estado": est, "volumen_agregado_mm3": round(agregado, 1)}


def op_corte(doc, model, op, n):
    if model is None:
        raise Parada("'%s': no hay cuerpo que cortar todavía." % n)
    area = None
    pasante = bool(op.get("pasante"))
    prof_d = None if pasante else float(op["profundidad"])
    intentos = ([(SE_LEFT, SE_SYMMETRIC)] if pasante else [(SE_LEFT, SE_RIGHT), (SE_LEFT, SE_LEFT)])
    ultimo = ""
    for perfil_lado, plano_lado in intentos:
        prof, reg, _ = dibujar_perfil(doc, op["plano"], op["perfil"])
        cerrar_perfil(prof, PROFILE_CLOSED)
        area = sum(a for a, _ in reg)
        antes = volumen_mm3(model)
        prof_m = (2.5 * _extension_mm(model) if pasante else prof_d) * MM
        feat = se.reintentar(model.ExtrudedCutouts.AddFinite, prof, perfil_lado, plano_lado, prof_m)
        quitado = antes - volumen_mm3(model)
        maximo = area * (prof_m / MM) * 1.02 + 1.0
        if feat.Status in (FEATURE_OK, FEATURE_WARNED) and 1e-6 < quitado <= maximo:
            return model, {"estado": estado_ok(feat, n), "volumen_quitado_mm3": round(quitado, 1),
                           "area_perfil_mm2": round(area, 2)}
        ultimo = "quitó %.1f mm³ (máximo posible %.1f), estado %s" % (quitado, maximo, feat.Status)
        se.reintentar(feat.Delete)   # se prueba la otra dirección
    raise Parada("'%s' no cortó lo esperado: %s. ¿Perfil fuera de la pieza?" % (n, ultimo))


TABLA_ROSCAS = str(rutas_se.tabla_roscas())   # tabla de roscas de la instalación: nominal; menor interno; …; designación
AGUJERO_SIMPLE = 33                           # igRegularHole
ROSCA_NORMAL = 164                            # igRegularThread


def datos_rosca(designacion):
    """(diámetro nominal, diámetro menor interno) en mm para una designación de HOLES.TXT ('M6', 'M6 x 0.75'…)."""
    for linea in open(TABLA_ROSCAS, encoding="latin-1"):
        p = [x.strip() for x in linea.split(";")]
        if len(p) >= 4 and p[3].replace(" ", "").lower() == designacion.replace(" ", "").lower():
            return float(p[0]), float(p[1])
    raise Parada("La rosca '%s' no está en %s" % (designacion, TABLA_ROSCAS))


def op_agujero(doc, model, op, n):
    """Agujeros con la operación Agujero de Solid Edge (no cortes): simples ("diametro") o roscados ("rosca": "M6").
    Un agujero por centro: con varios centros en un mismo boceto, Solid Edge 2026 solo hace el primero (2026-10-31).
    El roscado se mecaniza al diámetro MENOR de la tabla de roscas y guarda la designación (M6…) en el agujero.
    (Asignar HoleType=igTappedHole lo convierte en 'escalonado' y ThreadDataByDescription no lee la tabla.)"""
    if model is None:
        raise Parada("'%s': no hay cuerpo que agujerear todavía." % n)
    M = pythoncom.Missing
    if op.get("rosca"):
        nom, menor = datos_rosca(op["rosca"])
        diam = menor
    else:
        diam, nom, menor = float(op["diametro"]), None, None
    pasante = bool(op.get("pasante"))
    quitado_total, hechos = 0.0, 0
    for k, (x, y) in enumerate(op["centros"], 1):
        hd = doc.HoleDataCollection.Add(AGUJERO_SIMPLE, diam * MM, M, M, M, M, M, M, M, M, M, M, M, M, M, M, M, M, M, M, True)
        if nom:
            hd.ThreadSetting = ROSCA_NORMAL
            hd.ThreadNominalDiameter = nom * MM
            hd.ThreadMinorDiameter = menor * MM
            hd.ThreadDescription = op["rosca"]
        hecho = False
        for lado in (SE_RIGHT, SE_LEFT):
            _, prof = add_sketch_profile(doc, PLANOS[op["plano"]])
            prof.Holes2d.Add(x * MM, y * MM)
            prof.End(0)
            prof.Visible = False
            antes = volumen_mm3(model)
            if pasante:
                feat = se.reintentar(model.Holes.AddThroughAll, prof, lado, hd)
            else:
                feat = se.reintentar(model.Holes.AddFinite, prof, lado, float(op["profundidad"]) * MM, hd)
            quitado = antes - volumen_mm3(model)
            maximo = math.pi * (diam / 2) ** 2 * (2.5 * _extension_mm(model) if pasante else float(op["profundidad"])) * 1.02 + 1
            if feat.Status in (FEATURE_OK, FEATURE_WARNED) and 1e-6 < quitado <= maximo:
                quitado_total += quitado
                hechos += 1
                hecho = True
                break
            se.reintentar(feat.Delete)
        if not hecho:
            raise Parada("'%s': el agujero %d en (%s, %s) no quitó material (¿centro fuera de la pieza?)." % (n, k, x, y))
    info = {"estado": "ok", "agujeros": hechos, "diametro_mm": round(diam, 3), "volumen_quitado_mm3": round(quitado_total, 1)}
    if nom:
        info.update(rosca=op["rosca"], nominal_mm=nom, menor_mm=menor)
    return model, info


def op_patron(doc, model, op, n, creadas):
    """Patrón de operación (JRV-16): repite las operaciones creadas por la operación "de".
    Circular: {"circular": {"cantidad": 6, "centro": [x, y], "angulo_total": 360}}  (probado en el plano xy)
    Rectangular: {"rectangular": {"cantidad_x": 3, "cantidad_y": 2, "paso_x": 20, "paso_y": 15}}"""
    origen = creadas.get(op["de"])
    if not origen:
        raise Parada("'%s': no hay operación previa llamada '%s' (use su campo 'nombre')." % (n, op["de"]))
    plano = doc.RefPlanes.Item(PLANOS[op.get("plano", "xy")])
    antes = volumen_mm3(model)
    if "circular" in op:
        c = op["circular"]
        k = int(c["cantidad"])
        total = math.radians(float(c.get("angulo_total", 360)))
        cx, cy = c.get("centro", [0, 0])
        feat = se.reintentar(model.Patterns.AddByCircular, len(origen), origen, plano, k, total, [cx * MM, cy * MM, 0.0],
                             0, 1, total < 2 * math.pi - 1e-9)       # 0 = ajustar las k copias al ángulo total
    elif "rectangular" in op:
        r = op["rectangular"]
        k = int(r["cantidad_x"]) * int(r["cantidad_y"])
        feat = se.reintentar(model.Patterns.AddByRectangular, len(origen), origen, plano, int(r["cantidad_x"]),
                             int(r["cantidad_y"]), float(r["paso_x"]) * MM, float(r["paso_y"]) * MM, 0.0, 2, 0)
    else:
        raise Parada("'%s': indique 'circular' o 'rectangular'." % n)
    est = estado_ok(feat, n)
    cambio = volumen_mm3(model) - antes
    return model, {"estado": est, "copias": k, "cambio_volumen_mm3": round(cambio, 1)}


def _volumen_revolucion(regiones, eje_pts):
    """Pappus: Σ área × 2π × distancia del centroide al eje (todo en mm)."""
    (x1, y1), (x2, y2) = eje_pts
    L = math.hypot(x2 - x1, y2 - y1)
    total = 0.0
    for area, (cx, cy) in regiones:
        d = abs((x2 - x1) * (y1 - cy) - (x1 - cx) * (y2 - y1)) / L
        total += area * 2 * math.pi * d
    return total


def op_revolucion(doc, model, op, n, corte=False):
    prof, reg, eje = dibujar_perfil(doc, op["plano"], op["perfil"])
    if eje is None:
        raise Parada("'%s': falta el elemento {\"eje\": [x1,y1,x2,y2]} en el perfil." % n)
    x1, y1, x2, y2 = next(e["eje"] for e in op["perfil"] if "eje" in e)
    eje_pts = [(x1, y1), (x2, y2)]
    ref = se.reintentar(prof.SetAxisOfRevolution, eje)
    cotas_puestas = acotar_revolucion(prof, eje, eje_pts) if not corte else 0
    cerrar_perfil(prof, PROFILE_CLOSED | PROFILE_REF_AXIS_REQUIRED)
    ang = math.radians(float(op.get("angulo", 360)))
    teorico = _volumen_revolucion(reg, eje_pts) * ang / (2 * math.pi)
    antes = volumen_mm3(model)
    if not corte:
        nuevo = se.reintentar(doc.Models.AddFiniteRevolvedProtrusion, 1, [prof], ref, SE_RIGHT, ang)
        model = model or nuevo
        feat = model.Features.Item(model.Features.Count)
        est = estado_ok(feat, n)
        cambio = volumen_mm3(model) - antes
        if cambio <= 1e-6:
            raise Parada("'%s' no añadió material." % n)
        return model, {"estado": est, "volumen_agregado_mm3": round(cambio, 1), "volumen_teorico_mm3": round(teorico, 1),
                       "cotas_en_boceto": cotas_puestas}
    if model is None:
        raise Parada("'%s': no hay cuerpo que cortar todavía." % n)
    feat = se.reintentar(model.RevolvedCutouts.AddFinite, prof, ref, SE_LEFT, SE_RIGHT, ang)
    quitado = antes - volumen_mm3(model)
    if feat.Status not in (FEATURE_OK, FEATURE_WARNED) or quitado <= 1e-6 or quitado > teorico * 1.02 + 1.0:
        raise Parada("'%s' no cortó lo esperado: quitó %.1f mm³ (máximo %.1f), estado %s."
                     % (n, quitado, teorico, feat.Status))
    return model, {"estado": estado_ok(feat, n), "volumen_quitado_mm3": round(quitado, 1),
                   "volumen_teorico_max_mm3": round(teorico, 1)}


def seleccionar_aristas(model, sel):
    caja = None
    edges = model.Body.Edges(1)
    out = []
    for i in range(1, edges.Count + 1):
        e = edges.Item(i)
        r = se._aplanar(e.GetEndPoints([0.0] * 3, [0.0] * 3))
        pts = [x for x in r if isinstance(x, list) and len(x) == 3]
        if len(pts) < 2:
            continue
        p1, p2 = [v / MM for v in pts[0]], [v / MM for v in pts[1]]
        cerrada = bool(e.IsClosed)
        ok = True
        if "en_plano" in sel:
            k = EJES[sel["en_plano"]["eje"]]
            valor = sel["en_plano"]["valor"]
            if valor in ("max", "min"):
                if caja is None:
                    r2 = se._aplanar(model.Body.GetRange([0.0] * 3, [0.0] * 3))
                    caja = [[v / MM for v in x] for x in r2 if isinstance(x, list) and len(x) == 3]
                valor = caja[1][k] if valor == "max" else caja[0][k]
            ok &= abs(p1[k] - valor) < 0.01 and abs(p2[k] - valor) < 0.01
            if cerrada:  # un círculo tiene inicio = fin: comprobar también el punto medio de su rango
                ok &= _arista_en_plano(e, k, valor)
        if sel.get("circulares"):
            ok &= cerrada
        if sel.get("rectas"):
            ok &= not cerrada
        if "paralelas_a" in sel:
            k = EJES[sel["paralelas_a"]]
            d = [p2[j] - p1[j] for j in range(3)]
            ok &= (not cerrada) and all(abs(d[j]) < 0.01 for j in range(3) if j != k) and abs(d[k]) > 0.01
        if ok:
            out.append(e)
    return out


def _arista_en_plano(e, k, valor):
    try:
        r = se._aplanar(e.GetRange([0.0] * 3, [0.0] * 3))
        pts = [x for x in r if isinstance(x, list) and len(x) == 3]
        return abs(pts[0][k] / MM - valor) < 0.01 and abs(pts[1][k] / MM - valor) < 0.01
    except Exception:
        return True


def op_acabado(model, op, n, tipo):
    if model is None:
        raise Parada("'%s': no hay cuerpo todavía." % n)
    aristas = seleccionar_aristas(model, op.get("aristas", {}))
    if not aristas:
        raise Parada("'%s': el selector de aristas no encontró ninguna (%s)." % (n, op.get("aristas")))
    antes = volumen_mm3(model)
    if tipo == "redondeo":
        feat = se.reintentar(model.Rounds.Add, len(aristas), aristas, [float(op["radio"]) * MM] * len(aristas))
    else:
        feat = se.reintentar(model.Chamfers.AddEqualSetback, len(aristas), aristas, float(op["distancia"]) * MM)
    est = estado_ok(feat, n)
    return model, {"estado": est, "aristas": len(aristas), "cambio_volumen_mm3": round(volumen_mm3(model) - antes, 2)}


# ---------------------------------------------------------------- material, propiedades y verificación
def aplicar_material(app, doc, nombre):
    """No detiene la receta: si el nombre no está en la tabla de materiales, lo informa.
    (MatTable.GetMaterialList no funciona desde pywin32: E_NOTIMPL, 2026-10-30.)"""
    try:
        mt = app.GetMaterialTable()
        se.reintentar(mt.ApplyMaterial, doc, nombre)
    except Exception as e:
        return {"aplicado": False, "pedido": nombre, "error": se.describir_error(e)}
    try:
        r = mt.GetCurrentMaterialName(doc)
        actual = r if isinstance(r, str) else next((x for x in se._aplanar(r) if isinstance(x, str)), None)
    except Exception:
        actual = None
    return {"aplicado": True, "pedido": nombre, "actual": actual}


def aplicar_propiedades(doc, props):
    si = doc.SummaryInfo
    hechas = {}
    for k, v in props.items():
        setattr(si, k, str(v))
        hechas[k] = getattr(si, k)
    return hechas


def verificar(model, esperado):
    vol = volumen_mm3(model)
    caja = bounding_box_mm(model.Body)
    res = {"volumen_mm3": round(vol, 2), "caja_mm": caja, "fallos": []}
    tol = float(esperado.get("tolerancia_mm", 0.5))
    if "caja_mm" in esperado and caja:
        medida = sorted(caja.values())
        if any(abs(a - b) > tol for a, b in zip(medida, sorted(esperado["caja_mm"]))):
            res["fallos"].append("caja %s ≠ esperada %s (±%s mm)" % (medida, sorted(esperado["caja_mm"]), tol))
    if "volumen_mm3" in esperado:
        ev = float(esperado["volumen_mm3"])
        if abs(vol - ev) > float(esperado.get("tolerancia_volumen", 0.005)) * ev:
            res["fallos"].append("volumen %.1f ≠ esperado %.1f mm³" % (vol, ev))
    return res


OPERACIONES = {"protrusion": op_protrusion, "corte": op_corte, "agujero": op_agujero}


def construir(receta, cerrar_al_final=False):
    salida = Path(receta["salida"])
    if salida.exists():
        raise Parada("%s ya existe: elija otra 'salida' (no se sobrescribe)." % salida)
    se.guardia_disco()
    bit = se.Bitacora(salida.with_name(salida.stem + "_bitacora.csv"))
    app = se.conectar()
    doc = se.reintentar(app.Documents.Add, "SolidEdge.PartDocument")
    doc.ModelingMode = 2
    model, pasos = None, []
    try:
        creadas = {}   # nombre de la operación de la receta → operaciones de Solid Edge que creó (para los patrones)
        for i, op in enumerate(receta["operaciones"], 1):
            tipo = op["tipo"]
            n = op.get("nombre") or "%d. %s" % (i, tipo)
            n0 = model.Features.Count if model is not None else 0
            if tipo in OPERACIONES:
                model, info = OPERACIONES[tipo](doc, model, op, n)
            elif tipo in ("revolucion", "corte_revolucion"):
                model, info = op_revolucion(doc, model, op, n, corte=(tipo == "corte_revolucion"))
            elif tipo in ("redondeo", "chaflan"):
                model, info = op_acabado(model, op, n, tipo)
            elif tipo == "patron":
                model, info = op_patron(doc, model, op, n, creadas)
            else:
                raise Parada("Tipo de operación desconocido: %s" % tipo)
            creadas[n] = [model.Features.Item(j) for j in range(n0 + 1, model.Features.Count + 1)]
            info["operacion"] = n
            pasos.append(info)
            bit.anotar("pieza", receta.get("nombre", ""), "", n, json.dumps(info, ensure_ascii=False), info["estado"])
            print("  %-34s %s" % (n, info))
        res = {"pasos": pasos}
        if receta.get("material"):
            res["material"] = aplicar_material(app, doc, receta["material"])
        if receta.get("propiedades"):
            res["propiedades"] = aplicar_propiedades(doc, receta["propiedades"])
        ver = verificar(model, receta.get("esperado", {}))
        res["verificacion"] = ver
        if ver["fallos"]:
            raise Parada("Verificación contra el plano: " + "; ".join(ver["fallos"]))
        se.guardar_nuevo(doc, salida)
        bit.anotar("guardar", receta.get("nombre", ""), "", str(salida), "", "ok")
        res.update(ok=True, archivo=str(salida))
        if cerrar_al_final:
            se.reintentar(doc.Close, False)
        return res
    except (Parada, se.ErrorSolidEdge, ValueError) as e:
        bit.anotar("PARADA", receta.get("nombre", ""), "", "", "", "detenido", str(e))
        return {"ok": False, "error": str(e), "pasos": pasos,
                "nota": "No se guardó nada. El documento queda abierto en Solid Edge para revisarlo."}


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    try:
        receta = json.loads(Path(argv[1]).read_text(encoding="utf-8-sig"))
        res = construir(receta, "--cerrar" in argv)
    except Parada as e:
        res = {"ok": False, "error": str(e)}
    except Exception as e:
        res = {"ok": False, "error": se.describir_error(e)}
    print(MARCA, json.dumps(res, ensure_ascii=False, default=str))
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
