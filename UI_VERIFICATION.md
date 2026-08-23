# Sonic Forge UI verification

Date: 2026-08-23

## Feature map

| Existing feature | UI location after redesign | Verified |
| --- | --- | --- |
| Single audio file | Source and destination / File | Yes |
| Source folder | Source and destination / Folder | Yes |
| Output folder | Source and destination / Choose | Yes |
| Title, artist, album, album artist | Metadata tab | Yes |
| Composer, year, track, genre, comment | Metadata | Yes |
| Disc, publisher, copyright, lyrics | Metadata / Actions / Additional fields | Yes |
| Read existing metadata | Metadata / Actions / Read tags | Yes |
| Overwrite genre | Metadata checkbox | Yes |
| Replace all metadata | Metadata checkbox | Yes |
| Clear all metadata | Metadata / Actions / Clear all | Yes |
| Integrated LUFS, true peak, LRA, final gain | Audio tab / Normalization | Yes |
| Denoise and strength | Audio processing / Cleanup and protection | Yes |
| Limiter | Audio processing / Cleanup and protection | Yes |
| EQ, filters, stereo width | Additional audio settings | Yes |
| Compressor | Additional audio settings | Yes |
| Pitch, speed, reverb, fades | Additional audio settings | Yes |
| Ocean, plasma, fusion, aurora | Cover art tab / Color mode | Yes |
| Seed, size, detail | Cover art | Yes |
| Center title and embed cover | Cover art | Yes |
| Do not change cover | Cover art header | Yes |
| Audio, metadata, cover stages | Processing tab | Yes |
| Run, stop, progress | Processing tab | Yes |
| Operation log and clear action | Processing tab / Processing log | Yes |
| RU/EN localization | Fixed header language button | Yes |
| Ctrl+A/C/X/V/Z | All editable fields and log | Yes |

## Checks

- `python -m compileall .`: passed.
- Module imports: passed.
- Ruff static checks: passed.
- Full temporary-file processing path: passed.
- Output audio, metadata, generated PNG, and embedded MP3 cover: passed.
- Four cover modes: passed.
- Window sizes 1180x860, 1280x920, and 1600x1000 in RU and EN: passed.
- Four fixed tabs: equal width and equal content area in RU and EN at 1180x860.
- No mapped widget outside the minimum window: passed.
- Button and checkbox geometry across RU/EN: unchanged.
- Button geometry across hover, pressed, focus, disabled, and processing states: unchanged.
- Denoise and cover dependency states: passed.
- Tooltip delay and non-overlapping placement: passed.
- UZYRO layered icon project round trip: five layers, 2048x2048, passed.
- Icon legibility at 16, 20, 24, 32, 40, 48, 64, 96, and 128 px: passed.
- PyInstaller one-file windowed build: passed.
- Packaged EXE startup, resource loading, and responsive main window: passed.
- Repository EXE and user copy SHA-256 match: passed.

## Tkinter limitations

- Native ttk controls do not provide arbitrary corner radii; the interface relies on spacing, alignment, restrained fills, and thin borders instead.
- Control widths are fixed where translated labels differ, so long future translations should be reviewed before being added.
