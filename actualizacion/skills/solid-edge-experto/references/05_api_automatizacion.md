# 05 — API COM de Solid Edge 2026 desde Python (pywin32)

Capítulo de referencia para automatizar Solid Edge 2026 (versión interna **226.00**) con Python 3.11 x64 + pywin32, como lo hace Jarvis en este equipo. Cubre qué se puede automatizar en **piezas, ensambles, explosionados, movimiento y planos**, cómo se hace, qué **no** se puede y cuál es la alternativa en ese caso (`StartCommand`, C#/.NET o la interfaz).

## Leyenda de etiquetas (léela antes de usar un dato)

| Etiqueta | Significa | Cómo usarlo |
|---|---|---|
| **[verificado en este equipo]** | Probado con Solid Edge 2026 en el PC del usuario | Úsalo tal cual. |
| **[doc oficial]** | Leído en la referencia de la API de Siemens durante esta investigación. ⚠️ La referencia pública que responde es la de **ST6/ST7/ST8 (106–108)**; la de SE 2026 no está abierta en internet (los enlaces nuevos redirigen al portal con inicio de sesión). | Muy probable que siga igual en 2026, pero las **firmas y los valores numéricos** se confirman con §1.6 antes de usarlos en un script nuevo. |
| **[muestra/código comunidad]** | Repositorio `tylerwagler/SolidEdge-MCP` (pywin32, medido contra SE **226.00.01.04**), repositorio `SolidEdgeCommunity/Samples` (C#/VB), ayuda de usuario en soliddna.com | Fuente secundaria seria; la de SolidEdge-MCP está medida contra SE 2026. |
| **[inferido]** | Deducción del investigador o firma recordada de la API que **no** se volvió a leer en esta sesión | Compruébalo (§1.6) o ensáyalo en una carpeta temporal antes de afirmarlo. |

> Equivale a las etiquetas de `SKILL.md`: [doc oficial] ≈ `[doc]`; [muestra/código comunidad] ≈ `[fuente secundaria]`.
> Postura oficial de Siemens: la API soportada es COM/.NET; **Python no está soportado oficialmente** (artículo de soporte PL8721130) [doc oficial]. Funciona porque es COM estándar, pero los parámetros de salida son el punto débil (§1.3, §7).

---

## Tabla de contenido

0. [Resumen: qué se puede y qué no](#0-resumen-qué-se-puede-y-qué-no)
1. [Estructura de la API](#1-estructura-de-la-api)
   1.1 Type libraries · 1.2 ProgIDs y tipos de documento · 1.3 Conexión y enlace temprano/tardío · 1.4 Propiedades de control de Application · 1.5 `StartCommand` e IDs de comando · 1.6 Autodescubrimiento: leer firmas y constantes en este equipo · 1.7 Unidades e índices
2. [Pieza (.par)](#2-pieza-par)
3. [Ensamble (.asm)](#3-ensamble-asm)
4. [Explosionado y configuraciones](#4-explosionado-y-configuraciones)
5. [Movimiento: motores, animación y video](#5-movimiento-motores-animación-y-video)
6. [Plano (.dft)](#6-plano-dft)
7. [Robustez: errores, reintentos, diálogos, rendimiento, hilos](#7-robustez)
8. [Lo que NO se puede por API y alternativas](#8-lo-que-no-se-puede-por-api-y-alternativas)
9. [Pendientes de verificar en este equipo](#9-pendientes-de-verificar-en-este-equipo)
10. [Fuentes](#10-fuentes)

---

## 0. Resumen: qué se puede y qué no

| Área | ¿Hay API? | Nivel | Nota corta |
|---|---|---|---|
| Pieza: bocetos, protrusión, revolución, cortes, agujeros, redondeos | Sí | 🟢 | Funciona en modo **ordenado** con pywin32 [muestra/código comunidad]. |
| Pieza: roscas (`Threads.Add`), barrido/solevado de **superficie**, vaciado (thinwall), simetría ordenada | Parcial | 🔴/🟡 | Fallan en SE 2026 desde pywin32; hay alternativas (§2.7). |
| Ensamble: colocar, mover, matrices, relaciones planar/axial | Sí | 🟢 | [verificado en este equipo] con las trampas de §3. |
| Ensamble: patrones y simetrías de ensamble | Parcial | 🔴 | `E_ACCESSDENIED` en SE 2025/2026 [muestra/código comunidad] → bucle de `AddWithMatrix`. |
| Ensamble: interferencia (`CheckInterference`) | Sí, pero | 🔴 desde pywin32 dinámico | [verificado en este equipo] que no funciona así; caminos en §3.6. |
| Ensamble: lista de materiales (BOM) | Indirecta | 🟢 | Recorrer `Occurrences` o leer un `PartsList` del plano. |
| **Explosionado** (entorno Explosionar-Renderizar-Animar, ERA) | **Parcial** | 🟡 | **`asm.AutoExplode(...)` existe en SE 2026** [verificado en este equipo: type library, §11]. Pasos manuales y líneas de flujo: solo con `StartCommand` (IDs en §11). Falta probar cómo se guarda la explosión como configuración (§4, §9). |
| **Motores / simular motor / animación / video** | **No (motor) · Sí (arrastre)** | 🔴/🟢 | No hay objeto ni comando "Motor" en SE 2026 [verificado en este equipo]. **Sí hay `DragComponentRotation`/`DragComponentTranslation` con detección de colisiones** y `Relations3d.AddAngular` para un "motor" por pasos (§5, §11). |
| Plano: vistas, cotas, textos, hojas | Sí | 🟢 | [doc oficial] + [muestra/código comunidad] medido en 2026. |
| Plano: **lista de piezas y globos** | **Sí** | 🟢 | `PartsLists.Add` con globos automáticos funcionó en SE 2026 [muestra/código comunidad]; `Balloons` existe (§6). |
| Exportar STEP/STL/PDF | Sí | 🟢 | Con `SaveCopyAs` y ruta **nueva** (§2.13, §6.8). |

---

## 1. Estructura de la API

### 1.1 Type libraries

Solid Edge expone su modelo de objetos en varias type libraries (archivos `.tlb` en `<instalación>\Program\`) [muestra/código comunidad: el volcado de SolidEdge-MCP los cita como `Program/geometry.tlb`, `Program/partattr.tlb`, `Simulation/x64/femap.tlb`].

| Librería (nombre .NET / COM) | Archivo | Contiene |
|---|---|---|
| SolidEdgeFramework | `framewrk.tlb` | `Application`, `Documents`, `Window`, `View`, `SelectSet`, `Environments`, eventos, `DocumentTypeConstants`, `ObjectType` |
| SolidEdgeFrameworkSupport | `fwksupp.tlb` | Elementos 2D compartidos: `Dimensions`, `Balloons`, `TextBoxes`, `Lines2d`, `Relations2d`… |
| SolidEdgePart | `Part.tlb` | `PartDocument`, `SheetMetalDocument`, `Models`, `Model`, operaciones, `RefPlanes`, `ProfileSets`, `Variables`… |
| SolidEdgeAssembly | `assembly.tlb` | `AssemblyDocument`, `Occurrences`, `Occurrence`, `Relations3d`, `Configurations`… |
| SolidEdgeDraft | `draft.tlb` | `DraftDocument`, `Sheets`, `Sections`, `DrawingViews`, `ModelLinks`, `PartsLists`… |
| SolidEdgeGeometry | `geometry.tlb` | `Body`, `Faces`, `Face`, `Edge`, `Vertex`, `Plane`, `Cylinder`, `Cone`… |
| SolidEdgeConstants | `constant.tlb` | Todos los enums, incluidas las tablas de **IDs de comando** (`PartCommandConstants`, `AssemblyCommandConstants`, `DetailCommandConstants`, `ExplodeCommandConstants`…) |

En SE 2026 `AssemblyDocument` tiene **98 métodos y 122 propiedades** (en ST7 eran 67 y ~111) [muestra/código comunidad: volcado de la type library]. Es decir, la referencia ST7 que se puede leer en línea **se queda corta**: lo que no aparezca ahí puede existir en 2026. Compruébalo con §1.6.

### 1.2 ProgIDs y tipos de documento

| Documento | ProgID para `Documents.Add` | Extensión | `doc.Type` (DocumentTypeConstants) |
|---|---|---|---|
| Aplicación | `SolidEdge.Application` | — | — |
| Pieza | `SolidEdge.PartDocument` | .par | `igPartDocument = 1` [muestra/código comunidad] |
| Plano | `SolidEdge.DraftDocument` | .dft | `igDraftDocument = 2` |
| Ensamble | `SolidEdge.AssemblyDocument` | .asm | `igAssemblyDocument = 3` |
| Chapa | `SolidEdge.SheetMetalDocument` | .psm | `igSheetMetalDocument = 4` |
| Soldadura | `SolidEdge.WeldmentDocument` | .pwd | (13 valores en total; el resto, léelo con §1.6) |

- `Documents.Add(ProgID, [Plantilla])` crea el documento [inferido: segundo argumento opcional con la ruta de la plantilla]. ⚠️ `Documents.Add("SolidEdge.WeldmentDocument")` sin plantilla puede **colgarse en un diálogo modal**: exigir siempre la ruta de la plantilla [muestra/código comunidad].
- `Documents.Open(ruta)` abre; `doc.Close(False)` cierra sin guardar [inferido].
- Application tiene `GetDefaultTemplatePath`, `SetDefaultTemplatePath` y `GetTemplateFileName` [doc oficial: lista de miembros].

### 1.3 Conexión: enlace tardío (dinámico) frente a temprano (makepy)

```python
import pythoncom
import win32com.client as w32
from win32com.client import dynamic

pythoncom.CoInitialize()                         # en CADA hilo que use COM (§7.5)
app = w32.GetActiveObject("SolidEdge.Application")   # Solid Edge ya abierto
# Si hay caché makepy, GetActiveObject/Dispatch pueden devolver objetos de enlace temprano.
# Para forzar el enlace tardío (el que usa Jarvis):
app = dynamic.Dispatch(app._oleobj_)             # [inferido]
print(app.Version, app.ActiveDocument.Name)
```

| | Enlace tardío (`Dispatch`, `dynamic.Dispatch`) | Enlace temprano (`gencache.EnsureDispatch`, makepy) |
|---|---|---|
| Firmas | Desconocidas: pywin32 pasa todo como VARIANT por valor | Conocidas: genera wrappers con los tipos y la dirección de cada parámetro |
| Parámetros `[out]` | **No los sabe crear** (por eso falla `CheckInterference`, §3.6) | Se **omiten** en la llamada y vuelven en una **tupla** con el retorno [inferido: comportamiento estándar de makepy] |
| Parámetros `[in,out]` de arreglos (`GetMatrix`, `GetRangeBox`, `Body.GetRange`, propiedades físicas) | Se pasa una **lista Python** de tamaño correcto y el resultado se lee del **valor de retorno**, no de la lista [verificado en este equipo para `GetMatrix`; muestra/código comunidad para el resto] | Igual, en tupla |
| Constantes | Hay que conocer los números | `win32com.client.constants.igRight`, etc. |
| Riesgo | Ninguno nuevo | ⚠️ Una vez generada la caché `gen_py`, **todo** `Dispatch` de esas librerías pasa a enlace temprano y puede cambiar el comportamiento de código viejo de Jarvis (mayúsculas, out-params). Si se usa, aislarlo o forzar `dynamic.Dispatch` en el resto [inferido]. |

SolidEdge-MCP usa **enlace tardío en todas partes** a propósito, para que los objetos se comporten igual si se conectó a un Solid Edge abierto o lo arrancó él [muestra/código comunidad]. Es la opción recomendada para Jarvis, con las excepciones puntuales de §3.6.

Reglas de pywin32 con proxies COM [muestra/código comunidad]:
- **Nunca `hasattr(obj, "X")`** sobre un proxy: devuelve `False` tanto si el miembro no existe como si el getter lanzó un error. Usar `try: v = obj.X except pywintypes.com_error: …`.
- **Nunca comparar proxies con `==`**: compara `FullName` o `Name`.
- Cuando un parámetro de salida queda entre argumentos obligatorios, pywin32 le asigna una posición: pasa los posteriores **por nombre**.

### 1.4 Propiedades de `Application` que controlan el comportamiento

| Propiedad / método | Qué hace [doc oficial] | Uso en scripts |
|---|---|---|
| `DelayCompute` | Suspende el recálculo | `True` mientras se crean relaciones o muchas operaciones; **imprescindible** con `AddAxial` (§3.3) [verificado en este equipo]. Restaurar siempre en `finally`. |
| `ScreenUpdating` | Activa/desactiva el refresco de pantalla | `False` en lotes; `True` antes de capturar imágenes [inferido]. |
| `Interactive` | Si la aplicación se puede usar interactivamente | `False` bloquea la interacción del usuario durante el script; algunos comandos que necesitan interfaz fallan con `False` [inferido]. |
| `DisplayAlerts` | Activa/desactiva alertas y mensajes | `False` al conectar (convierte algunos cuelgues en errores COM) [muestra/código comunidad]; ⚠️ **no** suprime el diálogo de sobrescritura de `SaveAs` [verificado en este equipo]. |
| `Visible`, `WindowState`, `hWnd` | Ventana | `hWnd` sirve para capturar la ventana por el sistema operativo (§5.3). |
| `DoIdle()` | Da tiempo ocioso para tareas pendientes tras un proceso intenso | Llamarlo tras lotes grandes y antes de exportar o capturar [inferido]. |
| `ActiveEnvironment`, `Environments` | Entorno de la ventana activa | Sondear para saber si `StartCommand` entró en ERA (§4) [inferido]. |
| `StartCommand(id)` | Activa un comando de Solid Edge | §1.5. |
| `GetGlobalParameter` / `SetGlobalParameter` | Parámetros globales | Opciones de exportación y de la aplicación [inferido para opciones concretas]. |
| `GetMaterialTable()` | Tabla de materiales | §2.11. |
| `GetDraftPrintUtility()` | Utilidad de impresión de planos | §6.8. |
| `ProcessID` | PID de Edge.exe | Para ubicar la instalación (§1.6). |
| `SetOLERequestPendingTimeout`, `SetOLEServerBusyTimeout` | Tiempos OLE | Existen en Application [doc oficial]; no sustituyen el filtro de mensajes del cliente (§7.2). |

### 1.5 `StartCommand` e IDs de comando

Firma [doc oficial]: `Application.StartCommand(CommandID As SolidEdgeCommandConstants)`. Sirve **cualquier** constante de cualquiera de los ~20 conjuntos (`PartCommandConstants`, `AssemblyCommandConstants`, `SheetMetalCommandConstants`, `DetailCommandConstants`, `ExplodeCommandConstants`…) **siempre que el entorno al que pertenece esté activo** [doc oficial].

Lo que hay que saber:
- `StartCommand` **lanza** el comando como si se pulsara el botón y devuelve el control; el script **no** puede rellenar el diálogo ni la barra de comandos que abre [inferido]. Es "abrir la puerta y pasarle el mando al usuario".
- Los IDs **pueden cambiar entre versiones**: los de abajo son de ST6/ST7. Para 2026, léelos de `constant.tlb` con §1.6.

IDs útiles (ST7 [doc oficial]; el conteo de 85 de `ExplodeCommandConstants` y los primeros valores coinciden en el volcado de 2026 [muestra/código comunidad]):

| Constante | ID (ST7) | Para qué |
|---|---|---|
| `AssemblyEnvironmentsExplodedView` | 33079 | Entrar al entorno **Explosionar-Renderizar-Animar** desde el ensamble |
| `AssemblyAssemblyToolsCheckInterference` | 25039 | Abrir **Verificar interferencia** (interactivo) |
| `AssemblyAssemblyToolsDisplayConfigurations` | 32826 | Abrir **Configuraciones de visualización** |
| `AssemblyFileSaveAsImage` | 58000 | **Guardar como imagen** (diálogo) |
| `AssemblyViewFit` / `AssemblyViewISOView` / `AssemblyViewFrontView` | 33022 / 32810 / 32811 | Encuadrar / isométrica / frontal |
| `AssemblyAssemblyRelationshipsGround` / `Mate` / `PlanarAlign` / `AxialAlign` | 32774 / 32772 / 25080 / 25081 | Comandos de relación (interactivos) |
| `ExplodeExplodedViewAutomaticExplode` | 65062 | **Explosión automática** (dentro de ERA) |
| `ExplodeExplodedViewExplode` / `Unexplode` / `Collapse` / `Reposition` | 65064 / 65068 / 65069 / 65066 | Explosión manual y edición |
| `ExplodeExplodedViewFlowLines` / `FlowLineTerminators` | 33095 / 33096 | Líneas de flujo |
| `ExplodeExplodedViewBindSubassembly` / `Unbind…` | 58001 / 58002 | Atar/desatar subensamble |
| `ExplodeAssemblyToolsDisplayConfigurations` | 32826 | Configuraciones (desde ERA) |
| `ExplodeFileSaveAsImage` | 58000 | Imagen desde ERA |
| `SolidEdgeCommandConstants.seAssemblyPlacePartCommand` (2026) | 32791 | Colocar pieza [muestra/código comunidad] |
| `seRefreshViewCommand` (2026) | 32876 | Refrescar vista |

`ExplodeCommandConstants` (ST6) **no** contiene nada de Animación, Render, Motor, Video ni Línea de tiempo [doc oficial]; los comandos de animación/render/motor, si tienen ID en 2026, hay que buscarlos por nombre con §1.6 (`buscar_constantes("Motor")`, `("Anim")`, `("Render")`).

### 1.6 Autodescubrimiento: leer firmas y constantes en este equipo

Como la referencia de 2026 no es pública, **la verdad está en las type libraries instaladas**. Estas tres funciones (solo lectura, no tocan el modelo) resuelven cualquier dato marcado [inferido]:

```python
import glob, os, pythoncom, win32api, win32con, win32process

def carpeta_program(app):
    """Carpeta Program de la instalación, a partir del PID de Edge.exe."""
    h = win32api.OpenProcess(win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ,
                             False, app.ProcessID)
    try:
        return os.path.dirname(win32process.GetModuleFileNameEx(h, 0))  # ...\Program
    finally:
        win32api.CloseHandle(h)

def cargar_constantes(program_dir):
    """{nombre: valor} de TODOS los enums de todas las .tlb de Program."""
    C = {}
    for ruta in glob.glob(os.path.join(program_dir, "*.tlb")):
        try:
            tlb = pythoncom.LoadTypeLib(ruta)
        except pythoncom.com_error:
            continue
        for i in range(tlb.GetTypeInfoCount()):
            ti = tlb.GetTypeInfo(i)
            ta = ti.GetTypeAttr()
            if ta.typekind == pythoncom.TKIND_ENUM:
                for j in range(ta.cVars):
                    vd = ti.GetVarDesc(j)
                    C[ti.GetNames(vd.memid)[0]] = vd.value
    return C

def buscar_constantes(C, texto):
    return sorted((k, v) for k, v in C.items() if texto.lower() in k.lower())

FLAGS = {1: "in", 2: "out", 8: "retval", 16: "opcional"}
def firma(obj, nombre=None):
    """Imprime métodos/propiedades del objeto COM vivo, con dirección de cada parámetro."""
    ti = obj._oleobj_.GetTypeInfo()
    ta = ti.GetTypeAttr()
    for k in range(ta.cFuncs):
        fd = ti.GetFuncDesc(k)
        nombres = ti.GetNames(fd.memid)
        if nombre and nombres[0].lower() != nombre.lower():
            continue
        params = []
        for idx, arg in enumerate(fd.args):
            pflags = arg[1]
            dirs = "/".join(v for b, v in FLAGS.items() if pflags & b) or "in"
            pn = nombres[idx + 1] if idx + 1 < len(nombres) else f"arg{idx}"
            params.append(f"{pn}[{dirs}]")
        tipo = {1: "método", 2: "get", 4: "put", 8: "putref"}.get(fd.invkind, fd.invkind)
        print(f"{nombres[0]} ({tipo}): {', '.join(params)}")
```

Uso típico: `firma(asm, "CheckInterference")`, `firma(app.ActiveDocument)` para ver los 98 métodos del ensamble de 2026, `buscar_constantes(C, "Explode")`. Requiere `pywin32` (`win32api`, `win32process`), que ya está en el venv de Jarvis [inferido]. Si `GetTypeInfo()` devuelve una dispinterface sin parámetros detallados, generar makepy en una carpeta aparte y leer el `.py` generado (buscar `def CheckInterference` y su línea `InvokeTypes`) es el plan B [inferido].

### 1.7 Unidades e índices

- La API trabaja en **SI: metros, radianes, kilogramos** [muestra/código comunidad]. 20 mm = `0.02`; 90° = `math.radians(90)`. Las variables angulares se leen en radianes.
- Colecciones COM **base 1**: `Item(1)` es el primero [muestra/código comunidad].
- Planos base de una pieza: `RefPlanes.Item(1)` = Superior (XY), `Item(2)` = Derecho (YZ), `Item(3)` = Frontal (XZ) [muestra/código comunidad]. El **Frontal tiene la normal hacia −Y** del mundo: en cortes sobre ese plano conviene `igSymmetric` o comprobar el lado [muestra/código comunidad].
- Un **ensamble no tiene `RefPlanes`**: usa `AsmRefPlanes`, con el mismo orden [muestra/código comunidad].

---

## 2. Pieza (.par)

### 2.1 Crear el documento y el modo de modelado

```python
doc = app.Documents.Add("SolidEdge.PartDocument")          # o con plantilla ISO
print(doc.ModelingMode)            # ordenado o síncrono según la plantilla/opciones
doc.ModelingMode = C["seModelingModeOrdered"]              # [inferido: nombre del enum]
```

- Jarvis y este capítulo trabajan en **modo ordenado**: la mayoría de las operaciones ordenadas funcionan por API; varias **síncronas** solo existen como `AddSync` (simetría, ciertas pestañas de chapa) [muestra/código comunidad].
- Comprueba el modo justo después de crear: una plantilla síncrona hace que métodos ordenados registren operaciones que no construyen nada [inferido].

### 2.2 Planos de referencia

| Tarea | Llamada | Notas |
|---|---|---|
| Paralelo a distancia | `doc.RefPlanes.AddParallelByDistance(PlanoPadre, Distancia, LadoNormal, [Pivote], [OrigenPivote], [Local])` | `LadoNormal`: `igNormalSide = 2` o `igReverseNormalSide = 1` (ReferenceElementConstants, valores [muestra/código comunidad]); orden de parámetros [inferido]. |
| Angular | `doc.RefPlanes.AddAngularByAngle(PlanoPadre, Ángulo_rad, Pivote, OrigenPivote, LadoNormal, [Local])` | `igPivotStart = 3`, `igPivotEnd = 4` [muestra/código comunidad]; orden [inferido]. |
| Ocultar | `plano.Visible = False` | [inferido] |

Las creaciones de planos se verifican por el aumento de `RefPlanes.Count` [muestra/código comunidad].

### 2.3 Perfiles (bocetos), relaciones 2D y cotas

```python
ps = doc.ProfileSets.Add()
perfil = ps.Profiles.Add(doc.RefPlanes.Item(1))     # boceto en el plano Superior
L = perfil.Lines2d
l1 = L.AddBy2Points(0.00, 0.00, 0.10, 0.00)
l2 = L.AddBy2Points(0.10, 0.00, 0.10, 0.05)
l3 = L.AddBy2Points(0.10, 0.05, 0.00, 0.05)
l4 = L.AddBy2Points(0.00, 0.05, 0.00, 0.00)
R = perfil.Relations2d
for a, b in ((l1, l2), (l2, l3), (l3, l4), (l4, l1)):
    R.AddKeypoint(a, C["igLineEnd"], b, C["igLineStart"])   # conexión de vértices
R.AddHorizontal(l1); R.AddVertical(l2)
d = perfil.Dimensions.AddLength(l1)                          # cota de longitud
estado = perfil.End(C["igProfileClosed"])                    # 0 = perfil válido
```

| Elemento | Métodos habituales [inferido salvo nota] |
|---|---|
| Líneas | `Lines2d.AddBy2Points(x1, y1, x2, y2)` |
| Círculos | `Circles2d.AddByCenterRadius(xc, yc, r)` |
| Arcos | `Arcs2d.AddByCenterStartEnd(xc, yc, xi, yi, xf, yf)` |
| Agujeros (perfil de agujero) | `Holes2d.Add(x, y)` |
| Relaciones 2D | `Relations2d.AddKeypoint`, `AddHorizontal`, `AddVertical`, `AddParallel`, `AddPerpendicular`, `AddTangent`, `AddEqual`… (27 métodos en `Relations2d`, 2026 [muestra/código comunidad]) |
| Cotas | `Dimensions.AddLength(obj)`, `AddRadius(obj)`, `AddCircularDiameter(obj)`, `AddDistanceBetweenObjects(...)`, `AddAngleBetweenObjects(...)` |
| Cerrar el boceto | `Profile.End(tipoValidación)` → código de estado; distinto de 0 = perfil inválido |
| Eje de revolución | `perfil.SetAxisOfRevolution(línea)` → devuelve el eje |

- **Varios perfiles disjuntos en un mismo boceto de corte no están soportados** desde COM; un perfil por operación [muestra/código comunidad].
- Tras usar el perfil en una operación, `perfil.Visible = False` deja limpio el modelo [inferido].

### 2.4 Protrusiones y revoluciones

```python
m = doc.Models.AddFiniteExtrudedProtrusion(1, (perfil,), C["igRight"], 0.02)  # 20 mm
eje = perfil_r.SetAxisOfRevolution(linea_eje)
m2 = doc.Models.AddFiniteRevolvedProtrusion(1, (perfil_r,), eje, C["igRight"], math.radians(360))
```

| Tarea | Llamada | Notas |
|---|---|---|
| Protrusión finita (base) | `Models.AddFiniteExtrudedProtrusion(NúmPerfiles, ArregloPerfiles, LadoPlanoPerfil, Distancia, [...])` → `Model` | `LadoPlanoPerfil` = FeaturePropertyConstants: `igLeft = 1`, `igRight = 2`, `igSymmetric = 3` (también `igInside = 4`) [muestra/código comunidad]. ⚠️ Pasar `0` se acepta en silencio y **no crea geometría** [muestra/código comunidad]. Firma [inferido]. |
| Revolución finita (base) | `Models.AddFiniteRevolvedProtrusion(NúmPerfiles, ArregloPerfiles, Eje, LadoPlanoPerfil, Ángulo_rad, [...])` | La cota del ángulo aparece como variable `RevolvedProtrusion_1_FiniteAngle` y se verificó numéricamente [muestra/código comunidad]. |
| Protrusiones posteriores | `m.ExtrudedProtrusions.AddFinite(...)` y familia sobre el `Model` | [inferido]: preferir los métodos **de colección** (`Model.<Colección>.Add*`) a los de `Models` [muestra/código comunidad]. |
| Solevado / barrido (sólidos) | `Models.AddLoftedProtrusion(...)`, `Models.AddSweptProtrusion(...)` | Necesitan un arreglo `Origins` con un punto **válido sobre cada sección**; un origen fijo "a ojo" no construye nada [muestra/código comunidad]. |
| Engrosar | `Models.AddThickenFeature(...)` | Funciona [muestra/código comunidad]. |

`ExtentTypeConstants` (extensión de cortes/agujeros): por analogía con los enums de 2026 `VentExtentTypeConstants` y `TabAndSlotExtentTypeConstants` (Finite=13, ThroughNext=14, FromTo=15, ThroughAll=16, ToKeyPoint=72) es muy probable que `igFinite = 13`, `igThroughNext = 14`, `igFromTo = 15`, `igThroughAll = 16` [inferido: confirmar con `buscar_constantes(C, "igThrough")`].

### 2.5 Cortes

| Tarea | Llamada | Notas |
|---|---|---|
| Corte finito | `m.ExtrudedCutouts.AddFiniteMulti(NúmPerfiles, ArregloPerfiles, LadoPlanoPerfil, Profundidad)` | Los `Models.Add*Cutout` **no funcionan**; usar los métodos de colección `ExtrudedCutouts.*Multi` [muestra/código comunidad]. |
| Corte pasante | `m.ExtrudedCutouts.AddThroughAllMulti(NúmPerfiles, ArregloPerfiles, LadoPlanoPerfil)` | [inferido: nombre por simetría con el anterior] |
| Corte de revolución | `m.RevolvedCutouts.AddFiniteMulti(...)` | [inferido] |

El lado del corte depende de la normal del plano del boceto: en el plano Frontal (normal −Y) usa `igSymmetric` o comprueba el resultado por volumen [muestra/código comunidad].

### 2.6 Agujeros y roscas

```python
hd = doc.HoleDataCollection.Add(HoleType=C["igRegularHole"], HoleDiameter=0.008)   # [inferido]
perfil_h = doc.ProfileSets.Add().Profiles.Add(cara_o_plano)
perfil_h.Holes2d.Add(0.03, 0.02); perfil_h.End(C["igProfileClosed"])
agujero = m.Holes.AddFinite(perfil_h, C["igRight"], 0.010, hd)                   # [inferido]
```

- El agujero necesita un objeto `HoleData` de `doc.HoleDataCollection`; pasar `None` no registra nada [muestra/código comunidad].
- **Roscas:** `Threads.Add` sobre un cilindro existente devuelve `E_INVALIDARG` con todas las formas probadas en SE 2026 [muestra/código comunidad]. **Alternativa:** crear el **agujero roscado** directamente (HoleData de tipo roscado); funciona [muestra/código comunidad]. Para un eje roscado exterior, documentar la rosca en el plano (nota/cota) o aplicarla por interfaz.

### 2.7 Redondeos, chaflanes, patrones, simetrías, vaciado, nervios

| Operación | Llamada | Estado en SE 2026 |
|---|---|---|
| Redondeo | `m.Rounds.Add(NúmConjuntos, ArregloAristas, ArregloRadios)` | 🟢 Funciona; acepta arreglo VARIANT o lista [muestra/código comunidad]. Firma [inferido]. |
| Mezcla (blend) | `Blends.Add` | 🔴 `E_FAIL` siempre; usar `Rounds.Add` [muestra/código comunidad]. |
| Chaflán | `m.Chamfers.AddEqualSetback(NúmAristas, ArregloAristas, Retroceso)` | [inferido] |
| Patrón rectangular/circular | `m.Patterns.AddByRectangular / AddByCircular` | 🔴 Las versiones sin `Ex` fallan en enlace tardío por exigir `SAFEARRAY(IDispatch)`; usar las variantes **`…Ex`** [muestra/código comunidad]. |
| Reconocer patrones | `RecognizeAndCreatePatterns` | 🔴 Inviable desde pywin32 [muestra/código comunidad]. |
| Simetría (mirror copy) | `m.MirrorCopies.Add(...)` | 🔴 En **ordenado** registra la operación pero no construye; `AddSync` funciona solo en documento síncrono; `AddSyncEx` no es usable en enlace tardío [muestra/código comunidad]. **Alternativa:** boceto simétrico (relación de simetría) o modelar con `igSymmetric`. |
| Vaciado (Thinwall) | `m.Thinwalls.Add(...)` | 🟡 Necesita elegir caras abiertas; la comunidad no lo logró por COM [muestra/código comunidad]. Alternativa: perfil de corte interior o hacerlo en la interfaz. |
| Nervio, chapa, etc. | `Ribs`, `Flanges`… | Pestañas de chapa ordenadas (`Flanges.Add*`, `Louvers.Add`) se registran y **nunca se resuelven**; `Flanges.AddSync` sí [muestra/código comunidad]. |
| Superficies de barrido / solevado / acotadas | `SweptSurfaces.Add`, `LoftedSurfaces.Add`, `BlueSurfs.Add` | 🔴 `SweptSurfaces.Add` **tumbó el proceso de Solid Edge** en 3 de 5 llamadas; los otros dan `E_INVALIDARG` [muestra/código comunidad]. No usar. |
| Simplificación automática | `Models.AddAutoSimplify` | 🔴 Tumbó Solid Edge (`RPC_S_CALL_FAILED`) [muestra/código comunidad]. |

### 2.8 Variables y fórmulas

| Tarea | Llamada | Notas |
|---|---|---|
| Crear variable | `doc.Variables.Add(Nombre, Fórmula, [TipoUnidad])` | [inferido] |
| Cambiar fórmula | `doc.Variables.Edit(Nombre, Fórmula)` | [inferido] |
| Leer valor | `doc.Variables.Item("Nombre").Value` | Siempre en SI (m, rad) [muestra/código comunidad]. |
| Encontrar cotas | `doc.Variables.Query(criterio, NamedBy=seVariableNameByBoth, …)` | Al enumerar `Variables.Item(i)` las cotas salen **sin nombre**; buscar por nombre o con `Query` [muestra/código comunidad]. |

Las cotas de operación aparecen como variables con nombres del tipo `RevolvedProtrusion_1_FiniteAngle` [muestra/código comunidad]: es la forma más estable de **editar una operación existente** (cambiar la variable y dejar que recalcule), en lugar de rehacerla.

### 2.9 Estado de operaciones (detectar errores) y edición

- Recorre `doc.DesignEdgebarFeatures` (orden del PathFinder) y lee `feature.Status` y `feature.Name`. ⚠️ La colección incluye los **planos base**, que no tienen todos los miembros de una operación (p. ej. `Suppress`): envolver cada lectura en `try` [muestra/código comunidad].
- `Status` devuelve un valor de `FeatureStatusConstants` (`igFeatureOK`, `igFeatureFailed`, `igFeatureWarned`, `igFeatureSuppressed`, `igFeatureRolledBack`…) [inferido: nombres]; compara contra `C[...]`, nunca contra números escritos a mano.
- **Verificación independiente** (lo que hace la comunidad): número de caras de `Body` y **volumen** antes y después de cada operación; el volumen detecta cambios que no alteran el número de caras [muestra/código comunidad].

### 2.10 Topología y geometría de caras [verificado en este equipo]

```python
cuerpo = doc.Models.Item(1).Body
caras = cuerpo.Faces(1)                     # 1 = igQueryAll
for i in range(1, caras.Count + 1):
    f = caras.Item(i)
    g = f.Geometry
    # Plano:     g.GetPlaneData(...)            → leer del VALOR DE RETORNO
    # Cilindro:  g.GetCylinderData([0]*3, [0]*3, 0.0)  (3 argumentos en Python) → retorno
    # Cono:      g.GetConeData(...)             → retorno
```

- `GetPlaneData` **no** da la normal orientada de la cara. Para la normal exterior: `Face.GetParamRange(...)` → un (u, v) interior → `Face.GetNormal(1, [u, v])` [verificado en este equipo].
- Otros filtros de `Faces(...)`: `igQueryPlane`, `igQueryCylinder`, `igQueryCone`… [inferido: nombres de `FeatureTopologyQueryTypeConstants`].
- Caja envolvente de un cuerpo: `Body.GetRange([0.0]*3, [0.0]*3)` → leer del retorno [muestra/código comunidad].
- Un documento de pieza abierto **dentro** de un ensamble (vía `occ.OccurrenceDocument`) llega con `ReadOnly=True`, `Dirty=False` [verificado en este equipo]: sirve para leer geometría, no para editar. Para editar: abrir el `.par` por su cuenta o pedir escritura (`SeekWriteAccess` existe en los documentos [doc oficial: descripción]; `Occurrence.MakeWritable` [muestra/código comunidad]).

### 2.11 Material y propiedades físicas

| Tarea | Llamada | Notas |
|---|---|---|
| Tabla de materiales | `mt = app.GetMaterialTable()` | Existe en Application [doc oficial]. |
| Aplicar material | `mt.ApplyMaterial(doc, "Acero")` | [inferido]; el nombre depende de la biblioteca/idioma: listar antes los disponibles. |
| Masa, volumen, CdG | `m.ComputePhysicalPropertiesWithSpecifiedDensity(Densidad, Precisión, …salidas…)` | Las salidas `[in,out]` de doble/arreglo: pasar `0.0` y listas del tamaño correcto y **leer la tupla de retorno** [muestra/código comunidad]. Firma completa [inferido]: confirmar con `firma(m, "ComputePhysicalPropertiesWithSpecifiedDensity")`. |
| Ensamble | `asm.PhysicalProperties` | Existe en AssemblyDocument [doc oficial]. |

### 2.12 Propiedades del archivo (alimentan el cuadro de rotulación y la lista de piezas)

```python
props = doc.Properties                                   # PropertySets
props.Item("SummaryInformation").Item("Title").Value = "Brida de entrada"
props.Item("SummaryInformation").Item("Author").Value = "el usuario"
props.Item("ProjectInformation").Item("Document Number").Value = "CAD-03-001"
props.Item("Custom").Add("Curso", "CAD 3er corte")      # propiedad personalizada
props.Save()
```

Conjuntos habituales: `SummaryInformation`, `DocumentSummaryInformation`, `ProjectInformation`, `MechanicalModeling`, `Custom` [inferido: nombres de uso común en ejemplos]. `doc.SummaryInfo` también existe [doc oficial]. Si el archivo es del usuario, **no** se guarda: se trabaja en una copia (regla de oro de `jarvis-operador`).

### 2.13 Exportar

| Formato | Llamada | Notas |
|---|---|---|
| STEP | `doc.SaveCopyAs(r"...\pieza.stp")` | 🟢 Escribió el archivo en SE 2026; apareció un diálogo modal que hubo que cerrar [muestra/código comunidad]. |
| STL, IGES, Parasolid (`.x_t`), JT | `doc.SaveCopyAs(ruta_con_extensión)` | Mismo mecanismo [muestra/código comunidad: herramienta de exportación]; STL no tuvo caso en la medición. |
| `Application.ConvertByFilePath` | — | 🔴 No escribe nada en 9 formatos y **no avisa** [muestra/código comunidad]. |

- **`SaveCopyAs`, no `SaveAs`**, para exportar: `SaveAs` re-apunta el documento abierto al archivo nuevo [muestra/código comunidad].
- ⚠️ **Nunca** a una ruta existente: abre un diálogo de sobrescritura que `DisplayAlerts` no suprime y bloquea Solid Edge [verificado en este equipo]. Comprobar con `os.path.exists` y generar un nombre libre.
- Comprobar después que el archivo existe y tiene tamaño > 0.

---

## 3. Ensamble (.asm)

### 3.1 Colocar ocurrencias

| Tarea | Llamada | Notas |
|---|---|---|
| Colocar por archivo | `occ = asm.Occurrences.AddByFilename(ruta)` | ⚠️ Deja la ocurrencia con una relación **Fijar (Ground)** que hay que borrar si la pieza debe moverse [verificado en este equipo]. Nombre resultante `pieza.par:1`, `:2`… [muestra/código comunidad]. |
| Colocar con matriz | `asm.Occurrences.AddWithMatrix(ruta, Matriz16)` | Existe [muestra/código comunidad: muestra `AddOccurrenceWithMatrix` y mapa de 2026]. Misma convención de matriz que §3.2 [inferido]. |
| Colocar con transformación | `asm.Occurrences.AddWithTransform(ruta, X, Y, Z, ÁnguloX, ÁnguloY, ÁnguloZ)` | Radianes [inferido: orden]. Muestra `AddOccurrencesWithTransform` [muestra/código comunidad]. |
| Reordenar | `asm.Occurrences.ReorderOccurrence(...)` | Existe [muestra/código comunidad]. |
| Mover a otro subensamble | `asm.TransferOccurrences(...)` | [doc oficial: descripción] |
| Disolver subensamble | `asm.DisperseSubassembly(...)` | Sube un nivel sus ocurrencias [doc oficial: descripción]. |
| Agrupar en archivo nuevo | `asm.BundleOccurrences(...)` | [doc oficial: descripción] |

Borrar el Fijar que deja `AddByFilename` (patrón de la muestra `DeleteOccurrenceGroundRelations` [muestra/código comunidad]):

```python
rels = occ.Relations3d
for i in range(rels.Count, 0, -1):            # de atrás hacia adelante
    r = rels.Item(i)
    if r.Type == C["igGroundRelation3d"]:     # [inferido: nombre en ObjectType]
        r.Delete()
```

### 3.2 Posición y matrices [verificado en este equipo]

```python
m = list(occ.GetMatrix([0.0] * 16))          # leer del retorno, no de la lista pasada
def a_ensamble(m, p):                         # p en coordenadas de pieza
    return [sum(m[4*j + i] * p[j] for j in range(3)) + m[12 + i] for i in range(3)]
occ.PutMatrix(m_nueva, True)
mn, mx = occ.GetRangeBox([0.0]*3, [0.0]*3)    # caja envolvente (funciona)
```

- `p_asm = R·p` con `R[i][j] = M[4j+i]`; traslación en `M[12..14]` [verificado en este equipo].
- `occ.GetTransform()` → `(X, Y, Z, ÁngX, ÁngY, ÁngZ)`, posición en metros y **ángulos en radianes** [muestra/código comunidad]. `PutTransform`, `PutOrigin(x, y, z)`, `Move(dx, dy, dz)`, `Rotate(...)` existen [muestra/código comunidad]; firma de `Rotate` (eje por dos puntos + ángulo) [inferido].
- Mover/rotar varias a la vez (y **copiar**): `asm.TranslateMultipleOccurrences(...)`, `asm.RotateMultipleOccurrences(...)` devuelven las ocurrencias movidas **o copiadas** [doc oficial: descripción]. Firma [inferido].
- Otras propiedades de `Occurrence`: `Name`, `OccurrenceFileName`, `OccurrenceDocument`, `Subassembly`, `SubOccurrences`, `Visible`, `IncludeInBom`, `IsPatternItem`, `Relations3d` [muestra/código comunidad]. En una `SubOccurrence` el archivo está en `SubOccurrenceFileName` [muestra/código comunidad].

### 3.3 Relaciones 3D

Miembros de `Relations3d` [doc oficial, ST7]: `AddAngular`, `AddAxial`, `AddAxialWithParallelOffset`, `AddBarrelCam`, `AddCenterPlane`, `AddGear`, `AddGround`, `AddPath`, `AddPlanar`, `AddPlanarCam`, `AddPoint`, `AddPointWithInferredGeometry`, `AddRigidSet`, `AddTangent`, `Item`, `Count`. ⚠️ **No existe `AddCam`**: la leva es `AddPlanarCam` o `AddBarrelCam`.

**`AddPlanar(Plano1, Plano2, NormalsAligned, PuntoRestricción1(), PuntoRestricción2()) → PlanarRelation3d`** [doc oficial].
- Las entradas deben ser **`Reference`**: `asm.CreateReference(occurrence, cara)`, nunca la cara suelta [verificado en este equipo].
- `NormalsAligned=True` = **Coincidir** respecto de las normales **exteriores** de las caras; `False` = **Alinear plano** [verificado en este equipo]. (La doc dice "True = planos acoplados, False = alineados" [doc oficial].)
- Los puntos de restricción en **coordenadas de pieza** funcionan aunque la pieza esté desplazada [verificado en este equipo].

**`AddAxial(...)`** — nace con `FixedRotate=True`; si el solver resuelve en ese momento, la pieza **salta** a una orientación "canónica" [verificado en este equipo]. Receta verificada:

```python
app.DelayCompute = True
try:
    r1 = asm.CreateReference(occA, caraCilA)
    r2 = asm.CreateReference(occB, caraCilB)
    rel = asm.Relations3d.AddAxial(r1, r2, False)   # 3er argumento: [inferido]
    rel.FixedRotate = False                          # deja libre el giro
finally:
    app.DelayCompute = False
```

| Relación | Método | Estado |
|---|---|---|
| Fijar | `AddGround(...)` | "Coloca la pieza en posición fija" [doc oficial]; firma [inferido]. |
| Ángulo | `AddAngular(...)` | Existe [doc oficial]; la comunidad no logró pasarle los elementos por COM [muestra/código comunidad]. |
| Engranaje | `AddGear(...)` | Existe; relación (`RatioValue1/2`) [muestra/código comunidad]. Firma [inferido]. |
| Tangente, punto, plano medio, conjunto rígido, trayectoria, levas | `AddTangent`, `AddPoint`, `AddCenterPlane`, `AddRigidSet`, `AddPath`, `AddPlanarCam`, `AddBarrelCam` | Existen [doc oficial]; no probadas por pywin32 [inferido]. |

Propiedades útiles de una relación: `Offset`, `NormalsAligned`, `FixedRotate` (axial), `Angle`, `Suppress`, `Status` (`Relation3dStatusConstants`), `DetailedStatus` (`Relation3dDetailedStatusConstants`), `Delete()`, `GetGeometry1/2` [muestra/código comunidad + enums de 2026]. Las relaciones también se listan en `asm.Relations3d` y por ocurrencia en `occ.Relations3d`.

### 3.4 Receta robusta de ensamble (resumen)

1. `AddByFilename` → borrar el Fijar de toda pieza que deba moverse (dejar fija solo la base).
2. Elegir caras **por regla geométrica** (tipo, eje, normal exterior con `GetNormal`), nunca por índice.
3. Preposicionar con `PutMatrix` en la pose calculada (evita saltos del solver).
4. `DelayCompute=True` → `CreateReference` ×2 → `AddPlanar`/`AddAxial` → ajustar `FixedRotate`/`Offset` → `DelayCompute=False`.
5. Verificar: `rel.Status`, que la matriz no cambió más de lo previsto, número de relaciones.

### 3.5 Patrones, duplicados y subensambles

- **Patrones y simetrías de ensamble** (`AssemblyFeaturesPatterns.Add`, `AssemblyFeaturesMirrors.Add`): `E_ACCESSDENIED (0x80070005)` en SE 2025/2026 [muestra/código comunidad]. La colección de patrones de componentes `asm.AssemblyPatterns` existe [doc oficial], pero no hay prueba de que su creación funcione por pywin32.
- **Alternativa robusta:** bucle de `AddWithMatrix` con la matriz de cada copia calculada en Python (rotación alrededor del eje del patrón) + relaciones si hacen falta; o `TranslateMultipleOccurrences`/`RotateMultipleOccurrences` con copia [doc oficial: descripción]; o el patrón dentro de la pieza.
- **Operaciones de ensamble** (cortes/agujeros a nivel de ensamble): funcionan con `HoleData` y lados `FeaturePropertyConstants` (1/2/3; `0` se acepta y no hace nada) [muestra/código comunidad]. `AssemblyFeatures.Recompute` falla: usar `asm.UpdateAll()` [muestra/código comunidad].
- Subensamble: `occ.Subassembly` (booleano) y `occ.SubOccurrences` para bajar niveles [muestra/código comunidad].

### 3.6 Interferencia

Firmas [doc oficial]:

```
CheckInterference(NumElementsSet1 [in], Set1() [in,out], Status [OUT],
                  [ComparisonMethod], [NumElementsSet2], [Set2], [AddInterferenceAsOccurrence],
                  [ReportFilename], [ReportType], [NumInterferences OUT], [InterferingPartsSet1 OUT],
                  [InterferingPartsOtherSet OUT], [ConfirmedInterference OUT],
                  [InterferenceOccurrence OUT], [IgnoreThreadInterferences])
CheckInterference2(... igual ..., [IgnoreSameNominalDiaConstant], [IgnoreNonThreadVsThreadConstant])
```

Constantes (2026) [muestra/código comunidad]:
- `InterferenceComparisonConstants`: `Set1vsSet2=1`, `Set1vsAllOther=2`, `Set1vsVisible=3`, `Set1vsItself=4`.
- `InterferenceStatusConstants`: `NoInterference=1`, `ConfirmedInterference=2`, `ProbableInterference=3`, `ConfirmedAndProbableInterference=4`, `IncompleteAnalysis=5`.
- `InterferenceReportConstants` (máscara): `PartNames=1`, `PartCentersOfGravity=2`, `InterferenceCenterOfGravity=4`, `InterferenceVolume=8`.
- `InterferenceOptionsConstants`: `IgnoreSameNominalDia=1`, `IgnoreThreadVsNonThreaded=2`.

**No funciona desde pywin32 dinámico** por el parámetro de salida `Status` [verificado en este equipo]. La comunidad lo confirma: pasar buffers da error de análisis y omitirlos da `DISP_E_TYPEMISMATCH` [muestra/código comunidad]. Caminos, del más barato al más fiable:

| # | Camino | Estado |
|---|---|---|
| 1 | `win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)` para `Status` y VARIANTs byref para las demás salidas; leer `.value` tras la llamada | [inferido]: mecanismo documentado de pywin32, **no probado** con SE. |
| 2 | Generar makepy de `assembly.tlb` en una carpeta aparte y llamar con la línea `InvokeTypes` del wrapper generado (las salidas vuelven en tupla) | [inferido]; cuidado con la caché `gen_py` (§1.3). La comunidad ya usa `InvokeTypes` con `VT_BYREF` explícito en otro método (`GetSymbolFileOrigin`) [muestra/código comunidad]. |
| 3 | Utilidad C#/.NET con `Interop.SolidEdge` (la muestra `ReportInterference` hace exactamente esto: cada ocurrencia contra todas las demás, con `OleMessageFilter`) | [muestra/código comunidad]. Requiere SDK de .NET → **OK del usuario** antes de instalar. |
| 4 | Filtro geométrico propio: solapamiento de `GetRangeBox` entre pares → candidatos; descarta lo que seguro no choca | 🟢 Funciona [verificado en este equipo: `GetRangeBox`], pero es **aproximado** (cajas, no sólidos). |
| 5 | `StartCommand(AssemblyAssemblyToolsCheckInterference)` y que el usuario lea el resultado | Siempre posible [doc oficial: ID en ST7]. |

`asm.MinimumDistance(...)` ("mide la distancia mínima entre dos elementos") también existe [doc oficial: descripción]; probablemente tiene salidas y el mismo problema [inferido].

### 3.7 Lista de materiales (BOM)

No hay un objeto "BOM" en el ensamble [inferido]. Dos caminos:
1. **Recorrer ocurrencias** [muestra/código comunidad]: agrupar `OccurrenceFileName`, contar, saltar las que tengan `IncludeInBom = False` y los elementos de patrón (`IsPatternItem`); para estructura jerárquica, recursión por `SubOccurrences` (+ `Visible`, `IsSuppressed`).
2. **Leer la lista de piezas de un plano** (`PartsList`, §6.6): respeta la numeración de elementos y las reglas de la lista. La muestra `WritePartsListsToExcel` lo hace [muestra/código comunidad].

En 2026 existen además `asm.ItemNumbers` y el enum `AssemblyReportTypeConstants` [muestra/código comunidad]; no se encontró cómo usarlos para informes [inferido].

---

## 4. Explosionado y configuraciones

### 4.1 Qué hay en la API

| Elemento | Qué hace | Fuente |
|---|---|---|
| `asm.ExplosionsCount` | Número de vistas explosionadas del ensamble (solo lectura) | [doc oficial] |
| `asm.Configurations` | Colección: `Add(Name) → Configuration`, `Apply(Index, [ActivationOverride], [SimplifyOverride])`, `AddDerivedConfig(...)`, `Save()`, `Item`, `Count`, `Dirty` | [doc oficial] |
| `Configuration` | `Apply()`, `Delete()`, `Save()`, `Update()`, `Name`, `ConfigurationType`, `Type` | [doc oficial] |
| `ConfigurationTypeConstants` | `seConfigurationType_Display = 0`, `seConfigurationType_Explode = 1` | [doc oficial] + presente en 2026 [muestra/código comunidad] |
| `AutoExplodeSelectionTypeConstants` | `seTopLevelAssembly = 0`, `seSubassembly = 1` | Enum **nuevo**, presente en SE 2026 [muestra/código comunidad] |
| `AutoExplodeTechniqueConstants` | `seBySubassemblyLevel = 0`, `seByIndividualPart = 1` | Enum nuevo en SE 2026 [muestra/código comunidad] |
| `ExplodeCommandConstants` | 85 IDs de comando del entorno ERA (§1.5) | [doc oficial] + 2026 [muestra/código comunidad] |
| `ISEAssemblyConfigurationChangeEvents` | Eventos de cambio de configuración | framewrk.tlb 2026 [muestra/código comunidad] |
| `DrawingViews.AddAssemblyView(..., ConfigurationName)` / `DrawingViews.AddWithConfiguration` | Vista de plano a partir de una configuración | [doc oficial] / [muestra/código comunidad] |

Los dos enums de explosión automática **reflejan exactamente** las opciones del comando Explosión automática ("Tipo de selección: Ensamble de nivel superior / Subensamble"; "Técnica: Por nivel de subensamble / Por pieza individual") [muestra/código comunidad: ayuda de usuario]. **Su existencia en 2026 sugiere que algún método nuevo los consume** (quizá entre los 31 métodos de `AssemblyDocument` que no están en la referencia ST7), pero **no se encontró** ni su nombre ni su firma [inferido]. Primer paso en este equipo: `firma(asm)` y buscar `Explode`/`Explosion` (§1.6, §9).

### 4.2 Qué **no** se encontró

- Ningún método documentado para **crear pasos de explosión** (mover una pieza a lo largo de un vector dentro de la explosión), **líneas de flujo**, **atar subensambles** o **guardar la configuración de explosión** por código. No hay equivalente al `AddExplodeStep` de SolidWorks [inferido: ausencia en la referencia ST7 y en el volcado 2026; alcance: nombres de interfaces y enums, no todos los métodos].
- `Configurations.Add(Name)` crea una configuración, pero la doc no dice de qué tipo ni cómo convertirla en explosión; lo más probable es que capture la **visualización** actual (visibilidades) [inferido].
- `PartsListType.igExploded = 2` **no** es una vista explosionada: es la lista de piezas "desplegada" (todas las piezas de subensambles al mismo nivel) [inferido por el nombre y los vecinos `igTopLevel`, `igAtomic`].

### 4.3 Alternativas para el explosionado

| Opción | Cómo | Ventaja / límite |
|---|---|---|
| **A. Semi-automático (recomendada)** | Script: abre el ensamble, `StartCommand(AssemblyEnvironmentsExplodedView)` → espera a que `app.ActiveEnvironment` cambie → `StartCommand(ExplodeExplodedViewAutomaticExplode)`. El usuario confirma el diálogo, ajusta con Explosionar/Reposicionar, añade líneas de flujo y **guarda la configuración** con nombre (p. ej. `Explosion_1`). El script luego comprueba `asm.ExplosionsCount` y lista `asm.Configurations` para verificar el nombre y `ConfigurationType == 1`. | Resultado ERA real (con líneas de flujo), reutilizable en el plano. Requiere al usuario en pantalla. |
| **B. Pseudo-explosión en una copia** | `SaveCopyAs` del ensamble con nombre nuevo → abrir la copia → suprimir relaciones (`rel.Suppress = True`) de las piezas a separar → `occ.Move(dx, dy, dz)` a lo largo del eje de montaje → guardar. | 100 % por código y verificable. **No** es una explosión de ERA: sin líneas de flujo y la copia ya no está "armada". Útil para imágenes o si el curso acepta una vista separada. Nunca sobre el ensamble original. |
| **C. Plano con vista explosionada** | Con la configuración de A ya guardada: `DrawingViews.AddAssemblyView(ml, orient, escala, x, y, tipo, ConfigurationName="Explosion_1")` o `AddWithConfiguration(...)` | Que el parámetro acepte la configuración de **explosión** está [inferido]: probar en temporal (§9). Si no, insertar la vista con el asistente y dejar el resto por código. |

---

## 5. Movimiento: motores, animación y video

### 5.1 Qué hay

- **No se encontraron interfaces `Motor`/`Motors`, ni de simulación o grabación de video**, en las type libraries de SE 2026 (búsqueda en todo el volcado de nombres de interfaces y enums; no incluye cada método) [muestra/código comunidad + inferido]. La API ST7 tampoco tiene motores en `AssemblyDocument` ni en `AssemblyCommandConstants` [doc oficial].
- Sí existen **eventos** de animación: `AnimationEventConstants` (`BeforeTimelineFrameUpdate=1`, `AfterTimelineFrameUpdate=2`, `BeforeDragComponentFrameUpdate=3`, `AfterDragComponentFrameUpdate=4`) y la interfaz `ISEAnimationEvents` [muestra/código comunidad]. Sirven para **reaccionar** a una animación que corre en la interfaz (p. ej. guardar un fotograma en cada actualización), no para crearla [inferido]. Exigen montar un receptor de eventos COM (`win32com.client.DispatchWithEvents`), que la comunidad declaró inviable en su arquitectura MCP [muestra/código comunidad]; en un script normal es posible [inferido].
- También existen en 2026 `DragComponentAnalysisOptionConstants` y `DragComponentCollisionOptionConstants` (opciones del comando Arrastrar componente) [muestra/código comunidad], sin método conocido que las use [inferido].

### 5.2 Alternativa: animar por pasos y capturar fotogramas

Para un mecanismo (p. ej. el Cardán), el giro se puede **imponer por pasos** y capturar cada pose:

```python
import math, os
frames = r"C:\...\temp\frames"; os.makedirs(frames, exist_ok=True)
vista = app.ActiveWindow.View
for k in range(0, 73):                       # 0..360° cada 5°
    ang = math.radians(5 * k)
    rel_ang.Angle = ang                      # una relación angular "motriz" [inferido]
    # o: asm.Variables.Edit("Angulo_motor", str(ang))   [inferido]
    app.DoIdle()
    vista.SaveAsImage(os.path.join(frames, f"f{k:03d}.png"))   # ver 5.3
```

- La forma más limpia de "mover el motor" es **una relación angular en el eje de entrada** cuyo `Angle` (o su variable) se cambia en cada paso; el resto del mecanismo lo arrastra el solver [inferido]. Requiere que el mecanismo esté subdefinido como debe (axiales con `FixedRotate=False`, §3.3).
- Rotar con `PutMatrix`/`Rotate` una pieza con relaciones no sirve: el solver la devuelve a su sitio o la rechaza [inferido].
- El video se arma fuera de Solid Edge con `ffmpeg -framerate 24 -i f%03d.png -pix_fmt yuv420p cardan.mp4` (habilidad `ffmpeg`).
- Comprobación de "mecanismo sano" sin video: tras cada paso, que ninguna relación pase a error (`rel.Status`) y que las piezas fijas no cambien de matriz.

### 5.3 `View.SaveAsImage` y la imagen en blanco

`app.ActiveWindow.View.SaveAsImage(Archivo, [Ancho], [Alto], …)` [inferido: parámetros opcionales]. En un ensamble de 90 ocurrencias devolvió **una imagen en blanco dos veces**, causa no aclarada [verificado en este equipo]. Hipótesis a descartar en orden [inferido]:
1. `ScreenUpdating=False`, ventana minimizada o Solid Edge sin foco → restaurar, `app.DoIdle()`, `View.Fit()` antes de capturar.
2. El render no terminó: `DoIdle()` + pequeña espera antes de guardar.
3. Tamaño de imagen mayor que el búfer de la GPU: probar `Ancho/Alto` explícitos y moderados (p. ej. 1600×900).
4. Alternativa sin API: capturar la ventana con el sistema operativo usando `app.hWnd` (p. ej. `PIL.ImageGrab` sobre el rectángulo de la ventana), o `StartCommand(AssemblyFileSaveAsImage)` interactivo.

### 5.4 Motor y "Simular motor" de verdad

Quedan para la **interfaz**: El usuario crea el motor (Motor, sobre la relación axial), lo simula y graba desde ERA/Animación. Si en 2026 existe un ID de comando para Motor, `buscar_constantes(C, "Motor")` lo encontrará, pero solo abriría el comando [inferido].

---

## 6. Plano (.dft)

### 6.1 Documento, hojas y secciones

```python
dft = app.Documents.Add("SolidEdge.DraftDocument")     # mejor con la plantilla de la universidad
hoja = dft.ActiveSheet
```

- `dft.Sheets`, `dft.ActiveSheet`; las hojas de trabajo y las de **fondo** (rotulación) viven en `dft.Sections` (sección de trabajo y sección de fondo) [inferido: nombres `WorkingSection`/`BackgroundSection`]. Añadir hoja funcionó en SE 2026 [muestra/código comunidad].
- La plantilla `.dft` de la universidad ya trae el fondo con el cuadro de rotulación: **usarla** en `Documents.Add` en lugar de dibujar el cuadro por código.
- `SelectSet.AddAll` solo funciona en planos con hoja activa (falla en piezas y ensambles) [muestra/código comunidad].

### 6.2 Vínculo al modelo y vistas

| Tarea | Llamada | Notas |
|---|---|---|
| Vincular modelo | `ml = dft.ModelLinks.Add(ruta_par_o_asm)` | [muestra/código comunidad] |
| Vista de pieza | `hoja.DrawingViews.AddPartView(ml, Orientación, Escala, x, y, TipoVista)` | [inferido: misma estructura que la de ensamble] |
| Vista de ensamble | `AddAssemblyView(From, Orientation, Scale, x, y, ViewType, [ConfigurationName], [Snapshot=False], [SnapShotQuality=0])` | [doc oficial]. `ViewType`: `seAssemblyDesignedView`, `seAssemblySimplifiedView`, `seAssemblyConfigurationSimplifiedView`. `SnapShotQuality` válido 1–5. |
| Vista con configuración | `DrawingViews.AddWithConfiguration(...)` | Existe en 2026 [muestra/código comunidad]; firma: §1.6. |
| Proyectada (plegada) | `AddByFold(VistaBase, DirecciónPliegue, x, y)` | [doc oficial: existe]; firma [inferido]. |
| Auxiliar | `AddByAuxiliaryFold(...)` | [doc oficial] |
| Detalle | `AddByDetailEnvelope(...)` / `AddDetailView(...)` | [doc oficial] |
| Corte | `DrawingView.AddSectionCut(...)`, `GetSectionCuts()` | La colección `DrawingViews` **no** tiene `AddSectionView` [doc oficial: lista ST7]; la vista de corte se crea desde la vista con línea de corte [muestra/código comunidad: mapa]. Firma [inferido]; si se resiste, hacer el corte en la interfaz. |
| Vista vacía / PMI / chapa | `AddEmptyView`, `AddPMIModelView`, `AddSheetMetalView` | [doc oficial] |
| Alinear | `DrawingViews.Align` / `Unalign` (sobre la selección) | [doc oficial] |
| Escala | propiedad de escala de `DrawingView` (`ScaleFactor`; la comunidad la llama `Scale`) | Fijar 0,5 y releer 0,5 funcionó en 2026 [muestra/código comunidad]. Nombre exacto: §1.6. |
| Actualizar | `drawing_view.Update()` | [muestra/código comunidad] |

Orientaciones (`ViewOrientationConstants`): `igFrontView`, `igTopView`, `igRightView`, `igIsoView`/trimétricas como `igTrimetricTopFrontRightView`, `igDimetricTopBackLeftView`… [doc oficial: algunos nombres]; **valores numéricos con §1.6**. Una vista isométrica a escala 1,0 se creó bien en 2026 [muestra/código comunidad].

### 6.3 Cotas

```python
dims = hoja.Dimensions
d1 = dims.AddLength(dv_linea.Reference)          # cota de una arista de la vista [inferido]
d2 = dims.AddDistanceBetweenObjects(o1, x1, y1, 0, False, o2, x2, y2, 0, False)   # [inferido]
```

- Una cota de distancia de 0,1 m sobre una línea del plano funcionó en 2026 [muestra/código comunidad].
- Para acotar el **modelo** dentro de una vista se usan los elementos 2D de la vista (`DrawingView.DVLines2d`, `DVCircles2d`, `DVArcs2d`) y su `Reference` [inferido].
- `AddRadius(obj)`, `AddCircularDiameter(obj)`, `AddAngle…` para radios, diámetros y ángulos [inferido: nombres]; la comunidad expone cotas lineales, angulares, radiales, diametrales y de coordenadas [muestra/código comunidad].
- **Recuperar cotas del modelo** ("Recuperar cotas"): no se encontró método de API [inferido]; alternativa: `StartCommand` con el ID de Detail correspondiente (buscar "Retrieve" con §1.6) o hacerlo en la interfaz.

### 6.4 Textos, símbolos y rotulación

- Cuadro de texto: `hoja.TextBoxes.Add(x, y, 0)` + `.Text = "…"` [inferido]; crear un texto "Hello" en (0,05; 0,05) funcionó en 2026 [muestra/código comunidad]. Marca de centro y SmartFrame también [muestra/código comunidad].
- **Cuadro de rotulación:** los campos de la plantilla son texto de propiedad (`%{Title}`, `%{Author}`…) ligado a las propiedades del archivo. Se rellena escribiendo las **propiedades** (§2.12) del plano o del modelo vinculado y refrescando el texto de propiedades (`dft.UpdatePropertyTextCacheAndDisplay()` [inferido: nombre]).

### 6.5 Globos

- `Balloon` (41 métodos, 58 propiedades) y `Balloons` (6, 6) existen en fwksupp.tlb de 2026 [muestra/código comunidad]; la hoja expone `hoja.Balloons` [muestra/código comunidad]. Hay muestra C# `CreateBalloon` [muestra/código comunidad].
- Tipos (`DimBalloonTypeConstants`): `igDimBalloonNone=0`, `Circle=1`, `NSided=2`, `Square=3`, `SquareRotated=4`… (14 valores) [muestra/código comunidad].
- **Lo práctico:** pedir globos **automáticos** al crear la lista de piezas (§6.6); quedan vinculados a los números de elemento. Los globos sueltos (`Balloons.Add(...)` [inferido: firma]) no se vinculan solos a la lista.

### 6.6 Lista de piezas

```python
pl = hoja.PartsLists.Add(vista_ensamble, "", 1, 1)
#                        DrawingView, SavedSettings, AutoBalloon, CreatePartsList   [inferido: orden]
pl.Update()                                                                           # [inferido]
```

- `PartsList` (18 métodos, 73 propiedades) y `PartsLists` existen en draft.tlb 2026 [muestra/código comunidad]. **Crear una lista con globos automáticos y colocarla en (0,15; 0,25) funcionó en SE 2026** [muestra/código comunidad].
- `PartsListType`: `igTopLevel=0`, `igAtomic=1`, `igExploded=2` [muestra/código comunidad]. `PartsListComponentType`: piezas, tubos, accesorios, perfiles estructurales.
- `SavedSettings` = nombre de un estilo/configuración guardado de lista de piezas (cadena vacía = predeterminado) [inferido]. Para el formato de la universidad, guardar una vez la configuración en la interfaz y pasar su nombre.
- Leer la tabla (para comprobar cantidades contra el ensamble): filas/columnas/celdas de `PartsList` (muestra `WritePartsListsToExcel`) [muestra/código comunidad].

### 6.7 Tabla de agujeros y otras tablas

- **Tabla de agujeros: no programable** (la colección `HoleTable2` no tiene `Add`) [muestra/código comunidad].
- Tabla de plegado (chapa): funciona [muestra/código comunidad].

### 6.8 Guardar, PDF e imprimir

| Tarea | Llamada | Notas |
|---|---|---|
| Guardar plano | `dft.SaveAs(ruta_nueva)` | Ruta **nueva** siempre (§2.13). |
| PDF | `dft.SaveCopyAs(r"...\plano.pdf")` | 🟢 Escribió el PDF en 2026 [muestra/código comunidad]. Opciones de PDF por parámetros globales [inferido]. |
| DXF/DWG | `dft.SaveCopyAs(ruta.dxf / .dwg)` | [inferido] |
| Imprimir | `dft.PrintOut(...)` o `app.GetDraftPrintUtility()` | Existen [doc oficial: listas de miembros]; la impresora por defecto se leyó como "Solid Edge PS Printer 3.0" [muestra/código comunidad]. |

---

## 7. Robustez

### 7.1 Errores COM frecuentes

`pywintypes.com_error` trae `e.hresult` (con signo). Si es `DISP_E_EXCEPTION (-2147352567)`, el código real está en `e.excepinfo[5]`.

| HRESULT | Decimal | Nombre | Qué suele significar en Solid Edge |
|---|---|---|---|
| 0x80010001 | -2147418111 | `RPC_E_CALL_REJECTED` | Solid Edge ocupado (recalculando o con un **diálogo modal abierto**). Reintentar con espera; si persiste, hay un diálogo que cerrar. |
| 0x8001010A | -2147417846 | `RPC_E_SERVERCALL_RETRYLATER` | Igual: reintentar más tarde. |
| 0x80070057 | -2147024809 | `E_INVALIDARG` | Argumento con forma o tipo incorrecto: cara en vez de `Reference`, arreglo mal formado, enum inválido; o método que la versión no acepta (roscas, superficies) [muestra/código comunidad]. |
| 0x80004005 | -2147467259 | `E_FAIL` | Falla genérica de la operación (geometría imposible, mezclas, cables) [muestra/código comunidad]. |
| 0x80020005 | -2147352571 | `DISP_E_TYPEMISMATCH` | Tipo de parámetro incorrecto; típico al omitir salidas en enlace tardío [muestra/código comunidad]. |
| 0x8002000E | -2147352562 | `DISP_E_BADPARAMCOUNT` | Número de argumentos incorrecto. |
| 0x80020003 | -2147352573 | `DISP_E_MEMBERNOTFOUND` | Miembro inexistente en ese objeto o versión. |
| 0x80070005 | -2147024891 | `E_ACCESSDENIED` | Patrones/simetrías de ensamble en SE 2025/2026 [muestra/código comunidad]. |
| 0x80004003 | -2147467261 | `E_POINTER` | Puntero nulo (p. ej. `AddFlangeByFace`) [muestra/código comunidad]. |
| 0x800706BA | -2147023174 | `RPC_S_SERVER_UNAVAILABLE` | **Edge.exe ya no existe** (se cerró o se cayó). Reconectar; no reintentar la misma llamada [muestra/código comunidad]. |
| 0x800706BE | -2147023170 | `RPC_S_CALL_FAILED` | Solid Edge **se cayó durante la llamada** (visto con `AddAutoSimplify`) [muestra/código comunidad]. |
| 0x800401E3 | -2147221021 | `MK_E_UNAVAILABLE` | `GetActiveObject` sin Solid Edge abierto, o Solid Edge y Python con distinto nivel de privilegios (uno como administrador) [inferido]. |
| 0x807B0086 | — | (propio de SE) | `Louvers.AddSync` [muestra/código comunidad]. |
| **0x80040225** | -2147221979 | `FACILITY_ITF`, código 0x225 | Error **definido por la propia interfaz de Solid Edge** (rango de errores propios de cada servidor). **No encontré documentación pública** de su significado; trátalo como "Solid Edge rechazó la operación en el estado actual" y registra el método, los argumentos y el estado del documento [inferido]. |

### 7.2 Reintentos y filtro de mensajes OLE

Las muestras C# registran siempre `OleMessageFilter.Register()` antes de llamar a Solid Edge [muestra/código comunidad]: el filtro hace que COM **reintente solo** cuando Solid Edge está ocupado. En Python hay dos opciones:

```python
# Opción 1 (simple y suficiente): reintento con espera exponencial
import time, pywintypes
OCUPADO = {-2147418111, -2147417846}
def reintentar(fn, *a, intentos=8, espera=0.25, **k):
    for n in range(intentos):
        try:
            return fn(*a, **k)
        except pywintypes.com_error as e:
            if e.hresult in OCUPADO and n < intentos - 1:
                time.sleep(espera * 2 ** n)
                continue
            raise

# Opción 2: filtro de mensajes propio   [inferido: no probado con SE]
import pythoncom, win32com.server.util
class FiltroMensajes:
    _com_interfaces_ = [pythoncom.IID_IMessageFilter]
    _public_methods_ = ["HandleInComingCall", "RetryRejectedCall", "MessagePending"]
    def HandleInComingCall(self, tipo, tarea, ticks, info): return 0      # SERVERCALL_ISHANDLED
    def RetryRejectedCall(self, tarea, ticks, tipo_rechazo):
        return 250 if ticks < 60000 else -1                                # reintentar 250 ms, máx 60 s
    def MessagePending(self, tarea, ticks, tipo): return 2                 # PENDINGMSG_WAITDEFPROCESS
pythoncom.CoRegisterMessageFilter(win32com.server.util.wrap(FiltroMensajes()))
```

Jarvis ya tiene `se_com_seguro.reintentar`: es la opción 1. Si el reintento se agota, **no** se mata `Edge.exe` (regla de `jarvis-operador`): se avisa al usuario, que casi siempre tiene un diálogo abierto.

### 7.3 Evitar diálogos modales

| Causa | Cómo evitarla |
|---|---|
| `SaveAs`/`SaveCopyAs` a una ruta existente | Comprobar `os.path.exists` y usar un nombre libre; `DisplayAlerts=False` **no** lo evita [verificado en este equipo]. |
| Exportar STEP | Puede abrir un diálogo; la comunidad lo cierra con un "cerrador de diálogos informativos" [muestra/código comunidad]. |
| Primera llamada a perfiles estructurales (frames) | Abre un modal que hay que cerrar [muestra/código comunidad]. |
| `Documents.Add` de soldadura sin plantilla | Se cuelga en un modal: exigir plantilla [muestra/código comunidad]. |
| Abrir archivos con vínculos rotos o de otra versión | Diálogos de vínculos/migración [inferido]: abrir primero a mano o asegurar las rutas. |

Regla general: `DisplayAlerts=False` al conectar [muestra/código comunidad], y si una llamada se queda esperando, sospechar de un diálogo y pedírselo al usuario.

### 7.4 Rendimiento

- `DelayCompute=True` durante lotes de relaciones u operaciones; `ScreenUpdating=False` durante lotes largos; `Interactive=False` si el usuario no debe tocar nada en ese rato. **Siempre** restaurar en `finally`: si el script cae con `ScreenUpdating=False`, Solid Edge queda "congelado" a la vista [inferido].
- `app.DoIdle()` al terminar el lote y antes de exportar o capturar [doc oficial: propósito].
- Leer propiedades de COM es caro: guardar en variables locales los objetos que se reutilizan (colecciones, cuerpos) en vez de recorrer la cadena `doc.Models.Item(1).Body` en cada iteración [inferido].
- En ensambles grandes, `asm.UpdateAll()` una vez al final, no tras cada cambio [muestra/código comunidad: `UpdateAll` sustituye a `Recompute`].

### 7.5 Hilos

- Los objetos COM pertenecen al **apartamento (hilo) que los creó**. Cada hilo que llame a Solid Edge debe hacer `pythoncom.CoInitialize()` al empezar y `pythoncom.CoUninitialize()` al terminar, y obtener **sus propios** proxies (`GetActiveObject` en ese hilo) [inferido: regla COM estándar].
- No pasar un proxy de un hilo a otro. Si hace falta: `pythoncom.CoMarshalInterThreadInterfaceInStream` / `CoGetInterfaceAndReleaseStream` [inferido].
- Patrón recomendado (el de SolidEdge-MCP): **un único hilo STA dedicado a COM** que ejecuta todas las llamadas en cola; el resto del programa (servidor web de Jarvis) solo le encarga trabajos [muestra/código comunidad].

### 7.6 Limpieza de referencias

- Al terminar: restaurar `DelayCompute`, `ScreenUpdating`, `Interactive`; cerrar los documentos que el script abrió (`doc.Close(False)` si no se debe guardar); borrar las referencias (`del occ, asm`) antes de `CoUninitialize` [inferido].
- Detectar un Solid Edge caído leyendo `app.Version` como sonda; si lanza `RPC_S_SERVER_UNAVAILABLE`, descartar el proxy y reconectar [muestra/código comunidad].

### 7.7 Esqueleto de script robusto

```python
import pythoncom, win32com.client as w32
from win32com.client import dynamic

def con_solid_edge(trabajo):
    pythoncom.CoInitialize()
    app = dynamic.Dispatch(w32.GetActiveObject("SolidEdge.Application")._oleobj_)
    previo = (app.DelayCompute, app.ScreenUpdating)
    app.DisplayAlerts = False
    try:
        return trabajo(app)
    finally:
        try:
            app.DelayCompute, app.ScreenUpdating = previo
            app.DoIdle()
        except Exception:
            pass                 # si Solid Edge cayó, no hay nada que restaurar
        del app
        pythoncom.CoUninitialize()
```

---

## 8. Lo que NO se puede por API y alternativas

| Tarea | Por qué no | Alternativa recomendada |
|---|---|---|
| **Crear la explosión** (pasos, líneas de flujo, guardar configuración de explosión) | La explosión **automática** sí tiene método: `asm.AutoExplode` [verificado en este equipo, §11]. Pasos manuales, líneas de flujo y el guardado de la configuración de explosión no tienen método conocido | **A′ (probar primero):** `AutoExplode` → `Configurations.Add("Explosion_1")` → comprobar `ConfigurationType`/`ExplosionsCount`. **A:** `StartCommand` al entorno ERA (IDs en §11) y el usuario ajusta y guarda. **B:** pseudo-explosión con `Move` en una **copia** del ensamble. |
| **Motores, simular motor, animación, video** | Sin interfaces `Motor` ni de video en SE 2026; solo eventos de la línea de tiempo (§5) | Relación angular "motriz" + pasos + `SaveAsImage` + `ffmpeg`; o el usuario en la interfaz. |
| `CheckInterference` desde pywin32 dinámico | Parámetro de salida `Status` [verificado en este equipo] | VARIANT byref o makepy (probar); utilidad C#; filtro por `GetRangeBox`; comando interactivo (§3.6). |
| Patrones / simetrías de ensamble | `E_ACCESSDENIED` en 2025/2026 [muestra/código comunidad] | Bucle de `AddWithMatrix`; `RotateMultipleOccurrences` con copia; patrón en la pieza. |
| Roscas `Threads.Add` | `E_INVALIDARG` [muestra/código comunidad] | Agujero roscado con `HoleData`. |
| Simetría ordenada (`MirrorCopies.Add`) | Registra y no construye [muestra/código comunidad] | Boceto simétrico, `igSymmetric`, o síncrono (`AddSync`). |
| Vaciado (thinwall) con caras abiertas | Selección de caras no lograda por COM [muestra/código comunidad] | Corte interior; o interfaz. |
| Superficies de barrido/solevado/acotadas | `E_INVALIDARG` o caída del proceso [muestra/código comunidad] | Sólidos por `AddLoftedProtrusion`/`AddSweptProtrusion` con `Origins` correctos; o interfaz. |
| `ConvertByFilePath` | No escribe nada [muestra/código comunidad] | Abrir y `SaveCopyAs`. |
| Sobrescribir un archivo existente | Diálogo modal que bloquea [verificado en este equipo] | Nombre nuevo siempre. |
| Tabla de agujeros en plano | Sin `Add` [muestra/código comunidad] | Cotas/notas, o interfaz. |
| ~~Recuperar cotas del modelo en el plano~~ | **Sí existe**: `DrawingView.RetrieveDimensions(...)` y `RetrieveCenterLinesCenterMarks(...)` [verificado en este equipo, §11] | Usar el método; `StartCommand(32803)` solo si falla. |
| Imagen fiable de un ensamble grande | `SaveAsImage` dio blanco [verificado en este equipo] | §5.3: refrescar, tamaño explícito, o captura de ventana con `hWnd`. |
| Eventos COM (sensores, tareas sin modo) | Necesitan receptor de eventos [muestra/código comunidad] | `DispatchWithEvents` en un script dedicado [inferido]. |
| Cualquier comando de interfaz sin método | — | `StartCommand(ID)` + el usuario completa; o .NET (`Interop.SolidEdge`) si es un método con salidas. |

---

## 9. Pendientes de verificar en este equipo

Ensayos cortos, en carpeta temporal, que convertirían [inferido] en [verificado en este equipo]:

1. `firma(asm)` sobre un ensamble de 2026: listar los 98 métodos y buscar `Explode`, `Explosion`, `AutoExplode`, `Motor`, `Animation` (¿qué método consume `AutoExplodeTechniqueConstants`?).
2. `C = cargar_constantes(carpeta_program(app))` y guardar el volcado en un JSON de referencia de Jarvis; leer de ahí los IDs de `AssemblyEnvironmentsExplodedView`, `ExplodeExplodedViewAutomaticExplode`, `AssemblyAssemblyToolsCheckInterference` y cualquier `*Motor*` en 2026.
3. `CheckInterference` con `VARIANT(VT_BYREF|VT_I4, 0)` para `Status` (camino 1 de §3.6).
4. `Configurations.Add("Prueba")` → ¿qué `ConfigurationType` devuelve? ¿aparece en el desplegable del plano?
5. `AddAssemblyView(..., ConfigurationName=<explosión guardada en ERA>)` → ¿sale explosionada?
6. `View.SaveAsImage` con ancho/alto explícitos tras `DoIdle()` + `Fit()` en el ensamble de 90 ocurrencias.
7. Relación angular motriz en el Cardán: cambiar `Angle` en pasos y comprobar que el resto sigue sin errores.
8. `PartsLists.Add` en la plantilla de la universidad: orden real de los 4 parámetros con `firma(hoja.PartsLists, "Add")`.

Cuando un ensayo pase, anotarlo en `jarvis-operador/memoria/lecciones.md` y cambiar aquí la etiqueta.

---

## 10. Fuentes

**Referencia oficial de Siemens (API, ST6–ST8; la de 2026 no es pública en línea)**
- AssemblyDocument, miembros (ST7): https://support.industrysoftware.automation.siemens.com/trainings/se/107/api/SolidEdgeAssembly~AssemblyDocument_members.html
- Relations3d, miembros (ST7): https://support.industrysoftware.automation.siemens.com/trainings/se/107/api/SolidEdgeAssembly~Relations3d_members.html
- Relations3d.AddPlanar (ST6/ST7): https://support.industrysoftware.automation.siemens.com/trainings/se/107/api/SolidEdgeAssembly~Relations3d~AddPlanar.html
- AssemblyDocument.CheckInterference: https://support.industrysoftware.automation.siemens.com/trainings/se/107/api/SolidEdgeAssembly~AssemblyDocument~CheckInterference.html
- AssemblyDocument.CheckInterference2: https://support.industrysoftware.automation.siemens.com/trainings/se/107/api/SolidEdgeAssembly~AssemblyDocument~CheckInterference2.html
- Configurations, miembros / Add / Apply: https://support.industrysoftware.automation.siemens.com/trainings/se/107/api/SolidEdgeAssembly~Configurations_members.html · https://support.industrysoftware.automation.siemens.com/trainings/se/107/api/SolidEdgeAssembly~Configurations~Add.html · https://support.industrysoftware.automation.siemens.com/trainings/se/107/api/SolidEdgeAssembly~Configurations~Apply.html
- Configuration, miembros: https://support.industrysoftware.automation.siemens.com/trainings/se/107/api/SolidEdgeAssembly~Configuration_members.html
- ConfigurationTypeConstants: https://docs.plm.automation.siemens.com/docs/se/108/api/SolidEdgeAssembly~ConfigurationTypeConstants.html
- AssemblyDocument.ExplosionsCount: https://docs.plm.automation.siemens.com/docs/se/108/api/SolidEdgeAssembly~AssemblyDocument~ExplosionsCount.html
- ExplodeCommandConstants (ST6): https://support.industrysoftware.automation.siemens.com/trainings/se/106/api/SolidEdgeConstants~ExplodeCommandConstants.html
- AssemblyCommandConstants (ST7): https://support.industrysoftware.automation.siemens.com/trainings/se/107/api/SolidEdgeConstants~AssemblyCommandConstants.html
- Application, miembros (ST7): https://support.industrysoftware.automation.siemens.com/trainings/se/107/api/SolidEdgeFramework~Application_members.html
- Application.StartCommand: https://support.industrysoftware.automation.siemens.com/trainings/se/107/api/SolidEdgeFramework~Application~StartCommand.html
- DrawingViews, miembros / AddAssemblyView: https://support.industrysoftware.automation.siemens.com/trainings/se/107/api/SolidEdgeDraft~DrawingViews_members.html · https://support.industrysoftware.automation.siemens.com/trainings/se/107/api/SolidEdgeDraft~DrawingViews~AddAssemblyView.html
- Índice del SDK ST10 (redirige al portal con inicio de sesión): https://docs.plm.automation.siemens.com/docs/se/110/api/SolidEdgeTOC.html
- Soporte Siemens, "¿SE 2024 soporta Python?" (PL8721130): https://support.sw.siemens.com/en-US/okba/PL8721130/Does-Solid-Edge-SE224-support-Python-scripting-capability-or-API/index.html

**Código y muestras de la comunidad**
- SolidEdge-MCP (pywin32, medido en SE 226.00.01.04): https://github.com/tylerwagler/SolidEdge-MCP — `CLAUDE.md`, `reference/VERIFICATION_STATUS.md`, `reference/LIVE_SWEEP.md`, `reference/typelib_summary.md`, `reference/TYPELIB_IMPLEMENTATION_MAP.md`, `src/solidedge_mcp/backends/assembly/_query.py`, `src/solidedge_mcp/backends/connection.py`
- SolidEdgeCommunity (organización, repositorios archivados): https://github.com/SolidEdgeCommunity
- Muestras C#/VB: https://github.com/SolidEdgeCommunity/Samples — `Assembly/ReportInterference`, `Assembly/AddOccurrenceWithMatrix`, `Assembly/AddOccurrencesWithTransform`, `Assembly/DeleteOccurrenceGroundRelations`, `Assembly/AddNewConfigurationAndApply`, `Assembly/ReportBom`, `Draft/CreateDrawingView`, `Draft/CreateBalloon`, `Draft/WritePartsListsToExcel`
- Ayuda de usuario ST6, Explosión automática: https://soliddna.com/SEHelp/ST6/EN/assemble_parts/atxpld1c.htm · opciones: https://soliddna.com/SEHelp/ST5/EN/a_h/atxpld2d.htm

**No consultadas en esta investigación** (límite de las herramientas web): el blog y los libros de Jason Newell, los foros de Siemens Community y el PDF "Solid Edge API" de Siemens (https://www.plm.automation.siemens.com/zh_cn/Images/Solid_Edge_API_tcm78-125829.pdf). Buen siguiente paso para confirmar firmas de pieza y plano marcadas [inferido].

---

## 11. Firmas verificadas en la type library de este equipo (2026-10-28)

Leídas con `scripts/firmas_api.py` directamente de `<SE>\Program\*.tlb` (sin abrir Solid Edge). Esto prueba que el método **existe** y cuál es su firma; **no** prueba que funcione desde pywin32 dinámico: los parámetros `[out]` pueden necesitar enlace temprano (makepy) o `VARIANT` byref, como pasó con `CheckInterference`. Etiqueta: [verificado en este equipo: firma].

### Ensamble (`AssemblyDocument`, 223 miembros en SE 2026)

```
AutoExplode(AutoExplodeSelectionType: AutoExplodeSelectionTypeConstants[in],   # 0 seTopLevelAssembly · 1 seSubassembly
            BindAllSubassemblies: bool[in],
            ExplodeTechnique: AutoExplodeTechniqueConstants[in],                 # 0 seBySubassemblyLevel · 1 seByIndividualPart
            ErrorCode: BSTR*[out],
            SpreadDistance: double[in, opt],                                     # metros
            Subassembly: IDispatch[in, opt]) -> HRESULT

DragComponentRotation(OccurrenceToDrag, AnalysisOption[0 sin análisis · 1 detectar colisiones],
            CollisionOption[0 solo la pieza arrastrada · 1 entre todas], Angle: double,
            ConsiderMovingParts: bool, ConsiderInactiveParts: bool, MoveGroundedParts: bool,
            DirectionX, DirectionY, DirectionZ: double, Sensitivity: double[opt],
            EdgeOrAxis: IDispatch[opt], CollisionFound: bool*[out,opt],
            CollidingPart: SAFEARRAY(IDispatch)*[out,opt]) -> HRESULT
DragComponentTranslation(...)   # igual, con Distance en lugar de Angle

CheckInterference / 2 / 3 / 4(NumElementsSet1, Set1: SAFEARRAY(IDispatch)*, Status: InterferenceStatusConstants*[out],
            ComparisonMethod[opt: 1 Set1vsSet2 · 2 Set1vsAllOther · 3 vsVisible · 4 vsItself], ...,
            NumInterferences*[out], ... , ShowIntersectionVolume[opt, solo la 4])
# InterferenceStatusConstants: 1 sin interferencia · 2 confirmada · 3 probable · 4 ambas · 5 análisis incompleto
```

`ExplosionsCount`, `Configurations`, `ActiveConfiguration` también existen.

### Relaciones (`Relations3d`)

```
AddGround(Occurrence)
AddPlanar(Plane1, Plane2, NormalsAligned: bool, ConstrainingPoint1: SAFEARRAY(double), ConstrainingPoint2: SAFEARRAY(double))
AddAxial(Axis1, Axis2, NormalsAligned: bool)
AddAngular(Element1, Element2, ReverseElement1Direction: bool, ReverseElement2Direction: bool,
           MeasureElement1, MeasureElement2, Angle: double, MeasureToPositiveSide: bool,
           MeasureFromPositiveSide: bool, MeasureCCW: bool)
AddTangent(Element1, Element2, ConstrainingPoint1, ConstrainingPoint2, Offset: double, IsHalfSpacePositive: bool)
AddGear(Element1, Element2, GearType, RatioType, GearRatio1: double, GearRatio2: double, Flip: bool)
AddCenterPlane(PlacementElement1, PlacementElement2, TargetElement1, TargetElement2, 4 × SAFEARRAY(double))
AddRigidSet(OccurrenceCount: long, Occurrences: SAFEARRAY(IUnknown))
AddPath(ConstrainingFollowerElement, ConstrainingCamEdges: SAFEARRAY(IUnknown))
AddPoint(PointGeometry, PointKeyPoint, ConnectGeometry, ConnectKeyPoint[opt])
```

### Configuraciones

```
Configurations.Add(Name: BSTR) -> Configuration
Configurations.Apply(Index: VARIANT, ActivationOverride[opt], SimplifyOverride[opt])
Configurations.AddDerivedConfig(nConfig, nZones, nQueries, configs, zones, queries, NewName)
ConfigurationTypeConstants: 0 seConfigurationType_Display · 1 seConfigurationType_Explode
```

### Plano

```
DrawingViews.AddPartView(ModelLink, Orientation, Scale, x, y, ViewType)
DrawingViews.AddPartViewByConfiguration(ModelLink, Orientation, Scale, x, y, ViewType, ConfigurationName)
DrawingViews.AddAssemblyView(ModelLink, Orientation, Scale, x, y, ViewType, ConfigurationName[opt], Snapshot[opt], SnapShotQuality[opt])
DrawingViews.AddWithConfiguration(ModelLink, Orientation, Scale, x, y, ConfigFileName, ConfigurationName)
DrawingViews.AddByFold(DrawingView, FoldDir, x, y)
DrawingView.Update()
DrawingView.RetrieveDimensions(IsRetrieve, DimensionStyleName, TypeLinear, TypeRadial, TypeAngular, TypeAnnotation,
           TypeCenterMark, GetDuplicatedRadial, GetDimensionToHiddenLines, ProjectCenterMark, ConnectCenters,
           GetCenterMarkToCircle, GetCenterMarkToArc)            # todos opcionales
DrawingView.RetrieveCenterLinesCenterMarks(...)                 # todos opcionales
PartsLists.Add(DrawingView, SavedSettings: BSTR, AutoBalloon: long, CreatePartsList: long) -> PartsList
DraftDocument.UpdateRetrievedDimensionsAndAnnotations()
PartsLists.AddEx(DrawingView, LinkToActive: long, SavedSettings: BSTR, AutoBalloon: long, CreatePartsList: long)
Sheet.Balloons.Add(x, y, z) · Balloons.AddByTerminator(TerminatorObject, x, y, z, keyPoint1: bool)
```

`SavedSettings` de la lista de piezas: nombre de una configuración guardada de `Template\Reports\DraftList.txt`. La instalación trae **«ISO»**, con las columnas del plano del curso (número de elemento, nombre de archivo, autor, cantidad), y **«Explosionada»** (ver `04_planos_draft.md`).

### Pieza (verificadas y probadas en vivo el 2026-10-28)

```
Models.AddFiniteExtrudedProtrusion(NumberOfProfiles, ProfileArray, ProfilePlaneSide, ExtrusionDistance, ...opt)
Models.AddFiniteRevolvedProtrusion(NumberOfProfiles, ProfileArray, ReferenceAxis, ProfilePlaneSide, AngleofRevolution, ...opt)
ExtrudedCutouts.AddFinite(Profile, ProfileSide, ProfilePlaneSide, Depth)
ExtrudedCutouts.AddThroughAll(Profile, ProfileSide, ProfilePlaneSide)
Holes.AddFinite(Profile, ProfilePlaneSide, FiniteDepth, HoleData) · AddFromTo · AddThroughNext
Profile.End(ValidationCriteria) -> int          # igProfileClosed = 1; 0 = perfil válido
Body.GetRange(min, max) · Body.GetExactRange(min, max) · Body.Volume   # Body.Range NO existe
Feature.Status: igFeatureOK 1216476310 · igFeatureFailed 1216476311 · Warned …312 · Suppressed …313 · RolledBack …314
```

Probado en vivo: con un perfil circular, `ExtrudedCutouts.AddFinite(perfil, igRight, igSymmetric, d)` quitó el **exterior** del círculo con estado OK. `igLeft` quitó el interior, que es lo correcto para un agujero. Mide siempre el volumen antes y después de un corte.

### IDs de comando útiles (`StartCommand`)

| Entorno | Comando | ID |
|---|---|---|
| Ensamble | Entrar a Explosionar-Renderizar-Animar (`AssemblyEnvironmentsExplodedView`) | 33079 |
| Ensamble | Verificar interferencia | 25039 |
| Ensamble | Configuraciones de visualización | 32826 |
| ERA | Explosión automática | 65062 |
| ERA | Explosionar (manual) | 65064 |
| ERA | Ajustar distancia de separación | 65065 |
| ERA | Reposicionar | 65066 |
| ERA | Quitar · Contraer · Desexplosionar | 65067 · 65069 · 65068 |
| ERA | Añadir / quitar quiebre (joggle) | 65071 / 65072 |
| ERA | Atar / desatar subensamble | 58001 / 58002 |
| ERA | Mover pieza | 32807 |
| ERA | Líneas de flujo · terminadores | 33095 · 33096 |
| Estudio (render/animación) | Línea de tiempo y reproducción | 33097 |
| Estudio | Asistente de trayectoria de vuelo · añadir/quitar fotogramas | 40273 · 33098 / 33099 |
| Estudio | Configurar render · render de escena · de área | 40275 · 40265 · 40264 |
| Plano | Lista de piezas | 32784 |
| Plano | Recuperar cotas | 32803 |
| Plano | Tabla de agujeros | 10516 |

En `MotionCommandConstants` (58 IDs) **no aparece ningún comando de motor**: solo herramientas comunes (medir, interferencia, propiedades físicas, visualización). El motor y "Simular motor" se hacen en la interfaz.

Para consultar cualquier otra firma: `python -X utf8 scripts/firmas_api.py assembly.tlb AssemblyDocument AutoExplode` (ver el propio script).
