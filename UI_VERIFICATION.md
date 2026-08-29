# Sonic Forge verification

Date: 2026-08-23

## User interface

- Startup client size: approximately `911 x 674` on the verification machine, preserving a compact horizontal 4:3 shape.
- Previous width cause: the Lyrics toolbar placed actions, format, language, and two long checkboxes in one horizontal row (`1218 px` requested width).
- Fix: actions and options use separate compact rows; the window adds only the width needed to preserve its horizontal shape.
- Five equal grid-weight tabs retain the same dimensions and window geometry when switched.
- Russian primary labels are shown in full. Long explanations remain in tooltips or wrapped secondary text.
- Processing log is read-only but supports mouse selection, `Ctrl+C`, `Ctrl+A`, scrolling, Copy/Select All context actions, Copy Log, and Clear.

## Cover pipeline

`SongAnalysis -> Local Lyrics -> VisualProfile -> CoverConcept -> LocalImageProvider -> Typography -> Validation`

- Primary backend: `stable-diffusion.cpp`, Windows Vulkan runtime commit `97d2990`.
- Recommended checkpoint: `DreamShaper8_LCM.safetensors` (about 2.1 GB).
- External storage: `%LOCALAPPDATA%\SonicForge\models\image`.
- Lazy behavior: no image runtime or model activity until a cover is requested.
- Device selection: discrete NVIDIA/AMD/Intel Arc is preferred; parameters can remain in RAM with a VRAM budget and layer streaming.
- Recovery: memory errors retry at 384 px on CPU; any remaining generation error activates Music2Picture.
- Secondary engine: embedded Music2Picture v2 with one adaptive VisualDNA-driven renderer; it is also available as the AI failure path.
- Cloud provider remains an optional architecture extension and is absent from the normal UI.

## Local image acceptance

The recommended model, semantic checker, and runtime were installed outside the repository. Real local generation completed successfully with the quality-oriented DreamShaper 8 model. Five 512 px acceptance covers were generated from real songs and visually inspected in `demo_covers/semantic_ai_final`. They use distinct scenes and focal metaphors: a house in grass, an open cage at sea, a broken red relic, lonely dancing shoes, and a train on diverging tracks.

| File | Semantic themes | Composition |
| --- | --- | --- |
| `01_another_love.png` | love, rain, conflict | aerial tableau / portrait |
| `02_drive_ahead.png` | night, journey, freedom, conflict | double exposure |
| `03_carol_bells.png` | winter night | symbolic city landscape |
| `04_bullet_hell.png` | conflict, resistance | portrait silhouette |
| `05_fallen_down.png` | rain, memory, nature, home | atmospheric landscape |

The five outputs differ in scene, subject, scale, layout, atmosphere, and visual metaphor. They are not recolored procedural templates.

## Lyrics and Voltune

- Local provider: bundled `faster-whisper`, loaded only on recognition.
- Language: provider detection plus script analysis; confidence is shown only when available.
- Exports: same-basename UTF-8 TXT and timestamped LRC.
- Current Voltune main `73f7012` checks `<basename>.lrc`, then `<basename>.txt`, then embedded lyrics.
- Lyrics run before cover generation and are given semantic priority. A recognition failure is logged per song and does not prevent cover generation.

## Automated checks

- Python compilation: passed.
- 25 unit/integration/GUI tests: passed.
- Forced local-provider failure: passed, fallback returned an image.
- Direct and fallback calls both use the same universal Music2Picture v2 renderer without style buckets.
- Model manager custom-path/status test: passed.
- Read-only journal copying test: passed.
- Stable window geometry and equal tab layout tests: passed.
- Lyrics batch, TXT/LRC, language analysis, semantic priority, and stage-order tests: passed.

## Packaging

- One-file windowed PyInstaller configuration; no terminal window.
- FFmpeg and FFprobe bundled.
- `faster-whisper`, CTranslate2, PyAV, ONNX Runtime, and Music2Picture fallback bundled.
- Image runtime and checkpoint intentionally stay outside the EXE.
