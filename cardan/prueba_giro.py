"""
Prueba cinemática del Cardán (punto 4 del criterio de terminado), por API.
Gira 'eje entrada' en pasos pequeños alrededor de su eje (como arrastrarlo a mano) y comprueba en
cada paso que la cadena le siga hasta 'Eje de salida1' sin que ninguna relación deje de estar
resuelta, sin que el eje de salida se invierta ni se desplace. Al final cierra el documento SIN
guardar: no cambia el archivo.
Uso: python prueba_giro.py RUTA\\Cardan.asm [grados_totales] [grados_pedidos_por_paso]
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import se_com_seguro as se  # noqa: E402
import ensamblar_cardan as ec  # noqa: E402


def angulo(P0, P1, eje, ref):
    a0, a1 = ec.unit(ec.perp(P0.d(ref), eje)), ec.unit(ec.perp(P1.d(ref), eje))
    return math.degrees(math.atan2(ec.dot(ec.cross(a0, a1), eje), ec.dot(a0, a1)))


def ref_perp(eje_part):
    return ec.unit(ec.perp([1, 0, 0] if abs(eje_part[0]) < .9 else [0, 1, 0], eje_part))


def main(ruta, vuelta=360.0, paso=30.0, max_pasos=200):
    """Pide giros de 'paso' grados (el solver concede menos, como al arrastrar) hasta que la
    entrada acumula 'vuelta' grados."""
    ruta = Path(ruta)
    est = ec.leer_estado(ruta)
    app = se.conectar()
    asm = ec.abrir_asm_limpio(app, ruta)
    ens = ec.Ensamble(asm, ruta, 0, None)
    R = est["roles"]
    eje = ec.occ_por_nombre(asm, R["eje_entrada"])
    sal = ec.occ_por_nombre(asm, R["eje_salida"])
    b_in, b_out = ec.Geo.de(eje).brida_unica(), ec.Geo.de(sal).brida_unica()
    P0, S0 = ens.pose(eje), ens.pose(sal)
    eje_in, pto_in = ec.unit(P0.d(b_in["eje"])), P0.p(b_in["centro_linea"])
    eje_out = ec.unit(S0.d(b_out["eje"]))
    c_out0 = S0.p(b_out["centro_apoyo"])
    filas, fallos = [], []
    acum_in = acum_out = 0.0
    try:
        Pprev, Sprev = P0, S0
        k = 0
        while abs(acum_in) < vuelta and k < max_pasos:
            k += 1
            objetivo = Pprev.girar_en_torno(pto_in, eje_in, math.radians(paso))
            se.reintentar(eje.PutMatrix, objetivo.matriz(), True)
            Pk, Sk = ens.pose(eje), ens.pose(sal)
            acum_in += angulo(Pprev, Pk, eje_in, ref_perp(b_in["eje"]))
            acum_out += angulo(Sprev, Sk, eje_out, ref_perp(b_out["eje"]))
            sentido = ec.dot(ec.unit(Sk.d(b_out["eje"])), eje_out)
            desplaz = ec.norm(ec.sub(Sk.p(b_out["centro_apoyo"]), c_out0))
            malas = [i for i in range(1, asm.Relations3d.Count + 1) if asm.Relations3d.Item(i).Status != se.REL_SOLVED]
            fila = {"paso": k, "entrada_acum": round(acum_in, 2), "salida_acum": round(acum_out, 2),
                    "sentido_eje_salida": round(sentido, 6), "desplaz_salida_mm": round(desplaz * 1000, 4),
                    "relaciones_no_resueltas": len(malas)}
            filas.append(fila)
            if malas or sentido < 0.999999 or desplaz > 5e-5:
                fallos.append(fila)
            Pprev, Sprev = Pk, Sk
    finally:
        asm.Close(False)
        print("Documento cerrado SIN guardar (el archivo no cambia).")
    for f in filas[:: max(1, len(filas) // 12)] + [filas[-1]]:
        print(json.dumps(f, ensure_ascii=False))
    ok = not fallos and abs(acum_in) >= vuelta and abs(abs(acum_out) - abs(acum_in)) < 5.0
    (ruta.with_name("prueba_giro.json")).write_text(json.dumps({"ok": ok, "fallos": fallos, "pasos": filas}, indent=1,
                                                               ensure_ascii=False), encoding="utf-8")
    print("PRUEBA DE GIRO:", ("OK — entrada %.0f°, salida %.0f°, sin relaciones rotas ni saltos" % (acum_in, acum_out))
          if ok else "FALLA: %s" % (fallos[:3] or "la cadena no completó la vuelta"))
    return 0 if ok else 1


if __name__ == "__main__":
    a = sys.argv[1:]
    sys.exit(main(a[0] if a else ec.ASM_DEFECTO, float(a[1]) if len(a) > 1 else 360.0, float(a[2]) if len(a) > 2 else 30.0))
