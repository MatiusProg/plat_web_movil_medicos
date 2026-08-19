# Entorno móvil — Flutter

Guía de instalación para los seis integrantes. Al terminar, `flutter doctor -v`
debe salir limpio: ese es el criterio de terminado de la tarea 6 del Sprint 0.

---

## Versiones acordadas

**Todos instalan la misma versión.** La deriva de versiones rompe compilaciones
y produce errores que parecen de código pero no lo son. El Scrum Master instala
primero, corre `flutter --version` y completa esta tabla; el resto se ajusta.

| Componente | Versión |
|---|---|
| Flutter SDK | _(completar)_ |
| Dart | _(la que trae Flutter)_ |
| Android Studio | _(completar)_ |
| Android SDK Platform | API 34 |
| JDK | 17 |

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

El conjunto ocupa entre 15 y 20 GB en disco. El emulador pide 16 GB de RAM para
ser usable; con 8 GB arranca pero se arrastra y vuelve lento cada ciclo de
prueba.

**Un celular Android por USB es la mejor opción para la mayoría.** Es más
rápido, no consume RAM del equipo y además es la condición real de la
demostración. No es un parche: es la alternativa recomendada.

Para habilitarlo:

1. **Ajustes ▸ Información del teléfono**, tocar siete veces *Número de compilación*
2. **Ajustes ▸ Opciones de desarrollador**, activar *Depuración por USB*
3. Conectar y aceptar el diálogo de autorización

Comprobar:

```bash
flutter devices
```

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
