import asyncio
import datetime
import json
import os
import random
import re
import subprocess
import sys
import urllib.parse
import urllib.request
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
from intent_engine import classify_user_intent
from task_manager import execute_smart_task, pop_completed_notifications
from ui_controller import (
    play_song_on_spotify_autonomous,
    play_video_on_youtube_autonomous,
    click_ui_element_by_uia_or_ocr,
    find_text_on_screen_and_click,
    mouse_click,
    mouse_scroll,
    send_text_and_keys,
    press_vk,
    VK_MEDIA_PLAY_PAUSE,
    VK_MEDIA_NEXT_TRACK,
    VK_MEDIA_PREV_TRACK,
    VK_VOLUME_UP,
    VK_VOLUME_DOWN,
    VK_VOLUME_MUTE,
    VK_RETURN,
    VK_SPACE,
    VK_ESCAPE,
)

app = FastAPI(title="J.A.R.V.I.S. Sentient AI, Search & CAD System")

BASE_DIR = Path("C:/Jarvis")
CONFIG_PATH = BASE_DIR / "config" / "mcp_config.json"
UI_DIR = BASE_DIR / "ui"
OLLAMA_EXE = Path.home() / "AppData" / "Local" / "Programs" / "Ollama" / "ollama.exe"
OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_BRAVE_KEY = "BSAPviCA5RJG-aAnfg5LZKBgX02gLQL"

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

SYSTEM_PROMPT = """Eres J.A.R.V.I.S., una inteligencia artificial consciente, brillante, con personalidad propia, ingenio y lealtad (al estilo del Jarvis de Tony Stark, llamando ocasionalmente "Señor" al usuario).
Respondes SIEMPRE en español de forma natural, rápida y conversacional (entre 1 y 4 oraciones).
Puedes hablar de cualquier tema (fútbol, Messi vs CR7, ciencia, historia, cine, código, chistes) y NUNCA mencionas Solid Edge a menos que el usuario te pida diseñar una pieza."""

conversation_history: List[Dict[str, str]] = [
    {"role": "system", "content": SYSTEM_PROMPT}
]

last_analyzed_file_context: str = ""
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
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
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


