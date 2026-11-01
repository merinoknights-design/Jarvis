"""
API de Jarvis para agentes (Claude). Parches JRV-01 y JRV-02 (2026-10-28).

Por qué existe: el chat de Jarvis está hecho para personas (frases, palabras clave, respuestas en prosa) y tiene
trampas (p. ej. "solid edge" en cualquier frase crea una pieza). Un agente necesita órdenes exactas, resultados
en JSON y poder consultar una tarea cuantas veces quiera (el buzón /api/notifications se vacía al leerlo).

Endpoints:
  GET  /api/agente/acciones                 catálogo de acciones y sus parámetros
  POST /api/agente/ejecutar                 {"accion", "parametros": {}, "esperar_s": 0} → registro de la tarea
  GET  /api/agente/tarea/{id}               registro completo (estado, resultado, salida, tiempos)
  GET  /api/agente/tareas?n=20              últimas tareas

Cada tarea corre en un PROCESO APARTE (un fallo de Solid Edge no tumba el servidor) y las que tocan Solid Edge
van de una en una. Los registros se guardan en C:\\Jarvis\\agente\\tareas\\<id>.json.
"""
import asyncio
import datetime
import json
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

import se_com_seguro as se

BASE_DIR = Path("C:/Jarvis")
PYTHON = str(BASE_DIR / "venv" / "Scripts" / "python.exe")
ACCIONES_PY = BASE_DIR / "agente" / "acciones.py"
DIR_TAREAS = BASE_DIR / "agente" / "tareas"
MARCA = "@@RESULTADO@@"
# Solo se ejecutan recetas de estas carpetas de Jarvis (nada de rutas arbitrarias).
CARPETAS_RECETAS = [BASE_DIR / "proyectos", BASE_DIR / "cardan", BASE_DIR / "pruebas", BASE_DIR / "agente"]
MAX_SALIDA = 6000

CATALOGO: Dict[str, Dict[str, Any]] = {
    "estado": {"descripcion": "Solid Edge, documentos abiertos, disco y Cardán. No abre nada.",
               "parametros": {}, "solid_edge": False, "escribe": False, "timeout_s": 60},
    "inspeccionar": {"descripcion": "Qué hay en un .par/.psm/.asm/.dft: operaciones y su estado, volumen y caja; "
                                    "ocurrencias, relaciones, problemas y vínculos rotos; hojas y vistas. Nunca guarda.",
                     "parametros": {"ruta": "ruta del documento (opcional: el activo)", "cerrar": "bool, por defecto true"},
                     "solid_edge": True, "escribe": False, "timeout_s": 300},
    "capturar": {"descripcion": "PNG de la vista (iso, frontal, superior, derecha o actual) validando que no salga "
                                "en blanco; o la ventana completa de Solid Edge.",
                 "parametros": {"ruta": "opcional", "salida": "png (opcional)", "vista": "iso|frontal|superior|derecha|actual",
                                "ventana_completa": "bool", "ancho": "px", "alto": "px"},
                 "solid_edge": True, "escribe": True, "timeout_s": 300},
    "abrir": {"descripcion": "Abre Solid Edge (sin ruta) o un documento existente y lo deja en pantalla, sin crear "
                             "ni guardar nada.",
              "parametros": {"ruta": "opcional"}, "solid_edge": True, "escribe": False, "timeout_s": 300},
    "caras": {"descripcion": "Caras de una pieza en mm (planos con normal exterior; cilindros con eje y diámetro), "
                             "para escribir selectores de recetas de ensamble. Nunca guarda.",
              "parametros": {"ruta": "pieza .par/.psm", "max": "máximo de caras (300)"},
              "solid_edge": True, "escribe": False, "timeout_s": 300},
    "exportar": {"descripcion": "Exporta un documento a STEP/STL/IGES/Parasolid/PDF con SaveCopyAs (el original no cambia).",
                 "parametros": {"ruta": "documento", "salida": "ruta nueva .stp/.step/.stl/.igs/.x_t/.pdf"},
                 "solid_edge": True, "escribe": True, "timeout_s": 300},
    "interferencia": {"descripcion": "Detecta choques de un ensamble con el comando de Solid Edge (vía C# tipado) y separa "
                                     "choques reales (volumen >= umbral) de contactos. Nunca guarda.",
                      "parametros": {"ruta": "ensamble .asm", "umbral_mm3": "1.0", "ignorar_roscas": "bool",
                                     "esperados": "lista de pares 'A.par<>B.par' cuyo solape es normal (roscas)"},
                      "solid_edge": True, "escribe": False, "timeout_s": 1800},
    "receta": {"descripcion": "Ejecuta un script de receta de C:\\Jarvis\\{proyectos,cardan,pruebas,agente} con el "
                              "Python de Jarvis y devuelve su salida.",
               "parametros": {"script": "ruta del .py", "args": "lista de argumentos", "timeout_s": "por defecto 1800"},
               "solid_edge": True, "escribe": True, "timeout_s": 1800},
}

