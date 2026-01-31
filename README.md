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
- **⏩ Playback Speed Control** - Adjust speed from 0.5x to 2.0x
- **⏪ Smart Auto-Rewind** - Automatically rewinds based on pause duration
- **🌐 Multi-language Interface** - English and Russian localization
- **🎨 Dark Theme** - Modern dark interface with customizable styles
- **📁 Folder Navigation** - Quick access to course folders from context menu

### 📋 Requirements

- **Operating System**: Windows 10/11
- **Python**: 3.10+

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

### 🚀 Installation

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

### 📖 Usage

1. **Add Library Paths**: Go to `Library → Settings` and add folders containing your video courses
2. **Scan Library**: Click `Library → Scan` to index your videos
3. **Watch Videos**: Double-click any video to start playback
4. **Resume Playback**: Your progress is automatically saved - just double-click to resume

### ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Space` | Play/Pause |
| `←` / `→` | Seek backward/forward 10 seconds |
| `Shift + ←` / `→` | Seek backward/forward 60 seconds |
| `.` / `,` | Frame step forward/backward |
| `↑` / `↓` | Volume up/down |
| `M` | Mute/Unmute |
| `F` | Toggle fullscreen |
| `Ctrl + R` | Rescan library |
| `Ctrl + ,` | Open settings |
| `F5` | Reload styles |

### 🏗️ Project Structure

```
SPVideoCoursesPlayer/
├── main.py              # Application entry point
├── player.py            # Video player widget
├── library.py           # Library tree widget
├── database.py          # SQLite database management
├── scanner.py           # Video scanner and indexer
├── mpv_handler.py       # MPV integration
├── settings_dialog.py   # Settings UI
├── about_dialog.py      # About dialog
├── subtitle_popup.py    # Subtitle settings popup
├── volume_popup.py      # Volume control popup
├── translator.py        # Localization system
├── styles.py            # UI styling
└── resources/
    ├── icons/           # Application icons
    ├── translations/    # Language files (en.json, ru.json)
    ├── styles/          # QSS stylesheets
    └── bin/             # External binaries
```

### 🤝 Contributing

Contributions are welcome! Please feel free to submit pull requests.

### 📄 License

This project is open source. See the LICENSE file for details.

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
- **⏩ Управление скоростью** — регулировка от 0.5x до 2.0x
- **⏪ Умная перемотка** — автоматическая перемотка в зависимости от длительности паузы
- **🌐 Многоязычный интерфейс** — русский и английский языки
- **🎨 Тёмная тема** — современный тёмный интерфейс с настраиваемыми стилями
- **📁 Навигация по папкам** — быстрый доступ к папкам курсов через контекстное меню

### 📋 Требования

- **Операционная система**: Windows 10/11
- **Python**: 3.10+

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

### 🚀 Установка

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

### 📖 Использование

1. **Добавьте пути к библиотеке**: Перейдите в `Библиотека → Настройки` и добавьте папки с видеокурсами
2. **Сканирование библиотеки**: Нажмите `Библиотека → Сканировать` для индексации видео
3. **Просмотр видео**: Дважды щёлкните по видео для начала воспроизведения
4. **Продолжение просмотра**: Ваш прогресс сохраняется автоматически — просто дважды щёлкните для продолжения

### ⌨️ Горячие клавиши

| Сочетание | Действие |
|-----------|----------|
| `Пробел` | Воспроизведение/Пауза |
| `←` / `→` | Перемотка на 10 секунд |
| `Shift + ←` / `→` | Перемотка на 60 секунд |
| `.` / `,` | Покадровый шаг вперёд/назад |
| `↑` / `↓` | Громкость выше/ниже |
| `M` | Без звука / Вернуть звук |
| `F` | Полноэкранный режим |
| `Ctrl + R` | Пересканировать библиотеку |
| `Ctrl + ,` | Открыть настройки |
| `F5` | Перезагрузить стили |

### 🏗️ Структура проекта

```
SPVideoCoursesPlayer/
├── main.py              # Точка входа приложения
├── player.py            # Виджет видеоплеера
├── library.py           # Виджет дерева библиотеки
├── database.py          # Управление базой SQLite
├── scanner.py           # Сканер и индексатор видео
├── mpv_handler.py       # Интеграция MPV
├── settings_dialog.py   # Интерфейс настроек
├── about_dialog.py      # Диалог «О программе»
├── subtitle_popup.py    # Настройки субтитров
├── volume_popup.py      # Управление громкостью
├── translator.py        # Система локализации
├── styles.py            # Стилизация интерфейса
└── resources/
    ├── icons/           # Иконки приложения
    ├── translations/    # Языковые файлы (en.json, ru.json)
    ├── styles/          # QSS таблицы стилей
    └── bin/             # Внешние исполняемые файлы
```

### 🤝 Участие в разработке

Ваши вклады приветствуются! Не стесняйтесь отправлять pull requests.

### 📄 Лицензия

Этот проект с открытым исходным кодом. Подробности см. в файле LICENSE.

---

<p align="center">
  Made with ❤️ for video course enthusiasts
</p>
