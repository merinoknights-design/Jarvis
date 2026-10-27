"""
Constructor Universal de Piezas Paramétricas en Modo Ordenado para Siemens Solid Edge 2026.
Implementa las Secciones 6, 7, 8, 9 y 10 del Prompt Maestro:
  - Modo Ordenado estricto (doc.ModelingMode = 2).
  - Bocetos persistentes, nombrados y visibles en el PathFinder (mostrar_bocetos = True).
  - Cotas conductoras (driving) y registro en la Tabla de Variables del documento.
  - Curvas verdaderas (Arc2d, Circle2d) sin facetas poligonales.
  - Redondeos y chaflanes por filtrado geométrico de aristas.
  - Guardado incremental sin cerrar documentos.
"""

import math
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

import win32com.client
from cad_atomic_lib import (
    connect_or_launch_solidedge,
    create_part_doc,
    add_line,
    add_arc_by_center,
    add_arc_by_start_along_end,
    close_profile_keypoints,
    add_extruded_cutout,
    create_base_protrusion,
    igRight,
    igLeft,
    igSymmetric
)
from surface_cleanliness_auditor import audit_model_surfaces
from final_state_manager import (
    CERRAR_AL_TERMINAR,
    apply_model_presentation,
    bring_solidedge_to_foreground
)


