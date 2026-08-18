# Progress

Running log of where the project is, what was learned, and what's next.
Update this at the end of each session.

---

## Status

| Stage | Description | Status |
|---|---|---|
| 1 | Project setup & dev container | ✅ Complete |
| 2 | Folder scanner | ⬜ Next |
| 3 | Audio extraction | ⬜ |
| 4 | Whisper integration | ⬜ |
| 5 | SRT writer | ⬜ |
| 6 | Pipeline wiring | ⬜ |
| 7 | Hardening | ⬜ |
| 8 | Configuration | ⬜ |
| 9 | Production packaging | ⬜ |
| 10 | Real world testing | ⬜ |

---

## Stage 1 — Project Setup ✅

**Completed:** 16 August 2026

### What was built

`.devcontainer/Dockerfile`

```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y ffmpeg --no-install-recommends \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt
```

`.devcontainer/requirements.txt`

```
openai-whisper==20250625
```

### Verified working

| Check | Result |
|---|---|
| `ffmpeg -version` | ffmpeg 7.1.5 |
| `import whisper` | resolves to `/usr/local/lib/python3.11/site-packages/whisper/` |
| `whisper.available_models()` | returns model list — confirms the *correct* whisper |

---

### Lessons learned

**1. pip and apt are different worlds**

- `apt-get` → system programs you run from a shell (`ffmpeg`, `git`)
- `pip` → Python libraries you `import` in code (`openai-whisper`, `torch`)

Test: will `main.py` say `import ffmpeg`? No — it shells out to the binary.
So ffmpeg belongs in apt, not `requirements.txt`.

Cost of getting this wrong: `pip install ffmpeg` *succeeds* (an abandoned
PyPI package of that name exists), installs something useless, and the build
goes green. Silent success is worse than a crash.

**2. Each `RUN` is an immutable layer**

A layer is a permanent snapshot. Deleting a file in a *later* `RUN` only
records a deletion on top — the data still ships inside the image.

```dockerfile
RUN apt-get install ...        # ← 40MB of lists baked in here, forever
RUN rm -rf /var/lib/apt/lists/*  # ← does not shrink the image
```

Rule: **create and delete within the same `RUN`**, chained with `&&`.

Security consequence for later: a secret copied in one layer and deleted in
the next is still fully recoverable from the image.

**3. Install name ≠ import name**

`pip install openai-whisper` → `import whisper`

Other examples: `pip install pillow` → `import PIL`;
`pip install beautifulsoup4` → `import bs4`. Never infer one from the other.

The trap here was real: a package named `whisper` exists on PyPI (v1.1.10) —
it's Graphite's time-series storage library. Installing it would have worked,
imported fine, and failed confusingly at Stage 4.

Verify before building: `pip index versions <name>`

**4. Verify by behaviour, not by path**

`whisper.__file__` tells you where a module came from, not what it is —
both the real and impostor packages install a module called `whisper`.
`whisper.available_models()` is the decisive test.

**5. Requirements are copied before the source code, deliberately**

Docker invalidates every layer after the first one that changed. `COPY . .`
before `pip install` would re-download ~2GB of torch on every edit to
`main.py`. Copying just `requirements.txt` first keeps the install cached.

**6. Build context is relative to `devcontainer.json`, not the Dockerfile**

No `build.context` is set, so the context defaults to `.devcontainer/`.
That's why `requirements.txt` lives there rather than in the project root.

Side effect: `src/` is *outside* the build context and cannot be `COPY`ed in.
Correct for a dev container — VS Code bind-mounts the source at runtime
instead, at `/workspaces/srt_generator`.

**7. Dockerfile grammar is one instruction per line**

`INSTRUCTION <arguments>`. `COPY` and `RUN` can never share a line.

**8. Version pinning uses `==`, not a dot**

`openai-whisper==20250625`. A dot is a legal character in a package name,
so `openai-whisper.20250625` is parsed as one name and fails to resolve.

OpenAI ships Whisper as date-stamped releases rather than semver.

---

### Open items carried forward

| Item | Notes | When |
|---|---|---|
| `runArgs: ["--gpus","all"]` | Removed for now. Hard requirement — blocks container *start* if Docker can't provide a GPU, with an error unrelated to your code. Never valid on the CPU-only target device. | Revisit Stage 4 |
| `BUILD_TARGET` build arg | Passed by `devcontainer.json` but no matching `ARG` in the Dockerfile — currently a no-op. Either wire it up or delete it. | Stage 4 / 9 |
| Whisper model cache | Models download to `~/.cache/whisper` inside the container and are lost on rebuild — ~1.5GB re-download each time. Fix with a `mounts` entry in `devcontainer.json`. | Before Stage 4 |
| `WORKDIR /app` vs `/workspaces/srt_generator` | VS Code bind-mounts and lands you in the latter, ignoring the Dockerfile `WORKDIR`. Harmless; align via `workspaceFolder` if it becomes confusing. | Optional |
| Running as root | Container runs as root, so files it creates are root-owned. Rarely bites on a Windows bind mount. | Note only |
| VS Code telemetry errors | `mobile.events.data.microsoft.com ... ECONNREFUSED` in the build log is blocked telemetry. Harmless noise. | Ignore |

---

## Stage 2 — Folder Scanner ⬜

**Goal:** scan a folder for media files, log what it finds, handle the
edge cases.

### To think about before writing

- Which extensions count as media? (`.mp4`, `.mkv`, `.avi`, `.mov`, ...)
  Where should that list live so Stage 8 can make it configurable?
- Recursive into subfolders, or top level only?
- Case sensitivity — `.MP4` vs `.mp4`. Linux filesystems care.
- Edge cases: folder empty, folder doesn't exist, no media files present,
  files present but unreadable.
- `os.listdir` vs `os.walk` vs `pathlib.Path.glob` — worth understanding
  the difference rather than picking the first one found.

### Definition of done

Point it at `input/`, get an accurate list of media files logged, and
have it fail gracefully on every edge case above.

---

## Session log

| Date | Covered |
|---|---|
| 16 Aug 2026 | Stage 1 complete — Dockerfile, requirements, container verified |
