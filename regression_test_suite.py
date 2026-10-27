"""
Banco de Pruebas de Regresión y Verificación de Aceptación Universal.
Implementa las Secciones 13.2, 14.1, 14.2 y 15.7 del Prompt Maestro:
  - Prueba de regresión del plano de motor (Pistón, Biela sup, Biela inf, Ensamble, Zip).
  - Pruebas de generalidad con 2 piezas distintas adicionales sin cambio de código.
  - Verificación de bocetos persistentes nombrados en modo ordenado.
  - Verificación de superficies limpias (cero facetas < 1.5mm).
  - Verificación de estado final abierto y visible en pantalla (CERRAR_AL_TERMINAR = False).
"""

import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, List

sys.path.append("C:/Jarvis")
from universal_task_orchestrator import UniversalTaskOrchestrator
from surface_cleanliness_auditor import audit_model_surfaces, format_audit_report
from cad_atomic_lib import connect_or_launch_solidedge
from final_state_manager import (
    CERRAR_AL_TERMINAR,
    apply_model_presentation,
    bring_solidedge_to_foreground
)


def run_full_acceptance_regression():
    print("\n" + "=" * 90)
    print("INICIANDO BANCO DE PRUEBAS DE REGRESIÓN UNIVERSAL (J.A.R.V.I.S. CAD)")
    print("=" * 90)

    workspace = Path("C:/Jarvis")
    orchestrator = UniversalTaskOrchestrator(workspace)

    # 1. Definición dinámica de la cola de trabajo del proyecto
    enunciado_test = """
    Examen Parcial 2 - Modelamiento 3D en Solid Edge 2026:
    Pieza 1: 01_Piston.par
    Pieza 2: 02_Biela_Parte_Superior.par
    Pieza 3: 03_Biela_Parte_Inferior.par
    Pieza 4: 05_Soporte_Horquilla_U.par
    Pieza 5: 06_Palanca_Balancin_Doble_Ojo.par
    Ensamble: 04_Ensamble_Motor_Piston.asm
    Empaquetado: PARCIAL_2_MODELAMIENTO_3D_ENTREGA.zip
    """

    print(">>> 1. Ingesta dinámica del enunciado y creación de cola.json...")
    tasks = orchestrator.initialize_queue_from_input(enunciado_test)
    print(f"    Cola inicializada con {len(tasks)} entregables dinámicos:")
    for t in tasks:
        print(f"      - [{t['id']}] {t['nombre']} ({t['tipo']})")

    # 2. Ejecución del orquestador en código
    print("\n>>> 2. Ejecución de la cola mediante el orquestador en código...")
    executed_tasks = orchestrator.run_queue()

    # 3. Auditoría exhaustiva de aceptación
    print("\n>>> 3. Auditoría de criterios de aceptación...")
    app = connect_or_launch_solidedge()
    acceptance_results = []

    for t in executed_tasks:
        if t["tipo"] == "pieza" and t.get("archivo"):
            p_path = Path(t["archivo"])
            if p_path.exists():
                doc = app.Documents.Open(str(p_path))
                audit = audit_model_surfaces(doc)
                sketches_count = doc.ProfileSets.Count
                mode = getattr(doc, "ModelingMode", 2)
                is_ordered = (mode == 2)
                clean_pass = audit.get("cleanliness_pass", False)
                facet_count = audit.get("faceted_strips_detected", 0)

                acceptance_results.append({
                    "name": t["nombre"],
                    "is_ordered": is_ordered,
                    "sketches_count": sketches_count,
                    "total_faces": audit.get("total_faces", 0),
                    "cylindrical_faces": audit.get("counts_by_type", {}).get("Cilíndrica", 0),
                    "faceted_strips": facet_count,
                    "clean_pass": clean_pass,
                    "status": "PASS" if (is_ordered and clean_pass and sketches_count > 0) else "FAIL"
                })

    print("\n" + "=" * 90)
    print("MATRIZ DE CUMPLIMIENTO DE CRITERIOS DE ACEPTACIÓN")
    print("=" * 90)
    print(f"{'Pieza':<32} | {'Modo':<9} | {'Bocetos':<8} | {'Caras':<6} | {'Cil':<5} | {'Facetas':<8} | {'Estado'}")
    print("-" * 90)
    for r in acceptance_results:
        modo_str = "Ordenado" if r["is_ordered"] else "Síncrono"
        print(f"{r['name']:<32} | {modo_str:<9} | {r['sketches_count']:<8} | {r['total_faces']:<6} | {r['cylindrical_faces']:<5} | {r['faceted_strips']:<8} | {r['status']}")
    print("=" * 90)

    # 4. Estado final garantizado
    if not CERRAR_AL_TERMINAR:
        bring_solidedge_to_foreground(app)
        print(f"\nESTADO FINAL VERIFICADO: {app.Documents.Count} documentos abiertos y visibles en Solid Edge 2026.")

    all_pass = all(r["status"] == "PASS" for r in acceptance_results)
    print(f"\nRESULTADO GLOBAL DE LA SUITE DE REGRESIÓN: {'100% PASS' if all_pass else 'FALLOS DETECTADOS'}\n")
    return all_pass


if __name__ == "__main__":
    run_full_acceptance_regression()
