"""
Zoom Magnifier Module
=====================
Renders a circular loupe (magnifying glass) over the slide,
centred on the hand cursor.  Same non-destructive overlay
pattern as SpotlightController — just import and call apply().

Usage
-----
    from presentation_app.zoom_module import ZoomMagnifier

    zoom = ZoomMagnifier(zoom_factor=2.5, radius=160)
    zoom.toggle()                     # on / off
    output = zoom.apply(slide, cx, cy)  # returns annotated frame
"""

from __future__ import annotations
import numpy as np
import cv2

# ── Pre-built circle mask cache (avoid recomputing each frame) ─────────────
_mask_cache: dict[int, np.ndarray] = {}

def _circle_mask(radius: int) -> np.ndarray:
    if radius not in _mask_cache:
        d = radius * 2
        mask = np.zeros((d, d), dtype=np.uint8)
        cv2.circle(mask, (radius, radius), radius - 2, 255, -1)
        _mask_cache[radius] = mask
    return _mask_cache[radius]


class ZoomMagnifier:
    """
    Parameters
    ----------
    zoom_factor : float  — how much to magnify (2.0 = 2×, 3.0 = 3×)
    radius      : int    — pixel radius of the loupe circle on screen
    border_color: BGR tuple
    border_thickness: int
    """

    def __init__(
        self,
        zoom_factor: float = 2.5,
        radius: int = 160,
        border_color: tuple = (255, 255, 255),
        border_thickness: int = 3,
    ):
        self.zoom_factor      = float(zoom_factor)
        self.radius           = int(radius)
        self.border_color     = border_color
        self.border_thickness = border_thickness
        self._active          = False

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def is_active(self) -> bool:
        return self._active

    def toggle(self):
        self._active = not self._active

    def apply(self, slide: np.ndarray, cx: int, cy: int) -> np.ndarray:
        """
        Return a copy of *slide* with the magnifier loupe drawn at (cx, cy).
        If inactive, returns *slide* unchanged (zero-copy).
        """
        if not self._active:
            return slide

        h, w = slide.shape[:2]
        r = self.radius

        # ── Source region in the original slide ───────────────────────────────
        src_half = int(r / self.zoom_factor)   # half-size of source patch
        src_x1 = cx - src_half
        src_y1 = cy - src_half
        src_x2 = cx + src_half
        src_y2 = cy + src_half

        # Clamp source to slide bounds
        src_x1c = max(0, src_x1)
        src_y1c = max(0, src_y1)
        src_x2c = min(w, src_x2)
        src_y2c = min(h, src_y2)

        if src_x2c <= src_x1c or src_y2c <= src_y1c:
            return slide   # cursor out of bounds entirely

        patch = slide[src_y1c:src_y2c, src_x1c:src_x2c]

        # Pad patch if cursor is near the edge so the loupe circle stays full
        pad_left  = src_x1c - src_x1
        pad_top   = src_y1c - src_y1
        pad_right = src_x2 - src_x2c
        pad_bot   = src_y2 - src_y2c
        if any(p > 0 for p in (pad_left, pad_top, pad_right, pad_bot)):
            patch = cv2.copyMakeBorder(
                patch, pad_top, pad_bot, pad_left, pad_right,
                cv2.BORDER_REFLECT_101
            )

        # ── Scale patch up to loupe diameter ─────────────────────────────────
        d = r * 2
        zoomed = cv2.resize(patch, (d, d), interpolation=cv2.INTER_LINEAR)

        # ── Destination region on the output slide ────────────────────────────
        dst_x1 = cx - r
        dst_y1 = cy - r
        dst_x2 = cx + r
        dst_y2 = cy + r

        # Clamp destination
        dx1c = max(0, dst_x1)
        dy1c = max(0, dst_y1)
        dx2c = min(w, dst_x2)
        dy2c = min(h, dst_y2)

        if dx2c <= dx1c or dy2c <= dy1c:
            return slide

        # Corresponding slice inside the zoomed patch
        zx1 = dx1c - dst_x1
        zy1 = dy1c - dst_y1
        zx2 = zx1 + (dx2c - dx1c)
        zy2 = zy1 + (dy2c - dy1c)

        # ── Circular mask blend ───────────────────────────────────────────────
        mask_full = _circle_mask(r)
        mask_crop = mask_full[zy1:zy2, zx1:zx2]
        zoomed_crop = zoomed[zy1:zy2, zx1:zx2]

        out = slide.copy()
        roi = out[dy1c:dy2c, dx1c:dx2c]

        alpha = mask_crop[:, :, np.newaxis].astype(np.float32) / 255.0
        roi[:] = (zoomed_crop * alpha + roi * (1 - alpha)).astype(np.uint8)

        # ── Border ring ───────────────────────────────────────────────────────
        cv2.circle(out, (cx, cy), r, self.border_color, self.border_thickness, cv2.LINE_AA)

        # ── Small crosshair at loupe centre ───────────────────────────────────
        ch = 12
        cv2.line(out, (cx - ch, cy), (cx + ch, cy), self.border_color, 1, cv2.LINE_AA)
        cv2.line(out, (cx, cy - ch), (cx, cy + ch), self.border_color, 1, cv2.LINE_AA)

        return out
