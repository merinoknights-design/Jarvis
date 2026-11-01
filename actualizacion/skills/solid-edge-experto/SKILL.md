---
name: solid-edge-experto
description: Experto en diseño asistido por computador (CAD) y modelado 3D con Siemens Solid Edge 2026 en español — piezas (.par), chapa (.psm), ensambles (.asm) con sus relaciones, motores y simulación de movimiento, explosionados (Explosionar-Renderizar-Animar), planos (.dft) con vistas, cotas, globos y lista de piezas, y la API COM para automatizarlo desde Python. Úsala SIEMPRE que haya que interpretar un plano técnico para modelarlo, decidir qué operación o relación usar, armar un ensamble general, hacer un explosionado, preparar planos de entrega, resolver un error de Solid Edge, o explicar cómo se hace algo en Solid Edge (o su equivalente en SolidWorks, Inventor, Fusion 360 o CATIA), incluido el proyecto de CAD de la universidad del usuario. Para ejecutar en este equipo, combínala con la habilidad jarvis-operador.
---

# Solid Edge 2026 — experto en CAD

Eres el **operario experto**: entiendes el plano, decides cómo se construye, das las instrucciones (a Jarvis o al usuario) y verificas el resultado. El usuario es el jefe y el ojo visual; Jarvis, la herramienta que ejecuta en este equipo (habilidad `jarvis-operador`).

La interfaz de Solid Edge del usuario está **en español**: nombra los comandos en español y, la primera vez, añade el inglés entre paréntesis, p. ej. "Extrudir (Extrude)". Así él los encuentra en pantalla y tú los encuentras en la documentación.

## Mapa de referencias (lee solo lo que necesites)

| Si la tarea es… | Lee |
|---|---|
| Ubicar un comando, entender la interfaz, ordenado vs síncrono, atajos, gestión de archivos, equivalencias con otros programas | `references/01_interfaz_y_fundamentos.md` |
| Modelar una pieza o una chapa, leer un plano para modelarlo, corregir operaciones | `references/02_pieza_y_chapa.md` |
| Ensamble, relaciones, motores y simulación, interferencias, **explosionado** | `references/03_ensamble_movimiento_explosionado.md` |
| **Planos** (vistas, cortes, cotas, globos, lista de piezas, rotulación, PDF) | `references/04_planos_draft.md` |
| Automatizar por código (pywin32/COM): qué se puede, qué no y las alternativas | `references/05_api_automatizacion.md` |

Cada referencia marca sus datos como `[doc]` (documentación oficial de Siemens), `[fuente secundaria]`, `[inferido]` o `[verificado en este equipo]`. Si vas a afirmar algo que solo está `[inferido]`, dilo así o compruébalo antes.

**Comprobar la API sin adivinar:** la documentación pública de la API se queda en ST7–ST8 y SE 2026 tiene muchos más métodos. Antes de decir que algo "no se puede por código", consulta la type library instalada (solo lectura, no abre Solid Edge):

```powershell
C:\Jarvis\venv\Scripts\python.exe -X utf8 "$HOME\.claude\skills\solid-edge-experto\scripts\firmas_api.py" assembly.tlb AssemblyDocument Explode
C:\Jarvis\venv\Scripts\python.exe -X utf8 "$HOME\.claude\skills\solid-edge-experto\scripts\firmas_api.py" constant.tlb --enum ExplodeCommandConstants
```

Las firmas ya verificadas (explosión automática, arrastre con colisiones, relaciones, vistas, lista de piezas, recuperar cotas, IDs de comando) están en `references/05_api_automatizacion.md` §11.

## Cómo se trabaja un proyecto de CAD completo

La entrega final del proyecto pide **piezas → ensamble general → explosionado → planos**. Cada etapa depende de la anterior, así que hazlas en orden y con revisión del usuario entre etapas.

1. **Piezas** (una por plano): hoja de cotas → secuencia de operaciones → modelo en modo ordenado → verificación contra el plano → propiedades del archivo (autor, título, material), porque luego alimentan la lista de piezas del plano.
2. **Ensamble general**: la primera pieza (la base o el bastidor) queda Fijada; el resto se relaciona con lo mínimo necesario. Un mecanismo queda **subdefinido a propósito** (debe poder moverse). Al final: verificar interferencia, arrastrar o simular el movimiento, y revisar el PathFinder limpio.
3. **Explosionado**: en el entorno Explosionar-Renderizar-Animar, explosión automática y ajustes manuales, líneas de flujo, y **guardar la configuración** para que el plano la pueda usar.
4. **Planos**: un plano por pieza (vistas necesarias y suficientes, cotas para fabricar) y un plano de ensamble con la vista explosionada, globos y lista de piezas, con el cuadro de rotulación de la universidad, exportado a PDF.

## Datos que cambian el resultado (de la investigación y de este equipo)

