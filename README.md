# SP Video Courses Player

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

- **📚 Video Library Management** - Organize video courses in a hierarchical tree structure
- **▶️ Built-in Video Player** - Powered by libmpv for smooth playback
- **📊 Progress Tracking** - Automatically saves and restores playback position
- **🖼️ Thumbnail Generation** - Creates preview thumbnails for easy navigation
- **🔊 Multi-track Audio Support** - Switch between embedded and external audio tracks
- **📝 Subtitle Support** - Load and display subtitles with customizable appearance
- **⏩ Playback Speed Control** - Adjust speed from 0.5x to 3.0x
- **🌐 Multi-language Interface** - English and Russian localization
- **🎨 Dark Theme** - Modern dark interface with customizable styles
- **📁 Folder Navigation** - Quick access to course folders from context menu

### 📖 Usage

1. **Add Library Paths**: Go to `Library → Settings` and add folders containing your video courses
2. **Scan Library**: Click `Library → Scan` to index your videos
3. **Watch Videos**: Double-click any video to start playback
4. **Resume Playback**: Your progress is automatically saved - just double-click to resume


### 🚀 Installation

#### Option 1: Download Executable (Recommended)
1. Download the latest release from the [Releases](../../releases) page
2. Extract the archive to your desired location
3. Run `SP Video Courses Player.exe`

#### Option 2: Run from Source
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

- **📚 Управление видеотекой** — организация видеокурсов в древовидной структуре
- **▶️ Встроенный видеоплеер** — на базе libmpv для плавного воспроизведения
- **📊 Отслеживание прогресса** — автоматическое сохранение и восстановление позиции воспроизведения
- **🖼️ Генерация миниатюр** — создание превью для удобной навигации
- **🔊 Поддержка нескольких аудиодорожек** — переключение между встроенными и внешними аудио
- **📝 Поддержка субтитров** — загрузка и отображение субтитров с настраиваемым внешним видом
- **⏩ Управление скоростью** — регулировка от 0.5x до 3.0x
- **🌐 Многоязычный интерфейс** — русский и английский языки
- **🎨 Тёмная тема** — современный тёмный интерфейс с настраиваемыми стилями
- **📁 Навигация по папкам** — быстрый доступ к папкам курсов через контекстное меню

### 📖 Использование

1. **Добавьте пути к библиотеке**: Перейдите в `Библиотека → Настройки` и добавьте папки с видеокурсами
2. **Сканирование библиотеки**: Нажмите `Библиотека → Сканировать` для индексации видео
3. **Просмотр видео**: Дважды щёлкните по видео для начала воспроизведения
4. **Продолжение просмотра**: Ваш прогресс сохраняется автоматически — просто дважды щёлкните для продолжения

### 🚀 Установка

#### Вариант 1: Скачать исполняемый файл (рекомендуется)
1. Скачайте последний релиз со страницы [Releases](../../releases)
2. Распакуйте архив в нужное место
3. Запустите `SP Video Courses Player.exe`

#### Вариант 2: Запуск из исходников
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
