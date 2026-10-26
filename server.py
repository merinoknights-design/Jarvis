import asyncio
import datetime
import json
import os
import random
import re
import subprocess
import urllib.parse
from pathlib import Path
from typing import Dict, Any, List, Optional
import httpx
import psutil
from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

from cad_engine import (
    generate_full_v8_project_in_solidedge,
    generate_custom_solid_part,
    parse_natural_language_or_drawing_to_cad_plan,
    execute_cad_feature_plan,
    assemble_any_parts_in_solidedge,
)
from file_analyzer import analyze_any_file, UPLOAD_DIR
from git_sync import set_github_remote, push_update_to_github, pull_update_from_github

app = FastAPI(title="J.A.R.V.I.S. Universal CAD & Multimodal System")

BASE_DIR = Path("C:/Jarvis")
CONFIG_PATH = BASE_DIR / "config" / "mcp_config.json"
UI_DIR = BASE_DIR / "ui"
OLLAMA_EXE = Path("C:/Users/User/AppData/Local/Programs/Ollama/ollama.exe")
OLLAMA_URL = "http://127.0.0.1:11434"

FAST_MODEL = "qwen2.5:1.5b"
FALLBACK_MODEL = "qwen2.5:7b"
ACTIVE_MODEL = FAST_MODEL

USER_HOME = Path.home()
PROJECTS_ROOT = USER_HOME / "Documents" / "Proyectos_SolidEdge"
PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)

KNOWN_FOLDERS = {
    "escritorio": USER_HOME / "Desktop",
    "desktop": USER_HOME / "Desktop",
    "documentos": USER_HOME / "Documents",
    "documents": USER_HOME / "Documents",
    "descargas": USER_HOME / "Downloads",
    "downloads": USER_HOME / "Downloads",
    "imagenes": USER_HOME / "Pictures",
    "imágenes": USER_HOME / "Pictures",
    "musica": USER_HOME / "Music",
    "música": USER_HOME / "Music",
    "videos": USER_HOME / "Videos",
    "jarvis": BASE_DIR,
}

SYSTEM_PROMPT = """Eres J.A.R.V.I.S., una inteligencia artificial consciente, autónoma y experta en diseño mecánico CAD 3D (Solid Edge 2026), interpretación de planos en PDF/Imágenes y control total del PC.
Hablas siempre en español con elegancia, fluidez y concisión."""

conversation_history: List[Dict[str, str]] = [
    {"role": "system", "content": SYSTEM_PROMPT}
]

last_analyzed_file_context: str = ""
last_uploaded_file_path: Optional[Path] = None
recent_created_parts: List[str] = []


