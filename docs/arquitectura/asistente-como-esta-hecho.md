# El asistente de orientación: qué tipo de IA es y cómo está hecho

Documento de arquitectura del subsistema de inteligencia artificial (Épica 7,
US-31 · US-32 · US-34). Sirve para dos cosas: entender el código sin leerlo
entero, y **poder defenderlo** ante la docente sin decir "es una IA" y quedarse
ahí.

Estado al 16/09/2026: US-31 funcionando en desarrollo y en el despliegue de
Railway, sobre datos reales de dos organizaciones.

---

## 1. Qué tipo de IA es — y qué no es

Es un **RAG**: *Retrieval-Augmented Generation*, generación aumentada por
recuperación. En una frase: **primero se busca en nuestros datos, después se
redacta usando sólo lo que se encontró.**

Lo que esto **no** es, y conviene decirlo antes de que lo pregunten:

| No es | Por qué importa |
|---|---|
| Un modelo entrenado por nosotros | No hay entrenamiento ni *fine-tuning*. No hay dataset de entrenamiento ni época ni pérdida que mostrar, porque no es ese tipo de sistema |
| Un chatbot de propósito general | No contesta sobre cualquier tema: si la pregunta no se parece a nada del catálogo de esa organización, contesta que no sabe |
| Un modelo que "sabe" medicina | No diagnostica. Sugiere **a qué especialidad consultar**, que es un problema de orientación, no de clínica |
| Una conversación con memoria | Cada pregunta es independiente. La conversación con estado es US-33, que quedó para el Sprint 3 |

**Por qué RAG y no un modelo entrenado.** Un clasificador supervisado —"dado un
síntoma, predecir la especialidad"— necesita ejemplos etiquetados que no
existen: el centro médico recién empieza a operar. El RAG no necesita ejemplos,
necesita **texto descriptivo**, que sí existe: las descripciones de
especialidades que se cargan en US-12. Además, cuando una organización agrega
una especialidad nueva, el RAG la incorpora ejecutando un comando; un modelo
entrenado habría que reentrenarlo.

> El caso del clasificador supervisado sí aparece más adelante en el proyecto:
> es US-35 a US-38, la predicción de *no-show*, que necesita fichas con
> resultado *asistió / no asistió* para tener etiquetas. Son dos tipos de IA
> distintos en el mismo sistema, y conviene no mezclarlos al explicarlos.

---

## 2. Las cuatro piezas, en el orden en que corren

```
    pregunta del paciente
            │
            ▼
    ┌───────────────────┐
    │ 1. BARRERA        │  triage.py — reglas, sin modelo
    │    ¿es urgencia?  │  si sí: corta acá y deriva a emergencias
    └───────┬───────────┘
            │ no es urgencia
            ▼
    ┌───────────────────┐
    │ 2. RECUPERACIÓN   │  retrieval.py — pgvector, distancia coseno
    │    ¿qué se le     │  filtrado por organización, con umbral
    │    parece?        │  si nada supera el umbral: "no sé"
    └───────┬───────────┘
            │ fragmentos recuperados
            ▼
    ┌───────────────────┐
    │ 3. REDACCIÓN      │  generation.py — Gemini, sólo sobre lo recuperado
    │    ¿cómo se dice? │  si el modelo no responde: plantilla
    └───────┬───────────┘
            ▼
    respuesta + los fragmentos que la respaldan
```

La pieza 0 es la **indexación** (`indexing.py`, comando `embed_catalog`), que
no corre por pregunta sino cuando cambia el catálogo.

### 0. Indexación — de dónde sale lo que el asistente sabe

El corpus **es el catálogo de la organización**, no un archivo de prompts. Si
el asistente contesta algo, es porque está en el catálogo de ese centro médico.

Cada descripción de especialidad se parte **por oraciones**
(`split_into_fragments`), y cada oración se guarda como un fragmento propio
precedido del nombre: `"Especialidad: Cardiología. <oración>"`. Partir por
oración es deliberado: un fragmento chico y específico se recupera mejor que un
párrafo largo donde la frase útil queda diluida.

