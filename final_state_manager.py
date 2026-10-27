"""
Módulo de Gestión de Estado Final y Presentación de Modelos para Siemens Solid Edge 2026.
Implementa las directrices de la Adenda de Estado Final para cualquier pieza y plano:
  1. Configuración central: CERRAR_AL_TERMINAR = False por defecto.
  2. Guardado normal sin cerrar (Save / SaveAs).
  3. Exportación a formatos neutros (STL, STEP, PNG) mediante SaveCopyAs sin cerrar el documento.
  4. Garantía de que los documentos de resultado queden abiertos, visibles y activos.
  5. Presentación visual estandarizada:
     - Ventana de Solid Edge maximizada y traída al frente en Windows.
     - Documento activo maximizado.
     - Vista isométrica con Fit (ajuste a la ventana).
     - Representación sombreada con aristas visibles.
     - Ocultamiento de planos de referencia, bocetos de construcción y elementos auxiliares.
     - Limpieza de comandos pendientes (comando Seleccionar activo, sin diálogos residuales).
     - Restauración de alertas (DisplayAlerts = True).
"""

import sys
import ctypes
from pathlib import Path
from typing import Dict, Any, List, Optional

import win32com.client

# Bandera de configuración central (por defecto False: NUNCA cerrar al terminar)
CERRAR_AL_TERMINAR: bool = False


def bring_solidedge_to_foreground(app) -> bool:
    """Trae la ventana de Solid Edge 2026 al primer plano del sistema operativo."""
    try:
        app.Visible = True
        app.WindowState = 2  # seWindowStateMaximize
    except Exception:
        pass

    try:
        hwnd = getattr(app, "hWnd", None)
        if hwnd:
            user32 = ctypes.windll.user32
            SW_RESTORE = 9
            SW_MAXIMIZE = 3
            user32.ShowWindow(hwnd, SW_RESTORE)
            user32.ShowWindow(hwnd, SW_MAXIMIZE)
            user32.SetForegroundWindow(hwnd)
            user32.BringWindowToTop(hwnd)
            return True
    except Exception:
        pass
    return False


def apply_model_presentation(doc, is_active: bool = True) -> None:
    """Aplica la presentación formal limpia del modelo en pantalla."""
    # 1. Ocultar planos de referencia
    try:
        ref_planes = doc.RefPlanes
        for i in range(1, ref_planes.Count + 1):
            ref_planes.Item(i).Visible = False
    except Exception:
        pass

    # 2. Ocultar bocetos y perfiles auxiliares
    try:
        ps = doc.ProfileSets
        for i in range(1, ps.Count + 1):
            p_set = ps.Item(i)
            for j in range(1, p_set.Profiles.Count + 1):
                p_set.Profiles.Item(j).Visible = False
    except Exception:
        pass

    try:
        sketches = getattr(doc, "Sketches", None)
        if sketches:
            for i in range(1, sketches.Count + 1):
                sketches.Item(i).Visible = False
    except Exception:
        pass

    # 3. Ocultar sistemas de coordenadas
    try:
        coords = getattr(doc, "CoordinateSystems", None)
        if coords:
            for i in range(1, coords.Count + 1):
                coords.Item(i).Visible = False
    except Exception:
        pass

    # 4. Configurar ventana y cámara 3D
    try:
        if doc.Windows.Count > 0:
            win = doc.Windows.Item(1)
            win.WindowState = 2  # Maximizado dentro del MDI de Solid Edge
            try:
                doc.Application.StartCommand(32824)  # Vista isométrica y modo sombreado con aristas
            except Exception:
                pass
            win.View.Fit()

            if is_active:
                win.Activate()
                doc.Activate()
    except Exception:
        pass


