"""
Aplica esta actualización a un Jarvis ya instalado. Solo usa la biblioteca estándar de Python.

Sin opciones es un ENSAYO: informa qué haría y no cambia nada. Con --aplicar:
  1. Respalda en C:\\Jarvis_respaldos\\<fecha>_pre_actualizacion todo lo que va a cambiar.
  2. Copia los archivos. Un archivo que el usuario modificó por su cuenta NO se pisa: se detiene y lo lista como conflicto.
  3. Crea .env si no existe (la clave de Brave pasa de la configuración vieja a .env, sin mostrarse).
  4. Compila las ayudas en C# con el compilador de Windows y las type libraries de su Solid Edge.
  5. Instala las habilidades de Claude en ~\\.claude\\skills (la memoria que ya exista allí no se toca).
Nunca borra nada, y no toca venv, uploads, memory, logs ni un .env existente. Se puede repetir sin riesgo.

Uso:  python -I -X utf8 actualizar_jarvis.py [--aplicar] [--destino C:\\Jarvis] [--skills carpeta] [--resuelto ruta/archivo ...]
  --resuelto: archivo con conflicto que ya se fusionó a mano; se deja como está.
Última línea:  @@RESULTADO@@ {json}
"""
import argparse
import datetime
import hashlib
import json
import re
import shutil
import socket
import subprocess
import sys
from pathlib import Path

MARCA = "@@RESULTADO@@"
AQUI = Path(__file__).resolve().parent
ORIGEN = AQUI.parent
SKILLS_ORIGEN = AQUI / "skills"
DISCO_MINIMO_GB = 0.3


def huella(p):
    """Huella del contenido sin depender de los finales de línea (git los puede cambiar al clonar)."""
    return hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def clasificar(manifiesto, destino, resueltos):
    grupos = {"nuevos": [], "reemplazar": [], "al_dia": [], "conflictos": [], "resueltos": []}
    for ruta, h in sorted(manifiesto["archivos"].items()):
        local = destino / ruta
        if not local.exists():
            grupos["nuevos"].append(ruta)
            continue
        actual = huella(local)
        if actual == h["nuevo"]:
            grupos["al_dia"].append(ruta)
        elif ruta in resueltos:
            grupos["resueltos"].append(ruta)
        elif actual == h["base"]:
            grupos["reemplazar"].append(ruta)
        else:
            grupos["conflictos"].append(ruta)
    return grupos


def edge_registrado():
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"SolidEdge.Application\CLSID") as k:
            clsid = winreg.QueryValue(k, None)
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, "CLSID\\%s\\LocalServer32" % clsid) as k:
            return winreg.QueryValue(k, None)
    except OSError:
        return None


def servidor_corriendo():
    with socket.socket() as s:
        s.settimeout(1)
        return s.connect_ex(("127.0.0.1", 7777)) == 0


def revisar_entorno(destino):
    libre = shutil.disk_usage(str(destino.anchor or "C:\\")).free / 1024 ** 3
    py = destino / "venv" / "Scripts" / "python.exe"
    return {"destino": str(destino), "destino_existe": destino.exists(), "es_c_jarvis": str(destino).lower() == r"c:\jarvis",
            "tiene_git": (destino / ".git").exists(), "python_de_jarvis": py.exists(), "disco_libre_gb": round(libre, 2),
            "solid_edge_registrado": edge_registrado(), "servidor_corriendo": servidor_corriendo(), "env_existe": (destino / ".env").exists()}


def migrar_env(destino):
    """Crea .env si falta. Devuelve qué pasó con la clave de Brave, sin mostrarla nunca."""
    env = destino / ".env"
    if env.exists():
        return "ya existía .env: no se tocó"
    clave = ""
    viejo = destino / "config" / "mcp_config.json"
    if viejo.exists():
        m = re.search(r'"BRAVE_API_KEY"\s*:\s*"([^"]+)"', viejo.read_text(encoding="utf-8", errors="replace"))
        clave = m.group(1) if m else ""
    ejemplo = (ORIGEN / ".env.ejemplo").read_text(encoding="utf-8")
    env.write_text(ejemplo.replace("BRAVE_API_KEY=\n", "BRAVE_API_KEY=%s\n" % clave), encoding="utf-8")
    return "clave de Brave movida a .env" if clave else "sin clave de Brave: Jarvis no buscará en la web hasta poner una en .env"


