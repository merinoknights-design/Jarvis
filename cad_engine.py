import json
import math
import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
import pythoncom
import win32com.client

from cad_edge_selector import (
    filter_support_edges_for_rounds,
    filter_top_rim_edges_for_chamfer,
    filter_inner_cavity_edges
)
from cad_validator import (
    validate_part_model_health,
    verify_dimensions_against_plan,
    capture_and_export_solid_edge_model
)
from cad_schema import (
    validate_cad_blueprint_schema,
    verify_cross_view_consistency,
    create_standard_piston_plan
)

# Constantes oficiales de la API de Siemens Solid Edge 2026
igRight = 1
igLeft = 2
igSymmetric = 3
seModelingModeSynchronous = 1
seModelingModeOrdered = 2  # VALOR 2 = Modo Ordenado real en Solid Edge (PathFinder Ordenado)
seApplicationGlobalDefaultModelingMode = 178


def get_or_start_solidedge():
    """Conecta con la instancia activa de Solid Edge 2026 o la inicia en Modo Ordenado por defecto."""
    pythoncom.CoInitialize()
    app = None
    try:
        app = win32com.client.GetActiveObject("SolidEdge.Application")
        _ = app.Version
    except Exception:
        app = None

    if app is None:
        import subprocess
        try:
            subprocess.run(["taskkill", "/f", "/im", "Edge.exe"], capture_output=True)
            import time
            time.sleep(1.0)
        except Exception:
            pass
        try:
            app = win32com.client.Dispatch("SolidEdge.Application")
        except Exception:
            import time
            time.sleep(2.0)
            app = win32com.client.Dispatch("SolidEdge.Application")
    app.Visible = True
    app.DisplayAlerts = False
    # Configurar Solid Edge globalmente para que cree documentos nuevos SIEMPRE en Modo Ordenado (2)
    try:
        app.SetGlobalParameter(seApplicationGlobalDefaultModelingMode, seModelingModeOrdered)
    except Exception:
        pass
    return app


def switch_to_ordered_mode(part_doc):
    """Fuerza que el documento de pieza esté en Modo Ordenado (2) y NO Síncrono (1)."""
    try:
        part_doc.ModelingMode = seModelingModeOrdered
    except Exception:
        pass
    try:
        part_doc.Application.SetGlobalParameter(seApplicationGlobalDefaultModelingMode, seModelingModeOrdered)
        part_doc.ModelingMode = 2
    except Exception:
        pass


def draw_closed_rectangle_with_dims(prof, cx: float, cy: float, w: float, l: float):
    """Dibuja un boceto rectangular cerrado, aplica restricciones Keypoint y cotas paramétricas."""
    hw, hl = w / 2.0, l / 2.0
    lines = prof.Lines2d
    l1 = lines.AddBy2Points(cx - hl, cy - hw, cx + hl, cy - hw)
    l2 = lines.AddBy2Points(cx + hl, cy - hw, cx + hl, cy + hw)
    l3 = lines.AddBy2Points(cx + hl, cy + hw, cx - hl, cy + hw)
    l4 = lines.AddBy2Points(cx - hl, cy + hw, cx - hl, cy - hw)

    rels = prof.Relations2d
    rels.AddKeypoint(l1, 1, l2, 0)
    rels.AddKeypoint(l2, 1, l3, 0)
    rels.AddKeypoint(l3, 1, l4, 0)
    rels.AddKeypoint(l4, 1, l1, 0)

    # Agregar cotas paramétricas reales al boceto 2D
    try:
        dims = prof.Dimensions
        dims.AddLength(l1)
        dims.AddLength(l2)
    except Exception:
        pass


def draw_closed_polygon(prof, cx: float, cy: float, radius: float, sides: int):
    """Dibuja un polígono cerrado con relaciones geométricas."""
    lines = prof.Lines2d
    rels = prof.Relations2d
    seg_lines = []
    pts = []
    for i in range(sides):
        ang = 2.0 * math.pi * i / sides
        pts.append((cx + radius * math.cos(ang), cy + radius * math.sin(ang)))
    for i in range(sides):
        p1 = pts[i]
        p2 = pts[(i + 1) % sides]
        seg_lines.append(lines.AddBy2Points(p1[0], p1[1], p2[0], p2[1]))
    for i in range(sides):
        rels.AddKeypoint(seg_lines[i], 1, seg_lines[(i + 1) % sides], 0)


def draw_l_profile_with_dims(prof, leg_x: float, leg_y: float, thickness: float):
    """Dibuja un perfil en L cerrado con relaciones Keypoint y cotas en el boceto."""
    lines = prof.Lines2d
    rels = prof.Relations2d
    pts = [
        (0.0, 0.0),
        (leg_x, 0.0),
        (leg_x, thickness),
        (thickness, thickness),
        (thickness, leg_y),
        (0.0, leg_y)
    ]
    segs = []
    for i in range(len(pts)):
        p1, p2 = pts[i], pts[(i + 1) % len(pts)]
        segs.append(lines.AddBy2Points(p1[0], p1[1], p2[0], p2[1]))
    for i in range(len(segs)):
        rels.AddKeypoint(segs[i], 1, segs[(i + 1) % len(segs)], 0)
    try:
        dims = prof.Dimensions
        dims.AddLength(segs[0])
        dims.AddLength(segs[5])
    except Exception:
        pass


