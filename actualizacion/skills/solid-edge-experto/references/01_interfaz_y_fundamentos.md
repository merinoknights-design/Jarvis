# 01 — Interfaz y fundamentos de Solid Edge 2026 (interfaz en español)

> **Para qué sirve este capítulo:** saber dónde está cada cosa en Solid Edge, cómo se llama en español y en inglés, y qué hace. Así el operario (Claude) puede guiar al usuario por la interfaz, buscar en la ayuda en cualquiera de los dos idiomas y traducir a Solid Edge lo que conoce de otros programas CAD.
>
> **Etiquetas:** `[doc]` = ayuda oficial de Siemens · `[fuente secundaria]` = blog o artículo de soporte de Siemens, prensa técnica o foros · `[inferido]` = deducción mía, sin verificar en pantalla.
>
> **Con qué versión está verificado.** La ayuda oficial en español que Siemens publica abierta en `docs.sw.siemens.com` corresponde a **Solid Edge 2024 (2310)**. La ayuda de 2025 y 2026 no apareció sin iniciar sesión. Los nombres en español salen, por tanto, de la ayuda 2024 `[doc]`, y los cambios de 2025 y 2026 salen de los blogs de Siemens `[fuente secundaria]`. **Si un nombre en pantalla no coincide, manda la pantalla del usuario:** se usa el Buscador de comandos (§3.6) y se corrige este archivo.

---

## Tabla de contenido

