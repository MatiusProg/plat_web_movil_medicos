# Acta — Sprint Planning 0

**Fecha:** __ de agosto de 2026
**Hora:** __:__ a __:__
**Modalidad:** ______
**Facilita:** Luis Mateo (Scrum Master)

## Asistentes

| Integrante | Rol | Asistió |
|---|---|---|
| Luis Mateo | Scrum Master | |
| Alexander Osinaga Blanco | Product Owner | |
| Karen Ortega | Developer | |
| Aguayo | Developer | |
| Iporo | Developer | |
| Mamani | Developer | |

## 1. Decisión de infraestructura

Se adopta **Supabase** como PostgreSQL gestionado para el entorno de
demostración, en reemplazo de una base propia en Railway. Railway se mantiene
para hospedar la aplicación Django.

Verificado antes de la reunión:

- pgvector habilitado y operativo (operador `<=>` funcionando)
- Rol `app_user` creado sin `BYPASSRLS`
- Prueba de aislamiento multi-inquilino: cada inquilino ve solo sus filas;
  sin `app.tenant_id` definido, cero filas

Evidencia en `evidencias/`.

**Consecuencias acordadas:**

- Django y Pytest se conectan como `app_user`, nunca como `postgres`
- Toda tabla con `tenant_id` lleva `ENABLE` y `FORCE ROW LEVEL SECURITY`
- El middleware usa `SET LOCAL`, nunca `SET`
- Desarrollo local en Docker; Supabase solo para demostración

_Observaciones del equipo:_

## 2. Definición de Terminado

Borrador presentado en `CONTRIBUTING.md`. Acuerdo alcanzado:

_(anotar los criterios finales, incluyendo los que el equipo modificó o agregó)_

## 3. Ritmo de trabajo

| Acuerdo | Valor |
|---|---|
| Hora límite de la daily | |
| Canal donde se escribe | |
| Quién consolida en el repositorio | Luis Mateo |
| Día y hora de la Review | |
| Día y hora de la Retrospectiva | |

## 4. Reparto del Sprint 0

| # | Tarea | Responsable | Terminado cuando |
|---|---|---|---|
| 1 | Proyecto Supabase, pgvector, rol y prueba de RLS | Luis Mateo | Hecho |
| 2 | Repositorio público, colaboradores, protección de `main` | Luis Mateo | Hecho |
| 3 | Esqueleto del repositorio y documentación base | Luis Mateo | Hecho |
| 4 | Proyecto Jira, épicas, backlog importado, sprints | | Tablero visible para los 6 |
| 5 | Entorno local (Docker + Django) | Todos | `migrate` sin errores |
| 6 | Entorno móvil (Flutter + Android Studio) | Todos | `flutter doctor -v` limpio |
| 7 | Despliegue mínimo en Railway contra Supabase | | URL pública responde |
| 8 | Guía de instalación en `docs/entorno/` | | Un tercero la sigue sin ayuda |

## 5. Objetivo del sprint

Leído y confirmado por el equipo. Ver `00-sprint-goal.md`.

## Acuerdos pendientes

| Tema | Responsable | Fecha |
|---|---|---|
| | | |