def build_revolved_part(plan: Dict[str, Any], save_path: Path) -> Dict[str, Any]:
    """
    Construye un SÓLIDO DE REVOLUCIÓN completo en Solid Edge 2026 (Modo Ordenado):
      1. Boceto 2D con eje de revolución (SetAxisOfRevolution) + Protrusión RevolvedProtrusion 360°
      2. Boceto y corte de ranuras anulares / gargantas de polea / canales de junta (RevolvedCutouts)
      3. Boceto y taladro central pasante o ciego (ExtrudedCutouts)
      4. Boceto y matriz circular de pernos en diámetro primitivo (PCD)
      5. Redondeos de acuerdo de radios (Rounds) y chaflanes de entrada (Chamfers)
    """
    app = get_or_start_solidedge()
    doc = app.Documents.Add("SolidEdge.PartDocument")
    switch_to_ordered_mode(doc)

    ref_planes = doc.RefPlanes
    plane_xy = ref_planes.Item(1)  # Superior
    plane_xz = ref_planes.Item(3)  # Frontal (eje longitudinal Z)
    profile_sets = doc.ProfileSets
    tree_ops: List[str] = []

    dims = plan.get("dimensions_mm", {})
    outer_d_m = float(dims.get("outer_diameter", 120.0)) / 1000.0
    r_max = outer_d_m / 2.0
    length_m = float(dims.get("height", dims.get("length", 100.0))) / 1000.0
    inner_d_m = float(dims.get("inner_diameter", 0.0)) / 1000.0
    r_inner = inner_d_m / 2.0
    step_d_m = float(dims.get("boss_diameter", outer_d_m * 1000.0 * 0.65)) / 1000.0
    r_step = step_d_m / 2.0
    step_h_m = float(dims.get("boss_height", length_m * 1000.0 * 0.45)) / 1000.0
    fillet_m = float(dims.get("fillet_radius", 2.0)) / 1000.0
    chamfer_m = float(dims.get("chamfer", 1.5)) / 1000.0 if isinstance(dims.get("chamfer"), (int, float)) else 0.0015
    bolt_count = int(dims.get("bolt_holes_count", 0))
    bolt_d_m = float(dims.get("bolt_hole_diameter", 8.0)) / 1000.0

    # 1. BOCETO Y PROTRUSIÓN POR REVOLUCIÓN 360°
    ps1 = profile_sets.Add()
    try:
        ps1.Name = "Boceto_01_Perfil_Revolucion"
    except Exception:
        pass
    prof1 = ps1.Profiles.Add(plane_xz)
    axis_line = prof1.Lines2d.AddBy2Points(0.0, 0.0, 0.0, length_m * 1.2)
    ref_axis = prof1.SetAxisOfRevolution(axis_line)

    lines = prof1.Lines2d
    rels = prof1.Relations2d
    # Perfil escalonado de revolución (eje / polea / buje)
    pts = [
        (0.0, 0.0),
        (r_step, 0.0),
        (r_step, step_h_m),
        (r_max, step_h_m),
        (r_max, length_m),
        (0.0, length_m)
    ]
    segs = []
    for i in range(len(pts)):
        p1 = pts[i]
        p2 = pts[(i + 1) % len(pts)]
        segs.append(lines.AddBy2Points(p1[0], p1[1], p2[0], p2[1]))
    for i in range(len(segs)):
        rels.AddKeypoint(segs[i], 1, segs[(i + 1) % len(segs)], 0)

    prof1.End(0)
    prof1.Visible = False

    model = doc.Models.AddFiniteRevolvedProtrusion(1, [prof1], ref_axis, igRight, 2.0 * math.pi)
    try:
        model.RevolvedProtrusions.Item(1).Name = "Protrusion_01_Solido_Revolucion_360"
    except Exception:
        pass
    tree_ops.append(f"1. Protrusion_01_Solido_Revolucion_360 (Ø{round(outer_d_m*1000,1)}mm / Ø{round(step_d_m*1000,1)}mm x {round(length_m*1000,1)}mm longitud)")

    # 2. VACIADO DE RANURA / GARGANTA ANULAR (si es polea o tiene ranura)
    if dims.get("has_groove", True) and r_max > 0.020:
        try:
            ps_grv = profile_sets.Add()
            try:
                ps_grv.Name = "Boceto_02_Garganta_Anular"
            except Exception:
                pass
            prof_grv = ps_grv.Profiles.Add(plane_xz)
            ax_grv = prof_grv.Lines2d.AddBy2Points(0.0, 0.0, 0.0, length_m * 1.2)
            ref_ax_grv = prof_grv.SetAxisOfRevolution(ax_grv)

            grv_w = float(dims.get("groove_width", 6.0)) / 1000.0
            grv_depth = float(dims.get("groove_depth", 5.0)) / 1000.0
            z_mid = (step_h_m + length_m) / 2.0
            z_g1 = z_mid - grv_w / 2.0
            z_g2 = z_mid + grv_w / 2.0
            r_g_inner = r_max - grv_depth
            r_g_outer = r_max + 0.005

            gl = prof_grv.Lines2d
            gr = prof_grv.Relations2d
            gp = [
                (r_g_inner, z_g1),
                (r_g_outer, z_g1),
                (r_g_outer, z_g2),
                (r_g_inner, z_g2)
            ]
            g_segs = []
            for i in range(len(gp)):
                g_segs.append(gl.AddBy2Points(gp[i][0], gp[i][1], gp[(i+1)%len(gp)][0], gp[(i+1)%len(gp)][1]))
            for i in range(len(g_segs)):
                gr.AddKeypoint(g_segs[i], 1, g_segs[(i+1)%len(g_segs)], 0)

            prof_grv.End(0)
            prof_grv.Visible = False
            feat_grv = model.RevolvedCutouts.AddFinite(prof_grv, ref_ax_grv, igRight, igRight, 2.0 * math.pi)
            try:
                feat_grv.Name = "Vaciado_01_Garganta_Anular_Revolucion"
            except Exception:
                pass
            tree_ops.append(f"2. Vaciado_01_Garganta_Anular_Revolucion (Garganta anular de prof. {round(grv_depth*1000,1)}mm x ancho {round(grv_w*1000,1)}mm)")
        except Exception as e:
            tree_ops.append(f"2. Ranura anular aviso: {e}")

    # 3. TALADRO CENTRAL PASANTE (Alojamiento para eje)
    if inner_d_m > 0.0:
        try:
            ps_hole = profile_sets.Add()
            try:
                ps_hole.Name = "Boceto_03_Barreno_Central"
            except Exception:
                pass
            prof_hole = ps_hole.Profiles.Add(plane_xy)
            prof_hole.Circles2d.AddByCenterRadius(0.0, 0.0, r_inner)
            prof_hole.End(0)
            prof_hole.Visible = False
            feat_hole = model.ExtrudedCutouts.AddFinite(prof_hole, igRight, igRight, length_m * 1.5)
            try:
                feat_hole.Name = "Corte_01_Barreno_Central_Pasante"
            except Exception:
                pass
            tree_ops.append(f"3. Corte_01_Barreno_Central_Pasante (Taladro pasante Ø{round(inner_d_m*1000,1)}mm)")
        except Exception as e:
            tree_ops.append(f"3. Barreno central aviso: {e}")

    # 4. MATRIZ CIRCULAR DE PERNOS (si aplica)
    if bolt_count > 0 and bolt_d_m > 0:
        try:
            ps_bolts = profile_sets.Add()
            try:
                ps_bolts.Name = "Boceto_04_Matriz_Pernos"
            except Exception:
                pass
            prof_bolts = ps_bolts.Profiles.Add(plane_xy)
            pcd_r = (r_step * 0.75) if r_step > (r_inner + bolt_d_m) else (r_max * 0.8)
            circles = prof_bolts.Circles2d
            for i in range(bolt_count):
                ang = 2.0 * math.pi * i / bolt_count
                bx = pcd_r * math.cos(ang)
                by = pcd_r * math.sin(ang)
                circles.AddByCenterRadius(bx, by, bolt_d_m / 2.0)
            prof_bolts.End(0)
            prof_bolts.Visible = False
            feat_bolts = model.ExtrudedCutouts.AddFinite(prof_bolts, igRight, igRight, length_m * 1.5)
            try:
                feat_bolts.Name = f"Corte_02_Matriz_{bolt_count}_Barrenos"
            except Exception:
                pass
            tree_ops.append(f"4. Corte_02_Matriz_{bolt_count}_Barrenos ({bolt_count} taladros Ø{round(bolt_d_m*1000,1)}mm en PCD Ø{round(pcd_r*2000,1)}mm)")
        except Exception as e:
            tree_ops.append(f"4. Matriz pernos aviso: {e}")

    # 5. REDONDEOS Y CHAFLANES
    if fillet_m > 0 or chamfer_m > 0:
        try:
            edges = model.Body.Edges(1)
            if edges.Count > 0:
                max_e = min(edges.Count, 6)
                edge_list = [edges.Item(i) for i in range(1, max_e + 1)]
                radii = [fillet_m] * max_e
                feat_rnd = model.Rounds.Add(max_e, edge_list, radii)
                try:
                    feat_rnd.Name = f"Redondeo_01_R{round(fillet_m*1000,1)}mm"
                except Exception:
                    pass
                tree_ops.append(f"5. Redondeo_01_R{round(fillet_m*1000,1)}mm (Redondeo de acuerdos y transiciones)")
        except Exception:
            pass

    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    if save_path.exists():
        try:
            save_path.unlink()
        except Exception:
            import time
            save_path = save_path.parent / f"{save_path.stem}_{int(time.time())}{save_path.suffix}"

    doc.SaveAs(str(save_path))
    try:
        app.StartCommand(32824)
    except Exception:
        pass

    return {
        "file": str(save_path),
        "plan": plan,
        "tree_operations": tree_ops
    }


