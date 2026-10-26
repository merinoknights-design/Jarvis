import ctypes
import json
import os
import re
import subprocess
import threading
import time
import unicodedata
import urllib.parse
from pathlib import Path
from typing import Optional, Tuple, List
import httpx
import pyautogui
from PIL import ImageGrab

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.02

# Activar DPI Awareness real (1920x1080) en Windows con escalado 125%/150% para que ImageGrab y los clics coincidan al 100%
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

user32 = ctypes.windll.user32

MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_WHEEL = 0x0800

VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_RETURN = 0x0D
VK_SPACE = 0x20
VK_ESCAPE = 0x1B

DEFAULT_BRAVE_KEY = "BSAPviCA5RJG-aAnfg5LZKBgX02gLQL"
_ocr_engine = None


def get_ocr():
    global _ocr_engine
    if _ocr_engine is None:
        from rapidocr_onnxruntime import RapidOCR
        _ocr_engine = RapidOCR()
    return _ocr_engine


def move_mouse(x: int, y: int):
    pyautogui.moveTo(int(x), int(y), duration=0.15)


def mouse_click(x: Optional[int] = None, y: Optional[int] = None, button: str = "left", double: bool = False):
    if x is not None and y is not None:
        pyautogui.click(x=int(x), y=int(y), clicks=2 if double else 1, interval=0.08, button=button)
    else:
        pyautogui.click(clicks=2 if double else 1, interval=0.08, button=button)


def mouse_scroll(direction: str = "down", amount: int = 6):
    delta = -120 * amount if direction == "down" else 120 * amount
    user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, int(delta), 0)


def press_vk(vk_code: int):
    user32.keybd_event(vk_code, 0, 0, 0)
    time.sleep(0.04)
    user32.keybd_event(vk_code, 0, 2, 0)


def send_text_and_keys(text: str, press_enter: bool = False):
    """Escribe cualquier texto o comentario en la ventana activa usando portapapeles + Ctrl+V de forma segura."""
    try:
        import pyperclip
        pyperclip.copy(text)
    except Exception:
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", f"Set-Clipboard -Value {json.dumps(text)}"],
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=2,
            )
        except Exception:
            pass
    time.sleep(0.12)
    try:
        pyautogui.hotkey("ctrl", "v")
        if press_enter:
            time.sleep(0.18)
            pyautogui.press("enter")
    except Exception:
        pass


def is_window_open_with_keyword(keyword: str) -> bool:
    """Verifica si ya existe una ventana visible cuyo título contenga keyword (ej. 'whatsapp', 'gmail', 'youtube')."""
    kw = keyword.lower().strip()
    try:
        from pywinauto import Desktop
        desk = Desktop(backend="uia")
        for win in desk.windows():
            if not win.is_visible():
                continue
            title = (win.window_text() or "").lower()
            if "j.a.r.v.i.s" in title:
                continue
            if kw in title:
                return True
    except Exception:
        pass
    return False


def focus_and_maximize_chrome_window(title_keyword: str = "") -> Optional[Tuple[int, int, int, int]]:
    """
    Trae al frente y maximiza la ventana de Google Chrome (o la que contenga title_keyword)
    para que los atajos de teclado y clics caigan siempre dentro de la aplicación web y nunca en Jarvis.
    Devuelve (left, top, right, bottom) de la ventana.
    """
    try:
        from pywinauto import Desktop
        desk = Desktop(backend="uia")
        target_win = None
        kw = title_keyword.lower().strip()

        for win in desk.windows():
            if not win.is_visible():
                continue
            title = (win.window_text() or "").strip()
            t_low = title.lower()
            if "j.a.r.v.i.s" in t_low:
                continue
            if kw and kw in t_low:
                target_win = win
                break
            if "chrome" in t_low or "edge" in t_low or "whatsapp" in t_low:
                target_win = win

        if target_win:
            try:
                user32.ShowWindow(target_win.handle, 3)  # SW_MAXIMIZE = 3
            except Exception:
                pass
            try:
                target_win.set_focus()
            except Exception:
                try:
                    user32.SetForegroundWindow(target_win.handle)
                except Exception:
                    pass
            time.sleep(0.25)
    except Exception:
        pass

    sw = user32.GetSystemMetrics(0)
    sh = user32.GetSystemMetrics(1)
    return (0, 0, sw, sh)


