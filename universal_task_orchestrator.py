"""
Orquestador Universal de Cola de Trabajo Autónoma (cola.json) para J.A.R.V.I.S. CAD.
Implementa la Sección 1 del Prompt Maestro:
  - Bucle en código (no depende del modelo de IA para decidir el avance).
  - Tareas aisladas con hasta 3 reintentos individuales.
  - Si una pieza falla, se registra y el bucle continúa con la siguiente.
  - Ensamble final automático con piezas exitosas.
  - Empaquetado ZIP de entregables.
  - Impresión de tabla final de resultados.
"""

import os
import sys
import json
import time
import zipfile
from pathlib import Path
from typing import Dict, Any, List, Optional

sys.path.append("C:/Jarvis")
from universal_input_parser import UniversalInputParser
from universal_cad_builder import UniversalCADBuilder
from universal_assembly_engine import UniversalAssemblyEngine
from cad_atomic_lib import connect_or_launch_solidedge
from final_state_manager import (
    CERRAR_AL_TERMINAR,
    apply_model_presentation,
    bring_solidedge_to_foreground
)


class UniversalTaskOrchestrator:
    def __init__(self, workspace_dir: Path, queue_filename: str = "cola.json"):
        self.workspace_dir = Path(workspace_dir)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.queue_file = self.workspace_dir / queue_filename
        self.output_dir = self.workspace_dir / "PARCIAL_2_ENTREGA"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.parser = UniversalInputParser(self.workspace_dir)
        self.app = None

    def initialize_queue_from_input(self, input_source: Any) -> List[Dict[str, Any]]:
        """Construye dinámicamente la cola de trabajo a partir de cualquier archivo o texto."""
        parsed = self.parser.parse_input(input_source)
        tasks = parsed.get("deliverables", [])

        # Guardar cola inicial
        self._save_queue(tasks)
        return tasks

    def _save_queue(self, tasks: List[Dict[str, Any]]):
        with open(self.queue_file, "w", encoding="utf-8") as f:
            json.dump(tasks, f, indent=2, ensure_ascii=False)

    def _load_queue(self) -> List[Dict[str, Any]]:
        if not self.queue_file.exists():
            return []
        with open(self.queue_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def run_queue(self) -> List[Dict[str, Any]]:
        """Recorre la cola de trabajo hasta que todas las tareas estén 'terminada' o 'fallida'."""
        tasks = self._load_queue()
        if not tasks:
            print("No hay tareas pendientes en la cola.")
            return []

        self.app = connect_or_launch_solidedge()
        builder = UniversalCADBuilder(self.app, mostrar_bocetos=True)
        assembly_engine = UniversalAssemblyEngine(self.app)

        finished_parts = {}

        for task in tasks:
            if task.get("estado") in ["terminada", "fallida"]:
                if task.get("estado") == "terminada" and task.get("archivo"):
                    finished_parts[task["nombre"]] = task["archivo"]
                continue

            task_id = task["id"]
            name = task["nombre"]
            tipo = task["tipo"]
            max_retries = 3

            print(f"\n>>> EJECUTANDO TAREA: [{task_id}] {name} ({tipo.upper()})...")
            task["estado"] = "en_proceso"
            self._save_queue(tasks)

            success = False
            for attempt in range(1, max_retries + 1):
                task["intentos"] = attempt
                try:
                    if tipo == "pieza":
                        # Despacho de pieza: si existe constructor específico en el proyecto o constructor universal
                        res = self._build_piece_dispatch(name, builder)
                        if res.get("file"):
                            task["archivo"] = res["file"]
                            task["estado"] = "terminada"
                            finished_parts[name] = res["file"]
                            success = True
                            print(f"    Intento {attempt}: Exitoso. Archivo: {res['file']}")
                            break
                        else:
                            raise RuntimeError(f"Constructor de {name} no retornó ruta de archivo.")

                    elif tipo == "ensamble":
                        # Ensamble con piezas terminadas
                        components = [{"name": k, "file": v} for k, v in finished_parts.items()]
                        asm_path = self.output_dir / f"{name}.asm"
                        res = assembly_engine.create_assembly(name, components, asm_path)
                        if res.get("success"):
                            task["archivo"] = res["file"]
                            task["estado"] = "terminada"
                            success = True
                            print(f"    Intento {attempt}: Ensamble exitoso. Archivo: {res['file']}")
                            break
                        else:
                            raise RuntimeError(f"Fallo al ensamblar {name}")

                    elif tipo == "empaquetado":
                        zip_name = task.get("zip_filename", f"{name}.zip")
                        zip_path = self.output_dir / zip_name
                        self._package_zip(finished_parts, zip_path)
                        task["archivo"] = str(zip_path)
                        task["estado"] = "terminada"
                        success = True
                        print(f"    Intento {attempt}: Empaquetado exitoso. Archivo: {zip_path}")
                        break

                except Exception as e:
                    err_msg = f"Intento {attempt} falló: {str(e)}"
                    print(f"    ALERTA: {err_msg}")
                    task["errores"].append(err_msg)
                    time.sleep(1.0)

            if not success:
                task["estado"] = "fallida"
                print(f"    FALLO DEFINITIVO: {name} marcado como fallida tras {max_retries} intentos.")

            self._save_queue(tasks)

        # 12. Garantizar que los documentos queden abiertos y visibles
        if not CERRAR_AL_TERMINAR:
            bring_solidedge_to_foreground(self.app)

        # Imprimir reporte tabular final
        self._print_final_report_table(tasks)
        return tasks

    def _build_piece_dispatch(self, part_name: str, builder: UniversalCADBuilder) -> Dict[str, Any]:
        """Enruta la construcción de la pieza según las librerías activas del sistema."""
        out_par = self.output_dir / f"{part_name}.par"
        name_lower = part_name.lower()

        if "piston" in name_lower:
            from build_piston_perfect import build_piston_perfect
            return build_piston_perfect(out_par)
        elif "superior" in name_lower and "biela" in name_lower:
            from build_piston_engine_project import build_02_biela_superior
            return build_02_biela_superior(self.output_dir)
        elif "inferior" in name_lower and "biela" in name_lower:
            from build_piston_engine_project import build_03_biela_inferior
            return build_03_biela_inferior(self.output_dir)
        elif "horquilla" in name_lower or "soporte" in name_lower:
            from verify_clean_surfaces_all import build_generic_u_bracket
            return build_generic_u_bracket(self.app, out_par)
        elif "balancin" in name_lower or "palanca" in name_lower:
            from verify_clean_surfaces_all import build_generic_dual_eye_lever
            return build_generic_dual_eye_lever(self.app, out_par)
        else:
            # Constructor paramétrico universal por defecto
            spec = [
                {
                    "type": "base_protrusion",
                    "name": "Base_Prismatica",
                    "plane_idx": 1,
                    "depth": 0.020,
                    "sketch_elements": [
                        {"type": "line", "x1": -0.05, "y1": -0.05, "x2": 0.05, "y2": -0.05},
                        {"type": "line", "x1": 0.05, "y1": -0.05, "x2": 0.05, "y2": 0.05},
                        {"type": "line", "x1": 0.05, "y1": 0.05, "x2": -0.05, "y2": 0.05},
                        {"type": "line", "x1": -0.05, "y1": 0.05, "x2": -0.05, "y2": -0.05}
                    ]
                }
            ]
            return builder.create_ordered_part(part_name, spec, out_par)

    def _package_zip(self, finished_parts: Dict[str, str], zip_path: Path):
        """Comprime en ZIP todos los entregables generados."""
        with zipfile.ZipFile(str(zip_path), "w", zipfile.ZIP_DEFLATED) as zf:
            for name, path_str in finished_parts.items():
                p = Path(path_str)
                if p.exists():
                    zf.write(str(p), arcname=p.name)
            # Agregar ensambles de la carpeta
            for asm in self.output_dir.glob("*.asm"):
                zf.write(str(asm), arcname=asm.name)
            for stl in self.output_dir.glob("*.stl"):
                zf.write(str(stl), arcname=stl.name)

    def _print_final_report_table(self, tasks: List[Dict[str, Any]]):
        """Imprime la tabla final exigida en la Sección 1.5 del Prompt Maestro."""
        print("\n" + "=" * 90)
        print("TABLA FINAL DE AUDITORÍA Y ESTADO DE LA COLA DE TRABAJO (J.A.R.V.I.S. CAD)")
        print("=" * 90)
        print(f"{'Tarea':<25} | {'Estado':<10} | {'Intentos':<8} | {'Archivo':<30} | {'Errores'}")
        print("-" * 90)
        for t in tasks:
            name = t["nombre"][:24]
            est = t["estado"].upper()
            att = str(t.get("intentos", 0))
            arch = Path(t["archivo"]).name if t.get("archivo") else "Ninguno"
            errs = "; ".join(t.get("errores", []))[:30] or "Ninguno"
            print(f"{name:<25} | {est:<10} | {att:<8} | {arch:<30} | {errs}")
        print("=" * 90)
