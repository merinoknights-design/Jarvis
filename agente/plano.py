"""
Planos (.dft) a partir de una pieza o un ensamble (JRV-50, JRV-51, JRV-52, JRV-53). 2026-10-30.

Usa la plantilla ISO de la instalación (A3 apaisado, fondo "Hoja A3", proyección de primer diedro).
  Pieza:    vista frontal + dos plegadas (debajo y a la derecha) + isométrica; escala normalizada según el
            tamaño; cotas y líneas de centro recuperadas del modelo en las vistas ortogonales.
  Ensamble: vista isométrica grande + lista de piezas "ISO" (número, archivo, autor, cantidad) con globos.
Nunca sobrescribe: el .dft y el .pdf deben ser rutas nuevas.

Uso:  python -X utf8 plano.py <modelo.par|.asm> <salida.dft> [--pdf] [--escala 1:2] [--hoja A3|A4]
        [--titulo "..."] [--autor "..."] [--proyecto "..."] [--numero "..."]
Última línea:  @@RESULTADO@@ {json}
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, r"C:\Jarvis")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import se_com_seguro as se  # noqa: E402
import acciones as A  # noqa: E402
import rutas_se  # noqa: E402

MARCA = "@@RESULTADO@@"
PLANTILLA = str(rutas_se.plantilla_plano())
HOJAS = {"A3": (31, "Hoja A3", 0.420, 0.297), "A4": (29, "Hoja A4", 0.297, 0.210)}
FRONTAL, SUPERIOR, DERECHA, ISO = 4, 1, 2, 9          # ViewOrientationConstants
PLEGAR_ABAJO, PLEGAR_DERECHA = 2, 3                    # FoldTypeConstants
ESCALAS = [10, 5, 2, 1, 1 / 2, 1 / 5, 1 / 10, 1 / 20, 1 / 50]


def escala_normalizada(dim_max_m, hueco_m):
    for e in ESCALAS:
        if dim_max_m * e <= hueco_m:
            return e
    return ESCALAS[-1]


def texto_escala(e):
    return "%g:1" % e if e >= 1 else "1:%g" % round(1 / e)


def leer_escala(t):
    a, b = t.split(":")
    return float(a) / float(b)


def caja_modelo(app, ruta):
    doc, mio = A.tomar_documento(app, str(ruta))
    try:
        if A.TIPOS.get(doc.Type) in ("pieza", "chapa"):
            caja = A.bounding_box_mm(doc.Models.Item(1).Body)
            props = A.propiedades(doc)
            return [caja["x"] / 1000, caja["y"] / 1000, caja["z"] / 1000], "pieza", props
        xs = []
        for i in range(1, doc.Occurrences.Count + 1):
            r = se._aplanar(doc.Occurrences.Item(i).GetRangeBox([0.0] * 3, [0.0] * 3))
            xs.append([x for x in r if isinstance(x, list) and len(x) == 3])
        mn = [min(p[0][k] for p in xs) for k in range(3)]
        mx = [max(p[1][k] for p in xs) for k in range(3)]
        return [mx[k] - mn[k] for k in range(3)], "ensamble", A.propiedades(doc)
    finally:
        if mio:
            A.cerrar(app, doc)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("modelo")
    ap.add_argument("salida")
    ap.add_argument("--pdf", action="store_true")
    ap.add_argument("--escala")
    ap.add_argument("--hoja", default="A3", choices=sorted(HOJAS))
    for p in ("titulo", "autor", "proyecto", "numero"):
        ap.add_argument("--" + p)
    a = ap.parse_args()
    modelo, salida = Path(a.modelo), Path(a.salida)
    pdf = salida.with_suffix(".pdf") if a.pdf else None
    for f in (salida, pdf):
        if f and f.exists():
            raise ValueError("%s ya existe: elija otro nombre." % f)
    if not modelo.exists():
        raise ValueError("No existe %s" % modelo)
    se.guardia_disco()
    app = se.conectar()
    dims, tipo, props_modelo = caja_modelo(app, modelo)
    tam, fondo, ancho, alto = HOJAS[a.hoja]
    dft = se.reintentar(app.Documents.Add, "SolidEdge.DraftDocument", PLANTILLA)
    res = {"tipo": tipo, "hoja": a.hoja, "vistas": []}
    try:
        hoja = dft.ActiveSheet
        hoja.SheetSetup.SheetSizeOption = tam
        bg = dft.Sections.BackgroundSection.Sheets
        hoja.Background = next(bg.Item(i) for i in range(1, bg.Count + 1) if bg.Item(i).Name == fondo)
        ml = se.reintentar(dft.ModelLinks.Add, str(modelo))
        vistas = hoja.DrawingViews
        if tipo == "pieza":
            # Cuadrantes útiles de un A3 por encima del cuadro de rotulación (abajo a la derecha)
            hueco = min(ancho * 0.30, alto * 0.36)
            e = leer_escala(a.escala) if a.escala else escala_normalizada(max(dims), hueco)
            fr = se.reintentar(vistas.AddPartView, ml, FRONTAL, e, ancho * 0.25, alto * 0.68, 0)
            ab = se.reintentar(vistas.AddByFold, fr, PLEGAR_ABAJO, ancho * 0.25, alto * 0.28)
            de = se.reintentar(vistas.AddByFold, fr, PLEGAR_DERECHA, ancho * 0.58, alto * 0.68)
            iso = se.reintentar(vistas.AddPartView, ml, ISO, e * 0.7, ancho * 0.82, alto * 0.70, 0)
            for nombre, v in (("frontal", fr), ("debajo", ab), ("derecha", de)):
                try:
                    v.RetrieveDimensions()
                    v.RetrieveCenterLinesCenterMarks()
                    res["vistas"].append(nombre + " (cotas recuperadas)")
                except Exception as err:
                    res["vistas"].append("%s (sin cotas: %s)" % (nombre, se.describir_error(err)))
            res["vistas"].append("isométrica")
            res["escala"] = texto_escala(e)
            # Las cotas recuperadas salen amontonadas (2026-10-30): se seleccionan todas y se reacomodan.
            try:
                sel = dft.SelectSet
                sel.RemoveAll()
                cotas = hoja.Dimensions
                for i in range(1, cotas.Count + 1):
                    sel.Add(cotas.Item(i))
                if sel.Count:
                    hoja.ArrangeDimensionsInSelectSet(1.0, True)
                res["cotas"] = sel.Count
                sel.RemoveAll()
            except Exception as err:
                res["cotas_sin_reacomodar"] = se.describir_error(err)
        else:
            hueco = min(ancho * 0.55, alto * 0.62)
            e = leer_escala(a.escala) if a.escala else escala_normalizada(max(dims) * 1.2, hueco)
            iso = se.reintentar(vistas.AddAssemblyView, ml, ISO, e, ancho * 0.36, alto * 0.55, 0)
            res["vistas"].append("isométrica del ensamble")
            res["escala"] = texto_escala(e)
            lista = se.reintentar(dft.PartsLists.Add, iso, "ISO", 1, 1)   # configuración "ISO", autoglobos, crear lista
            # Sin posición explícita la lista queda FUERA de la hoja (2026-10-30): se ancla por su esquina inferior
            # derecha justo encima del cuadro de rotulación de la plantilla ISO (que mide ~60 mm de alto en A3/A4).
            lista.AnchorPoint = 3      # igLowerRight
            lista.SetOrigin(ancho - 0.010, 0.062)
            try:
                lista.Update()
            except Exception:
                pass
            try:
                res["lista_de_piezas_filas"] = lista.Rows.Count
            except Exception:
                res["lista_de_piezas_filas"] = "?"
            res["globos"] = hoja.Balloons.Count
        # Propiedades del plano (alimentan el cuadro de rotulación con %{...})
        nuevas = {"Title": a.titulo or props_modelo.get("Title") or modelo.stem, "Author": a.autor or props_modelo.get("Author"),
                  "ProjectName": a.proyecto or props_modelo.get("ProjectName"), "DocumentNumber": a.numero}
        si = dft.SummaryInfo
        for k, v in nuevas.items():
            if v:
                setattr(si, k, str(v))
        res["propiedades"] = {k: getattr(si, k) for k in nuevas}
        try:
            se.reintentar(dft.UpdateAll)
        except Exception:
            pass
        se.guardar_nuevo(dft, salida)
        res["archivo"] = str(salida)
        if pdf:
            se.reintentar(dft.SaveCopyAs, str(pdf))
            res["pdf"] = str(pdf) if pdf.exists() else None
        res["ok"] = True
        return res
    finally:
        A.cerrar(app, dft)


if __name__ == "__main__":
    try:
        res = main()
    except Exception as e:
        res = {"ok": False, "error": str(e) if isinstance(e, ValueError) else se.describir_error(e)}
    print(MARCA, json.dumps(res, ensure_ascii=False, default=str))
    sys.exit(0 if res.get("ok") else 1)
