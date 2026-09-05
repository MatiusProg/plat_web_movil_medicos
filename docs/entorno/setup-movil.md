# Entorno móvil — Flutter

Guía de instalación para los seis integrantes. Al terminar, `flutter doctor -v`
debe salir limpio: ese es el criterio de terminado de la tarea 6 del Sprint 0.

---

## Versiones acordadas

**Todos instalan la misma versión.** La deriva de versiones rompe compilaciones
y produce errores que parecen de código pero no lo son.

| Componente | Versión |
|---|---|
| Flutter SDK | **3.47.2** (canal `stable`, publicada el 27/08/2026) |
| Dart | **3.13.2** (la que trae ese Flutter) |
| Android Studio | _(la última estable; no fija la compilación)_ |
| Android SDK Platform | API 34 |
| JDK | 17 |

> **Cómo se fijó esta versión.** La tabla estaba en `_(completar)_` y el shell
> de Flutter no podía esperar: es la última estable al momento de crear el
> proyecto, y es con la que `mobile/` está generado y probado. Si el Scrum
> Master prefiere otra, se cambia acá y se corre `flutter test` en `mobile/`
> antes de que el resto instale.

La versión de Android Studio no entra en la tabla a propósito: no interviene en
la compilación, sólo aporta el SDK de Android y el emulador. Lo que sí tiene
que coincidir es la API 34.

---

## Qué instalar y en qué orden

**Android Studio para la cadena de herramientas, VS Code para escribir código.**
No son alternativas. Android Studio es la forma razonable de obtener el Android
SDK, las platform-tools y el emulador, pero el resto del proyecto —Django,
React— vive en VS Code y nadie debería alternar entre dos editores.

### 1. Flutter SDK

Descargar de `docs.flutter.dev/get-started/install` y descomprimir en una ruta
**sin espacios ni tildes**:

- Windows: `C:\src\flutter`
- macOS / Linux: `~/development/flutter`

Agregar `flutter/bin` al PATH.

En Windows, evitar `C:\Program Files` y el escritorio: los espacios en la ruta
producen fallos intermitentes en las herramientas de compilación.

### 2. Android Studio

Durante la instalación, aceptar los tres componentes:

- Android SDK
- Android SDK Command-line Tools
- Android Emulator

Después, en **More Actions ▸ SDK Manager ▸ SDK Platforms**, instalar la API 34.

Aceptar las licencias:

```bash
flutter doctor --android-licenses
```

### 3. VS Code

Instalar las extensiones **Flutter** y **Dart**. Al abrir la carpeta `mobile/`
del repositorio, VS Code las ofrece solo: están declaradas en
`mobile/.vscode/extensions.json`.

---

## Verificación

```bash
flutter doctor -v
```

Debe salir sin errores. Los avisos sobre Xcode o desarrollo para Windows se
pueden ignorar: no aplican al proyecto.

**Al reportar la tarea en la daily, pegar la salida del comando.** No alcanza
con decir "ya instalé".

---

## Emulador o dispositivo físico

> **Decisión registrada (05/09/2026): se trabaja con celular por USB, no con
> emulador.** El emulador exige demasiado a las máquinas del equipo, y la
> demostración final se hace igual sobre un teléfono real. Android Studio se
> instala igual —hace falta por el SDK, las platform-tools y el `adb` que
> reconoce el teléfono—, pero **no se crea ningún dispositivo virtual**.
>
> Consecuencia práctica: `flutter devices` tiene que listar el celular
> conectado. Si no aparece, el problema es el cable, la depuración por USB o el
> diálogo de autorización — no el proyecto.

El conjunto ocupa entre 15 y 20 GB en disco. El emulador pide 16 GB de RAM para
ser usable; con 8 GB arranca pero se arrastra y vuelve lento cada ciclo de
prueba. Ése es el motivo de la decisión de arriba.

**Un celular Android por USB es más rápido, no consume RAM del equipo y además
es la condición real de la demostración.** No es un parche: es la forma de
trabajo elegida.

Para habilitarlo:

1. **Ajustes ▸ Información del teléfono**, tocar siete veces *Número de compilación*
2. **Ajustes ▸ Opciones de desarrollador**, activar *Depuración por USB*
3. Conectar y aceptar el diálogo de autorización

Comprobar:

```bash
flutter devices
```

### Con el celular por USB, la API no está en `localhost`

Esto es consecuencia directa de no usar emulador y es el primer tropiezo
garantizado. Para el teléfono, `localhost` es el propio teléfono: el backend no
está ahí.

1. Averiguá la IP de tu máquina en la red local (`ipconfig` en Windows).
2. Levantá Django escuchando fuera de localhost:

   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```

3. Pasale esa IP a la aplicación:

   ```bash
   flutter run --dart-define=API_BASE_URL=http://192.168.0.15:8000/api
   ```

El teléfono y la computadora tienen que estar en la **misma red**. Si el
firewall de Windows pregunta, hay que permitir Python en redes privadas.

---

## Ahorro de ancho de banda

El SDK de Flutter y el instalador de Android Studio suman varios gigabytes.
**Una persona los descarga y los comparte por USB o red local** en la reunión.
Bajar 20 GB seis veces es medio Sprint 0 perdido en algo que no es trabajo.

---

## Problemas frecuentes

| Síntoma | Causa | Solución |
|---|---|---|
| `flutter: command not found` | PATH mal configurado | Reabrir la terminal; verificar la variable de entorno |
| `cmdline-tools component is missing` | Falta un componente del SDK | SDK Manager ▸ SDK Tools ▸ Android SDK Command-line Tools |
| `Android license status unknown` | Licencias sin aceptar | `flutter doctor --android-licenses` |
| Compila en una máquina y en otra no | Versiones distintas de Flutter | Alinear con la tabla de arriba |
| Conflicto en `local.properties` | Archivo commiteado por error | Ya está en `.gitignore`; sacarlo del índice con `git rm --cached` |

---

## Nota sobre `local.properties`

`mobile/android/local.properties` contiene la ruta del SDK de **cada máquina**.
Está en `.gitignore` y no debe subirse: si entra al repositorio, genera
conflicto en cada `git pull` para los otros cinco.
