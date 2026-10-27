"""
Suite de Verificación y Auditoría de Limpieza de Superficies (PARTE 5 DE LA ADENDA).
Verifica la eliminación total de aproximaciones poligonales (facetas) y la existencia
de caras cilíndricas continuas y limpias en:
  - Pieza 1: Pistón de Motor (01_Piston.par)
  - Pieza 2: Biela Parte Superior (02_Biela_Parte_Superior.par)
  - Pieza 3: Biela Parte Inferior / Sombrerete (03_Biela_Parte_Inferior.par)
  - Pieza 4: Soporte Horquilla en U (05_Soporte_Horquilla_U.par) - Pieza de Generalidad A
  - Pieza 5: Palanca Balancín Doble Ojo (06_Palanca_Balancin_Doble_Ojo.par) - Pieza de Generalidad B
"""

import sys
import math
import time
from pathlib import Path
from typing import Dict, Any, List

import win32com.client

sys.path.append("C:/Jarvis")
from cad_engine import (
    get_or_start_solidedge,
    switch_to_ordered_mode,
    igRight,
    igLeft,
    igSymmetric
)
from cad_atomic_lib import (
    create_part_doc,
    add_sketch_profile,
    add_line,
    add_arc_by_center,
    add_arc_by_start_along_end,
    close_profile_keypoints,
    add_extruded_cutout,
    create_base_protrusion
)
from surface_cleanliness_auditor import audit_model_surfaces, format_audit_report
from final_state_manager import (
    CERRAR_AL_TERMINAR,
    apply_model_presentation,
    bring_solidedge_to_foreground
)


def build_generic_u_bracket(app, output_path: Path) -> Dict[str, Any]:
    """Pieza de Prueba de Generalidad 1: Soporte Horquilla en U.
    Demuestra que el sistema Jarvis modela cualquier oreja/soporte en U sin facetas."""
    doc = app.Documents.Add("SolidEdge.PartDocument")
    switch_to_ordered_mode(doc)
    ref_planes = doc.RefPlanes
    plane_xy = ref_planes.Item(1)
    plane_xz = ref_planes.Item(3)

    # 1. Base plana 120 x 80 x 15 mm
    ps1 = doc.ProfileSets.Add()
    prof1 = ps1.Profiles.Add(plane_xy)
    b1 = add_line(prof1, -0.060, -0.040, 0.060, -0.040)
    b2 = add_line(prof1, 0.060, -0.040, 0.060, 0.040)
    b3 = add_line(prof1, 0.060, 0.040, -0.060, 0.040)
    b4 = add_line(prof1, -0.060, 0.040, -0.060, -0.040)
    close_profile_keypoints(prof1, [b1, b2, b3, b4])
    prof1.End(0)
    prof1.Visible = False
    model = doc.Models.AddFiniteExtrudedProtrusion(1, [prof1], igRight, 0.015)

    # 2. Oreja vertical en U (altura 80mm, ancho 60mm, espesor 20mm, punta en U con semicírculo R30)
    ps2 = doc.ProfileSets.Add()
    prof2 = ps2.Profiles.Add(plane_xz)
    # Contorno continuo en U
    u_base = add_line(prof2, -0.030, 0.015, 0.030, 0.015)
    u_right = add_line(prof2, 0.030, 0.015, 0.030, 0.065)
    u_arc = add_arc_by_center(prof2, 0.0, 0.065, 0.030, 0.065, -0.030, 0.065)  # R30 semicírculo
    u_left = add_line(prof2, -0.030, 0.065, -0.030, 0.015)
    close_profile_keypoints(prof2, [u_base, u_right, u_arc, u_left])
    prof2.End(0)
    prof2.Visible = False
    doc.Models.AddFiniteExtrudedProtrusion(1, [prof2], igSymmetric, 0.040)

    # 3. Taladro pasante coaxial en la oreja en U (R15 / diam 30mm en centro (0, 0.065))
    ps3 = doc.ProfileSets.Add()
    prof3 = ps3.Profiles.Add(plane_xz)
    prof3.Circles2d.AddByCenterRadius(0.0, 0.065, 0.015)
    prof3.End(0)
    prof3.Visible = False
    model.ExtrudedCutouts.AddFinite(prof3, igRight, igSymmetric, 0.080)

    # 4. Cuatro taladros de montaje en la base (R4 en esquinas)
    ps4 = doc.ProfileSets.Add()
    prof4 = ps4.Profiles.Add(plane_xy)
    prof4.Circles2d.AddByCenterRadius(-0.045, -0.025, 0.005)
    prof4.Circles2d.AddByCenterRadius(0.045, -0.025, 0.005)
    prof4.Circles2d.AddByCenterRadius(0.045, 0.025, 0.005)
    prof4.Circles2d.AddByCenterRadius(-0.045, 0.025, 0.005)
    prof4.End(0)
    prof4.Visible = False
    model.ExtrudedCutouts.AddFinite(prof4, igRight, igRight, 0.020)

    apply_model_presentation(doc, is_active=False)
    doc.SaveAs(str(output_path))
    audit = audit_model_surfaces(doc)
    img_path = output_path.with_suffix(".png")
    try:
        doc.Windows.Item(1).View.SaveAsImage(str(img_path), 1920, 1080)
    except Exception:
        pass

    return {
        "part_name": "05_Soporte_Horquilla_U",
        "file": str(output_path),
        "image": str(img_path),
        "audit": audit
    }


