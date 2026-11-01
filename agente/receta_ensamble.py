"""
Ejecutor de recetas de ensamble (JRV-20, JRV-21, JRV-25). 2026-10-30.

Generaliza el método del Cardán: inserta piezas, quita el Fijar que deja AddByFilename (salvo las fijas),
preposiciona si se indica, crea las relaciones eligiendo caras por REGLAS GEOMÉTRICAS (ver caras.py), comprueba
que cada relación quede resuelta y se detiene SIN GUARDAR al primer fallo. Al final, orden y nombres del PathFinder.

Uso:  python -X utf8 receta_ensamble.py <receta.json> [--cerrar]
Última línea:  @@RESULTADO@@ {json}

Receta (mm y grados; caras en coordenadas de cada PIEZA; usa la acción `caras` para verlas):
{
  "nombre": "...", "salida": "C:\\...\\Ensamble.asm",
  "piezas": [
    {"id": "base", "archivo": "C:\\...\\Base.par", "fija": true},
    {"id": "tapa", "archivo": "...", "posicion": [0, 0, 30], "rotacion": [0, 0, 0]}      (preposición opcional)
  ],
  "relaciones": [
    {"tipo": "coincidir",      "a": {"pieza": "tapa", "cara": SEL}, "b": {"pieza": "base", "cara": SEL}, "desfase": 0},
    {"tipo": "alinear_plano",  "a": {...}, "b": {...}, "desfase": 0},
    {"tipo": "alinear_eje",    "a": {...}, "b": {...}, "alineados": false, "bloquear_giro": false},
    {"tipo": "insertar",       "a": {"pieza": "eje", "eje": SEL_CIL, "cara": SEL_PLANO}, "b": {...}},
    {"tipo": "angulo",         "a": {...}, "b": {...}, "angulo": 30},
    {"tipo": "tangente",       "a": {"pieza": ..., "cara": SEL_CIL}, "b": {"pieza": ..., "cara": SEL_PLANO}, "desfase": 0},
    {"tipo": "conjunto_rigido", "piezas": ["tapa", "eje"]}
  ],
  "orden_pathfinder": ["base", "tapa", ...],      (opcional)
  "nombres": {"tapa": "Tapa superior"}             (opcional: nombre visible de la ocurrencia en el PathFinder)
}
"a" es la pieza que se mueve; "b", la de referencia. "coincidir" = caras enfrentadas (normales exteriores opuestas);
"alinear_plano" = misma orientación y coplanares.
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, r"C:\Jarvis")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import se_com_seguro as se  # noqa: E402
import caras as C  # noqa: E402

MARCA = "@@RESULTADO@@"
MM = 0.001


class Parada(RuntimeError):
    pass


def matriz_desde(pos_mm, rot_deg):
    """Matriz 4x4 (16 valores, convención de GetMatrix: R[i][j] = M[4j+i], traslación en 12..14)."""
    rx, ry, rz = (math.radians(a) for a in rot_deg)
    cx, sx, cy, sy, cz, sz = math.cos(rx), math.sin(rx), math.cos(ry), math.sin(ry), math.cos(rz), math.sin(rz)
    R = [[cy * cz, sx * sy * cz - cx * sz, cx * sy * cz + sx * sz],
         [cy * sz, sx * sy * sz + cx * cz, cx * sy * sz - sx * cz],
         [-sy, sx * cy, cx * cy]]
    M = [0.0] * 16
    for i in range(3):
        for j in range(3):
            M[4 * j + i] = R[i][j]
    M[12], M[13], M[14] = (v * MM for v in pos_mm)
    M[15] = 1.0
    return M


class Ensamblador:
    def __init__(self, app, asm, bit):
        self.app, self.asm, self.bit = app, asm, bit
        self.occ = {}
        self._caras = {}

    def caras_de(self, pid):
        if pid not in self._caras:
            o = self.occ[pid]
            fs = o.OccurrenceDocument.Models.Item(1).Body.Faces(1)
            self._caras[pid] = [fs.Item(i) for i in range(1, fs.Count + 1)]
        return self._caras[pid]

    def ref(self, pid, sel):
        if pid not in self.occ:
            raise Parada("Pieza desconocida '%s'" % pid)
        try:
            i, cara, desc = C.elegir(self.caras_de(pid), sel)
        except ValueError as e:
            raise Parada("%s: %s" % (pid, e))
        return se.ref(self.asm, self.occ[pid], cara), cara, desc

    def comprobar(self, rel, nombre):
        st = rel.Status
        if st != se.REL_SOLVED:
            raise Parada("La relación '%s' no quedó resuelta (estado %s): caras incompatibles o sobredefinición." % (nombre, st))

    def planar(self, a, b, alineadas, desfase, nombre):
        ra, ca, _ = self.ref(a["pieza"], a["cara"])
        rb, cb, _ = self.ref(b["pieza"], b["cara"])
        pa, pb = se.puntos_arista(ca), se.puntos_arista(cb)
        if not pa or not pb:
            raise Parada("'%s': no se obtuvieron puntos de las caras." % nombre)
        # True = Coincidir respecto de las normales EXTERIORES (verificado 2026-10-28); False = Alinear plano
        rel = se.reintentar(self.asm.Relations3d.AddPlanar, ra, rb, not alineadas, pa[0], pb[0])
        if desfase:
            rel.Offset = float(desfase) * MM
        self.comprobar(rel, nombre)
        return rel

    def axial(self, a, b, alineados, bloquear, nombre, clave_a="cara", clave_b="cara"):
        ra, _, _ = self.ref(a["pieza"], a[clave_a])
        rb, _, _ = self.ref(b["pieza"], b[clave_b])
        # AddAxial nace con FixedRotate=True y el solver hace saltar la pieza: crear dentro de DelayCompute
        self.app.DelayCompute = True
        try:
            rel = se.reintentar(self.asm.Relations3d.AddAxial, ra, rb, bool(alineados))
            rel.FixedRotate = bool(bloquear)
        finally:
            self.app.DelayCompute = False
        self.comprobar(rel, nombre)
        return rel

    def angulo(self, a, b, grados, nombre, medida=None):
        """AddAngular exige los elementos que definen el plano de medida (con None da E_INVALIDARG, 2026-10-30).
        medida = {"a": {"pieza", "cara"}, "b": {...}}: p. ej. las dos caras que ya están en contacto."""
        ra, _, _ = self.ref(a["pieza"], a["cara"])
        rb, _, _ = self.ref(b["pieza"], b["cara"])
        if medida:
            ma, _, _ = self.ref(medida["a"]["pieza"], medida["a"]["cara"])
            mb, _, _ = self.ref(medida["b"]["pieza"], medida["b"]["cara"])
        else:
            ma, mb = ra, rb
        rel = se.reintentar(self.asm.Relations3d.AddAngular, ra, rb, False, False, ma, mb,
                            math.radians(float(grados)), True, True, True)
        self.comprobar(rel, nombre)
        return rel

    def tangente(self, a, b, desfase, nombre):
        ra, ca, _ = self.ref(a["pieza"], a["cara"])
        rb, cb, _ = self.ref(b["pieza"], b["cara"])
        rel = se.reintentar(self.asm.Relations3d.AddTangent, ra, rb, se.puntos_arista(ca)[0], se.puntos_arista(cb)[0],
                            float(desfase or 0) * MM, True)
        self.comprobar(rel, nombre)
        return rel

    def rigido(self, ids, nombre):
        occs = [self.occ[i] for i in ids]
        rel = se.reintentar(self.asm.Relations3d.AddRigidSet, len(occs), occs)
        self.comprobar(rel, nombre)
        return rel


def construir(receta, cerrar_al_final=False):
    salida = Path(receta["salida"])
    if salida.exists():
        raise Parada("%s ya existe: elija otra 'salida'." % salida)
    se.guardia_disco()
    bit = se.Bitacora(salida.with_name(salida.stem + "_bitacora.csv"))
    app = se.conectar()
    asm = se.reintentar(app.Documents.Add, "SolidEdge.AssemblyDocument")
    E = Ensamblador(app, asm, bit)
    pasos = []
    try:
        for p in receta["piezas"]:
            archivo = Path(p["archivo"])
            if not archivo.exists():
                raise Parada("No existe la pieza %s" % archivo)
            o = se.insertar(asm, archivo)
            E.occ[p["id"]] = o
            if not p.get("fija"):
                se.quitar_fijo(o)
            if "posicion" in p or "rotacion" in p:
                o.PutMatrix(matriz_desde(p.get("posicion", [0, 0, 0]), p.get("rotacion", [0, 0, 0])), True)
            bit.anotar("ensamble", p["id"], "", "insertar", archivo.name, "ok")
        for k, r in enumerate(receta.get("relaciones", []), 1):
            t = r["tipo"]
            nombre = r.get("nombre") or "%d. %s %s" % (k, t, "/".join(str(x) for x in (r.get("a", {}).get("pieza"),
                                                                                     r.get("b", {}).get("pieza")) if x))
            if t == "coincidir":
                E.planar(r["a"], r["b"], False, r.get("desfase"), nombre)
            elif t == "alinear_plano":
                E.planar(r["a"], r["b"], True, r.get("desfase"), nombre)
            elif t == "alinear_eje":
                E.axial(r["a"], r["b"], r.get("alineados", False), r.get("bloquear_giro", False), nombre)
            elif t == "insertar":
                E.axial(r["a"], r["b"], r.get("alineados", False), r.get("bloquear_giro", False), nombre + " (eje)",
                        "eje", "eje")
                E.planar(r["a"], r["b"], False, r.get("desfase"), nombre + " (cara)")
            elif t == "angulo":
                E.angulo(r["a"], r["b"], r["angulo"], nombre, r.get("plano_medida"))
            elif t == "tangente":
                E.tangente(r["a"], r["b"], r.get("desfase"), nombre)
            elif t == "conjunto_rigido":
                E.rigido(r["piezas"], nombre)
            else:
                raise Parada("Tipo de relación desconocido: %s" % t)
            pasos.append({"relacion": nombre, "estado": "resuelta"})
            bit.anotar("ensamble", "", "", nombre, t, "resuelta")
            print("  %-45s resuelta" % nombre)
        # Orden y nombres del PathFinder (JRV-25)
        orden = receta.get("orden_pathfinder", [])
        for previo, sig in zip(orden, orden[1:]):
            # Ojo: con AfterTarget=True el orden salió exactamente invertido (2026-10-30): el efectivo es False.
            se.reintentar(asm.Occurrences.ReorderOccurrence, E.occ[sig], E.occ[previo], False)
        for pid, nombre in receta.get("nombres", {}).items():
            E.occ[pid].Name = nombre
        est = se.estado_ensamble(asm)
        malas = [o["nombre"] for o in est["ocurrencias"] if o["status"] in (se.OCC_OVER, se.OCC_NOT_CONSISTENT)]
        no_resueltas = [r["i"] for r in est["relaciones"] if r["status"] != se.REL_SOLVED]
        if malas or no_resueltas:
            raise Parada("Ensamble con problemas: sobredefinidas/inconsistentes %s; relaciones no resueltas %s"
                         % (malas, no_resueltas))
        se.guardar_nuevo(asm, salida)
        bit.anotar("guardar", "", "", str(salida), "", "ok")
        res = {"ok": True, "archivo": str(salida), "relaciones": pasos,
               "ocurrencias": [{"nombre": o["nombre"], "fija": o["fija"], "status": o["status"]} for o in est["ocurrencias"]],
               "orden_pathfinder": [asm.Occurrences.Item(i).Name for i in range(1, asm.Occurrences.Count + 1)]}
        if cerrar_al_final:
            se.reintentar(asm.Close, False)
        return res
    except Exception as e:
        msg = str(e) if isinstance(e, (Parada, se.ErrorSolidEdge, ValueError)) else se.describir_error(e)
        bit.anotar("PARADA", "", "", "", "", "detenido", msg)
        return {"ok": False, "error": msg, "relaciones": pasos,
                "nota": "No se guardó nada. El ensamble queda abierto en Solid Edge para revisarlo."}


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    try:
        res = construir(json.loads(Path(argv[1]).read_text(encoding="utf-8-sig")), "--cerrar" in argv)
    except Parada as e:
        res = {"ok": False, "error": str(e)}
    except Exception as e:
        res = {"ok": False, "error": se.describir_error(e)}
    print(MARCA, json.dumps(res, ensure_ascii=False, default=str))
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
