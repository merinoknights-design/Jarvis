"""
Acciones de Jarvis para agentes (Claude). Se ejecutan en un PROCESO APARTE del servidor, para que un fallo de
Solid Edge no tumbe a Jarvis.

Uso:  C:\\Jarvis\\venv\\Scripts\\python.exe -X utf8 acciones.py <accion> "<json de parámetros>" | @parametros.json
La última línea de la salida es:  @@RESULTADO@@ {json}

Acciones:
  estado                                   Solid Edge, documentos abiertos, disco y Cardán (no abre nada).
  inspeccionar {ruta?, cerrar?}            Lo que hay en un .par/.psm/.asm/.dft (JRV-05). Nunca guarda.
  capturar {ruta?, salida?, vista?, ancho?, alto?}   PNG de la vista, validando que no salga en blanco (JRV-03).
  abrir {ruta}                             Abre un documento existente y lo deja en pantalla, sin crear nada (JRV-06).

Parches JRV-03, JRV-05 y JRV-06 (2026-10-28).
"""
import json
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, r"C:\Jarvis")
import se_com_seguro as se  # noqa: E402
from cad_atomic_lib import (FEATURE_FAILED, FEATURE_OK, FEATURE_ROLLEDBACK, FEATURE_SUPPRESSED,  # noqa: E402
                            FEATURE_WARNED, bounding_box_mm)

MARCA = "@@RESULTADO@@"
PROYECTOS = Path.home() / "Documents" / "Proyectos_SolidEdge"
EXTENSIONES = {".par", ".psm", ".asm", ".dft", ".pwd"}
TIPOS = {1: "pieza", 2: "plano", 3: "ensamble", 4: "chapa", 6: "soldadura", 7: "ensamble", 8: "pieza",
         9: "chapa", 10: "ensamble"}
ESTADO_OPERACION = {FEATURE_OK: "ok", FEATURE_FAILED: "FALLÓ", FEATURE_WARNED: "aviso",
                    FEATURE_SUPPRESSED: "suprimida", FEATURE_ROLLEDBACK: "retrocedida"}
# Vistas con nombre: Solid Edge las nombra según el idioma de la interfaz, así que se prueban varias.
VISTAS = {"iso": ["Iso", "ISO", "Isométrica", "Isometrica", "Isometric"],
          "frontal": ["Alzado", "Front", "Frontal", "Anterior"],
          "superior": ["Planta", "Top", "Superior"],
          "derecha": ["Derecha", "Right", "Lateral derecha"]}
CONTENIDO_MINIMO = 0.01  # fracción de píxeles distintos del fondo; con solo los ejes de referencia sale ~0,0004


class ErrorAccion(RuntimeError):
    pass


# ----------------------------------------------------------------- documentos
def _misma_ruta(a: str, b: Path) -> bool:
    try:
        return Path(a).resolve() == b.resolve()
    except Exception:
        return False


def documentos(app):
    out = []
    for i in range(1, app.Documents.Count + 1):
        d = app.Documents.Item(i)
        try:
            sucio = bool(d.Dirty)
        except Exception:
            sucio = None
        out.append({"nombre": d.Name, "ruta": d.FullName, "tipo": TIPOS.get(d.Type, str(d.Type)), "sin_guardar": sucio})
    return out


def tomar_documento(app, ruta):
    """Devuelve (doc, abierto_por_mi). Sin ruta, el documento activo."""
    if not ruta:
        try:
            return app.ActiveDocument, False
        except Exception:
            raise ErrorAccion("No hay documento activo en Solid Edge y no se indicó 'ruta'.")
    ruta = Path(ruta)
    if ruta.suffix.lower() not in EXTENSIONES:
        raise ErrorAccion("Extensión no admitida: %s (se admiten %s)" % (ruta.suffix, sorted(EXTENSIONES)))
    for i in range(1, app.Documents.Count + 1):
        d = app.Documents.Item(i)
        if _misma_ruta(d.FullName, ruta):
            return d, False
    if not ruta.exists():
        raise ErrorAccion("No existe %s" % ruta)
    return se.reintentar(app.Documents.Open, str(ruta)), True


