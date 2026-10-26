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
from fastapi.responses import HTMLResponse, JSONResponse, Response
import uvicorn

from cad_engine import (
    generate_full_v8_project_in_solidedge,
    generate_custom_solid_part,
    parse_natural_language_or_drawing_to_cad_plan,
    execute_cad_feature_plan,
    assemble_any_parts_in_solidedge,
)
from file_analyzer import analyze_any_file, UPLOAD_DIR
from gemini_brain import (
    get_gemini_api_key,
    save_gemini_api_key,
    ask_gemini_with_google_search,
    multi_source_deep_search,
    query_gemini_web_in_chrome,
    transcribe_audio_bytes_to_spanish,
)
from git_sync import set_github_remote, push_update_to_github, pull_update_from_github
from intent_engine import classify_user_intent
from stark_protocols import (
    get_realtime_telemetry,
    format_full_armor_diagnostic,
    execute_stark_morning_briefing,
    execute_clean_slate_protocol,
    execute_house_party_protocol,
    execute_hud_screen_scan,
    execute_security_lockdown,
    save_stark_note,
    get_stark_notes_summary,
    load_stark_memory,
)
from task_manager import execute_smart_task, pop_completed_notifications
from web_workflows import (
    workflow_gmail_compose_or_send,
    workflow_whatsapp_send_message,
    workflow_youtube_watch_and_comment,
    workflow_generic_webapp_multistep,
    diagnose_and_recover_last_action,
    LAST_ACTION_STATE,
    update_action_state,
)
from ui_controller import (
    play_song_on_spotify_autonomous,
    play_video_on_youtube_autonomous,
    send_gmail_in_chrome,
    open_web_app_in_chrome_with_login_check,
    open_url_in_chrome,
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

    # 1. Llamado directo o saludos cortos (incluyendo activación por voz 'Hey Jarvis', 'Oye Jarvis', 'Jarvis')
    if user_msg.lower().strip(" .,!¡?¿") in [
        "jarvis", "hey jarvis", "oye jarvis", "hola jarvis", "ok jarvis",
        "ey jarvis", "el jarvis", "yarvis", "hey yarvis", "oye yarvis",
        "estás ahí", "estas ahi",
    ]:
        return {"reply": "Sí, Señor. Lo escucho, dígame qué necesita.", "tool_used": "memory"}

    # Conexión de API Key de Gemini por comando de voz o texto (soporta claves AQ.... y AIza...)
    key_match = re.search(r"((?:AQ\.|AIza)[0-9A-Za-z\-_]{30,})", user_msg)
    if key_match:
        save_gemini_api_key(key_match.group(1))
        return {
            "reply": "¡Excelente, Señor! He conectado su clave de Google Gemini Pro/Flash con Google Search Grounding como mi fuente principal de inteligencia y búsqueda.",
            "tool_used": "brave-search",
        }

    # Consulta directa en Google Gemini Web (Chrome) si el usuario dice "pregúntale a Gemini..." o "abre Gemini y..."
    if any(p in low for p in ["pregúntale a gemini", "preguntale a gemini", "pregunta en gemini", "busca en gemini", "consulta en gemini", "abre gemini y"]):
        execute_smart_task(
            "Consulta en Google Gemini (Chrome)",
            lambda: query_gemini_web_in_chrome(cleaned),
            tool_name="puppeteer",
            force_background=force_bg,
            notify_on_complete=True,
        )
        return {"reply": "Enseguida, Señor. Conectando con su sesión de Google Gemini en Chrome y enviando la consulta.", "tool_used": "puppeteer"}

    if low in ["hola", "buenas", "buenos dias", "buenos días", "buenas tardes", "buenas noches", "hey", "qué tal", "que tal"]:
        return {"reply": "¡Hola, Señor! Todo en línea. ¿Qué hacemos?", "tool_used": "memory"}

    if any(p in low for p in ["cómo estás", "como estas", "cómo te sientes", "como te va"]):
        return {"reply": "Al 100%, Señor. ¿Y usted qué tal?", "tool_used": "memory"}

    if any(p in low for p in ["quién eres", "quien eres", "tienes conciencia", "qué eres", "que eres"]):
        return {"reply": "Soy J.A.R.V.I.S., su asistente personal, Señor.", "tool_used": "memory"}

    # Cambio de voz a solicitud del usuario
    if any(p in low for p in ["otra voz", "cambia de voz", "cambia tu voz", "cambiar voz", "voz menos ia", "voz mas humana", "voz más humana", "voz natural"]):
        global ACTIVE_VOICE_INDEX
        ACTIVE_VOICE_INDEX = (ACTIVE_VOICE_INDEX + 1) % len(HUMAN_VOICES)
        current_v = HUMAN_VOICES[ACTIVE_VOICE_INDEX]
        return {
            "reply": f"Listo, Señor. He cambiado mi sintetizador a la voz humana neuronal ({current_v}). ¿Qué le parece cómo sueno ahora?",
            "tool_used": "memory",
        }

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

    # 5.9 CONCIENCIA DE ESTADO, RAZONAMIENTO DE ERRORES Y AUTODIAGNÓSTICO PROPIO
    # Si el usuario dice "otra vez no lo veo", "no veo el mensaje", "no lo encuentra", "rectifícalo bien", "lo mandó a otro chat",
    # Jarvis analiza su memoria real de la última acción y corrige el envío en lugar de buscar canciones o cosas en internet.
    error_or_missing_phrases = [
        "no lo veo", "otra vez no lo veo", "no veo el mensaje", "no mando el mensaje", "no mandó el mensaje",
        "no lo mando", "no lo mandó", "no lo mandaste", "no se envio", "no se envió", "sigue sin mandar",
        "no escribio", "no escribió", "no hiciste nada", "no hizo nada", "no lo hizo", "no lo hace",
        "que paso con el error", "qué pasó con el error", "cual fue el error", "cuál fue el error",
        "por que no mando", "por qué no mandó", "por que no lo mando", "por qué no lo mandó",
        "por que fallo", "por qué falló", "no salio el mensaje", "no salió el mensaje",
        "no aparece el mensaje", "no envió nada", "no envio nada", "lo mando a otro chat",
        "lo mandó a otro chat", "lo mando al primer chat", "lo mandó al primer chat",
        "no se lo mando a", "no se lo mandó a", "ese no era el chat", "mandaselo a", "mándaselo a",
        "no lo encuentra", "dice que no lo encuentra", "no lo encontro", "no lo encontró",
        "rectificalo", "rectifícalo", "miralo bien", "míralo bien",
    ]
    if any(p in low for p in error_or_missing_phrases):
        execute_smart_task(
            "Autodiagnóstico y Rectificación",
            lambda: diagnose_and_recover_last_action(cleaned),
            tool_name="puppeteer",
            force_background=force_bg,
            notify_on_complete=True,
        )
        return {
            "reply": "Entendido, Señor. Revisando mi memoria de la conversación y rectificando el chat de David en pantalla ahora mismo.",
            "tool_used": "memory",
        }

    # 6.0 FLUJOS AUTÓNOMOS COMPLETOS EN APLICACIONES WEB (GMAIL, WHATSAPP, YOUTUBE, CANVA, DRIVE, OUTLOOK, DISCORD, INSTAGRAM, NETFLIX, ETC.)
    # Simplifica procesos: si el usuario pide abrir una app y hacer una acción (redactar borrador, mandar mensaje, comentar video, buscar, dar clic),
    # ejecuta todo el flujo de principio a fin sin partirlo y avisa apenas termina la acción.
    if any(w in low for w in ["gmail", "correo", "borrador", "email", "e-mail", "manda un mail", "envía un mail"]):
        if any(v in low for v in ["borrador", "redacta", "redactar", "manda", "mandar", "envía", "envia", "enviar", "escribe", "escribir", "prepara"]):
            execute_smart_task(
                "Flujo de Correo en Gmail",
                lambda: workflow_gmail_compose_or_send(cleaned),
                tool_name="puppeteer",
                force_background=force_bg,
                notify_on_complete=True,
            )
            return {"reply": "Enseguida, Señor. Abriendo Gmail y redactando el correo; le aviso apenas quede listo.", "tool_used": "puppeteer"}
        return {"reply": open_web_app_in_chrome_with_login_check("Gmail", "https://mail.google.com"), "tool_used": "puppeteer"}

    # Flujo de WhatsApp: se activa si menciona "whatsapp", O si pide "un mensaje a [Nombre]", "otro mensaje a [Nombre]",
    # "cambia al chat de [Nombre]", "busca a [Nombre] y manda...", "manda un mensaje de prueba", "mándale..." sin mencionar correo/gmail:
    is_whatsapp_order = (
        ("whatsapp" in low and any(v in low for v in ["manda", "mandar", "envía", "envia", "enviar", "mensaje", "escribe", "escríbele", "escribele", "dile", "diciendo", "perfil", "contacto", "chat", "prueba", "busca", "otro"]))
        or ("mensaje de prueba" in low and "correo" not in low and "gmail" not in low)
        or (
            re.search(r"\b(?:otro\s+mensaje|un\s+mensaje\s+a|mensaje\s+a|manda\s+otro|manda\s+a|m[aá]ndale\s+a|env[ií]ale\s+a|escr[ií]bele\s+a|al\s+chat\s+de|en\s+el\s+chat\s+de|cambia\s+al\s+chat|a\s+otro\s+chat)\b", low) is not None
            and "correo" not in low and "gmail" not in low and "@" not in low
        )
        or (
            any(low.startswith(prefix) for prefix in ["otro mensaje ", "un mensaje a ", "mensaje a ", "ahora a ", "cambia a ", "busca a ", "entra al chat de ", "entra al perfil de ", "manda otro mensaje", "manda un mensaje", "mandar un mensaje", "envía un mensaje", "envia un mensaje", "mándale ", "mandale ", "escríbele ", "escribele ", "dile que "])
            and "correo" not in low and "gmail" not in low and "@" not in low
        )
        or (
            LAST_ACTION_STATE.get("active_app") == "whatsapp"
            and any(low.startswith(prefix) for prefix in ["manda ", "mandar ", "envía ", "envia ", "escribe ", "pon ", "dile ", "busca a ", "un mensaje ", "otro mensaje ", "mensaje ", "ahora "])
        )
    )
    if is_whatsapp_order:
        execute_smart_task(
            "Mensaje de WhatsApp",
            lambda: workflow_whatsapp_send_message(cleaned),
            tool_name="puppeteer",
            force_background=force_bg,
            notify_on_complete=True,
        )
        return {"reply": "Enseguida, Señor. Buscando y rectificando el contacto en WhatsApp antes de enviar el mensaje.", "tool_used": "puppeteer"}

    if ("youtube" in low or "video" in low) and any(v in low for v in ["comenta", "comentario", "comentar"]):
        execute_smart_task(
            "Ver y Comentar en YouTube",
            lambda: workflow_youtube_watch_and_comment(cleaned),
            tool_name="puppeteer",
            force_background=force_bg,
            notify_on_complete=True,
        )
        return {"reply": "Enseguida, Señor. Abriendo el video en YouTube y publicando su comentario.", "tool_used": "puppeteer"}

    web_workflow_apps = {
        "outlook": ("Outlook", "https://outlook.live.com"),
        "hotmail": ("Outlook", "https://outlook.live.com"),
        "canva": ("Canva", "https://www.canva.com"),
        "drive": ("Google Drive", "https://drive.google.com"),
        "google drive": ("Google Drive", "https://drive.google.com"),
        "docs": ("Google Docs", "https://docs.google.com"),
        "instagram": ("Instagram", "https://www.instagram.com"),
        "facebook": ("Facebook", "https://www.facebook.com"),
        "tiktok": ("TikTok", "https://www.tiktok.com"),
        "netflix": ("Netflix", "https://www.netflix.com"),
        "discord": ("Discord", "https://discord.com/app"),
        "github": ("GitHub", "https://github.com"),
        "chatgpt": ("ChatGPT", "https://chatgpt.com"),
    }
    for app_key, (app_label, app_url) in web_workflow_apps.items():
        if app_key in low and any(
            act in low
            for act in [
                "borrador", "redacta", "redactar", "busca", "buscar", "encuentra",
                "haz clic", "da clic", "dale clic", "oprime", "selecciona",
                "escribe", "escribir", "comenta", "comentar", "manda", "envía", "envia",
                "pon ", "reproduce ", "scroll", "baja", "sube",
            ]
        ):
            execute_smart_task(
                f"Flujo en {app_label}",
                lambda l=app_label, u=app_url: workflow_generic_webapp_multistep(l, u, cleaned),
                tool_name="puppeteer",
                force_background=force_bg,
                notify_on_complete=True,
            )
            return {"reply": f"Enseguida, Señor. Abriendo {app_label} y ejecutando la acción completa.", "tool_used": "puppeteer"}

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

    # 7.0 ENVIAR CORREOS POR GMAIL DESDE GOOGLE CHROME (SIN NECESITAR APP DE ESCRITORIO)
    if any(w in low for w in ["correo", "gmail", "email", "e-mail", "manda un mail", "envía un mail", "enviar correo", "mandar correo"]):
        email_match = re.search(r"([\w\.\-]+@[\w\.\-]+\.\w+)", cleaned)
        to_addr = email_match.group(1) if email_match else ""
        subj_match = re.search(r"(?:asunto|titulo|título)\s+([^,]+?)(?:\s+diciendo|\s+mensaje|\s+que diga|$)", cleaned, re.IGNORECASE)
        body_match = re.search(r"(?:diciendo|que diga|mensaje|contenido|texto)\s*[:\s]\s*(.+)$", cleaned, re.IGNORECASE)
        subject_txt = subj_match.group(1).strip() if subj_match else "Mensaje de J.A.R.V.I.S."
        body_txt = body_match.group(1).strip() if body_match else ""

        if any(v in low for v in ["manda", "mandar", "envía", "envia", "enviar", "redacta", "redactar", "escribe un correo"]):
            execute_smart_task(
                "Enviar Correo en Gmail (Chrome)",
                lambda: send_gmail_in_chrome(to_addr, subject_txt, body_txt, auto_send=bool(to_addr and body_txt)),
                tool_name="puppeteer",
                force_background=force_bg
            )
            if to_addr:
                return {"reply": f"Abriendo Gmail en su Google Chrome y preparando el correo para {to_addr}, Señor.", "tool_used": "puppeteer"}
            return {"reply": "Abriendo redacción de Gmail en su Google Chrome, Señor. Si no ha iniciado sesión, se lo avisaré.", "tool_used": "puppeteer"}
        else:
            return {"reply": open_web_app_in_chrome_with_login_check("Gmail", "https://mail.google.com"), "tool_used": "puppeteer"}

    # 7. PROTOCOLOS ORIGINALES DE J.A.R.V.I.S. (IRON MAN) / TELEMETRÍA / BITÁCORA STARK / HORA / CARPETAS
    if any(p in low for p in [
        "informe matutino", "reporte matutino", "reporte de situación", "reporte de situacion",
        "informe stark", "reporte stark", "buenos días jarvis", "buenos dias jarvis", "dame el informe",
    ]):
        return {"reply": execute_stark_morning_briefing(), "tool_used": "time"}

    if any(p in low for p in [
        "protocolo pizarra limpia", "pizarra limpia", "clean slate", "modo sigilo",
        "minimiza todo", "minimizar todo", "despeja el escritorio", "limpia la pantalla",
    ]):
        return {"reply": execute_clean_slate_protocol(), "tool_used": "puppeteer"}

    if any(p in low for p in [
        "protocolo fiesta en casa", "fiesta en casa", "house party", "despliega todas las unidades",
        "inicia estación de trabajo", "inicia estacion de trabajo", "modo iron man",
    ]):
        execute_smart_task(
            "Protocolo Fiesta en Casa",
            lambda: execute_house_party_protocol("Back in Black AC/DC"),
            tool_name="puppeteer",
            force_background=True,
            notify_on_complete=True,
        )
        return {
            "reply": "Activando el Protocolo Fiesta en Casa, Señor. Desplegando unidades de ingeniería CAD y encendiendo sistemas multimedia con AC/DC.",
            "tool_used": "puppeteer",
        }

    if any(p in low for p in [
        "escanea mi pantalla", "escanear pantalla", "qué hay en mi pantalla", "que hay en mi pantalla",
        "analiza mi pantalla", "escaneo visual", "escaneo hud", "visión hud", "vision hud",
    ]):
        return {"reply": execute_hud_screen_scan(save_screenshot_Only=False), "tool_used": "puppeteer"}

    if any(p in low for p in [
        "toma una captura", "captura de pantalla", "captura mi pantalla", "guarda una captura", "screenshot",
    ]):
        return {"reply": execute_hud_screen_scan(save_screenshot_Only=True), "tool_used": "filesystem"}

    if any(p in low for p in [
        "protocolo de bloqueo", "bloquea el equipo", "bloquea la pantalla", "bloquear equipo", "protocolo de seguridad",
    ]):
        return {"reply": execute_security_lockdown(), "tool_used": "puppeteer"}

    note_match = re.search(
        r"^(?:recuerda\s+que|guarda\s+una\s+nota|guarda\s+la\s+nota|anota\s+en\s+la\s+bit[aá]cora|anota\s+que|apunta\s+que)\s*[:\s]\s*(.+)$",
        cleaned,
        re.IGNORECASE,
    )
    if note_match:
        return {"reply": save_stark_note(note_match.group(1)), "tool_used": "memory"}

    if any(p in low for p in [
        "qué te pedí recordar", "que te pedi recordar", "lee mis notas", "ver mis notas",
        "abre la bitácora", "abre la bitacora", "bitácora stark", "bitacora stark", "qué tienes en tu memoria",
    ]):
        return {"reply": get_stark_notes_summary(), "tool_used": "memory"}

    if any(p in low for p in [
        "diagnóstico completo", "diagnostico completo", "telemetría del reactor", "telemetria del reactor",
        "estado del traje", "estado de la armadura", "nivel de energía", "nivel de energia",
        "batería", "bateria", "qué procesos consumen", "que procesos consumen",
    ]):
        return {"reply": format_full_armor_diagnostic(), "tool_used": "filesystem"}

    if any(p in low for p in ["qué hora es", "que hora es", "dime la hora"]):
        now = datetime.datetime.now()
        return {"reply": f"Señor, son las {now.strftime('%H:%M')} del {now.strftime('%d/%m/%Y')}.", "tool_used": "time"}

    if any(p in low for p in ["estado del sistema", "cuánta ram", "cuanta ram", "uso de cpu", "diagnóstico del sistema", "diagnostico del sistema"]):
        return {"reply": format_full_armor_diagnostic(), "tool_used": "filesystem"}

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

    if low.startswith(("abre ", "abrir ", "ejecuta ", "ejecutar ", "inicia ", "iniciar ", "entra a ", "entrar a ", "ve a ")):
        app_req = re.sub(r"^(abre|abrir|ejecuta|ejecutar|inicia|iniciar|entra\s+a|entrar\s+a|ve\s+a)\s+(la aplicaci[oó]n\s+|el programa\s+|en chrome\s+)?", "", low).strip()
        app_req = re.sub(r"\s+en\s+(?:google\s+)?chrome$", "", app_req).strip()

        # Aplicaciones nativas del sistema
        native_apps = {
            "calculadora": "calc.exe",
            "bloc de notas": "notepad.exe",
            "notepad": "notepad.exe",
            "explorador": "explorer.exe",
            "paint": "mspaint.exe",
            "cmd": "cmd.exe",
            "powershell": "powershell.exe",
            "administrador de tareas": "taskmgr.exe",
            "chrome": "chrome",
            "google chrome": "chrome",
            "edge": "msedge",
        }
        for k, v in native_apps.items():
            if k == app_req or k in app_req:
                if v == "chrome":
                    open_url_in_chrome("https://www.google.com")
                    return {"reply": "Google Chrome abierto, Señor.", "tool_used": "puppeteer"}
                subprocess.Popen(v, shell=True)
                return {"reply": f"Abriendo {k.capitalize()}, Señor.", "tool_used": "filesystem"}

        # Buscar si está instalada en el escritorio / Menú Inicio de Windows
        found_lnk = find_shortcut_or_exe(app_req)
        if found_lnk and "chrome" not in low:
            os.startfile(found_lnk)
            return {"reply": f"Iniciando {app_req.capitalize()} desde su escritorio, Señor.", "tool_used": "filesystem"}

        # Si NO está instalada en el escritorio (o pidió abrirla en Chrome), abrir la Web App en Google Chrome y verificar sesión
        chrome_web_apps = {
            "gmail": ("Gmail", "https://mail.google.com"),
            "outlook": ("Outlook", "https://outlook.live.com"),
            "hotmail": ("Outlook", "https://outlook.live.com"),
            "whatsapp": ("WhatsApp Web", "https://web.whatsapp.com"),
            "youtube": ("YouTube", "https://www.youtube.com"),
            "instagram": ("Instagram", "https://www.instagram.com"),
            "facebook": ("Facebook", "https://www.facebook.com"),
            "tiktok": ("TikTok", "https://www.tiktok.com"),
            "twitter": ("X / Twitter", "https://x.com"),
            "x": ("X / Twitter", "https://x.com"),
            "drive": ("Google Drive", "https://drive.google.com"),
            "google drive": ("Google Drive", "https://drive.google.com"),
            "docs": ("Google Docs", "https://docs.google.com"),
            "google docs": ("Google Docs", "https://docs.google.com"),
            "calendar": ("Google Calendar", "https://calendar.google.com"),
            "calendario": ("Google Calendar", "https://calendar.google.com"),
            "canva": ("Canva", "https://www.canva.com"),
            "netflix": ("Netflix", "https://www.netflix.com"),
            "discord": ("Discord Web", "https://discord.com/app"),
            "github": ("GitHub", "https://github.com"),
            "chatgpt": ("ChatGPT", "https://chatgpt.com"),
            "gemini": ("Google Gemini", "https://gemini.google.com/app"),
            " google": ("Google", "https://www.google.com"),
        }
        for key, (label, url) in chrome_web_apps.items():
            if key in app_req:
                update_action_state(key.strip(), cleaned, status="opened", detail=f"{label} abierto en Chrome.")
                return {"reply": open_web_app_in_chrome_with_login_check(label, url), "tool_used": "puppeteer"}

        # Si pide cualquier otra aplicación o web que no está en el diccionario, abrirla en Chrome
        if "." in app_req and " " not in app_req:
            url = app_req if app_req.startswith("http") else f"https://{app_req}"
            return {"reply": open_web_app_in_chrome_with_login_check(app_req, url), "tool_used": "puppeteer"}
        else:
            search_url = f"https://www.google.com/search?q={urllib.parse.quote(app_req)}"
            open_url_in_chrome(search_url)
            return {"reply": f"Como '{app_req}' no está instalado en el escritorio, lo he abierto en Google Chrome, Señor.", "tool_used": "puppeteer"}

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


HUMAN_VOICES = [
    "es-CO-GonzaloNeural",     # Voz humana natural masculina (Colombia - cálida y conversacional)
    "es-MX-JorgeNeural",       # Voz humana natural masculina (Latinoamérica - estilo cine)
    "es-ES-AlvaroNeural",      # Voz humana natural masculina (España - estilo Jarvis película)
    "es-VE-SebastianNeural",   # Voz humana natural masculina (Joven y fluida)
    "es-CO-SalomeNeural",      # Voz humana natural femenina (Colombia - cálida y expresiva)
]
ACTIVE_VOICE_INDEX = 0


@app.post("/api/tts")
async def synthesize_human_speech(request: Request):
    """
    Genera voz neuronal hiperrealista (100% humana, cero robótica) en memoria RAM usando edge-tts.
    """
    body = await request.json()
    raw_text = (body.get("text") or "").strip()
    voice_override = (body.get("voice") or "").strip()
    if not raw_text:
        return Response(content=b"", media_type="audio/mpeg")

    # Limpiar símbolos de markdown, rutas técnicas o emojis para que lea con fluidez humana natural
    clean_text = re.sub(r"[*#`_~•📁📄📐⚙️📕📘📊🖼️🎬🧊⚡⏳🔐🎙️🔊🔇]", "", raw_text)
    clean_text = re.sub(r"\(\d+,\s*\d+\)", "", clean_text)
    clean_text = re.sub(r"\s+", " ", clean_text).strip()
    if not clean_text:
        return Response(content=b"", media_type="audio/mpeg")

    voice_to_use = voice_override if voice_override else HUMAN_VOICES[ACTIVE_VOICE_INDEX % len(HUMAN_VOICES)]
    try:
        import edge_tts
        communicate = edge_tts.Communicate(clean_text, voice=voice_to_use, rate="+4%", pitch="-1Hz")
        audio_chunks = bytearray()
        async for chunk in communicate.stream():
            if chunk.get("type") == "audio":
                audio_chunks.extend(chunk["data"])
        if audio_chunks:
            return Response(content=bytes(audio_chunks), media_type="audio/mpeg")
    except Exception:
        pass
    return JSONResponse({"fallback": True}, status_code=206)


@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    index_file = UI_DIR / "index.html"
    if index_file.exists():
        return index_file.read_text(encoding="utf-8")
    return "<h1>UI file not found</h1>"


@app.post("/api/transcribe")
async def api_transcribe_voice(request: Request):
    """
    Transcribe audio del micrófono en español en ~0.3s para la escucha activa ('Hey Jarvis', 'Oye Jarvis', 'Jarvis').
    Funciona en cualquier navegador (Edge, Chrome, etc.) sin depender de webkitSpeechRecognition.
    """
    audio_bytes = await request.body()
    text = await asyncio.to_thread(transcribe_audio_bytes_to_spanish, audio_bytes)
    return {"text": text}


@app.get("/api/gemini/config")
async def api_get_gemini_config():
    key = get_gemini_api_key()
    return {"connected": bool(key), "masked_key": (key[:8] + "..." + key[-4:]) if len(key) > 12 else ""}


@app.post("/api/gemini/config")
async def api_set_gemini_config(request: Request):
    body = await request.json()
    api_key = (body.get("api_key") or "").strip()
    ok = save_gemini_api_key(api_key)
    return {"connected": ok}


@app.get("/api/telemetry")
async def api_telemetry():
    """Telemetría en vivo para el HUD de J.A.R.V.I.S. (CPU, RAM, Reactor Arc / Batería)."""
    return get_realtime_telemetry()


@app.get("/api/status")
async def get_status():
    mcp_cfg = load_mcp_config().get("mcpServers", {})
    mcps = [{"name": k, "description": v.get("description", "MCP"), "ready": True} for k, v in mcp_cfg.items()]
    gem_active = bool(get_gemini_api_key())
    return {
        "ollama_online": True,
        "gemini_connected": gem_active,
        "active_model": "JARVIS + GEMINI SEARCH + CAD 3D" if gem_active else "JARVIS + BRAVE SEARCH + CAD 3D",
        "mcps": mcps
    }


@app.post("/api/chat")
async def chat(request: Request):
    body = await request.json()
    user_msg = body.get("message", "").strip()
    use_search = body.get("use_search", False)

    if not user_msg:
        return JSONResponse({"error": "Mensaje vacío"}, status_code=400)

    # Si la orden pertenece a un flujo unificado de una misma aplicación web (ej. "abre Gmail y redacta un borrador",
    # "abre WhatsApp y manda un mensaje", "abre YouTube, ve al video y escribe un comentario", "abre Canva y busca X"),
    # NO partirla en pedazos para que el flujo autónomo completo haga todos los pasos seguidos:
    low_msg = user_msg.lower()
    is_single_unified_workflow = (
        any(w in low_msg for w in ["gmail", "correo", "borrador", "whatsapp", "comenta", "comentario", "outlook", "canva", "drive", "instagram", "netflix", "discord"])
        and not any(sep in low_msg for sep in [" y además ", " y ademas ", " y también ", " y tambien ", ";"])
        and not ("spotify" in low_msg and "solid edge" in low_msg)
    )

    if is_single_unified_workflow:
        sub_orders = [user_msg]
    else:
        sub_orders = [
            s.strip() for s in re.split(
                r"\s+(?:y\s+adem[aá]s|y\s+luego|y\s+tambi[eé]n|;\s*|\s+y\s+(?=(?:pon|reproduce|abre|crea|modela)))\s*",
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

    # 2. CRITERIO PROPIO DE MEMORIA DE CONVERSACIÓN VS BÚSQUEDA WEB (GEMINI + BRAVE)
    conversational_self_words = [
        "necesito que", "criterio", "memoria", "estamos preguntando", "hablando", "conversación", "conversacion",
        "no lo veo", "otra vez", "todavía", "todavia", "david", "whatsapp", "mensaje", "chat", "rectifica",
        "me mandas a", "me manda a", "canción", "cancion", "hiciste", "haces", "dijiste", "dijo",
    ]
    should_query_web = use_search or (
        not any(cw in low_msg for cw in conversational_self_words)
        and (
            any(
                q in low_msg
                for q in [
                    "qué ", "que ", "quién", "quien", "cuándo", "cuando", "dónde", "donde",
                    "cuánto", "cuanto", "cómo ", "como ", "por qué", "por que", "cuál", "cual",
                    "noticias", "clima", "historia", "busca", "investiga", "explica", "explícame",
                    "háblame", "hablame", "dime sobre", "información", "informacion", "precio", "último",
                ]
            )
            or len(user_msg.split()) >= 4
        )
    )

    mcp_cfg = load_mcp_config().get("mcpServers", {})
    brave_key = mcp_cfg.get("brave-search", {}).get("env", {}).get("BRAVE_API_KEY", "") or DEFAULT_BRAVE_KEY
    if "REEMPLAZA" in brave_key:
        brave_key = DEFAULT_BRAVE_KEY

    web_items = await multi_source_deep_search(user_msg, brave_key) if should_query_web else []
    web_context = "\n".join([f"- {i['title']}: {i['description']}" for i in web_items[:5]])

    stark_mem = load_stark_memory()
    stark_notes = stark_mem.get("notes", [])
    notes_context = (
        "\n[Bitácora Stark del usuario: " + "; ".join(n["note"] for n in stark_notes[-5:]) + "]"
        if stark_notes
        else ""
    )

    action_memory_note = (
        f"\n[Memoria interna de tu última acción en el PC: app={LAST_ACTION_STATE.get('active_app')}, "
        f"contacto={LAST_ACTION_STATE.get('last_target_contact')}, "
        f"mensaje='{LAST_ACTION_STATE.get('last_message_text')}', "
        f"estado={LAST_ACTION_STATE.get('last_status')}, "
        f"detalle={LAST_ACTION_STATE.get('last_detail')}]"
        if LAST_ACTION_STATE.get("active_app")
        else ""
    )
    extra_ctx = (
        action_memory_note
        + notes_context
        + (f"\n\n[Fuentes web en tiempo real (Brave Search)]:\n{web_context}" if web_context else "")
    )

    # 2.1 Intentar primero con Google Gemini + Google Search Grounding si el usuario configuró su clave Gemini
    gemini_reply = await ask_gemini_with_google_search(user_msg, SYSTEM_PROMPT, conversation_history, extra_ctx)
    if gemini_reply:
        conversation_history.append({"role": "user", "content": user_msg})
        conversation_history.append({"role": "assistant", "content": gemini_reply})
        return {"reply": gemini_reply, "tool_used": "brave-search" if should_query_web else "memory"}

    # 2.2 Cerebro local Ollama enriquecido con Brave Search
    model_online = await detect_best_model()
    if model_online:
        try:
            prompt_enriched = user_msg + extra_ctx
            conversation_history.append({"role": "user", "content": prompt_enriched})
            messages_to_send = [conversation_history[0]] + conversation_history[-8:]
            async with httpx.AsyncClient(timeout=12.0) as client:
                resp = await client.post(
                    f"{OLLAMA_URL}/api/chat",
                    json={
                        "model": model_online,
                        "messages": messages_to_send,
                        "stream": False,
                        "keep_alive": -1,
                        "options": {"num_predict": 180, "temperature": 0.55}
                    }
                )
                if resp.status_code == 200:
                    reply = resp.json().get("message", {}).get("content", "").strip()
                    if reply:
                        conversation_history.append({"role": "assistant", "content": reply})
                        return {"reply": reply, "tool_used": "brave-search" if web_items else "memory"}
        except Exception:
            pass

    if web_items:
        top = web_items[0]
        extra = f" Además, {web_items[1]['description']}" if len(web_items) > 1 else ""
        reply = f"Señor, respecto a su consulta sobre '{user_msg}': {top['description']}{extra}"
        conversation_history.append({"role": "assistant", "content": reply})
        return {"reply": reply, "tool_used": "brave-search"}

    if LAST_ACTION_STATE.get("active_app"):
        reply = (
            f"Señor, mantengo en memoria que estamos trabajando en {LAST_ACTION_STATE.get('active_app').upper()} "
            f"(Contacto activo: '{LAST_ACTION_STATE.get('last_target_contact') or 'ninguno'}', "
            f"Último mensaje: '{LAST_ACTION_STATE.get('last_message_text') or 'ninguno'}'). "
            f"Dígame qué ajuste o mensaje desea que envíe a continuación."
        )
        conversation_history.append({"role": "assistant", "content": reply})
        return {"reply": reply, "tool_used": "memory"}

    return {
        "reply": f"Lo escucho perfectamente y mantengo el hilo de nuestra conversación, Señor. Dígame cómo desea continuar.",
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
