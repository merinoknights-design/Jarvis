# API propia de Jarvis (para escribir recetas sin leer su código)

Funciones de `C:\Jarvis` que se usan para construir: firmas, qué devuelven y sus trampas. Importa así:

```python
import sys; sys.path.insert(0, r"C:\Jarvis")
import se_com_seguro as se
from cad_atomic_lib import add_line, add_arc_by_center, add_arc_by_start_along_end, close_profile_keypoints
```

Ejecuta siempre con `C:\Jarvis\venv\Scripts\python.exe -X utf8 <script>`. **Unidades internas: metros** (escribe `mm = 0.001` y usa `60 * mm`).

## Contenido
1. `se_com_seguro.py`: conexión, archivos, ocurrencias, caras, relaciones, bitácora
2. `cad_atomic_lib.py`: bocetos y operaciones de pieza (qué usar y qué no)
3. Constantes verificadas
4. Plantilla de pieza (`scripts/plantilla_pieza.py`)
5. Clases del Cardán reutilizables

---

## 1. `se_com_seguro.py`

| Función | Qué hace | Notas |
|---|---|---|
| `conectar(lanzar=True, espera_max=240)` → `app` | Se engancha a Solid Edge; si no está abierto y `lanzar=True`, lo abre (~20 s) y espera a que responda. Pone `Visible=True` y `DisplayAlerts=False`. | Nunca cierra ni mata Solid Edge. Con `lanzar=False` lanza `ErrorSolidEdge` si no está abierto (útil para solo mirar). |
| `reintentar(fn, *args, intentos=40, espera=0.25, **kw)` | Llama a `fn` y reintenta **solo** si Solid Edge está ocupado (`RPC_E_CALL_REJECTED`, `RETRYLATER`). Otros errores suben tal cual. | Envuelve con esto cada llamada COM que cree o guarde algo. |
| `describir_error(e)` → str | Texto legible de un `com_error`. | Para la bitácora. |
| `ErrorSolidEdge` | Excepción con mensaje para el usuario. | |
| `sha256(ruta)` · `huellas(carpeta, "*.par")` → dict | Huellas de archivos. | Antes y después de tocar archivos del usuario. |
| `guardar_nuevo(doc, ruta)` → Path | `SaveAs` **solo si la ruta no existe**; si existe, `FileExistsError`. Comprueba que el archivo apareció. | Nunca sobrescribe: Solid Edge abriría un diálogo que lo bloquea. |
| `ruta_libre(ruta)` → Path | La ruta, o `_2`, `_3`… si ya existe. | Para nombres automáticos. |
| `insertar(asm, ruta_par)` → Occurrence | `Occurrences.AddByFilename`. | La ocurrencia nace **Fijada**: llama a `quitar_fijo` salvo para la base. |
| `quitar_fijo(occ)` → int · `es_fija(occ)` → bool · `relaciones_de(occ)` → list | Gestionar Fijar. | |
| `matriz(occ)` → 16 floats | `GetMatrix`. `p_asm = R·p + t`, `R[i][j] = M[4j+i]`, `t = M[12:15]`. | `occ.PutMatrix(M, True)` para mover. |
| `a_ensamble_punto(M, p)` · `a_ensamble_dir(M, v)` | Pasar de coordenadas de pieza a ensamble. | |
| `caras(occ)` → list | Todas las caras del cuerpo de la pieza de la ocurrencia. | |
| `describir(cara)` → dict | `{"area", "tipo": "plano"|"cilindro"|"cono"|"toro"|"otro", ...}`. Plano: `raiz`, `normal` (¡no siempre la exterior!). Cilindro: `base`, `eje`, `radio`. En **coordenadas de pieza, metros**. | Normal exterior: `cara.GetParamRange` + `cara.GetNormal(1, [u, v])` (ver `ensamblar_cardan.py`). |
| `rango_cara(cara)` → `[min, max]` | Caja de la cara. | |
| `puntos_arista(cara)` → list | Extremos de aristas (siempre sobre la cara). | Buenos puntos de restricción para `AddPlanar`. |
| `ref(asm, occ, entidad)` | `asm.CreateReference` con reintento. | Toda relación de ensamble necesita referencias, no caras sueltas. |
| `estado_ensamble(asm)` → dict | `{"ocurrencias": [{nombre, archivo, status, fija}], "relaciones": [{i, tipo, status, suprimida}]}`. | Relación sana `status 1`; ocurrencia 2 fija · 4 subdefinida · 32776 sobredefinida · 32784 inconsistente. |
| `Bitacora(ruta_csv)` · `.anotar(fase, piezas, caras, accion, relacion, estado, error)` | CSV con hora. | Una por proyecto o ensayo. |

