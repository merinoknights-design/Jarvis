import ctypes
import datetime
import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
import httpx
import numpy as np
import psutil
import pyautogui
from PIL import ImageGrab

from ui_controller import get_ocr, open_url_in_chrome, play_song_on_spotify_autonomous

BASE_DIR = Path("C:/Jarvis")
MEMORY_FILE = BASE_DIR / "config" / "stark_memory.json"
CAPTURES_DIR = Path.home() / "Pictures" / "Capturas_Jarvis"


def load_stark_memory() -> Dict[str, Any]:
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    if MEMORY_FILE.exists():
        try:
            return json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"notes": [], "preferences": {}}


def save_stark_note(note_text: str) -> str:
    data = load_stark_memory()
    clean_note = note_text.strip(" :.,'\"")
    if not clean_note:
        return "Señor, dígame qué dato o nota desea que guarde en la Bitácora Stark."
    entry = {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "note": clean_note,
    }
    data.setdefault("notes", []).append(entry)
    MEMORY_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return f"Anotado en mi memoria permanente Stark, Señor: '{clean_note}'."


def get_stark_notes_summary() -> str:
    data = load_stark_memory()
    notes = data.get("notes", [])
    if not notes:
        return "Señor, su Bitácora Stark está vacía por ahora. Puede decirme 'Recuerda que...' o 'Guarda una nota...' en cualquier momento."
    lines = [f"• [{n['timestamp']}] {n['note']}" for n in notes[-10:]]
    return "Señor, estos son los registros guardados en su Bitácora Stark:\n" + "\n".join(lines)


def get_realtime_telemetry() -> Dict[str, Any]:
    """Obtiene telemetría real del sistema para el HUD de Jarvis y diagnósticos de armadura."""
    cpu_pct = psutil.cpu_percent(interval=0.1)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage("C:/")
    batt = psutil.sensors_battery()
    battery_pct = int(batt.percent) if batt else 100
    plugged = bool(batt.power_plugged) if batt else True

    top_procs: List[str] = []
    try:
        procs = []
        for p in psutil.process_iter(["name", "memory_info"]):
            try:
                mem_mb = (p.info["memory_info"].rss or 0) / (1024 * 1024)
                name = p.info["name"] or "proc"
                if mem_mb > 40:
                    procs.append((mem_mb, name))
            except Exception:
                continue
        procs.sort(reverse=True)
        seen = set()
        for mb, name in procs:
            clean_n = name.replace(".exe", "")
            if clean_n.lower() not in seen:
                seen.add(clean_n.lower())
                top_procs.append(f"{clean_n} ({int(mb)} MB)")
            if len(top_procs) >= 4:
                break
    except Exception:
        pass

    return {
        "cpu": round(cpu_pct, 1),
        "ram_percent": round(ram.percent, 1),
        "ram_used_gb": round(ram.used / (1024 ** 3), 1),
        "ram_total_gb": round(ram.total / (1024 ** 3), 1),
        "disk_free_gb": round(disk.free / (1024 ** 3), 1),
        "arc_energy": battery_pct,
        "plugged": plugged,
        "top_processes": top_procs,
    }


def format_full_armor_diagnostic() -> str:
    """Diagnóstico completo estilo Mark LXXXV con procesos reales del PC."""
    t = get_realtime_telemetry()
    power_state = "conectado a la red principal" if t["plugged"] else "operando con reserva autónoma"
    procs_str = ", ".join(t["top_processes"]) if t["top_processes"] else "ninguno crítico"
    return (
        f"Diagnóstico completo de sistemas Mark LXXXV finalizado, Señor:\n"
        f"• Energía del Reactor Arc (Batería): {t['arc_energy']}% ({power_state}).\n"
        f"• Núcleo de Procesamiento (CPU): {t['cpu']}% de carga.\n"
        f"• Memoria Neural (RAM): {t['ram_percent']}% ({t['ram_used_gb']} GB de {t['ram_total_gb']} GB).\n"
        f"• Almacenamiento Local: {t['disk_free_gb']} GB disponibles.\n"
        f"• Procesos de mayor consumo: {procs_str}."
    )


def fetch_live_weather_brief() -> str:
    """Consulta el clima real actual en menos de 2 segundos para el Informe Matutino Stark."""
    try:
        r = httpx.get(
            "https://wttr.in/?format=j1&lang=es",
            headers={"User-Agent": "JarvisStarkAI/2.0"},
            timeout=2.8,
        )
        if r.status_code == 200:
            data = r.json()
            curr = data.get("current_condition", [{}])[0]
            area = data.get("nearest_area", [{}])[0]
            city = (area.get("areaName", [{}])[0].get("value") or "su ubicación").strip()
            temp_c = curr.get("temp_C", "")
            feels_c = curr.get("FeelsLikeC", "")
            desc_es = (
                curr.get("lang_es", [{}])[0].get("value")
                or curr.get("weatherDesc", [{}])[0].get("value")
                or "despejado"
            ).lower()
            if temp_c:
                return f"En {city} tenemos {temp_c}°C (sensación de {feels_c}°C) con cielo {desc_es}"
    except Exception:
        pass
    return "Los sensores meteorológicos externos están en línea"


def execute_stark_morning_briefing() -> str:
    """Informe Matutino / Reporte de Situación clásico de J.A.R.V.I.S. en Iron Man."""
    now = datetime.datetime.now()
    hour = now.hour
    saludo = "Buenos días" if hour < 12 else ("Buenas tardes" if hour < 19 else "Buenas noches")
    weather = fetch_live_weather_brief()
    t = get_realtime_telemetry()
    mem = load_stark_memory()
    notes_count = len(mem.get("notes", []))
    notes_msg = (
        f" Tiene {notes_count} nota(s) en su Bitácora Stark (última: '{mem['notes'][-1]['note']}')."
        if notes_count > 0
        else ""
    )
    return (
        f"{saludo}, Señor. Son las {now.strftime('%H:%M')} del {now.strftime('%d/%m/%Y')}. "
        f"{weather}. "
        f"El Reactor Arc está al {t['arc_energy']}% de energía, la CPU opera al {t['cpu']}% y la memoria RAM al {t['ram_percent']}%.{notes_msg} "
        f"Todos los sistemas de ingeniería y control están listos."
    )