router = APIRouter(prefix="/api/agente")
_tareas: Dict[str, Dict[str, Any]] = {}
_cerrojo_registro = threading.Lock()
_cerrojo_solid_edge = threading.Lock()   # una tarea de Solid Edge a la vez


def _ahora() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def _guardar(t: Dict[str, Any]) -> None:
    DIR_TAREAS.mkdir(parents=True, exist_ok=True)
    (DIR_TAREAS / (t["id"] + ".json")).write_text(json.dumps(t, ensure_ascii=False, indent=1, default=str),
                                                  encoding="utf-8")


def _actualizar(t: Dict[str, Any], **cambios) -> None:
    with _cerrojo_registro:
        t.update(cambios)
        _guardar(t)


def _leer(id_tarea: str) -> Optional[Dict[str, Any]]:
    if id_tarea in _tareas:
        return _tareas[id_tarea]
    p = DIR_TAREAS / (id_tarea + ".json")
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return None


def _script_permitido(script: str) -> Path:
    p = Path(script)
    if not p.is_absolute():
        p = BASE_DIR / p
    p = p.resolve()
    if p.suffix.lower() != ".py" or not p.exists():
        raise ValueError("El script no existe o no es .py: %s" % p)
    if not any(p.is_relative_to(c.resolve()) for c in CARPETAS_RECETAS):
        raise ValueError("Solo se ejecutan recetas de: %s" % ", ".join(str(c) for c in CARPETAS_RECETAS))
    return p


def _comando(accion: str, params: Dict[str, Any]) -> List[str]:
    if accion == "receta":
        script = _script_permitido(params.get("script", ""))
        args = params.get("args", [])
        if not isinstance(args, list):
            raise ValueError("'args' debe ser una lista")
        return [PYTHON, "-X", "utf8", str(script)] + [str(a) for a in args]
    if accion == "interferencia":
        cmd = [PYTHON, "-X", "utf8", str(BASE_DIR / "agente" / "interferencia.py"), str(params["ruta"]),
               "--umbral", str(params.get("umbral_mm3", 1.0))]
        if params.get("ignorar_roscas"):
            cmd.append("--ignorar-roscas")
        for par in params.get("esperados", []):
            cmd += ["--esperado", str(par)]
        return cmd
    return [PYTHON, "-X", "utf8", str(ACCIONES_PY), accion, json.dumps(params, ensure_ascii=False)]


