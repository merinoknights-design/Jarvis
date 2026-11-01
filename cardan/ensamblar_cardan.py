"""
Ensamble del Cardán (doble junta universal) en Solid Edge 2026 — por fases, con paradas.

Uso (Python de Windows de Jarvis):
    C:\\Jarvis\\venv\\Scripts\\python.exe ensamblar_cardan.py --fase N [--asm RUTA] [--piezas DIR]

    Fase 1  Base: soporte fijo (Fijar) -> eje entrada (A) -> Fork1 (B). Guarda Cardan.asm (ruta nueva).
    Fase 2  Primera junta: Cruz1 (C) -> Fork2 (C, otro brazo) -> eje central (B con Fork2).
    Fase 3  Segunda junta y cierre: Fork3 (B, en fase) -> Cruz2 (C) -> Fork4 (C)
            -> Eje de salida1 (B) -> cierre SOLO con Alinear eje contra el agujero superior.
    Fase 4  Tornillería: 10 pernos + 10 tuercas por brida (receta D), plan B por script.
    Fase 5  Verificación final (conteo, fijos, estados, huellas de los .par) y guardado.

Cómo elige caras (CONTEXTO §6.3): nunca por índice. Reglas geométricas:
  brida     = >=8 agujeros pequeños paralelos con centros en una circunferencia; caras de la
              brida = planos perpendiculares en los extremos de esos agujeros (la de mayor
              área es la de apoyo); centrado = cilindro de mayor radio coaxial en la brida.
  horquilla = agujeros de oreja: cilindros perpendiculares al eje cuya línea corta el eje.
  cruz      = dos líneas de cilindros perpendiculares que se cortan; pasador = el que llega
              más lejos; punta = plano perpendicular en ese extremo.
Cada pieza se PREPOSICIONA en su pose objetivo (calculada de la geometría; el cierre del
lazo se resuelve analíticamente) y luego se relaciona. Antes de crear una relación se
comprueba que sus caras sean coaxiales/coplanares en esa pose; después, que la pieza no
se haya movido. Si algo no cuadra: PARADA con mensaje claro, sin guardar.
Unidades: metros y radianes.
"""
import argparse
import json
import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import se_com_seguro as se  # noqa: E402

PLANO = {"soporte fijo": 1, "Fork": 4, "eje central": 1, "Central Cruz": 2, "eje entrada": 1,
         "Eje de salida1": 1, "Perno": 40, "tuercaM3": 40}
from rutas_cardan import ASM as ASM_DEFECTO, CARPETA_PIEZAS  # JRV-69 (2026-10-28): rutas en un solo sitio
AQUI = Path(__file__).resolve().parent

TOL_L = 2e-5      # 0.02 mm: coaxial / coplanar
TOL_DIR = 1e-6    # paralelismo (1 - |cos|)
TOL_MOV = 5e-5    # 0.05 mm: movimiento máximo admitido tras relacionar
TOL_ROT = 2e-4    # ~0.01°: giro máximo admitido tras relacionar (elementos de la matriz)


class Parada(Exception):
    """Condición de parada (CONTEXTO §7): se informa y no se sigue a ciegas."""


# =============================================================== vectores / matrices
def dot(a, b): return sum(x * y for x, y in zip(a, b))
def add(a, b): return [x + y for x, y in zip(a, b)]
def sub(a, b): return [x - y for x, y in zip(a, b)]
def mul(a, s): return [x * s for x in a]
def norm(a): return math.sqrt(dot(a, a))
def unit(a): n = norm(a); return [x / n for x in a]
def cross(a, b): return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]
def paralelos(a, b): return 1 - abs(dot(unit(a), unit(b))) < TOL_DIR
def mm(v): return [round(x * 1000, 3) for x in v]


def perp(v, d):
    """Componente de v perpendicular a d (d unitario)."""
    return sub(v, mul(d, dot(v, d)))


def rot_eje(eje, ang):
    """Matriz 3x3 (filas) de giro ang alrededor del eje unitario (Rodrigues)."""
    x, y, z = unit(eje)
    c, s, C = math.cos(ang), math.sin(ang), 1 - math.cos(ang)
    return [[c + x * x * C, x * y * C - z * s, x * z * C + y * s],
            [y * x * C + z * s, c + y * y * C, y * z * C - x * s],
            [z * x * C - y * s, z * y * C + x * s, c + z * z * C]]


