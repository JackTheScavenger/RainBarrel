import os
import json
import io
import asyncio
import ctypes
import hashlib
import importlib
import math
import re
import subprocess
import sys
import time
import random
import threading
import tempfile
import urllib.error
import urllib.request
import webbrowser
import winsound
import wave
from datetime import datetime
from tkinter import TclError, filedialog

import cv2
import mss
import numpy as np
import pyautogui
import customtkinter as ctk
from PIL import Image, ImageTk, ImageDraw, ImageEnhance, ImageFilter, ImageOps

# ================= TO-DO =================
# Rain page animations
# Bot to decide best skin to withdraw
# Collect rain without having the website up or your cursor moved at all
# Password system/accounts which i activate
# Free battle joiner
# Discount battle joiner
# Auto open daily case
# Randomize constants
# Add rain prediction

# ================= CONFIG =================

APP_NAME = "RainBarrel"
APP_VERSION = "1.1.21"
APP_USER_MODEL_ID = "JackTheScavenger.RainBarrel"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIDENCE_PERCENT = 65
DEFAULT_RAIN_CLICKER_INTERVAL = 25
DEFAULT_MOVE_TIME = 1.5
DEFAULT_MOVE_STEPS = 100
DEFAULT_RAIN_COLLECT_ANY_TIME = True
DEFAULT_RAIN_COLLECT_START_TIME = "00:00"
DEFAULT_RAIN_COLLECT_END_TIME = "23:59"
DEFAULT_RAIN_COLLECT_CHANCE = 100
DEFAULT_WEATHER_STATION_INTERVAL = 15
DEFAULT_WEATHER_NOTIFICATION_VOLUME = 100


def resource_path(filename):
    if getattr(sys, "frozen", False):
        return os.path.join(getattr(sys, "_MEIPASS", BASE_DIR), filename)
    return os.path.join(BASE_DIR, filename)


def app_data_path(filename):
    roots = [
        os.environ.get("APPDATA"),
        os.environ.get("LOCALAPPDATA"),
        os.path.expanduser("~"),
    ]
    if getattr(sys, "frozen", False):
        roots.append(os.path.dirname(sys.executable))
    roots.append(BASE_DIR)

    for root in roots:
        if not root:
            continue

        path = os.path.join(root, APP_NAME)
        try:
            os.makedirs(path, exist_ok=True)
            return os.path.join(path, filename)
        except OSError:
            continue

    return os.path.join(BASE_DIR, filename)


IMAGE_PATH = resource_path("Join Rain Event.png")
BATTLE_DISCOUNT_IMAGE_PATH = resource_path("100 % off .png")
RAIN_REWARD_IMAGE_PATH = resource_path("Rain amount.png")
RAIN_JOINED_IMAGE_PATH = resource_path("Rain Joined.png")
POPUP_AFTER_RAIN_IMAGE_PATH = resource_path("PopupAfterRain.png")
ICON_PATH = resource_path("app_icon.ico")
DEFAULT_DATA_PATH = resource_path("bandit_data.json")
DATA_PATH = app_data_path("bandit_data.json")
ALERT_SOUND_PATH = resource_path("rain_alert.wav")
BANDIT_CAMP_URL = "https://bandit.camp/"
UPDATE_MANIFEST_URL = "https://raw.githubusercontent.com/JackTheScavenger/RainBarrel/main/latest.json"
UPDATE_CHECK_TIMEOUT_SECONDS = 8
UPDATE_DOWNLOAD_TIMEOUT_SECONDS = 5 * 60
SELENIUM_PAGE_WAIT = 45
RAIN_TRACKER_WATCH_SECONDS = 3 * 60 + 10
RAIN_REWARD_WATCH_SECONDS = RAIN_TRACKER_WATCH_SECONDS
RAIN_RESULT_WATCH_SECONDS = RAIN_TRACKER_WATCH_SECONDS
RAIN_TIP_WATCH_SECONDS = RAIN_TRACKER_WATCH_SECONDS
RAIN_FOUND_COOLDOWN_SECONDS = 3 * 60
WEATHER_RAIN_FOUND_COOLDOWN_SECONDS = 3 * 60
RAIN_REWARD_SCAN_INTERVAL_SECONDS = 1
RAIN_RESULT_SCAN_INTERVAL_SECONDS = 1
RAIN_RESULT_FULL_SCREEN_OCR_EVERY = 2
RAIN_TIP_SCAN_INTERVAL_SECONDS = 1
RAIN_TIP_MISSES_AFTER_FOUND_TO_STOP = 3
RAIN_TIP_READING_CONFIRMATIONS = 2
RAIN_TIP_LARGE_JUMP_CONFIRMATIONS = 4
RAIN_TIP_DROP_CONFIRMATIONS = 5
RAIN_TIP_LARGE_JUMP_MIN_SCRAP = 8.0
RAIN_TIP_LARGE_JUMP_RATIO = 0.35
RAIN_TIP_RECENT_WINDOW = 6
RAIN_TIP_HISTORY_RECLAIM_CONFIRMATIONS = 2
RAIN_TIP_HISTORY_RECLAIM_MARGIN = 3
RAIN_TIP_FINAL_MIN_READS = 2
RAIN_TIP_FINAL_CLEAR_MARGIN = 2
RAIN_REWARD_POPUP_CONFIDENCE = 0.55
RAIN_REWARD_POPUP_TEMPLATE_SCALES = (0.75, 0.85, 0.95, 1.0, 1.1, 1.25, 1.4, 1.6)
RAIN_REWARD_TEMPLATE_IGNORE_RECTS = ((0.31, 0.45, 0.99, 0.95),)
RAIN_REWARD_POPUP_CROP_WIDTH = 520
RAIN_REWARD_POPUP_CROP_HEIGHT = 180
RAIN_JOINED_BOX_CONFIDENCE = 0.55
RAIN_JOINED_BOX_TEMPLATE_SCALES = (0.75, 0.85, 0.95, 1.0, 1.1, 1.25, 1.4, 1.6)
RAIN_JOINED_BOX_TEMPLATE_IGNORE_RECTS = ((0.44, 0.14, 0.68, 0.56),)
RAIN_JOINED_BOX_CROP_WIDTH = 620
RAIN_JOINED_BOX_CROP_HEIGHT = 280
RAIN_JOINED_TIP_LINE_RECTS = ((0.03, 0.30, 0.96, 0.68), (0.03, 0.42, 0.96, 0.66))
RAIN_RESULT_MIN_BOX_WIDTH = 180
RAIN_RESULT_MIN_BOX_HEIGHT = 60
RAIN_RESULT_CANDIDATE_LIMIT = 6
OCR_PREVIEW_LIMIT = 140
RAIN_REWARD_HISTORY_LIMIT = 100
RAIN_LOG_HISTORY_LIMIT = 500
BATTLE_SCAN_INTERVAL_SECONDS = 2.5
BATTLE_CLICK_OFFSET_X = 260
BATTLE_CLICK_OFFSET_Y = 0
WEATHER_RAIN_MAX_ACTIVE_SECONDS = 10 * 60
SCROLL_WHEEL_SPEED_MULTIPLIER = 3
RAIN_TARGET_TEMPLATE_SCALES = (0.80, 0.85, 0.90, 0.95, 1.0, 1.05, 1.10, 1.15, 1.20, 1.30, 1.40, 1.60)
RAIN_TARGET_MAX_COLOR_DIFF = 45.0
DEFAULT_POPUP_AFTER_RAIN_WAIT_SECONDS = 10
POPUP_AFTER_RAIN_CONFIDENCE = 0.82
POPUP_AFTER_RAIN_MAX_COLOR_DIFF = 32.0
POPUP_AFTER_RAIN_TEMPLATE_SCALES = (0.80, 0.85, 0.90, 0.95, 1.0, 1.05, 1.10, 1.15, 1.20, 1.30, 1.40)
POPUP_AFTER_RAIN_CHECKBOX_X_RATIO = 52 / 346
POPUP_AFTER_RAIN_CHECKBOX_Y_RATIO = 76 / 141
POPUP_AFTER_RAIN_CHECKBOX_RECT = (39 / 346, 64 / 141, 65 / 346, 89 / 141)

OCR_LOCK = threading.Lock()

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0
pyautogui.MINIMUM_DURATION = 0
pyautogui.MINIMUM_SLEEP = 0

COLORS = {
    "bg": "#050504",
    "top": "#101210",
    "side": "#080a08",
    "card": "#151816",
    "red": "#d9472f",
    "red2": "#ff6b4a",
    "orange": "#b86a36",
    "green": "#78a941",
    "text": "#e8e0d5",
    "muted": "#8a837b",
    "border": "#2a201d",
}

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002


# ================= IMAGE DETECTION =================

def locate_image_best_all_monitors(
    image_path,
    confidence=0.65,
    scales=(1.0,),
    grayscale=False,
    max_color_diff=None,
):
    target = cv2.imread(image_path, cv2.IMREAD_COLOR)

    if target is None:
        raise FileNotFoundError(f"Image not found: {image_path}")

    target_source = cv2.cvtColor(target, cv2.COLOR_BGR2GRAY) if grayscale else target
    target_h, target_w = target_source.shape[:2]

    with mss.mss() as sct:
        monitor = sct.monitors[0]
        screen_bgr = np.array(sct.grab(monitor))
        screen_bgr = cv2.cvtColor(screen_bgr, cv2.COLOR_BGRA2BGR)
        screen = screen_bgr
        if grayscale:
            screen = cv2.cvtColor(screen_bgr, cv2.COLOR_BGR2GRAY)

        screen_h, screen_w = screen.shape[:2]
        best = None
        best_valid = None

        for scale in scales:
            scaled_w = max(1, int(round(target_w * scale)))
            scaled_h = max(1, int(round(target_h * scale)))
            if scaled_w > screen_w or scaled_h > screen_h:
                continue

            if scale == 1.0:
                scaled_target = target_source
            else:
                interpolation = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_CUBIC
                scaled_target = cv2.resize(
                    target_source,
                    (scaled_w, scaled_h),
                    interpolation=interpolation,
                )

            result = cv2.matchTemplate(screen, scaled_target, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)
            color_diff = None
            if max_color_diff is not None:
                crop = screen_bgr[
                    max_loc[1] : max_loc[1] + scaled_h,
                    max_loc[0] : max_loc[0] + scaled_w,
                ]
                scaled_color_target = cv2.resize(
                    target,
                    (scaled_w, scaled_h),
                    interpolation=cv2.INTER_AREA if scale < 1.0 else cv2.INTER_CUBIC,
                )
                color_diff = float(
                    np.abs(crop.astype(np.int16) - scaled_color_target.astype(np.int16)).mean()
                )

            candidate = {
                "left": monitor["left"] + int(max_loc[0]),
                "top": monitor["top"] + int(max_loc[1]),
                "x": monitor["left"] + max_loc[0] + scaled_w // 2,
                "y": monitor["top"] + max_loc[1] + scaled_h // 2,
                "score": float(max_val),
                "scale": float(scale),
                "width": int(scaled_w),
                "height": int(scaled_h),
                "needed": float(confidence),
                "color_diff": color_diff,
            }
            if best is None or max_val > best["score"]:
                best = candidate

            color_ok = max_color_diff is None or color_diff is None or color_diff <= max_color_diff
            if candidate["score"] >= confidence and color_ok:
                if best_valid is None or candidate["score"] > best_valid["score"]:
                    best_valid = candidate

        if best_valid is not None:
            return best_valid, best

    return None, best


def locate_image_all_monitors(image_path, confidence=0.65):
    match, _ = locate_image_best_all_monitors(image_path, confidence=confidence)
    if match:
        return match["x"], match["y"], match["score"]

    return None


def locate_rain_target_all_monitors(confidence=0.65):
    return locate_image_best_all_monitors(
        IMAGE_PATH,
        confidence=confidence,
        scales=RAIN_TARGET_TEMPLATE_SCALES,
        grayscale=True,
        max_color_diff=RAIN_TARGET_MAX_COLOR_DIFF,
    )


def locate_popup_after_rain_all_monitors():
    return locate_image_best_all_monitors(
        POPUP_AFTER_RAIN_IMAGE_PATH,
        confidence=POPUP_AFTER_RAIN_CONFIDENCE,
        scales=POPUP_AFTER_RAIN_TEMPLATE_SCALES,
        grayscale=False,
        max_color_diff=POPUP_AFTER_RAIN_MAX_COLOR_DIFF,
    )


def get_screen_crop_for_match(match):
    with mss.mss() as sct:
        monitor = sct.monitors[0]
        screen = np.array(sct.grab(monitor))

    left = int(match["left"] - monitor["left"])
    top = int(match["top"] - monitor["top"])
    width = int(match["width"])
    height = int(match["height"])
    if width <= 0 or height <= 0:
        return None

    crop = screen[top : top + height, left : left + width]
    if crop.size == 0:
        return None

    return cv2.cvtColor(crop, cv2.COLOR_BGRA2RGB)


def validate_popup_after_rain_match(match):
    crop = get_screen_crop_for_match(match)
    if crop is None:
        return False, "popup crop was empty"

    height, width = crop.shape[:2]
    title = crop[
        int(height * 0.03) : max(int(height * 0.25), int(height * 0.03) + 1),
        int(width * 0.03) : max(int(width * 0.70), int(width * 0.03) + 1),
    ]
    green_pixels = (
        (title[:, :, 1] > 145)
        & (title[:, :, 0] > 75)
        & (title[:, :, 2] < 150)
        & ((title[:, :, 1].astype(np.int16) - title[:, :, 0].astype(np.int16)) > 25)
    )
    green_ratio = float(green_pixels.mean()) if green_pixels.size else 0.0

    left_ratio, top_ratio, right_ratio, bottom_ratio = POPUP_AFTER_RAIN_CHECKBOX_RECT
    checkbox = crop[
        int(height * top_ratio) : max(int(height * bottom_ratio), int(height * top_ratio) + 1),
        int(width * left_ratio) : max(int(width * right_ratio), int(width * left_ratio) + 1),
    ]
    dark_pixels = (
        (checkbox[:, :, 0] < 85)
        & (checkbox[:, :, 1] < 85)
        & (checkbox[:, :, 2] < 85)
    )
    light_pixels = (
        (checkbox[:, :, 0] > 120)
        & (checkbox[:, :, 1] > 120)
        & (checkbox[:, :, 2] > 120)
    )
    dark_ratio = float(dark_pixels.mean()) if dark_pixels.size else 0.0
    light_ratio = float(light_pixels.mean()) if light_pixels.size else 0.0

    valid = green_ratio >= 0.05 and dark_ratio >= 0.45 and light_ratio >= 0.02
    detail = (
        f"green title={green_ratio:.2f}, "
        f"checkbox dark={dark_ratio:.2f}, checkbox light={light_ratio:.2f}"
    )
    return valid, detail


def locate_image_matches_all_monitors(image_path, confidence=0.65, max_matches=8):
    target = cv2.imread(image_path, cv2.IMREAD_COLOR)

    if target is None:
        raise FileNotFoundError(f"Image not found: {image_path}")

    with mss.mss() as sct:
        monitor = sct.monitors[0]
        screen = np.array(sct.grab(monitor))

    screen_rgb = cv2.cvtColor(screen, cv2.COLOR_BGRA2RGB)
    screen_bgr = cv2.cvtColor(screen, cv2.COLOR_BGRA2BGR)
    result = cv2.matchTemplate(screen_bgr, target, cv2.TM_CCOEFF_NORMED)
    h, w = target.shape[:2]

    candidates = []
    ys, xs = np.where(result >= confidence)
    for x, y in zip(xs, ys):
        candidates.append(
            {
                "left": monitor["left"] + int(x),
                "top": monitor["top"] + int(y),
                "x": monitor["left"] + int(x) + w // 2,
                "y": monitor["top"] + int(y) + h // 2,
                "width": w,
                "height": h,
                "score": float(result[y, x]),
            }
        )

    candidates.sort(key=lambda item: item["score"], reverse=True)
    matches = []
    min_distance = max(w, h) * 0.65
    for candidate in candidates:
        if len(matches) >= max_matches:
            break

        if any(
            math.hypot(candidate["x"] - match["x"], candidate["y"] - match["y"]) < min_distance
            for match in matches
        ):
            continue

        matches.append(candidate)

    return matches, Image.fromarray(screen_rgb), monitor


def page_is_cloudflare_challenge(page):
    return "cf-chl" in page or "just a moment" in page or "enable javascript and cookies" in page


def page_has_active_rain_event(page):
    active_markers = [
        "join rain event",
        "claim rain",
        "collect rain",
        "rain ends in",
    ]

    return any(marker in page for marker in active_markers)


def parse_epoch_millis(value):
    try:
        timestamp = float(value)
    except (TypeError, ValueError):
        return None

    if timestamp <= 0:
        return None

    if timestamp >= 1_000_000_000_000:
        return int(timestamp)

    if timestamp >= 1_000_000_000:
        return int(timestamp * 1000)

    return None


def parse_weather_rain_active_until_ms(payload, now_ms):
    started_at = parse_epoch_millis(payload.get("startedAt")) or now_ms

    for key in ("endsAt", "endAt", "expiresAt", "expireAt", "finishedAt"):
        end_at = parse_epoch_millis(payload.get(key))
        if end_at is not None:
            max_end = started_at + WEATHER_RAIN_MAX_ACTIVE_SECONDS * 1000
            return min(end_at, max_end)

    try:
        duration = float(payload.get("duration", 0))
    except (TypeError, ValueError):
        duration = 0

    if duration <= 0:
        return now_ms

    if duration >= 1_000_000_000:
        end_at = parse_epoch_millis(duration)
    elif duration <= WEATHER_RAIN_MAX_ACTIVE_SECONDS:
        end_at = started_at + int(duration * 1000)
    else:
        end_at = started_at + int(duration)

    if end_at is None:
        return now_ms

    max_end = started_at + WEATHER_RAIN_MAX_ACTIVE_SECONDS * 1000
    return min(end_at, max_end)


def page_is_bandit_loading(page_text):
    page_text = page_text.strip().lower()
    return page_text.startswith("loading") and "cancel" in page_text


def get_browser_visible_text(driver):
    try:
        return driver.execute_script("return document.body ? document.body.innerText : '';") or ""
    except Exception:
        return ""


def parse_rain_reward_amount(text):
    patterns = [
        r"\byou\s+won\s+([0-9]+(?:[.,][0-9]+)?)(?:\s+scrap)?\b",
        r"\bwon\s+([0-9]+(?:[.,][0-9]+)?)\s+scrap\b",
        r"\byour\s+reward\s+([0-9]+(?:[.,][0-9]+)?)\s+scrap\b",
    ]
    match = None
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            break

    if not match:
        if re.search(r"\byou\s+won\b", text, re.IGNORECASE):
            numbers = re.findall(r"([0-9]+(?:[.,][0-9]+)?)", text)
            if numbers:
                try:
                    return float(numbers[0].replace(",", "."))
                except ValueError:
                    return None
        if re.search(r"\brakeback\s+rain\b", text, re.IGNORECASE):
            scrap_match = re.search(r"([0-9]+(?:[.,][0-9]+)?)\s*scrap\b", text, re.IGNORECASE)
            if scrap_match:
                try:
                    return float(scrap_match.group(1).replace(",", "."))
                except ValueError:
                    return None
        return None

    try:
        return float(match.group(1).replace(",", "."))
    except ValueError:
        return None


def parse_scrap_number(value):
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return round(float(value), 2)

    match = re.search(r"([0-9]+(?:[.,][0-9]+)?)", str(value))
    if not match:
        return None

    try:
        return round(float(match.group(1).replace(",", ".")), 2)
    except ValueError:
        return None


def parse_ocr_int(value):
    if value is None:
        return None

    normalized = str(value).translate(
        str.maketrans(
            {
                "O": "0",
                "o": "0",
                "I": "1",
                "l": "1",
                "|": "1",
                "S": "5",
                "s": "5",
                "B": "8",
            }
        )
    )
    normalized = re.sub(r"[^0-9]", "", normalized)
    if not normalized:
        return None

    try:
        return int(normalized)
    except ValueError:
        return None


def parse_ocr_scrap_number(value):
    if value is None:
        return None

    normalized = str(value)
    normalized = normalized.translate(str.maketrans({"O": "0", "o": "0", "I": "1", "l": "1", "|": "1"}))
    normalized = re.sub(r"\s+", "", normalized)
    normalized = normalized.replace(",", ".")
    normalized = re.sub(r"[^0-9.]", "", normalized)
    if normalized.count(".") > 1:
        first_dot = normalized.find(".")
        normalized = normalized[: first_dot + 1] + normalized[first_dot + 1 :].replace(".", "")

    match = re.search(r"([0-9]+(?:\.[0-9]+)?)", normalized)
    if not match:
        return None

    try:
        token = match.group(1)
        if "." not in token and len(token) >= 4:
            return round(float(token) / 100, 2)
        return round(float(token), 2)
    except ValueError:
        return None


