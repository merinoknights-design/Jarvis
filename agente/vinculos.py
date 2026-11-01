"""
Vínculos de documentos de Solid Edge con Revision Manager (el motor del Gestor de diseños), sin abrir Solid Edge.
JRV-69/70 (2026-10-28).

Uso:
  python -X utf8 vinculos.py listar   <documento>
  python -X utf8 vinculos.py redirigir <documento> <carpeta_vieja> <carpeta_nueva>

Reglas:
  - Trabaja sobre una COPIA: redirigir reescribe el documento.
  - Solo redirige vínculos cuya carpeta sea la vieja y cuyo archivo exista con el mismo nombre en la nueva;
    si falta alguno, no guarda nada.
  - Después, abre la copia en Solid Edge y GUÁRDALA UNA VEZ: tras redirigir, Solid Edge la abre marcada
    "con cambios" (actualiza su información de vínculos) y las recetas que exigen un documento limpio se
    detienen. Luego verifica con la acción `inspeccionar` (archivos_faltantes = []).
"""
import sys
from pathlib import Path

import pythoncom
import win32com.client


def _abrir(ruta):
    pythoncom.CoInitialize()
    rm = win32com.client.Dispatch("RevisionManager.Application")
    return rm.Open(str(ruta))


def listar(ruta):
    doc = _abrir(ruta)
    try:
        # LinkedDocuments.Item es una propiedad con parámetro: con pywin32 dinámico se recorre con el enumerador.
        return [(d.FullName, Path(d.FullName).exists()) for d in doc.LinkedDocuments]
    finally:
        doc.Close()


def redirigir(ruta, vieja, nueva):
    vieja, nueva = Path(vieja), Path(nueva)
    doc = _abrir(ruta)
    hechos, fallos = [], []
    try:
        pendientes = []
        for d in doc.LinkedDocuments:
            actual = Path(d.FullName)
            if str(actual.parent).lower() != str(vieja).lower():
                continue
            destino = nueva / actual.name
            if destino.exists():
                pendientes.append((d, destino))
            else:
                fallos.append(str(destino))
        if fallos:
            return hechos, fallos
        for d, destino in pendientes:
            d.Replace(str(destino))
            hechos.append(str(destino))
        # Ojo: con pywin32 dinámico, SaveAllLinks se EJECUTA al leer el atributo (devuelve un entero).
        doc.SaveAllLinks
    finally:
        doc.Close()
    return hechos, fallos


def main(argv):
    if len(argv) >= 3 and argv[1] == "listar":
        for ruta, existe in listar(argv[2]):
            print("%s  %s" % ("OK  " if existe else "FALTA", ruta))
        return 0
    if len(argv) >= 5 and argv[1] == "redirigir":
        hechos, fallos = redirigir(argv[2], argv[3], argv[4])
        if fallos:
            print("PARADA: no existen en la carpeta nueva (no se guardó nada):", *fallos, sep="\n  ")
            return 1
        print("redirigidos %d vínculos:" % len(hechos), *hechos, sep="\n  ")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
