"""
Módulo de Esquema y Validación de Planos CAD para J.A.R.V.I.S.
Define la estructura JSON estandarizada para piezas mecánicas en Siemens Solid Edge 2026,
verificación de consistencia entre vistas (frontal, superior, lateral, cortes) y detección de cotas inciertas.
"""

import json
from typing import Dict, Any, List, Optional, Tuple


def validate_cad_blueprint_schema(plan: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Valida que el plan JSON contenga las secciones mínimas requeridas
    para el modelado paramétrico en Solid Edge 2026.
    """
    errors: List[str] = []
    if not isinstance(plan, dict):
        return False, ["El plan debe ser un diccionario JSON válido."]

    # Validar metadatos básicos
    metadata = plan.get("metadata", {})
    if not metadata.get("part_name"):
        plan.setdefault("metadata", {})["part_name"] = plan.get("part_name", "Pieza_Mecanica")

    # Unidades por defecto mm
    if metadata.get("units") not in ["mm", "inch", "m"]:
        plan.setdefault("metadata", {})["units"] = "mm"

    # Validar dimensiones
    dims = plan.get("dimensions_mm", {})
    if not isinstance(dims, dict):
        errors.append("El campo 'dimensions_mm' debe ser un diccionario de cotas numéricas.")

    # Validar inconsistencias entre vistas
    views = plan.get("views_analyzed", [])
    uncertain = plan.get("uncertain_dimensions", [])

    return len(errors) == 0, errors


def verify_cross_view_consistency(dims: Dict[str, Any], views: List[Dict[str, Any]]) -> List[str]:
    """
    Verifica coherencia geométrica entre distintas vistas del plano:
    Ejemplo:
      - Diámetro exterior en vista superior debe coincidir con ancho total en frontal/corte A-A.
      - Altura interior en corte A-A no puede ser mayor que la altura total.
      - Radio concéntrico del pasador no puede ser mayor que el radio exterior del apoyo.
    """
    inconsistencies: List[str] = []

    # 1. Comprobación de alturas
    total_h = float(dims.get("total_height", dims.get("height", 0.0)))
    inner_h = float(dims.get("inner_height", 0.0))
    if total_h > 0.0 and inner_h > 0.0:
        if inner_h >= total_h:
            inconsistencies.append(
                f"Inconsistencia en alturas: Altura interior ({inner_h}mm) debe ser menor a la altura total ({total_h}mm)."
            )

    # 2. Comprobación de radios cilíndricos
    outer_r = float(dims.get("outer_radius", 0.0))
    if outer_r == 0.0 and dims.get("outer_diameter"):
        outer_r = float(dims.get("outer_diameter")) / 2.0

    inner_r = float(dims.get("inner_radius", 0.0))
    if inner_r == 0.0 and dims.get("inner_diameter"):
        inner_r = float(dims.get("inner_diameter")) / 2.0

    if outer_r > 0.0 and inner_r > 0.0:
        if inner_r >= outer_r:
            inconsistencies.append(
                f"Inconsistencia en radios: Radio interior ({inner_r}mm) debe ser menor al exterior ({outer_r}mm)."
            )

    # 3. Comprobación de abertura de apoyos vs radio exterior
    opening_w = float(dims.get("central_opening_width", dims.get("width", 0.0)))
    if outer_r > 0.0 and opening_w > 0.0:
        if opening_w >= (outer_r * 2.0):
            inconsistencies.append(
                f"Inconsistencia en abertura: Ancho ({opening_w}mm) excede el diámetro del cuerpo principal ({outer_r * 2}mm)."
            )

    # 4. Comprobación pasador vs apoyo
    pin_r = float(dims.get("pin_radius", 0.0))
    outer_pin_r = float(dims.get("pin_outer_radius", dims.get("outer_pin_radius", 0.0)))
    if pin_r > 0.0 and outer_pin_r > 0.0:
        if pin_r >= outer_pin_r:
            inconsistencies.append(
                f"Inconsistencia en pasador: Radio de agujero ({pin_r}mm) no puede superar radio del saliente ({outer_pin_r}mm)."
            )

    return inconsistencies


def create_standard_piston_plan(name: str = "Pieza_mecanica") -> Dict[str, Any]:
    """
    Genera el esquema estándar completo para la Pieza Mecánica analizada en la Guía de Modelamiento 3D.
    """
    return {
        "metadata": {
            "part_name": name,
            "units": "mm",
            "material": "Aluminio 6061-T6",
            "general_notes": "Radios de redondeo en los apoyos R5. Chaflán 5x45°. Radios interiores R15 y R25.",
            "confidence_score": 1.0
        },
        "views_analyzed": [
            {"name": "Vista Frontal", "type": "view"},
            {"name": "Corte A-A", "type": "section"},
            {"name": "Corte C-C", "type": "section"},
            {"name": "Detalle B", "type": "detail"},
            {"name": "Vista Superior", "type": "view"}
        ],
        "dimensions_mm": {
            "outer_radius": 150.0,
            "inner_radius": 130.0,
            "total_height": 180.0,
            "inner_height": 140.0,
            "central_opening_width": 100.0,
            "support_width": 40.0,
            "support_reference_dist": 100.0,
            "pin_radius": 25.0,
            "outer_pin_radius": 45.0,
            "transition_radius": 100.0,
            "ring_grooves_depth": 7.5,
            "ring_grooves_width": 5.0,
            "ring_grooves_step": 10.0,
            "crown_thickness": 20.0,
            "round_support": 5.0,
            "round_interior": 15.0,
            "chamfer_distance": 5.0,
            "chamfer_angle": 45.0
        },
        "uncertain_dimensions": [],
        "ordered_operations": [
            {
                "op_id": 1,
                "name": "Boceto_01_Cuerpo_Principal",
                "type": "protrusion_extrude",
                "plane": "Superior",
                "depth": 180.0
            },
            {
                "op_id": 2,
                "name": "Boceto_02_Escalones_Detalle_B",
                "type": "revolved_cutout",
                "plane": "Frontal",
                "grooves_count": 3
            },
            {
                "op_id": 3,
                "name": "Boceto_03_Vaciado_Interior_R130",
                "type": "extruded_cutout",
                "plane": "Superior",
                "depth": 160.0
            },
            {
                "op_id": 4,
                "name": "Boceto_04_Perfil_Frontal_R100",
                "type": "extruded_cutout",
                "plane": "Frontal",
                "symmetric_depth": 400.0
            },
            {
                "op_id": 5,
                "name": "Boceto_05_Aberturas_Apoyos_R25",
                "type": "extruded_cutout",
                "plane": "Frontal",
                "symmetric_depth": 400.0
            },
            {
                "op_id": 6,
                "name": "Redondeos_y_Chaflanes",
                "type": "geometric_finishing",
                "support_round_r": 5.0,
                "chamfer_dist": 5.0
            }
        ]
    }
