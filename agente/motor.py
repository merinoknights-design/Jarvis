"""
"Motor" por pasos y video del mecanismo (JRV-30, JRV-31). 2026-10-30. Nunca guarda.

Solid Edge 2026 no tiene objeto ni comando "Motor" en su API, y DragComponentRotation se puede llamar pero no
mueve nada (2026-10-30). Esto usa la técnica probada con el Cardán: pedir giros pequeños con PutMatrix a la pieza
motriz (el solver concede menos, como al arrastrarla con el ratón) y medir cómo la sigue el resto, comprobando en
cada paso que ninguna relación se rompa. Con --video captura un fotograma por paso y arma un MP4 con ffmpeg.

Uso:
  python -X utf8 motor.py <ensamble.asm> --pieza "eje entrada.par:1" [--diametro 20] [--seguir "Eje de salida1.par:1"]
         [--grados 360] [--paso 30] [--video C:\\ruta\\giro.mp4] [--fps 12]
  --diametro: cilindro de la pieza motriz que define el eje de giro (por defecto, el de mayor área).
Última línea:  @@RESULTADO@@ {json}
"""
import argparse
import json
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, r"C:\Jarvis")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import se_com_seguro as se  # noqa: E402
import acciones as A  # noqa: E402

MARCA = "@@RESULTADO@@"
MM = 0.001


def _unit(v):
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def _rot(u, th):
    """Matriz de rotación 3x3 de ángulo th alrededor del vector unitario u (Rodrigues)."""
    c, s, x, y, z = math.cos(th), math.sin(th), u[0], u[1], u[2]
    return [[c + x * x * (1 - c), x * y * (1 - c) - z * s, x * z * (1 - c) + y * s],
            [y * x * (1 - c) + z * s, c + y * y * (1 - c), y * z * (1 - c) - x * s],
            [z * x * (1 - c) - y * s, z * y * (1 - c) + x * s, c + z * z * (1 - c)]]


