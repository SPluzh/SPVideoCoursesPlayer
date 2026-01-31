# SPVideoCoursesPlayer

Видеоплеер для просмотра курсов с поддержкой зума, панорамирования и ускоренной обработкой видео.

## Требования

- Python 3.10+
- Библиотеки из `requirements.txt`
- `libmpv` (включена в проект: `libmpv-2.dll`)
- `ffmpeg` и `ffprobe` (должны быть в папке `bin/`)

## Установка и настройка для разработки

1. **Клонируйте репозиторий** (если еще не сделали):
   ```bash
   git clone <repository_url>
   cd sp_video_courses_player
   ```

2. **Создайте виртуальное окружение (рекомендуется):**
   ```bash
   python -m venv venv
   # Активация для Windows:
   .\venv\Scripts\activate
   # Активация для Linux/Mac:
   source venv/bin/activate
   ```

3. **Установите зависимости:**
   ```bash
   pip install -r requirements.txt
   ```

## Запуск приложения

Для запуска плеера выполните:
```bash
python main_with_mpv_zoom_pan_audio.py
```

## Сборка приложения

Проект настроен для сборки через PyInstaller.

1. Убедитесь, что установлены зависимости для разработки:
   ```bash
   pip install pyinstaller
   ```

2. Запустите сборку:
   ```bash
   pyinstaller SPVideoCoursesPlayer.spec
   ```

3. Готовый exe файл будет находиться в папке `dist/SPVideoCoursesPlayer`.

### Альтернативный способ сборки (Windows)

Для автоматической сборки вы можете просто запустить файл `__build.bat` из корневой папки проекта. Он проверит наличие зависимостей и выполнит сборку.