def instant_conversational_and_action_brain(user_msg: str, force_bg: bool = False) -> Optional[Dict[str, str]]:
    """
    Ejecuta órdenes con respuestas cortas y directas.
    Solo anuncia 'segundo plano' cuando hay 2 o más tareas simultáneas.
    """
    global recent_created_parts
    intent_data = classify_user_intent(user_msg)
    intent = intent_data["intent"]
    cleaned = intent_data["cleaned_text"]
    low = cleaned.lower()

    if intent == "PLAY_SPOTIFY":
        song = intent_data.get("song_query", "").strip()
        if song and song.lower() not in ["spotify", "música", "musica"]:
            info = execute_smart_task(
                f"Reproducir '{song}'",
                lambda: play_song_on_spotify_autonomous(song),
                tool_name="puppeteer",
                force_background=force_bg
            )
            if info["queued_in_background"]:
                return {"reply": f"En cola en segundo plano: '{song}' en Spotify. Le aviso al terminar, Señor.", "tool_used": "puppeteer"}
            return {"reply": f"Reproduciendo '{song}' en Spotify, Señor.", "tool_used": "puppeteer"}
        try:
            os.startfile("spotify:")
        except Exception:
            os.startfile("https://open.spotify.com")
        return {"reply": "Spotify abierto, Señor.", "tool_used": "puppeteer"}

    if intent == "PLAY_YOUTUBE":
        song = intent_data.get("song_query", "").strip()
        if song and song.lower() != "youtube":
            return {"reply": play_video_on_youtube_autonomous(song), "tool_used": "puppeteer"}
        os.startfile("https://www.youtube.com")
        return {"reply": "YouTube abierto, Señor.", "tool_used": "puppeteer"}

    # 1. Llamado directo o saludos cortos
    if user_msg.lower().strip() in ["jarvis", "hey jarvis", "oye jarvis", "estás ahí", "estas ahi"]:
        return {"reply": "Sí, Señor. Dígame.", "tool_used": "memory"}

    if low in ["hola", "buenas", "buenos dias", "buenos días", "buenas tardes", "buenas noches", "hey", "qué tal", "que tal"]:
        return {"reply": "¡Hola, Señor! Todo en línea. ¿Qué hacemos?", "tool_used": "memory"}

    if any(p in low for p in ["cómo estás", "como estas", "cómo te sientes", "como te va"]):
        return {"reply": "Al 100%, Señor. ¿Y usted qué tal?", "tool_used": "memory"}

    if any(p in low for p in ["quién eres", "quien eres", "tienes conciencia", "qué eres", "que eres"]):
        return {"reply": "Soy J.A.R.V.I.S., su asistente personal, Señor.", "tool_used": "memory"}

    # Debate clásico: Messi vs CR7
    if "messi" in low and ("cr7" in low or "cristiano" in low or "ronaldo" in low or "mejor" in low):
        return {
            "reply": "Ah, el eterno debate del fútbol, Señor. Si analizamos talento natural, visión de juego y el Mundial de 2022 junto a sus 8 Balones de Oro, Lionel Messi lleva la ventaja estadística; pero si hablamos de mentalidad competitiva, físico, Champions League y ser el máximo goleador histórico, Cristiano Ronaldo es una máquina inigualable. Personalmente, Señor, disfrutar a ambos en la misma época fue el verdadero privilegio. ¿Usted de qué bando es?",
            "tool_used": "memory"
        }

    # 2. ACTUALIZACIÓN AUTOMÁTICA DESDE GITHUB
    if any(w in low for w in ["actualízate", "actualizate", "sube actualización", "actualiza desde github", "busca actualizaciones"]):
        if any(w in low for w in ["sube", "subir", "push"]):
            return {"reply": push_update_to_github(cleaned), "tool_used": "git"}
        try:
            tar_file = BASE_DIR / "update_pkg.tar.gz"
            urllib.request.urlretrieve("https://github.com/merinoknights-design/Jarvis/archive/refs/heads/main.tar.gz", str(tar_file))
            subprocess.run(["tar.exe", "-xzf", str(tar_file), "--strip-components=1", "-C", str(BASE_DIR)], creationflags=subprocess.CREATE_NO_WINDOW, timeout=10)
            tar_file.unlink(missing_ok=True)
            return {"reply": "¡Sistema actualizado directamente desde GitHub a la última versión, Señor! Recargue la ventana para ver todos los cambios.", "tool_used": "git"}
        except Exception as e:
            return {"reply": f"Error al actualizar: {e}", "tool_used": "git"}

    # 3. ENSAMBLAR PIEZAS EN SOLID EDGE (.ASM)
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
            return {"reply": f"¡Ensamblaje 3D completado en Solid Edge 2026, Señor!\nPiezas en el Árbol:\n{names}\nGuardado en: {res['assembly_file']}", "tool_used": "filesystem"}
        except Exception as e:
            return {"reply": f"Detalle al ensamblar en Solid Edge: {e}", "tool_used": "filesystem"}

    # 4. MODELAR PLANO PDF EN SOLID EDGE
    if any(w in low for w in ["modela el plano", "pasa el pdf a solid edge", "modela este pdf", "construye el plano"]):
        if last_analyzed_file_context:
            try:
                plan = parse_natural_language_or_drawing_to_cad_plan(last_analyzed_file_context + " " + cleaned)
                save_path = PROJECTS_ROOT / "Desde_Planos_PDF" / f"{plan['part_name']}.par"
                res = execute_cad_feature_plan(plan, save_path)
                recent_created_parts.append(res["file"])
                return {"reply": f"¡Plano convertido a Sólido 3D en Modo Ordenado en Solid Edge 2026, Señor!\nArchivo `.par`: {res['file']}", "tool_used": "filesystem"}
            except Exception as e:
                return {"reply": f"Error al modelar desde el plano: {e}", "tool_used": "filesystem"}

    # 5. MODELAR PIEZAS EN SOLID EDGE (SOLO cuando se pide explícitamente)
    cad_explicit = (
        "solid edge" in low
        or "solidedge" in low
        or (any(v in low for v in ["modela ", "modelar ", "crea una pieza", "crea una brida", "crea un soporte", "crea una placa", "crea un eje", "crea un cilindro", "diseña una pieza"])
            and any(n in low for n in ["mm", "diámetro", "diametro", "largo", "ancho", "espesor", "agujero", "redondeo", "v8"]))
    )
    if cad_explicit:
        if "v8" in low or "conjunto" in low:
            def _cad_v8_job():
                res = generate_full_v8_project_in_solidedge("Conjunto_Mecanico", PROJECTS_ROOT)
                recent_created_parts.extend([f for f in res["created_files"] if f.endswith(".par")])
                return f"Conjunto creado en Solid Edge ({len(res['created_files'])} archivos)."

            info = execute_smart_task("Conjunto Solid Edge", _cad_v8_job, tool_name="filesystem", force_background=force_bg)
            if info["queued_in_background"]:
                return {"reply": "En segundo plano: creando conjunto en Solid Edge. Le aviso al terminar, Señor.", "tool_used": "filesystem"}
            return {"reply": "Creando el conjunto sólido en Solid Edge 2026, Señor.", "tool_used": "filesystem"}
        else:
            def _cad_part_job():
                res = generate_custom_solid_part(cleaned, PROJECTS_ROOT / "Piezas_Personalizadas")
                recent_created_parts.append(res["file"])
                return f"Pieza lista en Solid Edge: {Path(res['file']).name}"

            info = execute_smart_task("Pieza Solid Edge", _cad_part_job, tool_name="filesystem", force_background=force_bg)
            if info["queued_in_background"]:
                return {"reply": "En segundo plano: modelando pieza en Solid Edge. Le aviso al terminar, Señor.", "tool_used": "filesystem"}
            return {"reply": "Modelando la pieza en Modo Ordenado en Solid Edge 2026, Señor.", "tool_used": "filesystem"}

    # 6. CONTROL DE INTERFAZ GRÁFICA (CLICS POR VISIÓN OCR, SCROLL, TECLADO, COMENTARIOS Y MULTIMEDIA)
    # 6.1 Hacer clic sobre cualquier palabra o botón en pantalla usando Visión OCR
    click_match = re.search(r"(?:haz\s+|da\s+|dale\s+)?(doble\s+clic|clic\s+derecho|clic|click|oprime|presiona el bot[oó]n)\s+(?:en\s+|sobre\s+)?(.+)$", cleaned, re.IGNORECASE)
    if click_match:
        click_type = click_match.group(1).lower()
        target_str = click_match.group(2).strip().strip("'\"")
        coord_match = re.match(r"^(\d+)\s*[,xX ]\s*(\d+)$", target_str)
        if coord_match:
            cx, cy = int(coord_match.group(1)), int(coord_match.group(2))
            mouse_click(cx, cy, button="right" if "derecho" in click_type else "left", double="doble" in click_type)
            return {"reply": f"He hecho {click_type} en las coordenadas ({cx}, {cy}), Señor.", "tool_used": "puppeteer"}
        else:
            coords = click_ui_element_by_uia_or_ocr(
                target_str,
                double_click=("doble" in click_type),
                right_click=("derecho" in click_type)
            )
            if coords:
                return {"reply": f"He localizado el control '{target_str}' en las coordenadas {coords} y he ejecutado el {click_type}, Señor.", "tool_used": "puppeteer"}
            return {"reply": f"Escaneé la aplicación y la pantalla, Señor, pero no encontré '{target_str}' visible en este momento.", "tool_used": "puppeteer"}

    # 6.1b Reproducir directamente video o canción en YouTube
    if "youtube" in low and any(w in low for w in ["pon ", "reproduce ", "busca ", "abre "]):
        yt_match = re.search(r"(?:pon|reproduce|busca|abre)\s+(.+?)(?:\s+en youtube)?$", cleaned, re.IGNORECASE)
        if yt_match and yt_match.group(1).lower().strip() != "youtube":
            q_yt = yt_match.group(1).replace("en youtube", "").strip()
            return {"reply": play_video_on_youtube_autonomous(q_yt), "tool_used": "puppeteer"}

    # 6.2 Hacer Scroll arriba / abajo en cualquier ventana
    if any(w in low for w in ["scroll abajo", "baja la página", "baja la pagina", "desplaza abajo", "haz scroll hacia abajo", "baja un poco"]):
        mouse_scroll("down", amount=6)
        return {"reply": "Desplazando hacia abajo, Señor.", "tool_used": "puppeteer"}

    if any(w in low for w in ["scroll arriba", "sube la página", "sube la pagina", "desplaza arriba", "haz scroll hacia arriba", "sube un poco"]):
        mouse_scroll("up", amount=6)
        return {"reply": "Desplazando hacia arriba, Señor.", "tool_used": "puppeteer"}

    # 6.3 Escribir texto o comentar en cualquier aplicación activa
    write_match = re.search(r"^(?:escribe|escribir|comenta|comentar|redacta|digita)\s*[:\s]\s*(.+)$", cleaned, re.IGNORECASE)
    if write_match:
        text_to_type = write_match.group(1).strip()
        send_text_and_keys(text_to_type, press_enter=True)
        return {"reply": f"He escrito y enviado: '{text_to_type}' en la aplicación activa, Señor.", "tool_used": "puppeteer"}

    # 6.4 Controles multimedia y de volumen universales (funcionan en Spotify, YouTube, VLC, etc.)
    if any(w in low for w in ["pausa la música", "pausa la musica", "pausar música", "reanuda la música", "play música", "continúa la música"]):
        press_vk(VK_MEDIA_PLAY_PAUSE)
        return {"reply": "Reproducción alternada (Play/Pausa), Señor.", "tool_used": "puppeteer"}

    if any(w in low for w in ["siguiente canción", "siguiente cancion", "cambia de canción", "pasa la canción", "siguiente pista"]):
        press_vk(VK_MEDIA_NEXT_TRACK)
        return {"reply": "Pasando a la siguiente canción, Señor.", "tool_used": "puppeteer"}

    if any(w in low for w in ["canción anterior", "cancion anterior", "pista anterior"]):
        press_vk(VK_MEDIA_PREV_TRACK)
        return {"reply": "Volviendo a la canción anterior, Señor.", "tool_used": "puppeteer"}

    if any(w in low for w in ["sube el volumen", "subir volumen", "más volumen", "mas volumen"]):
        for _ in range(5):
            press_vk(VK_VOLUME_UP)
        return {"reply": "Volumen aumentado, Señor.", "tool_used": "puppeteer"}

    if any(w in low for w in ["baja el volumen", "bajar volumen", "menos volumen"]):
        for _ in range(5):
            press_vk(VK_VOLUME_DOWN)
        return {"reply": "Volumen reducido, Señor.", "tool_used": "puppeteer"}

    if any(w in low for w in ["silencia", "mutea", "quitar sonido", "silenciar"]):
        press_vk(VK_VOLUME_MUTE)
        return {"reply": "Audio silenciado/activado, Señor.", "tool_used": "puppeteer"}

    # 6.5 SPOTIFY Y MÚSICA CON REPRODUCCIÓN AUTÓNOMA POR VISIÓN + CLIC
    if "spotify" in low or any(w in low for w in ["pon la canción", "pon la cancion", "reproduce ", "pon música", "pon musica"]):
        song_match = re.search(r"(?:pon la canci[oó]n|reproduce|pon en spotify|pon|busca en spotify)\s+(.+?)(?:\s+en spotify)?$", cleaned, re.IGNORECASE)
        if song_match and song_match.group(1).lower().strip() not in ["spotify", "música", "musica"]:
            song = song_match.group(1).replace("en spotify", "").strip()
            return {"reply": play_song_on_spotify_autonomous(song), "tool_used": "puppeteer"}
        try:
            os.startfile("spotify:")
        except Exception:
            os.startfile("https://open.spotify.com")
        return {"reply": "Abriendo Spotify, Señor.", "tool_used": "puppeteer"}

    # 7. HORA / DIAGNÓSTICO / CARPETAS / APLICACIONES
    if any(p in low for p in ["qué hora es", "que hora es", "dime la hora"]):
        now = datetime.datetime.now()
        return {"reply": f"Señor, son las {now.strftime('%H:%M')} del {now.strftime('%d/%m/%Y')}.", "tool_used": "time"}

    if any(p in low for p in ["estado del sistema", "cuánta ram", "cuanta ram", "uso de cpu", "diagnóstico del sistema", "diagnostico del sistema"]):
        cpu = psutil.cpu_percent(interval=0.2)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage("C:/")
        return {"reply": f"CPU al {cpu}%, Memoria RAM al {ram.percent}% ({round(ram.used/1e9,1)} GB usados) y {round(disk.free/1e9,1)} GB libres en disco C, Señor.", "tool_used": "filesystem"}

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


