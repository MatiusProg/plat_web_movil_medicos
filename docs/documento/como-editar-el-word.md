# Cómo editar el Word del proyecto sin romperlo

> **Para qué es este archivo.** El 02/10/26 se completó el capítulo del Sprint 2,
> se pasaron sus historias a tablas, se homogeneizó el formato de los Sprints 0, 1
> y 2 y se movieron las capturas del Sprint 1, todo editando el XML del `.docx`
> en lugar de hacerlo a mano en Word. Acá está **cómo repetirlo** sobre otro
> `.docx` del proyecto, con los valores exactos y los scripts que lo hacen.
>
> Está escrito para que lo pueda seguir alguien —o una sesión de Claude— que no
> estuvo cuando se hizo. Los scripts están en
> [`herramientas-word/`](herramientas-word/) y todos reciben las rutas por
> argumento.

---

## 0. Reglas duras

Ninguna de estas es negociable. Cada una sale de un problema que pasó.

1. **Nunca se edita el original.** Se trabaja sobre una copia, y antes de nada se
   hacen dos respaldos con fecha: uno al lado del original
   (`Proyecto SI2 Grupo15 - respaldo AAAA-MM-DD.docx`) y otro fuera de OneDrive.
   El resultado se copia sobre el original **sólo** si pasó todas las
   verificaciones del punto 5.
2. **Word tiene que estar cerrado.** Si al lado del `.docx` hay un archivo
   `~$…docx`, alguien lo tiene abierto: se para ahí. Escribir encima de un
   documento abierto falla (`Device or resource busy`) o, peor, Word lo pisa
   al guardar.
3. **Las imágenes no se tocan.** Ni `word/media/*`, ni los `.rels`, ni el XML
   de `<w:drawing>`/`<w:pict>`. Una imagen sólo se puede **mover**, como
   párrafo completo, sin cambiarle un byte. Se comprueba con hashes antes y
   después (`verificar.py`).
4. **Sin control de cambios.** Todas las ediciones son limpias: nada de
   `<w:ins>`/`<w:del>`.
5. **Sólo texto, tablas y formato.** No se agregan imágenes, no se recomprimen,
   no se redimensionan.
6. **Se ubica todo por texto, nunca por índice.** Los índices de elemento cambian
   de un documento a otro y después de cada edición. Los scripts buscan anclas
   ("Sprint 2", "1.3 Contexto del Sistema", …) y **se detienen** si no las
   encuentran: si un script dice `PARADO`, no se fuerza, se mira qué es distinto.
7. **Las ediciones de los compañeros se conservan.** Si el documento destino tiene
   contenido que la base no tenía, ese contenido manda: se aplican los cambios
   encima, no se reemplaza el documento por la copia (`trasplantar.py` lo
   comprueba tramo por tramo).

---

## 1. Herramientas

| Qué | Dónde | Para qué |
|---|---|---|
| Python 3 | — | todos los scripts; usan sólo la biblioteca estándar salvo `paginas.py` |
| PyMuPDF y Pillow | `pip install pymupdf pillow` | `paginas.py`: láminas con las páginas del PDF |
| Microsoft Word | instalado | `exportar_pdf.ps1` exporta a PDF por COM, en sólo lectura |
| Skill `docx` de Claude | `scripts/office/validate.py` | valida el XML contra el esquema: `validate.py SALIDA.docx --original ENTRADA.docx` |
| `herramientas-word/comun.py` | este repo | helpers compartidos: leer/guardar el `.docx`, elementos, filas, celdas, anchos, colores, tablas de historias |

**En Windows, correr Python con `PYTHONIOENCODING=utf8`**: si no, los `print` con
tildes o flechas revientan con `UnicodeEncodeError` (incluido `validate.py`).

Sobre el skill `docx`:

- **`unzip` y `zip` no existen en Git Bash.** No hacen falta: `comun.guardar()`
  copia cada parte del `.docx` original tal cual y reemplaza sólo
  `word/document.xml`.
- **`merge_runs.py` no se usa.** Une runs contiguos para que el texto sea
  buscable, pero **también reescribe los cuadros de texto que viven dentro de
  las imágenes**, así que el XML de los dibujos deja de ser idéntico. Los
  scripts de acá no lo necesitan: leen el texto juntando los `<w:t>` de cada
  párrafo.
