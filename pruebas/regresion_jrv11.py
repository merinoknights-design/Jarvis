"""
Regresión de JRV-11 (no guarda NADA: crea piezas en memoria y las cierra sin guardar).
Ejecuta las mismas primitivas que C:\\Jarvis\\test_atomic_lib.py y comprueba lo que devuelven
las funciones de verificación de Jarvis frente a la geometría real.
"""
import math
import sys

sys.path.insert(0, r"C:\Jarvis")
import importlib
import cad_atomic_lib as L
import cad_validator as V

R = []


def caso(nombre, esperado_vol_mm3, esperado_caja, construir, app):
    doc = L.create_part_doc(app)
    try:
        model = construir(doc)
        vol_real = float(model.Body.Volume) * 1e9
        ok_feat = L.verify_feature_status(model)[0]
        props = L.get_model_physical_properties(model)
        health = V.validate_part_model_health(doc)
        caja = props.get("bounding_box_mm", {})
        caja_t = tuple(sorted([caja.get("x", 0), caja.get("y", 0), caja.get("z", 0)]))
        R.append({
            "caso": nombre,
            "vol_real_mm3": round(vol_real, 1), "vol_esperado_mm3": round(esperado_vol_mm3, 1),
            "geometria_ok": abs(vol_real - esperado_vol_mm3) < 0.01 * esperado_vol_mm3,
            "verify_feature_status": ok_feat,
            "caja_jarvis_mm": caja_t, "caja_esperada_mm": tuple(sorted(esperado_caja)),
            "health_valid": health.get("valid"), "health_caja": health.get("bounding_box_mm"),
            "fallidas": health.get("failed_features"), "avisos": health.get("warned_features", "—"),
        })
    except Exception as e:
        R.append({"caso": nombre, "EXCEPCION": f"{type(e).__name__}: {e}"})
    finally:
        try:
            doc.Close(False)
        except Exception:
            pass


def bloque_agujero(doc):
    ps, prof = L.add_sketch_profile(doc, 1)
    ls = [L.add_line(prof, -0.05, -0.04, 0.05, -0.04), L.add_line(prof, 0.05, -0.04, 0.05, 0.04),
          L.add_line(prof, 0.05, 0.04, -0.05, 0.04), L.add_line(prof, -0.05, 0.04, -0.05, -0.04)]
    L.close_profile_keypoints(prof, ls)
    model = L.create_base_protrusion(doc, prof, 0.030)
    ps, prof = L.add_sketch_profile(doc, 1)
    prof.Circles2d.AddByCenterRadius(0.0, 0.0, 0.0125)
    L.add_extruded_cutout(model, prof, 0.080, L.igRight, L.igSymmetric)   # ±40 mm: pasante
    return model


def cilindro_ranura(doc):
    ps, prof = L.add_sketch_profile(doc, 1)
    prof.Circles2d.AddByCenterRadius(0.0, 0.0, 0.030)
    model = L.create_base_protrusion(doc, prof, 0.080, L.igSymmetric)     # z de -40 a +40 mm
    ps, prof = L.add_sketch_profile(doc, 3)
    axis = L.add_line(prof, 0.0, 0.0, 0.0, 0.100)
    ls = [L.add_line(prof, 0.025, 0.030, 0.031, 0.030), L.add_line(prof, 0.031, 0.030, 0.031, 0.036),
          L.add_line(prof, 0.031, 0.036, 0.025, 0.036), L.add_line(prof, 0.025, 0.036, 0.025, 0.030)]
    L.close_profile_keypoints(prof, ls)
    L.add_revolved_cutout(model, prof, axis)
    return model


def main():
    app = L.connect_or_launch_solidedge()
    vol1 = 100 * 80 * 30 - math.pi * 12.5 ** 2 * 30
    caso("bloque 100x80x30 + agujero Ø25", vol1, (100, 80, 30), bloque_agujero, app)
    # Ranura anular: anillo r 25..30 mm, alto 6 mm (el resto del corte cae fuera del cilindro)
    vol2 = math.pi * 30 ** 2 * 80 - math.pi * (30 ** 2 - 25 ** 2) * 6
    caso("cilindro Ø60x80 + ranura anular", vol2, (60, 60, 80), cilindro_ranura, app)

    # Perfil ABIERTO (3 lados): con el parche debe detenerse con ValueError
    def perfil_abierto(doc):
        ps, prof = L.add_sketch_profile(doc, 1)
        L.add_line(prof, 0, 0, 0.05, 0); L.add_line(prof, 0.05, 0, 0.05, 0.03); L.add_line(prof, 0.05, 0.03, 0, 0.03)
        return L.create_base_protrusion(doc, prof, 0.01)
    caso("perfil abierto (debe detenerse)", 1.0, (0, 0, 0), perfil_abierto, app)

    # Volumen quitado: corte bueno vs. corte que no toca la pieza
    if hasattr(L, "verify_removed_volume"):
        doc = L.create_part_doc(app)
        try:
            ps, prof = L.add_sketch_profile(doc, 1)
            ls = [L.add_line(prof, -0.05, -0.04, 0.05, -0.04), L.add_line(prof, 0.05, -0.04, 0.05, 0.04),
                  L.add_line(prof, 0.05, 0.04, -0.05, 0.04), L.add_line(prof, -0.05, 0.04, -0.05, -0.04)]
            L.close_profile_keypoints(prof, ls)
            model = L.create_base_protrusion(doc, prof, 0.030)
            esperado = math.pi * 0.0125 ** 2 * 0.030
            for nombre, cx in [("agujero dentro de la pieza", 0.0), ("agujero FUERA de la pieza", 0.2)]:
                antes = float(model.Body.Volume)
                ps, prof = L.add_sketch_profile(doc, 1)
                prof.Circles2d.AddByCenterRadius(cx, 0.0, 0.0125)
                L.add_extruded_cutout(model, prof, 0.080, L.igRight, L.igSymmetric)
                ok, quitado = L.verify_removed_volume(model, antes, esperado)
                R.append({"caso": "volumen quitado: " + nombre, "verify_removed_volume": ok,
                          "estado_operacion_ok": L.verify_feature_status(model)[0],
                          "quitado_mm3": round(quitado * 1e9, 1), "esperado_mm3": round(esperado * 1e9, 1)})
        finally:
            doc.Close(False)

    # Lógica de estado con objetos simulados (sin Solid Edge)
    class F:
        def __init__(s, st): s.Status, s.Suppressed, s.Name = st, False, "f"
    class Fs:
        def __init__(s, st): s._f = F(st); s.Count = 1
        def Item(s, i): return s._f
    class M:
        def __init__(s, st): s.Features = Fs(st)
    for st, nombre in [(1216476310, "OK"), (1216476311, "FALLÓ"), (1216476312, "AVISO"), (1216476313, "SUPRIMIDA")]:
        R.append({"caso": f"estado simulado {nombre}", "verify_feature_status": L.verify_feature_status(M(st))[0]})

    for r in R:
        print(r)


if __name__ == "__main__":
    main()
