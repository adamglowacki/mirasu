# Girasol — Design Document

## Problem

Photos and videos captured on different cameras often end up with the wrong
orientation. Some devices never rotate pixels at all; some rotate photos but
not video; some "rotate" by writing an orientation flag (EXIF `Orientation`,
or an MP4/MOV display-matrix `rotate` tag) that only cooperating viewers
honor, leaving the pixels themselves untouched.

Girasol lets you triage a directory of files with a single keystroke per
file (OK / rotate 90° CW / rotate 90° CCW / rotate 180°), then bakes the
rotation into the actual pixel data — not just a tag — without introducing
quality loss or audio/video desync, and without touching your originals
until the result is verified.

## Scope (v1)

- **Photos:** JPEG, HEIC/HEIF
- **Video:** MP4, MOV
- Flat or recursive directory scan.
- Single-machine, single-user, interactive GTK4/libadwaita desktop app on
  NixOS.

Explicitly out of scope for v1: mirroring/flipping, arbitrary angles,
batch-import from cameras/cards, cloud sync.

## Workflow

### Phase 1 — Triage

1. Pick a directory (optionally recursive).
2. Girasol scans every supported file, reads any *existing* orientation
   signal (EXIF `Orientation` for JPEG/HEIC, the QuickTime/ISOBMFF display
   matrix `rotate` tag for MP4/MOV via `ffprobe`), and renders a preview
   **already corrected for that existing tag** — so what you see is what a
   correct player/viewer would currently show you. That's the thing you're
   actually judging.
3. One file is shown at a time, large preview + a sidebar list of every file
   with a status icon. Keys apply a decision and immediately advance:

   | Key | Action |
   |---|---|
   | `→` | Rotate 90° clockwise |
   | `←` | Rotate 90° counter-clockwise |
   | `↓` | Rotate 180° |
   | `↑` / `Space` | OK — no change |
   | `Backspace` | Go back one file (re-decide) |
   | `.` | Skip — revisit later |

4. Every decision is persisted immediately to a local SQLite state database
   keyed by `(absolute path, size, mtime)`, so the session survives a quit
   and a directory that's already fully triaged won't be re-asked.
5. At the end, a summary screen shows counts per decision before anything is
   written to disk. You explicitly confirm to start Phase 2.

### Phase 2 — Processing

- A file is a true no-op only if there's *nothing left to bake in*: marked
  OK **and** no existing orientation tag. That's the common case and those
  files are left completely untouched.
- A file marked OK that still carries an existing EXIF/display-matrix
  rotation tag is **not** a no-op — the whole point of Girasol is that a
  tag-only rotation isn't good enough, so even an "already looks right"
  file gets reprocessed to bake that tag's rotation into real pixels and
  drop the tag.
- Every other file (rotate-marked, or OK-but-tagged) is processed by a
  format-specific engine (below) into a **new** output file, written next
  to the original.
- The output is verified (dimensions, duration, frame count, presence of an
  audio stream, as applicable) before anything happens to the original.
- Only after verification: the original is moved into a
  `.girasol-originals/` backup folder inside the same directory, and the new
  file takes the original's name. If verification fails, the original is
  left alone and the file is flagged for inspection — nothing is silently
  overwritten.
- A progress screen shows per-file status and a running log. You delete the
  `.girasol-originals/` backups yourself once you're satisfied with the
  results — Girasol never deletes them automatically.

## Rotation engines

The guarantee in every case: the *only* change to pixel data is the exact
90°/180°/270° permutation you asked for. No resampling, no recompression
artifacts beyond what's noted below.

### JPEG

`jpegtran` performs the rotation losslessly on the DCT coefficients — the
image is never fully decoded and re-encoded, so it is **bit-exact** aside
from one unavoidable caveat: if a dimension isn't a multiple of the JPEG
MCU size (8 or 16px depending on subsampling), a sliver of edge pixels is
trimmed (equivalent to `jpegtran -trim`) since there's no lossless way to
rotate a partial block. This never affects compression quality elsewhere in
the image.

After rotation:
- `exiftool` resets `Orientation` to `1` (pixels are now physically
  correct; a stale tag would cause double-rotation in viewers that honor it).
- Any embedded EXIF thumbnail/preview image is stripped rather than rotated.
  Rotating it correctly is possible but adds real complexity for a part of
  the file that's cosmetic (most viewers and file managers regenerate
  thumbnails on demand) — a missing thumbnail is a strictly better outcome
  than a stale, wrongly-oriented one.

### HEIC/HEIF