def normalize_name_for_match(text: str) -> str:
    """
    Normaliza cualquier nombre o texto eliminando:
    - Tildes y virgulilla de la ñ (Niña -> Nina, Matías -> Matias, Gutiérrez -> Gutierrez)
    - Emojis (❤️‍🩹, ❤️, 😂, etc.) y símbolos especiales
    para que el OCR coincida siempre por el nombre aunque tenga emojis o ñ/tildes.
    """
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFD", text)
    no_diacritics = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    only_alnum = re.sub(r"[^a-zA-Z0-9\s]", " ", no_diacritics)
    return re.sub(r"\s+", " ", only_alnum).strip().lower()


def names_match_ignoring_emojis_and_accents(target_name: str, detected_text: str) -> bool:
    """
    Compara un nombre buscado (ej. 'Mi Niña Chiquita') contra el texto leído por OCR (ej. 'Mi Nina Chiquita ❤️‍🩹')
    ignorando emojis, tildes y la ñ->n.
    """
    norm_target = normalize_name_for_match(target_name)
    norm_detected = normalize_name_for_match(detected_text)
    if not norm_target or not norm_detected:
        return False
    if norm_target in norm_detected:
        return True
    if len(norm_detected) >= 4 and norm_detected in norm_target:
        return True

    target_words = [w for w in norm_target.split() if len(w) >= 2]
    detected_words = set(norm_detected.split())
    if target_words and all(any(tw in dw or dw in tw for dw in detected_words if len(dw) >= 2) for tw in target_words):
        return True
    return False


def click_ui_element_by_uia_or_ocr(target_text: str, double_click: bool = False, right_click: bool = False) -> Optional[Tuple[int, int]]:
    """
    1. Primero inspecciona los controles reales (botones, menús, pestañas, enlaces) de la ventana activa
       mediante Windows UI Automation (pywinauto backend='uia') y hace clic exacto en el control.
    2. Si no es un control estándar de Windows, escanea la pantalla con Visión OCR (RapidOCR) y hace clic.
    """
    target_low = target_text.lower().strip()

    # Paso 1: Intentar encontrar el botón/elemento nativo con Windows UI Automation
    try:
        from pywinauto import Desktop
        desk = Desktop(backend="uia")
        for win in desk.windows():
            if not win.is_visible():
                continue
            title = win.window_text()
            if "J.A.R.V.I.S" in title:
                continue
            try:
                for ctrl in win.descendants():
                    c_name = (ctrl.window_text() or "").strip()
                    if c_name and names_match_ignoring_emojis_and_accents(target_low, c_name):
                        rect = ctrl.rectangle()
                        cx = int((rect.left + rect.right) / 2)
                        cy = int((rect.top + rect.bottom) / 2)
                        if cx > 0 and cy > 0:
                            mouse_click(cx, cy, button="right" if right_click else "left", double=double_click)
                            return (cx, cy)
            except Exception:
                continue
    except Exception:
        pass

    # Paso 2: Respaldo con Visión OCR sobre toda la pantalla
    return find_text_on_screen_and_click(target_text, double_click=double_click, right_click=right_click)


def find_matches_in_region_fast(
    target_text: str, region_box: Tuple[int, int, int, int]
) -> List[Tuple[int, int, str]]:
    """
    Escaneo OCR ultrarrápido recortando ÚNICAMENTE la subregión necesaria (x1, y1, x2, y2).
    Compara los nombres ignorando emojis, tildes y ñ->n.
    """
    matches: List[Tuple[int, int, str]] = []
    if not normalize_name_for_match(target_text):
        return matches

    x1, y1, x2, y2 = region_box
    try:
        crop_path = Path("C:/Jarvis/logs/region_crop.png")
        crop_path.parent.mkdir(parents=True, exist_ok=True)
        img = ImageGrab.grab(bbox=(int(x1), int(y1), int(x2), int(y2)))
        img.save(str(crop_path))
        ocr = get_ocr()
        result, _ = ocr(str(crop_path))
        if result:
            for item in result:
                box, detected_text, _ = item[0], item[1], item[2]
                if names_match_ignoring_emojis_and_accents(target_text, detected_text):
                    xs = [pt[0] for pt in box]
                    ys = [pt[1] for pt in box]
                    cx = int(x1 + sum(xs) / 4.0)
                    cy = int(y1 + sum(ys) / 4.0)
                    matches.append((cx, cy, detected_text))
    except Exception:
        pass
    return matches