def rot_minima(a, b):
    """Giro mínimo que lleva la dirección a a la b."""
    a, b = unit(a), unit(b)
    c = dot(a, b)
    ax = cross(a, b)
    if norm(ax) < 1e-12:
        if c > 0:
            return [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
        otro = [1, 0, 0] if abs(a[0]) < 0.9 else [0, 1, 0]
        return rot_eje(unit(cross(a, otro)), math.pi)
    return rot_eje(unit(ax), math.atan2(norm(ax), c))


def mat_por(A, B): return [[sum(A[i][k] * B[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
def mat_vec(A, v): return [sum(A[i][k] * v[k] for k in range(3)) for i in range(3)]
def trasp(A): return [[A[j][i] for j in range(3)] for i in range(3)]


def base_a_base(a1, b1, a2, b2):
    """Giro que lleva el par ortonormal (a1,b1) al (a2,b2)."""
    c1, c2 = cross(a1, b1), cross(a2, b2)
    F1 = trasp([unit(a1), unit(b1), unit(c1)])   # columnas
    F2 = trasp([unit(a2), unit(b2), unit(c2)])
    return mat_por(F2, trasp(F1))


class Pose:
    """Transformación pieza -> ensamble: p_asm = R p + t."""

    def __init__(self, R, t):
        self.R, self.t = R, list(t)

    @staticmethod
    def de_matriz(M):
        return Pose([[M[4 * j + i] for j in range(3)] for i in range(3)], M[12:15])

    def matriz(self):
        R, t = self.R, self.t
        return [R[0][0], R[1][0], R[2][0], 0.0, R[0][1], R[1][1], R[2][1], 0.0,
                R[0][2], R[1][2], R[2][2], 0.0, t[0], t[1], t[2], 1.0]

    def p(self, v): return add(mat_vec(self.R, v), self.t)
    def d(self, v): return mat_vec(self.R, v)

    def inv_p(self, v): return mat_vec(trasp(self.R), sub(v, self.t))

    def girar_en_torno(self, punto, eje, ang):
        """Pose resultante de girar esta pose ang alrededor de la recta (punto, eje)."""
        G = rot_eje(eje, ang)
        return Pose(mat_por(G, self.R), add(mat_vec(G, sub(self.t, punto)), punto))

    def diferencia(self, otra):
        dt = norm(sub(self.t, otra.t))
        dr = max(abs(self.R[i][j] - otra.R[i][j]) for i in range(3) for j in range(3))
        return dt, dr


def pose_por_marcos(p_local, a_local, b_local, p_obj, a_obj, b_obj):
    """Pose que lleva el punto p_local a p_obj y el marco (a,b) local al objetivo."""
    R = base_a_base(a_local, b_local, a_obj, b_obj)
    return Pose(R, sub(p_obj, mat_vec(R, p_local)))


# ======================================================================= geometría
class Geo:
    """Caras clasificadas de un archivo de pieza (coordenadas de PIEZA). Una por archivo."""
    _cache = {}

    @classmethod
    def de(cls, occ):
        clave = Path(occ.OccurrenceFileName).stem
        if clave not in cls._cache:
            cls._cache[clave] = Geo(occ, clave)
        return cls._cache[clave]

    def __init__(self, occ, nombre):
        self.nombre = nombre
        self.caras = se.caras(occ)
        self.d = []
        for i, c in enumerate(self.caras, start=1):
            info = se.describir(c)
            info["i"] = i
            self.d.append(info)
        self._ext = {}
        self._rng = {}
        self._nrm = {}

    def tipo(self, t): return [x for x in self.d if x["tipo"] == t]

    def puntos(self, i):
        if i not in self._ext:
            self._ext[i] = se.puntos_arista(self.caras[i - 1])
        return self._ext[i]

    def rango(self, i):
        if i not in self._rng:
            self._rng[i] = se.rango_cara(self.caras[i - 1])
        return self._rng[i]

    def normal_ext(self, i):
        """Normal EXTERIOR de una cara plana (la de GetPlaneData puede ir al revés)."""
        if i not in self._nrm:
            f = self.caras[i - 1]
            u0, u1 = f.GetParamRange([0.0] * 2, [0.0] * 2)
            r = f.GetNormal(1, [(u0[0] + u1[0]) / 2, (u0[1] + u1[1]) / 2])
            self._nrm[i] = unit(list(r[1]))
        return self._nrm[i]

    def extension(self, i, eje):
        """Intervalo axial (min, max) de una cara a lo largo de 'eje' (por sus aristas)."""
        pts = self.puntos(i)
        if not pts:
            r = self.rango(i)
            pts = r if r else []
        vals = [dot(p, eje) for p in pts]
        return (min(vals), max(vals)) if vals else (None, None)

    def contiene(self, i, p, holgura=1e-5):
        r = self.rango(i)
        if not r:
            return False
        return all(r[0][k] - holgura <= p[k] <= r[1][k] + holgura for k in range(3))

    def planos_perp(self, eje, nivel=None, tol=TOL_L):
        out = []
        for x in self.tipo("plano"):
            if paralelos(x["normal"], eje) and (nivel is None or abs(dot(x["raiz"], eje) - nivel) < tol):
                out.append(x)
        return out

    def cilindros_coaxiales(self, punto, eje, tol=TOL_L):
        return [x for x in self.tipo("cilindro")
                if paralelos(x["eje"], eje) and norm(perp(sub(x["base"], punto), unit(eje))) < tol]

    # ------------------------------------------------------------------ bridas
    def bridas(self):
        if hasattr(self, "_bridas"):
            return self._bridas
        cil = self.tipo("cilindro")
        grupos = {}
        for x in cil:
            for k, g in grupos.items():
                if abs(g[0]["radio"] - x["radio"]) < 1e-7 and paralelos(g[0]["eje"], x["eje"]):
                    g.append(x)
                    break
            else:
                grupos[len(grupos)] = [x]
        bridas = []
        for g in grupos.values():
            if len(g) < 8:
                continue
            d = unit(g[0]["eje"])
            for x in g:
                x["_s"] = sum(self.extension(x["i"], d)) / 2
            g.sort(key=lambda x: x["_s"])
            racimos = [[g[0]]]
            for x in g[1:]:
                (racimos[-1].append(x) if abs(x["_s"] - racimos[-1][-1]["_s"]) < 3e-3 else racimos.append([x]))
            for r in racimos:
                lineas = [perp(x["base"], d) for x in r]
                distintas = []
                for p in lineas:
                    if all(norm(sub(p, q)) > 1e-4 for q in distintas):
                        distintas.append(p)
                if len(distintas) < 8:
                    continue
                c = mul([sum(p[k] for p in distintas) for k in range(3)], 1.0 / len(distintas))
                radios = [norm(sub(p, c)) for p in distintas]
                if max(radios) - min(radios) > 1e-4 or min(radios) < 1e-3:
                    continue
                s0 = min(self.extension(x["i"], d)[0] for x in r)
                s1 = max(self.extension(x["i"], d)[1] for x in r)
                caras0 = sorted(self.planos_perp(d, s0), key=lambda x: -x["area"])
                caras1 = sorted(self.planos_perp(d, s1), key=lambda x: -x["area"])
                if not caras0 or not caras1:
                    raise Parada("%s: brida sin caras planas en los extremos de sus agujeros" % self.nombre)
                f0, f1 = caras0[0], caras1[0]
                apoyo, tras = (f0, f1) if f0["area"] >= f1["area"] else (f1, f0)
                n_apoyo = self.normal_ext(apoyo["i"])
                n_tras = self.normal_ext(tras["i"])
                s_apoyo = dot(apoyo["raiz"], d)
                s_tras = dot(tras["raiz"], d)
                # coherencia: la normal exterior de cada cara apunta lejos de la otra
                if dot(n_apoyo, mul(d, s_apoyo - s_tras)) <= 0 or dot(n_tras, mul(d, s_tras - s_apoyo)) <= 0:
                    raise Parada("%s: caras de brida incoherentes (normales)" % self.nombre)
                centro_apoyo = add(c, mul(d, s_apoyo))
                rim = [x for x in self.cilindros_coaxiales(c, d)
                       if self.extension(x["i"], d)[0] >= s0 - 1e-5 and self.extension(x["i"], d)[1] <= s1 + 1e-5]
                if not rim:
                    raise Parada("%s: brida sin cilindro de centrado coaxial" % self.nombre)
                rim = max(rim, key=lambda x: x["radio"])
                bridas.append({"eje": d, "centro_linea": c, "rbc": radios[0], "agujeros": r,
                               "apoyo": apoyo, "tras": tras, "n_apoyo": n_apoyo, "n_tras": n_tras,
                               "centro_apoyo": centro_apoyo,
                               "centro_tras": add(c, mul(d, s_tras)), "rim": rim})
        self._bridas = bridas
        return bridas

    def brida_unica(self):
        b = self.bridas()
        if len(b) != 1:
            raise Parada("%s: se esperaba 1 brida y hay %d" % (self.nombre, len(b)))
        return b[0]

    # --------------------------------------------------------------- horquilla
    def horquilla(self):
        if hasattr(self, "_horq"):
            return self._horq
        b = self.brida_unica()
        d, c = b["eje"], b["centro_linea"]
        cand = []
        for x in self.tipo("cilindro"):
            e = unit(x["eje"])
            if abs(dot(e, d)) > 1e-6:
                continue
            # punto de corte entre la línea del agujero y el eje principal
            w = sub(x["base"], c)
            n = cross(d, e)
            if abs(dot(w, unit(n))) > TOL_L:
                continue   # no se cortan
            cand.append(x)
        if not cand:
            raise Parada("%s: no se hallaron agujeros de oreja que corten el eje" % self.nombre)
        rmin = min(x["radio"] for x in cand)
        orejas = [x for x in cand if abs(x["radio"] - rmin) < 1e-7]
        e = unit(orejas[0]["eje"])
        # centro de la junta: corte de la línea de orejas con el eje principal
        p0 = orejas[0]["base"]
        n = cross(d, e)
        m = cross(e, n)
        s = dot(sub(p0, c), m) / dot(d, m)
        J = add(c, mul(d, s))
        a_in = mul(b["n_apoyo"], -1.0)          # del apoyo hacia la horquilla
        f_c = dot(sub(J, b["centro_apoyo"]), a_in)
        if f_c <= 0:
            raise Parada("%s: el centro de la junta no está del lado de la horquilla" % self.nombre)
        lados = {}
        for sg in (1, -1):
            hueco = [x for x in orejas if sg * (sum(self.extension(x["i"], e)) / 2 - dot(J, e)) > 0]
            interior = []
            for x in self.planos_perp(e):
                ne = self.normal_ext(x["i"])
                nivel = dot(x["raiz"], e)
                if sg * (nivel - dot(J, e)) <= 0 or dot(ne, sub(J, x["raiz"])) <= 0:
                    continue
                if self.contiene(x["i"], add(J, mul(e, nivel - dot(J, e)))):
                    interior.append(x)
            if len(hueco) != 1 or not interior:
                raise Parada("%s: oreja %+d sin agujero único o sin cara interior" % (self.nombre, sg))
            interior.sort(key=lambda x: abs(dot(x["raiz"], e) - dot(J, e)))
            lados[sg] = {"agujero": hueco[0], "interior": interior[0]}
        self._horq = {"brida": b, "J": J, "e": e, "a_in": a_in, "f_c": f_c, "lados": lados}
        return self._horq

    # -------------------------------------------------------------------- cruz
    def cruz(self):
        if hasattr(self, "_cruz"):
            return self._cruz
        lineas = []
        for x in self.tipo("cilindro"):
            e = unit(x["eje"])
            for L in lineas:
                if paralelos(L["e"], e) and norm(perp(sub(x["base"], L["p"]), L["e"])) < TOL_L:
                    L["caras"].append(x)
                    L["area"] += x["area"]
                    break
            else:
                lineas.append({"e": e, "p": x["base"], "caras": [x], "area": x["area"]})
        lineas.sort(key=lambda L: -L["area"])
        par = None
        for i in range(len(lineas)):
            for j in range(i + 1, len(lineas)):
                A, B = lineas[i], lineas[j]
                if abs(dot(A["e"], B["e"])) > 1e-6:
                    continue
                n = unit(cross(A["e"], B["e"]))
                if abs(dot(sub(B["p"], A["p"]), n)) < TOL_L:
                    par = (A, B)
                    break
            if par:
                break
        if not par:
            raise Parada("%s: no se hallaron dos brazos perpendiculares que se corten" % self.nombre)
        A, B = par
        m = cross(B["e"], cross(A["e"], B["e"]))
        s = dot(sub(B["p"], A["p"]), m) / dot(A["e"], m)
        C = add(A["p"], mul(A["e"], s))
        brazos = []
        for L in (A, B):
            u = L["e"]
            lados = {}
            for sg in (1, -1):
                mejor, alcance = None, -1
                for x in L["caras"]:
                    lo, hi = self.extension(x["i"], u)
                    r = max(sg * (lo - dot(C, u)), sg * (hi - dot(C, u)))
                    if r > alcance + 1e-7 or (abs(r - alcance) < 1e-7 and mejor and x["area"] > mejor["area"]):
                        mejor, alcance = x, r
                nivel = dot(C, u) + sg * alcance
                puntas = [x for x in self.planos_perp(u, nivel)
                          if dot(self.normal_ext(x["i"]), mul(u, sg)) > 0
                          and self.contiene(x["i"], add(C, mul(u, nivel - dot(C, u))))]
                if not puntas:
                    raise Parada("%s: brazo sin cara de punta" % self.nombre)
                lados[sg] = {"pasador": mejor, "punta": max(puntas, key=lambda x: x["area"]), "alcance": alcance}
            brazos.append({"u": u, "lados": lados})
        self._cruz = {"C": C, "brazos": brazos}
        return self._cruz

    # --------------------------------------------------------------- tornillería
    def perno(self):
        if hasattr(self, "_perno"):
            return self._perno
        vast = max(self.tipo("cilindro"), key=lambda x: x["area"])
        u = unit(vast["eje"])
        lo, hi = self.extension(vast["i"], u)
        todos = [dot(p, u) for x in self.d for p in self.puntos(x["i"])]
        cmin, cmax = min(todos), max(todos)
        if abs(lo - cmin) < 1e-6 and abs(hi - cmax) > 1e-6:
            punta_dir, nivel_cabeza = mul(u, -1.0), hi
        elif abs(hi - cmax) < 1e-6 and abs(lo - cmin) > 1e-6:
            punta_dir, nivel_cabeza = u, lo
        else:
            raise Parada("Perno: no se distingue la punta de la cabeza")
        apoyo = [x for x in self.planos_perp(u, nivel_cabeza) if dot(self.normal_ext(x["i"]), punta_dir) > 0]
        if not apoyo:
            raise Parada("Perno: sin cara de apoyo bajo la cabeza")
        H0 = add(perp(vast["base"], u), mul(u, nivel_cabeza))
        self._perno = {"vastago": vast, "apoyo": max(apoyo, key=lambda x: x["area"]), "H0": H0, "punta": punta_dir}
        return self._perno

    def tuerca(self):
        if hasattr(self, "_tuerca"):
            return self._tuerca
        cil = self.tipo("cilindro")
        if len(cil) != 1:
            raise Parada("Tuerca: se esperaba 1 cilindro (agujero) y hay %d" % len(cil))
        h = cil[0]
        u = unit(h["eje"])
        caras = self.planos_perp(u)
        niveles = sorted(set(round(dot(x["raiz"], u), 7) for x in caras))
        if len(niveles) != 2:
            raise Parada("Tuerca: se esperaban 2 caras de apoyo y hay %d niveles" % len(niveles))
        apoyo = max(self.planos_perp(u, niveles[0]), key=lambda x: x["area"])
        n = self.normal_ext(apoyo["i"])
        N0 = add(perp(h["base"], u), mul(u, niveles[0]))
        self._tuerca = {"agujero": h, "apoyo": apoyo, "N0": N0, "cuerpo": mul(n, -1.0)}
        return self._tuerca


# ==================================================================== ensamble
class Ensamble:
    def __init__(self, asm, ruta, fase, bitacora):
        self.asm, self.ruta, self.fase, self.bit = asm, Path(ruta), fase, bitacora
        self.n_rel = 0

    # ---------------------------------------------------------------- utilidades
    def pose(self, occ): return Pose.de_matriz(se.matriz(occ))

    def poner(self, occ, pose):
        se.reintentar(occ.PutMatrix, pose.matriz(), True)

    def insertar(self, nombre, pose):
        """Inserta, quita el Fijar y (si se da pose) la preposiciona. Con pose=None queda en el
        origen para leer su geometría; luego hay que llamar a poner()."""
        occ = se.insertar(self.asm, CARPETA_PIEZAS / (nombre + ".par"))
        quitadas = se.quitar_fijo(occ)
        if se.es_fija(occ):
            raise Parada("%s sigue fijada tras quitar el Fijar" % occ.Name)
        if pose is not None:
            self.poner(occ, pose)
        self.bit.anotar(self.fase, occ.Name, "", "insertar + quitar Fijar (%d)%s" % (
            quitadas, " + preposicionar" if pose is not None else ""), "", "ok")
        return occ

    def _cara(self, occ, x):
        return Geo.de(occ).caras[x["i"] - 1]

    def _etq(self, occ, x):
        return "%s#%d(%s)" % (Path(occ.OccurrenceFileName).stem, x["i"], x["tipo"])

    def _comprobar_estado(self, rel, que):
        try:
            st = rel.Status
        except Exception:
            st = None
        if st != se.REL_SOLVED:
            raise Parada("%s: la relación quedó con estado %s (no resuelta)" % (que, st))

    def _crear(self, fn, que, piezas, caras, nombre_rel):
        """Crea la relación con hasta 2 intentos (CONTEXTO §7: falla 2 veces -> parada)."""
        ultimo = None
        for intento in (1, 2):
            try:
                rel = fn(intento)
                self._comprobar_estado(rel, que)
                self.n_rel += 1
                self.bit.anotar(self.fase, piezas, caras, que, nombre_rel, "resuelta")
                return rel
            except Parada:
                raise
            except Exception as e:
                ultimo = se.describir_error(e)
                self.bit.anotar(self.fase, piezas, caras, que, nombre_rel, "fallo intento %d" % intento, ultimo)
        raise Parada("%s falló 2 veces: %s · caras %s" % (que, ultimo, caras))

    def coincidir(self, oA, xA, oB, xB, que):
        """Coincidir (Mate): A es la pieza que se coloca, B la de referencia."""
        gA, gB = Geo.de(oA), Geo.de(oB)
        PA, PB = self.pose(oA), self.pose(oB)
        nA, nB = PA.d(gA.normal_ext(xA["i"])), PB.d(gB.normal_ext(xB["i"]))
        dist = abs(dot(sub(PA.p(xA["raiz"]), PB.p(xB["raiz"])), nB))
        if dot(nA, nB) > -1 + 1e-6 or dist > TOL_L:
            raise Parada("%s: las caras %s y %s no están enfrentadas y coplanares (cos=%.6f, sep=%.4f mm)"
                         % (que, self._etq(oA, xA), self._etq(oB, xB), dot(nA, nB), dist * 1000))
        caras = "%s / %s" % (self._etq(oA, xA), self._etq(oB, xB))
        pA, pB = gA.puntos(xA["i"]), gB.puntos(xB["i"])

        def fn(intento):
            k = 0 if intento == 1 else min(1, len(pA) - 1, len(pB) - 1)
            return se.reintentar(self.asm.Relations3d.AddPlanar,
                                 se.ref(self.asm, oA, self._cara(oA, xA)), se.ref(self.asm, oB, self._cara(oB, xB)),
                                 True, pA[k], pB[k])
        return self._crear(fn, que, "%s / %s" % (oA.Name, oB.Name), caras, "Coincidir")

    def alinear_eje(self, oA, xA, oB, xB, que):
        """Alinear eje con giro LIBRE (FixedRotate=False)."""
        PA, PB = self.pose(oA), self.pose(oB)
        eA, eB = PA.d(xA["eje"]), PB.d(xB["eje"])
        sep = norm(perp(sub(PA.p(xA["base"]), PB.p(xB["base"])), unit(eB)))
        if not paralelos(eA, eB) or sep > TOL_L:
            raise Parada("%s: los cilindros %s y %s no son coaxiales (sep=%.4f mm)"
                         % (que, self._etq(oA, xA), self._etq(oB, xB), sep * 1000))
        caras = "%s / %s" % (self._etq(oA, xA), self._etq(oB, xB))

        def fn(intento):
            # AddAxial nace con FixedRotate=True y, si el solver resuelve en ese instante, "bloquea"
            # el giro en una orientación canónica y la pieza salta (verificado: Fork2 giró 73°).
            # Con DelayCompute el giro se libera ANTES de resolver.
            app = self.asm.Application
            app.DelayCompute = True
            try:
                rel = se.reintentar(self.asm.Relations3d.AddAxial,
                                    se.ref(self.asm, oA, self._cara(oA, xA)), se.ref(self.asm, oB, self._cara(oB, xB)),
                                    dot(eA, eB) > 0)
                rel.FixedRotate = False
            finally:
                app.DelayCompute = False
            return rel
        return self._crear(fn, que, "%s / %s" % (oA.Name, oB.Name), caras, "Alinear eje")

    def no_se_movio(self, occ, esperada, que):
        dt, dr = self.pose(occ).diferencia(esperada)
        if dt > TOL_MOV or dr > TOL_ROT:
            raise Parada("%s: %s se movió %.4f mm / %.5f tras relacionar -> alguna relación tomó una cara "
                         "equivocada o la pose objetivo no es coherente" % (que, occ.Name, dt * 1000, dr))

    def revisar(self, que):
        malas = []
        for i in range(1, self.asm.Occurrences.Count + 1):
            o = self.asm.Occurrences.Item(i)
            if o.Status in (se.OCC_OVER, se.OCC_NOT_CONSISTENT):
                malas.append("%s (status %d)" % (o.Name, o.Status))
        if malas:
            raise Parada("%s: ocurrencias sobredefinidas/inconsistentes: %s" % (que, ", ".join(malas)))
        for i in range(1, self.asm.Relations3d.Count + 1):
            r = self.asm.Relations3d.Item(i)
            if r.Status != se.REL_SOLVED:
                raise Parada("%s: relación %d sin resolver (status %s)" % (que, i, r.Status))

    # ------------------------------------------------------------------ recetas
    def receta_B(self, mov, fija, b_mov, b_fija, que):
        """Brida rígida: coincidir caras de apoyo + centrado + 1 agujero de perno."""
        esperada = self.pose(mov)
        self.coincidir(mov, b_mov["apoyo"], fija, b_fija["apoyo"], que + " · apoyo de brida")
        self.alinear_eje(mov, b_mov["rim"], fija, b_fija["rim"], que + " · centrado")
        par = pares_agujeros(self, mov, b_mov, fija, b_fija)
        if not par:
            raise Parada("%s: ningún agujero de perno coincide entre las bridas" % que)
        self.alinear_eje(mov, par[0][0], fija, par[0][1], que + " · agujero de perno (fija el giro)")
        self.no_se_movio(mov, esperada, que)
        self.revisar(que)

    def receta_C(self, mov_es_cruz, cruz, brazo, horq_occ, que):
        """Cruz <-> horquilla: alinear eje (pasador / agujero de oreja) + coincidir (punta / cara interior)."""
        gc, gf = Geo.de(cruz), Geo.de(horq_occ)
        H = gf.horquilla()
        Pc, Pf = self.pose(cruz), self.pose(horq_occ)
        u_asm = Pc.d(brazo["u"])
        e_asm = Pf.d(H["e"])
        if not paralelos(u_asm, e_asm):
            raise Parada("%s: el brazo de la cruz no es paralelo a las orejas" % que)
        mov = cruz if mov_es_cruz else horq_occ
        esperada = self.pose(mov)
        sg_c = 1
        lado_c = brazo["lados"][sg_c]
        punta_asm = Pc.p(lado_c["punta"]["raiz"])
        # lado de la horquilla que queda del mismo lado que esa punta
        sg_f = 1 if dot(sub(punta_asm, Pf.p(H["J"])), e_asm) > 0 else -1
        lado_f = H["lados"][sg_f]
        if mov_es_cruz:
            self.alinear_eje(cruz, lado_c["pasador"], horq_occ, lado_f["agujero"], que + " · pasador en oreja")
            self.coincidir(cruz, lado_c["punta"], horq_occ, lado_f["interior"], que + " · punta contra oreja")
        else:
            self.alinear_eje(horq_occ, lado_f["agujero"], cruz, lado_c["pasador"], que + " · oreja en pasador")
            self.coincidir(horq_occ, lado_f["interior"], cruz, lado_c["punta"], que + " · oreja contra punta")
        self.no_se_movio(mov, esperada, que)
        self.revisar(que)


def pares_agujeros(ens, oA, bA, oB, bB):
    """Pares (agujero A, agujero B) coaxiales en la pose actual."""
    PA, PB = ens.pose(oA), ens.pose(oB)
    pares = []
    for xa in bA["agujeros"]:
        for xb in bB["agujeros"]:
            if paralelos(PA.d(xa["eje"]), PB.d(xb["eje"])) and \
                    norm(perp(sub(PA.p(xa["base"]), PB.p(xb["base"])), unit(PB.d(xb["eje"])))) < TOL_L:
                pares.append((xa, xb))
    return pares


def giro_para_agujeros(ens, oA, bA, poseA, oB, bB):
    """Ángulo mínimo (alrededor de la dirección devuelta) que alinea un agujero de A con uno de B."""
    PB = ens.pose(oB)
    d = unit(poseA.d(bA["eje"]))
    cA = poseA.p(bA["centro_linea"])
    cB = PB.p(bB["centro_linea"])
    if norm(perp(sub(cA, cB), d)) > TOL_L:
        raise Parada("Las bridas %s y %s no son coaxiales en la pose objetivo" % (oA.Name, oB.Name))
    mejor = None
    for xa in bA["agujeros"]:
        va = unit(perp(sub(poseA.p(xa["base"]), cA), d))
        for xb in bB["agujeros"]:
            vb = unit(perp(sub(PB.p(xb["base"]), cB), d))
            ang = math.atan2(dot(cross(va, vb), d), dot(va, vb))
            if mejor is None or abs(ang) < abs(mejor):
                mejor = ang
    return mejor, d


# ===================================================================== estado
def ruta_estado(asm_ruta): return Path(asm_ruta).with_name("cardan_estado.json")


def leer_estado(asm_ruta):
    p = ruta_estado(asm_ruta)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"fases": [], "roles": {}}


def escribir_estado(asm_ruta, est):
    ruta_estado(asm_ruta).write_text(json.dumps(est, indent=1, ensure_ascii=False), encoding="utf-8")


def occ_por_nombre(asm, nombre):
    for i in range(1, asm.Occurrences.Count + 1):
        o = asm.Occurrences.Item(i)
        if o.Name == nombre:
            return o
    raise Parada("No encuentro la ocurrencia %s en el ensamble (¿lo editó a mano?)" % nombre)


def abrir_asm(app, ruta):
    ruta = Path(ruta)
    for i in range(1, app.Documents.Count + 1):
        d = app.Documents.Item(i)
        try:
            if Path(d.FullName).resolve() == ruta.resolve():
                d.Activate()
                return d
        except Exception:
            continue
    if not ruta.exists():
        raise Parada("No existe %s: ejecute primero la fase 1" % ruta)
    return se.reintentar(app.Documents.Open, str(ruta))


def abrir_asm_limpio(app, ruta):
    """Abre el ensamble; si está abierto con cambios sin guardar (p. ej. tras una parada), se
    detiene: no se construye encima de un estado a medias."""
    doc = abrir_asm(app, ruta)
    try:
        sucio = bool(doc.Dirty)
    except Exception:
        sucio = False
    if sucio:
        raise Parada("%s está abierto con cambios sin guardar (¿quedó a medias una fase?). "
                     "Ciérrelo SIN guardar y vuelva a ejecutar la fase." % Path(ruta).name)
    return doc


def resumen(asm, ens, t0, est):
    e = se.estado_ensamble(asm)
    print("\n--- RESUMEN FASE %d (%.1f s) ---" % (ens.fase, time.time() - t0))
    conteo = {}
    for o in e["ocurrencias"]:
        conteo[o["archivo"]] = conteo.get(o["archivo"], 0) + 1
    print("Ocurrencias:", asm.Occurrences.Count, conteo)
    print("Fijas:", [o["nombre"] for o in e["ocurrencias"] if o["fija"]])
    print("Relaciones:", asm.Relations3d.Count, "(creadas en esta fase: %d)" % ens.n_rel)
    tipos = {}
    for r in e["relaciones"]:
        k = "%s/status%s%s" % (r["tipo"], r["status"], "/SUPRIMIDA" if r["suprimida"] else "")
        tipos[k] = tipos.get(k, 0) + 1
    print("Relaciones por tipo/estado:", tipos)
    print("Estados de ocurrencia:", {o["nombre"]: o["status"] for o in e["ocurrencias"]
                                     if not o["nombre"].startswith(("Perno", "tuerca"))})
    return e


# ====================================================================== fases
def fase1(app, args, bit, est):
    ruta = Path(args.asm)
    if ruta.exists():
        raise Parada("Ya existe %s. No se sobrescribe: use --asm con una ruta nueva." % ruta)
    asm = se.reintentar(app.Documents.Add, "SolidEdge.AssemblyDocument")
    ens = Ensamble(asm, ruta, 1, bit)
    I = Pose([[1, 0, 0], [0, 1, 0], [0, 0, 1]], [0, 0, 0])
    sop = se.insertar(asm, CARPETA_PIEZAS / "soporte fijo.par")
    if not se.es_fija(sop):
        se.reintentar(asm.Relations3d.AddGround, sop)
    bit.anotar(1, sop.Name, "", "insertar (queda Fijar)", "Fijar", "ok")
    # --- eje entrada (receta A) en su pose nativa
    eje = ens.insertar("eje entrada", I)
    g_eje, g_sop = Geo.de(eje), Geo.de(sop)
    b = g_eje.brida_unica()
    d, c = b["eje"], b["centro_linea"]
    huecos = [x for x in g_sop.tipo("cilindro") if paralelos(x["eje"], d) and norm(perp(sub(x["base"], c), d)) < TOL_L]
    if len(huecos) != 1:
        raise Parada("eje entrada: se esperaba 1 agujero del soporte coaxial y hay %d" % len(huecos))
    hueco = huecos[0]
    h_lo, h_hi = g_sop.extension(hueco["i"], d)
    s_c = dot(add(c, mul(d, sum(g_eje.extension(b["rim"]["i"], d)) / 2)), d)
    lado = 1 if s_c > (h_lo + h_hi) / 2 else -1             # el eje está del lado + o - del agujero
    cara_placa = [x for x in g_sop.planos_perp(d) if abs(dot(x["raiz"], d) - (h_hi if lado > 0 else h_lo)) < TOL_L
                  and dot(g_sop.normal_ext(x["i"]), mul(d, lado)) > 0]
    nivel = h_hi if lado > 0 else h_lo
    punta = [x for x in g_eje.planos_perp(d, nivel) if dot(g_eje.normal_ext(x["i"]), mul(d, -lado)) > 0
             and g_eje.contiene(x["i"], add(c, mul(d, nivel - dot(c, d))))]
    if len(cara_placa) != 1 or not punta:
        raise Parada("eje entrada: no hay cara de placa (%d) o cara de punta (%d) coplanares" % (len(cara_placa), len(punta)))
    cil_eje = [x for x in g_eje.cilindros_coaxiales(c, d) if x["radio"] <= hueco["radio"] + 1e-7]
    cil_eje.sort(key=lambda x: min(abs(v - nivel) for v in g_eje.extension(x["i"], d)))
    ens.alinear_eje(eje, cil_eje[0], sop, hueco, "A · eje entrada en agujero frontal")
    ens.coincidir(eje, punta[0], sop, cara_placa[0], "A · tope del eje contra la placa")
    ens.no_se_movio(eje, I, "A")
    ens.revisar("A")
    # --- Fork1 (receta B) en su pose nativa
    f1 = ens.insertar("Fork", I)
    ens.receta_B(f1, eje, Geo.de(f1).brida_unica(), b, "B · Fork1 = eje entrada")
    se.guardar_nuevo(asm, ruta)
    bit.anotar(1, "", "", "guardar como", str(ruta), "ok")
    est.update({"asm": str(ruta), "fases": [1], "roles": {"soporte": sop.Name, "eje_entrada": eje.Name, "fork1": f1.Name}})
    return asm, ens


def calcular_cierre(ens, sop, f1, cruz1, est):
    """Resuelve analíticamente la pose cerrada del lazo (centro de Cruz2)."""
    g_sop, g_f = Geo.de(sop), Geo.de(f1)
    H = g_f.horquilla()
    P1 = ens.pose(f1)
    J1 = P1.p(H["J"])
    e1 = P1.d(H["e"])
    C = Geo.de(cruz1).cruz()
    Pc = ens.pose(cruz1)
    libres = [br for br in C["brazos"] if not paralelos(Pc.d(br["u"]), e1)]
    if len(libres) != 1:
        raise Parada("Cruz1: no se identifica el brazo libre")
    q = unit(Pc.d(libres[0]["u"]))
    # agujero de salida = el del soporte que NO es coaxial con el eje de entrada
    d_in = P1.d(H["brida"]["eje"])
    salida = [x for x in g_sop.tipo("cilindro") if not paralelos(x["eje"], d_in)]
    if len(salida) != 1:
        raise Parada("Soporte: se esperaba 1 agujero de salida y hay %d" % len(salida))
    hs = salida[0]
    Q0, w = hs["base"], unit(hs["eje"])
    if abs(dot(w, q)) > 1e-6 or abs(dot(sub(Q0, J1), q)) > TOL_L:
        raise Parada("El eje de salida no está en el plano de giro de la Cruz1: el lazo no cierra en esta posición")
    h_lo, h_hi = g_sop.extension(hs["i"], w)
    t_h = (h_lo + h_hi) / 2 - dot(Q0, w)
    return {"J1": J1, "q": q, "Q0": Q0, "w": w, "t_h": t_h, "hueco_salida": hs["i"], "f_c": H["f_c"]}


def fase2(app, args, bit, est):
    asm = abrir_asm_limpio(app, args.asm)
    ens = Ensamble(asm, args.asm, 2, bit)
    R = est["roles"]
    sop, eje, f1 = (occ_por_nombre(asm, R[k]) for k in ("soporte", "eje_entrada", "fork1"))
    I = Pose([[1, 0, 0], [0, 1, 0], [0, 0, 1]], [0, 0, 0])
    # --- Cruz1 (receta C) en su pose nativa, con el brazo coaxial a las orejas de Fork1
    cz1 = ens.insertar("Central Cruz", I)
    H1 = Geo.de(f1).horquilla()
    P1 = ens.pose(f1)
    C = Geo.de(cz1).cruz()
    if norm(sub(ens.pose(cz1).p(C["C"]), P1.p(H1["J"]))) > TOL_L:
        raise Parada("Cruz1: su centro no coincide con el centro de la horquilla de Fork1")
    brazo1 = [br for br in C["brazos"] if paralelos(br["u"], P1.d(H1["e"]))][0]
    ens.receta_C(True, cz1, brazo1, f1, "C · Cruz1 en Fork1")
    # --- cierre del lazo
    k = calcular_cierre(ens, sop, f1, cz1, est)
    ec_tmp = ens.insertar("eje central", None)     # en el origen: se lee su geometría y luego se coloca
    g_ec = Geo.de(ec_tmp)
    bridas = g_ec.bridas()
    if len(bridas) != 2:
        raise Parada("eje central: se esperaban 2 bridas y hay %d" % len(bridas))
    J1, q, Q0, w, f_c = k["J1"], k["q"], k["Q0"], k["w"], k["f_c"]
    # brida inferior = la más cercana a J1 en la pieza tal como está modelada
    bridas.sort(key=lambda b: norm(sub(b["centro_apoyo"], J1)))
    b_lo, b_up = bridas
    D = norm(sub(b_up["centro_apoyo"], b_lo["centro_apoyo"]))
    Lc = 2 * f_c + D
    v = sub(Q0, J1)
    bq = dot(v, w)
    cq = dot(v, v) - Lc * Lc
    disc = bq * bq - cq
    if disc < 0:
        raise Parada("El lazo no cierra: el eje central no alcanza el eje de salida")
    raices = [-bq + math.sqrt(disc), -bq - math.sqrt(disc)]
    t2 = min(raices, key=lambda t: abs(t - k["t_h"]))
    J2 = add(Q0, mul(w, t2))
    u_c = unit(sub(J2, J1))
    w_out = w if k["t_h"] > t2 else mul(w, -1.0)
    print("Cierre del lazo: J1=%s J2=%s  |J1J2|=%.3f mm  ángulo eje central/entrada=%.3f°"
          % (mm(J1), mm(J2), Lc * 1000, math.degrees(math.acos(abs(dot(u_c, unit(P1.d(H1["brida"]["eje"]))))))))
    bit.anotar(2, "", "", "cierre analítico del lazo", "J2=%s" % mm(J2), "ok")
    # --- Fork2: apoyo en J1 + f_c·u_c, horquilla hacia J1, orejas en el brazo libre q
    Hf = Geo.de(f1).horquilla()
    pose_f2 = pose_por_marcos(Hf["J"], Hf["a_in"], Hf["e"], J1, mul(u_c, -1.0), q)
    f2 = ens.insertar("Fork", pose_f2)
    brazo_q = [br for br in C["brazos"] if not paralelos(br["u"], P1.d(H1["e"]))][0]
    ens.receta_C(False, cz1, brazo_q, f2, "C · Fork2 en el otro brazo de Cruz1")
    # --- eje central: brida inferior contra Fork2, coaxial con u_c, agujeros alineados
    Rm = rot_minima(b_lo["eje"] if dot(b_lo["eje"], sub(b_up["centro_apoyo"], b_lo["centro_apoyo"])) > 0
                    else mul(b_lo["eje"], -1.0), u_c)
    destino = add(J1, mul(u_c, f_c))
    pose_ec = Pose(Rm, sub(destino, mat_vec(Rm, b_lo["centro_apoyo"])))
    phi, eje_giro = giro_para_agujeros(ens, ec_tmp, b_lo, pose_ec, f2, Geo.de(f2).brida_unica())
    pose_ec = pose_ec.girar_en_torno(destino, eje_giro, phi)
    ens.poner(ec_tmp, pose_ec)
    bit.anotar(2, ec_tmp.Name, "", "preposicionar (giro %.2f° para alinear agujeros)" % math.degrees(phi), "", "ok")
    ens.receta_B(ec_tmp, f2, b_lo, Geo.de(f2).brida_unica(), "B · eje central = Fork2")
    se.reintentar(asm.Save)
    bit.anotar(2, "", "", "guardar", str(args.asm), "ok")
    est["roles"].update({"cruz1": cz1.Name, "fork2": f2.Name, "eje_central": ec_tmp.Name})
    est["cierre"] = {"J1": J1, "J2": J2, "u_c": u_c, "w_out": w_out, "q": q, "f_c": f_c,
                     "hueco_salida": k["hueco_salida"]}
    est["fases"].append(2)
    return asm, ens


def fase3(app, args, bit, est):
    asm = abrir_asm_limpio(app, args.asm)
    ens = Ensamble(asm, args.asm, 3, bit)
    R, K = est["roles"], est["cierre"]
    sop, f2, ec, cz1 = (occ_por_nombre(asm, R[k]) for k in ("soporte", "fork2", "eje_central", "cruz1"))
    J2, w_out, q, f_c = K["J2"], K["w_out"], K["q"], K["f_c"]
    g_ec = Geo.de(ec)
    Pec = ens.pose(ec)
    b_up = max(g_ec.bridas(), key=lambda b: norm(sub(Pec.p(b["centro_apoyo"]), K["J1"])))
    Hf = Geo.de(f2).horquilla()
    # --- Fork3: apoyo contra la brida superior, orejas paralelas a las de Fork2 (EN FASE)
    up_c = Pec.p(b_up["centro_apoyo"])
    a3 = unit(mul(Pec.d(b_up["n_apoyo"]), 1.0))     # del apoyo del eje hacia la horquilla
    if norm(sub(add(up_c, mul(a3, f_c)), J2)) > TOL_L:
        raise Parada("Fork3: el centro de su junta no cae en J2 calculado (%.4f mm)" % (norm(sub(add(up_c, mul(a3, f_c)), J2)) * 1000))
    e2 = unit(ens.pose(f2).d(Hf["e"]))
    pose_f3 = pose_por_marcos(Hf["J"], Hf["a_in"], Hf["e"], J2, a3, e2)
    f3 = ens.insertar("Fork", pose_f3)
    if len(pares_agujeros(ens, f3, Hf["brida"], ec, b_up)) < len(Hf["brida"]["agujeros"]):
        raise Parada("Fork3: con las orejas en fase con Fork2 sus agujeros no coinciden con la brida del eje central")
    ens.receta_B(f3, ec, Hf["brida"], b_up, "B · Fork3 = eje central (en fase con Fork2)")
    fase_ok = paralelos(ens.pose(f3).d(Hf["e"]), ens.pose(f2).d(Hf["e"]))
    bit.anotar(3, "%s / %s" % (f2.Name, f3.Name), "", "comprobar puesta en fase", "orejas paralelas", "ok" if fase_ok else "DESFASADAS")
    if not fase_ok:
        raise Parada("Fork2 y Fork3 quedaron desfasadas")
    # --- Cruz2: centro J2, un brazo en las orejas de Fork3 (q), el otro perpendicular a la salida
    e4 = unit(cross(q, w_out))
    Cg = Geo.de(cz1).cruz()
    A, B = Cg["brazos"]
    pose_c2 = pose_por_marcos(Cg["C"], A["u"], B["u"], J2, e2, e4)
    cz2 = ens.insertar("Central Cruz", pose_c2)
    ens.receta_C(True, cz2, A, f3, "C · Cruz2 en Fork3")
    # --- Fork4: apoyo en J2 + f_c·w_out, horquilla hacia J2, orejas en el otro brazo
    pose_f4 = pose_por_marcos(Hf["J"], Hf["a_in"], Hf["e"], J2, mul(w_out, -1.0), e4)
    f4 = ens.insertar("Fork", pose_f4)
    ens.receta_C(False, cz2, B, f4, "C · Fork4 en el otro brazo de Cruz2")
    # --- Eje de salida1: brida contra Fork4, coaxial con el agujero superior, agujeros alineados
    sal = ens.insertar("Eje de salida1", None)
    g_s = Geo.de(sal)
    bs = g_s.brida_unica()
    a_s = mul(bs["n_apoyo"], -1.0)                       # del apoyo hacia el interior del eje
    Rm = rot_minima(a_s, w_out)
    destino = add(J2, mul(w_out, f_c))
    pose_s = Pose(Rm, sub(destino, mat_vec(Rm, bs["centro_apoyo"])))
    phi, eje_giro = giro_para_agujeros(ens, sal, bs, pose_s, f4, Hf["brida"])
    pose_s = pose_s.girar_en_torno(destino, eje_giro, phi)
    ens.poner(sal, pose_s)
    bit.anotar(3, sal.Name, "", "preposicionar (giro %.2f° para alinear agujeros)" % math.degrees(phi), "", "ok")
    ens.receta_B(sal, f4, bs, Hf["brida"], "B · Eje de salida1 = Fork4")
    # --- cierre SOLO con Alinear eje contra el agujero superior del soporte
    g_sop = Geo.de(sop)
    Psop = ens.pose(sop)
    hs = g_sop.d[K["hueco_salida"] - 1]
    ax = unit(Psop.d(hs["eje"]))
    base_asm = Psop.p(hs["base"])
    Ps = ens.pose(sal)
    cand = [x for x in g_s.cilindros_coaxiales(Ps.inv_p(base_asm), trasp_d(Ps, ax))
            if x["radio"] <= hs["radio"] + 1e-7]
    if not cand:
        raise Parada("Eje de salida1: ningún cilindro coaxial con el agujero superior del soporte")
    h_lo, h_hi = ext_asm(g_sop, hs, Psop, ax)
    mid = (h_lo + h_hi) / 2
    cand.sort(key=lambda x: (-x["radio"], abs(sum(ext_asm(g_s, x, Ps, ax)) / 2 - mid)))
    cadena = [sal, f4, cz2, f3, ec, f2, cz1]
    antes = [ens.pose(o) for o in cadena]
    ens.alinear_eje(sal, cand[0], sop, hs, "Cierre · Eje de salida1 en agujero superior (solo Alinear eje)")
    for o, p in zip(cadena, antes):
        ens.no_se_movio(o, p, "Cierre")
    ens.revisar("Cierre del lazo")
    se.reintentar(asm.Save)
    bit.anotar(3, "", "", "guardar", str(args.asm), "ok")
    est["roles"].update({"fork3": f3.Name, "cruz2": cz2.Name, "fork4": f4.Name, "eje_salida": sal.Name})
    est["fases"].append(3)
    return asm, ens


def trasp_d(P, v): return mat_vec(trasp(P.R), v)


def ext_asm(g, x, P, ax):
    vals = [dot(P.p(p), ax) for p in g.puntos(x["i"])]
    return (min(vals), max(vals))


def fase4(app, args, bit, est):
    asm = abrir_asm_limpio(app, args.asm)
    ens = Ensamble(asm, args.asm, 4, bit)
    R = est["roles"]
    uniones = [("eje_entrada", None, "fork1"), ("eje_central", "inf", "fork2"),
               ("eje_central", "sup", "fork3"), ("eje_salida", None, "fork4")]
    hechos = est.get("bridas_tornilleria", [])
    pernos, tuercas = [], []
    for eje_rol, cual, fork_rol in uniones:
        clave = "%s/%s" % (fork_rol, eje_rol)
        if clave in hechos:
            continue
        eje, frk = occ_por_nombre(asm, R[eje_rol]), occ_por_nombre(asm, R[fork_rol])
        g_e, g_f = Geo.de(eje), Geo.de(frk)
        Pe, Pf = ens.pose(eje), ens.pose(frk)
        bf = g_f.brida_unica()
        cf = Pf.p(bf["centro_apoyo"])
        be = min(g_e.bridas(), key=lambda b: norm(sub(Pe.p(b["centro_apoyo"]), cf)))
        pares = pares_agujeros(ens, frk, bf, eje, be)
        print("Brida %s: %d pares de agujeros coaxiales" % (clave, len(pares)))
        if len(pares) != 10:
            raise Parada("Brida %s: se esperaban 10 agujeros comunes y hay %d (el plano pide 40 = 4 x 10)" % (clave, len(pares)))
        for xf, xe in pares:
            # perno: cabeza en la cara trasera de la brida del EJE, punta hacia el Fork
            dir_punta = mul(Pe.d(be["n_tras"]), -1.0)
            eje_l = unit(Pe.d(xe["eje"]))
            pto = Pe.p(xe["base"])
            plano_tras = Pe.p(be["tras"]["raiz"])
            Hh = add(pto, mul(eje_l, dot(sub(plano_tras, pto), eje_l)))
            per = ens.insertar("Perno", None)
            gP = Geo.de(per).perno()
            Rb = rot_minima(gP["punta"], dir_punta)
            esp = Pose(Rb, sub(Hh, mat_vec(Rb, gP["H0"])))
            ens.poner(per, esp)
            ens.alinear_eje(per, gP["vastago"], eje, xe, "D · perno en agujero (%s)" % clave)
            ens.coincidir(per, gP["apoyo"], eje, be["tras"], "D · cabeza contra brida (%s)" % clave)
            ens.no_se_movio(per, esp, "D perno")
            # tuerca: en la cara trasera de la brida del FORK
            plano_f = Pf.p(bf["tras"]["raiz"])
            N = add(pto, mul(eje_l, dot(sub(plano_f, pto), eje_l)))
            tu = ens.insertar("tuercaM3", None)
            gT = Geo.de(tu).tuerca()
            Rt = rot_minima(gT["cuerpo"], dir_punta)
            esp = Pose(Rt, sub(N, mat_vec(Rt, gT["N0"])))
            ens.poner(tu, esp)
            ens.alinear_eje(tu, gT["agujero"], per, gP["vastago"], "D · tuerca en perno (%s)" % clave)
            ens.coincidir(tu, gT["apoyo"], frk, bf["tras"], "D · tuerca contra brida (%s)" % clave)
            ens.no_se_movio(tu, esp, "D tuerca")
            pernos.append(per.Name)
            tuercas.append(tu.Name)
        ens.revisar("Tornillería %s" % clave)
        se.reintentar(asm.Save)
        hechos.append(clave)
        est["bridas_tornilleria"] = hechos
        escribir_estado(args.asm, est)
        bit.anotar(4, clave, "", "brida atornillada y guardada", "10 pernos + 10 tuercas", "ok")
    est["fases"].append(4)
    return asm, ens


def fase5(app, args, bit, est):
    asm = abrir_asm_limpio(app, args.asm)
    ens = Ensamble(asm, args.asm, 5, bit)
    e = se.estado_ensamble(asm)
    fallos = []
    conteo = {}
    for o in e["ocurrencias"]:
        conteo[o["archivo"]] = conteo.get(o["archivo"], 0) + 1
    if conteo != PLANO:
        fallos.append("conteo %s != plano %s" % (conteo, PLANO))
    fijas = [o["nombre"] for o in e["ocurrencias"] if o["fija"]]
    if fijas != [est["roles"]["soporte"]]:
        fallos.append("fijas: %s (solo debe estar el soporte)" % fijas)
    malas = [r for r in e["relaciones"] if r["status"] != se.REL_SOLVED or r["suprimida"]]
    if malas:
        fallos.append("relaciones sin resolver/suprimidas: %s" % malas[:10])
    occ_malas = [o for o in e["ocurrencias"] if o["status"] in (se.OCC_OVER, se.OCC_NOT_CONSISTENT)]
    if occ_malas:
        fallos.append("ocurrencias sobredefinidas/inconsistentes: %s" % occ_malas)
    sueltas = []
    for i in range(1, asm.Occurrences.Count + 1):
        o = asm.Occurrences.Item(i)
        if o.Relations3d.Count == 0:
            sueltas.append(o.Name)
    if sueltas:
        fallos.append("ocurrencias sin relaciones: %s" % sueltas)
    # puesta en fase
    f2, f3 = occ_por_nombre(asm, est["roles"]["fork2"]), occ_por_nombre(asm, est["roles"]["fork3"])
    Hf = Geo.de(f2).horquilla()
    if not paralelos(ens.pose(f2).d(Hf["e"]), ens.pose(f3).d(Hf["e"])):
        fallos.append("Fork2 y Fork3 desfasadas")
    # huellas de los .par
    antes = {}
    p_antes = AQUI / "huellas_par_ANTES.csv"
    if p_antes.exists():
        import csv
        with open(p_antes, encoding="utf-8-sig") as f:
            for fila in csv.DictReader(f):
                antes[fila["archivo"]] = fila["sha256"]
    ahora = se.huellas(CARPETA_PIEZAS)
    cambiados = [k for k in antes if antes[k] != ahora.get(k)]
    if not antes:
        fallos.append("no hay huellas previas de los .par para comparar")
    elif cambiados:
        fallos.append(".par MODIFICADOS: %s" % cambiados)
    informe = {"conteo": conteo, "fijas": fijas, "n_relaciones": len(e["relaciones"]),
               "relaciones_no_resueltas": len(malas), "ocurrencias_mal": len(occ_malas),
               "sin_relaciones": sueltas, "par_sin_cambios": not cambiados and bool(antes),
               "fallos": fallos}
    print(json.dumps(informe, indent=1, ensure_ascii=False))
    bit.anotar(5, "", "", "verificación final (puntos 1-3 y 6)", "", "OK" if not fallos else "FALLOS", "; ".join(fallos))
    se.reintentar(asm.Save)
    bit.anotar(5, "", "", "guardar final", str(args.asm), "ok")
    Path(args.asm).with_name("verificacion_final.json").write_text(json.dumps(informe, indent=1, ensure_ascii=False),
                                                                   encoding="utf-8")
    if fallos:
        raise Parada("Verificación final con fallos: " + "; ".join(fallos))
    est["fases"].append(5)
    return asm, ens


FASES = {1: fase1, 2: fase2, 3: fase3, 4: fase4, 5: fase5}


def main():
    global CARPETA_PIEZAS
    ap = argparse.ArgumentParser(description="Ensamble del Cardán por fases (Solid Edge 2026)")
    ap.add_argument("--fase", type=int, required=True, choices=sorted(FASES))
    ap.add_argument("--asm", default=str(ASM_DEFECTO))
    ap.add_argument("--piezas", default=str(CARPETA_PIEZAS))
    args = ap.parse_args()
    CARPETA_PIEZAS = Path(args.piezas)
    faltan = [p for p in PLANO if not (CARPETA_PIEZAS / (p + ".par")).exists()]
    if faltan:
        print("PARADA: faltan piezas del plano en %s: %s" % (CARPETA_PIEZAS, faltan))
        return 2
    est = leer_estado(args.asm) if args.fase > 1 else {"fases": [], "roles": {}}
    if args.fase > 1 and (args.fase - 1) not in est["fases"]:
        print("PARADA: la fase %d requiere la fase %d terminada (estado: %s)" % (args.fase, args.fase - 1, est["fases"]))
        return 2
    if args.fase in est["fases"]:
        print("PARADA: la fase %d ya se hizo en %s" % (args.fase, args.asm))
        return 2
    try:
        se.guardia_disco(ruta=Path(args.asm).anchor or "C:\\")  # Parche JRV-62
    except se.ErrorSolidEdge as e:
        print("PARADA: %s" % e)
        return 2
    Path(args.asm).parent.mkdir(parents=True, exist_ok=True)
    bit = se.Bitacora(Path(args.asm).with_name("bitacora_cardan.csv"))
    t0 = time.time()
    app = se.conectar()
    bit.anotar(args.fase, "", "", "inicio de fase", "Solid Edge %s" % app.Version, "ok")
    try:
        asm, ens = FASES[args.fase](app, args, bit, est)
    except Parada as p:
        bit.anotar(args.fase, "", "", "PARADA", "", "detenido", str(p))
        print("\nPARADA (fase %d): %s\nNo se guardó nada de esta fase. Revise Solid Edge." % (args.fase, p))
        return 1
    except Exception as e:
        msg = se.describir_error(e)
        bit.anotar(args.fase, "", "", "ERROR", "", "detenido", msg)
        print("\nERROR inesperado (fase %d): %s\nNo se guardó nada de esta fase." % (args.fase, msg))
        raise
    escribir_estado(args.asm, est)
    resumen(asm, ens, t0, est)
    bit.anotar(args.fase, "", "", "fin de fase", "", "ok")
    print("\nFase %d terminada. Revise en Solid Edge y diga OK para seguir." % args.fase)
    return 0


if __name__ == "__main__":
    sys.exit(main())