- **No hay LibreOffice ni `pdftoppm`.** El PDF sale de Word (`exportar_pdf.ps1`)
  y las páginas se miran con `paginas.py`.

### Los scripts

| Script | Uso |
|---|---|
| `inventario.py DOC.docx --titulos --tablas` | ubicarse: títulos con su numeración, tablas con estilo, ancho, grilla y color |
| `inventario.py DOC.docx --elementos A B` / `--formatos A B` | ver un tramo, o qué formatos de párrafo predominan |
| `comparar.py A.docx B.docx` | partes del paquete que difieren y diferencias de contenido (ignora el marcado que mete Word al guardar) |
| `trasplantar.py --base --editado --destino --salida` | llevar tramos ya editados de la copia al documento destino |
| `historias_tabla.py ENT SAL [--sprint 2]` | pasar las historias escritas como párrafos a tablas del modelo US-01 |
| `normalizar.py ENT SAL` | homogeneizar Sprints 0–2 (punto 4) |
| `mover_capturas.py ENT SAL` | mover las capturas del segundo juego del Sprint 1 al primero y borrar el segundo |
| `actualizar_us32.py ENT SAL` | contenido: US-32 integrada (PR #47) en el capítulo del Sprint 2 |
| `verificar.py ORIGINAL EDITADO --validate …/validate.py` | imágenes, relaciones y validación (punto 5) |
| `exportar_pdf.ps1 -Entrada X.docx -Salida X.pdf` | PDF con Word |
| `paginas.py X.pdf PREFIJO "texto" … [--desde A --hasta B]` | láminas de 8 páginas para revisar a ojo |
| `historico/contenido_sprint2.py` | **no se corre**: registro de cómo se escribió el capítulo del Sprint 2 sobre la copia (usa índices fijos de ese documento) |

---

## 2. Qué camino seguir

Primero se compara el destino con el documento del que partió la copia:

```
python herramientas-word/comparar.py "Proyecto SI2 Grupo15 - avance sprint2.docx" DESTINO.docx
```

**Camino A — el destino tiene el mismo contenido que la base en los tramos
editados** (fue el caso del oficial el 02/10/26). Se trasplantan los tramos de la
copia y después se aplica lo que la copia todavía no tenga:

```
python trasplantar.py --base AVANCE.docx --editado COPIA.docx --destino OFICIAL.docx --salida paso1.docx
python actualizar_us32.py paso1.docx paso2.docx
python verificar.py OFICIAL.docx paso2.docx --validate RUTA/validate.py
```

Los tramos por omisión son `2.4.3 Por qué C4 y cómo convive con UML` → `2.6
Entorno de desarrollo` (corrección del Modelo C4 en el Capítulo 2) y `Sprint 0`
→ `Sprint 3` (todo el Capítulo 4 de los Sprints 0, 1 y 2). Fuera de esos tramos
el destino queda como estaba: índice, carátula, otros capítulos.

**Camino B — el destino es otro documento, o un compañero editó esos tramos.**
`trasplantar.py` se detiene y dice en qué elemento difiere. Ahí se aplican las
transformaciones de formato una por una, en este orden, y el contenido nuevo
se escribe a mano o con un script propio:

```
python historias_tabla.py ENT.docx a1.docx --sprint 2
python normalizar.py a1.docx a2.docx
python mover_capturas.py a2.docx a3.docx
python verificar.py ENT.docx a3.docx --validate RUTA/validate.py
```

Este camino se probó el 02/10/26 sobre el avance del Sprint 2: los tres scripts
corren y `verificar.py` da OK.

### Qué hace `trasplantar.py` además de copiar

Al guardar en Word la copia cambia por dentro aunque el texto sea el mismo, y el
script lo deshace:

- **Word renumera los `rId`** al guardar. Cada `r:embed` del tramo se traduce al
  `rId` del destino que apunta a un archivo de `word/media` con el mismo md5.
  Si una imagen del tramo no tiene un archivo idéntico en el destino, se para.
- **Word renumera `docPr id`, `wp14:anchorId` y `wp14:editId`** de los dibujos.
  Cada dibujo del tramo se reemplaza por el XML exacto del dibujo del destino
  que usa la misma imagen.
- **Los `w:id` de los marcadores** del tramo pueden chocar con los del resto
  (`Duplicate id` en `validate.py`): se renumeran por encima del máximo.
- **El índice del destino apunta a marcadores `_Toc…`** de sus títulos. Los
  títulos del tramo traen los de la copia, con otros nombres, y el índice
  mostraría `¡Error! Marcador no definido.`. El script les pone los marcadores
  del destino, emparejando título con título por el texto sin numeración ni
  tildes, y en orden cuando el texto se repite entre sprints.

---

## 3. Contenido del Sprint 2 al 02/10/26

Lo escribió `historico/contenido_sprint2.py` sobre la copia. Fuente:
`docs/documento/sprint-2-capitulo-4.md`, `2-4-modelo-c4-correccion.md`,
`docs/sprints/sprint-2/reparto.md` y el código de `main`.

- **Capítulo 2:** el 2.4.3 deja de decir que C3 y C4 quedan fuera del alcance;
  el 2.4.4 tiene los cuatro niveles, con la tabla de contenedores en **cuatro**
  (sin "Subsistema de IA") y la de componentes en doce; la tabla del 2.5 suma
  "Modelo C4, niveles C1 y C2" y "…C3 y C4".
- **Sprint 2:**
  - 1.3, nota formal (el diagrama de casos de uso sigue pendiente);
  - 1.4, estados del backlog;
  - 2.1.1, texto de las cuatro figuras del C4;
  - 2.1.2, diseño conceptual, lógico y físico de `appointments`,
    `assistant_catalog_fragments`, `saved_reports`, `backup_records`,
    `services` y la columna nueva de `organizations`;
  - 2.1.3 y 2.1.4, comunicación, clases de análisis y secuencia de US-31;
  - 2.2.1, artefactos por historia;
  - 2.3.1 y 2.3.2, plan y reporte de CU18, CU21, CU32, CU33 y CU35;
  - Daily de las semanas 2 a 4 como estructura, y Review y Retro del Sprint 2
    con la retroalimentación pendiente.
- **US-32** (`actualizar_us32.py`):
  - T-34 Completado;
  - el estado pasa a cinco historias;
  - en la tabla de la historia, g) 22 pruebas y 418 en la suite, h) la
    pantalla web `/servicios`;
  - `services` en el diseño de datos y en el script SQL;
  - la fila de US-32 en 2.2.1;
  - en el plan, CP-32-07 a CP-32-10;
  - en el reporte, el bloque de CU33 (9 de 10 escenarios cubiertos; CP-32-04 no
    tiene prueba específica).

