import json
import ctypes
import math
import os
import random
import re
import subprocess
import sys
import threading
import time
from datetime import datetime
from importlib.util import find_spec
from pathlib import Path

os.environ.setdefault(
    "QTWEBENGINE_CHROMIUM_FLAGS",
    " ".join(
        [
            "--disable-features=CalculateNativeWinOcclusion,DirectCompositionVideoOverlays",
            "--disable-direct-composition-video-overlays",
            "--enable-gpu-rasterization",
            "--enable-zero-copy",
            "--ignore-gpu-blocklist",
        ]
    ),
)


def restart_with_project_venv_if_needed():
    if find_spec("PySide6") is not None:
        return

    script_path = Path(__file__).resolve()
    running_script = Path(sys.argv[0]).resolve() if sys.argv and sys.argv[0] else None
    if running_script != script_path:
        return

    venv_python = script_path.parent / "venv" / "Scripts" / "python.exe"
    if not venv_python.exists():
        return

    if Path(sys.executable).resolve() == venv_python.resolve():
        return

    subprocess.Popen(
        [str(venv_python), str(script_path), *sys.argv[1:]],
        cwd=str(script_path.parent),
    )
    raise SystemExit(0)


restart_with_project_venv_if_needed()

import main as legacy
from PySide6.QtCharts import QBarCategoryAxis, QBarSeries, QBarSet, QChart, QChartView, QValueAxis
from PySide6.QtCore import QObject, QMargins, QSize, Qt, QTime, QTimer, QUrl, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QIcon, QMovie, QPainter, QPalette, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QCheckBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
from PySide6.QtWebEngineWidgets import QWebEngineView
from shiboken6 import isValid


APP_NAME = "RainBarrel"
APP_VERSION = "1.2"
BANDIT_CAMP_URL = "https://bandit.camp/"
RAIN_REWARD_HISTORY_LIMIT = 100
DEFAULT_CONFIDENCE_PERCENT = 65
DEFAULT_RAIN_CLICKER_INTERVAL = 25
DEFAULT_MOVE_TIME = 1.5
DEFAULT_RAIN_COLLECT_ANY_TIME = True
DEFAULT_RAIN_COLLECT_START_TIME = "00:00"
DEFAULT_RAIN_COLLECT_END_TIME = "23:59"
DEFAULT_RAIN_COLLECT_CHANCE = 100
DEFAULT_RAIN_MIN_PREDICTION_ENABLED = False
DEFAULT_RAIN_MIN_PREDICTED_REWARD = 0.0
DEFAULT_RAIN_AUTO_ACTIVATE = False
DEFAULT_WEATHER_STATION_INTERVAL = 15
DEFAULT_WEATHER_NOTIFICATION_VOLUME = 100
DEFAULT_POPUP_AFTER_RAIN_WAIT_SECONDS = 10
DEFAULT_RAIN_FOUND_COOLDOWN_SECONDS = legacy.RAIN_FOUND_COOLDOWN_SECONDS
DEFAULT_RAIN_TRACKER_WATCH_SECONDS = legacy.RAIN_TRACKER_WATCH_SECONDS
DEFAULT_WEATHER_RAIN_FOUND_COOLDOWN_SECONDS = legacy.WEATHER_RAIN_FOUND_COOLDOWN_SECONDS
DEFAULT_RAIN_TIP_SCAN_INTERVAL_SECONDS = legacy.RAIN_TIP_SCAN_INTERVAL_SECONDS
DEFAULT_RAIN_REWARD_SCAN_INTERVAL_SECONDS = legacy.RAIN_REWARD_SCAN_INTERVAL_SECONDS
DEFAULT_RAIN_RESULT_SCAN_INTERVAL_SECONDS = legacy.RAIN_RESULT_SCAN_INTERVAL_SECONDS

COLORS = {
    "bg": "#020302",
    "top": "#10120f",
    "side": "#050805",
    "panel": "#10160f",
    "panel2": "#0c100c",
    "red": "#e1472d",
    "red2": "#ff5538",
    "orange": "#d67238",
    "gold": "#e2b12f",
    "green": "#80ad39",
    "green2": "#9ccc4a",
    "text": "#f1eee7",
    "muted": "#8f938b",
    "muted2": "#b7bbb2",
    "border": "#242c23",
    "border2": "#3a332c",
}


def app_data_path(filename):
    roots = [
        os.environ.get("APPDATA"),
        os.environ.get("LOCALAPPDATA"),
        os.path.expanduser("~"),
        os.path.dirname(os.path.abspath(__file__)),
    ]

    for root in roots:
        if not root:
            continue

        path = os.path.join(root, APP_NAME)
        try:
            os.makedirs(path, exist_ok=True)
            return os.path.join(path, filename)
        except OSError:
            continue

    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)


DATA_PATH = app_data_path("bandit_data.json")
DEBUG_LOG_PATH = app_data_path("qt_debug.log")
BROWSER_PROFILE_PATH = app_data_path("qt_browser_profile")
BROWSER_CACHE_PATH = app_data_path("qt_browser_cache")


def write_debug_log(message):
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as file:
            file.write(f"[{timestamp}] {message}\n")
    except OSError:
        pass


def load_saved_data():
    if not os.path.exists(DATA_PATH):
        return {}

    try:
        with open(DATA_PATH, "r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return {}

    return data if isinstance(data, dict) else {}


def save_saved_data(data):
    try:
        with open(DATA_PATH, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2)
        return True
    except OSError:
        return False


def clamp_int(value, default, minimum, maximum):
    try:
        value = int(float(value))
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(maximum, value))


def clamp_float(value, default, minimum, maximum):
    try:
        value = float(value)
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(maximum, value))


def parse_time_setting(value, default):
    text = str(value or default)
    parsed = QTime.fromString(text, "HH:mm")
    if parsed.isValid():
        return parsed
    return QTime.fromString(default, "HH:mm")


def parse_scrap_number(value):
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    match = re.search(r"-?\d+(?:,\d{3})*(?:\.\d+)?", str(value))
    if not match:
        return None

    try:
        return float(match.group(0).replace(",", ""))
    except ValueError:
        return None


def parse_rain_tip_from_page_text(text):
    if not text:
        return None

    patterns = [
        r"([0-9][0-9,]*(?:\.[0-9]+)?)\s+from\s+rain\s+tips",
        r"share\s+([0-9][0-9,]*(?:\.[0-9]+)?)",
        r"rain\s+tips[^0-9]*([0-9][0-9,]*(?:\.[0-9]+)?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, str(text), re.IGNORECASE)
        if match:
            parsed = parse_scrap_number(match.group(1))
            if parsed is not None:
                return parsed
    return None


def parse_rain_people_from_page_text(text):
    if not text:
        return None

    patterns = [
        r"rakeback\s+rain\s+([0-9][0-9,]*)\s+\d{1,2}:\d{2}",
        r"rakeback\s+rain\s+([0-9][0-9,]*)\s+(?:join|join\s+now|get\s+free|free\s+scrap)",
        r"([0-9][0-9,]*)\s+bandits?\s+(?:in|joined|claiming|online)?",
    ]
    for pattern in patterns:
        match = re.search(pattern, str(text), re.IGNORECASE)
        if not match:
            continue
        try:
            value = int(match.group(1).replace(",", ""))
        except ValueError:
            continue
        if value > 0:
            return value
    return None


def predict_rain_reward_from_history(history, current_tipped, current_people):
    current_tipped = parse_scrap_number(current_tipped)
    try:
        current_people = int(current_people)
    except (TypeError, ValueError):
        current_people = None

    if current_tipped is None or current_tipped <= 0 or current_people is None or current_people <= 0:
        return None

    samples = []
    for item in history:
        if not isinstance(item, dict):
            continue

        hist_tipped = parse_scrap_number(item.get("total_tipped"))
        hist_reward = parse_scrap_number(item.get("your_reward"))
        try:
            hist_people = int(item.get("people_joined"))
        except (TypeError, ValueError):
            continue

        if hist_tipped is None or hist_reward is None:
            continue
        if hist_tipped <= 0 or hist_reward <= 0 or hist_people <= 0:
            continue

        tip_distance = abs(math.log(current_tipped / hist_tipped))
        people_distance = abs(math.log(current_people / hist_people))
        distance = tip_distance + people_distance
        adjusted_reward = hist_reward * (current_tipped / hist_tipped) * (hist_people / current_people)
        weight = 1.0 / ((0.20 + distance) ** 2)
        samples.append(
            {
                "estimate": adjusted_reward,
                "weight": weight,
                "distance": distance,
                "hist_tipped": hist_tipped,
                "hist_people": hist_people,
                "hist_reward": hist_reward,
            }
        )

    if not samples:
        return None

    samples.sort(key=lambda item: item["distance"])
    nearest = samples[: min(20, len(samples))]
    weight_total = sum(item["weight"] for item in nearest)
    if weight_total <= 0:
        return None

    estimate = sum(item["estimate"] * item["weight"] for item in nearest) / weight_total
    variance = sum(((item["estimate"] - estimate) ** 2) * item["weight"] for item in nearest) / weight_total
    spread = math.sqrt(max(0.0, variance))
    best_distance = nearest[0]["distance"]
    if len(nearest) >= 8 and best_distance < 0.35:
        confidence = "high"
    elif len(nearest) >= 4 and best_distance < 0.65:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "estimate": round(max(0.0, estimate), 2),
        "low": round(max(0.0, estimate - spread), 2),
        "high": round(max(0.0, estimate + spread), 2),
        "sample_count": len(samples),
        "used_count": len(nearest),
        "confidence": confidence,
        "nearest": nearest[0],
    }


def format_rain_amount(amount):
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return "0"

    if amount.is_integer():
        return str(int(amount))
    return f"{amount:.2f}"


def format_duration(total_seconds):
    total_seconds = max(0, int(total_seconds or 0))
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


def format_last_rain_detected(value):
    if not value or value == "--":
        return "--"

    try:
        detected_at = datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return str(value)

    return detected_at.strftime("%I:%M %p").lstrip("0").lower()


def get_hourly_rain_averages(reward_history):
    hourly_values = [[] for _ in range(24)]

    for item in reward_history:
        if not isinstance(item, dict):
            continue

        timestamp = item.get("time")
        amount = item.get("amount")
        if timestamp is None or amount is None:
            continue

        try:
            hour = datetime.strptime(str(timestamp), "%Y-%m-%d %H:%M:%S").hour
        except ValueError:
            continue

        value = parse_scrap_number(amount)
        if value is not None:
            hourly_values[hour].append(value)

    return [
        (sum(values) / len(values)) if values else None
        for values in hourly_values
    ]


def hour_label(hour):
    suffix = "AM" if hour < 12 else "PM"
    display_hour = hour % 12 or 12
    return f"{display_hour}{suffix}"


def format_optional_rain_amount(amount):
    if amount is None or amount == "":
        return "--"
    return format_rain_amount(amount)


def parse_saved_timestamp(value):
    try:
        return datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        return None


def clean_rain_reward_history(history):
    cleaned = []
    if not isinstance(history, list):
        return cleaned

    for item in history:
        if not isinstance(item, dict):
            continue

        timestamp = item.get("time")
        amount = parse_scrap_number(item.get("amount"))
        if timestamp is None or amount is None:
            continue

        if parse_saved_timestamp(timestamp) is None:
            continue

        cleaned.append({"time": str(timestamp), "amount": round(amount, 2)})

    return cleaned[-RAIN_REWARD_HISTORY_LIMIT:]


def clean_rain_result_history(history):
    cleaned = []
    if not isinstance(history, list):
        return cleaned

    for item in history:
        if not isinstance(item, dict):
            continue

        try:
            timestamp = str(item.get("time"))
            people_joined = int(item.get("people_joined"))
            total_scrap_claimed = round(float(item.get("total_scrap_claimed")), 2)
            your_reward = round(float(item.get("your_reward", 0.0)), 2)
        except (TypeError, ValueError):
            continue

        if parse_saved_timestamp(timestamp) is None:
            continue
        if people_joined <= 0 or total_scrap_claimed <= 0:
            continue

        total_tipped = parse_scrap_number(item.get("total_tipped"))
        cleaned.append(
            {
                "time": timestamp,
                "people_joined": people_joined,
                "total_scrap_claimed": total_scrap_claimed,
                "total_tipped": total_tipped,
                "total_tipped_verified": bool(item.get("total_tipped_verified", total_tipped is not None)),
                "your_reward": your_reward,
            }
        )

    return cleaned[-RAIN_REWARD_HISTORY_LIMIT:]


class UiBridge(QObject):
    call = Signal(object)
    log = Signal(str)


def widget_is_alive(widget):
    try:
        return widget is not None and isValid(widget)
    except RuntimeError:
        return False


class StatRow(QFrame):
    def __init__(self, title, value):
        super().__init__()
        self.setObjectName("StatRow")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(12)

        title_label = QLabel(title.upper())
        title_label.setObjectName("StatLabel")

        self.value_label = QLabel(value)
        self.value_label.setObjectName("StatValue")
        self.value_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        layout.addWidget(title_label, 1)
        layout.addWidget(self.value_label)

    def set_value(self, value):
        self.value_label.setText(value)


class StatCard(QFrame):
    def __init__(self, title, rows):
        super().__init__()
        self.setObjectName("StatCard")
        self.rows_by_label = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 18, 24, 18)
        layout.setSpacing(2)

        title_label = QLabel(title)
        title_label.setObjectName("SectionTitle")
        layout.addWidget(title_label)

        for label, value in rows:
            row = StatRow(label, value)
            self.rows_by_label[label] = row
            layout.addWidget(row)

    def update_rows(self, rows):
        for label, value in rows:
            row = self.rows_by_label.get(label)
            if row is not None:
                row.set_value(value)


class RainPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 18)
        layout.setSpacing(12)

        title = QLabel("RAIN AUTOMATION")
        title.setObjectName("PageTitle")

        self.status_label = QLabel("Stopped")
        self.status_label.setObjectName("PageSubtitle")

        header_row = QHBoxLayout()
        header_row.addWidget(title)
        header_row.addStretch(1)
        header_row.addWidget(self.status_label)

        scroll = QScrollArea()
        scroll.setObjectName("StatsScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setContentsMargins(6, 0, 18, 12)
        self.content_layout.setSpacing(14)

        self.settings_grid = QGridLayout()
        self.settings_grid.setContentsMargins(0, 0, 0, 0)
        self.settings_grid.setHorizontalSpacing(14)
        self.settings_grid.setVerticalSpacing(14)
        for column in range(3):
            self.settings_grid.setColumnStretch(column, 1)
        self.content_layout.addLayout(self.settings_grid)
        self.content_layout.addStretch(1)

        self.footer_layout = QHBoxLayout()
        self.footer_layout.setContentsMargins(0, 4, 0, 0)
        self.footer_layout.addStretch(1)
        self.content_layout.addLayout(self.footer_layout)
        scroll.setWidget(content)

        layout.addLayout(header_row)
        layout.addWidget(scroll, 1)

    def clear_settings(self):
        while self.settings_grid.count():
            item = self.settings_grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        while self.footer_layout.count():
            item = self.footer_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.footer_layout.addStretch(1)

    def add_settings_card(self, title, column_span=1):
        index = self.settings_grid.count()
        row = index // 3
        column = index % 3

        card = QFrame()
        card.setObjectName("StatCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(22, 16, 22, 18)
        card_layout.setSpacing(9)

        title_label = QLabel(title)
        title_label.setObjectName("SectionTitle")
        card_layout.addWidget(title_label)

        self.settings_grid.addWidget(card, row, column, 1, column_span)
        return card_layout

    def add_footer_button(self, text, callback):
        button = QPushButton(text)
        button.setObjectName("TinyActionButton")
        button.clicked.connect(callback)
        self.footer_layout.addWidget(button)
        return button

    def set_running(self, running):
        self.status_label.setText("Scanning for rain" if running else "Stopped")


class BrowserPage(QWidget):
    def __init__(self):
        super().__init__()
        self.loaded = False

        self.profile = QWebEngineProfile("RainBarrelBrowser", self)
        self.profile.setPersistentStoragePath(BROWSER_PROFILE_PATH)
        self.profile.setCachePath(BROWSER_CACHE_PATH)
        self.profile.setPersistentCookiesPolicy(QWebEngineProfile.ForcePersistentCookies)
        self.profile.setHttpCacheType(QWebEngineProfile.DiskHttpCache)
        self.page = QWebEnginePage(self.profile, self)
        self.page.setBackgroundColor(QColor(COLORS["bg"]))
        self.browser = QWebEngineView()
        self.browser.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.browser.setAttribute(Qt.WA_NoSystemBackground, True)
        self.browser.setStyleSheet(f"background: {COLORS['bg']};")
        self.browser.setPage(self.page)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.browser, 1)

    def ensure_loaded(self):
        if self.loaded:
            return
        self.load_home()

    def load_home(self):
        self.loaded = True
        self.browser.setUrl(QUrl(BANDIT_CAMP_URL))


class BattlesPage(QWidget):
    def __init__(self, log_callback=None):
        super().__init__()
        self.log_callback = log_callback
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        title = QLabel("BATTLES")
        title.setObjectName("PageTitle")

        controls = QFrame()
        controls.setObjectName("StatCard")
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(22, 16, 22, 18)
        controls_layout.setSpacing(9)

        section_title = QLabel("BATTLE CONTROLS")
        section_title.setObjectName("SectionTitle")
        controls_layout.addWidget(section_title)

        button = QPushButton("START SCANNER")
        button.setObjectName("SideButton")
        button.clicked.connect(self.log_pending_migration)
        controls_layout.addWidget(button)

        note = QLabel("Battle controls are not migrated yet.")
        note.setObjectName("SideNote")
        controls_layout.addWidget(note)

        layout.addWidget(title)
        layout.addWidget(controls)
        layout.addStretch(1)

    def log_pending_migration(self):
        if self.log_callback is not None:
            self.log_callback("Battle scanner migration is still pending.")


class LogsPage(QWidget):
    def __init__(self, developer_mode_callback=None):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 18)
        layout.setSpacing(12)

        title = QLabel("LOGS")
        title.setObjectName("PageTitle")

        header = QHBoxLayout()
        header.addWidget(title)
        header.addStretch(1)
        self.developer_mode_checkbox = QCheckBox("DEVELOPER MODE")
        self.developer_mode_checkbox.setObjectName("SideCheckbox")
        self.developer_mode_checkbox.setChecked(False)
        if developer_mode_callback is not None:
            self.developer_mode_checkbox.toggled.connect(developer_mode_callback)
        header.addWidget(self.developer_mode_checkbox)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setObjectName("LogBox")
        self.log_box.setText(
            "[--] Rain controls, weather station, reward tracking, result tracking, and battle logs are combined here."
        )

        layout.addLayout(header)
        layout.addWidget(self.log_box, 1)

    def log(self, source, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_box.append(f"[{timestamp}] {source}: {message}")


class ActivityToggleButton(QPushButton):
    def __init__(self, label, callback):
        super().__init__(label)
        self.label = label
        self.active = False
        self.hovered = False
        self.setObjectName("ActivityToggleButton")
        self.setCursor(Qt.PointingHandCursor)
        self.clicked.connect(lambda checked=False: callback())
        self.set_active(False)

    def set_active(self, active):
        self.active = bool(active)
        self.setProperty("active", self.active)
        self.refresh_text()
        self.style().unpolish(self)
        self.style().polish(self)

    def refresh_text(self):
        if self.hovered:
            self.setText("STOP" if self.active else "START")
        else:
            self.setText(self.label)

    def enterEvent(self, event):
        self.hovered = True
        self.refresh_text()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hovered = False
        self.refresh_text()
        super().leaveEvent(event)


class BarrelLogoButton(QPushButton):
    def __init__(self, click_callback):
        super().__init__()
        self.idle_pixmap = QPixmap(legacy.resource_path("Barrel No Flow.png"))
        self.drip_movie = QMovie(legacy.resource_path("Barrel Drip.gif"))
        self.flow_movie = QMovie(legacy.resource_path("Barrel Flowing.gif"))
        self.current_movie = None
        self.rain_active = False
        self.hovered = False

        self.setObjectName("LogoButton")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(128, 52)
        self.setIconSize(QSize(122, 50))
        self.clicked.connect(lambda checked=False: click_callback())
        self.drip_movie.frameChanged.connect(lambda frame=0: self.update_movie_icon(self.drip_movie))
        self.flow_movie.frameChanged.connect(lambda frame=0: self.update_movie_icon(self.flow_movie))
        self.refresh_image()

    def set_rain_active(self, active):
        active = bool(active)
        if self.rain_active == active:
            return
        self.rain_active = active
        self.refresh_image()

    def enterEvent(self, event):
        self.hovered = True
        self.refresh_image()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hovered = False
        self.refresh_image()
        super().leaveEvent(event)

    def update_movie_icon(self, movie):
        if self.current_movie is not movie:
            return
        self.setIcon(QIcon(movie.currentPixmap()))

    def set_movie(self, movie):
        if self.current_movie is movie:
            return
        self.stop_current_movie()
        self.current_movie = movie
        self.update_movie_icon(movie)
        movie.start()

    def stop_current_movie(self):
        if self.current_movie is not None:
            self.current_movie.stop()
            self.current_movie = None

    def refresh_image(self):
        if self.rain_active:
            self.set_movie(self.flow_movie)
            return
        if self.hovered:
            self.set_movie(self.drip_movie)
            return
        self.stop_current_movie()
        self.setIcon(QIcon(self.idle_pixmap))


class StatsPage(QWidget):
    def __init__(
        self,
        data,
        delete_result_callback=None,
        export_callback=None,
        import_callback=None,
        reset_callback=None,
        refresh_callback=None,
    ):
        super().__init__()
        self.data = data
        self.stats = data.get("stats", {}) if isinstance(data.get("stats"), dict) else {}
        self.delete_result_callback = delete_result_callback
        self.stat_cards_by_title = {}
        self.history_signature = self.get_history_signature(self.stats)

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 18)
        root.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("STATS")
        title.setObjectName("PageTitle")
        header.addWidget(title)
        header.addStretch(1)

        for text, callback in (
            ("REFRESH", refresh_callback),
            ("EXPORT STATS", export_callback),
            ("IMPORT STATS", import_callback),
            ("RESET STATS", reset_callback),
        ):
            button = QPushButton(text)
            button.setObjectName("SmallActionButton")
            if callback is not None:
                button.clicked.connect(callback)
            else:
                button.setEnabled(False)
            header.addWidget(button)
        root.addLayout(header)

        scroll = QScrollArea()
        self.scroll_area = scroll
        scroll.setObjectName("StatsScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(6, 0, 18, 12)
        layout.setSpacing(14)

        for section_title, rows in self.get_stats_sections():
            card = StatCard(section_title, rows)
            self.stat_cards_by_title[section_title] = card
            layout.addWidget(card)

        layout.addWidget(self.build_rain_result_log())
        chart_card = QFrame()
        chart_card.setObjectName("StatCard")
        chart_layout = QVBoxLayout(chart_card)
        chart_layout.setContentsMargins(24, 18, 24, 18)
        chart_layout.setSpacing(10)
        chart_title = QLabel("AVERAGE RAIN COLLECTED BY HOUR")
        chart_title.setObjectName("SectionTitle")
        chart_layout.addWidget(chart_title)
        chart_layout.addWidget(self.build_hourly_chart())
        layout.addWidget(chart_card)
        layout.addStretch(1)

        scroll.setWidget(body)
        root.addWidget(scroll, 1)

    @staticmethod
    def get_history_signature(stats):
        if not isinstance(stats, dict):
            return (0, "", 0, "")

        result_history = stats.get("rain_result_history", [])
        reward_history = stats.get("rain_reward_history", [])
        if not isinstance(result_history, list):
            result_history = []
        if not isinstance(reward_history, list):
            reward_history = []

        result_tail = result_history[-1] if result_history else {}
        reward_tail = reward_history[-1] if reward_history else {}
        return (
            len(result_history),
            json.dumps(result_tail, sort_keys=True, default=str),
            len(reward_history),
            json.dumps(reward_tail, sort_keys=True, default=str),
        )

    def refresh_stats(self, stats):
        self.stats = stats if isinstance(stats, dict) else {}
        for section_title, rows in self.get_stats_sections():
            card = self.stat_cards_by_title.get(section_title)
            if card is not None:
                card.update_rows(rows)

        next_signature = self.get_history_signature(self.stats)
        if next_signature != self.history_signature:
            return False
        return True

    def get_stats_sections(self):
        total_time = float(self.stats.get("total_search_time_seconds", 0.0) or 0.0)
        total_collected = float(self.stats.get("total_rain_collected", 0.0) or 0.0)
        average_per_hour = total_collected / (total_time / 3600) if total_time > 0 else 0.0

        return [
            (
                "TOTAL RAIN STATS",
                [
                    ("Total Active Time", format_duration(total_time)),
                    ("Total Rains Clicked", str(int(self.stats.get("total_rains_clicked", 0) or 0))),
                    ("Total Rain Collected", format_rain_amount(total_collected)),
                    (
                        "Total After-Click Popups Clicked",
                        str(int(self.stats.get("total_after_rain_popups_clicked", 0) or 0)),
                    ),
                    ("Average Rain Per Hour", f"{format_rain_amount(average_per_hour)}/H"),
                    ("Last Rain Reward", format_rain_amount(self.stats.get("last_rain_reward", 0.0))),
                    ("Last Rain Detected", format_last_rain_detected(self.stats.get("last_rain_time", "--"))),
                ],
            ),
            (
                "CURRENT SESSION",
                [
                    ("Session Time", format_duration(float(self.stats.get("current_session_seconds", 0.0) or 0.0))),
                    ("Session Rains Clicked", str(int(self.stats.get("current_session_rains_clicked", 0) or 0))),
                    ("Session Rain Collected", format_rain_amount(self.stats.get("current_session_rain_collected", 0.0))),
                ],
            ),
            (
                "WEATHER STATION",
                [
                    (
                        "Total Weather Station Time",
                        format_duration(float(self.stats.get("total_weather_station_time_seconds", 0.0) or 0.0)),
                    ),
                    ("Total Weather Notifications", str(int(self.stats.get("total_weather_notifications", 0) or 0))),
                ],
            ),
            (
                "WEATHER SESSION",
                [
                    (
                        "Session Weather Time",
                        format_duration(float(self.stats.get("current_weather_session_seconds", 0.0) or 0.0)),
                    ),
                    (
                        "Session Weather Notifications",
                        str(int(self.stats.get("current_weather_session_notifications", 0) or 0)),
                    ),
                ],
            ),
        ]

    def build_rain_result_log(self):
        card = QFrame()
        card.setObjectName("StatCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 18, 24, 18)
        layout.setSpacing(10)

        title = QLabel("RAIN RESULT LOG")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)

        history = self.stats.get("rain_result_history", [])
        if not isinstance(history, list) or not history:
            empty = QLabel("No rain result history yet.")
            empty.setObjectName("SideNote")
            layout.addWidget(empty)
            return card

        visible_results = list(enumerate(history[-20:]))
        first_visible_index = len(history) - len(visible_results)

        table = QTableWidget(len(visible_results), 6)
        table.setObjectName("RainResultTable")
        table.setHorizontalHeaderLabels(["TIME", "PEOPLE", "TIPPED", "COLLECTED", "MINE", ""])
        table.verticalHeader().hide()
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionMode(QAbstractItemView.NoSelection)
        table.setAlternatingRowColors(True)
        table.setMinimumHeight(min(620, 44 + len(visible_results) * 38))

        for row_index, (relative_index, item) in enumerate(reversed(visible_results)):
            history_index = first_visible_index + relative_index
            timestamp = parse_saved_timestamp(item.get("time", ""))
            display_time = (
                timestamp.strftime("%m/%d %I:%M %p").replace(" 0", " ")
                if timestamp is not None
                else str(item.get("time", "--"))
            )
            values = [
                display_time,
                str(item.get("people_joined", "--")),
                format_optional_rain_amount(item.get("total_tipped")),
                format_rain_amount(item.get("total_scrap_claimed", 0.0)),
                format_rain_amount(item.get("your_reward", 0.0)),
            ]

            for column, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if column > 0:
                    cell.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                table.setItem(row_index, column, cell)

            delete_button = QPushButton("TRASH")
            delete_button.setObjectName("TinyDangerButton")
            if self.delete_result_callback is not None:
                delete_button.clicked.connect(lambda checked=False, index=history_index: self.delete_result_callback(index))
            table.setCellWidget(row_index, 5, delete_button)

        header = table.horizontalHeader()
        header.setStretchLastSection(False)
        header.resizeSection(0, 170)
        header.resizeSection(1, 90)
        header.resizeSection(2, 110)
        header.resizeSection(3, 120)
        header.resizeSection(4, 90)
        header.resizeSection(5, 78)
        layout.addWidget(table)
        return card

    def build_hourly_chart(self):
        reward_history = self.stats.get("rain_reward_history", [])
        if not isinstance(reward_history, list):
            reward_history = []

        averages = get_hourly_rain_averages(reward_history[-RAIN_REWARD_HISTORY_LIMIT:])
        values = [value or 0.0 for value in averages]
        categories = [hour_label(hour) for hour in range(24)]

        rain_set = QBarSet("Rain")
        rain_set.setColor(QColor(COLORS["red2"]))
        rain_set.append(values)

        series = QBarSeries()
        series.append(rain_set)
        series.setBarWidth(0.75)

        chart = QChart()
        chart.addSeries(series)
        chart.setBackgroundBrush(QBrush(QColor(COLORS["panel2"])))
        chart.legend().hide()
        chart.setMargins(QMargins(0, 0, 0, 0))

        x_axis = QBarCategoryAxis()
        x_axis.append(categories)
        x_axis.setLabelsColor(QColor(COLORS["muted"]))
        x_axis.setLabelsAngle(-45)
        chart.addAxis(x_axis, Qt.AlignBottom)
        series.attachAxis(x_axis)

        y_axis = QValueAxis()
        max_value = max(values) if values else 0
        y_axis.setRange(0, max_value * 1.15 if max_value > 0 else 1)
        y_axis.setLabelsColor(QColor(COLORS["muted"]))
        y_axis.setGridLineColor(QColor(COLORS["border"]))
        chart.addAxis(y_axis, Qt.AlignLeft)
        series.attachAxis(y_axis)

        view = QChartView(chart)
        view.setRenderHint(QPainter.Antialiasing)
        view.setMinimumHeight(260)
        return view


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.saved_data = load_saved_data()
        self.settings = self.saved_data.get("settings", {})
        if not isinstance(self.settings, dict):
            self.settings = {}
        self.settings.pop("open_bandit_on_startup", None)
        self.load_runtime_state()
        self.bridge = UiBridge()
        self.bridge.call.connect(self.handle_ui_call)
        self.bridge.log.connect(self.append_rain_log)
        self.weather_volume_preview_timer = QTimer(self)
        self.weather_volume_preview_timer.setSingleShot(True)
        self.weather_volume_preview_timer.timeout.connect(self.play_weather_volume_preview)

        self.setWindowTitle("Rain Barrel Qt")
        self.resize(1280, 820)
        self.setMinimumSize(980, 620)

        self.nav_buttons = {}
        self.logo_button = None
        self.rain_page_button = None
        self.rain_status_button = None
        self.battle_status_button = None
        self.mini_rain_status_button = None
        self.mini_battle_status_button = None
        self.mini_pin_button = None
        self.mini_total_label = None
        self.mini_prediction_label = None
        self.mini_mode = False
        self.mini_pinned = False
        self.mini_mode_normal_flags = self.windowFlags()
        self.mini_drag_offset = None
        self.full_mode_geometry = None
        self.full_mode_was_maximized = False
        self.developer_mode = False
        self.pages = QStackedWidget()

        self.rain_page = RainPage()
        self.browser_page = BrowserPage()
        self.battles_page = BattlesPage(log_callback=self.log_battle)
        self.stats_page = self.create_stats_page()
        self.logs_page = LogsPage(developer_mode_callback=self.set_developer_mode)

        for page in (self.rain_page, self.browser_page, self.battles_page, self.stats_page, self.logs_page):
            self.pages.addWidget(page)

        self.total_label = QLabel(self.get_total_text())
        self.total_label.setObjectName("SessionScrapAmount")
        self.session_pill = self.build_session_pill()

        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        self.mini_bar = self.build_mini_bar()
        self.mini_bar.hide()
        self.topbar = self.build_topbar()
        self.body = self.build_body()
        root_layout.addWidget(self.mini_bar)
        root_layout.addWidget(self.topbar)
        root_layout.addWidget(self.body, 1)
        self.setCentralWidget(root)

        self.build_rain_settings_page()
        self.restore_saved_weather_station_state()
        self.show_page("Browser")
        self.sync_rain_running_state()
        self.sync_battle_running_state()
        self.sync_barrel_logo_state()
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_data)
        self.refresh_timer.start(1000)
        self.timer_refresh = QTimer(self)
        self.timer_refresh.timeout.connect(self.refresh_check_timer_labels)
        self.timer_refresh.start(500)
        self.current_page = "Browser"

    def load_runtime_state(self):
        stats = self.saved_data.get("stats", {})
        if not isinstance(stats, dict):
            stats = {}

        self.rain_running = False
        self.weather_station_active = False
        self.weather_station_thread = None
        self.weather_station_driver = None
        self.weather_station_run_id = 0
        self.weather_station_check_pending = False
        self.weather_station_last_state = None
        self.weather_station_active_rain_notified = False
        self.weather_station_status = "Weather station off"
        self.weather_station_started_at = None
        self.weather_station_next_check_at = None
        self.weather_station_checkbox = None
        self.weather_station_status_label = None
        self.battle_running = False
        self.rain_worker_thread = None
        self.rain_run_id = 0
        self.rain_collector_next_check_at = None
        self.rain_reward_next_check_at = None
        self.rain_result_next_check_at = None
        self.rain_reward_timer_status = "Off"
        self.rain_result_timer_status = "Off"
        self.check_timer_value_labels = {}
        self.rain_scan_found_last_check = None
        self.chance_skipped_rain_target = None
        self.rain_auto_last_start_key = None
        self.rain_auto_last_stop_key = None
        self.rain_visual_active_until = 0

        self.total_search_time_seconds = float(stats.get("total_search_time_seconds", 0.0) or 0.0)
        self.total_rains_clicked = int(stats.get("total_rains_clicked", stats.get("click_count", 0)) or 0)
        self.total_rain_collected = float(stats.get("total_rain_collected", 0.0) or 0.0)
        self.total_after_rain_popups_clicked = int(stats.get("total_after_rain_popups_clicked", 0) or 0)
        self.last_rain_reward = float(stats.get("last_rain_reward", 0.0) or 0.0)
        self.rain_reward_history = clean_rain_reward_history(stats.get("rain_reward_history", []))
        self.rain_result_history = clean_rain_result_history(stats.get("rain_result_history", []))
        self.current_session_seconds = 0.0
        self.current_session_rains_clicked = 0
        self.current_session_rain_collected = 0.0
        self.current_session_started_at = None
        self.current_session_started_label = "--"
        self.total_weather_station_time_seconds = float(stats.get("total_weather_station_time_seconds", 0.0) or 0.0)
        self.total_weather_notifications = int(stats.get("total_weather_notifications", 0) or 0)
        self.current_weather_session_seconds = 0.0
        self.current_weather_session_notifications = 0
        self.current_weather_session_started_label = "--"
        self.last_weather_notification_key = stats.get("last_weather_notification_key")
        self.last_action = stats.get("last_action", "--")
        self.last_rain_time = stats.get("last_rain_time", "--")
        self.error_count = int(stats.get("error_count", 0) or 0)

        self.rain_tip_tracker_active = False
        self.rain_tip_tracker_run_id = 0
        self.rain_reward_tracker_active = False
        self.rain_reward_tracker_run_id = 0
        self.rain_result_tracker_active = False
        self.rain_result_tracker_run_id = 0
        self.rain_reward_lock = threading.Lock()
        self.rain_tracking_lock = threading.Lock()
        self.pending_rain_tracking_reward = None
        self.pending_rain_tracking_result = None
        self.pending_rain_tracking_recorded = False
        self.pending_rain_total_tipped = None
        self.pending_rain_total_tipped_at = None
        self.pending_rain_total_tipped_verified = False
        self.pending_rain_total_tipped_source = None
        self.pending_rain_people_joined = None
        self.pending_rain_prediction = None
        self.rain_prediction_value_label = None
        self.rain_prediction_detail_label = None
        self.rain_prediction_context_label = None
        self.rain_prediction_last_log_key = None
        self.rain_tracking_source = None
        self.rain_tracking_started_at = None
        self.rain_tracking_watch_until = None
        self.rain_tracking_last_extend_log_at = 0

    def wait_for_popup_after_rain_and_click(self):
        wait_seconds = self.get_popup_after_rain_wait_seconds()
        deadline = time.time() + wait_seconds
        best_match = None
        last_rejection_detail = None

        while self.rain_running and time.time() < deadline:
            try:
                match, best_match = legacy.locate_popup_after_rain_all_monitors()
            except FileNotFoundError:
                self.bridge.log.emit("After-click popup image not found in app files")
                return False

            if match:
                valid_match, validation_detail = legacy.validate_popup_after_rain_match(match)
                if not valid_match:
                    last_rejection_detail = validation_detail
                    best_match = match
                    time.sleep(0.5)
                    continue

                click_x = int(
                    match["left"]
                    + match["width"] * legacy.POPUP_AFTER_RAIN_CHECKBOX_X_RATIO
                    + random.randint(-3, 3)
                )
                click_y = int(
                    match["top"]
                    + match["height"] * legacy.POPUP_AFTER_RAIN_CHECKBOX_Y_RATIO
                    + random.randint(-3, 3)
                )
                self.bridge.log.emit(
                    "Found after-click popup "
                    f"| confidence={match['score']:.3f} scale={match['scale']:.2f}; "
                    f"{validation_detail}; clicking checkbox at X={click_x} Y={click_y}"
                )
                legacy.move_cursor_smooth(
                    click_x,
                    click_y,
                    total_time=self.get_move_time(),
                    steps=self.get_move_steps(),
                )
                if not self.rain_running:
                    return False

                legacy.pyautogui.click(click_x, click_y)
                self.total_after_rain_popups_clicked += 1
                self.ui_call(self.save_stats)
                self.bridge.log.emit("Clicked after-click popup checkbox")
                return True

            time.sleep(0.5)

        if best_match:
            color_diff = best_match.get("color_diff")
            color_detail = (
                f", color diff={color_diff:.1f}/{legacy.POPUP_AFTER_RAIN_MAX_COLOR_DIFF:.1f}"
                if color_diff is not None
                else ""
            )
            rejection_detail = f", rejected: {last_rejection_detail}" if last_rejection_detail else ""
            self.bridge.log.emit(
                "After-click popup not found "
                f"within {wait_seconds}s (best confidence={best_match['score']:.3f}, "
                f"needed={legacy.POPUP_AFTER_RAIN_CONFIDENCE:.3f}, scale={best_match['scale']:.2f}"
                f"{color_detail}{rejection_detail})"
            )
        else:
            self.bridge.log.emit(f"After-click popup not found within {wait_seconds}s")
        return False

    def get_rain_tracking_watch_until(self):
        with self.rain_tracking_lock:
            return self.rain_tracking_watch_until or 0

    def start_rain_trackers(self, source="rain tracker"):
        now = time.time()
        watch_seconds = self.get_rain_tracker_watch_seconds()
        with self.rain_tracking_lock:
            if (
                self.rain_tip_tracker_active
                or self.rain_reward_tracker_active
                or self.rain_result_tracker_active
            ):
                old_until = self.rain_tracking_watch_until or 0
                self.rain_tracking_watch_until = max(old_until, now + watch_seconds)
                remaining = max(0, int(self.rain_tracking_watch_until - now))
                existing_source = self.rain_tracking_source or "another trigger"
                if now - self.rain_tracking_last_extend_log_at >= 30:
                    self.rain_tracking_last_extend_log_at = now
                    self.bridge.log.emit(
                        f"Rain trackers already running from {existing_source}; {source} extended tracking "
                        f"(watching {remaining}s more)"
                    )
                return False

            self.pending_rain_tracking_reward = None
            self.pending_rain_tracking_result = None
            self.pending_rain_tracking_recorded = False
            self.pending_rain_total_tipped = None
            self.pending_rain_total_tipped_at = None
            self.pending_rain_total_tipped_verified = False
            self.pending_rain_total_tipped_source = None
            self.pending_rain_people_joined = None
            self.pending_rain_prediction = None
            self.rain_prediction_last_log_key = None
            self.rain_tracking_source = source
            self.rain_tracking_started_at = now
            self.rain_tracking_watch_until = now + watch_seconds
            self.rain_visual_active_until = max(self.rain_visual_active_until, self.rain_tracking_watch_until)

            self.rain_tip_tracker_run_id += 1
            tip_run_id = self.rain_tip_tracker_run_id
            self.rain_reward_tracker_run_id += 1
            reward_run_id = self.rain_reward_tracker_run_id
            self.rain_result_tracker_run_id += 1
            result_run_id = self.rain_result_tracker_run_id
            self.rain_tip_tracker_active = True
            self.rain_reward_tracker_active = True
            self.rain_result_tracker_active = True

        self.bridge.log.emit(f"Rain trackers started by {source}; watching for {watch_seconds}s")
        self.bridge.log.emit("Rain tip tracker started")
        self.bridge.log.emit("Rain reward tracker started")
        self.bridge.log.emit("Rain result tracker started")
        threading.Thread(target=self.rain_tip_tracker_worker, args=(tip_run_id,), daemon=True).start()
        threading.Thread(target=self.rain_reward_tracker_worker, args=(reward_run_id,), daemon=True).start()
        threading.Thread(target=self.rain_result_tracker_worker, args=(result_run_id,), daemon=True).start()
        self.ui_call(self.sync_barrel_logo_state)
        self.ui_call(self.refresh_rain_prediction_labels)
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

        self.ui_call(lambda summary=summary, reward=reward: self.record_rain_result(summary, reward))

    def get_prediction_sample_count(self):
        count = 0
        for item in self.rain_result_history:
            if not isinstance(item, dict):
                continue
            if parse_scrap_number(item.get("total_tipped")) is None:
                continue
            if parse_scrap_number(item.get("your_reward")) is None:
                continue
            try:
                if int(item.get("people_joined")) <= 0:
                    continue
            except (TypeError, ValueError):
                continue
            count += 1
        return count

    def refresh_rain_prediction_labels(self):
        if self.pending_rain_prediction:
            prediction = self.pending_rain_prediction
            estimate = prediction["estimate"]
            low = prediction["low"]
            high = prediction["high"]
            confidence = prediction["confidence"].upper()
            tipped = prediction["tipped"]
            people = prediction["people"]
            used_count = prediction["used_count"]
            sample_count = prediction["sample_count"]
            value_text = f"Expected Reward: {format_rain_amount(estimate)} scrap"
            detail_text = (
                f"Range {format_rain_amount(low)}-{format_rain_amount(high)} scrap | "
                f"{confidence} confidence"
            )
            context_text = (
                f"Current rain: {people} people, tipped {format_rain_amount(tipped)} | "
                f"using {used_count}/{sample_count} prior rains"
            )
        else:
            value_text = "Expected Reward: --"
            sample_count = self.get_prediction_sample_count()
            detail_text = "Waiting for current rain tip and joined count."
            context_text = f"Using {sample_count} previous rains with tips."

        if widget_is_alive(self.rain_prediction_value_label):
            self.rain_prediction_value_label.setText(value_text)
            self.rain_prediction_value_label.setStyleSheet(f"color: {COLORS['green2']}; font-weight: 900;")
        if widget_is_alive(self.rain_prediction_detail_label):
            self.rain_prediction_detail_label.setText(detail_text)
        if widget_is_alive(self.rain_prediction_context_label):
            self.rain_prediction_context_label.setText(context_text)
        self.refresh_mini_stats_labels()

    def get_mini_prediction_text(self):
        if not self.pending_rain_prediction:
            return "PREDICTED RAIN --"
        estimate = self.pending_rain_prediction.get("estimate")
        if estimate is None:
            return "PREDICTED RAIN --"
        return f"PREDICTED RAIN {format_rain_amount(estimate)}"

    def refresh_mini_stats_labels(self):
        if widget_is_alive(self.mini_total_label):
            self.mini_total_label.setText(self.get_total_text())
        if widget_is_alive(self.mini_prediction_label):
            self.mini_prediction_label.setText(self.get_mini_prediction_text())

    def update_rain_reward_prediction(self, tipped, people):
        prediction = predict_rain_reward_from_history(self.rain_result_history, tipped, people)
        with self.rain_tracking_lock:
            self.pending_rain_total_tipped = round(float(tipped), 2) if tipped is not None else None
            self.pending_rain_total_tipped_at = time.time() if tipped is not None else None
            self.pending_rain_total_tipped_verified = tipped is not None
            self.pending_rain_total_tipped_source = "built-in browser page text"
            self.pending_rain_people_joined = people
            self.pending_rain_prediction = (
                {
                    **prediction,
                    "tipped": round(float(tipped), 2),
                    "people": int(people),
                }
                if prediction
                else None
            )

        self.refresh_rain_prediction_labels()
        if not prediction:
            return

        log_key = (
            int(round(float(tipped) * 100)),
            int(people),
            int(round(prediction["estimate"] * 100)),
        )
        if log_key == self.rain_prediction_last_log_key:
            return
        self.rain_prediction_last_log_key = log_key
        self.log_rain(
            "Predicted rain reward: "
            f"{format_rain_amount(prediction['estimate'])} scrap "
            f"({int(people)} people, tipped {format_rain_amount(tipped)}, "
            f"{prediction['confidence']} confidence)"
        )

    def read_browser_rain_snapshot(self, timeout=2.0):
        if not widget_is_alive(self.browser_page):
            return None, "Built-in browser is not available"

        script = """
            (() => {
                const norm = (value) => String(value || "").replace(/\\s+/g, " ").trim();
                const isRendered = (element) => {
                    if (!element || !element.getBoundingClientRect) {
                        return false;
                    }
                    const style = window.getComputedStyle(element);
                    const rect = element.getBoundingClientRect();
                    return (
                        style.display !== "none" &&
                        style.visibility !== "hidden" &&
                        Number(style.opacity || 1) > 0.05 &&
                        rect.width > 3 &&
                        rect.height > 3
                    );
                };
                const collectCandidates = (predicate) => {
                    const matches = [];
                    const seen = new Set();
                    for (const element of Array.from(document.querySelectorAll("body *"))) {
                        if (!isRendered(element)) {
                            continue;
                        }
                        const text = norm(element.innerText || element.textContent);
                        if (!text || text.length > 1400) {
                            continue;
                        }
                        const lower = text.toLowerCase();
                        if (!predicate(lower)) {
                            continue;
                        }
                        if (seen.has(text)) {
                            continue;
                        }
                        seen.add(text);
                        const rect = element.getBoundingClientRect();
                        matches.push({
                            text,
                            top: Math.round(rect.top),
                            left: Math.round(rect.left),
                            width: Math.round(rect.width),
                            height: Math.round(rect.height),
                        });
                    }
                    matches.sort((a, b) => a.text.length - b.text.length);
                    return matches.slice(0, 6);
                };

                const rainTipCandidates = collectCandidates((lower) => (
                    lower.includes("rakeback rain") &&
                    lower.includes("rain tips") &&
                    (
                        lower.includes("join now") ||
                        lower.includes("free scrap") ||
                        lower.includes("play amount") ||
                        lower.includes("join rain event")
                    )
                ));
                const rainResultCandidates = collectCandidates((lower) => (
                    lower.includes("rakeback rain") &&
                    lower.includes("claimed") &&
                    lower.includes("from rain")
                ));
                const rainRewardCandidates = collectCandidates((lower) => (
                    (
                        lower.includes("you won") ||
                        lower.includes("your reward") ||
                        lower.includes("mark as read") ||
                        lower.includes("reward")
                    ) &&
                    (
                        lower.includes("scrap") ||
                        lower.includes("rakeback rain")
                    ) &&
                    !lower.includes("join rain event") &&
                    !lower.includes("rain tips") &&
                    !(lower.includes("claimed") && lower.includes("from rain"))
                ));

                return JSON.stringify({
                    href: String(window.location.href || ""),
                    readyState: String(document.readyState || ""),
                    tipCandidates: rainTipCandidates,
                    rewardCandidates: rainRewardCandidates,
                    resultCandidates: rainResultCandidates,
                });
            })()
        """

        done = threading.Event()
        result_holder = {"result": None, "error": None}

        def run_script():
            try:
                self.browser_page.page.runJavaScript(
                    script,
                    lambda result: (
                        result_holder.__setitem__("result", result),
                        done.set(),
                    ),
                )
            except RuntimeError as e:
                result_holder["error"] = e.__class__.__name__
                done.set()

        self.ui_call(run_script)
        if not done.wait(timeout):
            return None, "Built-in browser text read timed out"
        if result_holder["error"]:
            return None, f"Built-in browser text read failed: {result_holder['error']}"

        try:
            payload = json.loads(result_holder["result"]) if isinstance(result_holder["result"], str) else {}
        except json.JSONDecodeError:
            return None, "Built-in browser returned unreadable text data"

        href = str(payload.get("href", ""))
        if not href:
            return None, "Built-in browser has no loaded page yet"
        if "bandit.camp" not in href.lower():
            return None, "Built-in browser is not on bandit.camp"
        return payload, "Built-in browser text read"

    def read_rain_tip_context_from_browser_page(self):
        payload, detail = self.read_browser_rain_snapshot()
        if payload is None:
            return None, None, detail

        candidates = payload.get("tipCandidates", [])
        if not isinstance(candidates, list) or not candidates:
            return None, None, "Built-in browser rain tip panel not found"

        previews = []
        for candidate in candidates:
            text = str(candidate.get("text", "")) if isinstance(candidate, dict) else str(candidate)
            previews.append(legacy.compact_ocr_preview(text, 100))
            amount = parse_rain_tip_from_page_text(text)
            people = parse_rain_people_from_page_text(text)
            if amount is not None:
                detail = f"Read rain tip amount from browser page: {amount:.2f} scrap"
                if people is not None:
                    detail += f" with {people} people joined"
                return round(float(amount), 2), people, detail

        return (
            None,
            None,
            "Built-in browser rain tip panel found but amount was not parsed "
            f"(saw: {' | '.join(previews[:2])})",
        )

    def read_rain_tip_amount_from_browser_page(self):
        amount, people, detail = self.read_rain_tip_context_from_browser_page()
        return amount, detail

    def read_rain_reward_amount_from_browser_page(self):
        payload, detail = self.read_browser_rain_snapshot()
        if payload is None:
            return None, detail

        candidates = payload.get("rewardCandidates", [])
        if not isinstance(candidates, list) or not candidates:
            return None, "Built-in browser reward popup text not found"

        previews = []
        for candidate in candidates:
            text = str(candidate.get("text", "")) if isinstance(candidate, dict) else str(candidate)
            previews.append(legacy.compact_ocr_preview(text, 100))
            amount = legacy.parse_rain_reward_amount(text)
            if amount is not None:
                return round(float(amount), 2), f"Read reward popup from browser page: {amount:.2f} scrap"

        return (
            None,
            "Built-in browser reward popup text found but amount was not parsed "
            f"(saw: {' | '.join(previews[:2])})",
        )

    def read_rain_result_from_browser_page(self):
        payload, detail = self.read_browser_rain_snapshot()
        if payload is None:
            return None, detail

        candidates = payload.get("resultCandidates", [])
        if not isinstance(candidates, list) or not candidates:
            return None, "Built-in browser rain result message not found"

        previews = []
        for candidate in candidates:
            text = str(candidate.get("text", "")) if isinstance(candidate, dict) else str(candidate)
            previews.append(legacy.compact_ocr_preview(text, 120))
            result = legacy.parse_rain_result_summary(text)
            if result is not None:
                return (
                    result,
                    "Read rain result from browser page "
                    f"({result['people_joined']} people, {result['total_scrap_claimed']:.2f} scrap)",
                )

        return (
            None,
            "Built-in browser rain result message found but summary was not parsed "
            f"(saw: {' | '.join(previews[:2])})",
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

        try:
            while time.time() < self.get_rain_tracking_watch_until() and run_id == self.rain_tip_tracker_run_id:
                amount, people, detail = self.read_rain_tip_context_from_browser_page()

                if amount is not None:
                    tipped = round(float(amount), 2)
                    tipped_cents = legacy.rain_tip_cents(tipped)
                    read_index += 1
                    read_counts[tipped_cents] = read_counts.get(tipped_cents, 0) + 1
                    read_last_seen[tipped_cents] = read_index
                    recent_reads.append(tipped_cents)
                    recent_reads = recent_reads[-legacy.RAIN_TIP_RECENT_WINDOW:]
                    if candidate_tipped == tipped:
                        candidate_count += 1
                    else:
                        candidate_tipped = tipped
                        candidate_count = 1

                    confirmations_needed = legacy.RAIN_TIP_READING_CONFIRMATIONS
                    if last_tipped is not None:
                        if tipped < last_tipped:
                            confirmations_needed = legacy.RAIN_TIP_DROP_CONFIRMATIONS
                        elif tipped > last_tipped:
                            jump = tipped - last_tipped
                            jump_ratio = jump / max(last_tipped, 1.0)
                            if jump >= legacy.RAIN_TIP_LARGE_JUMP_MIN_SCRAP or jump_ratio >= legacy.RAIN_TIP_LARGE_JUMP_RATIO:
                                confirmations_needed = legacy.RAIN_TIP_LARGE_JUMP_CONFIRMATIONS

                    history_can_reclaim = False
                    if last_tipped is not None and tipped != last_tipped:
                        last_cents = legacy.rain_tip_cents(last_tipped)
                        history_can_reclaim = (
                            candidate_count >= legacy.RAIN_TIP_HISTORY_RECLAIM_CONFIRMATIONS
                            and read_counts.get(tipped_cents, 0)
                            >= read_counts.get(last_cents, 0) + legacy.RAIN_TIP_HISTORY_RECLAIM_MARGIN
                        )

                    recent_can_confirm = recent_reads.count(tipped_cents) >= confirmations_needed
                    if tipped != last_tipped and candidate_count < confirmations_needed:
                        if not history_can_reclaim and not recent_can_confirm:
                            last_detail = f"Confirming rain tipped amount: {format_rain_amount(tipped)} scrap"
                            time.sleep(self.get_rain_tip_scan_interval_seconds())
                            continue

                    misses_after_found = 0
                    last_tipped_verified = True
                    with self.rain_tracking_lock:
                        self.pending_rain_total_tipped = tipped
                        self.pending_rain_total_tipped_at = time.time()
                        self.pending_rain_total_tipped_verified = True
                        self.pending_rain_total_tipped_source = "built-in browser page text"
                        if people is not None:
                            self.pending_rain_people_joined = int(people)
                    if people is not None:
                        self.ui_call(lambda tipped=tipped, people=int(people): self.update_rain_reward_prediction(tipped, people))
                    write_debug_log(
                        "Rain tip raw read accepted: "
                        f"{format_rain_amount(tipped)} scrap | "
                        f"count={read_counts.get(tipped_cents, 0)} | "
                        f"recent={recent_reads.count(tipped_cents)}"
                    )
                    if last_tipped is None:
                        self.bridge.log.emit(f"Tracked rain tipped amount: {format_rain_amount(tipped)} scrap")
                    elif tipped != last_tipped:
                        self.bridge.log.emit(f"Updated rain tipped amount: {format_rain_amount(tipped)} scrap")
                    last_tipped = tipped
                else:
                    if last_tipped is not None and "not found" in detail.lower():
                        misses_after_found += 1
                        if misses_after_found >= legacy.RAIN_TIP_MISSES_AFTER_FOUND_TO_STOP:
                            break
                    with self.rain_tracking_lock:
                        rain_end_seen = self.pending_rain_tracking_reward is not None and self.pending_rain_tracking_result is not None
                    if rain_end_seen:
                        break

                last_detail = detail
                time.sleep(self.get_rain_tip_scan_interval_seconds())

            final_cents, final_verified = legacy.choose_final_rain_tip_cents(
                read_counts,
                legacy.rain_tip_cents(last_tipped) if last_tipped is not None else None,
                read_last_seen,
            )
            if final_cents is not None:
                final_tipped = legacy.rain_tip_amount_from_cents(final_cents)
                with self.rain_tracking_lock:
                    self.pending_rain_total_tipped = final_tipped
                    self.pending_rain_total_tipped_at = time.time()
                    self.pending_rain_total_tipped_verified = bool(final_verified)
                    self.pending_rain_total_tipped_source = "built-in browser page text final consensus"
                    final_people = self.pending_rain_people_joined
                if final_people is not None:
                    self.ui_call(
                        lambda tipped=final_tipped, people=int(final_people): self.update_rain_reward_prediction(
                            tipped,
                            people,
                        )
                    )
                write_debug_log(
                    "Rain tip final consensus: "
                    f"{format_rain_amount(final_tipped)} scrap | "
                    f"verified={bool(final_verified)} | "
                    f"reads={legacy.format_rain_tip_read_counts(read_counts)}"
                )
                if last_tipped is None or final_tipped != last_tipped:
                    self.bridge.log.emit(f"Final rain tipped consensus: {format_rain_amount(final_tipped)} scrap")
                last_tipped = final_tipped
                last_tipped_verified = bool(final_verified)

            if run_id == self.rain_tip_tracker_run_id and last_tipped is not None:
                suffix = "" if last_tipped_verified else " (unverified)"
                self.bridge.log.emit(f"Rain tip tracker finished with {format_rain_amount(last_tipped)} scrap{suffix}")
                self.bridge.log.emit(f"Rain tip read counts: {legacy.format_rain_tip_read_counts(read_counts)}")
            elif run_id == self.rain_tip_tracker_run_id and last_detail:
                self.bridge.log.emit(f"Rain tip tracker stopped: {last_detail}")
        finally:
            with self.rain_reward_lock:
                if run_id == self.rain_tip_tracker_run_id:
                    self.rain_tip_tracker_active = False
            self.maybe_record_pending_rain_result()

    def rain_reward_tracker_worker(self, run_id):
        last_detail = None
        try:
            while time.time() < self.get_rain_tracking_watch_until() and run_id == self.rain_reward_tracker_run_id:
                self.rain_reward_next_check_at = time.time()
                self.rain_reward_timer_status = ""
                amount, detail = self.read_rain_reward_amount_from_browser_page()
                if amount is not None:
                    own_reward = round(float(amount), 2)
                    self.rain_reward_next_check_at = None
                    self.rain_reward_timer_status = "Reward found"
                    self.bridge.log.emit(detail)
                    with self.rain_tracking_lock:
                        self.pending_rain_tracking_reward = own_reward
                    self.ui_call(lambda value=own_reward: self.record_rain_reward(value))
                    self.maybe_record_pending_rain_result()
                    return
                last_detail = detail
                scan_interval = self.get_rain_reward_scan_interval_seconds()
                self.rain_reward_next_check_at = time.time() + scan_interval
                time.sleep(scan_interval)
            if run_id == self.rain_reward_tracker_run_id and last_detail:
                self.bridge.log.emit(f"Rain reward tracker stopped: {last_detail}")
        finally:
            with self.rain_reward_lock:
                if run_id == self.rain_reward_tracker_run_id:
                    self.rain_reward_tracker_active = False
                    self.rain_reward_next_check_at = None
                    self.rain_reward_timer_status = "Off"

    def rain_result_tracker_worker(self, run_id):
        last_detail = None
        scan_count = 0
        try:
            while time.time() < self.get_rain_tracking_watch_until() and run_id == self.rain_result_tracker_run_id:
                self.rain_result_next_check_at = time.time()
                self.rain_result_timer_status = ""
                scan_count += 1
                result, detail = self.read_rain_result_from_browser_page()
                if result is not None:
                    with self.rain_tracking_lock:
                        self.pending_rain_tracking_result = result
                    self.rain_result_next_check_at = None
                    self.rain_result_timer_status = "Result found"
                    self.bridge.log.emit(f"Rain result summary found: {detail}")
                    self.maybe_record_pending_rain_result()
                    return
                last_detail = detail
                scan_interval = self.get_rain_result_scan_interval_seconds()
                self.rain_result_next_check_at = time.time() + scan_interval
                time.sleep(scan_interval)
            if run_id == self.rain_result_tracker_run_id and last_detail:
                self.bridge.log.emit(f"Rain result tracker stopped after {scan_count} scans: {last_detail}")
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
        self.last_action = f"Collected {format_rain_amount(amount)} scrap"
        self.save_stats()
        self.log_rain(f"Tracked rain reward: {format_rain_amount(amount)} scrap")
        self.reload_stats_if_visible()

    def record_rain_result(self, summary, your_reward):
        now = datetime.now()
        total_tipped = summary.get("total_tipped")
        with self.rain_tracking_lock:
            pending_total_tipped = self.pending_rain_total_tipped
            pending_total_tipped_at = self.pending_rain_total_tipped_at
            pending_total_tipped_verified = self.pending_rain_total_tipped_verified
            pending_total_tipped_source = self.pending_rain_total_tipped_source

        total_tipped_verified = total_tipped is not None
        total_tipped_source = "result page text" if total_tipped is not None else None
        if total_tipped is None and pending_total_tipped is not None:
            if pending_total_tipped_at is None or time.time() - pending_total_tipped_at < self.get_rain_tracker_watch_seconds():
                total_tipped = pending_total_tipped
                total_tipped_verified = bool(pending_total_tipped_verified)
                total_tipped_source = pending_total_tipped_source or "pending tip"

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
        self.log_rain(
            "Tracked rain result: "
            f"{item['people_joined']} people | "
            f"tipped {format_optional_rain_amount(item['total_tipped'])}"
            f"{'' if item['total_tipped_verified'] else ' (unverified)'} | "
            f"collected {format_rain_amount(item['total_scrap_claimed'])} | "
            f"you got {format_rain_amount(item['your_reward'])}"
        )
        write_debug_log(
            "Tracked rain result detail: "
            f"people={item['people_joined']} | "
            f"tipped={format_optional_rain_amount(item['total_tipped'])} | "
            f"tip_source={total_tipped_source or 'none'} | "
            f"verified={item['total_tipped_verified']} | "
            f"collected={format_rain_amount(item['total_scrap_claimed'])} | "
            f"reward={format_rain_amount(item['your_reward'])}"
        )
        self.refresh_rain_prediction_labels()
        self.reload_stats_if_visible()

    def remove_matching_rain_reward_for_result(self, result_item):
        reward_amount = parse_scrap_number(result_item.get("your_reward"))
        result_time = parse_saved_timestamp(result_item.get("time"))
        if reward_amount is None or not self.rain_reward_history:
            return None

        best_index = None
        best_time_delta = None
        for index, reward_item in enumerate(self.rain_reward_history):
            amount = parse_scrap_number(reward_item.get("amount"))
            if amount is None or abs(amount - reward_amount) > 0.001:
                continue
            reward_time = parse_saved_timestamp(reward_item.get("time"))
            if result_time is not None and reward_time is not None:
                time_delta = abs((result_time - reward_time).total_seconds())
                if time_delta > self.get_rain_tracker_watch_seconds():
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
            sum(parse_scrap_number(item.get("amount")) or 0.0 for item in self.rain_reward_history),
            2,
        )
        self.last_rain_reward = (
            parse_scrap_number(self.rain_reward_history[-1].get("amount")) or 0.0
            if self.rain_reward_history
            else 0.0
        )

    def delete_rain_result(self, history_index):
        if history_index < 0 or history_index >= len(self.rain_result_history):
            return

        scroll_value = self.get_stats_scroll_value()
        removed_result = self.rain_result_history.pop(history_index)
        removed_reward = self.remove_matching_rain_reward_for_result(removed_result)
        self.recalculate_rain_reward_stats()
        self.last_action = "Deleted rain result"
        self.save_data()
        reward_detail = ""
        if removed_reward is not None:
            removed_amount = parse_scrap_number(removed_reward.get("amount")) or 0.0
            reward_detail = f" and removed matching reward {format_rain_amount(removed_amount)}"
        self.log_rain(
            "Deleted rain result: "
            f"{removed_result.get('people_joined', '--')} people | "
            f"you got {format_rain_amount(removed_result.get('your_reward', 0.0))}"
            f"{reward_detail}"
        )
        self.refresh_rain_prediction_labels()
        self.reload_stats_if_visible(scroll_value)

    def set_weather_station_status(self, text, color=None):
        self.weather_station_status = text
        if widget_is_alive(self.weather_station_status_label):
            self.weather_station_status_label.setText(text)
            if color:
                self.weather_station_status_label.setStyleSheet(f"color: {color};")

    def get_weather_notification_volume(self):
        return clamp_int(
            self.settings.get("weather_notification_volume"),
            DEFAULT_WEATHER_NOTIFICATION_VOLUME,
            0,
            100,
        )

    def play_weather_notification_sound(self):
        volume = self.get_weather_notification_volume()
        threading.Thread(
            target=legacy.play_rain_alert_sound,
            args=(volume,),
            daemon=True,
        ).start()

    def schedule_weather_volume_preview(self):
        if widget_is_alive(self.weather_volume_spin):
            self.settings["weather_notification_volume"] = self.weather_volume_spin.value()
        self.weather_volume_preview_timer.start(350)

    def play_weather_volume_preview(self):
        self.play_weather_notification_sound()

    def toggle_weather_station(self, checked):
        write_debug_log(f"toggle_weather_station called: {checked}")
        self.settings["weather_station_enabled"] = bool(checked)
        if checked and not self.weather_station_active:
            self.weather_station_active = True
            self.weather_station_run_id += 1
            self.start_weather_station_timer()
            self.weather_station_next_check_at = time.time()
            self.set_weather_station_status("Checking weather station now...", COLORS["green"])
            self.refresh_keep_awake_state()
            self.start_weather_station()
            self.log_rain("Weather station enabled")
            self.save_data()
            self.reload_stats_if_visible()
        elif not checked and self.weather_station_active:
            self.disable_weather_station("Weather station off", "Weather station disabled")

    def restore_saved_weather_station_state(self):
        if not bool(self.settings.get("weather_station_enabled", False)):
            return
        if widget_is_alive(self.weather_station_checkbox):
            self.weather_station_checkbox.blockSignals(True)
            self.weather_station_checkbox.setChecked(True)
            self.weather_station_checkbox.blockSignals(False)
        self.toggle_weather_station(True)

    def disable_weather_station(self, status_text="Weather station off", log_message=None):
        self.weather_station_active = False
        self.settings["weather_station_enabled"] = False
        self.weather_station_run_id += 1
        self.weather_station_next_check_at = None
        self.weather_station_check_pending = False
        self.weather_station_last_state = None
        self.weather_station_active_rain_notified = False
        self.stop_weather_station_timer()
        driver = self.weather_station_driver
        self.weather_station_driver = None
        if driver is not None:
            threading.Thread(target=lambda: self.close_driver(driver), daemon=True).start()
        if widget_is_alive(self.weather_station_checkbox) and self.weather_station_checkbox.isChecked():
            self.weather_station_checkbox.blockSignals(True)
            self.weather_station_checkbox.setChecked(False)
            self.weather_station_checkbox.blockSignals(False)
        self.set_weather_station_status(status_text, COLORS["muted"])
        if log_message:
            self.log_rain(log_message)
        self.refresh_keep_awake_state()
        self.sync_barrel_logo_state()
        self.save_data()
        self.reload_stats_if_visible()

    def stop_weather_station_for_shutdown(self):
        self.weather_station_active = False
        self.weather_station_run_id += 1
        self.weather_station_next_check_at = None
        self.weather_station_check_pending = False
        self.weather_station_last_state = None
        self.weather_station_active_rain_notified = False
        self.stop_weather_station_timer()
        driver = self.weather_station_driver
        self.weather_station_driver = None
        if driver is not None:
            self.close_driver(driver)
        self.refresh_keep_awake_state()

    def close_driver(self, driver):
        try:
            driver.quit()
        except Exception:
            pass

    def start_weather_station(self):
        self.weather_station_last_state = None
        self.browser_page.ensure_loaded()
        self.log_rain("Weather station using built-in browser page text")
        self.schedule_weather_station_check(0)

    def schedule_weather_station_check(self, delay_seconds):
        if not self.weather_station_active:
            return
        run_id = self.weather_station_run_id
        delay_seconds = max(0.0, float(delay_seconds or 0))
        self.weather_station_next_check_at = time.time() + delay_seconds
        QTimer.singleShot(
            int(delay_seconds * 1000),
            lambda run_id=run_id: self.check_weather_station_browser_page(run_id),
        )

    def check_weather_station_browser_page(self, run_id):
        if not self.weather_station_active or run_id != self.weather_station_run_id:
            return
        if self.weather_station_check_pending:
            return

        self.weather_station_check_pending = True
        self.weather_station_next_check_at = time.time()
        script = """
            (() => {
                const norm = (value) => String(value || "").replace(/\\s+/g, " ").trim();
                const isVisible = (element) => {
                    if (!element || !element.getBoundingClientRect) {
                        return false;
                    }
                    const style = window.getComputedStyle(element);
                    const rect = element.getBoundingClientRect();
                    return (
                        style.display !== "none" &&
                        style.visibility !== "hidden" &&
                        Number(style.opacity || 1) > 0.05 &&
                        rect.width > 3 &&
                        rect.height > 3 &&
                        rect.bottom >= 0 &&
                        rect.right >= 0 &&
                        rect.top <= window.innerHeight &&
                        rect.left <= window.innerWidth
                    );
                };
                const buttonMarkers = ["join rain event", "claim rain", "collect rain"];
                const selector = [
                    "button",
                    "a",
                    "[role='button']",
                    "[class*='button']",
                    "[class*='Button']",
                    "div",
                    "span"
                ].join(",");
                const candidates = [];
                for (const element of Array.from(document.querySelectorAll(selector))) {
                    if (!isVisible(element)) {
                        continue;
                    }
                    const buttonText = norm(element.innerText || element.textContent);
                    const buttonLower = buttonText.toLowerCase();
                    const looksLikeRainButton = buttonMarkers.some(
                        (marker) => buttonLower === marker || (buttonText.length <= 60 && buttonLower.includes(marker))
                    );
                    if (!looksLikeRainButton) {
                        continue;
                    }

                    let node = element;
                    for (let depth = 0; node && depth < 8; depth += 1, node = node.parentElement) {
                        if (!isVisible(node)) {
                            continue;
                        }
                        const panelText = norm(node.innerText || node.textContent);
                        const lower = panelText.toLowerCase();
                        const hasTitle = lower.includes("rakeback rain");
                        const hasBody = (
                            lower.includes("rain tips") ||
                            lower.includes("free scrap") ||
                            lower.includes("join now") ||
                            lower.includes("play amount")
                        );
                        if (hasTitle && hasBody) {
                            candidates.push({
                                buttonText,
                                text: panelText.slice(0, 1200)
                            });
                            break;
                        }
                    }
                }

                return JSON.stringify({
                    href: String(window.location.href || ""),
                    title: String(document.title || ""),
                    readyState: String(document.readyState || ""),
                    text: String(document.body ? document.body.innerText : "").slice(0, 2000),
                    active: candidates.length > 0,
                    buttonText: candidates.length ? candidates[0].buttonText : "",
                    rainText: candidates.length ? candidates[0].text : "",
                    candidateCount: candidates.length
                });
            })()
        """
        try:
            self.browser_page.page.runJavaScript(
                script,
                lambda result, run_id=run_id: self.handle_weather_station_browser_text(run_id, result),
            )
        except RuntimeError as e:
            self.weather_station_check_pending = False
            self.report_weather_station_result(None, f"Built-in browser unavailable: {e.__class__.__name__}")
            delay = clamp_int(
                self.settings.get("weather_station_interval"),
                DEFAULT_WEATHER_STATION_INTERVAL,
                10,
                90,
            )
            self.schedule_weather_station_check(delay)

    def handle_weather_station_browser_text(self, run_id, result):
        self.weather_station_check_pending = False
        if not self.weather_station_active or run_id != self.weather_station_run_id:
            return

        state = None
        detail = "Built-in browser page text unavailable"
        notification_key = None

        try:
            payload = json.loads(result) if isinstance(result, str) else {}
        except json.JSONDecodeError:
            payload = {}

        href = str(payload.get("href", ""))
        ready_state = str(payload.get("readyState", ""))
        page_text = str(payload.get("text", ""))
        rain_text = str(payload.get("rainText", ""))
        button_text = str(payload.get("buttonText", ""))
        candidate_count = int(payload.get("candidateCount", 0) or 0)
        page_lower = page_text.lower()

        if not href:
            detail = "Built-in browser has no loaded page yet"
        elif "bandit.camp" not in href.lower():
            detail = "Built-in browser is not on bandit.camp"
        elif legacy.page_is_cloudflare_challenge(page_lower):
            detail = "Built-in browser is on Cloudflare check"
        elif ready_state and ready_state != "complete" and not page_text.strip():
            detail = "Built-in browser page is still loading"
        elif bool(payload.get("active")):
            state = True
            tip_amount = parse_rain_tip_from_page_text(rain_text)
            people_joined = parse_rain_people_from_page_text(rain_text)
            parts = ["Rain active in visible Rakeback Rain panel"]
            if button_text:
                parts.append(f"button {button_text}")
            if tip_amount is not None:
                with self.rain_tracking_lock:
                    self.pending_rain_total_tipped = round(float(tip_amount), 2)
                    self.pending_rain_total_tipped_at = time.time()
                    self.pending_rain_total_tipped_verified = True
                    self.pending_rain_total_tipped_source = "built-in browser page text"
                parts.append(f"value {format_rain_amount(tip_amount)}")
            if people_joined is not None:
                with self.rain_tracking_lock:
                    self.pending_rain_people_joined = int(people_joined)
                parts.append(f"people {people_joined}")
            if tip_amount is not None and people_joined is not None:
                self.update_rain_reward_prediction(tip_amount, people_joined)
            detail = " | ".join(parts)
            weather_cooldown = self.get_weather_rain_found_cooldown_seconds()
            notification_key = f"built_in_page_rain:{int(time.time() // weather_cooldown)}"
        else:
            state = False
            detail = f"No visible active Rakeback Rain join button found (candidates {candidate_count})"

        self.report_weather_station_result(state, detail, notification_key)

        delay = self.get_weather_rain_found_cooldown_seconds() if state is True else clamp_int(
            self.settings.get("weather_station_interval"),
            DEFAULT_WEATHER_STATION_INTERVAL,
            10,
            90,
        )
        self.schedule_weather_station_check(delay)

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

    def report_weather_station_result(self, state, detail, notification_key=None):
        was_active = self.weather_station_last_state is True
        timestamp = legacy.format_time_12h()
        if state is True:
            status = f"Rain active as of {timestamp}"
            color = COLORS["green"]
        elif state is False:
            status = f"No rain active as of {timestamp}"
            color = COLORS["muted"]
        else:
            status = f"Rain status unknown: {detail}"
            color = COLORS["red2"]
        self.set_weather_station_status(status, color)
        if state != self.weather_station_last_state:
            self.weather_station_last_state = state
            self.log_rain(f"Weather station: {detail}")
        if state is not True:
            self.weather_station_active_rain_notified = False
        if state is True and not was_active and not self.weather_station_active_rain_notified:
            self.record_rain_detected("weather station")
            self.start_rain_trackers("weather station")
            self.total_weather_notifications += 1
            self.current_weather_session_notifications += 1
            self.weather_station_active_rain_notified = True
            self.last_weather_notification_key = notification_key or f"weather_active:{int(time.time())}"
            self.save_stats()
            self.play_weather_notification_sound()

    def weather_station_worker(self, run_id):
        self.bridge.log.emit("Weather station worker started")
        driver = None
        browser_name = "Chrome visible"
        browser_ready = False
        rain_active_until_ms = 0
        rain_value = None
        rain_user_count = None
        rain_notification_key = None
        shutdown_status = None
        shutdown_log = None

        def should_continue():
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
                        driver, browser_name = legacy.create_weather_station_driver()
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
                            state, detail = legacy.wait_for_bandit_page(
                                driver,
                                browser_name,
                                should_continue=lambda: self.weather_station_active and run_id == self.weather_station_run_id,
                            )
                            if state is None and "failed:" in detail.lower():
                                raise RuntimeError(detail)
                            browser_ready = state is True
                            if browser_ready:
                                try:
                                    driver.execute_script("document.title = 'RainBarrel Weather Station';")
                                except Exception:
                                    pass
                                try:
                                    driver.minimize_window()
                                except Exception:
                                    pass
                                state = False
                                detail = "Watching Bandit rain websocket"
                        else:
                            now_ms = int(time.time() * 1000)
                            for event_type, payload in legacy.get_weather_station_rain_frames(driver):
                                if event_type == "rain":
                                    started_at = legacy.parse_epoch_millis(payload.get("startedAt")) or now_ms
                                    rain_active_until_ms = legacy.parse_weather_rain_active_until_ms(payload, now_ms)
                                    rain_value = payload.get("value")
                                    parsed_value = parse_scrap_number(rain_value)
                                    if parsed_value is not None:
                                        with self.rain_tracking_lock:
                                            self.pending_rain_total_tipped = parsed_value
                                            self.pending_rain_total_tipped_at = time.time()
                                            self.pending_rain_total_tipped_verified = True
                                            self.pending_rain_total_tipped_source = "weather station websocket"
                                    rain_user_count = payload.get("userCount")
                                    rain_notification_key = f"weather_rain:{started_at}"
                                elif event_type == "user_count":
                                    rain_user_count = payload

                            visible_text = legacy.get_browser_visible_text(driver).lower()
                            page_rain_active = legacy.page_has_active_rain_event(visible_text)
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
                                detail = (
                                    "No active rain controls found; ignored stale websocket timer"
                                    if rain_active_until_ms > now_ms
                                    else "No active rain controls found"
                                )
                                rain_active_until_ms = 0
                                rain_notification_key = None
                                state = False
                except Exception as e:
                    shutdown_status, shutdown_log = self.get_weather_station_shutdown_messages(e)
                    break

                self.ui_call(
                    lambda s=state, d=detail, k=rain_notification_key: self.report_weather_station_result(s, d, k)
                )

                delay = self.get_weather_rain_found_cooldown_seconds() if state is True else clamp_int(
                    self.settings.get("weather_station_interval"),
                    DEFAULT_WEATHER_STATION_INTERVAL,
                    10,
                    90,
                )
                self.sleep_with_check_timer("weather_station_next_check_at", delay, should_continue=should_continue)
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
                self.ui_call(
                    lambda status=shutdown_status, log=shutdown_log: self.disable_weather_station(
                        status_text=status,
                        log_message=log,
                    )
                )
            self.bridge.log.emit("Weather station worker stopped")
    def handle_ui_call(self, callback):
        callback()

    def ui_call(self, callback):
        self.bridge.call.emit(callback)

    def append_rain_log(self, message):
        write_debug_log(message)
        self.log_rain(message)

    def log_event(self, source, message):
        if widget_is_alive(self.logs_page):
            self.logs_page.log(source, message)

    def log_rain(self, message):
        self.log_event("Rain", message)

    def log_battle(self, message):
        self.log_event("Battle", message)

    def log_stats(self, message):
        self.log_event("Stats", message)

    def set_developer_mode(self, enabled):
        self.developer_mode = bool(enabled)
        self.sync_developer_navigation()
        if not self.developer_mode and self.current_page == "Battles":
            self.show_page("Rain")
        self.build_rain_settings_page()
        self.log_event("Developer", "Developer mode enabled" if enabled else "Developer mode disabled")

    def build_session_pill(self):
        pill = QFrame()
        pill.setObjectName("SessionPill")
        layout = QHBoxLayout(pill)
        layout.setContentsMargins(13, 6, 13, 6)
        layout.setSpacing(7)

        title = QLabel("SESSION")
        title.setObjectName("SessionScrapTitle")
        layout.addWidget(title)

        scrap_icon = QLabel()
        scrap_icon.setObjectName("ScrapIcon")
        scrap_icon.setFixedSize(22, 22)
        scrap_path = legacy.resource_path("Scrap.png")
        pixmap = QPixmap(scrap_path)
        if pixmap.isNull():
            scrap_icon.setText("SCRAP")
            scrap_icon.setFixedWidth(42)
        else:
            scrap_icon.setPixmap(
                pixmap.scaled(22, 22, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        layout.addWidget(scrap_icon)
        layout.addWidget(self.total_label)
        return pill

    def build_topbar(self):
        topbar = QFrame()
        topbar.setObjectName("Topbar")
        topbar.setFixedHeight(58)

        layout = QHBoxLayout(topbar)
        layout.setContentsMargins(16, 6, 16, 6)
        layout.setSpacing(8)

        self.logo_button = BarrelLogoButton(lambda: self.show_page("Browser"))
        layout.addWidget(self.logo_button)

        for page in ("Rain", "Stats", "Logs"):
            button = QPushButton(page.upper())
            button.setObjectName("NavButton")
            button.clicked.connect(lambda checked=False, page=page: self.show_page(page))
            self.nav_buttons[page] = button
            layout.addWidget(button)

        battle_page = "Battles"
        battle_button = QPushButton(battle_page.upper())
        battle_button.setObjectName("NavButton")
        battle_button.clicked.connect(lambda checked=False, page=battle_page: self.show_page(page))
        self.nav_buttons[battle_page] = battle_button
        layout.addWidget(battle_button)
        battle_button.setVisible(self.developer_mode)

        layout.addStretch(1)
        layout.addWidget(self.session_pill)

        activity_controls = QFrame()
        activity_controls.setObjectName("ActivityControls")
        activity_layout = QVBoxLayout(activity_controls)
        activity_layout.setContentsMargins(0, 0, 0, 0)
        activity_layout.setSpacing(2)

        self.rain_status_button = ActivityToggleButton("RAIN", self.toggle_rain_ui)
        self.battle_status_button = ActivityToggleButton("BATTLES", self.toggle_battle_ui)
        activity_layout.addWidget(self.rain_status_button)
        activity_layout.addWidget(self.battle_status_button)
        layout.addWidget(activity_controls)

        mini_button = QPushButton("MINI")
        mini_button.setObjectName("NavButton")
        mini_button.setCursor(Qt.PointingHandCursor)
        mini_button.clicked.connect(self.enter_mini_mode)
        layout.addWidget(mini_button)

        version = QLabel(f"Version {APP_VERSION}")
        version.setObjectName("VersionLabel")
        layout.addWidget(version)

        return topbar

    def build_mini_bar(self):
        mini_bar = QFrame()
        mini_bar.setObjectName("MiniBar")
        mini_bar.setFixedHeight(52)

        layout = QHBoxLayout(mini_bar)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        title = QLabel("RB")
        title.setObjectName("MiniTitle")
        layout.addWidget(title)

        mini_activity = QFrame()
        mini_activity.setObjectName("MiniActivityStack")
        mini_activity_layout = QVBoxLayout(mini_activity)
        mini_activity_layout.setContentsMargins(0, 0, 0, 0)
        mini_activity_layout.setSpacing(2)
        self.mini_rain_status_button = ActivityToggleButton("RAIN", self.toggle_rain_ui)
        self.mini_rain_status_button.setObjectName("MiniActivityButton")
        self.mini_battle_status_button = ActivityToggleButton("BATTLES", self.toggle_battle_ui)
        self.mini_battle_status_button.setObjectName("MiniActivityButton")
        mini_activity_layout.addWidget(self.mini_rain_status_button)
        mini_activity_layout.addWidget(self.mini_battle_status_button)
        layout.addWidget(mini_activity)

        mini_stats = QFrame()
        mini_stats.setObjectName("MiniStats")
        mini_stats_layout = QVBoxLayout(mini_stats)
        mini_stats_layout.setContentsMargins(0, 0, 0, 0)
        mini_stats_layout.setSpacing(0)

        mini_session_row = QHBoxLayout()
        mini_session_row.setContentsMargins(0, 0, 0, 0)
        mini_session_row.setSpacing(4)
        mini_session_title = QLabel("SESSION")
        mini_session_title.setObjectName("MiniStatTitle")
        mini_session_row.addWidget(mini_session_title)
        mini_scrap_icon = QLabel()
        mini_scrap_icon.setObjectName("MiniScrapIcon")
        mini_scrap_icon.setFixedSize(14, 14)
        pixmap = QPixmap(legacy.resource_path("Scrap.png"))
        if pixmap.isNull():
            mini_scrap_icon.setText("S")
        else:
            mini_scrap_icon.setPixmap(
                pixmap.scaled(14, 14, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        mini_session_row.addWidget(mini_scrap_icon)
        self.mini_total_label = QLabel(self.get_total_text())
        self.mini_total_label.setObjectName("MiniStatValue")
        mini_session_row.addWidget(self.mini_total_label)
        mini_session_row.addStretch(1)
        mini_stats_layout.addLayout(mini_session_row)

        self.mini_prediction_label = QLabel(self.get_mini_prediction_text())
        self.mini_prediction_label.setObjectName("MiniPredictionValue")
        mini_stats_layout.addWidget(self.mini_prediction_label)
        layout.addWidget(mini_stats, 1)

        self.mini_pin_button = QPushButton("PIN")
        self.mini_pin_button.setObjectName("MiniActionButton")
        self.mini_pin_button.setCursor(Qt.PointingHandCursor)
        self.mini_pin_button.clicked.connect(self.toggle_mini_pin)

        full_button = QPushButton("FULL")
        full_button.setObjectName("MiniActionButton")
        full_button.setCursor(Qt.PointingHandCursor)
        full_button.clicked.connect(self.exit_mini_mode)

        action_stack = QFrame()
        action_stack.setObjectName("MiniActionStack")
        action_layout = QHBoxLayout(action_stack)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(4)
        action_layout.addWidget(self.mini_pin_button)
        action_layout.addWidget(full_button)
        layout.addWidget(action_stack)

        return mini_bar

    def build_body(self):
        body = QFrame()
        body.setObjectName("Body")

        layout = QHBoxLayout(body)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self.pages, 1)
        return body

    def create_stats_page(self):
        return StatsPage(
            {"stats": self.get_current_stats()},
            delete_result_callback=self.delete_rain_result,
            export_callback=self.export_stats,
            import_callback=self.import_stats,
            reset_callback=self.reset_stats,
            refresh_callback=lambda checked=False: self.reload_stats_page(),
        )

    def show_page(self, page):
        if page == "Battles" and not self.developer_mode:
            page = "Rain"
        self.current_page = page
        page_indexes = {
            "Rain": 0,
            "Browser": 1,
            "Battles": 2,
            "Stats": 3,
            "Logs": 4,
        }
        self.pages.setCurrentIndex(page_indexes[page])
        if page == "Browser":
            self.browser_page.ensure_loaded()

        for name, button in self.nav_buttons.items():
            button.setProperty("active", name == page)
            button.style().unpolish(button)
            button.style().polish(button)

        if self.logo_button is not None:
            self.logo_button.setProperty("active", page == "Browser")
            self.logo_button.style().unpolish(self.logo_button)
            self.logo_button.style().polish(self.logo_button)

    def sync_developer_navigation(self):
        battle_button = self.nav_buttons.get("Battles")
        if battle_button is not None and widget_is_alive(battle_button):
            battle_button.setVisible(self.developer_mode)

    def build_rain_settings_page(self):
        self.rain_page.clear_settings()
        self.check_timer_value_labels = {}
        self.confidence_spin = None
        self.interval_spin = None
        self.move_time_spin = None
        self.move_steps_spin = None
        self.popup_wait_spin = None
        self.weather_interval_spin = None
        self.rain_found_cooldown_spin = None
        self.tracker_watch_spin = None
        self.weather_rain_cooldown_spin = None
        self.tip_scan_interval_spin = None
        self.reward_scan_interval_spin = None
        self.result_scan_interval_spin = None
        self.min_prediction_checkbox = None
        self.min_prediction_spin = None

        control_layout = self.rain_page.add_settings_card("RAIN CONTROL")
        self.rain_page_button = self.add_side_button(control_layout, self.get_start_text(), self.toggle_rain_ui)
        self.auto_activate_checkbox = self.add_side_checkbox(
            control_layout,
            "Rain Auto Activate",
            bool(self.settings.get("rain_auto_activate", DEFAULT_RAIN_AUTO_ACTIVATE)),
        )
        self.auto_activate_checkbox.toggled.connect(self.handle_auto_activate_changed)
        self.collect_start_time = self.add_time_setting(
            control_layout,
            "Auto Start",
            self.settings.get("rain_collect_start_time", DEFAULT_RAIN_COLLECT_START_TIME),
            DEFAULT_RAIN_COLLECT_START_TIME,
        )
        self.collect_end_time = self.add_time_setting(
            control_layout,
            "Auto Stop",
            self.settings.get("rain_collect_end_time", DEFAULT_RAIN_COLLECT_END_TIME),
            DEFAULT_RAIN_COLLECT_END_TIME,
        )

        collection_layout = self.rain_page.add_settings_card("RAIN COLLECTION")
        self.rain_chance_spin = self.add_slider_setting(
            collection_layout,
            "Collection Chance",
            clamp_int(
                self.settings.get("rain_collect_chance"),
                DEFAULT_RAIN_COLLECT_CHANCE,
                0,
                100,
            ),
            0,
            100,
            "%",
        )
        self.min_prediction_checkbox = self.add_side_checkbox(
            collection_layout,
            "Only Join Above Prediction",
            bool(self.settings.get("rain_min_prediction_enabled", DEFAULT_RAIN_MIN_PREDICTION_ENABLED)),
        )
        self.min_prediction_spin = self.add_decimal_slider_setting(
            collection_layout,
            "Minimum Predicted Reward",
            int(
                round(
                    clamp_float(
                        self.settings.get("rain_min_predicted_reward"),
                        DEFAULT_RAIN_MIN_PREDICTED_REWARD,
                        0.0,
                        1.0,
                    )
                    * 100
                )
            ),
            0.0,
            1.0,
            " scrap",
        )

        weather_layout = self.rain_page.add_settings_card("WEATHER STATION")
        self.weather_station_checkbox = self.add_side_checkbox(
            weather_layout,
            "Weather Station",
            self.weather_station_active or bool(self.settings.get("weather_station_enabled", False)),
        )
        self.weather_station_checkbox.toggled.connect(self.toggle_weather_station)
        self.weather_station_status_label = self.add_side_label(weather_layout, self.weather_station_status)
        self.weather_volume_spin = self.add_slider_setting(
            weather_layout,
            "Volume",
            clamp_int(
                self.settings.get("weather_notification_volume"),
                DEFAULT_WEATHER_NOTIFICATION_VOLUME,
                0,
                100,
            ),
            0,
            100,
            "%",
        )

        prediction_layout = self.rain_page.add_settings_card("RAIN PREDICTION")
        self.rain_prediction_value_label = self.add_side_label(prediction_layout, "Expected Reward: --")
        self.rain_prediction_detail_label = self.add_side_label(prediction_layout, "Waiting for current rain tip and joined count.")
        self.rain_prediction_context_label = self.add_side_label(
            prediction_layout,
            f"Using {self.get_prediction_sample_count()} previous rains with tips.",
        )
        self.refresh_rain_prediction_labels()

        if self.developer_mode:
            advanced_layout = self.rain_page.add_settings_card("DEVELOPER SETTINGS", column_span=3)
            self.confidence_spin = self.add_spin_setting(
                advanced_layout,
                "Confidence",
                clamp_int(
                    self.settings.get("confidence"),
                    DEFAULT_CONFIDENCE_PERCENT,
                    40,
                    100,
                ),
                40,
                100,
                "%",
            )
            self.interval_spin = self.add_spin_setting(
                advanced_layout,
                "Rain Check Delay",
                clamp_int(
                    self.settings.get("interval"),
                    DEFAULT_RAIN_CLICKER_INTERVAL,
                    10,
                    90,
                ),
                10,
                90,
                "s",
            )
            self.move_time_spin = self.add_double_setting(
                advanced_layout,
                "Move Time",
                clamp_float(
                    self.settings.get("move_time"),
                    DEFAULT_MOVE_TIME,
                    0.1,
                    5.0,
                ),
                0.1,
                5.0,
                0.1,
                "s",
            )
            self.move_steps_spin = self.add_spin_setting(
                advanced_layout,
                "Move Steps",
                clamp_int(
                    self.settings.get("move_steps"),
                    legacy.DEFAULT_MOVE_STEPS,
                    10,
                    250,
                ),
                10,
                250,
            )
            self.popup_wait_spin = self.add_spin_setting(
                advanced_layout,
                "After-Click Popup Wait",
                clamp_int(
                    self.settings.get("popup_after_rain_wait_seconds"),
                    DEFAULT_POPUP_AFTER_RAIN_WAIT_SECONDS,
                    5,
                    30,
                ),
                5,
                30,
                "s",
            )
            self.weather_interval_spin = self.add_spin_setting(
                advanced_layout,
                "Weather Check Delay",
                clamp_int(
                    self.settings.get("weather_station_interval"),
                    DEFAULT_WEATHER_STATION_INTERVAL,
                    10,
                    90,
                ),
                10,
                90,
                "s",
            )
            self.rain_found_cooldown_spin = self.add_spin_setting(
                advanced_layout,
                "Rain Found Cooldown",
                clamp_int(
                    self.settings.get("rain_found_cooldown_seconds"),
                    DEFAULT_RAIN_FOUND_COOLDOWN_SECONDS,
                    30,
                    600,
                ),
                30,
                600,
                "s",
            )
            self.tracker_watch_spin = self.add_spin_setting(
                advanced_layout,
                "Tracker Watch Time",
                clamp_int(
                    self.settings.get("rain_tracker_watch_seconds"),
                    DEFAULT_RAIN_TRACKER_WATCH_SECONDS,
                    30,
                    600,
                ),
                30,
                600,
                "s",
            )
            self.weather_rain_cooldown_spin = self.add_spin_setting(
                advanced_layout,
                "Weather Rain Cooldown",
                clamp_int(
                    self.settings.get("weather_rain_found_cooldown_seconds"),
                    DEFAULT_WEATHER_RAIN_FOUND_COOLDOWN_SECONDS,
                    30,
                    600,
                ),
                30,
                600,
                "s",
            )
            self.tip_scan_interval_spin = self.add_double_setting(
                advanced_layout,
                "Tip Scan Delay",
                clamp_float(
                    self.settings.get("rain_tip_scan_interval_seconds"),
                    DEFAULT_RAIN_TIP_SCAN_INTERVAL_SECONDS,
                    0.2,
                    5.0,
                ),
                0.2,
                5.0,
                0.1,
                "s",
            )
            self.reward_scan_interval_spin = self.add_double_setting(
                advanced_layout,
                "Reward Scan Delay",
                clamp_float(
                    self.settings.get("rain_reward_scan_interval_seconds"),
                    DEFAULT_RAIN_REWARD_SCAN_INTERVAL_SECONDS,
                    0.2,
                    5.0,
                ),
                0.2,
                5.0,
                0.1,
                "s",
            )
            self.result_scan_interval_spin = self.add_double_setting(
                advanced_layout,
                "Result Scan Delay",
                clamp_float(
                    self.settings.get("rain_result_scan_interval_seconds"),
                    DEFAULT_RAIN_RESULT_SCAN_INTERVAL_SECONDS,
                    0.2,
                    5.0,
                ),
                0.2,
                5.0,
                0.1,
                "s",
            )
            self.add_check_timer_panel(advanced_layout)

        self.rain_page.add_footer_button("RESET DEFAULTS", self.reset_default_settings)

        self.connect_auto_save_settings()
        self.sync_auto_activate_controls()
        self.sync_rain_running_state()

    def add_side_button(self, layout, text, callback):
        button = QPushButton(text)
        button.setObjectName("SideButton")
        button.clicked.connect(callback)
        layout.addWidget(button)
        return button

    def add_side_separator(self, layout, text):
        label = QLabel(text)
        label.setObjectName("SideSection")
        layout.addWidget(label)
        return label

    def add_side_label(self, layout, text):
        label = QLabel(text)
        label.setObjectName("SideNote")
        label.setWordWrap(True)
        layout.addWidget(label)
        return label

    def add_side_checkbox(self, layout, text, checked):
        checkbox = QCheckBox(text.upper())
        checkbox.setObjectName("SideCheckbox")
        checkbox.setChecked(checked)
        layout.addWidget(checkbox)
        return checkbox

    def add_spin_setting(self, layout, label_text, value, minimum, maximum, suffix=""):
        row = QFrame()
        row.setObjectName("SettingRow")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)

        label = QLabel(label_text)
        label.setObjectName("SettingLabel")
        spin = QSpinBox()
        spin.setObjectName("SettingSpin")
        spin.setRange(minimum, maximum)
        spin.setValue(value)
        spin.setSuffix(suffix)

        row_layout.addWidget(label, 1)
        row_layout.addWidget(spin)
        layout.addWidget(row)
        return spin

    def add_double_setting(self, layout, label_text, value, minimum, maximum, step, suffix=""):
        row = QFrame()
        row.setObjectName("SettingRow")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)

        label = QLabel(label_text)
        label.setObjectName("SettingLabel")
        spin = QDoubleSpinBox()
        spin.setObjectName("SettingSpin")
        spin.setRange(minimum, maximum)
        spin.setSingleStep(step)
        spin.setDecimals(1)
        spin.setValue(value)
        spin.setSuffix(suffix)

        row_layout.addWidget(label, 1)
        row_layout.addWidget(spin)
        layout.addWidget(row)
        return spin

    def add_slider_setting(self, layout, label_text, value, minimum, maximum, suffix=""):
        row = QFrame()
        row.setObjectName("SettingRow")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)

        label = QLabel(label_text)
        label.setObjectName("SettingLabel")
        slider = QSlider(Qt.Horizontal)
        slider.setObjectName("SettingSlider")
        slider.setRange(minimum, maximum)
        slider.setValue(value)
        value_label = QLabel(f"{value}{suffix}")
        value_label.setObjectName("TimerValue")
        value_label.setFixedWidth(48)
        value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        slider.valueChanged.connect(lambda new_value, label=value_label: label.setText(f"{new_value}{suffix}"))

        row_layout.addWidget(label, 1)
        row_layout.addWidget(slider, 2)
        row_layout.addWidget(value_label)
        layout.addWidget(row)
        return slider

    def add_decimal_slider_setting(self, layout, label_text, value, minimum, maximum, suffix=""):
        row = QFrame()
        row.setObjectName("SettingRow")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)

        label = QLabel(label_text)
        label.setObjectName("SettingLabel")
        slider = QSlider(Qt.Horizontal)
        slider.setObjectName("SettingSlider")
        slider.setRange(int(round(minimum * 100)), int(round(maximum * 100)))
        slider.setValue(clamp_int(value, int(round(minimum * 100)), int(round(minimum * 100)), int(round(maximum * 100))))
        value_label = QLabel(f"{slider.value() / 100:.2f}{suffix}")
        value_label.setObjectName("TimerValue")
        value_label.setFixedWidth(76)
        value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        slider.valueChanged.connect(
            lambda new_value, label=value_label: label.setText(f"{new_value / 100:.2f}{suffix}")
        )

        row_layout.addWidget(label, 1)
        row_layout.addWidget(slider, 2)
        row_layout.addWidget(value_label)
        layout.addWidget(row)
        return slider

    def add_time_setting(self, layout, label_text, value, default):
        row = QFrame()
        row.setObjectName("SettingRow")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)

        label = QLabel(label_text)
        label.setObjectName("SettingLabel")
        time_edit = QTimeEdit()
        time_edit.setObjectName("SettingSpin")
        time_edit.setDisplayFormat("h:mm AP")
        time_edit.setTime(parse_time_setting(value, default))

        row_layout.addWidget(label, 1)
        row_layout.addWidget(time_edit)
        layout.addWidget(row)
        return time_edit

    def connect_auto_save_settings(self):
        controls = [
            self.weather_volume_spin,
            self.rain_chance_spin,
            self.min_prediction_spin,
        ]
        for control in (
            self.confidence_spin,
            self.interval_spin,
            self.move_time_spin,
            self.move_steps_spin,
            self.popup_wait_spin,
            self.weather_interval_spin,
            self.rain_found_cooldown_spin,
            self.tracker_watch_spin,
            self.weather_rain_cooldown_spin,
            self.tip_scan_interval_spin,
            self.reward_scan_interval_spin,
            self.result_scan_interval_spin,
        ):
            if widget_is_alive(control):
                controls.append(control)

        for control in controls:
            control.valueChanged.connect(self.auto_save_rain_settings)

        self.weather_volume_spin.valueChanged.connect(self.schedule_weather_volume_preview)
        if widget_is_alive(self.min_prediction_checkbox):
            self.min_prediction_checkbox.toggled.connect(self.auto_save_rain_settings)
        self.collect_start_time.timeChanged.connect(self.auto_save_rain_settings)
        self.collect_end_time.timeChanged.connect(self.auto_save_rain_settings)

    def add_check_timer_panel(self, layout):
        card = QFrame()
        card.setObjectName("TimerCard")
        card_layout = QGridLayout(card)
        card_layout.setContentsMargins(12, 10, 12, 10)
        card_layout.setHorizontalSpacing(8)
        card_layout.setVerticalSpacing(5)

        title = QLabel("CHECK TIMERS")
        title.setObjectName("SettingLabel")
        card_layout.addWidget(title, 0, 0, 1, 2)

        self.check_timer_value_labels = {}
        rows = [
            ("Rain Collector", "rain_collector"),
            ("Weather Station", "weather_station"),
            ("Reward Checker", "reward_checker"),
            ("Results Checker", "result_checker"),
        ]
        values = self.get_check_timer_values()
        for row_index, (label_text, key) in enumerate(rows, start=1):
            label = QLabel(label_text)
            label.setObjectName("SettingLabel")
            value = QLabel(values.get(key, "Off"))
            value.setObjectName("TimerValue")
            value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            card_layout.addWidget(label, row_index, 0)
            card_layout.addWidget(value, row_index, 1)
            self.check_timer_value_labels[key] = value

        layout.addWidget(card)
        return card

    def auto_save_rain_settings(self, *args):
        self.save_rain_settings(log=False)

    def handle_auto_activate_changed(self, checked):
        self.sync_auto_activate_controls()
        self.save_rain_settings(log=False)

    def sync_auto_activate_controls(self):
        enabled = bool(self.auto_activate_checkbox.isChecked())
        self.collect_start_time.setEnabled(enabled)
        self.collect_end_time.setEnabled(enabled)

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
            "rain_collector": self.format_countdown(self.rain_collector_next_check_at, self.rain_running),
            "weather_station": self.format_countdown(self.weather_station_next_check_at, self.weather_station_active),
            "reward_checker": self.format_countdown(
                self.rain_reward_next_check_at,
                self.rain_reward_tracker_active,
                self.rain_reward_timer_status if self.rain_reward_tracker_active and self.rain_reward_timer_status != "Off" else None,
            ),
            "result_checker": self.format_countdown(
                self.rain_result_next_check_at,
                self.rain_result_tracker_active,
                self.rain_result_timer_status if self.rain_result_tracker_active and self.rain_result_timer_status != "Off" else None,
            ),
        }

    def refresh_check_timer_labels(self):
        values = self.get_check_timer_values()
        for key, label in list(self.check_timer_value_labels.items()):
            try:
                label.setText(values.get(key, "Off"))
            except RuntimeError:
                self.check_timer_value_labels.pop(key, None)

    def get_start_text(self):
        return "STOP" if self.rain_running else "START"

    def toggle_rain_ui(self):
        if self.rain_running:
            self.stop_rain_collector()
        else:
            self.start_rain_collector()

    def toggle_battle_ui(self):
        if self.battle_running:
            self.battle_running = False
            self.refresh_keep_awake_state()
            self.sync_battle_running_state()
            self.log_battle("Stopped")
            return

        self.log_battle("Battle scanner migration is still pending.")

    def enter_mini_mode(self):
        if self.mini_mode:
            return

        self.mini_mode = True
        self.mini_mode_normal_flags = self.windowFlags()
        self.full_mode_was_maximized = self.isMaximized()
        self.full_mode_geometry = self.geometry()
        if self.full_mode_was_maximized:
            self.showNormal()

        self.setWindowFlag(Qt.FramelessWindowHint, True)
        self.setWindowFlag(Qt.WindowStaysOnTopHint, self.mini_pinned)
        self.topbar.hide()
        self.body.hide()
        self.mini_bar.show()
        self.setMinimumSize(360, 52)
        self.setMaximumSize(460, 52)
        self.resize(410, 52)
        self.restore_mini_window_position()
        self.show()
        self.sync_rain_running_state()
        self.sync_battle_running_state()
        self.sync_mini_pin_state()
        self.refresh_mini_stats_labels()

    def exit_mini_mode(self):
        if not self.mini_mode:
            return

        self.save_mini_window_position()
        self.mini_mode = False
        geometry = self.geometry()
        self.setWindowFlag(Qt.FramelessWindowHint, False)
        self.setWindowFlag(Qt.WindowStaysOnTopHint, self.mini_pinned)
        self.setMaximumSize(16777215, 16777215)
        self.setMinimumSize(980, 620)
        self.mini_bar.hide()
        self.topbar.show()
        self.body.show()

        if self.full_mode_was_maximized:
            self.showMaximized()
        elif self.full_mode_geometry is not None:
            self.setGeometry(self.full_mode_geometry)
            self.show()
        else:
            self.setGeometry(geometry)
            self.resize(1280, 820)
            self.show()

    def restore_mini_window_position(self):
        try:
            x = int(self.settings.get("mini_window_x"))
            y = int(self.settings.get("mini_window_y"))
        except (TypeError, ValueError):
            return
        self.move(x, y)

    def save_mini_window_position(self):
        if not self.mini_mode:
            return
        position = self.pos()
        self.settings["mini_window_x"] = int(position.x())
        self.settings["mini_window_y"] = int(position.y())
        self.save_data()

    def toggle_mini_pin(self):
        self.mini_pinned = not self.mini_pinned
        geometry = self.geometry()
        self.setWindowFlag(Qt.WindowStaysOnTopHint, self.mini_pinned)
        self.setGeometry(geometry)
        self.show()
        self.sync_mini_pin_state()

    def sync_mini_pin_state(self):
        if self.mini_pin_button is not None and widget_is_alive(self.mini_pin_button):
            self.mini_pin_button.setText("UNPIN" if self.mini_pinned else "PIN")
            self.mini_pin_button.setProperty("active", self.mini_pinned)
            self.mini_pin_button.style().unpolish(self.mini_pin_button)
            self.mini_pin_button.style().polish(self.mini_pin_button)

    def mousePressEvent(self, event):
        if self.mini_mode and event.button() == Qt.LeftButton:
            self.mini_drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.mini_mode and self.mini_drag_offset is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self.mini_drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.mini_mode:
            self.mini_drag_offset = None
            self.save_mini_window_position()
        super().mouseReleaseEvent(event)

    def sync_rain_running_state(self):
        self.rain_page.set_running(self.rain_running)
        if self.rain_status_button is not None and widget_is_alive(self.rain_status_button):
            self.rain_status_button.set_active(self.rain_running)
        if self.mini_rain_status_button is not None and widget_is_alive(self.mini_rain_status_button):
            self.mini_rain_status_button.set_active(self.rain_running)
        if self.rain_page_button is not None and widget_is_alive(self.rain_page_button):
            self.rain_page_button.setText(self.get_start_text())
            self.rain_page_button.setProperty("running", self.rain_running)
            self.rain_page_button.style().unpolish(self.rain_page_button)
            self.rain_page_button.style().polish(self.rain_page_button)

    def sync_battle_running_state(self):
        if self.battle_status_button is not None and widget_is_alive(self.battle_status_button):
            self.battle_status_button.set_active(self.battle_running)
        if self.mini_battle_status_button is not None and widget_is_alive(self.mini_battle_status_button):
            self.mini_battle_status_button.set_active(self.battle_running)

    def rain_event_visually_active(self):
        now = time.time()
        if self.weather_station_last_state is True:
            return True
        if now < float(self.rain_visual_active_until or 0):
            return True
        if now < self.get_rain_tracking_watch_until():
            return True
        return (
            self.rain_tip_tracker_active
            or self.rain_reward_tracker_active
            or self.rain_result_tracker_active
        )

    def sync_barrel_logo_state(self):
        if self.logo_button is not None and widget_is_alive(self.logo_button):
            self.logo_button.set_rain_active(self.rain_event_visually_active())

    def get_total_search_time_seconds(self):
        if self.rain_running and self.current_session_started_at is not None:
            return self.total_search_time_seconds + (time.time() - self.current_session_started_at)
        return self.total_search_time_seconds

    def get_current_session_seconds(self):
        if self.rain_running and self.current_session_started_at is not None:
            return self.current_session_seconds + (time.time() - self.current_session_started_at)
        return self.current_session_seconds

    def get_total_weather_station_time_seconds(self):
        if self.weather_station_active and self.weather_station_started_at is not None:
            return self.total_weather_station_time_seconds + (time.time() - self.weather_station_started_at)
        return self.total_weather_station_time_seconds

    def get_current_weather_session_seconds(self):
        if self.weather_station_active and self.weather_station_started_at is not None:
            return self.current_weather_session_seconds + (time.time() - self.weather_station_started_at)
        return self.current_weather_session_seconds

    def start_rain_session(self):
        if self.current_session_started_at is None:
            self.current_session_seconds = 0.0
            self.current_session_rains_clicked = 0
            self.current_session_rain_collected = 0.0
            self.current_session_started_at = time.time()
            self.current_session_started_label = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def stop_rain_session(self):
        if self.current_session_started_at is None:
            return
        elapsed = max(0.0, time.time() - self.current_session_started_at)
        self.total_search_time_seconds += elapsed
        self.current_session_seconds += elapsed
        self.current_session_started_at = None

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

    def get_interval_seconds(self):
        return clamp_int(self.settings.get("interval"), DEFAULT_RAIN_CLICKER_INTERVAL, 10, 90)

    def get_confidence(self):
        return clamp_int(self.settings.get("confidence"), DEFAULT_CONFIDENCE_PERCENT, 40, 100) / 100.0

    def get_move_time(self):
        return clamp_float(self.settings.get("move_time"), DEFAULT_MOVE_TIME, 0.1, 5.0)

    def get_move_steps(self):
        return clamp_int(self.settings.get("move_steps"), legacy.DEFAULT_MOVE_STEPS, 10, 250)

    def get_rain_collect_chance(self):
        return clamp_int(self.settings.get("rain_collect_chance"), DEFAULT_RAIN_COLLECT_CHANCE, 0, 100)

    def get_rain_min_prediction_enabled(self):
        return bool(
            self.settings.get(
                "rain_min_prediction_enabled",
                DEFAULT_RAIN_MIN_PREDICTION_ENABLED,
            )
        )

    def get_rain_min_predicted_reward(self):
        return clamp_float(
            self.settings.get("rain_min_predicted_reward"),
            DEFAULT_RAIN_MIN_PREDICTED_REWARD,
            0.0,
            1.0,
        )

    def get_rain_found_cooldown_seconds(self):
        return clamp_int(
            self.settings.get("rain_found_cooldown_seconds"),
            DEFAULT_RAIN_FOUND_COOLDOWN_SECONDS,
            30,
            600,
        )

    def get_rain_tracker_watch_seconds(self):
        return clamp_int(
            self.settings.get("rain_tracker_watch_seconds"),
            DEFAULT_RAIN_TRACKER_WATCH_SECONDS,
            30,
            600,
        )

    def get_weather_rain_found_cooldown_seconds(self):
        return clamp_int(
            self.settings.get("weather_rain_found_cooldown_seconds"),
            DEFAULT_WEATHER_RAIN_FOUND_COOLDOWN_SECONDS,
            30,
            600,
        )

    def get_rain_tip_scan_interval_seconds(self):
        return clamp_float(
            self.settings.get("rain_tip_scan_interval_seconds"),
            DEFAULT_RAIN_TIP_SCAN_INTERVAL_SECONDS,
            0.2,
            5.0,
        )

    def get_rain_reward_scan_interval_seconds(self):
        return clamp_float(
            self.settings.get("rain_reward_scan_interval_seconds"),
            DEFAULT_RAIN_REWARD_SCAN_INTERVAL_SECONDS,
            0.2,
            5.0,
        )

    def get_rain_result_scan_interval_seconds(self):
        return clamp_float(
            self.settings.get("rain_result_scan_interval_seconds"),
            DEFAULT_RAIN_RESULT_SCAN_INTERVAL_SECONDS,
            0.2,
            5.0,
        )

    def get_rain_auto_activate(self):
        return bool(self.settings.get("rain_auto_activate", DEFAULT_RAIN_AUTO_ACTIVATE))

    def get_popup_after_rain_wait_seconds(self):
        return clamp_int(
            self.settings.get("popup_after_rain_wait_seconds"),
            DEFAULT_POPUP_AFTER_RAIN_WAIT_SECONDS,
            5,
            30,
        )

    def time_setting_to_minutes(self, value):
        parsed = QTime.fromString(str(value), "HH:mm")
        if not parsed.isValid():
            return None
        return parsed.hour() * 60 + parsed.minute()

    def enforce_rain_auto_activation(self):
        if not self.get_rain_auto_activate():
            return

        start_minutes = self.time_setting_to_minutes(
            self.settings.get("rain_collect_start_time", DEFAULT_RAIN_COLLECT_START_TIME)
        )
        end_minutes = self.time_setting_to_minutes(
            self.settings.get("rain_collect_end_time", DEFAULT_RAIN_COLLECT_END_TIME)
        )
        if start_minutes is None or end_minutes is None:
            return

        now = datetime.now()
        current_minutes = now.hour * 60 + now.minute
        today = now.strftime("%Y-%m-%d")
        if current_minutes == start_minutes:
            start_key = f"{today}:{start_minutes}"
            if self.rain_auto_last_start_key != start_key:
                self.rain_auto_last_start_key = start_key
                if not self.rain_running:
                    self.start_rain_collector(trigger="auto start time")
        if current_minutes == end_minutes:
            stop_key = f"{today}:{end_minutes}"
            if self.rain_auto_last_stop_key != stop_key:
                self.rain_auto_last_stop_key = stop_key
                if self.rain_running:
                    self.stop_rain_collector(trigger="auto stop time")

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
        if not self.rain_collection_chance_allowed(x, y):
            return False, f"Skipped rain target image by collection chance ({self.get_rain_collect_chance():.0f}%)"
        if self.get_rain_min_prediction_enabled():
            threshold = self.get_rain_min_predicted_reward()
            amount, people, detail = self.read_rain_tip_context_from_browser_page()
            if amount is None or people is None:
                return False, f"Skipped rain target image by prediction filter ({detail})"

            prediction = predict_rain_reward_from_history(self.rain_result_history, amount, people)
            self.ui_call(lambda tipped=amount, people=int(people): self.update_rain_reward_prediction(tipped, people))
            if prediction is None:
                return False, "Skipped rain target image by prediction filter (not enough matching result history)"
            if prediction["estimate"] < threshold:
                return (
                    False,
                    "Skipped rain target image by prediction filter "
                    f"(predicted {format_rain_amount(prediction['estimate'])} < "
                    f"{format_rain_amount(threshold)} scrap)",
                )
        return True, ""

    def sleep_with_check_timer(self, attr_name, seconds, should_continue=None):
        deadline = time.time() + max(0.0, float(seconds))
        setattr(self, attr_name, deadline)
        while time.time() < deadline:
            if should_continue is not None and not should_continue():
                return False
            time.sleep(min(0.25, max(0.0, deadline - time.time())))
        if should_continue is not None and not should_continue():
            return False
        setattr(self, attr_name, time.time())
        return True

    def get_current_rain_settings(self):
        if not hasattr(self, "rain_chance_spin") or not widget_is_alive(self.rain_chance_spin):
            return dict(self.settings)

        try:
            confidence = (
                self.confidence_spin.value()
                if widget_is_alive(self.confidence_spin)
                else clamp_int(self.settings.get("confidence"), DEFAULT_CONFIDENCE_PERCENT, 40, 100)
            )
            interval = (
                self.interval_spin.value()
                if widget_is_alive(self.interval_spin)
                else clamp_int(self.settings.get("interval"), DEFAULT_RAIN_CLICKER_INTERVAL, 10, 90)
            )
            move_time = (
                self.move_time_spin.value()
                if widget_is_alive(self.move_time_spin)
                else clamp_float(self.settings.get("move_time"), DEFAULT_MOVE_TIME, 0.1, 5.0)
            )
            move_steps = (
                self.move_steps_spin.value()
                if widget_is_alive(self.move_steps_spin)
                else clamp_int(self.settings.get("move_steps"), legacy.DEFAULT_MOVE_STEPS, 10, 250)
            )
            popup_wait = (
                self.popup_wait_spin.value()
                if widget_is_alive(self.popup_wait_spin)
                else clamp_int(
                    self.settings.get("popup_after_rain_wait_seconds"),
                    DEFAULT_POPUP_AFTER_RAIN_WAIT_SECONDS,
                    5,
                    30,
                )
            )
            rain_found_cooldown = (
                self.rain_found_cooldown_spin.value()
                if widget_is_alive(self.rain_found_cooldown_spin)
                else self.get_rain_found_cooldown_seconds()
            )
            tracker_watch = (
                self.tracker_watch_spin.value()
                if widget_is_alive(self.tracker_watch_spin)
                else self.get_rain_tracker_watch_seconds()
            )
            weather_rain_cooldown = (
                self.weather_rain_cooldown_spin.value()
                if widget_is_alive(self.weather_rain_cooldown_spin)
                else self.get_weather_rain_found_cooldown_seconds()
            )
            tip_scan_interval = (
                self.tip_scan_interval_spin.value()
                if widget_is_alive(self.tip_scan_interval_spin)
                else self.get_rain_tip_scan_interval_seconds()
            )
            reward_scan_interval = (
                self.reward_scan_interval_spin.value()
                if widget_is_alive(self.reward_scan_interval_spin)
                else self.get_rain_reward_scan_interval_seconds()
            )
            result_scan_interval = (
                self.result_scan_interval_spin.value()
                if widget_is_alive(self.result_scan_interval_spin)
                else self.get_rain_result_scan_interval_seconds()
            )
            return {
                **self.settings,
                "weather_station_enabled": self.weather_station_checkbox.isChecked(),
                "weather_station_interval": (
                    self.weather_interval_spin.value()
                    if widget_is_alive(self.weather_interval_spin)
                    else clamp_int(
                        self.settings.get("weather_station_interval"),
                        DEFAULT_WEATHER_STATION_INTERVAL,
                        10,
                        90,
                    )
                ),
                "weather_notification_volume": self.weather_volume_spin.value(),
                "confidence": confidence,
                "rain_auto_activate": self.auto_activate_checkbox.isChecked(),
                "rain_collect_chance": self.rain_chance_spin.value(),
                "rain_collect_any_time": True,
                "rain_collect_start_time": self.collect_start_time.time().toString("HH:mm"),
                "rain_collect_end_time": self.collect_end_time.time().toString("HH:mm"),
                "interval": interval,
                "move_time": move_time,
                "move_steps": move_steps,
                "popup_after_rain_wait_seconds": popup_wait,
                "rain_found_cooldown_seconds": rain_found_cooldown,
                "rain_tracker_watch_seconds": tracker_watch,
                "weather_rain_found_cooldown_seconds": weather_rain_cooldown,
                "rain_tip_scan_interval_seconds": tip_scan_interval,
                "rain_reward_scan_interval_seconds": reward_scan_interval,
                "rain_result_scan_interval_seconds": result_scan_interval,
                "rain_min_prediction_enabled": self.min_prediction_checkbox.isChecked(),
                "rain_min_predicted_reward": self.min_prediction_spin.value() / 100.0,
            }
        except RuntimeError:
            return dict(self.settings)

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

    def save_data(self):
        self.saved_data["settings"] = dict(self.settings)
        self.saved_data["stats"] = self.get_current_stats()
        return save_saved_data(self.saved_data)

    def save_stats(self):
        saved = self.save_data()
        self.refresh_data()
        return saved

    def save_rain_settings(self, log=True):
        self.settings = self.get_current_rain_settings()
        saved = self.save_data()
        message = "Settings applied" if saved else "Save failed"
        if hasattr(self, "settings_status") and widget_is_alive(self.settings_status):
            color = COLORS["green"] if saved else COLORS["red2"]
            self.settings_status.setText(message)
            self.settings_status.setStyleSheet(f"color: {color};")
        if log or not saved:
            self.log_rain(message)

    def reset_default_settings(self):
        self.settings = {
            **self.settings,
            "confidence": DEFAULT_CONFIDENCE_PERCENT,
            "interval": DEFAULT_RAIN_CLICKER_INTERVAL,
            "move_time": DEFAULT_MOVE_TIME,
            "move_steps": legacy.DEFAULT_MOVE_STEPS,
            "rain_auto_activate": DEFAULT_RAIN_AUTO_ACTIVATE,
            "rain_collect_any_time": DEFAULT_RAIN_COLLECT_ANY_TIME,
            "rain_collect_start_time": DEFAULT_RAIN_COLLECT_START_TIME,
            "rain_collect_end_time": DEFAULT_RAIN_COLLECT_END_TIME,
            "rain_collect_chance": DEFAULT_RAIN_COLLECT_CHANCE,
            "rain_min_prediction_enabled": DEFAULT_RAIN_MIN_PREDICTION_ENABLED,
            "rain_min_predicted_reward": DEFAULT_RAIN_MIN_PREDICTED_REWARD,
            "weather_station_interval": DEFAULT_WEATHER_STATION_INTERVAL,
            "weather_notification_volume": DEFAULT_WEATHER_NOTIFICATION_VOLUME,
            "popup_after_rain_wait_seconds": DEFAULT_POPUP_AFTER_RAIN_WAIT_SECONDS,
            "rain_found_cooldown_seconds": DEFAULT_RAIN_FOUND_COOLDOWN_SECONDS,
            "rain_tracker_watch_seconds": DEFAULT_RAIN_TRACKER_WATCH_SECONDS,
            "weather_rain_found_cooldown_seconds": DEFAULT_WEATHER_RAIN_FOUND_COOLDOWN_SECONDS,
            "rain_tip_scan_interval_seconds": DEFAULT_RAIN_TIP_SCAN_INTERVAL_SECONDS,
            "rain_reward_scan_interval_seconds": DEFAULT_RAIN_REWARD_SCAN_INTERVAL_SECONDS,
            "rain_result_scan_interval_seconds": DEFAULT_RAIN_RESULT_SCAN_INTERVAL_SECONDS,
        }
        self.saved_data["settings"] = self.settings
        self.save_data()
        self.build_rain_settings_page()
        self.log_rain("Default settings restored")

    def refresh_keep_awake_state(self):
        flags = legacy.ES_CONTINUOUS
        if self.rain_running or self.weather_station_active or self.battle_running:
            flags |= legacy.ES_SYSTEM_REQUIRED | legacy.ES_DISPLAY_REQUIRED

        try:
            ctypes.windll.kernel32.SetThreadExecutionState(flags)
        except Exception:
            pass

    def start_rain_collector(self, trigger="manual"):
        write_debug_log("start_rain_collector called")
        self.save_rain_settings(log=False)
        self.rain_running = True
        self.rain_run_id += 1
        run_id = self.rain_run_id
        self.rain_scan_found_last_check = None
        self.rain_collector_next_check_at = time.time()
        self.start_rain_session()
        self.save_stats()
        self.refresh_keep_awake_state()
        self.sync_rain_running_state()
        self.log_rain("Started" if trigger == "manual" else f"Started by {trigger}")
        self.rain_worker_thread = threading.Thread(target=self.rain_worker, args=(run_id,), daemon=True)
        self.rain_worker_thread.start()

    def stop_rain_collector(self, trigger="manual"):
        write_debug_log("stop_rain_collector called")
        self.rain_running = False
        self.rain_run_id += 1
        self.stop_rain_session()
        self.rain_collector_next_check_at = None
        self.save_stats()
        self.refresh_keep_awake_state()
        self.sync_rain_running_state()
        self.log_rain("Stopped" if trigger == "manual" else f"Stopped by {trigger}")

    def record_rain_detected(self, source):
        self.last_rain_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.last_action = f"Rain detected by {source}"
        self.rain_visual_active_until = max(
            self.rain_visual_active_until,
            time.time() + self.get_rain_tracker_watch_seconds(),
        )
        self.sync_barrel_logo_state()
        self.save_stats()

    def rain_worker(self, run_id):
        self.bridge.log.emit("Rain worker thread started")
        while self.rain_running and run_id == self.rain_run_id:
            try:
                self.rain_collector_next_check_at = time.time()
                confidence = self.get_confidence()
                match, best_match = legacy.locate_rain_target_all_monitors(confidence)

                if match:
                    self.rain_scan_found_last_check = True
                    x = match["x"]
                    y = match["y"]
                    score = match["score"]
                    scale = match["scale"]
                    self.ui_call(lambda: self.record_rain_detected("normal tracker"))
                    self.bridge.log.emit(
                        f"Found rain target image | X={x} Y={y} confidence={score:.3f} scale={scale:.2f}"
                    )

                    allowed, skip_reason = self.rain_collection_allowed(x, y)
                    if not allowed:
                        self.last_action = skip_reason
                        self.ui_call(self.save_stats)
                        self.bridge.log.emit(skip_reason)
                        self.sleep_with_check_timer(
                            "rain_collector_next_check_at",
                            2,
                            should_continue=lambda: self.rain_running and run_id == self.rain_run_id,
                        )
                        continue

                    legacy.move_cursor_smooth(
                        x,
                        y,
                        total_time=self.get_move_time(),
                        steps=self.get_move_steps(),
                    )
                    if not self.rain_running or run_id != self.rain_run_id:
                        break

                    legacy.pyautogui.click(x, y)
                    self.chance_skipped_rain_target = None
                    self.total_rains_clicked += 1
                    self.current_session_rains_clicked += 1
                    self.last_action = "Clicked rain join button"
                    self.ui_call(self.save_stats)
                    self.bridge.log.emit("Clicked rain join button")
                    self.start_rain_trackers("rain clicker")
                    self.wait_for_popup_after_rain_and_click()

                    move_x, move_y = legacy.get_random_point_all_monitors(avoid_x=x, avoid_y=y)
                    legacy.move_cursor_smooth(
                        move_x,
                        move_y,
                        total_time=self.get_move_time(),
                        steps=self.get_move_steps(),
                    )
                    self.sleep_with_check_timer(
                        "rain_collector_next_check_at",
                        self.get_rain_found_cooldown_seconds(),
                        should_continue=lambda: self.rain_running and run_id == self.rain_run_id,
                    )
                    continue

                self.chance_skipped_rain_target = None
                if self.rain_scan_found_last_check is not False:
                    if best_match:
                        color_diff = best_match.get("color_diff")
                        color_detail = (
                            f", color diff={color_diff:.1f}/{legacy.RAIN_TARGET_MAX_COLOR_DIFF:.1f}"
                            if color_diff is not None
                            else ""
                        )
                        self.bridge.log.emit(
                            "Rain target image not found "
                            f"(best confidence={best_match['score']:.3f}, needed={confidence:.3f}, "
                            f"scale={best_match['scale']:.2f}{color_detail})"
                        )
                    else:
                        self.bridge.log.emit("Rain target image not found (no screenshot/template match data)")
                self.rain_scan_found_last_check = False
            except Exception as e:
                self.error_count += 1
                self.last_action = "Error"
                self.ui_call(self.save_stats)
                self.bridge.log.emit(f"Error: {type(e).__name__}: {repr(e)}")

            self.sleep_with_check_timer(
                "rain_collector_next_check_at",
                self.get_interval_seconds(),
                should_continue=lambda: self.rain_running and run_id == self.rain_run_id,
            )

        self.rain_collector_next_check_at = None
        self.bridge.log.emit("Rain worker thread stopped")

    def get_total_text(self):
        return format_rain_amount(self.current_session_rain_collected)

    def refresh_data(self):
        self.enforce_rain_auto_activation()
        self.total_label.setText(self.get_total_text())
        self.refresh_mini_stats_labels()
        self.sync_barrel_logo_state()
        if self.pages.currentWidget() is self.stats_page:
            stats = self.get_current_stats()
            if not self.stats_page.refresh_stats(stats):
                self.reload_stats_page()

    def get_stats_scroll_value(self):
        if self.pages.currentWidget() is not self.stats_page:
            return None
        try:
            return self.stats_page.scroll_area.verticalScrollBar().value()
        except RuntimeError:
            return None

    def reload_stats_page(self, scroll_value=None):
        index = self.pages.indexOf(self.stats_page)
        old_page = self.stats_page
        if scroll_value is None:
            try:
                scroll_value = old_page.scroll_area.verticalScrollBar().value()
            except RuntimeError:
                scroll_value = 0
        self.pages.removeWidget(old_page)
        old_page.deleteLater()
        self.stats_page = self.create_stats_page()
        self.pages.insertWidget(index, self.stats_page)
        self.pages.setCurrentIndex(index)
        QTimer.singleShot(0, lambda value=scroll_value: self.restore_stats_scroll(value))

    def restore_stats_scroll(self, value):
        if not widget_is_alive(self.stats_page):
            return
        try:
            scrollbar = self.stats_page.scroll_area.verticalScrollBar()
            scrollbar.setValue(min(value, scrollbar.maximum()))
        except RuntimeError:
            pass

    def reload_stats_if_visible(self, scroll_value=None):
        if self.pages.currentWidget() is self.stats_page:
            self.reload_stats_page(scroll_value)

    def reset_stats(self):
        self.total_search_time_seconds = 0.0
        self.total_rains_clicked = 0
        self.total_rain_collected = 0.0
        self.total_after_rain_popups_clicked = 0
        self.last_rain_reward = 0.0
        self.rain_reward_history = []
        self.rain_result_history = []
        self.pending_rain_prediction = None
        self.rain_prediction_last_log_key = None
        self.last_weather_notification_key = None
        self.last_rain_time = "--"
        self.last_action = "--"
        self.error_count = 0
        self.total_weather_station_time_seconds = 0.0
        self.total_weather_notifications = 0
        if self.rain_running:
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
        self.log_stats("Stats reset")
        self.refresh_rain_prediction_labels()
        self.reload_stats_if_visible()

    def export_stats(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export RainBarrel stats",
            "rainbarrel-stats.json",
            "JSON Files (*.json);;All Files (*)",
        )
        if not path:
            return
        payload = {
            "app": APP_NAME,
            "version": APP_VERSION,
            "exported_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "stats": self.get_current_stats(),
        }
        try:
            with open(path, "w", encoding="utf-8") as file:
                json.dump(payload, file, indent=2)
        except OSError as e:
            self.log_stats(f"Stats export failed: {e.__class__.__name__}")
            return
        self.log_stats(f"Stats exported to {path}")

    def import_stats(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import RainBarrel stats",
            "",
            "JSON Files (*.json);;All Files (*)",
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as file:
                payload = json.load(file)
        except (OSError, json.JSONDecodeError) as e:
            self.log_stats(f"Stats import failed: {e.__class__.__name__}")
            return
        stats = payload.get("stats") if isinstance(payload, dict) else None
        if not isinstance(stats, dict):
            self.log_stats("Stats import failed: no stats object found")
            return

        self.saved_data["stats"] = stats
        self.total_search_time_seconds = float(stats.get("total_search_time_seconds", 0.0) or 0.0)
        self.total_rains_clicked = int(stats.get("total_rains_clicked", 0) or 0)
        self.total_rain_collected = float(stats.get("total_rain_collected", 0.0) or 0.0)
        self.total_after_rain_popups_clicked = int(stats.get("total_after_rain_popups_clicked", 0) or 0)
        self.last_rain_reward = float(stats.get("last_rain_reward", 0.0) or 0.0)
        self.rain_reward_history = clean_rain_reward_history(stats.get("rain_reward_history", []))
        self.rain_result_history = clean_rain_result_history(stats.get("rain_result_history", []))
        self.total_weather_station_time_seconds = float(stats.get("total_weather_station_time_seconds", 0.0) or 0.0)
        self.total_weather_notifications = int(stats.get("total_weather_notifications", 0) or 0)
        self.last_weather_notification_key = stats.get("last_weather_notification_key")
        self.last_rain_time = stats.get("last_rain_time", "--")
        self.last_action = stats.get("last_action", "Stats imported")
        self.error_count = int(stats.get("error_count", 0) or 0)
        self.save_stats()
        self.log_stats(f"Stats imported from {path}")
        self.reload_stats_if_visible()

    def open_bandit_website(self):
        self.show_page("Browser")

    def closeEvent(self, event):
        self.rain_running = False
        self.rain_run_id += 1
        self.rain_tip_tracker_active = False
        self.rain_tip_tracker_run_id += 1
        self.rain_reward_tracker_active = False
        self.rain_result_tracker_active = False
        self.rain_reward_tracker_run_id += 1
        self.rain_result_tracker_run_id += 1
        if self.weather_station_active:
            self.stop_weather_station_for_shutdown()
        self.stop_rain_session()
        self.save_stats()
        self.refresh_keep_awake_state()
        event.accept()


def apply_palette(app):
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(COLORS["bg"]))
    palette.setColor(QPalette.WindowText, QColor(COLORS["text"]))
    palette.setColor(QPalette.Base, QColor("#090909"))
    palette.setColor(QPalette.Text, QColor(COLORS["text"]))
    palette.setColor(QPalette.Button, QColor("#1b1f1a"))
    palette.setColor(QPalette.ButtonText, QColor(COLORS["text"]))
    app.setPalette(palette)


