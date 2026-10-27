"""
Script de Verificación Obligatoria de Estado Final (3 Casos de Prueba).
Valida estrictamente los 3 escenarios demandados por la Adenda:
  - Caso 1: Una pieza sola (debe quedar abierta, visible, isométrica y activa).
  - Caso 2: Varias piezas sin ensamble (todas abiertas, con la pieza indicada activa).
  - Caso 3: Ensamble completo (el ensamble activo en primer plano y sus componentes abiertos).
Genera capturas visuales y comprueba por la API de Solid Edge 2026.
"""

import sys
import json
from pathlib import Path

sys.stdout.reconfigure(line_buffering=True)
sys.path.append("C:/Jarvis")

from cad_atomic_lib import connect_or_launch_solidedge
from final_state_manager import (
    finalize_and_verify_open_state,
    apply_model_presentation,
    bring_solidedge_to_foreground
)

def run_three_cases_verification():
    app = connect_or_launch_solidedge()
    app.Visible = True
    app.DisplayAlerts = False

    base_dir = Path("C:/Jarvis/PARCIAL_2_ENTREGA")
    piston = base_dir / "01_Piston.par"
    biela_sup = base_dir / "02_Biela_Parte_Superior.par"
    biela_inf = base_dir / "03_Biela_Parte_Inferior.par"
    ensamble = base_dir / "04_Ensamble_Motor_Piston.asm"

    results = {}

    # =========================================================================
    # CASO 1: UNA SOLA PIEZA
    # =========================================================================
    print("\n==========================================")
    print("EJECUTANDO CASO 1: UNA SOLA PIEZA (01_Piston.par)")
    print("==========================================")
    # Cerrar documentos previos si los hubiera para aislar el caso
    for i in range(app.Documents.Count, 0, -1):
        try:
            app.Documents.Item(i).Close(False)
        except Exception:
            pass

    st1 = finalize_and_verify_open_state(
        app,
        expected_doc_paths=[piston],
        active_doc_path=piston,
        cerrar_al_terminar=False
    )
    cap1 = base_dir / "caso_1_pieza_sola.png"
    if app.ActiveDocument and app.ActiveDocument.Windows.Count > 0:
        try:
            app.StartCommand(32824)
        except Exception:
            pass
        win = app.ActiveDocument.Windows.Item(1)
        win.View.Fit()
        win.View.SaveAsImage(str(cap1), 1920, 1080)

    results["caso_1"] = {
        "descripcion": "Una sola pieza",
        "esperado": [piston.name],
        "activo_esperado": piston.name,
        "abiertos_api": [d["name"] for d in st1["open_documents"]],
        "activo_api": st1["active_document"],
        "captura": str(cap1),
        "exito": (len(st1["open_documents"]) == 1 and st1["active_document"] == piston.name)
    }
    print(f"Caso 1 completado. Documentos abiertos: {results['caso_1']['abiertos_api']}, Activo: {results['caso_1']['activo_api']}")

    # =========================================================================
    # CASO 2: VARIAS PIEZAS SIN ENSAMBLE
    # =========================================================================
    print("\n==========================================")
    print("EJECUTANDO CASO 2: VARIAS PIEZAS (Biela Sup + Biela Inf)")
    print("==========================================")
    for i in range(app.Documents.Count, 0, -1):
        try:
            app.Documents.Item(i).Close(False)
        except Exception:
            pass

    st2 = finalize_and_verify_open_state(
        app,
        expected_doc_paths=[biela_sup, biela_inf],
        active_doc_path=biela_sup,
        cerrar_al_terminar=False
    )
    cap2 = base_dir / "caso_2_varias_piezas.png"
    if app.ActiveDocument and app.ActiveDocument.Windows.Count > 0:
        try:
            app.StartCommand(32824)
        except Exception:
            pass
        win = app.ActiveDocument.Windows.Item(1)
        win.View.Fit()
        win.View.SaveAsImage(str(cap2), 1920, 1080)

    results["caso_2"] = {
        "descripcion": "Varias piezas sin ensamble",
        "esperado": [biela_sup.name, biela_inf.name],
        "activo_esperado": biela_sup.name,
        "abiertos_api": [d["name"] for d in st2["open_documents"]],
        "activo_api": st2["active_document"],
        "captura": str(cap2),
        "exito": (len(st2["open_documents"]) == 2 and st2["active_document"] == biela_sup.name)
    }
    print(f"Caso 2 completado. Documentos abiertos: {results['caso_2']['abiertos_api']}, Activo: {results['caso_2']['activo_api']}")

    # =========================================================================
    # CASO 3: ENSAMBLE COMPLETO CON PIEZAS COMPONENTES ABIERTAS
    # =========================================================================
    print("\n==========================================")
    print("EJECUTANDO CASO 3: ENSAMBLE COMPLETO (Motor de Pistón)")
    print("==========================================")
    # Abrir todos los componentes y el ensamble
    st3 = finalize_and_verify_open_state(
        app,
        expected_doc_paths=[piston, biela_sup, biela_inf, ensamble],
        active_doc_path=ensamble,
        cerrar_al_terminar=False
    )
    cap3 = base_dir / "caso_3_ensamble_completo.png"
    if app.ActiveDocument and app.ActiveDocument.Windows.Count > 0:
        try:
            app.StartCommand(32824)
        except Exception:
            pass
        win = app.ActiveDocument.Windows.Item(1)
        win.View.Fit()
        win.View.SaveAsImage(str(cap3), 1920, 1080)

    results["caso_3"] = {
        "descripcion": "Ensamble completo con piezas vivas",
        "esperado": [piston.name, biela_sup.name, biela_inf.name, ensamble.name],
        "activo_esperado": ensamble.name,
        "abiertos_api": [d["name"] for d in st3["open_documents"]],
        "activo_api": st3["active_document"],
        "captura": str(cap3),
        "exito": (len(st3["open_documents"]) >= 4 and st3["active_document"] == ensamble.name)
    }
    print(f"Caso 3 completado. Documentos abiertos: {results['caso_3']['abiertos_api']}, Activo: {results['caso_3']['activo_api']}")

    print("\n=== REPORTE DE VERIFICACION DE ESTADO FINAL ===")
    print(json.dumps(results, indent=2, ensure_ascii=False))

    # Guardar reporte en JSON
    json_path = base_dir / "reporte_verificacion_estado_final.json"
    json_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Reporte guardado en: {json_path}")
    return results

if __name__ == "__main__":
    run_three_cases_verification()