def instalar_skills(carpeta, respaldo):
    """Copia las habilidades. La memoria que ya tenga el usuario se conserva: es lo que su Claude ha aprendido."""
    hechos = {}
    for skill in sorted(p for p in SKILLS_ORIGEN.iterdir() if p.is_dir()):
        destino = carpeta / skill.name
        if destino.exists():
            shutil.copytree(destino, respaldo / "skills" / skill.name, dirs_exist_ok=True)
        copiados = conservados = 0
        for f in skill.rglob("*"):
            if not f.is_file():
                continue
            rel = f.relative_to(skill)
            d = destino / rel
            if rel.parts[0] == "memoria" and d.exists():
                conservados += 1
                continue
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, d)
            copiados += 1
        hechos[skill.name] = {"copiados": copiados, "memoria_conservada": conservados}
    return hechos


def compilar_csharp(destino):
    py = destino / "venv" / "Scripts" / "python.exe"
    r = subprocess.run([str(py if py.exists() else sys.executable), "-X", "utf8", str(destino / "agente" / "csharp" / "compilar.py")],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    linea = next((l for l in reversed(r.stdout.splitlines()) if l.startswith(MARCA)), None)
    return json.loads(linea[len(MARCA):]) if linea else {"ok": False, "error": (r.stdout + r.stderr)[-500:]}


def revisar_sintaxis(destino, rutas):
    errores = []
    for ruta in rutas:
        if ruta.endswith((".py", ".pyw")):
            try:
                compile((destino / ruta).read_text(encoding="utf-8"), ruta, "exec")
            except (SyntaxError, UnicodeDecodeError) as e:
                errores.append("%s: %s" % (ruta, e))
    return errores


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--aplicar", action="store_true")
    ap.add_argument("--destino", default=r"C:\Jarvis")
    ap.add_argument("--skills", default=str(Path.home() / ".claude" / "skills"))
    ap.add_argument("--resuelto", action="append", default=[])
    a = ap.parse_args()

    destino = Path(a.destino)
    manifiesto = json.loads((AQUI / "manifiesto.json").read_text(encoding="utf-8"))
    entorno = revisar_entorno(destino)
    res = {"version": manifiesto["version"], "modo": "aplicar" if a.aplicar else "ensayo", "entorno": entorno}
    if not destino.exists():
        return dict(res, ok=False, error="No existe %s" % destino)
    grupos = clasificar(manifiesto, destino, set(a.resuelto))
    res["archivos"] = {k: len(v) for k, v in grupos.items()}
    res["conflictos"] = grupos["conflictos"]
    res["reemplazar"] = grupos["reemplazar"]
    if grupos["conflictos"]:
        res["siguiente"] = ("Estos archivos tienen cambios propios del usuario. No se aplicó nada. Fusiónalos a mano con la versión nueva "
                            "y repite con --aplicar --resuelto <archivo> por cada uno.")
    if not a.aplicar:
        return dict(res, ok=True)
    if grupos["conflictos"]:
        return dict(res, ok=False, error="Hay conflictos sin resolver")
    if entorno["disco_libre_gb"] < DISCO_MINIMO_GB:
        return dict(res, ok=False, error="Quedan %.2f GB libres: libera espacio antes de actualizar" % entorno["disco_libre_gb"])

    respaldo = Path(r"C:\Jarvis_respaldos") / (datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S") + "_pre_actualizacion")
    if a.destino.lower() != r"c:\jarvis":     # ensayos de instalación en otra carpeta
        respaldo = destino.parent / (destino.name + "_respaldo_" + datetime.datetime.now().strftime("%H%M%S"))
    for ruta in grupos["reemplazar"]:
        d = respaldo / "jarvis" / ruta
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(destino / ruta, d)
    res["clave_brave"] = migrar_env(destino)   # antes de reemplazar la configuración vieja, que es de donde se lee
    for ruta in grupos["nuevos"] + grupos["reemplazar"]:
        d = destino / ruta
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ORIGEN / ruta, d)
    res["respaldo"] = str(respaldo)
    res["sintaxis_con_error"] = revisar_sintaxis(destino, list(manifiesto["archivos"]))
    res["compilacion"] = compilar_csharp(destino)
    res["skills"] = instalar_skills(Path(a.skills), respaldo)
    res["reiniciar_servidor"] = entorno["servidor_corriendo"]
    res["ok"] = not res["sintaxis_con_error"] and res["compilacion"].get("ok", False)
    if not res["ok"]:
        res["error"] = "Falló la sintaxis o la compilación: revisa 'sintaxis_con_error' y 'compilacion'"
    return res


if __name__ == "__main__":
    try:
        salida = main()
    except Exception as e:
        salida = {"ok": False, "error": "%s: %s" % (type(e).__name__, e)}
    print(MARCA, json.dumps(salida, ensure_ascii=False, indent=None))
    sys.exit(0 if salida.get("ok") else 1)
