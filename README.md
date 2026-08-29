# Кузница Звука

<p align="center">
  <a href="https://github.com/dumuzeyn/Sonic-Forge/raw/refs/heads/main/dist/SonicForge.exe">
    <img src="https://img.shields.io/badge/Скачать-SonicForge.exe-24272D?style=for-the-badge" alt="Скачать SonicForge.exe">
  </a>
</p>

[English](#sonic-forge)

Кузница Звука обрабатывает один аудиофайл или папку: анализирует музыку, изменяет звук и метаданные, локально распознаёт текст песни и создаёт обложки. Исходные файлы не изменяются. Готовый результат попадает в выбранную папку только после завершения всех отмеченных этапов.

## Возможности

- Нормализация громкости, шумоподавление, лимитер, эквалайзер, фильтры, компрессор и эффекты.
- Просмотр, изменение, полная замена или очистка метаданных.
- Локальное распознавание текста через `faster-whisper`, определение языка и экспорт TXT/LRC.
- Независимые этапы **Звук**, **Метаданные**, **Текст** и **Обложка**.
- Остановка без публикации незавершённых файлов.
- FFmpeg и FFprobe встроены в EXE.

## Два движка обложек

В приложении доступны два отдельных варианта. Они используют один анализ песни, но создают изображение разными способами.

### AI Cover Generation

Локальный генеративный движок создаёт полноценные художественные сцены: окружение, свет, глубину, центральную метафору и отдельную композицию для каждой песни. Для него используется `stable-diffusion.cpp` и выбранная пользователем совместимая модель `.safetensors`, `.ckpt` или `.gguf`.

Для песни создаются четыре художественные концепции. Проверка качества отбрасывает пустые, слишком тёмные, шаблонные и чрезмерно похожие варианты. Текст добавляется только после создания изображения и может быть отключён.

Модель хранится отдельно от EXE:

```text
%LOCALAPPDATA%\SonicForge\models\image
```

После установки модели генерация работает без интернета. Если AI-модель недоступна, выбранный AI-режим может завершить работу через Music2Picture v2 и сообщает об этом в журнале. Это аварийное поведение не объединяет два пользовательских режима: Music2Picture v2 можно выбрать напрямую.

### Music2Picture v2

Встроенный локальный движок не требует отдельной модели. В нём один универсальный параметрический режим без Aurora, Plasma, Ocean и Fusion. Геометрия, композиция, фактура, плотность, палитра, фокус и движение непрерывно вычисляются из `VisualDNA` и `VisualPlan`, поэтому песня не назначается одному из нескольких шаблонов.

## Анализ песни

Общая основа обоих движков:

```text
Audio
-> Audio Analysis
-> VisualDNA
-> Song Description
-> Visual Brief + VisualPlan
-> AI Cover Generation или Music2Picture v2
```

Анализ учитывает абсолютную громкость и пик без предварительной нормализации, относительную динамику, темп и уверенность, атаки, плотность и регулярность ритма, спектральный центр, спад, контраст, flatness, flux, басовую массу, гармоничность, тональность, лад, смены гармонии и контраст частей песни. Абсолютная громкость, локальная динамика и структура хранятся раздельно.

Звук формирует основную часть `VisualDNA`. Название, метаданные и имеющийся текст песни уточняют смысл, но не заменяют музыкальный характер. Простого правила вида «BPM определяет цвет» нет: палитра одновременно зависит от эмоциональных, тональных, спектральных и структурных признаков.

## Описания для папки

На вкладке **Обложка** можно создать описания для одного файла или сразу для всей папки. Каждая песня получает собственные `song_description` и `visual_brief`. В списке можно открыть результат конкретного трека и перегенерировать только его.

Привязка хранится по нормализованному полному пути, размеру и времени изменения файла, а внутри записи также сохраняется аудио-отпечаток. Неизменённые песни загружаются из кэша:

```text
%LOCALAPPDATA%\SonicForge\analysis\track_descriptions.json
```

При указанной папке назначения доступная копия результатов сохраняется в `.sonicforge/track_descriptions.json`. Ошибка одного повреждённого файла записывается отдельно и не останавливает остальные песни.

## Порядок выполнения

Для обложки сначала анализируется исходный звук, затем создаются описание, визуальный план и готовое изображение. Только после этого выполняются выбранные операции со звуком, метаданными и текстом; готовая обложка встраивается в обработанную копию перед публикацией:

```text
анализ -> VisualDNA -> описание -> визуальный план -> обложка
-> звук -> метаданные -> текст -> встраивание -> публикация
```

Имя файла используется как `Title` только при отсутствии тега названия и пустом поле названия в приложении.

## Использование

1. Выберите файл или папку с музыкой и папку назначения.
2. На вкладке **Обложка** выберите **AI-обложка** или **Music2Picture v2**.
3. Настройте нужные вкладки.
4. На вкладке **Выполнение** отметьте этапы и нажмите **Запустить**.

## Командная строка

```powershell
# Одна песня
python .\easy_music_process.py --source "C:\Music\song.mp3" --output "C:\Music\Ready"

# Папка с принудительной заменой жанра
python .\easy_music_process.py --source "C:\Music\Input" --output "C:\Music\Ready" --genre "Rock" --overwrite-genre

# Описания всех песен с постоянным кэшем
python .\music2picture.py describe --source "C:\Music\Input" --output "C:\Music\Ready"

# Music2Picture v2 без текста на изображении
python .\music2picture.py covers --source "C:\Music\Input" --output "C:\Music\Covers" --engine music2picture_v2 --text-mode none
```

## Установка и сборка

Готовая Windows-версия: [скачать SonicForge.exe](https://github.com/dumuzeyn/Sonic-Forge/raw/refs/heads/main/dist/SonicForge.exe).

AI-модель не входит в EXE из-за размера и загружается отдельно из окна управления моделью. Для сборки из исходников:

```powershell
pip install -r requirements.txt
pip install pyinstaller
python -m PyInstaller --noconfirm --clean .\SonicForge.spec
```

## Основа проектных решений

Архитектура использует собственную компактную реализацию анализа на NumPy/SciPy, но набор признаков и разделение уровней сверялись с первичными источниками:

- [Essentia: spectral, temporal, tonal and rhythm descriptors](https://essentia.upf.edu/documentation.html).
- [DEAM: continuous valence/arousal annotations for music](https://cvml.unige.ch/databases/DEAM/).
- [Music-color associations are mediated by emotion, PNAS](https://doi.org/10.1073/pnas.1212562110).
- [MuLan: joint embedding of music audio and natural language](https://arxiv.org/abs/2208.12415).
- [CLAP: learning audio concepts from natural-language supervision](https://arxiv.org/abs/2206.04769).
- [Audio-guided Album Cover Art Generation](https://arxiv.org/abs/2207.07162).

MuLan и CLAP указаны как направление для будущего обучаемого audio-text слоя; их модели не выдаются за уже встроенные в текущий анализатор.

> Автор проекта: Зейналов У.Р.о.

---

# Sonic Forge

Sonic Forge processes one track or a folder while leaving source files unchanged. Audio, metadata, local lyrics recognition, and cover creation remain independent stages, and completed files are published only after all selected work finishes.

## Two cover engines

**AI Cover Generation** and **Music2Picture v2** are separate user-selectable engines. Both consume the same audio-first pipeline:

```text
Audio -> Audio Analysis -> VisualDNA -> Song Description
-> Visual Brief + VisualPlan -> selected cover engine
```

AI Cover Generation uses a local `stable-diffusion.cpp` model to create cinematic, surreal, or editorial scenes and then applies quality control and optional typography. Music2Picture v2 is a built-in procedural renderer with one adaptive parametric system. It has no Aurora, Plasma, Ocean, or Fusion user modes.

The analysis keeps absolute loudness, local dynamics, global structure, rhythm, timbre, harmony, key, section contrast, and spectral change as distinct evidence. Audio dominates VisualDNA; metadata and existing lyrics provide bounded semantic guidance.

## Batch descriptions

Selecting a folder can generate a separate `song_description` and `visual_brief` for every supported audio file. Results are attached to each track by canonical path, size, modification time, and an audio fingerprint. Unchanged tracks are restored from `%LOCALAPPDATA%\SonicForge\analysis\track_descriptions.json`. One damaged file does not stop the batch, and the selected track can be regenerated independently.

## Download

[Download SonicForge.exe](https://github.com/dumuzeyn/Sonic-Forge/raw/refs/heads/main/dist/SonicForge.exe)

FFmpeg and FFprobe are bundled. The multi-gigabyte image model remains a separate optional download managed inside the application.

> Project author: Zeynalov U.R.o.
