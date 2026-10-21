"""
Gesture-controlled computer interface — Task Forge puzzle #185.

Live webcam feed -> MediaPipe Hands landmark tracking -> gesture
classification -> debounced OS mouse/scroll/volume control via pyautogui
(+ pycaw for real system volume on Windows, with an honest fallback).

Run:  python main.py [--config gesture_config.json]

Controls:
  g (configurable "toggle_key") — enable/disable gesture control
  q (configurable "exit_key")   — safe exit: releases any held mouse button,
                                   closes the webcam, destroys windows.

See README.md for the gesture list and the gesture_config.json schema.
"""
from __future__ import annotations

import argparse
import sys
import time

import cv2

from gesture_control.classifier import classify_gesture, PINCH, POINT, TWO_FINGER, THUMBS_UP, THUMBS_DOWN, FIST, OPEN_PALM
from gesture_control.config import load_config
from gesture_control.stability import StabilityTracker
from gesture_control.actions import ActionController
from gesture_control.volume_control import VolumeController


def get_screen_size() -> tuple[int, int]:
    try:
        import pyautogui

        return pyautogui.size()
    except Exception:
        return 1920, 1080


def landmarks_to_points(hand_landmarks) -> list[tuple[float, float, float]]:
    return [(lm.x, lm.y, lm.z) for lm in hand_landmarks.landmark]


def run(config_path: str) -> int:
    cfg = load_config(config_path)

    import pyautogui

    pyautogui.FAILSAFE = False  # we handle safe-exit via the 'q' key instead

    screen_w, screen_h = get_screen_size()

    cap = cv2.VideoCapture(cfg["camera_index"])
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, cfg["frame_width"])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg["frame_height"])

    if not cap.isOpened():
        print(
            "ERROR: could not open webcam (cv2.VideoCapture(%r).isOpened() == False). "
            "No camera hardware detected/accessible in this environment, or it's in use "
            "by another process. Exiting cleanly without crashing." % cfg["camera_index"],
            file=sys.stderr,
        )
        cap.release()
        return 1

    import mediapipe as mp

    mp_hands = mp.solutions.hands
    mp_drawing = mp.solutions.drawing_utils
    mp_styles = mp.solutions.drawing_styles

    hands = mp_hands.Hands(
        max_num_hands=cfg["max_hands"],
        min_detection_confidence=cfg["mediapipe"]["min_detection_confidence"],
        min_tracking_confidence=cfg["mediapipe"]["min_tracking_confidence"],
    )

    volume = VolumeController()
    print(f"Volume backend: {volume.backend}" + (f" (reason for fallback: {volume.error})" if volume.error else ""))

    action = ActionController(screen_w, screen_h, cfg)
    trackers: dict[int, StabilityTracker] = {}  # per-hand-slot debounce state

    control_enabled = True
    toggle_key = ord(cfg["toggle_key"])
    exit_key = ord(cfg["exit_key"])

    prev_time = time.time()
    fps = 0.0

    print("Gesture control running. Press 'g' to toggle control on/off, 'q' to exit safely.")

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("WARNING: frame grab failed, stopping.", file=sys.stderr)
                break

            frame = cv2.flip(frame, 1)  # mirror for natural control
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb)

            now = time.time()
            dt = now - prev_time
            prev_time = now
            if dt > 0:
                fps = 0.9 * fps + 0.1 * (1.0 / dt)

            active_labels = []

            if results.multi_hand_landmarks:
                for idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
                    mp_drawing.draw_landmarks(
                        frame,
                        hand_landmarks,
                        mp_hands.HAND_CONNECTIONS,
                        mp_styles.get_default_hand_landmarks_style(),
                        mp_styles.get_default_hand_connections_style(),
                    )

                    handedness_label = "Unknown"
                    if results.multi_handedness and idx < len(results.multi_handedness):
                        handedness_label = results.multi_handedness[idx].classification[0].label

                    points = landmarks_to_points(hand_landmarks)
                    raw_gesture = classify_gesture(
                        points,
                        pinch_threshold=cfg["pinch_threshold"],
                    )

                    tracker = trackers.setdefault(idx, StabilityTracker(cfg["debounce_frames"]))
                    result = tracker.update(raw_gesture)
                    confirmed = result.confirmed_gesture
                    active_labels.append(f"{handedness_label}:{confirmed or raw_gesture}")

                    if not control_enabled or confirmed is None:
                        if confirmed != PINCH:
                            action.release_any_held_button()
                        continue

                    index_tip = points[8]

                    if confirmed == POINT:
                        action.release_any_held_button()
                        action.reset_scroll()
                        action.move_cursor(index_tip[0], index_tip[1])

                    elif confirmed == PINCH:
                        action.move_cursor(index_tip[0], index_tip[1])
                        if not action.pinch_machine.active:
                            action.start_pinch()

                    elif confirmed == TWO_FINGER:
                        action.release_any_held_button()
                        middle_tip = points[12]
                        mid_y = (index_tip[1] + middle_tip[1]) / 2
                        action.scroll(mid_y)

                    elif confirmed == THUMBS_UP:
                        action.release_any_held_button()
                        action.reset_scroll()
                        if result.is_new_entry:
                            volume.volume_up(cfg["volume_step"])

                    elif confirmed == THUMBS_DOWN:
                        action.release_any_held_button()
                        action.reset_scroll()
                        if result.is_new_entry:
                            volume.volume_down(cfg["volume_step"])

                    elif confirmed in (FIST, OPEN_PALM):
                        # Neutral / idle states — deliberately no action.
                        action.release_any_held_button()
                        action.reset_scroll()

                    # If a pinch just ended (confirmed flipped away from PINCH
                    # while the mouse button is still logically down), release it.
                    if confirmed != PINCH and action.pinch_machine.active:
                        action.end_pinch()
            else:
                # No hand in frame at all — release anything held, for safety.
                action.release_any_held_button()
                trackers.clear()

            status = "ENABLED" if control_enabled else "DISABLED"
            overlay_lines = [
                f"Control: {status}  FPS: {fps:4.1f}",
                "Gestures: " + (", ".join(active_labels) if active_labels else "none"),
                f"Last pinch event: {action.pinch_machine.last_event or '-'}",
                "[g] toggle  [q] safe exit",
            ]
            y = 25
            for line in overlay_lines:
                cv2.putText(frame, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                y += 25

            cv2.imshow("Gesture Control Interface", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == toggle_key:
                control_enabled = not control_enabled
                if not control_enabled:
                    action.release_any_held_button()
            elif key == exit_key:
                break

    finally:
        action.release_any_held_button()
        hands.close()
        cap.release()
        cv2.destroyAllWindows()
        print("Shut down cleanly.")

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gesture-controlled computer interface")
    parser.add_argument("--config", default="gesture_config.json")
    args = parser.parse_args()
    sys.exit(run(args.config))
