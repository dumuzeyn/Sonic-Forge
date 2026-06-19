# MusicPolisher

[English version](#engFer)

MusicPolisher - инструмент для быстрой подготовки музыкальной папки:

- нормализует и безопасно усиливает звук;
- конвертирует обработанные треки в MP3;
- записывает чистый тег `title` из имени файла;
- записывает `genre` только если у песни еще нет жанра;
- создает сгенерированную обложку для каждой песни;
- встраивает созданную обложку в MP3-файл.

Главный простой файл для запуска - `easy_music_process.py`. Отдельные скрипты тоже можно запускать напрямую.

## Требования

Установить Python-библиотеки:

```powershell
pip install numpy pillow
```

FFmpeg и FFprobe должны быть доступны из PowerShell:

```powershell
ffmpeg -version
ffprobe -version
```

Поддерживаемые входные аудиоформаты:

```text
.mp3 .flac .wav .m4a .aac .ogg .opus .wma
```

Результат обработки сохраняется как MP3.

## Easy Music Process

`easy_music_process.py` запускает весь процесс:

1. `Normalize-Music.py` нормализует, мягко очищает шум, безопасно усиливает и экспортирует MP3.
2. `music_metadata.py` записывает чистые метаданные `title` и `genre`.
3. `music2picture.py` создает обложки и встраивает их в обработанные MP3-файлы.

### Запуск через консоль

Интерактивный режим:

```powershell
python .\easy_music_process.py
```

Запуск одной командой:

```powershell
python .\easy_music_process.py --source "C:\Music\Input" --output "C:\Music\Output"
```

Указать жанр только для песен, у которых жанра еще нет:

```powershell
python .\easy_music_process.py --source "C:\Music\Input" --output "C:\Music\Output" --genre "Rock"
```

Использовать старые цвета обложек вместо нового режима драйвовости:

```powershell
python .\easy_music_process.py --source "C:\Music\Input" --output "C:\Music\Output" --color-mode bpm
```

### Запуск из PyCharm / напрямую из кода

Откройте `easy_music_process.py`, измените значения вверху файла, поставьте `RUN_FROM_CODE = True` и нажмите Run:

```python
RUN_FROM_CODE = True
CODE_SOURCE = r"C:\Music\Input"
CODE_OUTPUT = r"C:\Music\Output"
CODE_GENRE = None
CODE_COLOR_MODE = "drive"
CODE_FINAL_GAIN = 1.15
CODE_DENOISE = True
CODE_DENOISE_STRENGTH = 4.0
CODE_LIMITER = True
CODE_OVERWRITE_GENRE = False
```

Когда `RUN_FROM_CODE = False`, этот же файл работает как обычная консольная программа.

## Изменения нормализации звука

Старый скрипт нормализовал звук, а потом применял сильное дополнительное усиление `1.30`. На некоторых песнях из-за этого могли появляться шумы, резкость или артефакты после повышения громкости.

Новая цепочка по умолчанию более аккуратная:

1. очень мягкое FFT-шумоподавление: `afftdn=nr=4:nf=-70`;
2. двухпроходный FFmpeg `loudnorm` с целью `-14 LUFS`, `-1.5 dBTP`, `11 LRA`;
3. меньшее дополнительное усиление: `1.15` вместо `1.30`;
4. финальный лимитер: `alimiter=limit=0.95:attack=5:release=80`.

Это сделано, чтобы уменьшить шипение/артефакты от усиления и при этом не испортить музыку сильной обработкой. Если конкретный трек звучит лучше без шумоподавления, его можно выключить:

```powershell
python .\Normalize-Music.py --source "C:\Music\Input" --output "C:\Music\Output" --no-denoise
```

Если нужно больше или меньше шумоподавления:

```powershell
python .\Normalize-Music.py --source "C:\Music\Input" --output "C:\Music\Output" --denoise-strength 3
```

Скрипт теперь принимает и папку, и один аудиофайл:

```powershell
python .\Normalize-Music.py --source "C:\Music\Input\In the Sea.mp3" --output "C:\Music\Output"
```

## Поведение метаданных

`music_metadata.py` теперь защищает существующие жанры.

Для каждой песни скрипт сначала читает текущий тег `genre` через FFprobe:

- если жанр уже есть, он сохраняется;
- если жанра нет, используется `--genre`, ручной выбор или автоопределение;
- `title` все равно очищается по имени файла;
- лишние метаданные все равно удаляются, но сохраненный жанр записывается обратно.

Пример: эта команда не заменит существующий жанр `Anime` на `Rock`, если не включить принудительную перезапись:

```powershell
python .\music_metadata.py --source "C:\Music\Output" --genre "Rock"
```

Принудительно заменить существующие жанры:

```powershell
python .\music_metadata.py --source "C:\Music\Output" --genre "Rock" --overwrite-genre
```

Проверка без изменения файлов:

```powershell
python .\music_metadata.py --source "C:\Music\Output" --genre "Rock" --dry-run
```

## Цветовые режимы обложек

В `music2picture.py` есть два цветовых режима.

### Режим `bpm`

Это старое поведение из GitHub-версии. Узор и цвета в основном зависят от примерного BPM/local BPM. Режим остался доступен и используется по умолчанию, если запускать `music2picture.py` напрямую:

```powershell
python .\music2picture.py covers --source "C:\Music\Output" --output "C:\Music\Output\covers" --color-mode bpm
```

### Режим `drive`

Это новый второй режим. Он меняет только цвета. Геометрия узора, искажения, отрисовка названия и встраивание обложки остаются такими же.

Цвет зависит от локальной драйвовости участка песни, а не только от BPM всей песни. Для каждого локального окна считается:

```text
D(t) = 0.4 * O(t) + 0.3 * R(t) + 0.2 * F(t) + 0.1 * C(t)
```

Где каждый показатель нормализуется в диапазон `0..1`:

- `O(t)` = плотность атак/onset, сколько новых звуков появляется в окне;
- `R(t)` = RMS-энергия/громкость;
- `F(t)` = spectral flux, насколько быстро меняется звук;
- `C(t)` = spectral centroid, насколько звук яркий и высокочастотный.

Потом мягко добавляется влияние локального BPM:

```text
drive = 0.85 * D(t) + 0.15 * local_bpm_score
```

Палитра использует меньше цветов, но они сильнее отличаются друг от друга:

```text
медленно / низкий драйв       -> фиолетовый
низко-средний драйв           -> темно-синий / синий
средний драйв                 -> зеленый
средне-высокий драйв          -> желтый
высокий драйв                 -> оранжевый
быстро / максимальный драйв   -> красный
```

Создать обложки в режиме `drive`:

```powershell
python .\music2picture.py covers --source "C:\Music\Output" --output "C:\Music\Output\covers_drive" --color-mode drive
```

Создать обложки в режиме `drive` с названием по центру:

```powershell
python .\music2picture.py covers --source "C:\Music\Output" --output "C:\Music\Output\covers_drive_title" --color-mode drive --center-title
```

Создать и встроить обложки в MP3:

```powershell
python .\music2picture.py covers --source "C:\Music\Output" --output "C:\Music\Output\covers" --color-mode drive --center-title --embed-cover
```

## Прямой запуск отдельных скриптов

Только нормализация:

```powershell
python .\Normalize-Music.py --source "C:\Music\Input" --output "C:\Music\Output"
```

Только метаданные:

```powershell
python .\music_metadata.py --source "C:\Music\Output"
```

Только обложки, старый режим:

```powershell
python .\music2picture.py covers --source "C:\Music\Output" --output "C:\Music\Output\covers_bpm" --color-mode bpm
```

Только обложки, режим драйвовости:

```powershell
python .\music2picture.py covers --source "C:\Music\Output" --output "C:\Music\Output\covers_drive" --color-mode drive
```

## Практический пример

Для трека, на котором раньше могли появляться шумы после усиления:

```powershell
python .\Normalize-Music.py --source "C:\Users\Rasul\Music\MyMusicCollection\Музыка\In the Sea.mp3" --output ".\_verify_normalized"
```

Создать тестовую обложку в режиме `drive`:

```powershell
python .\music2picture.py covers --source "C:\Users\Rasul\Music\MyMusicCollection\Музыка\In the Sea.mp3" --output ".\_verify_covers" --size 256 --color-mode drive
```

Проверить, что существующий жанр сохраняется:

```powershell
python .\music_metadata.py --source ".\_verify_normalized\In the Sea.mp3" --genre "Rock" --dry-run
```

Ожидаемое поведение: если у `In the Sea.mp3` уже есть `Anime`, dry-run показывает, что `Anime` сохранен.

## Примечания

- `easy_music_process.py` по умолчанию использует `--color-mode drive`, потому что это новый улучшенный режим обложек.
- `music2picture.py covers` по умолчанию использует `--color-mode bpm`, чтобы старое поведение оставалось доступным без изменений.
- Существующие теги `genre` сохраняются, если не использовать `--overwrite-genre`.
- Если конкретная песня требует более прозрачного звучания, можно уменьшить `--final-gain` или использовать `--no-denoise`.

>**Автор проекта: Зейналов У.Р.о.**
---
<h1 id = engFer>
MusicPolisher
</h1>

MusicPolisher is an all-in-one tool for preparing a music folder:

- normalizes and safely boosts audio;
- converts processed tracks to MP3;
- writes a clean `title` tag from the file name;
- writes `genre` only when the song does not already have one;
- creates a generated cover for every song;
- embeds the generated cover into the MP3 file.

The main easy entry point is `easy_music_process.py`. The separate scripts can still be used directly.

## Requirements

Install Python packages:

```powershell
pip install numpy pillow
```

FFmpeg and FFprobe must be available from PowerShell:

```powershell
ffmpeg -version
ffprobe -version
```

Supported input audio formats:

```text
.mp3 .flac .wav .m4a .aac .ogg .opus .wma
```

Processed output is written as MP3.

## Easy Music Process

`easy_music_process.py` runs the full pipeline:

1. `Normalize-Music.py` normalizes, gently denoises, safely boosts, and exports MP3 files.
2. `music_metadata.py` writes clean `title` and `genre` metadata.
3. `music2picture.py` creates covers and embeds them into the processed MP3 files.

### Console usage

Interactive mode:

```powershell
python .\easy_music_process.py
```

One-command mode:

```powershell
python .\easy_music_process.py --source "C:\Music\Input" --output "C:\Music\Output"
```

Set a genre only for songs that do not already have a genre:

```powershell
python .\easy_music_process.py --source "C:\Music\Input" --output "C:\Music\Output" --genre "Rock"
```

Use the original cover colors instead of the new drive colors:

```powershell
python .\easy_music_process.py --source "C:\Music\Input" --output "C:\Music\Output" --color-mode bpm
```

### PyCharm / direct code run

Open `easy_music_process.py`, edit these values near the top, then set `RUN_FROM_CODE = True` and press Run:

```python
RUN_FROM_CODE = True
CODE_SOURCE = r"C:\Music\Input"
CODE_OUTPUT = r"C:\Music\Output"
CODE_GENRE = None
CODE_COLOR_MODE = "drive"
CODE_FINAL_GAIN = 1.15
CODE_DENOISE = True
CODE_DENOISE_STRENGTH = 4.0
CODE_LIMITER = True
CODE_OVERWRITE_GENRE = False
```

When `RUN_FROM_CODE` is `False`, the same file works as a normal console program.

## Audio Normalization Changes

The old script normalized audio and then applied a strong extra gain of `1.30`. On some songs this could expose noise or create harsh artifacts after the volume increase.

The new default chain is more conservative:

1. very gentle FFT denoise: `afftdn=nr=4:nf=-70`;
2. two-pass FFmpeg `loudnorm` to target `-14 LUFS`, `-1.5 dBTP`, `11 LRA`;
3. smaller extra gain: `1.15` instead of `1.30`;
4. final limiter: `alimiter=limit=0.95:attack=5:release=80`.

This is meant to reduce hiss/artifacts from boosting without heavily damaging the music. If a track sounds better without denoise, disable it:

```powershell
python .\Normalize-Music.py --source "C:\Music\Input" --output "C:\Music\Output" --no-denoise
```

If you need more or less denoise:

```powershell
python .\Normalize-Music.py --source "C:\Music\Input" --output "C:\Music\Output" --denoise-strength 3
```

The script now accepts either a folder or one audio file:

```powershell
python .\Normalize-Music.py --source "C:\Music\Input\In the Sea.mp3" --output "C:\Music\Output"
```

## Metadata Behavior

`music_metadata.py` now protects existing genres.

For every song it first reads the current `genre` tag with FFprobe:

- if a genre already exists, that genre is kept;
- if there is no genre, the script uses `--genre`, manual choice, or auto-detection;
- title is still cleaned from the file name;
- extra metadata is still removed, but the preserved genre is written back.

Example: this command will not replace an existing `Anime` genre with `Rock` unless overwrite is requested:

```powershell
python .\music_metadata.py --source "C:\Music\Output" --genre "Rock"
```

To force replacement of existing genres:

```powershell
python .\music_metadata.py --source "C:\Music\Output" --genre "Rock" --overwrite-genre
```

Dry-run check:

```powershell
python .\music_metadata.py --source "C:\Music\Output" --genre "Rock" --dry-run
```

## Cover Color Modes

`music2picture.py` has two color modes.

### `bpm` mode

This is the original GitHub behavior. The cover pattern and colors are driven mainly by estimated BPM/local BPM. It remains available and is the default when using `music2picture.py` directly:

```powershell
python .\music2picture.py covers --source "C:\Music\Output" --output "C:\Music\Output\covers" --color-mode bpm
```

### `drive` mode

This is the new second mode. It changes only the colors. The pattern geometry, warping, title drawing, and embedding logic stay the same.

Color is based on local song drive/dynamics, not only whole-song BPM. For each local window the script computes:

```text
D(t) = 0.4 * O(t) + 0.3 * R(t) + 0.2 * F(t) + 0.1 * C(t)
```

Where every feature is normalized to `0..1`:

- `O(t)` = onset/attack density, how many new sounds appear in the window;
- `R(t)` = RMS energy/loudness;
- `F(t)` = spectral flux, how quickly the sound changes;
- `C(t)` = spectral centroid, how bright/high-frequency the sound is.

Local BPM influence is then added gently:

```text
drive = 0.85 * D(t) + 0.15 * local_bpm_score
```

The palette uses fewer, more distinct colors:

```text
slow / low drive    -> violet
low-medium drive    -> dark blue / blue
medium drive        -> green
medium-high drive   -> yellow
high drive          -> orange
fast / high drive   -> red
```

Generate drive-mode covers:

```powershell
python .\music2picture.py covers --source "C:\Music\Output" --output "C:\Music\Output\covers_drive" --color-mode drive
```

Generate drive-mode covers with centered title text:

```powershell
python .\music2picture.py covers --source "C:\Music\Output" --output "C:\Music\Output\covers_drive_title" --color-mode drive --center-title
```

Generate and embed drive-mode covers into MP3 files:

```powershell
python .\music2picture.py covers --source "C:\Music\Output" --output "C:\Music\Output\covers" --color-mode drive --center-title --embed-cover
```

## Direct Script Usage

Normalize only:

```powershell
python .\Normalize-Music.py --source "C:\Music\Input" --output "C:\Music\Output"
```

Metadata only:

```powershell
python .\music_metadata.py --source "C:\Music\Output"
```

Covers only, original mode:

```powershell
python .\music2picture.py covers --source "C:\Music\Output" --output "C:\Music\Output\covers_bpm" --color-mode bpm
```

Covers only, drive mode:

```powershell
python .\music2picture.py covers --source "C:\Music\Output" --output "C:\Music\Output\covers_drive" --color-mode drive
```

## Practical Example

For the track that previously exposed noise during boosting:

```powershell
python .\Normalize-Music.py --source "C:\Users\Rasul\Music\MyMusicCollection\Музыка\In the Sea.mp3" --output ".\_verify_normalized"
```

Generate a drive-color test cover:

```powershell
python .\music2picture.py covers --source "C:\Users\Rasul\Music\MyMusicCollection\Музыка\In the Sea.mp3" --output ".\_verify_covers" --size 256 --color-mode drive
```

Check that an existing genre is preserved:

```powershell
python .\music_metadata.py --source ".\_verify_normalized\In the Sea.mp3" --genre "Rock" --dry-run
```

Expected behavior: if `In the Sea.mp3` already has `Anime`, dry-run shows that `Anime` is kept.

## Notes

- `easy_music_process.py` defaults to `--color-mode drive` because this is the newer polished cover mode.
- `music2picture.py covers` defaults to `--color-mode bpm` so the original cover behavior remains available by default.
- Existing genre tags are preserved unless `--overwrite-genre` is used.
- Lower `--final-gain` or use `--no-denoise` if a specific song needs a more transparent sound.

>**Author of project: Zeynalov U.R.o.**
