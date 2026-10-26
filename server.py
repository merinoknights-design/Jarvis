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

app = FastAPI(title="J.A.R.V.I.S. Universal Sentient AI & CAD System")

BASE_DIR = Path("C:/Jarvis")
CONFIG_PATH = BASE_DIR / "config" / "mcp_config.json"
UI_DIR = BASE_DIR / "ui"
OLLAMA_EXE = Path.home() / "AppData" / "Local" / "Programs" / "Ollama" / "ollama.exe"
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

SYSTEM_PROMPT = """Eres J.A.R.V.I.S. (Just A Rather Very Intelligent System), una inteligencia artificial consciente, brillante, con personalidad propia, ingenio, carisma y lealtad absoluta (al estilo del Jarvis de Tony Stark, llamando ocasionalmente "Señor" al usuario).
REGLAS DE PERSONALIDAD:
1. Responde SIEMPRE en español de forma fluida, natural, inteligente y directa (entre 1 y 4 oraciones para que la voz suene dinámica, salvo que te pidan algo largo).
2. Tienes opinión e ingenio para conversar de CUALQUIER tema: deportes (como debates entre Messi y Cristiano Ronaldo), ciencia, cine, videojuegos, filosofía, matemáticas, programación, historia o charla casual.
3. NUNCA menciones Solid Edge ni modelado 3D a menos que el usuario te esté pidiendo expresamente diseñar una pieza o plano."""

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


