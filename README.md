# SP Video Courses Player

Desktop video player for local video courses built with Python, PyQt6 and libmpv (Windows). Features a hierarchical course library with progress tracking, favorites, tags, and fuzzy search. Includes Picture-in-Picture mode, interactive subtitle translation with word-click lookup and offline cache, dual subtitle tracks, AI noise reduction, compressor, video zoom, visual bookmarks (markers), course completion statistics, FFmpeg-powered timeline thumbnail previews, and Windows taskbar integration.

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PyQt6](https://img.shields.io/badge/PyQt6-6.6.0+-green.svg)](https://pypi.org/project/PyQt6/)
[![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)](https://www.microsoft.com/windows)
[![Latest Release](https://img.shields.io/github/v/release/SPluzh/SPVideoCoursesPlayer)](https://github.com/SPluzh/SPVideoCoursesPlayer/releases)
[![Latest Release Downloads](https://img.shields.io/github/downloads/SPluzh/SPVideoCoursesPlayer/latest/total)](https://github.com/SPluzh/SPVideoCoursesPlayer/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/SPluzh/SPVideoCoursesPlayer/total)](https://github.com/SPluzh/SPVideoCoursesPlayer/releases)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)

![](attachments/SP_Video_Courses_Player.gif)
![](attachments/SP_Video_Courses_Player_translate_popup.gif)
<p align="center">
  <a href="#english">English</a> •
  <a href="#russian">Русский</a>
</p>

---

<a name="english"></a>

## English

### Overview

**SP Video Courses Player** is a desktop application built for people who learn from downloaded video courses. Instead of hunting through folders in a file manager, you get a clean hierarchical library where every course remembers exactly where you left off, how much you've watched, and what's still ahead.

Play your videos with Picture-in-Picture mode so you can take notes while watching, and instant thumbnail previews as you hover over the timeline. Click on any word in the subtitles to get an instant translation, synonyms, and pronunciation audio right inside the player, with repeated lookups loading instantly. Professional audio tools (AI noise reduction, compressor, de-esser) help when lecture recordings aren't studio-quality. Visual bookmarks with screenshots let you mark and revisit key moments without scrubbing through the whole video.

### Features

- **Course Library** — Hierarchical tree with colored nesting lines, natural sort, Favorites, Tags (multi-tag OR filter), and fuzzy search with EN/RU transliteration
- **Progress Tracking** — Resumes from where you stopped, color-coded watched/in-progress/unwatched states, auto-advance to next video, bulk "Mark as Watched / Reset Progress"
- **Detailed Statistics** — Per-folder completion percentage, total/watched/remaining duration, course stats dialog
- **Advanced Playback** — Picture-in-Picture (PiP), fullscreen, zoom & pan, video rotation (90° steps), frame step, screenshot to clipboard
- **Timeline Preview** — Hover over the seekbar to instantly see a video thumbnail; jump to any percentage of the video with number keys
- **Professional Audio** — AI Noise Reduction, Compressor, De-esser, Mono mix, Sync Delay; dual audio track with independent volume
- **Subtitle & Translation** — Primary + secondary subtitle tracks displayed simultaneously, independent color/size settings, "show secondary on hover" option
- **Interactive Translation** — Click any subtitle word for instant translation, synonyms, and pronunciation audio; offline cache for instant repeat lookups; full-phrase translation via button or `Alt + ↑`
- **Subtitle Navigation** — Jump between subtitle phrases, replay the current one, or translate it — all with dedicated hotkeys
- **Speed Control** — Playback speed 0.5×–3.0× with pitch correction
- **Smart Markers** — Visual gallery with screenshots, 12 custom colors, timeline dots, edit/delete from gallery or seekbar right-click
- **Tags & Bulk Operations** — Create color-coded tags, assign to multiple items at once, filter library by any combination of tags
- **Keyboard Shortcuts** — All hotkeys work in both English and Russian keyboard layouts; media keys (Play/Pause, Next/Prev) work even when the app is in the background
- **Windows Integration** — Taskbar progress bar, thumbnail toolbar buttons (Prev, -10s, Play/Pause, +10s, Next), Always on Top toggle
- **PureRef Integration** — Badge button on each folder to open a linked `.pur` reference file; color-coded status dot (missing/exists/running)
- **Auto-Update** — Checks GitHub Releases on startup and updates with one click; FFmpeg and libmpv auto-download on first run
- **Modern UI** — Dark theme with full QSS styling, OSD notifications, High DPI / fractional scaling support, collapsible library panel (`Ctrl+L`)

### Usage

1. **Add Library Paths**: Go to `Library → Settings` and add folders containing your video courses
2. **Scan Library**: Click `Library → Scan` to index your videos

### Installation

#### Option 1: Standard Installation (Setup)
1. Download the latest installer (`SP_Video_Courses_Player_Setup_vX.Y.Z.exe`) from the [Releases](../../releases) page
2. Run the executable to install the player on your system

#### Option 2: Portable Version
1. Download the latest portable archive (`SP_Video_Courses_Player_vX.Y.Z.zip`) from the [Releases](../../releases) page
2. Extract the archive to your desired location
3. Run `SP Video Courses Player.exe`

<details>
<summary><strong>Option 3: Run from Source</strong></summary>

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/SPVideoCoursesPlayer.git
   cd SPVideoCoursesPlayer
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

   **Dependencies:**
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

### Manual Update (for Portable Version)

1. **Close** SP Video Courses Player completely
2. Download the latest portable `.zip` archive from the [Releases](https://github.com/SPluzh/SPVideoCoursesPlayer/releases/latest) page
3. Extract the archive into the application folder **with file replacement**

> **Note:** Your personal data is preserved during the update — `settings.ini` contains your application settings, and the `data/` folder stores the database, viewing progress, bookmarks, and cache. These files are not included in the release archive and will not be overwritten.

### Additional Components

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

### PureRef Integration (Optional)

To use the PureRef integration feature for managing reference images alongside your video courses:

1. **Download and Install PureRef** from [https://www.pureref.com/download.php](https://www.pureref.com/download.php)
2. **Default Path**: If installed to the default location (`C:\Program Files\PureRef\PureRef.exe`), the application will detect it automatically
3. **Custom Path**: If installed elsewhere, go to `Library → Settings → PureRef` section and browse to your `PureRef.exe` location
4. **Filename**: You can customize the reference filename (default: `reference.pur`) in the same settings section

Once configured, you'll see PureRef badges on folder items in your library, allowing quick access to reference files.

---

### Credits

- [PyQt6](https://pypi.org/project/PyQt6/) - GUI framework
- [libmpv](https://mpv.io/) - Video playback engine
- [FFmpeg](https://ffmpeg.org/) - Video processing & thumbnails
- [RNNoise](https://jmvalin.ca/demo/rnnoise/) (Xiph.Org) - AI noise reduction model
- [Lucide](https://lucide.dev/) - Icon toolkit

---

<a name="russian"></a>

## Русский

### Обзор

**SP Video Courses Player** — это десктопное приложение, созданное специально для тех, кто учится по скачанным видеокурсам. Вместо того чтобы искать папки в проводнике, вы получаете удобную древовидную библиотеку, где для каждого курса запоминается прогресс: где вы остановились, сколько уже посмотрели и сколько еще осталось.

Смотрите видео в режиме «Картинка-в-картинке» (PiP), чтобы делать заметки во время просмотра, и пользуйтесь мгновенным предпросмотром кадров при наведении на шкалу времени. Кликайте на любое слово в субтитрах для мгновенного перевода, просмотра синонимов и прослушивания произношения прямо в плеере, причем ранее переведенные слова будут открываться моментально. Профессиональные инструменты для работы со звуком (активное шумоподавление, компрессор, де-эссер) помогут, если лекция записана с фоновым шумом. Визуальные закладки со скриншотами позволяют отмечать и быстро находить ключевые моменты в один клик.

### Возможности

- **Библиотека курсов** — древовидная структура с цветными линиями вложенности, естественной сортировкой, Избранным, тегами (фильтрация по нескольким тегам) и нечетким поиском с автоматической транслитерацией EN/RU.
- **Отслеживание прогресса** — сохранение позиции воспроизведения, цветовая индикация статуса просмотра (просмотрено/в процессе/новое), автоматический переход к следующему видео, массовая отметка просмотренного или сброс прогресса.
- **Детальная статистика** — процент завершения для каждой папки, общее, просмотренное и оставшееся время, а также отдельное окно статистики курса.
- **Продвинутое воспроизведение** — режим «Картинка-в-картинке» (PiP), полноэкранный режим, масштабирование и панорамирование видео, поворот кадра на 90 градусов, покадровый шаг и копирование скриншота в буфер обмена.
- **Предпросмотр на шкале времени** — мгновенное отображение кадра при наведении курсора на таймлайн; быстрый переход к нужному проценту видео с помощью цифровых клавиш.
- **Профессиональный звук** — интеллектуальное шумоподавление, компрессор, де-эссер, моно-микс и настройка задержки синхронизации; поддержка второй аудиодорожки с независимой регулировкой громкости.
- **Субтитры и перевод** — одновременное отображение двух дорожек субтитров с независимой настройкой цвета и размера, опция показа вторых субтитров только при наведении мыши.
- **Интерактивный перевод** — перевод любого слова в субтитрах по клику с показом синонимов и озвучкой; кеширование для мгновенного повторного перевода; перевод всей фразы кнопкой или горячими клавишами.
- **Навигация по субтитрам** — быстрый переход между фразами, повтор текущей фразы или перевод — все с помощью удобных горячих клавиш.
- **Управление скоростью** — изменение скорости воспроизведения от 0.5x до 3.0x с сохранением естественного тона голоса.
- **Умные закладки** — визуальная галерея со скриншотами, 12 цветов для меток, точки закладок на шкале времени, редактирование и удаление прямо из галереи или по клику правой кнопкой мыши на таймлайне.
- **Теги и массовые операции** — создание цветных тегов, присвоение их нескольким элементам сразу, фильтрация библиотеки по любым комбинациям тегов.
- **Горячие клавиши** — управление работает как на английской, так и на русской раскладке клавиатуры; поддержка глобальных медиа-клавиш (Play/Pause, Next/Prev) даже когда окно приложения свернуто.
- **Интеграция с Windows** — отображение прогресса на панели задач, управление воспроизведением кнопками на эскизе панели задач (назад, -10 сек, воспроизведение/пауза, +10 сек, вперед), закрепление окна поверх других окон.
- **Интеграция с PureRef** — кнопка-значок на папках для быстрого открытия связанного файла референсов `.pur` с цветовой индикацией статуса файла (отсутствует, существует, запущен).
- **Автоматическое обновление** — проверка новых версий на GitHub при запуске и обновление в один клик; автоматическая загрузка FFmpeg и библиотек плеера при первом запуске.
- **Современный интерфейс** — темная тема с полной QSS-стилизацией, всплывающие уведомления на экране (OSD), поддержка High DPI и дробного масштабирования, быстрое скрытие боковой панели библиотеки.

### Использование

1. **Добавьте пути**: `Библиотека → Настройки` — укажите папки с курсами
2. **Сканирование**: `Библиотека → Сканировать` — индексация файлов

### Установка

#### Вариант 1: Стандартная установка (Setup)
1. Скачайте последний установщик (`SP_Video_Courses_Player_Setup_vX.Y.Z.exe`) со страницы [Releases](../../releases)
2. Запустите файл установки для инсталляции плеера в систему

#### Вариант 2: Портативная версия (Portable)
1. Скачайте последний архив портативной версии (`SP_Video_Courses_Player_vX.Y.Z.zip`) со страницы [Releases](../../releases)
2. Распакуйте архив в удобное место
3. Запустите `SP Video Courses Player.exe`

<details>
<summary><strong>Вариант 3: Запуск из исходников</strong></summary>

1. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/yourusername/SPVideoCoursesPlayer.git
   cd SPVideoCoursesPlayer
   ```

2. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```

   **Зависимости:**
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

### Ручное обновление (для портативной версии)

1. **Закройте** SP Video Courses Player полностью
2. Скачайте последний портативный `.zip` архив со страницы [Releases](https://github.com/SPluzh/SPVideoCoursesPlayer/releases/latest)
3. Распакуйте архив в папку приложения **с заменой файлов**

> **Примечание:** Ваши личные данные сохранятся при обновлении — `settings.ini` содержит настройки приложения, а папка `data/` хранит базу данных, прогресс просмотра, закладки и кеш. Эти файлы не входят в архив релиза и не будут перезаписаны.

### Дополнительные компоненты

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

### Интеграция с PureRef (опционально)

Для использования интеграции с PureRef для управления референсами рядом с видеокурсами:

1. **Скачайте и установите PureRef** с [https://www.pureref.com/download.php](https://www.pureref.com/download.php)
2. **Путь по умолчанию**: Если установлен в стандартное расположение (`C:\Program Files\PureRef\PureRef.exe`), приложение обнаружит его автоматически
3. **Другой путь**: Если установлен в другое место, перейдите в `Библиотека → Настройки → PureRef` и укажите путь к `PureRef.exe`
4. **Имя файла**: Вы можете настроить имя файла референсов (по умолчанию: `reference.pur`) в той же секции настроек

После настройки вы увидите значки PureRef на папках в библиотеке, позволяющие быстро открывать файлы референсов.

---

### Благодарности

- [PyQt6](https://pypi.org/project/PyQt6/) - Фреймворк для графического интерфейса
- [libmpv](https://mpv.io/) - Движок воспроизведения видео
- [FFmpeg](https://ffmpeg.org/) - Обработка видео и создание миниатюр
- [RNNoise](https://jmvalin.ca/demo/rnnoise/) (Xiph.Org) - AI модель шумоподавления
- [Lucide](https://lucide.dev/) - Набор иконок

---

<p align="center">
  Created for video course enthusiasts
</p>