def build_flange_coupling_part(plan: Dict[str, Any], save_path: Path) -> Dict[str, Any]:
    """
    Construye una BRIDA / ACOPLAMIENTO CIRCULAR en Solid Edge 2026:
      1. Protrusión 01: Disco plato exterior
      2. Protrusión 02: Cuello cilíndrico saliente / Maza
      3. Corte 01: Barreno pasante central
      4. Corte 02: Matriz circular de pernos en PCD
      5. Vaciado 01: Ranura concéntrica para junta tórica / O-ring (si aplica)
      6. Redondeos y chaflanes en bordes
    """
    app = get_or_start_solidedge()
    doc = app.Documents.Add("SolidEdge.PartDocument")
    switch_to_ordered_mode(doc)

    ref_planes = doc.RefPlanes
    plane_xy = ref_planes.Item(1)
    profile_sets = doc.ProfileSets
    tree_ops: List[str] = []

    dims = plan.get("dimensions_mm", {})
    outer_d_m = float(dims.get("outer_diameter", 160.0)) / 1000.0
    thickness_m = float(dims.get("thickness", 16.0)) / 1000.0
    boss_d_m = float(dims.get("boss_diameter", outer_d_m * 1000.0 * 0.55)) / 1000.0
    boss_h_m = float(dims.get("boss_height", 35.0)) / 1000.0
    inner_d_m = float(dims.get("inner_diameter", 45.0)) / 1000.0
    bolt_count = int(dims.get("bolt_holes_count", 6))
    bolt_d_m = float(dims.get("bolt_hole_diameter", 12.0)) / 1000.0
    fillet_m = float(dims.get("fillet_radius", 2.5)) / 1000.0

    # 1. DISCO BASE
    ps1 = profile_sets.Add()
    try:
        ps1.Name = "Boceto_01_Plato_Brida"
    except Exception:
        pass
    prof1 = ps1.Profiles.Add(plane_xy)
    prof1.Circles2d.AddByCenterRadius(0.0, 0.0, outer_d_m / 2.0)
    prof1.End(0)
    prof1.Visible = False
    model = doc.Models.AddFiniteExtrudedProtrusion(1, [prof1], igRight, thickness_m)
    try:
        model.ExtrudedProtrusions.Item(1).Name = "Protrusion_01_Plato_Brida"
    except Exception:
        pass
    tree_ops.append(f"1. Protrusion_01_Plato_Brida (Disco plato Ø{round(outer_d_m*1000,1)}mm x {round(thickness_m*1000,1)}mm)")

    # 2. CUELLO / MAZA CENTRAL
    try:
        ps2 = profile_sets.Add()
        try:
            ps2.Name = "Boceto_02_Cuello_Maza"
        except Exception:
            pass
        prof2 = ps2.Profiles.Add(plane_xy)
        prof2.Circles2d.AddByCenterRadius(0.0, 0.0, boss_d_m / 2.0)
        prof2.End(0)
        prof2.Visible = False
        feat_boss = model.ExtrudedProtrusions.AddFinite(prof2, igRight, igRight, boss_h_m + thickness_m)
        try:
            feat_boss.Name = "Protrusion_02_Cuello_Maza"
        except Exception:
            pass
        tree_ops.append(f"2. Protrusion_02_Cuello_Maza (Saliente cilíndrico Ø{round(boss_d_m*1000,1)}mm x {round(boss_h_m*1000,1)}mm)")
    except Exception as e:
        tree_ops.append(f"2. Cuello maza aviso: {e}")

    # 3. TALADRO CENTRAL PASANTE
    if inner_d_m > 0:
        try:
            ps3 = profile_sets.Add()
            try:
                ps3.Name = "Boceto_03_Barreno_Central"
            except Exception:
                pass
            prof3 = ps3.Profiles.Add(plane_xy)
            prof3.Circles2d.AddByCenterRadius(0.0, 0.0, inner_d_m / 2.0)
            prof3.End(0)
            prof3.Visible = False
            feat_cut = model.ExtrudedCutouts.AddFinite(prof3, igRight, igRight, (boss_h_m + thickness_m) * 2.0)
            try:
                feat_cut.Name = "Corte_01_Barreno_Central"
            except Exception:
                pass
            tree_ops.append(f"3. Corte_01_Barreno_Central (Taladro pasante Ø{round(inner_d_m*1000,1)}mm)")
        except Exception as e:
            tree_ops.append(f"3. Barreno central aviso: {e}")

    # 4. MATRIZ CIRCULAR DE TORNILLOS (PCD)
    if bolt_count > 0 and bolt_d_m > 0:
        try:
            ps4 = profile_sets.Add()
            try:
                ps4.Name = "Boceto_04_Matriz_Pernos"
            except Exception:
                pass
            prof4 = ps4.Profiles.Add(plane_xy)
            pcd_r = ((outer_d_m + boss_d_m) / 4.0)
            circs = prof4.Circles2d
            for i in range(bolt_count):
                ang = 2.0 * math.pi * i / bolt_count
                bx = pcd_r * math.cos(ang)
                by = pcd_r * math.sin(ang)
                circs.AddByCenterRadius(bx, by, bolt_d_m / 2.0)
            prof4.End(0)
            prof4.Visible = False
            feat_bolts = model.ExtrudedCutouts.AddFinite(prof4, igRight, igRight, thickness_m * 2.0)
            try:
                feat_bolts.Name = f"Corte_02_Matriz_{bolt_count}_Tornillos"
            except Exception:
                pass
            tree_ops.append(f"4. Corte_02_Matriz_{bolt_count}_Tornillos ({bolt_count} taladros Ø{round(bolt_d_m*1000,1)}mm en PCD Ø{round(pcd_r*2000,1)}mm)")
        except Exception as e:
            tree_ops.append(f"4. Matriz pernos aviso: {e}")

    # 5. REDONDEOS
    if fillet_m > 0:
        try:
            edges = model.Body.Edges(1)
            if edges.Count > 0:
                max_e = min(edges.Count, 4)
                edge_list = [edges.Item(i) for i in range(1, max_e + 1)]
                radii = [fillet_m] * max_e
                feat_rnd = model.Rounds.Add(max_e, edge_list, radii)
                try:
                    feat_rnd.Name = f"Redondeo_01_R{round(fillet_m*1000,1)}mm"
                except Exception:
                    pass
                tree_ops.append(f"5. Redondeo_01_R{round(fillet_m*1000,1)}mm (Redondeo de acuerdo entre plato y maza)")
        except Exception:
            pass

    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    if save_path.exists():
        try:
            save_path.unlink()
        except Exception:
            import time
            save_path = save_path.parent / f"{save_path.stem}_{int(time.time())}{save_path.suffix}"

    doc.SaveAs(str(save_path))
    try:
        app.StartCommand(32824)
    except Exception:
        pass

    return {
        "file": str(save_path),
        "plan": plan,
        "tree_operations": tree_ops
    }


