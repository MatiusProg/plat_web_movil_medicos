# Sprint 2 — Reparto de historias y alcance por integrante

**Fechas:** 12/09/26 – 05/10/26 · **Revisión de Sprint:** 06–08/10/26
**Corte de avance ante la docente:** **miércoles 16/09/26, 19:00**

**Objetivo:** cerrar el circuito completo de la ficha —reservar, pagar,
presentarse y ser atendido— y **adelantar el subsistema de inteligencia
artificial**, que el documento ubicaba en el Sprint 3, para que el asistente de
orientación esté funcionando sobre el catálogo real de cada organización.

Este documento es el contrato de trabajo del sprint: dice quién hace qué, en
qué archivos, de quién depende y para cuándo. Si vas a escribir código —o si le
vas a pedir a una IA que lo escriba por vos— leé primero la sección de tu
nombre y después la sección 6, que son las reglas que rompen el aislamiento
multi-inquilino si se ignoran.

Las convenciones de código están en `../../convenciones-de-codigo.md`. El
reparto del sprint anterior, en `../sprint-1/reparto.md`.

---

## 0. Qué cambió respecto del plan del documento

Tres cosas, y conviene tenerlas presentes antes de leer el reparto.

**1. El equipo pasó de seis a cinco.** Michael Mamani queda fuera del reparto.
Sus tres historias del Sprint 1 —US-05, US-09 y US-10, 16 h— entran a este
sprint repartidas entre quienes ya son dueños de esos módulos. La docente
mencionó la posibilidad de incorporar un reemplazo; la sección 8 dice
exactamente qué tomaría esa persona sin obligar a rehacer el reparto.

**2. La Épica 7 (chatbot RAG) se adelanta del Sprint 3 a este sprint.**
Entran **US-31, US-32 y US-34** —36 h—. Es la prioridad número uno del sprint
y lo que se muestra el 16/09. La sección 3 explica por qué estas tres y no las
otras.

**3. Dos historias se corren al Sprint 3** para hacer sitio: **US-23**
(agendamiento asistido en mostrador, 10 h, *Should*) y **US-33** (reserva
conversacional, 16 h, *Should*), esta última porque depende de que US-17 esté
terminada.

El total del proyecto no cambia: son las mismas 436 h, movidas de sprint.

| Sprint | Plan del documento | Plan vigente |
|---|---|---|
| Sprint 2 | US-17 a US-25 · 100 h | US-17 a US-22, US-24, US-25 + US-05, US-09, US-10 + **US-31, US-32, US-34** · **142 h** |
| Sprint 3 | US-26 a US-34 · 100 h | US-26 a US-30 + US-33 + US-23 · 74 h |

---

## 1. Reparto

| Integrante | Historias | Web | Móvil | Horas |
|---|---|---|---|---|
| Ortega Mancilla, Karen Paola | **US-31**, **US-34**, US-05 *(deuda S1)* | US-05 | US-31, US-34, US-05 | **30** |
| Iporo Chulque, José Daniel | **US-32**, US-22, US-09 *(deuda S1)*, US-10 *(deuda S1)* | US-32 *(backend)*, US-22, US-09, US-10 | — | **28** |
| Hurtado Castro, Luis Mateo *(SM)* | US-24, US-25 · + documentación | US-24, US-25 | — | **26** |
| Aguayo Quiroz, Luis Miguel | US-17, US-20 | backend de ambas | US-17, US-20 | **26** |
| Osinaga Blanco, Alexander *(PO)* | US-18, US-19, US-21 | — | US-18, US-19, US-21 | **32** |

**Total comprometido: 142 horas** · 5 integrantes · 28,4 h por integrante.

**14 historias:** las 8 del Sprint 2 que se conservan, las 3 de deuda del
Sprint 1 y las 3 del chatbot adelantadas del Sprint 3.

