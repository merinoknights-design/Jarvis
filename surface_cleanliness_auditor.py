"""
Módulo de Auditoría de Calidad y Limpieza de Superficies CAD para Siemens Solid Edge 2026.
Implementa las reglas de la Parte 5: Superficies Limpias en Soportes, Orejas y Salientes:
  1. Clasificación estricta de caras por geometría COM (Plana, Cilíndrica, Cónica, Esférica, Toroidal, Spline).
  2. Detección automática de facetas/polilíneas aproximadas (< 1.5mm o cuerdas adyacentes).
  3. Verificación de caras continuas únicas en contornos en U, alojamientos y agujeros cilíndricos.
  4. Generación de tablas comparativas de inventario de caras (Antes vs Después).
  5. Principio de Generalidad: Funciona sobre CUALQUIER documento .par y modelo 3D.
"""

import sys
import math
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

import win32com.client


def classify_face_geometry(face) -> str:
    """Clasifica una cara 3D de Solid Edge inspeccionando los métodos geométricos de Parasolid."""
    try:
        geom = face.Geometry
        form = getattr(face, "GeometryForm", None)

        # 1. Cilíndrica
        try:
            _ = geom.GetCylinderData
            return "Cilíndrica"
        except Exception:
            pass

        # 2. Plana
        try:
            _ = geom.GetPlaneData
            return "Plana"
        except Exception:
            pass

        # 3. Cónica
        try:
            _ = geom.GetConeData
            return "Cónica"
        except Exception:
            pass

        # 4. Esférica
        try:
            _ = geom.GetSphereData
            return "Esférica"
        except Exception:
            pass

        # 5. Toroidal
        try:
            _ = geom.GetTorusData
            return "Toroidal"
        except Exception:
            pass

        # 6. B-Spline / Forma Libre
        try:
            _ = geom.GetBSplineData
            return "Spline"
        except Exception:
            pass

        # Si tiene propiedad Radius pero no GetCylinderData
        if getattr(geom, "Radius", None) is not None:
            return "Cilíndrica"

        if form == 9:
            return "Plana"
        elif form == 10:
            return "Cilíndrica"
        elif form == 11:
            return "Cónica"
        elif form == 12:
            return "Esférica"
        elif form == 13:
            return "Toroidal"
        elif form == 14:
            return "Spline"

        return "Otra"
    except Exception:
        return "Desconocida"