def girar_matriz(M, punto, u, th):
    """Gira la pose M (convención GetMatrix) alrededor de la recta (punto, u)."""
    Q = _rot(u, th)
    R = [[M[4 * j + i] for j in range(3)] for i in range(3)]
    t = [M[12], M[13], M[14]]
    R2 = [[sum(Q[i][k] * R[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
    t2 = [sum(Q[i][k] * (t[k] - punto[k]) for k in range(3)) + punto[i] for i in range(3)]
    out = list(M)
    for i in range(3):
        for j in range(3):
            out[4 * j + i] = R2[i][j]
    out[12], out[13], out[14] = t2
    return out


def eje_de(occ, diametro=None):
    """(punto, dirección) del eje de un cilindro de la pieza, en coordenadas de PIEZA."""
    mejor = None
    for c in se.caras(occ):
        d = se.describir(c)
        if d["tipo"] != "cilindro":
            continue
        if diametro and abs(2 * d["radio"] / MM - diametro) > 0.02:
            continue
        if mejor is None or d["area"] > mejor["area"]:
            mejor = d
    if mejor is None:
        raise ValueError("%s: no hay cilindro%s" % (occ.Name, " de Ø%s mm" % diametro if diametro else ""))
    return mejor["base"], _unit(mejor["eje"])


def angulo_alrededor(M0, M1, eje_part, eje_asm):
    """Ángulo (°) que giró la pieza entre las poses M0 y M1 alrededor de su eje (eje_asm en el ensamble)."""
    ref = _unit(_cross(eje_part, [1, 0, 0] if abs(eje_part[0]) < 0.9 else [0, 1, 0]))
    a0 = _unit(_proj(se.a_ensamble_dir(M0, ref), eje_asm))
    a1 = _unit(_proj(se.a_ensamble_dir(M1, ref), eje_asm))
    return math.degrees(math.atan2(_dot(_cross(a0, a1), eje_asm), _dot(a0, a1)))


def _proj(v, u):
    k = _dot(v, u)
    return [v[i] - k * u[i] for i in range(3)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("asm")
    ap.add_argument("--pieza", required=True)
    ap.add_argument("--diametro", type=float)
    ap.add_argument("--seguir")
    ap.add_argument("--grados", type=float, default=360.0)
    ap.add_argument("--paso", type=float, default=30.0)
    ap.add_argument("--max-pasos", type=int, default=300)
    ap.add_argument("--video")
    ap.add_argument("--fps", type=int, default=12)
    a = ap.parse_args()

    if a.video:
        se.guardia_disco()
        if Path(a.video).exists():
            raise ValueError("%s ya existe: elija otro nombre para el video." % a.video)
    app = se.conectar()
    doc, mio = A.tomar_documento(app, a.asm)
    frames = Path(tempfile.mkdtemp(prefix="jarvis_motor_")) if a.video else None
    filas, fallos = [], []
    try:
        occ = {doc.Occurrences.Item(i).Name: doc.Occurrences.Item(i) for i in range(1, doc.Occurrences.Count + 1)}
        if a.pieza not in occ:
            raise ValueError("No existe la ocurrencia '%s'. Hay: %s" % (a.pieza, sorted(occ)[:20]))
        mot = occ[a.pieza]
        seg = occ.get(a.seguir) if a.seguir else None
        base_p, eje_p = eje_de(mot, a.diametro)
        M0 = se.matriz(mot)
        punto, u = se.a_ensamble_punto(M0, base_p), _unit(se.a_ensamble_dir(M0, eje_p))
        if seg is not None:
            sb, se_eje = eje_de(seg)
            S0 = se.matriz(seg)
            u_seg = _unit(se.a_ensamble_dir(S0, se_eje))
        if frames:
            se.reintentar(doc.Activate)
            A.traer_al_frente(app)
            view = app.ActiveWindow.View
            view.ApplyNamedView("Iso")
            view.Fit()
        acum = acum_seg = 0.0
        Mprev, Sprev = M0, (S0 if seg is not None else None)
        k = 0
        while abs(acum) < a.grados and k < a.max_pasos:
            k += 1
            se.reintentar(mot.PutMatrix, girar_matriz(Mprev, punto, u, math.radians(a.paso)), True)
            Mk = se.matriz(mot)
            acum += angulo_alrededor(Mprev, Mk, eje_p, u)
            fila = {"paso": k, "motriz_acum": round(acum, 2)}
            if seg is not None:
                Sk = se.matriz(seg)
                acum_seg += angulo_alrededor(Sprev, Sk, se_eje, u_seg)
                fila["seguidora_acum"] = round(acum_seg, 2)
                Sprev = Sk
            malas = [i for i in range(1, doc.Relations3d.Count + 1) if doc.Relations3d.Item(i).Status != se.REL_SOLVED]
            fila["relaciones_no_resueltas"] = len(malas)
            filas.append(fila)
            if malas:
                fallos.append(fila)
                break
            if frames:
                app.DoIdle()
                view.SaveAsImage(str(frames / ("f%04d.png" % k)), 1280, 800)
            Mprev = Mk
        res = {"ok": not fallos and abs(acum) >= a.grados, "pasos": len(filas), "motriz_grados": round(acum, 2),
               "fallos": fallos[:5], "muestra": filas[:: max(1, len(filas) // 8)]}
        if seg is not None:
            res["seguidora_grados"] = round(acum_seg, 2)
            res["relacion_transmision"] = round(acum_seg / acum, 4) if acum else None
        if frames and filas:
            ffmpeg = shutil.which("ffmpeg")
            if not ffmpeg:
                res["video_error"] = "ffmpeg no está en el PATH"
            else:
                r = subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-framerate", str(a.fps), "-i",
                                    str(frames / "f%04d.png"), "-pix_fmt", "yuv420p", "-vf",
                                    "scale=trunc(iw/2)*2:trunc(ih/2)*2", a.video], capture_output=True, text=True)
                res["video"] = a.video if r.returncode == 0 and Path(a.video).exists() else None
                if r.returncode != 0:
                    res["video_error"] = r.stderr[-500:]
        return res
    finally:
        if mio:
            A.cerrar(app, doc)     # SIN guardar: el archivo no cambia
        if frames:
            shutil.rmtree(frames, ignore_errors=True)


if __name__ == "__main__":
    try:
        res = main()
    except Exception as e:
        res = {"ok": False, "error": se.describir_error(e) if not isinstance(e, ValueError) else str(e)}
    print(MARCA, json.dumps(res, ensure_ascii=False, default=str))
    sys.exit(0 if res.get("ok") else 1)
