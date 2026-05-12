import os
import json
import io
import asyncio
import ctypes
import hashlib
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
import winsound
import wave
from datetime import datetime

import cv2
import mss
import numpy as np
import pyautogui
import customtkinter as ctk
from PIL import Image, ImageTk, ImageDraw, ImageFilter

# ================= TO-DO =================
# Rain page animations
# Bot to decide best skin to withdraw
# Collect rain without having the website up or your cursor moved at all
# Password system/accounts which i activate
# Free battle joiner
# Discount battle joiner
# 3 cent collector/gambler
# Increase scan scroller limit
# Auto open daily case

# ================= CONFIG =================

APP_NAME = "RainBarrel"
APP_VERSION = "1.0.19"
APP_USER_MODEL_ID = "JackTheScavenger.RainBarrel"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


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
ICON_PATH = resource_path("app_icon.ico")
DEFAULT_DATA_PATH = resource_path("bandit_data.json")
DATA_PATH = app_data_path("bandit_data.json")
ALERT_SOUND_PATH = resource_path("rain_alert.wav")
BANDIT_CAMP_URL = "https://bandit.camp/"
UPDATE_MANIFEST_URL = "https://raw.githubusercontent.com/YOUR_GITHUB_USERNAME/RainBarrel/main/latest.json"
UPDATE_CHECK_TIMEOUT_SECONDS = 8
UPDATE_DOWNLOAD_TIMEOUT_SECONDS = 5 * 60
SELENIUM_PAGE_WAIT = 45
RAIN_REWARD_WATCH_SECONDS = 45 * 60
RAIN_REWARD_SCAN_INTERVAL_SECONDS = 3
RAIN_REWARD_HISTORY_LIMIT = 100
BATTLE_SCAN_INTERVAL_SECONDS = 2.5
BATTLE_CLICK_OFFSET_X = 260
BATTLE_CLICK_OFFSET_Y = 0

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

def locate_image_all_monitors(image_path, confidence=0.65):
    target = cv2.imread(image_path, cv2.IMREAD_COLOR)

    if target is None:
        raise FileNotFoundError(f"Image not found: {image_path}")

    with mss.mss() as sct:
        monitor = sct.monitors[0]
        screen = np.array(sct.grab(monitor))
        screen = cv2.cvtColor(screen, cv2.COLOR_BGRA2BGR)

        result = cv2.matchTemplate(screen, target, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val >= confidence:
            h, w = target.shape[:2]
            x = monitor["left"] + max_loc[0] + w // 2
            y = monitor["top"] + max_loc[1] + h // 2
            return x, y, max_val

    return None


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
        "rain ends",
    ]

    return any(marker in page for marker in active_markers)


def page_is_bandit_loading(page_text):
    page_text = page_text.strip().lower()
    return page_text.startswith("loading") and "cancel" in page_text


def get_browser_visible_text(driver):
    try:
        return driver.execute_script("return document.body ? document.body.innerText : '';") or ""
    except Exception:
        return ""


def parse_rain_reward_amount(text):
    match = re.search(
        r"\byou\s+won\s+([0-9]+(?:[.,][0-9]+)?)\s+scrap\b",
        text,
        re.IGNORECASE,
    )
    if not match:
        return None

    try:
        return float(match.group(1).replace(",", "."))
    except ValueError:
        return None


def capture_all_monitors_image():
    with mss.mss() as sct:
        monitor = sct.monitors[0]
        screen = np.array(sct.grab(monitor))

    screen = cv2.cvtColor(screen, cv2.COLOR_BGRA2RGB)
    return Image.fromarray(screen)


async def ocr_image_with_windows(image):
    from winrt.windows.graphics.imaging import BitmapDecoder
    from winrt.windows.media.ocr import OcrEngine
    from winrt.windows.storage.streams import DataWriter, InMemoryRandomAccessStream

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


