# Guía de diseño de la web

**Es obligatoria.** Toda pantalla nueva o modificada la cumple, en todos los
roles (superadministrador, administración, recepción, médico y paciente). Si
algo de acá no te sirve para tu caso, se discute y se cambia la guía, no se
hace una excepción en una pantalla.

La revisión de un pull request que toca `frontend/` incluye esta guía, igual
que la Definición de Terminado de `CONTRIBUTING.md`.

---

## 1. Principios

1. **Primero lo que la persona vino a hacer.** Cada pantalla tiene una tarea
   principal; esa tarea tiene el único botón primario y el lugar más visible.
2. **Nada interno a la vista.** Ni códigos de historia (`US-24`), ni códigos de
   permiso (`catalog.branch.read`), ni nombres de tabla. La gente ve palabras.
3. **Nunca se esconde información en silencio.** Una lista se pagina, no se
   corta (ver §6). Si algo no está disponible, se dice por qué.
4. **No se ofrece lo que no se puede usar.** Si el rol o el plan del centro no
   lo permiten, la opción no aparece (la barra ya lo hace: §4).
5. **Coherencia antes que creatividad.** Una pantalla nueva se parece a las que
   ya existen; usa los componentes de §5 antes de dibujar uno propio.

---

## 2. Color

Sólo los tokens de `frontend/src/index.css`. **Ningún color fuera de ellos**
(nada de `blue-600`, `purple-500`, hex sueltos).

| Token | Para qué | Ejemplos |
|---|---|---|
| `marca-*` (verde azulado) | la acción y lo activo | botón primario, opción activa del menú, enlaces |
| `tinta-*` (pizarra) | todo lo demás | texto, bordes, fondos, la barra lateral |
| `alerta-*` (rojo) | lo destructivo y los errores | Desactivar, Restaurar, mensajes de error |
| `espera-*` (ámbar) | lo pendiente, lo que hay que mirar | borrador, «la próxima copia se puede…» |
| `emerald-*` | sólo estados «activo / correcto» | indicador de activo |

- Texto principal `tinta-900` (oscuro: `tinta-100`); secundario `tinta-500`.
- Fondo de página `tinta-50` (oscuro: `tinta-950`); paneles `white`
  (oscuro: `tinta-900/50`).
- **Todo lo que tiene color en claro tiene su `dark:`**. Se prueba en los dos.
- El color nunca es la única señal: un estado lleva también texto o ícono.

## 3. Tipografía

- **Figtree** para todo (`--font-sans`). Números que cambian (contadores,
  horas en tablas): `tabular-nums`.
- Escala fija:

| Uso | Clases |
|---|---|
| Título de página (uno por pantalla, `<h1>`) | `text-2xl font-semibold tracking-tight` |
| Título de sección o panel (`<h2>`) | `font-semibold` (16 px) |
| Texto corriente | `text-[0.9375rem]` o `text-sm` |
| Ayudas, metadatos, pies | `text-xs` / `text-sm text-tinta-500` |

- **Prohibido:** mayúsculas para rótulos (`uppercase tracking-wider`),
  resaltar una sola palabra de un título, monoespaciada para datos comunes.
- Líneas de texto de menos de ~80 caracteres (`max-w-2xl` en descripciones).

## 4. La estructura de la página

```
┌──────────┬─────────────────────────────────────────────────┐
│  Barra   │  Rótulo (opcional, frase corta)                 │
│ lateral  │  Título de la página               [Acciones]   │
│ agrupada │  Descripción de una o dos líneas                │
│          │                                                 │
│          │  [Filtros / buscador]                           │
│          │  Contenido (lista, tabla, formulario)           │
│          │  Paginador                                      │
└──────────┴─────────────────────────────────────────────────┘
```

- Contenedor: `mx-auto max-w-5xl px-5 py-8 sm:py-10` (formularios y detalles:
  `max-w-4xl`; listas anchas: `max-w-6xl`). Separación vertical `space-y-6`.
- **Cabecera:** título a la izquierda, acciones a la derecha y alineadas al
  pie del bloque (`flex flex-wrap items-end justify-between gap-4`). El rótulo
  de arriba es opcional, en minúsculas y sin códigos («Catálogo del centro
  médico», «Historia clínica»). Para el catálogo existe `CabeceraCatalogo`.
- **Sin scroll horizontal en la página, nunca.** Una tabla ancha va dentro de
  `overflow-x-auto` propio.
- Funciona desde 360 px de ancho: en móvil la barra es un cajón.

### La barra lateral (`componentes/BarraPlataforma.tsx`)

Toda entrada nueva del menú declara:

