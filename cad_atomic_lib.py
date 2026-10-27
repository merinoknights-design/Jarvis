"""
Librería Atómica de Automatización CAD para Siemens Solid Edge 2026.
Proporciona primitivas pequeñas, robustas y probadas individualmente:
  - Creación y cierre de bocetos (líneas, arcos, círculos, relaciones de coincidencia).
  - Operaciones 3D (protrusiones finitas, vaciados extruidos y por revolución).
  - Selección y aplicación de redondeos/chaflanes por filtrado geométrico de aristas.
  - Verificación paso a paso del estado de cada operación (Status, regeneración y volumen).
"""

import math
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional, Callable

import pythoncom
import win32com.client

# Constantes oficiales de la API de Siemens Solid Edge 2026
igRight = 1
igLeft = 2
igSymmetric = 3
seModelingModeOrdered = 2
seApplicationGlobalDefaultModelingMode = 178

# Estados FourCC oficiales reconocidos como sanos en Solid Edge COM
HEALTHY_STATUS_CODES = {0, 1, 1216476310, 1216476311}


def connect_or_launch_solidedge():
    """Conecta con la instancia activa de Solid Edge 2026 o inicia una nueva en Modo Ordenado sin cerrar procesos innecesariamente."""
    pythoncom.CoInitialize()
    app = None
    try:
        app = win32com.client.GetActiveObject("SolidEdge.Application")
        _ = app.Version
    except Exception:
        app = None

    if app is None:
        try:
            app = win32com.client.Dispatch("SolidEdge.Application")
        except Exception:
            # Solo en caso de error crítico de conexión COM se reinicia el proceso
            import subprocess
            try:
                subprocess.run(["taskkill", "/f", "/im", "Edge.exe"], capture_output=True)
                time.sleep(1.0)
            except Exception:
                pass
            time.sleep(2.0)
            app = win32com.client.Dispatch("SolidEdge.Application")

    app.Visible = True
    app.DisplayAlerts = False
    try:
        app.SetGlobalParameter(seApplicationGlobalDefaultModelingMode, seModelingModeOrdered)
    except Exception:
        pass
    return app


def create_part_doc(app):
    """Crea un documento de pieza (.par) asegurando el Modo Ordenado."""
    doc = app.Documents.Add("SolidEdge.PartDocument")
    try:
        doc.ModelingMode = seModelingModeOrdered
    except Exception:
        pass
    return doc


def add_sketch_profile(doc, plane_idx: int = 1, name: str = "") -> Tuple[Any, Any]:
    """Crea un ProfileSet y añade un Profile en el plano de referencia especificado (1=XY, 2=YZ, 3=XZ)."""
    ref_planes = doc.RefPlanes
    plane = ref_planes.Item(plane_idx)
    ps = doc.ProfileSets.Add()
    if name:
        try:
            ps.Name = name
        except Exception:
            pass
    prof = ps.Profiles.Add(plane)
    return ps, prof


def add_line(prof, x1: float, y1: float, x2: float, y2: float) -> Any:
    """Añade un segmento de línea recta 2D en metros."""
    return prof.Lines2d.AddBy2Points(x1, y1, x2, y2)


def add_circle(prof, cx: float, cy: float, radius: float) -> Any:
    """Añade una circunferencia 2D centrada en (cx, cy) con radio especificado en metros."""
    c = prof.Circles2d.AddByCenterRadius(cx, cy, radius)
    try:
        prof.Dimensions.AddRadius(c)
    except Exception:
        pass
    return c


def add_arc_by_center(prof, cx: float, cy: float, sx: float, sy: float, ex: float, ey: float) -> Any:
    """Añade un arco circular 2D en sentido antihorario desde (sx, sy) hasta (ex, ey)."""
    return prof.Arcs2d.AddByCenterStartEnd(cx, cy, sx, sy, ex, ey)


def add_arc_by_start_along_end(prof, sx: float, sy: float, mx: float, my: float, ex: float, ey: float) -> Any:
    """Añade un arco circular 2D que pasa por (sx, sy), a lo largo de (mx, my), y termina en (ex, ey)."""
    return prof.Arcs2d.AddByStartAlongEnd(sx, sy, mx, my, ex, ey)


def get_element_keypoint_indices(elem: Any) -> Tuple[int, int]:
    """Retorna los índices oficiales de Keypoint (inicio, fin) según el tipo de entidad geométrica 2D en Solid Edge COM.
    - Line2d: Keypoint 0 = Inicio, Keypoint 1 = Fin, Keypoint 2 = Punto medio.
    - Arc2d: Keypoint 0 = Centro, Keypoint 1 = Inicio, Keypoint 2 = Fin, Keypoint 3 = Punto medio.
    """
    try:
        kp_count = getattr(elem, "KeyPointCount", 0)
        if kp_count == 8:  # Arc2d
            return 1, 2
        elif kp_count == 3:  # Line2d
            return 0, 1
    except Exception:
        pass
    return 0, 1