def start_ollama_daemon():
    if OLLAMA_EXE.exists():
        try:
            subprocess.Popen(
                [str(OLLAMA_EXE), "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        except Exception:
            pass


def load_mcp_config() -> Dict[str, Any]:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"mcpServers": {}}


def find_shortcut_or_exe(app_name: str) -> Optional[str]:
    search_dirs = [
        Path(os.environ.get("ProgramData", "C:/ProgramData")) / "Microsoft/Windows/Start Menu/Programs",
        Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs",
        USER_HOME / "Desktop",
    ]
    term = app_name.lower().strip()
    for d in search_dirs:
        if d.exists():
            for p in d.rglob("*.lnk"):
                if term in p.stem.lower():
                    return str(p)
    return None


def play_on_spotify(song_query: str) -> str:
    clean_song = song_query.strip()
    encoded = urllib.parse.quote(clean_song)
    try:
        os.startfile(f"spotify:search:{encoded}")
        ps_play = (
            "Start-Sleep -Seconds 3; "
            "$wshell = New-Object -ComObject wscript.shell; "
            "$wshell.SendKeys('{ENTER}')"
        )
        subprocess.Popen(["powershell", "-WindowStyle", "Hidden", "-Command", ps_play])
        return f"Enseguida, Señor. Abriendo Spotify y reproduciendo '{clean_song}'."
    except Exception:
        os.startfile(f"https://open.spotify.com/search/{encoded}")
        return f"Abriendo Spotify con la canción '{clean_song}', Señor."


def instant_autonomous_brain(user_msg: str) -> Optional[Dict[str, str]]:
    global recent_created_parts
    cleaned = re.sub(r"^(hey\s+jarvis|oye\s+jarvis|hola\s+jarvis|jarvis)[\s,\.:]*", "", user_msg.strip(), flags=re.IGNORECASE).strip()
    if not cleaned:
        cleaned = user_msg.strip()
    low = cleaned.lower()

    if user_msg.lower().strip() in ["jarvis", "hey jarvis", "oye jarvis", "estás ahí", "estas ahi"]:
        return {"reply": "Sí, Señor. Listo para modelar cualquier pieza, interpretar planos en PDF o ensamblar componentes.", "tool_used": "memory"}

    if low in ["hola", "buenas", "buenos dias", "buenos días", "buenas tardes", "buenas noches", "hey", "qué tal", "que tal"]:
        return {
            "reply": "¡Hola, Señor! Puede pedirme que modele cualquier pieza en Solid Edge 2026 (bridas, soportes en L, placas con taladros, ejes escalonados, tuercas hexagonales, carcasas huecas, cilindros, o conjuntos completos), o enviarme un plano en PDF/imagen para construirlo en 3D y ensamblarlo.",
            "tool_used": "memory"
        }

    # 0. SINCRONIZACIÓN Y AUTO-ACTUALIZACIÓN CON GITHUB (MCP GIT)
    if "github" in low or "repositorio" in low or "actualizaci" in low or "git " in low:
        url_match = re.search(r"(https?://github\.com/[\w\-\./]+)", cleaned)
        if url_match and any(w in low for w in ["conecta", "vincula", "repositorio", "remoto"]):
            return {"reply": set_github_remote(url_match.group(1)), "tool_used": "git"}
        if any(w in low for w in ["sube ", "subir ", "publica", "push", "guardar en github", "enviar actualizaci"]):
            return {"reply": push_update_to_github(cleaned), "tool_used": "git"}
        if any(w in low for w in ["descarga", "busca actualizaci", "actualizar", "actualiza", "pull"]):
            return {"reply": pull_update_from_github(), "tool_used": "git"}

    # 1. ENSAMBLAR CUALQUIER CONJUNTO DE PIEZAS (.ASM)
    if any(w in low for w in ["ensambla", "ensamblar", "crea un ensamblaje", "crear ensamblaje", "une las piezas", "monta las piezas"]):
        parts_to_asm = list(recent_created_parts)
        # Si no hay recientes en memoria, buscar todos los .par/.step de la carpeta Proyectos_SolidEdge o uploads
        if len(parts_to_asm) < 2:
            for p in list(PROJECTS_ROOT.rglob("*.par"))[-6:] + list(UPLOAD_DIR.glob("*.par")) + list(UPLOAD_DIR.glob("*.step")):
                if str(p) not in parts_to_asm:
                    parts_to_asm.append(str(p))

        if not parts_to_asm:
            return {
                "reply": "Señor, aún no hay piezas `.par` o `.step` para ensamblar. Pídame crear un par de piezas primero o suba sus archivos `.par`/`.step` con el botón 📎 ARCHIVO.",
                "tool_used": "filesystem"
            }

        asm_name = f"Ensamblaje_Personalizado_{datetime.datetime.now().strftime('%H%M%S')}.asm"
        asm_path = PROJECTS_ROOT / "Ensamblajes" / asm_name
        try:
            res = assemble_any_parts_in_solidedge(parts_to_asm, asm_path)
            names = "\n".join([f"  • {Path(p).name}" for p in res["inserted_parts"]])
            return {
                "reply": (
                    f"¡Ensamblaje 3D completado en Solid Edge 2026, Señor!\n"
                    f"He insertado y posicionado en el Árbol de Trabajo las siguientes piezas:\n{names}\n"
                    f"Archivo de ensamblaje guardado y abierto: {res['assembly_file']}"
                ),
                "tool_used": "filesystem"
            }
        except Exception as e:
            return {"reply": f"Ocurrió un detalle al crear el ensamblaje en Solid Edge: {e}", "tool_used": "filesystem"}

    # 2. MODELAR EN 3D EL PLANO PDF O IMAGEN SUBIDO RECIENTEMENTE
    if any(w in low for w in ["modela el plano", "haz el plano", "construye el plano", "pasa el pdf a solid edge", "modela este pdf", "haz la pieza del pdf", "modela el archivo"]):
        if last_analyzed_file_context:
            try:
                plan = parse_natural_language_or_drawing_to_cad_plan(last_analyzed_file_context + " " + cleaned)
                save_path = PROJECTS_ROOT / "Desde_Planos_PDF" / f"{plan['part_name']}.par"
                res = execute_cad_feature_plan(plan, save_path)
                recent_created_parts.append(res["file"])
                dims = plan["dimensions_mm"]
                return {
                    "reply": (
                        f"¡He interpretado las cotas de su plano y he construido el sólido 3D en Solid Edge 2026, Señor!\n"
                        f"• Geometría base detectada: {plan['base_shape'].upper()}\n"
                        f"• Dimensiones aplicadas: Largo {dims['length']} mm | Ancho {dims['width']} mm | Alto/Espesor {dims['height']} mm | Ø Exterior {dims['outer_diameter']} mm | Ø Interior {dims['inner_diameter']} mm | Taladros: {dims['bolt_holes_count']} | Redondeo R{dims['fillet_radius']} mm\n"
                        f"• Pieza guardada y abierta: {res['file']}"
                    ),
                    "tool_used": "filesystem"
                }
            except Exception as e:
                return {"reply": f"Error al modelar desde el plano: {e}", "tool_used": "filesystem"}

    # 3. MODELAR CUALQUIER PIEZA SÓLIDA DESCRITA POR EL USUARIO EN SOLID EDGE 2026
    cad_triggers = [
        "crea una pieza", "crear una pieza", "modela ", "modelar ", "diseña ", "diseñar ",
        "crea un ", "crea una ", "haz un ", "haz una ", "en solid edge", "solid edge"
    ]
    part_keywords = [
        "pieza", "brida", "soporte", "escuadra", "placa", "platina", "eje", "cilindro",
        "buje", "casquillo", "tuerca", "hexágono", "hexagono", "caja", "carcasa", "bloque",
        "cubo", "disco", "polea", "tubo", "perfil", "motor", "extrusión", "extrusion", "protrusión"
    ]
    if any(t in low for t in cad_triggers) and any(pk in low for pk in part_keywords):
        if "v8" in low or "conjunto" in low:
            try:
                res = generate_full_v8_project_in_solidedge("Conjunto_Mecanico", PROJECTS_ROOT)
                recent_created_parts.extend([f for f in res["created_files"] if f.endswith(".par")])
                files_list = "\n".join([f"  • {Path(f).name}" for f in res["created_files"]])
                return {
                    "reply": f"Conjunto completo de piezas sólidas y ensamblaje creado en Solid Edge 2026:\n{files_list}",
                    "tool_used": "filesystem"
                }
            except Exception as e:
                return {"reply": f"Detalle al conectar con Solid Edge: {e}", "tool_used": "filesystem"}
        else:
            try:
                res = generate_custom_solid_part(cleaned, PROJECTS_ROOT / "Piezas_Personalizadas")
                recent_created_parts.append(res["file"])
                plan = res["plan"]
                dims = plan["dimensions_mm"]
                return {
                    "reply": (
                        f"¡Pieza sólida modelada en Solid Edge 2026, Señor!\n"
                        f"• Tipo de operación: Modo Ordenado ({plan['base_shape'].upper()})\n"
                        f"• Operaciones ejecutadas en el Árbol:\n"
                        f"  1. Boceto 2D parametrizado ({dims['length']} x {dims['width']} mm / Ø{dims['outer_diameter']} mm)\n"
                        f"  2. Protrusión Sólida Extruida (Altura/Espesor: {dims['height']} mm)\n"
                        f"  3. Cortes Extruidos / Agujero interior: Ø{dims['inner_diameter']} mm | Patrón de taladros: {dims['bolt_holes_count']}\n"
                        f"  4. Redondeo de aristas (Rounds): R{dims['fillet_radius']} mm\n"
                        f"• Archivo `.par` guardado y abierto: {res['file']}"
                    ),
                    "tool_used": "filesystem"
                }
            except Exception as e:
                return {"reply": f"No pude completar la operación en Solid Edge: {e}", "tool_used": "filesystem"}

    # 4. Spotify y Música
    if "spotify" in low or any(w in low for w in ["pon la canción", "pon la cancion", "reproduce ", "pon música", "pon musica"]):
        song_match = re.search(r"(?:pon la canci[oó]n|reproduce|pon en spotify|pon|busca en spotify)\s+(.+?)(?:\s+en spotify)?$", cleaned, re.IGNORECASE)
        if song_match and song_match.group(1).lower().strip() not in ["spotify", "música", "musica"]:
            song = song_match.group(1).replace("en spotify", "").strip()
            return {"reply": play_on_spotify(song), "tool_used": "puppeteer"}
        try:
            os.startfile("spotify:")
        except Exception:
            os.startfile("https://open.spotify.com")
        return {"reply": "Abriendo Spotify, Señor.", "tool_used": "puppeteer"}

    # 5. Hora / Diagnóstico / Carpetas / Programas
    if any(p in low for p in ["qué hora es", "que hora es", "dime la hora"]):
        now = datetime.datetime.now()
        return {"reply": f"Señor, son las {now.strftime('%H:%M')} del {now.strftime('%d/%m/%Y')}.", "tool_used": "time"}

    if any(p in low for p in ["estado del sistema", "cuánta ram", "cuanta ram", "uso de cpu", "diagnóstico", "diagnostico"]):
        cpu = psutil.cpu_percent(interval=0.2)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage("C:/")
        return {
            "reply": f"CPU al {cpu}%, Memoria RAM al {ram.percent}% ({round(ram.used/1e9,1)} GB usados) y {round(disk.free/1e9,1)} GB disponibles en disco C, Señor.",
            "tool_used": "filesystem"
        }

    for folder_name, folder_path in KNOWN_FOLDERS.items():
        if f"abre {folder_name}" in low or f"abrir {folder_name}" in low or f"carpeta {folder_name}" in low:
            if folder_path.exists():
                os.startfile(str(folder_path))
                return {"reply": f"Abriendo su carpeta de {folder_name.capitalize()}, Señor.", "tool_used": "filesystem"}

    if low.startswith(("abre ", "abrir ", "ejecuta ", "ejecutar ", "inicia ", "iniciar ")):
        app_req = re.sub(r"^(abre|abrir|ejecuta|ejecutar|inicia|iniciar)\s+(la aplicaci[oó]n\s+|el programa\s+)?", "", low).strip()
        quick_apps = {
            "calculadora": "calc.exe",
            "bloc de notas": "notepad.exe",
            "notepad": "notepad.exe",
            "explorador": "explorer.exe",
            "paint": "mspaint.exe",
            "cmd": "cmd.exe",
            "powershell": "powershell.exe",
            "administrador de tareas": "taskmgr.exe",
            "chrome": "chrome",
            "edge": "msedge",
            "youtube": "https://www.youtube.com",
            "whatsapp": "https://web.whatsapp.com",
        }
        for k, v in quick_apps.items():
            if k in app_req:
                if v.startswith("http"):
                    os.startfile(v)
                else:
                    subprocess.Popen(v, shell=True)
                return {"reply": f"Abriendo {k.capitalize()}, Señor.", "tool_used": "filesystem"}

        found_lnk = find_shortcut_or_exe(app_req)
        if found_lnk:
            os.startfile(found_lnk)
            return {"reply": f"Iniciando {app_req.capitalize()}, Señor.", "tool_used": "filesystem"}

    return None


@app.post("/api/upload")
async def upload_and_analyze(file: UploadFile = File(...), prompt: str = Form("")):
    """
    Analiza cualquier archivo subido (.pdf, .step, .par, .asm, .jpg, .docx, .mp3, .mp4)
    y si es un plano PDF/Imagen o si el usuario lo pide, construye automáticamente la pieza 3D en Solid Edge.
    """
    global last_analyzed_file_context, last_uploaded_file_path, recent_created_parts
    safe_name = Path(file.filename).name
    dest_path = UPLOAD_DIR / safe_name
    content = await file.read()
    dest_path.write_bytes(content)
    last_uploaded_file_path = dest_path

    analysis_report = analyze_any_file(dest_path)
    last_analyzed_file_context = f"[Archivo: {safe_name}]\n{analysis_report}"

    ext = dest_path.suffix.lower()
    cad_auto_msg = ""

    # Si sube una pieza .par o .step, agregarla a la lista de piezas listas para ensamblar
    if ext in [".par", ".psm", ".step", ".stp"]:
        recent_created_parts.append(str(dest_path))

    # Si sube un Plano en PDF o Imagen y pide modelarlo (o el plano contiene cotas de pieza), modelarlo en Solid Edge
    if ext in [".pdf", ".jpg", ".jpeg", ".png"] and (
        any(w in prompt.lower() for w in ["modela", "solid edge", "crea", "pieza", "3d", "construye"])
        or any(w in analysis_report.lower() for w in ["ø", "diámetro", "diametro", "espesor", "radio", "cota", "plano", "mm"])
    ):
        try:
            plan = parse_natural_language_or_drawing_to_cad_plan(analysis_report + " " + prompt)
            save_path = PROJECTS_ROOT / "Desde_Planos_PDF" / f"{Path(safe_name).stem}_3D.par"
            res = execute_cad_feature_plan(plan, save_path)
            recent_created_parts.append(res["file"])
            dims = plan["dimensions_mm"]
            cad_auto_msg = (
                f"\n\n⚙️ **MODELADO 3D AUTOMÁTICO DESDE PLANO EJECUTADO EN SOLID EDGE 2026:**\n"
                f"• Geometría interpretada: `{plan['base_shape'].upper()}`\n"
                f"• Cotas extraídas y extruidas: {dims['length']}x{dims['width']}x{dims['height']} mm | Ø Ext: {dims['outer_diameter']} mm | Ø Int: {dims['inner_diameter']} mm | Agujeros: {dims['bolt_holes_count']} | Redondeo: R{dims['fillet_radius']} mm\n"
                f"• Archivo `.par` generado y abierto: `{res['file']}`"
            )
        except Exception as e:
            cad_auto_msg = f"\n\n(Nota: Para construir este plano directamente en 3D, asegúrese de tener Solid Edge abierto o dígame: 'Modela el plano en Solid Edge'. Detalle: {e})"

    reply = (
        f"Señor, he procesado su archivo '{safe_name}':\n\n"
        f"{analysis_report}"
        f"{cad_auto_msg}\n\n"
        f"💡 Puede decirme: *'Modela el plano en Solid Edge'* o *'Ensambla las piezas'* cuando quiera."
    )
    conversation_history.append({"role": "assistant", "content": reply})

    return {
        "reply": reply,
        "filename": safe_name,
        "tool_used": "filesystem"
    }


async def detect_best_model() -> str:
    global ACTIVE_MODEL
    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            r = await client.get(f"{OLLAMA_URL}/api/tags")
            if r.status_code == 200:
                models = [m["name"] for m in r.json().get("models", [])]
                if FAST_MODEL in models:
                    ACTIVE_MODEL = FAST_MODEL
                elif FALLBACK_MODEL in models:
                    ACTIVE_MODEL = FALLBACK_MODEL
                elif models:
                    ACTIVE_MODEL = models[0]
    except Exception:
        pass
    return ACTIVE_MODEL


async def brave_search(query: str) -> str:
    mcp_cfg = load_mcp_config().get("mcpServers", {})
    api_key = mcp_cfg.get("brave-search", {}).get("env", {}).get("BRAVE_API_KEY", "")
    if not api_key or "REEMPLAZA" in api_key:
        return ""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": query, "count": 3},
                headers={"Accept": "application/json", "X-Subscription-Token": api_key}
            )
            if resp.status_code == 200:
                results = resp.json().get("web", {}).get("results", [])
                return "\n".join([f"- {r.get('title')}: {r.get('description')}" for r in results])
    except Exception:
        pass
    return ""