def cerrar(app, doc, espera_max=20.0):
    """Cierra SIN guardar y espera a que el documento desaparezca de app.Documents.
    Solid Edge termina de cerrar un instante después de Close(): sin esta espera, la acción siguiente lo
    encontraba aún abierto, lo tomaba por un documento del usuario y no lo cerraba (2026-10-28)."""
    ruta = doc.FullName
    se.reintentar(doc.Close, False)
    limite = time.time() + espera_max
    while time.time() < limite:
        if not any(_misma_ruta(app.Documents.Item(i).FullName, Path(ruta)) for i in range(1, app.Documents.Count + 1)):
            return
        time.sleep(0.3)


def traer_al_frente(app):
    try:
        import win32gui
        hwnd = int(app.hWnd)
        win32gui.ShowWindow(hwnd, 9)  # SW_RESTORE
        try:
            win32gui.SetForegroundWindow(hwnd)
        except Exception:
            pass  # Windows puede negarlo si otra app tiene el foco; la captura igual se intenta
    except Exception:
        pass


def propiedades(doc):
    out = {}
    try:
        si = doc.SummaryInfo
        for campo in ("Title", "Author", "Subject", "DocumentNumber", "ProjectName", "RevisionNumber"):
            try:
                out[campo] = getattr(si, campo)
            except Exception:
                pass
    except Exception:
        pass
    return out


# ------------------------------------------------------------- inspección
def inspeccionar_pieza(doc):
    out = {}
    try:
        out["modo"] = {1: "síncrono", 2: "ordenado"}.get(doc.ModelingMode, doc.ModelingMode)
    except Exception:
        pass
    if doc.Models.Count == 0:
        out["cuerpo"] = None
        return out
    model = doc.Models.Item(1)
    ops = []
    for i in range(1, model.Features.Count + 1):
        f = model.Features.Item(i)
        try:
            st = f.Status
        except Exception:
            st = None
        ops.append({"nombre": getattr(f, "Name", "?"), "estado": ESTADO_OPERACION.get(st, st)})
    out["operaciones"] = ops
    out["resumen_operaciones"] = dict(Counter(o["estado"] for o in ops))
    body = model.Body
    out["volumen_mm3"] = round(float(body.Volume) * 1e9, 2)
    out["caja_mm"] = bounding_box_mm(body)
    return out


def inspeccionar_ensamble(doc):
    est = se.estado_ensamble(doc)
    occs = est["ocurrencias"]
    sin_rel, faltantes = [], set()
    for i in range(1, doc.Occurrences.Count + 1):
        o = doc.Occurrences.Item(i)
        if o.Relations3d.Count == 0:
            sin_rel.append(o.Name)
        try:
            if not Path(o.OccurrenceFileName).exists():
                faltantes.add(o.OccurrenceFileName)
        except Exception:
            pass
    rels = est["relaciones"]
    out = {
        "ocurrencias": len(occs),
        "por_pieza": dict(Counter(o["archivo"] for o in occs)),
        "fijas": [o["nombre"] for o in occs if o["fija"]],
        "sobredefinidas": [o["nombre"] for o in occs if o["status"] == se.OCC_OVER],
        "inconsistentes": [o["nombre"] for o in occs if o["status"] == se.OCC_NOT_CONSISTENT],
        "sin_relaciones": sin_rel,
        "relaciones": len(rels),
        "relaciones_por_tipo": dict(Counter(str(r["tipo"]) for r in rels)),
        "relaciones_no_resueltas": [r["i"] for r in rels if r["status"] != se.REL_SOLVED],
        "relaciones_suprimidas": [r["i"] for r in rels if r["suprimida"]],
        # Vínculos rotos: el .asm guarda la ruta ABSOLUTA de cada pieza. Si alguien mueve las piezas con el
        # Explorador, el ensamble abre vacío (verificado 2026-10-28 con el Cardán). Se arregla con el Gestor
        # de diseños / Empaquetar proyecto, o volviendo a poner las piezas donde estaban.
        "archivos_faltantes": sorted(faltantes),
    }
    try:
        out["explosiones"] = int(doc.ExplosionsCount)
    except Exception:
        pass
    try:
        cfg = doc.Configurations
        out["configuraciones"] = [{"nombre": cfg.Item(i).Name, "tipo": {0: "visualización", 1: "explosión"}.get(
            cfg.Item(i).ConfigurationType, cfg.Item(i).ConfigurationType)} for i in range(1, cfg.Count + 1)]
    except Exception as e:
        out["configuraciones_error"] = se.describir_error(e)
    return out


