import json
import os
import re
from pathlib import Path
from typing import Dict, Any

UPLOAD_DIR = Path("C:/Jarvis/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def analyze_step_file(file_path: Path) -> str:
    """Analiza archivos CAD .STEP / .STP extrayendo entidades sólidas, caras, curvas y producto."""
    text = file_path.read_text(encoding="utf-8", errors="ignore")
    products = re.findall(r"PRODUCT\s*\(\s*'([^']*)'", text)
    solids = len(re.findall(r"MANIFOLD_SOLID_BREP", text))
    faces = len(re.findall(r"ADVANCED_FACE", text))
    cylinders = len(re.findall(r"CYLINDRICAL_SURFACE", text))
    planes = len(re.findall(r"PLANE\s*\(", text))
    circles = len(re.findall(r"CIRCLE\s*\(", text))
    edges = len(re.findall(r"EDGE_CURVE", text))

    return (
        f"📐 Análisis Geométrico CAD (.STEP) de '{file_path.name}':\n"
        f"• Piezas/Productos detectados: {', '.join(set(products[:8])) if products else 'Sólido Principal'}\n"
        f"• Sólidos B-Rep cerrados (MANIFOLD_SOLID_BREP): {solids}\n"
        f"• Caras sólidas avanzadas (ADVANCED_FACE): {faces}\n"
        f"• Superficies planas: {planes} | Superficies cilíndricas: {cylinders}\n"
        f"• Aristas (EDGE_CURVE): {edges} | Círculos/Taladros: {circles}"
    )


def analyze_solidedge_binary(file_path: Path) -> str:
    """Analiza archivos nativos de Solid Edge (.par, .asm, .psm, .dft) vía API COM o inspección binaria OLE."""
    ext = file_path.suffix.lower()
    tipo = {
        ".par": "Pieza Sólida de Solid Edge (PartDocument)",
        ".asm": "Ensamblaje de Solid Edge (AssemblyDocument)",
        ".psm": "Pieza de Chapa Metálica (SheetMetalDocument)",
        ".dft": "Plano Técnico 2D (DraftDocument)",
    }.get(ext, "Documento CAD Solid Edge")

    size_kb = round(file_path.stat().st_size / 1024, 1)
    info = [f"⚙️ Archivo Nativo Siemens Solid Edge: '{file_path.name}' ({size_kb} KB)", f"• Tipo: {tipo}"]

    # Intentar abrir/inspeccionar sus operaciones reales en Solid Edge si está disponible
    try:
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        se_app = win32com.client.Dispatch("SolidEdge.Application")
        se_app.Visible = True
        doc = se_app.Documents.Open(str(file_path))
        if ext == ".par":
            models_count = doc.Models.Count
            sketches_count = doc.ProfileSets.Count
            info.append(f"• Cuerpos Sólidos en el Árbol: {models_count}")
            info.append(f"• Bocetos 2D (ProfileSets): {sketches_count}")
            if models_count > 0:
                body = doc.Models.Item(1).Body
                info.append(f"• Aristas del sólido: {body.Edges(1).Count} | Caras: {body.Faces(1).Count}")
        elif ext == ".asm":
            occ_count = doc.Occurrences.Count
            sub_names = [doc.Occurrences.Item(i).Name for i in range(1, min(occ_count + 1, 12))]
            info.append(f"• Componentes en el Árbol de Ensamblaje ({occ_count}): {', '.join(sub_names)}")
    except Exception:
        pass

    return "\n".join(info)


def analyze_pdf(file_path: Path) -> str:
    from pypdf import PdfReader
    reader = PdfReader(str(file_path))
    num_pages = len(reader.pages)
    extracted = []
    for i in range(min(num_pages, 5)):
        extracted.append(reader.pages[i].extract_text() or "")
    full_text = "\n".join(extracted).strip()
    return (
        f"📕 Documento PDF '{file_path.name}' ({num_pages} páginas):\n"
        f"Contenido extraído:\n{full_text[:2500]}"
    )


def analyze_word(file_path: Path) -> str:
    import docx
    doc = docx.Document(str(file_path))
    paras = [p.text for p in doc.paragraphs if p.text.strip()]
    tables_count = len(doc.tables)
    content = "\n".join(paras)[:2500]
    return (
        f"📘 Documento Word '{file_path.name}' ({len(paras)} párrafos, {tables_count} tablas):\n"
        f"{content}"
    )


def analyze_excel(file_path: Path) -> str:
    import openpyxl
    wb = openpyxl.load_workbook(str(file_path), data_only=True)
    sheet = wb.active
    rows = []
    for r in list(sheet.iter_rows(values_only=True))[:15]:
        if any(r):
            rows.append(" | ".join([str(c) if c is not None else "" for c in r]))
    return (
        f"📊 Hoja de Cálculo Excel '{file_path.name}' (Hojas: {', '.join(wb.sheetnames)}):\n"
        + "\n".join(rows[:15])
    )


def analyze_image(file_path: Path) -> str:
    from PIL import Image
    img = Image.open(str(file_path))
    w, h = img.size
    mode = img.mode
    fmt = img.format

    ocr_text = ""
    try:
        from rapidocr_onnxruntime import RapidOCR
        engine = RapidOCR()
        result, _ = engine(str(file_path))
        if result:
            ocr_text = " | ".join([line[1] for line in result])
    except Exception:
        pass

    res = (
        f"🖼️ Imagen '{file_path.name}':\n"
        f"• Resolución: {w} x {h} px | Modo de color: {mode} | Formato: {fmt}\n"
    )
    if ocr_text:
        res += f"• Texto/Cotas detectadas por visión OCR en la imagen:\n  \"{ocr_text[:1500]}\""
    else:
        res += "• Imagen visual procesada correctamente (sin texto impreso detectado)."
    return res


def analyze_audio_or_video(file_path: Path) -> str:
    ext = file_path.suffix.lower()
    info = [f"🎬 Archivo Multimedia '{file_path.name}' ({round(file_path.stat().st_size / (1024*1024), 2)} MB):"]

    try:
        import av
        container = av.open(str(file_path))
        duration_sec = round(float(container.duration / av.time_base), 1) if container.duration else 0
        info.append(f"• Duración: {duration_sec} segundos")
        for stream in container.streams:
            if stream.type == "video":
                info.append(f"• Pista de Video: {stream.codec_context.name} ({stream.width}x{stream.height} px a {float(stream.average_rate or 0):.1f} FPS)")
            elif stream.type == "audio":
                info.append(f"• Pista de Audio: {stream.codec_context.name} ({stream.rate} Hz, {stream.channels} canales)")
        container.close()
    except Exception:
        pass

    # Transcribir voz si el archivo tiene audio corto/mediano usando faster-whisper
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        segments, _ = model.transcribe(str(file_path), beam_size=1)
        transcript = " ".join([seg.text for seg in segments]).strip()
        if transcript:
            info.append(f"• Transcripción de Audio/Voz detectada:\n  \"{transcript[:1500]}\"")
    except Exception:
        pass

    return "\n".join(info)


def analyze_any_file(file_path: Path) -> str:
    """Detecta y analiza cualquier archivo subido por el usuario."""
    ext = file_path.suffix.lower()
    try:
        if ext in [".step", ".stp", ".iges", ".igs"]:
            return analyze_step_file(file_path)
        elif ext in [".par", ".asm", ".psm", ".dft"]:
            return analyze_solidedge_binary(file_path)
        elif ext == ".stl":
            size_kb = round(file_path.stat().st_size / 1024, 1)
            return f"🧊 Malla 3D STL '{file_path.name}' ({size_kb} KB) lista para impresión 3D o importación en Solid Edge."
        elif ext == ".pdf":
            return analyze_pdf(file_path)
        elif ext in [".docx", ".doc"]:
            return analyze_word(file_path)
        elif ext in [".xlsx", ".xls"]:
            return analyze_excel(file_path)
        elif ext in [".jpg", ".jpeg", ".png", ".bmp", ".webp", ".gif"]:
            return analyze_image(file_path)
        elif ext in [".mp3", ".wav", ".m4a", ".ogg", ".mp4", ".mkv", ".avi", ".mov"]:
            return analyze_audio_or_video(file_path)
        else:
            text = file_path.read_text(encoding="utf-8", errors="ignore")[:2500]
            return f"📄 Archivo '{file_path.name}':\n{text}"
    except Exception as e:
        return f"Archivo '{file_path.name}' recibido ({round(file_path.stat().st_size/1024, 1)} KB). Detalle técnico: {e}"
