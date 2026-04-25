# SP Video Courses Player

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PyQt6](https://img.shields.io/badge/PyQt6-6.6.0+-green.svg)](https://pypi.org/project/PyQt6/)
[![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)](https://www.microsoft.com/windows)
[![Latest Release](https://img.shields.io/github/v/release/SPluzh/SPVideoCoursesPlayer)](https://github.com/SPluzh/SPVideoCoursesPlayer/releases)
[![Downloads](https://img.shields.io/github/downloads/SPluzh/SPVideoCoursesPlayer/total)](https://github.com/SPluzh/SPVideoCoursesPlayer/releases)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)

![](attachments/SP_Video_Courses_Player.gif)


<p align="center">
  <strong>Video player for local courses with hierarchical library, progress tracking, bookmarks, tags, and learning statistics. Includes video zoom, audio enhancement, custom subtitle settings, and instant thumbnail previews on the timeline</strong>
</p>

<p align="center">
  <a href="#english">English</a> •
  <a href="#russian">Русский</a>
</p>

---

<a name="english"></a>

## 🇬🇧 English

### Overview

SP Video Courses Player is a desktop application for watching and managing local video courses with hierarchical library organization, progress tracking, and learning statistics. Includes video zoom, audio enhancement, custom subtitle settings, and instant thumbnail previews on the timeline.

### ✨ Features

- **📚 Library Management** - Hierarchical tree structure with **Favorites** and **Tags** filtering
- **▶️ Advanced Player** - Built on **libmpv** with **Picture-in-Picture (PiP)** mode
- **🔊 Professional Audio Tools** - **AI Noise Reduction**, Compressor, De-esser, Mono mix, and precise Sync Delay
- **📊 Detailed Statistics** - Folder completion progress, watched duration, and remaining time
- **🔖 Smart Markers** - Visual marker gallery, custom colors, and timeline previews
- **🖼️ Instant Previews** - Hover over the timeline to see instantaneous video thumbnails
- **📝 Subtitle Support** - Customizable subtitles with size, color, and outline settings
- **⏩ Speed Control** - Adjust playback speed (0.5x - 3.0x) with pitch correction
- **🎨 Modern UI** - Dark theme with custom icons and responsive layout

### 📖 Usage

1. **Add Library Paths**: Go to `Library → Settings` and add folders containing your video courses
2. **Scan Library**: Click `Library → Scan` to index your videos

### 🚀 Installation

#### Option 1: Download Executable (Recommended)
1. Download the latest release from the [Releases](../../releases) page
2. Extract the archive to your desired location
3. Run `SP Video Courses Player.exe`

<details>
<summary><strong>Option 2: Run from Source</strong></summary>

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/SPVideoCoursesPlayer.git
   cd SPVideoCoursesPlayer
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

   **📦 Dependencies:**
   ```
   PyQt6
   python-mpv
   comtypes
   mutagen
   pyinstaller (for building)
   ```

3. Run the application:
   ```bash
   python main.py
   ```

</details>

### 🔄 Manual Update

1. **Close** SP Video Courses Player completely
2. Download the latest `.zip` archive from the [Releases](https://github.com/SPluzh/SPVideoCoursesPlayer/releases/latest) page
3. Extract the archive into the application folder **with file replacement**

> **Note:** Your personal data is preserved during the update — `settings.ini` contains your application settings, and the `data/` folder stores the database, viewing progress, bookmarks, and cache. These files are not included in the release archive and will not be overwritten.


### 📋 Requirements

- **Operating System**: Windows 10/11
- **Python**: 3.10+ (for source installation)


### 🔧 Additional Components

The application will automatically download these components on first run. If the automatic download fails, you can download them manually and place them in the `resources/bin/` directory:

- **libmpv-2.dll** ([Download from shinchiro](https://github.com/shinchiro/mpv-winbuild-cmake/releases) or [zhongfly](https://github.com/zhongfly/mpv-winbuild/releases)) - MPV video playback library. Look for `mpv-dev-x86_64-*.7z` and extract the DLL.
- **FFmpeg & FFprobe** ([Download Essentials](https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip)) - For video analysis and thumbnail generation. Extract `ffmpeg.exe` and `ffprobe.exe` from the `bin` folder of the archive.

**Placement:** Place all components into the `bin` directory. The path depends on how you run the application:

The folder structure should look like this (for EXE version):
```text
SP Video Courses Player/
├── SP Video Courses Player.exe
└── _internal/
    └── resources/
        └── bin/
            ├── libmpv-2.dll
            ├── ffmpeg.exe
            └── ffprobe.exe
```

### 🖼️ PureRef Integration (Optional)

To use the PureRef integration feature for managing reference images alongside your video courses:

1. **Download and Install PureRef** from [https://www.pureref.com/download.php](https://www.pureref.com/download.php)
2. **Default Path**: If installed to the default location (`C:\Program Files\PureRef\PureRef.exe`), the application will detect it automatically
3. **Custom Path**: If installed elsewhere, go to `Library → Settings → PureRef` section and browse to your `PureRef.exe` location
4. **Filename**: You can customize the reference filename (default: `reference.pur`) in the same settings section

Once configured, you'll see PureRef badges on folder items in your library, allowing quick access to reference files.

---

### 📜 Credits

- [PyQt6](https://pypi.org/project/PyQt6/) - GUI framework
- [libmpv](https://mpv.io/) - Video playback engine
- [FFmpeg](https://ffmpeg.org/) - Video processing & thumbnails
- [RNNoise](https://jmvalin.ca/demo/rnnoise/) (Xiph.Org) - AI noise reduction model
- [Lucide](https://lucide.dev/) - Icon toolkit

---

<a name="russian"></a>

## 🇷🇺 Русский

### Обзор

SP Video Courses Player — плеер для локальных видеокурсов с древовидной библиотекой, сохранением прогресса, закладками, тегами и статистикой обучения. Включает масштабирование кадра, улучшение звука, настройку субтитров и мгновенные превью на таймлайне.

### ✨ Возможности

- **📚 Управление библиотекой** — Древовидная структура с фильтрацией по **Избранному** и **Тегам**
- **▶️ Продвинутый плеер** — На базе **libmpv** с режимом **Картинка-в-картинке (PiP)**
- **🔊 Профессиональный звук** — **AI Шумоподавление**, Компрессор, Де-эссер, Моно-микс и точная настройка задержки
- **📊 Детальная статистика** — Прогресс по папкам, просмотренное время и остаток
- **🔖 Умные закладки** — Визуальная галерея маркеров, цветные метки и превью на таймлайне
- **🖼️ Мгновенное превью** — Наведение на таймлайн показывает кадр из видео
- **📝 Поддержка субтитров** — Настройка размера, цвета и обводки текста
- **⏩ Управление скоростью** — Регулировка (0.5x - 3.0x) без искажения тона
- **🎨 Современный UI** — Тёмная тема, адаптивный интерфейс и кастомные иконки

### 📖 Использование

1. **Добавьте пути**: `Библиотека → Настройки` — укажите папки с курсами
2. **Сканирование**: `Библиотека → Сканировать` — индексация файлов

### 🚀 Установка

#### Вариант 1: Скачать исполняемый файл (рекомендуется)
1. Скачайте последний релиз со страницы [Releases](../../releases)
2. Распакуйте архив в нужное место
3. Запустите `SP Video Courses Player.exe`

<details>
<summary><strong>Вариант 2: Запуск из исходников</strong></summary>

1. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/yourusername/SPVideoCoursesPlayer.git
   cd SPVideoCoursesPlayer
   ```

2. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```

   **📦 Зависимости:**
   ```
   PyQt6
   python-mpv
   comtypes
   mutagen
   pyinstaller (for building)
   ```

3. Запустите приложение:
   ```bash
   python main.py
   ```

</details>

### 🔄 Ручное обновление

1. **Закройте** SP Video Courses Player полностью
2. Скачайте последний `.zip` архив со страницы [Releases](https://github.com/SPluzh/SPVideoCoursesPlayer/releases/latest)
3. Распакуйте архив в папку приложения **с заменой файлов**

> **Примечание:** Ваши личные данные сохранятся при обновлении — `settings.ini` содержит настройки приложения, а папка `data/` хранит базу данных, прогресс просмотра, закладки и кеш. Эти файлы не входят в архив релиза и не будут перезаписаны.

### 📋 Требования

- **Операционная система**: Windows 10/11
- **Python**: 3.10+ (для запуска из исходников)


### 🔧 Дополнительные компоненты

Приложение автоматически загрузит эти компоненты при первом запуске. Если автоматическая загрузка не удалась, вы можете скачать их вручную и поместить в директорию `resources/bin/`:

- **libmpv-2.dll** ([Скачать от shinchiro](https://github.com/shinchiro/mpv-winbuild-cmake/releases) или [от zhongfly](https://github.com/zhongfly/mpv-winbuild/releases)) — библиотека воспроизведения видео MPV. Ищите `mpv-dev-x86_64-*.7z` и извлеките DLL.
- **FFmpeg и FFprobe** ([Скачать Essentials](https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip)) — для анализа видео и генерации миниатюр. Извлеките `ffmpeg.exe` и `ffprobe.exe` из папки `bin` архива.

**Путь:** Поместите все компоненты в папку `bin`. Путь зависит от способа запуска приложения:

Структура папок должна выглядеть так (для EXE версии):
```text
SP Video Courses Player/
├── SP Video Courses Player.exe
└── _internal/
    └── resources/
        └── bin/
            ├── libmpv-2.dll
            ├── ffmpeg.exe
            └── ffprobe.exe
```


### 🖼️ Интеграция с PureRef (опционально)

Для использования интеграции с PureRef для управления референсами рядом с видеокурсами:

1. **Скачайте и установите PureRef** с [https://www.pureref.com/download.php](https://www.pureref.com/download.php)
2. **Путь по умолчанию**: Если установлен в стандартное расположение (`C:\Program Files\PureRef\PureRef.exe`), приложение обнаружит его автоматически
3. **Другой путь**: Если установлен в другое место, перейдите в `Библиотека → Настройки → PureRef` и укажите путь к `PureRef.exe`
4. **Имя файла**: Вы можете настроить имя файла референсов (по умолчанию: `reference.pur`) в той же секции настроек

После настройки вы увидите значки PureRef на папках в библиотеке, позволяющие быстро открывать файлы референсов.

---

### 📜 Благодарности

- [PyQt6](https://pypi.org/project/PyQt6/) - Фреймворк для графического интерфейса
- [libmpv](https://mpv.io/) - Движок воспроизведения видео
- [FFmpeg](https://ffmpeg.org/) - Обработка видео и создание миниатюр
- [RNNoise](https://jmvalin.ca/demo/rnnoise/) (Xiph.Org) - AI модель шумоподавления
- [Lucide](https://lucide.dev/) - Набор иконок

---

<p align="center">
  Made with ❤️ for video course enthusiasts
</p>