**Ritmo.** El sprint dura 24 días corridos. 28,4 h por persona son ~1,2 h por
día y por persona: por debajo del ritmo del Sprint 1 (1,9 h/día), que se
entregó. La carga total es mayor, pero el sprint también es más largo.

---

## 2. El corte del miércoles 16/09 — qué se muestra

Son **dos días útiles** (lunes 15 y martes 16). Lo que se presenta no es una
historia terminada: es el **camino vertical del asistente funcionando de punta
a punta sobre datos reales**, aunque sea con una sola pregunta y una sola
organización. Eso es lo que la docente pidió ver.

| Quién | Qué lleva el 16/09 | Por qué es lo que hay que mostrar |
|---|---|---|
| **Karen** | App `assistant` creada, tabla de fragmentos con `vector` de pgvector, comando `embed_catalog` que indexa las especialidades, y `POST /api/assistant/suggest` devolviendo la especialidad sugerida **con los fragmentos que la respaldan** | Es el RAG completo: recuperar y después responder. Mostrar los fragmentos recuperados es lo que demuestra que no está alucinando |
| **Daniel** | El corpus administrativo cargado —horarios de sucursal, costos y preparaciones previas— y **la prueba de aislamiento**: la misma pregunta en las dos organizaciones sembradas devuelve catálogos distintos | El apartado 1.1.6 del documento dice que el multi-inquilino alcanza a la IA. Esta es la única evidencia de que se cumple, y es el diferencial del proyecto |
| **Alexander** | Pantalla de chat mínima en Flutter contra el endpoint de Karen — armazón, no la historia | Un endpoint en Postman no se ve; una conversación en el celular sí. Desde el 17 la pantalla pasa a Karen |
| **Luis Aguayo** | Modelo de `appointments` migrado y **el contrato del endpoint de reserva publicado** | Repite lo que le funcionó en el Sprint 1: publicar el contrato antes que la implementación desbloquea a los demás |
| **SM** | C1 y C2 del modelo C4 y el diagrama de navegación del móvil (sección 5), más el guion de la demostración | Es la otra mitad de lo que pidió la docente, y no depende de que el código esté |

**Lo que NO se promete el 16.** Ninguna historia cerrada, ni pago, ni reserva
funcionando. Decirlo de entrada evita que el avance se lea como un
incumplimiento.

**Antes de la demostración:** entrar al panel de Supabase el **15/09** y
verificar que el proyecto no está pausado. El plan gratuito se suspende a los
7 días sin actividad y el despliegue queda caído sin aviso.

---

## 3. Por qué estas tres historias de IA y no las otras

El subsistema de IA del documento son tres aplicaciones y doce historias. No
entran todas; entran las que **ya tienen sus datos**.

| Historia | Entra | Razón |
|---|---|---|
| **US-31** — sugerir especialidad por síntomas · 16 h · 🔴 | **Sí** | Es el núcleo: el pipeline de embeddings y la búsqueda por similitud. Sus datos ya existen: las descripciones de especialidades que Daniel cargó en US-12 son exactamente el corpus que el documento (5.2, IA 1) manda vectorizar |
| **US-32** — consultas administrativas · 10 h · 🟡 | **Sí** | Reutiliza el mismo índice y el mismo endpoint; sólo amplía el corpus con sucursales, horarios y preparaciones. Es la historia de IA más barata que existe una vez que US-31 está |
| **US-34** — derivación a emergencia · 10 h · 🔴 | **Sí** | Es *Must have* y es la **barrera de seguridad** del chatbot. No puede quedar para después: un asistente sanitario que no deriva una urgencia no se puede mostrar ni a la docente ni a nadie |
| US-33 — reservar conversando · 16 h · 🟡 | No | Necesita que US-17 exista para tener qué llamar. Pasa al Sprint 3, salvo el atajo de la sección 7 |
| US-35 a US-38 — no-show | No | Un clasificador supervisado necesita **etiquetas**: fichas con resultado *asistió / no asistió*. Ese dato empieza a existir recién cuando US-21 y US-22 estén corriendo. Entrenar antes es entrenar sobre nada |
| US-39 a US-42 — resúmenes | No | Dependen de US-24 (el encuentro clínico), que se construye en este sprint |