def inspeccionar_plano(doc):
    hojas = []
    for i in range(1, doc.Sheets.Count + 1):
        h = doc.Sheets.Item(i)
        fila = {"nombre": h.Name}
        for campo, coleccion in (("vistas", "DrawingViews"), ("globos", "Balloons")):
            try:
                fila[campo] = getattr(h, coleccion).Count
            except Exception:
                pass
        hojas.append(fila)
    out = {"hojas": hojas}
    try:
        out["listas_de_piezas"] = doc.PartsLists.Count
    except Exception:
        pass
    return out


def accion_inspeccionar(p):
    app = se.conectar()
    ruta = p.get("ruta")
    antes = se.sha256(Path(ruta)) if ruta and Path(ruta).exists() else None
    doc, mio = tomar_documento(app, ruta)
    try:
        tipo = TIPOS.get(doc.Type, str(doc.Type))
        res = {"documento": doc.FullName, "tipo": tipo, "abierto_por_jarvis": mio, "propiedades": propiedades(doc)}
        if tipo in ("pieza", "chapa"):
            res.update(inspeccionar_pieza(doc))
        elif tipo == "ensamble":
            res.update(inspeccionar_ensamble(doc))
        elif tipo == "plano":
            res.update(inspeccionar_plano(doc))
    finally:
        if mio and p.get("cerrar", True):
            cerrar(app, doc)
    if antes:
        res["archivo_sin_cambios"] = se.sha256(Path(ruta)) == antes
    return res


# ---------------------------------------------------------------- captura
def imagen_en_blanco(ruta):
    """(en_blanco, contenido): contenido = fracción de píxeles que NO son del color de fondo dominante.
    La desviación típica no basta: una vista vacía con solo los ejes de referencia daba 3,04 y pasaba."""
    from PIL import Image
    with Image.open(ruta) as im:
        hist = im.convert("L").histogram()
    contenido = 1.0 - max(hist) / float(sum(hist))
    return contenido < CONTENIDO_MINIMO, round(contenido, 4)


def mostrar_ocultas(doc):
    """Al abrir un ensamble por automatización, Solid Edge 2026 deja TODAS las ocurrencias ocultas
    (verificado con el Cardán: 0 de 90 visibles). Devuelve cuántas mostró."""
    n = 0
    for i in range(1, doc.Occurrences.Count + 1):
        o = doc.Occurrences.Item(i)
        try:
            if not o.Visible:
                o.Visible = True
                n += 1
        except Exception:
            pass
    return n


def captura_ventana(hwnd, salida):
    """Plan B: copia el área gráfica con PrintWindow (PW_RENDERFULLCONTENT, sirve para OpenGL/DirectX)."""
    import ctypes
    import win32gui
    import win32ui
    from PIL import Image
    l, t, r, b = win32gui.GetWindowRect(hwnd)
    w, h = r - l, b - t
    if w <= 0 or h <= 0:
        raise ErrorAccion("La ventana gráfica no tiene tamaño (¿minimizada?)")
    hdc = win32gui.GetWindowDC(hwnd)
    mfc = win32ui.CreateDCFromHandle(hdc)
    mem = mfc.CreateCompatibleDC()
    bmp = win32ui.CreateBitmap()
    bmp.CreateCompatibleBitmap(mfc, w, h)
    mem.SelectObject(bmp)
    try:
        ctypes.windll.user32.PrintWindow(hwnd, mem.GetSafeHdc(), 2)
        info = bmp.GetInfo()
        im = Image.frombuffer("RGB", (info["bmWidth"], info["bmHeight"]), bmp.GetBitmapBits(True), "raw", "BGRX", 0, 1)
        im.save(salida)
    finally:
        win32gui.DeleteObject(bmp.GetHandle())
        mem.DeleteDC()
        mfc.DeleteDC()
        win32gui.ReleaseDC(hwnd, hdc)