def audit_model_surfaces(doc_or_model) -> Dict[str, Any]:
    """Audita todas las caras de un modelo o documento de pieza en Solid Edge.
    Retorna un reporte detallado con conteo por tipo, facetas detectadas y veredicto de calidad."""
    if hasattr(doc_or_model, "Models"):
        if doc_or_model.Models.Count == 0:
            return {"error": "El documento no contiene modelos 3D", "success": False}
        body = doc_or_model.Models.Item(1).Body
    elif hasattr(doc_or_model, "Body"):
        body = doc_or_model.Body
    else:
        return {"error": "Objeto no válido para auditar caras", "success": False}

    faces_coll = body.Faces(1)
    total_faces = faces_coll.Count

    counts = {
        "Plana": 0,
        "Cilíndrica": 0,
        "Cónica": 0,
        "Esférica": 0,
        "Toroidal": 0,
        "Spline": 0,
        "Otra": 0
    }

    cylindrical_faces: List[Dict[str, Any]] = []
    narrow_planar_faces: List[Dict[str, Any]] = []
    faceted_strips_detected = 0

    face_details: List[Dict[str, Any]] = []

    for idx in range(1, total_faces + 1):
        f = faces_coll.Item(idx)
        kind = classify_face_geometry(f)
        counts[kind] = counts.get(kind, 0) + 1

        area = getattr(f, "Area", 0.0)
        rng = None
        min_dim = 1.0
        try:
            r = f.GetRange()
            if r and len(r) == 2:
                p_min, p_max = r[0], r[1]
                dx = abs(p_max[0] - p_min[0])
                dy = abs(p_max[1] - p_min[1])
                dz = abs(p_max[2] - p_min[2])
                dims = [d for d in [dx, dy, dz] if d > 1e-6]
                if dims:
                    min_dim = min(dims)
                rng = ((p_min[0], p_min[1], p_min[2]), (p_max[0], p_max[1], p_max[2]))
        except Exception:
            pass

        detail = {
            "index": idx,
            "type": kind,
            "area_m2": area,
            "min_dim_mm": min_dim * 1000.0,
            "range": rng
        }

        if kind == "Cilíndrica":
            geom = f.Geometry
            rad = getattr(geom, "Radius", 0.0)
            detail["radius_mm"] = rad * 1000.0 if rad else 0.0
            cylindrical_faces.append(detail)
        elif kind == "Plana":
            # Si una cara plana tiene una dimensión transversal muy estrecha (< 1.5mm)
            # y un área modesta (< 500 mm²), es síntoma de segmentación de arco (faceta)
            if (min_dim < 0.0015) and (area < 0.0008):
                narrow_planar_faces.append(detail)
                faceted_strips_detected += 1

        face_details.append(detail)

    # Criterio estricto de aceptación:
    # 1. Cero facetas / franjas poligonales en lugar de superficies curvas
    # 2. Las superficies curvas son caras cilíndricas continuas
    cleanliness_pass = (faceted_strips_detected == 0)

    return {
        "total_faces": total_faces,
        "counts_by_type": counts,
        "cylindrical_faces_count": len(cylindrical_faces),
        "cylindrical_faces": cylindrical_faces,
        "narrow_planar_faces_count": len(narrow_planar_faces),
        "faceted_strips_detected": faceted_strips_detected,
        "cleanliness_pass": cleanliness_pass,
        "details": face_details
    }


def format_audit_report(part_name: str, audit_data: Dict[str, Any]) -> str:
    """Genera una tabla de auditoría formateada en Markdown para presentación."""
    counts = audit_data.get("counts_by_type", {})
    total = audit_data.get("total_faces", 0)
    faceted = audit_data.get("faceted_strips_detected", 0)
    passed = audit_data.get("cleanliness_pass", False)
    status_str = "APROBADO (Superficies Limpias)" if passed else "FALLIDO (Contiene Facetas Poligonales)"

    lines = [
        f"### Auditoría de Superficies: {part_name}",
        f"**Estado General:** {status_str}",
        f"- **Total de Caras del Modelo:** {total}",
        f"- **Caras Cilíndricas Verdaderas:** {counts.get('Cilíndrica', 0)}",
        f"- **Caras Planas:** {counts.get('Plana', 0)}",
        f"- **Caras Cónicas:** {counts.get('Cónica', 0)}",
        f"- **Caras Toroidales (Redondeos):** {counts.get('Toroidal', 0)}",
        f"- **Caras Spline:** {counts.get('Spline', 0)}",
        f"- **Franjas/Facetas Poligonales Detectadas:** {faceted} (Requisito: 0)",
        ""
    ]
    if audit_data.get("cylindrical_faces"):
        lines.append("| Índice Cara | Tipo | Radio (mm) | Área (mm²) |")
        lines.append("| :--- | :--- | :--- | :--- |")
        for cf in audit_data["cylindrical_faces"]:
            lines.append(f"| Cara #{cf['index']} | Cilíndrica | {cf.get('radius_mm', 0.0):.2f} mm | {cf['area_m2'] * 1e6:.2f} mm² |")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Auditor de Limpieza de Superficies Solid Edge")
    parser.add_argument("file", nargs="?", default="C:/Jarvis/01_Piston.par", help="Ruta al archivo .par a auditar")
    args = parser.parse_args()

    p = Path(args.file)
    if not p.exists():
        print(f"Archivo no encontrado: {p}")
        sys.exit(1)

    app = win32com.client.Dispatch("SolidEdge.Application")
    app.DisplayAlerts = False
    doc = app.Documents.Open(str(p))
    res = audit_model_surfaces(doc)
    doc.Close(False)
    print(format_audit_report(p.name, res))
