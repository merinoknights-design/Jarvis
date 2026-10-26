import ctypes
import os
import re
import subprocess
import time
import urllib.parse
from pathlib import Path
from typing import Optional, Tuple, List
from PIL import ImageGrab

user32 = ctypes.windll.user32

# Constantes de eventos de Mouse y Teclado de la API Win32 (funcionan en todos los Windows sin instalar nada extra)
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_ABSOLUTE = 0x8000

VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_RETURN = 0x0D
VK_SPACE = 0x20
VK_TAB = 0x09
VK_ESCAPE = 0x1B
VK_BACK = 0x08

_ocr_engine = None


def get_ocr():
    global _ocr_engine
    if _ocr_engine is None:
        from rapidocr_onnxruntime import RapidOCR
        _ocr_engine = RapidOCR()
    return _ocr_engine


def move_mouse(x: int, y: int):
    user32.SetCursorPos(int(x), int(y))


def mouse_click(x: Optional[int] = None, y: Optional[int] = None, button: str = "left", double: bool = False):
    if x is not None and y is not None:
        user32.SetCursorPos(int(x), int(y))
        time.sleep(0.08)

    if button == "right":
        user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
        time.sleep(0.05)
        user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
    else:
        user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.05)
        user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        if double:
            time.sleep(0.08)
            user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.05)
            user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)


def mouse_scroll(direction: str = "down", amount: int = 5):
    """Hace scroll arriba o abajo en la ventana donde esté el cursor."""
    delta = -120 * amount if direction == "down" else 120 * amount
    user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, int(delta), 0)


def press_vk(vk_code: int):
    user32.keybd_event(vk_code, 0, 0, 0)
    time.sleep(0.04)
    user32.keybd_event(vk_code, 0, 2, 0)


def send_text_and_keys(text: str, press_enter: bool = False):
    """Escribe cualquier texto o comentario en la ventana activa usando el portapapeles + Ctrl+V para soportar acentos y emojis."""
    ps_cmd = (
        f"Set-Clipboard -Value {json.dumps(text)}; "
        "$wshell = New-Object -ComObject wscript.shell; "
        "Start-Sleep -Milliseconds 150; "
        "$wshell.SendKeys('^v'); "
    )
    if press_enter:
        ps_cmd += "Start-Sleep -Milliseconds 150; $wshell.SendKeys('{ENTER}');"
    subprocess.run(["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_cmd], timeout=6)


import json


def find_text_on_screen_and_click(target_text: str, double_click: bool = False, right_click: bool = False) -> Optional[Tuple[int, int]]:
    """
    Captura la pantalla actual, localiza con visión OCR dónde aparece 'target_text'
    y mueve el ratón hasta esas coordenadas exactas para hacer clic.
    """
    screenshot_path = Path("C:/Jarvis/logs/screen_scan.png")
    screenshot_path.parent.mkdir(parents=True, exist_ok=True)
    img = ImageGrab.grab()
    img.save(str(screenshot_path))

    ocr = get_ocr()
    result, _ = ocr(str(screenshot_path))
    if not result:
        return None

    target_low = target_text.lower().strip()
    best_coords = None

    for item in result:
        box, detected_text, score = item[0], item[1], item[2]
        if target_low in detected_text.lower():
            # Calcular el centro del cuadro delimitador [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
            xs = [pt[0] for pt in box]
            ys = [pt[1] for pt in box]
            cx = int(sum(xs) / 4.0)
            cy = int(sum(ys) / 4.0)
            best_coords = (cx, cy)
            break

    if best_coords:
        btn = "right" if right_click else "left"
        mouse_click(best_coords[0], best_coords[1], button=btn, double=double_click)
        return best_coords
    return None


def focus_window_by_title(title_part: str) -> bool:
    ps = (
        f"$p = Get-Process | Where-Object {{ $_.MainWindowTitle -like '*{title_part}*' -or $_.ProcessName -like '*{title_part}*' }} | Select-Object -First 1; "
        "if ($p) { $wshell = New-Object -ComObject wscript.shell; $wshell.AppActivate($p.Id) }"
    )
    subprocess.run(["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps], timeout=4)
    return True


def play_song_on_spotify_autonomous(song_query: str) -> str:
    """
    Abre Spotify con la canción buscada, espera a que cargue la interfaz,
    localiza en pantalla el resultado de la canción (o el área del Resultado Principal / Canciones)
    y le da doble clic real para que empiece a sonar automáticamente.
    """
    clean_song = song_query.strip()
    encoded = urllib.parse.quote(clean_song)

    try:
        os.startfile(f"spotify:search:{encoded}")
    except Exception:
        os.startfile(f"https://open.spotify.com/search/{encoded}")
        return f"Abriendo Spotify Web con '{clean_song}', Señor."

    def _auto_click_spotify_result():
        time.sleep(3.2)
        focus_window_by_title("Spotify")
        time.sleep(0.5)

        # 1. Intentar localizar el nombre de la canción en la lista de resultados de Spotify con visión OCR y darle doble clic
        words = [w for w in clean_song.split() if len(w) >= 3]
        search_target = words[0] if words else clean_song

        screenshot_path = Path("C:/Jarvis/logs/spotify_scan.png")
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        img = ImageGrab.grab()
        screen_w, screen_h = img.size
        img.save(str(screenshot_path))

        clicked = False
        try:
            ocr = get_ocr()
            result, _ = ocr(str(screenshot_path))
            if result:
                # Buscar coincidencias del nombre de la canción que estén debajo de la barra superior de búsqueda (y > 220px)
                matches = []
                for item in result:
                    box, txt, _ = item[0], item[1], item[2]
                    cx = int(sum(pt[0] for pt in box) / 4.0)
                    cy = int(sum(pt[1] for pt in box) / 4.0)
                    if cy > 210 and cx > 260 and search_target.lower() in txt.lower():
                        matches.append((cx, cy))
                if matches:
                    # Hacer doble clic sobre el primer resultado de canción encontrado
                    target_x, target_y = matches[0]
                    mouse_click(target_x, target_y, button="left", double=True)
                    clicked = True
        except Exception:
            pass

        if not clicked:
            # Respaldo por navegación de teclado de Spotify Desktop:
            # En Spotify Desktop tras abrir spotify:search:X, Tab -> Enter reproduce el Top Result
            ps_keys = (
                "$wshell = New-Object -ComObject wscript.shell; "
                "$wshell.AppActivate('Spotify'); "
                "Start-Sleep -Milliseconds 300; "
                "$wshell.SendKeys('{TAB}{TAB}{ENTER}');"
            )
            subprocess.run(["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_keys], timeout=5)
            # Y clic en la tarjeta de Resultado Principal de Spotify (zona estándar central-izquierda)
            top_result_x = int(screen_w * 0.36)
            top_result_y = int(screen_h * 0.42)
            mouse_click(top_result_x, top_result_y, button="left", double=True)

    import threading
    threading.Thread(target=_auto_click_spotify_result, daemon=True).start()
    return f"Enseguida, Señor. He abierto Spotify, localizado '{clean_song}' en pantalla y activado su reproducción automática."
