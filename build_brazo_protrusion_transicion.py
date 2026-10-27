"""
Constructor de la Pieza de Demostración de las Secciones 7.5 y 17.10 del Prompt Maestro:
Brazo Soporte con Protrusión Cilíndrica Adicional y Transición Parcial Acotada.
Demuestra:
  1. Cuerpo base del brazo (huella extruida 25 mm).
  2. Protrusión cilíndrica adicional (R30 x 45 mm, sobresale 20 mm sobre el brazo).
  3. Agujero pasante coaxial R15 (diam 30 mm) que atraviesa la protrusión y el brazo.
  4. Preservación del saliente limpio.
  5. Transición parcial con chaflán 5x45° acotada estrictamente a la arista de unión del escalón.
  6. Redondeos finales R5.
  7. Verificación completa por auditoría de caras y captura de inspección visual.
"""

import sys
import math
from pathlib import Path
from typing import Dict, Any, List

sys.path.append("C:/Jarvis")
from cad_engine import get_or_start_solidedge, switch_to_ordered_mode, igRight, igSymmetric
from cad_atomic_lib import (
    create_part_doc,
    add_sketch_profile,
    add_line,
    add_arc_by_center,
    close_profile_keypoints,
    add_extruded_cutout,
    create_base_protrusion
)
from surface_cleanliness_auditor import audit_model_surfaces, format_audit_report
from human_designer_engine import HumanDesignerEngine
from final_state_manager import (
    CERRAR_AL_TERMINAR,
    apply_model_presentation,
    bring_solidedge_to_foreground
)


