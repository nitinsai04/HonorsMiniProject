"""
Presentation Engine — combined gesture control + spotlight.
Accepts arbitrary image paths and a settings dict from the launcher.
"""

import os
import sys
import cv2
import numpy as np

# Allow importing spotlight_module from the project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from spotlight_module import SpotlightController
from cvzone.HandTrackingModule import HandDetector


# ── Constants ────────────────────────────────────────────────────────────────
CAM_W, CAM_H = 1280, 720
SLIDE_W, SLIDE_H = 960, 540
BUTTON_DELAY = 20
PINCH_THRESHOLD = 40

# Landmark indices
THUMB, INDEX, MIDDLE, RING = 4, 8, 12, 16

# BGR colours
RED   = (0,   0,   255)
CYAN  = (200, 200,  0)
YELLOW = (0, 255, 255)
WHITE  = (255, 255, 255)
BLACK  = (0,   0,   0)


# ── Helper ───────────────────────────────────────────────────────────────────
def _pinch(lm, a, b):
    x1, y1 = lm[a][0], lm[a][1]
    x2, y2 = lm[b][0], lm[b][1]
    return ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5 < PINCH_THRESHOLD


def _map_to_slide(lm):
    """Map index-finger camera coords → slide pixel coords."""
    x = int(np.interp(lm[INDEX][0], [CAM_W // 2, CAM_W], [0, SLIDE_W]))
    y = int(np.interp(lm[INDEX][1], [150, CAM_H - 150], [0, SLIDE_H]))
    return x, y


def _draw_hud(slide, slide_idx, total, spotlight_active):
    """Overlay slide counter and spotlight badge."""
    # Slide counter — bottom left
    cv2.putText(slide, f"{slide_idx + 1} / {total}",
                (12, SLIDE_H - 12), cv2.FONT_HERSHEY_SIMPLEX,
                0.65, WHITE, 2, cv2.LINE_AA)
    # Spotlight badge — top left
    if spotlight_active:
        cv2.rectangle(slide, (8, 8), (165, 35), BLACK, -1)
        cv2.putText(slide, "SPOTLIGHT ON", (12, 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, YELLOW, 2, cv2.LINE_AA)


# ── Main entry point ─────────────────────────────────────────────────────────
def run_presentation(image_paths: list, settings: dict = None):
    """
    Run the gesture-controlled presentation.

    Parameters
    ----------
    image_paths : list of str
        Absolute paths to slide images in display order.
    settings : dict, optional
        Keys: spotlight_radius, dim_opacity, gesture_threshold,
              dimmed_brightness, hardware_dim
    """
    if settings is None:
        settings = {}

    gesture_threshold = settings.get("gesture_threshold", 300)
    spotlight_radius  = settings.get("spotlight_radius", 150)
    dim_opacity       = settings.get("dim_opacity", 0.7)
    dimmed_brightness = settings.get("dimmed_brightness", 0.3)
    hardware_dim      = settings.get("hardware_dim", True)

    # ── Load slides ──────────────────────────────────────────────────────────
    slides = []
    for path in image_paths:
        img = cv2.imread(path)
        if img is not None:
            slides.append(cv2.resize(img, (SLIDE_W, SLIDE_H)))
        else:
            print(f"[engine] Warning: could not load '{path}', skipping.")

    if not slides:
        print("[engine] No valid images — aborting.")
        return

    # ── Devices ──────────────────────────────────────────────────────────────
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  CAM_W)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_H)

    detector = HandDetector(detectionCon=0.7, maxHands=1)

    spotlight = SpotlightController(
        radius=spotlight_radius,
        dim_opacity=dim_opacity,
        hardware_dim_enabled=hardware_dim,
        dimmed_brightness=dimmed_brightness,
    )

    # ── State ────────────────────────────────────────────────────────────────
    slide_idx       = 0
    btn_pressed     = False
    btn_counter     = 0
    annotations     = [[]]
    ann_number      = 0
    ann_start       = False

    print(f"\n[engine] Loaded {len(slides)} slides.")
    print("Controls: Raise hand above yellow line → pinch to navigate/spotlight")
    print("          Index only=Draw  |  Index+Middle=Pointer  |  I+M+R=Erase")
    print("Keyboard: s=spotlight  h=hw-brightness  +/-=radius  [/]=dim  q=quit\n")

    # ── Main loop ────────────────────────────────────────────────────────────
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frame = cv2.flip(frame, 1)

        slide = slides[slide_idx].copy()

        hands, frame = detector.findHands(frame)
        cv2.line(frame, (0, gesture_threshold),
                 (CAM_W, gesture_threshold), YELLOW, 5)

        if hands and not btn_pressed:
            hand    = hands[0]
            lm      = hand["lmList"]
            fingers = detector.fingersUp(hand)
            cx, cy  = hand["center"]
            finger_pos = _map_to_slide(lm)

            # ── Above threshold: slide navigation + spotlight toggle ─────────
            if cy <= gesture_threshold:
                ann_start = False

                if _pinch(lm, THUMB, INDEX):          # ← Previous
                    if slide_idx > 0:
                        slide_idx -= 1
                        annotations = [[]]
                        ann_number  = 0
                        btn_pressed = True

                elif _pinch(lm, THUMB, MIDDLE):        # → Next
                    if slide_idx < len(slides) - 1:
                        slide_idx += 1
                        annotations = [[]]
                        ann_number  = 0
                        btn_pressed = True

                elif _pinch(lm, THUMB, RING):          # Spotlight
                    spotlight.toggle()
                    btn_pressed = True

            # ── Below threshold: pointer / draw / erase ─────────────────────
            elif fingers == [0, 1, 1, 0, 0]:          # Pointer
                if not spotlight.is_active:
                    cv2.circle(slide, finger_pos, 10, RED, cv2.FILLED)
                ann_start = False

            elif fingers == [0, 1, 0, 0, 0]:          # Draw
                if not spotlight.is_active:
                    if not ann_start:
                        ann_start   = True
                        ann_number += 1
                        annotations.append([])
                    annotations[ann_number].append(finger_pos)
                    cv2.circle(slide, finger_pos, 5, CYAN, cv2.FILLED)
            else:
                ann_start = False

            if fingers == [0, 1, 1, 1, 0]:            # Erase last stroke
                if ann_number >= 0:
                    annotations.pop(-1)
                    ann_number -= 1
                    btn_pressed = True

        # ── Debounce ─────────────────────────────────────────────────────────
        if btn_pressed:
            btn_counter += 1
            if btn_counter > BUTTON_DELAY:
                btn_counter = 0
                btn_pressed = False

        # ── Render annotations ───────────────────────────────────────────────
        for stroke in annotations:
            for j in range(1, len(stroke)):
                cv2.line(slide, stroke[j - 1], stroke[j], CYAN, 5)

        # ── Spotlight overlay ────────────────────────────────────────────────
        if spotlight.is_active and hands:
            lm = hands[0]["lmList"]
            sx = int(np.interp(lm[INDEX][0], [CAM_W // 2, CAM_W], [0, SLIDE_W]))
            sy = int(np.interp(lm[INDEX][1], [150, CAM_H - 150], [0, SLIDE_H]))
            sx = max(spotlight.radius, min(sx, SLIDE_W - spotlight.radius))
            sy = max(spotlight.radius, min(sy, SLIDE_H - spotlight.radius))
            slide = spotlight.create_overlay(slide, sx, sy)

        # ── HUD ──────────────────────────────────────────────────────────────
        _draw_hud(slide, slide_idx, len(slides), spotlight.is_active)

        # Webcam thumbnail — top-right corner
        thumb = cv2.resize(frame, (213, 120))
        slide[0:120, SLIDE_W - 213:SLIDE_W] = thumb

        cv2.imshow("Presentation", slide)
        cv2.imshow("Camera", frame)

        # ── Keyboard ─────────────────────────────────────────────────────────
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("s"):
            spotlight.toggle()
        elif key == ord("h"):
            spotlight.toggle_hardware_control()
        elif key in (ord("+"), ord("=")):
            spotlight.increase_radius()
        elif key in (ord("-"), ord("_")):
            spotlight.decrease_radius()
        elif key == ord("["):
            spotlight.decrease_dim()
        elif key == ord("]"):
            spotlight.increase_dim()

    # ── Cleanup ───────────────────────────────────────────────────────────────
    spotlight.cleanup()
    cap.release()
    cv2.destroyAllWindows()
