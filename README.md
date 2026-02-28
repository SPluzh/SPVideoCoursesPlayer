# SP Video Courses Player

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PyQt6](https://img.shields.io/badge/PyQt6-6.6.0+-green.svg)](https://pypi.org/project/PyQt6/)
[![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)](https://www.microsoft.com/windows)
[![Latest Release](https://img.shields.io/github/v/release/SPluzh/SPVideoCoursesPlayer)](https://github.com/SPluzh/SPVideoCoursesPlayer/releases)
[![Downloads](https://img.shields.io/github/downloads/SPluzh/SPVideoCoursesPlayer/total)](https://github.com/SPluzh/SPVideoCoursesPlayer/releases)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

<p align="center">
  <img src="resources/icons/app_icon.png" alt="SP Video Courses Player" width="128" height="128">
</p>

<p align="center">
  <strong>A specialized video player for watching downloaded video courses with progress tracking</strong>
</p>

<p align="center">
  <a href="#english">English</a> •
  <a href="#russian">Русский</a>
</p>

---

<a name="english"></a>

## 🇬🇧 English

### Overview

SP Video Courses Player is a desktop application designed specifically for watching and managing downloaded video courses. It provides a seamless experience for organizing your video library, tracking your progress, and picking up where you left off.

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
3. **Watch Videos**: Double-click any video to start playback
4. **Audio Tools**: Click the volume icon to access **AI Noise Reduction** and effects
5. **Tools**: Use `P` for PiP mode, `G` for Markers, and Context Menu for Tags


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

3. Run the application:
   ```bash
   python main.py
   ```

</details>


### 📋 Requirements

- **Operating System**: Windows 10/11
- **Python**: 3.10+ (for source installation)

### 📦 Dependencies

```
PyQt6
python-mpv
comtypes
mutagen
pyinstaller (for building)
```

### 🔧 Additional Components

The application will automatically download these components on first run:
- **libmpv-2.dll** - MPV video playback library
- **FFmpeg & FFprobe** - For video analysis and thumbnail generation

---

<a name="russian"></a>

## 🇷🇺 Русский

### Обзор

SP Video Courses Player — это настольное приложение, специально разработанное для просмотра и управления скачанными видеокурсами. Оно обеспечивает удобную организацию видеотеки, отслеживание прогресса и возможность продолжить просмотр с того места, где вы остановились.

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
3. **Аудио инструменты**: Клик по значку громкости открывает **AI Шумоподавление** и эффекты
4. **Инструменты**: `P` — PiP режим, `G` — Маркеры, ПКМ — Теги и Избранное

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

3. Запустите приложение:
   ```bash
   python main.py
   ```

</details>

### 📋 Требования

- **Операционная система**: Windows 10/11
- **Python**: 3.10+ (для запуска из исходников)

### 📦 Зависимости

```
PyQt6
python-mpv
comtypes
mutagen
pyinstaller (для сборки)
```

### 🔧 Дополнительные компоненты

Приложение автоматически загрузит эти компоненты при первом запуске:
- **libmpv-2.dll** — библиотека воспроизведения видео MPV
- **FFmpeg и FFprobe** — для анализа видео и генерации миниатюр


---

<p align="center">
  Made with ❤️ for video course enthusiasts
</p>
