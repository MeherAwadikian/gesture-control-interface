"""
System volume control.

Tries pycaw (Windows Core Audio API) for real, direct volume control first.
If pycaw or its COM dependencies aren't available/importable (or any
Activate()/QueryInterface() call fails at construction time), falls back
honestly to pyautogui's simulated media keys rather than silently pretending
real control is happening. `self.backend` tells the caller which one is live
so the UI/log can say so.
"""
from __future__ import annotations

from typing import Optional


class VolumeController:
    def __init__(self):
        self.backend = "none"
        self.error: Optional[str] = None
        self._endpoint = None
        self._try_init_pycaw()

    def _try_init_pycaw(self) -> None:
        # pycaw's API shape has changed across versions. Newer releases
        # (>=20220416-ish) wrap the raw COM device in a pycaw.utils.AudioDevice
        # that exposes a ready-made `.EndpointVolume` property instead of the
        # old pattern of calling `.Activate()` directly on what GetSpeakers()
        # returns — that old pattern raises AttributeError on the new wrapper.
        # Try the modern property first, then fall back to the legacy
        # Activate()/QueryInterface() dance for older pycaw installs.
        try:
            from pycaw.utils import AudioUtilities

            speakers = AudioUtilities.GetSpeakers()
            self._endpoint = speakers.EndpointVolume
            self._endpoint.GetMasterVolumeLevelScalar()
            self.backend = "pycaw"
            return
        except Exception as exc_modern:  # noqa: BLE001
            modern_error = f"{type(exc_modern).__name__}: {exc_modern}"

        try:
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            from comtypes import CLSCTX_ALL

            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            self._endpoint = interface.QueryInterface(IAudioEndpointVolume)
            self._endpoint.GetMasterVolumeLevelScalar()
            self.backend = "pycaw"
        except Exception as exc_legacy:  # noqa: BLE001 - deliberately broad, this is a capability probe
            self.backend = "pyautogui_fallback"
            self.error = f"modern API failed ({modern_error}); legacy API failed ({type(exc_legacy).__name__}: {exc_legacy})"

    def volume_up(self, step: float = 0.05) -> None:
        if self.backend == "pycaw" and self._endpoint is not None:
            current = self._endpoint.GetMasterVolumeLevelScalar()
            self._endpoint.SetMasterVolumeLevelScalar(min(1.0, current + step), None)
        else:
            import pyautogui

            pyautogui.press("volumeup")

    def volume_down(self, step: float = 0.05) -> None:
        if self.backend == "pycaw" and self._endpoint is not None:
            current = self._endpoint.GetMasterVolumeLevelScalar()
            self._endpoint.SetMasterVolumeLevelScalar(max(0.0, current - step), None)
        else:
            import pyautogui

            pyautogui.press("volumedown")

    def current_level(self) -> Optional[float]:
        if self.backend == "pycaw" and self._endpoint is not None:
            return self._endpoint.GetMasterVolumeLevelScalar()
        return None