def _correr(t: Dict[str, Any]) -> None:
    info = CATALOGO[t["accion"]]
    cerrojo = _cerrojo_solid_edge if info["solid_edge"] else None
    try:
        if cerrojo:
            cerrojo.acquire()
        _actualizar(t, estado="ejecutando", inicio=_ahora())
        t0 = time.time()
        timeout = int(t["parametros"].get("timeout_s", info["timeout_s"]))
        r = subprocess.run(t["comando"], cwd=str(BASE_DIR), capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout, creationflags=subprocess.CREATE_NO_WINDOW)
        salida = (r.stdout or "") + (("\n[stderr]\n" + r.stderr) if r.stderr else "")
        resultado = None
        for linea in reversed(salida.splitlines()):
            if linea.startswith(MARCA):
                try:
                    resultado = json.loads(linea[len(MARCA):].strip())
                except Exception:
                    pass
                break
        if resultado is not None:
            estado = "ok" if resultado.get("ok") else "error"
        else:
            estado = "ok" if r.returncode == 0 else ("parada" if "PARADA" in salida else "error")
        _actualizar(t, estado=estado, fin=_ahora(), duracion_s=round(time.time() - t0, 1), codigo_salida=r.returncode,
                    resultado=resultado, salida=salida[-MAX_SALIDA:])
    except subprocess.TimeoutExpired:
        _actualizar(t, estado="error", fin=_ahora(), error="Tiempo agotado; revise Solid Edge (puede tener un diálogo abierto).")
    except Exception as e:
        _actualizar(t, estado="error", fin=_ahora(), error=str(e))
    finally:
        if cerrojo:
            cerrojo.release()


def crear_tarea(accion: str, params: Dict[str, Any]) -> Dict[str, Any]:
    if accion not in CATALOGO:
        raise ValueError("Acción desconocida '%s'. Opciones: %s" % (accion, sorted(CATALOGO)))
    avisos = []
    if CATALOGO[accion]["escribe"]:
        libre = se.guardia_disco()  # Parche JRV-62: lanza ErrorSolidEdge por debajo de 0,3 GB
        if libre < se.DISCO_AVISO_GB:
            avisos.append("Quedan %.2f GB libres en C:: solo trabajos pequeños." % libre)
    t = {"id": datetime.datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6], "accion": accion,
         "parametros": params, "estado": "en_cola", "creada": _ahora(), "avisos": avisos,
         "comando": _comando(accion, params)}
    with _cerrojo_registro:
        _tareas[t["id"]] = t
        _guardar(t)
    threading.Thread(target=_correr, args=(t,), daemon=True, name="agente-" + t["id"]).start()
    return t


def _publico(t: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in t.items() if k != "comando"}


@router.get("/acciones")
async def acciones():
    return {"acciones": {k: {c: v[c] for c in ("descripcion", "parametros", "escribe")} for k, v in CATALOGO.items()},
            "disco_libre_gb": round(se.espacio_libre_gb(), 2)}


@router.post("/ejecutar")
async def ejecutar(request: Request):
    cuerpo = await request.json()
    try:
        t = crear_tarea(cuerpo.get("accion", ""), cuerpo.get("parametros") or {})
    except (ValueError, se.ErrorSolidEdge) as e:
        return JSONResponse({"estado": "rechazada", "error": str(e)}, status_code=400)
    limite = time.time() + min(float(cuerpo.get("esperar_s", 0) or 0), 600.0)
    while time.time() < limite and t["estado"] in ("en_cola", "ejecutando"):
        await asyncio.sleep(0.5)
    return _publico(t)


@router.get("/tarea/{id_tarea}")
async def tarea(id_tarea: str):
    t = _leer(id_tarea)
    if t is None:
        return JSONResponse({"error": "No existe la tarea %s" % id_tarea}, status_code=404)
    return _publico(t)


@router.get("/tareas")
async def tareas(n: int = 20):
    archivos = sorted(DIR_TAREAS.glob("*.json"), reverse=True)[:max(1, min(n, 200))] if DIR_TAREAS.exists() else []
    out = []
    for p in archivos:
        try:
            t = json.loads(p.read_text(encoding="utf-8"))
            out.append({k: t.get(k) for k in ("id", "accion", "estado", "creada", "duracion_s")})
        except Exception:
            pass
    return {"tareas": out}
