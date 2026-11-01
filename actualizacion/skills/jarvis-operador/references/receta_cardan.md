# Receta del Cardán: el método que funcionó, como plantilla para cualquier ensamble

El 2026-10-28 Jarvis armó el Cardán (doble junta universal, 90 ocurrencias, 184 relaciones) **sin una sola relación fallida en la corrida oficial**, con un ensayo previo en temporal. Este documento explica el método, para repetirlo con otros ensambles. El código está en `C:\Jarvis\cardan\ensamblar_cardan.py`. Léelo antes de escribir una receta nueva: sus clases `Geo`, `Pose` y `Ensamble` son reutilizables.

## Contenido
1. Resultado y entregables
2. Método en 7 pasos
3. Reglas geométricas usadas (cómo se elige cada cara)
4. Recetas de unión A–D
5. Cierre de un lazo cinemático
6. Verificación final y prueba de giro
7. Cómo adaptar el método a otro ensamble

---

## 1. Resultado y entregables

| Dato | Valor |
|---|---|
| Piezas | soporte fijo 1 · Fork 4 · eje central 1 · Central Cruz 2 · eje entrada 1 · Eje de salida1 1 · Perno 40 · tuercaM3 40 |
| Relaciones | 184: 1 Fijar, 94 Alinear eje, 89 planares (Coincidir) |
| Tiempos de la corrida oficial | fase 1: 11 s · fase 2: 25 s · fase 3: 26 s · fase 4: 45 s · fase 5: 10 s |
| Prueba de giro | 360,6° de entrada → 360,6° de salida, 44 pasos, sin relaciones rotas |
| Archivos | `Documents\Proyectos_SolidEdge\Cardan\`: `Cardan.asm`, `bitacora_cardan.csv`, `cardan_estado.json`, `verificacion_final.json`, `prueba_giro.json` |

## 2. Método en 7 pasos

1. **Reconocer sin modificar.** Ensamble temporal sin guardar: insertar una ocurrencia de cada pieza y volcar sus caras (`inspeccionar_piezas.py`). Contar agujeros, ejes y bridas, y comprobar que las cantidades cuadran con el plano.
2. **Probar la API con una sola relación** antes del lote. Así se descubrieron la semántica de `NormalsAligned` y el salto por `FixedRotate`.
3. **Escribir reglas geométricas** por tipo de elemento (sección 3). Nunca índices de cara.
4. **Calcular la pose objetivo** de cada pieza antes de insertarla: dónde debe quedar su brida, su eje y sus orejas. En el Cardán, las piezas venían modeladas en las coordenadas del ensamble original, y eso sirvió de oráculo: con relaciones correctas, una pieza nativa no se mueve.
5. **Insertar → quitar Fijar → `PutMatrix` a la pose → relacionar → comprobar que no se movió.** Si se mueve más de 0,05 mm o 0,01°, alguna cara está mal elegida: se detiene sin guardar.
6. **Fases con paradas**, cada una con resumen y guardado; el estado se guarda en `cardan_estado.json` (fases hechas y nombre de la ocurrencia de cada rol). Al reabrir un documento con cambios sin guardar, se detiene.
7. **Verificación final** por script (conteo, fijos, estados, relaciones, huellas) + prueba de giro + revisión visual del usuario (interferencia).

## 3. Reglas geométricas (clase `Geo`)

| Elemento | Regla |
|---|---|
| **Brida** | ≥ 8 cilindros pequeños de igual radio y paralelos, cuyos ejes están en una circunferencia; se agrupan por posición axial (una brida por grupo). Caras de la brida: los planos perpendiculares en los dos extremos de esos agujeros; la **de mayor área es la de apoyo** (disco lleno) y la otra la trasera (anillo). Centrado: el cilindro coaxial de mayor radio dentro del espesor de la brida. |
| **Normal exterior** | `Face.GetNormal(1, [u, v])` en el centro de `GetParamRange`. `GetPlaneData` puede dar la normal al revés. |
| **Horquilla (Fork)** | Agujeros de oreja = cilindros perpendiculares al eje principal **cuya línea corta el eje**; de esos, el de menor radio. Centro de la junta = el corte. Caras interiores de las orejas = planos perpendiculares a las orejas, con la normal hacia el centro, que contienen el punto donde la línea de las orejas los atraviesa. |
| **Cruz** | Dos líneas de cilindros perpendiculares que se cortan (las de mayor área total). Pasador = el cilindro de cada brazo que llega más lejos del centro; punta = el plano perpendicular en ese extremo, con la normal hacia afuera. |
| **Perno** | Vástago = el cilindro de **mayor área** (el de menor radio sería un detalle de 0,2 mm). Punta = el extremo donde el vástago alcanza el borde del cuerpo; cara de apoyo = el plano bajo la cabeza, con la normal hacia la punta. |
| **Tuerca** | El único cilindro es el agujero; las dos caras perpendiculares son las de apoyo. |
| **Soporte** | El agujero coaxial con el eje de entrada; la cara de la placa con la normal hacia el eje. El otro agujero es el de salida. |

## 4. Recetas de unión

| Unión | Relaciones (en este orden) | Resultado |
|---|---|---|
| **A. Eje ↔ soporte** | Alinear eje (cilindro del eje más cercano al agujero, de radio ≤ al del agujero) + Coincidir (punta del eje ↔ cara de la placa) | gira libre |
| **B. Brida rígida** | Coincidir (apoyo ↔ apoyo) + Alinear eje (centrado ↔ centrado) + Alinear eje (un agujero de perno ↔ su agujero coaxial) | rígida |
| **C. Cruz ↔ horquilla** | Alinear eje (pasador ↔ agujero de oreja del mismo lado) + Coincidir (punta del pasador ↔ cara interior de la oreja) | gira en el pasador |
| **D. Perno y tuerca** | Perno: Alinear eje (vástago ↔ agujero de la brida del eje) + Coincidir (bajo cabeza ↔ cara trasera de esa brida). Tuerca: Alinear eje (agujero ↔ vástago) + Coincidir (cara de la tuerca ↔ cara trasera de la brida del Fork) | perno y tuerca giran sobre su eje (normal) |

Detalles que deciden el éxito:
- Todo `AddAxial` se crea dentro de `app.DelayCompute = True`, se pone `FixedRotate = False` y luego `DelayCompute = False`.
- `AddPlanar(..., True, punto1, punto2)` con las normales exteriores opuestas = Coincidir. Los puntos van en coordenadas de pieza: el extremo de una arista de la cara (siempre está sobre ella).
- El flag de `AddAxial` se pone según si los ejes de los cilindros apuntan igual en la pose objetivo.
- La pieza que se coloca va primero en la relación; la de referencia, segunda.

## 5. Cierre del lazo

El Cardán es un lazo cerrado: empieza y termina en el soporte. El cierre se resolvió **analíticamente** antes de insertar las piezas de la segunda junta:
- J1 = centro de la Cruz1 (fijo por el eje de entrada).
- La Cruz1 deja libre el giro alrededor de su otro brazo `q`; el centro J2 de la Cruz2 recorre un círculo de radio `L = 2·f_c + D` (f_c = 12 mm de la brida al centro de la horquilla; D = distancia entre las caras de apoyo del eje central) en el plano perpendicular a `q`.
- J2 = intersección de ese círculo con el eje del agujero de salida del soporte, eligiendo la raíz más cercana al agujero.
- Con J2 se calculan las poses del eje central, Fork3 (orejas paralelas a Fork2: **en fase**), Cruz2, Fork4 y el eje de salida (girado 4,97° para alinear sus agujeros con Fork4).
- El cierre es **solo** Alinear eje (eje de salida ↔ agujero superior). El eje de salida queda libre axialmente y la cadena lo posiciona; así no hay sobredefinición. Grados de libertad: 5 antes del cierre − 4 del cierre = 1 (el giro del mecanismo).

## 6. Verificación

- `--fase 5`: conteo exacto contra el plano, solo el soporte fijo, cero relaciones sin resolver o suprimidas, ninguna ocurrencia sobredefinida (32776) o inconsistente (32784), ninguna sin relaciones, Fork2 y Fork3 en fase, y huellas de los `.par` iguales a las de antes.
- `prueba_giro.py`: `PutMatrix` sobre una pieza relacionada es una *petición*; el solver concede menos (~3° por cada 10° pedidos), como un arrastre real. Por eso la prueba pide pasos de 30° hasta acumular 360° y verifica en cada paso: relaciones resueltas, el eje de salida no se invierte y no se desplaza. Cierra sin guardar.
- Interferencia: `agente\interferencia.py` con `--esperado "Perno.par<>tuercaM3.par"` (el solape de 2,945 mm³ por perno es la rosca modelada). Es solo para la pose guardada: en un mecanismo hay que barrer una vuelta con `agente\barrido_choques.py`. En el Cardán, las orejas de Fork 3 y Fork 4 rozan tuercas de la brida vecina en la junta 2 (28°): 4 tramos por vuelta, ~2,1 mm³. La revisión final la hace el usuario (pestaña Verificar).

## 7. Adaptar a otro ensamble

1. Copia `ensamblar_cardan.py` como `ensamblar_<proyecto>.py` en una carpeta nueva de `C:\Jarvis\`.
2. Cambia `PLANO` (piezas y cantidades) y la carpeta de piezas.
3. Reutiliza `Geo`, `Pose`, `Ensamble`, `receta_B` y `receta_C` si las uniones se parecen. Para uniones nuevas, añade a `Geo` reglas para reconocer las caras y escribe una receta `receta_X` con la misma estructura: validar → crear → comprobar que no se movió → revisar.
4. Si las piezas **no** vienen en coordenadas del ensamble, la pose objetivo se calcula por marcos (`pose_por_marcos`): punto + dos direcciones de la pieza → punto + dos direcciones en el ensamble.
5. Haz un ensayo completo en temporal (`--asm <temporal>\X.asm`) antes de la corrida oficial.
6. Si se va a repetir a menudo, conviértelo en orden de Jarvis (ver `cardan_orden` en `server.py`) y regístralo en `memoria/parches_aplicados.md`. Generalizarlo a una receta JSON es la mejora JRV-20.
