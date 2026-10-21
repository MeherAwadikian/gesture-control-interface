# Gesture-Controlled Computer Interface

A local Python desktop application that uses your webcam and MediaPipe Hands
to recognize hand gestures in real time and drive the OS mouse cursor,
clicks, drag, scroll, and system volume — no mouse or keyboard needed while
it's active.

This is a desktop program, not a web app: it moves the real OS cursor and
changes real system volume, which a browser is sandboxed from doing. See
`web-demo/` for a browser-based companion (landmark-detection visualizer
only — explained below).

## Install

```
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
python main.py
```

First run writes `gesture_config.json` next to `main.py` if it doesn't
already exist, pre-filled with defaults — edit it, no restart logic needed
beyond relaunching.

## Controls

- `g` — toggle gesture control on/off (type normally without the cursor
  jumping while it's off; landmarks still draw, no OS actions fire)
- `q` — safe exit: releases any held mouse button, closes the webcam, and
  destroys the window cleanly

## Gestures implemented (7, 6 mapped to actions)

| Gesture | Shape | Action |
|---|---|---|
| POINT | index finger only extended | move OS cursor |
| PINCH (short) | thumb tip touches index tip, released quickly with little movement | click |
| PINCH (held + moved) | same pinch, held longer / moved further | click-and-drag (mouseDown on pinch-start, mouseUp on release — same mechanism a real mouse button uses to distinguish click vs drag) |
| TWO_FINGER | index + middle extended, moved vertically | scroll |
| THUMBS_UP | only thumb extended, pointing up | system volume up |
| THUMBS_DOWN | only thumb extended, pointing down | system volume down |
| FIST | all fingers curled | neutral/idle — deliberately does nothing, prevents accidental triggers |
| OPEN_PALM | all 5 fingers extended | detected and shown on the overlay, intentionally left unmapped (bonus gesture, no assigned action) |

Both hands are tracked independently (MediaPipe `multi_handedness`, up to
`max_hands` from config) — each hand gets its own debounce state, so e.g.
one hand can scroll while the other points, though cursor-move actions from
multiple hands will contend for the same OS cursor (last-processed hand
wins per frame; documented limitation, not a crash).

## Debounce (the puzzle's own clue)

Gesture state is tracked **across frames**, not decided from a single frame.
`gesture_control/stability.py`'s `StabilityTracker` only "confirms" a raw
classification after it has repeated for `debounce_frames` consecutive
frames (~0.2-0.4s at the frame rate this app actually gets), and separately
flags the single frame where a gesture newly becomes confirmed
(`is_new_entry`). Discrete actions (volume step) key off `is_new_entry` so
they fire once per gesture entry, not once per frame while held. Continuous
actions (cursor move, scroll, drag) key off "currently confirmed", which is
exactly what should re-run every frame while held.

## Cursor smoothing

`gesture_control/smoothing.py`'s `EMASmoother` exponentially smooths the
mapped screen position across frames (`smoothing_factor` in config) to cut
landmark jitter before it reaches `pyautogui.moveTo`.

## Coordinate mapping

`gesture_control/actions.py::map_normalized_to_screen` trims `frame_margin`
off each edge of the normalized camera frame and stretches the remaining
"active region" to the full screen, independently per axis — so frame vs.
screen aspect-ratio mismatch doesn't skew the mapping, and the hand doesn't
need to reach the camera's physical frame edges to hit screen corners.

## System volume: real Core Audio control, with an honest fallback

`gesture_control/volume_control.py`'s `VolumeController` tries `pycaw`
(Windows Core Audio Endpoint Volume API) first for real, direct volume
control — trying the modern `AudioUtilities.GetSpeakers().EndpointVolume`
property, then falling back to the older `Activate()`/`QueryInterface()`
pattern for older pycaw versions. If neither works, it falls back to
`pyautogui.press('volumeup'/'volumedown')` (simulated media keys) and
reports which backend is actually active via `VolumeController.backend` and
prints it at startup — it does not silently claim real control if it isn't
getting it. On this machine the real `pycaw` backend was confirmed working:
read the live system volume, lowered it, read it back, raised it back, and
confirmed it returned to the exact original level — a genuine Core Audio
round-trip, not a mock.

## `gesture_config.json` schema

```json
{
  "camera_index": 0,
  "frame_width": 640,
  "frame_height": 480,
  "max_hands": 2,
  "mediapipe": {
    "min_detection_confidence": 0.7,
    "min_tracking_confidence": 0.6
  },
  "frame_margin": 0.15,
  "smoothing_factor": 0.5,
  "debounce_frames": 6,
  "pinch_threshold": 0.045,
  "click_max_duration_sec": 0.3,
  "click_max_movement_px": 15,
  "scroll_sensitivity_px_per_tick": 40,
  "scroll_ticks_per_event": 2,
  "volume_step": 0.05,
  "toggle_key": "g",
  "exit_key": "q"
}
```

## Tests

```
pip install pytest
pytest tests/ -v
```

Unit tests cover the pure logic with synthetic landmark coordinates — no
camera, no display, no real mouse/volume calls: gesture classification
(`test_classifier.py`), EMA smoothing (`test_smoothing.py`), debounce/
stability (`test_stability.py`), config loading (`test_config.py`), and the
coordinate-mapping + click-vs-drag + scroll state machines
(`test_actions.py`).

## Verification notes (read this before assuming more was tested)

This was built and verified in a sandboxed environment with no physical
hand available to perform gestures. What was actually confirmed, honestly:

- All 34 pure-logic unit tests **pass with real assertions** against
  synthetic landmark data (classifier, smoothing, debounce/stability,
  config loading, cursor mapping, click-vs-drag and scroll state machines)
  — none of them require a camera.
- This sandbox turned out to have an actual accessible camera device, so
  more was verifiable than typical: `cv2.VideoCapture(0).isOpened()`
  returns `True` here, and `scripts/camera_smoke_test.py` ran 30 real
  frames through the real MediaPipe Hands pipeline end-to-end (capture ->
  flip -> color convert -> inference) at ~10fps without crashing. It
  reported 0 hand detections across those 30 frames, which is expected and
  honest — there is no physical hand in front of whatever this
  environment's camera actually is, not a sign of a broken pipeline.
- `main.py` itself still checks `cap.isOpened()` before entering the main
  loop and exits with a clear error message rather than crashing if a
  camera genuinely isn't available — that path was also code-reviewed.
- System volume control was verified for real, not mocked: read the live
  Windows system volume via `pycaw`, lowered it by a small step, read it
  back, raised it back, and confirmed it returned to the exact original
  level.
- What was **not** and could not be verified here: the actual gesture
  classifications firing against a real moving hand (POINT/PINCH/scroll/
  thumbs-up-down/fist), and the resulting real cursor movement, click,
  drag, and scroll side effects — there's no hand to perform them with in
  this sandbox. That part rests on code review plus the synthetic-landmark
  unit tests covering the same classification/debounce/action logic that
  would run against real landmarks. Anyone running this locally with their
  own hand in frame should treat the first real run as the actual test of
  that part of the pipeline.

## Why this isn't deployed to Cloudflare as the main thing

The brief mentions "deploy on Cloudflare," but this program moves the real
OS mouse cursor and changes real system volume — actions a browser
sandbox is deliberately prevented from doing for security reasons, and
Cloudflare Pages/Workers have no webcam or OS access at all. Forcing this
into "deploy on Cloudflare" would mean faking it. Instead:

1. This Python app is the real, primary deliverable.
2. `web-demo/` is a static companion site (deployed to Cloudflare) that
   documents the project and includes a legitimate in-browser hand-landmark
   **visualizer** (MediaPipe Hands JS/WASM + `getUserMedia`) — that part
   genuinely can and does run in a browser, since it's detection/drawing
   only, not OS control. It's labeled clearly as a demo of the detection
   layer only.
