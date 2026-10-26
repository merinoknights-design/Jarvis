import asyncio
import io
import json
import os
import re
import time
import urllib.parse
import wave
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import httpx

from ui_controller import open_url_in_chrome, focus_and_maximize_chrome_window, send_text_and_keys, mouse_click, user32

BASE_DIR = Path("C:/Jarvis")
GEMINI_CONFIG_FILE = BASE_DIR / "config" / "gemini_config.json"
DEFAULT_BRAVE_KEY = "BSAPviCA5RJG-aAnfg5LZKBgX02gLQL"


def get_gemini_api_key() -> str:
    """Obtiene la API Key de Gemini desde config/gemini_config.json o variables de entorno."""
    env_key = os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")
    if env_key.strip():
        return env_key.strip()
    if GEMINI_CONFIG_FILE.exists():
        try:
            data = json.loads(GEMINI_CONFIG_FILE.read_text(encoding="utf-8"))
            return (data.get("api_key") or "").strip()
        except Exception:
            pass
    return ""


def save_gemini_api_key(api_key: str) -> bool:
    GEMINI_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    clean_key = api_key.strip()
    GEMINI_CONFIG_FILE.write_text(
        json.dumps({"api_key": clean_key, "updated_at": time.time()}, indent=2),
        encoding="utf-8",
    )
    os.environ["GEMINI_API_KEY"] = clean_key
    return bool(clean_key)


async def ask_gemini_with_google_search(
    user_query: str,
    system_instruction: str,
    history: List[Dict[str, str]],
    extra_context: str = "",
) -> Optional[str]:
    """
    Conecta directamente con Google Gemini (gemini-2.5-flash / gemini-2.0-flash)
    activando Google Search Grounding en tiempo real para que su fuente de búsqueda sea Google/Gemini.
    """
    api_key = get_gemini_api_key()
    if not api_key:
        return None

    contents = []
    for msg in history[-6:]:
        role = msg.get("role", "user")
        if role == "system":
            continue
        gem_role = "model" if role == "assistant" else "user"
        contents.append({"role": gem_role, "parts": [{"text": msg.get("content", "")}]})

    full_prompt = user_query + (f"\n\n[Contexto del sistema]:\n{extra_context}" if extra_context else "")
    contents.append({"role": "user", "parts": [{"text": full_prompt}]})

    for model_name in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        payload = {
            "system_instruction": {"parts": [{"text": system_instruction}]},
            "contents": contents,
            "tools": [{"google_search": {}}],
            "generationConfig": {"temperature": 0.65, "maxOutputTokens": 400},
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.post(url, json=payload)
                if r.status_code != 200:
                    # En Gemini 2.0/2.5 el tool puede llamarse google_search o google_search_retrieval, o ejecutarse con el contexto web enriquecido
                    payload.pop("tools", None)
                    r = await client.post(url, json=payload)
                if r.status_code == 200:
                    data = r.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        text_out = " ".join(p.get("text", "") for p in parts if p.get("text")).strip()
                        if text_out:
                            return text_out
        except Exception:
            continue
    return None


async def search_wikipedia_es(query: str) -> List[Dict[str, str]]:
    """Busca conocimiento enciclopédico verificado en Wikipedia en Español."""
    clean_q = re.sub(
        r"^(?:qu[eé]\s+es|qui[eé]n\s+es|qui[eé]n\s+fue|háblame\s+de|hablame\s+de|busca\s+sobre|investiga\s+sobre|historia\s+de|dime\s+sobre)\s+",
        "",
        query.strip(),
        flags=re.IGNORECASE,
    ).strip(" ?¿!¡.")
    if not clean_q or len(clean_q) < 2:
        return []

    results: List[Dict[str, str]] = []
    headers = {"User-Agent": "JarvisSentientAI/2.0 (Windows; ES)"}
    try:
        async with httpx.AsyncClient(timeout=3.2, headers=headers) as client:
            r = await client.get(
                "https://es.wikipedia.org/w/api.php",
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": clean_q,
                    "utf8": 1,
                    "format": "json",
                    "srlimit": 2,
                },
            )
            if r.status_code == 200:
                search_items = r.json().get("query", {}).get("search", [])
                for item in search_items[:2]:
                    title = item.get("title", "")
                    if not title:
                        continue
                    sum_resp = await client.get(
                        f"https://es.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(title)}"
                    )
                    if sum_resp.status_code == 200:
                        extract = (sum_resp.json().get("extract") or "").strip()
                        if extract:
                            results.append({"title": f"Wikipedia: {title}", "description": extract})
    except Exception:
        pass
    return results


