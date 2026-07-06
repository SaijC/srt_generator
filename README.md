# SRT Generator

A containerised background service that scans a folder for media files, transcribes the audio, translates to English if necessary, and outputs a `.srt` subtitle file alongside each media file.

---

## Project Goal

Automatically generate English subtitle files for a media library running on a low-power NUC box. The service runs quietly in the background, processing files at its own pace without impacting other running services.

---

## Pipeline

```
Scan folder for media files
        ↓
Extract audio (ffmpeg)
        ↓
Transcribe + Translate to English (Whisper)
        ↓
Write .srt file alongside source media
```

**Key decision:** Whisper handles both transcription and translation to English in a single pass using `--task translate`. This removes the need for a separate translation library and simplifies the pipeline significantly.

---

## Design Decisions

| Decision | Choice | Reason |
|---|---|---|
| Container | Docker via VS Code Dev Container | Clean dependencies, good learning environment |
| Audio extraction | ffmpeg | Industry standard |
| Transcription + Translation | OpenAI Whisper | Local, offline, handles both steps in one pass |
| Whisper model | `medium` (default, configurable) | Best fit for available RAM (~5GB usage) |
| Target language | English only | Whisper's translate mode covers all source languages |
| Output format | `.srt` | Standard subtitle format, named to match source file |
| Skip logic | Skip if matching `.srt` already exists | Avoids reprocessing on reruns |
| Processing | Sequential, one file at a time | Low resource environment, no rush |
| CPU priority | Low (nice level) | Background process, shouldn't compete with other services |

---

## Hardware

**Device:** GeekomMiniPC NucBox M5 Plus
**CPU:** AMD Ryzen 7 5825U (8 cores / 16 threads)
**RAM:** 32GB (approx. 14GB free for this service)
**Storage:** 512GB SSD

**Resource allocation for this service:**
- CPU: 8 of 16 threads (pinned via `--cpuset-cpus` in Docker)
- RAM: ~5GB (Whisper medium model)
- Fallback model: `small` (~2GB) if memory pressure increases

---

## Folder Structure

```
srt_generator/
├── .devcontainer/
│   ├── devcontainer.json
│   └── Dockerfile
├── src/
│   └── main.py
├── input/          # Mount point for media files
├── output/         # or .srt files written alongside input files
└── README.md
```

---

## Configuration (Environment Variables)

| Variable | Default | Description |
|---|---|---|
| `WHISPER_MODEL` | `medium` | Whisper model size (tiny/base/small/medium/large) |
| `INPUT_FOLDER` | `/input` | Folder to scan for media files |
| `OUTPUT_FOLDER` | same as input | Where to write .srt files |

---

## Development Curriculum

### Stage 1 — Project Setup
- Initialise git repo
- Create VS Code dev container config
- Install base dependencies (Python, ffmpeg, Whisper)
- Hello world inside the container ✓

### Stage 2 — Folder Scanner
- Scan a given folder for media files
- Log what it finds
- Handle edge cases (empty folder, no media files)

### Stage 3 — Audio Extraction
- Take a single media file
- Extract audio with ffmpeg
- Verify the output

### Stage 4 — Whisper Integration
- Feed extracted audio into Whisper
- Get transcript + English translation back
- Test with a short clip first

### Stage 5 — SRT Writer
- Take Whisper output
- Format and write a valid `.srt` file
- Verify it matches the source filename

### Stage 6 — Pipeline Wiring
- Connect all stages end to end
- Test the full flow with one file
- Then test with a folder of files

### Stage 7 — Hardening
- Error handling
- Skip logic (skip if `.srt` exists)
- Logging

### Stage 8 — Configuration
- Environment variables
- Model size toggle
- Input/output folder config

### Stage 9 — Production Packaging
- Write production Dockerfile
- Clean build from scratch
- Deploy to NUC

### Stage 10 — Real World Testing
- Test with actual media library
- Tune and fix what breaks

---

## Learning Approach

This is a learning project. The recommended approach for each stage:

1. **Concept first** — understand what the stage needs to do and why
2. **Write it yourself** — rough and broken is fine
3. **Run it** — errors are expected, that's where learning happens
4. **Review and debug** — bring it back for help understanding what went wrong
5. **Understand the fix** before moving on

Avoid copy-pasting code without understanding it. The goal is to finish with a working project *and* understanding of how it works.