> **Consecuencia que hay que ejecutar en este sprint aunque el modelo sea del
> Sprint 4.** US-21 (confirmación) y US-22 (check-in) tienen que **dejar
> registrado el desenlace de cada ficha** —asistió, no asistió, canceló— desde
> el primer día, con su fecha. Si no se guarda ahora, en el Sprint 4 no hay
> historial que etiquetar y el modelo de inasistencia no se puede entrenar con
> datos propios. Es una línea de código hoy y un sprint perdido después.

---

## 4. Qué le toca a cada uno

### Karen Ortega — *el asistente* — 30 h

Lleva el bloque de IA porque el chatbot es, técnicamente, una capa de
autorización más: cada recuperación tiene que filtrar por organización antes de
calcular la distancia, y ella es la dueña de la capa de identidad desde el
Sprint 0. El riesgo del chatbot no es que responda mal, es que responda con
datos de otro inquilino.

**US-31 — Sugerencia de especialidad por síntomas · 16 h · MÓVIL · 🔴**

App nueva `assistant`, bajo `/api/assistant/`. Tres piezas:

1. **Indexación.** Comando de gestión que recorre el catálogo de una
   organización, parte el texto en fragmentos y guarda su embedding en una
   columna `vector` de pgvector. Corre **dentro de `tenant_context(org.id)`**,
   como toda tarea fuera del ciclo HTTP.
2. **Recuperación.** Búsqueda por distancia coseno **con el filtro de
   organización aplicado antes de ordenar por similitud**, no después. Si el
   filtro va después del `ORDER BY`, se recorre el índice de todos los
   inquilinos y se descarta al final: funciona, y es una fuga.
3. **Respuesta.** El modelo de lenguaje responde **sólo** sobre los fragmentos
   recuperados, y la respuesta viaja con la lista de fragmentos que la
   sustentan. Sin esa lista no hay cómo demostrar que no alucinó.

> **La clave del proveedor no se versiona.** Va en variable de entorno, y en
> Railway se carga con el botón de aplicar cambios, no con *Redeploy*.
> Definir además qué pasa cuando el proveedor no responde: el chat degrada a
> "no puedo responder ahora", nunca a una respuesta inventada sin contexto.

**US-34 — Derivación a emergencia · 10 h · MÓVIL · 🔴**

Ante una descripción compatible con una urgencia, el asistente **corta el flujo
de reserva** y deriva a atención de emergencia. Dos capas, y las dos son
obligatorias: las reglas duras en el prompt del sistema **y** la validación en
el backend. La del prompt sola no sirve —se la puede rodear conversando—; la
del backend es la que se puede probar con un test.

Va junto a US-31 porque vive en el mismo endpoint y en la misma respuesta. El
asistente no se publica sin ella.

**US-05 — Edición de perfil · 4 h · WEB + MÓVIL · deuda del Sprint 1**

Perfil resuelto siempre desde el token, nunca desde un identificador del
cliente. Cambio de contraseña acreditando la actual y **sin** cerrar la sesión
en curso —a diferencia de US-03—. Documento, rol, organización y estado de la
cuenta no son editables por el usuario. Es de Karen porque vive en
`accounts/profile.py` y consume el `accounts/passwords.py` que ella escribió.

> **Además, mueve el cierre de sesión móvil a su lugar.** Hoy vive en un botón
> provisional de la pantalla de inicio, porque US-05 no se entregó. Al cerrar
> esta historia, el botón va a la pantalla de perfil y el provisional se borra.

**Archivos:** app `assistant` completa, `accounts/profile.py`. En móvil,
`mobile/lib/features/assistant/` y `mobile/lib/features/profile/`.

