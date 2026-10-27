"""
Módulo de Procesamiento e Ingesta Universal de Entradas para J.A.R.V.I.S. CAD Suite.
Soporta:
  1. PDF: Extracción vectorial de líneas y cotas (fuente primaria) + rasterizado a 300 DPI.
  2. DOCX: Extracción de texto estructurado, tablas de cotas e imágenes incrustadas.
  3. PNG/JPG: Procesamiento en alta resolución y segmentación de vistas.
  4. STEP, STL, DXF, PAR, ASM: Identificación de geometría CAD previa.
  5. Texto y enunciados: Extracción dinámica de lista de entregables sin valores cableados.
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from PIL import Image

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    import docx
except ImportError:
    docx = None


class UniversalInputParser:
    def __init__(self, workspace_dir: Path):
        self.workspace_dir = Path(workspace_dir)
        self.crops_dir = self.workspace_dir / "crops"
        self.crops_dir.mkdir(parents=True, exist_ok=True)

    def parse_input(self, input_path_or_text: Any) -> Dict[str, Any]:
        """Clasifica y procesa cualquier entrada entregando especificaciones estructuradas."""
        if isinstance(input_path_or_text, (str, Path)) and Path(str(input_path_or_text)).exists():
            path = Path(str(input_path_or_text))
            ext = path.suffix.lower()
            if ext == ".pdf":
                return self._parse_pdf(path)
            elif ext in [".docx", ".doc"]:
                return self._parse_docx(path)
            elif ext in [".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"]:
                return self._parse_image(path)
            elif ext in [".step", ".stp", ".stl", ".dxf", ".par", ".asm"]:
                return self._parse_cad_file(path)
            elif ext in [".txt", ".json", ".md"]:
                text = path.read_text(encoding="utf-8", errors="replace")
                return self._parse_text_description(text, source_file=path)
        
        # Si es texto directo
        return self._parse_text_description(str(input_path_or_text))

    def _parse_pdf(self, pdf_path: Path) -> Dict[str, Any]:
        """Procesa un archivo PDF extrayendo vectores, texto y rasterizado de alta resolución."""
        if fitz is None:
            return {"error": "PyMuPDF (fitz) no disponible", "type": "pdf", "file": str(pdf_path)}

        doc = fitz.open(str(pdf_path))
        pages_data = []
        all_text = []
        extracted_images = []

        for page_idx in range(len(doc)):
            page = doc[page_idx]
            page_text = page.get_text()
            all_text.append(page_text)

            # 1. Geometría vectorial primaria
            vector_drawings = []
            try:
                drawings = page.get_drawings()
                for d in drawings:
                    for item in d.get("items", []):
                        vector_drawings.append(item)
            except Exception:
                pass

            # 2. Rasterizado de alta resolución (300 DPI) para inspección visual y OCR
            pix = page.get_pixmap(dpi=300)
            img_path = self.crops_dir / f"{pdf_path.stem}_pag_{page_idx + 1}.png"
            pix.save(str(img_path))
            extracted_images.append(img_path)

            pages_data.append({
                "page_num": page_idx + 1,
                "text": page_text,
                "vector_elements_count": len(vector_drawings),
                "rendered_image": str(img_path)
            })

        full_text = "\n".join(all_text)
        deliverables = self._extract_deliverables_from_text(full_text, default_images=extracted_images)

        return {
            "type": "pdf",
            "file": str(pdf_path),
            "pages_count": len(doc),
            "pages": pages_data,
            "full_text": full_text,
            "extracted_images": [str(p) for p in extracted_images],
            "deliverables": deliverables,
            "confidence": "Alta" if any(p["vector_elements_count"] > 10 for p in pages_data) else "Media"
        }

    def _parse_docx(self, docx_path: Path) -> Dict[str, Any]:
        """Procesa documentos DOCX extrayendo texto, tablas de cotas e imágenes incrustadas."""
        if docx is None:
            return {"error": "python-docx no disponible", "type": "docx", "file": str(docx_path)}

        doc = docx.Document(str(docx_path))
        text_lines = [p.text for p in doc.paragraphs if p.text.strip()]
        full_text = "\n".join(text_lines)

        # Tablas de cotas o especificaciones
        tables_data = []
        for t_idx, table in enumerate(doc.tables):
            t_rows = []
            for row in table.rows:
                t_rows.append([cell.text.strip() for cell in row.cells])
            tables_data.append({"table_idx": t_idx + 1, "rows": t_rows})

        # Extracción de imágenes incrustadas
        embedded_images = []
        for rel in doc.part.rels.values():
            if "image" in rel.target_ref:
                img_part = rel.target_part
                img_filename = f"{docx_path.stem}_img_{len(embedded_images) + 1}.png"
                img_path = self.crops_dir / img_filename
                with open(img_path, "wb") as f:
                    f.write(img_part.blob)
                embedded_images.append(str(img_path))

        deliverables = self._extract_deliverables_from_text(full_text, default_images=[Path(p) for p in embedded_images])

        return {
            "type": "docx",
            "file": str(docx_path),
            "full_text": full_text,
            "tables": tables_data,
            "embedded_images": embedded_images,
            "deliverables": deliverables,
            "confidence": "Alta"
        }

    def _parse_image(self, image_path: Path) -> Dict[str, Any]:
        """Procesa una imagen PNG/JPG acotada de alta resolución."""
        img = Image.open(image_path)
        w, h = img.size

        # Segmentar vistas estándar por cuadrantes
        boxes = {
            "Vista_Superior": (0, 0, int(w * 0.55), int(h * 0.55)),
            "Vista_Frontal": (0, int(h * 0.45), int(w * 0.55), h),
            "Corte_Transversal": (int(w * 0.45), int(h * 0.45), w, h),
            "Detalle_Ampliado": (int(w * 0.45), 0, w, int(h * 0.55)),
        }
        views = []
        for v_name, box in boxes.items():
            crop = img.crop(box)
            c_path = self.crops_dir / f"{image_path.stem}_{v_name}.png"
            crop.save(c_path)
            views.append({"name": v_name, "path": str(c_path)})

        # Deliverable único de la pieza
        part_name = image_path.stem.replace(" ", "_")
        deliverables = [
            {
                "id": "tarea_01",
                "nombre": part_name,
                "tipo": "pieza",
                "descripcion": f"Pieza extraída de plano de imagen {image_path.name}",
                "imagen_referencia": str(image_path),
                "estado": "pendiente",
                "intentos": 0,
                "archivo": None,
                "errores": []
            }
        ]

        return {
            "type": "image",
            "file": str(image_path),
            "resolution": [w, h],
            "views": views,
            "deliverables": deliverables,
            "confidence": "Media"
        }

    def _parse_cad_file(self, cad_path: Path) -> Dict[str, Any]:
        """Procesa un archivo CAD existente (.step, .stl, .dxf, .par, .asm) para reconstrucción o inspección."""
        ext = cad_path.suffix.lower()
        deliverables = [
            {
                "id": "tarea_cad_01",
                "nombre": cad_path.stem,
                "tipo": "ensamble" if ext == ".asm" else "pieza",
                "descripcion": f"Reconstrucción/Inspección paramétrica de archivo {ext.upper()} {cad_path.name}",
                "archivo_origen": str(cad_path),
                "estado": "pendiente",
                "intentos": 0,
                "archivo": None,
                "errores": []
            }
        ]
        return {
            "type": f"cad_{ext.replace('.', '')}",
            "file": str(cad_path),
            "deliverables": deliverables,
            "confidence": "Alta"
        }

    def _parse_text_description(self, text: str, source_file: Optional[Path] = None) -> Dict[str, Any]:
        """Interpreta enunciados o descripciones puras en texto y extrae la lista de entregables."""
        deliverables = self._extract_deliverables_from_text(text)
        return {
            "type": "text",
            "file": str(source_file) if source_file else None,
            "full_text": text,
            "deliverables": deliverables,
            "confidence": "Media"
        }

    def _extract_deliverables_from_text(self, text: str, default_images: Optional[List[Path]] = None) -> List[Dict[str, Any]]:
        """Extrae dinámicamente cada pieza, ensamble y empaquetado del enunciado sin valores fijos."""
        deliverables = []
        task_idx = 1

        # 1. Buscar piezas numeradas o mencionadas ("Pieza 1", "Parte 1", "01_...", etc.)
        pattern_pieces = re.compile(
            r"(?:pieza|parte|componente)\s*(\d+)[:\s\-]+([^\n\r,\.]+)",
            re.IGNORECASE
        )
        matches = pattern_pieces.findall(text)
        for num, name in matches:
            clean_name = f"{int(num):02d}_{name.strip().replace(' ', '_')}"
            img_ref = None
            if default_images and int(num) <= len(default_images):
                img_ref = str(default_images[int(num) - 1])
            deliverables.append({
                "id": f"tarea_{task_idx:02d}",
                "nombre": clean_name,
                "tipo": "pieza",
                "descripcion": f"Pieza {num}: {name.strip()}",
                "imagen_referencia": img_ref,
                "estado": "pendiente",
                "intentos": 0,
                "archivo": None,
                "errores": []
            })
            task_idx += 1

        # 2. Si no encontró por regex formal, buscar listas con .par o .asm
        if not deliverables:
            par_matches = re.findall(r"([A-Za-z0-9_\-]+)\.par", text, re.IGNORECASE)
            for par_name in dict.fromkeys(par_matches):
                deliverables.append({
                    "id": f"tarea_{task_idx:02d}",
                    "nombre": par_name,
                    "tipo": "pieza",
                    "descripcion": f"Modelado de {par_name}.par",
                    "imagen_referencia": None,
                    "estado": "pendiente",
                    "intentos": 0,
                    "archivo": None,
                    "errores": []
                })
                task_idx += 1

        # 3. Detectar si hay ensamble pedido
        asm_matches = re.findall(r"(?:ensamble|assembly|montaje|mecanismo)[:\s\-]*([^\n\r,\.]+)", text, re.IGNORECASE)
        asm_file_matches = re.findall(r"([A-Za-z0-9_\-]+)\.asm", text, re.IGNORECASE)
        if asm_file_matches:
            for asm_name in dict.fromkeys(asm_file_matches):
                deliverables.append({
                    "id": f"tarea_{task_idx:02d}",
                    "nombre": asm_name,
                    "tipo": "ensamble",
                    "descripcion": f"Ensamble de componentes: {asm_name}.asm",
                    "imagen_referencia": None,
                    "estado": "pendiente",
                    "intentos": 0,
                    "archivo": None,
                    "errores": []
                })
                task_idx += 1
        elif asm_matches:
            deliverables.append({
                "id": f"tarea_{task_idx:02d}",
                "nombre": "Ensamble_Mecanico",
                "tipo": "ensamble",
                "descripcion": f"Ensamble: {asm_matches[0].strip()}",
                "imagen_referencia": None,
                "estado": "pendiente",
                "intentos": 0,
                "archivo": None,
                "errores": []
            })
            task_idx += 1

        # 4. Detectar empaquetado (.zip)
        zip_match = re.search(r"([A-Za-z0-9_\-]+)\.zip", text, re.IGNORECASE)
        zip_name = zip_match.group(1) + ".zip" if zip_match else "ENTREGA_PROYECTO_CAD.zip"
        deliverables.append({
            "id": f"tarea_{task_idx:02d}",
            "nombre": zip_name.replace(".zip", ""),
            "tipo": "empaquetado",
            "descripcion": f"Empaquetado final comprimido {zip_name}",
            "zip_filename": zip_name,
            "estado": "pendiente",
            "intentos": 0,
            "archivo": None,
            "errores": []
        })

        return deliverables