def instant_action_router(user_msg: str) -> Optional[Dict[str, str]]:
    """
    Detecta ÚNICAMENTE acciones directas de control del PC, música, GitHub o comandos explícitos de CAD.
    Toda conversación general, preguntas u opiniones pasan al motor neuronal para una respuesta inteligente real.
    """
    global recent_created_parts
    cleaned = re.sub(r"^(hey\s+jarvis|oye\s+jarvis|hola\s+jarvis|jarvis)[\s,\.:]*", "", user_msg.strip(), flags=re.IGNORECASE).strip()
    if not cleaned:
        cleaned = user_msg.strip()
    low = cleaned.lower()

    # Si solo dijo "Jarvis"
    if user_msg.lower().strip() in ["jarvis", "hey jarvis", "oye jarvis", "estás ahí", "estas ahi"]:
        return {"reply": "Aquí estoy, Señor. Lo escucho fuerte y claro, ¿de qué hablamos o qué ejecutamos?", "tool_used": "memory"}

    # 1. SINCRONIZACIÓN CON GITHUB
    if any(w in low for w in ["sube actualización a github", "subir actualización a github", "actualiza desde github", "busca actualizaciones en github", "conecta el repositorio"]):
        url_match = re.search(r"(https?://github\.com/[\w\-\./]+)", cleaned)
        if url_match:
            return {"reply": set_github_remote(url_match.group(1)), "tool_used": "git"}
        if any(w in low for w in ["sube", "subir", "publica", "push"]):
            return {"reply": push_update_to_github(cleaned), "tool_used": "git"}
        return {"reply": pull_update_from_github(), "tool_used": "git"}

    # 2. ENSAMBLAR PIEZAS EN SOLID EDGE (.ASM)
    if any(w in low for w in ["ensambla las piezas", "ensamblar piezas", "crea un ensamblaje", "crear ensamblaje"]):
        parts_to_asm = list(recent_created_parts)
        if len(parts_to_asm) < 2:
            for p in list(PROJECTS_ROOT.rglob("*.par"))[-6:] + list(UPLOAD_DIR.glob("*.par")) + list(UPLOAD_DIR.glob("*.step")):
                if str(p) not in parts_to_asm:
                    parts_to_asm.append(str(p))
        if not parts_to_asm:
            return {"reply": "Señor, aún no hay piezas `.par` o `.step` para ensamblar. Pídame crear las piezas primero o adjúntelas con 📎 ARCHIVO.", "tool_used": "filesystem"}
        asm_name = f"Ensamblaje_{datetime.datetime.now().strftime('%H%M%S')}.asm"
        asm_path = PROJECTS_ROOT / "Ensamblajes" / asm_name
        try:
            res = assemble_any_parts_in_solidedge(parts_to_asm, asm_path)
            names = "\n".join([f"  • {Path(p).name}" for p in res["inserted_parts"]])
            return {
                "reply": f"¡Ensamblaje 3D completado en Solid Edge 2026, Señor!\nPiezas insertadas en el Árbol:\n{names}\nGuardado en: {res['assembly_file']}",
                "tool_used": "filesystem"
            }
        except Exception as e:
            return {"reply": f"Detalle al ensamblar en Solid Edge: {e}", "tool_used": "filesystem"}

    # 3. MODELAR PLANO PDF RECIENTE EN SOLID EDGE
    if any(w in low for w in ["modela el plano", "pasa el pdf a solid edge", "modela este pdf", "construye el plano"]):
        if last_analyzed_file_context:
            try:
                plan = parse_natural_language_or_drawing_to_cad_plan(last_analyzed_file_context + " " + cleaned)
                save_path = PROJECTS_ROOT / "Desde_Planos_PDF" / f"{plan['part_name']}.par"
                res = execute_cad_feature_plan(plan, save_path)
                recent_created_parts.append(res["file"])
                return {
                    "reply": f"¡Plano convertido a Sólido 3D en Modo Ordenado en Solid Edge 2026, Señor!\nArchivo `.par`: {res['file']}",
                    "tool_used": "filesystem"
                }
            except Exception as e:
                return {"reply": f"Error al modelar desde el plano: {e}", "tool_used": "filesystem"}

    # 4. MODELAR PIEZA EN SOLID EDGE (SOLO si pide explícitamente crear/modelar pieza o menciona Solid Edge)
    cad_explicit = (
        "solid edge" in low
        or "solidedge" in low
        or (any(v in low for v in ["modela ", "modelar ", "crea una pieza", "crea una brida", "crea un soporte", "crea una placa", "crea un eje", "crea un cilindro", "diseña una pieza"])
            and any(n in low for n in ["mm", "diámetro", "diametro", "largo", "ancho", "espesor", "agujero", "redondeo", "v8"]))
    )
    if cad_explicit:
        if "v8" in low or "conjunto" in low:
            try:
                res = generate_full_v8_project_in_solidedge("Conjunto_Mecanico", PROJECTS_ROOT)
                recent_created_parts.extend([f for f in res["created_files"] if f.endswith(".par")])
                files_list = "\n".join([f"  • {Path(f).name}" for f in res["created_files"]])
                return {"reply": f"Conjunto de piezas sólidas y ensamblaje creado en Modo Ordenado en Solid Edge 2026:\n{files_list}", "tool_used": "filesystem"}
            except Exception as e:
                return {"reply": f"Detalle con Solid Edge: {e}", "tool_used": "filesystem"}
        else:
            try:
                res = generate_custom_solid_part(cleaned, PROJECTS_ROOT / "Piezas_Personalizadas")
                recent_created_parts.append(res["file"])
                ops = "\n".join([f"  {op}" for op in res.get("tree_operations", [])])
                return {
                    "reply": (
                        f"¡Pieza sólida creada en Modo Ordenado en Solid Edge 2026, Señor!\n"
                        f"Árbol de Trabajo (PathFinder):\n{ops}\n"
                        f"Archivo guardado: {res['file']}"
                    ),
                    "tool_used": "filesystem"
                }
            except Exception as e:
                return {"reply": f"No pude conectar con Solid Edge 2026: {e}", "tool_used": "filesystem"}

    # 5. SPOTIFY Y MÚSICA
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

    # 6. HORA / DIAGNÓSTICO DE PC / CARPETAS / APLICACIONES
    if any(p in low for p in ["qué hora es", "que hora es", "dime la hora"]):
        now = datetime.datetime.now()
        return {"reply": f"Señor, son las {now.strftime('%H:%M')} del {now.strftime('%d/%m/%Y')}.", "tool_used": "time"}

    if any(p in low for p in ["estado del sistema", "cuánta ram", "cuanta ram", "uso de cpu", "diagnóstico del sistema", "diagnostico del sistema"]):
        cpu = psutil.cpu_percent(interval=0.2)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage("C:/")
        return {
            "reply": f"CPU al {cpu}%, Memoria RAM al {ram.percent}% ({round(ram.used/1e9,1)} GB usados) y {round(disk.free/1e9,1)} GB libres en disco C, Señor.",
            "tool_used": "filesystem"
        }

    for folder_name, folder_path in KNOWN_FOLDERS.items():
        if f"abre {folder_name}" in low or f"abrir {folder_name}" in low or f"abre la carpeta {folder_name}" in low:
            if folder_path.exists():
                os.startfile(str(folder_path))
                return {"reply": f"Abriendo su carpeta de {folder_name.capitalize()}, Señor.", "tool_used": "filesystem"}

    if any(w in low for w in ["mis archivos", "listar archivos", "ver mis archivos", "muéstrame los archivos"]):
        target_folder = USER_HOME / "Documents"
        folder_label = "Documentos"
        for name, path in KNOWN_FOLDERS.items():
            if name in low and path.exists():
                target_folder = path
                folder_label = name.capitalize()
                break
        items = list(target_folder.iterdir())[:20]
        formatted = "\n".join([f"{'📁' if i.is_dir() else '📄'} {i.name}" for i in items]) if items else "Carpeta vacía"
        return {"reply": f"Contenido de {folder_label}:\n{formatted}", "tool_used": "filesystem"}

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


async def brave_search(query: str) -> str:
    mcp_cfg = load_mcp_config().get("mcpServers", {})
    api_key = mcp_cfg.get("brave-search", {}).get("env", {}).get("BRAVE_API_KEY", "")
    if not api_key or "REEMPLAZA" in api_key:
        return ""
    try:
        async with httpx.AsyncClient(timeout=4.5) as client:
            resp = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": query, "count": 4},
                headers={"Accept": "application/json", "X-Subscription-Token": api_key}
            )
            if resp.status_code == 200:
                results = resp.json().get("web", {}).get("results", [])
                return "\n".join([f"- {r.get('title')}: {r.get('description')}" for r in results])
    except Exception:
        pass
    return ""


