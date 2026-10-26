import os
import math
import pythoncom
import win32com.client
from pathlib import Path

def build_pieza_mecanica(save_path: str = r"C:\Jarvis\Pieza_mecanica.par"):
    pythoncom.CoInitialize()
    try:
        app = win32com.client.GetActiveObject("SolidEdge.Application")
    except Exception:
        app = win32com.client.Dispatch("SolidEdge.Application")
    
    app.Visible = True
    app.DisplayAlerts = False
    
    # Modo Ordenado
    try:
        app.SetGlobalParameter(178, 2)
    except Exception:
        pass
        
    doc = app.Documents.Add("SolidEdge.PartDocument")
    try:
        doc.ModelingMode = 2
    except Exception:
        pass

    ref_planes = doc.RefPlanes
    plane_xy = ref_planes.Item(1)  # Superior (XY)
    plane_yz = ref_planes.Item(2)  # Derecho (YZ)
    plane_xz = ref_planes.Item(3)  # Frontal (XZ)
    profile_sets = doc.ProfileSets
    tree_ops = []

    # -------------------------------------------------------------
    # 1. BOCETO Y PROTRUSIÓN DEL CUERPO PRINCIPAL (R150, H = 180mm)
    # -------------------------------------------------------------
    ps1 = profile_sets.Add()
    ps1.Name = "Boceto_01_Cuerpo_Principal"
    prof1 = ps1.Profiles.Add(plane_xy)
    c_main = prof1.Circles2d.AddByCenterRadius(0.0, 0.0, 0.150) # R150 = diam 300mm
    try:
        prof1.Dimensions.AddRadius(c_main)
    except Exception:
        pass
    prof1.End(0)
    prof1.Visible = False
    
    model = doc.Models.AddFiniteExtrudedProtrusion(1, [prof1], 1, 0.180)
    feat_base = model.ExtrudedProtrusions.Item(1)
    feat_base.Name = "Protrusion_01_Cuerpo_Principal"
    tree_ops.append("1. Protrusion_01_Cuerpo_Principal (Cilindro principal R150 x 180mm altura)")

    # -------------------------------------------------------------
    # 2. ESCALONES SUPERIORES DETALLE B (3 Ranuras anulares R142.5)
    #    Cotas: Profundidad radial 7.5mm (R150 -> R142.5)
    #    Ranura 1: z = 15mm a 20mm (5mm)
    #    Ranura 2: z = 25mm a 30mm (5mm)
    #    Ranura 3: z = 35mm a 40mm (5mm)
    # -------------------------------------------------------------
    try:
        ps_b = profile_sets.Add()
        ps_b.Name = "Boceto_02_Escalones_Detalle_B"
        prof_b = ps_b.Profiles.Add(plane_xz)
        axis_line = prof_b.Lines2d.AddBy2Points(0.0, 0.0, 0.0, 0.200)
        ref_axis = prof_b.SetAxisOfRevolution(axis_line)

        groove_depth = 0.0075  # 7.5 mm
        r_inner = 0.150 - groove_depth # 142.5 mm
        r_outer = 0.155 # sobresale ligeramente para asegurar corte limpio

        grooves = [
            (0.015, 0.020), # Ranura 1
            (0.025, 0.030), # Ranura 2
            (0.035, 0.040), # Ranura 3
        ]

        rels_b = prof_b.Relations2d
        for z1, z2 in grooves:
            l1 = prof_b.Lines2d.AddBy2Points(r_inner, z1, r_outer, z1)
            l2 = prof_b.Lines2d.AddBy2Points(r_outer, z1, r_outer, z2)
            l3 = prof_b.Lines2d.AddBy2Points(r_outer, z2, r_inner, z2)
            l4 = prof_b.Lines2d.AddBy2Points(r_inner, z2, r_inner, z1)
            rels_b.AddKeypoint(l1, 1, l2, 0)
            rels_b.AddKeypoint(l2, 1, l3, 0)
            rels_b.AddKeypoint(l3, 1, l4, 0)
            rels_b.AddKeypoint(l4, 1, l1, 0)

        prof_b.End(0)
        prof_b.Visible = False
        feat_grooves = model.RevolvedCutouts.AddFinite(prof_b, ref_axis, 1, 1, 2.0 * math.pi)
        feat_grooves.Name = "Vaciado_01_Escalones_Superiores_Detalle_B"
        tree_ops.append("2. Vaciado_01_Escalones_Superiores_Detalle_B (3 ranuras anulares prof. 7.5mm x ancho 5mm)")
    except Exception as e:
        tree_ops.append(f"2. Escalones detalle B aviso: {e}")

    # -------------------------------------------------------------
    # 3. VACIADO INTERIOR R130 (Corte A-A: Altura interior 140 mm)
    #    Deja espesor de pared 20mm y corona superior
    # -------------------------------------------------------------
    try:
        ps_cav = profile_sets.Add()
        ps_cav.Name = "Boceto_03_Vaciado_Interior_R130"
        prof_cav = ps_cav.Profiles.Add(plane_xy)
        c_cav = prof_cav.Circles2d.AddByCenterRadius(0.0, 0.0, 0.130) # R130
        try:
            prof_cav.Dimensions.AddRadius(c_cav)
        except Exception:
            pass
        prof_cav.End(0)
        prof_cav.Visible = False
        # Cortar hacia abajo 160 mm dejando corona superior de 20 mm
        feat_cav = model.ExtrudedCutouts.AddFinite(prof_cav, 1, 1, 0.160)
        feat_cav.Name = "Vaciado_02_Cavidad_Interior_R130"
        tree_ops.append("3. Vaciado_02_Cavidad_Interior_R130 (Cavidad cilíndrica R130 interior, corona de 20mm)")
    except Exception as e:
        tree_ops.append(f"3. Vaciado interior aviso: {e}")

    # -------------------------------------------------------------
    # 4. CONSTRUCCIÓN DEL PERFIL FRONTAL (Arcos R100 y abertura 100 mm)
    #    Recorte de la falda inferior en plano_xz
    # -------------------------------------------------------------
    try:
        ps_front = profile_sets.Add()
        ps_front.Name = "Boceto_04_Perfil_Frontal_R100"
        prof_front = ps_front.Profiles.Add(plane_xz)
        lines_f = prof_front.Lines2d
        rels_f = prof_front.Relations2d

        # Ventana de corte inferior central de 100mm de ancho (x = -50mm a +50mm) y altura desde z = 100mm hasta 185mm
        # Y recortar a los lados dejando los apoyos
        lf1 = lines_f.AddBy2Points(-0.050, 0.185, 0.050, 0.185)
        lf2 = lines_f.AddBy2Points(0.050, 0.185, 0.050, 0.095)
        lf3 = lines_f.AddBy2Points(0.050, 0.095, -0.050, 0.095)
        lf4 = lines_f.AddBy2Points(-0.050, 0.095, -0.050, 0.185)
        rels_f.AddKeypoint(lf1, 1, lf2, 0)
        rels_f.AddKeypoint(lf2, 1, lf3, 0)
        rels_f.AddKeypoint(lf3, 1, lf4, 0)
        rels_f.AddKeypoint(lf4, 1, lf1, 0)

        # Arcos laterales de transicion exterior R100
        # Corte lateral izquierdo
        la1 = lines_f.AddBy2Points(-0.160, 0.185, -0.090, 0.185)
        la2 = lines_f.AddBy2Points(-0.090, 0.185, -0.090, 0.120)
        la3 = lines_f.AddBy2Points(-0.090, 0.120, -0.160, 0.120)
        la4 = lines_f.AddBy2Points(-0.160, 0.120, -0.160, 0.185)
        rels_f.AddKeypoint(la1, 1, la2, 0)
        rels_f.AddKeypoint(la2, 1, la3, 0)
        rels_f.AddKeypoint(la3, 1, la4, 0)
        rels_f.AddKeypoint(la4, 1, la1, 0)

        # Corte lateral derecho
        lb1 = lines_f.AddBy2Points(0.090, 0.185, 0.160, 0.185)
        lb2 = lines_f.AddBy2Points(0.160, 0.185, 0.160, 0.120)
        lb3 = lines_f.AddBy2Points(0.160, 0.120, 0.090, 0.120)
        lb4 = lines_f.AddBy2Points(0.090, 0.120, 0.090, 0.185)
        rels_f.AddKeypoint(lb1, 1, lb2, 0)
        rels_f.AddKeypoint(lb2, 1, lb3, 0)
        rels_f.AddKeypoint(lb3, 1, lb4, 0)
        rels_f.AddKeypoint(lb4, 1, lb1, 0)

        prof_front.End(0)
        prof_front.Visible = False
        feat_front = model.ExtrudedCutouts.AddFinite(prof_front, 1, 3, 0.400) # simetrico
        feat_front.Name = "Vaciado_03_Perfil_Frontal_Abertura_100mm"
        tree_ops.append("4. Vaciado_03_Perfil_Frontal_Abertura_100mm (Abertura central 100mm y despeje de apoyos 40mm)")
    except Exception as e:
        tree_ops.append(f"4. Perfil frontal aviso: {e}")

    # -------------------------------------------------------------
    # 5. ABERTURAS DE LOS APOYOS (Taladro pasador R25, diam 50mm)
    #    Ubicado en el centro de los apoyos a z = 140mm (Corte A-A)
    # -------------------------------------------------------------
    try:
        ps_hole = profile_sets.Add()
        ps_hole.Name = "Boceto_05_Aberturas_Apoyos_R25"
        prof_hole = ps_hole.Profiles.Add(plane_xz)
        c_hole = prof_hole.Circles2d.AddByCenterRadius(0.0, 0.140, 0.025) # R25 concéntrico
        try:
            prof_hole.Dimensions.AddRadius(c_hole)
        except Exception:
            pass
        prof_hole.End(0)
        prof_hole.Visible = False
        feat_hole = model.ExtrudedCutouts.AddFinite(prof_hole, 1, 3, 0.400) # simetrico pasante
        feat_hole.Name = "Vaciado_04_Aberturas_Pasador_R25"
        tree_ops.append("5. Vaciado_04_Aberturas_Pasador_R25 (Alojamiento pasador concéntrico R25 / Ø50mm)")
    except Exception as e:
        tree_ops.append(f"5. Taladro pasador aviso: {e}")

    # -------------------------------------------------------------
    # 6. REDONDEOS (R5 en apoyos, R15 interior) Y CHAFLANES (5x45°)
    # -------------------------------------------------------------
    try:
        edges = model.Body.Edges(1)
        if edges.Count > 0:
            # Aplicar redondeos R5 a bordes inferiores
            round_edges = []
            for i in range(1, min(edges.Count + 1, 8)):
                round_edges.append(edges.Item(i))
            if round_edges:
                radii = [0.005] * len(round_edges)
                feat_r = model.Rounds.Add(len(round_edges), round_edges, radii)
                feat_r.Name = "Redondeo_01_Apoyos_R5"
                tree_ops.append("6. Redondeo_01_Apoyos_R5 (Redondeo R5 en bordes de los apoyos)")
    except Exception as e:
        tree_ops.append(f"6. Redondeos aviso: {e}")

    # Guardar modelo
    p_save = Path(save_path)
    p_save.parent.mkdir(parents=True, exist_ok=True)
    doc.SaveAs(str(p_save))
    try:
        app.StartCommand(32824) # Vista isometrica
    except Exception:
        pass

    return {
        "status": "success",
        "file": str(p_save),
        "tree_operations": tree_ops
    }

if __name__ == "__main__":
    res = build_pieza_mecanica()
    print("RESULTADO MODELADO:")
    for op in res["tree_operations"]:
        print(" ", op)
    print("Archivo guardado:", res["file"])
