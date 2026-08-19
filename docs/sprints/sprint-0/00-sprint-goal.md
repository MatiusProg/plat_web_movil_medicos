# Sprint 0 — Objetivo

**Periodo:** 19 al 27 de agosto de 2026
**Definido en:** Sprint Planning 0

## Objetivo

> Al 27 de agosto, cualquier integrante puede clonar el repositorio, levantar
> el entorno con un comando y tomar una historia del tablero sin preguntar
> nada a nadie.

## Cómo se verifica

Se cumple si los seis integrantes ejecutan y reportan sin errores:

1. `git clone` y `docker compose up -d`
2. `python manage.py migrate` contra la base local
3. `flutter doctor -v` limpio
4. Acceso al tablero de Jira con las historias visibles

## Alcance

Sprint de preparación: no se desarrolla funcionalidad. Se monta la
infraestructura, se acuerdan las reglas de trabajo y se deja el backlog
listo para el Sprint 1.
