# 02 · Modelado de piezas (.par) y chapa (.psm) en Solid Edge 2026 — modo ORDENADO

> Capítulo de referencia de la habilidad `solid-edge-experto`. Público: la sesión de Claude que actúa como
> **operario experto**: recibe un plano 2D (PDF/imagen, cotas en mm, tolerancia general ±0,5) y construye la
> pieza en Solid Edge 2026 **en modo ordenado** (con historial en el PathFinder), por API COM desde Python
> a través de Jarvis. El usuario revisa en pantalla. Interfaz de Solid Edge **en español**.
> Capítulos hermanos: `01_interfaz_y_fundamentos.md` (interfaz, ordenado vs síncrono), `04_planos_draft.md`
> (planos), `05_api_automatizacion.md` (API en detalle). Para EJECUTAR en este equipo: habilidad `jarvis-operador`.

## Tabla de contenido

0. [Leyenda, alcance y advertencias](#0-leyenda-alcance-y-advertencias)
1. [Conceptos base del entorno Pieza ordenado](#1-conceptos-base-del-entorno-pieza-ordenado)
2. [Bocetos y perfiles](#2-bocetos-y-perfiles)
   2.1 Planos de referencia · 2.2 Boceto vs perfil · 2.3 Herramientas 2D · 2.4 Relaciones 2D ·
   2.5 Cotas · 2.6 Variables · 2.7 Perfil bien definido y errores de perfil
3. [Operaciones sólidas](#3-operaciones-sólidas)
   3.0 Tabla maestra · 3.1 Extruir · 3.2 Cortar · 3.3 Revolución · 3.4 Barrido · 3.5 Por secciones (loft) ·
   3.6 Helicoidal · 3.7 Agujero · 3.8 Rosca · 3.9 Redondeo · 3.10 Chaflán · 3.11 Pared delgada / espesor ·
   3.12 Nervio, red de nervios, labio, desmoldeo · 3.13 Patrones · 3.14 Simetría · 3.15 Copia de pieza,
   sistemas de coordenadas, puntos clave
4. [Edición y corrección de errores](#4-edición-y-corrección-de-errores)
5. [Material, propiedades físicas y propiedades del archivo](#5-material-propiedades-físicas-y-propiedades-del-archivo)
6. [Chapa (.psm)](#6-chapa-psm)
7. [Método: del plano 2D al modelo 3D](#7-método-del-plano-2d-al-modelo-3d)
8. [Lista de verificación para dar una pieza por terminada](#8-lista-de-verificación-para-dar-una-pieza-por-terminada)
9. [Fuentes](#9-fuentes)

---

## 0. Leyenda, alcance y advertencias

**Marcas de procedencia** (cada dato lleva una):

| Marca | Significa |
|---|---|
| **[doc]** | Documentación oficial de Siemens: ayuda de Solid Edge (espejo público de la ayuda ST5/ST6 en soliddna.com), referencia oficial de la API (Part Type Library), blog oficial de Solid Edge o base de conocimiento de soporte de Siemens. |
| **[fuente secundaria]** | Curso universitario, distribuidor (DesignFusion), GrabCAD, temario de curso. |
| **[inferido]** | Conocimiento de dominio / práctica habitual de Solid Edge, no verificado en una fuente durante esta investigación. Tratar como hipótesis razonable y confirmar en pantalla. |
| **[traducción probable]** | Nombre en español NO verificado en la interfaz de Solid Edge 2026. El nombre en inglés es el ancla. |
| **[API?]** | Método o firma de la API no verificados; confirmar en `05_api_automatizacion.md` o con prueba en temporal. |
| **[local]** | Visto en el código de Jarvis de este equipo (`C:\Jarvis\cad_atomic_lib.py`). |

**Advertencias que cambian cómo usar este capítulo:**

1. **La ayuda oficial de 2026** (docs.sw.siemens.com) es una aplicación web que no se pudo leer como texto
   durante la investigación. El contenido funcional sale de la ayuda ST5/ST6 (2012-2013), de la referencia
   oficial de la API y de las novedades oficiales de 2026. El comportamiento de las operaciones ordenadas
   cambió poco desde entonces, pero **los nombres de botones y la barra de comandos sí cambiaron**: en 2026
   Siemens rediseñó las barras de comandos [doc — blog 2026]. Si un nombre no aparece, buscar por el inglés
   o por el ícono.
2. **Nombres en español:** no hay ayuda oficial en español accesible. Los nombres en español de este capítulo
   vienen de cursos en español (IMH, UPV/EHU con Solid Edge V20) o son traducciones probables. **La API COM
   no depende del idioma**: los métodos se llaman igual con interfaz en español. Cuando haya que decirle a
   el usuario qué botón pulsar, dar el nombre español probable + el inglés + la ubicación (pestaña > grupo).
3. **Historia de nombres:** antes de ST7 la extrusión se llamaba *Protrusion* y el corte *Cutout*; en la
   ayuda ST6 ya aparecen como **Extrude** y **Cut** en *Home > Solids* [doc]. En la API siguen los nombres
   viejos (`ExtrudedProtrusions`, `ExtrudedCutouts`) [doc]. En español antiguo (V20): «Protrusión por
   proyección», «Vaciado» [fuente secundaria — EHU].

---

## 1. Conceptos base del entorno Pieza ordenado

- **Entornos:** Pieza sólida `.par`, Pieza de chapa `.psm`, Conjunto `.asm`, Plano `.dft`, Soldadura `.pwd`
  [fuente secundaria — EHU].
- **Modelado por operaciones:** la pieza se construye con operaciones (protrusiones, vaciados, agujeros,
  redondeos…), no con booleanas libres [fuente secundaria — UPM]. Las operaciones basadas en perfil son
  **asociativas a su perfil**: si cambia el perfil, la operación se recalcula [doc].
- **Operación base:** la primera operación sólida. Su perfil **debe ser cerrado** [doc]. Se crea con Extruir,
  Revolución, Barrido, Por secciones, Helicoidal o Red de nervios [doc]. Construir la base **antes** de
  cualquier operación de tratamiento o de quitar material [doc].
- **Ordenado vs síncrono:** el PathFinder tiene una parte síncrona y una ordenada [doc]. En ordenado, el orden
  del árbol importa y cada operación depende de las anteriores. El curso pide **ordenado**: comprobar que el
  documento arranca en ordenado (opción de la plantilla / *Herramientas > Modelo > Ordenado*) [inferido;
  detalle en el capítulo 01]. Por API existe la propiedad del documento para el modo de modelado
  (`ModelingMode`) [API?].
- **Flujo de cualquier comando ordenado de perfil** (barra de comandos con pasos) [doc]:
  1. **Plano o boceto** — elegir cara plana o plano de referencia (o *Seleccionar desde boceto*).
  2. **Dibujar perfil** — se abre la vista de perfil.
  3. **Lado** — de qué lado va el material (se salta con perfiles cerrados).
  4. **Extensión** — cuánto se extiende (valor, cursor o punto clave de otra operación).
  5. **Tratamiento** (opcional) — ángulo de desmoldeo o abombado (*crown*).
  6. **Terminar** — se construye; perfil y cotas se ocultan.
  Se puede volver a cualquier paso desde la barra de comandos antes de terminar [fuente secundaria — EHU].
- **Vista previa dinámica** durante la extensión: Ctrl+Mayús+D [doc].
- **Unidades:** plantilla ISO métrica en mm. **La API trabaja en metros y radianes** (unidades internas):
  50 mm → `0.05` [inferido; muy consolidado — confirmar en el capítulo 05].

---

## 2. Bocetos y perfiles

### 2.1 Planos de referencia

**Planos base** (los tres de la plantilla) [inferido; nombres V20 de fuente secundaria — EHU]:

| Plano | EN | ES (V20, captura EHU) | ES 2026 probable | Contiene |
|---|---|---|---|---|
| XY | Top | Planta (xy) | Plano superior (xy) [traducción probable] | Vista superior |
| YZ | Right | Derecha (yz) | Plano derecho (yz) [traducción probable] | Vista lateral derecha |
| XZ | Front | Alzado (xz) | Plano frontal (xz) [traducción probable] | Vista frontal |

Por API: `doc.RefPlanes.Item(1..3)`. El orden habitual es 1 = Superior XY, 2 = Derecho YZ, 3 = Frontal XZ
[inferido — **verificar siempre con `.Name`** antes de usar].

**Planos creados** — *Inicio > Planos >* lista desplegable [inferido para ubicación; API = doc]:

| Tipo (ES probable) | EN | Se define con | API `RefPlanes.` |
|---|---|---|---|
| Coincidente | Coincident | Una cara plana o plano (copia en el mismo sitio) | (se usa la cara directamente) [inferido] |
| Paralelo | Parallel | Plano/cara + distancia + lado | `AddParallelByDistance` [doc] |
| Paralelo tangente | Parallel by tangent | Plano + cara curva a la que es tangente | `AddParallelByTangent` [doc] |
| En ángulo | Angled | Plano/cara + arista o eje de giro + ángulo | `AddAngularByAngle` [doc] |
| Perpendicular | Perpendicular | Como el angulado, a 90° | `AddAngularByAngle` con 90° [inferido] |
| Normal a curva | Normal to Curve | Curva/arista + punto (extremo, distancia, fracción, punto clave) | `AddNormalToCurve`, `…AtDistance`, `…AtArcLengthRatio`, `…AtDistanceAlongCurve`, `…AtKeyPoint` [doc] |
| Por 3 puntos | By 3 Points | Tres puntos clave | `AddBy3Points` [doc] |
| Tangente | Tangent | Cilindro/cono a un ángulo o en un punto clave; superficie curva en punto clave | `AddTangentToCylinderOrConeAtAngle`, `…AtKeyPoint`, `AddTangentToCurvedSurfaceAtKeyPoint` [doc] |

Regla práctica: **bocetar sobre planos de referencia** (base o creados con distancia/ángulo del plano) antes
que sobre caras del sólido, salvo que la cara sea estable. Una cara que desaparece en una edición deja la
operación **flotante** (ver §4.4) [doc + inferido].

### 2.2 Boceto independiente vs perfil dentro de la operación

- El perfil se puede **dibujar dentro del comando** (queda consumido por la operación) o **seleccionar de un
  boceto previo** con *Opciones de crear desde > Seleccionar desde boceto* (solo si el documento tiene
  bocetos) [doc].
- Los bocetos aparecen en el PathFinder igual que las operaciones [fuente secundaria — UPM].
- **Cuándo usar boceto aparte** [inferido]: si el mismo contorno alimenta varias operaciones, si es una
  trayectoria de barrido o una sección de loft, o si se quiere editar sin entrar en la operación.
- **Proyectar/Incluir aristas** (*Include*, en V20 «Incluir»): copia aristas del sólido al perfil con vínculo
  asociativo; útil para cortes que siguen el contorno existente [doc mención en chapa; resto inferido].

### 2.3 Herramientas de dibujo 2D

Pestaña *Boceto* (o *Inicio* dentro del perfil) > grupo *Dibujar* [inferido]. Nombres ES = [traducción
probable] salvo indicación.

| Herramienta (ES) | EN | Uso / opciones | API (en el `Profile`) |
|---|---|---|---|
| Línea | Line | Encadenada; con IntelliSketch da tangencia/perpendicularidad al vuelo | `Lines2d.AddBy2Points(x1,y1,x2,y2)` [local] |
| Arco | Arc (tangent / 3 points / center) | Tangente al final de línea, por 3 puntos, por centro | `Arcs2d.AddByCenterStartEnd`, `AddByStartAlongEnd` [local] |
| Círculo | Circle (center / 3 points / tangent) | Por centro y radio, 3 puntos, tangente | `Circles2d.AddByCenterRadius` [local] |
| Rectángulo | Rectangle (2 points / center / 3 points) | Por centro: queda simétrico respecto al origen | Rectángulo = 4 líneas + relaciones [inferido] |
| Polígono | Polygon (by center) | N lados inscrito/circunscrito | [API?] |
| Ranura | Slot | Ojal/colisa; ancho + centro a centro | [API?] |
| Elipse, Curva | Ellipse, Curve | Curva = B-spline por puntos | [API?] |
| Redondeo 2D («Acuerdo» en V20) | Fillet | Redondea la esquina de dos elementos | `Relations2d.AddFillet` crea la relación [doc] |
| Chaflán 2D | Chamfer | Esquina a distancia/ángulo | `Relations2d.AddChamfer` [doc] |
| Recortar / Recortar esquina | Trim / Trim Corner | Limpia sobrantes; esquina = recorta/extiende dos elementos | — |
| Extender | Extend to Next | Alarga hasta el siguiente elemento | — |
| Dividir | Split | Parte un elemento en un punto | — |
| Desplazamiento / Desplazamiento simétrico | Offset / Symmetric Offset | Copia paralela a distancia (simétrico: a ambos lados, p. ej. ranuras) | [API?] |
| Simetría (espejo 2D) | Mirror | Copia simétrica respecto a una línea | — |
| Mover, Rotar, Escalar, Estirar | Move, Rotate, Scale, Stretch | Edición 2D | — |
| Patrón 2D rectangular/circular | Rectangular/Circular Pattern (2D) | Repetición dentro del boceto | [API?] |
| Construcción | Construction | Convierte en geometría auxiliar (no forma perfil) | propiedad del elemento [API?] |
| Eje de revolución | Axis of Revolution | Marca la línea eje para Revolución | `Profile.SetAxisOfRevolution` [API?] |

Mientras se dibuja, **IntelliSketch** propone relaciones (conectado, tangente, colineal, perpendicular,
paralelo…) y, según la preferencia, las mantiene o solo las usa para colocar [fuente secundaria — eng-tips,
citando la ayuda]. **Alt** suspende IntelliSketch temporalmente; útil en bocetos cargados [fuente
secundaria]. *Asas de relación* (*Relationship Handles*, grupo *Relacionar*) muestra las relaciones [fuente
secundaria].

### 2.4 Relaciones 2D (restricciones geométricas)

Grupo *Relacionar* [inferido para la ubicación]. Significados = [doc] (ayuda ST5 «Geometric Relationships»).

| Relación (ES probable) | EN | Qué impone | API `Relations2d.` [doc] |
|---|---|---|---|
| Conectar | Connect | Une un punto clave a otro elemento o punto clave; también punto-sobre-elemento (símbolo X) | `AddKeypoint`, `AddPointOn` |
| Concéntrico | Concentric | Centros de arcos/círculos coincidentes | `AddConcentric` |
| Horizontal/Vertical | Horizontal/Vertical | Modo 1: línea horizontal/vertical. Modo 2: alinea puntos medios, centros o extremos | `AddHorizontal`, `AddVertical`, `AddHorizontalAlign`, `AddVerticalAlign` |
| Colineal | Collinear | Dos líneas sobre la misma recta | `AddColinear` |
| Paralelo | Parallel | Misma orientación | `AddParallel` |
| Perpendicular | Perpendicular | 90° entre elementos | `AddPerpendicular` |
| Tangente (+ variantes de curvatura) | Tangent | Tangencia; variantes de curvatura exigen B-spline | `AddTangent`, `AddTangentEqualCurvature` |
| Igual | Equal | Mismas longitudes o mismos radios | `AddEqual` |
| Simétrico (+ Eje de simetría) | Symmetric | Elementos simétricos respecto a una línea o plano: posición y tamaño | `AddSymmetric` |
| Fijar / Bloquear | Lock / Fix | Fija elemento o punto clave (quita 2 grados de libertad al punto) | `AddFix`, `AddKeypointFix` («Lock» en la interfaz) |
| Conjunto rígido | Rigid Set | Bloque de elementos 2D que se mueve como uno (no incluye cotas) | `AddSet` [doc para la relación; mapeo inferido] |
| Punto medio | (Connect to midpoint) | Conectar al punto clave «medio» de una línea | `AddKeypoint` con punto clave medio [inferido] |

Reglas [doc]: varias relaciones pueden coexistir en un punto (conectar + tangente donde un arco toca una línea);
dibujar con precisión y mirar los símbolos, porque **un «conectar» mal puesto deja el perfil abierto**; con
*QuickPick* se aísla y borra una relación concreta entre varias superpuestas. El **Asistente de relaciones**
(*Relationship Assistant*) añade relaciones de forma automática a lo ya dibujado [doc].
Por API, `AddHorizontal` falla si la línea ya tiene relación vertical [doc] → las relaciones contradictorias
dan error, no se «arreglan solas».

### 2.5 Cotas

- **Cota inteligente** (*Smart Dimension*): una herramienta que decide sola si es longitud, radio, diámetro o
  ángulo según lo que se seleccione [inferido]. Otras: *Distancia entre*, *Ángulo entre*, *Cota de
  coordenadas*, *Diámetro simétrico* (para perfiles de revolución dibujados como media sección: acota el
  diámetro respecto al eje) [inferido].
- **Impulsoras (driving) vs impulsadas (driven):** una cota **impulsora** (bloqueada) controla la geometría; una
  **impulsada** solo informa. Se alternan con *Bloquear/Desbloquear* en la barra de la cota [inferido]. En los
  agujeros, una cota de tamaño puesta sobre el círculo de agujero **queda impulsada**; el tamaño lo da el
  cuadro de opciones del agujero, y una relación que intente fijar el tamaño provoca aviso de sobrerrestricción
  [doc].
- **Escribir el valor exacto del plano** (nominal, no el límite de tolerancia). Con ±0,5 general, la cota del
  plano es la nominal: 40 → 40,000 [inferido — criterio de modelado].
- **Acotar como el plano:** mismas referencias (datums) y mismo esquema (en cadena, en paralelo, desde un eje).
  Así la intención de diseño coincide y el plano 2D podrá recuperar las cotas [inferido].
- API: `Profile.Dimensions.AddLength`, `AddRadius` [local para AddRadius], `AddDistanceBetweenObjects`,
  `AddAngleBetweenObjects` [API?]. El nombre del sistema de cada cota es tipo `V123`.

### 2.6 Variables (Tabla de variables)

- *Herramientas > Variables* [inferido]. Lista las cotas (tipo *Dim*) y variables de usuario (tipo *Var*),
  con nombre, valor, unidad y **fórmula** [inferido].
- Usos: renombrar `V123` → `Largo`; escribir fórmulas (`=Largo/2`, `=Diametro*0.5+2`); enlazar con Excel;
  piezas paramétricas (familias) [inferido].
- Regla de oro: una sola fuente de verdad por medida. Si dos cotas del plano son la misma medida (p. ej. dos
  agujeros iguales), usar la relación *Igual* o una fórmula, no dos valores escritos a mano [inferido].
- API: `doc.Variables.Add(nombre, formula, tipo_unidad)` y la propiedad `Formula` de la cota [API?].

### 2.7 Perfil bien definido y errores de perfil

- Solid Edge **permite** construir con perfiles no totalmente definidos (es permisivo) [inferido]. El curso y la
  robustez piden **totalmente definido**: cada elemento con posición y tamaño fijados por cotas o relaciones,
  ligado al origen/planos. Según versión, el grupo *Relacionar* ofrece mostrar el estado del boceto con colores
  [inferido — verificar en pantalla].
- **Validación de perfil:** cada perfil se valida contra lo que exige su operación. Si es inválido aparece el
  **Asistente de errores de perfil** (*Profile Error Assistant*): describe el error, al pasar el ratón resalta
  el elemento culpable y permite seleccionarlo, borrarlo, recolorearlo o pasarlo a construcción; luego
  **Validar** [doc].
- **Perfil abierto:** sus extremos se extienden hasta cortar el modelo (líneas en recto, arcos radialmente; un
  arco abierto se completa como círculo) [doc]. Útil para cortes que «rebanan» una cara.
- **Varios perfiles en una operación:** todos cerrados (Extruir, Revolución, Cortar, Corte por revolución, Red
  de nervios) y, en revolución, con eje común [doc].
- **Errores típicos de perfil** [inferido salvo lo marcado]:
  - Hueco minúsculo entre extremos (falta *Conectar*) → «perfil abierto» [doc: causa citada en ayuda].
  - Líneas duplicadas o superpuestas (doble clic, copiar encima) → autointersección.
  - Lazo que se cruza a sí mismo (forma de 8).
  - Sobrante sin recortar en una esquina (T) → ramificación.
  - Geometría de construcción olvidada como normal, o al revés.
  - Lazos anidados: un lazo cerrado dentro de otro genera un hueco (isla) en la extrusión; si no se quería,
    sobra el lazo interior.
  - En revolución: perfil que cruza el eje → sólido que se autointersecta.

---

## 3. Operaciones sólidas

### 3.0 Tabla maestra

Ubicación habitual: *Inicio > Sólidos* para crear/quitar material [doc ST6], *Inicio > Operaciones/Patrón*
para el resto [inferido]. Nombres ES = [traducción probable] salvo fuente indicada.

| Operación | ES | EN | Opciones clave | Cuándo | API |
|---|---|---|---|---|---|
| Protrusión extruida | Extruir («Protrusión por proyección» V20) | Extrude | Finita, A través de todo, Hasta siguiente, Desde-hasta, Hasta punto clave; simétrica; tratamiento; espesor de pared (2026) | Prismas, placas, perfiles constantes | Base: `Models.AddFiniteExtrudedProtrusion` [doc][local]; siguientes: `Model.ExtrudedProtrusions.AddFinite…` [API?] |
| Vaciado extruido | Cortar / Vaciado | Cut | Igual que Extruir | Bolsillos, ranuras pasantes, recortes de contorno | `ExtrudedCutouts.AddFinite`, `AddThroughAll`, `AddThroughNext`, `AddFromTo`, `AddFiniteByKeyPoint` (+ `…Multi`) [doc][local] |
| Revolución | Revolución | Revolve | Ángulo finito, 360°, simétrica; eje en el perfil | Ejes, bujes, poleas, pasadores | `Models.AddFiniteRevolvedProtrusion` [doc] |
| Corte por revolución | Corte/Vaciado por revolución | Revolved Cut | Igual | Gargantas, ranuras de anillo, avellanados especiales | `RevolvedCutouts.AddFinite` [local] |
| Barrido | Protrusión por barrido | Sweep | 1 trayectoria + 1 sección / varias | Tubos curvos, asas, juntas | `Models.AddSweptProtrusion` [doc]; `SweptCutouts` [doc] |
| Por secciones | Protrusión por secciones («Desvanecido» [no verificado]) | Loft | Secciones cerradas, puntos de inicio, curvas guía | Transiciones de sección (p. ej. carenados, toberas) | `Models.AddLoftedProtrusion` [doc]; `LoftedCutouts` [doc] |
| Helicoidal | Protrusión/Vaciado helicoidal | Helix | Paso, vueltas, altura, mano, radio/paso variable | Muelles, roscas especiales | `Models.AddFiniteBaseHelix` [doc]; `HelixProtrusions/HelixCutouts` [doc] |
| Agujero | Agujero | Hole | Simple, roscado, cónico, avellanado, refrentado; extensiones | TODO agujero normalizado o con cota de agujero | `HoleDataCollection.Add` + `Holes.AddFinite/AddThroughAll/AddThroughNext/AddFromTo` [doc para Holes; HoleData API?] |
| Rosca | Rosca | Thread | Cosmética sobre cara cilíndrica | Ejes roscados, agujeros ya hechos | `Threads.Add` [doc nombre; firma API?] |
| Redondeo | Redondeo | Round | Constante, variable, mezcla (*blend*) | Aristas con R | `Rounds.Add`, `AddVariable`, `AddBlend` [doc][local] |
| Chaflán | Chaflán | Chamfer | Retranqueos iguales, ángulo + retranqueo, retranqueos distintos | Aristas «1×45°» | `Chamfers.AddEqualSetback`, `AddSetbackAngle`, `AddUnequalSetback` [doc] |
| Pared delgada | Pared delgada / Vaciado de pared («Dar espesor» IMH, sin confirmar) | Thin Wall | Espesor común, caras abiertas, espesor único | Cajas, carcasas | `Thinwalls.Add` [doc nombre; firma API?] |
| Región delgada / Engrosar | Región con espesor / Incrementar espesor [fuente secundaria — IMH] | Thin Region / Thicken | — | Vaciar solo una zona / dar espesor a caras | `Thins`, `Thickens`, `Models.AddThickenFeature` [doc nombres] |
| Nervio | Nervio / Refuerzo [fuente secundaria — IMH «refuerzos»] | Rib | Perfil abierto, espesor, extender | Refuerzos interiores | `Ribs` [doc nombre] |
| Red de nervios | Red de refuerzos [fuente secundaria — IMH] | Web Network | Varios trazos abiertos | Cuadrículas de nervios | `Models.AddWebNetwork` [doc] |
| Labio | Reborde [fuente secundaria — IMH «rebordes»] | Lip | Aristas + ancho/alto | Encastres de carcasas | `Lips` [doc nombre] |
| Desmoldeo | Ángulo de desmoldeo / Dividir desmoldeo [fuente secundaria — IMH] | Draft | Desde plano, aristas, línea de partición | Piezas fundidas/inyectadas | `Drafts` [doc nombre] |
| Patrón | Patrón (rectangular, circular, a lo largo de curva, de relleno) | Pattern / Pattern Along Curve / Fill Pattern | Rejilla, polar, curva, relleno (2026) | Repeticiones «n×» | `Patterns.AddByRectangular`, `AddByCircular`, `AddByCurve`, `AddByFill` [doc nombres; firmas API?] |
| Simetría | Copia simétrica de operación / de pieza | Mirror Copy Feature / Part | Plano de simetría | Piezas simétricas | `MirrorCopies.Add`, `MirrorParts` [doc nombres] |
| Copia de pieza | Copia de pieza | Part Copy | Vínculo a otro .par | Reutilizar geometría | `Models.AddCopiedPart`, `CopiedParts` [doc] |

### 3.1 Extruir (protrusión)

Procedimiento ordenado [doc]:
1. *Inicio > Sólidos > Extruir*.
2. Elegir cara plana o plano de referencia (o *Seleccionar desde boceto*).
3. Dibujar el perfil (cerrado si es la base; abierto permitido después). Con perfil abierto, clic en el lado
   del material.
4. **Extensión** — tipos [doc, ayuda + API `igFinite, igThroughAll, igToNext, igToKeyPoint, igFromTo`]:

| Extensión (ES probable) | EN | Comportamiento |
|---|---|---|
| Finita | Finite | Distancia fija. Admite **Simétrica** (mitad a cada lado del plano del perfil: la distancia es el total) y **No simétrica** (dos distancias) [doc] |
| A través de todo | Through All | Atraviesa todo el cuerpo [doc] |
| Hasta siguiente | Through Next | Hasta la siguiente intersección cerrada con la pieza; en protrusiones el resultado debe **intersecar completamente** la pieza, si no, usar Desde-hasta o Finita [doc] |
| Desde-hasta | From/To | Entre dos caras o planos [doc] |
| Hasta punto clave | To Keypoint | Hasta un punto clave de otra operación; queda asociativo [doc] |

   Si no se pulsa ni *Simétrica* ni *No simétrica*, la extrusión va en un solo sentido [doc — KB Siemens].
5. **Tratamiento** (opcional): ángulo de desmoldeo (afinado) o abombado a las caras que genera el perfil [doc].
6. **2026 — espesor de pared:** Extruir, Revolución, Barrido, Por secciones y Helicoidal pueden crear la
   operación ya hueca: espesor, sentido del adelgazamiento, tapas de extremo y retirada del material interior,
   en ordenado y síncrono [doc — blog 2026]. Útil para tubos y perfiles huecos sin un vaciado aparte.
7. Terminar.

API [doc + local]: primera operación `Models.AddFiniteExtrudedProtrusion(NumberOfProfiles, ProfileArray,
ProfilePlaneSide, ExtrusionDistance)`; `ProfilePlaneSide` ∈ `igLeft, igRight, igSymmetric`; en simétrica cada
lado recibe la mitad de la distancia [doc].

### 3.2 Cortar (vaciado extruido)

Mismo flujo y extensiones que Extruir [doc]. Notas:
- Un agujero circular simple puede hacerse con Cortar, pero **avellanados y refrentados se hacen con Agujero**
  [doc]. Criterio del curso [inferido]: **todo agujero que el plano acote como agujero (Ø, profundidad, rosca,
  avellanado) se hace con Agujero**, porque luego el plano 2D lee sus datos para las notas y la tabla de
  agujeros (capítulo 04).
- Para algo que debe atravesar, usar **A través de todo**, nunca «Finita = espesor»: si el espesor cambia, el
  corte deja de atravesar [inferido].
- Perfil abierto en un corte: los extremos se prolongan y el corte puede «rebanar» la cara superior [doc].
- API: `ExtrudedCutouts.AddFinite / AddThroughAll / AddThroughNext / AddFromTo / AddFiniteByKeyPoint` y sus
  variantes `…Multi` para varios perfiles [doc].

### 3.3 Revolución y corte por revolución

Procedimiento [doc]: *Inicio > Sólidos > Revolución* (o *Corte por revolución*) → plano → perfil (abierto o
cerrado; **cerrado si es base**) **y eje de revolución** → lado (perfiles abiertos) → extensión → terminar.
- **Eje:** una línea del perfil o de construcción marcada con *Eje de revolución* [inferido]. El perfil no debe
  cruzar el eje; puede tocarlo [inferido].
- **Extensión:** ángulo finito, *Revolucionar 360°*, simétrica [inferido; la ayuda remite a «Define the extent
  of a revolved feature»].
- **Perfil = media sección** del plano (la mitad de la vista en corte longitudinal), acotando diámetros con cota
  de diámetro simétrico respecto al eje [inferido].
- API: `Models.AddFiniteRevolvedProtrusion(…, ReferenceAxis, ProfilePlaneSide, AngleofRevolution…)` [doc nombre;
  firma API?]; cortes `RevolvedCutouts.AddFinite` [local]. Ángulo en radianes (2π = 360°) [inferido].

### 3.4 Barrido (protrusión / corte por barrido)

[Base doc: comando de añadir material «a lo largo de una trayectoria definida por el usuario»; detalle inferido]
1. *Inicio > Sólidos > Barrido*. Opciones: *Una trayectoria y una sección* o *Varias trayectorias y secciones*.
2. Seleccionar/dibujar la **trayectoria** (boceto abierto o cerrado, o aristas): continua; mejor con
   tangencia en los tramos.
3. Seleccionar/dibujar la **sección** (cerrada) en un plano **normal a la trayectoria** en su inicio (crear el
   plano con *Normal a curva*).
4. Terminar. Opciones avanzadas según versión: alineación de la sección (normal/paralela), fusión de caras,
   torsión/escala.
Errores típicos: radio de curvatura de la trayectoria menor que la mitad del tamaño de la sección
(autointersección); sección que no toca la trayectoria; trayectoria con esquinas vivas.
API: `Models.AddSweptProtrusion` [doc]; cortes en `SweptCutouts` [doc].

### 3.5 Por secciones (loft)

- Pasa material por **varias secciones transversales**: bocetos, aristas de operaciones o perfiles dibujados en
  el comando [fuente secundaria — GrabCAD].
- En protrusión/corte por secciones **cada sección debe ser cerrada**; las abiertas solo valen para superficies
  [doc].
- **Puntos de inicio:** si no se corresponden entre secciones, la operación se retuerce o falla → alinearlos
  (mismo vértice «equivalente» en cada sección) [doc].
- **Curvas guía:** los planos de todas las secciones deben cortarlas [fuente secundaria — GrabCAD].
- Opciones de extensión abierta/cerrada y control de tangencia en los extremos [inferido].
- API: `Models.AddLoftedProtrusion` [doc]; cortes `LoftedCutouts` [doc].

### 3.6 Helicoidal (protrusión / vaciado helicoidal)

- Barre una sección a lo largo de una **hélice**: mano derecha/izquierda, radio constante/variable, paso
  constante/variable, extensión definida por caras de otra operación [doc].
- Para **roscas normalizadas no se usa**: usar Agujero roscado o Rosca [doc]. Las helicoidales consumen
  mucha memoria y ralentizan las vistas del plano: solo cuando la forma exacta importa (muelles, roscas
  especiales) [doc].
- Se define con eje + sección + parámetros (eje y paso, eje y vueltas, paso y vueltas) [inferido].
- API: `Models.AddFiniteBaseHelix` (base) [doc]; `HelixProtrusions`, `HelixCutouts` [doc].

### 3.7 Agujero

Pasos ordenados [doc]: **Plano** → **Agujero** (parámetros y colocación de uno o varios círculos de agujero)
→ **Extensión** → **Terminar**.

**Tipos** (cuadro *Opciones de agujero*; uno solo por operación) [doc]:

| Tipo (ES probable) | EN | Parámetros |
|---|---|---|
| Simple | Simple | Diámetro |
| Roscado | Threaded | Rosca estándar, rosca de tubo recta o cónica; designación (M8×1,25…) |
| Cónico | Tapered | Ángulo o relación; a partir del Ø superior o inferior. **Solo extensión Finita**; no admite rosca [doc + blog ST7] |
| Refrentado (abocardado) | Counterbore | Ø y profundidad del refrentado (la profundidad del agujero va en la extensión) |
| Avellanado | Countersink | Ø del avellanado y **ángulo total incluido** (p. ej. 90°) |

- **Extensiones:** *A través de todo*, *Hasta siguiente*, *Desde-hasta*, *Finita* (simple, refrentado,
  avellanado y roscado admiten las cuatro; cónico solo Finita) [doc].
- **Fondo en V** (solo Finita): ángulo incluido (118° típico de broca [inferido]) y si la profundidad se mide
  a la parte cilíndrica o a la punta [doc].
- **Colocación:** los perfiles de agujero no se dibujan: se colocan *círculos de agujero*; se ubican con cotas
  y relaciones al resto (p. ej. a aristas o al origen); **no** se acota su tamaño [doc]. Varios círculos en
  una operación = **patrón definido por el usuario** [doc] (para «4× Ø8» en posiciones irregulares).
- **Normas:** desde ST7 el cuadro tiene vista previa, chaflanes de inicio/fin/cuello incorporados, y el
  diámetro modelado de un roscado puede ser el de broca, el menor o el nominal [doc — blog ST7]. En ST5/ST6
  las medidas salían de `Holes.txt` y `PipeThreads.txt` (archivos editables, ruta en *Opciones > Ubicación de
  archivos*) y los ajustes comunes se guardan en *Ajustes guardados* (`Custom.xml`) [doc]. Elegir norma **ISO
  métrica** y el ajuste (normal/ajustado/holgado) del pasante [inferido].
- **Visualización de rosca:** las caras roscadas usan un estilo de cara propio («Rosca»), configurable
  [doc].
- API [doc para Holes; resto API?]: `hd = doc.HoleDataCollection.Add(HoleType=…, HoleDiameter=…)`; en el
  perfil, círculos con `Profile.Holes2d.Add(x, y)`; luego `Model.Holes.AddFinite(Profile, lado, profundidad,
  hd)` o `AddThroughAll` / `AddThroughNext` / `AddFromTo`.

### 3.8 Rosca (y rosca cosmética)

- *Rosca* aplica rosca a una **cara cilíndrica existente** (eje exterior o agujero) [inferido; el comando se cita
  junto a Agujero como vía para roscas normalizadas — doc]. En Solid Edge la rosca es **cosmética**: el cilindro
  conserva su diámetro y la rosca se ve por estilo de cara y se anota en el plano [doc para el estilo; resto
  inferido].
- Rosca física (hilos modelados) = Helicoidal, solo si se pide expresamente [doc].
- Criterio [inferido]: agujero roscado → Agujero tipo Roscado; eje roscado → Revolución/Extruir al Ø nominal +
  Rosca.
- API: `Model.Threads.Add(…)` [doc nombre; firma API?].

### 3.9 Redondeo

- Tipos [doc — API]: **constante** (`Rounds.Add`), **variable** (`AddVariable`), **mezcla** entre aristas/caras
  (`AddBlend`); entre superficies de construcción (`AddSurfaceBlend`).
- Procedimiento [inferido]: *Inicio > Sólidos/Operaciones > Redondeo* → elegir aristas, cadenas, caras
  (todas sus aristas) o la operación entera → radio → vista previa → terminar. Un mismo radio = una
  operación (agrupar todas las «R3»).
- **Si falla** [inferido salvo marca]:
  1. Radio ≥ ancho de una cara vecina → bajar el radio o redondear primero la arista más corta.
  2. Orden: radios **grandes antes que pequeños**; redondeos y chaflanes **al final**; redondeos exteriores
     antes de Pared delgada para que el espesor siga el radio.
  3. Esquinas donde coinciden 3 aristas con radios distintos → hacer cada radio en una operación separada y
     probar el orden.
  4. Aristas que ya no existen tras una edición → *Editar definición* y volver a escoger (§4).
  5. Para colocar redondeos en todas las aristas, seleccionar primero todos los redondeos y luego todos los
     acuerdos del filtro de selección [doc — KB Siemens].
- API: `Model.Rounds.Add(NumberOfEdgeSets, EdgeSetArray, RadiusArray)` [local; firma API?]. Seleccionar aristas
  **por geometría** (longitud, posición, caras adyacentes), nunca por índice [regla de jarvis-operador].

### 3.10 Chaflán

- Tipos [doc — API]: *Retranqueos iguales* (`AddEqualSetback` → «1×45°»), *Ángulo y retranqueo*
  (`AddSetbackAngle` → «2×30°»), *Retranqueos distintos* (`AddUnequalSetback` → «2×3»).
- En ángulo y retranqueo, la cara de referencia define desde dónde se mide [inferido].
- Lectura del plano: «C1», «1×45°» y «1 × 45°» son el mismo chaflán de 1 mm a 45° [inferido].

### 3.11 Pared delgada, región delgada, engrosar

- **Pared delgada** (*Thin Wall*) [doc]:
  1. **Espesor común** + sentido: interior (por defecto), exterior o simétrico.
  2. **Caras abiertas** (opcional): se eliminan (quedan abiertas); se pueden elegir varias.
  3. **Espesor único** (opcional): caras con otro espesor (botón *Espesor único* + caras + valor).
  Se puede previsualizar en cuanto se define el espesor común.
- **Engrosar** (*Thicken*): da espesor a caras, cadena de caras o cuerpo entero, con distancia [doc].
- **Región delgada** (*Thin Region*): vaciado local con caras de tapa [fuente secundaria].
- **2026:** espesor de pared integrado en Extruir/Revolución/Barrido/Por secciones/Helicoidal [doc — blog].

### 3.12 Nervio, red de nervios, labio, ángulo de desmoldeo

[Existencia y API = doc; mecánica = inferido]
- **Nervio** (*Rib*): perfil **abierto** (una línea o polilínea) en un plano que corta la pieza; se definen
  espesor, lado/simetría y dirección; la opción *Extender perfil* prolonga el trazo hasta las caras. API
  `Model.Ribs`.
- **Red de nervios** (*Web Network*): varios trazos abiertos a la vez, mismo espesor; puede ser operación base
  [doc]. API `Models.AddWebNetwork`, `Model.WebNetworks` [doc].
- **Labio** (*Lip*): reborde/ranura a lo largo de aristas (encastre de dos medias carcasas); ancho y alto,
  hacia dentro o fuera. API `Model.Lips`.
- **Ángulo de desmoldeo** (*Draft*): inclina caras respecto a un plano neutro/dirección de desmoldeo; variantes
  desde plano, desde aristas, desde línea de partición, y *Dividir desmoldeo* [fuente secundaria — IMH para el
  nombre]. También como **Tratamiento** dentro de Extruir/Cortar [doc]. API `Model.Drafts`.

### 3.13 Patrones

- **Patrón rectangular / circular de operaciones** (ordenado) [inferido]: *Patrón* → seleccionar las
  operaciones → elegir plano → dibujar el patrón (rectángulo de patrón: nº en X/Y y separación; circular:
  centro, nº y ángulo total) → modo de reparto *Ajustar* (n en una longitud), *Rellenar* o *Fijo*
  (separación fija) → suprimir ocurrencias si hace falta → terminar. Opción de cálculo *Inteligente* (cada
  ocurrencia se recalcula; para cuando la pieza cambia de forma) vs *Rápido* (copia geométrica; más ligero).
- **A lo largo de curva** (*Pattern Along Curve*): operaciones + curva/arista + punto ancla + nº/separación
  [inferido]. API `Patterns.AddByCurve` [doc].
- **Patrón de relleno** (*Fill Pattern*, nuevo en 2026, ordenado): repite una forma sobre superficies (también
  pliegues y curvas 3D); se controla forma, separación y densidad y se aplica a caras, aristas, cadenas,
  operaciones o cuerpos; se edita sobre la cara y se actualiza con el modelo [doc — blog 2026]. Texturas,
  aligeramiento (agujeros de alivio de peso — relevante en aeronáutica).
- Un patrón de agujeros iguales en posiciones irregulares se puede hacer dentro del propio Agujero (varios
  círculos) [doc].
- API [doc nombres; firmas API?]: `Patterns.AddByRectangular`, `AddByCircular`, `AddByCurve`, `AddByFill`;
  en versiones anteriores `Patterns.Add` con un perfil de patrón; también `UserDefinedPatterns`.

### 3.14 Simetría

- **Copia simétrica de operación** (*Mirror Copy Feature*): operaciones + plano de simetría [inferido].
  Estrategia para piezas simétricas: modelar media pieza (o un lado de los detalles) y reflejar; o extruir
  **simétrico** desde el plano medio [inferido].
- **Copia simétrica de pieza** (*Mirror Copy Part*): refleja todo el cuerpo [inferido]. API
  `Model.MirrorCopies.Add(…)` [doc nombre; firma API?], `Model.MirrorParts` [doc].

### 3.15 Copia de pieza, sistemas de coordenadas y puntos clave

- **Copia de pieza** (*Part Copy*): inserta el cuerpo de otro `.par` como operación, vinculado; se usa también
  para el desarrollo de chapa y piezas espejo [doc ST5 lo menciona en chapa; resto inferido].
  **Copia entre piezas** (*Inter-part copy*) en contexto de conjunto: copia geometría de otra pieza del
  conjunto con vínculo [inferido]. Una extensión hasta un punto clave de **otra pieza** del conjunto crea un
  vínculo entre piezas [doc]. API `Models.AddCopiedPart` [doc].
- **Sistema de coordenadas** (*Coordinate System*): para medir, exportar o referenciar; aparece en PathFinder
  [doc para PathFinder].
- **Puntos clave** (*keypoints*): extremos, puntos medios, centros, vértices. Sirven para extensiones
  asociativas (*Hasta punto clave*) y relaciones [doc].

---

## 4. Edición y corrección de errores

### 4.1 PathFinder: símbolos de estado [doc]

| Estado | Significado | Acción |
|---|---|---|
| Suprimida | La operación está desactivada | Clic derecho > *Anular supresión* [inferido para el nombre] |
| Problema (aviso) | Algo no cuadra; el detalle sale en la barra de avisos al seleccionarla | Leer el mensaje |
| Fallida | La operación no se pudo calcular | *Asistente de errores* (§4.3) |
| Retrocedida (*rolled back*) | Está después del punto actual del historial | Clic derecho > **Ir a** (*Goto*) para avanzar |
| Flotante | La cara sobre la que se creó ya no existe | Clic derecho en el origen > *Reposicionar operación* (*Reposition Feature*) y escoger cara nueva |
| Boceto con problema | — | Seleccionar y leer la barra de avisos |

Más acciones del PathFinder [doc]: pasar el ratón resalta; Ctrl/Mayús para multiselección; **reordenar
arrastrando** (una flecha marca el destino; lo que quede inválido va al Asistente de errores); borrar
(Supr); renombrar; *Desvincular* (*Detach*: la operación sale del sólido como superficie oculta); mostrar/ocultar
planos, bocetos, superficies y sistemas de coordenadas; agrupar.
Por API: estado de cada operación con `Feature.Status` [local] (sano antes de seguir).

### 4.2 Formas de editar [inferido salvo marca]

| Acción (ES probable) | EN | Qué hace | Cuándo |
|---|---|---|---|
| Edición dinámica | Dynamic Edit | Seleccionar la operación muestra sus cotas; clic en una cota y escribir el valor | Cambiar una medida |
| Editar perfil | Edit Profile | Abre solo el perfil (geometría, cotas, relaciones) | Cambiar la forma del contorno |
| Editar definición | Edit Definition | Reabre la barra de pasos: plano, lado, extensión, tratamiento, aristas | Cambiar tipo de extensión, aristas de redondeo, caras de pared delgada |
| Ir a | Goto | Retrocede el historial hasta una operación [doc] | Insertar una operación en medio: *Ir a* la anterior, crear, *Ir a* la última |
| Suprimir / Anular supresión | Suppress / Unsuppress | Desactiva sin borrar [doc para el estado] | Aislar qué rompe el modelo |
| Reordenar | Reorder (arrastrar) | Cambia el orden [doc]; API `Feature.Reorder` [doc — ejemplo de Round.Reorder] | Redondeo antes de un corte, etc. |
| Editar boceto | Edit Sketch | Edita el boceto origen; se actualizan las operaciones que lo usan | Perfiles «desde boceto» |

### 4.3 Asistente de errores [doc]

- Comando **Errores** (*Errors*, pestaña *Herramientas*): solo está activo cuando hay errores; revisarlo durante
  ediciones largas.
- En Pieza/Chapa ordenada registra operaciones que no recalculan; en Pieza síncrona, las que fallan.
- El cuadro lista cada error con **causa y acción correctora sugerida**; al seleccionar un error resalta los
  elementos implicados (p. ej. las caras de una topología no-manifold); botones para corregir o borrar.
- **Errores típicos citados por la ayuda:** un corte que ya no quita material (p. ej. una cota de 10 → 120 que
  lo saca del sólido) y una operación que crea topología **no-manifold** (caras que se tocan en una línea o un
  punto, espesor cero).

### 4.4 Recetas de corrección [inferido salvo marca]

1. **Leer antes de tocar:** el primer error del árbol suele arrastrar a los siguientes. Corregir de arriba
   abajo; los «errores» posteriores a menudo desaparecen solos.
2. **Perfil inválido:** *Editar perfil* → *Asistente de errores de perfil* → corregir → *Validar* [doc].
3. **Corte que no quita material:** comprobar lado y sentido de la extensión; pasar a *A través de todo*.
4. **Operación flotante:** *Reposicionar operación* [doc]; a futuro, bocetar en planos de referencia.
5. **Referencia de arista perdida** (redondeo/chaflán tras editar la base): *Editar definición* → volver a
   seleccionar aristas; si se repite, mover el redondeo al final.
6. **Redondeo que falla:** ver §3.9.
7. **Hasta siguiente que falla en protrusión** (no corta completamente la pieza): cambiar a Desde-hasta o
   Finita [doc].
8. **No-manifold:** cambiar una cota para que las caras se separen o se solapen con volumen; evitar aristas
   que coinciden exactamente.
9. **Diagnóstico por supresión:** suprimir operaciones desde el final hasta que el error desaparece; la
   última suprimida es la culpable.
10. **Límite de intentos:** dos fallos seguidos del mismo paso → parar y reportar al usuario con el error COM
    exacto (regla de jarvis-operador).

### 4.5 Si se mezcla con síncrono (referencia breve)

[inferido; el curso usa ordenado] En síncrono no hay historial: se editan caras con el **volante**
(*steering wheel*, mover/rotar), **cotas PMI 3D** que se pueden bloquear y **Reglas activas** (*Live Rules*:
mantener concéntrico, coplanar, paralelo, perpendicular, simétrico, tangente…). Las operaciones ordenadas se
calculan **después** de las síncronas. Cambiar a síncrono un modelo ordenado es una decisión del usuario, no del
operario.

---

## 5. Material, propiedades físicas y propiedades del archivo

### 5.1 Material

- **Tabla de materiales** (*Material Table*, pestaña *Herramientas*) [inferido para ubicación]. Al aplicar un
  material se fijan **densidad** y propiedades mecánicas, y el estilo visual [inferido]. En chapa, la pestaña
  *Material* sirve sobre todo para peso y análisis [doc — blog].
- Materiales típicos del curso aeronáutico: aluminio 2024-T3, 6061-T6, 7075-T6; acero; titanio Ti-6Al-4V
  [inferido]. Si el plano indica material, aplicarlo **antes** de leer la masa. Si el material no está en la
  biblioteca, crearlo con la densidad del plano o de una fuente fiable y anotarlo [inferido].
- API: tabla de materiales de la aplicación (`GetMaterialTable` / `ApplyMaterial`) [API?].

### 5.2 Propiedades físicas

- *Inspeccionar > Propiedades físicas* [inferido]: densidad, precisión, botón *Actualizar*; da **masa,
  volumen, área**, **centro de masa** y de volumen, momentos y ejes principales, radios de giro [inferido].
  El modelo puede mostrar el centro de masa, el de volumen y los ejes principales (`DisplayCenterOfMass`,
  `DisplayCenterOfVolume`, `DisplayPrincipalAxes` en la API) [doc].
- Uso como **verificación**: comparar el volumen calculado a mano (§7.5) con el del modelo.
- API: `Model.ComputePhysicalPropertiesWithSpecifiedDensity(…)` devuelve volumen, área, masa, CG… (en
  pywin32 los parámetros de salida vuelven en la tupla de retorno) [API? — el método es conocido; confirmar
  firma en el capítulo 05].

### 5.3 Propiedades del archivo

- *Archivo > Propiedades > Propiedades del archivo* [inferido]: **Resumen** (Título, Asunto, Autor, Empresa,
  Palabras clave, Comentarios), **Proyecto** (Número de documento, Revisión, Nombre del proyecto),
  **Personalizado** [inferido].
- Llenarlas en la pieza: el rótulo del plano las lee automáticamente (capítulo 04). Mínimo: Título (nombre de la
  pieza), Autor (el usuario), Número de documento, Material, Revisión [inferido].
- API: `doc.Properties` → conjuntos `SummaryInformation`, `ProjectInformation`, `Custom` [API?].

---

## 6. Chapa (.psm)

### 6.1 Arranque y parámetros globales

- Una pieza de chapa **empieza desde una plantilla de chapa** [doc — blog].
- **Tabla de materiales > pestaña Calibre** (*Gage*) [doc]: *Espesor del material*, *Radio de pliegue*,
  *Profundidad de alivio*, *Anchura de alivio*, *Ecuación de pliegue* (fórmula estándar, personalizada o de
  ejemplo), **Factor neutro**; opción de tomar calibres y factores neutros de un Excel (*Usar tabla de
  calibres*). El espesor puede venir del Excel, de la lista de calibres o escribirse [doc — blog].
- **Radio mínimo:** Solid Edge impone un radio mínimo en bridas (0 → ≈0,002 mm); para radio exactamente
  cero hay que modelar en el entorno Pieza [doc].
- **Fórmula estándar (PZL, longitud de la zona plástica)** [doc — ayuda + fuente secundaria DesignFusion]:
  `PZL = π · (BR + NF · THK) · BA / 180` (BA en grados) — para 90°: `PZL = 1,57 · (BR + NF · THK)`.
  BR = radio de pliegue, NF = factor neutro (0 a 1), THK = espesor, BA = ángulo de pliegue. Es el arco de
  la fibra neutra, que no se estira. Valor de referencia **NF ≈ 0,33** [fuente secundaria — KB Siemens/blog];
  el taller dicta el valor real. Menor NF → desarrollo un poco más corto [doc — blog].
- Desde 2022 el factor neutro sobrescrito en una operación tiene prioridad sobre el del Excel [doc — KB].
  En la tabla de calibres el ángulo se busca como **suplemento** del de la operación (pliegue de 120° → fila de
  60°) [doc — KB]. Desde 2025 hay además métodos de **deducción de pliegue** y **tolerancia de pliegue** por
  tabla [fuente secundaria — DesignFusion].
- Factor neutro por pliegue: se puede sobrescribir al colocar (opciones de la brida) o después (*Opciones de
  pliegue*) [doc — KB].

### 6.2 Operaciones de chapa

Ubicación: *Inicio > Chapa* [doc ST6 para Pestaña de contorno; resto inferido]. ES = [traducción probable] salvo
indicación; «Pestaña» y «Brida» se usan de forma inconsistente en traducciones — identificar por el inglés.

| Operación (ES probable) | EN | Qué hace | Opciones clave | API |
|---|---|---|---|---|
| Pestaña | Tab | Chapa plana desde **perfil cerrado**; también añade solapas planas | Espesor (lado) | `Models.AddBaseTab`, `Model.Tabs` [doc] |
| Brida de contorno / Pestaña de contorno | Contour Flange | Desde **perfil abierto**: perfil extruido de pared delgada con pliegues automáticos en las esquinas [doc] | Extensión (finita, cadena de aristas), lado del material, radio | `Models.AddBaseContourFlange`, `ContourFlanges.Add` (con factor neutro) [doc] |
| Brida | Flange | Pliega una pared desde una arista | Longitud (interior/exterior/pliegue exterior), ángulo, ancho (completo, centrado, desde extremo…), alivios, radio propio | `Flanges.Add`, `AddFlangeByFace`, `AddByMatchFace` [doc] |
| Brida por secciones | Lofted Flange | Transición entre dos perfiles (tolvas) | — | `Models.AddLoftedFlange` [doc] |
| Dobladillo | Hem [doc nombre EN] | Remate de arista (cerrado, abierto, en lágrima…) | Tipo, radio, longitud (cuadro *Opciones de dobladillo*) [doc] | `Model.Hems` [doc] |
| Recodo / Desplazamiento | Jog | Dos pliegues opuestos (escalón en Z) | Altura, ángulo | `Model.Jogs` [doc] |
| Pliegue / Doblar | Bend | Pliega una zona plana por una línea | Línea, ángulo, radio | `Model.Bends` [doc] |
| Desplegar / Replegar | Unbend / Rebend | Despliega para cortar en plano y vuelve a plegar [fuente secundaria — IMH] | — | `Unbends`, `Rebends` [doc] |
| Cerrar esquina de 2 pliegues | Close 2-Bend Corner | Cierra/solapa esquinas | Tipo de cierre, holgura | `CloseCorners` [doc] |
| Romper esquina | Break Corner | Chaflán/redondeo de esquina en chapa | — | `BreakCorners` [doc] |
| Embutición, persiana, nervadura, vaciado embutido, cartela | Dimple, Louver, Bead, Drawn Cutout, Gusset | Deformaciones de chapa [fuente secundaria — IMH «embutición»] | — | `Dimples`, `Louvers`, `Beads`, `DrawnCutouts`, `Gussets` [doc] |
| Grabado | Etch | Marca/texto sobre chapa; en 2026 también sobre pliegues, piezas y curvas 3D, editable [doc — blog] | — | `Etches` [doc] |
| Lengüeta y ranura | Tab and Slot | **Nuevo en 2026**: crea lengüetas y ranuras emparejadas de una vez, en pieza, multicuerpo o conjunto [doc — blog] | — | [API?] |
| Corte (normal) | Cut / Normal Cutout | En chapa, los cortes deben ser **normales a la cara** para que el desarrollo sea fabricable [inferido] | — | `NormalCutouts` [doc] |

- **Alivios:** el *alivio de pliegue* va en los extremos de pliegues que no atraviesan toda la pieza;
  cuadrado o redondo [doc — blog]; profundidad y ancho por defecto en la pestaña Calibre [doc]. El *alivio de
  esquina* (pliegue / pliegue y cara / cadena) se fija en la brida [inferido].
- **Bridas en varias aristas:** en 2026 mejoró el recorte y el inglete de bridas multiarista [doc — blog].

### 6.3 Desarrollo (patrón plano)

- **Desarrollo** (*Flat Pattern*) — *Herramientas > Plano > Desarrollo* (en ST6) [doc]: crea el desarrollo en
  el mismo archivo y añade la operación *Patrón plano* al PathFinder. Si el modelo plegado cambia, queda
  **desactualizado** (símbolo en PathFinder) → clic derecho > *Actualizar* [doc].
- *Opciones del desarrollo*: tamaño de corte actual (largo × ancho, solo lectura) y **alarmas** de tamaño
  máximo; mostrar caja y cotas del tamaño de corte [doc].
- **Guardar como desarrollo** (*Save As Flat*, menú Archivo): elegir la cara que queda arriba y una arista que
  fija el eje X y el origen; salida `.par`, `.psm` o `.dxf`; **no asociativo** con el plegado [doc]. Las
  líneas de pliegue solo se generan en DXF (capas `UpCenterlines`/`DownCenterlines`) [doc]. STEP no está en
  *Guardar como desarrollo*: pasar al entorno desarrollado y usar *Guardar como traducido* [doc — KB].
- Tratamientos del desarrollo (*Opciones de Solid Edge*): esquinas, simplificar B-splines, quitar alivios del
  sistema, usar desarrollo existente o modelo plegado [doc].
- Bridas por secciones con superficies regladas no se desarrollan [doc]. Las cotas PMI pasan a impulsadas en
  el desarrollo [doc].
- API: `Models.SaveAsFlatDXF` / `SaveAsFlatDXFEx` [doc]; la operación de desarrollo por API [API?].

### 6.4 Convertir una pieza en chapa

- Una pieza `.par` de espesor uniforme puede transformarse en chapa (*Transformar en chapa* / pieza a chapa)
  eligiendo la cara base y el espesor; las aristas vivas se convierten en pliegues con el radio del calibre
  [inferido]. La API tiene las colecciones `ConvToSMs` / `ConvertPartToSMCollection` [doc nombres].
- Si la conversión falla: espesor no uniforme, caras no paralelas, esquinas sin alivio → corregir en Pieza o
  modelar desde cero en `.psm` [inferido].

### 6.5 Secuencia típica de chapa [inferido]

1. Plantilla de chapa ISO mm → *Calibre*: espesor, radio, alivios, factor neutro del plano/taller.
2. Base: *Pestaña* (pieza mayormente plana) o *Brida de contorno* (perfil en L/U/Ω constante).
3. *Bridas* en aristas, con longitud medida como diga el plano (interior/exterior).
4. Cortes normales, agujeros, dobladillos, cierres de esquina.
5. *Desarrollo* → comprobar tamaño de corte → (si se pide) DXF.
6. Verificar espesor, radios, longitudes de ala y desarrollo contra el plano.

---

## 7. Método: del plano 2D al modelo 3D

### 7.1 Leer el plano (antes de abrir Solid Edge)

Producir una **hoja de cotas** (tabla) con todo lo legible [inferido; coincide con jarvis-operador]:
1. **Rótulo/cajetín:** título, material, escala, unidades (mm), tolerancia general (±0,5), **símbolo de
   proyección**: 1.er diedro (ISO-E, europeo) o 3.er diedro (ISO-A, americano). Define qué vista está a la
   derecha/abajo de cuál. No asumirlo: mirar el símbolo de los troncos de cono.
2. **Vistas:** frontal (alzado), superior (planta), lateral (perfil), cortes (A-A: lo rayado es material
   cortado), detalles (escala ampliada), vistas auxiliares (caras inclinadas).
3. **Cotas generales** (largo × ancho × alto) → caja envolvente para verificar al final.
4. **Símbolos** [inferido; convenciones ISO 129/ASME Y14.5]:

| En el plano | Significa | Operación |
|---|---|---|
| `Ø20` | Diámetro | Cilindro (Revolución/Extruir) o agujero |
| `R5` | Radio | Arco del perfil o Redondeo (si es arista) |
| `4× Ø8` / `4 AGUJ. Ø8` | 4 agujeros iguales | Agujero con 4 círculos o Agujero + Patrón |
| `Ø8 PASANTE` / `THRU` | Atraviesa | Agujero, extensión *A través de todo* |
| `Ø8 ↧12` | Profundidad 12 | Agujero *Finita* 12 (+ ¿fondo en V?) |
| `⌴ Ø14 ↧8` | Refrentado Ø14, prof. 8 | Agujero tipo Refrentado |
| `⌵ Ø16 × 90°` | Avellanado Ø16 a 90° | Agujero tipo Avellanado |
| `M10×1,5` / `M10` | Rosca métrica (paso grueso si no se indica) | Agujero roscado / Rosca |
| `1×45°` / `C1` | Chaflán | Chaflán retranqueos iguales |
| `□20` | Sección cuadrada 20 | Extruir |
| `SR10` | Radio esférico | Revolución con arco |
| Línea de trazos | Arista oculta | Rasgo interior: buscarlo en otra vista o corte |
| Línea de trazo y punto | Eje / plano de simetría | Revolución, simétrica, Simetría |
| `(50)` | Cota auxiliar/de referencia | No impulsa; usar para verificar |

5. **Contar** cada repetición y marcar lo **ilegible o contradictorio**. Cualquier cota que falte o se
   contradiga se pregunta al usuario **antes** de modelar; no se inventa (regla de jarvis-operador).
6. Para cada rasgo, anotar su **vista característica** (donde se ve su contorno verdadero) y su cota de
   posición.

### 7.2 Elegir plano de boceto y perfil base [inferido]

- **Vista frontal del plano ↔ plano Frontal XZ**; superior ↔ Superior XY; lateral derecha ↔ Derecho YZ.
  Mantener esta correspondencia hace que las vistas del plano 2D generado salgan igual que el original.
- **Perfil base** = el contorno de la **vista más característica** (la que muestra la forma «de extrusión»).
  Ejemplos: placa con contorno irregular → contorno en planta + Extruir espesor; eje escalonado → media
  sección longitudinal + Revolución; ménsula en L → perfil en L de la vista lateral + Extruir ancho.
- **Origen:** donde el plano pone sus referencias de cota (arista inferior izquierda, centro de un agujero
  principal, eje). Pieza simétrica → origen en el plano de simetría y extrusión **simétrica**.
- **Pieza de revolución** (todas las vistas circulares en una dirección) → siempre Revolución, no cilindros
  apilados.

### 7.3 Secuencia de operaciones [inferido; base «primero la operación base» = doc]

1. **Forma base** (la operación más grande que contenga más volumen).
2. **Añadidos** grandes (salientes, bridas, nervios, cubos).
3. **Cortes** grandes (bolsillos, ranuras, recortes de contorno, cortes por revolución).
4. **Pared delgada** si la pieza es hueca (después de las formas exteriores y de los redondeos exteriores que
   deban seguir el espesor).
5. **Agujeros** (comando Agujero), luego **patrones** y **simetrías** de agujeros/rasgos.
6. **Roscas** cosméticas.
7. **Redondeos** (grandes → pequeños) y **chaflanes** al final.
8. Material, propiedades, verificación.

Regla de robustez: cada operación referencia planos de referencia o la operación base, no aristas que una
operación posterior pueda cambiar.

### 7.4 Árbol de decisión geometría → operación [inferido]

| Si en el plano ves… | Usa |
|---|---|
| Contorno constante a lo largo de una dirección | Extruir / Cortar |
| Simetría de revolución (Ø en una vista, círculos en la otra) | Revolución / Corte por revolución |
| Forma constante que sigue una curva (tubo doblado) | Barrido (o 2026: espesor de pared en el barrido) |
| Sección que cambia de forma o tamaño (cuadrado → círculo) | Por secciones |
| Hélice (muelle, rosca especial) | Helicoidal (rosca normal → Agujero/Rosca) |
| Agujero con Ø/profundidad/rosca/avellanado | Agujero |
| Repetición regular | Patrón rectangular/circular/curva |
| Mitad igual a la otra | Extruir simétrico o Simetría |
| Caja de pared uniforme | Pared delgada |
| Refuerzo triangular o lámina interior | Nervio / Red de nervios |
| Aristas «R» / «1×45°» | Redondeo / Chaflán, al final |
| Chapa con pliegues | Archivo `.psm` (§6) |

### 7.5 Verificar contra el plano

1. **PathFinder limpio:** sin símbolos de error, aviso, flotante, suprimida o retrocedida; por API, `Status`
   sano en cada operación [doc + local].
2. **Caja envolvente** = cotas generales (por API `GetRange` del cuerpo; en pywin32 leer el valor de retorno)
   [local; jarvis-operador].
3. **Cotas una por una:** *Inspeccionar > Medir distancia / Medir ángulo* [inferido para ubicación] entre
   caras/aristas, contra la hoja de cotas. Tolerancia de aceptación del **modelo**: el valor nominal exacto
   (±0,001 mm), no ±0,5: la tolerancia del plano es para la fabricación, no para el CAD.
4. **Volumen:** calcularlo a mano por descomposición (prismas − agujeros: `V = a·b·c − n·π·d²/4·h`…) y
   compararlo con *Propiedades físicas*. Diferencia > 1 % → falta o sobra un rasgo [inferido].
5. **Conteos:** número de agujeros, nervios, ocurrencias de patrón.
6. **Vistas:** orientar a Frontal/Superior/Derecha y comparar silueta con cada vista del plano; una sección
   (*vista en corte* / *sección dinámica*) para rasgos internos [inferido].
7. **Masa** con el material del plano si el plano o el profesor la dan.

### 7.6 Errores comunes de estudiantes [inferido]

1. Bocetar la vista frontal sobre el plano Superior → pieza «acostada»; el plano 2D sale con vistas giradas.
2. Confundir R con Ø (modelar R10 como Ø10).
3. Leer mal el diedro y modelar un rasgo del lado contrario.
4. Ignorar líneas ocultas o el corte → faltan rasgos interiores.
5. Hacer agujeros con Cortar + círculo → el plano no puede poner nota de agujero ni tabla de agujeros.
6. Agujero «pasante» con profundidad finita igual al espesor → deja de atravesar si cambia el espesor.
7. Extrusión simétrica mal entendida: la distancia es el **total** (mitad a cada lado) [doc].
8. Redondeos al principio → aristas perdidas, operaciones posteriores fallan.
9. Perfiles abiertos por un hueco o con líneas duplicadas.
10. Cotas distintas de las del plano (otras referencias) → verificar se vuelve imposible.
11. Cotas redundantes → sobrerrestricción.
12. Plantilla en pulgadas, o por API olvidar que las unidades son metros (50 en vez de 0,05 → pieza de 50 m).
13. No asignar material → masa con densidad por defecto.
14. Revolución con el perfil cruzando el eje o sin eje definido.
15. Seleccionar caras/aristas por índice en la API → la receta se rompe tras cualquier edición.

### 7.7 Ejemplo resumido: ménsula en L con agujeros [inferido]

Plano: L de 80 × 60 × 40, espesor 8, dos agujeros Ø9 pasantes en el ala horizontal a 15 de los bordes, un
refrentado ⌴Ø15 ↧9 en el ala vertical, R8 en el pliegue exterior, chaflanes 1×45°.
1. Perfil en L (vista lateral) en el plano **Derecho YZ**, acotado con 80, 60 y 8; Extruir **simétrico** 40.
2. Agujero simple Ø9 *A través de todo* con dos círculos en la cara superior del ala horizontal, acotados a 15
   de los bordes y relacionados *Horizontal* entre sí.
3. Agujero tipo Refrentado (Ø9, ⌴Ø15 ↧9), *A través de todo*, en el ala vertical.
4. Redondeo R8 en la arista exterior del pliegue; chaflanes 1×45° al final.
5. Verificar: caja 80×60×40; volumen a mano ≈ (80·8 + 52·8)·40 − 2·π·4,5²·8 − (refrentado) ≈ 41 280 − 1 018 −
   … mm³; contar 3 agujeros; material; propiedades del archivo.

---

## 8. Lista de verificación para dar una pieza por terminada

Marcar cada punto **con la prueba** (número, captura o salida de la API) — no vale «se ve bien».

- [ ] Hoja de cotas completa; todas las dudas resueltas con el usuario (ninguna cota inventada).
- [ ] Documento en **modo ordenado**; plantilla ISO métrica (mm).
- [ ] Orientación: vista frontal del modelo = vista frontal del plano (Frontal XZ).
- [ ] PathFinder sin errores, avisos, flotantes, suprimidas ni retrocedidas; el *Ir a* está en la última
      operación; `Status` sano por API.
- [ ] Perfiles totalmente definidos (al menos todo lo funcional), sin relaciones contradictorias.
- [ ] Cada cota del plano existe en el modelo con su **valor nominal exacto** y las mismas referencias.
- [ ] Caja envolvente = cotas generales del plano.
- [ ] Volumen del modelo vs cálculo manual: diferencia < 1 %.
- [ ] Conteo correcto de agujeros, patrones, nervios.
- [ ] Agujeros hechos con **Agujero** (tipo, norma ISO, ajuste, rosca, profundidad/pasante correctos).
- [ ] Redondeos y chaflanes con los radios/medidas del plano, al final del árbol.
- [ ] **Material** aplicado; masa leída de Propiedades físicas.
- [ ] **Propiedades del archivo**: Título, Autor, Número de documento, Material, Revisión.
- [ ] Chapa: calibre (espesor, radio, factor neutro) del plano; desarrollo actualizado y tamaño de corte
      anotado.
- [ ] Nombres de operaciones legibles en el PathFinder (opcional, ayuda al usuario).
- [ ] Guardado con nombre nuevo, sin sobrescribir; huella del archivo de entrada intacta (jarvis-operador).
- [ ] el usuario revisó en pantalla y dio el OK.

---

## 9. Fuentes

**Oficiales Siemens [doc]**
- Ayuda de Solid Edge ST5/ST6 (espejo público de la ayuda oficial), páginas consultadas:
  - Hole command (ordered): https://soliddna.com/SEHelp/ST5/EN/a_h/feat11c.htm
  - Ordered feature overview y pasos de Extrude: https://soliddna.com/SEHelp/ST6/EN/feature_modeling/feat4a.htm
  - Extrude command (ordered): https://www.soliddna.com/SEHelp/ST6/EN/create_part/xid458037.htm
  - Cut command: https://soliddna.com/SEHelp/ST6/EN/create_part/feat3c.htm
  - Construct a base feature: https://soliddna.com/SEHelp/ST6/EN/create_part/feat4h.htm
  - Define the extent of an extruded feature: https://soliddna.com/SEHelp/ST6/EN/create_part/feat18h.htm
  - Construct an extrusion or cutout: https://soliddna.com/SEHelp/ST6/EN/create_part/feat11h.htm
  - Construct a revolved protrusion or cutout: https://soliddna.com/SEHelp/ST6/EN/feature_modeling/feat13h.htm
  - Helical Cutout / Helical Protrusion: https://soliddna.com/SEHelp/ST6/EN/feature_modeling/feat7c.htm , https://soliddna.com/SEHelp/ST6/EN/feature_modeling/feat8c.htm
  - Through Next (protrusions): https://soliddna.com/SEHelp/ST5/EN/a_h/feat31h.htm
  - Geometric relationships: https://soliddna.com/SEHelp/ST5/EN/a_h/geomrel1a.htm
  - Rigid Set command: https://soliddna.com/SEHelp/ST5/EN/i_v/rigidset1c.htm
  - PathFinder in a part model: https://soliddna.com/SEHelp/ST6/EN/create_part/pthfndb2a.htm
  - Errors command / Error Assistant: https://soliddna.com/SEHelp/ST6/EN/create_part/todo1c.htm
  - Loft (secciones cerradas, puntos de inicio): https://www.soliddna.com/SEHelp/ST5/EN/i_v/loftb1a.htm
  - Thin Wall command bar / command: https://soliddna.com/SEHelp/ST6/EN/feature_modeling/feat14d.htm , https://soliddna.com/SEHelp/ST5/EN/a_h/feat23c.htm
  - Gage tab / Material Table (PZL, factor neutro): https://www.soliddna.com/SEHelp/ST5/EN/i_v/material6d.htm
  - Flat pattern / Save As Flat: https://soliddna.com/SEHelp/ST6/EN/create_sheet_metal_part/fltptn1a.htm , https://soliddna.com/SEHelp/ST6/EN/create_sheet_metal_part/savflat2h.htm
  - Contour flange: https://soliddna.com/SEHelp/ST6/EN/create_sheet_metal_part/ctrflg3h.htm
  - Hem: https://www.soliddna.com/SEHelp/ST5/EN/a_h/hem2h.htm
- Referencia oficial de la API (Solid Edge Part Type Library):
  - Models: https://support.industrysoftware.automation.siemens.com/trainings/se/107/api/SolidEdgePart~Models_members.html
  - Model (colecciones): https://support.industrysoftware.automation.siemens.com/trainings/se/107/api/SolidEdgePart~Model_members.html
  - ExtrudedCutouts: https://support.industrysoftware.automation.siemens.com/trainings/se/107/api/SolidEdgePart~ExtrudedCutouts_members.html
  - Holes, Rounds, Chamfers, Patterns, Thinwalls, Threads, MirrorCopies, Flanges: mismo dominio, páginas `SolidEdgePart~<Colección>_members.html`
  - RefPlanes: https://support.industrysoftware.automation.siemens.com/trainings/se/107/api/SolidEdgePart~RefPlanes_members.html
  - Relations2d: https://support.industrysoftware.automation.siemens.com/trainings/se/107/api/SolidEdgeFrameworkSupport~Relations2d_members.html
  - AddFiniteExtrudedProtrusion (extensiones y lado simétrico): https://docs.plm.automation.siemens.com/docs/se/108/api/SolidEdgePart~Models~AddFiniteExtrudedProtrusion.html
  - ContourFlange.NeutralFactor: https://support.industrysoftware.automation.siemens.com/trainings/se/107/api/SolidEdgePart~ContourFlange~NeutralFactor.html
  - SaveAsFlatDXF: https://support.industrysoftware.automation.siemens.com/trainings/se/107/api/SolidEdgePart~Models~SaveAsFlatDXF.html
- Blog oficial de Solid Edge:
  - Novedades 2026, pieza y chapa: https://blogs.sw.siemens.com/solidedge/new-in-designcenter-solid-edge-2026-part-and-sheet-metal/
  - Comando Agujero ST7: https://blogs.sw.siemens.com/solidedge/introducing-the-new-st7-hole-command/
  - Introducción a chapa: https://blogs.sw.siemens.com/solidedge/sheet-metal-intro/
  - Solid Edge 2026 (barras de comando rediseñadas): https://blogs.sw.siemens.com/solidedge/designcenter-solid-edge-2026/
- Base de conocimiento de soporte Siemens:
  - Extrusión en un solo sentido: https://support.sw.siemens.com/en-US/okba/PL8004183/Can-an-Extrusion-be-limited-to-one-direction-in-the-Extent-step/index.html
  - Redondeos en todas las aristas: https://support.sw.siemens.com/en-US/okba/PL8007778/How-to-place-rounds-and-fillets-on-every-edge-of-a-part/index.html
  - Factor neutro por pliegue (síncrono): https://support.sw.siemens.com/en-US/okba/PL8008909/Want-different-neutral-factors-in-same-part-in-Synchronous/index.html
  - Factor neutro sobrescrito vs tabla de calibres: https://support.sw.siemens.com/en-US/okba/PL8537400/Overwrite-the-neutral-factor-for-one-feature-if-a-gagetable-is-in-use/index.html
  - Ángulo suplementario en tabla de calibres: https://support.sw.siemens.com/en-US/okba/PL8775926/Flat-Pattern-calculation-error-using-Gagetable-file/index.html
  - Factor neutro 0,33 y desarrollo en familias: https://support.sw.siemens.com/en-US/okba/PL8523989/Family-of-Parts-published-members-have-wrong-flatten-when-defining-different-sheet-metal-gages/index.html
  - Desarrollo a STEP: https://support.sw.siemens.com/en-US/okba/PL8792615/Saving-a-Flattened-Sheetmetal-Part-as-STEP/index.html

**Secundarias [fuente secundaria]**
- DesignFusion, fórmula PZL y Machinery Handbook: https://designfusion.com/gated-content/customer-resources/solid-edge---machinery-handbook-bend-formula-and-solid-edge
- DesignFusion, deducción de pliegue en 2025: https://www.designfusion.com/gated-content/customer-resources/solid-edge-2025---bend-deduction
- IMH, temario «Solid Edge Pieza II» (nombres en español): https://www.imh.eus/es/cursos/diseno/solid-edge-pieza-ii-operaciones-avanzadas-aula-virtual
- UPV/EHU OCW, apuntes «2. Solid Edge» (interfaz V20 en español): https://ocw.ehu.eus/pluginfile.php/44409/mod_resource/content/1/2-SolidEdge.pdf
- UPM, práctica de Dibujo Industrial con Solid Edge (solo fragmento de búsqueda): https://moodle.upm.es/en-abierto/pluginfile.php/277/mod_label/intro/practica2.pdf
- GrabCAD, loft con curvas guía: https://grabcad.com/tutorials/solid-edge-tutorials-how-to-use-loft-protrusion-loft-cutout-command
- Eng-Tips FAQ (IntelliSketch, Alt): https://eng-tips.com/forums/562/faqs/1410

**Local [local]**
- `C:\Jarvis\cad_atomic_lib.py` y módulos de Jarvis: métodos COM ya usados en este equipo
  (`Models.AddFiniteExtrudedProtrusion`, `ExtrudedCutouts.AddFinite`, `RevolvedCutouts.AddFinite`,
  `Rounds.Add`, `Dimensions.AddRadius`, `ProfileSets.Add`, `Profiles.Add`, `Lines2d.AddBy2Points`,
  `Circles2d.AddByCenterRadius`, `Arcs2d.AddByCenterStartEnd`, `Arcs2d.AddByStartAlongEnd`).

**No accesible durante la investigación:** ayuda oficial de Solid Edge 2026 en docs.sw.siemens.com (se renderiza
con JavaScript) y cursos oficiales «self-paced» spse01510/15/30 (de pago o en Scribd sin texto). Lo que dependa
de ellos está marcado [inferido] o [traducción probable].
