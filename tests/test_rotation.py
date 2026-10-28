from orienta.core.rotation import (
    Decision,
    Rotation,
    effective_image_rotation,
    ffmpeg_transpose_filter,
)


def test_compose_identity():
    assert Rotation.NONE.compose(Rotation.NONE) == Rotation.NONE
    assert Rotation.CW90.compose(Rotation.NONE) == Rotation.CW90


def test_compose_wraps_mod_360():
    assert Rotation.CW90.compose(Rotation.CW180) == Rotation.CCW90
    assert Rotation.CW180.compose(Rotation.CW180) == Rotation.NONE
    assert Rotation.CCW90.compose(Rotation.CW90) == Rotation.NONE


def test_decision_to_rotation():
    assert Decision.OK.to_rotation() == Rotation.NONE
    assert Decision.ROTATE_CW.to_rotation() == Rotation.CW90
    assert Decision.ROTATE_CCW.to_rotation() == Rotation.CCW90
    assert Decision.ROTATE_180.to_rotation() == Rotation.CW180


def test_effective_image_rotation_no_tag_ok():
    assert effective_image_rotation(1, Decision.OK) == Rotation.NONE


def test_effective_image_rotation_no_tag_with_decision():
    assert effective_image_rotation(1, Decision.ROTATE_CW) == Rotation.CW90
    assert effective_image_rotation(1, Decision.ROTATE_CCW) == Rotation.CCW90
    assert effective_image_rotation(1, Decision.ROTATE_180) == Rotation.CW180


def test_effective_image_rotation_composes_with_existing_tag():
    # Orientation 6 => stored pixels need 90 CW to look right already.
    # User additionally marks ROTATE_CW => total physical rotation 180.
    assert effective_image_rotation(6, Decision.ROTATE_CW) == Rotation.CW180
    # Orientation 8 => stored pixels need 270 CW (90 CCW).
    # User marks OK (preview already looked correct) => apply exactly the tag's rotation.
    assert effective_image_rotation(8, Decision.OK) == Rotation.CCW90
    # Orientation 3 (180) + user marks ROTATE_180 again => net NONE (cancels out).
    assert effective_image_rotation(3, Decision.ROTATE_180) == Rotation.NONE


def test_effective_image_rotation_unknown_orientation_defaults_to_none_tag():
    # Mirrored orientations (2,4,5,7) aren't modeled; fall back to no tag rotation.
    assert effective_image_rotation(2, Decision.OK) == Rotation.NONE


def test_ffmpeg_transpose_filter():
    assert ffmpeg_transpose_filter(Rotation.NONE) is None
    assert ffmpeg_transpose_filter(Rotation.CW90) == "transpose=1"
    assert ffmpeg_transpose_filter(Rotation.CCW90) == "transpose=2"
    assert ffmpeg_transpose_filter(Rotation.CW180) == "transpose=1,transpose=1"
