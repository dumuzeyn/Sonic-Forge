# Кузница Звука

<p align="center">
  <a href="https://github.com/dumuzeyn/Sonic-Forge/raw/refs/heads/main/dist/SonicForge.exe">
    <img src="https://img.shields.io/badge/Скачать-SonicForge.exe-24272D?style=for-the-badge" alt="Скачать SonicForge.exe">
  </a>
</p>

[English](#sonic-forge)

Кузница Звука обрабатывает один аудиофайл или папку: анализирует музыку, изменяет звук и метаданные, локально распознаёт текст песни и создаёт обложки. Исходные файлы не изменяются. Готовый результат попадает в выбранную папку только после завершения всех отмеченных этапов.

## Возможности

- Понятные профили звука и макро-регуляторы с отдельным экспертным режимом.
- Анализ записи, рекомендация обработки и выровненное по громкости сравнение «Оригинал / Результат».
- Двухпроходная нормализация, автоматическое шумоподавление, лимитер, эквалайзер, компрессор и эффекты.
- Просмотр, изменение, полная замена или очистка метаданных.
- Локальное распознавание текста через `faster-whisper`, определение языка и экспорт TXT/LRC.
- Независимые этапы **Звук**, **Метаданные**, **Текст** и **Обложка**.
- Остановка без публикации незавершённых файлов.
- FFmpeg встроен в EXE; длительность и метаданные читаются внутри приложения.

## Обработка звука

В обычном режиме выбирается ожидаемый результат: **Сбалансированный**, **Сохранить характер**, **Громче и плотнее**, **Чистый звук**, **Больше баса**, **Ярче и подробнее** или **Шире**. Интенсивность и четыре аккуратных регулятора позволяют уточнить громкость, характер, бас и пространство без работы с инженерными терминами.

Кнопка **Анализировать** оценивает громкость, динамику, бас, высокие частоты и постоянный фоновый шум, после чего объясняет рекомендацию. **Создать сравнение** готовит характерный фрагмент; оригинал и обработанный результат воспроизводятся с одинаковой воспринимаемой громкостью.

В экспертном окне отдельно находятся **Улучшение** и **Темп и эффекты**. Нейтральные настройки действительно ничего не меняют: частотные срезы выключены, финальное усиление равно `1.0`, а шумоподавление в режиме **Авто** применяется только при обнаружении заметного постоянного шума. Частота дискретизации и число каналов по умолчанию сохраняются как в источнике.

Одинаковая цепочка коррекции используется перед loudnorm в обоих проходах:

```text
источник -> коррекция / эффекты -> анализ loudnorm
источник -> та же коррекция / эффекты -> loudnorm -> защита пиков -> результат
```

## Два движка обложек

В приложении доступны два отдельных варианта. Они используют один анализ песни, но создают изображение разными способами.

### AI Cover Generation

Локальный генеративный движок создаёт полноценные художественные сцены: окружение, свет, глубину, центральную метафору и отдельную композицию для каждой песни. Для него используется `stable-diffusion.cpp` и выбранная пользователем совместимая модель `.safetensors`, `.ckpt` или `.gguf`.

При прямом создании приложение генерирует один готовый вариант, а кнопка **Новый вариант** создаёт следующую независимую трактовку. В полном конвейере сравниваются разные художественные концепции: кинематографическая сцена, портрет в окружении, предметная метафора, редакционная, сюрреалистическая, абстрактная или минималистичная композиция. У каждого семейства свой короткий prompt-шаблон и контекстный negative prompt. Портретный вариант разрешает человека и запрещает только дефекты лица, рук и случайные дубликаты.

Смысловая CLIP-модель загружается в память в основном пути AI-генерации и сопоставляет каждый результат с предметом, сценой и метафорой. Если файл CLIP отсутствует в старой установке, приложение пытается установить его автоматически. Общий отбор учитывает смысл, эстетику, композицию, свободную область для названия, разнообразие, соответствие концепции и визуальные дефекты; вклад каждого компонента виден в журнале.

Текст добавляется только после генерации изображения и может быть отключён. Для названия доступны исходный, очищенный, стилизованный и короткий режимы. Обработчик названия удаляет мусор файла, оценивает уверенность, выбирает смысловые слова, строит иерархию строк и при сомнении возвращается к очищенному оригиналу. Короткий вариант использует только слова исходного названия.

Типографика получает изображение, характер песни, художественную концепцию и результат обработки названия одновременно. Она выбирает семейство шрифта, вес, реальное межбуквенное расстояние, разбиение строк, смысловой акцент, иерархию исполнителя, безопасную область и один из вариантов раскладки. Цвет, контраст, подложка, обводка и свечение рассчитываются по пикселям конкретной зоны, поэтому текст не является одинаковой надписью поверх всех обложек.

Модель хранится отдельно от EXE:

```text
%LOCALAPPDATA%\SonicForge\models\image
```

При рекомендуемой установке загружаются основная модель изображения, локальный движок и модель смысловой проверки. После установки генерация работает без интернета. Экономный, быстрый, сбалансированный, качественный и максимальный профили имеют отдельные размеры, число шагов и guidance. Текущая SD 1.x модель честно работает в собственном разрешении до 512×512; больший итоговый размер получается отдельным увеличением и отмечается в журнале вместе с возможностями backend.

Если AI-модель недоступна, выбранный AI-режим может завершить работу через Music2Picture v2 и сообщает об этом в журнале. Это аварийное поведение не объединяет два пользовательских режима: Music2Picture v2 можно выбрать напрямую.

### Music2Picture v2

Встроенный локальный движок не требует отдельной модели и интернета. Основной режим **Artistic Texture v3** создаёт насыщенную абстрактную живопись из крупных цветовых масс, текучих переходов, органических завихрений, мелких прожилок и мягкого зерна. Старые Aurora, Plasma, Ocean, Fusion и waveform-подобные стили не используются.

Темп, энергия, бас, динамика и спектральный характер управляют масштабом, турбулентностью, направлением потоков, детализацией и контрастом художественно, а не рисуются в виде графика. Для каждого трека строится гармоничная палитра из 3–7 оттенков и выбирается одна из пяти пространственных композиций. Отпечаток аудио, версия генератора и номер варианта образуют постоянный seed: одинаковые исходник и настройки дают одинаковую обложку.

**Быстрый просмотр** строит вариант в размере 384×384 во временной папке. **Новый вариант** увеличивает номер вариации предсказуемо, а **Создать обложку** выводит выбранный вариант в заданном полном размере. Все эти операции выполняются в фоновом потоке и не замораживают окно.

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

### Только создать обложку

1. Выберите один аудиофайл. Папку назначения указывать необязательно.
2. Откройте вкладку **Обложка** и выберите движок.
3. Нажмите **Создать обложку**.

PNG сохранится рядом с песней. Если указана папка назначения, он попадёт в её подпапку `covers`. Галочка **Встроить в файл** также добавляет созданную обложку в выбранный MP3. Для Music2Picture можно сначала нажать **Быстрый просмотр**, выбрать **Новый вариант**, а затем выполнить **Создать обложку** в полном качестве. Эти действия не требуют запуска остальных этапов.

### Полная обработка

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

AI-модель и модель смысловой проверки не входят в EXE из-за размера и загружаются отдельно из окна управления моделью. Среда смысловой проверки включена в приложение, поэтому после рекомендуемой установки никаких дополнительных программ не требуется. Для сборки из исходников:

```powershell
pip install -r requirements.txt
pip install pyinstaller
python -m PyInstaller --noconfirm --clean .\SonicForge.spec
```

## Основа проектных решений

Архитектура использует собственную компактную реализацию анализа на NumPy, но набор признаков и разделение уровней сверялись с первичными источниками:

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

## Audio processing

The standard view offers result-oriented profiles and clean macro controls for loudness, character, bass, and stereo space. **Analyze** explains the recording's loudness, dynamics, tonal balance, and stationary noise; **Create comparison** generates loudness-matched Original and Result previews.

Expert settings separate enhancement from tempo and creative effects. Both loudnorm passes use the exact same preprocessing chain. Final gain defaults to `1.0`, frequency cuts are genuinely off until enabled, automatic denoise only acts on detected stationary noise, and source sample rate and mono/stereo layout are preserved whenever MP3 supports them.

## Two cover engines

**AI Cover Generation** and **Music2Picture v2** are separate user-selectable engines. Both consume the same audio-first pipeline:

```text
Audio -> Audio Analysis -> VisualDNA -> Song Description
-> Visual Brief + VisualPlan -> selected cover engine
```

AI Cover Generation uses a local `stable-diffusion.cpp` model with distinct compact templates for cinematic, portrait, symbolic, editorial, surreal, abstract, and minimal scenes. A local CLIP model is loaded in the main runtime path and compares every candidate with the song concept. Final ranking combines semantic relevance, aesthetics, composition, title-safe space, diversity, concept fit, and artifact penalties.

Original, cleaned, stylized, and short title modes are available. Stylized mode builds semantic emphasis and line hierarchy rather than merely changing case, while low-confidence transformations fall back to the cleaned canonical title. Typography receives the actual artwork pixels, song profile, concept, and title treatment to select contextual font roles, tracking, layout, contrast protection, and accents.

Music2Picture v2 uses the built-in **Artistic Texture v3** renderer. It creates layered fluid, marbled, and turbulent artwork locally from macro color masses, meso-scale flows, and micro detail; it never draws a waveform or spectrum. Audio features control texture scale, flow, turbulence, contrast, detail, and a deterministic 3–7 color palette. Five spatial composition families prevent every track from becoming a recolored copy of one template.

**Quick preview** renders a deterministic 384×384 draft. **New variant** advances the stable variation number, while **Create cover** renders that selected variant at full quality. Cover work stays off the UI thread.

The analysis keeps absolute loudness, local dynamics, global structure, rhythm, timbre, harmony, key, section contrast, and spectral change as distinct evidence. Audio dominates VisualDNA; metadata and existing lyrics provide bounded semantic guidance.

## Batch descriptions

Selecting a folder can generate a separate `song_description` and `visual_brief` for every supported audio file. Results are attached to each track by canonical path, size, modification time, and an audio fingerprint. Unchanged tracks are restored from `%LOCALAPPDATA%\SonicForge\analysis\track_descriptions.json`. One damaged file does not stop the batch, and the selected track can be regenerated independently.

## Download

[Download SonicForge.exe](https://github.com/dumuzeyn/Sonic-Forge/raw/refs/heads/main/dist/SonicForge.exe)

FFmpeg is bundled. The multi-gigabyte image and semantic models remain separate downloads managed inside the application. Their runtime dependencies are included, so the recommended installation needs no additional software.

> Project author: Zeynalov U.R.o.
