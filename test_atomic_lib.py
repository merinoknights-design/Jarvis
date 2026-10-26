"""
Suite de Pruebas Unitarias para la Librería Atómica CAD (cad_atomic_lib.py).
Valida las primitivas de modelado paso a paso ANTES de procesar los planos de ingeniería:
  1. Bloque con agujero pasante y redondeos en aristas.
  2. Pieza cilíndrica de revolución con ranura anular.
  3. Bloque con vaciado extruido simétrico.
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
    add_circle,
    close_profile_keypoints,
    create_base_protrusion,
    add_extruded_cutout,
    add_revolved_cutout,
    verify_feature_status,
    apply_fillets_geometric,
    get_model_physical_properties,
    igRight,
    igSymmetric
)


def run_unit_tests():
    app = connect_or_launch_solidedge()
    test_results = []
    out_dir = Path("C:/Jarvis/atomic_tests")
    out_dir.mkdir(parents=True, exist_ok=True)

    print("\n=======================================================")
    print("EJECUTANDO BATERÍA DE PRUEBAS DE LA LIBRERÍA ATÓMICA")
    print("=======================================================")

    # -----------------------------------------------------------------
    # PRUEBA 1: BLOQUE CON AGUJERO Y REDONDEOS
    # -----------------------------------------------------------------
    print("\n[TEST 1/3] Bloque prismático 100x80x30mm con taladro Ø25mm y redondeos R3...")
    doc1 = create_part_doc(app)
    try:
        ps, prof = add_sketch_profile(doc1, 1, "Boceto_Bloque")
        l1 = add_line(prof, -0.050, -0.040, 0.050, -0.040)
        l2 = add_line(prof, 0.050, -0.040, 0.050, 0.040)
        l3 = add_line(prof, 0.050, 0.040, -0.050, 0.040)
        l4 = add_line(prof, -0.050, 0.040, -0.050, -0.040)
        close_profile_keypoints(prof, [l1, l2, l3, l4])
        model1 = create_base_protrusion(doc1, prof, 0.030)
        ok1, st1, nm1 = verify_feature_status(model1, "Protrusion_Base")
        assert ok1, f"Fallo al crear protrusión base (Status={st1})"

        # Añadir taladro central Ø25mm
        ps_h, prof_h = add_sketch_profile(doc1, 1, "Boceto_Taladro")
        add_circle(prof_h, 0.0, 0.0, 0.0125)
        add_extruded_cutout(model1, prof_h, 0.040)
        ok2, st2, nm2 = verify_feature_status(model1, "Taladro_Central")
        assert ok2, f"Fallo al cortar taladro (Status={st2})"

        # Aplicar redondeos R3
        def top_filter(edges):
            res = []
            for i in range(1, min(edges.Count + 1, 8)):
                res.append(edges.Item(i))
            return res
        f_ok, count_r = apply_fillets_geometric(model1, top_filter, 0.003)

        props1 = get_model_physical_properties(model1)
        doc1.SaveAs(str(out_dir / "Prueba_01_Bloque_Agujero.par"))
        doc1.Close(False)
        print(f"  -> TEST 1 PASADO CON ÉXITO: {props1['volume_cm3']} cm3, {count_r} aristas redondeadas.")
        test_results.append(("Test 1: Bloque + Agujero + R3", "PASADO", f"{props1['volume_cm3']} cm3"))
    except Exception as e:
        doc1.Close(False)
        print(f"  -> TEST 1 FALLIDO: {e}")
        test_results.append(("Test 1: Bloque + Agujero + R3", "FALLIDO", str(e)))

    # -----------------------------------------------------------------
    # PRUEBA 2: PIEZA DE REVOLUCIÓN CON RANURA ANULAR
    # -----------------------------------------------------------------
    print("\n[TEST 2/3] Cilindro Ø60x80mm con ranura anular por corte de revolución...")
    doc2 = create_part_doc(app)
    try:
        ps2, prof2 = add_sketch_profile(doc2, 1, "Boceto_Cilindro")
        add_circle(prof2, 0.0, 0.0, 0.030)  # R30 = Ø60
        model2 = create_base_protrusion(doc2, prof2, 0.080)
        ok_cyl, _, _ = verify_feature_status(model2, "Cilindro_Base")
        assert ok_cyl, "Fallo al crear cilindro base"

        # Corte por revolución en plano XZ
        ps_r, prof_r = add_sketch_profile(doc2, 3, "Boceto_Ranura_Revolucion")
        axis = add_line(prof_r, 0.0, 0.0, 0.0, 0.100)
        # Ranura: prof. 5mm x ancho 6mm en Z=0.030 a Z=0.036
        rl1 = add_line(prof_r, 0.025, 0.030, 0.031, 0.030)
        rl2 = add_line(prof_r, 0.031, 0.030, 0.031, 0.036)
        rl3 = add_line(prof_r, 0.031, 0.036, 0.025, 0.036)
        rl4 = add_line(prof_r, 0.025, 0.036, 0.025, 0.030)
        close_profile_keypoints(prof_r, [rl1, rl2, rl3, rl4])
        add_revolved_cutout(model2, prof_r, axis)
        ok_rev, _, _ = verify_feature_status(model2, "Ranura_Revolucion")
        assert ok_rev, "Fallo al realizar vaciado por revolución"

        props2 = get_model_physical_properties(model2)
        doc2.SaveAs(str(out_dir / "Prueba_02_Revolucion_Ranura.par"))
        doc2.Close(False)
        print(f"  -> TEST 2 PASADO CON ÉXITO: {props2['volume_cm3']} cm3.")
        test_results.append(("Test 2: Revolución + Ranura Anular", "PASADO", f"{props2['volume_cm3']} cm3"))
    except Exception as e:
        doc2.Close(False)
        print(f"  -> TEST 2 FALLIDO: {e}")
        test_results.append(("Test 2: Revolución + Ranura Anular", "FALLIDO", str(e)))

    # -----------------------------------------------------------------
    # PRUEBA 3: BLOQUE CON VACIADO SIMÉTRICO
    # -----------------------------------------------------------------
    print("\n[TEST 3/3] Bloque con vaciado simétrico transversal...")
    doc3 = create_part_doc(app)
    try:
        ps3, prof3 = add_sketch_profile(doc3, 1, "Boceto_Base_Simetrica")
        add_circle(prof3, 0.0, 0.0, 0.050)
        model3 = create_base_protrusion(doc3, prof3, 0.060)

        # Vaciado rectangular simétrico a través de plano XZ
        ps_s, prof_s = add_sketch_profile(doc3, 3, "Boceto_Corte_Simetrico")
        sl1 = add_line(prof_s, -0.020, 0.020, 0.020, 0.020)
        sl2 = add_line(prof_s, 0.020, 0.020, 0.020, 0.040)
        sl3 = add_line(prof_s, 0.020, 0.040, -0.020, 0.040)
        sl4 = add_line(prof_s, -0.020, 0.040, -0.020, 0.020)
        close_profile_keypoints(prof_s, [sl1, sl2, sl3, sl4])
        add_extruded_cutout(model3, prof_s, 0.120, igRight, igSymmetric)
        ok_sym, _, _ = verify_feature_status(model3, "Corte_Simetrico")
        assert ok_sym, "Fallo al realizar vaciado simétrico"

        props3 = get_model_physical_properties(model3)
        doc3.SaveAs(str(out_dir / "Prueba_03_Corte_Simetrico.par"))
        doc3.Close(False)
        print(f"  -> TEST 3 PASADO CON ÉXITO: {props3['volume_cm3']} cm3.")
        test_results.append(("Test 3: Vaciado Simétrico", "PASADO", f"{props3['volume_cm3']} cm3"))
    except Exception as e:
        doc3.Close(False)
        print(f"  -> TEST 3 FALLIDO: {e}")
        test_results.append(("Test 3: Vaciado Simétrico", "FALLIDO", str(e)))

    print("\n=======================================================")
    print("RESUMEN DE PRUEBAS DE LIBRERÍA ATÓMICA:")
    all_passed = True
    for name, status, detail in test_results:
        print(f"  • {name:35} | {status:8} | {detail}")
        if status != "PASADO":
            all_passed = False
    print("=======================================================\n")
    return all_passed


if __name__ == "__main__":
    ok = run_unit_tests()
    sys.exit(0 if ok else 1)