def apply_styles(app):
    app.setStyleSheet(
        f"""
        QMainWindow {{
            background: {COLORS["bg"]};
        }}
        QWidget {{
            color: {COLORS["text"]};
            font-family: "Segoe UI";
            font-size: 13px;
        }}
        QStackedWidget {{
            background: transparent;
            border: none;
        }}
        #Topbar {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #171a15, stop:0.52 #10120f, stop:1 #171814);
            border-bottom: 1px solid #1e241d;
        }}
        #MiniBar {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #171a15, stop:0.55 #0c100c, stop:1 #171814);
            border: none;
        }}
        #MiniTitle {{
            color: {COLORS["red2"]};
            font-family: Impact;
            font-size: 20px;
            font-weight: 900;
            min-width: 26px;
        }}
        #MiniStats {{
            background: transparent;
            border: none;
        }}
        #MiniStatTitle {{
            color: {COLORS["muted2"]};
            font-size: 9px;
            font-weight: 900;
        }}
        #MiniStatValue {{
            color: #f5dfce;
            font-size: 11px;
            font-weight: 900;
        }}
        #MiniPredictionValue {{
            color: {COLORS["green2"]};
            font-size: 11px;
            font-weight: 900;
        }}
        #MiniScrapIcon {{
            color: #f5dfce;
            font-size: 10px;
            font-weight: 900;
        }}
        #Body {{
            background: qradialgradient(cx:0.52, cy:0.12, radius:1.1, fx:0.52, fy:0.12, stop:0 #11150f, stop:0.45 #050705, stop:1 #010201);
        }}
        QScrollBar:vertical {{
            background: #070907;
            width: 12px;
            margin: 0px;
        }}
        QScrollBar::handle:vertical {{
            background: #343a32;
            border: 1px solid #454d42;
            border-radius: 5px;
            min-height: 32px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: #4b5548;
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        #LogoButton {{
            background: transparent;
            border: none;
            border-radius: 0px;
            padding: 0px;
        }}
        #LogoButton:hover {{
            background: transparent;
            border: none;
        }}
        #LogoButton[active="true"] {{
            background: transparent;
            border: none;
        }}
        #NavButton {{
            background: transparent;
            color: #8e928b;
            border: none;
            border-radius: 3px;
            padding: 9px 11px;
            font-size: 14px;
            font-weight: 900;
        }}
        #NavButton:hover {{
            color: #d8dbd2;
            background: #171b16;
        }}
        #NavButton[active="true"] {{
            color: {COLORS["red2"]};
            background: #151912;
            border-bottom: 2px solid {COLORS["red"]};
        }}
        #SideButton, #SmallActionButton {{
            background: #161b14;
            color: {COLORS["text"]};
            border: 1px solid #2d352b;
            border-radius: 4px;
            padding: 9px 12px;
            font-size: 13px;
            font-weight: 900;
        }}
        #SideButton:hover, #SmallActionButton:hover {{
            background: #20271d;
            border-color: #485241;
            color: #ffffff;
        }}
        #SideButton:pressed, #SmallActionButton:pressed {{
            background: #0f120f;
        }}
        #SideButton:disabled {{
            color: #62675f;
            background: #0d100d;
            border-color: #20261f;
        }}
        #SideButton[running="true"] {{
            color: {COLORS["text"]};
            background: {COLORS["red"]};
            border-color: #713326;
        }}
        #SessionPill {{
            background: #141814;
            border: 1px solid #2b3329;
            border-radius: 15px;
        }}
        #SessionScrapTitle {{
            color: {COLORS["muted2"]};
            font-size: 12px;
            font-weight: 900;
        }}
        #SessionScrapAmount {{
            color: #f5dfce;
            font-size: 13px;
            font-weight: 900;
        }}
        #ScrapIcon {{
            color: #f5dfce;
            font-size: 10px;
            font-weight: 900;
        }}
        #ActivityControls {{
            background: transparent;
            border: none;
        }}
        #ActivityToggleButton {{
            color: {COLORS["text"]};
            background: #8f2f22;
            border: 1px solid #64241b;
            border-radius: 9px;
            padding: 1px 10px;
            min-width: 76px;
            min-height: 17px;
            max-height: 17px;
            font-size: 10px;
            font-weight: 900;
        }}
        #ActivityToggleButton:hover {{
            color: #ffffff;
            background: #b83b2a;
            border-color: {COLORS["red2"]};
        }}
        #ActivityToggleButton[active="true"] {{
            color: #111111;
            background: {COLORS["green"]};
            border-color: #9dcc52;
        }}
        #ActivityToggleButton[active="true"]:hover {{
            color: #111111;
            background: {COLORS["green2"]};
            border-color: #c4e67b;
        }}
        #MiniActivityButton {{
            color: {COLORS["text"]};
            background: #8f2f22;
            border: 1px solid #64241b;
            border-radius: 9px;
            padding: 1px 8px;
            min-width: 70px;
            min-height: 18px;
            max-height: 18px;
            font-size: 10px;
            font-weight: 900;
        }}
        #MiniActivityButton:hover {{
            color: #ffffff;
            background: #b83b2a;
            border-color: {COLORS["red2"]};
        }}
        #MiniActivityButton[active="true"] {{
            color: #111111;
            background: {COLORS["green"]};
            border-color: #9dcc52;
        }}
        #MiniActivityButton[active="true"]:hover {{
            color: #111111;
            background: {COLORS["green2"]};
            border-color: #c4e67b;
        }}
        #MiniActionButton {{
            color: {COLORS["text"]};
            background: #161b14;
            border: 1px solid #2d352b;
            border-radius: 9px;
            padding: 0px;
            min-width: 36px;
            max-width: 36px;
            min-height: 36px;
            max-height: 36px;
            font-size: 9px;
            font-weight: 900;
        }}
        #MiniActionButton:hover {{
            background: #20271d;
            border-color: #485241;
            color: #ffffff;
        }}
        #MiniActionButton[active="true"] {{
            color: #111111;
            background: {COLORS["gold"]};
            border-color: #f1c24a;
        }}
        #VersionLabel, #MutedLabel {{
            color: {COLORS["muted"]};
            font-weight: 700;
        }}
        #SideTitle, #SectionTitle {{
            color: {COLORS["red2"]};
            font-family: Impact;
            font-size: 34px;
            letter-spacing: 0px;
        }}
        #SideNote {{
            color: {COLORS["muted"]};
            line-height: 1.25;
        }}
        #SideSection {{
            color: {COLORS["gold"]};
            font-size: 12px;
            font-weight: 900;
            margin-top: 12px;
        }}
        #SideCheckbox {{
            color: {COLORS["text"]};
            font-weight: 800;
            spacing: 8px;
        }}
        #SideCheckbox::indicator {{
            width: 16px;
            height: 16px;
            border-radius: 3px;
            border: 1px solid #495246;
            background: #0d100d;
        }}
        #SideCheckbox::indicator:checked {{
            background: {COLORS["green"]};
            border-color: {COLORS["green2"]};
        }}
        #SettingLabel {{
            color: {COLORS["muted"]};
            font-weight: 700;
        }}
        #SettingSpin, QComboBox {{
            background: #080a08;
            color: {COLORS["text"]};
            border: 1px solid #2d352b;
            border-radius: 4px;
            padding: 5px 8px;
            min-width: 78px;
        }}
        #SettingSpin:focus {{
            border-color: #59634f;
        }}
        QSpinBox::up-button, QSpinBox::down-button,
        QDoubleSpinBox::up-button, QDoubleSpinBox::down-button,
        QTimeEdit::up-button, QTimeEdit::down-button {{
            background: #151a14;
            border: none;
            width: 16px;
        }}
        #SettingSlider::groove:horizontal {{
            background: #080a08;
            border: 1px solid #2d352b;
            border-radius: 4px;
            height: 8px;
        }}
        #SettingSlider::sub-page:horizontal {{
            background: {COLORS["green"]};
            border-radius: 4px;
        }}
        #SettingSlider::handle:horizontal {{
            background: {COLORS["red2"]};
            border: 1px solid #8f2f22;
            border-radius: 7px;
            width: 14px;
            margin: -4px 0px;
        }}
        #TimerCard {{
            background: #0e130d;
            border: 1px solid #252d24;
            border-radius: 5px;
        }}
        #TimerValue {{
            color: {COLORS["red2"]};
            font-weight: 900;
        }}
        #PageTitle {{
            color: {COLORS["red2"]};
            font-family: Impact;
            font-size: 54px;
            letter-spacing: 0px;
        }}
        #PageSubtitle {{
            color: {COLORS["muted"]};
            font-weight: 900;
            padding-top: 18px;
        }}
        #LogBox {{
            background: #030403;
            color: {COLORS["text"]};
            border: 1px solid #232b22;
            border-radius: 4px;
            padding: 10px;
            selection-background-color: {COLORS["red"]};
        }}
        QTextEdit {{
            background: #030403;
            selection-background-color: {COLORS["red"]};
        }}
        #StatsScroll {{
            background: transparent;
            border: none;
        }}
        #StatCard {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #11170f, stop:0.65 #0e130d, stop:1 #090d09);
            border: 1px solid #273026;
            border-radius: 6px;
        }}
        #StatRow {{
            border-bottom: 1px solid #1b211b;
        }}
        #StatLabel {{
            color: {COLORS["muted"]};
            font-size: 12px;
            font-weight: 900;
        }}
        #StatValue {{
            color: {COLORS["red2"]};
            font-size: 18px;
            font-weight: 900;
        }}
        #RainResultTable {{
            background: #090d09;
            alternate-background-color: #10150f;
            color: {COLORS["text"]};
            border: 1px solid #252e24;
            gridline-color: #20271f;
            selection-background-color: #222b20;
        }}
        QHeaderView::section {{
            background: #151b13;
            color: {COLORS["muted"]};
            border: none;
            border-bottom: 1px solid #2a3229;
            padding: 7px;
            font-size: 11px;
            font-weight: 900;
        }}
        #TinyDangerButton {{
            background: #241613;
            color: {COLORS["red2"]};
            border: 1px solid #4a251f;
            border-radius: 4px;
            padding: 4px 6px;
            font-size: 10px;
            font-weight: 900;
        }}
        #TinyDangerButton:hover {{
            background: #3a211c;
        }}
        #TinyActionButton {{
            background: #151a14;
            color: {COLORS["muted2"]};
            border: 1px solid #2d352b;
            border-radius: 9px;
            padding: 5px 12px;
            font-size: 10px;
            font-weight: 900;
        }}
        #TinyActionButton:hover {{
            color: {COLORS["text"]};
            background: #20271d;
            border-color: #485241;
        }}
        QTableCornerButton::section {{
            background: #151b13;
            border: none;
        }}
        """
    )


def main():
    try:
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True)
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_DontCreateNativeWidgetSiblings, True)
    except AttributeError:
        QApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)
        QApplication.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings, True)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setFont(QFont("Segoe UI", 10))
    apply_palette(app)
    apply_styles(app)

    window = MainWindow()
    window.showMaximized()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