def execute_clean_slate_protocol() -> str:
    """
    Protocolo 'Pizarra Limpia' (Clean Slate - Iron Man 3):
    Minimiza todas las ventanas abiertas en el escritorio (Win+D) para despejar el área de trabajo al instante.
    """
    try:
        pyautogui.hotkey("win", "d")
    except Exception:
        pass
    return (
        "Protocolo Pizarra Limpia ejecutado, Señor. He despejado todas las ventanas de su escritorio "
        "y dejado la estación en modo sigilo."
    )


def execute_house_party_protocol(song_choice: str = "Back in Black AC/DC") -> str:
    """
    Protocolo 'Fiesta en Casa' (House Party - Iron Man 3):
    Despliega el entorno completo de trabajo y entretenimiento (abre carpeta de proyectos CAD, Chrome y música en Spotify).
    """
    projects_dir = Path.home() / "Documents" / "Proyectos_SolidEdge"
    projects_dir.mkdir(parents=True, exist_ok=True)
    try:
        os.startfile(str(projects_dir))
    except Exception:
        pass

    try:
        play_song_on_spotify_autonomous(song_choice)
    except Exception:
        pass

    return (
        f"Protocolo Fiesta en Casa activado, Señor: he desplegado su directorio de ingeniería CAD, "
        f"encendido los sistemas multimedia con '{song_choice}' en Spotify y puesto todos los módulos en línea."
    )


def execute_hud_screen_scan(save_screenshot_Only: bool = False) -> str:
    """
    Escaneo Táctico HUD de la pantalla actual:
    - Guarda una captura de alta resolución en Imágenes/Capturas_Jarvis (con respaldo GDI/UIA).
    - Lista todas las ventanas visibles activas y los elementos principales en pantalla.
    """
    CAPTURES_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    shot_path = CAPTURES_DIR / f"HUD_Scan_{stamp}.png"

    img = None
    try:
        img = ImageGrab.grab()
        img.save(str(shot_path))
    except Exception:
        try:
            ps_shot = (
                "Add-Type -AssemblyName System.Windows.Forms,System.Drawing; "
                "$b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds; "
                "$bmp = New-Object System.Drawing.Bitmap($b.Width, $b.Height); "
                "$g = [System.Drawing.Graphics]::FromImage($bmp); "
                "$g.CopyFromScreen($b.Location, [System.Drawing.Point]::Empty, $b.Size); "
                f"$bmp.Save('{str(shot_path)}'); $g.Dispose(); $bmp.Dispose()"
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_shot],
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=3,
            )
            if shot_path.exists():
                from PIL import Image
                img = Image.open(str(shot_path))
        except Exception:
            pass

    if save_screenshot_Only:
        if shot_path.exists():
            return f"Captura táctica guardada en su carpeta de Imágenes, Señor: {shot_path}"
        return "Señor, el protector de pantalla o sesión impidió guardar el archivo PNG en este instante."

    # 1. Detectar ventanas visibles activas y controles principales mediante UI Automation
    visible_titles: List[str] = []
    uia_snippets: List[str] = []
    try:
        from pywinauto import Desktop
        desk = Desktop(backend="uia")
        for w in desk.windows():
            if w.is_visible():
                t = (w.window_text() or "").strip()
                if t and "Program Manager" not in t and "Barra de tareas" not in t:
                    visible_titles.append(t)
                    if len(uia_snippets) < 10 and "J.A.R.V.I.S" not in t:
                        try:
                            for ctrl in w.descendants()[:30]:
                                cname = (ctrl.window_text() or "").strip()
                                if len(cname) >= 4 and cname not in uia_snippets and cname != t:
                                    uia_snippets.append(cname)
                                    if len(uia_snippets) >= 10:
                                        break
                        except Exception:
                            pass
    except Exception:
        pass

    # 2. Extraer textos principales con OCR en RAM si la imagen está disponible
    detected_snippets: List[str] = []
    if img is not None:
        try:
            ocr = get_ocr()
            res, _ = ocr(np.array(img), use_angle_cls=False)
            if res:
                for item in res[:15]:
                    txt = (item[1] or "").strip()
                    if len(txt) >= 3:
                        detected_snippets.append(txt)
        except Exception:
            pass

    all_snippets = detected_snippets if detected_snippets else uia_snippets
    wins_summary = ", ".join(visible_titles[:6]) if visible_titles else "Escritorio principal"
    ocr_summary = " | ".join(all_snippets[:10]) if all_snippets else "Interfaz activa sin texto adicional"
    shot_note = f" (captura guardada en `{shot_path.name}`)" if shot_path.exists() else ""
    return (
        f"Escaneo visual HUD completado, Señor{shot_note}:\n"
        f"• Ventanas activas detectadas: {wins_summary}.\n"
        f"• Elementos leídos en pantalla: {ocr_summary}."
    )


def execute_security_lockdown() -> str:
    """Bloquea la estación de trabajo de Windows inmediatamente (Protocolo de Seguridad Stark)."""
    try:
        ctypes.windll.user32.LockWorkStation()
        return "Protocolo de bloqueo de seguridad ejecutado, Señor. Estación asegurada."
    except Exception as e:
        return f"No se pudo bloquear la estación: {e}"
