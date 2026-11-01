# 04 — Planos en Solid Edge 2026: entorno Plano (Draft, `.dft`)

> Capítulo de referencia de la habilidad `solid-edge-experto`. Cubre crear el plano desde el modelo, hojas y cuadro de rotulación con propiedades, vistas (incluida la **explosionada**), cotas, anotaciones, **globos y lista de piezas**, salida a **PDF** y los checklists de entrega. El detalle fino de la API COM está en `05_api_automatizacion.md` (§6); aquí solo se dice si existe acceso por API y cómo encaja.
> Contexto de uso: estudiante de Ingeniería Aeronáutica (USB Bogotá), Solid Edge 2026 **en español**, normas **ISO**, **mm**, plano de pieza por pieza y plano de **ensamble general explosionado** en A3 1:1, con globos `número/cantidad` y lista de piezas `Número de elemento | Nombre archivo (sin extensión) | Autor | Cantidad`.

**Leyenda de etiquetas**
- **[doc]** ayuda oficial de Siemens (ayuda de Solid Edge en inglés, espejo ST5/ST6 en soliddna.com; los conceptos del entorno Plano no han cambiado en lo esencial) o referencia oficial de la API.
- **[local]** verificado en la **instalación real de Solid Edge 2026 de este equipo** (`<SE>\`): mapa de comandos en español `<SE>\Program\ResDLLs\000A\SECmdMap.xml`, recursos de la cinta `Ribbon.drx`/`DtlDCX.DRX`, plantillas `<SE>\Template\…` y preferencias `<SE>\Preferences\…`. Es la fuente más fiable para los **nombres en español**.
- **[fuente secundaria]** base de conocimiento de Siemens (KB), blog oficial, foros o cursos.
- **[inferido]** deducción razonada, no comprobada en pantalla. **[traducción probable]** nombre en español no confirmado. **[API?]** acceso por API no confirmado.

---

## Tabla de contenido

0. [Lo esencial en 20 líneas](#0-lo-esencial-en-20-líneas)
1. [Conceptos: documento, hojas, plantillas, normas y escalas](#1-conceptos-documento-hojas-plantillas-normas-y-escalas)
2. [Tabla maestra de comandos ES ↔ EN](#2-tabla-maestra-de-comandos-es--en)
3. [Crear el plano desde el modelo](#3-crear-el-plano-desde-el-modelo)
4. [Hojas, hoja de fondo y cuadro de rotulación con propiedades](#4-hojas-hoja-de-fondo-y-cuadro-de-rotulación-con-propiedades)
5. [Vistas](#5-vistas)
6. [Acotado](#6-acotado)
7. [Anotaciones](#7-anotaciones)
8. [Ensamble: globos (Ref. elemento) y lista de piezas](#8-ensamble-globos-ref-elemento-y-lista-de-piezas)
9. [Salida: PDF, DWG/DXF e impresión](#9-salida-pdf-dwgdxf-e-impresión)
10. [Normas ISO de referencia rápida](#10-normas-iso-de-referencia-rápida)
11. [Método y checklists de entrega](#11-método-y-checklists-de-entrega)
12. [Mapa API COM para el operario (Jarvis)](#12-mapa-api-com-para-el-operario-jarvis)
13. [Problemas frecuentes y su arreglo](#13-problemas-frecuentes-y-su-arreglo)
14. [Fuentes](#14-fuentes)

---

## 0. Lo esencial en 20 líneas

1. Un plano `.dft` **no copia** el modelo: guarda un **vínculo** (ModelLink) al `.par`/`.asm`. Si el modelo cambia, las vistas quedan **desactualizadas** y se actualizan con **Actualizar vistas**. Entregar el `.dft` sin sus modelos rompe el plano [doc].
2. El comando en español para crear el plano desde el modelo se llama **«Crear dibujo»** (no «Crear plano»): Menú de la aplicación › Nuevo › Crear dibujo [local][doc].
3. El asistente de vistas se llama **«Asistente de vistas»** en la cinta y «Asistente de vistas de dibujo» en el buscador de comandos [local].
4. Plantilla ISO de fábrica: `<SE>\Template\ISO Metric\iso metric draft.dft`. Trae hojas de fondo **«Hoja A4», «Hoja A4V», «Hoja A3», «Hoja A2», «Hoja A1», «Hoja A0»** [local]. El A3 del curso se consigue asignando «Hoja A3» en **Configuración de la hoja** [local][doc].
5. El cuadro de rotulación vive en la **hoja de fondo** y se rellena solo con **texto de propiedades** `%{…}` que lee las propiedades del archivo [doc][local].
6. La **vista explosionada** no se crea en el plano: se crea en *Explosionar-Renderizar-Animar*, se **guarda como configuración de visualización** y en el plano se elige esa configuración en el Asistente de vistas («Configuración de visualización del modelo») [doc][local]. La configuración vive en el archivo `.cfg` junto al `.asm` [local].
7. **Cotas**: «Smart Dimension» (así, en inglés, también en la interfaz española) para acotar a mano; **«Recuperar cotas»** trae las cotas del modelo, pero **no funciona en vistas isométricas, de detalle ni auxiliares** [doc][local].
8. **Globos**: en la interfaz española el comando de plano se llama **«Ref. elemento»** (referencia de elemento), no «Globo» [local]. Los globos «número/cantidad» salen de dos casillas: «Usar número de artículo para texto superior» y «Usar cantidad de artículos para texto inferior» [local].
9. **Lista de piezas** (Inicio › Tablas): la configuración guardada **«ISO»** de fábrica ya trae exactamente las columnas del plano del curso: `Número de elemento | Nombre archivo (sin extensión) | Autor | Cantidad` [local]. Existe también la configuración **«Explosionada»** [local].
10. Salida: **Guardar como › PDF** o Imprimir a escala 1:1 en el tamaño de la hoja; revisar que el A3 salga a 420×297 mm [doc][inferido].
11. Por API: `ModelLinks.Add`, `DrawingViews.AddPartView`/`AddAssemblyView(…, ConfigurationName)`, `PartsLists.Add(vista, "ISO", AutoBalloon, CreatePartsList)` existen [doc]; unidades de la API en **metros** [local].

---

## 1. Conceptos: documento, hojas, plantillas, normas y escalas

### 1.1 Qué contiene un `.dft`
| Elemento | Qué es | Etiqueta |
|---|---|---|
| **Hoja de trabajo** (Working sheet) | Página donde van vistas, cotas, anotaciones y tablas. Puede haber muchas («Hoja1», «Hoja2»…). | [doc][local] |
| **Hoja de fondo** (Background sheet) | Telón de fondo con marco y cuadro de rotulación. Cada hoja de trabajo tiene **una** hoja de fondo asignada; una hoja de fondo puede servir a muchas. Se imprime con la hoja de trabajo; la hoja de trabajo toma el **tamaño** de su fondo. Los gráficos del fondo **no se escalan** con la escala de la hoja (siempre 1:1). | [doc] |
| **Hoja modelo 2D** (2D Model sheet) | Espacio de dibujo 2D a escala 1:1; solo una por documento, no se renombra. Poco útil para el curso. | [doc][local] |
| **Vínculos al modelo** (ModelLinks) | Referencias a `.par`/`.psm`/`.asm`. Las vistas de pieza son **asociativas**. | [doc] |
| **Vistas de dibujo** | Vistas 2D generadas del 3D (pieza o ensamble) o vistas 2D puras. | [doc] |
| **Tablas** | Lista de piezas, tabla de agujeros, tabla de revisiones (nativa en 2026), tablas de usuario. | [doc][local][fuente secundaria] |

Mostrar unas u otras: **Ver › Vistas de la hoja › Trabajo / Fondo / Modelo 2D** (EN: View › Sheet Views › Working / Background / 2D Model) [local][doc].

### 1.2 Plantillas instaladas (verificado en `<SE>\Template`) [local]
| Carpeta | Archivo | Uso |
|---|---|---|
| `ISO Metric` | `iso metric draft.dft` | **Plantilla de plano ISO** (la que se usa por defecto para el curso si la universidad no da otra). |
| `Quicksheet` | `iso metric QS part.dft`, `iso metric QS assembly.dft` | Plantillas «Hoja rápida» (Quicksheet): traen vistas y lista de piezas predefinidas que se rellenan solas al crear el dibujo. |
| `Reports` | `DraftList.txt` | Configuraciones guardadas de la **lista de piezas** («ANSI», «ISO», «ISO - Hojas nuevas», «ANSI - Hojas nuevas», «Explosionada»). |
| `Reports` | `DraftWizard.txt` | Valores por defecto del Asistente de vistas (KB de Siemens: ahí se guardan) [fuente secundaria]. En este equipo está vacío. |
| `3D PDF Publish`, `Symbol`, `Nailboard` | — | Otros usos (PDF 3D, símbolos, arneses). |

Contenido confirmado de la plantilla ISO [local]: hoja de trabajo «Hoja1»; hojas de fondo **«Hoja A4», «Hoja A4V», «Hoja A3», «Hoja A2», «Hoja A1», «Hoja A0»**; textos de propiedades en el rótulo como `%{pset=0pid=2|R1}` (título del modelo), `%{pset=0pid=4}` (autor), `Hoja %{pset=6pid=29} de %{pset=6pid=28}`, `Archivo: %{pset=6pid=74}` y la fecha `%{pset=0pid=1002/@d/MM/yy}`.

> Si la universidad entrega su propia plantilla (con escudo y campos «Nombre del proyecto», «Profesor», «Código estudiantil»…), **usar esa** y no la ISO de fábrica [inferido].

### 1.3 Norma de dibujo y diedro
- El ángulo de proyección (**primer diedro** = ISO/europeo, **tercer diedro** = ANSI/americano) se define en **Opciones de Solid Edge › Normas de dibujo** (EN: Solid Edge Options › Drawing Standards › Projection angle) y determina dónde aparecen las vistas plegadas [doc][traducción probable].
- Con ISO: **primer diedro** → la vista superior se coloca **debajo** del alzado y la vista lateral izquierda a la **derecha** [doc ISO 128-30/5456-2; inferido para el comportamiento de plegado].
- Poner el **símbolo de proyección** (cono truncado) en el rótulo [ISO 5456-2].

### 1.4 Escalas
- Escalas métricas disponibles en `<SE>\Preferences\Custom.XML` (lista «Metric»): **50:1, 20:1, 10:1, 5:1, 2:1, 1:1, 1:2, 1:5, 1:10, 1:20, 1:50, 1:100 …** — coinciden con ISO 5455 [local].
- **Escala de vista** ≠ **escala de hoja**. La escala de la vista se fija al crearla (barra de comandos del asistente) o en sus propiedades; la de la hoja con **Establecer escala de la hoja** (Set Sheet Scale) y sirve para la propiedad «Escala de hoja» del rótulo [local][doc].
- Los gráficos de la hoja de fondo siempre son 1:1 respecto a la hoja [doc].

---

## 2. Tabla maestra de comandos ES ↔ EN

Nombres en español sacados del mapa de comandos y de la cinta de **tu** Solid Edge 2026 [local]. Ubicación en la cinta según la ayuda en inglés [doc] (pestaña **Inicio** = Home) salvo indicación.

| Comando | ES (interfaz real) | EN | Dónde está | Qué hace | API |
|---|---|---|---|---|---|
| Crear dibujo | **Crear dibujo** | Create Drawing | Menú aplicación › Nuevo › Crear dibujo (desde .par/.asm abierto); clic derecho en PathFinder | Crea el .dft con plantilla y lanza el asistente | `Documents.Add` + `ModelLinks.Add` [doc][API?] |
| Asistente de vistas | **Asistente de vistas** (buscador: «Asistente de vistas de dibujo») | View Wizard / Drawing View Wizard | Inicio › Vistas de dibujo | Primera vista de un modelo + plegadas | `AddPartView` / `AddAssemblyView` [doc] |
| Vista principal | **Vista principal** | Principal View | Inicio › Vistas de dibujo | Pliega una vista ortogonal/isométrica desde otra | `AddByFold` [API?] |
| Vista auxiliar | **Vista auxiliar** (cinta: «Auxiliar») | Auxiliary View | Inicio › Vistas de dibujo | Vista perpendicular a una arista inclinada | [API?] |
| Vista de detalle | **Vista de detalle** (cinta: «Detalle») | Detail View | Inicio › Vistas de dibujo | Ampliación de una zona | [API?] |
| Plano de corte | **Línea del plano de corte** (cinta: «Plano de corte») | Cutting Plane | Inicio › Vistas de dibujo | Dibuja la línea de corte en una vista | [API?] |
| Vista en corte | **Vista en corte** | Section View | Inicio › Vistas de dibujo | Crea el corte a partir del plano de corte | [API?] |
| Corte parcial | **Vista en corte parcial** (cinta: «Corte parcial») | Broken-Out Section View | Inicio › Vistas de dibujo | Corte localizado con perfil cerrado y profundidad | [API?] |
| Vista interrumpida | **Vista de rotura** | Broken View / Add Break Lines | Inicio › Vistas de dibujo / clic derecho en vista | Acorta piezas largas con líneas de rotura | [API?] |
| Vista de modelo 2D | **Vista de modelo 2D** | 2D Model View | Inicio › Vistas de dibujo | Vista de la hoja modelo 2D | [API?] |
| Actualizar vistas | **Actualizar vistas** / «Actualizar vistas de dibujo» | Update Views | Inicio › Vistas de dibujo; clic derecho › Actualizar | Regenera vistas desactualizadas | `DrawingView.Update` [API?]; ID comando 57083 [local] |
| Seguidor de vistas | **Seguidor de vistas de dibujo** | Drawing View Tracker | Inicio › Vistas de dibujo | Lista qué vistas están desactualizadas y por qué | — |
| Smart Dimension | **Smart Dimension** (no se tradujo) | SmartDimension | Inicio › Cota | Cota de un elemento (longitud, Ø, R, ángulo) | `Dimensions.Add…` [API?] |
| Distancia entre | **Distancia entre** | Distance Between | Inicio › Cota | Cota lineal entre dos elementos; cotas en cadena/base | [API?] |
| Ángulo entre | **Ángulo entre** | Angle Between | Inicio › Cota | Cota angular | [API?] |
| Cota de coordenadas | **Cota de coordenadas** / «Cota de coordenadas angulares» | Coordinate Dimension | Inicio › Cota | Cotas por coordenadas desde un origen | [API?] |
| Diámetro simétrico | **Diámetro simétrico** | Symmetric Diameter | Inicio › Cota | Ø en vista lateral de pieza de revolución | [API?] |
| Cota de chaflán | **Cota de chaflán** | Chamfer Dimension | Inicio › Cota | Acota chaflanes (C×45°) | [API?] |
| Recuperar cotas | **Recuperar cotas** | Retrieve Dimensions | Inicio › Cota | Trae cotas y anotaciones del modelo | `DrawingView.RetrieveDimensions` [verificado en este equipo: firma] |
| Actualizar cotas recuperadas | **Actualizar cotas recuperadas** | Update Retrieved Dimensions | Inicio › Cota | Refresca cotas recuperadas | `DraftDocument.UpdateRetrievedDimensionsAndAnnotations` [verificado en este equipo: firma] |
| Organizar cotas | **Organizar cotas** | Arrange Dimensions | Inicio › Cota | Espacía y alinea cotas | — |
| Cotas automáticas | **Acotado automático** / «Cotas automáticas» | AutoDimensions | Inicio | Acota sola la geometría 2D nueva | — |
| Llamada | **Llamada** | Callout | Inicio › Anotación | Nota con o sin directriz; admite texto de propiedades | [API?] |
| Directriz | **Directriz** | Leader | Inicio › Anotación | Flecha/línea de referencia | [API?] |
| Globo | **Ref. elemento** («Referencia de elemento») | Balloon | Inicio › Anotación | Globo; vinculado a la lista de piezas | `Balloons.Add` [API?] |
| Marca de centro | **Marca de centro** | Center Mark | Inicio › Anotación | Cruz de centro en arcos/círculos | [API?] |
| Línea de centro | **Línea de centro** | Center Line | Inicio › Anotación | Eje entre dos puntos/aristas | [API?] |
| Líneas centrales automáticas | **Líneas centrales automáticas** | Automatic Center Lines | Inicio › Anotación | Ejes y marcas de centro de una vista de golpe | [API?] |
| Círculo de marcas de agujero | **Círculo de marcas de agujero(s)** | Bolt Hole Circle | Inicio › Anotación | Círculo primitivo de agujeros | [API?] |
| Acabado superficial | **Símbolo de acabado superficial** (buscador: «Símbolo de textura de superficie») | Surface Texture Symbol | Inicio › Anotación | Símbolo ISO 1302/21920 | [API?] |
| Soldadura | **Símbolo de soldadura** | Weld Symbol | Inicio › Anotación | Símbolo ISO 2553 | [API?] |
| Marco de tolerancia geométrica | **Marco de control de operación** | Feature Control Frame | Inicio › Anotación | Marco GD&T (ISO 1101) | [API?] |
| Datum | **Marco de referencia absoluta** | Datum Frame | Inicio › Anotación | Letra de referencia (datum) | [API?] |
| Objetivo de datum | **Objetivo de referencia absoluta** | Datum Target | Inicio › Anotación | Punto/área de referencia | [API?] |
| Estado de borde | **Estado de borde** | Edge Condition | Inicio › Anotación | Rebabas/aristas (ISO 13715) | [API?] |
| Texto | **Texto** | Text | Inicio › Anotación | Cuadro de texto (no vinculable a propiedades) | [API?] |
| Lista de piezas | **Lista de piezas** | Parts List | Inicio › Tablas | Tabla BOM asociativa + globos automáticos | `PartsLists.Add` [doc] |
| Tabla de agujeros | **Tabla de agujeros** | Hole Table | Inicio › Tablas | Tabla de coordenadas de agujeros (2026: ajustes y tolerancias del modelo) | [API?] |
| Tabla de revisiones | **Tabla de revisiones** | Revision Table | Inicio › Tablas | Nativa en 2026 | [API?] |
| Tabla de tolerancias | **Tabla de tolerancias** | Tolerance Table | Inicio › Tablas | Tabla de tolerancias generales | [API?] |
| Bloques | **Bloques** / «Etiqueta de bloque» / «Tabla de bloques» | Blocks | Pestaña de bloques/biblioteca | Grupos reutilizables (logo, rótulo) | [API?] |
| Configuración de la hoja | **Configuración de la hoja** (buscador: «Ajuste de la hoja») | Sheet Setup | Menú aplicación; doble clic/clic derecho en pestaña de hoja | Tamaño, escala y **fondo** de la hoja | `Sheet.SheetSetup` [API?] |
| Insertar hoja | **Insertar hoja** / «Lámina nueva» | New Sheet | Clic derecho en pestaña de hoja | Añade hoja de trabajo | `Sheets.AddSheet` [API?] |
| Renombrar / reordenar / borrar hoja | **Renombrar hoja**, **Reordenar hojas**, **Borrar Hoja** | Rename/Reorder/Delete Sheet | Clic derecho en pestaña | Gestión de hojas | [API?] |
| Escala de hoja | **Establecer escala de la hoja** | Set Sheet Scale | Inicio/Ver | Escala de hoja (usuario o derivada de una vista) | [API?] |
| Hoja de fondo / trabajo | **Fondo** / **Trabajo** / **Modelo 2D** | Background / Working / 2D Model | Ver › Vistas de la hoja | Alterna lo que se muestra | [API?] |
| Actualizar textos de propiedades | **Actualizar todos los textos de propiedades** | Update All Property Text | Inicio | Refresca los `%{…}` | [API?] |
| Convertir textos de propiedades | **Convertir todos los textos de propiedades** | Convert All Property Text | Inicio | Los vuelve texto fijo (pierde vínculo) | — |
| Propiedades del archivo | **Propiedades del archivo** | File Properties | Menú aplicación › Propiedades | Título, autor, proyecto, personalizadas | `SummaryInfo`/`Properties` [API?] |
| Imprimir | **Imprimir** / «Imprimir planos» (lote) | Print / Print Drawings | Menú aplicación | Impresión, también a PDF | `PrintOut` [API?] |
| Guardar como | **Guardar como** / «Guardar copia como» / «Guardar como traducido» | Save As / Save Copy As / Save As Translated | Menú aplicación | PDF, DWG, DXF, imagen | `SaveAs`, `SaveCopyAs` [fuente secundaria][API?] |
| Comparación de dibujos | **Comparación de dibujos** | Drawing Compare | Herramientas | Compara dos versiones del plano | — |

> ⚠️ Rarezas de traducción en tu instalación [local]: «Draft» a veces se tradujo como **«desmoldeo»** (p. ej. «Clonar desmoldeo», «Patrón rectangular (desmoldeo)»); «datum» se tradujo como **«referencia absoluta»**; el globo es **«Ref. elemento»**. Si un comando no aparece con el nombre esperado, usar el **buscador de comandos** de la cinta con el nombre inglés o el alias.

---

## 3. Crear el plano desde el modelo

### 3.1 Método A — «Crear dibujo» desde la pieza o el ensamble abierto (recomendado) [doc][local]
1. Abrir el `.par` o `.asm` y **guardarlo** (las vistas toman el estado guardado) [inferido].
2. **Menú de la aplicación › Nuevo › Crear dibujo** (o clic derecho sobre el archivo en PathFinder/Biblioteca).
3. En el diálogo **Crear dibujo**: elegir la **plantilla** (`ISO Metric\iso metric draft.dft` o la de la universidad) y marcar **«Ejecutar el Asistente de creación de vistas de dibujo»** [traducción probable de *Run Drawing View Creation Wizard*].
4. Si NO se marca el asistente: con plantilla normal, un ensamble genera **una isométrica**; una pieza genera **alzado, planta y perfil**; una plantilla *Quicksheet* genera sus vistas y lista de piezas [doc].
5. Seguir con el asistente (§5.1). Guardar el `.dft` con nombre propio, p. ej. `P01_Horquilla.dft`, en la **misma carpeta** que los modelos [inferido].

### 3.2 Método B — Nuevo plano y luego el asistente [doc]
1. **Nuevo › Plano ISO** (plantilla ISO métrica).
2. **Inicio › Vistas de dibujo › Asistente de vistas** › elegir el modelo (diálogo **Seleccionar vínculo / Select Attachment** si ya hay modelos vinculados).
3. Colocar vistas (§5.1).

### 3.3 Método C — Arrastrar el modelo a la hoja [doc]
Arrastrar un `.asm` desde la Biblioteca a una hoja vacía crea una **isométrica**; un `.par` crea alzado, planta y perfil. Rápido pero sin control de escala/orientación.

### 3.4 Plantilla «Hoja rápida» (Quicksheet) [doc][local]
- Plano con vistas vacías ya colocadas + lista de piezas; al «Crear dibujo» se rellenan con el modelo.
- Útil para repetir el mismo formato en las 8–10 piezas del proyecto: preparar UNA vez la plantilla de la universidad con vistas tipo, y guardarla con **Crear plantilla Hoja rápida** (Create Quicksheet template) [local].
- Para que una Quicksheet ponga globos automáticos: en las propiedades de la vista (pestaña General) activar **Auto-balloon** antes de crear la plantilla [fuente secundaria: KB PL8629304].

### 3.5 Novedad 2026: dibujos automáticos con IA [fuente secundaria]
Solid Edge 2026 anuncia generación automática de planos 2D (vistas ortogonales, rotas e isométricas con cotas; «70–80 % del trabajo»), eligiendo plantilla, tamaño y vistas. El nombre exacto del comando en español no se verificó. **Tratar el resultado como borrador**: revisar vistas necesarias, cotas duplicadas y rótulo con el checklist §11.

---

## 4. Hojas, hoja de fondo y cuadro de rotulación con propiedades

### 4.1 Elegir A3 horizontal en la hoja de trabajo [doc][local]
1. Clic derecho en la pestaña «Hoja1» › **Configuración de la hoja** (o doble clic en la pestaña).
2. Pestaña **Tamaño** (Size): tamaño estándar / horizontal [traducción probable].
3. Pestaña **Fondo** (Background): elegir **«Hoja A3»** y marcar mostrar fondo.
4. **Guardar valores por defecto** si todas las hojas nuevas serán A3 [doc].
5. Escala de la hoja: **Establecer escala de la hoja** (1:1 en el caso del curso) [local].

### 4.2 Editar el cuadro de rotulación [doc][fuente secundaria]
1. **Ver › Vistas de la hoja › Fondo**: aparecen las pestañas de las hojas de fondo («Hoja A3», …).
2. Ir a la pestaña de la hoja de fondo usada. Editar líneas, textos y logo (Insertar imagen / Insertar objeto para el **escudo**) [local: «Insertar imagen»].
3. Los campos que deben **rellenarse solos** se crean con **Llamada** (Callout) sin directriz y con **texto de propiedades**, NO con «Texto» (un cuadro de texto no se vincula a propiedades) [fuente secundaria: eng-tips].
4. Volver con **Ver › Vistas de la hoja › Trabajo**.
5. Consejo: dejar **todo** el texto de propiedades en la hoja de fondo; así sirve a todas las hojas [fuente secundaria].

### 4.3 Texto de propiedades `%{…}` — sintaxis [doc][local]
- Una cadena empieza en `%{` y termina en `}`; admite **códigos de formato** `/xx` (precisión, tolerancias apiladas `/st`, unidades duales `/du`, fecha `/@…`) [doc].
- Se inserta desde el diálogo **Seleccionar texto de propiedades** (botón *Texto de propiedades* en Llamada, Ref. elemento, Lista de piezas) [doc]; así la sintaxis queda bien escrita.
- **Fuente** de la propiedad (sufijo) [doc]:

| Fuente (EN) | Sufijo | Lee la propiedad de… |
|---|---|---|
| From Active Document | (ninguno) | el propio `.dft` |
| Index Reference | `|R1` (`|R2`…) | el **1.er modelo vinculado** (2.º…) |
| Named Reference | `|<archivo>` | un modelo concreto por nombre |
| From Graphic Connection | `|G` | el objeto al que apunta la llamada/globo |
| From Graphic Connection to Part | `|GP` | la pieza del objeto apuntado |
| (leyendas de vista) | `|DV` | la vista de dibujo [local] |

- En 2026 el archivo guarda los códigos internos `pset/pid` (lo que se ve en el diálogo es el nombre) [local]. Tabla de códigos observados en la plantilla ISO y en `DraftList.txt` [local; significado de cada código inferido por contexto]:

| Código | Propiedad | Uso típico en el rótulo |
|---|---|---|
| `%{pset=0pid=2|R1}` | Título del **modelo** (1.er vínculo) | «Nombre de la pieza» |
| `%{pset=0pid=2}` | Título del **plano** | — |
| `%{pset=0pid=4}` | Autor del plano | «Nombre» (dibujó) |
| `%{pset=3pid=2}`, `%{pset=3pid=3}` | Propiedades de proyecto (n.º de documento / revisión) [inferido] | «Plano número» |
| `%{pset=6pid=74}` | Nombre de archivo | «Archivo» |
| `%{pset=6pid=78}` | Nombre de archivo **sin extensión** | columna de la lista de piezas |
| `%{pset=6pid=29}` / `%{pset=6pid=28}` | N.º de hoja / número de hojas | «Hoja 1 de 2» |
| `%{pset=0pid=1002/@d/MM/yy}` | Fecha (con formato) | «Fecha» |
| `%{pset=10pid=1|G}` / `%{pset=10pid=2|G}` | Número de elemento / cantidad (lista) | lista de piezas y globos |

- Formas «con nombre» que también funcionan (versiones anteriores, foros): `%{Title|R1}`, `%{Document Number|R1}`, `%{Revision number|R1}` [fuente secundaria].
- Propiedades del documento activo disponibles: Título, Asunto, Autor, Palabras clave, Proyecto, Número de documento, Revisión, Estado, Nombre de archivo (con y sin extensión, ruta), Nombre/Número de hoja, Número de hojas, **Escala de hoja**, fechas (creado/modificado/origen) [doc].

### 4.4 Plan concreto para el rótulo del curso [inferido, sobre [doc]]
| Campo del rótulo | Dónde se escribe el valor | Fuente del texto de propiedades |
|---|---|---|
| Nombre del proyecto | Propiedades del archivo del **.dft** › Proyecto (o del modelo con `|R1`) | Activo: Proyecto |
| Nombre de la pieza | Propiedades del **modelo** › Título | `|R1`: Título |
| Plano número | .dft › Número de documento | Activo: Número de documento |
| Nombre | .dft › Autor | Activo: Autor |
| Profesor | .dft › **Personalizada** «Profesor» | Activo: personalizada |
| Código estudiantil | .dft › **Personalizada** «Codigo estudiantil» | Activo: personalizada |
| Fecha | automática | Activo: fecha con formato `/@dd/MM/yyyy` |
| Escala | automática | Activo: Escala de hoja |
| Tolerancia general | texto fijo «±0,5 mm salvo indicación» | — |

Pasos: 1) Menú aplicación › **Propiedades del archivo** › pestañas Resumen/Proyecto/**Personalizada** → rellenar. 2) En el fondo, Llamada › Texto de propiedades › elegir fuente y propiedad. 3) **Actualizar todos los textos de propiedades**. 4) Si un campo muestra `####` o el texto de error, no hay modelo vinculado o la propiedad está vacía (el texto de error se configura en Opciones › General) [fuente secundaria].
- Los campos `|R1` quedan **en blanco hasta colocar una vista** del modelo [fuente secundaria].
- Rellenar el **Autor** de cada `.par` (Propiedades del archivo › Resumen › Autor): alimenta la columna «Autor» de la lista de piezas [local: columna `pset=0pid=4`].

### 4.5 Varias hojas [doc][local]
- Clic derecho en la pestaña › **Insertar hoja**, **Renombrar hoja** («Vistas», «Corte A-A»…), **Reordenar hojas**, **Borrar Hoja**.
- Cada hoja de trabajo puede tener otro fondo (p. ej. «Hoja A4V» para una pieza pequeña).
- «Hoja %{pset=6pid=29} de %{pset=6pid=28}» numera automáticamente [local].

---

## 5. Vistas

### 5.1 Asistente de vistas (View Wizard) — paso a paso [doc][local]
1. **Inicio › Vistas de dibujo › Asistente de vistas** → elegir el modelo.
2. **Opciones de vista de dibujo**: para ensambles, lista **«Configuración de visualización del modelo»** (aquí se elige la configuración **explosionada**), vista de modelo PMI o zona; botón *Avanzado* para limitar aristas [doc][local].
3. **Orientación de la vista**: alzado (Frontal), superior, derecha, **iso**, o *Personalizada* (permite girar a gusto o perspectiva) [doc].
4. **Disposición**: marcar vistas adicionales (planta, perfil, isométrica) que se colocan junto a la principal [doc].
5. Barra de comandos antes de colocar: **estilo de vista**, **leyenda**, **escala**, **estilo de aristas** (visibles/ocultas), **sombreado** [doc].
6. Clic en la hoja. Si se colocó una sola vista, el comando sigue activo: clic a derecha/izquierda/arriba/abajo **pliega** vistas ortogonales; clic en diagonal crea **pictóricas** (isométricas). Clic derecho/Esc termina [doc].
7. Opción de opciones: **Opciones de Solid Edge › Asistente de vistas de dibujo › «Usar barra de comandos…»** cambia entre modo barra (rápido) y modo diálogos paso a paso [doc].

### 5.2 Vistas principales/proyectadas [doc]
- **Vista principal** (Principal View): seleccionar una vista existente y mover el cursor → pliega la proyección según el diedro de la norma. Mantiene **alineación** con la vista madre.
- Usar el **mínimo de vistas necesarias** (§11).

### 5.3 Isométrica / pictórica [doc]
- Plegando en diagonal desde una vista o con orientación iso en el asistente.
- ⚠️ **Recuperar cotas no funciona en isométricas** [doc]: las isométricas del curso son de presentación; acotar en ortogonales.

### 5.4 Vista auxiliar [doc]
**Vista auxiliar** › clic en una arista inclinada de una vista → se pliega perpendicular a ella. Para caras inclinadas que se verían deformadas.

### 5.5 Vista de detalle [doc][local]
**Vista de detalle** (cinta «Detalle») › dibujar el círculo (o perfil) de la zona en la vista madre › colocar la vista › fijar escala (2:1, 5:1…). Leyenda automática «DETALLE A (2:1)». Las vistas de detalle **conservan su escala** propia y sirven de base para cortes [doc]. No admiten Recuperar cotas [doc].

### 5.6 Cortes [doc][inferido donde se indica]
Procedimiento general:
1. Tener la vista donde se ve la traza del corte (ortogonal, auxiliar o de detalle).
2. **Plano de corte** › seleccionar la vista › dibujar la **línea de corte** con líneas (entorno de perfil) › definir el **sentido de mirada** con la flecha › **Cerrar plano de corte** [doc][local: «Cerrar plano de corte»].
3. **Vista en corte** › seleccionar la línea de corte › elegir opciones en la barra (tipo, rayado) › colocar. El sentido lo da la línea de corte, no el lado donde se hace clic [doc].
4. Leyenda «CORTE A-A»; rayado automático; editar rayado (estilo, separación, ángulo) en **Propiedades de la vista › Visualización** por pieza [doc].

| Tipo | Cómo se dibuja la línea de corte | Etiqueta |
|---|---|---|
| **Corte total** | Una línea recta que atraviesa toda la pieza | [doc] |
| **Corte quebrado/escalonado** (offset) | Varias líneas ortogonales que pasan por los elementos a mostrar | [inferido: «multi-segmento»] |
| **Corte alineado (girado)** | Dos o más líneas con ángulo + opción **Vista en corte girada** (Revolved Section View) en la barra | [doc] |
| **Medio corte** | Línea en «L»: desde fuera hasta el eje de simetría y luego a lo largo del eje hasta salir de la pieza | [inferido] |
| **Solo sección** | Opción *Section Only*: muestra solo la rebanada cortada (rápido en ensambles) | [doc] |

- En ensambles: decidir qué piezas se cortan (**ejes, tornillos, pasadores y chavetas NO se cortan** según la norma) → casilla **Cortar tornillería** (Cut hardware) en Visualización y ajustes de visualización del modelo [doc]. Los nervios cortados longitudinalmente no se rayan (pestaña Avanzado) [doc].

### 5.7 Corte parcial (Broken-out) [doc][local]
**Vista en corte parcial** (cinta «Corte parcial») › seleccionar la vista › dibujar un **perfil cerrado** (línea a mano alzada o curva) alrededor de la zona › **definir la profundidad** (clic en una vista vecina o valor) › terminar. Útil para mostrar un agujero interior sin cortar toda la pieza.

### 5.8 Vista interrumpida (Broken view) [doc][local]
Clic derecho en la vista › **Agregar líneas de rotura** [traducción probable] (buscador: «Vista de rotura») › dibujar los pares de líneas › terminar. Acorta piezas largas (ejes, perfiles) para usar mayor escala. Las vistas plegadas perpendiculares **heredan** las roturas (Heredar líneas de rotura / Quitar herencia) [doc]. La cota de longitud total sigue mostrando el valor real [inferido].

### 5.9 Vista de ensamble y vista EXPLOSIONADA [doc][fuente secundaria][local]
**En el ensamble (antes del plano):**
1. **Herramientas › Entornos › Explosionar-Renderizar-Animar** (buscador: «Explosionar el entorno animación renderizada») [local].
2. **Explosionar automático** o **Explosionar** manual; ajustar con los comandos de modificación. Cada operación queda como evento en la pestaña Explosión del PathFinder [doc][local].
3. Opcional: **Líneas de flujo** / **Terminadores de línea de flujo**; **Arrastrar líneas de flujo** convierte las de evento en de anotación [doc][local].
4. **Orientar la vista** como debe salir en el plano (isométrica). En vistas explosionadas el botón de orientación del plano está **deshabilitado**: la orientación la fija la cámara guardada [fuente secundaria: KB PL8707940].
5. **Guardar la configuración de visualización** (Configuraciones de visualización › nombre, p. ej. `Explosionada_ISO`). **Sin configuración guardada no se puede colocar la explosión en el plano** [doc]. 2026 refuerza «capturar ensambles explosionados como configuraciones de visualización para planos» [fuente secundaria].
6. Para otra explosión: **Desexplosionar** (Unexplode) y repetir [doc][traducción probable].
7. ⚠️ Las configuraciones viven en el archivo **`<ensamble>.cfg`** junto al `.asm` (ej. en `<SE>\Training`: `carrier.asm` + `carrier.cfg`) [local]. Copiar siempre el `.cfg` con el ensamble.

**En el plano:**
1. **Asistente de vistas** › elegir el `.asm` › en **Opciones de vista de dibujo** elegir la **Configuración de visualización del modelo** = la explosionada [doc][local].
2. Colocar la vista (orientación la da la configuración). Escala: la que quepa en A3 (el plano del curso usa 1:1).
3. Ajustar líneas de flujo en **Propiedades de la vista › Anotación**; editarlas con **Dibujar en vista** [doc].
4. Cambiar la configuración de una vista existente: **Propiedades de la vista de dibujo › Visualización › configuración** [fuente secundaria]. Si cambia la configuración, la vista queda desactualizada («La configuración ha cambiado y la vista de dibujo está desactualizada») [local].
5. Alternativa: Menú aplicación › Nuevo › **Crear dibujo** desde el entorno Ensamble (no disponible dentro de ERA) [doc].

### 5.10 Estilo de visualización de vistas [doc]
- **Aristas**: visibles, ocultas (líneas de trazos), tangentes; en ensambles desmarcar *Mostrar aristas ocultas* y *Mostrar aristas de piezas ocultas* mejora rendimiento [doc].
- **Sombreado**: vista sombreada o sombreada con aristas (barra del asistente / propiedades). Para planos de fabricación ISO usar **líneas** (sin sombrear); la isométrica de presentación puede ir sombreada [inferido].
- Calidad: «Borrador» (rápida, solo aristas visibles) vs alta calidad [doc]. Error «al generar la vista sombreada… poca memoria» → bajar DPI en Propiedades de la vista [local].
- Ocultar/mostrar aristas puntuales: **Ocultar borde / Mostrar borde**; **Pintor de bordes** [local].

### 5.11 Actualizar vistas cuando cambia el modelo [doc][local]
- Vista desactualizada = **marco gris/sombreado** alrededor y aviso «Una o más vistas de dibujo están desactualizadas» [doc][local].
- **Inicio › Vistas de dibujo › Actualizar vistas** o clic derecho › **Actualizar**. **Seguidor de vistas de dibujo** dice cuáles y por qué [local].
- ⚠️ «Las cotas colocadas en estas vistas desactualizadas se **desconectarán** al actualizar» si la geometría a la que apuntaban desaparece [local] → revisar cotas (color de cota desconectada) tras cada actualización.
- **Desactivar vistas de dibujo** congela las vistas e ignora cambios del modelo; **Activar** las vuelve a vincular [local].
- La lista de piezas no se actualiza por fecha de archivo: se recalcula y compara; contorno gris = desactualizada → clic derecho › Actualizar [doc].

### 5.12 Alinear, mover y recortar vistas [doc][local]
- Las vistas plegadas quedan **alineadas**; clic derecho › mantener/romper alineación [inferido]. Mover arrastrando el marco.
- **Recortar vista** (Crop) para quitar zonas [local]. **Establecer profundidad de vista de dibujo** limita la geometría tras un plano [local][doc].
- Leyendas: **Mostrar leyenda**, mostrar escala de la vista en la leyenda [local].

---

## 6. Acotado

### 6.1 Smart Dimension (cota inteligente) [doc][local]
1. **Inicio › Cota › Smart Dimension**.
2. Clic en una línea → longitud; en un círculo → Ø (o radio según opción de la barra); en un arco → R; dos líneas no paralelas → ángulo.
3. Colocar el texto; la barra de comandos permite elegir estilo, tipo (Ø/R), prefijo y tolerancia.
4. Para distancias entre elementos: **Distancia entre** (soporta cotas encadenadas y desde una base común) [doc]. Ángulos: **Ángulo entre** [doc].
5. Cotas de piezas de revolución vistas de lado: **Diámetro simétrico** [local].
6. **Organizar cotas** para espaciarlas uniformemente [local].

### 6.2 Recuperar cotas (Retrieve Dimensions) [doc][local]
1. **Inicio › Cota › Recuperar cotas**.
2. En la barra (grupo Propiedades) marcar qué tipos traer (todas por defecto).
3. Clic en una vista **ortogonal o de corte**. Esc para terminar.
4. Quitar: misma orden › **Quitar cotas** › clic en la vista.
- Las cotas recuperadas son **impulsadas (bloqueadas)**; vienen de cotas del modelo/PMI de pieza, chapa o ensamble de nivel superior [doc].
- **No funciona en vistas de detalle, auxiliares ni isométricas** [doc].
- Tras recuperar: **borrar duplicados**, reubicar, completar faltantes con Smart Dimension. Recuperar NO garantiza un acotado de fabricación correcto [inferido].
- **Actualizar cotas recuperadas** tras cambiar el modelo [local].

### 6.3 Tolerancias [doc][inferido donde se indica]
En la barra de la cota o en **Propiedades de la cota › Tipo de cota**: nominal, **tolerancia ±** (simétrica/asimétrica), **límites** (máx/mín), **clase/ajuste** ISO (H7, g6, H7/g6) con la tabla `SE-LimitsAndFitsTableISO.txt` [local: archivo presente]. Formatos de texto: apilado `/st`, límite, dual `/du` [doc]. Tolerancia general: en el rótulo («±0,5 mm») o con **Tabla de tolerancias** [local].

### 6.4 Prefijos, sufijos y texto de cota [doc][local]
- Diálogo **Prefijo** de la cota: Ø (código `%DI`), R, «4X», «M8», texto superior/inferior, sufijos [doc: `%DI`; resto inferido].
- **Copiadora de prefijos** copia el prefijo de una cota a otras [local].
- Cotas de chaflán: **Cota de chaflán** (C2 o 2×45°) [local].

### 6.5 Coordenadas y cotas automáticas [doc][local]
**Cota de coordenadas** (ordinate) desde un origen; **Cotas de coordenadas automáticas**; **Cambiar la cota de origen** [local]. Útiles para placas con muchos agujeros (o usar Tabla de agujeros).

### 6.6 Reglas ISO 129-1 que el operario debe aplicar [ISO 129-1, resumen]
1. Cada medida **una sola vez**, en la vista donde mejor se ve la forma.
2. No acotar a aristas ocultas.
3. Cotas fuera de la pieza, menores cerca y mayores lejos; no cruzar líneas de cota.
4. Diámetros donde se ve el perfil (vista lateral) con Ø; radios con R en la vista del arco.
5. Unidades mm sin escribir «mm» en cada cota; decimales con **coma** en ISO/Colombia [inferido para el estilo].
6. Agujeros repetidos: «4X Ø6».
7. Ninguna cota redundante (cadena cerrada); dejar un tramo sin acotar o como referencia entre paréntesis.

---

## 7. Anotaciones

| Necesidad | Comando ES | Procedimiento breve | Etiqueta |
|---|---|---|---|
| Ejes y centros | **Líneas centrales automáticas** | Seleccionar la(s) vista(s) → crea ejes de cilindros y marcas de centro | [local][inferido: comportamiento] |
| Centro de un agujero | **Marca de centro** | Clic en el círculo/arco | [local] |
| Eje entre dos aristas | **Línea de centro** | Dos clics (o modo «2 líneas») | [local] |
| Agujeros en círculo | **Círculo de marcas de agujero** | Centro + agujeros | [local] |
| Nota con flecha | **Llamada** (+ directriz) | Texto, símbolos y texto de propiedades | [doc] |
| Rugosidad | **Símbolo de acabado superficial** | Elegir tipo, Ra, colocar sobre la arista | [local] |
| Soldadura | **Símbolo de soldadura** | Lado flecha/otro lado, tipo y medida | [local] |
| GD&T | **Marco de control de operación** + **Marco de referencia absoluta** | Marco: característica, tolerancia, referencias A|B|C; datum: letra sobre la cara | [local] |
| Agujeros | **Tabla de agujeros** | Seleccionar vista y origen → tabla X/Y/Ø; 2026 muestra ajustes/tolerancias del modelo | [local][fuente secundaria] |
| Reutilizar dibujo | **Bloques** | Crear bloque (logo, rótulo, símbolo) y colocarlo; también bloques de vista | [local][fuente secundaria] |
| Anotar alineado | **Forma de alineamiento de anotaciones** | Línea guía a la que se pegan globos/llamadas; se mueven con la vista | [fuente secundaria][local] |
| Símbolos propios | Símbolos definidos por el usuario (2026) | Biblioteca propia de símbolos | [fuente secundaria] |

---

## 8. Ensamble: globos (Ref. elemento) y lista de piezas

### 8.1 Cómo se relacionan [doc]
- La **lista de piezas** es asociativa a la **vista** con la que se crea.
- Los **globos** muestran el **número de elemento** de la lista **activa**. Si no hay lista activa, el globo muestra «NA» [fuente secundaria: KB PL7009563].
- Con varias listas, la activa se cambia con clic derecho › **Hacer activa** [doc].

### 8.2 Preparar el ensamble (antes del plano) [fuente secundaria][doc]
1. Cada `.par` con **Autor** y **Título** rellenos (Propiedades del archivo), y nombre de archivo limpio (la columna usa el nombre **sin extensión**) [local].
2. Comprobar en las **propiedades de aparición** de cada componente que **«Informes / Lista de piezas»** esté en **Sí**; si está en No, la pieza no sale en la lista y su globo dice «NA» [fuente secundaria: KB PL8512589, PL8599076][traducción probable].
3. Piezas repetidas (p. ej. 4 tornillos) deben ser **el mismo archivo** colocado varias veces: así la **Cantidad** sale 4 automáticamente [inferido].
4. Números de elemento del ensamble (opcional): Opciones de Solid Edge › Números de elemento + casilla «Usar números de elemento generados por el conjunto» en la pestaña Opciones de la lista [doc][traducción probable].

### 8.3 Crear la lista de piezas con globos automáticos [doc][local]
1. **Inicio › Tablas › Lista de piezas**.
2. En la barra: **Configuración guardada** = **«ISO»** (columnas `Número de elemento | Nombre archivo (sin extensión) | Autor | Cantidad`, idénticas al plano del curso) o **«Explosionada»** (Número, Nombre archivo, Cantidad + columna oculta *Orden del conjunto* para ordenar) [local].
3. Activar **Ref. elemento automática** (Auto-Balloon: «Crea automáticamente referencias de elementos en la vista de dibujo seleccionada») [local][doc].
4. Antes de colocar, abrir **Propiedades de la lista de piezas** y en la pestaña de **globos** (Balloon) marcar: forma de **círculo dividido** [traducción probable], **«Usar número de artículo para texto superior»** y **«Usar cantidad de artículos para texto inferior»** → globos `número/cantidad` como en el plano del curso [local]. ⚠️ Estos valores **solo se editan al colocar** la lista; después aparecen en gris [fuente secundaria: KB PL8008953].
5. Clic en la **vista explosionada** → aparecen los globos y la tabla sigue al cursor → clic para colocarla (encima del rótulo, alineada a su ancho) [doc][inferido].
6. Reordenar/ajustar globos: arrastrarlos; usar **Forma de alineamiento de anotaciones** para alinearlos [fuente secundaria].

### 8.4 Pestañas de «Propiedades de la lista de piezas» [doc; nombres ES confirmados donde se marca local]
| Pestaña (EN) | ES | Para qué |
|---|---|---|
| General | General | Estilo de tabla, altura máx./filas, **Configuraciones guardadas** (guardar y reaplicar formato) |
| Location | Ubicación [traducción probable] | Posición; misma hoja u **hojas nuevas** |
| Title | Título [traducción probable] | Texto del título/subtítulo |
| Columns | **Columnas** [local] | Columnas disponibles/usadas; propiedades combinadas o texto |
| Data | Datos [traducción probable] | Añadir/quitar filas y editar celdas (sustituciones) |
| Options | Opciones [traducción probable] | Formato del número de elemento, **marcar elementos sin globo** (asterisco), longitudes de tubos/perfiles |
| Item Number | Número de elemento [inferido] | Editar números tras crear |
| List Control | **Control de listas** [local] | Detalle por pieza/subconjunto (aplanar, explosionar subconjuntos) |
| Sorting | Ordenación [traducción probable] | Ordenar por título, n.º de documento, cantidad…; **renumerar** (renumera globos si fueron automáticos) |
| Groups | Grupos [traducción probable] | Subtítulos en listas largas |
| Balloon | **Ref. elemento** [local] | Forma, texto, número/cantidad, duplicados, pilas de tornillería |

### 8.5 Globos manuales [doc][local]
- **Inicio › Anotación › Ref. elemento** › en la barra elegir forma, número/cantidad, **Texto de propiedades** › clic en la pieza (punta) y clic para colocar.
- Un globo manual sobre una pieza **excluida** de la lista muestra «NA» [doc].
- Globos sin pieza o tras eliminar piezas: los globos de piezas borradas **no se eliminan solos** → borrarlos a mano tras actualizar [doc].
- Elementos de la lista sin globo se marcan con **asterisco** (*) salvo que se cambie en Opciones [doc].

### 8.6 Errores típicos de globos/lista [fuente secundaria]
| Síntoma | Causa | Arreglo |
|---|---|---|
| Lista vacía (solo cabecera), sin globos | Piezas con «Informes/Lista de piezas = No» | Ponerlo en Sí en el ensamble |
| Globo «NA» | Lista no activa, o pieza excluida | Clic derecho en la lista › Hacer activa; revisar exclusión |
| Número del globo ≠ lista | Celda con sustitución manual | Borrar sustituciones en Datos y renumerar |
| Pestaña de globos en gris | Ya se colocó la lista | Rehacer la lista o editar globos uno a uno |
| Quitar una pieza de la vista la quita de la lista | Comportamiento de diseño | Excluir en la lista, no en la vista |

---

## 9. Salida: PDF, DWG/DXF e impresión

### 9.1 PDF (lo que se entrega) [doc][inferido donde se indica]
1. **Menú aplicación › Guardar como** › Tipo **PDF (*.pdf)** › **Opciones**: hojas a incluir (todas/activa), resolución, color/monocromo, incrustar fuentes [inferido: nombres de opciones].
2. Alternativa: **Imprimir** con una impresora PDF, **tamaño de papel = tamaño de la hoja** (A3) y escala **1:1 / sin ajustar**; si se marca «Ajustar a página», el plano deja de estar a escala [inferido].
3. Varias hojas → un PDF multipágina [inferido].
4. Revisión del PDF: abrirlo, medir el marco (A3 = 420×297 mm), verificar que el rótulo no muestre `%{…}` ni `####`, que las líneas ocultas y de centro salgan con su tipo de línea, y que el texto sea legible (≥ 2,5 mm) [inferido; ISO 3098 para altura de letra].
- Novedad 2026: PDF 3D con vistas de sección PMI (no es el entregable del curso) [fuente secundaria].

### 9.2 DWG/DXF [doc][inferido]
**Guardar como** › AutoCAD (*.dwg / *.dxf) › **Opciones** → asistente de traducción (versión de AutoCAD, hojas → espacios papel, escala). Los símbolos definidos por el usuario de 2026 se conservan en DXF/DWG [fuente secundaria].

### 9.3 Impresión [doc][local]
- **Imprimir**: impresora, papel, orientación, rango de hojas, escala. **Imprimir planos** imprime en lote varias hojas/documentos [local].
- Comprobar en la vista previa que el marco cabe completo [inferido].

---

## 10. Normas ISO de referencia rápida [normas citadas; resumen propio]

| Norma | Qué fija | Aplicación en el plano |
|---|---|---|
| ISO 5457 | Formatos y marco | A4 210×297, **A3 420×297**, A2 594×420, A1 841×594, A0 1189×841 mm; margen de archivo **20 mm** a la izquierda y **10 mm** en el resto (A3/A4) |
| ISO 7200 | Cuadro de rotulación | Abajo a la derecha, ancho máx. 180 mm; campos: título, n.º de plano, propietario, autor, fecha, escala, hoja, método de proyección |
| ISO 5455 | Escalas | Ampliación 2:1, 5:1, 10:1, 20:1, 50:1; reducción 1:2, 1:5, 1:10, 1:20, 1:50… |
| ISO 128 (-20, -30, -40…) | Líneas, vistas, cortes | Continua gruesa = aristas visibles; continua fina = cotas, rayado; trazos finos = ocultas; trazo-punto fino = ejes; trazo-punto fino con extremos gruesos = plano de corte; rayado a 45° |
| ISO 5456-2 | Proyección | **Primer diedro** (método E) con su símbolo |
| ISO 129-1 | Acotado | §6.6 |
| ISO 2768-1 | Tolerancias generales | Si el curso usa ±0,5 mm, indicarlo en el rótulo |
| ISO 1101 / 5459 | GD&T y referencias | Marcos de tolerancia y datums |
| ISO 21920-1 (antes 1302) | Rugosidad | Símbolo de acabado |
| ISO 6433 | Referencias de elementos | **Globos** con número; la lista de piezas los relaciona |
| ISO 7573 | Lista de piezas | Encima del rótulo; numeración de abajo hacia arriba si se apoya en el rótulo |
| ISO 3098 | Rotulación | Altura de letra normalizada (2,5 / 3,5 / 5 / 7 mm) |

---

## 11. Método y checklists de entrega

### 11.1 Método para el plano de una pieza
1. **Analizar la pieza**: forma, simetrías, agujeros, zonas inclinadas, detalles pequeños.
2. **Elegir el alzado**: la vista que más información da y con menos aristas ocultas, en posición de trabajo/fabricación.
3. **Vistas necesarias y suficientes**: añadir planta/perfil solo si aportan; sustituir vistas por **cortes** si hay interiores; **detalle** para zonas pequeñas; **auxiliar** para caras inclinadas; **rotura** para piezas largas. Isométrica pequeña como ayuda de lectura (sin cotas).
4. **Escala** normalizada que llene ~60–70 % del área útil del formato.
5. **Ejes y marcas de centro** (Líneas centrales automáticas + revisión).
6. **Acotar**: Recuperar cotas en ortogonales/cortes → borrar duplicados → completar con Smart Dimension → comprobar que con las cotas se puede **fabricar** (cada elemento con forma + posición).
7. **Tolerancias y acabados** donde haga falta; tolerancia general en el rótulo.
8. **Rótulo**: propiedades rellenas, actualizar textos de propiedades.
9. **Revisión** con el checklist y **PDF**.

### 11.2 Checklist — plano de pieza
- [ ] Plantilla correcta (universidad o ISO), formato y orientación correctos; marco y rótulo completos.
- [ ] Diedro ISO (primer diedro) y símbolo de proyección.
- [ ] Vistas necesarias y suficientes; alzado bien elegido; ninguna vista redundante.
- [ ] Interiores mostrados con corte (no con muchas ocultas); rayado correcto; ejes/tornillos no rayados.
- [ ] Escala normalizada (ISO 5455) en el rótulo y, si difiere, junto a la vista.
- [ ] Todas las cotas para fabricar; ninguna duplicada; ninguna a línea oculta; ninguna cadena cerrada.
- [ ] Ø y R correctos; agujeros repetidos con «nX»; chaflanes y redondeos acotados.
- [ ] Ejes de simetría y marcas de centro en todos los cilindros/agujeros.
- [ ] Tolerancia general (±0,5) y tolerancias/ajustes particulares donde aplica.
- [ ] Rótulo: proyecto, pieza, profesor, fecha, plano n.º, nombre, código, escala, material (si se pide).
- [ ] Ninguna vista desactualizada ni cota desconectada (Seguidor de vistas limpio).
- [ ] PDF a escala, legible, sin `%{…}`/`####`.

### 11.3 Checklist — plano de ensamble explosionado
- [ ] Configuración explosionada guardada en el `.asm` (y su `.cfg` en la carpeta del proyecto).
- [ ] Vista explosionada isométrica colocada con esa configuración; líneas de flujo visibles y limpias.
- [ ] (Opcional) vista del ensamble armado para referencia.
- [ ] Lista de piezas con configuración «ISO»: Número de elemento | Nombre archivo (sin extensión) | Autor | Cantidad.
- [ ] Cantidades verificadas contra el ensamble (contar ocurrencias).
- [ ] Un globo por cada elemento distinto; globos `número/cantidad`; ninguno «NA»; ninguno con asterisco en la lista.
- [ ] Globos ordenados (alineados en fila/columna, en sentido horario o por orden de montaje), directrices sin cruzarse.
- [ ] Lista de piezas encima del rótulo, mismo ancho, sin solaparse con la vista.
- [ ] Rótulo completo (escala 1:1 o la real), tolerancia general.
- [ ] PDF A3 revisado.

### 11.4 Flujo de trabajo de la sesión (operario + el usuario) [inferido]
1. Operario: comprueba modelos guardados, propiedades (Autor/Título) e «Informes/Lista de piezas = Sí».
2. Operario: crea el `.dft` en carpeta temporal, coloca vistas y lista → **parada**: El usuario revisa en pantalla.
3. Operario: cotas y anotaciones → **parada**.
4. Operario: rótulo y PDF → **parada final**; luego guardado oficial con nombre nuevo (nunca sobrescribir).

---

## 12. Mapa API COM para el operario (Jarvis)

> Firmas detalladas, pruebas reales y trampas en `05_api_automatizacion.md` §6. Aquí solo el mapa por tarea.

- **Unidades**: la API trabaja en **metros** y radianes. Evidencia: `DraftList.txt` guarda anchos de columna 0,020 (= 20 mm) y origen 0,195 m para A4 [local]. Un A3 horizontal mide 0,420 × 0,297 m.

| Tarea | Llamada | Estado |
|---|---|---|
| Crear plano con plantilla | `app.Documents.Add("SolidEdge.DraftDocument", r"<SE>\Template\ISO Metric\iso metric draft.dft")` | [API?] firma de plantilla |
| Hojas | `dft.Sheets`, `dft.ActiveSheet`, `Sheets.AddSheet(...)`, `sheet.Activate()` | [doc: `DraftDocument.Sheets`][API?] resto |
| Fondo / tamaño de hoja | `sheet.SheetSetup` (tamaño, fondo) / `sheet.Background` | [API?] |
| Vincular modelo | `link = dft.ModelLinks.Add(r"...\pieza.par")` | [doc] |
| Vista de pieza | `sheet.DrawingViews.AddPartView(link, Orientación, Escala, x, y, sePartDesignedView)` | [doc] |
| Vista de ensamble / **explosionada** | `sheet.DrawingViews.AddAssemblyView(link, Orientación, Escala, x, y, ViewType, ConfigurationName="Explosionada_ISO")` | [doc] firma; uso con explosión [inferido] |
| Cambiar configuración | `DrawingView.Configuration = "…"` (lectura/escritura) | [doc] |
| Vista plegada | `DrawingViews.AddByFold(vista, dirección, x, y)` | [API?] |
| Actualizar | `DrawingView.Update()` / `app.StartCommand(57083)` (Actualizar vistas de dibujo) | [API?]; ID [local] |
| Lista de piezas + globos | `sheet.PartsLists.Add(vista, "ISO", 1, 1)` → `SavedSettings` = nombre de `DraftList.txt` («ISO», «Explosionada»…); `AutoBalloon=1` | [doc] firma; nombre de configuración [inferido de local]; funcionamiento real ver 05 §6 |
| Lista con archivo de configuración | `PartsLists.AddEx(...)` usa `Template\Reports\DraftList.txt` | [fuente secundaria] |
| Globo suelto | `sheet.Balloons.Add(x, y, z)` · `Balloons.AddByTerminator(objeto, x, y, z, keyPoint)` (globo con flecha a un elemento) | [verificado en este equipo: firma] |
| Cotas | `sheet.Dimensions.AddLength / AddDistanceBetweenObjects / AddRadialDiameter / AddAngularBetween…` | [API?] |
| Recuperar cotas | `vista.RetrieveDimensions(...)` (13 parámetros opcionales: lineales, radiales, angulares, anotaciones, marcas de centro…) · `vista.RetrieveCenterLinesCenterMarks(...)` · `dft.UpdateRetrievedDimensionsAndAnnotations()`. Respaldo: `StartCommand(32803)` | [verificado en este equipo: firma; falta probarlo en vivo] |
| Propiedades del archivo | `doc.Properties` / `doc.SummaryInfo` (Autor, Título…) en `.par` y `.dft` | [API?] |
| Actualizar texto de propiedades | `StartCommand(10180)` («Actualizar todos los textos de propiedades») | [API?]; ID [local] |
| PDF | `dft.SaveAs(r"...\plano.pdf")` o `dft.SaveCopyAs(...)` | [fuente secundaria][API?] |
| Imprimir | `dft.PrintOut(...)` | [API?] |

IDs de comando útiles para `Application.StartCommand` (del mapa de comandos de tu instalación) [local; uso con StartCommand: API?]: Asistente de vistas **25101**, Vista principal **32871**, Vista en corte **32921**, Línea del plano de corte **32922**, Vista de detalle **32788**, Vista en corte parcial **25105**, Vista de rotura **40039**, Recuperar cotas **32803**, Lista de piezas **32784**, Ref. elemento **10070**, Actualizar vistas de dibujo **57083**, Seguidor de vistas **32986**, Configuración de la hoja **10002**, Actualizar todos los textos de propiedades **10180**, Líneas centrales automáticas **33133**, Tabla de agujeros **11501**, Crear dibujo **39001**.

Reglas para el operario: crear el plano en carpeta temporal; nunca `SaveAs` sobre ruta existente (abre diálogo y bloquea Solid Edge); verificar cada vista por API (número de vistas, escala, `Configuration`) y pedir al usuario la revisión visual (ver habilidad `jarvis-operador`) [inferido].

---

## 13. Problemas frecuentes y su arreglo

| Problema | Causa probable | Arreglo | Etiqueta |
|---|---|---|---|
| Vistas con marco gris | Modelo cambió | Actualizar vistas; revisar cotas desconectadas | [doc][local] |
| No aparece la explosión en el asistente | No se guardó la configuración, o falta el `.cfg` | Guardar configuración en ERA; copiar `.cfg` con el `.asm` | [doc][local] |
| No puedo girar la vista explosionada | Orientación bloqueada en vistas explosionadas | Orientar en ERA y volver a guardar la configuración | [fuente secundaria] |
| Recuperar cotas no hace nada | Vista isométrica/detalle/auxiliar | Recuperar en ortogonal o corte | [doc] |
| Rótulo vacío | Sin vista del modelo (`|R1`) o propiedad vacía | Colocar vista; rellenar propiedades; Actualizar textos | [fuente secundaria] |
| Rótulo con `%{…}` literal | Se escribió como «Texto» y no como Llamada con texto de propiedades | Rehacer con Llamada | [fuente secundaria] |
| Lista sin piezas / globos «NA» | Exclusión en propiedades de aparición o lista inactiva | §8.6 | [fuente secundaria] |
| Cantidad errónea | Piezas iguales guardadas como archivos distintos | Usar el mismo archivo varias veces | [inferido] |
| PDF no está a escala | «Ajustar a página» o papel distinto | Papel = hoja, escala 1:1 | [inferido] |
| Plano abre sin vistas en otro PC | Rutas de vínculos rotas | Entregar carpeta completa (.dft + .par + .asm + .cfg); **Empaquetar dependencias** (Pack-n-go) | [local: comando existe][inferido] |
| Vista sombreada falla | Memoria/DPI | Bajar DPI en Propiedades de la vista | [local] |

---

## 14. Fuentes

**Instalación local de Solid Edge 2026 (este equipo, verificación directa)**
- `<SE>\Program\ResDLLs\000A\SECmdMap.xml` (mapa de comandos en español) y `<SE>\Program\ResDLLs\0009\SECmdMap.xml` (inglés), emparejados por ID.
- `<SE>\Program\ResDLLs\000A\Ribbon.drx`, `DtlDCX.DRX`, `detail.drx` (textos de la cinta y diálogos del entorno Plano).
- `<SE>\Template\ISO Metric\iso metric draft.dft`, `<SE>\Template\Reports\DraftList.txt`, `<SE>\Template\Quicksheet\*`, `<SE>\Preferences\Custom.XML`, `<SE>\Preferences\SE-LimitsAndFitsTableISO.txt`, `<SE>\Training\*.cfg`.

**Ayuda oficial de Solid Edge (espejo de la ayuda ST5/ST6 en inglés)**
- Drawing production workflow: https://soliddna.com/SEHelp/ST6/EN/drawing_production/detail1h.htm
- Create Drawing command: https://soliddna.com/SEHelp/ST6/EN/drawing_production/createdrawing1c.htm
- View Wizard command: https://soliddna.com/SEHelp/ST5/EN/i_v/prtvw1c.htm
- Drawing view creation: https://soliddna.com/SEHelp/ST6/EN/drawing_production/dview1a.htm
- Drawing sheets: https://soliddna.com/SEHelp/ST6/EN/drawing_production/sheet1a.htm
- Section views: https://soliddna.com/SEHelp/ST6/EN/drawing_production/secvw1a.htm
- Broken views: https://soliddna.com/SEHelp/ST6/EN/drawing_production/brknvw1a.htm
- Retrieve dimensions: https://soliddna.com/SEHelp/ST6/EN/dimensions/dimret1h.htm
- Exploded assemblies in Draft: https://soliddna.com/SEHelp/ST6/EN/assemble_parts/xpldas1a.htm
- Parts lists: https://soliddna.com/SEHelp/ST5/EN/i_v/prtlst1a.htm
- Property text (uso, fuentes, sintaxis): https://soliddna.com/SEHelp/ST5/EN/i_v/prptxt1a.htm · https://soliddna.com/SEHelp/ST6/EN/annotations/prptxt2a.htm · https://www.soliddna.com/SEHelp/ST5/EN/i_v/prptxt3a.htm · https://soliddna.com/SEHelp/ST5/EN/a_h/drawprop1a.htm
- Drawing View Wizard options: https://soliddna.com/SEHelp/ST6/EN/customize_solid_edge/xid608261.htm

**Referencia oficial de la API (Solid Edge Draft Type Library)**
- AddAssemblyView: https://support.industrysoftware.automation.siemens.com/trainings/se/107/api/SolidEdgeDraft~DrawingViews~AddAssemblyView.html
- AddPartView: https://support.industrysoftware.automation.siemens.com/trainings/se/107/api/SolidEdgeDraft~DrawingViews~AddPartView.html
- PartsLists.Add: https://support.industrysoftware.automation.siemens.com/trainings/se/107/api/SolidEdgeDraft~PartsLists~Add.html
- DrawingView.Configuration: https://support.industrysoftware.automation.siemens.com/trainings/se/107/api/SolidEdgeDraft~DrawingView~Configuration.html
- PartsLists.AddEx (versión 108): https://docs.plm.automation.siemens.com/docs/se/108/api/SolidEdgeDraft~PartsLists~AddEx.html

**Base de conocimiento y blogs de Siemens (fuente secundaria)**
- Defaults del asistente (DraftWizard.txt): https://support.sw.siemens.com/en-US/okba/PL8628556/How-to-change-default-settings-of-Drawing-View-Creation-Wizard/index.html
- Lista vacía / globos no creados: https://support.sw.siemens.com/en-US/okba/PL8512589/In-draft-the-parts-list-is-empty-and-balloons-are-not-created/index.html
- No se pueden poner globos a ciertos componentes: https://support.sw.siemens.com/en-US/okba/PL8599076/Cannot-Balloon-Certain-Components-in-Assembly-Drawing/index.html
- Número de elemento «NA» en globo: https://support.sw.siemens.com/en-US/okba/PL7009563/Item-number-not-available-in-balloon/index.html
- Globo ≠ número de la lista: https://support.sw.siemens.com/en-US/okba/PL8008871/Balloon-in-Parts-List-is-not-matching-Parts-List-Item-Number/index.html
- Pestaña de globos en gris: https://support.sw.siemens.com/en-US/okba/PL8008953/Values-in-balloon-tab-of-the-Parts-List-Properties-are-grayed-out/index.html
- Globos automáticos en Quicksheet: https://support.sw.siemens.com/en-US/okba/PL8629304/How-to-get-Automatic-Balloons-in-quick-sheet-template/index.html
- Exclusión de piezas por propiedad de aparición: https://support.sw.siemens.com/en-US/okba/PL8786558/Occurrence-Properties-Drawing-View-Option-Removes-Part-from-Parts-List/index.html
- Orientación deshabilitada en vistas explosionadas: https://support.sw.siemens.com/en-US/okba/PL8707940/View-Orientation-button-disabled-for-Exploded-Drawing-Views/index.html
- Vistas con configuraciones de visualización: https://support.sw.siemens.com/en-US/okba/PL8520708/Drawing-View-Placement-With-Display-Configurations/index.html
- Forma de alineamiento de anotaciones: https://blogs.sw.siemens.com/solidedge/manage-annotations-using-alignment-shape/
- Novedades 2026 en Draft y MBD: https://blogs.sw.siemens.com/solidedge/new-in-designcenter-solid-edge-2026-draft-and-mbd/
- Novedades 2026 en ensambles (explosión visual, configuraciones): https://blogs.sw.siemens.com/solidedge/new-assembly-productivity-tools-in-designcenter-solid-edge-2026/
- Develop3D, Solid Edge 2026: https://develop3d.com/cad/designcenter-solid-edge-2026/

**Foros (fuente secundaria)**
- Texto de propiedades en el rótulo (`%{Title|R1}`): https://www.eng-tips.com/threads/how-to-get-file-properties-from-a-part-to-populate-a-draft-document.298626 · https://www.eng-tips.com/threads/se-templates-props.170578/

**Normas ISO (consulta de referencia, resumidas)**: ISO 128 (líneas, vistas y cortes), ISO 129-1 (acotado), ISO 5455 (escalas), ISO 5456-2 (proyección), ISO 5457 (formatos y marco), ISO 7200 (cuadro de rotulación), ISO 6433 (referencias de elementos), ISO 7573 (lista de piezas), ISO 3098 (rotulación), ISO 2768-1 (tolerancias generales), ISO 1101 (GD&T).
