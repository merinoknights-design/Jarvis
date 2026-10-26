import ctypes
import json
import os
import re
import subprocess
import threading
import time
import urllib.parse
from pathlib import Path
from typing import Optional, Tuple, List
import httpx
import pyautogui
from PIL import ImageGrab

pyautogui.FAILSAFE = False
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
    """Escribe cualquier texto o comentario en la ventana activa usando portapapeles + Ctrl+V."""
    import pyperclip
    pyperclip.copy(text)
    time.sleep(0.1)
    pyautogui.hotkey("ctrl", "v")
    if press_enter:
        time.sleep(0.12)
        pyautogui.press("enter")


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
                    c_name = (ctrl.window_text() or "").strip().lower()
                    if c_name and target_low in c_name:
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


def find_text_on_screen_and_click(target_text: str, double_click: bool = False, right_click: bool = False) -> Optional[Tuple[int, int]]:
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
    """Busca el primer video de YouTube y lo abre reproduciéndose directamente."""
    direct_url = resolve_youtube_video_url(query)
    if direct_url:
        os.startfile(direct_url)
        return f"Reproduciendo '{query}' directamente en YouTube, Señor."
    q = urllib.parse.quote(query.strip())
    os.startfile(f"https://www.youtube.com/results?search_query={q}")
    return f"Abriendo resultados de '{query}' en YouTube, Señor."