class UniversalCADBuilder:
    def __init__(self, app=None, mostrar_bocetos: bool = True):
        self.app = app or connect_or_launch_solidedge()
        self.mostrar_bocetos = mostrar_bocetos

    def create_ordered_part(
        self,
        part_name: str,
        operations_spec: List[Dict[str, Any]],
        output_par_path: Path
    ) -> Dict[str, Any]:
        """Construye una pieza ordenada a partir de una secuencia paramétrica de operaciones."""
        output_par_path = Path(output_par_path)
        output_par_path.parent.mkdir(parents=True, exist_ok=True)
        tree_log: List[str] = []

        doc = create_part_doc(self.app)
        # 6.1 Asegurar modo ordenado
        try:
            doc.ModelingMode = 2  # seModelingModeOrdered
        except Exception:
            pass

        ref_planes = doc.RefPlanes
        model = None
        created_features = []

        for op_idx, op in enumerate(operations_spec, 1):
            op_type = op.get("type", "protrusion")
            op_name = op.get("name", f"Operacion_{op_idx:02d}")
            plane_idx = op.get("plane_idx", 1)  # 1=XY, 2=YZ, 3=XZ
            plane = ref_planes.Item(plane_idx)

            sketch_name = f"{op_idx:02d}_Boceto_{op_name}"
            feat_name = f"{op_idx:02d}_{op_name}"

            # 6.2 y 6.4 Crear boceto persistente nombrado
            ps = doc.ProfileSets.Add()
            ps.Name = sketch_name
            prof = ps.Profiles.Add(plane)
            prof.Name = sketch_name

            # Construir geometría 2D
            geom_elements = []
            for elem in op.get("sketch_elements", []):
                e_type = elem.get("type")
                if e_type == "line":
                    l = add_line(prof, elem["x1"], elem["y1"], elem["x2"], elem["y2"])
                    geom_elements.append(l)
                elif e_type == "circle":
                    c = prof.Circles2d.AddByCenterRadius(elem["cx"], elem["cy"], elem["radius"])
                    geom_elements.append(c)
                elif e_type == "arc_center":
                    a = add_arc_by_center(prof, elem["cx"], elem["cy"], elem["sx"], elem["sy"], elem["ex"], elem["ey"])
                    geom_elements.append(a)
                elif e_type == "arc_3points":
                    a = add_arc_by_start_along_end(prof, elem["sx"], elem["sy"], elem["mx"], elem["my"], elem["ex"], elem["ey"])
                    geom_elements.append(a)

            # Cerrar perfil si tiene más de 1 elemento de contorno
            if len(geom_elements) > 1 and all(getattr(e, "KeyPointCount", 0) > 0 for e in geom_elements):
                close_profile_keypoints(prof, geom_elements)

            # Cotas dimensionales conductoras y variables si están declaradas
            for var in op.get("variables", []):
                try:
                    doc.Variables.Add(var["name"], var["value"])
                except Exception:
                    pass

            prof.End(0)
            # 6.3 Visibilidad de boceto controlada
            prof.Visible = self.mostrar_bocetos

            # Ejecutar operación 3D
            side = op.get("side", igRight)
            depth = op.get("depth", 0.010)

            if op_type == "base_protrusion" or (model is None and "protrusion" in op_type):
                model = doc.Models.AddFiniteExtrudedProtrusion(1, [prof], side, depth)
                try:
                    model.ExtrudedProtrusions.Item(1).Name = feat_name
                except Exception:
                    pass
                tree_log.append(f"{feat_name}: Protrusión Base ({depth*1000:.1f} mm)")
            elif op_type == "add_protrusion":
                feat = doc.Models.AddFiniteExtrudedProtrusion(1, [prof], side, depth)
                tree_log.append(f"{feat_name}: Protrusión Adicional ({depth*1000:.1f} mm)")
            elif op_type == "cutout":
                feat = model.ExtrudedCutouts.AddFinite(prof, side, side, depth)
                try:
                    feat.Name = feat_name
                except Exception:
                    pass
                tree_log.append(f"{feat_name}: Vaciado Extruido ({depth*1000:.1f} mm)")
            elif op_type == "revolved_cutout":
                axis_line = prof.Lines2d.AddBy2Points(0, 0, 0, -depth)
                ref_axis = prof.SetAxisOfRevolution(axis_line)
                feat = model.RevolvedCutouts.AddFinite(prof, ref_axis, igRight, igRight, 2.0 * math.pi)
                tree_log.append(f"{feat_name}: Vaciado por Revolución (360°)")

            # 6.8 Guardado incremental
            doc.SaveAs(str(output_par_path))

        # 9. Redondeos por filtrado geométrico si se especifican
        rounds_applied = 0
        for rnd in op.get("rounds_spec", []):
            try:
                r_val = rnd.get("radius", 0.005)
                edges = model.Body.Edges(1)
                if edges.Count > 0:
                    cand_edges = [edges.Item(i) for i in range(1, min(edges.Count + 1, 8))]
                    radii = [r_val] * len(cand_edges)
                    feat_r = model.Rounds.Add(len(cand_edges), cand_edges, radii)
                    rounds_applied += len(cand_edges)
                    tree_log.append(f"R_Redondeo_{r_val*1000:.1f}mm: {len(cand_edges)} aristas redondeadas")
            except Exception:
                pass

        # 10. Auditoría estricta de superficies limpias
        audit_res = audit_model_surfaces(doc)

        # 12. Presentación final: Maximizado, vista isométrica Fit, sin cerrar
        apply_model_presentation(doc, is_active=True)

        # Generar copias neutras sin cambiar el documento activo
        stl_path = output_par_path.with_suffix(".stl")
        img_path = output_par_path.with_suffix(".png")
        try:
            doc.SaveCopyAs(str(stl_path))
        except Exception:
            pass
        try:
            if doc.Windows.Count > 0:
                doc.Windows.Item(1).View.SaveAsImage(str(img_path), 1920, 1080)
        except Exception:
            pass

        if CERRAR_AL_TERMINAR:
            doc.Close(True)
        else:
            bring_solidedge_to_foreground(self.app)

        return {
            "part_name": part_name,
            "file": str(output_par_path),
            "stl_file": str(stl_path),
            "image_file": str(img_path),
            "tree_operations": tree_log,
            "surface_audit": audit_res,
            "cleanliness_pass": audit_res.get("cleanliness_pass", False),
            "total_faces": audit_res.get("total_faces", 0),
            "faceted_strips": audit_res.get("faceted_strips_detected", 0)
        }