async def search_brave_enriched(query: str, api_key: str = DEFAULT_BRAVE_KEY) -> List[Dict[str, str]]:
    """Consulta Brave Search Web con hasta 6 resultados limpios y detallados."""
    results: List[Dict[str, str]] = []
    try:
        async with httpx.AsyncClient(timeout=3.8) as client:
            resp = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": query, "count": 6, "search_lang": "es"},
                headers={"Accept": "application/json", "X-Subscription-Token": api_key or DEFAULT_BRAVE_KEY},
            )
            if resp.status_code == 200:
                web_res = resp.json().get("web", {}).get("results", [])
                for r in web_res:
                    desc = re.sub(r"<[^>]+>", "", r.get("description", "")).strip()
                    desc = re.sub(r"https?://\S+", "", desc)
                    desc = re.sub(r"(?i)suscr[ií]bete\s+a\s+[^.]+", "", desc).strip()
                    title = re.sub(r"<[^>]+>", "", r.get("title", "")).strip()
                    if desc and len(desc) > 25:
                        results.append({"title": title, "description": desc})
    except Exception:
        pass
    return results


async def multi_source_deep_search(query: str, brave_key: str = DEFAULT_BRAVE_KEY) -> List[Dict[str, str]]:
    """
    Combina en paralelo Wikipedia en Español + Brave Web Search enriquecido
    para alimentar a Jarvis (y a Gemini/Ollama) con información profunda y verificada.
    """
    wiki_task = asyncio.create_task(search_wikipedia_es(query))
    brave_task = asyncio.create_task(search_brave_enriched(query, brave_key))
    wiki_res, brave_res = await asyncio.gather(wiki_task, brave_task, return_exceptions=True)

    combined: List[Dict[str, str]] = []
    if isinstance(wiki_res, list):
        combined.extend(wiki_res)
    if isinstance(brave_res, list):
        combined.extend(brave_res)
    return combined[:6]


def query_gemini_web_in_chrome(prompt_text: str) -> str:
    """
    Abre Gemini en Google Chrome (https://gemini.google.com/app) con la sesión activa del usuario,
    hace clic en la caja de consulta y envía la pregunta directamente a Gemini Web.
    """
    clean_p = re.sub(
        r"^(?:abre\s+gemini\s+y\s+|entra\s+a\s+gemini\s+y\s+|preg[uú]ntale\s+a\s+gemini|pregunta\s+en\s+gemini|busca\s+en\s+gemini|consulta\s+en\s+gemini)\s*[:\s]*",
        "",
        prompt_text.strip(),
        flags=re.IGNORECASE,
    ).strip()

    open_url_in_chrome("https://gemini.google.com/app")
    if not clean_p:
        return "He abierto Google Gemini en su navegador Chrome, Señor."

    time.sleep(4.2)
    left, top, right, bottom = focus_and_maximize_chrome_window("Gemini")
    w = max(800, right - left)
    h = max(600, bottom - top)
    # Caja de texto inferior central de Gemini Web
    mouse_click(left + int(w * 0.50), top + int(h * 0.86), button="left", double=False)
    time.sleep(0.25)
    send_text_and_keys(clean_p, press_enter=True)
    return f"Ya abrí Google Gemini en Chrome y envié su consulta: '{clean_p}', Señor."


def transcribe_audio_bytes_to_spanish(audio_bytes: bytes) -> str:
    """
    Convierte cualquier fragmento de audio del micrófono (WebM, Ogg, WAV, MP4) a WAV PCM 16kHz en memoria RAM
    usando PyAV (`av`) y lo transcribe al instante en español con SpeechRecognition (Google Speech API)
    o `faster-whisper` como respaldo.
    """
    if not audio_bytes or len(audio_bytes) < 200:
        return ""

    wav_buffer = io.BytesIO()
    try:
        import av
        input_container = av.open(io.BytesIO(audio_bytes))
        resampler = av.AudioResampler(format="s16", layout="mono", rate=16000)
        pcm_chunks = bytearray()
        for frame in input_container.decode(audio=0):
            resampled_frames = resampler.resample(frame)
            if not isinstance(resampled_frames, list):
                resampled_frames = [resampled_frames] if resampled_frames else []
            for rf in resampled_frames:
                pcm_chunks.extend(bytes(rf.planes[0]))
        input_container.close()

        if len(pcm_chunks) < 800:
            return ""

        with wave.open(wav_buffer, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(bytes(pcm_chunks))
    except Exception:
        return ""

    wav_bytes = wav_buffer.getvalue()
    try:
        import speech_recognition as sr
        recognizer = sr.Recognizer()
        with sr.AudioFile(io.BytesIO(wav_bytes)) as source:
            audio_data = recognizer.record(source)
        text = recognizer.recognize_google(audio_data, language="es-CO")
        return (text or "").strip()
    except Exception:
        return ""
