"""
Batería de regresión de Jarvis (JRV-64). 2026-10-30.

Ejecuta, en una carpeta NUEVA de %TEMP%\\jarvis_ensayos\\regresion_<fecha>\\, todo lo que se ha construido y
probado: verificación de piezas (JRV-11), recetas de pieza (brida, eje, bloques), receta de ensamble con las
siete clases de relación, inspección, captura, exportación STEP, planos de pieza y de ensamble con PDF, y
(opcional, --cardan) el motor sobre una copia del Cardán. No toca ningún archivo del usuario.

Uso:  C:\\Jarvis\\venv\\Scripts\\python.exe -X utf8 C:\\Jarvis\\pruebas\\correr_todo.py [--cardan]
Ejecútala después de cualquier parche a Jarvis. Si Solid Edge se comporta raro (piezas que no siguen al
mecanismo), ciérralo sin documentos abiertos y repítela.
"""
import datetime
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PY = sys.executable
AG = RAIZ / "agente"
REC = RAIZ / "pruebas" / "recetas"
MARCA = "@@RESULTADO@@"


def correr(args, timeout=900):
    t0 = time.time()
    r = subprocess.run([PY, "-X", "utf8"] + [str(a) for a in args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout)
    res = None
    for linea in reversed(r.stdout.splitlines()):
        if linea.startswith(MARCA):
            res = json.loads(linea[len(MARCA):])
            break
    return r.returncode, res, round(time.time() - t0, 1), r.stdout + r.stderr


def receta_en(carpeta, nombre_json, reemplazos):
    """Copia una receta de prueba cambiando las rutas de salida/piezas a la carpeta de esta corrida."""
    t = (REC / nombre_json).read_text(encoding="utf-8-sig")
    t = t.replace("%ENSAYOS%", str(carpeta).replace("\\", "\\\\"))
    for a, b in reemplazos.items():
        t = t.replace(a, b)
    p = carpeta / nombre_json
    p.write_text(t, encoding="utf-8")
    return p


def main():
    carpeta = Path(os.environ["TEMP"]) / "jarvis_ensayos" / ("regresion_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
    carpeta.mkdir(parents=True)
    filas = []

    def caso(nombre, args, comprobar=lambda r: True, timeout=900, espera_fallo=False):
        rc, res, dur, salida = correr(args, timeout)
        if espera_fallo:      # prueba negativa: la herramienta debe fallar, y por el motivo que se comprueba
            ok = rc != 0 and res is not None and comprobar(res)
        else:
            ok = rc == 0 and (res is None or res.get("ok", True)) and comprobar(res)
        filas.append((nombre, "OK" if ok else "FALLA", dur, "" if ok else (res or {}).get("error", salida[-300:])))
        print("%-46s %-6s %6.1f s %s" % filas[-1])
        return res

    caso("JRV-11 verificación de piezas", [RAIZ / "pruebas" / "regresion_jrv11.py"],
         comprobar=lambda r: True)
    for j in ("brida_prueba_2.json", "eje_prueba.json", "base_prueba.json", "tapa_prueba.json"):
        p = receta_en(carpeta, j, {"Brida_prueba_2.par": "Brida_prueba.par"})
        caso("receta de pieza: " + j, [AG / "receta_pieza.py", p, "--cerrar"])
    p = receta_en(carpeta, "ensamble_prueba.json", {"Ensamble_prueba_2.asm": "Ensamble_prueba.asm"})
    caso("receta de ensamble (7 relaciones)", [AG / "receta_ensamble.py", p, "--cerrar"],
         comprobar=lambda r: len(r.get("relaciones", [])) == 6)
    par, asm = carpeta / "Brida_prueba.par", carpeta / "Ensamble_prueba.asm"
    (carpeta / "p.json").write_text(json.dumps({"ruta": str(asm)}), encoding="utf-8")
    caso("inspeccionar ensamble", [AG / "acciones.py", "inspeccionar", "@" + str(carpeta / "p.json")],
         comprobar=lambda r: r["ocurrencias"] == 5 and not r["relaciones_no_resueltas"] and not r["archivos_faltantes"])
    (carpeta / "c.json").write_text(json.dumps({"ruta": str(asm), "salida": str(carpeta / "ensamble.png")}), encoding="utf-8")
    caso("capturar ensamble", [AG / "acciones.py", "capturar", "@" + str(carpeta / "c.json")])
    (carpeta / "e.json").write_text(json.dumps({"ruta": str(par), "salida": str(carpeta / "Brida.step")}), encoding="utf-8")
    caso("exportar STEP", [AG / "acciones.py", "exportar", "@" + str(carpeta / "e.json")],
         comprobar=lambda r: r["bytes"] > 1000 and r.get("original_sin_cambios", True))
    caso("plano de pieza + PDF", [AG / "plano.py", par, carpeta / "Brida.dft", "--pdf"],
         comprobar=lambda r: r.get("cotas", 0) >= 4 and r.get("pdf"))
    caso("plano de ensamble + lista + PDF", [AG / "plano.py", asm, carpeta / "Ensamble.dft", "--pdf"],
         comprobar=lambda r: r.get("lista_de_piezas_filas") == 4 and r.get("pdf"))
    # 2026-10-31: agujeros con rosca, patrones, choques, tornillería y edición de una pieza existente
    p = receta_en(carpeta, "placa_agujeros.json", {})
    caso("receta: agujeros Ø8, M6 pasante, M5 ciego", [AG / "receta_pieza.py", p, "--cerrar"],
         comprobar=lambda r: [x.get("rosca") for x in r["pasos"][1:]] == [None, "M6", "M5"])
    p = receta_en(carpeta, "brida_patron.json", {})
    caso("receta: patrón circular 6x y rectangular 3x2", [AG / "receta_pieza.py", p, "--cerrar"],
         comprobar=lambda r: [x.get("copias") for x in r["pasos"] if "copias" in x] == [6, 6])
    p = receta_en(carpeta, "choque_prueba.json", {})
    caso("receta de ensamble con choque a propósito", [AG / "receta_ensamble.py", p, "--cerrar"])
    caso("interferencia: detecta el choque", [AG / "interferencia.py", carpeta / "Choque_prueba.asm"],
         comprobar=lambda r: len(r["choques"]) == 1 and r["archivo_sin_cambios"])
    # El ensamble de prueba SÍ tiene un cruce real (un eje atraviesa el disco de la brida, ~4543 mm³): se diseñó para
    # probar relaciones, no para estar libre de choques. Sirve para probar la lista de choques esperados.
    caso("interferencia: choque declarado como esperado", [AG / "interferencia.py", asm, "--esperado", "Brida_prueba.par<>Eje_prueba.par"],
         comprobar=lambda r: not r["choques"] and len(r["esperados_aceptados"]) == 1 and r["archivo_sin_cambios"])
    caso("tornillería del ensamble", [AG / "tornilleria.py", asm], comprobar=lambda r: r["ocurrencias"] == 5)
    lista = caso("editar pieza: listar cotas", [AG / "editar_pieza.py", "listar", par],
                 comprobar=lambda r: r["cotas"] and r["operaciones_con_profundidad"]) or {}
    prof = next(((k, v) for k, v in (lista.get("operaciones_con_profundidad") or {}).items() if isinstance(v, float)), None)
    if prof:
        caso("editar pieza: profundidad +2 mm, pieza nueva",
             [AG / "editar_pieza.py", "cambiar", par, carpeta / "Brida_editada.par", "--profundidad", "%s=%g" % (prof[0], prof[1] + 2)],
             comprobar=lambda r: r["original_sin_cambios"] and r["despues"]["volumen_mm3"] > r["antes"]["volumen_mm3"])
    # 2026-11-01: barrido de choques durante el giro. El cruce eje-brida no depende del giro del eje principal
    caso("barrido: choque constante durante el giro", [AG / "barrido_choques.py", asm, "--pieza", "Eje principal", "--grados", "30"],
         comprobar=lambda r: r["original_sin_cambios"] and any(t["constante"] and t["piezas"] == "Brida_prueba.par <> Eje_prueba.par"
                                                               for t in r["choques"]))
    caso("barrido: se detiene si la pieza no existe", [AG / "barrido_choques.py", asm, "--pieza", "no existe.par:1"],
         comprobar=lambda r: "No existe la ocurrencia" in r.get("error", ""), espera_fallo=True)
    if "--cardan" in sys.argv:
        # Con otro nombre: el usuario puede tener abierto su Cardan.asm y no se abre un segundo documento con el mismo nombre
        copia = carpeta / "Cardan_regresion.asm"
        sys.path.insert(0, str(RAIZ / "cardan"))
        import rutas_cardan
        fuente = next((f for f in (Path(os.environ["TEMP"]) / "jarvis_ensayos" / "cardan_vinculos" / "Cardan.asm", rutas_cardan.ASM) if f.exists()), None)
        if fuente is None:
            raise SystemExit("--cardan: no encuentro Cardan.asm en %s" % rutas_cardan.ASM)
        shutil.copy2(fuente, copia)
        caso("motor sobre copia del Cardán (90°)", [AG / "motor.py", copia, "--pieza", "eje entrada.par:1",
                                                    "--diametro", "14", "--seguir", "Eje de salida1.par:1", "--grados", "90"],
             comprobar=lambda r: abs(abs(r["seguidora_grados"]) - abs(r["motriz_grados"])) < 5)
        caso("barrido del Cardán: oreja de Fork 4 con tuerca 25", [AG / "barrido_choques.py", copia, "--pieza", "eje entrada.par:1", "--diametro", "14",
                                                                   "--grados", "30", "--esperado", "Perno.par<>tuercaM3.par"],
             comprobar=lambda r: r["original_sin_cambios"] and any(t["pareja"] == "Fork.par:4 <> tuercaM3.par:25" and abs(t["max_mm3"] - 2.103) < 0.01
                                                                   for t in r["choques"]) and bool(r["esperados_aceptados"]))
    fallas = [f for f in filas if f[1] != "OK"]
    print("\n%d/%d casos OK · carpeta: %s" % (len(filas) - len(fallas), len(filas), carpeta))
    (carpeta / "informe.json").write_text(json.dumps(filas, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0 if not fallas else 1


if __name__ == "__main__":
    sys.exit(main())