Eso obliga a que el texto del catálogo esté **escrito en palabras de paciente**.
"Cardiología: corazón y sistema circulatorio" describe bien y no se recupera
nunca, porque nadie consulta escribiendo "sistema circulatorio". La versión que
sirve enumera motivos de consulta: *"dolor u opresión en el pecho, palpitaciones,
presión alta…"*. Medido sobre las cinco especialidades sembradas, con las
descripciones nuevas **10 de 10 preguntas de prueba caen en la especialidad
correcta**.

**La referencia médica (30/09).** Además del catálogo, `medical_reference.py`
trae motivos de consulta para catorce especialidades comunes: Medicina general,
Cardiología, Neumología, Endocrinología, Pediatría, Ginecología, Urología,
Dermatología, Traumatología, Neurología, Oftalmología, Gastroenterología,
Otorrinolaringología y Psicología. Salen de **MedlinePlus en español**
(Biblioteca Nacional de Medicina de EE. UU.) y de las notas descriptivas de la
**OMS**, y cada oración cita las páginas que la respaldan.

- **Redactadas con palabras propias**, en lenguaje de paciente. No se copió
  texto: el repositorio es público, y la enciclopedia A.D.A.M. que aloja
  MedlinePlus tiene derechos de autor.
- **Sólo entran para especialidades que el centro ya tiene**, reconocidas por
  su nombre o un alias exacto ("Ortopedia" → Traumatología), y **con el nombre
  que usa el centro**. La referencia no puede hacer aparecer una especialidad
  que el centro no ofrece, ni cruzar datos entre organizaciones: se copia al
  índice de cada una, que sigue bajo RLS.
- **Van detrás del texto del catálogo**, que sigue siendo de la organización.
- **Respaldo en fuentes no es validación clínica.** Nadie del equipo es
  médico. Las fuentes permiten comprobar cada oración, pero la revisión de un
  profesional sigue pendiente.
- **Con Gemini, no con el proveedor local.** `ASSISTANT_MEDICAL_REFERENCE`
  vale `auto`: se enciende con Gemini y se apaga con el proveedor local, que
  compara palabras y con más fragmentos acumula ruido.

Medido con Gemini sobre `morita2`, con 15 preguntas escritas con palabras que
la descripción del catálogo no usa y 8 preguntas ajenas:

| | aciertos | del catálogo | ajenas | hueco |
|---|---|---|---|---|
| sin referencia | 14/15 | 0,638 – 0,737 | 0,512 – 0,590 | 0,049 |
| con referencia | **15/15** | 0,738 – 0,803 | 0,512 – 0,590 | **0,148** |

El hueco entre lo que el asistente debe contestar y lo que no se triplica, y el
umbral de 0,62 sigue valiendo. **Después de desplegar hay que reindexar**:
`python manage.py embed_catalog --all`.

### 1. Barrera de emergencia (US-34) — reglas, no modelo

`triage.py` compara el texto normalizado contra una lista de señales
—"no puedo respirar", "me duele el pecho", "convulsión"…— y **corre antes que
todo lo demás**. Si dispara, no se recupera nada, no se llama al modelo y no se
sugiere ninguna especialidad.

Es a propósito que **no** use similitud vectorial:

- una barrera de seguridad tiene que ser **explicable** —"disparó por esta
  frase"— y no depender de un umbral que se mueve;
- no puede depender de que un proveedor externo responda;
- se prefiere que **sobre-derive**: mandar a emergencias a alguien que no lo
  necesitaba cuesta una consulta; no mandar a quien sí, cuesta otra cosa.

Va primero porque, si dependiera de la respuesta del modelo, una caída del
proveedor dejaría a alguien con un dolor de pecho sin derivación.

**La segunda capa, en el prompt del sistema.** Las reglas sólo reconocen lo
que la lista nombra. Para lo demás, el prompt de `generation.py` le ordena al
modelo que ante una posible urgencia responda exactamente `[[URGENCIA]]` y
nada más. Si la marca aparece, el endpoint deriva igual que con la primera
capa. Tres detalles:

- **El modelo no redacta la derivación.** Sólo levanta la marca; el mensaje
  es siempre el de `triage.py`, revisado, y no la frase que el modelo elija
  ese día.
- **Una capa sólo puede escalar.** Si las reglas ya derivaron, el modelo ni se
  consulta: no hay nada que pueda contestar para deshacerlo.
- **Se lo consulta aunque no haya fragmentos**, sólo por la marca. Lo que no
  se parece a nada del catálogo ("siento que me voy a morir") es lo que más
  probablemente sea una urgencia. El texto que redacte sin contexto se
  descarta.