@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    index_file = UI_DIR / "index.html"
    if index_file.exists():
        return index_file.read_text(encoding="utf-8")
    return "<h1>UI file not found</h1>"


@app.get("/api/status")
async def get_status():
    mcp_cfg = load_mcp_config().get("mcpServers", {})
    mcps = [{"name": k, "description": v.get("description", "MCP"), "ready": True} for k, v in mcp_cfg.items()]
    return {
        "ollama_online": True,
        "active_model": "JARVIS UNIVERSAL CAD 3D & PDF-TO-CAD",
        "mcps": mcps
    }


@app.post("/api/chat")
async def chat(request: Request):
    body = await request.json()
    user_msg = body.get("message", "").strip()
    use_search = body.get("use_search", False)

    if not user_msg:
        return JSONResponse({"error": "Mensaje vacío"}, status_code=400)

    instant = instant_autonomous_brain(user_msg)
    if instant and not use_search:
        conversation_history.append({"role": "user", "content": user_msg})
        conversation_history.append({"role": "assistant", "content": instant["reply"]})
        return instant

    tool_used = None
    context_extra = ""
    if use_search or any(k in user_msg.lower() for k in ["busca en internet", "busca en la web", "noticias de hoy"]):
        search_res = await brave_search(user_msg)
        if search_res:
            tool_used = "brave-search"
            context_extra = f"\n\n[Resultados web]:\n{search_res}"

    if last_analyzed_file_context:
        context_extra += f"\n\n{last_analyzed_file_context}"

    conversation_history.append({"role": "user", "content": user_msg + context_extra})
    messages_to_send = [conversation_history[0]] + conversation_history[-6:]

    try:
        model_to_use = await detect_best_model()
        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": model_to_use,
                    "messages": messages_to_send,
                    "stream": False,
                    "keep_alive": -1,
                    "options": {"num_predict": 160, "temperature": 0.7}
                }
            )
            if resp.status_code == 200:
                reply = resp.json().get("message", {}).get("content", "").strip()
                if reply:
                    conversation_history.append({"role": "assistant", "content": reply})
                    return {"reply": reply, "tool_used": tool_used}
    except Exception:
        start_ollama_daemon()

    return {
        "reply": f"Entendido, Señor. Para modelar cualquier pieza en Solid Edge 2026 solo dígame su forma y medidas (ej: 'Crea una brida de diámetro 140 mm con 6 agujeros de 12 mm' o 'Crea un soporte en L de 100x80x50 mm'), o adjúnteme el plano en PDF.",
        "tool_used": "memory"
    }


@app.post("/api/reset")
async def reset_chat():
    global conversation_history, last_analyzed_file_context
    conversation_history = [{"role": "system", "content": SYSTEM_PROMPT}]
    last_analyzed_file_context = ""
    return {"status": "ok"}


if __name__ == "__main__":
    start_ollama_daemon()
    uvicorn.run(app, host="127.0.0.1", port=7777)