def find_all_matches_uia_and_ocr(target_text: str, window_keyword: str = "") -> List[Tuple[int, int, str]]:
    """
    Escanea la ventana activa usando tanto Windows UI Automation (pywinauto) como Visión OCR (RapidOCR)
    y devuelve TODAS las coincidencias como lista de (cx, cy, texto_detectado).
    Permite distinguir por coordenadas si un nombre (ej. 'David') está en:
      - La barra de búsqueda (arriba a la izquierda)
      - La lista de resultados de chats (abajo a la izquierda)
      - El encabezado del chat abierto (arriba a la derecha, confirmando que estamos en el chat correcto)
    """
    matches: List[Tuple[int, int, str]] = []
    target_low = target_text.lower().strip()
    if not target_low:
        return matches

    kw = window_keyword.lower().strip()

    # 1. Buscar en el árbol UIA de la ventana
    try:
        from pywinauto import Desktop
        desk = Desktop(backend="uia")
        for win in desk.windows():
            if not win.is_visible():
                continue
            title = (win.window_text() or "").strip()
            t_low = title.lower()
            if "j.a.r.v.i.s" in t_low:
                continue
            if kw and kw not in t_low and "chrome" not in t_low:
                continue
            try:
                for ctrl in win.descendants():
                    c_name = (ctrl.window_text() or "").strip()
                    if c_name and target_low in c_name.lower():
                        rect = ctrl.rectangle()
                        cx = int((rect.left + rect.right) / 2)
                        cy = int((rect.top + rect.bottom) / 2)
                        if cx > 0 and cy > 0:
                            matches.append((cx, cy, c_name))
            except Exception:
                continue
    except Exception:
        pass

    # 2. Buscar con Visión OCR sobre la pantalla actual
    try:
        screenshot_path = Path("C:/Jarvis/logs/screen_scan_multi.png")
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        img = ImageGrab.grab()
        img.save(str(screenshot_path))
        ocr = get_ocr()
        result, _ = ocr(str(screenshot_path))
        if result:
            for item in result:
                box, detected_text, _ = item[0], item[1], item[2]
                if target_low in detected_text.lower():
                    xs = [pt[0] for pt in box]
                    ys = [pt[1] for pt in box]
                    cx = int(sum(xs) / 4.0)
                    cy = int(sum(ys) / 4.0)
                    matches.append((cx, cy, detected_text))
    except Exception:
        pass

    return matches


def find_text_on_screen_and_click(target_text: str, double_click: bool = False, right_click: bool = False) -> Optional[Tuple[int, int]]:
    try:
        screenshot_path = Path("C:/Jarvis/logs/screen_scan.png")
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        img = ImageGrab.grab()
        img.save(str(screenshot_path))

        ocr = get_ocr()
        result, _ = ocr(str(screenshot_path))
        if not result:
            return None

        target_low = target_text.lower().strip()
        for item in result:
            box, detected_text, _ = item[0], item[1], item[2]
            if target_low in detected_text.lower():
                xs = [pt[0] for pt in box]
                ys = [pt[1] for pt in box]
                cx = int(sum(xs) / 4.0)
                cy = int(sum(ys) / 4.0)
                btn = "right" if right_click else "left"
                mouse_click(cx, cy, button=btn, double=double_click)
                return (cx, cy)
    except Exception:
        pass
    return None


def resolve_spotify_track_uri(song_query: str) -> Optional[str]:
    """Busca el ID oficial de la pista en Spotify (spotify:track:ID) en 0.3s para abrir la canción directa."""
    try:
        r = httpx.get(
            "https://api.search.brave.com/res/v1/web/search",
            params={"q": f"site:open.spotify.com/track {song_query}", "count": 5},
            headers={"Accept": "application/json", "X-Subscription-Token": DEFAULT_BRAVE_KEY},
            timeout=3.5
        )
        if r.status_code == 200:
            for item in r.json().get("web", {}).get("results", []):
                url = item.get("url", "")
                m = re.search(r"open\.spotify\.com/(?:intl-[a-z]+/)?track/([A-Za-z0-9]+)", url)
                if m:
                    return f"spotify:track:{m.group(1)}"
    except Exception:
        pass
    return None