def accion_capturar(p):
    se.guardia_disco()
    app = se.conectar()
    ruta = p.get("ruta")
    doc, mio = tomar_documento(app, ruta)
    vista = (p.get("vista") or "iso").lower()
    nombre = Path(doc.FullName).stem if doc.FullName else doc.Name
    salida = Path(p.get("salida") or (PROYECTOS / "_capturas" / ("%s_%s.png" % (nombre, vista))))
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida = se.ruta_libre(salida)
    res = {"documento": doc.FullName, "vista": vista, "intentos": []}
    try:
        se.reintentar(doc.Activate)
        traer_al_frente(app)
        if TIPOS.get(doc.Type) == "ensamble":
            ocultas = sum(1 for i in range(1, doc.Occurrences.Count + 1) if not doc.Occurrences.Item(i).Visible)
            res["ocurrencias_ocultas"] = ocultas
            # Solo se muestran si el documento lo abrió Jarvis (se cierra sin guardar) o si se pide expresamente:
            # en un documento que el usuario tiene abierto, cambiar la visibilidad cambiaría lo que él está viendo.
            if ocultas and p.get("mostrar_ocultas", mio):
                res["ocurrencias_mostradas"] = mostrar_ocultas(doc)
        win = app.ActiveWindow
        view = win.View
        if p.get("ventana_completa"):
            app.DoIdle()
            time.sleep(float(p.get("espera_s", 1.5)))
            captura_ventana(int(app.hWnd), str(salida))
            vacia, cont = imagen_en_blanco(salida)
            res.update(ok=True, archivo=str(salida), metodo="PrintWindow (ventana completa)", contenido=cont)
            return res
        if vista in VISTAS:
            for nv in VISTAS[vista]:
                try:
                    view.ApplyNamedView(nv)
                    res["vista_aplicada"] = nv
                    break
                except Exception:
                    continue
        view.Fit()
        app.DoIdle()
        view.Update()
        time.sleep(float(p.get("espera_s", 1.5)))
        # Plan A: SaveAsImage
        try:
            view.SaveAsImage(str(salida), int(p.get("ancho", 1600)), int(p.get("alto", 1000)))
            vacia, desv = imagen_en_blanco(salida)
            res["intentos"].append({"metodo": "SaveAsImage", "en_blanco": vacia, "contenido": desv})
            if not vacia:
                res.update(ok=True, archivo=str(salida), metodo="SaveAsImage")
                return res
            salida.unlink(missing_ok=True)
        except Exception as e:
            res["intentos"].append({"metodo": "SaveAsImage", "error": se.describir_error(e)})
        # Plan B: copiar la ventana gráfica
        try:
            captura_ventana(int(win.DrawHwnd), str(salida))
            vacia, desv = imagen_en_blanco(salida)
            res["intentos"].append({"metodo": "PrintWindow", "en_blanco": vacia, "contenido": desv})
            if not vacia:
                res.update(ok=True, archivo=str(salida), metodo="PrintWindow")
                return res
            salida.unlink(missing_ok=True)
        except Exception as e:
            res["intentos"].append({"metodo": "PrintWindow", "error": str(e)})
        res["ok"] = False
        if res.get("ocurrencias_ocultas"):
            faltan = [doc.Occurrences.Item(i).OccurrenceFileName for i in range(1, doc.Occurrences.Count + 1)
                      if not Path(doc.Occurrences.Item(i).OccurrenceFileName).exists()]
            if faltan:
                res["causa_probable"] = ("El ensamble no encuentra %d archivos de pieza (vínculos rotos), p. ej. %s"
                                         % (len(set(faltan)), faltan[0]))
        return res
    finally:
        if mio and p.get("cerrar", True):
            cerrar(app, doc)


# ------------------------------------------------------------ estado y abrir
def accion_estado(p):
    res = {"disco_libre_gb": round(se.espacio_libre_gb(), 2)}
    try:
        app = se.conectar(lanzar=False)
        res.update(solid_edge=True, version=app.Version, documentos=documentos(app))
    except Exception:
        res["solid_edge"] = False
    from cardan.rutas_cardan import ASM as CARDAN_ASM  # JRV-69 (2026-10-28)
    est = CARDAN_ASM.with_name("cardan_estado.json")
    if est.exists():
        res["cardan_fases"] = json.loads(est.read_text(encoding="utf-8")).get("fases", [])
    return res


