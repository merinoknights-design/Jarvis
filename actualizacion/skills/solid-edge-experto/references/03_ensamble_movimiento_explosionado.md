# 03 · Ensambles (.asm), movimiento y explosionado en Solid Edge 2026

> Capítulo de referencia de la habilidad `solid-edge-experto`. Para ejecutar en el equipo del usuario se combina con `jarvis-operador`. La API COM en detalle vive en `05_api_automatizacion.md`; aquí solo se indica si cada función tiene acceso por API.

## Tabla de contenido

0. [Cómo leer este capítulo (etiquetas, versiones, nombres en español)](#0-cómo-leer-este-capítulo)
1. [Grados de libertad: el modelo mental](#1-grados-de-libertad-el-modelo-mental)
2. [Relaciones de ensamble, una por una (tabla maestra)](#2-relaciones-de-ensamble-tabla-maestra)
3. [Detalle y opciones de cada relación](#3-detalle-y-opciones-de-cada-relación)
4. [Flujos de colocación: FlashFit, tradicional, Pasos reducidos, Guardar ajuste, Ensamblar, Magnetic Snap (2026)](#4-flujos-de-colocación)
5. [Diagnóstico: PathFinder, conflictos, sobredefinición, subdefinición](#5-diagnóstico-pathfinder-conflictos-y-subdefinición)
6. [Gestión del ensamble (insertar, piezas estándar, subensambles, patrones, simetría, grupos, configuraciones, BOM, edición en sitio)](#6-gestión-del-ensamble)
7. [Inspección: interferencias, medir, propiedades físicas, arrastrar componente, cortes](#7-inspección)
8. [Movimiento: motores, Simular motor, animación y video](#8-movimiento-motores-simular-motor-y-video)
9. [Caso cardán: hacerlo girar con un motor](#9-caso-cardán-hacerlo-girar-con-un-motor)
10. [Explosionado en el entorno Explosionar-Renderizar-Animar (ERA)](#10-explosionado-en-el-entorno-era)
11. [Animación del explosionado, render y exportación](#11-animación-del-explosionado-render-y-exportación)
12. [De la configuración explosionada al plano (vista, globos, lista de piezas)](#12-de-la-configuración-explosionada-al-plano)
13. [Método y buenas prácticas para el ensamble general de entrega](#13-método-y-buenas-prácticas)
14. [Checklist de entrega (ensamble + explosionado + animación)](#14-checklist-de-entrega)
15. [Lo que no se pudo verificar](#15-lo-que-no-se-pudo-verificar)
16. [Fuentes](#16-fuentes)

---

## 0. Cómo leer este capítulo

**Etiquetas de procedencia**
- `[doc]` = documentación oficial de Siemens: ayuda de Solid Edge (espejo de la ayuda ST5/ST6 en soliddna.com), manuales oficiales de autoformación de Siemens (en español: spse01540 *Modelado de conjuntos* y spse01541 *Explosionado-Renderizado-Animación*, edición 2010/ST3; en inglés: spse01691 *Exploding assemblies* y spse01693 *Animating assemblies*, ST4), referencia de la API (*Solid Edge Assembly Type Library*, v106/v107) y artículos de la base de conocimiento de Siemens.
- `[fuente secundaria]` = blogs (incluido el blog oficial de Solid Edge en blogs.sw.siemens.com), revendedores, foros y prensa técnica.
- `[inferido]` = deducción del investigador a partir de la geometría o de varias fuentes. **Antes de afirmarlo ante el usuario, compruébalo en pantalla.**
- `[API?]` = no está confirmado si existe acceso COM; lo cubre en detalle `05_api_automatizacion.md`.

**Advertencia de versión.** No se encontró la ayuda en línea de la versión 2026 (docs.sw.siemens.com no devolvió contenido legible). Casi todo lo marcado `[doc]` viene de ayudas y manuales de ST3 a ST7 (2010-2014). Los conceptos de ensamble, motor y ERA no han cambiado de fondo desde entonces, pero **los nombres de la cinta (ribbon) y la posición de los botones pueden variar en 2026**. Lo confirmado como novedad 2026 se marca **(2026)**.

**Nombres en español: la trampa principal.** En la interfaz de Solid Edge en español, el ensamble se llama **Conjunto** (entorno Conjunto, *PathFinder de Conjunto*, "subconjunto"), el plano se llama **Plano** y la pieza, **Pieza** `[doc]` (manuales spse01540/41). El usuario dice "ensamble"; en pantalla busca "Conjunto". Los nombres de comandos de este capítulo salen de los manuales oficiales en español cuando existen; si no, se da el inglés y se marca `[traducción probable]`. La relación Ground aparece en los manuales como **anclaje / Anclar**; en la interfaz del usuario puede aparecer como **Fijar** `[traducción probable]`. Mate aparece como **Coincidir / relación de coincidencia** `[doc]`.

---

## 1. Grados de libertad: el modelo mental

- Un componente libre tiene **6 GDL**: 3 traslaciones (X, Y, Z) y 3 rotaciones. Cada relación quita algunos. Una pieza "colocada de manera definitiva" (*fully positioned*) no puede moverse respecto al conjunto; "la primera relación controla algunos movimientos… al aplicar más relaciones se controla un mayor número" `[doc]`.
- **Ensamble estático** (soporte, carcasa, tornillería): cada pieza totalmente posicionada.
- **Mecanismo** (cardán, biela-manivela, engranajes): **subdefinido a propósito**. Solo debe quedar libre el GDL que el mecanismo necesita (p. ej., el giro del eje de entrada). Un motor solo se puede asignar a una pieza **infrarrestringida** (subdefinida) o con relaciones suprimidas, y el conjunto debe quedar subdefinido "de modo que el mecanismo tenga libertad de movimiento en los ejes adecuados" `[doc]`.
- Solid Edge **no muestra un contador numérico de GDL** por pieza (al menos no se encontró en la ayuda revisada). El estado se lee con los **símbolos del PathFinder** (§5) y se prueba con **Arrastrar componente** (§7.4) `[inferido]`.
- Regla práctica para quitar GDL sin sobredefinir: plano-plano quita 3; eje-eje quita 4 (5 con giro bloqueado); se completa con lo que falte. Insertar (coincidencia + eje con giro bloqueado) = 6 de una vez `[inferido]` (a partir de la definición de Insertar `[doc]`).

---

## 2. Relaciones de ensamble: tabla maestra

Ubicación general: **Inicio → grupo Ensamblar → comando Ensamblar / Poner pieza**, lista **Tipos de relaciones** de la barra de comandos `[doc]`; en versiones recientes también hay botones de relación sueltos en el grupo Ensamblar/Relacionar `[inferido]`. En el **PathFinder de Conjunto**, panel inferior, se ven, editan, suprimen y borran `[doc]`.

GDL que quita: valores para el caso típico (cara plana-cara plana, cilindro-cilindro), `[inferido]` salvo indicación. "R" = rotación, "T" = traslación.

| Relación (ES, manual Siemens) | EN | Qué hace | GDL que quita | Cuándo usarla | API COM |
|---|---|---|---|---|---|
| **Anclar / Fijar** (relación de anclaje) | Ground | Fija la pieza en posición y orientación respecto al conjunto `[doc]` | 6 | Solo la primera pieza (base/bastidor). Se aplica **automáticamente a la primera pieza** del conjunto `[doc]` | `Relations3d.AddGround` `[doc]` |
| **Coincidir** (relación de coincidencia) | Mate | Cara de una pieza coplanar y **enfrentada** a la de otra (normales opuestas); desplazamiento fijo, flotante o de rango `[doc]` | 3 (1T + 2R); con desplazamiento flotante, 2R hasta que otra relación fije la distancia | Apoyos cara contra cara: tapa sobre carcasa, cabeza de perno sobre arandela | `AddPlanar` con normales opuestas `[doc]` (parámetro de orientación `[API?]`) |
| **Alinear plano** (alineamiento/alineación plana) | Planar align | Caras coplanares con normales **en el mismo sentido** `[doc]` | 3 (1T + 2R) | Enrasar caras; fijar la orientación angular con desplazamiento flotante `[doc]` | `AddPlanar` con `NormalsAligned` `[doc]` |
| **Alinear eje** (alineación axial) | Axial align | Ejes colineales: 2 cilindros, cilindro y elemento lineal, o 2 elementos lineales `[doc]` | 4 (2T + 2R); **con Bloquear rotación, 5** `[doc]` (bloquea el giro "en una posición al azar") | Ejes en agujeros, pasadores, pernos. **En mecanismos: Desbloquear rotación** | `AddAxial`; propiedad `FixedRotate` = bloquear giro `[doc]` |
| **Insertar** | Insert | Aplica **Coincidir con desplazamiento fijo + Alinear eje con rotación fija** en un paso `[doc]` | 6 (5 si se desbloquea la rotación) | Tornillos, tuercas, arandelas, bujes (piezas axisimétricas) `[doc]` | No hay `AddInsert`: `AddPlanar` + `AddAxial` con `FixedRotate=True` `[inferido]` `[API?]` |
| **Conectar** (relación de conexión) | Connect | Lleva un **punto significativo** de una pieza a un punto, línea o cara de otra `[doc]` | punto-punto 3T · punto-línea 2T · punto-plano 1T | Cuando no hay caras planas útiles (piezas con desmoldeo), centros de esferas, conos avellanados, centros de crucetas `[doc]` | `AddPoint` / `AddPointWithInferredGeometry` `[doc]` (equivalencia con Conectar `[inferido]`) |
| **Ángulo** (relación angular) | Angle | Ángulo entre dos caras o dos bordes; **requiere una alineación axial previa** entre las piezas `[doc]` | 1R | Fijar la posición angular de una pieza que gira sobre un eje; posar un mecanismo en un ángulo dado | `AddAngular` `[doc]` |
| **Tangente** (relación tangencial) | Tangent | Cilindro, cono o toro de una pieza tangente a cilindro, cono, toro o plano de otra; con o sin desplazamiento `[doc]` | 1T (típico) | Rodillos sobre superficies, levas simples, ruedas | `AddTangent` `[doc]` |
| **Leva** | Cam | Bucle cerrado de caras **tangentes** (leva) con un seguidor (plano, cilindro, esfera o punto); variante leva de tambor `[doc]` | 1 (mantiene contacto) | Mecanismos leva-seguidor, para animar | `AddPlanarCam`, `AddBarrelCam` `[doc]` |
| **Engranaje** | Gear | **No posiciona**: acopla el movimiento de dos piezas con una relación de transmisión. Tipos Rotación-Rotación, Rotación-Lineal, Lineal-Lineal `[doc]` | 1 GDL relativo (acopla, no ubica) | Engranajes, poleas, piñón-cremallera | `AddGear` (tipo RotaryRotary/RotaryLinear/LinearLinear, dientes o vueltas, valores 1 y 2, invertir) `[doc]` |
| **Paralela** | Parallel | Ejes o elementos lineales paralelos, con desplazamiento fijo o flotante `[doc]` | 2R (+1T con desplazamiento fijo) | Mantener una distancia radial conocida en diseño descendente `[doc]` | `AddAxialWithParallelOffset` y propiedades `ParallelOffset`/`FixedParallelOffset` `[doc]` (que sea "Paralela" `[API?]`) |
| **Plano central / Centrar** | Center-plane | Centra un punto medio entre dos caras, planos o puntos; opción **Simple** o **Doble**; de 2 a 4 componentes; las caras no tienen que ser paralelas `[doc]` | 1T (simple) | Centrar una pieza entre las orejas de una horquilla (la cruceta del cardán) | `AddCenterPlane` `[doc]` |
| **Conjunto rígido** | Rigid set | Une 2 o más componentes de forma rígida entre sí, sin posicionarlos respecto al resto `[doc]` | 6 relativos entre miembros | Soldar virtualmente una horquilla a su eje, o un perno a su tuerca, para que se muevan juntos | `AddRigidSet` `[doc]` |
| **Trayectoria** | Path | Un seguidor recorre una cadena de curvas abierta o cerrada, plana o 3D, sin autointersecciones; sirve para limitar el rango de movimiento `[doc]` | 2T (sigue la curva) | Pasador en ranura, carros sobre guías curvas | `AddPath` `[doc]` |
| **Coincidir sistemas de coordenadas** | Match coordinate systems | Aplica alineaciones planas sobre los tres ejes de dos sistemas de coordenadas `[doc]` | 6 | Piezas repetidas en la misma posición relativa | `[API?]` |

---

## 3. Detalle y opciones de cada relación

### 3.1 Desplazamientos (Coincidir, Alinear plano, Paralela, Tangente, Conectar)
- **Fijo**: crea una **cota directriz** editable; con un valor distinto de 0, Alinear plano deja de ser coplanar `[doc]`.
- **Flotante**: la distancia la controla otra relación; crea una **cota dirigida** no editable. Uso típico: tras Alinear eje con **Desbloquear rotación**, una Alinear plano flotante controla la orientación angular. Si intentas ponerla fija y choca con otra relación, aparece un mensaje de conflicto `[doc]`.
- **Rango**: "no está pensado para tolerancias geométricas y puede sobrerrestringir la pieza" `[doc]`. Para limitar un recorrido, la ayuda prefiere la relación Trayectoria por ser más eficiente `[doc]`.
- Se admiten cotas **cero y negativas** `[doc]`.
- Crean cotas: coincidencia, alineación plana, conexión, ángulo, tangente y paralela. **No** crean cotas: alineación axial, anclaje y leva `[doc]`.
- Ver las cotas: opción *Mostrar todas las cotas* (cuadro Opciones de la barra de comandos) o seleccionar la relación en el panel inferior del PathFinder, que la muestra seleccionada y editable `[doc]`.

### 3.2 Coincidir (Mate)
- Si una coincidencia entra en conflicto con otras relaciones, Solid Edge **intenta aplicar Alinear plano en su lugar** `[doc]`. Vigila que no te cambie el tipo sin darte cuenta.
- Problema conocido: una **primera** coincidencia con distancia 0 al insertar una pieza nueva puede dar conflicto. Solución de Siemens: aplicar antes las alineaciones, o usar distancia entre caras y poner 0 después `[doc]` (KB PL8571490).
- **Invertir** (*Flip*) o la tecla **Tab** eligen la solución alternativa (normal contraria) `[doc]`.

### 3.3 Alinear eje (Axial align)
- **Bloquear rotación**: fija el giro en una posición al azar y "se necesita una relación menos". Útil en tornillería `[doc]`.
- **Desbloquear rotación**: deja libre el giro para controlarlo con Ángulo o con Alinear plano flotante, o para dejarlo libre en un mecanismo `[doc]`.
- Flujo tradicional: no admite borde circular. **FlashFit sí** permite bordes circulares en ambas piezas `[doc]`.
- El **Asistente de relaciones de conjunto** crea las alineaciones axiales siempre **desbloqueadas**: bloquéalas a mano donde convenga `[doc]`.
- En la API la propiedad es `FixedRotate`; también existen `Orientation`, `Flip()`, `Offset`, `Suppress`, `Status` y `DetailedStatus` en `AxialRelation3d` `[doc]`.

### 3.4 Insertar (Insert)
- Crea dos relaciones: coincidencia con desplazamiento fijo (tecleable) y alineación axial con rotación fija; el eje empieza **bloqueado** y se puede cambiar a Desbloquear `[doc]`.
- Guardar ajuste sobre una pieza puesta con Insertar captura una coincidencia y una alineación axial `[doc]`.

### 3.5 Conectar (Connect)
- Puntos significativos reconocibles: extremos de líneas, arcos y elipses; punto medio de línea; centros de arco, círculo, elipse, esfera y cono. Líneas: aristas lineales, ejes de referencia, ejes de conos, toros y esferas. Superficies: caras planas, planos de referencia, caras de toro, cono y esfera `[doc]`.
- Combinaciones: punto-punto, punto-línea, punto-cara, línea-punto, cara-punto `[doc]`.
- Cono a cono: conecta la intersección teórica de los conos (perno avellanado), con desplazamiento opcional `[doc]`.

### 3.6 Ángulo (Angle)
- Entre dos caras o dos bordes, con **alineación axial previa**; editar el valor hace girar la pieza `[doc]`. Guardar ajuste **no** captura ángulos `[doc]`.
- Para un mecanismo, un Ángulo **lo bloquea**. Si sirve para posar una posición de plano, **suprímelo** antes de simular `[inferido]`.

### 3.7 Leva y Trayectoria
- Leva: las caras del bucle deben ser tangentes; si una edición rompe la tangencia, la relación falla. Un seguidor plano se trata como infinito. En leva de tambor la curva puede ser abierta o cerrada, 3D, de arcos y B-splines, con continuidad tangente. Hace falta alineación axial y coincidencia para sostener la pieza de la leva durante la simulación del motor; las interferencias se ignoran `[doc]`.
- Trayectoria: cadena de aristas de pieza o bocetos del conjunto; si no es tangente-continua, se añaden pequeños redondeos en las esquinas. Una ranura solo vale como trayectoria si se hizo con el comando Ranura `[doc]`.

### 3.8 Engranaje (Gear)
- No posiciona: primero se colocan las piezas con coincidencia y alineaciones `[doc]`.
- Rotación-Rotación: caras cilíndricas o cónicas, bordes circulares o ejes cilíndricos. *Valor 1 / Valor 2* = relación de transmisión, en **Dientes** o **Vueltas** (esta opción solo existe en Rotación-Rotación). **Invertir** cambia el sentido relativo `[doc]`.
- Si un engranaje gira sin arrastrar su eje: pon la alineación axial engranaje-eje en **rotación bloqueada** `[fuente secundaria]`.

### 3.9 Conjunto rígido (Rigid set)
- Aparece en el panel inferior bajo cada miembro; al seleccionarlo se resaltan todos. Borrarlo lo quita de todos. Un componente puede estar en varios conjuntos rígidos. Al crearlo, las relaciones ya existentes entre miembros se pueden **Suprimir**, **Eliminar** o **Ignorar** (quedan en aviso y Arrastrar componente las ignora) `[doc]`.

### 3.10 Plano central (Center-plane)
- **Simple**: el punto medio de la pieza a colocar es un punto, cara o plano. **Doble**: el punto medio se define por la distancia entre dos planos, caras o puntos. El destino queda centrado entre lo seleccionado. De 2 a 4 componentes `[doc]`.

---

## 4. Flujos de colocación

### 4.1 Insertar componentes
1. Pestaña **Biblioteca de piezas** (panel lateral) → navegar a la carpeta → **arrastrar y soltar** la pieza o el subconjunto en la ventana `[doc]`.
2. **La primera pieza de un conjunto nuevo se ancla automáticamente** `[doc]`. Debe ser la base (en el cardán, el soporte fijo).
3. Con **Mantener relaciones** activo (menú contextual de Biblioteca de piezas), las relaciones que apliques se conservan. Si está desactivado, Solid Edge las sustituye por un **anclaje** y la pieza no seguirá a las demás `[doc]` (KB PL8566091: revisar *Maintain relationships when placing component* en Opciones → Conjunto).
4. Para repetir una pieza: copiar/pegar, o arrastrar desde el PathFinder `[doc]`.
5. **Propiedades de ocurrencia**: nombre, cantidad, si se ve en conjuntos superiores, si sale en el plano, si cuenta en la lista de materiales, en las propiedades de masa y en el análisis de interferencias `[doc]`.
6. Subconjunto: igual que una pieza; con FlashFit o Pasos reducidos, sus piezas deben estar **activas** (botón **Activar pieza**) `[doc]`.

API: `Occurrences.AddByFilename` (colocación) `[API?: firma exacta en 05]`.

### 4.2 FlashFit (método por defecto)
1. Seleccionar una cara o borde de la **pieza a colocar** (se ve translúcida) `[doc]`.
2. Seleccionar la cara o borde de la **pieza destino**: la lógica de inferencia elige Coincidir, Alinear plano o Alinear eje según el tipo de elemento y la solución más cercana `[doc]`.
3. **Invertir** o **Tab** = solución alternativa `[doc]`.
4. Mover arrastrando; **Ctrl + arrastrar** gira, limitado a los GDL que queden `[doc]`.
5. FlashFit mueve la primera pieza seleccionada; si está totalmente restringida, mueve la segunda `[doc]`.
- FlashFit **no reconoce** Ángulo, Leva, Paralela ni Tangente: para esas, usa el flujo tradicional `[doc]`.

### 4.3 Flujo tradicional y Pasos reducidos
- **Tradicional**: elige el tipo en **Tipos de relaciones** y sigue la barra de comandos paso a paso `[doc]`.
- **Pasos reducidos** (Opciones de la barra de comandos): quita los pasos de seleccionar pieza y aceptar, de 5 a 3 pasos en una coincidencia típica. Hay que fijar el tipo y el valor de desplazamiento **antes** de elegir la cara destino. En conjuntos grandes usa QuickPick `[doc]`.

### 4.4 Guardar ajuste (Capture Fit)
- **Inicio → grupo Relacionar → Guardar ajuste** → en el cuadro *Capturar ajuste*, Agregar/Quitar las relaciones a capturar → Aceptar `[doc]`.
- La próxima vez que coloques esa pieza, solo eliges las caras destino. Opción automática: *Guardar ajuste automáticamente al poner piezas*. **No captura ángulos** `[doc]`.
- Ideal para los 40 pernos y 40 tuercas del cardán `[inferido]`. Constante de comando `AssemblyAssemblyRelationshipsCaptureFit` `[doc]` (v106; valor numérico a verificar en 2026).

### 4.5 Comando Ensamblar (Assemble)
- Coloca varias piezas ya soltadas y sin posicionar, relacionándolas entre sí sin seguir un orden estricto. Muy útil para **mecanismos** `[doc]`.
- Flujo: soltar el grupo de piezas → **Ensamblar** (FlashFit por defecto) → relacionar la pieza A con destinos → **clic derecho** para pasar a otra pieza `[doc]`.

### 4.6 Asistente de relaciones de conjunto (Assembly Relationship Assistant)
- Crea relaciones a partir de la posición geométrica actual, útil para conjuntos importados `[doc]`.
- Entradas: conjunto de selección, si borra las relaciones existentes, si usa los planos base. Salidas: Coincidir, Alinear plano, Alinear eje, Conectar, con o sin desplazamientos → **Procesar** → revisar la lista → **Aceptar** `[doc]`.
- Pautas: anclar una pieza e incluirla en el conjunto 1; probar sin desplazamientos; trabajar con grupos pequeños; bloquear después las alineaciones axiales que lo necesiten `[doc]`.

### 4.7 Magnetic Snap Assembly (2026)
- Comando nuevo de Designcenter Solid Edge 2026: usa IA para **encajar y restringir** componentes a caras o bordes, aplicando **varias relaciones a la vez**. Reconoce cinco geometrías: plana, cilíndrica, arista recta, arista circular y sistemas de coordenadas `[fuente secundaria]` (blog oficial de Siemens).
- No se publicó qué relaciones concretas crea ni dónde está en la cinta: **revisa el PathFinder después de usarlo** para ver qué relaciones dejó y si bloqueó giros que el mecanismo necesita `[inferido]`. Nombre en español: no verificado.

---

## 5. Diagnóstico: PathFinder, conflictos y subdefinición

### 5.1 Panel superior del PathFinder de Conjunto (símbolos de estado) `[doc]`
Leyenda oficial (manual en español): Pieza activa · Pieza inactiva · Pieza oculta · Pieza descargada · **Pieza sin colocar de manera definitiva** (subdefinida) · **Pieza con relaciones en conflicto** · Pieza vinculada · Pieza simplificada · **Falta componente** · Pieza de componente alterno · Posición controlada por relación 2D en boceto de conjunto · **Pieza ajustable** · **Conjunto ajustable** · **Sistema de sujeción** · Grupo de patrón · Elemento de patrón · Planos de referencia · Boceto · Grupo de piezas y subconjuntos · **Motor** · estados de documento (Disponible, En uso, En revisión, Emitido, Congelado, Obsoleto).
- Los símbolos pueden **combinarse** (p. ej., oculta y no colocada definitivamente) `[doc]`.
- **No hay símbolo de "totalmente posicionada"**: una pieza sin marca de subdefinición ni de conflicto está bien `[doc]` / `[inferido]`.
- El orden del panel es el **orden de colocación**. Borrar una relación puede poner otras piezas en "sin colocar definitivamente" si dependían de ella `[doc]`.

### 5.2 Panel inferior (relaciones de la pieza seleccionada) `[doc]`
Símbolos: anclaje, coincidencia, alineamiento plano, alineamiento axial, conexión, ángulo, tangente, engranaje, **relación suprimida**, **relación fallida**.
- Al seleccionar una relación: se resaltan los elementos usados; se edita el desplazamiento fijo; se cambia el tipo de desplazamiento; se suprime, se reactiva o se elimina; con **Editar definición** + **Tipos de relaciones** se sustituye por otra `[doc]`.
- Las relaciones **en conflicto se muestran en rojo** al seleccionar la pieza conflictiva `[doc]`.
- Una línea discontinua separa las relaciones con piezas situadas por encima de la seleccionada de las relaciones con piezas por debajo `[doc]`.

### 5.3 Procedimiento de diagnóstico
1. **Pieza con conflicto (rojo)**: añadir relaciones **no arregla** un conflicto previo. Suprime **todas** las relaciones de esa pieza y recréalas, sobre todo si es un conflicto de cara invertida en Coincidir o Alinear plano. Al terminar, borra las suprimidas `[fuente secundaria]` (blog de buenas prácticas de Siemens).
2. **Relación fallida**: suele venir de una cara u operación que cambió o se suprimió en la pieza. Evita relacionar con operaciones que puedan desaparecer `[fuente secundaria]`; repara la geometría importada (comando Optimizar) antes de insertar `[fuente secundaria]`.
3. **Sobredefinición**: síntomas: conflicto, mensaje al poner un desplazamiento fijo, o un mecanismo que no se mueve. Causas típicas: dos relaciones que quitan el mismo GDL (p. ej., Alinear eje **bloqueado** + Ángulo, o Insertar + otra coincidencia en el mismo eje), desplazamientos de **rango**, piezas relacionadas con **dos piezas ancladas** distintas `[doc]` / `[inferido]`.
4. **Subdefinición no deseada**: la pieza "flota". Arrastrar componente muestra hacia dónde se mueve; completa con la relación que quita ese GDL `[inferido]`.
5. **Relaciones convertidas en anclaje** al insertar: opción Mantener relaciones desactivada (§4.1) `[doc]`.
6. **Mover la base anclada**: usa **Arrastrar componente**, no Mover componentes; así las demás piezas la siguen `[doc]` (KB PL8014376).
7. **Relationship Browser / Assembly Relationship Manager**: utilidad que acompaña a Solid Edge desde ST5 para listar, resaltar, seleccionar, suprimir o borrar relaciones; solo trabaja en el nivel abierto, sin entrar en subconjuntos `[fuente secundaria]` (blog de Siemens, 2015). Su presencia en 2026 no se verificó.
8. **API**: cada `Relation3d` expone `Status` (constante `Relation3dStatusConstants`) y `DetailedStatus` `[doc]`. Recorrerlas tras construir por código es la forma de que Jarvis detecte relaciones fallidas sin mirar la pantalla `[inferido]`.

---

## 6. Gestión del ensamble

| Función | ES (UI) | EN | Dónde | Qué hace | API |
|---|---|---|---|---|---|
| Biblioteca de piezas | Biblioteca de piezas | Parts Library | Pestaña del panel lateral | Navegar, buscar y arrastrar piezas `[doc]` | `Occurrences.AddByFilename` `[API?]` |
| Piezas estándar | Piezas estándar `[traducción probable]` | Standard Parts | Pestaña/aplicación Standard Parts (requiere base de datos configurada) | Tornillos, tuercas y arandelas normalizados (ISO, DIN…) `[inferido]` | `[API?]` |
| Sistema de sujeción | Sistema de sujeción `[doc: símbolo PathFinder]` | Fastener System | Inicio → Ensamblar (posición `[inferido]`) | Coloca perno + arandelas + tuerca en agujeros a la vez `[inferido]` | `[API?]` |
| Subconjunto: transferir | Transferir `[traducción probable]` | Transfer | Inicio → Modificar | Pasa piezas a un subconjunto nuevo o existente, o a otro nivel `[doc]` | `[API?]` |
| Subconjunto: dispersar | Dispersar `[traducción probable]` | Disperse | Inicio → Modificar | Sube las piezas un nivel y elimina el subconjunto `[doc]` | `[API?]` |
| Conjunto ajustable | Conjunto ajustable | Adjustable Assembly | Menú contextual del PathFinder | El subconjunto se resuelve en el nivel superior y sus piezas pueden moverse (necesario para motores) `[doc]` | `[API?]` |
| Reemplazar pieza | Reemplazar pieza `[traducción probable]` | Replace Part | Inicio → Modificar | Sustituye una ocurrencia conservando las relaciones posibles `[inferido]` | constante `AssemblyAssemblyRelationshipsReplacePart` `[doc]` |
| Patrón de conjunto | Patrón | Pattern (Assembly) | Inicio → Patrón | Repite piezas siguiendo un **patrón de operación de una pieza** (p. ej., el patrón de agujeros de la horquilla), o un patrón de boceto o a lo largo de curva `[doc]` | `AssemblyPatterns.Create`, `AssemblyPattern.Edit`/`EditAlongCurve`/`EditDuplicate` `[doc]` |
| Duplicar componentes | Duplicar componentes `[traducción probable]` | Duplicate Components | Inicio → Patrón (desde ST7) | Copia un grupo armado a otras ubicaciones que un patrón no cubre `[fuente secundaria]` | `EditDuplicate` `[doc]` |
| Simetría de componentes | Componentes simétricos `[traducción probable]` | Mirror Components | Inicio → Patrón | Refleja piezas o subconjuntos sobre un plano del conjunto, de forma asociativa. Acción por pieza: **Rotar** (reutiliza el archivo) o **Simetría** (crea `*_mir.par`). Los subconjuntos se eligen en el PathFinder `[doc]` / `[doc KB]` | `[API?]` |
| Mover componentes | Mover componentes | Move Components | Inicio → Modificar | Mueve o copia (opción Copiar → crea un grupo en el PathFinder) `[doc]` | `[API?]` |
| Agrupar | Agrupar / Desagrupar | Group / Ungroup | Menú contextual del PathFinder | Reúne piezas en una entrada lógica; *Seleccionar componentes* habilita acciones de grupo `[doc]` | `AssemblyGroups` `[doc]` |
| Mostrar/ocultar | casillas, Mostrar sólo, Mostrar todo | Show only / Show all | PathFinder | Visibilidad; el color del texto indica oculto `[doc]` | `Occurrence.Visible` `[API?]` |
| Configuraciones de visualización | Configuraciones de visualización | Display Configurations | Inicio → Configuraciones | Guarda visibilidad, activación y simplificación; y en ERA, el explosionado (§10) `[doc]` | constante `AssemblyAssemblyToolsDisplayConfigurations` `[doc]`; colección `Configurations` `[API?]` |
| Configuraciones de pieza (2026) | — | Part Display Configurations | — | Variantes de visualización de una pieza en un solo documento `[fuente secundaria]` | `[API?]` |
| Zonas | Zonas `[traducción probable]` | Zones | Herramientas | Selección por volumen en conjuntos grandes `[inferido]` | `[API?]` |
| Editar en sitio | Editar (activar en posición) → Cerrar y volver | Edit in place | Menú contextual del PathFinder | Modificar una pieza viendo el conjunto; *Abrir* la abre sola `[doc]` | `[API?]` |
| Copia entre piezas | Copia entre piezas `[traducción probable]` | Inter-Part Copy | Pieza activa en sitio | Geometría asociativa de otra pieza `[inferido]` | `[API?]` |
| Empaquetar duplicados (2025) | — | Pack All | PathFinder | Agrupa ocurrencias repetidas para un árbol más limpio `[fuente secundaria]` | `[API?]` |
| Ir a pieza | Ir a pieza | Scroll To | Menú contextual | Desplaza el PathFinder hasta la pieza seleccionada en pantalla `[doc]` | — |
| Lista de materiales | Informe / Lista de piezas | Reports / Parts List | Conjunto: Herramientas → Informes `[inferido]`; Plano: Lista de piezas | Estructura y cantidades. Lo controla la propiedad de ocurrencia "en informes/lista de plano" `[doc]` | `[API?]` |

**Procedimientos clave**
- *Transferir a un subconjunto nuevo* `[doc]`: 1) seleccionar las piezas en el PathFinder (Ctrl+clic); 2) Inicio → Modificar → **Transferir**; 3) en *Transferir a nivel de conjunto*, elegir el destino → **Nuevo subconjunto**; 4) plantilla, nombre, ubicación → Aceptar. Requiere permiso de escritura en todos los archivos; las relaciones se reconstruyen **solo si la pieza de referencia queda por debajo** del nuevo nivel (si no, se convierten en anclajes) `[doc]`.
- *Dispersar* `[doc]`: seleccionar el subconjunto → **Dispersar** → confirmar. Solo afecta al nivel superior; los subconjuntos anidados suben intactos.
- *Patrón de pernos en el cardán* `[doc]` + `[inferido]`: colocar **1 perno** con Insertar en un agujero que pertenezca a un patrón de agujeros de la horquilla → **Patrón** → elegir el perno → elegir el patrón de operación de la pieza → se crean los demás y siguen al patrón si cambia. Si se **descarta (drop)** un patrón, sus piezas quedan **ancladas** `[doc]`.

---

## 7. Inspección

### 7.1 Verificar interferencia (Check Interference) `[doc]`
Ubicación: **Inspeccionar → Verificar interferencia** `[traducción probable]` (EN: Inspect → Check Interference).
1. Definir el **conjunto 1** (y el 2 si aplica); un subconjunto entero se elige en el PathFinder, o con una consulta en *Herramientas de selección*.
2. Comparación: conjunto 1 contra conjunto 2 (predeterminado), contra todas las demás piezas, contra las piezas visibles, o contra sí mismo.
3. Pestaña **Opciones**: *Ignorar elementos de sujeción roscados que interfieren con agujeros sin rosca*; *Ignorar interferencias del mismo diámetro nominal*; *Ignorar interferencias entre roscas coincidentes* (compara diámetro nominal y tipo de rosca).
4. Salidas: informe a archivo de texto, **mostrar volúmenes de interferencia**, **guardar volúmenes como pieza**, resaltar las piezas que interfieren, atenuar u ocultar las que no.
5. Si no hay interferencias, sale un mensaje que lo dice.
- Para el cardán: conjunto 1 = todo contra sí mismo, con las opciones de rosca activas para que pernos M y tuercas M no den falsos positivos `[inferido]`.
- API: `AssemblyDocument.CheckInterference` `[doc]`; constante `AssemblyAssemblyToolsCheckInterference` `[doc]`.

### 7.2 Medir
- Inspeccionar → Medir distancia, Medir distancia mínima, Medir ángulo; útil para comprobar holguras y la distancia entre centros de crucetas `[inferido]`.

### 7.3 Propiedades físicas del conjunto
- Inspeccionar → **Propiedades físicas**: masa, volumen, centro de masa y momentos. Solo cuentan las ocurrencias con *usar en propiedades de masa* activado `[doc]` (propiedad de ocurrencia); cada pieza debe tener material y densidad `[inferido]`. Constante `AssemblyAssemblyToolsPhysicalProperties` `[doc]`.

### 7.4 Arrastrar componente (Drag Component) `[doc]`
- La pieza debe estar libre (subdefinida) o anclada. Si no se mueve, clic derecho → **Suprimir** temporalmente relaciones `[doc]`.
- Modos de la barra de comandos:
  - **Sin análisis**: mueve y observa; **Restablecer** devuelve la posición inicial.
  - **Detectar colisiones**: avisa de choques mientras arrastras; los valores se aplican de una vez y la precisión depende del zoom.
  - **Movimiento físico**: detecta contactos entre superficies sin restricciones y crea restricciones temporales (engranajes, contacto deslizante); Distancia y Ángulo se aplican de forma incremental; *Sensibilidad* equilibra velocidad y precisión. Si falla, revisa que todas las piezas tengan **propiedades de masa** válidas guardadas `[doc]` (KB PL7008680).
- **Opciones de análisis**: *Localizar componentes anclados*; *Analizar (solo piezas mostradas)*: solo activas o activas e inactivas; *Opciones de colisión*: solo las de la pieza seleccionada o entre todas, *Mostrar interferencias existentes*, *Aviso sonoro*, **Detener el movimiento al chocar**.
- Consejo: en sombreado, las caras ocultas en colisión no se resaltan; usa líneas ocultas vectoriales y haz zoom en la zona sospechosa `[doc]`.

**Arrastrar componente vs Simular motor** `[inferido]` (a partir de `[doc]`):

| | Arrastrar componente | Simular motor |
|---|---|---|
| Entrada | Mano del usuario (arrastre, o distancia y ángulo tecleados) | Motor definido (velocidad, límites, duración) |
| Repetible | No | Sí (F5 repite) |
| Colisiones | Sí (Detectar colisiones / Movimiento físico) | Sí (en Propiedades del grupo de motores) |
| Salida | Ninguna; solo comprobación | Animación guardable (AVI) y reutilizable en ERA |
| Uso | Diagnóstico rápido de GDL | Demostración y entrega |

### 7.5 Cortes del ensamble
- Vista con **planos de recorte** (Ver → *Set Planes* / planos de recorte) o vistas de sección en la pestaña PMI, para revisar solapes internos `[fuente secundaria]` (blog de buenas prácticas de Siemens). No ensambles en **perspectiva**: dificulta seleccionar aristas y planos `[fuente secundaria]`.

---

## 8. Movimiento: motores, Simular motor y video

### 8.1 Crear un motor `[doc]`
Ubicación: **Inicio → grupo Ensamblar → Motor** (en versiones recientes, botón **Motor rotacional**, con Motor lineal en el mismo desplegable; **Simular motor** justo debajo) `[doc]` / `[fuente secundaria]`.
1. (Recomendado) **Unidades**: botón Aplicación → Propiedades → **Propiedades del archivo** → pestaña **Unidades** → **Unidades avanzadas** → *Velocidad angular* = rpm o °/s → Aceptar `[doc]`.
2. Inicio → Ensamblar → **Motor** (o Motor rotacional).
3. **Tipo de motor**: Rotación o Lineal.
4. Seleccionar la **pieza infrarrestringida** que hará de motor (o una con sus relaciones suprimidas).
5. Seleccionar el **eje**: cara cilíndrica, borde cilíndrico o eje cilíndrico (en uno lineal, un elemento lineal) `[doc]`.
6. **Valor y límites del motor**: velocidad y, si quieres, un límite de recorrido (ejemplo oficial: 1750 rpm y 720° = dos vueltas). Las unidades de velocidad aceptan expresiones (el manual teclea `1/60` para 1/60 rpm) `[doc]`.
7. **Invertir dirección** si el giro sale al revés → **Finalizar** `[doc]`.
8. Queda una entrada **Motor** en el PathFinder; seleccionarla → **Editar definición** para cambiar parámetros `[doc]`.
- Puede haber **tantos motores como quieras** `[doc]`.
- **Velocidad para que se vea**: 120-360 °/s, no las rpm reales `[fuente secundaria]` (blog Siemens).

### 8.2 Simular motor `[doc]`
1. Inicio → Ensamblar → **Simular motor** → se abre **Propiedades del grupo de motores**:
   - Análisis: **Sin análisis** · **Detectar colisiones** · **Movimiento físico** (restricciones temporales entre superficies en contacto: engranajes sin relación Engranaje, contactos deslizantes).
   - **Duración del motor**: *Usar límites del motor como duración si se ha definido* o *Duración predeterminada del motor* (segundos).
   - **Motores disponibles** → Agregar/Quitar → **Motores en la animación**.
2. Aceptar → se abre el **Editor de animaciones** (versión reducida) → **Reproducir**. **F5** repite. Los controles son Ir al inicio, Cuadro anterior, Reproducir/Pausa, Parar, Cuadro siguiente, Ir al final y la **Velocidad**, que solo afecta a la reproducción, no al AVI ni a las rpm del motor `[doc]`.
3. Para cambiar valores después: clic derecho en **Motores** de la línea de tiempo → **Editar definición** `[doc]`.
4. **Guardar como película** (botón del editor) → AVI (§11.3) `[doc]`.
5. Al guardar el .asm, acepta guardar los cambios del editor de animaciones `[doc]`.

**Reglas que hacen fallar una simulación**
- Solo participan los motores del **conjunto activo**. Si la pieza motriz o las piezas arrastradas están en un **subconjunto**, ese subconjunto debe ser **Conjunto ajustable** (clic derecho en el PathFinder) para que sus relaciones se resuelvan arriba `[doc]`.
- Si la pieza motriz está totalmente posicionada (p. ej., Alinear eje **bloqueado** o un Ángulo), no se puede elegir o no gira: desbloquea o suprime `[doc]` / `[inferido]`.
- Para mecanismos con levas, el componente de la leva necesita alineación axial y coincidencia que lo sostengan `[doc]`.
- Problema conocido en ST10: algunos motores giraban al revés en ERA; arreglado en Solid Edge 2019; el remedio era poner **Actualizar = Relaciones** en el editor de línea de tiempo de ERA `[doc]` (KB PL8003396, leído solo como resumen).
- Recomendación de la comunidad: **define y prueba el motor en el entorno Conjunto** (Simular motor) y después llévalo a la línea de tiempo de ERA `[fuente secundaria]`.

### 8.3 Entorno Motion (simulación dinámica)
- Existe una constante de comando `AssemblyEnvironmentsMotion` `[doc]` y tutoriales antiguos entran por Herramientas → Entornos → *Motion* `[fuente secundaria]`. Su disponibilidad y licencia en 2026 **no se verificaron**. Para una entrega de CAD basta con Motor + Simular motor (cinemática) `[inferido]`.

API de motores: **no existe** ningún objeto ni comando "Motor" en las type libraries de SE 2026 `[verificado en este equipo]` (ver `05_api_automatizacion.md` §11). El motor se crea por interfaz. Para mover el mecanismo por código hay dos alternativas: una relación Angular motriz cuyo ángulo se cambia por pasos, o `AssemblyDocument.DragComponentRotation(...)`, que además **detecta colisiones** `[verificado en este equipo: firma]`.

---

## 9. Caso cardán: hacerlo girar con un motor

Situación: el cardán (soporte fijo, ejes, 4 horquillas, 2 crucetas, 40 pernos, 40 tuercas) se armó por API con **Anclar/Fijar + Alinear eje + Coincidir/Alinear plano**. Si las alineaciones axiales se crearon con **giro bloqueado** (`FixedRotate=True`) o se usó Alinear plano para orientar horquillas y crucetas, **el mecanismo está bloqueado** y el motor no podrá moverlo `[inferido]`.

### 9.1 Cadena cinemática objetivo `[inferido]`
| Unión | Relaciones recomendadas | GDL que queda |
|---|---|---|
| Soporte | Anclar (único anclaje del conjunto) | 0 |
| Eje de entrada ↔ alojamiento del soporte | Alinear eje **desbloqueado** + Coincidir (hombro con cara del soporte) o desplazamiento flotante | 1R (giro del eje): **aquí va el motor** |
| Horquilla 1 ↔ eje de entrada | Alinear eje **bloqueado** + Coincidir, o **Conjunto rígido** | 0 relativo (gira con el eje) |
| Cruceta 1 ↔ horquilla 1 | Alinear eje **desbloqueado** (muñón ↔ agujeros de la horquilla) + **Plano central** (cruceta centrada entre las orejas) | 1R relativo |
| Horquilla 2 ↔ cruceta 1 | Alinear eje **desbloqueado** (el otro muñón) + Plano central | 1R relativo |
| Eje intermedio ↔ horquillas 2 y 3 | Conjunto rígido o Alinear eje bloqueado + Coincidir | 0 relativo |
| Cruceta 2 y horquilla 4 | Igual que la junta 1 | 1R + 1R |
| Eje de salida ↔ soporte | Alinear eje **desbloqueado** + Coincidir/flotante | 1R |
| Pernos y tuercas | Insertar (bloqueado) **contra la pieza que sujetan y que se mueve**, nunca contra una pieza del otro lado de una articulación | 0 relativo |

- Comprobación de coherencia: con los tres ejes colineales (doble cardán a 0°), la cruceta queda determinada; al girar el eje de entrada, todo gira con velocidad de salida igual a la de entrada. Para que la animación muestre que es una junta universal, conviene que el diseño tenga un **ángulo** entre ejes (10-20°) si el soporte lo permite `[inferido]`.
- Si la cruceta se centró con Conectar (centro de la cruceta ↔ punto de intersección de ejes) en lugar de Plano central, también vale, pero no combines ambos: sobredefines `[inferido]`.

### 9.2 Procedimiento operativo (operario + el usuario)
1. **Probar antes de crear el motor**: Arrastrar componente (modo Sin análisis) sobre el eje de entrada, girándolo. ¿Gira toda la cadena? Si no, sigue con el paso 2 `[doc]` / `[inferido]`.
2. **Encontrar el bloqueo**: en el PathFinder, selecciona cada pieza de la cadena y mira el panel inferior: alineaciones axiales bloqueadas, Alinear plano o Ángulo que fijan la orientación, pernos que cruzan la articulación. **Suprime** (no borres) la sospechosa y repite el arrastre `[doc]` / `[inferido]`.
3. Desbloquear el giro: selecciona la relación axial → **Editar definición** → **Desbloquear rotación**. Por API, `AxialRelation3d.FixedRotate = False` `[doc]`.
4. Cuando el arrastre gire todo sin colisiones (modo Detectar colisiones), crea el **motor rotacional** en el eje de entrada: pieza = eje de entrada, eje = su cara cilíndrica, 90-180 °/s, límite 360° o 720° `[inferido]` (rango de velocidad: `[fuente secundaria]`).
5. **Simular motor** → *Detectar colisiones* → Reproducir. Si algo choca, revisa holguras con Verificar interferencia (§7.1) `[doc]`.
6. Guardar como película (AVI) para la entrega, o llevar el motor a la animación de ERA (§11) `[doc]`.
7. Guardar el .asm y aceptar los cambios del editor de animaciones `[doc]`.

**Ojo con el explosionado** `[doc]`: Explosionado automático usa las coincidencias y alineaciones axiales para decidir direcciones y **no puede explosionar piezas ancladas**. Si al construir por API se anclaron piezas para "colocarlas" (no solo el soporte), quedarán quietas al explosionar: sustituye esos anclajes por relaciones, o explosiónalas a mano con *Explosionar*.

---

## 10. Explosionado en el entorno ERA

Nombre oficial en español: aplicación **Explosionado - Renderizado - Animación** `[doc]` (el usuario la llama *Explosionar-Renderizar-Animar*). EN: **Explode-Render-Animate (ERA)**.
Acceso: **Herramientas → grupo Entornos → Explosionado-Renderizado-Animación** `[doc]` / `[fuente secundaria]`. Salida: **Cerrar ERA** (*Close ERA*) `[fuente secundaria]`.
Cada operación queda como **evento** en la pestaña **PathFinder de Explosionado** `[doc]`.

### 10.1 Comandos del entorno

| Comando (ES manual) | EN | Qué hace | Constante API (v106) |
|---|---|---|---|
| Explosionado automático | Automatic Explode | Explosiona por relaciones (mejor con coincidencia y alineación axial). No explosiona anclados ni tubos `[doc]` | `ExplodeExplodedViewAutomaticExplode` (65062) `[doc]` |
| Explosionar | Explode | Explosión manual: piezas → pieza base → cara o plano de la base → dirección → distancia `[doc]` | `ExplodeExplodedViewExplode` (65064) |
| Vincular / Desvincular subconjunto | Bind / Unbind Subassembly | El subconjunto explota como una sola unidad; símbolo en el PathFinder `[doc]` | 58001 / 58002 |
| Mover pieza (explosionada) | Move Exploded Part | Mueve o gira por el vector original, un vector nuevo o un plano; *Mover piezas dependientes*; un vector nuevo crea un quiebre (*saliente/joggle*) y un evento nuevo `[doc]` | `[API?]` |
| Reposicionar | Reposition | Cambia el **orden** de una pieza respecto a una de referencia (la flecha indica el lado) `[doc]` | `[API?]` |
| Contraer | Collapse | Devuelve la pieza a su sitio respecto a su antecesora; borra su línea de flujo `[doc]` | 65069 |
| Quitar | Remove | Oculta la pieza y la devuelve a la posición sin explosionar `[doc]` | `[API?]` |
| Desexplosionar | Unexplode | Reensambla todo para empezar otra explosión `[doc]` | 65068 |
| Líneas de flujo / Terminadores | Flow Lines / Flow Line Terminators | Muestra u oculta todas las líneas y sus flechas `[doc]` | 33095 / 33096 |
| Editar líneas de flujo | Edit Flow Lines (Modify) | Cambia longitud, posición del quiebre o anclaje de la línea `[doc]` | `[API?]` |
| Configuraciones de visualización | Display Configurations | Guarda, aplica o borra la explosión con nombre `[doc]` | 32826 |
| Editor de animaciones | Animation Editor | Línea de tiempo (§11) `[doc]` | `[API?]` |
| Guardar como imagen | Save as Image | Exporta una imagen `[inferido por el nombre]` | `ExplodeFileSaveAsImage` (58000) `[doc]` |

Constantes tomadas de la referencia v106: **verifica los valores en 2026** antes de usarlos con `StartCommand` `[API?]`.

### 10.2 Procedimiento paso a paso (explosionado de entrega)
1. Abre el .asm **con todas las piezas activas**. Si hay subconjuntos que deben moverse en bloque, **Vincúlalos** antes (Inicio → Vincular subconjunto, tras seleccionarlos en el PathFinder de Conjunto) `[doc]`.
2. Herramientas → Entornos → **Explosionado-Renderizado-Animación** `[doc]`.
3. **Explosionado automático** `[doc]`:
   1. *Seleccionar*: **Conjunto de nivel superior** (todo) o **Subconjunto** (los elegidos) → Aceptar.
   2. *Configuración*: **Opciones de explosionado automático** → *Vincular todos los subconjuntos* (sí/no) y *Técnica de explosionado*: **Por nivel de subconjunto** (las piezas de cada subconjunto quedan juntas) o **Por pieza individual** (ignora la estructura; las piezas se pueden mezclar).
   3. **Distancia de distribución automática** activada, o desactivada y teclear la distancia.
   4. **Explosionar** para previsualizar (puedes cambiar la distancia y volver a pulsar) → **Finalizar**.
4. **Corregir a mano** `[doc]`:
   - Piezas que no se movieron (ancladas, o colocadas sin coincidencia ni alineación axial) → **Explosionar**: seleccionar piezas → Aceptar → pieza base → cara o plano de la base que da la dirección → flecha de sentido → **Distancia** → Finalizar. Con varias piezas: *Distribuir componentes uniformemente* (orden con Mover arriba/abajo) o *Mover componentes como una unidad*.
   - Orden incorrecto → **Reposicionar**.
   - Distancia o dirección → **Mover pieza** (arrastrar sobre el eje del triedro; X = vector de explosión).
   - Pernos y tuercas: que salgan **a lo largo de su eje** y por encima de la cara que sujetan. Mételos en un **Grupo de eventos** para que en la animación se muevan juntos `[doc]` / `[inferido]`.
5. **Ajustar distancias exactas** en el PathFinder de Explosionado `[doc]`: seleccionar un evento → teclear Distancia (o ángulo) en la barra de comandos. Una pieza con varios eventos → seleccionar la pieza → Distancia (solo cambia los eventos lineales). Varias piezas → seleccionarlas con un recuadro → Distancia.
6. **Líneas de flujo** `[doc]`:
   - Mostrar u ocultar todas (Líneas de flujo, Terminadores); una sola, con clic derecho en la pieza o el evento → Mostrar/Ocultar líneas de flujo.
   - **Editar líneas de flujo**: arrastrar un extremo cambia la longitud; arrastrar el quiebre lo reubica; clic cerca de un extremo y luego en un borde o cara reancla la línea (por defecto nacen en el centro de la caja envolvente de la pieza antecesora).
   - Borrar un quiebre: evento en el PathFinder de Explosionado → Eliminar.
   - **Dos tipos de línea**: las de **evento** (las crean los comandos de explosión y siguen la trayectoria en la animación) y las de **anotación** (para planos). "Soltar" (*drop*) las de evento las convierte en anotación, cada una con su entrada propia; las de anotación se editan con Modificar y pueden engancharse a puntos clave `[doc]`.
   - Solo se pueden seleccionar líneas en pantalla con Editar líneas de flujo, o desde el PathFinder de Explosionado `[doc]`.
7. **PathFinder de Explosionado** `[doc]`: símbolos de Pieza, Conjunto, **Grupo** (piezas en un mismo vector, que se animan en secuencia), **Grupo de eventos** (piezas que se mueven a la vez), Evento lineal, Evento de rotación, Piezas movidas y Piezas no explosionadas. Los grupos se reordenan arrastrando (los grupos de eventos no). *Agregar a grupo de eventos* y *Quitar de grupo de eventos* (no disponibles con el Editor de animaciones abierto).
8. **Encuadre**: orienta la vista (isométrica) y ajusta el zoom antes de guardar; la vista se guarda con la configuración y luego evita problemas de líneas de flujo en el plano `[doc]` (KB PL8014193).
9. **Guardar la configuración** `[doc]`: Inicio → grupo Configuraciones → **Configuraciones de visualización** → escribir el *Nombre de configuración* (sin `\ / :`), p. ej. `EXPLOSIONADO_ENTREGA` → **Guardar**. Atajo: el comando **Guardar configuración de visualización** de la cinta guarda sobre el nombre que se ve en la cinta `[doc]` (manual ST4).
10. **Cerrar ERA** y **guardar el .asm** `[fuente secundaria]` (PROLIM).
11. Para otra explosión: **Desexplosionar**, explosionar de nuevo y guardar con **otro nombre** `[doc]`.

**Dónde viven las configuraciones**: el cuadro muestra un **Archivo de configuración** que contiene los nombres y datos de visualización `[doc]`. En Solid Edge suele ser un `.cfg` con el mismo nombre que el `.asm`, en la misma carpeta: **entrégalo junto con el .asm**, o la explosión no aparecerá al abrirlo en otro equipo `[inferido]` (comprueba que el archivo exista).

**Aplicar una configuración explosionada fuera de ERA** `[doc]` (manual ST4): la opción *Options for displaying exploded configurations outside ERA* ofrece **Preguntar acción**, **Aplicar solo ajustes de visualización** (sin entrar a ERA) o **Cambiar a ERA y explosionar**.

**Novedad 2026: Visual Explode.** Siemens anuncia mejoras para **capturar el estado explosionado como configuración de visualización** reutilizable en planos, imágenes y animaciones, "con más precisión y manteniendo las relaciones" `[fuente secundaria]`. No se encontró la descripción del comando ni su nombre en español. **Prioriza el flujo clásico de esta sección**, que en 2026 sigue existiendo `[inferido]`, y prueba Visual Explode solo si el usuario lo ve en su cinta.

---

## 11. Animación del explosionado, render y exportación

### 11.1 Editor de animaciones `[doc]`
En ERA: Inicio → grupo Animar → **Editor de animaciones**. Tipos de evento: **Cámara, Motor, Explosionado, Aspecto, Trayectoria del movimiento**.
- Barra superior: Lista de animaciones · **Nueva animación** · Guardar animación · Eliminar · **Propiedades de la animación** (duración, nombre, cuadros por segundo) · **Guardar como película** · **Trayectoria de cámara** (asistente) · Visualizar trayectoria de cámara · Trayectoria del movimiento · Aspecto (aparecer o desvanecer piezas).
- Panel izquierdo: categorías de eventos; clic derecho → **Editar definición** (Cámara → Asistente de trayectoria de cámara; Motor → Propiedades del grupo de motores; Explosionado → **Propiedades de explosión**) · Renombrar · Eliminar · Ampliar todo.
- Panel derecho: línea de tiempo con **barras de duración** (arrastrar para mover; arrastrar los extremos para alargar o acortar); Alternar escala cuadros/segundos; Insertar cuadro clave (cámara y trayectoria); Cortar, Copiar, Pegar, Eliminar duración.

### 11.2 Animar la explosión, paso a paso
1. En ERA, con la configuración explosionada guardada → **Editor de animaciones** → **Nueva animación** → nombre, duración (p. ej., 20 s), fps (20-30 recomendado; 60 = muy alta calidad y archivo grande) `[doc]` / `[fuente secundaria]`.
2. Clic derecho en **Explosionado** → Editar definición → **Propiedades de explosión** `[doc]`:
   - **Usar explosionado desde configuración** → elige `EXPLOSIONADO_ENTREGA`.
   - **Velocidad**: *Velocidad común para todas las piezas* o *Duración del explosionado* (segundos por evento).
   - **Orden de animación**: *Primero más interno* o *Primero más externo*.
   - **Estado inicial**: *Contraído* (arranca armado y se despiece: lo normal) o *Ampliado*.
3. (Opcional) **Motor**: clic derecho en Motor → Editar definición → agregar el motor del eje de entrada; ubica su barra **antes** de la explosión (primero gira y luego se despiece) `[doc]` / `[inferido]`.
4. (Opcional) **Cámara**: Asistente de trayectoria de cámara (órbita alrededor del conjunto) `[doc]`.
5. (Opcional) **Aspecto**: desvanecer el soporte para mostrar el interior. El autor del blog de Siemens no lo veía en la vista previa, pero sí en la película final `[fuente secundaria]`.
6. **Reproducir** y ajustar las barras. **Guardar animación** `[doc]`.

### 11.3 Guardar video `[doc]`
- **Guardar como película** → cuadro *Guardar como película* → **Opciones**: calidad de render, compresión y tamaño en píxeles → formato **AVI** `[doc]` / `[fuente secundaria]`.
- No se encontró confirmación de MP4 nativo en 2026. Si la entrega pide MP4, convierte el AVI con ffmpeg (hay una habilidad `ffmpeg` en el equipo): `ffmpeg -i cardan.avi -c:v libx264 -pix_fmt yuv420p cardan.mp4` `[inferido]`.
- Con Solid Edge Embedded Client (Teamcenter), los AVI se guardan en carpetas no administradas `[doc]`.

### 11.4 Render
- Desde ST7 (2014), el render fotorrealista de Solid Edge es **KeyShot** (integración incluida en Classic y Premium; en Foundation, plugin descargable): un botón envía el modelo, y *Update Render* refresca tras cambios. KeyShot también puede renderizar animaciones cuadro a cuadro `[fuente secundaria]` / `[doc]` (folleto de Siemens).
- En las versiones antiguas, ERA tenía render propio (estilo de vista de presentación; Renderizar escena o área; materiales, fondos, luces) `[doc]` (manual 2010). **No se verificó qué queda de él en 2026 ni qué licencia de KeyShot trae la edición universitaria del usuario**.
- Para la entrega de CAD, normalmente basta con una **imagen sombreada con aristas** exportada (Guardar como imagen) y el AVI con sombreado estándar `[inferido]`.

---

## 12. De la configuración explosionada al plano

### 12.1 Crear la vista explosionada `[doc]`
**Opción A, desde el conjunto** (fuera de ERA; *Crear plano* no está disponible dentro de ERA):
1. Aplicación → **Nuevo → Crear plano** (*Create Drawing*) → plantilla de la universidad → con *Ejecutar asistente de creación de vistas* marcado `[doc]` / `[fuente secundaria]`.
2. En el asistente, página de opciones de vista de conjunto → **Configuración** → elige `EXPLOSIONADO_ENTREGA` → orientación (isométrica o la guardada) → Finalizar → colocar la vista `[doc]`.

**Opción B, desde un .dft**: comando **Asistente de vistas de dibujo** (*View Wizard*) → seleccionar el .asm → elegir la configuración explosionada → colocar `[doc]`. También se puede cambiar después: Propiedades de la vista → pestaña de visualización → configuración `[doc]` (KB PL8007195).

### 12.2 Globos y lista de piezas
- **Lista de piezas** (*Parts List*) en la pestaña Inicio del plano → clic en la vista explosionada → coloca la tabla y puede **numerar con globos automáticamente** `[inferido]` (detalle en `04_planos_draft.md`).
- Los valores de la pestaña de globos de *Propiedades de la lista de piezas* solo se pueden editar **al colocar la lista por primera vez**; después quedan en gris `[doc]` (KB PL8008953). **Configura los globos antes de colocar.**
- Si una pieza no sale en la lista o su globo dice N/A: en sus **Propiedades de ocurrencia**, la columna *Informes/Lista de plano* debe estar en **Sí** `[doc]` (KB PL8599076).
- Los 40 pernos y 40 tuercas iguales deben salir como **una fila con cantidad 40**: depende de que sean el mismo archivo .par `[inferido]`.

### 12.3 Líneas de flujo en el plano `[doc]`
- Se muestran **automáticamente**; se controlan en *Propiedades de la vista de dibujo* → pestaña **Anotación**, o con **Dibujar en vista**.
- Si en el plano salen líneas que faltan o incompletas: abre la configuración en ERA, **ajusta la vista** (Ajustar), **guárdala** otra vez y **actualiza las vistas** del plano `[doc]` (KB PL8014193).
- Las líneas de flujo de **anotación** (las "soltadas" en ERA) son las pensadas para el plano; tras ponerlas hay que **guardar la configuración** antes de llevarla al plano `[doc]`.
- **Vista explosionada en perspectiva**: guarda la configuración con la perspectiva activa y usa *Orientación personalizada* del asistente; después cambia la vista a esa configuración `[doc]` (KB PL8007195).

---

## 13. Método y buenas prácticas

**Orden lógico** `[doc]` / `[fuente secundaria]` / `[inferido]`
1. **Modela las piezas en la orientación que tendrán en el conjunto**, con los planos base como simetría: el solver acierta más `[fuente secundaria]`.
2. **Primera pieza = base anclada** (soporte o bastidor). Un solo anclaje por grupo de piezas relacionadas: relacionarlas con dos piezas ancladas distintas puede funcionar hoy y fallar mañana `[doc]`.
3. Relaciona todo con **una referencia común** (la base o sus planos), no en cadenas largas, **salvo en cadenas cinemáticas** como el cardán `[fuente secundaria]`.
4. **Relaciones mínimas suficientes**: las redundantes consumen memoria, ralentizan el cálculo y generan conflictos. Revisa el estado en el PathFinder y suprime o borra las sobrantes `[fuente secundaria]`.
5. Usa **FlashFit** cuando aplique: aplica el mínimo de relaciones `[fuente secundaria]`.
6. **Totalmente posicionado** todo lo que no deba moverse; **subdefinido a propósito solo el GDL del mecanismo**. Los conjuntos parcialmente restringidos se resuelven de forma menos predecible al arrastrar `[fuente secundaria]`.
7. **Subconjuntos** para grupos lógicos (cada junta universal, la tornillería de una brida): las relaciones dentro del subconjunto aceleran el nivel superior `[fuente secundaria]`. Si el subconjunto debe moverse por dentro → **Conjunto ajustable** `[doc]`.
8. **Simetría**: relaciona las piezas simétricas con planos medios o ejes; si todo el conjunto es simétrico, relaciona la base con los planos base del conjunto `[fuente secundaria]`.
9. No relaciones contra operaciones que puedan suprimirse; ante una relación dudosa, **suprímela** en vez de borrarla o cambiarla `[fuente secundaria]`.
10. **Nombres**: archivos claros (`01_Soporte.par`, `02_Eje_entrada.par`, `03_Horquilla.par`…), grupos renombrados en el PathFinder y propiedades del archivo (título, autor, material) llenas, porque alimentan la lista de piezas `[inferido]`. Guarda las piezas en carpetas por subconjunto y usa **Design Manager** para renombrar o mover sin romper vínculos `[fuente secundaria]`.
11. **Plantilla** común (unidades, precisión, propiedades) para conjunto y piezas `[fuente secundaria]`.
12. **No ensambles en perspectiva** `[fuente secundaria]`.

**Verificación final**
- PathFinder sin rojo, sin relaciones fallidas y sin símbolos de "sin colocar" salvo en las piezas del mecanismo `[doc]`.
- **Verificar interferencia** de todo contra sí mismo, con las opciones de rosca activas → 0 interferencias, o solo las esperadas `[doc]`.
- **Arrastrar componente** con *Detectar colisiones* sobre el eje de entrada → gira toda la cadena sin choques `[doc]`.
- **Simular motor** → reproduce sin saltos ni bloqueos `[doc]`.
- **Propiedades físicas** con masas coherentes (comprueba que todas las piezas tengan material) `[inferido]`.

---

## 14. Checklist de entrega

**Ensamble general (.asm)**
- [ ] Una sola pieza anclada (la base); todas las demás posicionadas con relaciones.
- [ ] PathFinder sin conflictos (rojo) ni relaciones fallidas; las suprimidas, borradas o justificadas.
- [ ] Solo el mecanismo queda subdefinido, y a propósito (eje de entrada, crucetas, eje de salida).
- [ ] Tornillería con Insertar y en patrón donde se pueda; misma pieza .par repetida, para que la lista cuente cantidades.
- [ ] Verificar interferencia = 0 (con las opciones de rosca); captura del resultado.
- [ ] Propiedades de cada pieza (nombre, número, material, autor) completas.
- [ ] Ocurrencias que deben salir en el plano con *Informes/Lista de plano = Sí*.

**Movimiento**
- [ ] Arrastrar componente en el eje de entrada mueve toda la cadena.
- [ ] Motor rotacional en el eje de entrada (90-180 °/s; límite de 360° o 720°); entrada *Motor* visible en el PathFinder.
- [ ] Simular motor con *Detectar colisiones*, sin choques.
- [ ] AVI guardado (y MP4 convertido, si lo piden).

**Explosionado (ERA)**
- [ ] Todas las piezas separadas, pernos y tuercas a lo largo de su eje y en grupos de eventos.
- [ ] Orden lógico de desmontaje (de fuera hacia dentro), sin piezas solapadas en la vista.
- [ ] Líneas de flujo limpias (sin cruces innecesarias), con terminadores.
- [ ] Vista isométrica encuadrada y **configuración guardada con nombre** (`EXPLOSIONADO_ENTREGA`).
- [ ] Archivo de configuraciones (.cfg) junto al .asm en la carpeta de entrega `[inferido]`.

**Animación**
- [ ] Animación en ERA: motor (opcional), explosión (estado inicial Contraído), cámara (opcional).
- [ ] AVI exportado con fps y tamaño adecuados; reproducido una vez fuera de Solid Edge para comprobarlo.

**Plano de conjunto (.dft)** (detalle en `04_planos_draft.md`)
- [ ] Vista explosionada desde la configuración guardada; líneas de flujo visibles.
- [ ] Lista de piezas con globos que coinciden; cantidades correctas (40 pernos, 40 tuercas, 4 horquillas, 2 crucetas…).
- [ ] Cuadro de rotulación de la universidad; exportado a PDF.

**Empaquetado**
- [ ] Carpeta con todos los .par, .asm, .cfg, .dft, .avi/.mp4 y .pdf. Al abrir el .asm desde otra ruta no falta ningún componente (sin símbolo *Falta componente*).

---

## 15. Lo que no se pudo verificar

- La ayuda oficial **2026** (docs.sw.siemens.com no devolvió contenido legible). Las posiciones exactas en la cinta y los nombres en español de 2026 pueden diferir de los manuales de 2010-2014.
- Nombre en español de Ground en la UI del usuario (**Fijar** o **Anclar**), de Check Interference, Drag Component, Transfer, Disperse, Mirror, Standard Parts y de las novedades 2026.
- Qué relaciones crea exactamente **Magnetic Snap Assembly** (2026) y cómo funciona **Visual Explode** (2026).
- ~~Si existe API COM para motores y explosiones~~ → resuelto el 2026-10-28 en la type library de SE 2026: **motores no**; **explosión automática sí** (`AssemblyDocument.AutoExplode`); arrastre con colisiones sí (`DragComponentRotation`/`Translation`). Sigue sin verificar cómo se guarda la explosión como configuración por API y si hay API del Editor de animaciones.
- Formatos de video distintos de AVI y la licencia de **KeyShot** en la edición del usuario.
- La cantidad de GDL que quita cada relación es deducción geométrica `[inferido]`; la ayuda de Siemens no la tabula.
- Que el archivo de configuraciones sea un `.cfg` separado (el cuadro oficial menciona un "Archivo de configuración"; la extensión es inferida).

---

## 16. Fuentes

**Ayuda oficial de Solid Edge (espejo de ST5/ST6) — `[doc]`**
- Relaciones de conjunto (resumen y enlaces): https://soliddna.com/SEHelp/ST6/EN/assemble_parts/const1a.htm · https://soliddna.com/SEHelp/ST5/EN/a_h/const1a.htm
- Mate: https://soliddna.com/SEHelp/ST6/EN/assemble_parts/mate1c.htm
- Axial Align: https://soliddna.com/SEHelp/ST6/EN/assemble_parts/align2c.htm
- Insert: https://soliddna.com/SEHelp/ST6/EN/assemble_parts/insert1c.htm
- Connect: https://soliddna.com/SEHelp/ST6/EN/assemble_parts/conect1c.htm
- Angle: https://soliddna.com/SEHelp/ST6/EN/assemble_parts/angle1c.htm
- Parallel: https://soliddna.com/SEHelp/ST6/EN/assemble_parts/parall1c.htm
- Tangent: https://soliddna.com/SEHelp/ST6/EN/assemble_parts/tangas1c.htm
- Cam: https://soliddna.com/SEHelp/ST6/EN/assemble_parts/cam1c.htm
- Center-Plane: https://soliddna.com/SEHelp/ST6/EN/assemble_parts/center_plane1c.htm
- Ground: https://soliddna.com/SEHelp/ST6/EN/assemble_parts/ground1c.htm
- Rigid Set: https://soliddna.com/SEHelp/ST6/EN/assemble_parts/xid453586.htm
- Path: https://soliddna.com/SEHelp/ST6/EN/assemble_parts/xid453577.htm
- Gear: https://soliddna.com/SEHelp/ST5/EN/a_h/gear1c.htm · https://soliddna.com/SEHelp/ST5/EN/a_h/gear1d.htm
- Capture Fit: https://soliddna.com/SEHelp/ST6/EN/assemble_parts/capfit1c.htm
- Assembly Relationship Assistant: https://soliddna.com/SEHelp/ST6/EN/assemble_parts/relasst1c.htm
- PathFinder en conjuntos: https://soliddna.com/SEHelp/ST6/EN/assemble_parts/pthfnd1a.htm
- Motores: https://soliddna.com/SEHelp/ST6/EN/assemble_parts/motor1c.htm · https://soliddna.com/SEHelp/ST6/EN/assemble_parts/motor1h.htm · https://soliddna.com/SEHelp/ST6/EN/assemble_parts/motor2h.htm
- Motor Group Properties: https://soliddna.com/SEHelp/ST5/EN/i_v/prpmotor1d.htm
- Arrastrar componente y colisiones: https://soliddna.com/SEHelp/ST6/EN/assemble_parts/movprt1a.htm · https://soliddna.com/SEHelp/ST6/EN/assemble_parts/movprt2d.htm
- Verificar interferencia: https://soliddna.com/SEHelp/ST6/EN/assemble_parts/intfer1a.htm · https://soliddna.com/SEHelp/ST6/EN/assemble_parts/intfer3d.htm
- Reestructurar (Transferir/Dispersar): https://soliddna.com/SEHelp/ST6/EN/assemble_parts/restructure1a.htm · https://soliddna.com/SEHelp/ST6/EN/assemble_parts/transfer2h.htm · https://soliddna.com/SEHelp/ST6/EN/assemble_parts/disperse1h.htm
- Mirror Components: https://soliddna.com/SEHelp/ST6/EN/assemble_parts/mirasm1c.htm
- Patrón (Pattern Assembly Feature): https://soliddna.com/SEHelp/ST5/EN/a_h/feat14c.htm
- Vistas explosionadas en conjuntos (ERA): https://soliddna.com/SEHelp/ST6/EN/assemble_parts/xpldas1a.htm · https://soliddna.com/SEHelp/ST5/EN/w_z/xpldas1a.htm
- Barra de Explosionado automático: https://soliddna.com/SEHelp/ST5/EN/a_h/atxpld1d.htm
- Display Configuration Options: https://soliddna.com/SEHelp/ST5/EN/a_h/configmngroptionsd.htm

**Manuales oficiales de autoformación de Siemens — `[doc]`**
- spse01540 *Modelado de conjuntos* (español): https://support.industrysoftware.automation.siemens.com/training/se/es/ST3/pdf/spse01540.pdf
- spse01541 *Aplicación Explosionado - Renderizado - Animación* (español): https://support.industrysoftware.automation.siemens.com/training/se/es/ST3/pdf/spse01541.pdf
- spse01541 (inglés): https://support.industrysoftware.automation.siemens.com/training/se/en/ST3/pdf/spse01541.pdf
- spse01691 *Exploding assemblies* (ST4): https://support.industrysoftware.automation.siemens.com/training/se/en/ST4/pdf/spse01691-s-1040_en.pdf
- spse01693 *Animating assemblies* (ST4): https://support.industrysoftware.automation.siemens.com/training/se/en/ST4/pdf/spse01693-s-1040_en.pdf
- Folleto *Solid Edge motion simulation, explode – render – animate*: https://www.plm.automation.siemens.com/en_us/Images/10171_tcm1023-5057.pdf

**Referencia API (Solid Edge Assembly Type Library) — `[doc]`**
- Relations3d: https://support.industrysoftware.automation.siemens.com/trainings/se/107/api/SolidEdgeAssembly~Relations3d_members.html
- AddAxialWithParallelOffset: https://support.industrysoftware.automation.siemens.com/trainings/se/107/api/SolidEdgeAssembly~Relations3d~AddAxialWithParallelOffset.html
- AxialRelation3d: https://support.industrysoftware.automation.siemens.com/trainings/se/107/api/SolidEdgeAssembly~AxialRelation3d_members.html
- PlanarRelation3d: https://support.industrysoftware.automation.siemens.com/trainings/se/107/api/SolidEdgeAssembly~PlanarRelation3d_members.html
- AddGear: https://support.industrysoftware.automation.siemens.com/trainings/se/107/api/SolidEdgeAssembly~Relations3d~AddGear.html
- RigidSetRelation3d: https://support.industrysoftware.automation.siemens.com/trainings/se/107/api/SolidEdgeAssembly~RigidSetRelation3d_members.html
- CamFollowerRelation3d: https://support.industrysoftware.automation.siemens.com/trainings/se/107/api/SolidEdgeAssembly~CamFollowerRelation3d.html
- AssemblyPatterns.Create: https://support.industrysoftware.automation.siemens.com/trainings/se/107/api/SolidEdgeAssembly~AssemblyPatterns~Create.html
- AssemblyDocument.CheckInterference: https://support.industrysoftware.automation.siemens.com/trainings/se/107/api/SolidEdgeAssembly~AssemblyDocument~CheckInterference.html
- AssemblyCommandConstants: https://support.industrysoftware.automation.siemens.com/trainings/se/106/api/SolidEdgeConstants~AssemblyCommandConstants.html
- ExplodeCommandConstants: https://support.industrysoftware.automation.siemens.com/trainings/se/106/api/SolidEdgeConstants~ExplodeCommandConstants.html

**Base de conocimiento de Siemens — `[doc]`** (algunos requieren inicio de sesión; leídos como resumen de búsqueda)
- PL8566091 Relaciones sustituidas por anclaje: https://support.sw.siemens.com/en-US/okba/PL8566091/Created-relationships-while-inserting-components-are-unexpectedly-substituted-with-a-Ground-relationship/index.html
- PL8571490 Primera coincidencia no se aplica: https://support.sw.siemens.com/en-US/okba/PL8571490/First-Mate-relationship-can-not-be-applied/index.html
- PL8014376 Mover la base anclada: https://support.sw.siemens.com/en-US/okba/PL8014376/Relationships-not-staying-together-as-anticipated-after-Move/index.html
- PL8003396 Motor gira al revés en ERA: https://support.sw.siemens.com/en-US/okba/PL8003396/Animation-Motor-is-moving-in-wrong-direction/index.html
- PL7009565 / PL7008680 Movimiento físico: https://support.sw.siemens.com/en-US/okba/PL7009565/Drag-Component-with-option-Physical-Motion/index.html · https://support.sw.siemens.com/en-US/okba/PL7008680/Physical-movement-not-moving-parts/index.html
- PL8014193 Líneas de flujo mal en el plano: https://support.sw.siemens.com/en-US/okba/PL8014193/Flow-lines-of-an-exploded-view-are-not-shown-correctly/index.html
- PL8007195 Vista explosionada en perspectiva: https://support.sw.siemens.com/en-US/okba/PL8007195/How-to-place-a-perspective-view-in-draft-of-an-exploded-assembly/index.html
- PL8599076 Globos N/A / pieza fuera de la lista: https://support.sw.siemens.com/en-US/okba/PL8599076/Cannot-Balloon-Certain-Components-in-Assembly-Drawing/index.html
- PL8008953 Pestaña de globos en gris: https://support.sw.siemens.com/en-US/okba/PL8008953/Values-in-balloon-tab-of-the-Parts-List-Properties-are-grayed-out/index.html
- PL8736257 / PL8669638 Mirror Components: https://support.sw.siemens.com/en-US/okba/PL8736257/Subassemblies-do-not-expand-during-Mirror-Component/index.html · https://support.sw.siemens.com/en-US/okba/PL8669638/How-to-avoid-an-extra-output-file-_mirpar-while-mirroring-frame-components-with-an-asymmetrical-profile/index.html
- PL8017372 Dispersar un subconjunto: https://support.sw.siemens.com/en-US/okba/PL8017372/How-do-you-break-up-a-subassembly-into-individual-parts/index.html

**Fuentes secundarias**
- Blog Siemens, *Solid Edge assembly best practices*: https://blogs.sw.siemens.com/solidedge/solid-edge-assembly-best-practices/
- Blog Siemens, *Creating animations in Solid Edge* (2013): https://blogs.sw.siemens.com/solidedge/creating-animations-in-solid-edge/
- Blog Siemens, *New assembly productivity tools in Designcenter Solid Edge 2026*: https://blogs.sw.siemens.com/solidedge/new-assembly-productivity-tools-in-designcenter-solid-edge-2026
- Blog Siemens, *Designcenter Solid Edge 2026 artificial intelligence*: https://blogs.sw.siemens.com/solidedge/designcenter-solid-edge-2026-artificial-intelligence/
- Blog Siemens, *Solid Edge 2025 design productivity*: https://blogs.sw.siemens.com/solidedge/solid-edge-2025-design-productivity/
- Blog Siemens, *Using the Solid Edge Relationship Browser*: https://blogs.sw.siemens.com/solidedge/using-the-solid-edge-relationship-browser/
- Blog Siemens, *ST7 Duplicate Components*: https://blogs.sw.siemens.com/solidedge/st7-duplicate-components/
- Blog Siemens, KeyShot incluido con ST7: https://blogs.sw.siemens.com/news/new-world-class-rendering-capabilities-from-keyshot-included-with-solid-edge-st7/
- Develop3D, *Designcenter Solid Edge 2026*: https://develop3d.com/cad/designcenter-solid-edge-2026/
- PROLIM, *How to Create an Exploded Drawing in Solid Edge*: https://prolim.com/blog/solid-edge/how-to-create-an-exploded-drawing-in-solid-edge
- Design Engineering, *Assembly tips and tricks in Solid Edge ST*: https://www.design-engineering.com/assembly-tips-and-tricks-in-solid-edge-st-127630/
- GrabCAD, patrón de pernos en conjunto: https://grabcad.com/questions/how-to-assemble-patterns-in-solid-edge
- Eng-Tips, motores en animación: https://www.eng-tips.com/threads/how-do-you-put-your-motion-simulation-into-your-animation.275289