## 2. `cad_atomic_lib.py`

| Función | Úsala | Notas |
|---|---|---|
| `add_line(prof, x1, y1, x2, y2)` | ✅ | `Lines2d.AddBy2Points`. |
| `add_arc_by_center(prof, cx, cy, sx, sy, ex, ey)` · `add_arc_by_start_along_end(...)` | ✅ | Arcos verdaderos. |
| `add_circle(prof, cx, cy, r)` | ⚠️ | Además añade una cota de radio; si no la quieres: `prof.Circles2d.AddByCenterRadius(cx, cy, r)`. |
| `close_profile_keypoints(prof, [elementos en orden])` | ✅ | Une fin con inicio con relaciones de punto clave (líneas: 0 inicio, 1 fin; arcos: 1 inicio, 2 fin). |
| `add_sketch_profile(doc, plano)` | ✅ | `plano`: 1 Superior (XY) · 2 Derecho (YZ) · 3 Frontal (XZ). |
| `create_base_protrusion(doc, prof, depth, side)` | ✅ | Desde JRV-11 valida el perfil (`End(igProfileClosed)`) y lanza `ValueError` si está abierto. |
| `add_extruded_cutout(model, prof, depth, side, extent)` | ⚠️ | `side` = **qué lado del perfil se quita**. ⚠️ En este módulo **`igRight = 1` e `igLeft = 2` están invertidos** respecto a la type library (JRV-67): con un círculo, el `igRight` *de este módulo* (= 1) quita el interior, que es lo correcto para un agujero. En código nuevo usa `SE_LEFT = 1` / `SE_RIGHT = 2`. Comprueba siempre el volumen quitado con `verify_removed_volume`. |
| `add_revolved_cutout(model, prof, axis_line, ang)` | ✅ | Valida perfil cerrado + eje. Misma advertencia de lado. |
| `apply_fillets_geometric(model, filtro, r)` | ✅ con filtro propio | Traga los errores: comprueba el estado de la operación. |
| `verify_feature_status(model)` → `(sana, status, nombre)` | ✅ desde JRV-11 | Mira la **última** operación. Sana = `FEATURE_OK` o `FEATURE_WARNED`. |
| `verify_removed_volume(model, vol_antes_m3, esperado_m3, rel_tol=0.005)` → `(ok, quitado_m3)` | ✅ nuevo | Toma `vol_antes = float(model.Body.Volume)` antes del corte. Detecta cortes que quitaron el lado equivocado o nada. |
| `bounding_box_mm(body)` → `{x, y, z}` | ✅ nuevo | Caja envolvente correcta (`GetRange`). |
| `get_model_physical_properties(model)` | ✅ desde JRV-11 | Volumen, caras, aristas y caja; los errores van en claves `*_error`. |
| Constantes | — | `FEATURE_OK/FAILED/WARNED/SUPPRESSED/ROLLEDBACK`, `PROFILE_CLOSED`, `PROFILE_REF_AXIS_REQUIRED`, `SE_LEFT/SE_RIGHT/SE_SYMMETRIC`. |

`cad_validator.validate_part_model_health(doc)` también está corregido (JRV-11): devuelve `failed_features`, `warned_features`, volumen y caja reales. La prueba de regresión de estas funciones es `C:\Jarvis\pruebas\regresion_jrv11.py`: ejecútala después de cualquier cambio en estos módulos.

## 3. Constantes verificadas (type library de SE 2026)

