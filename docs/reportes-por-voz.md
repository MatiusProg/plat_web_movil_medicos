# Reportes por voz — cómo está hecho

Característica general 5. Nota corta para el equipo: qué hace cada pieza, qué
pasa cuando algo falla y qué mirar si se rompe.

## El camino, de punta a punta

```
   la persona habla
        │
        │  Web Speech API (Chrome/Edge)  ·  speech_to_text (Android)
        ▼
   texto transcrito EN EL DISPOSITIVO
        │
        │  POST /api/reporting/interpret/   {"text": "...", "dataset": "..."}
        ▼
   reporting/voice.py
        │   1. arma el prompt con datasets.available_for(user)
        │   2. le pregunta a Gemini (JSON estricto, temperature 0)
        │   3. sanea: lo que no está en el catálogo se descarta y se nombra
        │   4. valida con query.build(...) — sin ejecutar
        ▼
   {"understood": true, "definition": {...}, "spoken_summary": "...",
    "unresolved": [...], "generated_by": "gemini"}
        │
        ▼
   el formulario queda lleno · la persona confirma
        │
        │  POST /api/reporting/run/      (el de siempre)
        ▼
   vista previa, Excel, PDF, HTML, CSV o correo
```

**No hay audio en ninguna parte de ese camino.** Transcribe el dispositivo y lo
que viaja es texto. Por eso no hay permisos de almacenamiento, no hay archivos
temporales y no hay nada que borrar después.

## Lo que no se negocia

1. **La voz no ejecuta.** Propone y la persona confirma. El enunciado pide una
   interfaz previa para filtrar; además, una frase mal entendida que exporta
   sola es un reporte equivocado que nadie revisó.
2. **El modelo elige de una lista cerrada**, armada con el catálogo que esa
   persona puede ver. Lo que no puede consultar por pantalla no entra en el
   prompt ni puede salir en la propuesta.
3. **Lo que vuelve se valida igual.** Columna, filtro, operador y orden se
   comprueban contra `datasets.py`; lo que no exista se descarta y se nombra en
   `unresolved`. Nada se ignora en silencio.
4. **Si el proveedor no está, se degrada.** Se adivina el conjunto por su nombre
   y nada más: **ningún filtro inventado**. La respuesta lo dice con
   `generated_by: "plantilla"` y las dos pantallas lo muestran.

## Qué mirar cuando algo falla

| Síntoma | Dónde mirar |
|---|---|
| En la web no aparece el botón de hablar | Firefox no tiene la API; y el micrófono exige **https o localhost**. Por `http://192.168…` no funciona: `useVoz.ts` lo detecta y lo explica |
| En el teléfono no aparece el botón | Falta el reconocedor del sistema, o se negó el permiso. `voice_input.dart::preparar()` devuelve `false` y deja el motivo |
| Entiende el conjunto pero ningún filtro | Casi siempre es `generated_by: "plantilla"`: no hubo clave o se agotó la cuota de Gemini (`GEMINI_API_KEY`, `ASSISTANT_CHAT_PROVIDER`) |
| Dice «no se puede filtrar por X» | El filtro no está declarado en `datasets.py`. Se agrega ahí, en un bloque, y aparece solo en las dos pantallas |
| Entiende de más, con datos ajenos | No debería poder: el catálogo va filtrado por permisos y `query.build` vuelve a exigir el permiso del conjunto. Hay prueba de las dos cosas |

## Archivos

| Pieza | Archivo |
|---|---|
| Interpretación y degradación | `backend/reporting/voice.py` |
| Endpoint y bitácora | `backend/reporting/views.py::InterpretVoiceView` |
| Pruebas del backend | `backend/tests/test_caracteristica_5_voz.py` |
| Micrófono de la web | `frontend/src/componentes/useVoz.ts` |
| Constructor de la web | `frontend/src/paginas/Reportes.tsx` |
| Micrófono del móvil | `mobile/lib/features/reporting/voice_input.dart` |
| Constructor del móvil | `mobile/lib/features/reporting/reports_screen.dart` |
| Pruebas del móvil | `mobile/test/reporting_voz_test.dart` |

## Frases que sirven para probar

- «pacientes mujeres dadas de alta en septiembre, con nombre, documento y teléfono, en Excel»
- «profesionales de cardiología ordenados por apellido»
- «la bitácora de ayer en PDF» — dicha por alguien **sin** permiso de bitácora
  tiene que responder que no se pudo armar, no un archivo.