**Depende de:** Daniel, por el corpus de US-32 —pero sólo para ampliarlo: US-31
arranca con las descripciones de especialidades que ya están cargadas.

**Dependen de ella:** Daniel (US-32 monta sobre su pipeline) y el Sprint 3
completo del chatbot.

---

### José Daniel Iporo — *mostrador, padrón y el chatbot administrativo* — 28 h

Sigue siendo el dueño de `catalog`, y por eso el corpus administrativo es suyo:
es el mismo texto que él escribió en US-12. Su bloque es todo web y todo de
mostrador.

**US-32 — Consultas administrativas al asistente · 10 h · backend · 🟡**

Horarios, sucursales, costos y preparación previa a estudios, respondidos por
el mismo endpoint de Karen sobre el mismo índice. Su trabajo es el **corpus**:
qué se vectoriza, con qué granularidad y con qué texto. Un fragmento por
sucursal con su horario completo se recupera bien; un fragmento con las tres
sucursales juntas no distingue cuál pidió el paciente.

No construye pantalla: la conversación ya la tiene Karen. Acuerda con ella el
formato del fragmento antes de cargar nada.

**US-22 — Check-in en recepción · 6 h · WEB · 🔴**

Verificación del código del comprobante —QR o documento— y habilitación del
ingreso a consulta. El código lo emite Alexander en US-19: **acordar el formato
y la firma el primer día**, o se emite uno y se valida otro. Un comprobante ya
usado no se acepta dos veces, y el rechazo dice por qué.

> Acá se registra el desenlace *asistió*. Ver la nota de la sección 3: sin eso
> el Sprint 4 no tiene qué entrenar.

**US-09 — Búsqueda de pacientes · 6 h · WEB · deuda del Sprint 1**

Por documento (exacta) y por nombre o apellido (parcial, sin distinguir
mayúsculas ni tildes), en menos de 2 segundos con 10.000 registros (RNF-01).
Eso obliga a un índice de texto sobre el nombre normalizado. El conjunto de
prueba es **sintético**: el repositorio es público.

**US-10 — ABM de pacientes · 6 h · WEB · deuda del Sprint 1**

Corrección de datos, alta manual desde ventanilla, baja **lógica y nunca
física**, y fusión de duplicados reasignando fichas, antecedentes y atenciones
antes de inactivar el registro absorbido. Cada corrección, baja y fusión va a
la bitácora de US-06 con el valor anterior y el nuevo.

**Archivos:** `assistant/corpus.py` *(acordado con Karen)*, `patients/search.py`,
`patients/admin_ops.py`, el módulo de check-in dentro de `appointments`
*(nombre a acordar con Luis Aguayo)*.

**Depende de:** Karen (pipeline de US-31) y Alexander (formato del comprobante).

**Dependen de él:** nadie de forma bloqueante. Es lo que le permite absorber la
deuda del sprint anterior sin arrastrar al resto.

---

### Luis Mateo Hurtado *(Scrum Master)* — *la historia clínica* — 26 h + documentación

Toma la Épica 5 completa porque ya es el dueño de `patients/history.py`
—los antecedentes declarados de US-08— y el encuentro clínico se escribe encima
de eso.

**US-24 — Registro de la atención · 16 h · WEB · 🔴**

App nueva `encounters`. Motivo de consulta, evolución, diagnóstico,
indicaciones y tratamiento. Es la historia más grande del sprint. Tres
decisiones:

- **El encuentro se cierra, no se borra.** Una vez firmado no se edita: se
  agrega una enmienda que referencia al original. Una historia clínica que se
  puede reescribir no es una historia clínica.
- **Toda apertura de historia clínica va a la bitácora de US-06**, que ya
  registra ese evento desde el Sprint 1. Es el asiento que más importa de los
  cinco.
- El encuentro cuelga de la ficha de US-17, no del paciente suelto: es lo que
  después permite cruzar atención con sucursal, especialidad e inasistencia.

