"""
Módulo de Validación, Verificación Dimensional y Autocorrección para Siemens Solid Edge 2026.
Valida la regeneración del árbol de operaciones (PathFinder), verifica cotas físicas
(volumen, bounding box) contra el plano, exporta capturas de inspección y modelos .par/.step.
"""

import os
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional


def validate_part_model_health(doc) -> Dict[str, Any]:
    """
    Inspecciona la integridad del modelo 3D en Solid Edge:
      - Estado de cada operación (Feature Status) para alertar sobre bocetos rotos o fallos.
      - Volumen del cuerpo (Body.Volume).
      - Rango tridimensional y Bounding Box aproximado.
      - Conteo de caras y aristas regeneradas.
    """
    health = {
        "valid": False,
        "features_total": 0,
        "failed_features": [],
        "features_list": [],
        "volume_cm3": 0.0,
        "faces_count": 0,
        "edges_count": 0,
        "bounding_box_mm": {"x": 0.0, "y": 0.0, "z": 0.0},
        "errors": []
    }

    try:
        models = doc.Models
        if models.Count == 0:
            health["errors"].append("El documento no contiene ningún modelo 3D extruido.")
            return health

        model = models.Item(1)
        features = model.Features
        health["features_total"] = features.Count

        for i in range(1, features.Count + 1):
            try:
                feat = features.Item(i)
                f_name = getattr(feat, "Name", f"Feature_{i}")
                f_status = getattr(feat, "Status", 0)
                is_suppressed = getattr(feat, "Suppressed", False)
                health["features_list"].append({"name": f_name, "status": f_status, "suppressed": is_suppressed})
                # En Solid Edge COM, status 0 o FourCC 1216476310/1216476311 corresponden a operaciones sanas
                healthy_statuses = [0, 1, 1216476310, 1216476311]
                if f_status not in healthy_statuses or is_suppressed:
                    health["failed_features"].append(f_name)
            except Exception:
                continue

        body = getattr(model, "Body", None)
        if body:
            try:
                vol_m3 = float(body.Volume)
                health["volume_cm3"] = round(vol_m3 * 1_000_000.0, 2)
            except Exception:
                pass

            try:
                health["faces_count"] = body.Faces.Count
                health["edges_count"] = body.Edges(1).Count
            except Exception:
                pass

            # Calcular Bounding Box
            try:
                min_arr = [0.0, 0.0, 0.0]
                max_arr = [0.0, 0.0, 0.0]
                # Range(min, max) en Solid Edge COM
                body.Range(min_arr, max_arr)
                dx = abs(max_arr[0] - min_arr[0]) * 1000.0
                dy = abs(max_arr[1] - min_arr[1]) * 1000.0
                dz = abs(max_arr[2] - min_arr[2]) * 1000.0
                health["bounding_box_mm"] = {
                    "x": round(dx, 2),
                    "y": round(dy, 2),
                    "z": round(dz, 2)
                }
            except Exception:
                pass

        health["valid"] = len(health["failed_features"]) == 0 and health["features_total"] > 0
    except Exception as e:
        health["errors"].append(f"Excepción al verificar salud del modelo: {e}")

    return health


def verify_dimensions_against_plan(
    measured_box: Dict[str, float],
    plan_dims: Dict[str, Any],
    tolerance_mm: float = 5.0
) -> Tuple[bool, List[str]]:
    """
    Compara las dimensiones físicas reales del Bounding Box de Solid Edge
    con las cotas del plano técnico extraídas por visión.
    """
    discrepancies: List[str] = []

    expected_height = float(plan_dims.get("total_height", plan_dims.get("height", 0.0)))
    if expected_height > 0.0 and measured_box.get("z", 0.0) > 0.0:
        diff_z = abs(measured_box["z"] - expected_height)
        if diff_z > tolerance_mm:
            discrepancies.append(
                f"Altura física ({measured_box['z']}mm) difiere de la esperada ({expected_height}mm) por {round(diff_z, 1)}mm."
            )

    expected_diam = float(plan_dims.get("outer_radius", 0.0)) * 2.0
    if expected_diam == 0.0 and plan_dims.get("outer_diameter"):
        expected_diam = float(plan_dims.get("outer_diameter"))

    if expected_diam > 0.0:
        max_planar = max(measured_box.get("x", 0.0), measured_box.get("y", 0.0))
        if max_planar > 0.0:
            diff_d = abs(max_planar - expected_diam)
            if diff_d > tolerance_mm:
                discrepancies.append(
                    f"Diámetro/Ancho plano ({max_planar}mm) difiere del esperado ({expected_diam}mm) por {round(diff_d, 1)}mm."
                )

    is_ok = len(discrepancies) == 0
    return is_ok, discrepancies


def capture_and_export_solid_edge_model(doc, save_base_path: Path) -> Dict[str, str]:
    """
    Exporta el documento nativo (.par), el formato estándar neutro (.step)
    y captura una imagen de inspección isométrica de alta resolución.
    """
    results = {}
    save_base_path = Path(save_base_path)
    save_base_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Guardar documento nativo .par
    par_path = save_base_path.with_suffix(".par")
    try:
        if par_path.exists():
            try:
                par_path.unlink()
            except Exception:
                par_path = save_base_path.parent / f"{save_base_path.stem}_{int(time.time())}.par"
        doc.SaveAs(str(par_path))
        results["par_file"] = str(par_path)
    except Exception as e:
        results["par_error"] = str(e)

    # 2. Ajustar vista isométrica y encuadre
    app = doc.Application
    try:
        app.StartCommand(32824)  # ISO View
    except Exception:
        pass

    try:
        if doc.Windows.Count > 0:
            win = doc.Windows.Item(1)
            if hasattr(win, "View") and hasattr(win.View, "Fit"):
                win.View.Fit()
    except Exception:
        pass

    # 3. Exportar captura de imagen para verificación visual
    img_path = save_base_path.with_suffix(".png")
    try:
        if doc.Windows.Count > 0:
            win = doc.Windows.Item(1)
            if hasattr(win, "View") and hasattr(win.View, "SaveAsImage"):
                win.View.SaveAsImage(str(img_path), 1920, 1080)
                if img_path.exists() and img_path.stat().st_size > 100:
                    results["inspection_image"] = str(img_path)
    except Exception:
        pass

    # 4. Exportar .step neutro
    step_path = save_base_path.with_suffix(".step")
    try:
        doc.SaveAs(str(step_path))
        if step_path.exists() and step_path.stat().st_size > 100:
            results["step_file"] = str(step_path)
    except Exception:
        pass

    return results