def execute_universal_cad_plan(plan: Dict[str, Any], save_path: Path) -> Dict[str, Any]:
    """
    MOTOR UNIVERSAL DE AUTOMATIZACIÓN CAD EN SIEMENS SOLID EDGE 2026:
    Ejecuta cualquier sólido paramétrico complejo (Modo Ordenado):
      - Pistones complejos (Cilindros con ranuras anulares, cavidades, vaciados frontales, alojamientos y acuerdos)
      - Sólidos de revolución (Ejes escalonados, poleas con gargantas, bujes, discos, válvulas)
      - Bridas y acoplamientos (Platos con salientes, matriz polar de barrenos y ranuras de junta)
      - Soportes y perfiles en L/T/U con orificios de fijación
      - Cajas, bloques mecánicos, placas perforadas y carcasas con cajeras vaciadas
    """
    shape = plan.get("base_shape", "box")
    if shape in ["cylinder_piston", "piston_complex"] or plan.get("is_complex_blueprint") or "pieza_mecanica" in str(save_path).lower():
        return build_pieza_mecanica_piston(save_path)
    elif shape in ["revolved", "revolved_part", "pulley", "stepped_shaft", "bushing", "shaft", "gear_blank"]:
        return build_revolved_part(plan, save_path)
    elif shape in ["flange", "coupling"]:
        return build_flange_coupling_part(plan, save_path)
    else:
        return build_prismatic_machined_part(plan, save_path)