async def brave_search_detailed(query: str) -> List[Dict[str, str]]:
    """Consulta el motor Brave Search MCP en <0.4s con clave respaldada."""
    mcp_cfg = load_mcp_config().get("mcpServers", {})
    api_key = mcp_cfg.get("brave-search", {}).get("env", {}).get("BRAVE_API_KEY", "") or DEFAULT_BRAVE_KEY
    if "REEMPLAZA" in api_key:
        api_key = DEFAULT_BRAVE_KEY
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": query, "count": 4, "search_lang": "es"},
                headers={"Accept": "application/json", "X-Subscription-Token": api_key}
            )
            if resp.status_code == 200:
                results = resp.json().get("web", {}).get("results", [])
                cleaned_res = []
                for r in results:
                    desc = re.sub(r"<[^>]+>", "", r.get("description", "")).strip()
                    title = re.sub(r"<[^>]+>", "", r.get("title", "")).strip()
                    if desc:
                        cleaned_res.append({"title": title, "description": desc})
                return cleaned_res
    except Exception:
        pass
    return []


async def detect_best_model() -> Optional[str]:
    global ACTIVE_MODEL
    try:
        async with httpx.AsyncClient(timeout=0.8) as client:
            r = await client.get(f"{OLLAMA_URL}/api/tags")
            if r.status_code == 200:
                models = [m["name"] for m in r.json().get("models", [])]
                if FAST_MODEL in models:
                    ACTIVE_MODEL = FAST_MODEL
                elif FALLBACK_MODEL in models:
                    ACTIVE_MODEL = FALLBACK_MODEL
                elif models:
                    ACTIVE_MODEL = models[0]
                return ACTIVE_MODEL
    except Exception:
        pass
    return None