**US-25 — Historial longitudinal · 10 h · WEB · 🔴**

Todos los encuentros del paciente **sin importar la sucursal**, en una línea de
tiempo única. Es el argumento multi-sede del proyecto aplicado a lo clínico, el
mismo que US-15 aplicó a la disponibilidad. Se lee con permiso explícito y cada
lectura deja asiento en la bitácora.

**Además, como SM y de cara al 06–08/10:**

- **Modelo C4 y las características de calidad** — sección 5.
- **Diagramas de estado, navegación y tiempo** — sección 5.
- Abrir `config/urls.py` **una sola vez**, en un commit, al inicio del sprint,
  para incluir `appointments`, `payments`, `encounters` y `assistant`. Después
  queda cerrado para todos.
- Coordinar la demostración del 16/09 y la del cierre.

**Archivos:** app `encounters` completa, `/api/encounters/`.

**Depende de:** Luis Aguayo (US-17: sin ficha no hay a qué colgar el encuentro).

**Dependen de él:** el Sprint 3 completo —US-26 recetas, US-27 historial en el
móvil— y la Épica 9 de resúmenes del Sprint 4.

---

### Luis Miguel Aguayo — *la ficha* — 26 h

Dueño único de `appointments`, app nueva bajo `/api/appointments/`. Es la
continuación natural de `scheduling`: en el Sprint 1 derivó los espacios
reservables, en este los ocupa. Lleva la historia de la que depende todo el
resto del sprint.

**US-17 — Reserva de ficha · 16 h · MÓVIL · 🔴**

Sucursal, profesional, fecha y hora, sobre el endpoint de disponibilidad que él
mismo publicó en US-13. Lo que define la historia no es el formulario, es la
**concurrencia**: dos pacientes pidiendo el mismo espacio al mismo tiempo tienen
que terminar en una reserva y un rechazo, nunca en dos reservas. Eso se resuelve
con un bloqueo en la base sobre el espacio, no comprobando disponibilidad antes
de insertar —entre la comprobación y la inserción cabe la otra petición—.

La ficha nace **pendiente de pago** y sólo se confirma cuando US-18 avisa. Una
ficha pendiente ocupa el espacio por una ventana corta y configurable; vencida,
lo libera. Si no, un carrito abandonado bloquea un cupo para siempre.

Usa el selector *"¿para quién es esta ficha?"* de US-07, que ya está publicado
como widget compartido. No se vuelve a escribir.

**US-20 — Cancelación y reprogramación · 10 h · MÓVIL · 🟡**

Dentro de la política de anticipación de la organización, que es un parámetro y
no un número escrito en el código. Cancelar **libera el espacio en el acto** y
dispara la devolución que corresponda según lo que haya decidido US-18.
Reprogramar es liberar y volver a tomar en una sola transacción: si la segunda
mitad falla, el paciente no puede quedarse sin las dos.

> **Primera vez en Flutter.** Sus dos historias tienen pantalla móvil y hasta
> ahora trabajó sólo en backend. Mitigación: **el 19/09 publica el contrato del
> endpoint de reserva** —como hizo con el de disponibilidad, que funcionó— y
> Alexander le hace la recorrida del shell esa misma semana. Empieza por la
> pantalla de US-20, que es la chica.

**Archivos:** `appointments/booking.py`, `appointments/changes.py`, bloque
propio en `appointments/urls.py`. En móvil,
`mobile/lib/features/appointments/`.

**Depende de:** nadie para arrancar. Su modelo es lo primero del sprint.

**Dependen de él:** Alexander (US-18, US-19, US-21), el SM (US-24), Daniel
(US-22) y toda la Épica 8 del Sprint 4. **Es la ruta crítica del sprint.**

---

### Alexander Osinaga *(Product Owner)* — *pago, comprobante y confirmación* — 32 h

