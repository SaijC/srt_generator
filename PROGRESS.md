# Progress

Running log of where the project is, what was learned, and what's next.
Update this at the end of each session.

---

## Status

| Stage | Description | Status |
|---|---|---|
| 1 | Project setup & dev container | ✅ Complete |
| 2 | Folder scanner | ✅ Complete |
| 3 | Audio extraction | ⬜ Next |
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

## Stage 2 — Folder Scanner ✅

**Completed:** 18 August 2026

**Goal:** scan a folder for media files, log what it finds, handle the
edge cases.

### What was built

`src/media_collector.py` — a `MediaCollector` class:

```python
class MediaCollector:
    def __init__(self):
        self.media_files = []

    def collect_media_files(self, directory):
        self.media_files.clear()

        if not os.path.isdir(directory):
            logging.error(f"{directory} does not exist or is not a directory.")
            return

        for root, _, files in os.walk(
            directory,
            onerror=lambda e: logging.error(f"Error accessing {e.filename}: {e.strerror}")
        ):
            for file in files:
                file_extension = pathlib.Path(file).suffix
                if not file_extension:
                    continue
                if file_extension.lower() not in MEDIA_TYPES:
                    continue
                file_path = os.path.join(root, file)
                self.media_files.append(file_path)

    @property
    def get_media_files(self):
        return self.media_files
```

- Recursive scan via `os.walk`, extension match case-insensitive against
  `MEDIA_TYPES` (`src/const.py` — `{".avi", ".mp4", ".mkv"}`, pulled out
  so Stage 8 can make it configurable)
- Missing directory / not-a-directory → `logging.error`, early return,
  via a single `os.path.isdir` check
- Unreadable directory mid-walk → handled via `os.walk`'s `onerror`
  callback, logged with the offending path and reason, walk continues
- `__main__` block points at `/input` (the real devcontainer mount) and
  prints a numbered list, or logs "No media files found."

### Verified working

Ran against the real mounted library (`/input` → `d:/projects/movies`)
via `python -m src.media_collector` — correctly walked into nested
subfolders (e.g. `Beverly Hills Cop/`, `Sinners (2025)/`) and returned
only `.avi`/`.mp4`/`.mkv` files, numbered and printed.

### Lessons learned

**1. Relative imports need `-m`, not direct execution**

`media_collector.py` has `from .const import MEDIA_TYPES` — a relative
import, which only resolves when Python knows the file is part of the
`src` package. `python src/media_collector.py` fails with
`attempted relative import with no known parent package`; the fix is
`python -m src.media_collector` run from the project root, which is what
makes `src/__init__.py` matter.

**2. `os.walk` fails silently by default**

Both a nonexistent starting directory and an unreadable subdirectory
mid-walk produce *no exception* unless you opt in: check `os.path.exists`
before walking, and pass an `onerror` callback (invoked with the
`OSError`, exposing `.filename` and `.strerror`) to catch read failures
without aborting the whole scan.

**3. `str.rsplit('.', 1)[-1]` on an extensionless filename doesn't fail**

A filename with no dot at all (e.g. `README`) still returns the whole
filename from `rsplit` — there's nothing to split on. It falls through to
the `MEDIA_TYPES` check and gets excluded there instead, which is a
different code path than the explicit `if not file_extension` guard added
for filenames *ending* in a dot (e.g. `"file."` → `""`). Both are handled,
just via two different mechanisms — worth knowing which is doing what.
(Superseded by lesson 5 below — extension parsing later moved to
`pathlib.Path.suffix`, which changes this behaviour slightly since
`.suffix` on an extensionless name returns `""` directly rather than the
whole filename.)

**4. `logging` vs. `print` split: diagnostics vs. output**

Errors (missing/unreadable directory) go through `logging.error`;
`__main__`'s actual result reporting (the numbered file list) stays on
`print`. Diagnostics vs. requested output being different channels is a
reasonable split, not an inconsistency.

**5. `pathlib.Path.suffix` includes the leading dot — `rsplit` doesn't**

Switching extension parsing from `file.rsplit('.', 1)[-1]` to
`pathlib.Path(file).suffix` looks like a pure readability swap but isn't:
`Path("movie.mp4").suffix` returns `".mp4"`, dot included, while the old
`rsplit` approach returned `"mp4"`. `MEDIA_TYPES` was written for the
dot-less form, so after the switch every real file silently failed the
`in MEDIA_TYPES` check — the scanner ran without error and just reported
zero files found. Fixed by updating `MEDIA_TYPES` in `const.py` to
`{".avi", ".mp4", ".mkv"}` to match what `.suffix` actually returns.
Caught by re-running against the real `/input` library rather than
trusting the code by inspection — a good example of why the "run it and
see" step in the Learning Approach matters even for a change that looks
harmless.

**6. `os.path.isdir()` subsumes `os.path.exists()`**

`isdir()` returns `False` for a path that doesn't exist at all, not just
for one that exists but isn't a directory. `os.path.exists(directory) or
not os.path.isdir(directory)`-style double checks are redundant — a
single `isdir()` check covers both cases.

### Open items carried forward

| Item | Notes | When |
|---|---|---|
| `onerror` path untested | Hard to trigger a real permissions error inside a container running as root — logic reviewed but not exercised end to end. | Revisit if it matters later |

---

## Session log

| Date | Covered |
|---|---|
| 16 Aug 2026 | Stage 1 complete — Dockerfile, requirements, container verified |
| 17 Aug 2026 | Stage 2 started (WIP, off-record) — `MediaCollector` class scanning with `os.walk`, `MEDIA_TYPES` extracted to `const.py` |
| 18 Aug 2026 | Reviewed WIP Stage 2 code, brought PROGRESS.md up to date with what's actually in the repo |
| 18 Aug 2026 | Stage 2 complete — added missing-directory and unreadable-directory handling, switched to `logging`, fixed `/input` mount path, verified against real media library |
| 18 Aug 2026 | Post-completion cleanup — switched extension parsing to `pathlib.Path.suffix`, caught and fixed the dot-prefix mismatch this introduced in `MEDIA_TYPES`, collapsed redundant `exists`/`isdir` check |