def build_generic_dual_eye_lever(app, output_path: Path) -> Dict[str, Any]:
    """Pieza de Prueba de Generalidad 2: Balancín / Palanca Doble Ojo.
    Demuestra la tangencia continua entre dos arcos de diferente radio unidos por flancos rectos."""
    doc = app.Documents.Add("SolidEdge.PartDocument")
    switch_to_ordered_mode(doc)
    ref_planes = doc.RefPlanes
    plane_xy = ref_planes.Item(1)

    # Ojo mayor R35 en (0, 0), ojo menor R20 en (0.150, 0)
    # Tangentes exteriores entre ambos círculos
    ps1 = doc.ProfileSets.Add()
    prof1 = ps1.Profiles.Add(plane_xy)

    r1, r2, dist = 0.035, 0.020, 0.150
    # Ángulo de tangencia exterior
    alpha = math.asin((r1 - r2) / dist)
    # Puntos de tangencia superior
    x1_top = -r1 * math.sin(alpha)
    y1_top = r1 * math.cos(alpha)
    x2_top = dist - r2 * math.sin(alpha)
    y2_top = r2 * math.cos(alpha)

    # Puntos de tangencia inferior
    x1_bot = -r1 * math.sin(alpha)
    y1_bot = -r1 * math.cos(alpha)
    x2_bot = dist - r2 * math.sin(alpha)
    y2_bot = -r2 * math.cos(alpha)

    # Arco ojo mayor: desde (x1_bot, y1_bot) alrededor del lado izquierdo hasta (x1_top, y1_top)
    arc_major = add_arc_by_start_along_end(prof1, x1_bot, y1_bot, -r1, 0.0, x1_top, y1_top)
    # Línea superior tangente
    l_top = add_line(prof1, x1_top, y1_top, x2_top, y2_top)
    # Arco ojo menor: desde (x2_top, y2_top) alrededor del lado derecho hasta (x2_bot, y2_bot)
    arc_minor = add_arc_by_start_along_end(prof1, x2_top, y2_top, dist + r2, 0.0, x2_bot, y2_bot)
    # Línea inferior tangente
    l_bot = add_line(prof1, x2_bot, y2_bot, x1_bot, y1_bot)

    close_profile_keypoints(prof1, [arc_major, l_top, arc_minor, l_bot])
    prof1.End(0)
    prof1.Visible = False
    model = doc.Models.AddFiniteExtrudedProtrusion(1, [prof1], igRight, 0.025)

    # Taladro ojo mayor R18
    ps2 = doc.ProfileSets.Add()
    prof2 = ps2.Profiles.Add(plane_xy)
    prof2.Circles2d.AddByCenterRadius(0.0, 0.0, 0.018)
    prof2.End(0)
    prof2.Visible = False
    model.ExtrudedCutouts.AddFinite(prof2, igRight, igSymmetric, 0.050)

    # Taladro ojo menor R10
    ps3 = doc.ProfileSets.Add()
    prof3 = ps3.Profiles.Add(plane_xy)
    prof3.Circles2d.AddByCenterRadius(dist, 0.0, 0.010)
    prof3.End(0)
    prof3.Visible = False
    model.ExtrudedCutouts.AddFinite(prof3, igRight, igSymmetric, 0.050)

    apply_model_presentation(doc, is_active=False)
    doc.SaveAs(str(output_path))
    audit = audit_model_surfaces(doc)
    img_path = output_path.with_suffix(".png")
    try:
        doc.Windows.Item(1).View.SaveAsImage(str(img_path), 1920, 1080)
    except Exception:
        pass

    return {
        "part_name": "06_Palanca_Balancin_Doble_Ojo",
        "file": str(output_path),
        "image": str(img_path),
        "audit": audit
    }