Nada de esto inventa datos de reuniones ni horas reales. Lo que no tiene datos
quedó marcado **Pendiente**.

---

## 4. Reglas de formato (Sprints 0, 1 y 2)

**Medidas del documento** (`styles.xml` y `sectPr`):

- Página Carta 12240 × 15840, márgenes izquierdo y derecho 1701, así que el texto
  útil mide 8838 dxa. **Ancho estándar de tabla: 8828 dxa.**
- `docDefaults`: Times New Roman 12 pt (`sz 24`), color `404040`, interlineado
  480 y primera línea 284. Por eso todo párrafo de celda necesita
  `firstLine=0`.

### 4.1 Historias de usuario — modelo: la tabla de US-01 del Sprint 0

- **Tabla:** `tblStyle=Tablaconcuadrcula`, `tblW auto`, grilla **4248 / 4580**,
  siete filas:

  | Fila | Contenido |
  |---|---|
  | 0 | nombre corto (gridSpan 2, `shd fill=45B0E1 themeFill=accent1 themeFillTint=99`, `vAlign center`, `trHeight 832`, centrado y en negrita) |
  | 1 | `CUxx — ` en negrita + nombre del caso de uso, y a la derecha la descripción (+ un párrafo vacío) |
  | 2 | separador vacío (gridSpan 2) |
  | 3 | `Prioridad: X` y `Cant Horas : N hr`, con espacio antes de los dos puntos |
  | 4 | `Funcionalidades:` y un párrafo por inciso, **sólo la letra `a)` en negrita**; las notas sin letra van como párrafo normal |
  | 5 | `Responsables: ` y después `Web: …` y `Móvil: …` en párrafos separados (se parte en ` · `) |
  | 6 | texto del prototipo, las capturas debajo y un párrafo vacío |
- **Párrafos de celda:** `<w:ind w:firstLine="0"/>`; runs con `rFonts cs="Times
  New Roman"`, `color auto` y `lang eastAsia="es-BO"`.
