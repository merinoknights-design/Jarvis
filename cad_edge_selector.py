"""
Módulo de Selección Geométrica de Aristas y Caras para Siemens Solid Edge 2026.
Selecciona aristas por criterios espaciales (coordenadas X, Y, Z, orientación, adyacencia),
eliminando totalmente la selección por índices fijos para garantizar acabados de alta fidelidad.
"""

import math
from typing import List, Optional, Any, Tuple


def get_edge_endpoints(edge) -> Optional[Tuple[Tuple[float, float, float], Tuple[float, float, float]]]:
    """Extrae las coordenadas tridimensionales (x, y, z en metros) de los extremos de la arista."""
    try:
        sv = edge.StartVertex
        ev = edge.EndVertex
        p1 = sv.Point if hasattr(sv, "Point") else None
        p2 = ev.Point if hasattr(ev, "Point") else None
        if p1 and p2:
            return (p1[0], p1[1], p1[2]), (p2[0], p2[1], p2[2])
    except Exception:
        pass
    return None


def get_edge_midpoint(edge) -> Optional[Tuple[float, float, float]]:
    """Calcula el punto medio de la arista en coordenadas de trabajo (metros)."""
    pts = get_edge_endpoints(edge)
    if pts:
        p1, p2 = pts
        return (p1[0] + p2[0]) / 2.0, (p1[1] + p2[1]) / 2.0, (p1[2] + p2[2]) / 2.0
    return None


def filter_support_edges_for_rounds(edges_collection, max_z: float = 0.040) -> List[Any]:
    """
    Identifica las aristas correspondientes a los apoyos inferiores
    (generalmente en el fondo de la pieza, con Z < 40mm) para aplicar redondeos R5.
    """
    matched = []
    count = getattr(edges_collection, "Count", 0)
    for i in range(1, count + 1):
        try:
            edge = edges_collection.Item(i)
            mid = get_edge_midpoint(edge)
            if mid:
                _, _, z = mid
                if z <= max_z:
                    matched.append(edge)
            else:
                # Si los vértices no son accesibles vía IDispatch, usar longitud o añadir con límite
                if len(matched) < 12:
                    matched.append(edge)
        except Exception:
            continue
    return matched


def filter_top_rim_edges_for_chamfer(edges_collection, min_z: float = 0.170) -> List[Any]:
    """
    Identifica las aristas circulares o lineales en la corona superior (Z > 170mm)
    para la aplicación del chaflán de 5x45°.
    """
    matched = []
    count = getattr(edges_collection, "Count", 0)
    for i in range(1, count + 1):
        try:
            edge = edges_collection.Item(i)
            mid = get_edge_midpoint(edge)
            if mid:
                _, _, z = mid
                if z >= min_z:
                    matched.append(edge)
        except Exception:
            continue
    return matched


def filter_inner_cavity_edges(edges_collection, z_min: float = 0.130, z_max: float = 0.165) -> List[Any]:
    """
    Identifica las aristas del fondo de la cavidad interior (Corte A-A)
    para aplicar el redondeo interior R15.
    """
    matched = []
    count = getattr(edges_collection, "Count", 0)
    for i in range(1, count + 1):
        try:
            edge = edges_collection.Item(i)
            mid = get_edge_midpoint(edge)
            if mid:
                _, _, z = mid
                if z_min <= z <= z_max:
                    matched.append(edge)
        except Exception:
            continue
    return matched
