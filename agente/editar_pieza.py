"""
Editar una pieza existente sin rehacerla (JRV-17). 2026-10-31.

  listar:  cotas (variables de cota del documento: nombre, valor en mm), operaciones con profundidad y agujeros.
  cambiar: abre la pieza, cambia SOLO lo pedido, regenera, comprueba que todas las operaciones sigan sanas,
           mide caja y volumen antes y después, y GUARDA COMO PIEZA NUEVA. El original no se toca (se comprueba
           su huella). Si una operación falla tras el cambio, no guarda y lo dice.

Uso:
  python -X utf8 editar_pieza.py listar <pieza.par>
  python -X utf8 editar_pieza.py cambiar <pieza.par> <salida.par> [--cota NOMBRE=mm ...] [--profundidad OPERACION=mm ...]
         [--material NOMBRE]
  NOMBRE es el nombre de la cota que da `listar` (p. ej. V117 o el nombre que le haya puesto el usuario).
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
from cad_atomic_lib import FEATURE_OK, FEATURE_WARNED, bounding_box_mm  # noqa: E402

MARCA = "@@RESULTADO@@"
MM = 0.001
CON_PROFUNDIDAD = ("ExtrudedProtrusions", "ExtrudedCutouts")


def cotas(doc, con_boceto=False):
    """{nombre: objeto Dimension} de las cotas de los bocetos (las que gobiernan la geometría).
    Se leen boceto por boceto: Variables.Query con filtros de tipo devolvía 0 (2026-10-31)."""
    out = {}
    for i in range(1, doc.ProfileSets.Count + 1):
        perfiles = doc.ProfileSets.Item(i).Profiles
        for j in range(1, perfiles.Count + 1):
            ds = perfiles.Item(j).Dimensions
            for k in range(1, ds.Count + 1):
                d = ds.Item(k)
                out[d.DisplayName] = (d, i) if con_boceto else d
    return out


def operaciones(model):
    out = {}
    for col in CON_PROFUNDIDAD:
        try:
            c = getattr(model, col)
            for i in range(1, c.Count + 1):
                f = c.Item(i)
                try:
                    out[f.Name] = f
                except Exception:
                    pass
        except Exception:
            pass
    return out


def estado_operaciones(model):
    malas = []
    for i in range(1, model.Features.Count + 1):
        f = model.Features.Item(i)
        try:
            if f.Status not in (FEATURE_OK, FEATURE_WARNED):
                malas.append(f.Name)
        except Exception:
            pass
    return malas


def medir(model):
    return {"volumen_mm3": round(float(model.Body.Volume) * 1e9, 2), "caja_mm": bounding_box_mm(model.Body)}


def listar(ruta):
    app = se.conectar()
    doc, mio = A.tomar_documento(app, ruta)
    try:
        model = doc.Models.Item(1)
        res = {"pieza": str(ruta), "medidas": medir(model),
               "cotas": {k: {"valor_mm": round(d.Value / MM, 4), "boceto": b} for k, (d, b) in cotas(doc, True).items()},
               "operaciones_con_profundidad": {}, "operaciones": []}
        for nombre, f in operaciones(model).items():
            try:
                res["operaciones_con_profundidad"][nombre] = round(f.Depth / MM, 4)
            except Exception:
                res["operaciones_con_profundidad"][nombre] = "no finita"
        for i in range(1, model.Features.Count + 1):
            f = model.Features.Item(i)
            res["operaciones"].append({"nombre": f.Name, "estado": "ok" if f.Status in (FEATURE_OK, FEATURE_WARNED) else f.Status})
        try:
            res["agujeros"] = [{"nombre": model.Holes.Item(i).Name,
                                "dato": model.Holes.Item(i).HoleData.ThreadDescription or
                                        "Ø%.3f" % (model.Holes.Item(i).HoleData.HoleDiameter / MM)}
                               for i in range(1, model.Holes.Count + 1)]
        except Exception:
            pass
        res["ok"] = True
        return res
    finally:
        if mio:
            A.cerrar(app, doc)


def cambiar(ruta, salida, cambios_cota, cambios_prof, material=None):
    salida = Path(salida)
    if salida.exists():
        raise ValueError("%s ya existe: elija otro nombre." % salida)
    if Path(salida).resolve() == Path(ruta).resolve():
        raise ValueError("La salida debe ser una pieza NUEVA, no el original.")
    se.guardia_disco()
    antes_huella = se.sha256(Path(ruta))
    app = se.conectar()
    doc, mio = A.tomar_documento(app, ruta)
    if not mio:
        raise ValueError("La pieza ya está abierta en Solid Edge: ciérrala (o pide al usuario que la cierre) y repite.")
    hechos = []
    try:
        model = doc.Models.Item(1)
        antes = medir(model)
        dims = cotas(doc)
        for nombre, mm in cambios_cota.items():
            if nombre not in dims:
                raise ValueError("No existe la cota '%s'. Hay: %s" % (nombre, sorted(dims)))
            viejo = dims[nombre].Value / MM
            # Una cota de referencia (Constraint=False) acepta el valor pero NO mueve la geometría (2026-10-31):
            # se convierte en cota que gobierna antes de cambiarla.
            if not dims[nombre].Constraint:
                dims[nombre].Constraint = True
            dims[nombre].Value = mm * MM
            hechos.append("cota %s: %.4g → %.4g mm" % (nombre, viejo, mm))
        ops = operaciones(model)
        for nombre, mm in cambios_prof.items():
            if nombre not in ops:
                raise ValueError("No existe la operación '%s'. Hay: %s" % (nombre, sorted(ops)))
            viejo = ops[nombre].Depth / MM
            ops[nombre].Depth = mm * MM
            hechos.append("profundidad %s: %.4g → %.4g mm" % (nombre, viejo, mm))
        se.reintentar(doc.Recompute)
        malas = estado_operaciones(model)
        despues = medir(model)
        if malas:
            return {"ok": False, "error": "Tras el cambio fallan estas operaciones: %s. No se guardó nada." % malas,
                    "cambios": hechos, "antes": antes, "despues": despues}
        if material:
            se.reintentar(app.GetMaterialTable().ApplyMaterial, doc, material)
            hechos.append("material: " + material)
        se.guardar_nuevo(doc, salida)
        return {"ok": True, "archivo": str(salida), "cambios": hechos, "antes": antes, "despues": despues,
                "original_sin_cambios": se.sha256(Path(ruta)) == antes_huella}
    finally:
        A.cerrar(app, doc)


def pares(lista):
    out = {}
    for p in lista or []:
        k, v = p.rsplit("=", 1)
        out[k.strip()] = float(v.replace(",", "."))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("modo", choices=["listar", "cambiar"])
    ap.add_argument("pieza")
    ap.add_argument("salida", nargs="?")
    ap.add_argument("--cota", action="append")
    ap.add_argument("--profundidad", action="append")
    ap.add_argument("--material")
    a = ap.parse_args()
    if a.modo == "listar":
        return listar(a.pieza)
    if not a.salida:
        raise ValueError("Falta la ruta de salida (pieza nueva).")
    return cambiar(a.pieza, a.salida, pares(a.cota), pares(a.profundidad), a.material)


if __name__ == "__main__":
    try:
        res = main()
    except Exception as e:
        res = {"ok": False, "error": str(e) if isinstance(e, ValueError) else se.describir_error(e)}
    print(MARCA, json.dumps(res, ensure_ascii=False, default=str))
    sys.exit(0 if res.get("ok") else 1)
