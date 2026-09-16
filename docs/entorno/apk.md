# La APK: cómo se instala y cómo se publica una nueva

Dos públicos y dos mitades. La primera es para quien **sólo quiere usar la
aplicación** en su teléfono — la docente, alguien del equipo que no compila, un
compañero que quiere probarla —. La segunda es para quien **publica una versión
nueva** después de un cambio.

---

## 1 · Instalarla

**Descarga:** <https://github.com/MatiusProg/plat_web_movil_medicos/releases/latest>

Se baja el archivo `.apk` que figura como *asset* de esa publicación.

| Requisito | Detalle |
|---|---|
| Android | **7.0 o superior** (API 24) |
| Espacio | ~130 MB con la aplicación instalada; el archivo pesa 54 MB |
| Conexión | Sí. La aplicación habla con la API desplegada en Railway |

**Pasos en el teléfono:**

1. Abrir el enlace y descargar el `.apk`.
2. Al abrirlo, Android avisa que la aplicación viene de un **origen
   desconocido**. Hay que permitirlo para la aplicación desde la que se
   descargó (Chrome, o el gestor de archivos): *Ajustes → Aplicaciones →
   Acceso especial → Instalar aplicaciones desconocidas*.
3. Instalar. **Play Protect puede advertir que no reconoce al desarrollador**
   — «Instalar de todas formas»—. No es un falso positivo raro ni algo que se
   pueda desactivar desde el proyecto: ver el punto 3 de abajo.
4. Abrir **Centro Médico** e iniciar sesión. En el campo *Centro médico* va el
   identificador de la organización; se deja vacío **sólo** para administrar la
   plataforma.

**Instalar una versión nueva encima de una vieja no borra nada** y no hace falta
desinstalar primero: mantienen la misma firma. Si Android rechaza la
instalación con «la aplicación no se instaló», casi siempre es porque la que
está instalada se compiló en otra máquina —otra clave de depuración—; ahí sí
hay que desinstalar antes.

> **A qué backend le pega.** La APK publicada apunta a la API de Railway. No
> hay forma de cambiarlo desde la aplicación: la dirección se fija al compilar.
> Para probar contra un backend local hay que compilarse una propia, con el
> `--dart-define` del punto 2.

---

## 2 · Publicar una versión nueva

```bash
cd mobile
flutter test                       # 93 pruebas; si alguna falla, no se publica
flutter build apk --release \
    --dart-define=API_BASE_URL=https://web-production-872fa.up.railway.app/api
```

El archivo queda en `mobile/build/app/outputs/flutter-apk/app-release.apk`.

**El `--dart-define` no es opcional.** Sin él la aplicación queda apuntando a
`http://localhost:8000/api`, que en un teléfono no existe: la pantalla de
ingreso se ve perfecta y ninguna petición llega a ningún lado. Es el error que
más fácil se cuela, porque **compila sin una sola advertencia**.

Después, en GitHub: *Releases → Draft a new release*, etiqueta nueva
(`movil-v0.3.0` y así), **subir el `.apk` como asset** y publicar.

### El enlace del README no se toca — y esa es la idea

El README apunta a **`/releases/latest`**, que GitHub resuelve solo a la
publicación más reciente. Así que al subir una versión nueva **no hay que
actualizar ningún enlace en ninguna parte**: quien ya tenía el link guardado
—la docente, por ejemplo— baja la nueva sin que nadie le avise.

Lo que sí hay que respetar para que eso funcione:

- La publicación tiene que quedar marcada como **«Set as the latest release»**.
  Es lo que decide qué devuelve `/releases/latest`.
- Si se publica como *pre-release* o como borrador, **no cuenta como la última**
  y el enlace sigue entregando la anterior. Es el único modo de romperlo.
- Un solo `.apk` por publicación. Con dos assets, quien entra no sabe cuál
  bajar.

> Si algún día la distribución pasa a Drive o a un enlace directo a un archivo,
> **eso deja de ser cierto**: cada archivo nuevo es una URL nueva y hay que
> actualizarla a mano en el README y avisarle a quien la tenga guardada. Es
> exactamente la tarea que este esquema evita.

---

## 3 · Por qué Android desconfía, y por qué está bien así

La APK se firma con la **clave de depuración**, no con una de publicación:
`android/app/build.gradle.kts` lo dice con todas las letras —«Signing with the
debug keys for now»—. Para un proyecto de materia alcanza, y es la razón de la
advertencia de Play Protect.

Lo que implica, para decirlo antes de que lo pregunten:

- **No se puede subir a Google Play así.** Play exige una clave propia y un
  proceso de publicación.
- **Dos personas que compilen en máquinas distintas producen APK
  incompatibles**: cada máquina tiene su propia clave de depuración, y Android
  no deja actualizar una aplicación con una firma que no es la misma. Por eso
  conviene que las publicaciones las haga siempre la misma persona, o que se
  comparta una clave de publicación de verdad.

Lo que **no** implica: que la conexión sea insegura. La aplicación habla con la
API por HTTPS igual que la web; la firma es la identidad de quien publica, no
el cifrado del tráfico.