def parse_rain_tip_amount(text):
    patterns = [
        r"([0-9OIl|]+(?:[\s.,][0-9OIl|]+)?)\s+from\s+rain\s+tips?\b",
        r"([0-9OIl|]+(?:[\s.,][0-9OIl|]+)?)\s+from\s+rain\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return parse_ocr_scrap_number(match.group(1))
    return None


def count_rain_result_named_users(names_text):
    title_match = list(re.finditer(r"\brake\s*back\s+rain\s+", names_text, flags=re.IGNORECASE))
    if title_match:
        names_text = names_text[title_match[-1].end():]
    else:
        names_text = re.sub(r"^[\s\W]*(?:rain)\b", "", names_text, flags=re.IGNORECASE)

    names_text = re.sub(r"[\r\n]+", " ", names_text)
    names_text = re.sub(r"\s+", " ", names_text).strip(" ,.:;")
    if not names_text:
        return 0

    rough_parts = re.split(r"\s*,\s*|\s+\band\b\s+|\s*\.\s+", names_text, flags=re.IGNORECASE)
    parts = [part.strip(" ,.:;*#") for part in rough_parts if part.strip(" ,.:;*#")]

    return len(parts)


def find_rain_result_title_match(text):
    patterns = (
        r"\brake\s*back\s+rain\b",
        r"\brakeb[aeo]ck\s+rain\b",
        r"\brake[bh]ack\s+rain\b",
    )
    matches = []
    for pattern in patterns:
        matches.extend(re.finditer(pattern, text, flags=re.IGNORECASE))

    if not matches:
        return None

    return sorted(matches, key=lambda item: item.start())[-1]


def normalize_rain_result_text(text):
    normalized = re.sub(r"\s+", " ", text or "").strip()
    title_match = find_rain_result_title_match(normalized)
    if title_match is None:
        return None

    return normalized[title_match.start() :]


def text_looks_like_rain_join_prompt(text):
    return re.search(
        r"\b(join\s+rain|join\s+now|rain\s+tips?|based\s+on\s+your\s+play|"
        r"amount\s*share|requirements?\s+to\s+join|get\s+free\s+scrap)\b",
        text,
        re.IGNORECASE,
    ) is not None


def text_has_rain_result_wording(text):
    if find_rain_result_other_count(text)[0] is not None:
        return True

    return re.search(
        r"\b(?:claimed|clalmed|clairned|clamed|daimed)\b",
        text,
        re.IGNORECASE,
    ) is not None


def find_rain_result_other_count(text):
    other_pattern = re.compile(
        r"(?:\b(?:and|ard|arid|ana)\b|&)?\s*"
        r"(?P<others>[0-9OSBIl|]{1,5})\s*"
        r"(?:other|0ther|otner|uther|othcr)\s+bandits?",
        re.IGNORECASE,
    )
    matches = list(other_pattern.finditer(text))
    if not matches:
        return None, None

    match = matches[-1]
    return parse_ocr_int(match.group("others")), match


def parse_rain_result_summary(text):
    normalized = normalize_rain_result_text(text)
    if normalized is None:
        return None

    if text_looks_like_rain_join_prompt(normalized):
        return None

    if not text_has_rain_result_wording(normalized):
        return None

    from_rain = r"(?:from|fr0m|f(?:r|n)?om|frm|fom)\s+rain\b"
    claimed_word = r"(?:claimed|clalmed|clairned|clamed|daimed)"
    claimed_amount = (
        rf"(?:\b{claimed_word}\b[^\d]{{0,40}})"
        rf"(?P<claimed>[0-9]+(?:[.,][0-9]+)?)\s+{from_rain}"
    )
    other_claimed_amount = (
        rf"(?:\b{claimed_word}\b[^\d]{{0,40}})?"
        rf"(?P<claimed>[0-9]+(?:[.,][0-9]+)?)\s+{from_rain}"
    )
    other_count, other_match = find_rain_result_other_count(normalized)
    parsed_other_count = False
    if other_match is not None and other_count is not None:
        tail = normalized[other_match.end() :]
        amount_match = re.search(other_claimed_amount, tail, re.IGNORECASE)
        if amount_match:
            names_text = normalized[: other_match.start()]
            named_count = count_rain_result_named_users(names_text)
            people_joined = named_count + int(other_count)
            total_claimed = float(amount_match.group("claimed").replace(",", "."))
            parsed_other_count = True

    if not parsed_other_count:
        match = re.search(
            r"(?P<names>.*?)\s+" + claimed_amount,
            normalized,
            re.IGNORECASE,
        )
        if not match:
            return None

        people_joined = count_rain_result_named_users(match.group("names"))
        total_claimed = float(match.group("claimed").replace(",", "."))

    tipped_match = re.search(
        r"\btipped\s+(?P<tipped>[0-9]+(?:[.,][0-9]+)?)\b",
        normalized,
        re.IGNORECASE,
    )
    total_tipped = parse_scrap_number(tipped_match.group("tipped")) if tipped_match else None

    if people_joined <= 0 or total_claimed <= 0:
        return None

    return {
        "people_joined": int(people_joined),
        "total_scrap_claimed": round(total_claimed, 2),
        "total_tipped": total_tipped,
    }


def capture_all_monitors_image():
    with mss.mss() as sct:
        monitor = sct.monitors[0]
        screen = np.array(sct.grab(monitor))

    screen = cv2.cvtColor(screen, cv2.COLOR_BGRA2RGB)
    return Image.fromarray(screen)


def compact_ocr_preview(text, limit=OCR_PREVIEW_LIMIT):
    preview = re.sub(r"\s+", " ", text or "").strip()
    if not preview:
        return "no readable text"

    if len(preview) > limit:
        return preview[:limit].rstrip() + "..."

    return preview


def locate_image_in_pil(image, image_path, confidence=0.7, scales=(1.0,), ignore_rects=()):
    if not os.path.exists(image_path):
        return None, None

    target = cv2.imread(image_path, cv2.IMREAD_COLOR)
    if target is None:
        return None, None

    screen_rgb = np.array(image.convert("RGB"))
    screen_gray = cv2.cvtColor(screen_rgb, cv2.COLOR_RGB2GRAY)
    target_gray = cv2.cvtColor(target, cv2.COLOR_BGR2GRAY)
    screen_h, screen_w = screen_gray.shape[:2]
    best = None
    best_score = 0.0

    for scale in scales:
        target_w = max(1, int(target_gray.shape[1] * scale))
        target_h = max(1, int(target_gray.shape[0] * scale))
        if target_w > screen_w or target_h > screen_h:
            continue

        scaled_target = cv2.resize(
            target_gray,
            (target_w, target_h),
            interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC,
        )

        if ignore_rects:
            scaled_mask = np.full((target_h, target_w), 255, dtype=np.uint8)
            for left_ratio, top_ratio, right_ratio, bottom_ratio in ignore_rects:
                left = min(max(0, int(target_w * left_ratio)), target_w)
                top = min(max(0, int(target_h * top_ratio)), target_h)
                right = min(max(left, int(target_w * right_ratio)), target_w)
                bottom = min(max(top, int(target_h * bottom_ratio)), target_h)
                scaled_mask[top:bottom, left:right] = 0
            result = cv2.matchTemplate(
                screen_gray,
                scaled_target,
                cv2.TM_CCORR_NORMED,
                mask=scaled_mask,
            )
        else:
            result = cv2.matchTemplate(screen_gray, scaled_target, cv2.TM_CCOEFF_NORMED)

        result = np.nan_to_num(result, nan=0.0, posinf=0.0, neginf=0.0)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        if max_val > best_score:
            best_score = float(max_val)
            best = {
                "left": int(max_loc[0]),
                "top": int(max_loc[1]),
                "width": int(target_w),
                "height": int(target_h),
                "score": float(max_val),
                "scale": float(scale),
            }

    if best is None or best_score < confidence:
        return None, best_score

    return best, best_score


def crop_rain_reward_popup(screenshot):
    match, best_score = locate_image_in_pil(
        screenshot,
        RAIN_REWARD_IMAGE_PATH,
        confidence=RAIN_REWARD_POPUP_CONFIDENCE,
        scales=RAIN_REWARD_POPUP_TEMPLATE_SCALES,
        ignore_rects=RAIN_REWARD_TEMPLATE_IGNORE_RECTS,
    )
    if not match:
        return None, best_score

    left = max(0, match["left"] - 12)
    top = max(0, match["top"] - 12)
    right = min(screenshot.width, left + RAIN_REWARD_POPUP_CROP_WIDTH)
    bottom = min(screenshot.height, top + RAIN_REWARD_POPUP_CROP_HEIGHT)
    crop = screenshot.crop((left, top, right, bottom))

    if crop.width < 900:
        crop = crop.resize((crop.width * 2, crop.height * 2), Image.LANCZOS)

    return crop, match["score"]


def crop_rain_joined_box(screenshot):
    match, best_score = locate_image_in_pil(
        screenshot,
        RAIN_JOINED_IMAGE_PATH,
        confidence=RAIN_JOINED_BOX_CONFIDENCE,
        scales=RAIN_JOINED_BOX_TEMPLATE_SCALES,
        ignore_rects=RAIN_JOINED_BOX_TEMPLATE_IGNORE_RECTS,
    )
    if not match:
        return None, best_score

    left = max(0, match["left"] - 12)
    top = max(0, match["top"] - 12)
    right = min(screenshot.width, left + RAIN_JOINED_BOX_CROP_WIDTH)
    bottom = min(screenshot.height, top + RAIN_JOINED_BOX_CROP_HEIGHT)
    crop = screenshot.crop((left, top, right, bottom))

    if crop.width < 900:
        crop = crop.resize((crop.width * 2, crop.height * 2), Image.LANCZOS)

    return crop, match["score"]


def crop_image_by_ratio(image, rect):
    left_ratio, top_ratio, right_ratio, bottom_ratio = rect
    left = min(max(0, int(image.width * left_ratio)), image.width)
    top = min(max(0, int(image.height * top_ratio)), image.height)
    right = min(max(left + 1, int(image.width * right_ratio)), image.width)
    bottom = min(max(top + 1, int(image.height * bottom_ratio)), image.height)
    return image.crop((left, top, right, bottom))


def prepare_tip_ocr_variant(image):
    gray = ImageOps.grayscale(image)
    gray = ImageEnhance.Contrast(gray).enhance(2.4)
    gray = ImageEnhance.Sharpness(gray).enhance(1.8)
    gray = gray.filter(ImageFilter.MedianFilter(size=3))
    threshold = 150
    return gray.point(lambda pixel: 255 if pixel >= threshold else 0, mode="1").convert("RGB")


def build_rain_tip_ocr_images(joined_crop):
    images = [joined_crop]
    for rect in RAIN_JOINED_TIP_LINE_RECTS:
        line_crop = crop_image_by_ratio(joined_crop, rect)
        if line_crop.width < 900:
            line_crop = line_crop.resize((line_crop.width * 2, line_crop.height * 2), Image.LANCZOS)
        images.append(line_crop)
        images.append(prepare_tip_ocr_variant(line_crop))
    return images


def rain_tip_cents(amount):
    return int(round(float(amount) * 100))


def rain_tip_amount_from_cents(cents):
    return round(int(cents) / 100, 2)


def choose_rain_tip_amount(candidates):
    if not candidates:
        return None

    cents_counts = {}
    for candidate in candidates:
        cents = rain_tip_cents(candidate)
        cents_counts[cents] = cents_counts.get(cents, 0) + 1

    confirmed = [(cents, count) for cents, count in cents_counts.items() if count >= 2]
    if confirmed:
        confirmed.sort(key=lambda item: item[1], reverse=True)
        if len(confirmed) == 1 or confirmed[0][1] > confirmed[1][1]:
            return rain_tip_amount_from_cents(confirmed[0][0])
        return None

    if len(cents_counts) == 1:
        return rain_tip_amount_from_cents(next(iter(cents_counts)))

    return None


def choose_final_rain_tip_cents(read_counts, fallback_cents=None, read_last_seen=None):
    if not read_counts:
        return fallback_cents, fallback_cents is not None

    ranked = sorted(read_counts.items(), key=lambda item: item[1], reverse=True)
    top_cents, top_count = ranked[0]
    runner_count = ranked[1][1] if len(ranked) > 1 else 0

    if top_count >= RAIN_TIP_FINAL_MIN_READS and top_count >= runner_count + RAIN_TIP_FINAL_CLEAR_MARGIN:
        if fallback_cents is not None and top_cents != fallback_cents and read_last_seen is not None:
            if read_last_seen.get(top_cents, -1) < read_last_seen.get(fallback_cents, -1):
                return fallback_cents, False
        return top_cents, True

    if fallback_cents is not None and read_last_seen is not None:
        fallback_count = read_counts.get(fallback_cents, 0)
        if fallback_count >= RAIN_TIP_READING_CONFIRMATIONS:
            latest_seen = max(read_last_seen.values(), default=-1)
            if read_last_seen.get(fallback_cents, -1) == latest_seen:
                return fallback_cents, True

    return fallback_cents, False


def format_rain_tip_read_counts(read_counts, limit=4):
    if not read_counts:
        return "no reads"

    ranked = sorted(read_counts.items(), key=lambda item: item[1], reverse=True)
    return ", ".join(
        f"{rain_tip_amount_from_cents(cents):.2f}x{count}"
        for cents, count in ranked[:limit]
    )


def build_rain_result_ocr_images(crop):
    base = crop.convert("RGB")
    enlarged = base.resize(
        (max(1, base.width * 2), max(1, base.height * 2)),
        Image.Resampling.LANCZOS,
    )
    enhanced = ImageEnhance.Contrast(enlarged).enhance(1.7)
    enhanced = ImageEnhance.Sharpness(enhanced).enhance(1.8)
    return (base, enhanced)


def find_rain_result_candidate_crops(screenshot):
    image_rgb = np.array(screenshot.convert("RGB"))
    hsv = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2HSV)

    yellow_mask = cv2.inRange(
        hsv,
        np.array([14, 80, 90], dtype=np.uint8),
        np.array([45, 255, 255], dtype=np.uint8),
    )
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    yellow_mask = cv2.morphologyEx(yellow_mask, cv2.MORPH_CLOSE, kernel, iterations=1)
    yellow_mask = cv2.dilate(yellow_mask, kernel, iterations=1)

    contours, _ = cv2.findContours(yellow_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidates = []
    screen_width, screen_height = screenshot.size

    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if w < RAIN_RESULT_MIN_BOX_WIDTH or h < RAIN_RESULT_MIN_BOX_HEIGHT:
            continue

        aspect = w / max(h, 1)
        if aspect < 1.4 or aspect > 6.5:
            continue

        left = max(0, x - 8)
        top = max(0, y - 8)
        right = min(screen_width, x + w + 8)
        bottom = min(screen_height, y + h + 8)
        candidates.append(
            {
                "crop": screenshot.crop((left, top, right, bottom)),
                "area": w * h,
            }
        )

    candidates.sort(key=lambda item: item["area"], reverse=True)
    return [item["crop"] for item in candidates[:RAIN_RESULT_CANDIDATE_LIMIT]]


async def ocr_image_with_windows(image):
    imaging = importlib.import_module("winrt.windows.graphics.imaging")
    ocr = importlib.import_module("winrt.windows.media.ocr")
    streams = importlib.import_module("winrt.windows.storage.streams")
    BitmapDecoder = imaging.BitmapDecoder
    OcrEngine = ocr.OcrEngine
    DataWriter = streams.DataWriter
    InMemoryRandomAccessStream = streams.InMemoryRandomAccessStream

    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="PNG")

    stream = InMemoryRandomAccessStream()
    writer = DataWriter(stream)
    writer.write_bytes(buffer.getvalue())
    await writer.store_async()
    await writer.flush_async()
    writer.detach_stream()
    stream.seek(0)

    decoder = await BitmapDecoder.create_async(stream)
    bitmap = await decoder.get_software_bitmap_async()
    engine = OcrEngine.try_create_from_user_profile_languages()
    if engine is None:
        return ""

    result = await engine.recognize_async(bitmap)
    return result.text or ""


def run_windows_ocr(image):
    with OCR_LOCK:
        return asyncio.run(ocr_image_with_windows(image))


def read_rain_reward_amount_from_screen():
    try:
        screenshot = capture_all_monitors_image()
    except (ImportError, ModuleNotFoundError):
        return None, "Windows OCR packages are not installed"
    except Exception as e:
        return None, f"Screenshot failed: {e.__class__.__name__}"

    reward_crop, popup_score = crop_rain_reward_popup(screenshot)
    if reward_crop is None:
        if popup_score is None:
            return None, "Reward popup image not found"
        return None, f"Reward popup image not found (best match={popup_score:.2f})"

    try:
        text = run_windows_ocr(reward_crop)
    except (ImportError, ModuleNotFoundError):
        return None, "Windows OCR packages are not installed"
    except Exception as e:
        return None, f"Reward popup OCR failed: {e.__class__.__name__}"

    reward = parse_rain_reward_amount(text)
    if reward is None:
        return (
            None,
            "Reward popup image found but amount was not parsed "
            f"(match={popup_score:.2f}, OCR saw: {compact_ocr_preview(text)})",
        )

    return reward, f"Read reward popup: {reward:.2f} scrap"


def read_rain_tip_amount_from_screen():
    try:
        screenshot = capture_all_monitors_image()
    except (ImportError, ModuleNotFoundError):
        return None, "Windows OCR packages are not installed"
    except Exception as e:
        return None, f"Screenshot failed: {e.__class__.__name__}"

    joined_crop, box_score = crop_rain_joined_box(screenshot)
    if joined_crop is None:
        if box_score is None:
            return None, "Rain joined box image not found"
        return None, f"Rain joined box image not found (best match={box_score:.2f})"

    candidates = []
    previews = []
    for ocr_image in build_rain_tip_ocr_images(joined_crop):
        try:
            text = run_windows_ocr(ocr_image)
        except (ImportError, ModuleNotFoundError):
            return None, "Windows OCR packages are not installed"
        except Exception as e:
            return None, f"Rain joined box OCR failed: {e.__class__.__name__}"

        previews.append(compact_ocr_preview(text, 80))
        amount = parse_rain_tip_amount(text)
        if amount is not None:
            candidates.append(amount)

    amount = choose_rain_tip_amount(candidates)
    if amount is None:
        return (
            None,
            "Rain joined box found but tip amount was not parsed "
            f"(match={box_score:.2f}, OCR saw: {' | '.join(previews)})",
        )

    return amount, f"Read rain tip amount: {amount:.2f} scrap"


def read_rain_result_from_screen(allow_full_screen_ocr=True):
    try:
        screenshot = capture_all_monitors_image()
    except (ImportError, ModuleNotFoundError):
        return None, "Windows OCR packages are not installed"
    except Exception as e:
        return None, f"Screenshot failed: {e.__class__.__name__}"

    result_box_detail = None
    for crop in find_rain_result_candidate_crops(screenshot):
        previews = []
        for ocr_crop in build_rain_result_ocr_images(crop):
            try:
                text = run_windows_ocr(ocr_crop)
            except (ImportError, ModuleNotFoundError):
                return None, "Windows OCR packages are not installed"
            except Exception:
                continue

            result = parse_rain_result_summary(text)
            if result is not None:
                return (
                    result,
                    "Read rain result yellow box "
                    f"({result['people_joined']} people, "
                    f"{result['total_scrap_claimed']:.2f} scrap)",
                )
            previews.append(compact_ocr_preview(text))

        if previews:
            result_box_detail = (
                "Rain result yellow box found but summary was not parsed "
                f"(OCR saw: {' | '.join(previews[:2])})"
            )

    if allow_full_screen_ocr:
        try:
            text = run_windows_ocr(screenshot)
        except (ImportError, ModuleNotFoundError):
            return None, "Windows OCR packages are not installed"
        except Exception as e:
            return None, f"Rain result OCR failed: {e.__class__.__name__}"

        result = parse_rain_result_summary(text)
        if result is not None:
            return (
                result,
                "Read rain result summary "
                f"({result['people_joined']} people, "
                f"{result['total_scrap_claimed']:.2f} scrap)",
            )
        text_preview = compact_ocr_preview(text)
    else:
        text_preview = ""

    if result_box_detail:
        return None, result_box_detail

    if allow_full_screen_ocr:
        if find_rain_result_title_match(text or "") is None:
            return None, "Rain result title not visible " f"(OCR saw: {text_preview})"
        return None, "Rain result summary not parsed " f"(OCR saw: {text_preview})"
    return None, "Rain result yellow box not visible"


def parse_battle_discount(text):
    normalized = text.replace("％", "%").replace("O", "0").replace("o", "0")
    match = re.search(r"([0-9]{1,3}(?:[.,][0-9]+)?)\s*%", normalized)
    if not match:
        return None

    try:
        return min(max(float(match.group(1).replace(",", ".")), 0.0), 100.0)
    except ValueError:
        return None


def read_battle_discount_from_screen(screenshot, match, monitor):
    left = max(monitor["left"], match["left"] - 90)
    top = max(monitor["top"], match["top"] - 55)
    right = min(monitor["left"] + monitor["width"], match["left"] + match["width"] + 140)
    bottom = min(monitor["top"] + monitor["height"], match["top"] + match["height"] + 75)

    relative_box = (
        int(left - monitor["left"]),
        int(top - monitor["top"]),
        int(right - monitor["left"]),
        int(bottom - monitor["top"]),
    )

    try:
        crop = screenshot.crop(relative_box)
        text = run_windows_ocr(crop)
    except (ImportError, ModuleNotFoundError):
        return None, "Windows OCR packages are not installed"
    except Exception as e:
        return None, f"OCR failed: {e.__class__.__name__}"

    discount = parse_battle_discount(text)
    if discount is None:
        return None, "No discount percent readable near match"

    return discount, f"Read battle discount: {discount:.0f}%"


def check_bandit_rain_event_http():
    request = urllib.request.Request(
        BANDIT_CAMP_URL,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            html = response.read().decode("utf-8", errors="ignore")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore").lower()
        if e.code == 403 and page_is_cloudflare_challenge(body):
            return None, "Blocked by Cloudflare challenge"
        return None, f"HTTP {e.code}"
    except urllib.error.URLError as e:
        reason = getattr(e, "reason", e)
        return None, f"Connection failed: {reason}"
    except TimeoutError:
        return None, "Connection timed out"

    page = html.lower()
    if page_is_cloudflare_challenge(page):
        return None, "Blocked by Cloudflare challenge"

    is_active = page_has_active_rain_event(page)
    if is_active:
        return True, "Rain event appears active"

    return False, "No active rain event found"


def build_volume_adjusted_wav(sound_path, volume_percent):
    try:
        with wave.open(sound_path, "rb") as wav_file:
            params = wav_file.getparams()
            frames = wav_file.readframes(params.nframes)
    except (wave.Error, OSError):
        return None

    sample_width = params.sampwidth
    if sample_width not in (1, 2, 4):
        return None

    volume_scale = max(0.0, min(float(volume_percent), 100.0)) / 100.0

    if sample_width == 1:
        samples = np.frombuffer(frames, dtype=np.uint8).astype(np.float32)
        adjusted = np.clip(((samples - 128.0) * volume_scale) + 128.0, 0, 255).astype(np.uint8)
    elif sample_width == 2:
        samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32)
        adjusted = np.clip(samples * volume_scale, -32768, 32767).astype(np.int16)
    else:
        samples = np.frombuffer(frames, dtype=np.int32).astype(np.float64)
        adjusted = np.clip(samples * volume_scale, -2147483648, 2147483647).astype(np.int32)

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setparams(params)
        wav_file.writeframes(adjusted.tobytes())
    return buffer.getvalue()


def play_rain_alert_sound(volume_percent=100):
    try:
        if os.path.exists(ALERT_SOUND_PATH):
            if float(volume_percent) >= 99.9:
                winsound.PlaySound(
                    ALERT_SOUND_PATH,
                    winsound.SND_FILENAME | winsound.SND_ASYNC,
                )
            else:
                sound_bytes = build_volume_adjusted_wav(ALERT_SOUND_PATH, volume_percent)
                if sound_bytes is not None:
                    winsound.PlaySound(sound_bytes, winsound.SND_MEMORY)
                else:
                    winsound.PlaySound(
                        ALERT_SOUND_PATH,
                        winsound.SND_FILENAME | winsound.SND_ASYNC,
                    )
        else:
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
    except RuntimeError:
        pass


def check_bandit_rain_event_selenium():
    try:
        from selenium import webdriver
        from selenium.common.exceptions import WebDriverException
        from selenium.webdriver.chrome.options import Options as ChromeOptions
        from selenium.webdriver.edge.options import Options as EdgeOptions
    except ImportError:
        return None, "Selenium is not installed"

    browser_attempts = [
        ("Chrome visible", webdriver.Chrome, ChromeOptions, False),
        ("Edge visible", webdriver.Edge, EdgeOptions, False),
        ("Chrome headless", webdriver.Chrome, ChromeOptions, True),
        ("Edge headless", webdriver.Edge, EdgeOptions, True),
    ]

    last_error = "No browser driver available"
    for browser_name, browser_class, options_class, headless in browser_attempts:
        driver = None
        try:
            options = options_class()
            if headless:
                options.add_argument("--headless=new")
            options.add_argument("--window-size=1280,900")
            options.add_argument("--disable-gpu")

            driver = browser_class(options=options)
            driver.set_page_load_timeout(30)
            driver.get(BANDIT_CAMP_URL)

            deadline = time.time() + SELENIUM_PAGE_WAIT
            page = ""
            visible_text = ""
            while time.time() < deadline:
                page = driver.page_source.lower()
                visible_text = get_browser_visible_text(driver).lower()

                if page_is_cloudflare_challenge(page) or page_is_cloudflare_challenge(visible_text):
                    break

                if not page_is_bandit_loading(visible_text):
                    break

                time.sleep(2)

            combined_page = f"{visible_text}\n{page}"
            if page_is_cloudflare_challenge(combined_page):
                last_error = f"{browser_name} reached Cloudflare challenge"
                continue

            if page_is_bandit_loading(visible_text):
                last_error = f"{browser_name} stayed on Bandit loading screen"
                continue

            if page_has_active_rain_event(combined_page):
                return True, f"{browser_name} found active rain event"

            return False, f"{browser_name} found no active rain event"
        except WebDriverException as e:
            last_error = f"{browser_name} failed: {e.__class__.__name__}"
        finally:
            if driver:
                try:
                    driver.quit()
                except WebDriverException:
                    pass

    return None, last_error


