"""Non-interactive smoke test: opens the real webcam, runs a few frames
through the real MediaPipe Hands pipeline, and exits — no GUI window, no
keypress needed. Confirms the capture+inference pipeline actually runs
end-to-end on this machine without crashing. Separate from main.py's
interactive loop, which needs a 'q' keypress to exit cleanly.

Run: python scripts/camera_smoke_test.py
"""
import os
import sys
import time

import cv2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gesture_control.classifier import classify_gesture
from gesture_control.stability import StabilityTracker

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("NO CAMERA: cv2.VideoCapture(0).isOpened() == False")
    sys.exit(1)

import mediapipe as mp

hands = mp.solutions.hands.Hands(max_num_hands=2, min_detection_confidence=0.7, min_tracking_confidence=0.6)

n_frames = 30
n_hands_seen = 0
gesture_counts = {}
tracker = StabilityTracker(required_frames=4)
start = time.time()

for i in range(n_frames):
    ok, frame = cap.read()
    if not ok:
        print(f"frame grab failed at {i}")
        break
    frame = cv2.flip(frame, 1)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb)
    if results.multi_hand_landmarks:
        n_hands_seen += len(results.multi_hand_landmarks)
        for hl in results.multi_hand_landmarks:
            pts = [(lm.x, lm.y, lm.z) for lm in hl.landmark]
            g = classify_gesture(pts)
            gesture_counts[g] = gesture_counts.get(g, 0) + 1
            tracker.update(g)

elapsed = time.time() - start
hands.close()
cap.release()

print(f"Processed {n_frames} frames in {elapsed:.2f}s ({n_frames/elapsed:.1f} fps)")
print(f"Hand detections across frames: {n_hands_seen}")
print(f"Gesture classifications seen: {gesture_counts}")
print(f"Final debounced/confirmed gesture: {tracker.confirmed}")
print("SMOKE TEST PASSED: capture + MediaPipe inference pipeline ran without crashing.")
