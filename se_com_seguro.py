"""
Capa COM segura para Solid Edge 2026 (Jarvis).

Reglas que aplica (CONTEXTO_ENSAMBLE_CARDAN.md §6.1 y §10):
  - Conectar a la instancia abierta; si no hay, lanzarla. NUNCA matar Edge.exe.
  - Reintentar cuando Solid Edge responde "ocupado" (RPC_E_CALL_REJECTED / RETRYLATER).
  - DisplayAlerts = False.
  - Nunca guardar sobre una ruta existente (el diálogo de sobrescribir bloquea SE).
  - Quitar el Fijar (Ground) que AddByFilename deja en cada ocurrencia.
  - Relaciones con Reference (CreateReference), nunca con caras sueltas.
  - Bitácora CSV de cada acción.
  - No guardar con menos de 0,3 GB libres en C: (el disco llegó a 0 bytes el 2026-10-28).
Unidades de la API: metros y radianes.
"""

import csv
import datetime
import hashlib
import math
import os
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import pythoncom
import pywintypes
import win32com.client

# Constantes de las type libraries de Solid Edge (tomadas de SolidEdge-MCP / doc. Siemens)
IG_QUERY_ALL = 1
IG_GROUND_REL = 1959028688
IG_AXIAL_REL = 1472929712
IG_PLANAR_REL = -2058948880
REL_SOLVED = 1
OCC_WELL, OCC_FIXED, OCC_UNDER, OCC_OVER = 1, 2, 4, 32776
OCC_NOT_CONSISTENT = 32784
OCUPADO = {-2147418111, -2147417846}  # RPC_E_CALL_REJECTED, RPC_E_SERVERCALL_RETRYLATER

NOMBRES_REL = {IG_GROUND_REL: "Fijar", IG_AXIAL_REL: "Alinear eje", IG_PLANAR_REL: "Planar"}


class ErrorSolidEdge(RuntimeError):
    """Error con mensaje claro para el usuario (en vez de seguir a ciegas)."""


# ---------------------------------------------------------------- llamadas COM
def es_ocupado(e: Exception) -> bool:
    return isinstance(e, pywintypes.com_error) and e.hresult in OCUPADO


def reintentar(fn, *args, intentos: int = 40, espera: float = 0.25, **kwargs):
    """Ejecuta fn y reintenta solo si Solid Edge está ocupado. Otros errores suben tal cual."""
    for _ in range(intentos):
        try:
            return fn(*args, **kwargs)
        except pywintypes.com_error as e:
            if e.hresult not in OCUPADO:
                raise
            time.sleep(espera)
    raise ErrorSolidEdge("Solid Edge siguió ocupado tras %d intentos (¿hay un diálogo abierto?)" % intentos)


def describir_error(e: Exception) -> str:
    if isinstance(e, pywintypes.com_error):
        detalle = ""
        try:
            if e.excepinfo and e.excepinfo[2]:
                detalle = " · " + str(e.excepinfo[2]).strip()
        except Exception:
            pass
        return "COM 0x%08X %s%s" % (e.hresult & 0xFFFFFFFF, e.strerror, detalle)
    return "%s: %s" % (type(e).__name__, e)


def conectar(lanzar: bool = True, espera_max: float = 240.0):
    """Conecta con Solid Edge. Si no está abierto y lanzar=True, lo abre y espera a que responda.
    Nunca cierra ni mata un Solid Edge existente."""
    pythoncom.CoInitialize()
    app = None
    try:
        app = win32com.client.GetActiveObject("SolidEdge.Application")
    except pywintypes.com_error:
        app = None
    if app is None:
        if not lanzar:
            raise ErrorSolidEdge("Solid Edge no está abierto. Ábralo y vuelva a intentar.")
        app = win32com.client.Dispatch("SolidEdge.Application")
    limite = time.time() + espera_max
    while True:
        try:
            _ = app.Version
            break
        except pywintypes.com_error as e:
            if e.hresult not in OCUPADO or time.time() > limite:
                raise ErrorSolidEdge("Solid Edge no responde: " + describir_error(e))
            time.sleep(1.0)
    reintentar(setattr, app, "Visible", True)
    reintentar(setattr, app, "DisplayAlerts", False)
    return app


# ------------------------------------------------------------------- archivos
def sha256(ruta: Path) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest().upper()


def huellas(carpeta: Path, patron: str = "*.par") -> Dict[str, str]:
    return {p.name: sha256(p) for p in sorted(Path(carpeta).glob(patron))}