def accion_abrir(p):
    ruta = p.get("ruta")
    app = se.conectar()
    if not ruta:  # solo abrir Solid Edge y traerlo al frente
        traer_al_frente(app)
        return {"solid_edge": True, "version": app.Version, "documentos": documentos(app)}
    doc, mio = tomar_documento(app, ruta)
    se.reintentar(doc.Activate)
    traer_al_frente(app)
    return {"documento": doc.FullName, "tipo": TIPOS.get(doc.Type, str(doc.Type)), "ya_estaba_abierto": not mio,
            "nota": "Abierto solo para ver: Jarvis no lo guarda."}


def accion_caras(p):
    """Caras de una pieza (.par/.psm) en mm y coordenadas de pieza, para escribir selectores de recetas (JRV-20)."""
    import caras as C
    app = se.conectar()
    doc, mio = tomar_documento(app, p.get("ruta"))
    try:
        if TIPOS.get(doc.Type) not in ("pieza", "chapa"):
            raise ErrorAccion("'caras' es para piezas (.par/.psm); en un ensamble, inspecciona cada pieza.")
        fs = doc.Models.Item(1).Body.Faces(1)
        lista = C.describir_caras([fs.Item(i) for i in range(1, fs.Count + 1)])
        return {"documento": doc.FullName, "caras": lista[: int(p.get("max", 300))], "total": len(lista)}
    finally:
        if mio and p.get("cerrar", True):
            cerrar(app, doc)


def accion_exportar(p):
    """Exporta un documento a STEP, STL, IGES, Parasolid o PDF con SaveCopyAs (el original no cambia). JRV-19."""
    se.guardia_disco()
    ruta, salida = p.get("ruta"), Path(p["salida"])
    if salida.exists():
        raise ErrorAccion("%s ya existe: elija otro nombre." % salida)
    if salida.suffix.lower() not in (".stp", ".step", ".stl", ".igs", ".iges", ".x_t", ".pdf"):
        raise ErrorAccion("Formato no admitido: %s" % salida.suffix)
    app = se.conectar()
    antes = se.sha256(Path(ruta)) if ruta and Path(ruta).exists() else None
    doc, mio = tomar_documento(app, ruta)
    try:
        salida.parent.mkdir(parents=True, exist_ok=True)
        se.reintentar(doc.SaveCopyAs, str(salida))
    finally:
        if mio and p.get("cerrar", True):
            cerrar(app, doc)
    if not salida.exists():
        raise ErrorAccion("SaveCopyAs no produjo %s" % salida)
    res = {"archivo": str(salida), "bytes": salida.stat().st_size}
    if antes:
        res["original_sin_cambios"] = se.sha256(Path(ruta)) == antes
    return res


ACCIONES = {"estado": accion_estado, "inspeccionar": accion_inspeccionar, "capturar": accion_capturar,
            "abrir": accion_abrir, "caras": accion_caras, "exportar": accion_exportar}


def main(argv):
    if len(argv) < 2 or argv[1] not in ACCIONES:
        print(__doc__)
        print(MARCA, json.dumps({"ok": False, "error": "Acción desconocida. Opciones: %s" % sorted(ACCIONES)}))
        return 2
    try:
        crudo = argv[2].strip() if len(argv) > 2 else ""
        if crudo.startswith("@"):  # @archivo.json: cómodo desde PowerShell 5.1, que se come las comillas dobles
            crudo = Path(crudo[1:]).read_text(encoding="utf-8-sig")
        params = json.loads(crudo) if crudo else {}
        res = ACCIONES[argv[1]](params)
        res.setdefault("ok", True)
    except (ErrorAccion, se.ErrorSolidEdge, FileNotFoundError) as e:
        res = {"ok": False, "error": str(e)}
    except Exception as e:
        res = {"ok": False, "error": se.describir_error(e)}
    print(MARCA, json.dumps(res, ensure_ascii=False, default=str))
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