def create_weather_station_driver():
    try:
        from selenium import webdriver
        from selenium.common.exceptions import WebDriverException
        from selenium.webdriver.chrome.options import Options
    except ImportError:
        return None, "Selenium is not installed"

    try:
        options = Options()
        options.add_argument("--window-size=1280,900")
        options.add_argument("--disable-gpu")
        options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(30)
        try:
            driver.execute_cdp_cmd("Network.enable", {})
        except WebDriverException:
            pass
        return driver, "Chrome minimized"
    except ModuleNotFoundError as e:
        missing_module = getattr(e, "name", None) or str(e)
        return None, f"Chrome failed: missing module {missing_module}"
    except WebDriverException as e:
        return None, f"Chrome failed: {e.__class__.__name__}: {e}"
    except Exception as e:
        return None, f"Chrome failed: {e.__class__.__name__}: {e}"


def wait_for_bandit_page(driver, browser_name="Chrome visible", should_continue=None):
    try:
        driver.get(BANDIT_CAMP_URL)

        deadline = time.time() + SELENIUM_PAGE_WAIT
        while time.time() < deadline:
            if should_continue and not should_continue():
                return None, f"{browser_name} check stopped"

            page = driver.page_source.lower()
            visible_text = get_browser_visible_text(driver).lower()

            if page_is_cloudflare_challenge(page) or page_is_cloudflare_challenge(visible_text):
                return None, f"{browser_name} reached Cloudflare challenge"

            if not page_is_bandit_loading(visible_text):
                return True, f"{browser_name} loaded Bandit"

            time.sleep(2)

        return None, f"{browser_name} stayed on Bandit loading screen"
    except Exception as e:
        return None, f"{browser_name} failed: {e.__class__.__name__}"


def get_weather_station_rain_frames(driver):
    rain_events = []

    try:
        logs = driver.get_log("performance")
    except Exception:
        return rain_events

    for entry in logs:
        try:
            message = json.loads(entry["message"])["message"]
        except (KeyError, json.JSONDecodeError):
            continue

        if message.get("method") != "Network.webSocketFrameReceived":
            continue

        payload = message.get("params", {}).get("response", {}).get("payloadData", "")
        if "chat.rain" not in payload:
            continue

        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            continue

        action = data.get("a")
        if not isinstance(action, list) or not action:
            continue

        event_name = action[0]
        if event_name == "chat.rain" and len(action) > 1 and isinstance(action[1], dict):
            rain_events.append(("rain", action[1]))
        elif event_name == "chat.rain.userCount" and len(action) > 1:
            rain_events.append(("user_count", action[1]))

    return rain_events


def check_bandit_rain_event():
    state, detail = check_bandit_rain_event_http()
    if state is not None or "Cloudflare" not in detail:
        return state, detail

    return check_bandit_rain_event_selenium()


# ================= CURSOR MOVEMENT =================

def move_cursor_smooth(x, y, total_time=1.5, steps=100):
    sx, sy = pyautogui.position()

    mx = (sx + x) / 2
    my = (sy + y) / 2

    cx = mx + random.randint(-60, 60)
    cy = my + random.randint(-45, 45)

    start = time.perf_counter()

    for i in range(steps + 1):
        t = i / steps
        eased = 0.5 - 0.5 * math.cos(math.pi * t)

        bx = (1 - eased) ** 2 * sx + 2 * (1 - eased) * eased * cx + eased ** 2 * x
        by = (1 - eased) ** 2 * sy + 2 * (1 - eased) * eased * cy + eased ** 2 * y

        pyautogui.moveTo(int(bx), int(by), duration=0)

        target_time = start + total_time * t
        sleep_time = target_time - time.perf_counter()

        if sleep_time > 0:
            time.sleep(sleep_time)

    pyautogui.moveTo(x, y, duration=0)


def get_random_point_all_monitors(margin=80, avoid_x=None, avoid_y=None, avoid_radius=220):
    with mss.mss() as sct:
        monitor = sct.monitors[0]

    min_x = monitor["left"] + margin
    max_x = monitor["left"] + monitor["width"] - margin
    min_y = monitor["top"] + margin
    max_y = monitor["top"] + monitor["height"] - margin

    if min_x > max_x:
        min_x = monitor["left"]
        max_x = monitor["left"] + monitor["width"] - 1
    if min_y > max_y:
        min_y = monitor["top"]
        max_y = monitor["top"] + monitor["height"] - 1

    for _ in range(40):
        target_x = random.randint(min_x, max_x)
        target_y = random.randint(min_y, max_y)

        if avoid_x is None or avoid_y is None:
            return target_x, target_y

        if math.hypot(target_x - avoid_x, target_y - avoid_y) >= avoid_radius:
            return target_x, target_y

    if avoid_x is None or avoid_y is None:
        return random.randint(min_x, max_x), random.randint(min_y, max_y)

    fallback_x = min_x if avoid_x > (min_x + max_x) // 2 else max_x
    fallback_y = min_y if avoid_y > (min_y + max_y) // 2 else max_y
    return fallback_x, fallback_y


# ================= BACKGROUND =================

def make_background(width, height):
    img = Image.new("RGB", (width, height), COLORS["bg"])
    pixels = img.load()

    for _ in range(width * height // 28):
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        v = random.randint(8, 26)
        pixels[x, y] = (v, max(4, v - 5), max(3, v - 8))

    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)

    cx = width // 2 + 100
    cy = height // 2 + 40

    for r in range(440, 30, -24):
        alpha = max(0, int(70 * (1 - r / 440)))
        gd.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(170, 45, 25, alpha))

    glow = glow.filter(ImageFilter.GaussianBlur(36))
    img = Image.alpha_composite(img.convert("RGBA"), glow)

    return ImageTk.PhotoImage(img)


# ================= CUSTOM BUTTON =================

class BanditButton(ctk.CTkButton):
    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            corner_radius=8,
            height=36,
            fg_color="#1b1f1a",
            hover_color="#2a241f",
            text_color=COLORS["text"],
            border_width=1,
            border_color="#2e2a24",
            font=ctk.CTkFont(family="Impact", size=15),
            **kwargs,
        )


class FastScrollableFrame(ctk.CTkScrollableFrame):
    def _get_fast_scroll_units(self, delta, divisor=6):
        units = int(delta / divisor * SCROLL_WHEEL_SPEED_MULTIPLIER)
        if units == 0 and delta:
            units = 1 if delta > 0 else -1
        return -units

    def _mouse_wheel_all(self, event):
        if not self.check_if_master_is_canvas(event.widget):
            return

        if sys.platform.startswith("win"):
            units = self._get_fast_scroll_units(event.delta, 6)
        elif sys.platform == "darwin":
            units = self._get_fast_scroll_units(event.delta, 1)
        else:
            units = self._get_fast_scroll_units(getattr(event, "delta", 0) or 1, 1)

        if self._shift_pressed:
            if self._parent_canvas.xview() != (0.0, 1.0):
                self._parent_canvas.xview("scroll", units, "units")
        else:
            if self._parent_canvas.yview() != (0.0, 1.0):
                self._parent_canvas.yview("scroll", units, "units")


# ================= UPDATES =================

def split_version(version):
    parts = []
    for part in re.findall(r"\d+", str(version)):
        parts.append(int(part))
    return parts or [0]


def version_is_newer(remote_version, current_version):
    remote = split_version(remote_version)
    current = split_version(current_version)
    length = max(len(remote), len(current))
    remote.extend([0] * (length - len(remote)))
    current.extend([0] * (length - len(current)))
    return remote > current


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def powershell_quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def normalize_confidence_percent(value):
    try:
        confidence = float(value)
    except (TypeError, ValueError, TclError):
        confidence = DEFAULT_CONFIDENCE_PERCENT

    if confidence <= 1.0:
        confidence *= 100

    return min(max(int(round(confidence)), 10), 100)


def clamp_int_setting(value, default, min_value, max_value):
    try:
        setting = int(round(float(value)))
    except (TypeError, ValueError, TclError):
        setting = default

    return min(max(setting, min_value), max_value)


def clamp_float_setting(value, default, min_value, max_value, digits=1):
    try:
        setting = float(value)
    except (TypeError, ValueError, TclError):
        setting = default

    return round(min(max(setting, min_value), max_value), digits)


def format_time_12h(dt=None):
    dt = dt or datetime.now()
    return dt.strftime("%I:%M:%S %p").lstrip("0")


def set_windows_app_user_model_id():
    if sys.platform != "win32":
        return

    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except Exception:
        pass


def bandit_appears_open_in_window_titles():
    if sys.platform != "win32":
        return False

    user32 = ctypes.windll.user32
    titles = []

    def enum_window(hwnd, _):
        try:
            if not user32.IsWindowVisible(hwnd):
                return True

            length = user32.GetWindowTextLengthW(hwnd)
            if length <= 0:
                return True

            buffer = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buffer, length + 1)
            title = buffer.value.strip().lower()
            if title:
                titles.append(title)
        except Exception:
            pass

        return True

    enum_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)(enum_window)
    try:
        user32.EnumWindows(enum_proc, 0)
    except Exception:
        return False

    return any("bandit" in title and ("camp" in title or "bandit.camp" in title) for title in titles)


# ================= APP =================