Sigue con la cara del paciente: en el Sprint 1 construyó el shell, la búsqueda y
la disponibilidad —las dos pantallas que desembocan en la reserva—. Este sprint
lleva todo lo que ocurre **después** de elegir el turno.

**US-18 — Pago en línea con Stripe · 16 h · MÓVIL · 🔴**

App nueva `payments`. Tres cosas que no son negociables:

- **La confirmación de la ficha la dispara el webhook de Stripe, no la pantalla
  del paciente.** Si se confirma cuando el móvil dice "pagué", una app cerrada a
  destiempo deja fichas cobradas sin confirmar o confirmadas sin cobrar.
- **El webhook se verifica con la firma de Stripe.** Un endpoint que confirma
  fichas contra un POST sin firmar es una forma de reservar gratis.
- **Modo de prueba, con tarjetas de prueba.** Ni una clave viva en el
  repositorio ni en la demostración.

Definir con el PO —él mismo— la **política de devolución** que después ejecuta
US-20, y escribirla en la historia.

**US-19 — Comprobante digital con QR · 10 h · MÓVIL · 🔴**

Código único **firmado** por ficha, de un solo uso, presentable sin conexión
—el paciente llega al centro médico y puede no tener señal—. Acordar el formato
con Daniel el primer día: él lo valida en el mostrador.

**US-21 — Confirmación de asistencia · 6 h · MÓVIL · 🟡**

El paciente confirma que va a asistir. La infraestructura de push completa es
US-28, del Sprint 3: en este sprint la confirmación vive dentro de la app y por
correo, y se deja el registro asentado.

> Acá se registra el desenlace *confirmó / no confirmó*, y en US-20 el
> *canceló*. Ver la nota de la sección 3.

**Archivos:** app `payments` completa, `appointments/receipts.py`. En móvil,
`mobile/lib/features/payments/` y `mobile/lib/features/receipts/`.

**Depende de:** Luis Aguayo (la ficha de US-17 tiene que existir antes que el
pago).

**Dependen de él:** Daniel (US-22 valida su comprobante) y el Sprint 4 (la
variable "pagó por adelantado" es, según el documento, la más predictiva del
modelo de inasistencia).

---

## 5. La parte del documento

Lo que pidió la docente además del código. **El alcance exacto se cierra en la
reunión de equipo**; lo de abajo es la propuesta que se lleva a esa reunión, no
un acuerdo tomado.

**Modelo C4.** Cuatro niveles, de menor a mayor detalle:

| Nivel | Qué muestra | Estado |
|---|---|---|
| **C1 — Contexto** | La plataforma como caja única con sus actores y los cuatro sistemas externos: Stripe, el proveedor de modelo de lenguaje, Firebase Cloud Messaging y el correo transaccional | Descrito en el capítulo 3; falta el diagrama |
| **C2 — Contenedores** | App móvil Flutter, SPA React, API Django, PostgreSQL con pgvector | Falta |
| **C3 — Componentes** | Los componentes de la API: `accounts`, `tenancy`, `catalog`, `patients`, `scheduling`, `audit` y las nuevas `appointments`, `payments`, `encounters`, `assistant` | Falta |
| **C4 — Código** | Un solo camino, el más representativo. Propuesta: la recuperación del asistente, que es el énfasis del proyecto | Falta |

> **Las "8 características".** Entendemos que son las ocho características de
> calidad de la **ISO/IEC 25010** —adecuación funcional, eficiencia de
> desempeño, compatibilidad, usabilidad, fiabilidad, seguridad, mantenibilidad
> y portabilidad—, que se cruzarían con los RNF-01 a RNF-18 que ya están en el
> documento. **Confirmarlo con la docente antes de dibujar nada**: si se
> refería a otra cosa, es trabajo tirado.

**Los tres diagramas nuevos.** Uno por familia, con el candidato propuesto:

| Diagrama | Candidato | Por qué ese |
|---|---|---|
| **Estados** | El ciclo de vida de la ficha: *pendiente de pago → confirmada → en espera → atendida*, con *vencida*, *cancelada*, *reprogramada* y *ausente* | Es el único objeto del sistema con estados de verdad, y este sprint los construye todos |
| **Navegación** | Las pantallas del móvil del paciente: ingreso → búsqueda → disponibilidad → reserva → pago → comprobante, con el asistente como entrada alternativa | Es la superficie que más creció y la que se demuestra |
| **Tiempo (secuencia)** | Reserva con pago: móvil → API → Stripe → webhook → confirmación. Alternativa: la consulta al asistente, móvil → API → pgvector → modelo de lenguaje | Es donde el orden de los mensajes importa y donde está el error que más cuesta: confirmar desde la pantalla en vez del webhook |

Los tres van al modelo de Enterprise Architect,
`docs/diagramas/PlataformaMedica.eapx`. **El `.eapx` es binario: dos ramas que
lo toquen en paralelo no se pueden fusionar.** Todos los diagramas van en la
misma rama y los hace una sola persona. Además, **la licencia Trial caduca
cerca del 22/09/26**: lo que haya que dibujar en EA se dibuja antes de esa
fecha o se resuelve la licencia.

---

## 6. Reglas que no se negocian

Las ocho del Sprint 1 siguen vigentes sin cambios —autorización con
`user.has_permission()`, tokens con `tokens_for_user()`, contexto en
`accounts/authentication.py`, `tenant_context()` fuera del ciclo HTTP,
`makemigrations` sólo avisando al SM, código en inglés y comentarios en
español, datos sintéticos, y prueba de aislamiento en toda historia—. Están en
`../sprint-1/reparto.md`, sección 5. Se agregan tres, propias de este sprint:

9. **La recuperación vectorial filtra por organización ANTES de ordenar por
   similitud.** Es la regla 4 llevada a la IA. Filtrar después del `ORDER BY`
   funciona igual y es una fuga: el índice se recorrió entero.

10. **Ningún importe, estado de pago ni confirmación de ficha se decide en el
    cliente.** El móvil pide y muestra; quien decide es el backend, y en el
    caso del pago, el webhook firmado de Stripe.

11. **Ninguna clave de proveedor externo —Stripe, modelo de lenguaje— entra al
    repositorio, ni siquiera en un `.env.example` con un valor "de ejemplo" que
    después alguien completa y commitea.** Variables de entorno, y en Railway
    con el botón de aplicar cambios.

Y una de proceso: **toda historia de IA cierra con la prueba de aislamiento
hecha sobre el asistente**, no sólo sobre el ORM. La pregunta de un paciente de
la organización A no puede recuperar un fragmento de la B.

---

## 7. Ruta crítica

| Fecha | Qué tiene que estar | Quién |
|---|---|---|
| **15/09** | Supabase verificada como activa; `config/urls.py` abierto e incluidas las cuatro apps nuevas | SM |
| **16/09 · 19:00** | **Corte de avance ante la docente** — sección 2 | Todos |
| **19/09** | Modelo de `appointments` migrado y contrato de reserva publicado — desbloquea a Alexander, Daniel y al SM | Luis Aguayo |
| **19/09** | Formato del comprobante acordado entre quien lo emite y quien lo valida | Alexander + Daniel |
| **22/09** | Lo que necesite Enterprise Architect, dibujado — **caduca la licencia Trial** | SM |
| **26/09** | US-17 mergeada. **Si está antes del 24/09, entra US-33** (reserva conversacional) como estirón, entre Karen y Luis Aguayo | Luis Aguayo |
| **26/09** | US-31 y US-34 mergeadas: el asistente no se publica sin la derivación a emergencia | Karen |
| **29/09** | US-18 mergeada con el webhook verificado — sin esto no hay ficha confirmada ni check-in que probar | Alexander |
| **02/10** | Backend completo y congelado; sólo pantallas, documento y pruebas | Todos |
| **05/10** | Cierre del sprint | — |