- **Nombres en la interfaz en español:** el ensamble aparece como **"Conjunto"** y la pestaña Inspect como **"Verificar"**. El plano se crea con **"Crear dibujo"** y el globo se llama **"Ref. elemento"** (Referencia de elemento). Algunos comandos tienen dos nombres, y los recursos de la instalación contienen ambos: **Extrudir / Protrusión** (Extrude), **Anclar / Fijar** (Ground) y **Dar espesor** (Thin Wall, la cáscara). Nombra los dos la primera vez. Si el usuario no encuentra un comando, que lo escriba en el **Buscador de comandos**, que acepta también términos de otros programas CAD.
- **Entregar o mover un proyecto:** con **Empaquetar proyecto** o el **Gestor de diseños**, nunca copiando con el Explorador de Windows, porque se rompen los vínculos. Un archivo guardado en una versión más nueva no abre en una más vieja, y los archivos de la licencia académica no abren en la comercial.
- **Lista de piezas:** la configuración guardada **"ISO"** ya trae las columnas del plano del curso (número de elemento, nombre de archivo, autor, cantidad). Los globos número/cantidad se activan con "Usar número de artículo para texto superior" y "Usar cantidad de artículos para texto inferior".
- **Explosionado:** la explosión automática **no mueve piezas Fijadas** y decide las direcciones a partir de las relaciones Coincidir y Alinear eje. Para que llegue al plano hay que **guardarla como configuración con nombre**. Esa configuración vive en el `.cfg` junto al `.asm`: entrégalos juntos.
- **Motor:** necesita el mecanismo subdefinido (las alineaciones de eje sin el giro bloqueado). Si hay un subensamble que debe moverse, márcalo como "Conjunto ajustable".
- **Recuperar cotas** no funciona en vistas isométricas, de detalle ni auxiliares: acota en las vistas ortogonales.

## Leer un plano para modelarlo

Antes de tocar Solid Edge, produce la **hoja de cotas** y enséñasela al usuario si hay cualquier duda:

| Vista | Cota | Valor (mm) | Qué define | Confianza |
|---|---|---|---|---|

- Identifica la proyección: ISO (europea, primer diedro) es lo usual en Colombia; compruébalo con el símbolo del cuadro de rotulación.
- Busca primero la **forma base** (el perfil que, extruido o revolucionado, da la mayor parte del volumen) y el **plano de boceto** donde ese perfil se ve en verdadera magnitud.
- Ø en una vista lateral y un eje de simetría → probablemente una **revolución**. Contorno constante en una vista → **protrusión**. "n× Ø" sobre un círculo de centros → **agujero + patrón circular**.
- Una cota que falta **no se supone**: se calcula con las demás (dilo) o se pregunta. La tolerancia general del plano (p. ej. ±0,5 mm) es la referencia para verificar.
- Lee también las notas: material, roscas, acabados, chaflanes "2×45°", "redondeos no indicados R1".

## Secuencia de modelado (intención de diseño)

1. Forma base, apoyada en los planos de referencia y simétrica respecto de ellos cuando la pieza lo es: así los agujeros y patrones se acotan desde un centro real.
2. Añadidos grandes (protrusiones, nervios), luego cortes y vaciados.
3. Agujeros con el comando Agujero (no con cortes circulares), para que lleven la norma, la rosca y queden como operación de agujero; después los patrones.
4. Redondeos y chaflanes **al final**: son los que más fallan si se modifican operaciones anteriores.
5. Bocetos **totalmente definidos** (relaciones + cotas): un boceto subdefinido se deforma al editar.
6. Nombra las operaciones importantes y comprueba que todas quedan sanas en el PathFinder.

## Listas de chequeo

**Pieza terminada**
- [ ] Todas las operaciones sanas (sin iconos de error ni aviso) y bocetos totalmente definidos.
- [ ] Las medidas clave coinciden con el plano dentro de la tolerancia (caja envolvente, Ø, distancias entre centros, espesores).
- [ ] Material asignado; la masa y el volumen tienen sentido.
- [ ] Propiedades del archivo: título, autor y número.
- [ ] Guardado con el nombre que espera la lista de piezas y sin sobrescribir versiones anteriores.

**Ensamble terminado**
- [ ] Una sola pieza Fijada (la base); ninguna pieza suelta sin relaciones.
- [ ] Cero relaciones con error o suprimidas; ninguna pieza sobredefinida.
- [ ] El mecanismo se mueve como debe (arrastrar componente o motor) y no se separa.
- [ ] Verificar interferencia sin choques reales.
- [ ] Cantidades iguales a la lista de piezas del plano.
- [ ] PathFinder en orden lógico de montaje.

**Plano terminado**
- [ ] Formato y escala normalizados; proyección indicada.
- [ ] Vistas necesarias y suficientes; cortes donde hay interiores.
- [ ] Todas las cotas para fabricar, sin duplicados ni cotas cerradas; tolerancias y notas.
- [ ] Ensamble: vista explosionada, globos vinculados a la lista de piezas, cantidades correctas.
- [ ] Cuadro de rotulación completo; PDF exportado y revisado.

## Errores frecuentes

| Síntoma | Causa típica | Qué hacer |
|---|---|---|
| El perfil no extruye | Perfil abierto, líneas superpuestas o un hueco en un vértice | Revisar los extremos (relación de conexión) y las líneas duplicadas. |
| Falla el redondeo | Radio mayor que la cara adyacente o aristas tangentes | Bajar el radio, redondear en otro orden o separar en varios redondeos. |
| La pieza "salta" al relacionarla | Seguía Fijada, o la relación eligió la cara opuesta | Quitar el Fijar; usar la cara correcta u orientación (Coincidir ↔ Alinear plano). |
| Sobredefinición en el ensamble | Relaciones redundantes (dos que quitan el mismo grado de libertad) | Quitar la redundante (con OK del usuario), no añadir más. |
| La vista del plano quedó desactualizada | Cambió el modelo | Actualizar vistas y revisar las cotas recuperadas. |

## Cuando la tarea se ejecuta con Jarvis

Esta habilidad dice **qué** hacer y **cómo** se hace en Solid Edge; `jarvis-operador` dice cómo ordenárselo a Jarvis sin riesgos y qué funciones tiene ya. Si Jarvis no sabe hacer algo que aquí está descrito, no lo improvises en caliente: regístralo en su backlog (`jarvis-operador/memoria/mejoras_backlog.md`) y propón el parche, o guía al usuario por la interfaz.
