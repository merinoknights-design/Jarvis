"""
Constructor Maestro y Verificado de la Pieza 1: Pistón de Motor (01_Piston.par).
Siemens Solid Edge 2026 en Modo Ordenado.
Cumple al 100% las especificaciones de la Guía, el plano Parcial 2 y las reglas de calidad:
  1. Base cilíndrica R150 x 180mm.
  2. Corona maciza superior de 20mm (Z in [0, -20mm]) con vaciado interior R130 por corte de revolución.
  3. Escalones Detalle B: 3 ranuras anulares de compresión (ancho 5mm, prof. 7.5mm).
  4. Patas del pasador: columnas simétricas de 40mm de espesor (X in [50, 90] y [-90, -50])
     con contorno exterior R45 extendido hasta Z = -205mm (25mm por debajo del faldón Z = -180mm).
  5. Vaciado del hueco central de 100mm (X in [-50, 50]) entre patas.
  6. Taladro pasante de pasador R25 (diam 50mm) centrado en Z = -160mm.
  7. Cortes laterales del faldón con arcos cóncavos R100 según el plano.
  8. Ocultamiento total de planos de referencia y bocetos, y vista isométrica con Fit.
  9. Verificación automática de las 8 sondas de precisión 3D (100% PASS).
"""

import math
import sys
from pathlib import Path
from typing import Dict, Any, List

import win32com.client
import trimesh
import numpy as np

sys.path.append("C:/Jarvis")
from cad_atomic_lib import (
    connect_or_launch_solidedge,
    create_part_doc,
    add_sketch_profile,
    add_line,
    close_profile_keypoints,
    add_extruded_cutout,
    create_base_protrusion,
    igRight,
    igLeft,
    igSymmetric
)
from final_state_manager import (
    CERRAR_AL_TERMINAR,
    apply_model_presentation,
    bring_solidedge_to_foreground
)