- **Título encima:** párrafo sin estilo, `ind left=360 firstLine=0`, run en
  negrita (`b`, `bCs`). Texto `US-NN — …` con dos dígitos (`US-5` pasa a
  `US-05`) y sin espacios al final.
- **Secuencia:** título, tabla y **un** párrafo vacío.

### 4.2 Títulos

- `Titulo2`, `Titulo3` y `Titulo4` van **sin formato directo**: se quitan
  `numPr`, `spacing`, `ind` y `color auto`, y manda el estilo. `titulo5` lleva
  `ind left=708`.
- **La numeración se escribe a mano, nunca automática.** El "Historias de
  Usuario" con `numPr ilvl=1 numId=30` salía como "1.3 1.2 …" en cuanto se le
  escribía el número. Correcciones:
  - `Historias de Usuario` pasa a `1.2 Historias de Usuario`;
  - `2.2.1.` y `2.3.1.` pierden el punto final;
  - en el Sprint 2, `2.1.4 Diseño de procesos` pasa de `Titulo3` a `Titulo4`, y
    sus hijos se numeran de 2.1.4.1 a 2.1.4.5 (`navegacion` pasa a
    `navegación`);
  - `2.1.1.4 nivel 4` pasa a `Nivel 4`.
- **Después de cambiar títulos hay que actualizar el índice en Word** (clic
  derecho sobre el índice → Actualizar campos → Actualizar toda la tabla).

### 4.3 Texto corrido

Se aplica a los párrafos sin estilo, con texto, fuera de tablas, sin imagen y que
no son código:

- `<w:spacing w:line="276" w:lineRule="auto"/>` (1,15) y sin `ind` directo, así
  que heredan la primera línea de 284.
- Se quita `color auto` de los runs, para que hereden `404040`.

Los bloques SQL (`shd fill=121314`, Consolas 10,5 pt, `spacing line=285`) no se
tocan.

### 4.4 Tablas

En todas: `tblW` en dxa = 8828; el `tcW` de cada celda es la suma de su
`gridSpan` sobre la grilla; sin `tblInd`; párrafos de celda con
`firstLine=0`, salvo los numerados.

| Tipo (fila 0 empieza con) | Grilla (dxa) | Además |
|---|---|---|
| `IDCaso de Uso…` | 846 / 1843 / 1701 / 4438 | |
| `Sprint Backlog` (cabecera 4×2) | 4414 / 4414 | etiqueta hasta `:` en negrita y el valor normal |
| `IDTarea…` | 686 / 1742 / 1003 / 1346 / 1479 / 1335 / 1237 | sin `rFonts ascii=system-ui` ni `Calibri`; `sz 21` |
| `RolMiembros…` | 2263 / 3261 / 3304 | |
| `Daily Scrum` | 9 columnas: 1481 / 1052 / 1232 / 1155 / 1172 / 1114 / 1202 / 1074 / 923 | **excepción:** `tblW 10405`, `tblInd -714`, `tblLayout fixed`. Nueve columnas no entran en 8828 |
| `REVISION DE SPRINT` | 4413 / 4415 | |
| `RETROSPECTIVA` | 2942 / 2939 / 2940 / 7 | |
| `HistoriaComponentes…` | 1613 / 4919 / 2296 | `Tablaconcuadrculaclara`, rutas en Consolas |
| `Convención de identificadores` | 8828 | fondo `EAF3F4` |
| Pruebas (fila 0 con `fill=17324D`) | la propia, escalada a 8828 | encabezado `17324D` con texto `FFFFFF`; **banda `F2F6F9` en las filas pares**, impares sin fondo; `tcMar` 90 / 110 / 90 / 110 |
| `ColumnaTipoRestricción` (diseño de datos) | 2212 / 1748 / 4868 | mismo estilo que las de pruebas |

### 4.5 Mover imágenes de una tabla a otra (`mover_capturas.py`)

El Sprint 1 tenía las historias **dos veces**: un primer juego completo y un
segundo juego de plantillas casi vacías, que tenía las 11 capturas de prototipo.

1. **Ubicar los dos juegos por texto:** los 28 títulos `US-NN — …` entre
   `1.2 Historias de Usuario` y `1.3 Contexto del Sistema`. Tienen que ser las
   mismas 14 historias, en el mismo orden, cada título seguido de su tabla.
