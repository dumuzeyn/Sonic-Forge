# MusicPolisher

MusicPolisher - проект для людей, которые любят скачивать свои любимые песни и хотят, чтобы папка с музыкой быстро становилась аккуратнее: звук нормализован, название песни записано в теги, жанр указан, лишние метаданные убраны, а у каждой песни есть своя интересная обложка.

Идея проекта: выбрать папку с скаченными песнями, выбрать папку для результата, при желании указать жанр всех песен в папке **(если ничего не писать жанр определиться автоматически)**, и получить обработанную коллекцию с минимальной систематизацией.

[English version](#engMP)

## Что делает проект

- Нормализует и усиливает звук.
- Конвертирует обработанные треки в MP3.
- Записывает название песни в тег `title`.
- Записывает жанр в тег `genre`.
- Если жанр не указан, пытается определить его автоматически.
- Очищает лишние метаданные и оставляет только название и жанр.
- Создает отдельную обложку для каждой песни.
- Встраивает созданную обложку в MP3-файл.

## Самый простой запуск

Главный простой файл:

```text
easy_music_process.py
```

Запуск из папки проекта:

```powershell
python .\easy_music_process.py
```

Программа спросит:

```text
Папка с песнями:
Папка, куда все сохранить:
Жанр для всех песен или Enter для автоопределения:
```

Если написать жанр, например:

```text
Rock
```

то этот жанр будет записан во все песни.

Если просто нажать Enter, программа сама попробует определить жанр для каждой песни.

## Быстрый запуск одной командой

```powershell
python .\easy_music_process.py --source "C:\Music\Input" --output "C:\Music\Output" --genre "Pop"
```

Автоопределение жанра:

```powershell
python .\easy_music_process.py --source "C:\Music\Input" --output "C:\Music\Output"
```

## Как работает простой файл

`easy_music_process.py` сам не выполняет всю работу. Он только запускает функции из трех основных файлов проекта:

```text
Normalize-Music.py  -> нормализация и усиление звука
music_metadata.py   -> очистка и запись title/genre
music2picture.py    -> создание и встраивание обложек
```

Порядок работы:

1. Обрабатывает звук и сохраняет новые MP3-файлы в выбранную папку.
2. Записывает название песни и жанр.
3. Создает PNG-обложки в папке `covers`.
4. Встраивает каждую обложку в соответствующую песню.

## Зависимости

Нужен Python и две библиотеки:

```powershell
pip install numpy pillow
```

Также нужен FFmpeg. Он должен быть доступен из PowerShell:

```powershell
ffmpeg -version
ffprobe -version
```

Официальная страница FFmpeg:

```text
https://ffmpeg.org/download.html
```

Для Windows можно использовать сборки:

```text
https://www.gyan.dev/ffmpeg/builds/
```

Обычно достаточно скачать `release essentials`, распаковать, например в:

```text
C:\ffmpeg
```

и добавить в `Path` папку:

```text
C:\ffmpeg\bin
```

### Правильная установка FFmpeg на Windows

1. Откройте страницу сборок FFmpeg:

```text
https://www.gyan.dev/ffmpeg/builds/
```

2. Скачайте архив `release essentials`.
3. Распакуйте архив в удобное место, например:

```text
C:\ffmpeg
```

4. Проверьте, что внутри есть папка `bin`, а в ней файлы:

```text
ffmpeg.exe
ffprobe.exe
```

Правильный путь обычно выглядит так:

```text
C:\ffmpeg\bin\ffmpeg.exe
C:\ffmpeg\bin\ffprobe.exe
```

5. Добавьте папку `C:\ffmpeg\bin` в системную переменную `Path`.

Как добавить в `Path`:

1. Нажмите `Win + R`.
2. Введите `sysdm.cpl` и нажмите Enter.
3. Откройте вкладку `Дополнительно`.
4. Нажмите `Переменные среды`.
5. В разделе `Системные переменные` найдите `Path`.
6. Нажмите `Изменить`.
7. Нажмите `Создать`.
8. Добавьте:

```text
C:\ffmpeg\bin
```

9. Нажмите `OK` во всех окнах.
10. Закройте старый PowerShell и откройте новый.
11. Проверьте установку:

```powershell
ffmpeg -version
ffprobe -version
```

Если обе команды показывают версию, FFmpeg установлен правильно.

## Поддерживаемые форматы

Входные файлы:

```text
.mp3
.flac
.wav
.m4a
.aac
.ogg
.opus
.wma
```

Результат сохраняется как MP3. Встраивание обложки поддерживается для MP3.

## Остальные файлы

Можно пользоваться отдельными частями проекта напрямую.

### Только нормализация

```powershell
python .\Normalize-Music.py --source "C:\Music\Input" --output "C:\Music\Output"
```

### Только метаданные

Один жанр для всех песен:

```powershell
python .\music_metadata.py --source "C:\Music\Output" --genre "Rock"
```

Автоопределение жанра:

```powershell
python .\music_metadata.py --source "C:\Music\Output"
```

### Только обложки

Создать обложки и встроить их в MP3:

```powershell
python .\music2picture.py covers --source "C:\Music\Output" --output "C:\Music\Output\covers" --center-title --embed-cover
```

## Как создаются обложки

Обложка строится из самой песни. Скрипт анализирует громкость, басы, средние и высокие частоты, пики и примерный BPM. На основе этих данных создается уникальный цветной узор.

Обложки не одинаковые даже при похожих песнях: в генерации есть случайность, но она направляется характеристиками аудио. Поэтому изображение выглядит живым и связано с треком.

## Примеры

В папке `example` есть тестовые песни и готовые обложки.

```text
example/Im so sorry.mp3
example/Into Yesterday.mp3
example/INVISIBLE.mp3
```

Папки с примерами:

```text
example/covers_no_title
example/covers_with_title
```


> **Автор проекта: Зейналов У.Р.о.**

---
<h1 id = engMP>
English Version
</h1>

MusicPolisher is a project for people who like downloading their favorite songs and want their music folder to become cleaner with minimal effort: normalized audio, proper song titles, genre tags, removed extra metadata, and a unique interesting cover for every track.

The idea of ​​the project: select a folder with downloaded songs, select a folder for the result, optionally specify the genre of all songs in the folder **(if you don’t specify anything, the genre will be determined automatically)**, and get a processed collection with minimal systematization.

## What It Does

- Normalizes and boosts audio.
- Converts processed tracks to MP3.
- Writes the song name to the `title` tag.
- Writes the genre to the `genre` tag.
- If no genre is entered, tries to detect it automatically.
- Removes extra metadata and keeps only title and genre.
- Creates a separate cover image for every song.
- Embeds the generated cover into the MP3 file.

## Easiest Usage

Main simple file:

```text
easy_music_process.py
```

Run from the project folder:

```powershell
python .\easy_music_process.py
```

The program asks for:

```text
Folder with songs
Folder where everything will be saved
Genre for all songs, or Enter for auto-detect
```

If you enter a genre, for example:

```text
Rock
```

that genre will be used for every song.

If you press Enter, the program will try to detect the genre for each song automatically.

## One-Command Usage

```powershell
python .\easy_music_process.py --source "C:\Music\Input" --output "C:\Music\Output" --genre "Pop"
```

Auto-detect genre:

```powershell
python .\easy_music_process.py --source "C:\Music\Input" --output "C:\Music\Output"
```

## How The Simple File Works

`easy_music_process.py` does not duplicate the main logic. It only calls functions from the three main project files:

```text
Normalize-Music.py  -> audio normalization and boost
music_metadata.py   -> title/genre cleanup and writing
music2picture.py    -> cover generation and embedding
```

Processing order:

1. Processes audio and saves new MP3 files to the selected output folder.
2. Writes song title and genre.
3. Creates PNG covers in the `covers` folder.
4. Embeds each cover into the matching song.

## Requirements

Python packages:

```powershell
pip install numpy pillow
```

FFmpeg is also required. It must be available from PowerShell:

```powershell
ffmpeg -version
ffprobe -version
```

Official FFmpeg page:

```text
https://ffmpeg.org/download.html
```

Windows builds:

```text
https://www.gyan.dev/ffmpeg/builds/
```

Usually you can download `release essentials`, extract it, for example to:

```text
C:\ffmpeg
```

and add this folder to `Path`:

```text
C:\ffmpeg\bin
```

### Correct FFmpeg Installation On Windows

1. Open the FFmpeg builds page:

```text
https://www.gyan.dev/ffmpeg/builds/
```

2. Download the `release essentials` archive.
3. Extract the archive to a simple folder, for example:

```text
C:\ffmpeg
```

4. Check that there is a `bin` folder inside it, and that it contains:

```text
ffmpeg.exe
ffprobe.exe
```

The correct paths usually look like this:

```text
C:\ffmpeg\bin\ffmpeg.exe
C:\ffmpeg\bin\ffprobe.exe
```

5. Add `C:\ffmpeg\bin` to the system `Path` variable.

How to add it to `Path`:

1. Press `Win + R`.
2. Type `sysdm.cpl` and press Enter.
3. Open the `Advanced` tab.
4. Click `Environment Variables`.
5. In `System variables`, find `Path`.
6. Click `Edit`.
7. Click `New`.
8. Add:

```text
C:\ffmpeg\bin
```

9. Click `OK` in all windows.
10. Close the old PowerShell window and open a new one.
11. Check the installation:

```powershell
ffmpeg -version
ffprobe -version
```

If both commands show a version, FFmpeg is installed correctly.

## Supported Formats

Input files:

```text
.mp3
.flac
.wav
.m4a
.aac
.ogg
.opus
.wma
```

The result is saved as MP3. Cover embedding is supported for MP3.

## Other Files

You can also use each part directly.

### Normalize Only

```powershell
python .\Normalize-Music.py --source "C:\Music\Input" --output "C:\Music\Output"
```

### Metadata Only

One genre for all songs:

```powershell
python .\music_metadata.py --source "C:\Music\Output" --genre "Rock"
```

Auto-detect genre:

```powershell
python .\music_metadata.py --source "C:\Music\Output"
```

### Covers Only

Create covers and embed them into MP3 files:

```powershell
python .\music2picture.py covers --source "C:\Music\Output" --output "C:\Music\Output\covers" --center-title --embed-cover
```

## How Covers Are Generated

The cover is generated from the song itself. The script analyzes loudness, bass, mids, highs, peaks, and estimated BPM. These values drive a unique colorful pattern.

Covers are not identical even for similar songs: generation includes randomness, but the randomness is guided by the audio features. This makes the image feel alive and connected to the track.

## Examples

The `example` folder contains test songs and generated covers.

```text
example/Im so sorry.mp3
example/Into Yesterday.mp3
example/INVISIBLE.mp3
```

Example cover folders:

```text
example/covers_no_title
example/covers_with_title
```

> **Author of project: Zeynalov U.R.o.**