def save_and_export_without_closing(
    doc,
    save_path: Path,
    export_stl: bool = True,
    export_step: bool = True,
    capture_image: bool = True
) -> Dict[str, str]:
    """
    Guarda el documento y genera copias neutras (STL, STEP, PNG) mediante SaveCopyAs.
    EL DOCUMENTO QUEDA ABIERTO Y ACTIVO EN SOLID EDGE (sin llamadas a Close).
    """
    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    generated = {"par_file": str(save_path)}

    # 1. Guardado normal de la pieza/ensamble
    doc.SaveAs(str(save_path))

    # 2. Exportar copia STL si se solicita (para pruebas de sondas y verificación)
    if export_stl:
        stl_path = save_path.with_suffix(".stl")
        try:
            doc.SaveCopyAs(str(stl_path))
            generated["stl_file"] = str(stl_path)
        except Exception:
            pass

    # 3. Exportar copia STEP si se solicita
    if export_step:
        step_path = save_path.with_suffix(".step")
        try:
            doc.SaveCopyAs(str(step_path))
            generated["step_file"] = str(step_path)
        except Exception:
            pass

    # 4. Captura de inspección visual directa del viewport activo
    if capture_image:
        img_path = save_path.with_suffix(".png")
        try:
            if doc.Windows.Count > 0:
                win = doc.Windows.Item(1)
                try:
                    doc.Application.StartCommand(32824)
                except Exception:
                    pass
                win.View.Fit()
                win.View.SaveAsImage(str(img_path), 1920, 1080)
                generated["inspection_image"] = str(img_path)
        except Exception:
            pass

    # Dejar el modelo presentado limpiamente
    apply_model_presentation(doc, is_active=True)
    return generated


def finalize_and_verify_open_state(
    app,
    expected_doc_paths: List[Path],
    active_doc_path: Optional[Path] = None,
    cerrar_al_terminar: bool = CERRAR_AL_TERMINAR
) -> Dict[str, Any]:
    """
    Garantiza que todos los documentos de resultado queden abiertos, visibles y presentados
    en pantalla. Si se detecta pantalla de inicio, reabre automáticamente los archivos.
    """
    if cerrar_al_terminar:
        for i in range(app.Documents.Count, 0, -1):
            try:
                app.Documents.Item(i).Close(False)
            except Exception:
                pass
        return {"status": "closed", "open_documents": [], "active_document": None}

    # Asegurar que la aplicación esté visible
    app.Visible = True
    app.DisplayAlerts = False

    # Verificar si algún documento esperado fue cerrado o si estamos en pantalla de inicio
    currently_open_names = {}
    for i in range(1, app.Documents.Count + 1):
        try:
            d = app.Documents.Item(i)
            currently_open_names[Path(d.FullName).name.lower()] = d
        except Exception:
            pass

    # Reabrir cualquier documento esperado que falte
    for p in expected_doc_paths:
        p = Path(p)
        if p.exists() and p.name.lower() not in currently_open_names:
            try:
                opened_doc = app.Documents.Open(str(p))
                currently_open_names[p.name.lower()] = opened_doc
            except Exception as e:
                print(f"Aviso reabriendo {p.name}: {e}")

    # Determinar documento que debe quedar activo
    if active_doc_path is None and expected_doc_paths:
        active_doc_path = expected_doc_paths[-1]
    active_doc_name = Path(active_doc_path).name.lower() if active_doc_path else None

    # Aplicar presentación limpia a cada documento
    for i in range(1, app.Documents.Count + 1):
        try:
            doc = app.Documents.Item(i)
            is_target_active = (Path(doc.FullName).name.lower() == active_doc_name)
            apply_model_presentation(doc, is_active=is_target_active)
        except Exception:
            pass

    # Si hay documento activo, forzar su activación explícita
    if active_doc_name and active_doc_name in currently_open_names:
        try:
            target_doc = currently_open_names[active_doc_name]
            target_doc.Activate()
            if target_doc.Windows.Count > 0:
                win = target_doc.Windows.Item(1)
                win.Activate()
                win.WindowState = 2
                try:
                    app.StartCommand(32824)
                except Exception:
                    pass
                win.View.Fit()
        except Exception:
            pass

    # Limpiar comandos o cuadros residuales (volver a comando Selección neutral)
    try:
        app.StartCommand(2)  # seCmdSelect
    except Exception:
        pass

    # Restaurar alertas del sistema
    try:
        app.DisplayAlerts = True
    except Exception:
        pass

    # Traer ventana de Solid Edge al frente
    bring_solidedge_to_foreground(app)

    # Comprobación de estado final por la API
    open_docs_list = []
    for i in range(1, app.Documents.Count + 1):
        try:
            d = app.Documents.Item(i)
            open_docs_list.append({
                "index": i,
                "name": d.Name,
                "full_path": d.FullName
            })
        except Exception:
            pass

    active_doc_name_real = None
    try:
        if app.ActiveDocument:
            active_doc_name_real = app.ActiveDocument.Name
    except Exception:
        pass

    return {
        "success": len(open_docs_list) >= len(expected_doc_paths),
        "open_documents_count": len(open_docs_list),
        "open_documents": open_docs_list,
        "active_document": active_doc_name_real,
        "solidedge_visible": bool(app.Visible)
    }
