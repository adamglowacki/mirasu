# Orienta

Fast, keyboard-driven triage for photos and videos that need their
rotation physically fixed - not just tagged. See [design.md](design.md)
for the full design and the guarantees each format gets.

## Running

```
nix run . -- /path/to/photos
nix run . -- /path/to/photos --recursive
```

Or for development:

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