0. [Vocabulario: lo que más confunde](#0-vocabulario-lo-que-más-confunde)
1. [Entornos y tipos de documento](#1-entornos-y-tipos-de-documento)
2. [Modelado ordenado vs síncrono](#2-modelado-ordenado-vs-síncrono)
3. [Anatomía de la ventana](#3-anatomía-de-la-ventana)
4. [La cinta por entorno: pestañas, grupos y comandos](#4-la-cinta-por-entorno-pestañas-grupos-y-comandos)
5. [Selección: QuickPick, filtros, cercados y puntos significativos](#5-selección-quickpick-filtros-cercados-y-puntos-significativos)
6. [Ver y orientar el modelo](#6-ver-y-orientar-el-modelo)
7. [Atajos de teclado y de ratón](#7-atajos-de-teclado-y-de-ratón)
8. [Opciones de Solid Edge: lo que importa](#8-opciones-de-solid-edge-lo-que-importa)
9. [Flujo de un proyecto y gestión de archivos vinculados](#9-flujo-de-un-proyecto-y-gestión-de-archivos-vinculados)
10. [Conceptos CAD transferibles](#10-conceptos-cad-transferibles)
11. [Equivalencias con SolidWorks, Inventor, Fusion 360 y CATIA V5](#11-equivalencias-con-solidworks-inventor-fusion-360-y-catia-v5)
12. [Novedades 2025–2026 que afectan al operario](#12-novedades-20252026-que-afectan-al-operario)
13. [Puente hacia la API COM (resumen)](#13-puente-hacia-la-api-com-resumen)
14. [Fuentes](#14-fuentes)

---

## 0. Vocabulario: lo que más confunde

| Lo que dice el usuario / el profesor | Término **oficial** en el Solid Edge en español | Inglés | Nota |
|---|---|---|---|
| Ensamble | **Conjunto** (entorno Conjunto, `.asm`) | Assembly | La ayuda en español usa siempre «Conjunto» `[doc]`. En la cinta, el grupo se llama «Ensamblar» `[doc]`. |
| Plano / dibujo | **Plano** (entorno Plano, `.dft`) | Draft / Drawing | «Vista de dibujo» = drawing view `[doc]`. |
| Operación / feature | **Operación** | Feature | Extrusión, agujero, redondeo… `[doc]` |
| Croquis | **Boceto** / **perfil** | Sketch / profile | En modo ordenado aparece «perfil» `[doc]`. |
| Restricción (de boceto) | **Relación** (geométrica) | Relationship | Horizontal, tangente, concéntrico… `[doc]` |
| Restricción (de ensamble), *mate* | **Relación de conjunto** | Assembly relationship | Coincidir, Alineación axial… `[doc]` |
| Cota / dimensión | **Cota** | Dimension | «Cota inteligente» = Smart Dimension `[doc]`. |
| Fijar la primera pieza | **Anclar** (relación de **anclaje**) | Ground | La 1.ª pieza que se coloca queda anclada sola `[doc]`. |
| Protrusión / extruir | **Extrudir** (crea una protrusión o un vaciado) | Extrude | En la ayuda 2024 el comando se llama Extrudir, y «Protrusión» sigue en las variantes (por barrido, por secciones…) `[doc]`. Desde qué versión cambió el nombre: `[inferido]`. En versiones viejas y en tutoriales aparece «Protrusión» |
| Corte / vaciado | **Cortar** · **Vaciado** | Cut · Cutout | `[doc]` |
| Vaciado tipo cáscara (*shell*) | **Dar espesor** (dentro de la lista **Pared fina**) | Thin Wall | ⚠️ No confundir con **Incrementar espesor** (Thicken) `[doc]`. |
| Redondeo / filete | **Redondeo** | Round | `[doc]` |
| Globo | **Referencia de elemento** | Balloon | En Plano, grupo Anotación `[doc]`. |
| Lista de materiales | **Lista de piezas** | Parts List | Plano > Tablas `[doc]`. |
| Explosionado | Entorno **ERA** (Explosionado-Renderizado-Animación) | Explode-Render-Animate | `[doc]` |
| Árbol | **PathFinder** | PathFinder | Mismo nombre en ambos idiomas `[doc]`. |
| Barra de mensajes | **BarraDeAvisos** | PromptBar | Escrito así, junto `[doc]`. |
| *Steering wheel* | **Controlador de volante** | Steering wheel | Sólo en síncrono `[doc]`. |
| Planos base | **Planta (xy) · Derecha (yz) · Alzado (xz)** | Top · Right · Front | `[doc]` |

---

## 1. Entornos y tipos de documento

Un **entorno** es el conjunto de pestañas, comandos y barras de comandos para una tarea. Se activan por separado `[doc]`.

| Entorno (ES) | EN | Extensión | Para qué | Plantilla ISO métrica por defecto |
|---|---|---|---|---|
| **Pieza** | Part | `.par` | Sólidos 3D: protrusiones, vaciados, agujeros, redondeos, ángulos de desmoldeo… `[doc]` | `iso metric part.par` `[doc]` |
| **Chapa** | Sheet Metal | `.psm` | Piezas finas desarrollables: caras, pestañas, plegados, desarrollo `[doc]` | `iso metric sheet metal.psm` `[inferido]` |
| **Conjunto** | Assembly | `.asm` | Combina piezas y subconjuntos con relaciones de conjunto `[doc]` | `iso metric assembly.asm` `[inferido]` |
| **Plano** | Draft | `.dft` | Dibujos 2D asociativos al modelo 3D `[doc]` | `iso metric draft.dft` `[doc]` |
| **Soldadura** (conjunto de soldadura) | Weldment | `.pwd` | Conjunto soldado con cordones y preparación `[doc]` | `[inferido]` |

**Subentornos** (se entra y se sale desde un documento): Boceto, Boceto 3D, ERA, Motion (Movimiento), Engineering Reference, Simulación, Diseño generativo, Impresión 3D, Ingeniería inversa, PMI `[doc]`. Para volver se usa el grupo **Cerrar** (por ejemplo «Cerrar boceto», «Cerrar ERA») `[doc]`.

**Plantillas** `[doc]`:
- Solid Edge instala plantillas anglosajonas y métricas por entorno, con normas ANSI, DIN, ESKD, GB, ISO, JIS y UNI.
- Se crean desde **Archivo > Nuevo**, eligiendo la plantilla. «Editar lista…» cambia las plantillas que aparecen.
- Un documento nuevo tiene un nombre temporal y vive en memoria hasta que se guarda: el primer **Guardar** pide el nombre y la carpeta.
- **Archivo > Ajustes > Opciones > Ayudas > Establecer plantillas predeterminadas** fija qué plantilla usa cada tipo de documento.
- **Plantilla rápida** (Plano): un plano con vistas vacías; al arrastrar un modelo encima, las vistas se rellenan.

**Unidades** `[doc]`: Opciones de Solid Edge, pestaña **Unidades**. Sistemas disponibles: **MMKS** (mm, kg, s), IPS, MKS, FPS y CPS. Se definen unidades base (longitud, masa, tiempo, ángulo, temperatura), unidades derivadas y la **precisión de lectura**. La precisión sólo cambia cómo se muestra el número, no el valor. Las unidades pertenecen **al archivo activo**. La plantilla ISO métrica arranca en mm `[inferido]`.

**Propiedades del archivo** `[doc]`: **Archivo > Información > Propiedades** (comando Propiedades). Grupos General, Resumen (título, autor…) y Personalizado. Alimentan la lista de piezas y el cuadro de rotulación del plano, así que se rellenan en cada pieza.

**Material** `[doc]`: la **Tabla de materiales** define el material, la densidad y, en chapa, la **Medida** (*gage*: espesor, radio de plegado, desahogo). PathFinder muestra un colector de material. La opción «Pedir material en documentos de modelo nuevos» (Opciones > General) obliga a elegirlo al crear la pieza.

---

## 2. Modelado ordenado vs síncrono

### 2.1 Qué es cada uno `[doc]`

| | **Ordenado** (Ordered) | **Síncrono** (Synchronous) |
|---|---|---|
| Base | **Historial**: secuencia de operaciones controladas por bocetos | **Caras**: una operación es un grupo de caras, **sin historial** |
| Boceto | Sigue unido a la operación y la controla | Se **consume**: deja de controlar la operación una vez creada |
| Edición | Volver a cualquier paso de la operación (Editar definición, Edición dinámica) | Mover o rotar caras con el **controlador de volante**, editar cotas 3D del modelo |
| Caras | No se editan directamente | Se editan directamente |
| Intención de diseño | En el orden y las referencias del árbol | En el panel **Intención de diseño** (antes Live Rules / «reglas vivas») y en las cotas 3D |
| Bocetos | Ordenados: no sirven para operaciones síncronas | Síncronos: sirven para operaciones síncronas y ordenadas |

Un modelo puede tener **sólo síncronas, sólo ordenadas o ambas**. Cuando conviven, el PathFinder muestra una **parte Síncrona** arriba y una **parte Ordenada** abajo. Lo ordenado se calcula **después** de lo síncrono `[doc]`.

### 2.2 Cómo se cambia `[doc]`

- **Al crear un documento:** Opciones de Solid Edge > **Ayudas** > «Iniciar documentos de Pieza y Chapa usando este entorno» → Síncrono u Ordenado.
- **Al abrir un documento:** si sólo tiene elementos síncronos, se abre en síncrono; si tiene ordenados (o mezcla), se abre en **ordenado**.
- **Durante el trabajo:** clic derecho en PathFinder o en la ventana gráfica → **Pasar a Síncrono** (Transition to Synchronous) o **Pasar a Ordenado** (Transition to Ordered). Si el modelo tiene ambos tipos, también vale **pulsar la barra de entorno** en PathFinder `[doc, ayuda ST6]`.
- **Mover a síncrono** (Move to Synchronous): en el entorno ordenado, clic derecho sobre operaciones ordenadas. Las mueve a la parte síncrona, donde se pueden editar como caras.
  - Es **de una sola dirección**: no hay vuelta de síncrono a ordenado.
  - Arrastra **todo lo que hay por encima** de la operación elegida, en orden contiguo desde arriba.
  - Las simetrías y patrones exigen mover también sus antecesoras.
  - Las cotas intentan engancharse a un vértice; las que no lo encuentran quedan **colgando**.
  - Siemens recomienda **recalcular** el nodo ordenado y resolver avisos antes de moverlas.
- **Convertir** (sin documentos abiertos, por lotes): convierte operaciones ordenadas en síncronas a nivel de archivo, con el cuadro «Convertidor de ordenado a síncrono».

### 2.3 Cuándo usar cada uno

- **Para el curso y para piezas que salen de un plano acotado → ORDENADO** `[inferido]`. Deja un historial que el profesor y el usuario pueden leer, bocetos totalmente definidos con las cotas del plano, y se reproduce paso a paso con **Reproducción de operaciones**. La API COM es además más predecible en ordenado (ver capítulo 05).
- **Síncrono** conviene para editar modelos importados (STEP sin historial), hacer cambios rápidos de geometría y conceptos `[doc]`/`[inferido]`.
- Siemens vende el modo híbrido: base síncrona y detalles ordenados (redondeos, patrones) `[fuente secundaria — blog Siemens "Example of mixing synchronous and ordered"]`.
- **Regla práctica para el operario:** decide un modo por pieza y declarálo antes de empezar. Si un archivo abre en síncrono y hay que trabajarlo con historial, se pasa a ordenado (clic derecho > Pasar a Ordenado) **antes** de crear operaciones `[inferido]`.

### 2.4 Controlador de volante (síncrono) `[doc]`

Herramienta gráfica para **mover o rotar** caras, operaciones, bocetos, planos de referencia, sistemas de coordenadas y cuerpos de diseño. No mueve los planos base ni el sistema de coordenadas base.

| Parte | Qué hace (botón izquierdo + arrastrar) |
|---|---|
| **Eje** (flecha) | Mueve la selección a lo largo del eje; escribes la distancia |
| **Toroide** (anillo) | Rota alrededor del eje perpendicular; salta cada 90°, con **Mayús** cada 15° |
| **Plano de herramientas** | Mueve la selección dentro del plano |
| **Origen** (botón central) | Reposiciona el volante; pulsarlo lo despliega entero |
| **Botón del eje** | Reorienta el eje hacia un punto significativo |
| **Ctrl + arrastrar** | Mueve una **copia** de la selección |

- **Exposición progresiva:** con una sola cara seleccionada sólo aparece el eje principal.
- **Intro** termina el movimiento y **Esc** lo cancela.
- La tecla **V** abre el panel *Intención de diseño – Avanzada*, y **Ctrl+E** el Administrador de soluciones.
- Existe también un **controlador de volante 2D** para bocetos.
- En Conjunto, **Mover con el controlador de volante** mueve componentes.

### 2.5 Panel Intención de diseño (antes Live Rules) `[doc]`

Aparece al modificar un modelo síncrono. Muestra las relaciones de cara que se conservarán: coplanar, concéntrico, tangente, simétrico (**Ctrl+Y** = simetría local) y otras. Se desmarcan las que no se quieren respetar y el movimiento se confirma con **Intro**. En versiones ST (ST1–ST9) este mecanismo se llamaba «Live Rules» `[fuente secundaria — conocimiento general, no verificado en la ayuda 2024]`, y en español, «reglas vivas» `[traducción probable]`. Si el usuario o un tutorial dicen «Live Rules», se refieren a este panel.

---

## 3. Anatomía de la ventana

| # | Elemento (ES) | EN | Dónde está | Para qué sirve |
|---|---|---|---|---|
| 1 | **Menú Archivo** (pestaña Archivo) | File menu / Application menu | Primera pestaña de la cinta | Nuevo, Abrir, Guardar, Guardar como, **Empaquetar proyecto**, Imprimir, Información (propiedades, materiales), **Ajustes > Opciones**, **Personalizar**, **Temas**. Vuelves al documento pulsando otra vez Archivo o cualquier pestaña `[doc]` |
| 2 | **Barra de herramientas Acceso rápido** | Quick Access Toolbar | Arriba a la izquierda | Comandos a un clic (Guardar, Deshacer…). Se personaliza **por entorno**; se guarda en `<Tema>QATCustom.xml` y se conserva entre versiones `[doc]` |
| 3 | **Cinta de comandos** | Ribbon | Arriba | Pestañas → grupos → comandos. Algunas pestañas son contextuales. **Alt** muestra las letras de acceso. Se puede minimizar `[doc]` |
| 4 | **Buscador de comandos** | Command Finder | **Arriba a la derecha** (2024; antes en la barra de estado) | Busca por nombre o por capacidad, **también con términos de otros CAD** («fillet», «mate»…). Localiza el comando en la cinta, abre su ayuda o lo ejecuta. «Mostrar correspondencias fuera del entorno» busca en otros entornos `[doc]` |
| 5 | **Pestañas de documento** | Document tabs | Debajo de la cinta | Un documento abierto por pestaña. **Ctrl+Tab** cambia de documento `[inferido]` / Ver > Ventana > Cambiar entre ventanas `[doc]` |
| 6 | **BarraDeAvisos** | PromptBar | Debajo de la cinta, acoplable | Indica **qué espera el comando ahora** («seleccione una cara…»). Se puede agrandar la letra y pasarla a varias líneas. **Es lo primero que se lee cuando algo no avanza** `[doc]` |
| 7 | **PathFinder** | PathFinder | Panel a la izquierda (flotante o acoplado) | Árbol del documento: operaciones, bocetos, planos y sistemas de coordenadas (Pieza); componentes y **relaciones** (Conjunto). Seleccionar, mostrar u ocultar, suprimir, renombrar, reordenar, **Ir a** (*rollback*), editar. Tiene una pestaña **Reproducción de operaciones** `[doc]` |
| 8 | **Barra de comandos** (vertical) | Command bar (vertical, VCB) | Por defecto a la derecha de PathFinder, pegada arriba en la ventana gráfica | Opciones del comando activo agrupadas (Pasos, Formato, Propiedades…), con un **selector** que dice cuántos elementos llevas y una **casilla verde** cuando el paso está completo. Su posición se recuerda entre sesiones. Desde 2024 casi todos los comandos usan la vertical `[doc]` |
| 9 | **Barra de comandos de selección** (antes QuickBar) | Command bar overview (QuickBar) | Al seleccionar geometría | Propone la acción por defecto según lo seleccionado; por ejemplo, una región de boceto ofrece **Extrudir** (agregar o quitar) y Revolución `[doc]` |
| 10 | **Barra de herramientas de contexto** | Context toolbar | En la punta del cursor al seleccionar | Comandos frecuentes para el elemento seleccionado (líneas, cotas, vistas de dibujo, planos…). Se desvanece al alejar el cursor; **Ctrl+G** la vuelve a mostrar. Desde 2025 sale también con **clic derecho** en Plano, Pieza ordenada y Conjunto `[doc]` + `[fuente secundaria]` |
| 11 | **Menú radial** | Radial menu | **Mantener** pulsado el botón derecho | Menú circular con los comandos del entorno; se arrastra hasta la cuña y se suelta. Personalizable `[doc]` |
| 12 | **Menú contextual** | Shortcut menu | **Clic** derecho | Comandos según dónde esté el cursor y qué haya seleccionado; también **reinicia** el comando `[doc]` |
| 13 | **Cubo de vista rápida** | Quick View Cube | Esquina de la ventana gráfica | Orientar haciendo clic en caras, aristas y esquinas, y botón Inicio (ISO) `[doc]` |
| 14 | **Barra de estado** | Status bar | Abajo | Mensajes y, a la derecha, zoom, ajustar, encuadre, rotar, **estilos de vista**, **Orientación de la vista** (vistas guardadas) y **corredera de zoom** `[doc]` |
| 15 | **Comandos de predicción** (IU adaptable) | Predictive commands (Adaptive UI) | Barra flotante bajo la cinta | Aprende el uso y propone los comandos siguientes. Clic derecho > «Muéstrame» (dónde está en la cinta). Se activa o desactiva en Opciones > Ayudas `[doc]` |
| 16 | **Paneles / ventanas acoplables** | Panes / docking windows | Ver > Mostrar > Paneles | Biblioteca de piezas, Capas, Sensores, Variables… con flechas de acople `[doc]` |
| 17 | **Discovery Center** / página de inicio | Discovery Center | Al arrancar | Tutoriales, pruebas y aprendizaje. La pestaña Abrir lista los recientes y los anclados `[doc]` |
| 18 | **Design Copilot** (2026) | Design Copilot | Asistente dentro de la aplicación | Respuestas de ayuda en lenguaje natural, con contexto `[fuente secundaria]`. Ubicación exacta sin verificar `[inferido]` |

**Cursores:** el cursor cambia según lo que espera el comando y avisa cuando hay QuickPick disponible (§5) `[doc]`.

**Temas** `[doc]`: el tema por defecto es **Equilibrado**; se cambia en Archivo > Ajustes > Temas. La configuración de colores de la aplicación es Claro o Medio en 2024, y **Oscuro** desde 2026 (Opciones > **Ayudas**) `[fuente secundaria]`.

---

## 4. La cinta por entorno: pestañas, grupos y comandos

> Nombres en español tomados de las rutas «pestaña → grupo → comando» que cita la ayuda 2024 en español `[doc]`. Los grupos pueden cambiar de orden o nombre entre versiones, y algunos aparecen sólo en síncrono o sólo en ordenado. Si no aparece, **Buscador de comandos**.

### 4.1 Pestañas en Pieza y Chapa

| Pestaña ES | EN | Contenido |
|---|---|---|
| **Inicio** | Home | El 90 % del modelado: boceto, sólidos, patrones, planos, modificar `[doc]` |
| **Abocetar** | Sketching | Dibujo 2D, relaciones, cotas, IntelliSketch, insertar imagen o texto `[doc]` |
| **Superficies** | Surfacing | Curvas y superficies: BlueSurf, barrido, limitada, recortar… `[doc]` |
| **PMI** | PMI | Cotas y anotaciones 3D, vistas de modelo, PDF 3D `[doc]` |
| **Verificar** | Inspect | Medir, propiedades físicas, interferencias, análisis de curvatura `[doc]` |
| **Herramientas** | Tools | Asistentes, entornos (ERA, Motion…), variables, modelo, transformar `[doc]` |
| **Ver** | View | Paneles, estilos, orientación, recorte, ventanas `[doc]` |
| Contextuales / por licencia | — | Simulación, Impresión 3D, Ingeniería inversa, Diseño generativo, Teamcenter `[doc]` |

### 4.2 Pestaña Inicio (Pieza) — grupos y comandos

| Grupo ES / EN | Comandos ES (EN) | Para qué |
|---|---|---|
| **Portapapeles** / Clipboard | Pegar, Cortar, Copiar, **Copia de pieza** (Part Copy), **Copia asociativa entre piezas** (Inter-Part Copy), Pegado especial, Copiar en biblioteca `[doc]` | Reutilizar geometría entre archivos |
| **Seleccionar** / Select | **Seleccionar** (Select), lista Seleccionar (filtros y prioridades), **Modo Administrador de selecciones**, Cercado poligonal `[doc]` | Herramienta de selección. En síncrono, seleccionar una región crea la operación directamente |
| **Boceto** / Sketch | **Boceto** (Sketch), Boceto 3D, Copiar boceto, Desprender de boceto (Tear-Off Sketch) `[doc]` | Boceto ordenado sobre un plano o cara |
| **Dibujo** / Draw | Línea (Line), Rectángulo por centro, Círculo, Arco, Curva, Construcción, **Proyectar en boceto** (Project), Desplazamiento simétrico, Recortar (Trim), Extender hasta siguiente, Recortar esquina, Chaflán, **Eje de revolución** (Axis of Revolution, grupo «Dibujar» en perfiles ordenados) `[doc]` (Círculo/Arco `[inferido]`) | Geometría 2D |
| **Relacionar** / Relate | Conectar, Concéntrico, Horizontal/Vertical, Colineal, Paralela, Perpendicular, Tangente, Igual, Simétrico / Eje de simetría, Bloquear, Conjunto rígido, **Asistente de relaciones**, Controladores de relaciones `[doc]` | Relaciones geométricas |
| **Cota** / Dimension | **Cota inteligente** (Smart Dimension), **Distancia entre**, Ángulo entre, Cota de coordenadas, Recuperar cotas, Estilos `[doc]` | Cotas que conducen el boceto |
| **Sólidos** / Solids | **Extrudir** (Extrude), **Cortar** (Cut), **Revolución** (Revolve), Corte por revolución (Revolved Cut), lista **Barrido** (Protrusión / Vaciado por barrido), **Por secciones** (Lofted Protrusion / Cutout), Helicoidal (Helix), **Agujero** (Hole), Ranura (Slot), Roscas (Thread), **Redondeo** (Round), **Chaflán** (Chamfer), Combinación (Blend), **Desmoldeo** (Draft), lista **Pared fina** (Thin Wall: **Dar espesor**, Dar espesor en región, Incrementar espesor, Refuerzo (Rib), Red de refuerzos (Web Network), Resalte de montaje (Mounting Boss), Abertura (Vent)…), **Agregar cuerpo** (Add Body), primitivas Cuadro / Cilindro / Esfera `[doc]` | Operaciones de sólido |
| **Patrón** / Pattern | **Patrón** (Rectangular / Circular), **A lo largo de la curva** (Along Curve), Patrón según tabla, **Patrón de relleno** (Fill Pattern), **Simetría** (Mirror) `[doc]` | Repetir y simetrizar |
| **Modificar** / Modify (síncrono) | **Mover caras**, Rotar caras, Desplazamiento (Offset Faces), Eliminar caras, Cambiar tamaño de agujeros, Escala, Dividir, Puente, Rellenar `[doc]` | Edición directa |
| **Planos** / Planes (también «Referencia») | **Plano coincidente** (Coincident Plane), **Más planos** (paralelo, angular, perpendicular a curva, por 3 puntos, tangente), **Sistema de coordenadas** `[doc]` | Geometría de referencia |
| **Sección** / Section | **Sección activa** (Live Section) `[doc]` | Corte dinámico del modelo |
| **Orientar** / Orient | Ajustes del Cubo de vista rápida `[doc]` | — |
| **Cerrar** / Close | **Cerrar boceto** (Close Sketch), Cerrar boceto 3D… `[doc]` | Salir del subentorno |

**Detalle útil del comando Extrudir** `[doc]`:
- En síncrono, la operación base necesita una región de boceto **cerrada**.
- Para las operaciones siguientes valen bocetos abiertos o caras planas.
- Con la opción **Automática**, el lado del boceto donde está el cursor decide si añade o quita material.
- En ordenado, Extrudir construye «una protrusión o un vaciado». Con varios perfiles, todos deben estar cerrados.

### 4.3 Pestaña Inicio en Chapa — grupo **Chapa** (Sheet Metal) `[doc]`

| Comando ES | EN |
|---|---|
| **Cara** | Tab (operación base plana) |
| **Pestaña** | Flange |
| **Pestaña por contorno** | Contour Flange |
| **Pestaña por secciones** | Lofted Flange |
| **Pestaña multiborde** | Multi-Edge Flange |
| **Plegado** / Desplegar / Volver a plegar | Bend / Unbend / Rebend |
| **Pestaña doble** | Jog |
| **Cerrar esquina de 2 / 3 plegados** | Close 2-Bend / 3-Bend Corner |
| **Recortar esquina** | Break Corner |
| **Embutición**, Embutición con vaciado, **Celosía**, Refuerzo, Refuerzo en cruz, Refuerzo en ángulo | Dimple, Drawn Cutout, Louver, Bead, Cross Brake, Gusset |
| **Vaciado perpendicular** | Normal Cutout |
| **Chapa desarrollada** (en Herramientas > Modelo) | Flat Pattern |

El detalle completo está en el capítulo 02.

### 4.4 Conjunto (`.asm`)

| Pestaña / grupo ES | EN | Comandos ES (EN) |
|---|---|---|
| Inicio > **Ensamblar** | Home > Assemble | **Insertar componente** (Insert Component), **Ensamblar** (Assemble, con **FlashFit**), **Coincidir** (Mate), **Alineación plana** (Planar Align), **Alineación axial** (Axial Align), **Insertar** (Insert), Conectar (Connect), Ángulo (Angle), Tangente, Leva (Cam), Trayectoria (Path), Paralela, **Engranaje** (Gear), Coincidir sistemas de coordenadas, **Plano central** (Center-Plane), Conjunto rígido (Rigid Set), **Anclar** (Ground), Guardar ajuste (Capture Fit) `[doc]` |
| Inicio > **Componentes** | Components | **Crear pieza en posición** (Create Part In-Place) `[doc]` |
| Inicio > **Modificar** | Modify | **Arrastrar componente** (Drag Component), Mover componentes, **Sustituir pieza** (Replace Part), Transferir, Dispersar `[doc]` |
| Inicio > **Patrón** | Pattern | Patrón (de componentes), **Simetría de componentes** (Mirror Components) `[doc]` |
| Inicio > **Configuraciones** | Configurations | **Configuraciones de visualización**, Administrador de configuraciones, Tomar instantánea `[doc]` |
| Inicio > **Motores** | Motors | Motor rotacional, Motor de tabla de variables, **Simular motor** `[doc]` |
| **Operaciones** (pestaña) | Features | Operaciones de conjunto: Agujero, Vaciado, Vaciado por revolución, Redondeo, Sustraer, soldaduras; Patrón; Planos; Boceto `[doc]` |
| Verificar > **Evaluar** | Inspect > Evaluate | **Comprobar interferencia** (Check Interference), Estadísticas del conjunto, **Reparar archivos que faltan** `[doc]` |
| Herramientas > **Entornos** | Tools > Environs | **ERA**, **Motion**, Engineering Reference, Solid Edge 3D Publishing `[doc]` |
| Herramientas > **Asistentes** | Assistants | Asistente de relaciones (de conjunto), Informes, **Asistente de Gestor de diseños** `[doc]` |

- **Panel Biblioteca de piezas** (Parts Library): desde aquí se **arrastran** las piezas al conjunto. Su opción **Mantener relaciones** viene activada `[doc]`.
- **PathFinder de Conjunto**: arriba los componentes, abajo las **relaciones** del componente seleccionado. Se pueden editar, suprimir o eliminar `[doc]`.
- La **1.ª pieza queda anclada automáticamente** `[doc]`.

### 4.5 Plano (`.dft`)

| Grupo (pestaña Inicio) ES | EN | Comandos ES (EN) |
|---|---|---|
| **Vistas de dibujo** | Drawing Views | **Asistente de vistas** (View Wizard), **Vista principal** (Principal View), Vista auxiliar, **Plano de corte** (Cutting Plane), **Vista en corte** (Section View), **Detalle**, **Corte parcial** (Broken-Out), Vista rota, **Actualizar vistas**, Paleta de vistas del modelo `[doc]` |
| **Cota** | Dimension | Cota inteligente, Distancia entre, **Recuperar cotas** (Retrieve Dimensions), Cota de coordenadas automática, Estilos `[doc]` |
| **Anotación** | Annotation | **Llamada** (Callout), **Referencia de elemento** (Balloon), **Línea de centro**, **Marca de centro**, Líneas de centro automáticas, Texto, Estado de borde, Requisitos técnicos `[doc]` |
| **Tablas** | Tables | **Lista de piezas** (Parts List), Tabla de bloques, tabla de agujeros `[doc]` |
| **Texto de propiedades** | Property Text | Actualizar todo, Convertir todo `[doc]` |
| Pestaña Ver > **Vistas de hoja** | View > Sheet Views | **Fondo** (Background: hojas de fondo con marco y rotulación), Hojas de trabajo, Modelo 2D `[doc]` |

La plantilla de partida es **ISO Metric Draft** `[doc]`. El flujo completo de planos está en el capítulo 04.

### 4.6 Entorno ERA (Explosionado-Renderizado-Animación)

- **Entrar:** desde el conjunto, **Herramientas > Entorno(s) > ERA** `[doc]`.
- **Inicio > Explosionar:** **Explosionado automático** (Auto Explode) y **Explosionar** (manual) `[doc]`.
- **Inicio > Modificar:** Quitar explosionado, Vincular, Reposicionar, Dispersar `[doc]`.
- **Inicio > Animar:** Editor de animaciones `[doc]`.
- **Configuraciones:** la vista explosionada se **guarda como configuración**, y las configuraciones explosionadas **sólo se editan en ERA** `[doc]`.
- **Salir:** **Cerrar ERA** `[doc]`.
- **PathFinder de explosionado:** muestra los grupos de piezas `[doc]`.
- El explosionado automático se guía por las relaciones: las piezas con **Alineación axial** se separan a lo largo del eje `[doc]`.

---

## 5. Selección: QuickPick, filtros, cercados y puntos significativos

| Herramienta ES | EN | Uso |
|---|---|---|
| **QuickPick** | QuickPick | Detén el cursor sobre la zona; cuando cambia al aviso de QuickPick, **clic derecho**. Sale una lista con un elemento por fila; al pasar por encima se resalta y al pulsar se selecciona. En Opciones de QuickPick se puede cambiar a botón izquierdo `[doc]` |
| **Cercado** | Fence | Arrastra una caja para seleccionar. **Alt+clic** inicia un cercado poligonal; **Alt+clic+arrastrar**, uno de lazo `[doc]` |
| **Mayús / Ctrl + clic** | — | Añadir o quitar de la selección `[doc]` |
| **Ctrl+A** | — | Seleccionar todos los elementos 2D del boceto `[doc]` |
| **Modo Administrador de selecciones** | Selection Manager Mode | **Mayús+Barra espaciadora**: selecciones avanzadas (cadenas, caras conectadas, operaciones…) `[doc]` |
| **SmartSelect** | SmartSelect | Selecciona elementos parecidos (caras del mismo radio, agujeros iguales…) `[doc]` |
| **Lista Seleccionar** (filtro) | Select list / Selection Filter | Inicio > Seleccionar: prioridad de cara, de borde o de vértice, y tipos. **Ctrl+Barra espaciadora** recorre los filtros `[doc]` (en contexto de subdivisión; extensible `[inferido]`) |
| **Buscar componentes** | Find Components | En conjunto, seleccionar componentes por criterio `[doc]` |
| **Puntos significativos** | Keypoints | Con el elemento bajo el cursor: **M** punto medio, **I** intersección, **C** centro, **E** extremo («mice»). Sin distinguir mayúsculas. En operaciones, **K** activa M/C/E sobre el volante `[doc]` |

---

## 6. Ver y orientar el modelo

**Estilos de vista** `[doc]`: Ver > Estilo > paleta **Estilos de vista**. Opciones: Jaula de alambre (Wireframe), Bordes visibles, Bordes visibles y ocultos, **Sombreado** (Shaded) y **Sombreado con bordes visibles**. También Sombra proyectada (Drop Shadow), Reflexión del suelo, **Perspectiva** y Sustituciones de vista (Renderizado).

**Orientación** `[doc]`:
- **Orientación de la vista** (View Orientation), abajo a la derecha en la barra de estado: galería de vistas predefinidas con vista previa en vivo. Desde ahí se abre **Vistas guardadas** (Saved Views), que guarda orientación y zoom con un nombre. Sirven después para animaciones de conjunto.
- **Cubo de vista rápida**: cara = vista ortogonal, arista = vista a 45°, esquina = isométrica, flechas de giro, botón Inicio = ISO. Si se cierra, se reactiva en Inicio > Orientar > Ajustes del Cubo de vista rápida.
- **Ver cara** (Look at Face): pone una cara paralela a la pantalla.
- **Vista de boceto** (Sketch View, **Ctrl+H**): mira de frente al plano de boceto bloqueado.
- **Girar alrededor** (Spin About), **Rotar**, Vista anterior y Actualizar vista: grupo Ver > Orientar.
- **Ajustar** (Fit): **Ctrl+Ajustar** ajusta al área que no tapan PathFinder ni la barra de comandos.
- **Planos de recorte**: Ver > Recortar > Establecer planos / Activar recorte, para limitar la profundidad visible.
- **Sección activa**: Inicio > Sección.

---

## 7. Atajos de teclado y de ratón

### 7.1 Ratón `[doc]`

| Acción | Efecto |
|---|---|
| Clic izquierdo | Seleccionar o colocar. Doble clic activa un objeto vinculado o incrustado |
| Arrastrar con el izquierdo | Cercado o arrastrar elemento |
| **Clic derecho** | Menú contextual; **reinicia o acepta** el comando. En muchos pasos, clic derecho = «aceptar / terminar» (por ejemplo, crear la Cara en chapa) |
| **Mantener el derecho** | **Menú radial** |
| Clic derecho con el aviso de QuickPick | Lista QuickPick |
| **Arrastrar con el botón central** | **Rotar** la vista (alrededor del centro del modelo) |
| Clic central sobre vértice / arista / cara | Fija el punto o eje de rotación; clic en vacío lo borra. **Alt** + central cancela |
| **Mayús + arrastrar central** | **Encuadre** (pan) |
| **Rueda** | Zoom. Si Opciones > General > «Habilitar cambios de valor usando la rueda del ratón» está activa, la rueda cambia valores y el zoom pasa a **Ctrl+rueda** |
| **Alt + arrastrar central** | Zoom de área |
| **Doble clic central** | **Ajustar** todo |
| Ctrl + clic izquierdo (Ensamblar/FlashFit) | Rota la pieza no restringida `[doc]` |

### 7.2 Teclado — vistas `[doc]`

| Vista ES | EN | Atajo |
|---|---|---|
| Planta | Top | **Ctrl+T** |
| Alzado | Front | **Ctrl+F** |
| Derecha | Right | **Ctrl+R** |
| Izquierda | Left | **Ctrl+L** |
| Inferior | Bottom | **Ctrl+B** |
| Posterior (trasera) | Back | **Ctrl+K** |
| Isométrica | Isometric | **Ctrl+I** |
| Dimétrica | Dimetric | **Ctrl+J** |
| Trimétrica | Trimetric | **Ctrl+M** |
| Normal al plano de boceto bloqueado | Sketch view | **Ctrl+H** |
| Acercar / alejar | Zoom in / out | **Ctrl+↑ / Ctrl+↓** (también Ctrl+← / Ctrl+→) |
| Encuadrar | Pan | **Mayús+Ctrl+flechas** |
| Herramienta de zoom (sólo Plano) | Zoom tool | **Alt+Z** |

### 7.3 Teclado — modelado y boceto `[doc]` salvo indicación

| Atajo | Efecto |
|---|---|
| **Esc** | Cancelar el comando o la operación; vuelve a Seleccionar |
| **Intro** | Confirmar (por ejemplo, un movimiento síncrono) |
| **F3** | Bloquear o desbloquear el plano de boceto |
| **F5** | Limpiar la visualización de puntos clave (también refrescar `[inferido]`) |
| **F8 / F9** | Ordenado: reposicionar la cuadrícula / activar el ajuste a cuadrícula |
| **F12, Alt+X, Alt+Y** | Introducir coordenadas X/Y de la cuadrícula |
| **M, I, C, E** | Ajustar a medio, intersección, centro y extremo |
| **S** (sobre el punto medio de una línea) | Dibujar la línea simétricamente |
| **Alt + arrastrar** | Suspender o quitar relaciones reconocidas al mover un elemento de boceto |
| **Ctrl+C / Ctrl+X / Ctrl+V** | Copiar, cortar y pegar elementos de boceto. **Ctrl+arrastrar** copia |
| **Ctrl+G** | Volver a mostrar la barra de herramientas de contexto |
| **Ctrl+E** | Administrador de soluciones (síncrono) |
| **V** | Panel Intención de diseño – Avanzada |
| **Ctrl+Y** | Simetría local en Intención de diseño ⚠️ no es «rehacer» en ese contexto |
| **Mayús+Barra espaciadora** | Modo Administrador de selecciones |
| **Ctrl+Barra espaciadora** | Recorrer los filtros de selección |
| **Alt** | Letras de acceso de la cinta |
| **F1** | Ayuda del comando bajo el cursor |
| **Mayús+F9 / Mayús+F10** | Grabar vídeo / parar la grabación |
| **Ctrl+Z, Ctrl+S, Ctrl+N, Ctrl+O, Ctrl+P** | Deshacer, guardar, nuevo, abrir e imprimir: estándar de Windows `[inferido]` |

**Lista completa y oficial:** Personalizar (flecha de la barra Acceso rápido) > pestaña **Teclado** > «Seleccionar comandos de: Todas las asignaciones del teclado» > **Imprimir** `[doc]`. La Tarjeta de referencia rápida (`qrc.pdf`) de la ayuda trae los atajos de síncrono `[doc]`.

---

## 8. Opciones de Solid Edge: lo que importa

**Abrir:** **Archivo > Ajustes > Opciones** `[doc]`. Desde 2024 el cuadro tiene **buscador** de ajustes `[doc]`. Algunas páginas cambian según el entorno activo (Pieza, Conjunto, Plano) `[doc]`.

| Página / pestaña ES | EN | Ajustes clave |
|---|---|---|
| **Ayudas** | Helpers | Página de inicio. **Entorno inicial de Pieza y Chapa (síncrono u ordenado)**. Plantillas predeterminadas y opciones de creación. **Configuración de colores de la aplicación** (Claro/Medio; **Oscuro** en 2026 `[fuente secundaria]`). **PathFinder acoplable**. Sugerencias de comandos. Tamaño del volante y del cubo. **Comandos de predicción** `[doc]` |
| **General** | General | Mostrar unidades en los campos. Tamaño de los planos de referencia. **Pedir material en documentos nuevos**. **Pasos de deshacer**. Archivos recientes (hasta 100). Edición dinámica de perfiles. Rueda del ratón para valores. «Indicar perfiles infrarrestringidos en PathFinder» `[doc]` |
| **Unidades** | Units | Sistema (MMKS…), unidades base y derivadas, precisión: **del archivo activo** `[doc]` |
| **Ubicación de los archivos** | File Locations | Plantillas, biblioteca, **archivo de gestión de vínculos** `LinkMgmt.txt`, caché `[doc]` |
| **Perfil de usuario** | User Profile | Nombre de usuario (va a las propiedades), Foco de atención `[doc]` |
| **Colores** | Colors | Colores del fondo y del resaltado, y **colores de estado de relación de boceto** `[doc]` |
| **Vista / Ver** | View | Visualización 3D `[doc]` |
| **Guardar** | Save | Recordatorio de guardado `[doc]` |
| **Asociaciones entre piezas** | Inter-Part | Permitir vínculos asociativos entre piezas `[doc]` |
| **Conjunto** | Assembly | Comportamiento de colocación y sustitución de piezas (soluciones por IA para Reemplazar pieza) `[doc]` |
| **Normas de dibujo**, **Estilo de cota**, **Anotación**, **Visualización de bordes** | Drawing Standards… | Plano: proyección (1.er/3.er diedro), estilos `[doc]` |
| **Administrar** | Manage | Gestión de datos de Solid Edge o Teamcenter `[doc]` |
| **Privacidad de datos** | Data Privacy | Telemetría (2024+) `[doc]` |

**Personalizar** (Archivo > Personalizar, o la flecha de la barra Acceso rápido) `[doc]`:
- Pestañas **Cinta**, **Acceso rápido**, **Teclado**, **Menú radial** y **Distribución**.
- Los cambios se hacen **por entorno**.
- Hay «Restaurar» para volver a los valores de fábrica.

**Migrar ajustes entre versiones:** Asistente de configuración y preferencias, que captura y despliega los ajustes en un archivo cifrado `[doc]`. En 2026 también se restauran desde la nube con licencia de usuario nominal `[fuente secundaria]`.

---

## 9. Flujo de un proyecto y gestión de archivos vinculados

### 9.1 Orden recomendado (proyecto de curso)

1. **Una carpeta por proyecto** y todo dentro: piezas, subconjuntos, conjunto, planos. Solid Edge guarda en cada documento contenedor **referencias (vínculos)** a los archivos que usa `[doc]`. Mantener todo junto evita la mayoría de los vínculos rotos `[inferido]`.
2. **Piezas** (`.par`/`.psm`): plantilla ISO métrica, modo ordenado, material y propiedades rellenas, nombre definitivo **desde el primer guardado** (renombrar después rompe vínculos, §9.3).
3. **Conjunto** (`.asm`): Insertar componente (o arrastrar desde la Biblioteca de piezas). La 1.ª pieza queda anclada y las demás se relacionan. Después **Comprobar interferencia** y Arrastrar componente / Simular motor.
4. **Explosionado**: Herramientas > ERA > Explosionado automático y ajustes > **guardar la configuración** > Cerrar ERA.
5. **Planos** (`.dft`): Asistente de vistas desde la pieza o el conjunto. En el conjunto, vista con la **configuración explosionada**, **Referencias de elemento** (globos) y **Lista de piezas**. La rotulación se toma de las propiedades. Al final, Guardar como PDF.
6. **Empaquetar proyecto** para entregar (§9.2).

Cada etapa depende de la anterior: los planos son **asociativos**. Si cambia el modelo, las vistas se marcan desactualizadas y se pulsa **Actualizar vistas** `[doc]`.

### 9.2 Empaquetar proyecto (Pack and Go) `[doc]`

- Está en **Archivo > Empaquetar proyecto**.
- Copia **el conjunto completo de documentos relacionados** (subconjuntos, piezas y, si se quiere, planos y resultados) a una **carpeta o a un `.zip`**, para compartirlo dentro o fuera de la organización.
- Viene activado por defecto; un administrador puede desactivarlo con SEAdmin.
- **Es la forma correcta de entregar un proyecto al profesor o de llevarlo a otro PC** `[inferido]`.

### 9.3 Mover, renombrar y archivos que faltan

- **No renombrar ni mover piezas con el Explorador de Windows** si ya están usadas en un conjunto o un plano. El contenedor sigue buscando la ruta antigua `[inferido, coherente con la ayuda]`.
- **Gestor de diseños** (Design Manager), antes «Administrador de revisiones» (Revision Manager) `[fuente secundaria]`. Hace Guardar como, **Mover**, **Renombrar**, Sustituir y Revisar **actualizando las referencias** de toda la jerarquía. Se trabaja marcando la acción en la lista y luego **Inicio > Acción > Realizar acciones**. También está el **Asistente de Gestor de diseños** (Herramientas > Asistentes) `[doc]`.
- **Reparar archivos que faltan** (Verificar > Evaluar) `[doc]`:
  - Se abre **solo** al abrir un conjunto con archivos que no encuentra.
  - Se añaden carpetas a «Buscar en», se ordenan por prioridad y se pulsa **Buscar y sustituir**: busca de forma recursiva y toma la **primera** coincidencia válida.
  - También permite Sustituir pieza / con pieza nueva.
  - Sólo funciona en el conjunto principal.
  - El orden de búsqueda de vínculos al abrir lo define `LinkMgmt.txt` (Opciones > Ubicación de los archivos).
- **Vínculos interrumpidos** (Herramientas > Buscar, o clic derecho en el Explorador): genera un `.txt` con los archivos que tienen vínculos rotos `[doc]`.
- **Dónde se ha usado** (Where Used): qué conjuntos o planos usan un archivo `[doc]`.

### 9.4 Versiones de archivo y licencia académica

- **Hacia delante sí, hacia atrás no:** una versión nueva abre archivos de cualquier versión anterior con núcleo Parasolid (desde V5). **Una versión antigua no abre archivos guardados en otra más nueva** y no existe «guardar como versión anterior» `[fuente secundaria — KB Siemens PL8007905, PL8001999]`. Para pasar geometría a una versión vieja sólo queda exportar a formato neutro (STEP, Parasolid `.x_t`), que llega **sin historial** `[fuente secundaria]`.
- ⚠️ Un archivo de 2024 abierto y **guardado** en 2026 ya no abre en 2024 `[inferido]`. Si la universidad tiene una versión distinta a la del usuario, se acuerda la versión antes de entregar.
- **Licencia Academic/Student:** los archivos creados con licencia académica quedan **marcados**. Se abren en otra licencia académica, pero **no en Solid Edge comercial**. Los archivos comerciales sí se abren en la académica. Los planos llevan **marca de agua** según la licencia `[fuente secundaria — KB Siemens PL8506730; página Student Edition]`.
- La carpeta de registro y anotaciones va por versión (`Version 224` = 2024 `[doc]`; por extensión `Version 226` = 2026 `[inferido]`).

---

## 10. Conceptos CAD transferibles

### 10.1 Intención de diseño

Construir el modelo para que **cambie como cambiaría la pieza real**:
- Acotar desde los datos de fabricación (aristas de referencia, ejes).
- Usar simetría con los planos base.
- Agujeros con el comando Agujero, para que lleven norma y rosca.
- Redondeos al final.

En ordenado, la intención vive en el **orden de operaciones, las referencias y las cotas**. En síncrono, en las **relaciones de cara** (panel Intención de diseño) y en las **cotas 3D bloqueadas** `[doc]`/`[inferido]`.

### 10.2 Árbol de historial (PathFinder, ordenado) `[doc]`

- Las operaciones se calculan **de arriba abajo**: cada una depende de las anteriores (antecesores y dependientes).
- **Ir a** devuelve el modelo a ese punto (*rollback*), **Insertar una operación** la mete en medio, **Suprimir** la desactiva sin borrarla, **Reordenar** la arrastra y **Recalcular** la regenera.
- La **pestaña Reproducción de operaciones** reproduce la construcción paso a paso (Rebobinar, Reproducir, Incremento, Parar).
- Símbolos en PathFinder: operación suprimida, **operación con problema** (el detalle está en la BarraDeAvisos), ejecución sin éxito, operación revertida, **origen flotante** (la cara de colocación ya no existe; se arregla con clic derecho > Reposicionar operación) y **boceto con perfiles infrarrestringidos**.
- **Asistente de errores** (Herramientas > Asistentes) lista y repara las operaciones con fallos.

### 10.3 Grados de libertad y restricciones

- **Boceto:** un elemento 2D tiene grados de libertad de posición, tamaño y orientación. **Relaciones** (geométricas) + **cotas** (dimensionales) los eliminan. Un boceto **totalmente definido** no se deforma al editarlo. El comando **Colores de relaciones** pinta los elementos según su grado de libertad (en ordenado 2D: Verificar > Evaluar), y los colores se configuran en Opciones > Colores. Sin él, todos los elementos se ven azules `[doc]`.
- **Relaciones geométricas** (ES / EN) `[doc]`: Conectar (Connect, 1 o 2 GDL), Colineal (Collinear), Concéntrico (Concentric), Igual (Equal), Horizontal/Vertical, Tangente (Tangent; también con igual curvatura), Simétrico (Symmetric), Paralela (Parallel), Perpendicular, Acuerdo, Chaflán, Vínculo, **Bloquear** (Lock), **Conjunto rígido** (Rigid Set). **IntelliSketch** las propone mientras se dibuja y el **Asistente de relaciones** las añade después.
- **Conjunto:** una pieza libre tiene **6 GDL** (3 traslaciones y 3 rotaciones). Cada relación de conjunto quita algunos: Coincidir quita 3 (1 traslación y 2 rotaciones), Alineación axial quita 4, Insertar quita 5 `[inferido — cinemática general]`. Un mecanismo queda **subdefinido a propósito** para poder moverse. Las relaciones redundantes sobredefinen y dan error.
- **Relaciones de conjunto** (lista oficial) `[doc]`: FlashFit, Coincidir (Mate), Alineación plana (Planar Align), Alineación axial (Axial Align), Insertar (Insert), Conectar (Connect), Ángulo, Tangente, Leva (Cam), Trayectoria (Path), Paralela, Engranaje (Gear), Coincidir sistemas de coordenadas, Plano central (Center-Plane), Conjunto rígido (Rigid Set), Anclar (Ground).

### 10.4 Referencias `[doc]`

- **Planos de referencia base:** Planta (xy), Derecha (yz) y Alzado (xz), en el origen. Se muestran u ocultan en PathFinder.
- **Planos globales:** coincidentes, paralelos, angulares, perpendiculares a una curva, por 3 puntos o tangentes. En ordenado se recomienda apoyarlos en geometría estable `[inferido]`.
- **Sistema de coordenadas base** y sistemas adicionales (comando Sistema de coordenadas, síncrono y ordenado). En conjunto se puede posicionar con «Coincidir sistemas de coordenadas».

### 10.5 Nomenclatura (buenas prácticas) `[inferido]`

- Archivos: `<proyecto>_<nº>_<nombre>.par`, por ejemplo `CARDAN_03_Cruceta.par`. Sin tildes ni espacios si van a pasar por scripts o por COM. El mismo nombre en el plano: `CARDAN_03_Cruceta.dft`.
- Operaciones: renombrar las importantes en PathFinder (clic derecho > Renombrar `[doc]`), por ejemplo «Base_Ø40», «Agujeros_M6».
- Las propiedades (Título, Autor, Número de documento, Material) se rellenan **siempre**: la Lista de piezas y la rotulación las leen.

---

## 11. Equivalencias con SolidWorks, Inventor, Fusion 360 y CATIA V5

> Equivalencias funcionales. Nombres de otros CAD en inglés (su interfaz original) `[fuente secundaria — conocimiento general de esos productos]`. Truco oficial: el **Buscador de comandos** de Solid Edge acepta el término de la competencia y devuelve el comando equivalente `[doc]`.

### 11.1 Operaciones de pieza

| Solid Edge (ES / EN) | SolidWorks | Inventor | Fusion 360 | CATIA V5 |
|---|---|---|---|---|
| Extrudir → protrusión (Extrude) | Extruded Boss/Base | Extrude (Join) | Extrude (Join) | Pad |
| Cortar / Vaciado (Cut / Cutout) | Extruded Cut | Extrude (Cut) | Extrude (Cut) | Pocket |
| Revolución (Revolve) | Revolved Boss/Base | Revolve | Revolve | Shaft |
| Corte por revolución (Revolved Cut) | Revolved Cut | Revolve (Cut) | Revolve (Cut) | Groove |
| Protrusión por barrido (Swept Protrusion) | Swept Boss/Base | Sweep | Sweep | **Rib** ⚠️ |
| Vaciado por barrido (Swept Cutout) | Swept Cut | Sweep (Cut) | Sweep (Cut) | **Slot** ⚠️ |
| Protrusión por secciones (Lofted Protrusion) | Lofted Boss/Base | Loft | Loft | Multi-sections Solid |
| Vaciado por secciones (Lofted Cutout) | Lofted Cut | Loft (Cut) | Loft (Cut) | Removed Multi-sections Solid |
| Protrusión helicoidal (Helical Protrusion) | Helix curve + Sweep | Coil | Coil | Helix + Rib |
| Redondeo (Round) | Fillet | Fillet | Fillet | Edge Fillet |
| Chaflán (Chamfer) | Chamfer | Chamfer | Chamfer | Chamfer |
| **Dar espesor** (Thin Wall) | Shell | Shell | Shell | Shell |
| Incrementar espesor (Thicken) | Thicken | Thicken/Offset | Thicken | Thick Surface |
| Agujero (Hole) | Hole Wizard | Hole | Hole | Hole |
| Roscas (Thread) | Cosmetic Thread / Thread | Thread | Thread | Thread/Tap |
| **Refuerzo** (Rib) | Rib | Rib | Rib | **Stiffener** ⚠️ |
| Desmoldeo (Draft) | Draft | Face Draft | Draft | Draft Angle |
| Patrón rectangular / circular (Pattern) | Linear / Circular Pattern | Rectangular / Circular Pattern | Rectangular / Circular Pattern | Rectangular / Circular Pattern |
| Simetría (Mirror) | Mirror | Mirror | Mirror | Mirror |
| Plano coincidente / Más planos | Reference Plane | Work Plane | Construction Plane | Plane |
| Boceto (Sketch) | Sketch | Sketch | Sketch | Sketch (Sketcher) |
| Relaciones geométricas | Sketch Relations | Geometric Constraints | Sketch Constraints | Constraints |
| Cota inteligente (Smart Dimension) | Smart Dimension | Dimension | Sketch Dimension | Constraint (dimensional) |
| Mover caras (síncrono) | Move Face (Direct Editing) | Direct Edit | Press Pull / Move | (no equivalente directo) |

⚠️ **Falsos amigos:** en CATIA, *Rib* = barrido que añade y *Slot* = barrido que quita. En Solid Edge, **Refuerzo (Rib)** es un nervio, y **Ranura (Slot)** es una ranura de agujero alargado `[doc para SE]`.

### 11.2 Conjuntos, explosionado y planos

| Solid Edge (ES / EN) | SolidWorks | Inventor | Fusion 360 | CATIA V5 |
|---|---|---|---|---|
| Conjunto `.asm` (Assembly) | Assembly `.sldasm` | Assembly `.iam` | Design con componentes `.f3d` | Product `.CATProduct` |
| Relaciones de conjunto | Mates | Constraints / Joints | Joints | Assembly Constraints |
| **Coincidir** (Mate, caras enfrentadas) | Coincident (anti-aligned) | Mate | Rigid / Planar joint `[inferido]` | Contact / Coincidence |
| **Alineación plana** (Planar Align, mismo sentido) | Coincident (aligned) / Flush | Flush | — `[inferido]` | Coincidence (orientación igual) |
| **Alineación axial** (Axial Align) | Concentric | Mate (ejes) / Insert | Revolute / Cylindrical joint | Coincidence (ejes) |
| **Insertar** (Insert) | Concentric + Coincident | Insert | Revolute joint `[inferido]` | Coincidence + Contact |
| Ángulo / Paralela / Tangente | Angle / Parallel / Tangent | Angle / Tangent | (limits / joint) | Angle / Parallelism / Contact |
| Leva / Trayectoria / Engranaje | Cam / Path / Gear (mechanical mates) | Transitional / Motion constraints | Pin-slot / Motion link | (DMU Kinematics) |
| Plano central (Center-Plane) | Symmetric / Width | (Symmetry) | — | — |
| **Anclar** (Ground) | Fix | Ground | Ground | Fix |
| Conjunto rígido (Rigid Set) | Lock / Make rigid | Rigid joint | Rigid Group | Fix Together |
| ERA: Explosionado automático / Explosionar | Exploded View | Presentation `.ipn` | Animation workspace (Explode) | Explode / Scenes (DMU) |
| Comprobar interferencia | Interference Detection | Analyze Interference | Interference | Clash |
| Simular motor / Motion | Motion Study | Dynamic Simulation | Motion Study / Animate joints | DMU Kinematics |
| Plano `.dft` (Draft) | Drawing `.slddrw` | Drawing `.idw`/`.dwg` | Drawing workspace | Drafting `.CATDrawing` |
| Asistente de vistas / Vista principal | Model View / Standard 3 View | Base View | Base View | View Creation Wizard / Front View |
| Referencia de elemento (Balloon) | Balloon | Balloon | Balloon | Balloon |
| Lista de piezas (Parts List) | Bill of Materials | Parts List | Table (BOM) | Bill of Material |
| Recuperar cotas | Model Items | Retrieve Dimensions | — | Generate Dimensions |

---

## 12. Novedades 2025–2026 que afectan al operario

| Versión | Novedad | Efecto práctico | Etiqueta |
|---|---|---|---|
| 2024 | Barras de comandos **verticales** de texto (FlashFit, Coincidir, cotas, Curva…). Selector con contador y casilla verde en «Pasos» | Leer siempre la barra vertical: indica qué falta | `[doc]` |
| 2024 | PathFinder y VCB **opacos**; **Ctrl+Ajustar** | — | `[doc]` |
| 2024 | Opciones con **buscador**; comando **Crear plano** desde PathFinder; operaciones de conjunto **reordenables** | — | `[doc]` |
| 2024 | **Sustituir pieza** con soluciones propuestas por IA (opción en Opciones > Conjunto) | — | `[doc]` |
| 2025 | VCB rediseñadas y **ocultación automática** de la barra vertical. Barra de contexto con clic derecho en Plano, Pieza ordenada y Conjunto. Iconos escalables 4K. **Discovery Center** | La barra de contexto aparece al hacer clic derecho | `[fuente secundaria]` |
| 2026 | **Tema oscuro** (Opciones > Ayudas). Iconos SVG. VCB con menos espacio vacío; Círculo, Rectángulo y Línea con iconos directos en vez de desplegables | Los desplegables de Círculo y Rectángulo ya no existen como antes | `[fuente secundaria]` |
| 2026 | **Deshacer/Rehacer de Mostrar/Ocultar** en Pieza y Conjunto | — | `[fuente secundaria]` |
| 2026 | **Magnetic Snap Assembly** (ensamblado por imanes, IA que reconoce relaciones al acercar piezas) | Útil para colocar rápido, pero **revisar qué relaciones creó** en PathFinder | `[fuente secundaria]`; nombre ES sin verificar `[traducción probable]` |
| 2026 | **Automatic Drawing** (plano automático: vistas ortogonales, rotas e isométricas con cotas) | Borrador de plano; hay que revisar normas y cotas | `[fuente secundaria]` |
| 2026 | **Design Copilot** (asistente de IA de ayuda dentro de la aplicación) | Consultas de «¿dónde está…?» | `[fuente secundaria]` |
| 2026 | **Walkthrough** (recorrido en primera persona del conjunto), **Part Display Configurations**, nuevas opciones de explosionado | — | `[fuente secundaria]` |
| 2026 | **Espesor de pared** en Extrudir, Revolución, Barrido, Por secciones y Hélice (operación de pared delgada); **Patrón de relleno** en ordenado; **Tab and Slot** (pestaña y ranura) en chapa; mejoras de **Grabado** (Etch) y de pestaña multiborde | Una operación hueca sin necesidad de Dar espesor | `[fuente secundaria]` |
| 2026 | Tablas de revisión nativas, tolerancia automática de agujeros, símbolos de usuario, calcomanías sombreadas en vistas | Plano | `[fuente secundaria]` |
| 2026 | Nombre comercial «**Designcenter** Solid Edge 2026»; «Designcenter X Solid Edge» es la versión SaaS (licencia nominal, ajustes en la nube) | El producto es el mismo; sólo cambia la marca | `[fuente secundaria]` |

---

## 13. Puente hacia la API COM (resumen)

El detalle está en `05_api_automatizacion.md`. Aquí sólo se fija la correspondencia de conceptos.

| Concepto de interfaz | En la API (pywin32) | Etiqueta |
|---|---|---|
| La aplicación | `win32com.client.GetActiveObject("SolidEdge.Application")` o `Dispatch(...)` | `[fuente secundaria]` |
| Archivo > Nuevo con un tipo | `app.Documents.Add("SolidEdge.PartDocument")`, `"SolidEdge.SheetMetalDocument"`, `"SolidEdge.AssemblyDocument"`, `"SolidEdge.DraftDocument"`, `"SolidEdge.WeldmentDocument"` | `[fuente secundaria]` |
| Ordenado / síncrono | Propiedad `ModelingMode` del documento de pieza (`seModelingModeOrdered` / `seModelingModeSynchronous`) | `[fuente secundaria]` |
| Ejecutar un comando de la cinta | `app.StartCommand(<id de comando>)`: lanza el comando como si se pulsara (la interacción posterior es de la interfaz) | `[fuente secundaria]` |
| Barra de comandos o QuickBar | Constantes `SECommandBarModeConstants` (modo Command Bar / Quick Bar) | `[doc — referencia API Siemens]` |

Regla: lo que se pueda hacer por API se hace por API (reproducible). La interfaz se usa para lo que la API no cubre, y para revisar visualmente con el usuario `[inferido]`.

---

## 14. Fuentes

**Ayuda oficial de Siemens — Solid Edge 2024 (2310), en español y en inglés** (consultada el 2026-10-28; los textos salen del índice `topics.json` de cada manual):
- Índice del manual de interfaz (ES): https://docs.sw.siemens.com/es-ES/doc/246738425/PL20220830878154140.user_interface/xid1816059
- Entornos de Solid Edge: https://docs.sw.siemens.com/es-ES/doc/246738425/PL20220830878154140.user_interface/xid1330018
- Entorno Pieza / Chapa / Conjunto / Plano: …`user_interface/mdovr4i`, `mdovr5i`, `mdovr2i`, `mdovr3i`
- Movimientos síncronos y ordenados: https://docs.sw.siemens.com/es-ES/doc/246738425/PL20220830878154140.user_interface/xid840948
- Menú Archivo: …`user_interface/xid1182107` · IU adaptable: …`xid1874823` · Usar el ratón: …`mouse1a` · Controlador de volante: …`moving_faces_002`
- Barra Acceso rápido: …`user_interface/quickaccesstoolbar` · Barra de comandos: …`quickbar1a`, `commandbar1a` · BarraDeAvisos: …`promptbar1a` · Menús radiales: …`radial_menu1a` · Barras de contexto: …`xid2053601`
- Buscador de comandos: https://docs.sw.siemens.com/es-ES/doc/246738425/PL20220830878154140.user_interface/cmdref1a
- QuickPick: …`user_interface/xid708083` · Puntos significativos: …`select1a` · Atajos del teclado: …`keybd4d`
- Vistas con teclas: https://docs.sw.siemens.com/es-ES/doc/246738425/PL20220830878154140.user_interface/view1a · Cubo de vista rápida: …`xid820314` · Orientación de la vista: …`view1c` · Estilos: …`dirvw1h` · Visualización básica: …`viewbasics1a`
- Plantillas y documentos: …`user_interface/doccr1a`, `helpers3d`, `xid1171338` · Temas: …`xid603697`
- Manual Diseño (ES): https://docs.sw.siemens.com/es-ES/doc/246738425/PL20220830878154140.design/ordered1a · Mover a síncrono: …`design/movetosynchronous1a` · Extrudir: …`design/procut1c`, `xid458037` · Revolución: …`prorev1c`, `feat18c` · PathFinder en pieza: …`pthfndb2a` · Controlador de volante: …`steeringw1a`, `steeringw2a_table` · Panel Intención de diseño: …`featedit7a` · Relaciones geométricas: …`geomrel1a` · Planos de referencia: …`refplaneb1a` · Bocetos síncronos y ordenados: …`xid1320810` · Atajos de abocetado: …`xid1322781` · Reproducción de operaciones: …`plybck1d` · Relaciones de conjunto: …`xid453632`, `const1a`, `ground1h` · Colores de relaciones: …`skchrlshpcolor1c` · Reparar archivos que faltan: …`xid1021871`, `xid1022042` · Actividad «Explosionar un conjunto»: …`id1608066`
- Manual Fabricación (opciones): https://docs.sw.siemens.com/es-ES/doc/246738425/PL20220830878154140.manufacture/helpers1d · Unidades: …`manufacture/xid833601` · General (Pieza): …`genopt3d`
- Gestión de documentos: https://docs.sw.siemens.com/es-ES/doc/246738425/PL20220830878154140.managing_documents/xid1169603 (Gestor de diseños) · Mover documentos: …`xid1171411` · Vínculos interrumpidos: …`xid1177457` · Empaquetar proyecto: …`xid1171813`
- Novedades 2024 (ES): https://docs.sw.siemens.com/es-ES/doc/246738425/PL20220830878154140.newse/xid667374 (…`xid2191665`, `xid2205017`)
- Datos crudos (índices): `https://docs.sw.siemens.com/documentation/external/PL20220830878154140/{es-ES|en-US}/se_help/se/2023/se_help/{es-ES|en-US}/{user_interface|design|manufacture|managing_documents|newse}/topics.json`

**Siemens — blogs, novedades y soporte** `[fuente secundaria]`:
- New in Solid Edge 2025: UI/UX — https://blogs.sw.siemens.com/solidedge/new-in-solid-edge-2025-ui-ux/
- Designcenter Solid Edge 2026 (personalización: tema oscuro, VCB, SVG, deshacer de visibilidad) — https://blogs.sw.siemens.com/solidedge/?p=18296
- Designcenter Solid Edge 2026 (resumen) — https://blogs.sw.siemens.com/solidedge/designcenter-solid-edge-2026/
- New in Designcenter Solid Edge 2026: Part and Sheet Metal — https://blogs.sw.siemens.com/solidedge/new-in-designcenter-solid-edge-2026-part-and-sheet-metal/
- New in Designcenter Solid Edge 2026: Draft and MBD — https://blogs.sw.siemens.com/solidedge/new-in-designcenter-solid-edge-2026-draft-and-mbd/ (sólo visto en buscador)
- Example of mixing synchronous and ordered — https://blogs.sw.siemens.com/solidedge/example-of-mixing-synchronous-and-ordered/ (sólo visto en buscador)
- KB: archivos académicos en licencia comercial — https://support.sw.siemens.com/en-US/okba/PL8506730/Open-a-file-from-commercial-licensed-Solid-Edge-in-an-Academic-licensed-Solid-Edge/index.html
- KB: ¿abren archivos de 2019 en versiones anteriores? (no) — https://support.sw.siemens.com/en-US/okba/PL8007905/Can-Solid-Edge-2019-files-be-opened-in-earlier-versions-of-Solid-Edge/index.html
- KB: abrir archivos de versiones anteriores en la última — https://support.sw.siemens.com/en-US/okba/PL8001999/Opening-previous-version-of-Solid-Edge-files-in-the-latest-version/index.html
- Student Edition (descarga y restricciones) — https://resources.sw.siemens.com/en-US/download-solid-edge-student-edition
- Referencia API, `SECommandBarModeConstants` — https://support.industrysoftware.automation.siemens.com/trainings/se/107/api/SolidEdgeConstants~SECommandBarModeConstants.html
- Ayuda ST6 (réplica en soliddna.com), recorrido de la interfaz — https://soliddna.com/SEHelp/ST6/EN/user_interface/guitour1a.htm

**Prensa técnica** `[fuente secundaria]`:
- DEVELOP3D, «Designcenter Solid Edge 2026» — https://develop3d.com/cad/designcenter-solid-edge-2026/
- IT Brief, «Siemens unveils AI features in latest Designcenter Solid Edge 2026» — https://itbrief.news/story/siemens-unveils-ai-features-in-latest-designcenter-solid-edge-2026

**Sin verificar en este capítulo:**
- La ayuda en español de 2025 y 2026 (pide iniciar sesión en el Support Center).
- La ubicación exacta en la cinta de Design Copilot, Magnetic Snap Assembly y Automatic Drawing.
- Los nombres de las plantillas de Chapa, Conjunto y Soldadura.
- El valor numérico de las constantes de la API.