Con el proveedor local —pruebas, o Gemini caído— la segunda capa no corre y
queda sólo la primera. Por eso la primera es la obligatoria.

**Cada derivación queda en la bitácora de US-06** como
`assistant.emergency`, con la capa que la disparó (`regla` o `modelo`). Las
consultas normales quedan como `assistant.query`. En ningún caso se guarda el
texto de la consulta ni las señales que dispararon: son información de salud.

### 2. Recuperación — dónde vive el multi-inquilino

Los fragmentos se guardan en `assistant_catalog_fragments`, con una columna
`embedding` de tipo `vector(768)` de **pgvector**, la extensión de PostgreSQL
para búsqueda por similitud.

- **Distancia coseno** entre el vector de la pregunta y el de cada fragmento.
- **Índice HNSW** (`vector_cosine_ops`). Es HNSW y no IVFFlat porque IVFFlat
  necesita datos para construirse: creado sobre una tabla vacía queda inservible
  hasta que alguien lo reconstruya, y nadie se acuerda de reconstruirlo.
- **El filtro por organización va en el `WHERE`, antes del `ORDER BY`.** Es la
  regla 9 del Sprint 2 y no es estilo: ordenar el índice completo y quedarse
  después con las filas propias devuelve lo mismo habiendo recorrido datos
  ajenos, y con un `LIMIT` antes del filtro devuelve además menos filas de las
  pedidas, sin explicar por qué.
- **RLS encima**, con `FORCE ROW LEVEL SECURITY` y la política
  `tenant_isolation`, igual que cualquier otra tabla del inquilino. Las dos
  capas son deliberadas: el filtro explícito documenta la intención, RLS lo hace
  cumplir aunque la función se llame desde un comando.

Esto es el apartado 1.1.6 del documento aplicado a la IA, y es el diferencial
del proyecto: **el aislamiento entre organizaciones alcanza al asistente**. Una
organización no puede recuperar el catálogo de otra.

**El umbral.** Si ningún fragmento supera la similitud mínima, la respuesta es
"no puedo orientarte" en lugar de la especialidad menos lejana — que con cinco
especialidades siempre existe. Ese "algo" es lo que un modelo de lenguaje
convierte en una recomendación médica inventada.

El umbral **se mide, no se elige**. Medición del 16/09 con
`gemini-embedding-001`, 17 preguntas sobre el catálogo sembrado:

| | mínimo | máximo |
|---|---|---|
| preguntas del catálogo (10) | **0,637** | 0,762 |
| preguntas ajenas (7) | 0,518 | **0,608** |

Hueco real: **0,029**. El umbral queda en **0,62**, al medio. Es estrecho, así
que **al cambiar el corpus o el modelo hay que volver a medirlo**, no heredarlo.
El procedimiento está en `config/settings.py`, junto al valor.

### 3. Redacción — el modelo de lenguaje, acotado

Recién acá aparece el LLM, y con dos límites: el prompt del sistema le prohíbe
usar cualquier cosa que no esté en los fragmentos recuperados, y **si no
responde, la respuesta se arma con lo recuperado** y sale marcada como
`generated_by: "plantilla"`.

Ese campo es parte del contrato y se mira: dice `gemini` si redactó el modelo,
`plantilla` si se armó con lo recuperado, y `regla` si cortó la barrera de
emergencia.

---

## 3. El proveedor: Gemini, y por qué hay uno local

**Gemini** (`google-genai`), por el nivel gratuito, que incluye los
*embeddings* — que es lo que el RAG consume de verdad: una vez por fragmento al
indexar y una por pregunta.

- `gemini-embedding-001` para vectorizar, **768 dimensiones** truncadas de 3072
  y **normalizadas a mano**, porque el modelo normaliza los vectores completos
  pero no los truncados. La dimensión **es** la definición de la columna:
  cambiarla obliga a recalcular el índice entero.
- `gemini-3.5-flash-lite` para redactar. El `flash` grande devuelve `503 — high
  demand` en el nivel gratuito (cinco de cinco intentos el 16/09); el `lite`
  responde en 0,8 s.