---

## 8. Si llega el reemplazo de Michael

El reparto **no se rehace**. La persona que llegue toma, en este orden:

1. **US-23 — agendamiento asistido en mostrador · 10 h · WEB.** Se corrió al
   Sprint 3 justamente para esto. Es *Should have*, es web, **nadie depende de
   ella** y reutiliza el flujo de reserva de Luis Aguayo y el cobro de
   Alexander sin tocarles el código: es la historia que menos conocimiento
   previo del repositorio exige.
2. **Las pruebas de aislamiento del asistente** (sección 6), que hoy están
   repartidas entre Karen y Daniel.
3. Si llega temprano y rinde, **US-33** deja de ser un estirón y pasa a ser
   suya, con Karen de apoyo.

Es el mismo criterio que se usó en el Sprint 1 con Michael y que hizo que su
ausencia no arrastrara al resto del sprint: carga baja, web, y nada colgando de
ella.

Lo primero que hace, el día uno, es `../../entorno/primeros-pasos.md` hasta
tener las pruebas en verde, y leer la sección 6 de este documento y la 5 del
Sprint 1. No escribe una línea antes.

---

## 9. Tareas nuevas para el Sprint Backlog del documento

La numeración del Sprint 1 llegó hasta T-24. El Sprint 2 arranca en T-25.

| ID | Tarea | Tipo | Estimación | Responsable | Prioridad |
|---|---|---|---|---|---|
| T-25 | Reserva de ficha | Historia | 16 horas | Aguayo Quiroz, L.M. | Must have |
| T-26 | Pago en línea con Stripe | Historia | 16 horas | Osinaga Blanco, A. | Must have |
| T-27 | Comprobante digital con QR | Historia | 10 horas | Osinaga Blanco, A. | Must have |
| T-28 | Cancelación y reprogramación | Historia | 10 horas | Aguayo Quiroz, L.M. | Should have |
| T-29 | Confirmación de asistencia | Historia | 6 horas | Osinaga Blanco, A. | Should have |
| T-30 | Check-in en recepción | Historia | 6 horas | Iporo Chulque, J.D. | Must have |
| T-31 | Registro de la atención | Historia | 16 horas | Hurtado Castro, L.M. | Must have |
| T-32 | Historial clínico longitudinal | Historia | 10 horas | Hurtado Castro, L.M. | Must have |
| T-33 | Sugerencia de especialidad por síntomas (RAG) | Historia | 16 horas | Ortega Mancilla, K.P. | Must have |
| T-34 | Consultas administrativas al asistente | Historia | 10 horas | Iporo Chulque, J.D. | Should have |
| T-35 | Derivación a atención de emergencia | Historia | 10 horas | Ortega Mancilla, K.P. | Must have |
| T-36 | Modelo C4 y diagramas de estado, navegación y tiempo | Técnica | *(a estimar en la reunión)* | Hurtado Castro, L.M. | Must have |
| *(arrastre S1)* | Edición de perfil — US-05 | Historia | 4 horas | Ortega Mancilla, K.P. | Must have |
| *(arrastre S1)* | Búsqueda de pacientes — US-09 | Historia | 6 horas | Iporo Chulque, J.D. | Must have |
| *(arrastre S1)* | ABM de pacientes — US-10 | Historia | 6 horas | Iporo Chulque, J.D. | Must have |

Las tres de arrastre **conservan el identificador que ya tienen** en el Sprint
Backlog del Sprint 1 —hay que verificarlo en el documento—, como se hizo con
T-06 cuando US-04 pasó del Sprint 0 al Sprint 1. No se les da un número nuevo.

También hay que corregir en el apartado 3.11 la tabla de planificación: el
Sprint 2 pasa a 142 h y el Sprint 3 a 74 h, por el movimiento de la sección 0.
El total de 436 h no cambia.
