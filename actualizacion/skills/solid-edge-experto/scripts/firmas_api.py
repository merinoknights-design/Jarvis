"""
Consulta la API COM de Solid Edge directamente en sus type libraries (SOLO LECTURA: no abre Solid Edge).

Uso (con el Python de Jarvis, que trae pywin32):
  python -X utf8 firmas_api.py <tlb> <Tipo> [patron]      firmas de los métodos de <Tipo> que contienen <patron>
  python -X utf8 firmas_api.py <tlb> --buscar <patron>     tipos y miembros cuyo nombre contiene <patron>
  python -X utf8 firmas_api.py constant.tlb --enum <Enum>  valores de una enumeración (p. ej. IDs de comando)

Ejemplos:
  firmas_api.py assembly.tlb AssemblyDocument Explode
  firmas_api.py assembly.tlb Relations3d Add
  firmas_api.py draft.tlb --buscar Balloon
  firmas_api.py constant.tlb --enum ExplodeCommandConstants

Librerías habituales (en la carpeta Program de Solid Edge; se detecta sola con el registro de Windows): framewrk.tlb, fwksupp.tlb, Part.tlb, assembly.tlb, draft.tlb, geometry.tlb, constant.tlb.
Que un método exista no garantiza que funcione desde pywin32 dinámico: los parámetros [out] pueden necesitar makepy o VARIANT byref.
"""
import re
import sys
from pathlib import Path

import pythoncom

def _carpeta_programa():
    """Carpeta de Edge.exe según el registro: cada instalación puede estar en otro sitio."""
    import winreg
    with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"SolidEdge.Application\CLSID") as k:
        clsid = winreg.QueryValue(k, None)
    with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, "CLSID\\%s\\LocalServer32" % clsid) as k:
        return Path(re.match(r'\s*"?(.+?edge\.exe)', winreg.QueryValue(k, None), re.I).group(1)).parent


PROG = _carpeta_programa()
VT = {2: "short", 3: "long", 4: "float", 5: "double", 7: "date", 8: "BSTR", 9: "IDispatch", 11: "bool", 12: "VARIANT",
      13: "IUnknown", 16: "char", 17: "byte", 18: "ushort", 19: "ulong", 22: "int", 23: "uint", 24: "void",
      25: "HRESULT", 26: "ptr", 27: "SAFEARRAY", 29: "userdef"}
INVOKE = {1: "", 2: "[get] ", 4: "[put] ", 8: "[putref] "}


def tipo(td, ti):
    vt = td[0] if isinstance(td, tuple) else td
    while isinstance(vt, tuple):
        td, vt = vt, vt[0]
    if isinstance(td, tuple) and len(td) > 1:
        inner = td[1]
        if vt == 26:
            return tipo(inner, ti) + "*"
        if vt == 27:
            return "SAFEARRAY(" + tipo(inner, ti) + ")"
        if vt == 29:
            try:
                return ti.GetRefTypeInfo(inner).GetDocumentation(-1)[0]
            except Exception:
                return "userdef"
    return VT.get(vt & 0xFFF, str(vt))


def firma(ti, nombre_tipo, fd):
    names = ti.GetNames(fd.memid)
    params = []
    for j, a in enumerate(fd.args):
        f = [s for bit, s in ((1, "in"), (2, "out"), (8, "retval"), (16, "opt")) if a[1] & bit]
        nombre = names[j + 1] if j + 1 < len(names) else f"p{j}"
        params.append(f"{nombre}: {tipo(a[0], ti)}[{','.join(f)}]")
    return f"{INVOKE.get(fd.invkind, '')}{nombre_tipo}.{names[0]}({', '.join(params)}) -> {tipo(fd.rettype, ti)}"


def abrir(tlb):
    p = Path(tlb) if Path(tlb).is_absolute() else PROG / tlb
    return pythoncom.LoadTypeLib(str(p))


def tipos(lib):
    for i in range(lib.GetTypeInfoCount()):
        yield lib.GetDocumentation(i)[0], lib.GetTypeInfo(i)


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 1
    lib = abrir(argv[1])
    if argv[2] == "--enum":
        for n, ti in tipos(lib):
            if n == argv[3]:
                attr = ti.GetTypeAttr()
                for k in range(attr.cVars):
                    vd = ti.GetVarDesc(k)
                    print(f"{ti.GetNames(vd.memid)[0]} = {vd.value}")
        return 0
    if argv[2] == "--buscar":
        pat = re.compile(argv[3], re.I)
        for n, ti in tipos(lib):
            attr = ti.GetTypeAttr()
            hits = sorted({ti.GetNames(ti.GetFuncDesc(i).memid)[0] for i in range(attr.cFuncs)
                           if pat.search(ti.GetNames(ti.GetFuncDesc(i).memid)[0])})
            hits += [ti.GetNames(ti.GetVarDesc(i).memid)[0] for i in range(attr.cVars)
                     if pat.search(ti.GetNames(ti.GetVarDesc(i).memid)[0])]
            if pat.search(n) or hits:
                print(f"{n}: {', '.join(hits[:40])}")
        return 0
    objetivo, pat = argv[2], re.compile(argv[3] if len(argv) > 3 else ".", re.I)
    vistos = set()
    for n, ti in tipos(lib):
        if n not in (objetivo, "_I" + objetivo + "Auto", "I" + objetivo):
            continue
        attr = ti.GetTypeAttr()
        for i in range(attr.cFuncs):
            fd = ti.GetFuncDesc(i)
            nombre = ti.GetNames(fd.memid)[0]
            if pat.search(nombre):
                s = firma(ti, objetivo, fd)
                if s not in vistos:
                    vistos.add(s)
                    print(s)
    if not vistos:
        print(f"Nada en {objetivo} con '{pat.pattern}'. Prueba --buscar {objetivo}.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
