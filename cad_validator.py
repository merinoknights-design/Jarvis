"""
Módulo de Validación, Verificación Dimensional y Autocorrección para Siemens Solid Edge 2026.
Valida la regeneración del árbol de operaciones (PathFinder), verifica cotas físicas
(volumen, bounding box) contra el plano, exporta capturas de inspección y modelos .par/.step.
"""

import os
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

from cad_atomic_lib import FEATURE_OK, FEATURE_WARNED, bounding_box_mm


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
        "warned_features": [],
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
                # Parche JRV-11 (2026-10-28): antes se aceptaba 1216476311, que es igFeatureFailed, y las
                # operaciones fallidas pasaban por sanas. Sana = igFeatureOK; con aviso = construyó, se informa.
                if is_suppressed or f_status not in (FEATURE_OK, FEATURE_WARNED):
                    health["failed_features"].append(f_name)
                elif f_status == FEATURE_WARNED:
                    health["warned_features"].append(f_name)
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
                health["faces_count"] = body.Faces(1).Count  # Parche JRV-11: Faces exige igQueryAll (1)
                health["edges_count"] = body.Edges(1).Count
            except Exception:
                pass

            # Calcular Bounding Box (Parche JRV-11: Body.Range no existe; antes la caja salía siempre 0)
            try:
                box = bounding_box_mm(body)
                if box:
                    health["bounding_box_mm"] = box
                else:
                    health["errors"].append("No se pudo leer la caja envolvente (GetRange).")
            except Exception as e:
                health["errors"].append(f"Caja envolvente: {e}")

        health["valid"] = len(health["failed_features"]) == 0 and health["features_total"] > 0
    except Exception as e:
        health["errors"].append(f"Excepción al verificar salud del modelo: {e}")

    return health


def verify_dimensions_against_plan(
    measured_box: Dict[str, float],
    plan_dims: Dict[str, Any],
    tolerance_mm: float = 0.5
) -> Tuple[bool, List[str]]:
    """
    Compara las dimensiones físicas reales del Bounding Box de Solid Edge
    con las cotas del plano técnico extraídas por visión.
    Parche JRV-11 (2026-10-28): tolerancia por defecto ±0,5 mm (la general de los planos del curso; antes 5 mm).
    Hasta este parche la caja medida valía 0 y esta comparación se saltaba siempre.
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

    # 4. Exportar .step neutro mediante SaveCopyAs para NO alterar el documento abierto
    step_path = save_base_path.with_suffix(".step")
    try:
        doc.SaveCopyAs(str(step_path))
        if step_path.exists() and step_path.stat().st_size > 100:
            results["step_file"] = str(step_path)
    except Exception:
        pass

    return results