def read_rain_reward_amount_from_screen():
    try:
        screenshot = capture_all_monitors_image()
        text = asyncio.run(ocr_image_with_windows(screenshot))
    except (ImportError, ModuleNotFoundError):
        return None, "Windows OCR packages are not installed"
    except Exception as e:
        return None, f"OCR failed: {e.__class__.__name__}"

    amount = parse_rain_reward_amount(text)
    if amount is None:
        return None, "Rain reward popup not visible yet"

    return amount, f"Read reward popup: {amount:.2f} scrap"


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
        text = asyncio.run(ocr_image_with_windows(crop))
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


def set_windows_app_user_model_id():
    if sys.platform != "win32":
        return

    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except Exception:
        pass


# ================= APP =================

class App(ctk.CTk):
    def __init__(self):
        set_windows_app_user_model_id()
        super().__init__()

        if not os.path.exists(IMAGE_PATH):
            raise FileNotFoundError(f"Missing image: {IMAGE_PATH}")
        if not os.path.exists(BATTLE_DISCOUNT_IMAGE_PATH):
            raise FileNotFoundError(f"Missing image: {BATTLE_DISCOUNT_IMAGE_PATH}")

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

        self.confidence = ctk.DoubleVar(value=saved_settings.get("confidence", 0.65))
        self.interval = ctk.DoubleVar(value=saved_settings.get("interval", 25.0))
        self.move_time = ctk.DoubleVar(value=saved_settings.get("move_time", 1.5))
        self.move_steps = ctk.IntVar(value=saved_settings.get("move_steps", 100))
        self.weather_station_interval = ctk.IntVar(value=saved_settings.get("weather_station_interval", 15))
        self.weather_notification_volume = ctk.IntVar(
            value=saved_settings.get("weather_notification_volume", 100)
        )
        self.weather_station_warn_before_open = ctk.BooleanVar(
            value=saved_settings.get("weather_station_warn_before_open", True)
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
        self.last_rain_reward = float(saved_stats.get("last_rain_reward", 0.0))
        self.rain_reward_history = saved_stats.get("rain_reward_history", [])
        if not isinstance(self.rain_reward_history, list):
            self.rain_reward_history = []
        self.rain_reward_history = self.clean_rain_reward_history(self.rain_reward_history)
        self.rain_reward_tracker_active = False
        self.rain_reward_lock = threading.Lock()
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

        self.build_ui()
        self.show_page("Rain")
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.bind("<Configure>", self.on_resize)

        self.stat_value_labels = {}
        self.active_stats_page = "Rain"
        self.after(500, self.refresh_stats_live)
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

        dialog = ctk.CTkToplevel(self)
        dialog.geometry("500x300")
        dialog.resizable(False, False)
        dialog.title("Update Available")
        dialog.transient(self)
        dialog.configure(fg_color=COLORS["bg"])
        self.update_dialog = dialog

        self.update_idletasks()
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 500) // 2
        y = self.winfo_y() + (self.winfo_height() - 300) // 2
        dialog.geometry(f"500x300+{max(x, 0)}+{max(y, 0)}")
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
            wraplength=430,
            justify="left",
        ).pack(anchor="w", padx=22, pady=(0, 10))

        notes_text = notes or "No update notes were provided."
        ctk.CTkLabel(
            shell,
            text=notes_text,
            text_color=COLORS["muted"],
            font=ctk.CTkFont(size=12),
            wraplength=430,
            justify="left",
        ).pack(anchor="w", padx=22)

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
            self.after(0, lambda path=downloaded_path: self.install_downloaded_update(path))
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
            Write-UpdateLog "$description failed on attempt ${attempt}: $($_.Exception.Message)"
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

    def get_current_settings(self):
        return {
            "confidence": round(float(self.confidence.get()), 3),
            "interval": round(float(self.interval.get()), 3),
            "move_time": round(float(self.move_time.get()), 3),
            "move_steps": int(self.move_steps.get()),
            "weather_station_interval": int(self.weather_station_interval.get()),
            "weather_notification_volume": int(self.weather_notification_volume.get()),
            "weather_station_warn_before_open": bool(self.weather_station_warn_before_open.get()),
            "battle_minimum_discount": round(float(self.battle_minimum_discount.get()), 1),
            "battle_free_cases_only": bool(self.battle_free_cases_only.get()),
            "rain_chart_mode": self.get_rain_chart_mode(),
        }

    def get_current_stats(self):
        return {
            "total_search_time_seconds": round(self.get_total_search_time_seconds(), 1),
            "total_rains_clicked": int(self.total_rains_clicked),
            "total_rain_collected": round(self.total_rain_collected, 2),
            "last_rain_reward": round(self.last_rain_reward, 2),
            "rain_reward_history": self.rain_reward_history[-RAIN_REWARD_HISTORY_LIMIT:],
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

    def apply_rain_settings(self):
        self.confidence.set(min(max(float(self.confidence.get()), 0.1), 1.0))
        self.interval.set(min(max(float(self.interval.get()), 10.0), 90.0))
        self.move_time.set(min(max(float(self.move_time.get()), 0.1), 5.0))
        self.move_steps.set(min(max(int(float(self.move_steps.get())), 10), 250))
        self.weather_station_interval.set(min(max(int(float(self.weather_station_interval.get())), 10), 90))
        self.weather_notification_volume.set(
            min(max(int(float(self.weather_notification_volume.get())), 0), 100)
        )

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
        self.weather_notification_volume.set(int(round(float(value))))

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
            args=(self.weather_notification_volume.get(),),
            daemon=True,
        ).start()

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

    def get_hourly_rain_totals(self):
        hourly_sums = [0.0] * 24
        hourly_counts = [0] * 24

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

            hourly_sums[hour] += value
            hourly_counts[hour] += 1

        return hourly_sums, hourly_counts

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
        totals, counts = self.get_hourly_rain_totals()
        averages = []

        for hour in range(24):
            if counts[hour]:
                averages.append(totals[hour] / counts[hour])
            else:
                averages.append(None)

        return averages

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
            text="AVERAGE RAIN COLLECTED BY HOUR",
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
        self.last_rain_reward = 0.0
        self.rain_reward_history = []
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

    def save_stats(self):
        self.save_data()
        self.refresh_topbar_total()
        self.after(0, self.refresh_stats_now)

    def record_rain_detected(self, source):
        self.last_rain_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.last_action = f"Rain detected by {source}"
        self.save_stats()

    def start_rain_reward_tracker(self):
        with self.rain_reward_lock:
            if self.rain_reward_tracker_active:
                return
            self.rain_reward_tracker_active = True

        threading.Thread(target=self.rain_reward_tracker_worker, daemon=True).start()

    def rain_reward_tracker_worker(self):
        deadline = time.time() + RAIN_REWARD_WATCH_SECONDS
        last_detail = None

        try:
            while time.time() < deadline:
                amount, detail = read_rain_reward_amount_from_screen()
                if amount is not None:
                    self.after(0, lambda value=amount: self.record_rain_reward(value))
                    return

                last_detail = detail
                time.sleep(RAIN_REWARD_SCAN_INTERVAL_SECONDS)

            if last_detail:
                self.log(f"Rain reward tracker stopped: {last_detail}")
        finally:
            with self.rain_reward_lock:
                self.rain_reward_tracker_active = False

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

        self.left_panel = ctk.CTkScrollableFrame(
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
        )

        self.advanced_settings_btn = BanditButton(
            self.left_panel,
            text=self.get_advanced_settings_button_text(),
            command=self.toggle_advanced_settings,
        )
        self.advanced_settings_btn.pack(fill="x", padx=18, pady=(4, 6))

        if self.advanced_settings_enabled.get():
            self.add_setting("Confidence", self.confidence, 0.1, 1.0)
            self.add_setting("Rain Clicker Check Delay", self.interval, 10, 90)
            self.add_setting("Move Time", self.move_time, 0.1, 5.0)
            self.add_setting("Move Steps", self.move_steps, 10, 250)
            self.add_setting("Weather Station Check Interval", self.weather_station_interval, 10, 90)

            BanditButton(
                self.left_panel,
                text="APPLY",
                command=self.apply_rain_settings,
            ).pack(fill="x", padx=18, pady=(12, 6))

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

    def set_weather_station_status(self, text, color=None):
        self.weather_station_status = text

        if hasattr(self, "weather_station_status_label"):
            self.weather_station_status_label.configure(
                text=text,
                text_color=color or COLORS["muted"],
            )

    def report_weather_station_result(self, state, detail, notification_key=None):
        timestamp = datetime.now().strftime("%H:%M:%S")
        previous_state = self.weather_station_last_state

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

            if state is True and previous_state is not True and notification_key is None:
                self.record_rain_detected("weather station")
                self.total_weather_notifications += 1
                self.current_weather_session_notifications += 1
                self.last_weather_notification_key = f"state:{timestamp}:{detail}"
                self.save_stats()
                threading.Thread(
                    target=play_rain_alert_sound,
                    args=(self.weather_notification_volume.get(),),
                    daemon=True,
                ).start()

        if state is True and notification_key is not None and notification_key != self.last_weather_notification_key:
            self.record_rain_detected("weather station")
            self.total_weather_notifications += 1
            self.current_weather_session_notifications += 1
            self.last_weather_notification_key = notification_key
            self.save_stats()
            threading.Thread(
                target=play_rain_alert_sound,
                args=(self.weather_notification_volume.get(),),
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
        close_reason = None

        try:
            while self.weather_station_active and run_id == self.weather_station_run_id:
                try:
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
                                    started_at = int(payload.get("startedAt", now_ms))
                                    duration = int(payload.get("duration", 0))
                                    rain_active_until_ms = started_at + duration
                                    rain_value = payload.get("value")
                                    rain_user_count = payload.get("userCount")
                                    rain_notification_key = f"weather_rain:{started_at}"
                                elif event_type == "user_count":
                                    rain_user_count = payload

                            if rain_active_until_ms > now_ms:
                                ends_in = max(0, int((rain_active_until_ms - now_ms) / 1000))
                                parts = [f"Rain websocket active, ends in {ends_in}s"]
                                if rain_user_count is not None:
                                    parts.append(f"{rain_user_count} users")
                                if rain_value is not None:
                                    parts.append(f"value {rain_value}")
                                state, detail = True, " | ".join(parts)
                            else:
                                page = driver.page_source.lower()
                                visible_text = get_browser_visible_text(driver).lower()
                                combined_page = f"{visible_text}\n{page}"

                                if page_has_active_rain_event(combined_page):
                                    state, detail = True, "Rain appears active on page fallback"
                                else:
                                    state, detail = False, "No active rain websocket event"
                                    rain_notification_key = None
                except Exception as e:
                    close_reason = f"Chrome closed or became unavailable ({e.__class__.__name__}: {e})"
                    break

                self.after(
                    0,
                    lambda s=state, d=detail, k=rain_notification_key: self.report_weather_station_result(s, d, k),
                )

                delay = min(max(int(float(self.weather_station_interval.get())), 10), 90)
                for _ in range(delay):
                    if not self.weather_station_active or run_id != self.weather_station_run_id:
                        break
                    time.sleep(1)
        finally:
            if driver is not None:
                try:
                    driver.quit()
                except Exception:
                    pass
            if self.weather_station_driver is driver:
                self.weather_station_driver = None
            if self.weather_station_thread is not None and getattr(self.weather_station_thread, "run_id", None) == run_id:
                self.weather_station_thread = None
            if close_reason and run_id == self.weather_station_run_id:
                self.after(
                    0,
                    lambda reason=close_reason: self.disable_weather_station(
                        status_text=reason,
                        log_message="Weather station turned off because Chrome was closed",
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

    def add_setting(self, label, variable, min_v, max_v, command=None):
        box = ctk.CTkFrame(self.left_panel, fg_color="#111411", corner_radius=12)
        box.pack(fill="x", padx=14, pady=8)

        ctk.CTkLabel(
            box,
            text=label.upper(),
            text_color=COLORS["text"],
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(anchor="w", padx=12, pady=(10, 2))

        ctk.CTkSlider(
            box,
            from_=min_v,
            to=max_v,
            variable=variable,
            command=command,
            progress_color=COLORS["red"],
            button_color=COLORS["red2"],
            button_hover_color="#ff8a6c",
        ).pack(fill="x", padx=12, pady=(4, 8))

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

    def clear_content(self):
        self.hourly_chart_canvas = None
        for child in self.content.winfo_children():
            child.destroy()

    def clear_left_panel(self):
        for child in self.left_panel.winfo_children():
            child.destroy()

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
        self.page_title("RAIN BARREL", "WATCHING FOR YOUR TARGET IMAGE")

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
            font=ctk.CTkFont(family="Impact", size=30),
        ).pack(pady=(24, 6))

        ctk.CTkLabel(
            card,
            text="Press START to begin scanning all monitors.",
            text_color=COLORS["text"],
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack()

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

        scroll = ctk.CTkScrollableFrame(
            self.content,
            fg_color="transparent",
            corner_radius=0,
            scrollbar_button_color="#2e2a24",
            scrollbar_button_hover_color="#453931",
        )
        scroll.pack(fill="both", expand=True, padx=0, pady=(0, 18))

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
            self.build_hourly_rain_chart(scroll)

    # ================= LOGGING =================

    def log(self, msg):
        if not hasattr(self, "log_box"):
            return

        timestamp = datetime.now().strftime("%H:%M:%S")
        self.after(0, lambda: self._log(timestamp, msg))

    def _log(self, timestamp, msg):
        try:
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
                    confidence=max(0.55, float(self.confidence.get()) - 0.05),
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
                        total_time=self.move_time.get(),
                        steps=int(self.move_steps.get()),
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

    def toggle(self):
        self.running = not self.running

        if self.running:
            self.start_rain_session()
            self.save_stats()
            self.refresh_keep_awake_state()
            self.sync_rain_clicker_controls()
            self.log("Started")
            threading.Thread(target=self.worker, daemon=True).start()
        else:
            self.stop_rain_session()
            self.save_stats()
            self.refresh_keep_awake_state()
            self.sync_rain_clicker_controls()
            self.log("Stopped")

    def worker(self):
        while self.running:
            try:
                match = locate_image_all_monitors(IMAGE_PATH, self.confidence.get())

                if match:
                    x, y, score = match
                    self.record_rain_detected("normal tracker")

                    self.log(f"Found target | X={x} Y={y} confidence={score:.3f}")

                    move_cursor_smooth(
                        x,
                        y,
                        total_time=self.move_time.get(),
                        steps=int(self.move_steps.get()),
                    )

                    if not self.running:
                        break

                    pyautogui.click(x, y)
                    self.total_rains_clicked += 1
                    self.current_session_rains_clicked += 1
                    self.last_action = "Clicked target"
                    self.after(0, self.save_stats)
                    self.log("Clicked target")
                    self.after(0, self.start_rain_reward_tracker)

                    move_away_x, move_away_y = get_random_point_all_monitors(
                        avoid_x=x,
                        avoid_y=y,
                    )
                    move_cursor_smooth(
                        move_away_x,
                        move_away_y,
                        total_time=self.move_time.get(),
                        steps=int(self.move_steps.get()),
                    )

                    time.sleep(2)
                else:
                    self.log("Not found")

            except Exception as e:
                self.error_count += 1
                self.last_action = "Error"
                self.after(0, self.save_stats)
                self.log(f"Error: {type(e).__name__}: {repr(e)}")

            time.sleep(self.interval.get())


if __name__ == "__main__":
    app = App()
    app.mainloop()