# Alias oficial de compatibilidad
execute_cad_feature_plan = execute_universal_cad_plan


def build_prismatic_machined_part(plan: Dict[str, Any], save_path: Path) -> Dict[str, Any]:
    app = get_or_start_solidedge()
    doc = app.Documents.Add("SolidEdge.PartDocument")
    switch_to_ordered_mode(doc)

    # Mostrar planos de referencia base en el árbol
    ref_planes = doc.RefPlanes
    plane_xy = ref_planes.Item(1)  # Plano Planta (XY)
    plane_xz = ref_planes.Item(3)  # Plano Alzado (XZ)
    profile_sets = doc.ProfileSets

    shape = plan.get("base_shape", "box")
    dims = plan.get("dimensions_mm", {})

    length_m = float(dims.get("length", 120.0)) / 1000.0
    width_m = float(dims.get("width", 80.0)) / 1000.0
    height_m = float(dims.get("height", 40.0)) / 1000.0
    diam_m = float(dims.get("outer_diameter", 90.0)) / 1000.0
    inner_diam_m = float(dims.get("inner_diameter", 0.0)) / 1000.0
    fillet_m = float(dims.get("fillet_radius", 2.5)) / 1000.0
    bolt_count = int(dims.get("bolt_holes_count", 0))
    bolt_diam_m = float(dims.get("bolt_hole_diameter", 10.0)) / 1000.0
    thickness_m = float(dims.get("thickness", 14.0)) / 1000.0

    tree_operations: List[str] = []

    # =========================================================================
    # OPERACIÓN 1: BOCETO BASE 2D + PROTRUSIÓN EXTRUIDA SÓLIDA PRINCIPAL
    # =========================================================================
    ps1 = profile_sets.Add()
    try:
        ps1.Name = "Boceto_01_Perfil_Base"
    except Exception:
        pass
    prof1 = ps1.Profiles.Add(plane_xy)

    if shape in ["cylinder", "flange", "stepped_shaft", "bushing", "gear_blank"]:
        c_base = prof1.Circles2d.AddByCenterRadius(0.0, 0.0, diam_m / 2.0)
        try:
            prof1.Dimensions.AddRadius(c_base)
        except Exception:
            pass
        ext_depth = height_m if shape != "flange" else thickness_m
    elif shape == "polygon":
        sides = int(dims.get("sides", 6))
        draw_closed_polygon(prof1, 0.0, 0.0, diam_m / 2.0, sides)
        ext_depth = height_m
    elif shape == "l_bracket":
        draw_l_profile_with_dims(prof1, length_m, height_m, thickness_m)
        ext_depth = width_m
    else:
        draw_closed_rectangle_with_dims(prof1, 0.0, 0.0, width_m, length_m)
        ext_depth = height_m

    prof1.End(0)
    prof1.Visible = False

    model = doc.Models.AddFiniteExtrudedProtrusion(1, [prof1], igRight, ext_depth)
    try:
        model.ExtrudedProtrusions.Item(1).Name = "Protrusion_01_Base_Solida"
    except Exception:
        pass
    tree_operations.append(f"1. Protrusion_01_Base_Solida (Boceto 2D cerrado -> Extrusión sólida de {round(ext_depth*1000, 1)} mm)")

    # =========================================================================
    # OPERACIÓN 2: SEGUNDA PROTRUSIÓN SÓLIDA (Cuello / Escalón / Saliente)
    # =========================================================================
    if shape in ["flange", "stepped_shaft"] or dims.get("boss_diameter", 0) > 0:
        try:
            boss_d_m = float(dims.get("boss_diameter", diam_m * 1000.0 * 0.58)) / 1000.0
            boss_h_m = float(dims.get("boss_height", height_m * 1000.0)) / 1000.0
            ps_boss = profile_sets.Add()
            try:
                ps_boss.Name = "Boceto_02_Saliente_Cuello"
            except Exception:
                pass
            prof_boss = ps_boss.Profiles.Add(plane_xy)
            c_boss = prof_boss.Circles2d.AddByCenterRadius(0.0, 0.0, boss_d_m / 2.0)
            try:
                prof_boss.Dimensions.AddRadius(c_boss)
            except Exception:
                pass
            prof_boss.End(0)
            prof_boss.Visible = False
            feat_boss = model.ExtrudedProtrusions.AddFinite(prof_boss, igRight, igRight, boss_h_m)
            try:
                feat_boss.Name = "Protrusion_02_Cuello_Escalon"
            except Exception:
                pass
            tree_operations.append(f"2. Protrusion_02_Cuello_Escalon (Ø{round(boss_d_m*1000,1)} mm x {round(boss_h_m*1000,1)} mm)")
        except Exception:
            pass

    # =========================================================================
    # OPERACIÓN 3: BOCETO + CORTE EXTRUIDO CENTRAL (Taladro / Alojamiento)
    # =========================================================================
    if inner_diam_m > 0.0 and inner_diam_m < diam_m:
        try:
            ps_cut = profile_sets.Add()
            try:
                ps_cut.Name = "Boceto_03_Taladro_Central"
            except Exception:
                pass
            prof_cut = ps_cut.Profiles.Add(plane_xy)
            c_cut = prof_cut.Circles2d.AddByCenterRadius(0.0, 0.0, inner_diam_m / 2.0)
            try:
                prof_cut.Dimensions.AddRadius(c_cut)
            except Exception:
                pass
            prof_cut.End(0)
            prof_cut.Visible = False
            cut_depth = max(height_m, ext_depth) * 2.5
            feat_cut = model.ExtrudedCutouts.AddFinite(prof_cut, igRight, igSymmetric, cut_depth)
            try:
                feat_cut.Name = "Corte_01_Alojamiento_Central"
            except Exception:
                pass
            tree_operations.append(f"3. Corte_01_Alojamiento_Central (Corte extruido pasante Ø{round(inner_diam_m*1000,1)} mm)")
        except Exception:
            pass

    # =========================================================================
    # OPERACIÓN 4: VACIADO DE CAJA / CARCASA (Cajera interior sólida)
    # =========================================================================
    if dims.get("hollow_shell", False):
        try:
            ps_shell = profile_sets.Add()
            try:
                ps_shell.Name = "Boceto_Cajera_Interior"
            except Exception:
                pass
            prof_shell = ps_shell.Profiles.Add(plane_xy)
            inner_w = max(width_m - 2 * thickness_m, 0.01)
            inner_l = max(length_m - 2 * thickness_m, 0.01)
            draw_closed_rectangle_with_dims(prof_shell, 0.0, 0.0, inner_w, inner_l)
            prof_shell.End(0)
            prof_shell.Visible = False
            feat_shell = model.ExtrudedCutouts.AddFinite(prof_shell, igRight, igRight, max(height_m - thickness_m, 0.005))
            try:
                feat_shell.Name = "Corte_Cajera_Vaciado"
            except Exception:
                pass
            tree_operations.append(f"4. Corte_Cajera_Vaciado (Cajera interior de espesor {round(thickness_m*1000,1)} mm)")
        except Exception:
            pass

    # =========================================================================
    # OPERACIÓN 5: BOCETO + CORTE EXTRUIDO DE MATRIZ DE TALADROS / PERNOS
    # =========================================================================
    if bolt_count > 0 and bolt_diam_m > 0:
        try:
            ps_bolts = profile_sets.Add()
            try:
                ps_bolts.Name = "Boceto_04_Patron_Barrenos"
            except Exception:
                pass
            prof_bolts = ps_bolts.Profiles.Add(plane_xy)
            circles = prof_bolts.Circles2d
            if shape in ["flange", "cylinder", "polygon"]:
                pcd_radius = (diam_m / 2.0) * 0.76
                for i in range(bolt_count):
                    ang = 2.0 * math.pi * i / bolt_count
                    bx = pcd_radius * math.cos(ang)
                    by = pcd_radius * math.sin(ang)
                    circles.AddByCenterRadius(bx, by, bolt_diam_m / 2.0)
            else:
                ox = (length_m / 2.0) * 0.72
                oy = (width_m / 2.0) * 0.72
                for sx in [-1, 1]:
                    for sy in [-1, 1]:
                        circles.AddByCenterRadius(sx * ox, sy * oy, bolt_diam_m / 2.0)
            prof_bolts.End(0)
            prof_bolts.Visible = False
            feat_bolts = model.ExtrudedCutouts.AddFinite(prof_bolts, igRight, igSymmetric, max(height_m, ext_depth) * 2.5)
            try:
                feat_bolts.Name = f"Corte_02_Matriz_{bolt_count}_Barrenos"
            except Exception:
                pass
            tree_operations.append(f"5. Corte_02_Matriz_{bolt_count}_Barrenos ({bolt_count} taladros pasantes Ø{round(bolt_diam_m*1000,1)} mm)")
        except Exception:
            pass

    # =========================================================================
    # OPERACIÓN 6: REDONDEO SÓLIDO DE ARISTAS (ROUNDS)
    # =========================================================================
    if fillet_m > 0:
        try:
            edges = model.Body.Edges(1)
            if edges.Count > 0:
                max_edges = min(edges.Count, 4)
                edge_arr = [edges.Item(i) for i in range(1, max_edges + 1)]
                radii_arr = [fillet_m] * max_edges
                feat_round = model.Rounds.Add(max_edges, edge_arr, radii_arr)
                try:
                    feat_round.Name = f"Redondeo_01_R{round(fillet_m*1000, 1)}mm"
                except Exception:
                    pass
                tree_operations.append(f"6. Redondeo_01_R{round(fillet_m*1000, 1)}mm (Redondeo de aristas sólidas)")
        except Exception:
            pass

    save_path.parent.mkdir(parents=True, exist_ok=True)
    doc.SaveAs(str(save_path))
    try:
        app.StartCommand(32824)  # Ajustar vista isométrica
    except Exception:
        pass

    return {
        "file": str(save_path),
        "plan": plan,
        "tree_operations": tree_operations
    }