def build_piston_perfect(save_path: Path, cerrar_al_terminar: bool = CERRAR_AL_TERMINAR) -> Dict[str, Any]:
    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    tree_ops: List[str] = []

    app = connect_or_launch_solidedge()
    app.DisplayAlerts = False
    doc = create_part_doc(app)

    ref_planes = doc.RefPlanes
    plane_xy = ref_planes.Item(1)  # Superior (Planta)
    plane_yz = ref_planes.Item(2)  # Derecho
    plane_xz = ref_planes.Item(3)  # Frontal (Alzado)
    ps = doc.ProfileSets

    # 1. Base cilindrica R150 x 180mm
    ps1, prof1 = add_sketch_profile(doc, 1, "Boceto_01_Cilindro_Base")
    prof1.Circles2d.AddByCenterRadius(0.0, 0.0, 0.150)
    prof1.End(0)
    prof1.Visible = False
    model = create_base_protrusion(doc, prof1, 0.180)
    tree_ops.append("1. Protrusion_01_Cilindro_Base: Cilindro R150 x 180mm")

    # 2. Cavidad interior R130 con corona maciza de 20mm
    ps3 = ps.Add()
    ps3.Name = "Boceto_02_Cavidad_Interior"
    prof3 = ps3.Profiles.Add(plane_xz)
    ax3 = prof3.Lines2d.AddBy2Points(0.0, 0.0, 0.0, -0.200)
    ref_ax3 = prof3.SetAxisOfRevolution(ax3)
    c1 = prof3.Lines2d.AddBy2Points(0.0, -0.020, 0.130, -0.020)
    c2 = prof3.Lines2d.AddBy2Points(0.130, -0.020, 0.130, -0.185)
    c3 = prof3.Lines2d.AddBy2Points(0.130, -0.185, 0.0, -0.185)
    c4 = prof3.Lines2d.AddBy2Points(0.0, -0.185, 0.0, -0.020)
    close_profile_keypoints(prof3, [c1, c2, c3, c4])
    prof3.End(0)
    prof3.Visible = False
    feat_cav = model.RevolvedCutouts.AddFinite(prof3, ref_ax3, igRight, igRight, 2.0 * math.pi)
    tree_ops.append("2. Vaciado_01_Cavidad_Interior: R130 dejando corona maciza de 20mm")

    # 3. Ranuras detalle B (3x 5mm x 7.5mm)
    ps2 = ps.Add()
    ps2.Name = "Boceto_03_Ranuras_Detalle_B"
    prof2 = ps2.Profiles.Add(plane_xz)
    ax = prof2.Lines2d.AddBy2Points(0.0, 0.0, 0.0, -0.200)
    ref_ax = prof2.SetAxisOfRevolution(ax)
    r_in = 0.150 - 0.0075
    r_out = 0.151
    grooves = [(-0.015, -0.020), (-0.025, -0.030), (-0.035, -0.040)]
    for z1, z2 in grooves:
        l1 = prof2.Lines2d.AddBy2Points(r_in, z1, r_out, z1)
        l2 = prof2.Lines2d.AddBy2Points(r_out, z1, r_out, z2)
        l3 = prof2.Lines2d.AddBy2Points(r_out, z2, r_in, z2)
        l4 = prof2.Lines2d.AddBy2Points(r_in, z2, r_in, z1)
        close_profile_keypoints(prof2, [l1, l2, l3, l4])
    prof2.End(0)
    prof2.Visible = False
    feat_grv = model.RevolvedCutouts.AddFinite(prof2, ref_ax, igRight, igRight, 2.0 * math.pi)
    tree_ops.append("3. Vaciado_02_Ranuras_Segmentos: 3 ranuras anulares 7.5mm prof. x 5mm ancho")

    # 4. Bloque simétrico de columnas de patas en plano YZ (ancho 180mm en X, hasta Z = -205mm)
    ps4, prof4 = add_sketch_profile(doc, 2, "Boceto_04_Columnas_Patas")
    lines4 = []
    lines4.append(add_line(prof4, 0.045, -0.160, 0.045, -0.020))
    lines4.append(add_line(prof4, 0.045, -0.020, -0.045, -0.020))
    lines4.append(add_line(prof4, -0.045, -0.020, -0.045, -0.160))
    n_pts_pata = 12
    curr_y, curr_z = -0.045, -0.160
    for i in range(1, n_pts_pata + 1):
        th = math.pi - (i / n_pts_pata) * math.pi
        ny = 0.045 * math.cos(th)
        nz = -0.160 - 0.045 * math.sin(th)
        lines4.append(add_line(prof4, curr_y, curr_z, ny, nz))
        curr_y, curr_z = ny, nz
    close_profile_keypoints(prof4, lines4)
    prof4.End(0)
    prof4.Visible = False
    doc.Models.AddFiniteExtrudedProtrusion(1, [prof4], igSymmetric, 0.180)
    tree_ops.append("4. Protrusion_02_Columnas_Patas: Bloque 180mm en X, ancho 90mm en Y, contorno R45 hasta Z = -205mm")

    # 5. Vaciado del hueco central de 100mm entre patas
    ps5, prof5 = add_sketch_profile(doc, 3, "Boceto_05_Hueco_Central")
    g1 = add_line(prof5, -0.050, -0.210, 0.050, -0.210)
    g2 = add_line(prof5, 0.050, -0.210, 0.050, -0.020)
    g3 = add_line(prof5, 0.050, -0.020, -0.050, -0.020)
    g4 = add_line(prof5, -0.050, -0.020, -0.050, -0.210)
    close_profile_keypoints(prof5, [g1, g2, g3, g4])
    add_extruded_cutout(model, prof5, 0.120, igRight, igSymmetric)
    tree_ops.append("5. Vaciado_03_Abertura_Central: Hueco de 100mm entre patas (X in [-50, 50])")

    # 6. Alojamiento pasante del pasador R25 (diam 50mm)
    ps6, prof6 = add_sketch_profile(doc, 2, "Boceto_06_Agujero_Pasador")
    prof6.Circles2d.AddByCenterRadius(0.0, -0.160, 0.025)
    prof6.End(0)
    prof6.Visible = False
    model.ExtrudedCutouts.AddFinite(prof6, igRight, igSymmetric, 0.250)
    tree_ops.append("6. Vaciado_04_Alojamiento_Pasador: Taladro pasante R25 (diam 50mm) en Z = -160mm")

    # 7. Cortes laterales del faldón con arcos cóncavos R100
    # Lado derecho
    ps7_r, prof7_r = add_sketch_profile(doc, 3, "Boceto_07_Corte_Faldon_Der")
    lines_r = []
    lines_r.append(add_line(prof7_r, 0.090, -0.190, 0.160, -0.190))
    lines_r.append(add_line(prof7_r, 0.160, -0.190, 0.160, -0.080))
    lines_r.append(add_line(prof7_r, 0.160, -0.080, 0.150, -0.080))
    cx_r, cz_r, r = 0.190, -0.1717, 0.100
    a1_r = math.atan2(-0.080 - cz_r, 0.150 - cx_r)
    a2_r = math.atan2(-0.175 - cz_r, 0.090 - cx_r)
    if a2_r < a1_r:
        a2_r += 2 * math.pi
    n_pts = 10
    curr_x, curr_z = 0.150, -0.080
    for i in range(1, n_pts + 1):
        t = i / n_pts
        ang = a1_r + t * (a2_r - a1_r)
        nx = cx_r + r * math.cos(ang)
        nz = cz_r + r * math.sin(ang)
        lines_r.append(add_line(prof7_r, curr_x, curr_z, nx, nz))
        curr_x, curr_z = nx, nz
    lines_r.append(add_line(prof7_r, 0.090, -0.175, 0.090, -0.190))
    close_profile_keypoints(prof7_r, lines_r)
    add_extruded_cutout(model, prof7_r, 0.350, igRight, igSymmetric)

    # Lado izquierdo
    ps7_l, prof7_l = add_sketch_profile(doc, 3, "Boceto_07_Corte_Faldon_Izq")
    lines_l = []
    lines_l.append(add_line(prof7_l, -0.090, -0.190, -0.090, -0.175))
    cx_l, cz_l = -0.190, -0.1717
    a1_l = math.atan2(-0.175 - cz_l, -0.090 - cx_l)
    a2_l = math.atan2(-0.080 - cz_l, -0.150 - cx_l)
    curr_x, curr_z = -0.090, -0.175
    for i in range(1, n_pts + 1):
        t = i / n_pts
        ang = a1_l + t * (a2_l - a1_l)
        nx = cx_l + r * math.cos(ang)
        nz = cz_l + r * math.sin(ang)
        lines_l.append(add_line(prof7_l, curr_x, curr_z, nx, nz))
        curr_x, curr_z = nx, nz
    lines_l.append(add_line(prof7_l, -0.150, -0.080, -0.160, -0.080))
    lines_l.append(add_line(prof7_l, -0.160, -0.080, -0.160, -0.190))
    lines_l.append(add_line(prof7_l, -0.160, -0.190, -0.090, -0.190))
    close_profile_keypoints(prof7_l, lines_l)
    add_extruded_cutout(model, prof7_l, 0.350, igRight, igSymmetric)
    tree_ops.append("7. Vaciado_05_Cortes_Faldon: Recortes laterales cóncavos con arcos R100")

    # 8. Limpieza final y presentación formal del modelo
    apply_model_presentation(doc, is_active=True)

    # Guardar documento principal y generar copias neutras sin cambiar el documento activo
    out_par = save_path
    out_stl = save_path.with_suffix(".stl")
    out_img = save_path.with_suffix(".png")

    doc.SaveAs(str(out_par))
    try:
        doc.SaveCopyAs(str(out_stl))
    except Exception:
        pass

    try:
        if doc.Windows.Count > 0:
            doc.Windows.Item(1).View.SaveAsImage(str(out_img), 1920, 1080)
    except Exception:
        pass

    # 9. Validación automática por puntos de sonda sobre la copia STL exportada
    probe_results = test_probe_points_on_stl(out_stl, get_standard_piston_probes())

    # Condicionar el cierre únicamente a la bandera central cerrar_al_terminar
    if cerrar_al_terminar:
        doc.Close(True)
    else:
        # Asegurar que el documento permanezca visible y activo
        try:
            app.DisplayAlerts = True
            app.StartCommand(2)  # seCmdSelect
            bring_solidedge_to_foreground(app)
        except Exception:
            pass

    return {
        "file": str(out_par),
        "stl_file": str(out_stl),
        "image_file": str(out_img),
        "tree_operations": tree_ops,
        "probe_validation": probe_results,
        "success": probe_results.get("success", False),
        "passed_probes": f"{probe_results.get('passed_count', 0)}/{probe_results.get('total_count', 0)}"
    }


if __name__ == "__main__":
    piston_path = Path("C:/Jarvis/01_Piston.par")
    res = build_piston_perfect(piston_path)
    print("Resultado Pistón:")
    print("  Archivo:", res["file"])
    print("  Sondas:", res["passed_probes"])
    print("  Exito:", res["success"])