DISCO_MINIMO_GB = 0.3   # por debajo no se escribe nada
DISCO_AVISO_GB = 1.0    # por debajo, solo trabajos pequeños


def espacio_libre_gb(ruta: str = "C:\\") -> float:
    return shutil.disk_usage(ruta).free / 1024 ** 3


def guardia_disco(minimo_gb: float = DISCO_MINIMO_GB, ruta: str = "C:\\") -> float:
    """Parche JRV-62 (2026-10-28): se niega a seguir si queda menos de `minimo_gb` libres.
    Devuelve los GB libres para que quien llama pueda avisar si están por debajo de DISCO_AVISO_GB."""
    libre = espacio_libre_gb(ruta)
    if libre < minimo_gb:
        raise ErrorSolidEdge("Disco casi lleno: quedan %.2f GB libres en %s (mínimo %.1f GB). "
                             "Libere espacio antes de guardar." % (libre, ruta, minimo_gb))
    return libre


def guardar_nuevo(doc, ruta: Path) -> Path:
    """SaveAs solo a una ruta que NO existe. Si existe, error claro (nunca dejar que SE pregunte)."""
    ruta = Path(ruta)
    guardia_disco(ruta=ruta.anchor or "C:\\")
    if ruta.exists():
        raise FileExistsError("Ya existe %s: no se sobrescribe. Elija otra ruta." % ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    reintentar(doc.SaveAs, str(ruta))
    if not ruta.exists():
        raise ErrorSolidEdge("SaveAs no produjo el archivo %s" % ruta)
    return ruta


def ruta_libre(ruta: Path) -> Path:
    """Devuelve la ruta tal cual si no existe; si existe, añade _2, _3… (nunca sobrescribe)."""
    ruta = Path(ruta)
    if not ruta.exists():
        return ruta
    n = 2
    while True:
        cand = ruta.with_name("%s_%d%s" % (ruta.stem, n, ruta.suffix))
        if not cand.exists():
            return cand
        n += 1


# ---------------------------------------------------------------- ocurrencias
def insertar(asm, ruta_par: Path):
    ruta_par = Path(ruta_par)
    if not ruta_par.exists():
        raise ErrorSolidEdge("No existe la pieza %s" % ruta_par)
    return reintentar(asm.Occurrences.AddByFilename, str(ruta_par))


def relaciones_de(occ) -> List[Any]:
    rels = occ.Relations3d
    return [rels.Item(i) for i in range(1, rels.Count + 1)]


def quitar_fijo(occ) -> int:
    """Borra las relaciones Fijar (Ground) de una ocurrencia. Devuelve cuántas quitó."""
    n = 0
    rels = occ.Relations3d
    for i in range(rels.Count, 0, -1):
        r = rels.Item(i)
        if r.Type == IG_GROUND_REL:
            reintentar(r.Delete)
            n += 1
    return n


def es_fija(occ) -> bool:
    return any(r.Type == IG_GROUND_REL for r in relaciones_de(occ))


def matriz(occ) -> List[float]:
    """Matriz 4x4 de la ocurrencia (16 valores; traslación en 12,13,14; metros)."""
    res = occ.GetMatrix([0.0] * 16)
    if isinstance(res, tuple) and len(res) == 1:
        res = res[0]
    return [float(v) for v in res]


def a_ensamble_punto(M: Sequence[float], p: Sequence[float]) -> List[float]:
    return [sum(p[j] * M[4 * j + i] for j in range(3)) + M[12 + i] for i in range(3)]


def a_ensamble_dir(M: Sequence[float], v: Sequence[float]) -> List[float]:
    return [sum(v[j] * M[4 * j + i] for j in range(3)) for i in range(3)]


# ---------------------------------------------------------------------- caras
def _aplanar(res) -> List[Any]:
    """Aplana el retorno de un método COM con parámetros de salida."""
    if not isinstance(res, (tuple, list)):
        return [res]
    out = []
    for r in res:
        if isinstance(r, (tuple, list)) and len(r) and not isinstance(r[0], (tuple, list)):
            out.append([float(x) for x in r])
        else:
            out.append(r)
    return out


def caras(occ) -> List[Any]:
    fs = occ.OccurrenceDocument.Models.Item(1).Body.Faces(IG_QUERY_ALL)
    return [fs.Item(i) for i in range(1, fs.Count + 1)]


def describir(cara) -> Dict[str, Any]:
    """Clasifica una cara en coordenadas de la PIEZA (metros)."""
    g = cara.Geometry
    d: Dict[str, Any] = {"area": float(cara.Area)}
    try:
        r = _aplanar(g.GetPlaneData([0.0] * 3, [0.0] * 3))
        vec = [x for x in r if isinstance(x, list) and len(x) == 3]
        if len(vec) >= 2:
            return {**d, "tipo": "plano", "raiz": vec[0], "normal": _unit(vec[1])}
    except Exception:
        pass
    try:
        r = _aplanar(g.GetCylinderData([0.0] * 3, [0.0] * 3, 0.0))
        vec = [x for x in r if isinstance(x, list) and len(x) == 3]
        esc = [x for x in r if isinstance(x, float)]
        if len(vec) >= 2 and esc:
            return {**d, "tipo": "cilindro", "base": vec[0], "eje": _unit(vec[1]), "radio": esc[-1]}
    except Exception:
        pass
    try:
        r = _aplanar(g.GetConeData([0.0] * 3, [0.0] * 3, 0.0, 0.0))
        vec = [x for x in r if isinstance(x, list) and len(x) == 3]
        esc = [x for x in r if isinstance(x, float)]
        if len(vec) >= 2 and esc:
            return {**d, "tipo": "cono", "base": vec[0], "eje": _unit(vec[1]), "radio": esc[0]}
    except Exception:
        pass
    try:
        r = _aplanar(g.GetTorusData([0.0] * 3, [0.0] * 3, 0.0, 0.0))
        vec = [x for x in r if isinstance(x, list) and len(x) == 3]
        if len(vec) >= 2:
            return {**d, "tipo": "toro", "base": vec[0], "eje": _unit(vec[1])}
    except Exception:
        pass
    return {**d, "tipo": "otro"}


def rango_cara(cara) -> Optional[List[List[float]]]:
    try:
        r = _aplanar(cara.GetRange([0.0] * 3, [0.0] * 3))
        vec = [x for x in r if isinstance(x, list) and len(x) == 3]
        return vec[:2] if len(vec) >= 2 else None
    except Exception:
        return None


def puntos_arista(cara) -> List[List[float]]:
    """Extremos de las aristas de la cara (siempre están SOBRE la cara)."""
    pts = []
    try:
        es = cara.Edges
        for i in range(1, es.Count + 1):
            try:
                r = _aplanar(es.Item(i).GetEndPoints([0.0] * 3, [0.0] * 3))
                pts.extend([x for x in r if isinstance(x, list) and len(x) == 3][:2])
            except Exception:
                pass
    except Exception:
        pass
    return pts


def _unit(v: Sequence[float]) -> List[float]:
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


# ---------------------------------------------------------------- relaciones
def ref(asm, occ, entidad):
    return reintentar(asm.CreateReference, occ, entidad)


def estado_ensamble(asm) -> Dict[str, Any]:
    occs = []
    for i in range(1, asm.Occurrences.Count + 1):
        o = asm.Occurrences.Item(i)
        try:
            st = o.Status
        except Exception:
            st = None
        occs.append({"nombre": o.Name, "archivo": Path(o.OccurrenceFileName).stem, "status": st,
                     "fija": es_fija(o)})
    rels = []
    for i in range(1, asm.Relations3d.Count + 1):
        r = asm.Relations3d.Item(i)
        try:
            st = r.Status
        except Exception:
            st = None
        try:
            sup = bool(r.Suppress)
        except Exception:
            sup = None
        rels.append({"i": i, "tipo": NOMBRES_REL.get(r.Type, r.Type), "status": st, "suprimida": sup})
    return {"ocurrencias": occs, "relaciones": rels}


# ------------------------------------------------------------------- bitácora
class Bitacora:
    CAMPOS = ["hora", "fase", "piezas", "caras", "accion", "relacion", "estado", "error"]

    def __init__(self, ruta: Path):
        self.ruta = Path(ruta)
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        nuevo = not self.ruta.exists()
        if nuevo:
            with open(self.ruta, "w", newline="", encoding="utf-8-sig") as f:
                csv.writer(f).writerow(self.CAMPOS)

    def anotar(self, fase, piezas="", caras="", accion="", relacion="", estado="", error=""):
        fila = [datetime.datetime.now().isoformat(timespec="seconds"), fase, piezas, caras, accion,
                relacion, estado, error]
        with open(self.ruta, "a", newline="", encoding="utf-8-sig") as f:
            csv.writer(f).writerow(fila)