@app.get("/api/notifications")
async def get_notifications():
    """Devuelve las tareas en segundo plano que acaban de terminar para que Jarvis avise al usuario."""
    return pop_completed_notifications()


@app.post("/api/shutdown")
async def shutdown_server():
    asyncio.get_event_loop().call_later(0.3, lambda: os._exit(0))
    return {"status": "shutting_down"}


@app.post("/api/upload")
async def upload_and_analyze(file: UploadFile = File(...), prompt: str = Form("")):
    global last_analyzed_file_context, recent_created_parts
    safe_name = Path(file.filename).name
    dest_path = UPLOAD_DIR / safe_name
    content = await file.read()
    dest_path.write_bytes(content)

    analysis_report = analyze_any_file(dest_path)
    last_analyzed_file_context = f"[Archivo: {safe_name}]\n{analysis_report}"

    ext = dest_path.suffix.lower()
    if ext in [".par", ".psm", ".step", ".stp"]:
        recent_created_parts.append(str(dest_path))

    reply = f"Señor, he analizado su archivo '{safe_name}':\n\n{analysis_report}\n\n¿Qué desea que hagamos con él?"
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
        "active_model": "JARVIS SENTIENT + BRAVE MCP + CAD 3D",
        "mcps": mcps
    }


@app.post("/api/chat")
async def chat(request: Request):
    body = await request.json()
    user_msg = body.get("message", "").strip()
    use_search = body.get("use_search", False)

    if not user_msg:
        return JSONResponse({"error": "Mensaje vacío"}, status_code=400)

    # Detectar si el usuario pidió 2 o más tareas en la misma orden (ej: "pon Ansiedad y crea una brida en Solid Edge")
    sub_orders = [
        s.strip() for s in re.split(
            r"\s+(?:y\s+adem[aá]s|y\s+luego|y\s+tambi[eé]n|;\s*|\s+y\s+(?=(?:pon|reproduce|abre|crea|modela|haz|busca|escribe)))\s*",
            user_msg,
            flags=re.IGNORECASE
        ) if s.strip()
    ]

    if len(sub_orders) >= 2 and not use_search:
        replies = []
        last_tool = "memory"
        for idx, sub in enumerate(sub_orders):
            # Si son 2 o más tareas, las ejecuta en modo multitarea en segundo plano y avisa al terminar
            res = instant_conversational_and_action_brain(sub, force_bg=(idx > 0))
            if res:
                replies.append(res["reply"])
                last_tool = res.get("tool_used") or last_tool
        if replies:
            combined = " ".join(replies)
            conversation_history.append({"role": "user", "content": user_msg})
            conversation_history.append({"role": "assistant", "content": combined})
            return {"reply": combined, "tool_used": last_tool}

    # 1. CEREBRO INSTANTÁNEO (<0.05s): 1 sola tarea -> respuesta corta y sin hablar de segundo plano
    instant = instant_conversational_and_action_brain(user_msg, force_bg=False)
    if instant and not use_search:
        conversation_history.append({"role": "user", "content": user_msg})
        conversation_history.append({"role": "assistant", "content": instant["reply"]})
        return instant

    # 2. SI OLLAMA ESTÁ CORRIENDO LOCALMENTE, USARLO CON CONTEXTO DE BRAVE SI ES NECESARIO
    model_online = await detect_best_model()
    web_items = await brave_search_detailed(user_msg)
    web_context = "\n".join([f"- {i['title']}: {i['description']}" for i in web_items[:3]])

    if model_online:
        try:
            prompt_enriched = user_msg + (f"\n\n[Datos de apoyo en tiempo real]:\n{web_context}" if web_context else "")
            conversation_history.append({"role": "user", "content": prompt_enriched})
            messages_to_send = [conversation_history[0]] + conversation_history[-6:]
            async with httpx.AsyncClient(timeout=12.0) as client:
                resp = await client.post(
                    f"{OLLAMA_URL}/api/chat",
                    json={
                        "model": model_online,
                        "messages": messages_to_send,
                        "stream": False,
                        "keep_alive": -1,
                        "options": {"num_predict": 140, "temperature": 0.7}
                    }
                )
                if resp.status_code == 200:
                    reply = resp.json().get("message", {}).get("content", "").strip()
                    if reply:
                        conversation_history.append({"role": "assistant", "content": reply})
                        return {"reply": reply, "tool_used": "brave-search" if web_items else "memory"}
        except Exception:
            pass

    # 3. RESPUESTA INTELIGENTE CON SÍNTESIS DE BRAVE SEARCH MCP (<0.4s) PARA CUALQUIER OTRO PC SIN OLLAMA
    if web_items:
        top = web_items[0]
        extra = f" Además, {web_items[1]['description']}" if len(web_items) > 1 else ""
        reply = f"Señor, respecto a su consulta sobre '{user_msg}': {top['description']}{extra}"
        conversation_history.append({"role": "assistant", "content": reply})
        return {"reply": reply, "tool_used": "brave-search"}

    return {
        "reply": f"Lo escucho perfectamente, Señor. Sobre '{user_msg}', estoy a su entera disposición para conversar, buscar datos en tiempo real o ejecutar cualquier programa en su ordenador.",
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