def main():
    print("=== SUITE DE AUDITORÍA DE SUPERFICIES LIMPIAS ===")
    app = get_or_start_solidedge()
    app.DisplayAlerts = False
    output_dir = Path("C:/Jarvis/PARCIAL_2_ENTREGA")
    output_dir.mkdir(parents=True, exist_ok=True)

    results = []

    # 1. Auditoría Pieza 1: Pistón
    piston_path = output_dir / "01_Piston.par"
    doc_piston = app.Documents.Open(str(piston_path))
    audit_piston = audit_model_surfaces(doc_piston)
    apply_model_presentation(doc_piston, is_active=False)
    try:
        doc_piston.Windows.Item(1).View.SaveAsImage(str(output_dir / "01_Piston_Superficies_Limpias.png"), 1920, 1080)
    except Exception:
        pass
    results.append({
        "part_name": "01_Piston (Pistón Motor)",
        "file": str(piston_path),
        "audit": audit_piston
    })

    # 2. Auditoría Pieza 2: Biela Superior
    biela_sup_path = output_dir / "02_Biela_Parte_Superior.par"
    doc_biela_sup = app.Documents.Open(str(biela_sup_path))
    audit_biela_sup = audit_model_surfaces(doc_biela_sup)
    apply_model_presentation(doc_biela_sup, is_active=False)
    try:
        doc_biela_sup.Windows.Item(1).View.SaveAsImage(str(output_dir / "02_Biela_Superior_Superficies_Limpias.png"), 1920, 1080)
    except Exception:
        pass
    results.append({
        "part_name": "02_Biela_Parte_Superior",
        "file": str(biela_sup_path),
        "audit": audit_biela_sup
    })

    # 3. Auditoría Pieza 3: Sombrerete Biela Inferior
    biela_inf_path = output_dir / "03_Biela_Parte_Inferior.par"
    doc_biela_inf = app.Documents.Open(str(biela_inf_path))
    audit_biela_inf = audit_model_surfaces(doc_biela_inf)
    apply_model_presentation(doc_biela_inf, is_active=False)
    try:
        doc_biela_inf.Windows.Item(1).View.SaveAsImage(str(output_dir / "03_Biela_Inferior_Superficies_Limpias.png"), 1920, 1080)
    except Exception:
        pass
    results.append({
        "part_name": "03_Biela_Parte_Inferior",
        "file": str(biela_inf_path),
        "audit": audit_biela_inf
    })

    # 4. Pieza de Generalidad A: Soporte Horquilla U
    p4_path = output_dir / "05_Soporte_Horquilla_U.par"
    p4_res = build_generic_u_bracket(app, p4_path)
    results.append({
        "part_name": "05_Soporte_Horquilla_U (Generalidad A)",
        "file": str(p4_path),
        "audit": p4_res["audit"]
    })

    # 5. Pieza de Generalidad B: Balancín Doble Ojo
    p5_path = output_dir / "06_Palanca_Balancin_Doble_Ojo.par"
    p5_res = build_generic_dual_eye_lever(app, p5_path)
    results.append({
        "part_name": "06_Palanca_Balancin_Doble_Ojo (Generalidad B)",
        "file": str(p5_path),
        "audit": p5_res["audit"]
    })

    # Imprimir tablas de resultados
    for r in results:
        print(format_audit_report(r["part_name"], r["audit"]))

    # Ensamble final abierto
    asm_path = output_dir / "04_Ensamble_Motor_Piston.asm"
    if asm_path.exists():
        doc_asm = app.Documents.Open(str(asm_path))
        apply_model_presentation(doc_asm, is_active=True)
        try:
            doc_asm.Windows.Item(1).View.SaveAsImage(str(output_dir / "04_Ensamble_Motor_Superficies_Limpias.png"), 1920, 1080)
        except Exception:
            pass

    if not CERRAR_AL_TERMINAR:
        bring_solidedge_to_foreground(app)
        print(f"\nESTADO FINAL: {app.Documents.Count} documentos permanecen abiertos y visibles en pantalla.")


if __name__ == "__main__":
    main()