def build_brazo_protrusion_transicion(output_path: Path) -> Dict[str, Any]:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    human = HumanDesignerEngine()
    analysis = human.analyze_part_as_engineer("07_Brazo_Soporte_Protrusion_Transicion", [])

    human.log("Iniciando Solid Edge 2026 en Modo Ordenado...")
    app = get_or_start_solidedge()
    doc = app.Documents.Add("SolidEdge.PartDocument")
    switch_to_ordered_mode(doc)

    ref_planes = doc.RefPlanes
    plane_xy = ref_planes.Item(1)  # Superior
    tree_ops: List[str] = []

    # -------------------------------------------------------------------------
    # PASO 1: CUERPO BASE DEL SALIENTE / BRAZO (Espesor 25 mm)
    # -------------------------------------------------------------------------
    human.log("Paso 1: Extruyo la huella base del brazo (140x60mm con punta redondeada R30) hasta 25mm.")
    ps1 = doc.ProfileSets.Add()
    ps1.Name = "01_Boceto_Huella_Brazo"
    prof1 = ps1.Profiles.Add(plane_xy)
    prof1.Name = "01_Boceto_Huella_Brazo"

    # Rectángulo con punta semicircular R30 en (0, 0.110)
    l1 = add_line(prof1, -0.030, 0.0, 0.030, 0.0)
    l2 = add_line(prof1, 0.030, 0.0, 0.030, 0.110)
    arc_tip = add_arc_by_center(prof1, 0.0, 0.110, 0.030, 0.110, -0.030, 0.110)
    l3 = add_line(prof1, -0.030, 0.110, -0.030, 0.0)
    close_profile_keypoints(prof1, [l1, l2, arc_tip, l3])
    prof1.End(0)
    prof1.Visible = True

    model = doc.Models.AddFiniteExtrudedProtrusion(1, [prof1], igRight, 0.025)
    try:
        model.ExtrudedProtrusions.Item(1).Name = "01_Protrusion_Brazo_Base_25mm"
    except Exception:
        pass
    tree_ops.append("01_Protrusion_Brazo_Base_25mm: Cuerpo base espesor 25mm")

    # -------------------------------------------------------------------------
    # PASO 2: PROTRUSIÓN ADICIONAL CILÍNDRICA (Espesor 45 mm, sobresale 20 mm)
    # -------------------------------------------------------------------------
    human.log("Paso 2: Modelo la protrusión cilíndrica adicional concéntrica R30 con espesor total 45mm.")
    ps2 = doc.ProfileSets.Add()
    ps2.Name = "02_Boceto_Protrusion_Cilindrica"
    prof2 = ps2.Profiles.Add(plane_xy)
    prof2.Name = "02_Boceto_Protrusion_Cilindrica"
    prof2.Circles2d.AddByCenterRadius(0.0, 0.110, 0.030)  # R30
    prof2.End(0)
    prof2.Visible = True

    feat_boss = doc.Models.AddFiniteExtrudedProtrusion(1, [prof2], igRight, 0.045)
    try:
        feat_boss.Name = "02_Protrusion_Cilindro_Jefe_45mm"
    except Exception:
        pass
    tree_ops.append("02_Protrusion_Cilindro_Jefe_45mm: Saliente cilíndrico R30 que sobresale 20mm")

    # -------------------------------------------------------------------------
    # PASO 3: AGUJERO PASANTE COAXIAL R15 (diam 30 mm)
    # -------------------------------------------------------------------------
    human.log("Paso 3: Perforo el agujero pasante R15 coaxial. Atraviesa tanto la protrusión como el brazo base.")
    ps3 = doc.ProfileSets.Add()
    ps3.Name = "03_Boceto_Taladro_Coaxial"
    prof3 = ps3.Profiles.Add(plane_xy)
    prof3.Name = "03_Boceto_Taladro_Coaxial"
    prof3.Circles2d.AddByCenterRadius(0.0, 0.110, 0.015)  # R15
    prof3.End(0)
    prof3.Visible = True

    feat_hole = model.ExtrudedCutouts.AddFinite(prof3, igRight, igSymmetric, 0.100)
    try:
        feat_hole.Name = "03_Corte_Taladro_Coaxial_R15"
    except Exception:
        pass
    tree_ops.append("03_Corte_Taladro_Coaxial_R15: Taladro coaxial pasante R15 (diam 30mm)")

    # -------------------------------------------------------------------------
    # PASO 4 Y 5: TRANSICIÓN PARCIAL (Chaflán 5x45° acotado al escalón de unión)
    # -------------------------------------------------------------------------
    human.log("Paso 4 y 5: Aplico la transición parcial con chaflán 5x45° únicamente en las aristas de unión del escalón.")
    edges = model.Body.Edges(1)
    step_edges = []
    for i in range(1, edges.Count + 1):
        e = edges.Item(i)
        r = e.GetExactRange()
        # Filtrar aristas circulares o rectas situadas en la cota de transición Z = 0.025m
        if r and len(r) == 2:
            p_min, p_max = r[0], r[1]
            if abs(p_min[2] - 0.025) < 0.002 and abs(p_max[2] - 0.025) < 0.002:
                # Comprobar que está en la zona del saliente (Y > 0.05m)
                if p_min[1] > 0.05:
                    step_edges.append(e)

    if step_edges:
        try:
            # Chaflán acotado a las aristas del escalón
            chamf = model.Chamfers.Add(len(step_edges), step_edges, 0.005, 0.005)
            try:
                chamf.Name = "04_Chaflan_Transicion_Parcial_5mm"
            except Exception:
                pass
            tree_ops.append(f"04_Chaflan_Transicion_Parcial_5mm: {len(step_edges)} aristas del escalón biseladas")
            human.log(f"Transición parcial aplicada con éxito en {len(step_edges)} aristas seleccionadas por criterio geométrico.")
        except Exception as e:
            human.log(f"Aviso en chaflán por API: {e}")

    # -------------------------------------------------------------------------
    # PASO 6: REDONDEOS FINALES R5 EN ESQUINAS DE BASE
    # -------------------------------------------------------------------------
    human.log("Paso 6: Aplico redondeos finales R5 en esquinas posteriores de la base.")
    base_corner_edges = []
    for i in range(1, edges.Count + 1):
        e = edges.Item(i)
        r = e.GetExactRange()
        if r and len(r) == 2:
            p_min, p_max = r[0], r[1]
            # Aristas verticales en Y=0
            if abs(p_min[1]) < 0.002 and abs(p_max[1]) < 0.002:
                if abs(p_max[2] - p_min[2]) > 0.020:
                    base_corner_edges.append(e)

    if base_corner_edges:
        try:
            radii = [0.005] * len(base_corner_edges)
            feat_rnd = model.Rounds.Add(len(base_corner_edges), base_corner_edges, radii)
            try:
                feat_rnd.Name = "05_Redondeo_Esquinas_R5"
            except Exception:
                pass
            tree_ops.append(f"05_Redondeo_Esquinas_R5: {len(base_corner_edges)} aristas redondeadas a R5")
        except Exception as e:
            pass

    # -------------------------------------------------------------------------
    # PASO 7: AUDITORÍA DE SUPERFICIES Y ESTADO FINAL
    # -------------------------------------------------------------------------
    human.log("Paso 7: Audito la limpieza de superficies (Parasolid) y genero capturas de las uniones.")
    audit = audit_model_surfaces(doc)
    human.log(f"Auditoría concluida: {audit['total_faces']} caras totales, {audit['counts_by_type'].get('Cilíndrica', 0)} cilíndricas, {audit['faceted_strips_detected']} facetas.")

    doc.SaveAs(str(output_path))
    apply_model_presentation(doc, is_active=True)

    img_path = output_path.with_suffix(".png")
    try:
        doc.Windows.Item(1).View.SaveAsImage(str(img_path), 1920, 1080)
    except Exception:
        pass

    if not CERRAR_AL_TERMINAR:
        bring_solidedge_to_foreground(app)

    return {
        "part_name": "07_Brazo_Soporte_Protrusion_Transicion",
        "file": str(output_path),
        "image": str(img_path),
        "analysis": analysis,
        "tree_operations": tree_ops,
        "audit": audit,
        "human_log": human.log_humano
    }


if __name__ == "__main__":
    out_file = Path("C:/Jarvis/PARCIAL_2_ENTREGA/07_Brazo_Soporte_Protrusion_Transicion.par")
    res = build_brazo_protrusion_transicion(out_file)
    print("\nRESULTADO FINAL DE LA DEMOSTRACIÓN:")
    print("Archivo:", res["file"])
    print("Caras totales:", res["audit"]["total_faces"])
    print("Facetas:", res["audit"]["faceted_strips_detected"])
    print("Estado Limpieza:", "PASS" if res["audit"]["cleanliness_pass"] else "FAIL")