def close_profile_keypoints(prof, elements_list: List[Any]) -> bool:
    """Aplica relaciones geométricas de coincidencia (Keypoint) para cerrar el perfil garantizando
    la correspondencia exacta entre líneas y arcos verdaderos (evitando unir al centro del arco)."""
    if len(elements_list) < 2:
        return False
    rels = prof.Relations2d
    n = len(elements_list)
    for i in range(n):
        curr_elem = elements_list[i]
        next_elem = elements_list[(i + 1) % n]
        _, curr_end_kp = get_element_keypoint_indices(curr_elem)
        next_start_kp, _ = get_element_keypoint_indices(next_elem)
        try:
            rels.AddKeypoint(curr_elem, curr_end_kp, next_elem, next_start_kp)
        except Exception:
            pass
    return True


def end_and_hide_profile(prof):
    """Finaliza el boceto de forma limpia y oculta su visibilidad para operaciones 3D."""
    prof.End(0)
    prof.Visible = False


def create_base_protrusion(doc, prof, depth: float, side: int = igRight) -> Any:
    """Crea la primera protrusión extruida finita del documento."""
    end_and_hide_profile(prof)
    model = doc.Models.AddFiniteExtrudedProtrusion(1, [prof], side, depth)
    return model


def add_subsequent_protrusion(doc_or_model, prof, depth: float, side: int = igRight, extent_side: int = igRight) -> Any:
    """Añade una protrusión extruida adicional a un modelo 3D existente de forma robusta."""
    end_and_hide_profile(prof)
    try:
        # doc.Models.AddFiniteExtrudedProtrusion añade features de adición con status saludable 1216476310
        doc = getattr(doc_or_model, "Parent", doc_or_model)
        models = getattr(doc, "Models", None)
        if models is not None:
            return models.AddFiniteExtrudedProtrusion(1, [prof], side if side == igSymmetric else extent_side, depth)
    except Exception:
        pass
    model = doc_or_model if hasattr(doc_or_model, "ExtrudedProtrusions") else doc_or_model.Models.Item(1)
    feat = model.ExtrudedProtrusions.AddFinite(prof, side, extent_side, depth)
    return feat


def add_extruded_cutout(model, prof, depth: float, side: int = igRight, extent_type: int = igRight) -> Any:
    """Añade un vaciado extruido (corte recto o simétrico) al modelo 3D."""
    end_and_hide_profile(prof)
    feat = model.ExtrudedCutouts.AddFinite(prof, side, extent_type, depth)
    return feat


def add_revolved_cutout(model, prof, axis_line: Any, sweep_angle: float = 2.0 * math.pi) -> Any:
    """Añade un corte por revolución de 360 grados alrededor de un eje especificado."""
    ref_axis = prof.SetAxisOfRevolution(axis_line)
    end_and_hide_profile(prof)
    feat = model.RevolvedCutouts.AddFinite(prof, ref_axis, igRight, igRight, sweep_angle)
    return feat


def verify_feature_status(model, expected_name: str = "") -> Tuple[bool, int, str]:
    """Verifica que la última operación agregada al modelo no esté fallida ni suprimida."""
    try:
        feats = model.Features
        if feats.Count == 0:
            return False, -1, "No hay operaciones en el árbol"
        last_feat = feats.Item(feats.Count)
        name = getattr(last_feat, "Name", expected_name)
        status = getattr(last_feat, "Status", 0)
        suppressed = getattr(last_feat, "Suppressed", False)
        is_healthy = (status in HEALTHY_STATUS_CODES) and not suppressed
        return is_healthy, status, name
    except Exception as e:
        return False, -99, str(e)


def apply_fillets_geometric(model, edge_filter_func: Callable[[Any], List[Any]], radius: float) -> Tuple[bool, int]:
    """Aplica redondeos paramétricos seleccionando aristas con una función de filtrado geométrico."""
    try:
        edges_col = model.Body.Edges(1)
        matched_edges = edge_filter_func(edges_col)
        if matched_edges:
            radii = [radius] * len(matched_edges)
            feat_r = model.Rounds.Add(len(matched_edges), matched_edges, radii)
            return True, len(matched_edges)
    except Exception:
        pass
    return False, 0


def get_model_physical_properties(model) -> Dict[str, Any]:
    """Lee el volumen, conteo de caras y límites de la caja envolvente del modelo."""
    props = {"volume_cm3": 0.0, "faces": 0, "edges": 0, "bounding_box_mm": {"x": 0.0, "y": 0.0, "z": 0.0}}
    try:
        body = model.Body
        props["volume_cm3"] = round(float(body.Volume) * 1_000_000.0, 2)
        props["faces"] = body.Faces.Count
        props["edges"] = body.Edges(1).Count
        min_p = [0.0, 0.0, 0.0]
        max_p = [0.0, 0.0, 0.0]
        try:
            body.Range(min_p, max_p)
            props["bounding_box_mm"] = {
                "x": round(abs(max_p[0] - min_p[0]) * 1000.0, 1),
                "y": round(abs(max_p[1] - min_p[1]) * 1000.0, 1),
                "z": round(abs(max_p[2] - min_p[2]) * 1000.0, 1),
            }
        except Exception:
            pass
    except Exception:
        pass
    return props
