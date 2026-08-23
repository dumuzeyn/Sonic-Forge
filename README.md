# Кузница Звука

<p align="center">
  <a href="https://github.com/dumuzeyn/Sonic-Forge/blob/main/dist/SonicForge.exe">
    <img src="https://img.shields.io/badge/Скачать_EXE-Кузница--Звука.exe-24272D?style=for-the-badge" alt="Скачать SonicForge.exe">
  </a>
</p>

[English version](#english)

Кузница Звука — настольная утилита для подготовки музыкальных файлов. Она обрабатывает одну песню или папку, нормализует звук, изменяет метаданные, создаёт обложки и публикует готовый результат только после успешного завершения выбранных этапов.

## Возможности

- Нормализация громкости через FFmpeg loudnorm, шумоподавление и лимитер.
- Эквалайзер, частотные срезы, ширина стерео, компрессор и дополнительные звуковые эффекты.
- Чтение, редактирование, полная перезапись или очистка метаданных в выходной копии.
- Автоматическое определение жанра и принудительная замена существующего жанра.
- Генерация обложек в режимах `ocean`, `plasma`, `fusion` и `aurora`.
- Настраиваемые размер, детализация и Seed; встраивание обложки в MP3.
- Независимый выбор этапов: звук, метаданные и обложка.
- Остановка обработки без публикации незавершённых файлов.
- Русский и английский интерфейс, журнал операций и встроенные FFmpeg/FFprobe.

## Интерфейс

Источник и папка назначения всегда видны сверху. Остальные настройки разделены на четыре одинаковые вкладки, которые не меняют размер при переключении:

1. **Источник и результат** — выбор отдельного файла или папки и каталога назначения.
2. **Метаданные** — основные теги, чтение существующих значений и дополнительные поля.
3. **Звук** — нормализация, очистка, защита и отдельное окно дополнительных настроек.
4. **Обложка** — режим, Seed, размер, детализация и параметры встраивания.
5. **Выполнение** — выбор этапов, запуск, остановка, индикатор и журнал обработки.

Флажок **Не менять обложку** отключает связанные параметры, но не скрывает их. При отключённом шумоподавлении поле его силы также становится недоступным.

## Скачать и запустить

Готовая сборка содержит FFmpeg и FFprobe. Для запуска достаточно одного файла:

[Скачать SonicForge.exe](https://github.com/dumuzeyn/Sonic-Forge/blob/main/dist/SonicForge.exe)

```powershell
.\dist\SonicForge.exe
```

Сборка из исходников:

```powershell
pip install numpy pillow psutil pyinstaller
python -m PyInstaller --noconfirm --clean .\SonicForge.spec
```

## Примеры команд

Одна песня:

```powershell
python .\easy_music_process.py --source "C:\Music\Input\song.mp3" --output "C:\Music\Output" --color-mode plasma
```

Папка:

```powershell
python .\easy_music_process.py --source "C:\Music\Input" --output "C:\Music\Output" --color-mode plasma
```

Папка с принудительной заменой жанра:

```powershell
python .\easy_music_process.py --source "C:\Music\Input" --output "C:\Music\Output" --genre "Rock" --overwrite-genre --color-mode plasma
```

## Иконка

Монограмма `SF` создана в редакторе UZYRO по исходному силуэту. Редактируемый многослойный исходник находится в `assets/SonicForgeIcon.prdx`; PNG и многоразмерный ICO экспортированы из этого проекта. В знаке нет звуковой волны, внешней рамки или скруглённого контейнера.

> **Автор проекта: Зейналов У.Р.о.**

---

<h1 id="english">Sonic Forge</h1>

<p align="center">
  <a href="https://github.com/dumuzeyn/Sonic-Forge/blob/main/dist/SonicForge.exe">
    <img src="https://img.shields.io/badge/Download_EXE-Sonic--Forge.exe-24272D?style=for-the-badge" alt="Download SonicForge.exe">
  </a>
</p>

Sonic Forge is a desktop utility for preparing music files. It processes a single song or a folder, normalizes audio, edits metadata, creates cover art, and publishes finished files only after the selected stages complete successfully.

## Features

- FFmpeg loudnorm normalization, denoise, and limiter.
- Equalizer, frequency cutoffs, stereo width, compressor, and additional effects.
- Read, edit, fully replace, or clear metadata in the output copy.
- Automatic genre estimation and forced replacement of existing genres.
- Cover generation in `ocean`, `plasma`, `fusion`, and `aurora` modes.
- Configurable size, detail, Seed, and MP3 cover embedding.
- Independent audio, metadata, and cover processing stages.
- Safe cancellation without publishing incomplete files.
- Russian and English UI, an integrated processing log, and bundled FFmpeg/FFprobe.

## Interface

Source and destination remain visible at the top. Metadata, audio, cover art, and processing are separated into four equal tabs whose size does not change when selected. Additional audio and metadata fields open in compact dialogs.

**Do not change cover** disables related controls without hiding them. Disabling denoise also disables its strength field.

## Download And Launch

[Download SonicForge.exe](https://github.com/dumuzeyn/Sonic-Forge/blob/main/dist/SonicForge.exe)

```powershell
.\dist\SonicForge.exe
```

Build from source:

```powershell
pip install numpy pillow psutil pyinstaller
python -m PyInstaller --noconfirm --clean .\SonicForge.spec
```

## Command Examples

```powershell
python .\easy_music_process.py --source "C:\Music\Input\song.mp3" --output "C:\Music\Output" --color-mode plasma
python .\easy_music_process.py --source "C:\Music\Input" --output "C:\Music\Output" --color-mode plasma
python .\easy_music_process.py --source "C:\Music\Input" --output "C:\Music\Output" --genre "Rock" --overwrite-genre --color-mode plasma
```

## Icon

The `SF` monogram was traced from the supplied silhouette in UZYRO. Its editable layered source is `assets/SonicForgeIcon.prdx`; the PNG and multi-size ICO are exported from that project. The mark has no waveform, outer border, or rounded container.

> **Project author: Zeynalov U.R.o.**