| Grupo | Valores |
|---|---|
| Lado / extensión (`FeaturePropertyConstants`) | `igLeft 1` · `igRight 2` · `igSymmetric 3` · `igFinite 13` · `igThroughAll 16` · `igNormal 20` |
| Estado de operación (`Feature.Status`) | `igFeatureOK 1216476310` · `igFeatureFailed 1216476311` · `igFeatureWarned 1216476312` · `igFeatureSuppressed 1216476313` · `igFeatureRolledBack 1216476314` |
| Validación de perfil (`Profile.End`) | `igProfileClosed 1` · `igProfileSingle 4` · `igProfileNoSelfIntersect 8` · `igProfileRefAxisRequired 16` (revoluciones) |
| Modo de modelado (`doc.ModelingMode`) | `2` = ordenado |

Firmas de operaciones de pieza (verificadas): `Models.AddFiniteExtrudedProtrusion(n, [perfiles], lado, distancia)` · `Models.AddFiniteRevolvedProtrusion(n, [perfiles], eje, lado, ángulo)` · `ExtrudedCutouts.AddFinite(perfil, ladoPerfil, ladoPlano, profundidad)` · `ExtrudedCutouts.AddThroughAll(perfil, ladoPerfil, ladoPlano)` · `Holes.AddFinite(perfil, ladoPlano, profundidad, HoleData)` · `Profile.SetAxisOfRevolution(línea)` · `Body.GetRange(min, max)` / `GetExactRange`. Para cualquier otra: `solid-edge-experto/scripts/firmas_api.py`.

## 4. Plantilla de pieza

`%USERPROFILE%\.claude\skills\jarvis-operador\scripts\plantilla_pieza.py`, probada en vivo el 2026-10-28 (bloque 60 × 40 × 10 con agujero Ø10: caja y volumen exactos).