class App(ctk.CTk):
    def __init__(self):
        set_windows_app_user_model_id()
        super().__init__()

        if not os.path.exists(IMAGE_PATH):
            raise FileNotFoundError(f"Missing image: {IMAGE_PATH}")
        if not os.path.exists(BATTLE_DISCOUNT_IMAGE_PATH):
            raise FileNotFoundError(f"Missing image: {BATTLE_DISCOUNT_IMAGE_PATH}")
        if not os.path.exists(RAIN_JOINED_IMAGE_PATH):
            raise FileNotFoundError(f"Missing image: {RAIN_JOINED_IMAGE_PATH}")

        ctk.set_appearance_mode("dark")

        self.title("Bandit Automation")
        self.apply_window_icon()
        self.geometry("1120x680")
        self.minsize(900, 560)

        self.running = False
        self.closing = False
        self.battle_running = False
        self.battle_thread = None
        self.battle_run_id = 0
        self.weather_station_thread = None
        self.weather_station_driver = None
        self.weather_station_run_id = 0
        self.weather_station_last_state = None
        self.weather_station_status = "Weather station off"
        self.weather_station_started_at = None
        self.current_page = "Rain"
        self.saved_data = self.load_saved_data()
        saved_settings = self.saved_data.get("settings", {})
        saved_stats = self.saved_data.get("stats", {})

        self.confidence = ctk.IntVar(
            value=normalize_confidence_percent(
                saved_settings.get("confidence", DEFAULT_CONFIDENCE_PERCENT)
            )
        )
        self.interval = ctk.IntVar(
            value=clamp_int_setting(
                saved_settings.get("interval", DEFAULT_RAIN_CLICKER_INTERVAL),
                DEFAULT_RAIN_CLICKER_INTERVAL,
                10,
                90,
            )
        )
        self.move_time = ctk.DoubleVar(
            value=clamp_float_setting(
                saved_settings.get("move_time", DEFAULT_MOVE_TIME),
                DEFAULT_MOVE_TIME,
                0.1,
                5.0,
                1,
            )
        )
        self.move_steps = ctk.IntVar(
            value=clamp_int_setting(
                saved_settings.get("move_steps", DEFAULT_MOVE_STEPS),
                DEFAULT_MOVE_STEPS,
                10,
                250,
            )
        )
        self.rain_collect_any_time = ctk.BooleanVar(
            value=saved_settings.get("rain_collect_any_time", DEFAULT_RAIN_COLLECT_ANY_TIME)
        )
        self.rain_collect_start_time = ctk.StringVar(
            value=saved_settings.get("rain_collect_start_time", DEFAULT_RAIN_COLLECT_START_TIME)
        )
        self.rain_collect_end_time = ctk.StringVar(
            value=saved_settings.get("rain_collect_end_time", DEFAULT_RAIN_COLLECT_END_TIME)
        )
        self.rain_collect_chance = ctk.IntVar(
            value=clamp_int_setting(
                saved_settings.get("rain_collect_chance", DEFAULT_RAIN_COLLECT_CHANCE),
                DEFAULT_RAIN_COLLECT_CHANCE,
                0,
                100,
            )
        )
        self.popup_after_rain_wait_seconds = ctk.IntVar(
            value=clamp_int_setting(
                saved_settings.get(
                    "popup_after_rain_wait_seconds",
                    DEFAULT_POPUP_AFTER_RAIN_WAIT_SECONDS,
                ),
                DEFAULT_POPUP_AFTER_RAIN_WAIT_SECONDS,
                5,
                30,
            )
        )
        self.weather_station_interval = ctk.IntVar(
            value=clamp_int_setting(
                saved_settings.get("weather_station_interval", DEFAULT_WEATHER_STATION_INTERVAL),
                DEFAULT_WEATHER_STATION_INTERVAL,
                10,
                90,
            )
        )
        self.weather_notification_volume = ctk.IntVar(
            value=clamp_int_setting(
                saved_settings.get("weather_notification_volume", DEFAULT_WEATHER_NOTIFICATION_VOLUME),
                DEFAULT_WEATHER_NOTIFICATION_VOLUME,
                0,
                100,
            )
        )
        self.weather_station_warn_before_open = ctk.BooleanVar(
            value=saved_settings.get("weather_station_warn_before_open", True)
        )
        self.open_bandit_on_startup = ctk.BooleanVar(
            value=saved_settings.get("open_bandit_on_startup", False)
        )
        self.battle_minimum_discount = ctk.DoubleVar(
            value=saved_settings.get("battle_minimum_discount", 100.0)
        )
        self.battle_free_cases_only = ctk.BooleanVar(
            value=saved_settings.get("battle_free_cases_only", True)
        )
        self.rain_chart_mode = ctk.StringVar(value=saved_settings.get("rain_chart_mode", "Bar"))
        self.weather_station_enabled = ctk.BooleanVar(value=False)
        self.weather_station_active = False
        self.advanced_settings_enabled = ctk.BooleanVar(value=False)
        self.weather_volume_preview_job = None
        self.keep_awake_job = None
        self.check_timer_job = None
        self.check_timer_labels = {}
        self.rain_collector_next_check_at = None
        self.weather_station_next_check_at = None
        self.rain_reward_next_check_at = None
        self.rain_result_next_check_at = None
        self.rain_reward_timer_status = "Off"
        self.rain_result_timer_status = "Off"
        self.update_check_in_progress = False
        self.update_download_in_progress = False
        self.update_status_label = None
        self.update_dialog = None
        self.update_panel_status_label = None
        self.update_progress = None
        self.update_progress_is_indeterminate = False

        self.total_search_time_seconds = float(saved_stats.get("total_search_time_seconds", 0.0))
        self.total_rains_clicked = int(
            saved_stats.get("total_rains_clicked", saved_stats.get("click_count", 0))
        )
        self.total_rain_collected = float(saved_stats.get("total_rain_collected", 0.0))
        self.total_after_rain_popups_clicked = int(
            saved_stats.get("total_after_rain_popups_clicked", 0)
        )
        self.last_rain_reward = float(saved_stats.get("last_rain_reward", 0.0))
        self.rain_reward_history = saved_stats.get("rain_reward_history", [])
        if not isinstance(self.rain_reward_history, list):
            self.rain_reward_history = []
        self.rain_reward_history = self.clean_rain_reward_history(self.rain_reward_history)
        self.rain_result_history = saved_stats.get("rain_result_history", [])
        if not isinstance(self.rain_result_history, list):
            self.rain_result_history = []
        self.rain_result_history = self.clean_rain_result_history(self.rain_result_history)
        self.rain_reward_tracker_active = False
        self.rain_reward_tracker_run_id = 0
        self.rain_result_tracker_active = False
        self.rain_result_tracker_run_id = 0
        self.rain_reward_lock = threading.Lock()
        self.rain_tracking_lock = threading.Lock()
        self.pending_rain_tracking_reward = None
        self.pending_rain_tracking_result = None
        self.pending_rain_tracking_recorded = False
        self.rain_tracking_source = None
        self.rain_tracking_started_at = None
        self.rain_tracking_watch_until = None
        self.current_session_seconds = 0.0
        self.current_session_rains_clicked = 0
        self.current_session_rain_collected = 0.0
        self.current_session_started_at = None
        self.current_session_started_label = "--"
        self.total_weather_station_time_seconds = float(
            saved_stats.get("total_weather_station_time_seconds", 0.0)
        )
        self.total_weather_notifications = int(saved_stats.get("total_weather_notifications", 0))
        self.current_weather_session_seconds = 0.0
        self.current_weather_session_notifications = 0
        self.current_weather_session_started_label = "--"
        self.last_weather_notification_key = saved_stats.get("last_weather_notification_key")
        self.last_action = saved_stats.get("last_action", "--")
        self.last_rain_time = saved_stats.get("last_rain_time", "--")
        self.error_count = saved_stats.get("error_count", 0)

        self.bg_image = None
        self.bg_job = None
        self.hourly_chart_canvas = None
        self.chance_skipped_rain_target = None
        self.pending_rain_total_tipped = None
        self.pending_rain_total_tipped_at = None
        self.pending_rain_total_tipped_verified = False
        self.rain_tip_tracker_active = False
        self.rain_tip_tracker_run_id = 0
        self.rain_log_entries = []
        self.rain_scan_found_last_check = None

        self.build_ui()
        self.show_page("Rain")
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.bind("<Configure>", self.on_resize)

        self.stat_value_labels = {}
        self.active_stats_page = "Rain"
        self.after(500, self.refresh_stats_live)
        self.check_timer_job = self.after(500, self.refresh_check_timer_labels)
        self.after(900, self.open_bandit_on_startup_if_enabled)
        self.after(1500, self.check_for_updates_on_startup)

    def apply_window_icon(self):
        if not os.path.exists(ICON_PATH):
            return

        try:
            self.iconbitmap(ICON_PATH)
        except Exception:
            pass

        try:
            icon_image = Image.open(ICON_PATH)
            self.window_icon_photo = ImageTk.PhotoImage(icon_image)
            self.iconphoto(True, self.window_icon_photo)
        except Exception:
            pass

    # ================= UPDATES =================

    def updates_are_configured(self):
        return (
            UPDATE_MANIFEST_URL.startswith("https://")
            and "YOUR_GITHUB_USERNAME" not in UPDATE_MANIFEST_URL
        )

    def check_for_updates_on_startup(self):
        if self.updates_are_configured():
            self.check_for_updates(silent=True)

    def check_for_updates(self, silent=False):
        if self.update_check_in_progress or self.update_download_in_progress:
            return

        if not self.updates_are_configured():
            if not silent:
                self.show_update_message(
                    "Updates are not configured yet. Set UPDATE_MANIFEST_URL in main.py before building the exe.",
                    COLORS["orange"],
                )
            return

        self.update_check_in_progress = True
        self.show_update_message("Checking for updates...", COLORS["muted"])
        threading.Thread(target=self.update_check_worker, args=(silent,), daemon=True).start()

    def update_check_worker(self, silent):
        try:
            separator = "&" if "?" in UPDATE_MANIFEST_URL else "?"
            manifest_url = f"{UPDATE_MANIFEST_URL}{separator}_={int(time.time())}"
            request = urllib.request.Request(
                manifest_url,
                headers={
                    "User-Agent": f"{APP_NAME}/{APP_VERSION}",
                    "Cache-Control": "no-cache",
                    "Pragma": "no-cache",
                },
            )
            with urllib.request.urlopen(request, timeout=UPDATE_CHECK_TIMEOUT_SECONDS) as response:
                manifest = json.loads(response.read().decode("utf-8", errors="ignore"))

            if not isinstance(manifest, dict):
                raise ValueError("Update manifest is not a JSON object")

            remote_version = str(manifest.get("version", "")).strip()
            update_url = str(manifest.get("url", "")).strip()
            if not remote_version or not update_url:
                raise ValueError("Update manifest needs version and url")

            if version_is_newer(remote_version, APP_VERSION):
                if silent:
                    self.after(
                        0,
                        lambda version=remote_version: self.show_update_message(
                            f"Update {version} is available. Use CHECK FOR UPDATES to install.",
                            COLORS["green"],
                        ),
                    )
                else:
                    self.after(
                        0,
                        lambda version=remote_version: self.show_update_message(
                            f"Update {version} found.",
                            COLORS["green"],
                        ),
                    )
                    self.after(0, lambda data=manifest: self.prompt_update_available(data))
            else:
                self.after(
                    0,
                    lambda version=remote_version: self.show_update_message(
                        f"RainBarrel is up to date ({APP_VERSION}). Latest manifest is {version}.",
                        COLORS["green"],
                    ),
                )
        except Exception as e:
            self.after(
                0,
                lambda error=e: self.show_update_message(
                    f"Update check failed: {error}",
                    COLORS["orange"],
                ),
            )
        finally:
            self.after(0, self.finish_update_check)

    def finish_update_check(self):
        self.update_check_in_progress = False

    def show_update_message(self, text, color=None):
        if hasattr(self, "update_status_label") and self.update_status_label is not None:
            try:
                self.update_status_label.configure(text=text, text_color=color or COLORS["muted"])
            except Exception:
                pass
        if hasattr(self, "update_panel_status_label") and self.update_panel_status_label is not None:
            try:
                if self.update_panel_status_label.winfo_exists():
                    self.update_panel_status_label.configure(
                        text=text,
                        text_color=color or COLORS["muted"],
                    )
            except Exception:
                pass
        self.log(text)

    def prompt_update_available(self, manifest):
        if self.update_download_in_progress:
            return

        version = str(manifest.get("version", "")).strip()
        notes = str(manifest.get("notes", "")).strip()
        if not getattr(sys, "frozen", False):
            self.show_update_message(
                f"Update {version} is available. Build the exe to use automatic install.",
                COLORS["orange"],
            )
            return

        dialog_width = 540
        dialog_height = 340
        dialog = ctk.CTkToplevel(self)
        dialog.geometry(f"{dialog_width}x{dialog_height}")
        dialog.resizable(False, False)
        dialog.title("Update Available")
        dialog.transient(self)
        dialog.configure(fg_color=COLORS["bg"])
        self.update_dialog = dialog

        self.update_idletasks()
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - dialog_width) // 2
        y = self.winfo_y() + (self.winfo_height() - dialog_height) // 2
        dialog.geometry(f"{dialog_width}x{dialog_height}+{max(x, 0)}+{max(y, 0)}")
        dialog.lift()
        dialog.attributes("-topmost", True)
        dialog.after(1200, lambda: dialog.attributes("-topmost", False))

        shell = ctk.CTkFrame(
            dialog,
            fg_color="#151412",
            border_color="#2f1d18",
            border_width=1,
            corner_radius=12,
        )
        shell.pack(fill="both", expand=True, padx=18, pady=18)

        ctk.CTkLabel(
            shell,
            text="UPDATE AVAILABLE",
            text_color=COLORS["red2"],
            font=ctk.CTkFont(family="Impact", size=30),
        ).pack(anchor="w", padx=22, pady=(18, 8))

        ctk.CTkLabel(
            shell,
            text=f"Version {version} is available. You are running {APP_VERSION}.",
            text_color=COLORS["text"],
            font=ctk.CTkFont(size=14, weight="bold"),
            wraplength=455,
            justify="left",
        ).pack(anchor="w", padx=22, pady=(0, 10))

        notes_text = notes or "No update notes were provided."
        ctk.CTkLabel(
            shell,
            text=notes_text,
            text_color=COLORS["muted"],
            font=ctk.CTkFont(size=12),
            wraplength=455,
            justify="left",
        ).pack(anchor="w", fill="x", padx=22, pady=(0, 2))

        self.update_progress = ctk.CTkProgressBar(
            shell,
            progress_color=COLORS["red2"],
        )
        self.update_progress.pack(fill="x", padx=22, pady=(18, 0))
        self.update_progress.set(0)

        self.update_status_label = ctk.CTkLabel(
            shell,
            text="",
            text_color=COLORS["muted"],
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.update_status_label.pack(anchor="w", padx=22, pady=(8, 0))

        button_row = ctk.CTkFrame(shell, fg_color="transparent")
        button_row.pack(fill="x", padx=22, pady=(18, 16))
        button_row.grid_columnconfigure((0, 1), weight=1)

        def clear_update_dialog_refs():
            self.update_status_label = None
            self.update_progress = None
            if self.update_dialog is dialog:
                self.update_dialog = None

        def close_dialog():
            if self.update_download_in_progress:
                self.show_update_message("Update is still downloading...", COLORS["muted"])
                return

            clear_update_dialog_refs()
            try:
                dialog.destroy()
            except Exception:
                pass

        def start_update():
            for child in button_row.winfo_children():
                child.configure(state="disabled")
            self.begin_update_download(manifest)

        BanditButton(
            button_row,
            text="LATER",
            command=close_dialog,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))

        ctk.CTkButton(
            button_row,
            text="UPDATE NOW",
            height=36,
            fg_color=COLORS["green"],
            hover_color="#8dc34b",
            text_color="#111111",
            font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=18,
            command=start_update,
        ).grid(row=0, column=1, sticky="ew", padx=(6, 0))

        dialog.protocol("WM_DELETE_WINDOW", close_dialog)

    def begin_update_download(self, manifest):
        if self.update_download_in_progress:
            return

        self.update_download_in_progress = True
        self.show_update_message("Downloading update...", COLORS["muted"])
        if self.update_progress is not None:
            try:
                self.update_progress.start()
                self.update_progress_is_indeterminate = True
            except Exception:
                self.update_progress = None

        threading.Thread(
            target=self.update_download_worker,
            args=(manifest,),
            daemon=True,
        ).start()

    def update_download_worker(self, manifest):
        try:
            update_url = str(manifest.get("url", "")).strip()
            expected_hash = str(manifest.get("sha256", "")).strip().lower()
            version = str(manifest.get("version", "")).strip()

            updates_dir = os.path.join(tempfile.gettempdir(), APP_NAME, "updates")
            os.makedirs(updates_dir, exist_ok=True)
            downloaded_path = os.path.join(updates_dir, f"{APP_NAME}-{version}.exe")

            request = urllib.request.Request(
                update_url,
                headers={"User-Agent": f"{APP_NAME}/{APP_VERSION}"},
            )
            with urllib.request.urlopen(request, timeout=UPDATE_DOWNLOAD_TIMEOUT_SECONDS) as response:
                total_size = response.headers.get("Content-Length")
                try:
                    total_size = int(total_size) if total_size else None
                except ValueError:
                    total_size = None

                downloaded_size = 0
                with open(downloaded_path, "wb") as file:
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break

                        file.write(chunk)
                        downloaded_size += len(chunk)
                        self.after(
                            0,
                            lambda done=downloaded_size, total=total_size: self.report_update_download_progress(
                                done,
                                total,
                            ),
                        )
                        if total_size and downloaded_size >= total_size:
                            break

            if expected_hash:
                self.after(0, lambda: self.show_update_message("Verifying update...", COLORS["muted"]))
                actual_hash = sha256_file(downloaded_path).lower()
                if actual_hash != expected_hash:
                    raise ValueError("Downloaded update did not match the expected SHA256 hash")

            self.after(0, lambda: self.show_update_message("Preparing installer...", COLORS["muted"]))
            self.after(0, lambda path=downloaded_path: self.try_install_downloaded_update(path))
        except Exception as e:
            self.after(
                0,
                lambda error=e: self.finish_failed_update(f"Update failed: {error}"),
            )

    def finish_failed_update(self, message):
        self.update_download_in_progress = False
        if self.update_progress is not None:
            try:
                self.update_progress.stop()
                self.update_progress.set(0)
            except Exception:
                self.update_progress = None
        self.show_update_message(message, COLORS["orange"])

    def report_update_download_progress(self, downloaded_size, total_size):
        if total_size:
            percent = min(max(downloaded_size / total_size, 0.0), 1.0)
            downloaded_mb = downloaded_size / (1024 * 1024)
            total_mb = total_size / (1024 * 1024)
            text = f"Downloading update... {percent * 100:.0f}% ({downloaded_mb:.1f}/{total_mb:.1f} MB)"

            if self.update_progress is not None:
                try:
                    if self.update_progress_is_indeterminate:
                        self.update_progress.stop()
                        self.update_progress_is_indeterminate = False
                    self.update_progress.set(percent)
                except Exception:
                    self.update_progress = None
        else:
            downloaded_mb = downloaded_size / (1024 * 1024)
            text = f"Downloading update... {downloaded_mb:.1f} MB"

        if self.update_status_label is not None:
            try:
                self.update_status_label.configure(text=text, text_color=COLORS["muted"])
            except Exception:
                self.update_status_label = None

        if self.update_panel_status_label is not None:
            try:
                if self.update_panel_status_label.winfo_exists():
                    self.update_panel_status_label.configure(text=text, text_color=COLORS["muted"])
            except Exception:
                pass

    def try_install_downloaded_update(self, downloaded_path):
        try:
            self.install_downloaded_update(downloaded_path)
        except Exception as e:
            self.finish_failed_update(f"Could not prepare installer: {e}")

    def install_downloaded_update(self, downloaded_path):
        target_path = sys.executable
        target_dir = os.path.dirname(target_path)
        if not os.access(target_dir, os.W_OK):
            self.finish_failed_update(
                "Update downloaded, but this folder is not writable. Move RainBarrel somewhere writable and try again."
            )
            return

        script_path = os.path.join(tempfile.gettempdir(), APP_NAME, "install_update.ps1")
        script = f"""
$ErrorActionPreference = 'Stop'
$processId = {os.getpid()}
$targetPath = {powershell_quote(target_path)}
$targetDir = Split-Path -Parent $targetPath
$downloadedPath = {powershell_quote(downloaded_path)}
$backupPath = "$targetPath.bak"
$logPath = Join-Path (Split-Path -Parent $PSCommandPath) 'update.log'

function Write-UpdateLog($message) {{
    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    Add-Content -LiteralPath $logPath -Value "[$timestamp] $message"
}}

function Invoke-WithRetry($description, [scriptblock]$action) {{
    for ($attempt = 1; $attempt -le 20; $attempt++) {{
        try {{
            & $action
            return
        }} catch {{
            if ($attempt -eq 20) {{
                throw
            }}
            Write-UpdateLog "$description failed on attempt ${{attempt}}: $($_.Exception.Message)"
            Start-Sleep -Milliseconds 500
        }}
    }}
}}

try {{
    Write-UpdateLog "Updater started"
    $deadline = (Get-Date).AddSeconds(20)
    while ((Get-Process -Id $processId -ErrorAction SilentlyContinue) -and ((Get-Date) -lt $deadline)) {{
        Start-Sleep -Milliseconds 250
    }}
    if (Get-Process -Id $processId -ErrorAction SilentlyContinue) {{
        Write-UpdateLog "Old app process $processId did not exit; stopping it"
        Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    }}
    if (Test-Path -LiteralPath $backupPath) {{
        Remove-Item -LiteralPath $backupPath -Force -ErrorAction SilentlyContinue
    }}
    if (Test-Path -LiteralPath $targetPath) {{
        Invoke-WithRetry "Backing up current exe" {{ Move-Item -LiteralPath $targetPath -Destination $backupPath -Force }}
    }}
    Invoke-WithRetry "Installing downloaded exe" {{ Move-Item -LiteralPath $downloadedPath -Destination $targetPath -Force }}

    $env:PYINSTALLER_RESET_ENVIRONMENT = '1'
    Get-ChildItem Env:_PYI_* -ErrorAction SilentlyContinue | Remove-Item -ErrorAction SilentlyContinue
    $ie4uinitPath = Join-Path (Join-Path $env:SystemRoot 'System32') 'ie4uinit.exe'
    if (Test-Path -LiteralPath $ie4uinitPath) {{
        Start-Process -FilePath $ie4uinitPath -ArgumentList '-show' -WindowStyle Hidden -ErrorAction SilentlyContinue
    }}
    Write-UpdateLog "Starting updated app"
    $startedProcess = Start-Process -FilePath $targetPath -WorkingDirectory $targetDir -PassThru
    Start-Sleep -Seconds 3
    if ($startedProcess.HasExited) {{
        Write-UpdateLog "Direct start exited with code $($startedProcess.ExitCode); trying explorer fallback"
        Start-Process -FilePath 'explorer.exe' -ArgumentList $targetPath
    }} else {{
        Write-UpdateLog "Started process id $($startedProcess.Id)"
    }}
    Remove-Item -LiteralPath $backupPath -Force -ErrorAction SilentlyContinue
    Write-UpdateLog "Updater completed"
    Remove-Item -LiteralPath $PSCommandPath -Force -ErrorAction SilentlyContinue
}} catch {{
    Write-UpdateLog "Updater failed: $($_.Exception.Message)"
    if ((Test-Path -LiteralPath $backupPath) -and -not (Test-Path -LiteralPath $targetPath)) {{
        Move-Item -LiteralPath $backupPath -Destination $targetPath -Force -ErrorAction SilentlyContinue
    }}
}}
"""

        try:
            os.makedirs(os.path.dirname(script_path), exist_ok=True)
            with open(script_path, "w", encoding="utf-8") as file:
                file.write(script)

            flags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
            subprocess.Popen(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    script_path,
                ],
                creationflags=flags,
            )
        except Exception as e:
            self.finish_failed_update(f"Could not start updater: {e}")
            return

        self.show_update_message("Installing update. RainBarrel will restart now...", COLORS["green"])
        if self.update_progress is not None:
            try:
                self.update_progress.stop()
                self.update_progress.set(1)
            except Exception:
                self.update_progress = None
        self.after(800, self.on_close)

    # ================= PERSISTENCE =================

    def load_saved_data(self):
        paths = [DATA_PATH]
        if DEFAULT_DATA_PATH != DATA_PATH:
            paths.append(DEFAULT_DATA_PATH)

        for path in paths:
            if not os.path.exists(path):
                continue

            try:
                with open(path, "r", encoding="utf-8") as file:
                    data = json.load(file)
                    if isinstance(data, dict):
                        return data
            except (OSError, json.JSONDecodeError):
                continue

        return {}

    def get_setting_value(self, variable, default):
        try:
            return variable.get()
        except (TclError, ValueError):
            return default

    def get_current_settings(self):
        return {
            "confidence": normalize_confidence_percent(
                self.get_setting_value(self.confidence, DEFAULT_CONFIDENCE_PERCENT)
            ),
            "interval": clamp_int_setting(
                self.get_setting_value(self.interval, DEFAULT_RAIN_CLICKER_INTERVAL),
                DEFAULT_RAIN_CLICKER_INTERVAL,
                10,
                90,
            ),
            "move_time": clamp_float_setting(
                self.get_setting_value(self.move_time, DEFAULT_MOVE_TIME),
                DEFAULT_MOVE_TIME,
                0.1,
                5.0,
                1,
            ),
            "move_steps": clamp_int_setting(
                self.get_setting_value(self.move_steps, DEFAULT_MOVE_STEPS),
                DEFAULT_MOVE_STEPS,
                10,
                250,
            ),
            "rain_collect_any_time": bool(self.rain_collect_any_time.get()),
            "rain_collect_start_time": self.rain_collect_start_time.get(),
            "rain_collect_end_time": self.rain_collect_end_time.get(),
            "rain_collect_chance": clamp_int_setting(
                self.get_setting_value(self.rain_collect_chance, DEFAULT_RAIN_COLLECT_CHANCE),
                DEFAULT_RAIN_COLLECT_CHANCE,
                0,
                100,
            ),
            "popup_after_rain_wait_seconds": clamp_int_setting(
                self.get_setting_value(
                    self.popup_after_rain_wait_seconds,
                    DEFAULT_POPUP_AFTER_RAIN_WAIT_SECONDS,
                ),
                DEFAULT_POPUP_AFTER_RAIN_WAIT_SECONDS,
                5,
                30,
            ),
            "weather_station_interval": clamp_int_setting(
                self.get_setting_value(
                    self.weather_station_interval,
                    DEFAULT_WEATHER_STATION_INTERVAL,
                ),
                DEFAULT_WEATHER_STATION_INTERVAL,
                10,
                90,
            ),
            "weather_notification_volume": clamp_int_setting(
                self.get_setting_value(
                    self.weather_notification_volume,
                    DEFAULT_WEATHER_NOTIFICATION_VOLUME,
                ),
                DEFAULT_WEATHER_NOTIFICATION_VOLUME,
                0,
                100,
            ),
            "weather_station_warn_before_open": bool(self.weather_station_warn_before_open.get()),
            "open_bandit_on_startup": bool(self.open_bandit_on_startup.get()),
            "battle_minimum_discount": round(float(self.battle_minimum_discount.get()), 1),
            "battle_free_cases_only": bool(self.battle_free_cases_only.get()),
            "rain_chart_mode": self.get_rain_chart_mode(),
        }

    def get_current_stats(self):
        return {
            "total_search_time_seconds": round(self.get_total_search_time_seconds(), 1),
            "total_rains_clicked": int(self.total_rains_clicked),
            "total_rain_collected": round(self.total_rain_collected, 2),
            "total_after_rain_popups_clicked": int(self.total_after_rain_popups_clicked),
            "last_rain_reward": round(self.last_rain_reward, 2),
            "rain_reward_history": self.rain_reward_history[-RAIN_REWARD_HISTORY_LIMIT:],
            "rain_result_history": self.rain_result_history[-RAIN_REWARD_HISTORY_LIMIT:],
            "current_session_seconds": round(self.get_current_session_seconds(), 1),
            "current_session_rains_clicked": int(self.current_session_rains_clicked),
            "current_session_rain_collected": round(self.current_session_rain_collected, 2),
            "current_session_started_label": self.current_session_started_label,
            "total_weather_station_time_seconds": round(self.get_total_weather_station_time_seconds(), 1),
            "total_weather_notifications": int(self.total_weather_notifications),
            "current_weather_session_seconds": round(self.get_current_weather_session_seconds(), 1),
            "current_weather_session_notifications": int(self.current_weather_session_notifications),
            "current_weather_session_started_label": self.current_weather_session_started_label,
            "last_weather_notification_key": self.last_weather_notification_key,
            "last_rain_time": self.last_rain_time,
            "last_action": self.last_action,
            "error_count": int(self.error_count),
        }

    def clean_rain_reward_history(self, history):
        cleaned = []

        for item in history:
            if not isinstance(item, dict):
                continue

            timestamp = item.get("time")
            amount = item.get("amount")
            if timestamp is None or amount is None:
                continue

            try:
                datetime.strptime(str(timestamp), "%Y-%m-%d %H:%M:%S")
                amount = round(float(amount), 2)
            except (TypeError, ValueError):
                continue

            cleaned.append({"time": str(timestamp), "amount": amount})

        return cleaned[-RAIN_REWARD_HISTORY_LIMIT:]

    def clean_rain_result_history(self, history):
        cleaned = []

        for item in history:
            if not isinstance(item, dict):
                continue

            try:
                timestamp = str(item.get("time"))
                datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                people_joined = int(item.get("people_joined"))
                total_scrap_claimed = round(float(item.get("total_scrap_claimed")), 2)
                your_reward = round(float(item.get("your_reward", 0.0)), 2)
            except (TypeError, ValueError):
                continue

            if people_joined <= 0 or total_scrap_claimed <= 0:
                continue

            total_tipped = parse_scrap_number(item.get("total_tipped"))
            total_tipped_verified = bool(item.get("total_tipped_verified", total_tipped is not None))
            cleaned.append(
                {
                    "time": timestamp,
                    "people_joined": people_joined,
                    "total_scrap_claimed": total_scrap_claimed,
                    "total_tipped": total_tipped,
                    "total_tipped_verified": total_tipped_verified,
                    "your_reward": your_reward,
                }
            )

        return cleaned[-RAIN_REWARD_HISTORY_LIMIT:]

    def save_data(self):
        data = {
            "settings": self.get_current_settings(),
            "stats": self.get_current_stats(),
        }

        try:
            with open(DATA_PATH, "w", encoding="utf-8") as file:
                json.dump(data, file, indent=2)
            return True
        except OSError:
            return False

    def normalize_time_setting(self, value):
        value = str(value).strip()
        if not value:
            return None

        compact_value = value.upper().replace(" ", "")
        formats = [
            ("%H:%M", value),
            ("%H", value),
            ("%I:%M %p", value.upper()),
            ("%I %p", value.upper()),
            ("%I:%M%p", compact_value),
            ("%I%p", compact_value),
        ]

        for time_format, candidate in formats:
            try:
                parsed = datetime.strptime(candidate, time_format)
                return parsed.strftime("%H:%M")
            except ValueError:
                continue

        return None

    def time_setting_to_minutes(self, value):
        normalized = self.normalize_time_setting(value)
        if not normalized:
            return None

        hour, minute = normalized.split(":")
        return int(hour) * 60 + int(minute)

    def rain_collection_time_allowed(self):
        if self.rain_collect_any_time.get():
            return True

        start_minutes = self.time_setting_to_minutes(self.rain_collect_start_time.get())
        end_minutes = self.time_setting_to_minutes(self.rain_collect_end_time.get())
        if start_minutes is None or end_minutes is None:
            return False

        now = datetime.now()
        current_minutes = now.hour * 60 + now.minute
        if start_minutes <= end_minutes:
            return start_minutes <= current_minutes <= end_minutes

        return current_minutes >= start_minutes or current_minutes <= end_minutes

    def rain_collection_chance_allowed(self, x, y):
        skipped = self.chance_skipped_rain_target
        if skipped and math.hypot(x - skipped[0], y - skipped[1]) < 30:
            return False

        chance = self.get_rain_collect_chance()
        if chance <= 0:
            self.chance_skipped_rain_target = (x, y)
            return False

        if chance >= 100:
            self.chance_skipped_rain_target = None
            return True

        if random.uniform(0, 100) <= chance:
            self.chance_skipped_rain_target = None
            return True

        self.chance_skipped_rain_target = (x, y)
        return False

    def rain_collection_allowed(self, x, y):
        if not self.rain_collection_time_allowed():
            return False, "Skipped rain target image outside rain collection time"

        if not self.rain_collection_chance_allowed(x, y):
            chance = self.get_rain_collect_chance()
            return False, f"Skipped rain target image by collection chance ({chance:.0f}%)"

        return True, ""

    def get_confidence(self):
        return normalize_confidence_percent(
            self.get_setting_value(self.confidence, DEFAULT_CONFIDENCE_PERCENT)
        ) / 100.0

    def get_rain_collect_chance(self):
        return clamp_int_setting(
            self.get_setting_value(self.rain_collect_chance, DEFAULT_RAIN_COLLECT_CHANCE),
            DEFAULT_RAIN_COLLECT_CHANCE,
            0,
            100,
        )

    def get_interval_seconds(self):
        return clamp_int_setting(
            self.get_setting_value(self.interval, DEFAULT_RAIN_CLICKER_INTERVAL),
            DEFAULT_RAIN_CLICKER_INTERVAL,
            10,
            90,
        )

    def get_popup_after_rain_wait_seconds(self):
        return clamp_int_setting(
            self.get_setting_value(
                self.popup_after_rain_wait_seconds,
                DEFAULT_POPUP_AFTER_RAIN_WAIT_SECONDS,
            ),
            DEFAULT_POPUP_AFTER_RAIN_WAIT_SECONDS,
            5,
            30,
        )

    def get_move_time(self):
        return clamp_float_setting(
            self.get_setting_value(self.move_time, DEFAULT_MOVE_TIME),
            DEFAULT_MOVE_TIME,
            0.1,
            5.0,
            1,
        )

    def get_move_steps(self):
        return clamp_int_setting(
            self.get_setting_value(self.move_steps, DEFAULT_MOVE_STEPS),
            DEFAULT_MOVE_STEPS,
            10,
            250,
        )

    def sleep_with_check_timer(self, attr_name, seconds, should_continue=None):
        seconds = max(0.0, float(seconds))
        deadline = time.time() + seconds
        setattr(self, attr_name, deadline)

        while time.time() < deadline:
            if should_continue is not None and not should_continue():
                return False
            time.sleep(min(0.25, max(0.0, deadline - time.time())))

        if should_continue is not None and not should_continue():
            return False

        setattr(self, attr_name, time.time())
        return True

    def set_confidence_percent(self, value):
        self.confidence.set(normalize_confidence_percent(value))

    def set_interval_setting(self, value):
        self.interval.set(clamp_int_setting(value, DEFAULT_RAIN_CLICKER_INTERVAL, 10, 90))

    def set_rain_collect_chance(self, value):
        self.rain_collect_chance.set(clamp_int_setting(value, DEFAULT_RAIN_COLLECT_CHANCE, 0, 100))

    def set_move_time_setting(self, value):
        self.move_time.set(clamp_float_setting(value, DEFAULT_MOVE_TIME, 0.1, 5.0, 1))

    def set_move_steps_setting(self, value):
        self.move_steps.set(clamp_int_setting(value, DEFAULT_MOVE_STEPS, 10, 250))

    def set_weather_station_interval_setting(self, value):
        self.weather_station_interval.set(
            clamp_int_setting(value, DEFAULT_WEATHER_STATION_INTERVAL, 10, 90)
        )

    def set_weather_notification_volume(self, value):
        self.weather_notification_volume.set(
            clamp_int_setting(value, DEFAULT_WEATHER_NOTIFICATION_VOLUME, 0, 100)
        )

    def set_popup_after_rain_wait_seconds(self, value):
        self.popup_after_rain_wait_seconds.set(
            clamp_int_setting(value, DEFAULT_POPUP_AFTER_RAIN_WAIT_SECONDS, 5, 30)
        )

    def apply_rain_settings(self):
        self.set_confidence_percent(
            self.get_setting_value(self.confidence, DEFAULT_CONFIDENCE_PERCENT)
        )
        self.set_interval_setting(
            self.get_setting_value(self.interval, DEFAULT_RAIN_CLICKER_INTERVAL)
        )
        self.set_move_time_setting(self.get_setting_value(self.move_time, DEFAULT_MOVE_TIME))
        self.set_move_steps_setting(self.get_setting_value(self.move_steps, DEFAULT_MOVE_STEPS))
        self.set_rain_collect_chance(
            self.get_setting_value(self.rain_collect_chance, DEFAULT_RAIN_COLLECT_CHANCE)
        )
        self.set_popup_after_rain_wait_seconds(
            self.get_setting_value(
                self.popup_after_rain_wait_seconds,
                DEFAULT_POPUP_AFTER_RAIN_WAIT_SECONDS,
            )
        )
        self.set_weather_station_interval_setting(
            self.get_setting_value(
                self.weather_station_interval,
                DEFAULT_WEATHER_STATION_INTERVAL,
            )
        )
        self.set_weather_notification_volume(
            self.get_setting_value(
                self.weather_notification_volume,
                DEFAULT_WEATHER_NOTIFICATION_VOLUME,
            )
        )

        start_time = self.normalize_time_setting(self.rain_collect_start_time.get())
        end_time = self.normalize_time_setting(self.rain_collect_end_time.get())
        if not self.rain_collect_any_time.get() and (not start_time or not end_time):
            message = "Use a valid rain time like 09:30 or 9:30 PM"
            if hasattr(self, "settings_status_label"):
                self.settings_status_label.configure(text=message, text_color=COLORS["red2"])
            self.log(message)
            return

        self.rain_collect_start_time.set(start_time or "00:00")
        self.rain_collect_end_time.set(end_time or "23:59")
        self.sync_rain_time_window_controls()

        saved = self.save_data()
        message = "Settings applied" if saved else "Save failed"
        if hasattr(self, "settings_status_label"):
            self.settings_status_label.configure(
                text=message,
                text_color=COLORS["green"] if saved else COLORS["red2"],
            )

        self.log(message)
        self.refresh_stats_now()

    def apply_battle_settings(self):
        self.battle_minimum_discount.set(
            min(max(float(self.battle_minimum_discount.get()), 0.0), 100.0)
        )

        saved = self.save_data()
        message = "Battle settings applied" if saved else "Save failed"
        if hasattr(self, "battle_settings_status_label"):
            self.battle_settings_status_label.configure(
                text=message,
                text_color=COLORS["green"] if saved else COLORS["red2"],
            )

        self.battle_log(message)
        self.refresh_stats_now()

    def preview_weather_notification_volume(self, value):
        self.set_weather_notification_volume(value)

        if self.weather_volume_preview_job:
            self.after_cancel(self.weather_volume_preview_job)

        self.weather_volume_preview_job = self.after(150, self.play_weather_volume_preview)

    def play_weather_volume_preview(self):
        self.weather_volume_preview_job = None
        try:
            winsound.PlaySound(None, winsound.SND_PURGE)
        except RuntimeError:
            pass

        threading.Thread(
            target=play_rain_alert_sound,
            args=(
                clamp_int_setting(
                    self.get_setting_value(
                        self.weather_notification_volume,
                        DEFAULT_WEATHER_NOTIFICATION_VOLUME,
                    ),
                    DEFAULT_WEATHER_NOTIFICATION_VOLUME,
                    0,
                    100,
                ),
            ),
            daemon=True,
        ).start()

    def toggle_rain_collect_any_time(self):
        self.sync_rain_time_window_controls()
        self.apply_rain_settings()

    def show_rain_settings_message(self, message, color=None):
        if hasattr(self, "settings_status_label"):
            self.settings_status_label.configure(
                text=message,
                text_color=color or COLORS["muted"],
            )

    def open_bandit_website(self, auto=False):
        if auto and not self.open_bandit_on_startup.get():
            return False

        if auto and bandit_appears_open_in_window_titles():
            message = "Bandit.camp already appears open"
            self.show_rain_settings_message(message, COLORS["muted"])
            self.log(message)
            return False

        try:
            opened = webbrowser.open(BANDIT_CAMP_URL, new=2)
        except Exception as e:
            message = f"Could not open Bandit.camp: {e.__class__.__name__}"
            self.show_rain_settings_message(message, COLORS["red2"])
            self.log(message)
            return False

        message = "Opened Bandit.camp" if opened else "Sent Bandit.camp open request"
        self.show_rain_settings_message(message, COLORS["green"])
        self.log(message)
        return True

    def open_bandit_on_startup_if_enabled(self):
        self.open_bandit_website(auto=True)

    def toggle_open_bandit_on_startup(self):
        saved = self.save_data()
        message = "Bandit startup setting saved" if saved else "Save failed"
        self.show_rain_settings_message(
            message,
            COLORS["green"] if saved else COLORS["red2"],
        )
        self.log(message)

    def reset_default_settings(self):
        self.confidence.set(DEFAULT_CONFIDENCE_PERCENT)
        self.interval.set(DEFAULT_RAIN_CLICKER_INTERVAL)
        self.move_time.set(DEFAULT_MOVE_TIME)
        self.move_steps.set(DEFAULT_MOVE_STEPS)
        self.rain_collect_any_time.set(DEFAULT_RAIN_COLLECT_ANY_TIME)
        self.rain_collect_start_time.set(DEFAULT_RAIN_COLLECT_START_TIME)
        self.rain_collect_end_time.set(DEFAULT_RAIN_COLLECT_END_TIME)
        self.rain_collect_chance.set(DEFAULT_RAIN_COLLECT_CHANCE)
        self.popup_after_rain_wait_seconds.set(DEFAULT_POPUP_AFTER_RAIN_WAIT_SECONDS)
        self.weather_station_interval.set(DEFAULT_WEATHER_STATION_INTERVAL)
        self.weather_notification_volume.set(DEFAULT_WEATHER_NOTIFICATION_VOLUME)
        self.weather_station_warn_before_open.set(True)
        self.open_bandit_on_startup.set(False)
        self.sync_rain_time_window_controls()

        saved = self.save_data()
        message = "Default settings restored" if saved else "Save failed"
        self.show_rain_settings_message(
            message,
            COLORS["green"] if saved else COLORS["red2"],
        )
        self.log(message)

    def get_total_search_time_seconds(self):
        if self.running and self.current_session_started_at is not None:
            return self.total_search_time_seconds + (time.time() - self.current_session_started_at)
        return self.total_search_time_seconds

    def get_current_session_seconds(self):
        if self.running and self.current_session_started_at is not None:
            return self.current_session_seconds + (time.time() - self.current_session_started_at)
        return self.current_session_seconds

    def finalize_active_session_time(self):
        if self.current_session_started_at is None:
            return

        elapsed = max(0.0, time.time() - self.current_session_started_at)
        self.total_search_time_seconds += elapsed
        self.current_session_seconds += elapsed
        self.current_session_started_at = None

    def start_rain_session(self):
        self.current_session_seconds = 0.0
        self.current_session_rains_clicked = 0
        self.current_session_rain_collected = 0.0
        self.current_session_started_at = time.time()
        self.current_session_started_label = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def stop_rain_session(self):
        self.finalize_active_session_time()

    def get_total_weather_station_time_seconds(self):
        if self.weather_station_active and self.weather_station_started_at is not None:
            return self.total_weather_station_time_seconds + (time.time() - self.weather_station_started_at)
        return self.total_weather_station_time_seconds

    def get_current_weather_session_seconds(self):
        if self.weather_station_active and self.weather_station_started_at is not None:
            return self.current_weather_session_seconds + (time.time() - self.weather_station_started_at)
        return self.current_weather_session_seconds

    def start_weather_station_timer(self):
        if self.weather_station_started_at is None:
            self.current_weather_session_seconds = 0.0
            self.current_weather_session_notifications = 0
            self.current_weather_session_started_label = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.weather_station_started_at = time.time()

    def stop_weather_station_timer(self):
        if self.weather_station_started_at is None:
            return

        elapsed = max(0.0, time.time() - self.weather_station_started_at)
        self.total_weather_station_time_seconds += elapsed
        self.current_weather_session_seconds += elapsed
        self.weather_station_started_at = None

    def format_duration(self, total_seconds):
        total_seconds = max(0, int(total_seconds))
        days, remainder = divmod(total_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        parts = []
        if days:
            parts.append(f"{days}D")
        if hours:
            parts.append(f"{hours}H")
        if minutes:
            parts.append(f"{minutes}M")
        if seconds or not parts:
            parts.append(f"{seconds}S")
        return " ".join(parts)

    def format_countdown(self, next_check_at, active, status=None):
        if not active:
            return "Off"

        if status:
            return status

        if next_check_at is None:
            return "Checking now"

        remaining = int(math.ceil(next_check_at - time.time()))
        if remaining <= 0:
            return "Checking now"

        return f"{remaining}s"

    def get_check_timer_values(self):
        return {
            "rain_collector": self.format_countdown(
                self.rain_collector_next_check_at,
                self.running,
            ),
            "weather_station": self.format_countdown(
                self.weather_station_next_check_at,
                self.weather_station_active,
            ),
            "reward_checker": self.format_countdown(
                self.rain_reward_next_check_at,
                self.rain_reward_tracker_active,
                self.rain_reward_timer_status
                if self.rain_reward_tracker_active and self.rain_reward_timer_status != "Off"
                else None,
            ),
            "result_checker": self.format_countdown(
                self.rain_result_next_check_at,
                self.rain_result_tracker_active,
                self.rain_result_timer_status
                if self.rain_result_tracker_active and self.rain_result_timer_status != "Off"
                else None,
            ),
        }

    def refresh_check_timer_labels(self):
        if self.closing:
            return

        values = self.get_check_timer_values()
        stale_keys = []

        for key, label in self.check_timer_labels.items():
            try:
                if not label.winfo_exists():
                    stale_keys.append(key)
                    continue
                label.configure(text=values.get(key, "Off"))
            except (TclError, RuntimeError):
                stale_keys.append(key)

        for key in stale_keys:
            self.check_timer_labels.pop(key, None)

        self.check_timer_job = self.after(500, self.refresh_check_timer_labels)

    def format_last_rain_detected(self):
        if not self.last_rain_time or self.last_rain_time == "--":
            return "--"

        try:
            detected_at = datetime.strptime(self.last_rain_time, "%Y-%m-%d %H:%M:%S")
        except (TypeError, ValueError):
            return str(self.last_rain_time)

        return detected_at.strftime("%I:%M %p").lstrip("0").lower()

    def format_rain_amount(self, amount):
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            return "0"

        if amount.is_integer():
            return str(int(amount))
        return f"{amount:.2f}"

    def get_average_rain_collected_per_hour(self):
        active_hours = self.get_total_search_time_seconds() / 3600
        if active_hours <= 0:
            return 0.0
        return self.total_rain_collected / active_hours

    def format_rain_amount_per_hour(self, amount):
        return f"{self.format_rain_amount(amount)}/H"

    def format_optional_rain_amount(self, amount):
        if amount is None or amount == "":
            return "--"

        return self.format_rain_amount(amount)

    def get_hourly_rain_values(self):
        hourly_values = [[] for _ in range(24)]

        for item in self.rain_reward_history:
            if not isinstance(item, dict):
                continue

            timestamp = item.get("time")
            amount = item.get("amount")
            if timestamp is None or amount is None:
                continue

            try:
                hour = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S").hour
                value = float(amount)
            except (TypeError, ValueError):
                continue

            hourly_values[hour].append(value)

        return hourly_values

    def get_typical_hourly_value(self, values):
        if not values:
            return None

        values = sorted(values)
        midpoint = (len(values) - 1) // 2
        return values[midpoint]

    def format_hour_label(self, hour):
        suffix = "AM" if hour < 12 else "PM"
        display_hour = hour % 12
        if display_hour == 0:
            display_hour = 12
        return f"{display_hour}{suffix}"

    def get_rain_chart_mode(self):
        mode = self.rain_chart_mode.get()
        if mode not in ("Bar", "Line"):
            mode = "Bar"
            self.rain_chart_mode.set(mode)
        return mode

    def set_rain_chart_mode(self, mode):
        if mode not in ("Bar", "Line"):
            mode = "Bar"

        self.rain_chart_mode.set(mode)
        self.save_data()
        if self.hourly_chart_canvas is not None:
            self.draw_hourly_rain_chart(self.hourly_chart_canvas)

    def get_hourly_rain_averages(self):
        return [
            self.get_typical_hourly_value(values)
            for values in self.get_hourly_rain_values()
        ]

    def build_hourly_rain_chart(self, parent):
        card = ctk.CTkFrame(
            parent,
            fg_color="#151412",
            border_color="#2f1d18",
            border_width=1,
            corner_radius=10,
        )
        card.pack(fill="x", padx=34, pady=12)

        ctk.CTkLabel(
            card,
            text="TYPICAL RAIN COLLECTED BY HOUR",
            text_color=COLORS["red2"],
            font=ctk.CTkFont(family="Impact", size=26),
        ).pack(anchor="w", padx=26, pady=(18, 10))

        mode_row = ctk.CTkFrame(card, fg_color="transparent")
        mode_row.pack(fill="x", padx=26, pady=(0, 10))

        ctk.CTkLabel(
            mode_row,
            text="GRAPH",
            text_color=COLORS["muted"],
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(side="left")

        ctk.CTkSegmentedButton(
            mode_row,
            values=["Bar", "Line"],
            variable=self.rain_chart_mode,
            command=self.set_rain_chart_mode,
            selected_color=COLORS["red"],
            selected_hover_color="#b83928",
            unselected_color="#1b1f1a",
            unselected_hover_color="#2a241f",
            text_color=COLORS["text"],
        ).pack(side="right")

        averages = self.get_hourly_rain_averages()
        populated_values = [value for value in averages if value is not None]

        if not populated_values:
            ctk.CTkLabel(
                card,
                text="No rain collection history yet.",
                text_color=COLORS["muted"],
                font=ctk.CTkFont(size=13),
            ).pack(anchor="w", padx=26, pady=(0, 22))
            return

        canvas = ctk.CTkCanvas(
            card,
            height=282,
            highlightthickness=0,
            bg="#110f0e",
        )
        canvas.pack(fill="x", padx=18, pady=(0, 18))
        self.hourly_chart_canvas = canvas
        canvas.bind("<Configure>", lambda event: self.draw_hourly_rain_chart(canvas))
        self.after(0, lambda: self.draw_hourly_rain_chart(canvas))

    def draw_hourly_rain_chart(self, canvas):
        try:
            if not canvas.winfo_exists():
                return
        except Exception:
            return

        averages = self.get_hourly_rain_averages()
        populated_values = [value for value in averages if value is not None]
        if not populated_values:
            return

        canvas.delete("all")

        canvas_width = max(canvas.winfo_width(), 420)
        canvas_height = max(canvas.winfo_height(), 240)
        left_pad = 52
        right_pad = 22
        top_pad = 28
        bottom_pad = 58
        chart_height = canvas_height - top_pad - bottom_pad
        chart_width = canvas_width - left_pad - right_pad
        slot_width = chart_width / 24
        max_value = max(populated_values) or 1.0

        axis_color = "#3a2b26"
        label_color = COLORS["muted"]
        bar_color = COLORS["red2"]
        muted_bar = "#2a201d"
        line_color = COLORS["green"]
        baseline_y = canvas_height - bottom_pad
        mode = self.get_rain_chart_mode()

        canvas.create_line(left_pad, top_pad, left_pad, baseline_y, fill=axis_color, width=1)
        canvas.create_line(
            left_pad,
            baseline_y,
            canvas_width - right_pad,
            baseline_y,
            fill=axis_color,
            width=1,
        )
        canvas.create_text(
            left_pad,
            top_pad - 10,
            text=self.format_rain_amount(max_value),
            fill=label_color,
            anchor="w",
            font=("Segoe UI", 8),
        )

        line_points = []

        for index, average in enumerate(averages):
            x0 = left_pad + index * slot_width + max(2, slot_width * 0.12)
            x1 = left_pad + (index + 1) * slot_width - max(2, slot_width * 0.12)
            center_x = (x0 + x1) / 2

            if average is not None:
                bar_height = max(5, (average / max_value) * chart_height)
                y0 = baseline_y - bar_height
                line_points.append((center_x, y0, average))
                if mode == "Bar":
                    canvas.create_rectangle(x0, y0, x1, baseline_y, fill=bar_color, outline="")
            else:
                bar_height = 3
                y0 = baseline_y - bar_height
                if mode == "Bar":
                    canvas.create_rectangle(x0, y0, x1, baseline_y, fill=muted_bar, outline="")

            if mode == "Bar" and average is not None:
                canvas.create_text(
                    center_x,
                    max(top_pad + 8, y0 - 11),
                    text=self.format_rain_amount(average),
                    fill=COLORS["text"],
                    font=("Segoe UI", 9, "bold"),
                )

            if index % 3 == 0 or index == 23:
                canvas.create_text(
                    center_x,
                    canvas_height - 18,
                    text=self.format_hour_label(index),
                    fill=label_color,
                    font=("Segoe UI", 8),
                )

        if mode == "Line" and line_points:
            for first, second in zip(line_points, line_points[1:]):
                canvas.create_line(
                    first[0],
                    first[1],
                    second[0],
                    second[1],
                    fill=line_color,
                    width=3,
                    smooth=True,
                )

            for center_x, y, average in line_points:
                canvas.create_oval(
                    center_x - 4,
                    y - 4,
                    center_x + 4,
                    y + 4,
                    fill=COLORS["red2"],
                    outline=COLORS["text"],
                    width=1,
                )
                canvas.create_text(
                    center_x,
                    max(top_pad + 8, y - 13),
                    text=self.format_rain_amount(average),
                    fill=COLORS["text"],
                    font=("Segoe UI", 9, "bold"),
                )

    def reset_stats(self):
        self.total_search_time_seconds = 0.0
        self.total_rains_clicked = 0
        self.total_rain_collected = 0.0
        self.total_after_rain_popups_clicked = 0
        self.last_rain_reward = 0.0
        self.rain_reward_history = []
        self.rain_result_history = []
        self.last_weather_notification_key = None
        self.last_rain_time = "--"
        self.last_action = "--"
        self.error_count = 0
        self.total_weather_station_time_seconds = 0.0
        self.total_weather_notifications = 0

        if self.running:
            self.start_rain_session()
        else:
            self.current_session_seconds = 0.0
            self.current_session_rains_clicked = 0
            self.current_session_rain_collected = 0.0
            self.current_session_started_label = "--"

        if self.weather_station_active:
            self.current_weather_session_seconds = 0.0
            self.current_weather_session_notifications = 0
            self.current_weather_session_started_label = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.weather_station_started_at = time.time()
        else:
            self.current_weather_session_seconds = 0.0
            self.current_weather_session_notifications = 0
            self.current_weather_session_started_label = "--"

        self.save_stats()
        if self.current_page == "Stats":
            self.stats_page(self.active_stats_page)
        self.log("Stats reset")

    def apply_imported_stats(self, stats):
        self.total_search_time_seconds = float(stats.get("total_search_time_seconds", 0.0))
        self.total_rains_clicked = int(stats.get("total_rains_clicked", stats.get("click_count", 0)))
        self.total_rain_collected = float(stats.get("total_rain_collected", 0.0))
        self.total_after_rain_popups_clicked = int(
            stats.get("total_after_rain_popups_clicked", 0)
        )
        self.last_rain_reward = float(stats.get("last_rain_reward", 0.0))
        self.rain_reward_history = self.clean_rain_reward_history(stats.get("rain_reward_history", []))
        self.rain_result_history = self.clean_rain_result_history(stats.get("rain_result_history", []))
        self.total_weather_station_time_seconds = float(stats.get("total_weather_station_time_seconds", 0.0))
        self.total_weather_notifications = int(stats.get("total_weather_notifications", 0))
        self.last_weather_notification_key = stats.get("last_weather_notification_key")
        self.last_rain_time = stats.get("last_rain_time", "--")
        self.last_action = stats.get("last_action", "Stats imported")
        self.error_count = int(stats.get("error_count", 0))

        if self.running:
            self.start_rain_session()
        else:
            self.current_session_seconds = float(stats.get("current_session_seconds", 0.0))
            self.current_session_rains_clicked = int(stats.get("current_session_rains_clicked", 0))
            self.current_session_rain_collected = float(stats.get("current_session_rain_collected", 0.0))
            self.current_session_started_label = stats.get("current_session_started_label", "--")

        if self.weather_station_active:
            self.current_weather_session_seconds = 0.0
            self.current_weather_session_notifications = 0
            self.current_weather_session_started_label = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.weather_station_started_at = time.time()
        else:
            self.current_weather_session_seconds = float(stats.get("current_weather_session_seconds", 0.0))
            self.current_weather_session_notifications = int(stats.get("current_weather_session_notifications", 0))
            self.current_weather_session_started_label = stats.get("current_weather_session_started_label", "--")

    def export_stats(self):
        path = filedialog.asksaveasfilename(
            title="Export RainBarrel stats",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile=f"rainbarrel_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        )
        if not path:
            return

        data = {
            "app": APP_NAME,
            "version": APP_VERSION,
            "exported_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "stats": self.get_current_stats(),
        }

        try:
            with open(path, "w", encoding="utf-8") as file:
                json.dump(data, file, indent=2)
        except OSError as e:
            self.log(f"Stats export failed: {e.__class__.__name__}")
            return

        self.log(f"Stats exported to {path}")

    def import_stats(self):
        path = filedialog.askopenfilename(
            title="Import RainBarrel stats",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError) as e:
            self.log(f"Stats import failed: {e.__class__.__name__}")
            return

        stats = data.get("stats", data) if isinstance(data, dict) else None
        if not isinstance(stats, dict):
            self.log("Stats import failed: no stats object found")
            return

        try:
            self.apply_imported_stats(stats)
        except (TypeError, ValueError) as e:
            self.log(f"Stats import failed: {e.__class__.__name__}")
            return

        self.save_stats()
        if self.current_page == "Stats":
            self.stats_page(self.active_stats_page)
        self.log(f"Stats imported from {path}")

    def save_stats(self):
        self.save_data()
        self.refresh_topbar_total()
        self.after(0, self.refresh_stats_now)

    def record_rain_detected(self, source):
        self.last_rain_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.last_action = f"Rain detected by {source}"
        self.save_stats()

    def get_rain_tracking_watch_until(self):
        with self.rain_tracking_lock:
            return self.rain_tracking_watch_until or 0.0

    def start_rain_trackers(self, source="rain tracker"):
        now = time.time()
        watch_until = now + RAIN_TRACKER_WATCH_SECONDS
        with self.rain_reward_lock:
            already_running = (
                self.rain_tip_tracker_active
                or self.rain_reward_tracker_active
                or self.rain_result_tracker_active
            )
            existing_source = self.rain_tracking_source or "another source"

        if already_running:
            with self.rain_tracking_lock:
                previous_watch_until = self.rain_tracking_watch_until or 0.0
                self.rain_tracking_watch_until = max(previous_watch_until, watch_until)
                if self.rain_tracking_source and source not in self.rain_tracking_source:
                    self.rain_tracking_source = f"{self.rain_tracking_source} + {source}"
            extended_by = max(0, int(self.rain_tracking_watch_until - previous_watch_until))
            if extended_by > 0:
                remaining = max(0, int(self.rain_tracking_watch_until - time.time()))
                self.log(
                    f"Rain trackers already running from {existing_source}; "
                    f"{source} extended tracking by {extended_by}s "
                    f"(watching {remaining}s more)"
                )
            else:
                self.log(f"Rain trackers already running from {existing_source}; {source} trigger reused")
            return False

        with self.rain_tracking_lock:
            self.pending_rain_tracking_reward = None
            self.pending_rain_tracking_result = None
            self.pending_rain_tracking_recorded = False
            self.pending_rain_total_tipped = None
            self.pending_rain_total_tipped_at = None
            self.pending_rain_total_tipped_verified = False
            self.rain_tracking_source = source
            self.rain_tracking_started_at = now
            self.rain_tracking_watch_until = watch_until

        with self.rain_reward_lock:
            self.rain_tip_tracker_run_id += 1
            tip_run_id = self.rain_tip_tracker_run_id
            self.rain_reward_tracker_run_id += 1
            reward_run_id = self.rain_reward_tracker_run_id
            self.rain_result_tracker_run_id += 1
            result_run_id = self.rain_result_tracker_run_id
            self.rain_tip_tracker_active = True
            self.rain_reward_tracker_active = True
            self.rain_result_tracker_active = True
            self.rain_reward_next_check_at = time.time()
            self.rain_result_next_check_at = time.time()
            self.rain_reward_timer_status = ""
            self.rain_result_timer_status = ""

        self.log(f"Rain trackers started by {source}; watching for {RAIN_TRACKER_WATCH_SECONDS}s")
        self.log("Rain tip tracker started")
        self.log("Rain reward tracker started")
        self.log("Rain result tracker started")
        threading.Thread(
            target=self.rain_tip_tracker_worker,
            args=(tip_run_id,),
            daemon=True,
        ).start()
        threading.Thread(
            target=self.rain_reward_tracker_worker,
            args=(reward_run_id,),
            daemon=True,
        ).start()
        threading.Thread(
            target=self.rain_result_tracker_worker,
            args=(result_run_id,),
            daemon=True,
        ).start()
        return True

    def maybe_record_pending_rain_result(self):
        with self.rain_tracking_lock:
            if self.pending_rain_tracking_recorded:
                return
            if self.pending_rain_tracking_reward is None or self.pending_rain_tracking_result is None:
                return
            if self.rain_tip_tracker_active:
                return

            reward = self.pending_rain_tracking_reward
            summary = self.pending_rain_tracking_result
            self.pending_rain_tracking_recorded = True

        self.after(
            0,
            lambda summary=summary, reward=reward: self.record_rain_result(summary, reward),
        )

    def rain_tip_tracker_worker(self, run_id):
        last_detail = None
        last_tipped = None
        last_tipped_verified = False
        candidate_tipped = None
        candidate_count = 0
        read_counts = {}
        read_last_seen = {}
        recent_reads = []
        read_index = 0
        misses_after_found = 0
        tip_parse_warning_logged = False

        try:
            while time.time() < self.get_rain_tracking_watch_until() and run_id == self.rain_tip_tracker_run_id:
                amount, detail = read_rain_tip_amount_from_screen()
                if (
                    amount is None
                    and not tip_parse_warning_logged
                    and detail.startswith("Rain joined box found")
                ):
                    tip_parse_warning_logged = True
                    self.log(detail)

                if amount is not None:
                    tipped = round(float(amount), 2)
                    tipped_cents = rain_tip_cents(tipped)
                    read_index += 1
                    read_counts[tipped_cents] = read_counts.get(tipped_cents, 0) + 1
                    read_last_seen[tipped_cents] = read_index
                    recent_reads.append(tipped_cents)
                    recent_reads = recent_reads[-RAIN_TIP_RECENT_WINDOW:]
                    if candidate_tipped == tipped:
                        candidate_count += 1
                    else:
                        candidate_tipped = tipped
                        candidate_count = 1
                    confirmations_needed = RAIN_TIP_READING_CONFIRMATIONS
                    if last_tipped is not None:
                        if tipped < last_tipped:
                            confirmations_needed = RAIN_TIP_DROP_CONFIRMATIONS
                        elif tipped > last_tipped:
                            jump = tipped - last_tipped
                            jump_ratio = jump / max(last_tipped, 1.0)
                            if jump >= RAIN_TIP_LARGE_JUMP_MIN_SCRAP or jump_ratio >= RAIN_TIP_LARGE_JUMP_RATIO:
                                confirmations_needed = RAIN_TIP_LARGE_JUMP_CONFIRMATIONS

                    history_can_reclaim = False
                    if last_tipped is not None and tipped != last_tipped:
                        last_cents = rain_tip_cents(last_tipped)
                        tipped_seen = read_counts.get(tipped_cents, 0)
                        last_seen = read_counts.get(last_cents, 0)
                        history_can_reclaim = (
                            candidate_count >= RAIN_TIP_HISTORY_RECLAIM_CONFIRMATIONS
                            and tipped_seen >= last_seen + RAIN_TIP_HISTORY_RECLAIM_MARGIN
                        )

                    recent_count = recent_reads.count(tipped_cents)
                    recent_can_confirm = recent_count >= confirmations_needed

                    if tipped != last_tipped and candidate_count < confirmations_needed:
                        if not history_can_reclaim and not recent_can_confirm:
                            last_detail = f"Confirming rain tipped amount: {self.format_rain_amount(tipped)} scrap"
                            time.sleep(RAIN_TIP_SCAN_INTERVAL_SECONDS)
                            continue
                    misses_after_found = 0
                    last_tipped_verified = True
                    with self.rain_tracking_lock:
                        self.pending_rain_total_tipped = tipped
                        self.pending_rain_total_tipped_at = time.time()
                        self.pending_rain_total_tipped_verified = True
                    if last_tipped is None:
                        self.log(f"Tracked rain tipped amount: {self.format_rain_amount(tipped)} scrap")
                    elif tipped != last_tipped:
                        self.log(f"Updated rain tipped amount: {self.format_rain_amount(tipped)} scrap")
                    last_tipped = tipped
                else:
                    if last_tipped is not None and "not found" in detail.lower():
                        misses_after_found += 1
                        if misses_after_found >= RAIN_TIP_MISSES_AFTER_FOUND_TO_STOP:
                            break
                    with self.rain_tracking_lock:
                        rain_end_seen = (
                            self.pending_rain_tracking_reward is not None
                            and self.pending_rain_tracking_result is not None
                        )
                    if rain_end_seen:
                        break

                last_detail = detail
                time.sleep(RAIN_TIP_SCAN_INTERVAL_SECONDS)

            final_cents, final_verified = choose_final_rain_tip_cents(
                read_counts,
                rain_tip_cents(last_tipped) if last_tipped is not None else None,
                read_last_seen,
            )
            if final_cents is not None:
                final_tipped = rain_tip_amount_from_cents(final_cents)
                with self.rain_tracking_lock:
                    self.pending_rain_total_tipped = final_tipped
                    self.pending_rain_total_tipped_at = time.time()
                    self.pending_rain_total_tipped_verified = bool(final_verified)
                if last_tipped is None or final_tipped != last_tipped:
                    self.log(f"Final rain tipped consensus: {self.format_rain_amount(final_tipped)} scrap")
                last_tipped = final_tipped
                last_tipped_verified = bool(final_verified)

            if run_id == self.rain_tip_tracker_run_id and last_tipped is not None:
                suffix = "" if last_tipped_verified else " (unverified)"
                self.log(f"Rain tip tracker finished with {self.format_rain_amount(last_tipped)} scrap{suffix}")
                self.log(f"Rain tip read counts: {format_rain_tip_read_counts(read_counts)}")
            elif run_id == self.rain_tip_tracker_run_id and last_detail:
                self.log(f"Rain tip tracker stopped: {last_detail}")
        finally:
            with self.rain_reward_lock:
                if run_id == self.rain_tip_tracker_run_id:
                    self.rain_tip_tracker_active = False
            self.maybe_record_pending_rain_result()

    def rain_reward_tracker_worker(self, run_id):
        last_detail = None
        reward_parse_warning_logged = False

        try:
            while time.time() < self.get_rain_tracking_watch_until() and run_id == self.rain_reward_tracker_run_id:
                self.rain_reward_next_check_at = time.time()
                self.rain_reward_timer_status = ""

                amount, detail = read_rain_reward_amount_from_screen()
                if (
                    amount is None
                    and not reward_parse_warning_logged
                    and detail.startswith("Reward popup image found")
                ):
                    reward_parse_warning_logged = True
                    self.log(detail)

                if amount is not None:
                    own_reward = round(float(amount), 2)
                    self.rain_reward_next_check_at = None
                    self.rain_reward_timer_status = "Reward found"
                    self.log(detail)
                    with self.rain_tracking_lock:
                        self.pending_rain_tracking_reward = own_reward
                    self.after(0, lambda value=own_reward: self.record_rain_reward(value))
                    self.maybe_record_pending_rain_result()
                    return

                last_detail = detail
                self.rain_reward_next_check_at = time.time() + RAIN_REWARD_SCAN_INTERVAL_SECONDS
                time.sleep(RAIN_REWARD_SCAN_INTERVAL_SECONDS)

            if run_id == self.rain_reward_tracker_run_id and last_detail:
                self.log(f"Rain reward tracker stopped: {last_detail}")
        finally:
            with self.rain_reward_lock:
                if run_id == self.rain_reward_tracker_run_id:
                    self.rain_reward_tracker_active = False
                    self.rain_reward_next_check_at = None
                    self.rain_reward_timer_status = "Off"

    def rain_result_tracker_worker(self, run_id):
        last_detail = None
        scan_count = 0
        result_parse_warning_logged = False

        try:
            while time.time() < self.get_rain_tracking_watch_until() and run_id == self.rain_result_tracker_run_id:
                self.rain_result_next_check_at = time.time()
                self.rain_result_timer_status = ""

                scan_count += 1
                result, detail = read_rain_result_from_screen(
                    allow_full_screen_ocr=scan_count % RAIN_RESULT_FULL_SCREEN_OCR_EVERY == 0
                )
                if (
                    result is None
                    and not result_parse_warning_logged
                    and detail.startswith("Rain result yellow box found")
                ):
                    result_parse_warning_logged = True
                    self.log(detail)

                if result is not None:
                    with self.rain_tracking_lock:
                        self.pending_rain_tracking_result = result
                    self.rain_result_next_check_at = None
                    self.rain_result_timer_status = "Result found"
                    self.log(f"Rain result summary found: {detail}")
                    self.maybe_record_pending_rain_result()
                    return

                last_detail = detail
                self.rain_result_next_check_at = time.time() + RAIN_RESULT_SCAN_INTERVAL_SECONDS
                time.sleep(RAIN_RESULT_SCAN_INTERVAL_SECONDS)

            if run_id == self.rain_result_tracker_run_id and last_detail:
                self.log(f"Rain result tracker stopped after {scan_count} scans: {last_detail}")
        finally:
            with self.rain_reward_lock:
                if run_id == self.rain_result_tracker_run_id:
                    self.rain_result_tracker_active = False
                    self.rain_result_next_check_at = None
                    self.rain_result_timer_status = "Off"

    def record_rain_reward(self, amount):
        amount = round(float(amount), 2)
        now = datetime.now()

        self.total_rain_collected += amount
        self.current_session_rain_collected += amount
        self.last_rain_reward = amount
        self.rain_reward_history.append(
            {
                "time": now.strftime("%Y-%m-%d %H:%M:%S"),
                "amount": amount,
            }
        )
        self.rain_reward_history = self.rain_reward_history[-RAIN_REWARD_HISTORY_LIMIT:]
        self.last_action = f"Collected {self.format_rain_amount(amount)} scrap"
        self.save_stats()
        self.log(f"Tracked rain reward: {self.format_rain_amount(amount)} scrap")
        if self.current_page == "Stats" and self.active_stats_page == "Rain":
            self.stats_page("Rain")

    def record_rain_result(self, summary, your_reward):
        now = datetime.now()
        total_tipped = summary.get("total_tipped")
        with self.rain_tracking_lock:
            pending_total_tipped = self.pending_rain_total_tipped
            pending_total_tipped_at = self.pending_rain_total_tipped_at
            pending_total_tipped_verified = self.pending_rain_total_tipped_verified
        total_tipped_verified = total_tipped is not None
        if total_tipped is None and pending_total_tipped is not None:
            if pending_total_tipped_at is None or time.time() - pending_total_tipped_at < RAIN_REWARD_WATCH_SECONDS:
                total_tipped = pending_total_tipped
                total_tipped_verified = bool(pending_total_tipped_verified)

        item = {
            "time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "people_joined": int(summary["people_joined"]),
            "total_scrap_claimed": round(float(summary["total_scrap_claimed"]), 2),
            "total_tipped": parse_scrap_number(total_tipped),
            "total_tipped_verified": total_tipped_verified,
            "your_reward": round(float(your_reward), 2),
        }

        self.rain_result_history.append(item)
        self.rain_result_history = self.rain_result_history[-RAIN_REWARD_HISTORY_LIMIT:]
        self.last_action = "Tracked rain result"
        self.save_stats()
        self.log(
            "Tracked rain result: "
            f"{item['people_joined']} people | "
            f"tipped {self.format_optional_rain_amount(item['total_tipped'])}"
            f"{'' if item['total_tipped_verified'] else ' (unverified)'} | "
            f"collected {self.format_rain_amount(item['total_scrap_claimed'])} | "
            f"you got {self.format_rain_amount(item['your_reward'])}"
        )
        if self.current_page == "Stats" and self.active_stats_page == "Rain":
            self.stats_page("Rain")

    def parse_saved_timestamp(self, value):
        try:
            return datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S")
        except (TypeError, ValueError):
            return None

    def remove_matching_rain_reward_for_result(self, result_item):
        reward_amount = parse_scrap_number(result_item.get("your_reward"))
        result_time = self.parse_saved_timestamp(result_item.get("time"))
        if reward_amount is None or not self.rain_reward_history:
            return None

        best_index = None
        best_time_delta = None
        for index, reward_item in enumerate(self.rain_reward_history):
            amount = parse_scrap_number(reward_item.get("amount"))
            if amount is None or abs(amount - reward_amount) > 0.001:
                continue

            reward_time = self.parse_saved_timestamp(reward_item.get("time"))
            if result_time is not None and reward_time is not None:
                time_delta = abs((result_time - reward_time).total_seconds())
                if time_delta > RAIN_TRACKER_WATCH_SECONDS:
                    continue
            else:
                time_delta = 0

            if best_index is None or time_delta < best_time_delta:
                best_index = index
                best_time_delta = time_delta

        if best_index is None:
            return None

        return self.rain_reward_history.pop(best_index)

    def recalculate_rain_reward_stats(self):
        self.total_rain_collected = round(
            sum(
                parse_scrap_number(item.get("amount")) or 0.0
                for item in self.rain_reward_history
            ),
            2,
        )
        self.last_rain_reward = (
            parse_scrap_number(self.rain_reward_history[-1].get("amount")) or 0.0
            if self.rain_reward_history
            else 0.0
        )

        session_start = None
        if self.current_session_started_at is not None:
            session_start = datetime.fromtimestamp(self.current_session_started_at)
        else:
            session_start = self.parse_saved_timestamp(self.current_session_started_label)

        if session_start is not None:
            self.current_session_rain_collected = round(
                sum(
                    parse_scrap_number(item.get("amount")) or 0.0
                    for item in self.rain_reward_history
                    if (
                        self.parse_saved_timestamp(item.get("time")) is not None
                        and self.parse_saved_timestamp(item.get("time")) >= session_start
                    )
                ),
                2,
            )
        elif not self.running:
            self.current_session_rain_collected = 0.0

    def delete_rain_result(self, history_index):
        if history_index < 0 or history_index >= len(self.rain_result_history):
            return

        removed_result = self.rain_result_history.pop(history_index)
        removed_reward = self.remove_matching_rain_reward_for_result(removed_result)
        self.recalculate_rain_reward_stats()
        self.last_action = "Deleted rain result"
        self.save_stats()

        reward_detail = ""
        if removed_reward is not None:
            removed_amount = parse_scrap_number(removed_reward.get("amount")) or 0.0
            reward_detail = f" and removed matching reward {self.format_rain_amount(removed_amount)}"

        self.log(
            "Deleted rain result: "
            f"{removed_result.get('people_joined', '--')} people | "
            f"you got {self.format_rain_amount(removed_result.get('your_reward', 0.0))}"
            f"{reward_detail}"
        )

        if self.current_page == "Stats" and self.active_stats_page == "Rain":
            self.stats_page("Rain")
        self.refresh_stats_now()

    def refresh_keep_awake_state(self):
        flags = ES_CONTINUOUS
        if self.running or self.weather_station_active or self.battle_running:
            flags |= ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED

        try:
            ctypes.windll.kernel32.SetThreadExecutionState(flags)
        except Exception:
            pass

        if self.keep_awake_job:
            self.after_cancel(self.keep_awake_job)
            self.keep_awake_job = None

        if self.running or self.weather_station_active or self.battle_running:
            self.keep_awake_job = self.after(45000, self.refresh_keep_awake_state)

    def close_driver_async(self, driver):
        if driver is None:
            return

        def close_driver():
            try:
                driver.quit()
            except Exception:
                pass

        threading.Thread(target=close_driver, daemon=True).start()

    def on_close(self):
        if self.closing:
            return

        self.closing = True
        self.running = False
        self.battle_running = False
        self.battle_run_id += 1

        driver = self.weather_station_driver
        self.weather_station_driver = None
        self.weather_station_active = False
        self.weather_station_run_id += 1
        self.rain_tip_tracker_active = False
        self.rain_tip_tracker_run_id += 1
        self.rain_reward_tracker_active = False
        self.rain_result_tracker_active = False
        self.rain_reward_tracker_run_id += 1
        self.rain_result_tracker_run_id += 1
        self.rain_tracking_watch_until = None
        self.rain_collector_next_check_at = None
        self.weather_station_next_check_at = None
        self.rain_reward_next_check_at = None
        self.rain_result_next_check_at = None
        self.rain_reward_timer_status = "Off"
        self.rain_result_timer_status = "Off"

        try:
            self.weather_station_enabled.set(False)
        except Exception:
            pass

        if self.keep_awake_job:
            try:
                self.after_cancel(self.keep_awake_job)
            except Exception:
                pass
            self.keep_awake_job = None

        if self.check_timer_job:
            try:
                self.after_cancel(self.check_timer_job)
            except Exception:
                pass
            self.check_timer_job = None

        try:
            self.stop_rain_session()
            self.stop_weather_station_timer()
            self.refresh_keep_awake_state()
            self.save_data()
        except Exception:
            pass

        self.close_driver_async(driver)

        try:
            self.destroy()
        except Exception:
            try:
                self.quit()
            except Exception:
                pass

    # ================= UI BUILD =================

    def build_ui(self):
        self.canvas = ctk.CTkCanvas(self, highlightthickness=0, bg=COLORS["bg"])
        self.canvas.pack(fill="both", expand=True)

        self.bg_id = self.canvas.create_image(0, 0, anchor="nw")

        self.topbar = ctk.CTkFrame(self.canvas, height=58, fg_color=COLORS["top"], corner_radius=0)
        self.topbar_id = self.canvas.create_window(0, 0, anchor="nw", window=self.topbar)

        self.left_panel_container = ctk.CTkFrame(
            self.canvas,
            width=285,
            fg_color=COLORS["side"],
            border_color="#161a16",
            border_width=1,
            corner_radius=0,
        )
        self.left_id = self.canvas.create_window(0, 58, anchor="nw", window=self.left_panel_container)

        self.left_panel = FastScrollableFrame(
            self.left_panel_container,
            width=285,
            height=622,
            fg_color=COLORS["side"],
            corner_radius=0,
            scrollbar_button_color="#2e2a24",
            scrollbar_button_hover_color="#453931",
        )
        self.left_panel.pack(fill="both", expand=True)

        self.content = ctk.CTkFrame(
            self.canvas,
            fg_color="transparent",
            corner_radius=0,
        )
        self.content_id = self.canvas.create_window(285, 58, anchor="nw", window=self.content)

        self.build_topbar()

        self.after(100, self.force_resize)

    def build_topbar(self):
        logo = ctk.CTkLabel(
            self.topbar,
            text="BANDIT",
            text_color=COLORS["red"],
            font=ctk.CTkFont(family="Impact", size=34, weight="bold"),
        )
        logo.pack(side="left", padx=(18, 24))

        self.nav_buttons = {}

        for page in ["Rain", "Battles", "Stats"]:
            btn = BanditButton(
                self.topbar,
                text=page.upper(),
                command=lambda p=page: self.show_page(p),
            )
            btn.pack(side="left", padx=6)
            self.nav_buttons[page] = btn

        self.toggle_btn = ctk.CTkButton(
            self.topbar,
            text="START",
            width=105,
            height=36,
            fg_color=COLORS["green"],
            hover_color="#8dc34b",
            text_color="#111111",
            font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=18,
            command=self.toggle,
        )
        self.toggle_btn.pack(side="right", padx=(8, 18), pady=10)

        self.status_pill = ctk.CTkLabel(
            self.topbar,
            text="OFFLINE",
            fg_color="#2c2c2c",
            text_color=COLORS["text"],
            corner_radius=18,
            width=90,
            height=30,
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.status_pill.pack(side="right", padx=8, pady=10)

        self.topbar_total_label = ctk.CTkLabel(
            self.topbar,
            text=self.get_topbar_total_text(),
            fg_color="#181412",
            text_color=COLORS["red2"],
            corner_radius=16,
            width=150,
            height=30,
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.topbar_total_label.pack(side="right", padx=(8, 4), pady=10)

    def get_topbar_total_text(self):
        return f"TOTAL RAIN {self.format_rain_amount(self.total_rain_collected)}"

    def refresh_topbar_total(self):
        if hasattr(self, "topbar_total_label"):
            self.topbar_total_label.configure(text=self.get_topbar_total_text())

    def build_stats_left_panel(self):
        ctk.CTkLabel(
            self.left_panel,
            text="STATS",
            text_color=COLORS["red2"],
            font=ctk.CTkFont(family="Impact", size=24),
        ).pack(anchor="w", padx=18, pady=(20, 8))

        ctk.CTkLabel(
            self.left_panel,
            text="Select a stats page",
            text_color=COLORS["muted"],
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w", padx=18, pady=(0, 16))

        for page in ["Rain", "Battles"]:
            BanditButton(
                self.left_panel,
                text=page.upper(),
                command=lambda p=page: self.stats_page(p)
            ).pack(fill="x", padx=18, pady=8)

    def build_battles_left_panel(self):
        ctk.CTkLabel(
            self.left_panel,
            text="BATTLES",
            text_color=COLORS["red2"],
            font=ctk.CTkFont(family="Impact", size=24),
        ).pack(anchor="w", padx=18, pady=(20, 8))

        ctk.CTkLabel(
            self.left_panel,
            text="Battle finder settings",
            text_color=COLORS["muted"],
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w", padx=18, pady=(0, 16))

        self.add_setting(
            "Minimum Discount",
            self.battle_minimum_discount,
            0,
            100,
        )

        self.battle_free_cases_switch = ctk.CTkSwitch(
            self.left_panel,
            text="FREE CASES ONLY",
            variable=self.battle_free_cases_only,
            command=self.apply_battle_settings,
            onvalue=True,
            offvalue=False,
            fg_color="#3a3a3a",
            progress_color=COLORS["green"],
            button_color="#d8d2ca",
            button_hover_color="#ffffff",
            text_color=COLORS["text"],
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.battle_free_cases_switch.pack(anchor="w", padx=18, pady=(2, 14))

        BanditButton(
            self.left_panel,
            text="APPLY",
            command=self.apply_battle_settings,
        ).pack(fill="x", padx=18, pady=(4, 6))

        self.battle_settings_status_label = ctk.CTkLabel(
            self.left_panel,
            text="Free cases only requires a 100% discount.",
            text_color=COLORS["muted"],
            font=ctk.CTkFont(size=12, weight="bold"),
            wraplength=230,
            justify="left",
        )
        self.battle_settings_status_label.pack(anchor="w", padx=18, pady=(0, 8))

    def build_rain_left_panel(self):
        ctk.CTkLabel(
            self.left_panel,
            text="RAIN SETTINGS",
            text_color=COLORS["red2"],
            font=ctk.CTkFont(family="Impact", size=24),
        ).pack(anchor="w", padx=18, pady=(20, 8))

        ctk.CTkLabel(
            self.left_panel,
            text="Weather station controls",
            text_color=COLORS["muted"],
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w", padx=18, pady=(0, 16))

        self.weather_station_switch = ctk.CTkSwitch(
            self.left_panel,
            text="WEATHER STATION",
            variable=self.weather_station_enabled,
            command=self.toggle_weather_station,
            onvalue=True,
            offvalue=False,
            fg_color="#3a3a3a",
            progress_color=COLORS["green"],
            button_color="#d8d2ca",
            button_hover_color="#ffffff",
            text_color=COLORS["text"],
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.weather_station_switch.pack(anchor="w", padx=18, pady=(0, 12))

        self.weather_station_status_label = ctk.CTkLabel(
            self.left_panel,
            text=self.weather_station_status,
            text_color=COLORS["muted"],
            font=ctk.CTkFont(size=12),
            wraplength=230,
        )
        self.weather_station_status_label.pack(anchor="w", padx=18, pady=(0, 12))

        self.add_setting(
            "Weather Notification Volume",
            self.weather_notification_volume,
            0,
            100,
            command=self.preview_weather_notification_volume,
            step=1,
        )

        ctk.CTkFrame(self.left_panel, height=1, fg_color="#24201d").pack(fill="x", padx=18, pady=14)

        ctk.CTkLabel(
            self.left_panel,
            text="Rain collection controls",
            text_color=COLORS["muted"],
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w", padx=18, pady=(0, 16))

        self.add_setting(
            "Rain Collection Chance",
            self.rain_collect_chance,
            0,
            100,
            command=self.set_rain_collect_chance,
            step=1,
        )

        self.rain_collect_any_time_switch = ctk.CTkSwitch(
            self.left_panel,
            text="COLLECT ANY TIME",
            variable=self.rain_collect_any_time,
            command=self.toggle_rain_collect_any_time,
            onvalue=True,
            offvalue=False,
            fg_color="#3a3a3a",
            progress_color=COLORS["green"],
            button_color="#d8d2ca",
            button_hover_color="#ffffff",
            text_color=COLORS["text"],
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.rain_collect_any_time_switch.pack(anchor="w", padx=18, pady=(2, 10))

        self.add_rain_time_window_setting()

        self.advanced_settings_btn = BanditButton(
            self.left_panel,
            text=self.get_advanced_settings_button_text(),
            command=self.toggle_advanced_settings,
        )
        self.advanced_settings_btn.pack(fill="x", padx=18, pady=(4, 6))

        if self.advanced_settings_enabled.get():
            self.add_setting(
                "Confidence Percent",
                self.confidence,
                10,
                100,
                command=self.set_confidence_percent,
                step=1,
            )
            self.add_setting(
                "Rain Clicker Check Delay",
                self.interval,
                10,
                90,
                command=self.set_interval_setting,
                step=1,
            )
            self.add_setting(
                "After-Click Popup Watch Seconds",
                self.popup_after_rain_wait_seconds,
                5,
                30,
                command=self.set_popup_after_rain_wait_seconds,
                step=1,
            )
            self.add_setting(
                "Move Time",
                self.move_time,
                0.1,
                5.0,
                command=self.set_move_time_setting,
                step=0.1,
            )
            self.add_setting(
                "Move Steps",
                self.move_steps,
                10,
                250,
                command=self.set_move_steps_setting,
                step=1,
            )
            self.add_setting(
                "Weather Station Check Interval",
                self.weather_station_interval,
                10,
                90,
                command=self.set_weather_station_interval_setting,
                step=1,
            )
            self.add_check_timer_panel()

        BanditButton(
            self.left_panel,
            text="APPLY",
            command=self.apply_rain_settings,
        ).pack(fill="x", padx=18, pady=(12, 6))

        BanditButton(
            self.left_panel,
            text="RESET DEFAULT SETTINGS",
            command=self.reset_default_settings,
        ).pack(fill="x", padx=18, pady=(0, 6))

        self.settings_status_label = ctk.CTkLabel(
            self.left_panel,
            text="",
            text_color=COLORS["muted"],
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.settings_status_label.pack(anchor="w", padx=18, pady=(0, 8))

        ctk.CTkFrame(self.left_panel, height=1, fg_color="#24201d").pack(fill="x", padx=18, pady=18)

        ctk.CTkLabel(
            self.left_panel,
            text="APP",
            text_color=COLORS["orange"],
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(anchor="w", padx=18)

        ctk.CTkLabel(
            self.left_panel,
            text=f"Version {APP_VERSION}",
            text_color=COLORS["text"],
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w", padx=18, pady=(4, 8))

        BanditButton(
            self.left_panel,
            text="OPEN BANDIT.CAMP",
            command=self.open_bandit_website,
        ).pack(fill="x", padx=18, pady=(0, 8))

        self.open_bandit_startup_switch = ctk.CTkSwitch(
            self.left_panel,
            text="OPEN BANDIT ON STARTUP",
            variable=self.open_bandit_on_startup,
            command=self.toggle_open_bandit_on_startup,
            onvalue=True,
            offvalue=False,
            fg_color="#3a3a3a",
            progress_color=COLORS["green"],
            button_color="#d8d2ca",
            button_hover_color="#ffffff",
            text_color=COLORS["text"],
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.open_bandit_startup_switch.pack(anchor="w", padx=18, pady=(0, 12))

        BanditButton(
            self.left_panel,
            text="CHECK FOR UPDATES",
            command=lambda: self.check_for_updates(silent=False),
        ).pack(fill="x", padx=18, pady=(0, 8))

        self.update_panel_status_label = ctk.CTkLabel(
            self.left_panel,
            text="",
            text_color=COLORS["muted"],
            font=ctk.CTkFont(size=12),
            wraplength=230,
            justify="left",
        )
        self.update_panel_status_label.pack(anchor="w", padx=18, pady=(0, 20))

    def get_advanced_settings_button_text(self):
        return "HIDE ADVANCED SETTINGS" if self.advanced_settings_enabled.get() else "SHOW ADVANCED SETTINGS"

    def toggle_advanced_settings(self):
        self.advanced_settings_enabled.set(not self.advanced_settings_enabled.get())
        if self.current_page == "Rain":
            self.clear_left_panel()
            self.build_rain_left_panel()

    def confirm_weather_station_enable(self):
        if not self.weather_station_warn_before_open.get():
            return True

        result = {"action": "cancel"}

        dialog = ctk.CTkToplevel(self)
        dialog.geometry("460x260")
        dialog.resizable(False, False)
        dialog.overrideredirect(True)
        dialog.transient(self)
        dialog.grab_set()
        dialog.configure(fg_color=COLORS["bg"])

        self.update_idletasks()
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 460) // 2
        y = self.winfo_y() + (self.winfo_height() - 260) // 2
        dialog.geometry(f"460x260+{max(x, 0)}+{max(y, 0)}")

        shell = ctk.CTkFrame(
            dialog,
            fg_color="#151412",
            border_color="#2f1d18",
            border_width=1,
            corner_radius=12,
        )
        shell.pack(fill="both", expand=True, padx=18, pady=18)

        ctk.CTkLabel(
            shell,
            text="WEATHER STATION",
            text_color=COLORS["red2"],
            font=ctk.CTkFont(family="Impact", size=30),
        ).pack(anchor="w", padx=22, pady=(18, 8))

        ctk.CTkLabel(
            shell,
            text=(
                "Chrome will open for Weather Station and must stay open "
                "so it can properly detect whether rain is active."
            ),
            text_color=COLORS["text"],
            font=ctk.CTkFont(size=14, weight="bold"),
            wraplength=390,
            justify="left",
        ).pack(anchor="w", padx=22, pady=(0, 12))

        ctk.CTkLabel(
            shell,
            text="Closing that browser window will turn Weather Station off.",
            text_color=COLORS["muted"],
            font=ctk.CTkFont(size=12),
            wraplength=390,
            justify="left",
        ).pack(anchor="w", padx=22)

        button_row = ctk.CTkFrame(shell, fg_color="transparent")
        button_row.pack(fill="x", padx=22, pady=(22, 18))
        button_row.grid_columnconfigure((0, 1, 2), weight=1)

        def close_with(action):
            result["action"] = action
            dialog.destroy()

        BanditButton(
            button_row,
            text="CANCEL",
            command=lambda: close_with("cancel"),
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))

        BanditButton(
            button_row,
            text="DO NOT NOTIFY",
            command=lambda: close_with("dont_notify"),
        ).grid(row=0, column=1, sticky="ew", padx=6)

        ctk.CTkButton(
            button_row,
            text="CONTINUE",
            height=36,
            fg_color=COLORS["green"],
            hover_color="#8dc34b",
            text_color="#111111",
            font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=18,
            command=lambda: close_with("continue"),
        ).grid(row=0, column=2, sticky="ew", padx=(6, 0))

        dialog.protocol("WM_DELETE_WINDOW", lambda: close_with("cancel"))
        dialog.wait_window()

        if result["action"] == "dont_notify":
            self.weather_station_warn_before_open.set(False)
            self.save_data()
            return True

        return result["action"] == "continue"

    def disable_weather_station(self, status_text="Weather station off", log_message=None):
        self.weather_station_active = False
        self.weather_station_enabled.set(False)
        self.weather_station_run_id += 1
        self.weather_station_next_check_at = None
        self.stop_weather_station_timer()

        driver = self.weather_station_driver
        self.weather_station_driver = None
        self.close_driver_async(driver)

        self.set_weather_station_status(status_text, COLORS["muted"])
        if log_message:
            self.log(log_message)

        self.refresh_keep_awake_state()
        self.save_data()
        self.refresh_stats_now()

    def toggle_weather_station(self):
        self.weather_station_active = bool(self.weather_station_enabled.get())

        if self.weather_station_active:
            if not self.confirm_weather_station_enable():
                self.weather_station_active = False
                self.weather_station_enabled.set(False)
                return
            self.weather_station_run_id += 1
            self.start_weather_station_timer()
            self.weather_station_next_check_at = time.time()
            self.set_weather_station_status("Checking weather station now...", COLORS["orange"])
            self.refresh_keep_awake_state()
            self.start_weather_station()
            self.log("Weather station enabled")
        else:
            self.disable_weather_station(
                status_text="Weather station off",
                log_message="Weather station disabled",
            )
            return

        self.save_data()
        self.refresh_stats_now()

    def start_weather_station(self):
        if (
            self.weather_station_thread
            and self.weather_station_thread.is_alive()
            and getattr(self.weather_station_thread, "run_id", None) == self.weather_station_run_id
        ):
            return

        self.weather_station_last_state = None
        self.weather_station_thread = threading.Thread(
            target=self.weather_station_worker,
            args=(self.weather_station_run_id,),
            daemon=True,
        )
        self.weather_station_thread.run_id = self.weather_station_run_id
        self.weather_station_thread.start()

    def mark_weather_station_browser(self, driver):
        try:
            driver.execute_script("document.title = 'RainBarrel Weather Station';")
        except Exception:
            pass

    def get_weather_station_shutdown_messages(self, error=None):
        if error is None:
            return (
                "Weather station off (Chrome closed)",
                "Weather station turned off because Chrome was closed",
            )

        detail = str(error).lower()
        closed_markers = [
            "closed",
            "invalid session",
            "no such window",
            "target window",
            "disconnected",
            "not connected",
            "web view not found",
        ]

        if any(marker in detail for marker in closed_markers):
            return (
                "Weather station off (Chrome closed)",
                "Weather station turned off because Chrome was closed",
            )

        return (
            "Weather station off (Chrome unavailable)",
            f"Weather station turned off: {error.__class__.__name__}",
        )

    def set_weather_station_status(self, text, color=None):
        self.weather_station_status = text

        if hasattr(self, "weather_station_status_label"):
            self.weather_station_status_label.configure(
                text=text,
                text_color=color or COLORS["muted"],
            )

    def report_weather_station_result(self, state, detail, notification_key=None):
        timestamp = format_time_12h()

        if state is True:
            status = f"Rain active as of {timestamp}"
            color = COLORS["green"]
        elif state is False:
            status = f"No rain active as of {timestamp}"
            color = COLORS["muted"]
        else:
            status = f"Rain status unknown: {detail}"
            color = COLORS["orange"]

        self.set_weather_station_status(status, color)

        if state != self.weather_station_last_state:
            self.weather_station_last_state = state
            self.log(f"Weather station: {detail}")

        if state is True and notification_key is not None and notification_key != self.last_weather_notification_key:
            self.record_rain_detected("weather station")
            self.start_rain_trackers("weather station")
            self.total_weather_notifications += 1
            self.current_weather_session_notifications += 1
            self.last_weather_notification_key = notification_key
            self.save_stats()
            threading.Thread(
                target=play_rain_alert_sound,
                args=(
                    clamp_int_setting(
                        self.get_setting_value(
                            self.weather_notification_volume,
                            DEFAULT_WEATHER_NOTIFICATION_VOLUME,
                        ),
                        DEFAULT_WEATHER_NOTIFICATION_VOLUME,
                        0,
                        100,
                    ),
                ),
                daemon=True,
            ).start()

    def weather_station_worker(self, run_id):
        driver = None
        browser_name = "Chrome visible"
        browser_ready = False
        rain_active_until_ms = 0
        rain_value = None
        rain_user_count = None
        rain_notification_key = None
        shutdown_status = None
        shutdown_log = None

        def weather_station_should_continue():
            nonlocal shutdown_status, shutdown_log

            if not self.weather_station_active or run_id != self.weather_station_run_id:
                return False

            if driver is None:
                return True

            try:
                if not driver.window_handles:
                    shutdown_status, shutdown_log = self.get_weather_station_shutdown_messages()
                    return False
            except Exception as e:
                shutdown_status, shutdown_log = self.get_weather_station_shutdown_messages(e)
                return False

            return True

        try:
            while self.weather_station_active and run_id == self.weather_station_run_id:
                try:
                    self.weather_station_next_check_at = time.time()
                    if driver is None:
                        driver, browser_name = create_weather_station_driver()
                        self.weather_station_driver = driver

                    if driver is None:
                        state, detail = None, browser_name
                    else:
                        handles = driver.window_handles
                        if not handles:
                            raise RuntimeError("Browser window closed")

                        current_url = (driver.current_url or "").lower()
                        if browser_ready and "bandit.camp" not in current_url:
                            raise RuntimeError("Bandit tab closed")

                        if not browser_ready:
                            state, detail = wait_for_bandit_page(
                                driver,
                                browser_name,
                                should_continue=lambda: self.weather_station_active and run_id == self.weather_station_run_id,
                            )
                            if state is None and "failed:" in detail.lower():
                                raise RuntimeError(detail)
                            browser_ready = state is True
                            if browser_ready:
                                self.mark_weather_station_browser(driver)
                                try:
                                    driver.minimize_window()
                                except Exception:
                                    pass
                                state = False
                                detail = "Watching Bandit rain websocket"
                        else:
                            now_ms = int(time.time() * 1000)
                            for event_type, payload in get_weather_station_rain_frames(driver):
                                if event_type == "rain":
                                    started_at = parse_epoch_millis(payload.get("startedAt")) or now_ms
                                    rain_active_until_ms = parse_weather_rain_active_until_ms(
                                        payload,
                                        now_ms,
                                    )
                                    rain_value = payload.get("value")
                                    parsed_rain_value = parse_scrap_number(rain_value)
                                    if parsed_rain_value is not None:
                                        with self.rain_tracking_lock:
                                            self.pending_rain_total_tipped = parsed_rain_value
                                            self.pending_rain_total_tipped_at = time.time()
                                            self.pending_rain_total_tipped_verified = True
                                    rain_user_count = payload.get("userCount")
                                    rain_notification_key = f"weather_rain:{started_at}"
                                elif event_type == "user_count":
                                    rain_user_count = payload

                            visible_text = get_browser_visible_text(driver).lower()
                            page_rain_active = page_has_active_rain_event(visible_text)

                            if page_rain_active:
                                ends_in = max(0, int((rain_active_until_ms - now_ms) / 1000))
                                parts = ["Rain active in page text"]
                                if rain_active_until_ms > now_ms:
                                    parts.append(f"websocket ends in {ends_in}s")
                                if rain_user_count is not None:
                                    parts.append(f"{rain_user_count} users")
                                if rain_value is not None:
                                    parts.append(f"value {rain_value}")
                                state, detail = True, " | ".join(parts)
                            else:
                                if rain_active_until_ms > now_ms:
                                    detail = "No active rain controls found; ignored stale websocket timer"
                                else:
                                    detail = "No active rain controls found"
                                rain_active_until_ms = 0
                                rain_notification_key = None
                                state = False
                except Exception as e:
                    shutdown_status, shutdown_log = self.get_weather_station_shutdown_messages(e)
                    break

                self.after(
                    0,
                    lambda s=state, d=detail, k=rain_notification_key: self.report_weather_station_result(s, d, k),
                )

                if state is True:
                    delay = WEATHER_RAIN_FOUND_COOLDOWN_SECONDS
                else:
                    delay = clamp_int_setting(
                        self.get_setting_value(
                            self.weather_station_interval,
                            DEFAULT_WEATHER_STATION_INTERVAL,
                        ),
                        DEFAULT_WEATHER_STATION_INTERVAL,
                        10,
                        90,
                    )
                self.sleep_with_check_timer(
                    "weather_station_next_check_at",
                    delay,
                    should_continue=weather_station_should_continue,
                )
                if shutdown_status:
                    break
        finally:
            if driver is not None:
                try:
                    driver.quit()
                except Exception:
                    pass
            if self.weather_station_driver is driver:
                self.weather_station_driver = None
            if run_id == self.weather_station_run_id:
                self.weather_station_next_check_at = None
            if self.weather_station_thread is not None and getattr(self.weather_station_thread, "run_id", None) == run_id:
                self.weather_station_thread = None
            if shutdown_status and run_id == self.weather_station_run_id:
                self.after(
                    0,
                    lambda status=shutdown_status, log=shutdown_log: self.disable_weather_station(
                        status_text=status,
                        log_message=log,
                    ),
                )

    def sync_rain_clicker_controls(self):
        if self.running:
            topbar_text = "STOP"
            button_color = COLORS["red"]
            hover_color = "#b83928"
            text_color = COLORS["text"]
            status_text = "ONLINE"
            status_color = COLORS["red"]
        else:
            topbar_text = "START"
            button_color = COLORS["green"]
            hover_color = "#8dc34b"
            text_color = "#111111"
            status_text = "OFFLINE"
            status_color = "#2c2c2c"

        if hasattr(self, "toggle_btn"):
            self.toggle_btn.configure(
                text=topbar_text,
                fg_color=button_color,
                hover_color=hover_color,
                text_color=text_color,
            )

        if hasattr(self, "status_pill"):
            self.status_pill.configure(text=status_text, fg_color=status_color)

    def add_rain_time_window_setting(self):
        box = ctk.CTkFrame(self.left_panel, fg_color="#111411", corner_radius=12)
        box.pack(fill="x", padx=14, pady=8)
        box.grid_columnconfigure((0, 1), weight=1, uniform="rain_time")

        ctk.CTkLabel(
            box,
            text="COLLECT BETWEEN",
            text_color=COLORS["text"],
            font=ctk.CTkFont(size=12, weight="bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(10, 6))

        ctk.CTkLabel(
            box,
            text="START",
            text_color=COLORS["muted"],
            font=ctk.CTkFont(size=10, weight="bold"),
        ).grid(row=1, column=0, sticky="w", padx=(12, 6), pady=(0, 2))

        ctk.CTkLabel(
            box,
            text="END",
            text_color=COLORS["muted"],
            font=ctk.CTkFont(size=10, weight="bold"),
        ).grid(row=1, column=1, sticky="w", padx=(6, 12), pady=(0, 2))

        self.rain_collect_start_entry = ctk.CTkEntry(
            box,
            textvariable=self.rain_collect_start_time,
            height=30,
            fg_color="#070807",
            border_color="#30251f",
            text_color=COLORS["text"],
            placeholder_text="00:00",
        )
        self.rain_collect_start_entry.grid(row=2, column=0, sticky="ew", padx=(12, 6), pady=(0, 12))

        self.rain_collect_end_entry = ctk.CTkEntry(
            box,
            textvariable=self.rain_collect_end_time,
            height=30,
            fg_color="#070807",
            border_color="#30251f",
            text_color=COLORS["text"],
            placeholder_text="23:59",
        )
        self.rain_collect_end_entry.grid(row=2, column=1, sticky="ew", padx=(6, 12), pady=(0, 12))
        self.sync_rain_time_window_controls()

    def add_check_timer_panel(self):
        box = ctk.CTkFrame(self.left_panel, fg_color="#111411", corner_radius=12)
        box.pack(fill="x", padx=14, pady=8)
        box.grid_columnconfigure(0, weight=1)
        box.grid_columnconfigure(1, weight=0)

        ctk.CTkLabel(
            box,
            text="CHECK TIMERS",
            text_color=COLORS["text"],
            font=ctk.CTkFont(size=12, weight="bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(10, 6))

        values = self.get_check_timer_values()
        rows = [
            ("Rain Collector", "rain_collector"),
            ("Weather Station", "weather_station"),
            ("Reward Checker", "reward_checker"),
            ("Results Checker", "result_checker"),
        ]

        for row_index, (label_text, key) in enumerate(rows, start=1):
            ctk.CTkLabel(
                box,
                text=label_text,
                text_color=COLORS["muted"],
                font=ctk.CTkFont(size=12),
            ).grid(row=row_index, column=0, sticky="w", padx=12, pady=3)

            value_label = ctk.CTkLabel(
                box,
                text=values.get(key, "Off"),
                text_color=COLORS["red2"],
                font=ctk.CTkFont(size=12, weight="bold"),
            )
            value_label.grid(row=row_index, column=1, sticky="e", padx=12, pady=3)
            self.check_timer_labels[key] = value_label

        ctk.CTkFrame(box, height=4, fg_color="transparent").grid(
            row=len(rows) + 1,
            column=0,
            columnspan=2,
            sticky="ew",
        )

    def sync_rain_time_window_controls(self):
        state = "disabled" if self.rain_collect_any_time.get() else "normal"
        border_color = "#24201d" if state == "disabled" else "#30251f"
        fg_color = "#151816" if state == "disabled" else "#070807"
        text_color = COLORS["muted"] if state == "disabled" else COLORS["text"]

        for entry_name in ("rain_collect_start_entry", "rain_collect_end_entry"):
            if hasattr(self, entry_name):
                getattr(self, entry_name).configure(
                    state=state,
                    border_color=border_color,
                    fg_color=fg_color,
                    text_color=text_color,
                )

    def add_setting(self, label, variable, min_v, max_v, command=None, step=None):
        box = ctk.CTkFrame(self.left_panel, fg_color="#111411", corner_radius=12)
        box.pack(fill="x", padx=14, pady=8)

        ctk.CTkLabel(
            box,
            text=label.upper(),
            text_color=COLORS["text"],
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(anchor="w", padx=12, pady=(10, 2))

        slider_options = {
            "master": box,
            "from_": min_v,
            "to": max_v,
            "variable": variable,
            "command": command,
            "progress_color": COLORS["red"],
            "button_color": COLORS["red2"],
            "button_hover_color": "#ff8a6c",
        }

        if step is not None:
            slider_options["number_of_steps"] = max(1, int(round((max_v - min_v) / step)))

        ctk.CTkSlider(**slider_options).pack(fill="x", padx=12, pady=(4, 8))

        ctk.CTkEntry(
            box,
            textvariable=variable,
            height=28,
            fg_color="#070807",
            border_color="#30251f",
            text_color=COLORS["text"],
        ).pack(fill="x", padx=12, pady=(0, 10))

    # ================= RESIZE =================

    def force_resize(self):
        self.on_resize()

    def on_resize(self, event=None):
        w = max(self.winfo_width(), 900)
        h = max(self.winfo_height(), 560)
        sidebar_height = h - 58

        self.canvas.itemconfig(self.topbar_id, width=w, height=58)
        self.canvas.itemconfig(self.left_id, width=285, height=sidebar_height)
        self.canvas.itemconfig(self.content_id, width=w - 285, height=sidebar_height)
        self.left_panel_container.configure(width=285, height=sidebar_height)
        self.left_panel.configure(width=285, height=sidebar_height)

        if self.bg_job:
            self.after_cancel(self.bg_job)

        self.bg_job = self.after(250, self.redraw_background)

    def redraw_background(self):
        w = max(self.winfo_width(), 900)
        h = max(self.winfo_height(), 560)

        self.bg_image = make_background(w, h)
        self.canvas.itemconfig(self.bg_id, image=self.bg_image)

    # ================= PAGE SYSTEM =================

    def reset_scroll_frame(self, scroll_frame):
        try:
            if not scroll_frame.winfo_exists():
                return

            canvas = getattr(scroll_frame, "_parent_canvas", None)
            if canvas is None:
                return

            canvas.yview_moveto(0)
            canvas.xview_moveto(0)
        except (TclError, RuntimeError):
            pass

    def clear_content(self):
        self.hourly_chart_canvas = None
        for child in self.content.winfo_children():
            child.destroy()

    def clear_left_panel(self):
        self.check_timer_labels = {}
        for child in self.left_panel.winfo_children():
            child.destroy()
        self.reset_scroll_frame(self.left_panel)

    def show_page(self, page):
        self.current_page = page

        self.clear_content()
        self.clear_left_panel()

        for name, btn in self.nav_buttons.items():
            if name == page:
                btn.configure(fg_color=COLORS["red"], hover_color="#b83928")
            else:
                btn.configure(fg_color="#1b1f1a", hover_color="#2a241f")

        if page == "Rain":
            self.build_rain_left_panel()
            self.rain_page()

        elif page == "Battles":
            self.build_battles_left_panel()
            self.battles_page()

        elif page == "Stats":
            self.build_stats_left_panel()
            self.stats_page("Rain")

        self.after(0, lambda: self.reset_scroll_frame(self.left_panel))
        self.after(0, self.force_resize)

    def page_title(self, title, subtitle):
        ctk.CTkLabel(
            self.content,
            text=title,
            text_color=COLORS["red"],
            font=ctk.CTkFont(family="Impact", size=46),
        ).pack(pady=(28, 4))

        ctk.CTkLabel(
            self.content,
            text=subtitle,
            text_color=COLORS["text"],
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(pady=(0, 22))

    def rain_page(self):
        card = ctk.CTkFrame(
            self.content,
            fg_color="#181412",
            border_color="#331f19",
            border_width=1,
            corner_radius=10,
        )
        card.pack(fill="both", expand=True, padx=34, pady=8)

        ctk.CTkLabel(
            card,
            text="RAIN AUTOMATION",
            text_color=COLORS["red2"],
            font=ctk.CTkFont(family="Impact", size=42),
        ).pack(pady=(26, 12))

        self.log_box = ctk.CTkTextbox(
            card,
            height=260,
            fg_color="#090909",
            border_color="#2a211d",
            border_width=1,
            text_color=COLORS["text"],
            corner_radius=8,
        )
        self.log_box.pack(fill="both", expand=True, padx=22, pady=22)

        self.restore_rain_log()
        if not self.rain_log_entries:
            self.log("Rain page loaded")

    def battles_page(self):
        self.page_title("BATTLES", "SCREEN SCANNER")

        card = ctk.CTkFrame(
            self.content,
            fg_color="#181412",
            border_color="#331f19",
            border_width=1,
            corner_radius=10,
        )
        card.pack(fill="both", expand=True, padx=34, pady=8)

        ctk.CTkLabel(
            card,
            text="BATTLE AUTO JOIN",
            text_color=COLORS["red2"],
            font=ctk.CTkFont(family="Impact", size=30),
        ).pack(pady=(24, 6))

        self.battle_status_label = ctk.CTkLabel(
            card,
            text=self.get_battle_status_text(),
            text_color=COLORS["text"],
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.battle_status_label.pack(pady=(0, 12))

        self.battle_toggle_btn = BanditButton(
            card,
            text=self.get_battle_toggle_text(),
            command=self.toggle_battle_scanner,
        )
        self.battle_toggle_btn.pack(pady=(0, 16))

        self.battle_log_box = ctk.CTkTextbox(
            card,
            height=260,
            fg_color="#090909",
            border_color="#2a211d",
            border_width=1,
            text_color=COLORS["text"],
            corner_radius=8,
        )
        self.battle_log_box.pack(fill="both", expand=True, padx=22, pady=(0, 22))

        self.battle_log("Battles page loaded")

    def get_stats_sections(self, stat_page):
        if stat_page == "Rain":
            return [
                (
                    "TOTAL RAIN STATS",
                    [
                        ("Total Active Time", self.format_duration(self.get_total_search_time_seconds())),
                        ("Total Rains Clicked", str(self.total_rains_clicked)),
                        ("Total Rain Collected", self.format_rain_amount(self.total_rain_collected)),
                        (
                            "Total After-Click Popups Clicked",
                            str(self.total_after_rain_popups_clicked),
                        ),
                        (
                            "Average Rain Per Hour",
                            self.format_rain_amount_per_hour(self.get_average_rain_collected_per_hour()),
                        ),
                        ("Last Rain Reward", self.format_rain_amount(self.last_rain_reward)),
                        ("Last Rain Detected", self.format_last_rain_detected()),
                    ],
                ),
                (
                    "CURRENT SESSION",
                    [
                        ("Session Time", self.format_duration(self.get_current_session_seconds())),
                        ("Session Rains Clicked", str(self.current_session_rains_clicked)),
                        ("Session Rain Collected", self.format_rain_amount(self.current_session_rain_collected)),
                    ],
                ),
                (
                    "WEATHER STATION",
                    [
                        (
                            "Total Weather Station Time",
                            self.format_duration(self.get_total_weather_station_time_seconds()),
                        ),
                        ("Total Weather Notifications", str(self.total_weather_notifications)),
                    ],
                ),
                (
                    "WEATHER SESSION",
                    [
                        (
                            "Session Weather Time",
                            self.format_duration(self.get_current_weather_session_seconds()),
                        ),
                        ("Session Weather Notifications", str(self.current_weather_session_notifications)),
                    ],
                ),
            ]

        return [
            (
                "BATTLES",
                [
                    ("Status", "Scanning" if self.battle_running else "Stopped"),
                    ("Minimum Discount", f"{float(self.battle_minimum_discount.get()):.0f}%"),
                    ("Free Cases Only", "Yes" if self.battle_free_cases_only.get() else "No"),
                ],
            )
        ]


    def refresh_stats_live(self):
        self.refresh_stats_now()
        self.after(500, self.refresh_stats_live)

    def refresh_stats_now(self):
        self.refresh_topbar_total()

        if self.current_page == "Stats" and hasattr(self, "stat_value_labels"):
            sections = self.get_stats_sections(self.active_stats_page)

            for _, rows in sections:
                for label, value in rows:
                    if label in self.stat_value_labels:
                        self.stat_value_labels[label].configure(text=value)

            if self.active_stats_page == "Rain" and self.hourly_chart_canvas is not None:
                self.draw_hourly_rain_chart(self.hourly_chart_canvas)

    def stats_page(self, stat_page="Rain"):
        self.active_stats_page = stat_page
        self.clear_content()
        self.stat_value_labels = {}

        self.page_title("STATS", stat_page.upper())

        action_row = ctk.CTkFrame(self.content, fg_color="transparent")
        action_row.pack(fill="x", padx=34, pady=(0, 4))

        BanditButton(
            action_row,
            text="RESET STATS",
            command=self.reset_stats,
        ).pack(side="right")

        BanditButton(
            action_row,
            text="IMPORT STATS",
            command=self.import_stats,
        ).pack(side="right", padx=(0, 8))

        BanditButton(
            action_row,
            text="EXPORT STATS",
            command=self.export_stats,
        ).pack(side="right", padx=(0, 8))

        scroll = FastScrollableFrame(
            self.content,
            fg_color="transparent",
            corner_radius=0,
            scrollbar_button_color="#2e2a24",
            scrollbar_button_hover_color="#453931",
        )
        scroll.pack(fill="both", expand=True, padx=0, pady=(0, 18))
        self.after(0, lambda frame=scroll: self.reset_scroll_frame(frame))

        for section_title, rows in self.get_stats_sections(stat_page):
            stats = ctk.CTkFrame(
                scroll,
                fg_color="#151412",
                border_color="#2f1d18",
                border_width=1,
                corner_radius=10,
            )
            stats.pack(fill="x", padx=34, pady=12)

            ctk.CTkLabel(
                stats,
                text=section_title,
                text_color=COLORS["red2"],
                font=ctk.CTkFont(family="Impact", size=26),
            ).pack(anchor="w", padx=26, pady=(18, 10))

            for label, value in rows:
                row = ctk.CTkFrame(stats, fg_color="transparent")
                row.pack(fill="x", padx=26, pady=12)

                ctk.CTkLabel(row, text=label.upper(), text_color=COLORS["muted"]).pack(side="left")

                value_label = ctk.CTkLabel(
                    row,
                    text=value,
                    text_color=COLORS["red2"],
                    font=ctk.CTkFont(size=18, weight="bold"),
                )
                value_label.pack(side="right")

                self.stat_value_labels[label] = value_label

        if stat_page == "Rain":
            self.build_rain_result_log(scroll)
            self.build_hourly_rain_chart(scroll)

    def get_trash_icon(self):
        if hasattr(self, "trash_icon"):
            return self.trash_icon

        icon = Image.new("RGBA", (18, 18), (0, 0, 0, 0))
        draw = ImageDraw.Draw(icon)
        color = (232, 224, 213, 255)
        draw.rounded_rectangle((5, 6, 13, 15), radius=1, outline=color, width=2)
        draw.line((4, 5, 14, 5), fill=color, width=2)
        draw.line((7, 3, 11, 3), fill=color, width=2)
        draw.line((7, 8, 7, 13), fill=color, width=1)
        draw.line((11, 8, 11, 13), fill=color, width=1)
        self.trash_icon = ctk.CTkImage(light_image=icon, dark_image=icon, size=(16, 16))
        return self.trash_icon

    def build_rain_result_log(self, parent):
        card = ctk.CTkFrame(
            parent,
            fg_color="#151412",
            border_color="#2f1d18",
            border_width=1,
            corner_radius=10,
        )
        card.pack(fill="x", padx=34, pady=12)

        ctk.CTkLabel(
            card,
            text="RAIN RESULT LOG",
            text_color=COLORS["red2"],
            font=ctk.CTkFont(family="Impact", size=26),
        ).pack(anchor="w", padx=26, pady=(18, 10))

        if not self.rain_result_history:
            ctk.CTkLabel(
                card,
                text="No rain result history yet.",
                text_color=COLORS["muted"],
                font=ctk.CTkFont(size=13),
            ).pack(anchor="w", padx=26, pady=(0, 22))
            return

        table = ctk.CTkFrame(card, fg_color="transparent")
        table.pack(fill="x", padx=18, pady=(0, 18))
        for index, weight in enumerate((2, 1, 1, 1, 1)):
            table.grid_columnconfigure(index, weight=weight, uniform="rain_result")
        table.grid_columnconfigure(5, weight=0, minsize=42)

        headers = ["TIME", "PEOPLE", "TIPPED", "COLLECTED", "MINE", ""]
        for column, header in enumerate(headers):
            ctk.CTkLabel(
                table,
                text=header,
                text_color=COLORS["muted"],
                font=ctk.CTkFont(size=11, weight="bold"),
            ).grid(row=0, column=column, sticky="w", padx=8, pady=(0, 6))

        visible_results = list(enumerate(self.rain_result_history[-20:]))
        first_visible_index = len(self.rain_result_history) - len(visible_results)

        for row_index, (relative_index, item) in enumerate(reversed(visible_results), start=1):
            history_index = first_visible_index + relative_index
            try:
                timestamp = datetime.strptime(item.get("time", ""), "%Y-%m-%d %H:%M:%S")
                display_time = timestamp.strftime("%m/%d %I:%M %p").replace(" 0", " ")
            except (TypeError, ValueError):
                display_time = str(item.get("time", "--"))

            values = [
                display_time,
                str(item.get("people_joined", "--")),
                self.format_optional_rain_amount(item.get("total_tipped")),
                self.format_rain_amount(item.get("total_scrap_claimed", 0.0)),
                self.format_rain_amount(item.get("your_reward", 0.0)),
            ]
            row_color = "#1b1815" if row_index % 2 else "transparent"

            for column, value in enumerate(values):
                cell = ctk.CTkFrame(table, fg_color=row_color, corner_radius=6)
                cell.grid(row=row_index, column=column, sticky="ew", padx=2, pady=2)
                ctk.CTkLabel(
                    cell,
                    text=value,
                    text_color=COLORS["text"] if column == 0 else COLORS["red2"],
                    font=ctk.CTkFont(size=12, weight="bold" if column > 0 else "normal"),
                ).pack(anchor="w", padx=6, pady=5)

            delete_cell = ctk.CTkFrame(table, fg_color=row_color, corner_radius=6)
            delete_cell.grid(row=row_index, column=5, sticky="ew", padx=2, pady=2)
            ctk.CTkButton(
                delete_cell,
                text="",
                image=self.get_trash_icon(),
                width=28,
                height=28,
                corner_radius=6,
                fg_color="#241714",
                hover_color="#3a211c",
                border_width=1,
                border_color="#3b2620",
                command=lambda index=history_index: self.delete_rain_result(index),
            ).pack(padx=4, pady=3)

    # ================= LOGGING =================

    def log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.rain_log_entries.append((timestamp, msg))
        self.rain_log_entries = self.rain_log_entries[-RAIN_LOG_HISTORY_LIMIT:]

        if not hasattr(self, "log_box"):
            return

        self.after(0, lambda: self._log(timestamp, msg))

    def _log(self, timestamp, msg):
        try:
            self.log_box.insert("end", f"[{timestamp}] {msg}\n")
            self.log_box.see("end")
        except Exception:
            pass

    def restore_rain_log(self):
        try:
            self.log_box.delete("1.0", "end")
            for timestamp, msg in self.rain_log_entries:
                self.log_box.insert("end", f"[{timestamp}] {msg}\n")
            self.log_box.see("end")
        except Exception:
            pass

    def battle_log(self, msg):
        if not hasattr(self, "battle_log_box"):
            return

        timestamp = datetime.now().strftime("%H:%M:%S")
        self.after(0, lambda: self._battle_log(timestamp, msg))

    def _battle_log(self, timestamp, msg):
        try:
            self.battle_log_box.insert("end", f"[{timestamp}] {msg}\n")
            self.battle_log_box.see("end")
        except Exception:
            pass

    # ================= AUTOMATION =================

    def get_battle_toggle_text(self):
        return "STOP BATTLE SCANNER" if self.battle_running else "START BATTLE SCANNER"

    def get_battle_status_text(self):
        if self.battle_running:
            return "Scanning for battle discounts"

        return "Stopped"

    def sync_battle_controls(self):
        if hasattr(self, "battle_toggle_btn"):
            self.battle_toggle_btn.configure(
                text=self.get_battle_toggle_text(),
                fg_color=COLORS["red"] if self.battle_running else COLORS["green"],
                hover_color="#b83928" if self.battle_running else "#8dc34b",
                text_color=COLORS["text"] if self.battle_running else "#111111",
            )

        if hasattr(self, "battle_status_label"):
            self.battle_status_label.configure(text=self.get_battle_status_text())

    def toggle_battle_scanner(self):
        if self.battle_running:
            self.battle_running = False
            self.battle_run_id += 1
            self.refresh_keep_awake_state()
            self.sync_battle_controls()
            self.battle_log("Battle scanner stopped")
            return

        self.apply_battle_settings()
        self.battle_running = True
        self.battle_run_id += 1
        run_id = self.battle_run_id
        self.refresh_keep_awake_state()
        self.sync_battle_controls()
        self.battle_log("Battle scanner started")
        self.battle_thread = threading.Thread(target=self.battle_worker, args=(run_id,), daemon=True)
        self.battle_thread.start()

    def battle_discount_is_allowed(self, discount):
        if discount is None:
            return False

        if self.battle_free_cases_only.get():
            return discount >= 100.0

        return discount >= float(self.battle_minimum_discount.get())

    def battle_worker(self, run_id):
        while self.battle_running and run_id == self.battle_run_id:
            try:
                matches, screenshot, monitor = locate_image_matches_all_monitors(
                    BATTLE_DISCOUNT_IMAGE_PATH,
                    confidence=max(0.55, self.get_confidence() - 0.05),
                    max_matches=8,
                )

                if not matches:
                    self.battle_log("No battle discount found")
                    time.sleep(BATTLE_SCAN_INTERVAL_SECONDS)
                    continue

                clicked = False
                for match in matches:
                    discount, detail = read_battle_discount_from_screen(screenshot, match, monitor)
                    if discount is None:
                        self.battle_log(detail)
                        continue

                    self.battle_log(
                        f"Found discount {discount:.0f}% | confidence={match['score']:.3f}"
                    )
                    if not self.battle_discount_is_allowed(discount):
                        continue

                    click_x = match["x"] + BATTLE_CLICK_OFFSET_X
                    click_y = match["y"] + BATTLE_CLICK_OFFSET_Y
                    self.battle_log(f"Joining battle at X={click_x} Y={click_y}")

                    move_cursor_smooth(
                        click_x,
                        click_y,
                        total_time=self.get_move_time(),
                        steps=self.get_move_steps(),
                    )

                    if not self.battle_running or run_id != self.battle_run_id:
                        break

                    pyautogui.click(click_x, click_y)
                    clicked = True
                    time.sleep(4)
                    break

                if matches and not clicked:
                    if self.battle_free_cases_only.get():
                        self.battle_log("Skipped: no free case discount found")
                    else:
                        self.battle_log(
                            f"Skipped: no discount met {float(self.battle_minimum_discount.get()):.0f}%"
                        )

            except Exception as e:
                self.error_count += 1
                self.last_action = "Battle scanner error"
                self.after(0, self.save_stats)
                self.battle_log(f"Error: {type(e).__name__}: {repr(e)}")

            time.sleep(BATTLE_SCAN_INTERVAL_SECONDS)

        if run_id == self.battle_run_id:
            self.after(0, self.sync_battle_controls)

    def wait_for_popup_after_rain_and_click(self):
        wait_seconds = self.get_popup_after_rain_wait_seconds()
        deadline = time.time() + wait_seconds
        best_match = None
        last_rejection_detail = None

        while self.running and time.time() < deadline:
            try:
                match, best_match = locate_popup_after_rain_all_monitors()
            except FileNotFoundError:
                self.log("After-click popup image not found in app files")
                return False

            if match:
                valid_match, validation_detail = validate_popup_after_rain_match(match)
                if not valid_match:
                    last_rejection_detail = validation_detail
                    best_match = match
                    time.sleep(0.5)
                    continue

                click_x = int(
                    match["left"]
                    + match["width"] * POPUP_AFTER_RAIN_CHECKBOX_X_RATIO
                    + random.randint(-3, 3)
                )
                click_y = int(
                    match["top"]
                    + match["height"] * POPUP_AFTER_RAIN_CHECKBOX_Y_RATIO
                    + random.randint(-3, 3)
                )
                self.log(
                    "Found after-click popup "
                    f"| confidence={match['score']:.3f} scale={match['scale']:.2f}; "
                    f"{validation_detail}; "
                    f"clicking checkbox at X={click_x} Y={click_y}"
                )

                move_cursor_smooth(
                    click_x,
                    click_y,
                    total_time=self.get_move_time(),
                    steps=self.get_move_steps(),
                )

                if not self.running:
                    return False

                pyautogui.click(click_x, click_y)
                self.total_after_rain_popups_clicked += 1
                self.save_stats()
                self.log("Clicked after-click popup checkbox")
                if self.current_page == "Stats" and self.active_stats_page == "Rain":
                    self.after(0, lambda: self.stats_page("Rain"))
                return True

            time.sleep(0.5)

        if best_match:
            color_diff = best_match.get("color_diff")
            color_detail = (
                f", color diff={color_diff:.1f}/{POPUP_AFTER_RAIN_MAX_COLOR_DIFF:.1f}"
                if color_diff is not None
                else ""
            )
            rejection_detail = (
                f", rejected: {last_rejection_detail}"
                if last_rejection_detail
                else ""
            )
            self.log(
                "After-click popup not found "
                f"within {wait_seconds}s (best confidence={best_match['score']:.3f}, "
                f"needed={POPUP_AFTER_RAIN_CONFIDENCE:.3f}, scale={best_match['scale']:.2f}"
                f"{color_detail}{rejection_detail})"
            )
        else:
            self.log(f"After-click popup not found within {wait_seconds}s")

        return False

    def toggle(self):
        self.running = not self.running

        if self.running:
            self.rain_scan_found_last_check = None
            self.rain_collector_next_check_at = time.time()
            self.start_rain_session()
            self.save_stats()
            self.refresh_keep_awake_state()
            self.sync_rain_clicker_controls()
            self.log("Started")
            threading.Thread(target=self.worker, daemon=True).start()
        else:
            self.stop_rain_session()
            self.rain_collector_next_check_at = None
            self.save_stats()
            self.refresh_keep_awake_state()
            self.sync_rain_clicker_controls()
            self.log("Stopped")

    def worker(self):
        while self.running:
            try:
                self.rain_collector_next_check_at = time.time()
                confidence = self.get_confidence()
                match, best_match = locate_rain_target_all_monitors(confidence)

                if match:
                    self.rain_scan_found_last_check = True
                    x = match["x"]
                    y = match["y"]
                    score = match["score"]
                    scale = match["scale"]
                    self.record_rain_detected("normal tracker")

                    self.log(
                        f"Found rain target image | X={x} Y={y} "
                        f"confidence={score:.3f} scale={scale:.2f}"
                    )

                    allowed, skip_reason = self.rain_collection_allowed(x, y)
                    if not allowed:
                        self.last_action = skip_reason
                        self.after(0, self.save_stats)
                        self.log(skip_reason)
                        self.sleep_with_check_timer(
                            "rain_collector_next_check_at",
                            2,
                            should_continue=lambda: self.running,
                        )
                        continue

                    move_cursor_smooth(
                        x,
                        y,
                        total_time=self.get_move_time(),
                        steps=self.get_move_steps(),
                    )

                    if not self.running:
                        break

                    pyautogui.click(x, y)
                    self.chance_skipped_rain_target = None
                    self.total_rains_clicked += 1
                    self.current_session_rains_clicked += 1
                    self.last_action = "Clicked rain join button"
                    self.after(0, self.save_stats)
                    self.log("Clicked rain join button")
                    self.start_rain_trackers("rain clicker")
                    self.wait_for_popup_after_rain_and_click()

                    move_away_x, move_away_y = get_random_point_all_monitors(
                        avoid_x=x,
                        avoid_y=y,
                    )
                    move_cursor_smooth(
                        move_away_x,
                        move_away_y,
                        total_time=self.get_move_time(),
                        steps=self.get_move_steps(),
                    )

                    self.sleep_with_check_timer(
                        "rain_collector_next_check_at",
                        RAIN_FOUND_COOLDOWN_SECONDS,
                        should_continue=lambda: self.running,
                    )
                    continue
                else:
                    self.chance_skipped_rain_target = None
                    if self.rain_scan_found_last_check is not False:
                        if best_match:
                            color_diff = best_match.get("color_diff")
                            color_detail = (
                                f", color diff={color_diff:.1f}/{RAIN_TARGET_MAX_COLOR_DIFF:.1f}"
                                if color_diff is not None
                                else ""
                            )
                            self.log(
                                "Rain target image not found "
                                f"(best confidence={best_match['score']:.3f}, "
                                f"needed={confidence:.3f}, scale={best_match['scale']:.2f}"
                                f"{color_detail})"
                            )
                        else:
                            self.log("Rain target image not found (no screenshot/template match data)")
                    self.rain_scan_found_last_check = False

            except Exception as e:
                self.error_count += 1
                self.last_action = "Error"
                self.after(0, self.save_stats)
                self.log(f"Error: {type(e).__name__}: {repr(e)}")

            self.sleep_with_check_timer(
                "rain_collector_next_check_at",
                self.get_interval_seconds(),
                should_continue=lambda: self.running,
            )

        self.rain_collector_next_check_at = None


if __name__ == "__main__":
    app = App()
    app.mainloop()
