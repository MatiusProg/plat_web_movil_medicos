# Cómo contribuir

Reglas de trabajo del Grupo 15. Se acordaron en el Sprint Planning 0 y
cualquier cambio se discute en una retrospectiva, no por mensaje suelto.

---

## Ramas

`main` está protegida: nadie empuja directo, ni siquiera el dueño del
repositorio. Todo entra por pull request.

Nomenclatura, con el identificador de la tarjeta de Jira al principio:

```
feat/KOL-12-registro-de-pacientes
fix/KOL-45-error-en-agenda
docs/KOL-03-capitulo-2
chore/KOL-07-configuracion-docker
```

| Prefijo | Cuándo |
|---|---|
| `feat/` | Funcionalidad nueva |
| `fix/` | Corrección de un defecto |
| `docs/` | Documentación, actas, capítulos |
| `chore/` | Configuración, dependencias, infraestructura |

Una rama por historia. Ramas de vida corta: si lleva más de tres días
abierta, la historia era demasiado grande y conviene partirla.

---

## Commits

```
KOL-12: agregar validación de cédula en el registro
```

El identificador va al principio para que la integración GitHub–Jira vincule
el commit con la tarjeta automáticamente. Mensaje en español, en infinitivo,
describiendo qué hace el cambio y no qué archivo se tocó.

---

## Pull requests

1. Rama desde `main` actualizada.
2. PR con título `KOL-12: descripción breve`.
3. Al menos **una aprobación** antes de fusionar.
4. Quien revisa no es quien escribió el código.
5. Fusionar con *Squash and merge* para mantener el historial legible.
6. Borrar la rama después de fusionar.

Revisar un PR no es un trámite. Si algo no se entiende, se pregunta en el PR
—no por WhatsApp— para que la discusión quede registrada.

---

## Definición de Terminado

> **Borrador para acordar en el Sprint Planning 0.** El equipo puede modificar,
> quitar o agregar criterios. Que salga modificado es buena señal.

Una historia está terminada cuando:

1. Cumple **todos** sus criterios de aceptación y el Product Owner lo confirmó.
2. El código entró a `main` por pull request con al menos una aprobación.
3. Las pruebas pasan en local sin errores.
4. Si la historia crea o modifica una tabla con `tenant_id`, esa tabla tiene
   `ENABLE` y `FORCE ROW LEVEL SECURITY`, y existe una prueba que verifica que
   un inquilino no ve los datos de otro.
5. No hay credenciales ni datos de personas reales en el código.
6. La tarjeta de Jira está en *Done*, con el enlace al pull request.

---

## Credenciales

El repositorio es público. Una credencial commiteada se considera comprometida
en minutos, no en días: hay bots que vigilan el flujo público de commits
buscando exactamente cadenas de conexión y claves de API.

- Los valores reales viven en el `.env` local y en las variables de Railway.
- El `.env` está en `.gitignore`. Nunca se fuerza su inclusión.
- *Push protection* está activo y bloquea el envío si detecta un secreto.
- Si algo se filtra: **rotar la credencial de inmediato**. Borrar el commit no
  sirve, el historial lo conserva y en un repositorio público alguien ya lo copió.

---

## Base de datos

- **Desarrollo:** PostgreSQL local con Docker Compose. Cada uno el suyo.
- **Demostración:** Supabase. Entorno compartido — no se corren migraciones
  experimentales ahí.

Django se conecta siempre como `app_user`, nunca como `postgres`. El porqué
está en el README, en la sección de aislamiento multi-inquilino. Vale la pena
leerla antes del primer pull request que toque la base.
