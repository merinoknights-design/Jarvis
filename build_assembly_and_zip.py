"""
Constructor del Ensamble Mecánico y Empaquetado Final ZIP para Siemens Solid Edge 2026.
Inserta:
  - 01_Piston.par
  - 02_Biela_Parte_Superior.par
  - 03_Biela_Parte_Inferior.par
Guarda 04_Ensamble_Motor_Piston.asm, genera captura de inspección y empaqueta en .zip.
"""

import os
import sys
import zipfile
from pathlib import Path

sys.path.append("C:/Jarvis")
from cad_engine import get_or_start_solidedge

output_dir = Path("C:/Jarvis/PARCIAL_2_ENTREGA")
asm_save_path = output_dir / "04_Ensamble_Motor_Piston.asm"

print("Iniciando creación del Ensamble en Solid Edge 2026...")
app = get_or_start_solidedge()
asm_doc = app.Documents.Add("SolidEdge.AssemblyDocument")
occurrences = asm_doc.Occurrences

piston_par = output_dir / "01_Piston.par"
biela_sup_par = output_dir / "02_Biela_Parte_Superior.par"
biela_inf_par = output_dir / "03_Biela_Parte_Inferior.par"

inserted = []

# 1. Piston en el origen
if piston_par.exists():
    occ1 = occurrences.AddByFilename(str(piston_par))
    occ1.PutOrigin(0.0, 0.0, 0.0)
    inserted.append("01_Piston.par")
    print("Insertado Pistón como componente base fijo en el origen.")

# 2. Biela Superior (coaxial con el pasador del pistón en Z = -135mm)
if biela_sup_par.exists():
    occ2 = occurrences.AddByFilename(str(biela_sup_par))
    # Posicionar el ojo del pie de biela centrado en el pasador del pistón
    occ2.PutOrigin(0.0, 0.0, -0.135)
    inserted.append("02_Biela_Parte_Superior.par")
    print("Insertada Biela Superior acoplada coaxialmente al pasador del pistón.")

# 3. Biela Inferior (acoplada en la cabeza de biela)
if biela_inf_par.exists():
    occ3 = occurrences.AddByFilename(str(biela_inf_par))
    occ3.PutOrigin(0.0, 0.0, -0.135)
    inserted.append("03_Biela_Parte_Inferior.par")
    print("Insertada Biela Inferior (Sombrerete) acoplada en la cara de partición.")

# Guardar documento de ensamble
if asm_save_path.exists():
    try:
        asm_save_path.unlink()
    except Exception:
        pass

asm_doc.SaveAs(str(asm_save_path))
print(f"Ensamble guardado exitosamente en: {asm_save_path}")

try:
    app.StartCommand(32824)  # Vista isométrica
except Exception:
    pass

# Captura de imagen del ensamble
asm_img = asm_save_path.with_suffix(".png")
try:
    if asm_doc.Windows.Count > 0:
        win = asm_doc.Windows.Item(1)
        win.View.Fit()
        win.View.SaveAsImage(str(asm_img), 1920, 1080)
        print(f"Captura de inspección del ensamble guardada en: {asm_img}")
except Exception as e:
    print(f"Aviso en captura del ensamble: {e}")

# Cerrar ensamble limpiamente
asm_doc.Close(False)

# Empaquetado ZIP
zip_path = output_dir / "PARCIAL_2_MODELAMIENTO_3D_ENTREGA.zip"
print(f"\nGenerando empaquetado final: {zip_path.name}...")
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    for f in output_dir.glob("*"):
        if f.suffix.lower() in [".par", ".asm", ".step", ".png", ".pdf"] and f != zip_path:
            zf.write(f, arcname=f.name)
            print(f"  + Añadido al ZIP: {f.name} ({round(f.stat().st_size/1024, 1)} KB)")

print(f"\nEMPAQUETADO FINAL COMPLETADO: {zip_path} ({round(zip_path.stat().st_size/1024, 1)} KB)")
