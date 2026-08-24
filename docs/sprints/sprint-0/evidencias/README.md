# Evidencias del Sprint 0

Capturas de las funcionalidades terminadas, tomadas contra el entorno real
—backend en `localhost:8000`, frontend en `localhost:5173`— y no sobre un
prototipo.

> **Todos los datos son ficticios.** El repositorio es público: no se cargan
> datos de personas reales en ningún entorno, ni en fixtures, ni en capturas.
> El usuario `ana@kolping.test` y la organización `kolping` se crean con un
> script local de datos de prueba.

---

## US-02 — Inicio de sesión (Karen)

| Captura | Qué demuestra |
|---|---|
| [`us02-01-formulario-de-inicio-de-sesion.jpg`](us02-01-formulario-de-inicio-de-sesion.jpg) | El formulario. El campo **Centro médico** es lo que resuelve el inquilino: el correo es único por organización, no global. El panel de la izquierda confirma a cuál se está entrando. |
| [`us02-02-credenciales-incorrectas.jpg`](us02-02-credenciales-incorrectas.jpg) | Contraseña incorrecta → **401**. Un correo inexistente devuelve **exactamente esta misma respuesta**: desde el formulario no se puede averiguar qué correos están registrados. |
| [`us02-03-sesion-iniciada-roles-y-permisos.jpg`](us02-03-sesion-iniciada-roles-y-permisos.jpg) | Sesión abierta con los **roles y permisos** que devolvió el backend. Es la parte *"para acceder a las funciones según mi rol"* de la historia: con esto el frontend sabe qué menú dibujar. |
| [`us02-04-cuenta-bloqueada-rnf-07.jpg`](us02-04-cuenta-bloqueada-rnf-07.jpg) | **RNF-07** cumplido: a los 5 intentos fallidos la cuenta se bloquea 15 minutos y **no entra ni con la contraseña correcta** (HTTP 423). La cuenta regresiva corre en vivo y el formulario queda deshabilitado hasta que venza. |

### Lo que las capturas no muestran

Estas cuatro cubren lo que se ve. El resto de la historia se verifica con las
**34 pruebas automatizadas** de `backend/tests/test_us02.py`, que entran por
HTTP como un cliente real:

- **RNF-08** en el propio login: un usuario no entra por el slug de otra
  organización, y dos organizaciones pueden compartir el mismo correo.
- **RNF-06**: la renovación del token rota el refresco, y el anterior deja de
  servir.
- **CU4**: el cierre de sesión manda el refresco a la lista negra.
- La **bitácora de intentos**: cada intento —exitoso o no— deja su fila en
  `login_attempts`, que sólo puede leer el Superadministrador de Plataforma.

Para reproducirlo:

```bash
cd backend
.venv\Scripts\activate
pytest tests/test_us02.py -v
```
