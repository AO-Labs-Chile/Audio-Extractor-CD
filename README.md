# Audio Extractor CD 💽

![Release Version](https://img.shields.io/badge/Versión-1.1.1-blue)
![OS](https://img.shields.io/badge/OS-Windows_10%2B-lightgrey)
![Made in Chile](https://img.shields.io/badge/Desarrollado_en-Chile-red)

**Audio Extractor CD** es una herramienta moderna, rápida y profesional para digitalizar tu colección de CDs de audio físicos. Extrae pistas directamente desde la lectora óptica de tu computador (sector por sector) y conviértelas en formatos de altísima calidad sin pérdida, o en formatos comprimidos de máxima compatibilidad.

Desarrollado por **AO Labs Chile** ([www.aolabs.cl](https://www.aolabs.cl)).

---

## ✨ Características Principales

- **⚙️ Motor de Extracción Precisa:** Lectura directa del hardware (vía `win32`) que procesa tu disco sector por sector para asegurar que no haya saltos ni errores de audio.
- **🎵 Múltiples Formatos:** Exporta tu música en **FLAC** (calidad original sin pérdida), **MP3** (hasta 320 kbps), **WAV**, **AAC**, **OGG** y **OPUS**.
- **🌐 Metadatos Automáticos y Manuales:** Poderoso motor de búsqueda conectado a la API de **iTunes Store**, **Discogs** y **MusicBrainz**. Al insertar un disco, el programa detecta automáticamente álbumes y pistas, o te permite buscarlos en la base de datos de Discogs con un clic.
- **🖼️ Gestión de Portadas Inteligente:** Autodescarga carátulas en altísima resolución. Si no encuentra la correcta, puedes usar el buscador integrado, o cargar tu propia imagen `.jpg`/`.png` desde tu computador; la imagen quedará permanentemente inyectada dentro del archivo FLAC/MP3 y en la carpeta destino como `Folder.jpg`.
- **💻 Integración con Windows:** Configurado con "AutoPlay Handlers" para que Windows te sugiera extraer música automáticamente al insertar un disco. Además, incorpora bloqueo de múltiple apertura (si el programa ya está abierto, lo traerá al frente).
- **🔄 Actualizador Silencioso:** El instalador funciona inteligentemente como un actualizador para futuras versiones. Simplemente instálalo encima y actualizará todo el código sin necesidad de desinstalar nada y sin borrar tus configuraciones.
- **🎨 Interfaz Premium:** Un diseño oscuro (Dark Mode), responsivo, de carga rápida y moderno, utilizando `pywebview` para renderizar un motor web nativo de escritorio ligero y libre de dependencias pesadas.

---

## 🚀 Descarga e Instalación

Puedes descargar el programa oficial listo para usar desde la sección de **[Releases](https://github.com/)** a la derecha de esta pantalla. Ofrecemos dos versiones para Windows:

1. **Versión Instalador (`.exe`):** Instala el programa en tu sistema, crea accesos directos en tu escritorio y lo integra nativamente con Windows.
2. **Versión Portable (`.zip`):** Una versión autónoma que no requiere instalación. Descomprime y ejecuta `Audio_Extractor_CD_AO_Labs.exe` desde cualquier pendrive o carpeta.

### Requisitos Mínimos
- Windows 10 o Windows 11 (64-bits).
- Unidad Lectora de CD/DVD física o externa (USB).

> ⚠️ **Nota sobre la instalación (Windows SmartScreen):** Como este es un proyecto de software independiente, es posible que Windows te muestre una pantalla de advertencia azul indicando "Editor desconocido" al intentar instalarlo. Esto es normal y el instalador es completamente seguro. Para continuar, simplemente haz clic en **"Más información"** y luego presiona **"Ejecutar de todas formas"**.

---

## 🛠️ Tecnologías Utilizadas

- **Python 3.10**: Motor principal de backend y lectura de hardware.
- **PyWebView**: Contenedor ligero de frontend (HTML/CSS/JS nativo).
- **FFmpeg**: Sistema de codificación universal de formatos de audio e inyección de metadatos (etiquetas ID3/Vorbis).
- **PyInstaller & Inno Setup**: Empaquetado y distribución.

---

## 📜 Licencia

Copyright © 2026 AO Labs Chile. Todos los derechos reservados.