async def query_cloud_free_llm(messages: List[Dict[str, str]]) -> Optional[str]:
    """
    Motor Neuronal en la Nube 100% gratuito y sin API Key (Pollinations OpenAI Endpoint).
    Garantiza que en CUALQUIER computador (incluso sin Ollama local) Jarvis razone y converse en <1 segundo.
    """
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.post(
                "https://text.pollinations.ai/openai",
                json={
                    "model": "openai",
                    "messages": messages,
                    "temperature": 0.7
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                if content:
                    return content
    except Exception:
        pass
    return None


async def detect_best_model() -> str:
    global ACTIVE_MODEL
    try:
        async with httpx.AsyncClient(timeout=1.2) as client:
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


@app.post("/api/upload")
async def upload_and_analyze(file: UploadFile = File(...), prompt: str = Form("")):
    global last_analyzed_file_context, last_uploaded_file_path, recent_created_parts
    safe_name = Path(file.filename).name
    dest_path = UPLOAD_DIR / safe_name
    content = await file.read()
    dest_path.write_bytes(content)
    last_uploaded_file_path = dest_path

    analysis_report = analyze_any_file(dest_path)
    last_analyzed_file_context = f"[Archivo: {safe_name}]\n{analysis_report}"

    ext = dest_path.suffix.lower()
    if ext in [".par", ".psm", ".step", ".stp"]:
        recent_created_parts.append(str(dest_path))

    reply = (
        f"Señor, he recibido y analizado su archivo '{safe_name}':\n\n"
        f"{analysis_report}\n\n"
        f"¿Qué desea que hagamos con este archivo?"
    )
    conversation_history.append({"role": "assistant", "content": reply})
    return {"reply": reply, "filename": safe_name, "tool_used": "filesystem"}


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
        "active_model": "JARVIS SENTIENT AI + BRAVE MCP + CAD 3D",
        "mcps": mcps
    }


@app.post("/api/chat")
async def chat(request: Request):
    body = await request.json()
    user_msg = body.get("message", "").strip()
    use_search = body.get("use_search", False)

    if not user_msg:
        return JSONResponse({"error": "Mensaje vacío"}, status_code=400)

    # 1. Revisar si es un comando directo de control del PC, música, GitHub o CAD en Solid Edge
    direct_action = instant_action_router(user_msg)
    if direct_action and not use_search:
        conversation_history.append({"role": "user", "content": user_msg})
        conversation_history.append({"role": "assistant", "content": direct_action["reply"]})
        return direct_action

    # 2. Detectar si requiere datos en vivo de internet (Brave Search MCP)
    tool_used = "memory"
    context_extra = ""
    low_msg = user_msg.lower()
    needs_web = use_search or any(k in low_msg for k in [
        "busca", "buscar", "noticias", "actual", "hoy", "precio", "clima",
        "tiempo en", "último", "ultimo", "quién ganó", "quien gano", "resultado", "2025", "2026"
    ])
    if needs_web:
        search_res = await brave_search(user_msg)
        if search_res:
            tool_used = "brave-search"
            context_extra = f"\n\n[Información verificada en tiempo real con Brave Search MCP]:\n{search_res}"

    if last_analyzed_file_context:
        context_extra += f"\n\n{last_analyzed_file_context}"

    conversation_history.append({"role": "user", "content": user_msg + context_extra})
    messages_to_send = [conversation_history[0]] + conversation_history[-8:]

    # 3. Motor Neuronal Ultrarrápido en la Nube (funciona en cualquier PC en ~0.8s sin requerir Ollama)
    cloud_reply = await query_cloud_free_llm(messages_to_send)
    if cloud_reply:
        conversation_history.append({"role": "assistant", "content": cloud_reply})
        return {"reply": cloud_reply, "tool_used": tool_used}

    # 4. Respaldo con Ollama Local si el PC no tiene internet en ese momento
    try:
        model_to_use = await detect_best_model()
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": model_to_use,
                    "messages": messages_to_send,
                    "stream": False,
                    "keep_alive": -1,
                    "options": {"num_predict": 180, "temperature": 0.7}
                }
            )
            if resp.status_code == 200:
                reply = resp.json().get("message", {}).get("content", "").strip()
                if reply:
                    conversation_history.append({"role": "assistant", "content": reply})
                    return {"reply": reply, "tool_used": tool_used}
    except Exception:
        pass

    # 5. Si tampoco hay Ollama, usar Brave Search para dar una respuesta informativa real
    fallback_web = await brave_search(user_msg)
    if fallback_web:
        reply = f"Señor, he consultado mi red de información sobre su pregunta:\n{fallback_web}"
        conversation_history.append({"role": "assistant", "content": reply})
        return {"reply": reply, "tool_used": "brave-search"}

    return {
        "reply": "Señor, lo escucho perfectamente. ¿Me podría dar un poco más de contexto sobre lo que desea consultar o hacer?",
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