| Campo | Regla |
|---|---|
| `etiqueta` | dos o tres palabras, sustantivo («Copias de seguridad», no «Gestionar respaldos») |
| `seccion` | `General`, `Atención`, `Catálogo`, `Organización` o `Plataforma` |
| `icono` | uno **propio** que represente la tarea; no repetir el genérico |
| `requiere` | el permiso que la habilita (o `'plataforma'`) |
| `requierePlan` | la función del plan que necesita, si necesita una (p. ej. `ai_chatbot`) |

No se agregan secciones nuevas sin cambiar esta guía. Plegar: el tirador del
borde o `Ctrl+B`; plegada, cada opción muestra su nombre al pasar el mouse.

## 5. Componentes

**Antes de crear uno, usa estos** (`componentes/` y `paginas/catalogo_comun.tsx`):

| Componente | Cuándo |
|---|---|
| `Boton` | la acción principal. **Uno por pantalla** (y uno por formulario o modal). Ancho completo por defecto; en cabeceras, `className="w-auto"`. |
| `SECONDARY` | acciones secundarias (Editar, Actualizar, Cancelar) |
| `DANGER` | lo destructivo (Desactivar). Siempre con confirmación |
| `Paginador` | debajo de toda lista paginada (§6) |
| `ErrorCatalogo` / `AvisoCatalogo` | error y confirmación de una operación |
| `ConfirmacionCatalogo` | confirmar algo destructivo |
| `EstadoCatalogo`, `Etiqueta` | estado (Activa/Inactiva) y etiquetas cortas |

Reglas de los botones:

- Radio `rounded-lg`, alto `py-2.5`, `text-sm font-semibold`. Paneles y
  tarjetas, `rounded-2xl`; insignias, `rounded-full`.
- Ícono **al lado** del texto, nunca arriba. Sin `→` pegado al texto.
- El texto dice lo que pasa: «Guardar cambios», «Registrar servicio»,
  «Generar y descargar»; no «Enviar» ni «Aceptar».
- Un botón de sólo ícono lleva `aria-label`.
- Sin sombras grandes ni botones que «se levantan» al pasar el mouse.

Formularios: la etiqueta **arriba** del campo; la ayuda debajo en `text-xs`;
el error del campo debajo, en `alerta-*`. Al guardar, el botón muestra
`cargando` y no se puede tocar dos veces.

Modales: título claro, un `Boton` y «Cancelar»; se cierran con Escape y
clic afuera (salvo mientras guardan).

## 6. Listas y paginación

(Definición de Terminado, criterio 8.)

- **Una lista que la persona recorre se muestra paginada**: `pedirPagina` +
  `Paginador`. Si se puede buscar, buscador arriba, que vuelve a la página 1.
- **Un desplegable trae la lista completa**: `todasLasPaginas`.
- **Prohibido** quedarse con `pagina.results` de la primera página.

## 7. Estados

- **Cargando:** texto corto («Cargando servicios…»), no pantallas en blanco.
- **Vacío:** dice qué falta y qué hacer («No hay servicios. Registra el
  primero.»), con la acción a mano si el rol puede hacerla.
- **Error:** qué pasó y cómo seguir, sin disculpas ni códigos técnicos. Si el
  backend manda `detail`, se muestra ese texto.
- **Límite del plan** (`code: "plan_limit"`): se muestra el `detail` tal cual;
  ya habla del plan del centro médico.

## 8. Texto

- **Tuteo** (español de Bolivia): «Elige», «Tienes», «Puedes». Las pantallas
  viejas en voseo se pasan a tuteo cuando se tocan.
- Frases cortas, voz activa, sin relleno. Se nombran las cosas como las
  entiende quien usa el sistema (ficha, sucursal, atención), no como están en
  el código.
- Fechas `es-BO` y horas en 24 h (`hourCycle: 'h23'`).

## 9. Accesibilidad

- Foco visible en todo lo que se puede tocar con el teclado.
- Contraste suficiente en claro y oscuro (texto secundario nunca por debajo
  de `tinta-500` sobre blanco).
- Íconos decorativos con `aria-hidden`; los que son la única señal, con
  nombre accesible.
- `prefers-reduced-motion`: nada de animaciones que no respondan a una acción.

## 10. Antes de abrir el pull request

- [ ] La pantalla usa los componentes de §5 y sólo los tokens de §2.
- [ ] Ningún código interno a la vista (`US-…`, permisos, tablas).
- [ ] Probada con **cada rol** que la ve, en **claro y oscuro**, a 1280 px y
      a 390 px, sin scroll horizontal.
- [ ] Las listas paginan (§6); los vacíos y errores dicen qué hacer (§7).
- [ ] Si agrega una opción al menú, tiene `seccion`, ícono propio y, si hace
      falta, `requierePlan`.
- [ ] `npx tsc -b` y `npm run lint` en verde.
