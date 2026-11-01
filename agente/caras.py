"""
Caras de una pieza: descripción y selección por reglas geométricas (JRV-20, 2026-10-30).

Todas las medidas en MILÍMETROS y en coordenadas de la PIEZA. Nunca por índice de cara: los índices cambian si
alguien edita la pieza.

Selector de cara (dict):
  {"plano": {"normal": "+z" | "-x" | [nx, ny, nz], "en": 40, "contiene": [x, y, z]}}
        normal EXTERIOR de la cara; "en" = coordenada a lo largo del eje de la normal (solo con "+x"…"-z");
        "contiene" = un punto que debe estar en el plano.
  {"cilindro": {"diametro": 30, "eje": "z" | [ax, ay, az], "cerca_de": [x, y, z]}}
Si varias caras cumplen, se elige la más cercana a "cerca_de" o, si no se indica, la de mayor área.
"""
import math

import se_com_seguro as se

MM = 0.001
EJES = {"x": [1, 0, 0], "y": [0, 1, 0], "z": [0, 0, 1]}
TOL_MM = 0.02


def _unit(v):
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def normal_exterior(cara):
    """La de GetPlaneData puede ir al revés; GetNormal en el centro paramétrico da la exterior."""
    u0, u1 = cara.GetParamRange([0.0] * 2, [0.0] * 2)
    r = cara.GetNormal(1, [(u0[0] + u1[0]) / 2, (u0[1] + u1[1]) / 2])
    return _unit(list(r[1]))


def describir_caras(caras):
    """Lista de dicts en mm: índice (1..n), tipo, área y geometría."""
    out = []
    for i, c in enumerate(caras, 1):
        d = se.describir(c)
        fila = {"i": i, "tipo": d["tipo"], "area_mm2": round(d["area"] * 1e6, 2)}
        if d["tipo"] == "plano":
            n = normal_exterior(c)
            fila["normal"] = [round(x, 4) for x in n]
            fila["punto"] = [round(x / MM, 3) for x in d["raiz"]]
            fila["distancia_origen_mm"] = round(_dot(n, d["raiz"]) / MM, 3)
        elif d["tipo"] in ("cilindro", "cono"):
            fila["eje"] = [round(x, 4) for x in d["eje"]]
            fila["base"] = [round(x / MM, 3) for x in d["base"]]
            fila["diametro_mm"] = round(2 * d["radio"] / MM, 3)
        r = se.rango_cara(c)
        if r:
            fila["centro_mm"] = [round((a + b) / 2 / MM, 3) for a, b in zip(r[0], r[1])]
        out.append(fila)
    return out


def _vector(v):
    if isinstance(v, str):
        signo = -1 if v.startswith("-") else 1
        return [signo * x for x in EJES[v.lstrip("+-")]]
    return _unit(v)


def elegir(caras, sel):
    """Devuelve (índice 1..n, cara) que cumple el selector; lanza ValueError si ninguna o es ambiguo sin desempate."""
    desc = describir_caras(caras)
    candidatos = []
    if "plano" in sel:
        s = sel["plano"]
        n_obj = _vector(s["normal"]) if "normal" in s else None
        for f in desc:
            if f["tipo"] != "plano":
                continue
            if n_obj and _dot(n_obj, f["normal"]) < 0.9995:
                continue
            if "en" in s and isinstance(s.get("normal"), str):
                k = "xyz".index(s["normal"].lstrip("+-"))
                if abs(f["punto"][k] - float(s["en"])) > TOL_MM:
                    continue
            if "contiene" in s:
                d = abs(_dot(f["normal"], [p - q for p, q in zip(s["contiene"], f["punto"])]))
                if d > TOL_MM:
                    continue
            candidatos.append(f)
        cerca = s.get("cerca_de")
    elif "cilindro" in sel:
        s = sel["cilindro"]
        for f in desc:
            if f["tipo"] != "cilindro":
                continue
            if "diametro" in s and abs(f["diametro_mm"] - float(s["diametro"])) > TOL_MM:
                continue
            if "eje" in s and abs(_dot(_vector(s["eje"]), f["eje"])) < 0.9995:
                continue
            candidatos.append(f)
        cerca = s.get("cerca_de")
    else:
        raise ValueError("Selector de cara desconocido: %s" % sel)
    if not candidatos:
        raise ValueError("Ninguna cara cumple %s" % sel)
    if cerca:
        def dist(f):
            if f["tipo"] == "cilindro":  # distancia del punto a la recta del eje
                v = [p - q for p, q in zip(cerca, f["base"])]
                t = _dot(v, f["eje"])
                return math.sqrt(max(_dot(v, v) - t * t, 0.0))
            return math.dist(cerca, f.get("centro_mm", f["punto"]))
        elegido = min(candidatos, key=dist)
    else:
        elegido = max(candidatos, key=lambda f: f["area_mm2"])
    return elegido["i"], caras[elegido["i"] - 1], elegido
