"""
Script de prueba maestro del Piston con hueco central counter-clockwise.
"""
import sys
import math
from pathlib import Path

sys.path.append("C:/Jarvis")
from cad_atomic_lib import (
    connect_or_launch_solidedge,
    create_part_doc,
    add_sketch_profile,
    add_line,
    close_profile_keypoints,
    add_extruded_cutout,
    create_base_protrusion,
    igRight, igLeft, igSymmetric
)
from piston_probe_validator import test_probe_points_on_stl, get_standard_piston_probes

def build_perfect_piston():
    app = connect_or_launch_solidedge()
    app.DisplayAlerts = False
    doc = create_part_doc(app)
    ref_planes = doc.RefPlanes
    plane_xy = ref_planes.Item(1)  # Superior (Planta)
    plane_yz = ref_planes.Item(2)  # Derecho
    plane_xz = ref_planes.Item(3)  # Frontal (Alzado)
    ps = doc.ProfileSets

    print(">>> 1. Base cilindrica R150 x 180mm...")
    ps1, prof1 = add_sketch_profile(doc, 1, "Boceto_01_Cilindro_Base")
    prof1.Circles2d.AddByCenterRadius(0.0, 0.0, 0.150)
    prof1.End(0)
    prof1.Visible = False
    model = create_base_protrusion(doc, prof1, 0.180)

    print(">>> 2. Cavidad interior R130 con corona maciza de 20mm...")
    ps3 = ps.Add()
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
    model.RevolvedCutouts.AddFinite(prof3, ref_ax3, igRight, igRight, 2.0 * math.pi)

    print(">>> 3. Ranuras detalle B (3x 5mm x 7.5mm)...")
    ps2 = ps.Add()
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
    model.RevolvedCutouts.AddFinite(prof2, ref_ax, igRight, igRight, 2.0 * math.pi)

    print(">>> 4. Bloque simetrico de columnas de patas en plano YZ (ancho 180mm en X)...")
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

    print(">>> 5. Vaciado del hueco central de 100mm entre patas (CCW con igRight)...")
    ps5, prof5 = add_sketch_profile(doc, 3, "Boceto_05_Hueco_Central")
    g1 = add_line(prof5, -0.050, -0.210, 0.050, -0.210)
    g2 = add_line(prof5, 0.050, -0.210, 0.050, -0.020)
    g3 = add_line(prof5, 0.050, -0.020, -0.050, -0.020)
    g4 = add_line(prof5, -0.050, -0.020, -0.050, -0.210)
    close_profile_keypoints(prof5, [g1, g2, g3, g4])
    add_extruded_cutout(model, prof5, 0.120, igRight, igSymmetric)

    print(">>> 6. Alojamiento pasante del pasador R25 (diam 50mm)...")
    ps6, prof6 = add_sketch_profile(doc, 2, "Boceto_06_Agujero_Pasador")
    prof6.Circles2d.AddByCenterRadius(0.0, -0.160, 0.025)
    prof6.End(0)
    prof6.Visible = False
    model.ExtrudedCutouts.AddFinite(prof6, igRight, igSymmetric, 0.250)

    print(">>> 7. Cortes laterales del faldon con arcos concavos R100...")
    # 7.1 Lado derecho (CCW)
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

    # 7.2 Lado izquierdo (CCW)
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

    print(">>> 8. Limpieza final: ocultar planos y croquis...")
    for i in range(1, ref_planes.Count + 1):
        try:
            ref_planes.Item(i).Visible = False
        except Exception:
            pass

    for i in range(1, ps.Count + 1):
        try:
            p_set = ps.Item(i)
            for j in range(1, p_set.Profiles.Count + 1):
                p_set.Profiles.Item(j).Visible = False
        except Exception:
            pass

    try:
        win = doc.Windows.Item(1)
        win.View.Fit()
        win.View.Orientation = 1
    except Exception:
        pass

    out_par = Path("C:/Jarvis/01_Piston_Perfecto.par")
    out_stl = Path("C:/Jarvis/01_Piston_Perfecto.stl")
    out_img = Path("C:/Jarvis/01_Piston_Perfecto.png")

    doc.SaveAs(str(out_par))
    doc.SaveCopyAs(str(out_stl))
    try:
        win.View.SaveAsImage(str(out_img), 1920, 1080)
    except Exception:
        pass

    doc.Close(True)
    print("Modelo guardado y cerrado.")

    print("\n>>> 9. Evaluacion de las 8 sondas de precision...")
    probes = get_standard_piston_probes()
    val_res = test_probe_points_on_stl(out_stl, probes)
    print(f"Watertight: {val_res['is_watertight']}")
    print(f"Limites 3D (mm): {val_res['bounds']}")
    print(f"Volumen (mm3): {val_res['volume_mm3']:.2f}")
    print(f"Sondas pasadas: {val_res['passed_count']} de {val_res['total_count']}")
    for r in val_res["results"]:
        status = "[PASO]" if r["pasa"] else "[FALLO]"
        print(f"  {status} {r['nombre']} ({r['coords']}): Esperado={r['esperado']}, Obtenido={r['obtenido']} | {r['detalle']}")

    return val_res

if __name__ == "__main__":
    build_perfect_piston()
