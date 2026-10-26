"""
Orquestador de Cola de Trabajo Autónoma y Resiliente (cola.json).
Resuelve el FALLO 3:
  - Bucle de control 100% en código (no depende de la IA para avanzar).
  - Tareas aisladas en cola: pendiente -> en_proceso -> terminada / fallida.
  - Reintentos individuales (hasta 3) con reporte exacto de error.
  - Si una pieza falla, el bucle NO se detiene y continúa con la siguiente.
  - El ensamble se genera automáticamente con las piezas terminadas con éxito.
  - Al finalizar, genera e imprime la tabla final de auditoría.
"""

import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import json
import time
from pathlib import Path
from typing import Dict, Any, List

from view_reader_and_checker import (
    crop_views_from_sheet,
    dual_read_and_build_cota_table,
    validate_piece_geometric_consistency,
    generate_2d_verification_preview
)
from cad_atomic_lib import connect_or_launch_solidedge
from build_piston_engine_project import (
    build_01_piston,
    build_02_biela_superior,
    build_03_biela_inferior,
    build_04_ensamble_motor,
    package_exam_zip
)


class TaskQueueOrchestrator:
    def __init__(self, workspace_dir: Path, queue_file_name: str = "cola.json"):
        self.workspace_dir = Path(workspace_dir)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.queue_file = self.workspace_dir / queue_file_name
        self.crops_dir = self.workspace_dir / "crops"
        self.crops_dir.mkdir(parents=True, exist_ok=True)

    def initialize_queue(self, pdf_extracted_images_dir: Path) -> List[Dict[str, Any]]:
        """Construye la lista inicial de tareas en cola.json a partir de las láminas identificadas."""
        tasks = [
            {
                "id": "tarea_01",
                "nombre": "01_Piston",
                "tipo": "pieza",
                "descripcion": "Pistón de Motor (1.5 Puntos)",
                "pagina_pdf": 2,
                "imagen_referencia": str(pdf_extracted_images_dir / "page_2_img_4_Image36.png"),
                "estado": "pendiente",
                "intentos": 0,
                "archivo": None,
                "errores": []
            },
            {
                "id": "tarea_02",
                "nombre": "02_Biela_Parte_Superior",
                "tipo": "pieza",
                "descripcion": "Biela Parte Superior (1.5 Puntos)",
                "pagina_pdf": 3,
                "imagen_referencia": str(pdf_extracted_images_dir / "page_3_img_3_Image41.png"),
                "estado": "pendiente",
                "intentos": 0,
                "archivo": None,
                "errores": []
            },
            {
                "id": "tarea_03",
                "nombre": "03_Biela_Parte_Inferior",
                "tipo": "pieza",
                "descripcion": "Biela Parte Inferior / Sombrerete (1.0 Punto)",
                "pagina_pdf": 4,
                "imagen_referencia": str(pdf_extracted_images_dir / "page_4_img_3_Image46.png"),
                "estado": "pendiente",
                "intentos": 0,
                "archivo": None,
                "errores": []
            },
            {
                "id": "tarea_04",
                "nombre": "04_Ensamble_Motor_Piston",
                "tipo": "ensamble",
                "descripcion": "Ensamble Mecánico y Relaciones Cinemáticas (1.0 Punto)",
                "pagina_pdf": 5,
                "imagen_referencia": str(pdf_extracted_images_dir / "page_5_img_2_Image50.jpg"),
                "estado": "pendiente",
                "intentos": 0,
                "archivo": None,
                "errores": []
            },
            {
                "id": "tarea_05",
                "nombre": "05_Empaquetado_Zip",
                "tipo": "empaquetado",
                "descripcion": "Compresión final de archivos .par, .asm y .step en ZIP",
                "pagina_pdf": 1,
                "imagen_referencia": None,
                "estado": "pendiente",
                "intentos": 0,
                "archivo": None,
                "errores": []
            }
        ]
        self.save_queue(tasks)
        return tasks

    def load_queue(self) -> List[Dict[str, Any]]:
        if self.queue_file.exists():
            return json.loads(self.queue_file.read_text(encoding="utf-8"))
        return []

    def save_queue(self, tasks: List[Dict[str, Any]]):
        self.queue_file.write_text(json.dumps(tasks, indent=2, ensure_ascii=False), encoding="utf-8")

    def run_orchestration_loop(self) -> Dict[str, Any]:
        """Bucle estricto en código que procesa la cola hasta que no queden tareas pendientes."""
        tasks = self.load_queue()
        completed_parts = {}

        print("\n=======================================================")
        print("INICIANDO ORQUESTADOR DE COLA AUTÓNOMA (cola.json)")
        print("=======================================================")

        while True:
            # Buscar la siguiente tarea pendiente o en proceso
            current_task = None
            for t in tasks:
                if t["estado"] in ["pendiente", "en_proceso"]:
                    current_task = t
                    break

            if current_task is None:
                # No quedan tareas pendientes, bucle completado
                break

            task_id = current_task["id"]
            name = current_task["nombre"]
            t_type = current_task["tipo"]
            current_task["estado"] = "en_proceso"
            self.save_queue(tasks)

            print(f"\n>>> PROCESANDO TAREA: {name} (Tipo: {t_type})")

            # Paso 1: Si es pieza y tiene plano, realizar segmentación, doble lectura y preview 2D
            ref_img = current_task.get("imagen_referencia")
            if ref_img and Path(ref_img).exists() and t_type == "pieza":
                try:
                    views = crop_views_from_sheet(Path(ref_img), self.crops_dir, name)
                    c_table = dual_read_and_build_cota_table(views)
                    validate_piece_geometric_consistency(name, c_table)
                    prev_path = self.crops_dir / f"preview_2d_{name}.png"
                    generate_2d_verification_preview(name, prev_path)
                    print(f"  [FALLO 2 RESUELTO] Segmentadas {len(views)} vistas y generada preview 2D: {prev_path.name}")
                except Exception as e:
                    print(f"  [Aviso en preanálisis 2D]: {e}")

            # Paso 2: Ejecución aislada con hasta 3 reintentos
            success = False
            while current_task["intentos"] < 3 and not success:
                current_task["intentos"] += 1
                attempt_num = current_task["intentos"]
                try:
                    print(f"  -> Ejecutando intento {attempt_num}/3 para {name}...")
                    if name == "01_Piston":
                        res = build_01_piston(self.workspace_dir)
                        current_task["archivo"] = res["file"]
                        completed_parts["01_Piston"] = res["file"]
                        success = True
                    elif name == "02_Biela_Parte_Superior":
                        res = build_02_biela_superior(self.workspace_dir)
                        current_task["archivo"] = res["file"]
                        completed_parts["02_Biela_Parte_Superior"] = res["file"]
                        success = True
                    elif name == "03_Biela_Parte_Inferior":
                        res = build_03_biela_inferior(self.workspace_dir)
                        current_task["archivo"] = res["file"]
                        completed_parts["03_Biela_Parte_Inferior"] = res["file"]
                        success = True
                    elif name == "04_Ensamble_Motor_Piston":
                        res = build_04_ensamble_motor(completed_parts, self.workspace_dir)
                        current_task["archivo"] = res["assembly_file"]
                        success = True
                    elif name == "05_Empaquetado_Zip":
                        zip_file = package_exam_zip(self.workspace_dir)
                        current_task["archivo"] = str(zip_file)
                        success = True

                except Exception as e:
                    err_msg = f"Error en intento {attempt_num}: {e}"
                    print(f"  [!] {err_msg}")
                    current_task["errores"].append(err_msg)
                    time.sleep(1.0)

            # Actualizar estado final de la tarea
            if success:
                current_task["estado"] = "terminada"
                print(f"  [OK] TAREA COMPLETADA CON ÉXITO: {current_task['archivo']}")
            else:
                current_task["estado"] = "fallida"
                print(f"  [X] TAREA MARCADA COMO FALLIDA TRAS 3 INTENTOS. Pasando a la siguiente...")

            self.save_queue(tasks)

        # Generar Tabla Final de Auditoría
        print("\n=======================================================")
        print("TABLA FINAL DE ESTADO DE LA COLA DE TRABAJO (cola.json):")
        print(f"{'Tarea':26} | {'Estado':10} | {'Intentos':8} | {'Archivo':32} | {'Errores'}")
        print("-" * 95)
        for t in tasks:
            f_name = Path(t['archivo']).name if t.get('archivo') else "Ninguno"
            err_count = len(t.get('errores', []))
            print(f"{t['nombre']:26} | {t['estado']:10} | {t['intentos']:8} | {f_name:32} | {err_count} errores")
        print("=======================================================\n")

        return {"tasks": tasks, "queue_file": str(self.queue_file)}


if __name__ == "__main__":
    orch = TaskQueueOrchestrator(
        workspace_dir=Path("C:/Jarvis/queue_workspace"),
        queue_file_name="cola.json"
    )
    orch.initialize_queue(Path("C:/Jarvis/uploads/pdf_extracted_images"))
    orch.run_orchestration_loop()
