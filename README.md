# Orienta

Fast, keyboard-driven triage for photos and videos that need their
rotation physically fixed - not just tagged. See [design.md](design.md)
for the full design and the guarantees each format gets.

## Prerequisites

NixOS (or Nix with flakes enabled) is the only requirement — every other
dependency (ffmpeg, jpegtran, exiftool, libheif, GTK4, libadwaita,
PyGObject) is pinned in `flake.nix` and fetched automatically the first
time you run it. If `nix run`/`nix develop` complain about flakes being an
experimental feature, add this to your NixOS configuration (or
`~/.config/nix/nix.conf`) and rebuild/re-login:

```
nix.settings.experimental-features = [ "nix-command" "flakes" ];
```

## Running

From inside this directory (`/home/ai/qrocs`):

```
nix run . -- /path/to/photos
nix run . -- /path/to/photos --recursive   # include subdirectories
```

The first run will take a while as Nix builds/fetches the dependency
closure; subsequent runs are instant.

### Running from anywhere, without cloning first

```
nix run github:<your-username>/<your-repo> -- /path/to/photos
```

(only works once this directory is pushed to a git remote).

### Installing permanently (so `orienta` is just a command)

Add it to your NixOS system packages or home-manager config, e.g. in
`home.nix`:

```nix
home.packages = [
  (builtins.getFlake "/home/ai/qrocs").packages.${builtins.currentSystem}.default
];
```

then after `home-manager switch`, just run:

```
orienta /path/to/photos
```

### Development mode (editable source, for working on Orienta itself)

```
nix develop
python3 -m orienta.main /path/to/photos
```

## Triage keys

| Key | Action |
|---|---|
| `→` | Rotate 90° clockwise |
| `←` | Rotate 90° counter-clockwise |
| `↓` | Rotate 180° |
| `↑` / `Space` | OK — no additional rotation |
| `Backspace` | Go back one file |
| `.` | Skip — revisit later |

Decisions save continuously; quitting and reopening the same directory
resumes where you left off. After the last file, review the summary and
click **Start processing**.

Originals are moved into a `.orienta-originals/` folder next to them only
after the rotated output is verified - delete that folder yourself once
you're happy with the results.

## Testing

```
nix develop
python3 -m pytest tests/ -q                 # unit + integration tests
xvfb-run -a python3 tests/gui_smoke.py       # headless GUI smoke test
```