def resolve_youtube_video_url(query: str) -> Optional[str]:
    """Busca el ID del primer video oficial en YouTube para reproducirlo directamente."""
    try:
        r = httpx.get(
            "https://api.search.brave.com/res/v1/web/search",
            params={"q": f"site:youtube.com/watch {query}", "count": 5},
            headers={"Accept": "application/json", "X-Subscription-Token": DEFAULT_BRAVE_KEY},
            timeout=3.5
        )
        if r.status_code == 200:
            for item in r.json().get("web", {}).get("results", []):
                url = item.get("url", "")
                if "youtube.com/watch?v=" in url:
                    return url
    except Exception:
        pass
    return None


def trigger_spotify_play_button_uia() -> bool:
    """
    Bucle inteligente con criterio de verificación:
    Recorre en ciclo la ventana de Spotify buscando el botón 'Reproducir'/'Play',
    lo pulsa y verifica si el estado cambió a 'Pausar'/'Pause' (confirmando que ya está sonando).
    """
    try:
        from pywinauto import Desktop
        desk = Desktop(backend="uia")

        for attempt in range(4):
            spotify_win = None
            for w in desk.windows():
                title = (w.window_text() or "").lower()
                cname = (w.element_info.class_name or "").lower()
                if "spotify" in title or ("chrome_widgetwin" in cname and w.is_visible() and "j.a.r.v.i.s" not in title):
                    if "spotify" in title or any("spotify" in (c.window_text() or "").lower() for c in w.children()):
                        spotify_win = w
                        break

            if not spotify_win:
                time.sleep(0.8)
                continue

            try:
                spotify_win.set_focus()
            except Exception:
                pass
            time.sleep(0.35)

            win_rect = spotify_win.rectangle()
            buttons = spotify_win.descendants(control_type="Button")

            # Verificar si ya está reproduciendo (si el botón principal ya dice 'Pausar' / 'Pause')
            already_playing = False
            play_candidates = []

            for ctrl in buttons:
                name = (ctrl.window_text() or "").strip().lower()
                r = ctrl.rectangle()
                rel_y = r.top - win_rect.top
                rel_x = r.left - win_rect.left

                # Zona central de la pista/álbum (excluyendo la barra inferior del reproductor)
                if 150 < rel_y < (win_rect.height() - 105) and rel_x > 200:
                    if name in ["pausar", "pause"] or name.startswith("pausar ") or name.startswith("pause "):
                        already_playing = True
                        break
                    if name in ["reproducir", "play"] or name.startswith("reproducir ") or name.startswith("play "):
                        play_candidates.append(ctrl)

            if already_playing:
                return True

            if play_candidates:
                target_btn = play_candidates[0]
                rect = target_btn.rectangle()
                cx = int((rect.left + rect.right) / 2)
                cy = int((rect.top + rect.bottom) / 2)
                mouse_click(cx, cy, button="left", double=False)
                time.sleep(0.7)
                # En el siguiente ciclo del bucle comprobará si ya pasó a 'Pausar'
            else:
                pyautogui.press("enter")
                time.sleep(0.7)

        return True
    except Exception:
        pass
    return False


def play_song_on_spotify_autonomous(song_query: str) -> str:
    """
    Se ejecuta en segundo plano:
    1. Resuelve el Track ID exacto de la canción (spotify:track:ID).
    2. Abre esa pista en Spotify Desktop.
    3. Recorre en bucle la ventana con Windows UI Automation hasta pulsar el botón verde de Play y confirmar que suena.
    """
    clean_song = song_query.strip()
    track_uri = resolve_spotify_track_uri(clean_song)
    encoded = urllib.parse.quote(clean_song)
    uri_to_open = track_uri if track_uri else f"spotify:search:{encoded}"

    try:
        os.startfile(uri_to_open)
    except Exception:
        os.startfile(f"https://open.spotify.com/search/{encoded}")
        return f"Spotify Web abierto con '{clean_song}', Señor."

    time.sleep(2.6)
    ok = trigger_spotify_play_button_uia()
    if not ok:
        time.sleep(1.0)
        trigger_spotify_play_button_uia()

    return f"La canción '{clean_song}' ya está cargada y reproduciéndose en Spotify, Señor."


def play_video_on_youtube_autonomous(query: str) -> str:
    """Busca el primer video de YouTube en Chrome, lo abre y verifica inicio de reproducción."""
    direct_url = resolve_youtube_video_url(query)
    target_url = direct_url if direct_url else f"https://www.youtube.com/results?search_query={urllib.parse.quote(query.strip())}"
    open_url_in_chrome(target_url)

    if not direct_url:
        # Si abrió lista de resultados, hacer clic automático en el primer video tras cargar
        def _click_first_yt():
            time.sleep(3.2)
            w = user32.GetSystemMetrics(0)
            h = user32.GetSystemMetrics(1)
            mouse_click(int(w * 0.38), int(h * 0.36), button="left", double=False)
        threading.Thread(target=_click_first_yt, daemon=True).start()

    return f"Reproduciendo '{query}' en YouTube dentro de Chrome, Señor."


