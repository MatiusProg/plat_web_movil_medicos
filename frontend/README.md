# Frontend web

React + Vite + TailwindCSS, en TypeScript.

## Levantarlo

```bash
npm install
cp .env.example .env.local     # ya viene apuntando a localhost:8000
npm run dev                    # http://localhost:5173
```

**El backend tiene que estar corriendo.** Si no, la pantalla de login lo dice
en vez de quedarse esperando:

```bash
cd ../backend
.venv\Scripts\activate         # Windows
python manage.py runserver
```

El puerto **5173 no se cambia**: es el que está en `CORS_ALLOWED_ORIGINS` de
`config/settings.py`, y moverlo obliga a tocar el `.env` de los seis.

## Comandos

| Comando | Qué hace |
|---|---|
| `npm run dev` | servidor de desarrollo con recarga en caliente |
| `npm run build` | verifica los tipos y compila a `dist/` |
| `npm run lint` | oxlint |
| `npm run preview` | sirve lo compilado, para probar el build |

**Antes de abrir un pull request**, `npm run build` y `npm run lint` tienen que
pasar los dos: el `build` corre `tsc` en modo estricto, así que un error de
tipos frena ahí y no en la demostración.

## Estructura

```
src/
  api/           el contrato con el backend (tipos, cliente HTTP, endpoints)
  sesion/        estado de la sesión, renovación automática, localStorage
  componentes/   los reutilizables: Campo, Boton, Aviso, iconos, PanelMarca
  paginas/       una carpeta por pantalla
  rutas/         RutaProtegida y useTitulo
```

**Regla del archivo compartido**, igual que en el backend: si dos personas van
a tocar el mismo archivo en el mismo sprint, se parte en un paquete antes de
empezar, no después del primer conflicto.

## Antes de escribir código acá

Leé **[docs/frontend/decisiones.md](../docs/frontend/decisiones.md)**: qué se
eligió, por qué, y qué queda pendiente de acordar en el Sprint 1 —incluido el
idioma del código, que acá es español y en el backend es inglés.
