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

Antes de compilar, subir la versión en `mobile/pubspec.yaml`
(`version: 1.5.0+5` → `1.5.1+6`: el número después del `+` tiene que crecer
siempre, o Android no deja instalar encima).

```bash
cd mobile
flutter test                       # 185 pruebas al 01/11/26; si alguna falla, no se publica
flutter build apk --release \
    --dart-define=API_BASE_URL=https://web-production-872fa.up.railway.app/api \
    --dart-define=FIREBASE_API_KEY=<valor> \
    --dart-define=FIREBASE_APP_ID=<valor> \
    --dart-define=FIREBASE_MESSAGING_SENDER_ID=<valor> \
    --dart-define=FIREBASE_PROJECT_ID=<valor>
```

En PowerShell el salto de línea es el acento grave (`` ` ``), no la barra
invertida; o se escribe todo en una sola línea.

El archivo queda en `mobile/build/app/outputs/flutter-apk/app-release.apk`.

**El `--dart-define` de la API no es opcional.** Sin él la aplicación queda
apuntando a `http://localhost:8000/api`, que en un teléfono no existe: la
pantalla de ingreso se ve perfecta y ninguna petición llega a ningún lado. Es
el error que más fácil se cuela, porque **compila sin una sola advertencia**.

**Los cuatro de Firebase activan el push (US-28).** Salen de la consola de
Firebase: *Configuración del proyecto → General → tu app Android*, o del
`google-services.json` de esa app (`api_key.current_key`,
`client_info.mobilesdk_app_id`, `project_info.project_number` y
`project_info.project_id`). No son secretos como la credencial del backend,
pero **no van al repositorio**. Sin ellos la APK compila y funciona entera,
pero el teléfono no se registra y **no recibe avisos**, también sin ninguna
advertencia. La v1.5.0 salió así; la **v1.5.1** (01/11/26) ya los lleva.
Para el push hacen falta las dos puntas: estos cuatro en la APK y
`FIREBASE_CREDENTIALS` (la cuenta de servicio del mismo proyecto) en el
backend de Railway, que ya está cargada.

Para comprobar que los cuatro quedaron adentro, igual que la URL de abajo:
`grep -a -c "<FIREBASE_PROJECT_ID>"` sobre `libapp.so` tiene que dar 1 o más.

Para comprobar que la URL quedó adentro antes de publicar:

```bash
unzip -p build/app/outputs/flutter-apk/app-release.apk lib/arm64-v8a/libapp.so | grep -a -c "web-production-872fa"
# tiene que dar 1 o más
```

Después, en GitHub:

1. *Releases → Draft a new release*.
2. *Choose a tag*: escribir la etiqueta nueva (`v1.5.1`) y *Create new tag on
   publish*, sobre `main`.
3. Título `App móvil v1.5.1 — …` y en la descripción qué cambia y cómo se
   instala (copiar el formato de la anterior).
4. Renombrar el archivo a `centro-medico-v1.5.1.apk` y **arrastrarlo como
   asset**. Uno solo.
5. Dejar marcado **«Set as the latest release»** y *Publish release*.

O desde la terminal, con `gh`:

```bash
cp build/app/outputs/flutter-apk/app-release.apk centro-medico-v1.5.1.apk
gh release create v1.5.1 centro-medico-v1.5.1.apk --target main --latest \
    --title "App móvil v1.5.1 — notificaciones push" --notes "…"
```

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
