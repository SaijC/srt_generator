# SRT Generator — working notes for Claude

## Read first

- `README.md` — project goal, pipeline, design decisions, hardware, and the stage-by-stage curriculum
- `PROGRESS.md` — current stage, what's been built, lessons learned, open items carried forward

Read both at the start of every session before suggesting anything. The current
stage is whichever row is marked **Next** in the PROGRESS.md status table.

## This is a learning project — how to help

The goal is that I finish understanding the code, not just possessing it.
Follow the Learning Approach section in `README.md`:

- **Do not write the stage implementation for me.** Not even as "a starting
  point to react to." If I ask for the code outright, ask me to attempt it first.
- **Concept before code.** When a stage starts, explain what it needs to do and
  what the real design choices are — then stop and let me write it.
- **When I bring you broken code**, explain *why* it broke before offering a
  fix, and prefer pointing at the line over rewriting the file.
- **Answer direct questions directly.** "What's the difference between `os.walk`
  and `pathlib.Path.glob`?" is a question, not a request for my folder scanner.
- Exception: scaffolding I'm not trying to learn — a test fixture, a one-off
  shell command, boilerplate I've already covered — is fine to write outright.

## Environment

- **Dev machine:** Windows 11, x86_64, NVIDIA GPU (CUDA). Code runs inside the
  VS Code dev container defined in `.devcontainer/`.
- **Target device:** CPU-only mini PC (Ryzen 7 5825U, ~14GB free RAM). Anything
  that only works with CUDA is a bug, not a feature. GPU is an optimisation,
  never a requirement.
- VS Code bind-mounts the source at `/workspaces/srt_generator`, which overrides
  the Dockerfile's `WORKDIR /app`.
- The build context is `.devcontainer/`, so `src/` cannot be `COPY`ed into the
  image. This is intentional for a dev container — the source is bind-mounted
  at runtime instead.
- Verify a rebuild **by behaviour, not by path**: `whisper.available_models()`,
  not `whisper.__file__`. An unrelated package named `whisper` exists on PyPI
  (Graphite's time-series library) and installs a module of the same name.

## Conventions

- Pin Python dependencies with `==` in `.devcontainer/requirements.txt`.
- System programs go in `apt-get` (ffmpeg, git); Python libraries go in
  `requirements.txt`. Don't mix them up.
- Create and delete within a single `RUN` layer — a later `rm` does not shrink
  the image.
- **No new dependencies without discussing it first.** Whisper's `--task
  translate` is deliberately doing the job a separate translation library
  would; adding one would be a design change, not a convenience.

## End of session

Update `PROGRESS.md`: set the stage status in the table, record what was built,
append any lessons learned and open items carried forward, and add a row to the
session log. Keep the existing table formats.