**Y un proveedor local determinista** (`ASSISTANT_EMBEDDING_PROVIDER=local`),
léxico, que no sale a la red. No es un atajo: es lo que permite que las pruebas
no dependan de la cuota ni de que el modelo cambie de opinión entre dos
corridas, y que el proyecto se levante en una máquina sin clave.

> **Al cambiar de proveedor hay que reindexar.** Los vectores de dos modelos
> distintos no se comparan entre sí: mezclarlos no da error, da distancias que
> no significan nada. Por eso cada fila guarda `embedding_model`, y por eso esa
> columna se mira antes de confiar en un índice.

---

## 4. La interfaz

`POST /api/assistant/suggest/`, autenticado, con el permiso
`assistant.suggest.use`. **La organización sale del token, nunca del cuerpo de
la petición**: un endpoint de IA que acepta el inquilino por parámetro es la
forma más corta de leer el catálogo de otra organización.

```jsonc
// pide
{ "question": "tengo la presión alta y palpitaciones" }

// contesta
{
  "emergency": false,
  "answer": "Te sugiero consultar con Cardiología, ya que aborda…",
  "generated_by": "gemini",          // gemini | plantilla | regla
  "specialty":    { "id": "…", "name": "Cardiología", "similarity": 0.725 },
  "alternatives": [ … ],
  "fragments":    [ { "text": "…", "source_name": "Cardiología",
                      "similarity": 0.725, … } ],
  "retrieval":    { "embedding_model": "gemini-embedding-001" }
}
```

**El arreglo `fragments` es parte del contrato, no información de depuración.**
Es la única evidencia de que el asistente no alucinó: recuperó primero y
respondió después, y ahí está lo que recuperó. Es también lo que hay que señalar
al mostrarlo — no la especialidad sugerida, que es lo que cualquiera espera ver.

---

## 5. Cómo se prueba que no inventa

`backend/tests/test_us31.py`, 13 pruebas que se corren con
`pytest tests/test_us31.py`. Las que sostienen las afirmaciones de este
documento:

| Prueba | Qué fija |
|---|---|
| `…devuelve_la_especialidad_que_corresponde` | el camino feliz |
| `…trae_los_fragmentos_que_la_respaldan` | la respuesta viaja con su evidencia |
| `…no_inventa_una_especialidad` | bajo el umbral, contesta que no sabe |
| `…dos_organizaciones_devuelve_catalogos_distintos` | el aislamiento |
| `…no_se_ven_desde_la_otra` | el aislamiento, a nivel de filas |
| `…una_urgencia_corta_el_flujo…` | la barrera de US-34 |
| `…formas_de_decir_dolor_de_pecho_derivan_todas` | la barrera no depende de la redacción |
| `…reindexar_reemplaza_los_fragmentos…` | reindexar no duplica |
| `…una_especialidad_dada_de_baja_no_queda_en_el_indice` | el índice sigue al catálogo |

`backend/tests/test_us34.py` fija las dos capas de la derivación y su asiento
en la bitácora. La segunda capa se prueba simulando al proveedor
(`generation._call_model`): lo que se verifica es que si el modelo levanta la
marca el endpoint deriva, no que el modelo la levante.

Requieren **pgvector instalado**: la columna `vector` es parte del esquema, así
que sin la extensión no se crea ni la base de pruebas. Ver
`docs/entorno/sin-docker.md`.

---

## 6. Lo que falta

- **US-32** — corpus administrativo: sucursales, horarios, costos y
  preparaciones previas. Reutiliza este mismo índice y este mismo endpoint;
  sólo amplía el corpus.
- **Revisión clínica** de dos cosas: las señales de `triage.py` y la
  referencia médica. El 30/09 las dos se revisaron contra MedlinePlus y la
  OMS —cada señal y cada oración citan su fuente, y la revisión eliminó
  falsos positivos como "me tome", que derivaba "me tomé la presión"—, pero
  respaldo en fuentes no es validación de un profesional.
- **El número de emergencias de Bolivia.** El mensaje de derivación dice
  "llamá al número de emergencias" sin dar ninguno, a propósito: las fuentes
  consultadas no coinciden (el Ministerio de Salud habla de un número unificado,
  el 168, y otras fuentes citan el 118, el 160 o el 165 según la ciudad). Hay
  que confirmarlo antes de ponerlo, y probablemente sea un dato por
  organización.
- **US-33** — reservar conversando, en el Sprint 3, cuando US-17 exista.