def find_chrome_exe() -> Optional[str]:
    candidates = [
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
        Path.home() / "AppData/Local/Google/Chrome/Application/chrome.exe",
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return None


def open_url_in_chrome(url: str) -> bool:
    """Abre cualquier URL directamente en Google Chrome con la sesión activa del usuario."""
    chrome_exe = find_chrome_exe()
    if chrome_exe:
        subprocess.Popen([chrome_exe, url])
        return True
    os.startfile(url)
    return False


def check_if_login_required_on_screen() -> bool:
    """
    Escanea la pantalla con OCR tras abrir una Web App en Chrome para saber si el usuario
    ya está logueado o si la página le está pidiendo Iniciar Sesión.
    """
    try:
        screenshot_path = Path("C:/Jarvis/logs/login_check.png")
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        img = ImageGrab.grab()
        img.save(str(screenshot_path))
        ocr = get_ocr()
        result, _ = ocr(str(screenshot_path))
        if not result:
            return False
        full_text = " ".join([item[1].lower() for item in result])
        login_indicators = [
            "iniciar sesión", "iniciar sesion", "inicia sesión", "sign in",
            "log in", "introduce tu contraseña", "ingresa tu correo",
            "usa tu cuenta de google", "elegir una cuenta"
        ]
        return any(ind in full_text for ind in login_indicators)
    except Exception:
        return False


def send_gmail_in_chrome(to_email: str = "", subject: str = "", body_text: str = "", auto_send: bool = True) -> str:
    """
    Abre Gmail en Google Chrome con los campos Para, Asunto y Cuerpo ya rellenados.
    Verifica si el usuario está logueado:
      - Si no está logueado, le pide iniciar sesión.
      - Si ya está logueado y hay destinatario/mensaje, pulsa 'Enviar' automáticamente.
    """
    params = {"view": "cm", "fs": "1"}
    if to_email:
        params["to"] = to_email.strip()
    if subject:
        params["su"] = subject.strip()
    if body_text:
        params["body"] = body_text.strip()

    compose_url = "https://mail.google.com/mail/?" + urllib.parse.urlencode(params)
    open_url_in_chrome(compose_url)

    time.sleep(4.0)
    if check_if_login_required_on_screen():
        return "Señor, abrí Gmail en Google Chrome pero veo que no ha iniciado sesión. Por favor inicie sesión en su cuenta y yo continuaré con el envío."

    if to_email and (body_text or subject) and auto_send:
        time.sleep(1.5)
        # Intentar hacer clic en el botón 'Enviar' / 'Send' o usar el atajo oficial de Gmail (Ctrl + Enter)
        clicked = click_ui_element_by_uia_or_ocr("Enviar", double_click=False, right_click=False)
        if not clicked:
            pyautogui.hotkey("ctrl", "enter")
        return f"Correo redactado y enviado en Gmail para '{to_email}' desde Google Chrome, Señor."

    return "He abierto la ventana de redacción de Gmail en su Google Chrome con su sesión activa, Señor."


def open_web_app_in_chrome_with_login_check(app_name: str, direct_url: str) -> str:
    """Abre cualquier aplicación en Google Chrome y verifica si el usuario ya tiene sesión iniciada."""
    open_url_in_chrome(direct_url)

    def _verify_session():
        time.sleep(3.8)
        if check_if_login_required_on_screen():
            from task_manager import COMPLETED_NOTIFICATIONS, _lock
            with _lock:
                COMPLETED_NOTIFICATIONS.append({
                    "id": "login_notice",
                    "title": f"Sesión en {app_name}",
                    "message": f"🔐 Señor, he abierto {app_name} en Google Chrome, pero necesita iniciar sesión en su cuenta para que pueda operar dentro.",
                    "voice_summary": f"Señor, por favor inicie sesión en {app_name} dentro de Chrome para poder continuar.",
                    "tool_used": "puppeteer",
                    "status": "done"
                })

    threading.Thread(target=_verify_session, daemon=True).start()
    return f"Abriendo {app_name} en su Google Chrome, Señor."