2. **Antes de borrar:** en el segundo juego no puede haber más relaciones que
   los `r:embed` de los dibujos (ni `r:id`, ni hipervínculos), ni imágenes en
   sus párrafos sueltos.
3. **Se mueve el `<w:p>` completo que contiene el dibujo**, byte a byte, en el
   orden de las filas. La de US-04 que estaba en una fila extra va debajo de la
   otra.
4. **Fila Prototipo del destino:** los párrafos con texto, después los de
   imagen y un párrafo vacío al final.
5. **Responsables:**
   - el `Web:` vacío de US-03 se completa con lo que tenía el segundo juego
     (Web y Móvil: Karen Ortega);
   - US-05, US-09 y US-10 suman la línea «No se desarrolló en el Sprint 1 (era
     de Michael Mamani, que retiró la materia); pasa al Sprint 2.».
6. **Se borran** los títulos, las tablas y los vacíos del segundo juego.
7. **Se verifica:**
   - el mismo multiconjunto de dibujos antes y después (68 = 68);
   - ninguna relación de imagen sin uso ni referencia sin relación;
   - que ya no quede texto del segundo juego ("Nombre del/los Caso/s de uso"
     sólo aparece en las plantillas de los Sprints 3 y 4).

| Historia | Capturas |
|---|---|
| US-03 | 1 |
| US-04 | 2 |
| US-06 | 1 |
| US-07 | 2 |
| US-08 | 1 |
| US-13 | 1 |
| US-14 | 1 |
| US-15 | 1 |
| US-16 | 1 |

---

## 5. Verificación (siempre, antes de guardar sobre el original)

```
python herramientas-word/verificar.py ORIGINAL.docx SALIDA.docx --validate RUTA/scripts/office/validate.py
powershell -File herramientas-word/exportar_pdf.ps1 -Entrada SALIDA.docx -Salida SALIDA.pdf
python herramientas-word/paginas.py SALIDA.pdf lamina "US-01 — Registro de paciente" "Número de Sprint: 1" "Número de Sprint: 2" "Resumen de casos de uso" "REVISION DE SPRINT 2"
```

`verificar.py` tiene que terminar en `RESULTADO: OK`. Eso exige:

- partes del paquete fuera de `document.xml` idénticas;
- el mismo XML de dibujos;
- sin relaciones huérfanas ni faltantes;
- `validate.py` en `PASSED`.

Además se revisan a ojo las láminas, al menos de cada sprint:

- una historia;
- el Backlog;
- el Daily;
- la Review;
- una tabla de pruebas.

En el PDF, el texto `Error!` en el índice quiere decir que se perdió un
marcador `_Toc`.

---

## 6. Trampas que ya costaron tiempo

- **`<w:p …/>` autocerrado.** Una regex `<w:p…>.*?</w:p>` se traga desde ahí
  hasta el próximo `</w:p>` y rompe la celda siguiente. `comun.PARA_RE` lo
  reconoce primero.
- **Doble escape.** El texto que sale de `txt()` ya viene con `&amp;`/`&gt;`; hay
  que pasarlo por `html.unescape` antes de volver a escribirlo, o aparece
  `&amp;gt;` en el documento.
- **Word guarda cambiando el marcado.** Después de abrir y guardar, el XML trae
  otros `rsid`, `proofErr`, runs partidos, `rId` y `docPr` renumerados. Por eso
  `comparar.py` compara contenido y no XML, y `trasplantar.py` traduce
  referencias.
- **Una herramienta que edita el archivo mientras está abierto** en un editor o
  en Word puede no persistir el cambio. Hay que verificar siempre releyendo
  después de escribir.
- **Las plantillas de los Sprints 3 y 4** siguen con el formato viejo: no entran
  en estas reglas.

---

## 7. Registro de aplicación

| Fecha | Documento | Camino | Resultado |
|---|---|---|---|
| 02/10/26 | `docs/documento/Proyecto SI2 Grupo15 - copia.docx` | edición directa (scripts de `historico/` y sus versiones generales) | aprobado por el equipo |
| 02/10/26 | OneDrive `Proyecto SI2 Grupo15.docx` | A: `trasplantar.py` + `actualizar_us32.py` | `verificar.py` OK; respaldo `Proyecto SI2 Grupo15 - respaldo 2026-10-02.docx` al lado |
