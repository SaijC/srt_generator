# Progress

Running log of where the project is, what was learned, and what's next.
Update this at the end of each session.

---

## Status

| Stage | Description | Status |
|---|---|---|
| 1 | Project setup & dev container | ✅ Complete |
| 2 | Folder scanner | 🟡 In progress |
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

### Session 2 — 17 August 2026

`src/media_collector.py` + `src/const.py`. Walks a folder with `os.walk`,
filters by extension, collects full paths.

**Working:** finds all 10 films in the real test library. Correctly ignores
`.nfo`, `.jpg`, `.png`, `Thumbs.db`, a uTorrent `.dat` part-file, and an
empty release folder.

**Free win:** `os.walk` puts directories in the second tuple element, so a
folder named `dir.mp4` is never mistaken for a file. `Path.glob` would have
needed an explicit `.is_file()` check.

#### Fixed this session

| Bug | Cause |
|---|---|
| Always printed `0` | `collect_media_files()` was never called — the property returned the empty list from `__init__` |
| `const.py` raised `TypeError` | `set("avi","mp4","mkv")` — `set()` takes one iterable. Never fired, because the constant was duplicated in `media_collector.py` and `const` was never imported |
| Results accumulated across calls | `.clear()` at the top of the method |
| Module ran on import | Wrapped the entry point in `if __name__ == "__main__":` |
| `from const import ...` | Implicit relative import — broke under `-m` and under `import src.media_collector`. Now `from .const import ...` |

#### Lessons learned

**1. `import x` means "search a list of folders", not "the file next to me"**

The list is `sys.path`, and its first entry depends on how you launched:

| Command | `sys.path[0]` | `__package__` |
|---|---|---|
| `python3 src/media_collector.py` | `.../src` | `None` |
| `python3 -m src.media_collector` | `.../` (cwd) | `'src'` |

A leading dot (`from .const`) resolves against `__package__`, not `sys.path` —
so it points at the sibling file regardless of launch method. Script mode has
no package, hence *"attempted relative import with no known parent package."*

Cost: the file can no longer be run directly. **Entry point is now
`python3 -m src.media_collector`**, and it must be run from the project root.

Never fix this with `sys.path.append()` — it mutates global state as an import
side effect and hides the real decision.

**2. Relative paths mean "relative to wherever I'm standing"**

`"./input/movies"` worked from the project root and returned `0 []` from
`src/`. In production nobody types `cd` first — cwd is whatever `WORKDIR`
says (`/app`), so the scanner would find nothing, forever.

Same shape as the import bug, two lines apart: code that works because of
where you happened to be standing.

**3. `--mount` fails loud, `-v` fails silent**

| Nonexistent source | Behaviour |
|---|---|
| `-v` / `--volume` | silently creates an empty directory |
| `--mount type=bind` | errors, container refuses to start |

`devcontainer.json` `mounts` uses `--mount` semantics. A typo'd mount that
silently produced an empty `/input` would look identical to "no media files"
— you'd debug the scanner instead of the config. Third instance of the
Stage 1 `pip install ffmpeg` lesson.

Also: mount strings are `key=value` pairs split on commas. `", target=..."`
makes the key `" target"` — no trimming. **No spaces.**

**4. Editor green ≠ runtime green**

`.vscode/settings.json` had `"python.analysis.extraPaths": ["./src"]`, which
tells Pylance to search a folder Python doesn't. The broken
`from const import ...` showed no squiggle while failing at runtime. Removed.

**5. Stale `.git/index.lock`**

A rebuild killed git mid-commit; the lock survived and blocked every
subsequent write. `rm -f .git/index.lock` after confirming nothing is running.

#### Real test data changed the picture

15GB library, gitignored via `input/*`. What it exposed that a toy folder
couldn't:

- **9 of 10 films already have a `.srt`** — only *Sinners (2025)* doesn't.
  Running the finished pipeline today would re-transcribe 9 files for nothing.
  Stage 7 skip logic is now concrete, not theoretical.
- **`~uTorrentPartFile_650BD82C.dat`** — a partial download. Harmless because
  `.dat` isn't in the set, but had it been named `.mkv`, ffmpeg would have been
  handed a truncated file. Stage 7 material.
- **Nothing in the sample has an uppercase extension**, so the case bug stays
  invisible against this data. Rename one to `.MKV` to prove it.

#### Carried into next session

| Item | Note |
|---|---|
| `"./input/movies"` | Read `INPUT_FOLDER` from env, default `/input`. Decide `os.environ[...]` (KeyError, loud) vs `os.getenv(..., default)` (silent fallback). Default belongs in `const.py` |
| Verify the mount | `ls /input` inside the container. Ten films = live. Empty = mounted a real-but-wrong folder, which `--mount` won't catch |
| Case sensitivity | `.MKV` still invisible |
| `rsplit('.', 1)[-1]` | Returns the whole string when there's no dot — a file named `mp4` matches. `Path(f).suffix` returns `''` instead, and gives `.stem` for Stage 5 |
| Missing folder | `os.walk` returns `[]` with no exception. Same for a path that's a file. Check before walking |
| `print` → `logging` | Stage 7 wants it; doing it now avoids editing every call site twice |
| `@property get_media_files` | Two idioms at once. Consider returning a list from the method instead — no state to go stale, no call-order requirement |
| 15GB in `input/movies` | Redundant once `/input` is mounted from the real library. Confirm it's a copy before deleting |
| `readonly` on the mount | Stage 5 writes `.srt` alongside source media, so read-only would block it. Decide where subtitles go |

**The through-line:** the scanner still can't tell *"no media files"* apart
from *"you pointed me somewhere wrong."* The bottom half of that table is all
one job.

---

## Session log

| Date | Covered |
|---|---|
| 16 Aug 2026 | Stage 1 complete — Dockerfile, requirements, container verified |
| 17 Aug 2026 | Stage 2 in progress — scanner working on real data; imports, packaging and mounts sorted; path/edge-case handling outstanding |