There is no bitstream-level lossless rotation trick for HEIF the way
`jpegtran` has for JPEG. The engine decodes via `pillow-heif` (libheif
bindings), applies an exact in-memory pixel transpose (the same lossless
operation PIL uses — no interpolation, since it's a 90°/180° permutation),
and re-encodes through libheif at maximum quality.

This is **not bit-exact** — flagged explicitly in the UI as "near-lossless"
vs. JPEG's "bit-exact" — because it's one generation of HEIC re-encode.
In practice, at max quality this is visually indistinguishable, but it's an
honest distinction worth preserving in the UI rather than overclaiming.
`Orientation` is reset the same way as for JPEG.

### MP4 / MOV

Both are ISO-BMFF/QuickTime family containers; `ffprobe`/`ffmpeg` handle
their rotation metadata identically, so there's a single video engine with
codec-aware parameters (H.264 → `libx264`, H.265 → `libx265`).

```
ffmpeg -i in.mp4 -map 0 -c:a copy -c:s copy \
       -vf "<composed transpose/flip>" \
       -c:v <same family as source> -crf <visually-lossless> -preset slow \
       -metadata:s:v:0 rotate=0 \
       out.mp4
```

Key points:
- **Audio/subtitles are always stream-copied** (`-c:a copy -c:s copy`),
  never re-encoded. Only the video stream's pixels change, so presentation
  timestamps stay aligned to the same timebase — sync is preserved by
  construction, not by after-the-fact correction.
- If the source already carries a rotation matrix/`rotate` tag, that part is
  deliberately **not** hand-computed: ffmpeg's demuxer auto-applies a
  stream's display-matrix rotation whenever a filtergraph is in use (its
  `-autorotate` behavior, on by default). The engine only adds its own
  `transpose` filter for your marked decision on top of that, so the tag's
  rotation and your decision are still baked in together in a **single**
  ffmpeg pass — it just avoids reimplementing ffmpeg's own
  (notoriously sign-ambiguous) display-matrix math, reusing well-tested
  code instead of a hand-rolled equivalent.
- Quality target is "visually lossless, size-preserving" (per your
  decision): CRF tuned per codec family (x264 ≈ 16, x265 ≈ 18 by default,
  configurable) rather than mathematically-lossless mode, to keep output
  file size and encode time close to the source instead of the 3–10×
  blow-up a bit-exact lossless encode would cost.
- Any leftover rotation tag is explicitly zeroed on output so a tag-honoring
  player never double-rotates an already-baked-in result.

## Composing existing tags with your decision

For every file, Girasol computes:

```
effective_rotation = existing_tag_rotation ⊕ your_marked_rotation
```

(`⊕` = composition of rotations mod 360°, in the group {0°, 90°, 180°,
270°}). This is the single transform actually applied, and it's why the
preview shown during triage is pre-corrected for the existing tag — you're
always marking relative to what's visually wrong, never having to mentally
account for a tag you can't see.

## Persistence / state

- SQLite database at `~/.local/state/girasol/girasol.db`.
- Row key: `(absolute_path, size, mtime)` — so edits to a file between scans
  invalidate its cached decision rather than silently reusing a stale one.
- Per-run log file under `~/.local/state/girasol/logs/`.

## Architecture

The app is split into a GTK-free **core** (scanning, metadata reading,
rotation composition, the three engines, verification, the SQLite state
layer) and a thin **UI** layer (GTK4/libadwaita) that only handles
rendering and key-to-decision mapping, delegating everything else to core.
This is what makes the core exhaustively unit- and integration-testable
without needing to drive the GUI event loop.

```
girasol/
  core/
    db.py          SQLite state (decisions, resumability)
    scanner.py      directory walk, file classification
    metadata.py     exiftool/ffprobe wrappers for existing orientation tags
    rotation.py     Rotation enum + composition (⊕) logic
    engines/
      jpeg.py       jpegtran + exiftool pipeline
      heic.py       pillow-heif pipeline
      video.py      ffmpeg command construction + execution
    pipeline.py     orchestration: engine dispatch, verification, promote/backup
  ui/
    app.py          Adw.Application
    triage_window.py
    process_window.py
    preview.py      thumbnail / video-frame generation + caching
  main.py
```

## Packaging

Everything ships as a Nix flake (`flake.nix`) with pinned runtime
dependencies (`ffmpeg`, `libjpeg` for `jpegtran`, `exiftool`, `libheif`,
`pillow-heif`, `gtk4`, `libadwaita`, `pygobject3`). `nix run` or a
home-manager install gets you a fully reproducible environment — no
system Python/pip drift, which is the main thing that makes this
"flawless on NixOS" rather than "works on the machine I built it on."

## Testing strategy

- **Unit tests** for rotation composition, metadata parsing, scanner
  classification, and SQLite state — fast, no subprocesses.
- **Integration tests** that generate real sample media on the fly
  (a JPEG via Pillow, an MP4/MOV via `ffmpeg`, a HEIC via `pillow-heif`/
  `heif-enc`) with a deliberately asymmetric test pattern, run each engine
  against it, and assert the output's pixels/frames match an
  independently-computed rotation of the input — not just that the process
  exited 0.
- **Pipeline tests** covering the verify → promote/backup → failure-leaves-
  original-untouched paths.
- **GUI smoke test** launching the real `Adw.Application` under a headless
  X server (`xvfb-run`) to confirm the window and widget tree construct
  without error on this exact dependency set, since GTK/GI version
  mismatches are the most likely source of "works in theory, crashes on
  this machine."

## Known limitations (v1)

- HEIC rotation is near-lossless, not bit-exact (no equivalent of
  `jpegtran`'s coefficient-level trick exists for HEIF).
- JPEG dimensions not divisible by the MCU size lose a sliver of edge
  pixels on rotation (standard `jpegtran -trim` behavior).
- Embedded JPEG thumbnails/previews are stripped, not rotated.
- Flip/mirror and arbitrary-angle rotation are not supported.