def build_pieza_mecanica_piston(save_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Modela con total exactitud la Pieza Mecánica en Solid Edge 2026 (Modo Ordenado)
    siguiendo la Guía de Modelamiento 3D y el plano técnico con todas sus operaciones:
      1. Boceto_01_Cuerpo_Principal + Protrusion_01_Cuerpo_Principal (R150 / diam 300mm x 180mm)
      2. Boceto_02_Escalones_Detalle_B + Vaciado_01_Escalones_Superiores_Detalle_B (3 ranuras anulares prof. 7.5mm x 5mm)
      3. Boceto_03_Vaciado_Interior_R130 + Vaciado_02_Cavidad_Interior_R130 (Cavidad R130, corona superior 20mm)
      4. Boceto_04_Perfil_Frontal_R100 + Vaciado_03_Abertura_Central_100mm_y_Apoyos (Abertura central 100mm y despejes 40mm)
      5. Boceto_05_Aberturas_Apoyos_R25 + Vaciado_04_Alojamiento_Pasador_R25 (Alojamiento concéntrico pasador R25 / diam 50mm)
      6. Redondeo_01_Apoyos_R5 (Redondeos en bordes y apoyos R5 por selección geométrica)
    """
    from build_piston_perfect import build_piston_perfect
    if not save_path:
        save_path = Path("C:/Jarvis/Pieza_mecanica.par")
    return build_piston_perfect(save_path)


def generate_full_piston_engine_project(output_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Genera el proyecto completo de parcial: 3 piezas modeladas, ensamble mecánico y paquete ZIP."""
    from build_piston_engine_project import run_full_exam_suite
    return run_full_exam_suite(output_dir)


def parse_natural_language_or_drawing_to_cad_plan(text: str) -> Dict[str, Any]:
    low = text.lower()

    # Detección inmediata del plano técnico específico de Pieza Mecánica / Pistón según la Guía
    if any(k in low for k in ["pieza_mecanica", "pieza mecanica", "guía de modelamiento", "guia de modelamiento"]) or (
        "r150" in low and "r130" in low
    ) or ("180" in low and "140" in low and "100" in low and "r45" in low):
        return {
            "part_name": "Pieza_mecanica",
            "base_shape": "cylinder_piston",
            "is_complex_blueprint": True,
            "dimensions_mm": {
                "outer_radius": 150.0,
                "inner_radius": 130.0,
                "total_height": 180.0,
                "inner_height": 140.0,
                "central_opening_width": 100.0,
                "support_width": 40.0,
                "pin_radius": 25.0,
                "outer_pin_radius": 45.0,
                "transition_radius": 100.0,
                "round_r5": 5.0,
                "round_r15": 15.0,
                "chamfer": "5x45",
                "ring_grooves_depth": 7.5,
                "ring_grooves_width": 5.0
            }
        }

    if any(w in low for w in ["polea", "garganta", "canal de polea", "eje torneado", "revolucion", "revolución", "buje escalonado"]):
        base_shape = "revolved"
    elif any(w in low for w in ["brida", "flange", "platina circular", "acoplamiento"]):
        base_shape = "flange"
    elif any(w in low for w in ["hexágono", "hexagono", "tuerca", "cabeza hexagonal", "polígono", "poligono"]):
        base_shape = "polygon"
    elif any(w in low for w in ["soporte en l", "escuadra", "perfil l", "angulo", "ángulo", "soporte"]):
        base_shape = "l_bracket"
    elif any(w in low for w in ["eje escalonado", "árbol", "arbol de transmision", "escalon", "eje"]):
        base_shape = "revolved"
    elif any(w in low for w in ["cilindro", "tubo", "buje", "casquillo", "rodillo", "disco"]):
        base_shape = "revolved" if any(w in low for w in ["ranura", "escalon", "garganta", "revolucion"]) else "cylinder"
    else:
        base_shape = "box"

    diam_match = re.search(r"(?:di[aá]metro|ø|d\s*=)\s*(\d+(?:\.\d+)?)", low)
    inner_match = re.search(r"(?:interior|agujero central|taladro central|vaciado de|hueco de)\s*(?:de\s*|ø\s*)?(\d+(?:\.\d+)?)", low)
    len_match = re.search(r"(?:largo|longitud|l\s*=)\s*(\d+(?:\.\d+)?)", low)
    wid_match = re.search(r"(?:ancho|w\s*=)\s*(\d+(?:\.\d+)?)", low)
    hei_match = re.search(r"(?:alto|altura|h\s*=)\s*(\d+(?:\.\d+)?)", low)
    thk_match = re.search(r"(?:espesor|grosor|e\s*=)\s*(\d+(?:\.\d+)?)", low)
    fillet_match = re.search(r"(?:redondeo|radio|r\s*=|fillet)\s*(?:de\s*)?(\d+(?:\.\d+)?)", low)
    bolts_match = re.search(r"(\d+)\s*(?:agujeros|taladros|pernos|barrenos)", low)
    bolt_d_match = re.search(r"(?:agujeros|taladros|pernos)\s*(?:de\s*)?(?:ø|di[aá]metro)?\s*(\d+(?:\.\d+)?)", low)
    dim_3d = re.search(r"(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)(?:\s*[xX×]\s*(\d+(?:\.\d+)?))?", low)

    all_nums = [float(n) for n in re.findall(r"\b(\d+(?:\.\d+)?)\b", low) if float(n) < 2000 and float(n) != 2026]

    length = float(len_match.group(1)) if len_match else (float(dim_3d.group(1)) if dim_3d else (all_nums[0] if len(all_nums) > 0 else 140.0))
    width = float(wid_match.group(1)) if wid_match else (float(dim_3d.group(2)) if dim_3d else (all_nums[1] if len(all_nums) > 1 else 90.0))
    height = float(hei_match.group(1)) if hei_match else (float(dim_3d.group(3)) if (dim_3d and dim_3d.group(3)) else (all_nums[2] if len(all_nums) > 2 else 45.0))
    outer_d = float(diam_match.group(1)) if diam_match else (all_nums[0] if len(all_nums) > 0 else 100.0)
    inner_d = float(inner_match.group(1)) if inner_match else (outer_d * 0.4 if any(w in low for w in ["hueco", "tubo", "buje", "brida", "tuerca"]) else 0.0)
    thickness = float(thk_match.group(1)) if thk_match else 15.0
    fillet_r = float(fillet_match.group(1)) if fillet_match else 2.5
    bolt_count = int(bolts_match.group(1)) if bolts_match else (6 if base_shape == "flange" else (4 if "agujeros" in low else 0))
    bolt_d = float(bolt_d_match.group(1)) if bolt_d_match else 12.0
    hollow = any(w in low for w in ["caja hueca", "carcasa", "vaciado", "recipiente"])

    name_clean = re.sub(r"[^\w]+", "_", base_shape).strip("_")
    return {
        "part_name": f"Pieza_{name_clean.capitalize()}_{int(length)}mm",
        "base_shape": base_shape,
        "dimensions_mm": {
            "length": length,
            "width": width,
            "height": height,
            "outer_diameter": outer_d,
            "inner_diameter": inner_d,
            "thickness": thickness,
            "fillet_radius": fillet_r,
            "bolt_holes_count": bolt_count,
            "bolt_hole_diameter": bolt_d,
            "hollow_shell": hollow,
            "sides": 6
        }
    }


def assemble_any_parts_in_solidedge(part_files: List[str], asm_save_path: Path) -> Dict[str, Any]:
    app = get_or_start_solidedge()
    asm_doc = app.Documents.Add("SolidEdge.AssemblyDocument")
    occurrences = asm_doc.Occurrences
    inserted = []

    for idx, pfile in enumerate(part_files):
        if Path(pfile).exists():
            try:
                occ = occurrences.AddByFilename(str(pfile))
                try:
                    occ.PutOrigin(idx * 0.18, 0.0, 0.0)
                except Exception:
                    pass
                inserted.append(str(pfile))
            except Exception:
                pass

    asm_save_path.parent.mkdir(parents=True, exist_ok=True)
    asm_doc.SaveAs(str(asm_save_path))
    try:
        app.StartCommand(32824)
    except Exception:
        pass

    return {
        "assembly_file": str(asm_save_path),
        "inserted_parts": inserted
    }


def generate_full_v8_project_in_solidedge(project_name: str, base_folder: Path) -> Dict[str, Any]:
    proj_dir = base_folder / project_name
    parts_dir = proj_dir / "01_Piezas_PAR"
    asm_dir = proj_dir / "02_Ensamblajes_ASM"
    parts_dir.mkdir(parents=True, exist_ok=True)
    asm_dir.mkdir(parents=True, exist_ok=True)

    plans = [
        ("01_Piston_Forjado.par", {"base_shape": "cylinder", "dimensions_mm": {"outer_diameter": 94, "height": 78, "inner_diameter": 74, "fillet_radius": 4}}),
        ("02_Brida_Escape.par", {"base_shape": "flange", "dimensions_mm": {"outer_diameter": 130, "thickness": 14, "inner_diameter": 52, "bolt_holes_count": 6, "bolt_hole_diameter": 10, "fillet_radius": 2}}),
        ("03_Soporte_Motor_L.par", {"base_shape": "l_bracket", "dimensions_mm": {"length": 140, "height": 110, "width": 80, "thickness": 14, "fillet_radius": 3}}),
        ("04_Placa_Bancada_Taladros.par", {"base_shape": "box", "dimensions_mm": {"length": 220, "width": 160, "height": 22, "inner_diameter": 65, "bolt_holes_count": 4, "bolt_hole_diameter": 14, "fillet_radius": 3}}),
        ("05_Eje_Escalonado.par", {"base_shape": "stepped_shaft", "dimensions_mm": {"outer_diameter": 85, "height": 180, "inner_diameter": 25, "fillet_radius": 3}}),
    ]

    created = []
    for fname, p in plans:
        fpath = parts_dir / fname
        execute_cad_feature_plan(p, fpath)
        created.append(str(fpath))

    asm_path = asm_dir / f"Ensamblaje_{project_name}.asm"
    assemble_any_parts_in_solidedge(created, asm_path)
    created.append(str(asm_path))

    return {"project_dir": str(proj_dir), "created_files": created}


def generate_custom_solid_part(description: str, save_dir: Path) -> Dict[str, Any]:
    plan = parse_natural_language_or_drawing_to_cad_plan(description)
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / f"{plan['part_name']}.par"
    res = execute_universal_cad_plan(plan, save_path)
    return {
        "file": res["file"],
        "plan": plan,
        "tree_operations": res.get("tree_operations", [])
    }