Para una pieza nueva: cópiala a la carpeta del proyecto (`C:\Jarvis\proyectos\<proyecto>\piezas\<pieza>.py`, ver SKILL.md), cambia `construir()` y `ESPERADO`, ensaya en `%TEMP%\jarvis_ensayos\<pieza>\` y, cuando el usuario apruebe, guarda la oficial en `Documents\Proyectos_SolidEdge\<Proyecto>\Piezas\`. Trae: modo ordenado, comprobación del estado real de cada operación, comprobación del volumen quitado por cada corte, verificación final de caja y volumen, guardado sin sobrescribir y bitácora.

## 6. API de agentes y acciones (JRV-01/02/03/05/06, 2026-10-28)

- Servidor: `C:\Jarvis\api_agente.py` (router en `server.py`). Acciones: `C:\Jarvis\agente\acciones.py`, en un proceso aparte.
- También se puede llamar sin servidor: `python -X utf8 C:\Jarvis\agente\acciones.py <accion> @parametros.json`. El `@archivo` existe porque PowerShell 5.1 se come las comillas dobles del JSON en línea. La última línea de la salida es `@@RESULTADO@@ {json}`.
- Registro de cada tarea: `id`, `accion`, `parametros`, `estado` (`en_cola` · `ejecutando` · `ok` · `error` · `parada` · `rechazada`), `inicio`, `fin`, `duracion_s`, `codigo_salida`, `resultado` (JSON de la acción), `salida` (últimos 6000 caracteres), `avisos` (p. ej. disco bajo).
- `receta` solo ejecuta `.py` de `C:\Jarvis\{proyectos,cardan,pruebas,agente}`; el `timeout_s` por defecto es 1800.
- **Capturas**: la validación mide la fracción de píxeles distintos del fondo (≥ 1 %). Una vista con solo los ejes de referencia da ~0,04 %. Probado: pieza 14,9 %, ensamble de prueba 10,2 %. Si el ensamble tiene piezas ocultas y lo abrió Jarvis, las muestra; si faltan archivos de pieza, lo dice en `causa_probable`.
- Nombres de vista que funcionan en SE 2026 en español: `ApplyNamedView("Iso")`. El cubo de vistas muestra "Planta", "Alzado" y "Derecha".

## 7. Herramientas de producción (2026-10-30)

Todas están en `C:\Jarvis\agente\` y se ejecutan con la acción `receta` de la API (`script`, `args`) o directamente. La última línea de su salida es `@@RESULTADO@@ {json}`. Ninguna sobrescribe ni toca archivos del usuario. La documentación completa del formato está en el docstring de cada una.

| Herramienta | Para qué | Uso |
|---|---|---|
| `receta_pieza.py` | Construir una pieza desde una receta JSON en mm. Operaciones: protrusión, corte, revolución, corte de revolución, redondeo, chaflán, **agujero** (Ø o rosca `M…`, pasante o ciego) y **patron** (circular o rectangular de otra operación con nombre). Detalle en su docstring. Ejemplos probados: `C:\Jarvis\pruebas\recetas\{brida_prueba,eje_prueba,base_prueba,tapa_prueba,placa_agujeros,brida_patron}.json` | `receta_pieza.py receta.json [--cerrar]` |
| `receta_ensamble.py` | Ensamble con relaciones desde una receta JSON (piezas, relaciones, orden y nombres del PathFinder). Ejemplo: `pruebas\recetas\ensamble_prueba.json` | `receta_ensamble.py receta.json [--cerrar]` |
| `caras.py` + acción `caras` | Ver las caras de una pieza (normales exteriores, ejes, diámetros) para escribir los selectores | acción `caras {ruta}` |
| `motor.py` | Girar una pieza por pasos, medir la seguidora y hacer el video | `motor.py asm --pieza "X.par:1" --diametro 14 --seguir "Y.par:1" --grados 360 --video salida.mp4` |
| `explosion.py` | Pseudo-explosión en una copia (para vistas e imágenes) | `explosion.py asm salida_explosionado.asm --factor 1.9 [--eje x]` |
| `plano.py` | Plano de pieza o de ensamble (lista + globos) con PDF | `plano.py modelo salida.dft --pdf --titulo … --autor … --numero …` |
| acción `exportar` | STEP/STL/IGES/Parasolid/PDF | acción `exportar {ruta, salida}` |
| `vinculos.py` | Listar o redirigir los vínculos de un ensamble movido | `vinculos.py listar asm` · `redirigir asm vieja nueva` |
| `interferencia.py` + acción `interferencia` | Detectar choques en un ensamble (2026-10-31): choques reales, contactos, esperados; nunca guarda. Usa `csharp\InterferenciaTipada.exe` | `interferencia.py asm [--umbral 1.0] [--ignorar-roscas] [--esperado "A.par<>B.par"]` · acción `interferencia {ruta, umbral_mm3, ignorar_roscas, esperados}` |
| `barrido_choques.py` | Choques durante el giro de un mecanismo (2026-11-01): tramos con pareja, ángulos, pico y máximo. Nunca guarda; se niega si el ensamble ya está abierto. Una vuelta del Cardán tarda unos 5 min | `barrido_choques.py asm --pieza "eje entrada.par:1" --diametro 14 --esperado "Perno.par<>tuercaM3.par" [--grados 360] [--cada 5] [--paso 30] [--informe salida.json]` |
| `C:\Jarvis\rutas_se.py` | Dónde está Solid Edge en este equipo, según el registro. `JARVIS_SE_RAIZ` en `.env` la fuerza | `python -X utf8 C:\Jarvis\rutas_se.py` |
| `csharp\compilar.py` | Genera en este equipo el interop tipado e `InterferenciaTipada.exe` | `python -X utf8 C:\Jarvis\agente\csharp\compilar.py` |
| `tornilleria.py` | Inventario de tornillería y agujeros de un ensamble con designación deducida (sugerencia, no certeza) | `tornilleria.py asm` |
| `editar_pieza.py` | Corregir una pieza existente sin rehacerla: ver sus cotas y cambiar las que hagan falta → pieza nueva | `editar_pieza.py listar par` · `cambiar par salida.par --cota V340=25 --profundidad "Protrusión 1"=12` |
| `C:\Jarvis\pruebas\correr_todo.py` | Regresión completa (21 casos + 2 del Cardán) | `correr_todo.py [--cardan]`. Ejecútala tras cualquier parche |

## 5. Clases del Cardán reutilizables

En `C:\Jarvis\cardan\ensamblar_cardan.py`:
- `Geo`: reconoce bridas, horquillas, cruces, pernos, tuercas y soportes por reglas geométricas.
- `Pose`: poses objetivo y conversión por marcos.
- `Ensamble`: `coincidir`, `alinear_eje` (con `DelayCompute` y `FixedRotate=False`), `receta_B` (brida rígida), `receta_C` (cruz-horquilla) y `revisar` (comprueba que nada se movió).

Detalle del método: `references/receta_cardan.md`.
