# Frontend web — decisiones del arranque

El proyecto de `frontend/` se creó junto con **US-02** (inicio de sesión),
porque la historia necesita una pantalla y la carpeta estaba vacía.

> **Esto es un borrador para acordar en el Sprint 1.** El README dice que el
> frontend se fija en el Sprint 1, así que estas decisiones las tomó una sola
> persona por necesidad, no por acuerdo. Que salgan modificadas es buena señal
> — igual que la Definición de Terminado.

---

## Lo que ya estaba decidido

No lo elegí yo: está en el documento del proyecto, apartado 2.2.2 —
*"React con Vite y TailwindCSS (frontend web)"*.

| Pieza | Versión |
|---|---|
| React | 19.2 |
| Vite | 8.2 |
| Tailwind CSS | 4.3 |

## Lo que hubo que decidir

| Decisión | Qué se eligió | Por qué |
|---|---|---|
| Lenguaje | **TypeScript** | La respuesta del login tiene diez campos anidados y cinco códigos de error. Con TypeScript, cambiar el contrato del backend rompe la compilación; sin él, rompe en pantalla y recién en la demostración. |
| Rutas | **react-router-dom 7** | Es el estándar de facto y lo que la mayoría de los tutoriales asume. No hay razón para buscar otra cosa. |
| Estado global | **Context de React**, sin librería | Lo único global hoy es la sesión. Redux o Zustand para un objeto sería traer una dependencia por adelantado. Si en el Sprint 2 aparece estado compartido de verdad —la agenda, el carrito de fichas—, se revisa. |
| Datos del servidor | **`fetch` envuelto**, sin TanStack Query | Mismo criterio: tres endpoints no justifican una capa de caché. Es la primera candidata a entrar cuando lleguen las pantallas de listado. |
| Iconos | **SVG a mano** | Son ocho trazos. Un paquete de iconos pesa más que toda la aplicación de hoy. |
| Alias de importación | `@/` → `src/` | Para no encadenar `../../`. |

## El idioma del código

**El frontend está escrito en español; el backend, en inglés.** No es un
descuido, pero **hay que acordarlo**: es la decisión de esta lista que más
conviene discutir.

`docs/convenciones-de-codigo.md` §3 fija el inglés, pero ese documento se
titula *"Convenciones de código — backend"* y su argumento es específico del
backend: Django, DRF y la nomenclatura HL7 FHIR, cuyos recursos —`Patient`,
`Practitioner`, `Encounter`— son en inglés. Ninguna de esas tres razones
alcanza al frontend.

Lo que **sí** queda en inglés, y no es negociable:

- **Los campos del contrato con la API** (`access`, `refresh`, `organization`,
  `permissions`). Traducirlos obligaría a mapear en cada petición y a mantener
  dos vocabularios para la misma cosa.
- **Lo que impone React**: `useState`, `className`, `onChange`, los nombres de
  los archivos de configuración.

Si el equipo prefiere el inglés también acá, el cambio es mecánico y conviene
hacerlo ahora, con cinco archivos, y no en el Sprint 3.

## Dónde se guardan los tokens

En **`localStorage`**, y tiene un costo que hay que decir en voz alta.

- **A favor:** recargar la pestaña no te echa, que es lo mínimo que se espera.
- **En contra:** `localStorage` es legible por cualquier JavaScript de la
  página. Un XSS se lleva la sesión.
- **La alternativa** —cookie `HttpOnly` + `SameSite`— es más segura, pero exige
  que el backend emita y lea cookies. Hoy no lo hace: `config/settings.py`
  declara la API como pura, sin `SessionMiddleware`, y con un comentario que
  explica por qué.
- **Mitigación mientras tanto:** el acceso dura 30 minutos y el refresco rota
  en cada uso, así que una fuga tiene ventana corta.

**Queda anotado para revisar antes de producción.** No es una decisión cerrada.

---

## Estructura

```
frontend/src/
  api/           el contrato con el backend
    tipos.ts       las formas que devuelve accounts, y ErrorApi
    cliente.ts     fetch envuelto: token, X-Organization, errores
    autenticacion.ts  US-02: login, refresh, logout
  sesion/        el estado de la sesión
    almacenamiento.ts  localStorage, con todos los accesos envueltos
    ContextoSesion.tsx renovación automática y sincronía entre pestañas
    useSesion.ts       el hook, en archivo aparte por la recarga en caliente
  componentes/   los reutilizables: Campo, Boton, Aviso, iconos, PanelMarca
  paginas/       una carpeta por pantalla
  rutas/         RutaProtegida y useTitulo
```

**Regla del archivo compartido**, igual que en el backend: si dos personas van
a tocar el mismo archivo en el mismo sprint, se parte antes de empezar.

## Cómo se levanta

```bash
cd frontend
npm install
cp .env.example .env.local     # ya viene apuntando a localhost:8000
npm run dev                    # http://localhost:5173
```

El backend tiene que estar corriendo. El puerto **5173 no se cambia**: es el
que está en `CORS_ALLOWED_ORIGINS` de `config/settings.py`, y moverlo obliga a
tocar el `.env` de los seis.

## Lo que falta

- **Verificar el diseño en un teléfono real.** Está escrito para adaptarse
  —bajo 1024 px el panel de marca se colapsa y el formulario ocupa todo— pero
  se probó en escritorio.
- **Pruebas automatizadas.** No hay ninguna todavía. Vitest + Testing Library
  es el camino natural; conviene decidirlo antes de que haya diez pantallas.
- **`prefers-reduced-motion`** está respetado, pero no se probó con lector de
  pantalla.
