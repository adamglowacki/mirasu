"""Rotation algebra shared by every engine.

All rotations in this module are clockwise degrees, as seen by someone
looking at the displayed image/frame right-side up.
"""

from enum import IntEnum


class Rotation(IntEnum):
    NONE = 0
    CW90 = 90
    CW180 = 180
    CCW90 = 270  # i.e. 270 degrees clockwise

    def compose(self, other: "Rotation") -> "Rotation":
        """Rotation equivalent to applying ``self`` then ``other``, both clockwise."""
        return Rotation((int(self) + int(other)) % 360)


class Decision(IntEnum):
    """A single triage keystroke."""

    OK = 0
    ROTATE_CW = 1
    ROTATE_CCW = 2
    ROTATE_180 = 3

    def to_rotation(self) -> Rotation:
        return {
            Decision.OK: Rotation.NONE,
            Decision.ROTATE_CW: Rotation.CW90,
            Decision.ROTATE_CCW: Rotation.CCW90,
            Decision.ROTATE_180: Rotation.CW180,
        }[self]


# EXIF `Orientation` -> degrees clockwise needed to rotate the *stored*
# pixels to display correctly. Values 2, 4, 5, 7 involve a mirror and are
# intentionally unsupported in v1 (see design.md "Known limitations").
EXIF_ORIENTATION_TO_ROTATION = {
    1: Rotation.NONE,
    3: Rotation.CW180,
    6: Rotation.CW90,
    8: Rotation.CCW90,
}

MIRRORED_EXIF_ORIENTATIONS = {2, 4, 5, 7}


def effective_image_rotation(exif_orientation: int, decision: Decision) -> Rotation:
    """The single physical rotation to apply to raw stored pixels.

    Combines whatever the existing EXIF tag says the raw pixels need to
    display correctly with the user's additional triage decision, since the
    user made their decision looking at an already tag-corrected preview.
    """
    tag_rotation = EXIF_ORIENTATION_TO_ROTATION.get(exif_orientation, Rotation.NONE)
    return tag_rotation.compose(decision.to_rotation())


def ffmpeg_transpose_filter(rotation: Rotation) -> str | None:
    """ffmpeg ``-vf`` filter string implementing a clockwise rotation.

    Returns None for Rotation.NONE (no filter needed).
    """
    if rotation is Rotation.NONE:
        return None
    if rotation is Rotation.CW90:
        return "transpose=1"
    if rotation is Rotation.CW180:
        return "transpose=1,transpose=1"
    if rotation is Rotation.CCW90:
        return "transpose=2"
    raise ValueError(f"Unhandled rotation: {rotation!r}")
