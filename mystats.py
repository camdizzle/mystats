import time
import tkinter as tk
from tkinter import ttk
from tkinter import Menu
from tkinter import filedialog
from tkinter import messagebox
from tkcalendar import Calendar
import asyncio
import sys
import os
import uuid
import base64
import datetime
from datetime import datetime, timedelta, timezone
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread.exceptions import SpreadsheetNotFound, WorksheetNotFound
import requests
import re
import tkinter.simpledialog as simpledialog
from PIL import Image, ImageTk, ImageDraw
from twitchio.ext import commands
from flask import Flask, Response, jsonify, request, send_from_directory, stream_with_context
import threading
import glob
import math
import random
import json
import copy
import chardet
from collections import defaultdict
import csv
import pytz
from colorama import Fore, Style
import atexit
import webbrowser
from twitchio.ext.commands.errors import CommandNotFound
import sounddevice as sd
import soundfile as sf
from twitchio import errors
import io
from io import BytesIO
from dateutil import parser
import socket
import logging
import queue
import tempfile
import subprocess
import warnings
import html
import hashlib
import unicodedata
import shutil
from pathlib import Path

if sys.platform == "win32":
    import ctypes

try:
    import ttkbootstrap as ttkbootstrap_module
except ImportError:
    ttkbootstrap_module = None

try:
    import pystray
except ImportError:
    pystray = None

try:
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=r"pkg_resources is deprecated as an API.*",
            category=UserWarning,
        )
        from win10toast import ToastNotifier
except ImportError:
    ToastNotifier = None

# Global Variables
version = '6.3.0'
text_widget = None
bot = None
BOT_SHOULD_RUN = True
GLOBAL_SOCKET = None
DEBUG = False
HAS_TTKBOOTSTRAP = ttkbootstrap_module is not None
DEFAULT_UI_THEME = "darkly"
app_style = None
season_quest_tree = None

SEASON_QUEST_DEFINITIONS = [
    {
        'id': 'races',
        'label': 'Season Races',
        'target_key': 'season_quest_target_races',
        'legacy_complete_key': 'season_quest_complete_races',
        'message': "🎯 Season Quest Complete: {name} finished {value:,} / {target:,} season races!",
    },
    {
        'id': 'points',
        'label': 'Season Points',
        'target_key': 'season_quest_target_points',
        'legacy_complete_key': 'season_quest_complete_points',
        'message': "🎯 Season Quest Complete: {name} earned {value:,} / {target:,} season points!",
    },
    {
        'id': 'race_hs',
        'label': 'Race High Score',
        'target_key': 'season_quest_target_race_hs',
        'legacy_complete_key': 'season_quest_complete_race_hs',
        'message': "🎯 Season Quest Complete: {name} reached race high score {value:,} (target {target:,})!",
    },
    {
        'id': 'br_hs',
        'label': 'BR High Score',
        'target_key': 'season_quest_target_br_hs',
        'legacy_complete_key': 'season_quest_complete_br_hs',
        'message': "🎯 Season Quest Complete: {name} reached BR high score {value:,} (target {target:,})!",
    },
    {
        'id': 'tilt_levels',
        'label': 'Tilt Levels',
        'target_key': 'season_quest_target_tilt_levels',
        'legacy_complete_key': 'season_quest_complete_tilt_levels',
        'message': "🎯 Season Quest Complete: {name} participated in {value:,} / {target:,} tilt levels!",
    },
    {
        'id': 'tilt_tops',
        'label': 'Top Tiltees',
        'target_key': 'season_quest_target_tilt_tops',
        'legacy_complete_key': 'season_quest_complete_tilt_tops',
        'message': "🎯 Season Quest Complete: {name} got {value:,} / {target:,} top-tiltee finishes!",
    },
    {
        'id': 'tilt_points',
        'label': 'Tilt Points',
        'target_key': 'season_quest_target_tilt_points',
        'legacy_complete_key': 'season_quest_complete_tilt_points',
        'message': "🎯 Season Quest Complete: {name} earned {value:,} / {target:,} tilt points!",
    },
]
rivals_tree = None
mycycle_tree = None
mycycle_session_label = None
mycycle_session_position_label = None
mycycle_prev_button = None
mycycle_next_button = None
mycycle_export_button = None
mycycle_home_session_ids = []
mycycle_home_session_index = 0
root = None
tray_icon = None
tray_thread = None
tray_queue = queue.Queue()
is_forced_exit = False
win_toaster = ToastNotifier() if ToastNotifier is not None else None
is_hiding_to_tray = False
tray_hint_toast_shown = False
channel_prompted_this_session = False

TRAY_MINIMIZE_TOAST_MESSAGE = (
    "The app is running in the system tray. Double-click the icon to reopen."
)

logger = logging.getLogger("mystats")
logger.propagate = False  # All output goes strictly to the log file, not the console

APPDATA_ROOT = Path('/appdata/local/mystats')
APPDATA_ROOT.mkdir(parents=True, exist_ok=True)


def appdata_path(*parts):
    path = APPDATA_ROOT.joinpath(*parts)
    path.parent.mkdir(parents=True, exist_ok=True)
    return str(path)

# Log errors and milestones (INFO and above) to mystats.log only
_log_file_handler = logging.FileHandler(appdata_path("mystats.log"), encoding="utf-8")
_log_file_handler.setLevel(logging.INFO)
_log_file_handler.setFormatter(
    logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
)
logger.addHandler(_log_file_handler)
logger.setLevel(logging.INFO)

_RAW_CSV_READER = csv.reader


def _sanitize_csv_lines(file_obj):
    """Yield text lines with embedded NUL bytes removed."""
    for line in file_obj:
        if "\x00" in line:
            line = line.replace("\x00", "")
        yield line


def iter_csv_rows(file_obj, **reader_kwargs):
    """Safely iterate CSV rows from a text file-like object."""
    return _RAW_CSV_READER(_sanitize_csv_lines(file_obj), **reader_kwargs)

def append_csv_rows_safely(file_path, rows):
    """Append rows to CSV and force data to disk to reduce partial-write corruption."""
    with open(file_path, "a", newline="", encoding="utf-8", errors="ignore") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerows(rows)
        csv_file.flush()
        os.fsync(csv_file.fileno())


def _settings_file_candidates():
    appdata_settings = Path(appdata_path("settings.txt"))
    candidates = [appdata_settings]

    # Legacy paths used by older desktop builds.
    legacy_candidates = [
        Path.cwd() / "settings.txt",
        Path(__file__).resolve().parent / "settings.txt",
    ]

    local_app_data = os.getenv('LOCALAPPDATA')
    if local_app_data:
        local_app_data_path = Path(local_app_data)
        legacy_candidates.extend([
            local_app_data_path / "mystats" / "settings.txt",
            local_app_data_path / "mystats" / "data" / "settings.txt",
            local_app_data_path / "MyStats" / "settings.txt",
            local_app_data_path / "MyStats" / "data" / "settings.txt",
        ])

    for candidate in legacy_candidates:
        if candidate not in candidates:
            candidates.append(candidate)

    return candidates


def _migrate_settings_file_if_needed(settings_candidates):
    destination = Path(settings_candidates[0])
    if destination.exists():
        return

    for candidate in settings_candidates[1:]:
        source = Path(candidate)
        if not source.exists() or source == destination:
            continue

        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            print(f"Migrated settings file from {source} to {destination}")
            return
        except OSError as exc:
            print(f"Failed to migrate settings from {source} to {destination}: {exc}")


def _resolve_settings_file_path():
    candidates = _settings_file_candidates()
    _migrate_settings_file_if_needed(candidates)
    return str(candidates[0])


SETTINGS_FILE_PATH = _resolve_settings_file_path()



TEAM_DATA_FILE = "teams_data.json"
TEAM_DATA_LOCK = threading.Lock()
TEAM_POINTS_CACHE_FILE = "team_points_cache.json"
TEAM_POINTS_CACHE_LOCK = threading.Lock()
TEAM_EMOTE_CACHE_LOCK = threading.Lock()
TEAM_EMOTE_CACHE_TTL_SECONDS = 900
TEAM_EMOTE_CACHE = {'expires_at': 0.0, 'channel': '', 'lookup': {}}

SUPPORTED_UI_LANGUAGES = {'en', 'es', 'fr', 'de', 'pt', 'au'}

LANGUAGE_DISPLAY_NAMES = {
    'en': 'English',
    'es': 'Español',
    'fr': 'Français',
    'de': 'Deutsch',
    'pt': 'Português',
    'au': 'Aussie',
}

UI_TEXT = {
    'en': {},
    'de': {
        'Settings': 'Einstellungen',
        'General': 'Allgemein',
        'Audio': 'Audio',
        'Chat': 'Chat',
        'Season Quests': 'Saison-Quests',
        'Rivals': 'Rivalen',
        'MyCycle': 'MyCycle',
        'Appearance': 'Darstellung',
        'Overlay': 'Overlay',
        'Tilt': 'Tilt',
        'Core app settings': 'Kern-App-Einstellungen',
        'Channel': 'Kanal',
        'Marble Day': 'Marble-Tag',
        'Season': 'Saison',
        'Language': 'Sprache',
        'Mystats Directory': 'MyStats-Verzeichnis',
        'Open Location': 'Ort öffnen',
        'Reset Defaults': 'Standards zurücksetzen',
        'Save and Close': 'Speichern und schließen',
        'MyStats - Marbles On Stream Companion Application': 'MyStats - Marbles On Stream Begleit-App',
        'About': 'Über',
        'Mystats Application': 'Mystats-Anwendung',
        'Version': 'Version',
        'Close': 'Schließen',
        'Developed by\nCamWOW': 'Entwickelt von\nCamWOW',
        'Contact Information\nDiscord: https://discord.gg/camwow\nWebsite: https://www.camwow.tv': 'Kontaktinformationen\nDiscord: https://discord.gg/camwow\nWebsite: https://www.camwow.tv',
        'Acknowledgments\nA heartfelt thank you to Vibblez for his incredible contributions, ideas, and unwavering support. His creative vision and technical expertise have been instrumental not only in shaping the MyStats application, but more specifically in elevating the website to new heights. From conceptualizing unique features to refining the user experience, his efforts have left an indelible mark on this project.': 'Danksagung\nEin herzliches Dankeschön an Vibblez für seine unglaublichen Beiträge, Ideen und unermüdliche Unterstützung. Seine kreative Vision und technische Expertise waren nicht nur für die Entwicklung der MyStats-Anwendung entscheidend, sondern insbesondere auch dafür, die Website auf ein neues Niveau zu heben. Von der Konzeption einzigartiger Funktionen bis zur Verfeinerung der Benutzererfahrung hat er dieses Projekt nachhaltig geprägt.',
        'The application is a companion tool for Marbles On Stream, designed to enhance user engagement and streamline data management. It tracks and processes race data in real-time, handles event management, and posts automated race results to Twitch chat. Key features include Battle Royale crown win tracking, checkpoint processing, event status toggling, and seamless integration with the Twitch API for authenticating users and dynamically updating relevant stats and events. The application provides a user-friendly interface built with Tkinter, ensuring that race results, event statuses, and other critical information are easily accessible to both streamers and their viewers.': 'Die Anwendung ist ein Begleittool für Marbles On Stream, das die Nutzerinteraktion verbessert und das Datenmanagement vereinfacht. Sie verfolgt und verarbeitet Renndaten in Echtzeit, verwaltet Events und veröffentlicht automatische Rennergebnisse im Twitch-Chat. Zu den Kernfunktionen gehören die Verfolgung von Battle-Royale-Kronensiegen, Checkpoint-Verarbeitung, das Umschalten von Event-Status sowie die nahtlose Integration der Twitch-API zur Authentifizierung und dynamischen Aktualisierung relevanter Statistiken und Events. Die Anwendung bietet eine benutzerfreundliche Tkinter-Oberfläche, sodass Rennergebnisse, Event-Status und andere wichtige Informationen für Streamer und Zuschauer leicht zugänglich sind.',
    },
}

CHAT_TEXT = {
    'de': {
        'Race winner': 'Rennsieger',
        'won the race': 'hat das Rennen gewonnen',
        'points': 'Punkte',
        'season': 'Saison',
        'today': 'heute',
        'top 3': 'Top 3',
        'high score': 'Highscore',
        'new high score': 'neuer Highscore',
        'leaderboard': 'Bestenliste',
        'event': 'Event',
        'completed': 'abgeschlossen',
        'current': 'aktuell',
        'average': 'Durchschnitt',
        'total': 'gesamt',
        'deaths': 'Tode',
        'levels': 'Level',
    },
}

AUSSIE_SLANG_REPLACEMENTS = {
    'hello': "g'day",
    'hi': "g'day",
    'yes': 'too right',
    'no': 'nah',
    'friend': 'mate',
    'friends': 'mates',
    'everyone': 'all the mates',
    'great': 'bonza',
    'amazing': 'bonza',
    'very': 'bloody',
    'really': 'bloody',
    'thank you': 'cheers',
    'thanks': 'cheers',
    'please': 'if ya can',
    'goodbye': 'hooroo',
    'good': 'bonza',
    'small': 'tiny as',
    'afternoon': 'arvo',
    'breakfast': 'brekkie',
    'barbecue': 'barbie',
    'sandals': 'thongs',
    'truck': 'ute',
    'service station': 'servo',
    'gas station': 'servo',
    'convenience store': 'servo',
    'difficult': 'a bit crook',
    'problem': 'sticky wicket',
    'my': 'me',
    'is not': "ain't",
    'are not': "ain't",
    'do not': "don't",
    'cannot': "can't",
}


def _to_aussie_slang(text):
    slangified = str(text)

    for source, target in sorted(AUSSIE_SLANG_REPLACEMENTS.items(), key=lambda item: len(item[0]), reverse=True):
        slangified = re.sub(rf"\b{re.escape(source)}\b", target, slangified, flags=re.IGNORECASE)

    slangified = re.sub(r'\s+', ' ', slangified).strip()
    return slangified


def get_ui_language():
    config_manager = globals().get('config')
    if config_manager is None:
        return 'en'

    language = str(config_manager.get_setting('app_language') or 'en').strip().lower()
    return language if language in SUPPORTED_UI_LANGUAGES else 'en'


def tr(text):
    language = get_ui_language()
    if language == 'au':
        return _to_aussie_slang(text)
    return UI_TEXT.get(language, {}).get(text, text)


def translate_chat_message(message):
    language = get_ui_language()
    if language == 'en':
        return message
    if language == 'au':
        return _to_aussie_slang(message)

    translated = str(message)
    replacements = CHAT_TEXT.get(language, {})
    for source, target in sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True):
        translated = re.sub(re.escape(source), target, translated, flags=re.IGNORECASE)
    return translated


def get_placement_emote(place):
    return {1: "🥇", 2: "🥈", 3: "🥉"}.get(place, "")


def show_leaderboard_medal_emotes():
    config_manager = globals().get('config')
    if config_manager is None:
        return True
    return str(config_manager.get_setting('chat_leaderboard_show_medals') or 'True') == 'True'


def format_ranked_label(place):
    emote = get_placement_emote(place) if show_leaderboard_medal_emotes() else ""
    return f"{emote} {place}." if emote else f"{place}."


def pluralize(count, singular, plural=None):
    if plural is None:
        plural = f"{singular}s"
    return singular if count == 1 else plural


def supports_system_tray():
    return pystray is not None


def _get_app_icon_path():
    candidates = []

    if getattr(sys, "frozen", False):
        candidates.append(os.path.dirname(os.path.abspath(sys.executable)))

    candidates.append(os.path.dirname(os.path.abspath(__file__)))
    candidates.append(os.getcwd())

    for base_dir in candidates:
        icon_path = os.path.join(base_dir, "circle1.ico")
        if os.path.exists(icon_path):
            return icon_path

    return None


def _apply_window_icon(window):
    icon_path = _get_app_icon_path()

    if not icon_path:
        return

    try:
        window.iconbitmap(icon_path)
    except Exception:
        logger.warning("Unable to apply window icon from %s", icon_path)


def _build_tray_image():
    icon_path = _get_app_icon_path()

    if icon_path:
        try:
            return Image.open(icon_path)
        except Exception:
            logger.warning("Unable to load tray icon from %s", icon_path)

    image = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((6, 6, 58, 58), radius=12, fill=(20, 20, 20, 255))
    draw.text((20, 18), "MS", fill=(255, 255, 255, 255))
    return image


def _drain_tray_queue():
    if not root or not root.winfo_exists():
        return

    while True:
        try:
            command = tray_queue.get_nowait()
        except queue.Empty:
            break

        if command == "show":
            restore_from_tray()
        elif command == "dashboard":
            open_dashboard()
        elif command == "exit":
            force_exit_application()

    root.after(250, _drain_tray_queue)


def _on_tray_open(icon, item):
    tray_queue.put("show")


def _on_tray_dashboard(icon, item):
    tray_queue.put("dashboard")


def _on_tray_exit(icon, item):
    tray_queue.put("exit")


def start_system_tray_icon():
    global tray_icon, tray_thread

    if not supports_system_tray() or tray_icon is not None:
        return

    menu = pystray.Menu(
        pystray.MenuItem("Open MyStats", _on_tray_open, default=True),
        pystray.MenuItem("Open Dashboard", _on_tray_dashboard),
        pystray.MenuItem("Exit", _on_tray_exit),
    )

    tray_icon = pystray.Icon("mystats", _build_tray_image(), "MyStats", menu)
    tray_thread = threading.Thread(target=tray_icon.run, daemon=True)
    tray_thread.start()


def stop_system_tray_icon():
    global tray_icon, tray_thread

    if tray_icon is not None:
        tray_icon.stop()
        tray_icon = None
        tray_thread = None


def _set_hiding_to_tray(value):
    global is_hiding_to_tray
    is_hiding_to_tray = value


def is_minimize_to_tray_enabled():
    return str(config.get_setting("minimize_to_tray") or "False").strip().lower() == "true"


def minimize_to_tray():
    global is_hiding_to_tray, tray_hint_toast_shown

    if not root or not root.winfo_exists():
        return

    if not supports_system_tray():
        root.iconify()
        return

    is_hiding_to_tray = True
    root.withdraw()
    if not tray_hint_toast_shown:
        show_windows_toast("MyStats", TRAY_MINIMIZE_TOAST_MESSAGE)
        tray_hint_toast_shown = True
        config.set_setting("tray_hint_toast_shown", "True", persistent=True)

    try:
        start_system_tray_icon()
    except Exception as exc:
        logger.warning("Failed to initialize system tray icon: %s", exc)
        root.deiconify()
        root.iconify()

    root.after(300, lambda: _set_hiding_to_tray(False))


def handle_root_minimize(event=None):
    if not root or not root.winfo_exists() or is_forced_exit:
        return

    if is_hiding_to_tray:
        return

    if str(root.state()) == "iconic" and is_minimize_to_tray_enabled():
        minimize_to_tray()



def restore_from_tray():
    if not root or not root.winfo_exists():
        return

    stop_system_tray_icon()
    root.deiconify()
    root.lift()
    root.focus_force()


def force_exit_application():
    global is_forced_exit
    is_forced_exit = True
    on_close()


def get_initial_ui_theme():
    try:
        with open(SETTINGS_FILE_PATH, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.startswith("UI_THEME="):
                    theme_name = line.split("=", 1)[1].strip()
                    if theme_name:
                        return theme_name
    except FileNotFoundError:
        pass

    return DEFAULT_UI_THEME


def create_root_window():
    """Create the root window, preferring ttkbootstrap when installed."""
    initial_theme = get_initial_ui_theme()

    if HAS_TTKBOOTSTRAP:
        root_window = ttkbootstrap_module.Window(themename=DEFAULT_UI_THEME)
        style = root_window.style

        try:
            style.theme_use(initial_theme)
        except Exception:
            style.theme_use(DEFAULT_UI_THEME)
    else:
        root_window = tk.Tk()
        style = ttk.Style(root_window)
        available_themes = style.theme_names()
        style.theme_use(initial_theme if initial_theme in available_themes else "clam")

    _apply_window_icon(root_window)
    return root_window, style


def configure_dpi_awareness():
    """Opt into modern DPI handling so window dimensions match scaled text."""
    if sys.platform != "win32":
        return

    try:
        # Windows 10 creators update and newer (best behavior).
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        return
    except Exception:
        pass

    try:
        # Windows 8.1 fallback.
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return
    except Exception:
        pass

    try:
        # Legacy fallback.
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def apply_ui_styles(style):
    """Central app styles for a modern, cleaner UI."""
    style.configure("App.TFrame", padding=8)
    style.configure("Card.TLabelframe", padding=12)
    style.configure("Card.TLabelframe.Label", font=("Segoe UI", 10, "bold"))
    style.configure("Heading.TLabel", font=("Segoe UI", 16, "bold"))
    style.configure("Small.TLabel", font=("Segoe UI", 9))

    # Modern flat button look (no bevel), with subtle interactive states.
    style.configure("TButton", padding=(10, 6), relief="flat", borderwidth=0)
    style.map("TButton", relief=[("pressed", "flat"), ("active", "flat")])
    style.configure("Primary.TButton", padding=(12, 7), relief="flat", borderwidth=0)
    style.map("Primary.TButton", relief=[("pressed", "flat"), ("active", "flat")])
    style.configure("Green.TButton", foreground="#0f5132")
    style.map("Green.TButton", foreground=[("active", "#198754")])
    style.configure("Red.TButton", foreground="#842029")
    style.map("Red.TButton", foreground=[("active", "#dc3545")])
    style.configure("SessionActive.TButton", foreground="#ffffff", background="#146c43")
    style.map("SessionActive.TButton", foreground=[("active", "#ffffff")], background=[("active", "#198754")])
    style.configure("SessionInactive.TButton", foreground="#ffffff", background="#842029")
    style.map("SessionInactive.TButton", foreground=[("active", "#ffffff")], background=[("active", "#dc3545")])
    style.configure("SessionDelete.TButton", foreground="#ffffff", background="#6c757d")
    style.map("SessionDelete.TButton", foreground=[("active", "#ffffff")], background=[("active", "#5c636a")])
    style.configure("Success.Small.TLabel", font=("Segoe UI", 9, "bold"), foreground="#198754")
    style.configure("Danger.Small.TLabel", font=("Segoe UI", 9, "bold"), foreground="#dc3545")

    # Improve field density/readability.
    style.configure("TEntry", padding=4)
    style.configure("TCombobox", padding=3)
    style.configure("TCheckbutton", padding=2)


def get_available_ui_themes():
    return sorted(app_style.theme_names())


def apply_theme(theme_name):
    global app_style

    if not theme_name:
        return

    app_style.theme_use(theme_name)
    apply_ui_styles(app_style)


def is_chat_response_enabled(setting_key):
    cfg = globals().get("config")
    if cfg is None:
        return True

    setting_value = cfg.get_setting(setting_key)

    # Backward compatibility for old setting name.
    if setting_value is None and setting_key == "chat_all_commands":
        setting_value = cfg.get_setting("chat_mystats_command")

    if setting_value is None:
        return True
    return str(setting_value).strip().lower() == "true"


def get_chat_max_names():
    try:
        value = int(config.get_setting("chat_max_names") or 25)
    except (TypeError, ValueError):
        value = 25

    return min(25, max(3, value))


def get_api_season_number(default='67'):
    """Map the stored app season to the PixelByPixel API season parameter."""
    raw_season = str(config.get_setting('season') or '').strip()
    season_digits = ''.join(ch for ch in raw_season if ch.isdigit())
    return season_digits or default


def fetch_pixelbypixel_leaderboard(statistic_name):
    season_number = get_api_season_number()
    api_url = (
        "https://pixelbypixel.studio/api/leaderboards"
        f"?offset=0&statisticName={statistic_name}&seasonNumber={season_number}"
    )
    logger.info("API call: leaderboards (statistic=%s, season=%s)", statistic_name, season_number)
    response = requests.get(api_url, timeout=15)
    response.raise_for_status()

    data = response.json()
    leaderboard_data = data.get("Leaderboard", []) if isinstance(data, dict) else []
    if not isinstance(leaderboard_data, list):
        return []
    return leaderboard_data


def refresh_tilt_lifetime_xp_from_leaderboard():
    """Populate Starting Lifetime XP from TiltedExpertise for the configured channel."""
    channel_name = (config.get_setting('CHANNEL') or '').strip().lower().lstrip('@')
    if not channel_name:
        return

    try:
        leaderboard_data = fetch_pixelbypixel_leaderboard("TiltedExpertise")
    except requests.RequestException as exc:
        print(f"Could not refresh TiltedExpertise value: {exc}")
        return

    def normalize_name(value):
        return str(value or '').strip().lower().lstrip('@')

    for record in leaderboard_data:
        if not isinstance(record, dict):
            continue

        identity_candidates = [
            record.get('DisplayName'),
            record.get('UserName'),
            record.get('Username'),
            record.get('ChannelName'),
            record.get('TwitchName'),
        ]
        if channel_name not in {normalize_name(candidate) for candidate in identity_candidates if candidate}:
            continue

        stat_value = record.get('StatValue', 0)
        try:
            parsed_stat_value = str(max(0, int(float(stat_value))))
        except (TypeError, ValueError):
            return

        if config.get_setting('tilt_lifetime_base_xp') != parsed_stat_value:
            config.set_setting('tilt_lifetime_base_xp', parsed_stat_value, persistent=True)
            print(f"Tilt Starting Lifetime XP auto-set from API: {parsed_stat_value}")
        return


def get_tilt_output_directory():
    output_directory = appdata_path("TiltedOutputFiles")
    os.makedirs(output_directory, exist_ok=True)
    return output_directory


def safe_read_csv_rows(path, retries=5, retry_delay=0.5):
    """Read CSV rows safely from files that may be locked by game writes."""
    for _ in range(retries):
        try:
            if not path or not os.path.exists(path):
                return []

            with open(path, 'rb') as f:
                raw_data = f.read()

            result = chardet.detect(raw_data)
            encoding = result['encoding'] if result['encoding'] else 'utf-8'
            decoded = raw_data.decode(encoding, errors='ignore')
            return list(iter_csv_rows(io.StringIO(decoded)))
        except Exception:
            time.sleep(retry_delay)

    return []


def chunked_join_messages(prefix, continuation_prefix, items, separator=' | ', max_length=480):
    """Build one or more chunked messages with a shared prefix strategy."""
    if not items:
        return []

    chunks = []
    current = prefix

    for item in items:
        rendered_item = f"{item}{separator}"
        if len(current) + len(rendered_item) > max_length:
            chunks.append(current.rstrip(', '))
            current = f"{continuation_prefix}{rendered_item}"
        else:
            current += rendered_item

    if current:
        chunks.append(current.rstrip(', '))

    return chunks




def parse_tilt_elapsed_to_seconds(value):
    token = str(value or '').strip()
    if not token:
        return 0

    parts = token.split(':')
    try:
        nums = [int(float(part.strip() or 0)) for part in parts]
    except (TypeError, ValueError):
        return 0

    if len(nums) == 1:
        return max(0, nums[0])
    if len(nums) == 2:
        minutes, seconds = nums
        return max(0, (minutes * 60) + seconds)

    hours, minutes, seconds = nums[-3:]
    return max(0, (hours * 3600) + (minutes * 60) + seconds)


def format_tilt_duration(total_seconds):
    seconds = max(0, int(total_seconds or 0))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"

def parse_tilt_level_state(level_rows):
    """Parse LastTiltLevel.csv using header aliases when possible, with positional fallbacks."""
    if len(level_rows) < 2:
        return None

    headers = [h.strip().lower() for h in level_rows[0]]
    row = level_rows[1]
    index_by_header = {h: idx for idx, h in enumerate(headers)}

    def get_field(alias_list, fallback_index=None, default=''):
        for alias in alias_list:
            idx = index_by_header.get(alias)
            if idx is not None and idx < len(row):
                return row[idx].strip()
        if fallback_index is not None and fallback_index < len(row):
            return row[fallback_index].strip()
        return default

    current_level_raw = get_field(['level', 'currentlevel'], fallback_index=0, default='0')
    digits_only = ''.join(ch for ch in current_level_raw if ch.isdigit())
    current_level = int(digits_only or '0')

    elapsed_time = get_field(['timeelapsed', 'elapsedtime', 'time'], fallback_index=1, default='0:00')
    top_tiltee = get_field(['toptiltee', 'topplayer', 'topuser'], fallback_index=2, default='')

    level_xp_raw = get_field(['points', 'levelexp', 'expertise'], fallback_index=3, default='0')
    total_xp_raw = get_field(['totalexp', 'totalexpertise'], fallback_index=4, default='0')
    live_raw = get_field(['live', 'islive'], fallback_index=5, default='')
    level_passed_raw = get_field(['levelpassed', 'passed'], fallback_index=6, default='false').lower()

    try:
        level_xp = int(float(level_xp_raw))
    except (TypeError, ValueError):
        level_xp = 0

    try:
        total_xp = int(float(total_xp_raw))
    except (TypeError, ValueError):
        total_xp = 0

    return {
        'current_level': current_level,
        'elapsed_time': elapsed_time,
        'top_tiltee': top_tiltee,
        'level_xp': level_xp,
        'total_xp': total_xp,
        'live': live_raw,
        'level_passed': level_passed_raw == 'true'
    }


def parse_boolean_token(value, default=False):
    token = str(value or '').strip().lower()
    if token in ('true', 'yes', 'y', '1'):
        return True
    if token in ('false', 'no', 'n', '0'):
        return False
    return default


def normalize_channel_name(value):
    raw_value = str(value or '').strip().lower()
    if not raw_value:
        return ''

    if raw_value.startswith('https://') or raw_value.startswith('http://'):
        raw_value = raw_value.rstrip('/').split('/')[-1]

    return raw_value.lstrip('@')


def format_user_tag(value, default='unknown'):
    username = str(value or '').strip().lstrip('@')
    if not username:
        username = default
    return f"@{username}"


def _team_data_path():
    base_dir = config.get_setting('directory') or '.'
    return os.path.join(base_dir, TEAM_DATA_FILE)


def _team_points_cache_path():
    base_dir = config.get_setting('directory') or '.'
    return os.path.join(base_dir, TEAM_POINTS_CACHE_FILE)


def _load_team_data():
    path = _team_data_path()
    if not os.path.exists(path):
        return {'channels': {}}

    try:
        with open(path, 'r', encoding='utf-8') as f:
            payload = json.load(f)
        if not isinstance(payload, dict):
            return {'channels': {}}
        channels = payload.get('channels')
        if not isinstance(channels, dict):
            payload['channels'] = {}
        return payload
    except Exception as exc:
        logger.warning("Failed to load team data: %s", exc)
        return {'channels': {}}


def _save_team_data(payload):
    path = _team_data_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2)


def _load_team_points_cache():
    path = _team_points_cache_path()
    if not os.path.exists(path):
        return {'channels': {}}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            payload = json.load(f)
        if not isinstance(payload, dict):
            return {'channels': {}}
        channels = payload.get('channels')
        if not isinstance(channels, dict):
            payload['channels'] = {}
        return payload
    except Exception as exc:
        logger.warning("Failed to load team points cache: %s", exc)
        return {'channels': {}}


def _save_team_points_cache(payload):
    path = _team_points_cache_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2)


def _week_key_from_timestamp(ts):
    if not ts:
        ts = datetime.now(timezone.utc)
    iso = ts.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _day_key_from_timestamp(ts):
    if not ts:
        ts = datetime.now(timezone.utc)
    return ts.strftime('%Y-%m-%d')


def _resolve_team_bonus_percent(bonus_payload, default_percent=0):
    if not isinstance(bonus_payload, dict):
        return max(0, int(default_percent or 0))
    try:
        if bonus_payload.get('bonus_percent') is not None:
            return max(0, int(bonus_payload.get('bonus_percent')))
    except (TypeError, ValueError):
        pass
    try:
        return max(0, (int(bonus_payload.get('multiplier', 1)) - 1) * 100)
    except (TypeError, ValueError):
        return max(0, int(default_percent or 0))


def _team_has_recent_bits_bonus(team, now, cooldown_minutes=60):
    try:
        cooldown = max(0, int(cooldown_minutes))
    except (TypeError, ValueError):
        cooldown = 60
    if cooldown <= 0:
        return False
    cutoff = now - timedelta(minutes=cooldown)
    for entry in reversed(team.get('bonus_windows', []) if isinstance(team.get('bonus_windows'), list) else []):
        if not isinstance(entry, dict):
            continue
        if str(entry.get('source') or 'bits').lower() != 'bits':
            continue
        end_at = _parse_allraces_timestamp(entry.get('end_at'))
        if end_at and end_at >= cutoff:
            return True
    return False


def _team_most_recent_bits_bonus_end(team):
    latest_end = None
    for entry in team.get('bonus_windows', []) if isinstance(team.get('bonus_windows'), list) else []:
        if not isinstance(entry, dict):
            continue
        if str(entry.get('source') or 'bits').lower() != 'bits':
            continue
        end_at = _parse_allraces_timestamp(entry.get('end_at'))
        if end_at and (latest_end is None or end_at > latest_end):
            latest_end = end_at
    return latest_end


def _get_channel_season_points_state(payload, channel_name, season_value):
    channels = payload.setdefault('channels', {})
    channel_key = _normalize_username(channel_name)
    channel_state = channels.setdefault(channel_key, {'seasons': {}})
    seasons = channel_state.setdefault('seasons', {})
    season_key = str(season_value or config.get_setting('season') or 'default')
    season_state = seasons.setdefault(season_key, {'teams': {}})
    season_state.setdefault('teams', {})
    return season_state


def _get_team_points_bucket(season_state, team_name):
    teams = season_state.setdefault('teams', {})
    bucket = teams.setdefault(team_name, {
        'season_points': 0,
        'daily': {},
        'weekly': {},
        'bonus_races_daily': {},
        'last_updated': None,
    })
    bucket.setdefault('season_points', 0)
    bucket.setdefault('daily', {})
    bucket.setdefault('weekly', {})
    bucket.setdefault('bonus_races_daily', {})
    return bucket


def _remove_team_points_cache_entry(channel_name, season_value, team_name):
    with TEAM_POINTS_CACHE_LOCK:
        cache_payload = _load_team_points_cache()
        season_state = _get_channel_season_points_state(cache_payload, channel_name, season_value)
        teams = season_state.setdefault('teams', {})
        if team_name in teams:
            teams.pop(team_name, None)
            _save_team_points_cache(cache_payload)


def _rename_team_points_cache_entry(channel_name, season_value, old_team_name, new_team_name):
    with TEAM_POINTS_CACHE_LOCK:
        cache_payload = _load_team_points_cache()
        season_state = _get_channel_season_points_state(cache_payload, channel_name, season_value)
        teams = season_state.setdefault('teams', {})
        old_bucket = teams.get(old_team_name)
        if old_bucket is None:
            return
        if new_team_name in teams:
            return
        teams[new_team_name] = old_bucket
        teams.pop(old_team_name, None)
        _save_team_points_cache(cache_payload)


def _record_live_team_points_rows(channel_name, rows):
    if not rows:
        return

    season_value = config.get_setting('season') or 'default'
    with TEAM_DATA_LOCK:
        team_data = _load_team_data()
        channel_state = _get_channel_team_state(team_data, channel_name)
        with TEAM_POINTS_CACHE_LOCK:
            cache_payload = _load_team_points_cache()
            season_state = _get_channel_season_points_state(cache_payload, channel_name, season_value)

            team_data_changed = False
            for row in rows:
                if len(row) < 6:
                    continue
                username = _normalize_username(row[1])
                if not username:
                    continue
                mode = row[4] if len(row) > 4 else ''
                if not _is_team_scoring_mode(mode):
                    continue
                try:
                    base_points = int(row[3])
                except (TypeError, ValueError):
                    continue
                ts = _parse_allraces_timestamp(row[5]) or datetime.now(timezone.utc)

                team_name, _ = _find_team_for_user(channel_state, username)
                if not team_name:
                    continue
                team = channel_state.get('teams', {}).get(team_name)
                if not isinstance(team, dict):
                    continue

                member_meta = team.get('member_meta', {}) if isinstance(team.get('member_meta'), dict) else {}
                user_meta = member_meta.get(username, {}) if isinstance(member_meta.get(username), dict) else {}

                active_bonus = team.get('active_bonus') if isinstance(team.get('active_bonus'), dict) else None
                bonus_percent = 0
                if active_bonus:
                    start_at = _parse_iso_datetime(active_bonus.get('start_at'))
                    end_at = _parse_iso_datetime(active_bonus.get('end_at'))
                    if start_at and end_at and start_at <= ts <= end_at:
                        bonus_percent = _resolve_team_bonus_percent(active_bonus, 0)

                sub_bonus = int(round(base_points * 0.10)) if bool(user_meta.get('is_subscriber')) else 0
                bonus_extra = int(math.floor(base_points * (bonus_percent / 100.0)))
                total_add = base_points + sub_bonus + bonus_extra

                bucket = _get_team_points_bucket(season_state, team_name)
                day_key = _day_key_from_timestamp(ts)
                week_key = _week_key_from_timestamp(ts)

                bucket['season_points'] = int(bucket.get('season_points', 0)) + total_add
                bucket['daily'][day_key] = int(bucket['daily'].get(day_key, 0)) + total_add
                bucket['weekly'][week_key] = int(bucket['weekly'].get(week_key, 0)) + total_add
                if bonus_percent > 0:
                    bucket['bonus_races_daily'][day_key] = int(bucket['bonus_races_daily'].get(day_key, 0)) + 1
                bucket['last_updated'] = datetime.now(timezone.utc).isoformat()

                # Dual-track Team Effort Points (TEP): participation-driven and non-overlapping with bits bonus.
                try:
                    tep_threshold = max(1, int(config.get_setting('teams_tep_threshold') or 40))
                except ValueError:
                    tep_threshold = 40
                try:
                    tep_per_race = max(0, int(config.get_setting('teams_tep_per_race') or 1))
                except ValueError:
                    tep_per_race = 1
                try:
                    tep_bonus_minutes = max(1, int(config.get_setting('teams_tep_bonus_duration_minutes') or 15))
                except ValueError:
                    tep_bonus_minutes = 15
                try:
                    tep_bits_cooldown_minutes = max(0, int(config.get_setting('teams_tep_bits_cooldown_minutes') or 60))
                except ValueError:
                    tep_bits_cooldown_minutes = 60
                try:
                    tep_member_daily_cap = max(0, int(config.get_setting('teams_tep_member_daily_cap') or 10))
                except ValueError:
                    tep_member_daily_cap = 10
                try:
                    tep_team_daily_cap = max(0, int(config.get_setting('teams_tep_team_daily_cap') or 100))
                except ValueError:
                    tep_team_daily_cap = 100

                team.setdefault('effort_bank', 0)
                effort_daily = team.setdefault('effort_daily', {})
                day_effort = effort_daily.setdefault(day_key, {'team_total': 0, 'members': {}})
                members_effort = day_effort.setdefault('members', {})
                member_effort_today = int(members_effort.get(username, 0) or 0)
                team_effort_today = int(day_effort.get('team_total', 0) or 0)

                member_room = max(0, tep_member_daily_cap - member_effort_today)
                team_room = max(0, tep_team_daily_cap - team_effort_today)
                tep_earned = min(tep_per_race, member_room, team_room)
                if tep_earned > 0:
                    members_effort[username] = member_effort_today + tep_earned
                    day_effort['team_total'] = team_effort_today + tep_earned
                    team['effort_bank'] = int(team.get('effort_bank', 0)) + tep_earned
                    team_data_changed = True

                # Keep only recent effort days to avoid unbounded growth.
                if len(effort_daily) > 10:
                    for stale_day in sorted(effort_daily.keys())[:-10]:
                        effort_daily.pop(stale_day, None)

                # No overlap rule + bits cooldown rule for TEP activation.
                now = datetime.now(timezone.utc)
                active_now = team.get('active_bonus') if isinstance(team.get('active_bonus'), dict) else None
                if active_now:
                    active_end = _parse_allraces_timestamp(active_now.get('end_at'))
                    if active_end and active_end < now:
                        team['active_bonus'] = None
                        team['active_bonus_label'] = None
                        active_now = None
                        team_data_changed = True

                while int(team.get('effort_bank', 0)) >= tep_threshold:
                    if active_now is not None:
                        break
                    if _team_has_recent_bits_bonus(team, now, tep_bits_cooldown_minutes):
                        break
                    team['effort_bank'] = int(team.get('effort_bank', 0)) - tep_threshold
                    tep_bonus = {
                        'bonus_percent': 15,
                        'source': 'tep',
                        'start_at': now.isoformat(),
                        'end_at': (now + timedelta(minutes=tep_bonus_minutes)).isoformat(),
                    }
                    team['active_bonus'] = tep_bonus
                    team['active_bonus_label'] = f"⚡+{tep_bonus['bonus_percent']}%"
                    team.setdefault('bonus_windows', []).append({
                        'bonus_percent': 15,
                        'source': 'tep',
                        'start_at': now.isoformat(),
                        'end_at': (now + timedelta(minutes=tep_bonus_minutes)).isoformat(),
                        'trigger_tep': tep_threshold,
                    })
                    active_now = tep_bonus
                    team_data_changed = True
                    enqueue_overlay_event('team_effort_bonus', f"🏁 Team Effort Bonus: {team_name} earned +15% for {tep_bonus_minutes}m")

            _save_team_points_cache(cache_payload)
        if team_data_changed:
            _save_team_data(team_data)


def _normalize_team_name(name):
    return re.sub(r'\s+', ' ', str(name or '').strip())


def _normalize_username(name):
    return str(name or '').strip().lower().lstrip('@')


def _generate_team_name(seed_text=''):
    prefixes = [
        'Turbo', 'Neon', 'Cosmic', 'Iron', 'Velocity', 'Quantum', 'Marble', 'Apex', 'Pulse', 'Nova'
    ]
    suffixes = [
        'Racers', 'Orbit', 'Legends', 'Storm', 'Dynasty', 'Squad', 'Alliance', 'Crew', 'Circuit', 'Titans'
    ]
    seed = f"{seed_text}-{datetime.now(timezone.utc).isoformat()}-{uuid.uuid4()}"
    digest = hashlib.sha256(seed.encode('utf-8')).hexdigest()
    prefix = prefixes[int(digest[:4], 16) % len(prefixes)]
    suffix = suffixes[int(digest[4:8], 16) % len(suffixes)]
    return f"{prefix} {suffix}"


def _get_channel_team_state(payload, channel_name):
    channels = payload.setdefault('channels', {})
    channel_key = _normalize_username(channel_name)
    if channel_key not in channels:
        channels[channel_key] = {
            'teams': {},
            'invites': [],
            'settings': {
                'points_mode': 'season',
                'max_team_size': 25,
            }
        }
    channel_state = channels[channel_key]
    channel_state.setdefault('teams', {})
    channel_state.setdefault('invites', [])
    channel_state.setdefault('settings', {'points_mode': 'season', 'max_team_size': 25})
    channel_state['settings'].setdefault('points_mode', 'season')
    channel_state['settings'].setdefault('max_team_size', 25)
    return channel_state


def _find_team_for_user(channel_state, username):
    user_key = _normalize_username(username)
    for team_name, team in channel_state.get('teams', {}).items():
        if team.get('captain') == user_key:
            return team_name, 'captain'
        if user_key in team.get('co_captains', []):
            return team_name, 'co_captain'
        if user_key in team.get('members', []):
            return team_name, 'member'
    return None, None


def _extract_subscriber_status(author):
    if not author:
        return False

    badges = getattr(author, 'badges', None)
    if isinstance(badges, dict):
        if 'subscriber' in badges or 'broadcaster' in badges:
            return True
    elif isinstance(badges, (list, tuple)):
        for badge in badges:
            token = str(badge).lower()
            if 'subscriber' in token or 'broadcaster' in token:
                return True

    is_sub = getattr(author, 'is_subscriber', None)
    if isinstance(is_sub, bool):
        return is_sub

    return False


def _extract_sub_tier(author):
    """Best-effort Twitch sub tier parsing: returns 0 (not sub), 1, 2, or 3."""
    if not author:
        return 0

    badges = getattr(author, 'badges', None)
    badge_blob = ''
    if isinstance(badges, dict):
        badge_blob = ' '.join([f"{k}/{v}" for k, v in badges.items()])
    elif isinstance(badges, (list, tuple)):
        badge_blob = ' '.join(str(v) for v in badges)

    token = badge_blob.lower()
    if 'subscriber' in token or 'broadcaster' in token:
        if '3000' in token:
            return 3
        if '2000' in token:
            return 2
        return 1

    if getattr(author, 'is_subscriber', False):
        return 1

    return 0


def _extract_message_bits(message):
    tags = getattr(message, 'tags', None)
    if isinstance(tags, dict):
        raw_bits = tags.get('bits')
        if raw_bits is not None:
            try:
                return max(0, int(raw_bits))
            except (TypeError, ValueError):
                pass

    raw_attr = getattr(message, 'bits', None)
    if raw_attr is not None:
        try:
            return max(0, int(raw_attr))
        except (TypeError, ValueError):
            pass

    return 0


def _parse_iso_datetime(raw_value):
    token = str(raw_value or '').strip()
    if not token:
        return None
    try:
        parsed = parser.parse(token)
    except Exception:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    else:
        parsed = parsed.astimezone(timezone.utc)
    return parsed


def _parse_allraces_timestamp(raw_value):
    return _parse_iso_datetime(raw_value)


def _is_team_scoring_mode(mode_value):
    normalized_mode = str(mode_value or '').strip().lower()
    return normalized_mode in {'race', 'br'}


def _sum_points_from_allraces(username, *, days=None, since_dt=None):
    username_key = _normalize_username(username)
    total = 0
    data_dir = config.get_setting('directory')
    if not data_dir:
        return 0

    cutoff = None
    if days is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, int(days)))
    if since_dt is not None:
        cutoff = max(cutoff, since_dt) if cutoff else since_dt

    for allraces in glob.glob(os.path.join(data_dir, "allraces_*.csv")):
        file_basename = os.path.basename(allraces)
        file_date = None
        date_match = re.search(r"allraces_(\d{4}-\d{2}-\d{2})\.csv$", file_basename)
        if date_match:
            try:
                file_date = datetime.strptime(date_match.group(1), "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except ValueError:
                file_date = None

        if cutoff and file_date and file_date < cutoff.replace(hour=0, minute=0, second=0, microsecond=0):
            continue

        try:
            with open(allraces, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) < 4:
                        continue
                    if _normalize_username(row[1]) != username_key:
                        continue
                    mode = row[4] if len(row) > 4 else ''
                    if not _is_team_scoring_mode(mode):
                        continue
                    try:
                        total += int(row[3])
                    except (TypeError, ValueError):
                        continue
        except Exception:
            continue

    return total


def _compute_team_points(channel_state, team_name, window='season'):
    channel_name = config.get_setting('CHANNEL')
    season_value = config.get_setting('season') or 'default'
    with TEAM_POINTS_CACHE_LOCK:
        cache_payload = _load_team_points_cache()
        season_state = _get_channel_season_points_state(cache_payload, channel_name, season_value)
        bucket = season_state.get('teams', {}).get(team_name)
        if isinstance(bucket, dict):
            if window == 'daily':
                day_key = _day_key_from_timestamp(datetime.now(timezone.utc))
                if day_key in bucket.get('daily', {}):
                    return int(bucket.get('daily', {}).get(day_key, 0))
            if window == 'weekly':
                week_key = _week_key_from_timestamp(datetime.now(timezone.utc))
                if week_key in bucket.get('weekly', {}):
                    return int(bucket.get('weekly', {}).get(week_key, 0))
            elif 'season_points' in bucket:
                return int(bucket.get('season_points', 0))

    team = channel_state.get('teams', {}).get(team_name)
    if not team:
        return 0

    members = [team.get('captain')] + list(team.get('co_captains', [])) + list(team.get('members', []))
    members = [m for m in {_normalize_username(v) for v in members} if m]

    points_mode = channel_state.get('settings', {}).get('points_mode', 'season')
    created_at = team.get('created_at')
    created_dt = None
    if created_at:
        try:
            created_dt = parser.parse(created_at)
            if created_dt.tzinfo is None:
                created_dt = created_dt.replace(tzinfo=timezone.utc)
            else:
                created_dt = created_dt.astimezone(timezone.utc)
        except Exception:
            created_dt = None

    total_points = 0
    member_meta = team.get('member_meta', {}) if isinstance(team.get('member_meta'), dict) else {}
    for username in members:
        since_member_join = None
        user_meta = member_meta.get(username, {}) if isinstance(member_meta.get(username), dict) else {}
        joined_at = _parse_iso_datetime(user_meta.get('joined_at'))
        if points_mode == 'active':
            since_member_join = joined_at or created_dt

        if window == 'daily':
            user_points = _sum_points_from_allraces(username, days=1, since_dt=since_member_join)
        elif window == 'weekly':
            user_points = _sum_points_from_allraces(username, days=7, since_dt=since_member_join)
        else:
            user_points = _sum_points_from_allraces(username, since_dt=since_member_join)

        # Subscribers receive +10% points while subscribed (best-effort from current metadata).
        if bool(user_meta.get('is_subscriber')):
            user_points = int(round(user_points * 1.10))

        total_points += user_points

    total_points += _compute_team_bonus_points(channel_state, team_name, window=window)

    # Cache fallback scan result so subsequent calls are O(1) local reads.
    with TEAM_POINTS_CACHE_LOCK:
        cache_payload = _load_team_points_cache()
        season_state = _get_channel_season_points_state(cache_payload, channel_name, season_value)
        bucket = _get_team_points_bucket(season_state, team_name)
        day_key = _day_key_from_timestamp(datetime.now(timezone.utc))
        week_key = _week_key_from_timestamp(datetime.now(timezone.utc))
        if window == 'daily':
            bucket['daily'][day_key] = int(total_points)
        elif window == 'weekly':
            bucket['weekly'][week_key] = int(total_points)
        else:
            bucket['season_points'] = int(total_points)
        bucket['last_updated'] = datetime.now(timezone.utc).isoformat()
        _save_team_points_cache(cache_payload)

    return total_points


def _compute_team_bonus_points(channel_state, team_name, window='season'):
    team = channel_state.get('teams', {}).get(team_name)
    if not team:
        return 0

    windows = team.get('bonus_windows', [])
    if not windows:
        return 0

    members = [team.get('captain')] + list(team.get('co_captains', [])) + list(team.get('members', []))
    members = {_normalize_username(v) for v in members if v}
    if not members:
        return 0

    now = datetime.now(timezone.utc)
    if window == 'daily':
        cutoff = now - timedelta(days=1)
    elif window == 'weekly':
        cutoff = now - timedelta(days=7)
    else:
        cutoff = None

    parsed_windows = []
    for entry in windows:
        start = _parse_allraces_timestamp(entry.get('start_at'))
        end = _parse_allraces_timestamp(entry.get('end_at'))
        if not start or not end:
            continue
        if cutoff and end < cutoff:
            continue
        try:
            mult = 1.0 + (_resolve_team_bonus_percent(entry, 0) / 100.0)
        except (TypeError, ValueError):
            mult = 1
        if mult <= 1.0:
            continue
        parsed_windows.append((start, end, mult))

    if not parsed_windows:
        return 0

    data_dir = config.get_setting('directory')
    if not data_dir:
        return 0

    bonus_points = 0
    for allraces in glob.glob(os.path.join(data_dir, "allraces_*.csv")):
        try:
            with open(allraces, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) < 6:
                        continue
                    if _normalize_username(row[1]) not in members:
                        continue
                    mode = row[4] if len(row) > 4 else ''
                    if not _is_team_scoring_mode(mode):
                        continue
                    ts = _parse_allraces_timestamp(row[5])
                    if not ts:
                        continue
                    if cutoff and ts < cutoff:
                        continue
                    try:
                        row_points = int(row[3])
                    except (TypeError, ValueError):
                        continue
                    for start, end, mult in parsed_windows:
                        if start <= ts <= end:
                            bonus_points += int(math.floor(row_points * (mult - 1.0)))
                            break
        except Exception:
            continue

    return bonus_points


def _compute_team_bonus_races(channel_state, team_name, *, days=None):
    channel_name = config.get_setting('CHANNEL')
    season_value = config.get_setting('season') or 'default'
    with TEAM_POINTS_CACHE_LOCK:
        cache_payload = _load_team_points_cache()
        season_state = _get_channel_season_points_state(cache_payload, channel_name, season_value)
        bucket = season_state.get('teams', {}).get(team_name)
        if isinstance(bucket, dict):
            day_key = _day_key_from_timestamp(datetime.now(timezone.utc))
            if days is None or int(days) <= 1:
                return int(bucket.get('bonus_races_daily', {}).get(day_key, 0))

    team = channel_state.get('teams', {}).get(team_name)
    if not team:
        return 0

    bonus_windows = team.get('bonus_windows', [])
    if not bonus_windows:
        return 0

    members = [team.get('captain')] + list(team.get('co_captains', [])) + list(team.get('members', []))
    members = {_normalize_username(v) for v in members if v}
    if not members:
        return 0

    parsed_windows = []
    cutoff = None
    if days is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, int(days)))
    for window in bonus_windows:
        start = _parse_allraces_timestamp(window.get('start_at'))
        end = _parse_allraces_timestamp(window.get('end_at'))
        if not start or not end:
            continue
        if cutoff and end < cutoff:
            continue
        parsed_windows.append((start, end))

    if not parsed_windows:
        return 0

    data_dir = config.get_setting('directory')
    if not data_dir:
        return 0

    count = 0
    for allraces in glob.glob(os.path.join(data_dir, "allraces_*.csv")):
        try:
            with open(allraces, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) < 6:
                        continue
                    if _normalize_username(row[1]) not in members:
                        continue
                    mode = row[4] if len(row) > 4 else ''
                    if not _is_team_scoring_mode(mode):
                        continue
                    ts = _parse_allraces_timestamp(row[5])
                    if not ts:
                        continue
                    if any(start <= ts <= end for start, end in parsed_windows):
                        count += 1
        except Exception:
            continue

    return count


def _compute_team_subscriber_stats(team):
    member_meta = team.get('member_meta', {})
    if not isinstance(member_meta, dict):
        member_meta = {}

    tier_points = 0
    sub_count = 0
    for info in member_meta.values():
        if not isinstance(info, dict):
            continue
        try:
            tier = int(info.get('sub_tier', 0))
        except (TypeError, ValueError):
            tier = 0
        normalized_tier = max(0, min(3, tier))
        tier_points += normalized_tier
        if normalized_tier > 0:
            sub_count += 1

    members = [team.get('captain')] + list(team.get('co_captains', [])) + list(team.get('members', []))
    total_members = len([member for member in members if member])
    coverage_pct = (sub_count / total_members * 100) if total_members > 0 else 0.0
    estimated_team_bonus_pct = (sub_count / total_members * 10) if total_members > 0 else 0.0

    return {
        'tier_points': tier_points,
        'sub_count': sub_count,
        'total_members': total_members,
        'coverage_pct': coverage_pct,
        'estimated_team_bonus_pct': estimated_team_bonus_pct,
    }


def _compute_team_sub_points(team):
    return _compute_team_subscriber_stats(team).get('tier_points', 0)


def _is_teams_enabled_flag():
    return bool(parse_boolean_token(config.get_setting('teams_enabled'), default=True))


def _random_overlay_team_emote():
    raw_pool = str(config.get_setting('teams_overlay_emote_pool') or '').strip()
    if raw_pool:
        pool = [token.strip() for token in raw_pool.split(',') if token.strip()]
    else:
        pool = ['Kappa', 'PogChamp', 'LUL', 'HeyGuys', 'CoolCat']
    return random.choice(pool) if pool else ':white_check_mark:'


def _overlay_team_icon(team):
    logo = str(team.get('logo') or '').strip()
    return logo or _random_overlay_team_emote()


def _fetch_twitch_emotes_page(url, headers, params):
    lookup = {}
    cursor = None
    for _ in range(8):
        query = dict(params or {})
        if cursor:
            query['after'] = cursor
        try:
            response = requests.get(url, headers=headers, params=query, timeout=8)
        except Exception:
            break
        if response.status_code != 200:
            break
        try:
            payload = response.json() or {}
        except Exception:
            break

        for emote in payload.get('data', []) or []:
            if not isinstance(emote, dict):
                continue
            name = str(emote.get('name') or '').strip().lower()
            if not name:
                continue
            images = emote.get('images') if isinstance(emote.get('images'), dict) else {}
            emote_url = str(images.get('url_2x') or images.get('url_1x') or images.get('url_4x') or '').strip()
            if emote_url:
                lookup[name] = emote_url

        cursor = (((payload.get('pagination') or {}).get('cursor')) or '').strip()
        if not cursor:
            break
    return lookup


def _build_twitch_emote_lookup(channel_name):
    token = get_oauth_token()
    if not token:
        return {}

    headers = {
        'Authorization': f'Bearer {token}',
        'Client-Id': CLIENT_ID,
    }

    lookup = {}
    lookup.update(_fetch_twitch_emotes_page('https://api.twitch.tv/helix/chat/emotes/global', headers, {'first': 100}))

    broadcaster_id = ''
    normalized_channel = _normalize_username(channel_name)
    if normalized_channel:
        try:
            user_response = requests.get(
                'https://api.twitch.tv/helix/users',
                headers=headers,
                params={'login': normalized_channel},
                timeout=8,
            )
            if user_response.status_code == 200:
                user_payload = user_response.json() or {}
                users = user_payload.get('data') or []
                if users:
                    broadcaster_id = str((users[0] or {}).get('id') or '').strip()
        except Exception:
            broadcaster_id = ''

    if broadcaster_id:
        lookup.update(_fetch_twitch_emotes_page(
            'https://api.twitch.tv/helix/chat/emotes',
            headers,
            {'first': 100, 'broadcaster_id': broadcaster_id},
        ))

    return lookup


def _get_twitch_emote_lookup_cached(channel_name):
    now_ts = time.time()
    normalized_channel = _normalize_username(channel_name)
    with TEAM_EMOTE_CACHE_LOCK:
        if (
            TEAM_EMOTE_CACHE.get('lookup')
            and TEAM_EMOTE_CACHE.get('channel') == normalized_channel
            and now_ts <= float(TEAM_EMOTE_CACHE.get('expires_at') or 0.0)
        ):
            return dict(TEAM_EMOTE_CACHE.get('lookup') or {})

    lookup = _build_twitch_emote_lookup(normalized_channel)
    with TEAM_EMOTE_CACHE_LOCK:
        TEAM_EMOTE_CACHE['lookup'] = dict(lookup)
        TEAM_EMOTE_CACHE['channel'] = normalized_channel
        TEAM_EMOTE_CACHE['expires_at'] = now_ts + TEAM_EMOTE_CACHE_TTL_SECONDS
    return lookup


def _team_logo_icon_url(logo_text, channel_name):
    logo = str(logo_text or '').strip()
    if not logo:
        return None

    if logo.startswith('http://') or logo.startswith('https://'):
        return logo

    lookup = _get_twitch_emote_lookup_cached(channel_name)
    if not lookup:
        return None

    candidates = [logo.lower()]
    if logo.startswith(':') and logo.endswith(':') and len(logo) > 2:
        candidates.append(logo[1:-1].strip().lower())

    for candidate in candidates:
        if candidate in lookup:
            return lookup[candidate]

    return None


def _build_team_leaderboard_rows(*, window='season', limit=10):
    if not _is_teams_enabled_flag():
        return []

    channel_name = config.get_setting('CHANNEL')
    with TEAM_DATA_LOCK:
        data = _load_team_data()
        channel_state = _get_channel_team_state(data, channel_name)
        teams_snapshot = {
            team_name: {
                'captain': team.get('captain'),
                'co_captains': list(team.get('co_captains', [])),
                'members': list(team.get('members', [])),
                'is_recruiting': bool(team.get('is_recruiting')),
                'active_bonus_label': team.get('active_bonus_label') or '—',
                'logo': team.get('logo'),
            }
            for team_name, team in channel_state.get('teams', {}).items()
            if isinstance(team, dict)
        }

    if not teams_snapshot:
        return []

    channel_state_for_points = {'teams': teams_snapshot}
    rows = []
    for team_name, team in teams_snapshot.items():
        points = _safe_int(_compute_team_points(channel_state_for_points, team_name, window=window))
        logo_text = _overlay_team_icon(team)
        rows.append({
            'name': team_name,
            'points': points,
            'captain': format_user_tag(team.get('captain')),
            'size': 1 + len(team.get('co_captains', [])) + len(team.get('members', [])),
            'recruiting': bool(team.get('is_recruiting')),
            'bonus_label': team.get('active_bonus_label') or '—',
            'icon': logo_text,
            'icon_url': _team_logo_icon_url(logo_text, channel_name),
        })

    rows.sort(key=lambda row: (-_safe_int(row.get('points')), str(row.get('name', '')).lower()))
    for idx, row in enumerate(rows, start=1):
        row['rank'] = idx
    return rows[:max(1, _safe_int(limit) or 10)]


def _build_overlay_teams_payload(limit=10):
    return {
        'updated_at': datetime.now().isoformat(timespec='seconds'),
        'top_today': _build_team_leaderboard_rows(window='daily', limit=limit),
        'top_weekly': _build_team_leaderboard_rows(window='weekly', limit=limit),
        'top_season': _build_team_leaderboard_rows(window='season', limit=limit),
    }


def _get_top_players_points(days=1, limit=5):
    data_dir = config.get_setting('directory')
    if not data_dir:
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, int(days)))
    points = defaultdict(int)
    display_names = {}
    for allraces in glob.glob(os.path.join(data_dir, "allraces_*.csv")):
        file_basename = os.path.basename(allraces)
        date_match = re.search(r"allraces_(\d{4}-\d{2}-\d{2})\.csv$", file_basename)
        if date_match:
            try:
                file_date = datetime.strptime(date_match.group(1), "%Y-%m-%d").replace(tzinfo=timezone.utc)
                if file_date < cutoff.replace(hour=0, minute=0, second=0, microsecond=0):
                    continue
            except ValueError:
                pass
        try:
            with open(allraces, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) < 4:
                        continue
                    user_key = _normalize_username(row[1])
                    if not user_key:
                        continue
                    display_names[user_key] = row[2].strip() if len(row) > 2 and row[2].strip() else user_key
                    try:
                        points[user_key] += int(row[3])
                    except (TypeError, ValueError):
                        continue
        except Exception:
            continue
    top_rows = sorted(points.items(), key=lambda item: item[1], reverse=True)[:max(1, int(limit))]
    return [(display_names.get(user, user), score) for user, score in top_rows]


def _walk_payload_nodes(payload):
    stack = [payload]
    while stack:
        current = stack.pop()
        yield current
        if isinstance(current, dict):
            for value in current.values():
                if isinstance(value, (dict, list)):
                    stack.append(value)
        elif isinstance(current, list):
            for value in current:
                if isinstance(value, (dict, list)):
                    stack.append(value)


def _extract_streamer_candidates(payload):
    candidates = []

    for current in _walk_payload_nodes(payload):
        if not isinstance(current, dict):
            continue

        streamer_value = None
        for key in ('streamer', 'streamer_username', 'streamerUsername', 'channel', 'username', 'twitch'):
            if key in current and str(current.get(key) or '').strip():
                streamer_value = current.get(key)
                break

        if streamer_value is None:
            continue

        normalized_streamer = normalize_channel_name(streamer_value)
        if not normalized_streamer:
            continue

        score = 0
        status_tokens = str(current.get('status') or '').strip().lower()
        if status_tokens in {'active', 'current', 'live', 'selected'}:
            score += 3

        for key in ('active', 'is_active', 'isActive', 'current', 'is_current', 'isCurrent', 'selected', 'is_selected'):
            if parse_boolean_token(current.get(key), default=False):
                score += 3
                break

        context_blob = ' '.join(f"{k}={v}" for k, v in current.items()).lower()
        if 'competitive' in context_blob:
            score += 2
        if 'raid' in context_blob:
            score += 2

        candidates.append((score, normalized_streamer))

    return candidates


def _parse_competition_timestamp(raw_value):
    if raw_value is None:
        return None

    if isinstance(raw_value, (int, float)):
        ts = float(raw_value)
        if ts > 10_000_000_000:
            ts /= 1000.0
        try:
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None

    token = str(raw_value).strip()
    if not token:
        return None

    try:
        as_num = float(token)
        if as_num > 10_000_000_000:
            as_num /= 1000.0
        return datetime.fromtimestamp(as_num, tz=timezone.utc)
    except (TypeError, ValueError, OverflowError, OSError):
        pass

    try:
        parsed = parser.parse(token)
    except (TypeError, ValueError, OverflowError):
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def get_competitive_raid_started_at(payload):
    preferred_keys = (
        'raid_started_at', 'raidStartTime', 'raid_start_time', 'start_time',
        'startTime', 'started_at', 'startedAt', 'timestamp', 'time'
    )

    if isinstance(payload, dict):
        for key in preferred_keys:
            parsed = _parse_competition_timestamp(payload.get(key))
            if parsed is not None:
                return parsed

    for node in _walk_payload_nodes(payload):
        if not isinstance(node, dict):
            continue
        for key in preferred_keys:
            parsed = _parse_competition_timestamp(node.get(key))
            if parsed is not None:
                return parsed

    return None


def get_current_competitive_raid_streamer(payload):
    candidates = _extract_streamer_candidates(payload)
    if not candidates:
        return None

    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def _extract_top_three_entries(payload):
    candidates = []
    score_keys = ('score', 'points', 'xp', 'value', 'total')

    for node in _walk_payload_nodes(payload):
        if not isinstance(node, list) or len(node) < 3:
            continue

        entries = []
        for item in node:
            if not isinstance(item, dict):
                continue

            username = ''
            for name_key in ('streamer', 'streamer_username', 'streamerUsername', 'channel', 'username', 'name'):
                username = normalize_channel_name(item.get(name_key))
                if username:
                    break
            if not username:
                continue

            score_value = None
            for score_key in score_keys:
                if score_key in item:
                    try:
                        score_value = int(float(item.get(score_key) or 0))
                    except (TypeError, ValueError):
                        score_value = None
                    break

            rank_raw = item.get('rank')
            try:
                rank_value = int(float(rank_raw)) if rank_raw is not None else None
            except (TypeError, ValueError):
                rank_value = None

            entries.append({'streamer': username, 'score': score_value, 'rank': rank_value})

        if len(entries) < 3:
            continue

        ranked_count = sum(1 for e in entries if e.get('rank') is not None)
        scored_count = sum(1 for e in entries if e.get('score') is not None)
        list_score = ranked_count * 2 + scored_count
        candidates.append((list_score, entries))

    if not candidates:
        return []

    _, entries = max(candidates, key=lambda pair: pair[0])

    if any(e.get('rank') is not None for e in entries):
        entries.sort(key=lambda e: (e.get('rank') is None, e.get('rank') if e.get('rank') is not None else 999999))
    elif any(e.get('score') is not None for e in entries):
        entries.sort(key=lambda e: (e.get('score') is None, -(e.get('score') or 0)))

    return entries[:3]


def format_competitive_raid_top_three(entries):
    if not entries:
        return None

    formatted = []
    for place, entry in enumerate(entries[:3], start=1):
        label = f"{place}) {entry.get('streamer', 'unknown')}"
        score = entry.get('score')
        if score is not None:
            label += f" ({score:,})"
        formatted.append(label)

    return "🏁 Competitive raid final top 3: " + " | ".join(formatted)


def fetch_competitions_payload(timeout=20):
    logger.info("API call: competitions")
    response = requests.get("https://pixelbypixel.studio/api/competitions", timeout=timeout)
    response.raise_for_status()
    return response.json()


def fetch_competitions_history_payload(timeout=20):
    history_urls = [
        "https://pixelbypixel.studio/api/competitions/history",
        "https://pixelbypixel.studio/api/competition-history",
    ]

    last_error = None
    for history_url in history_urls:
        try:
            logger.info("API call: competition history (%s)", history_url)
            response = requests.get(history_url, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as error:
            last_error = error

    if last_error is not None:
        raise last_error

    raise requests.RequestException("No competition history endpoint candidates configured")


def get_competitive_raid_poll_delay_seconds(started_at, now=None):
    if started_at is None:
        return 180

    now_utc = now.astimezone(timezone.utc) if now else datetime.now(timezone.utc)
    elapsed_seconds = max(0, int((now_utc - started_at).total_seconds()))
    cycle_seconds = 20 * 60
    position_in_cycle = elapsed_seconds % cycle_seconds
    seconds_to_rotation = cycle_seconds - position_in_cycle

    if position_in_cycle < 5 * 60:
        baseline = 90
    else:
        baseline = 150

    if seconds_to_rotation <= 75:
        return max(15, seconds_to_rotation + 2)

    return baseline


def get_competitive_raid_cycle_state(now=None):
    """Return deterministic competitive raid cycle state.

    Cycle definition (UTC):
    - Live window: first 5 minutes of each 20-minute block (:00/:20/:40)
    - Queue window: remaining 15 minutes
    """
    now_utc = now.astimezone(timezone.utc) if now else datetime.now(timezone.utc)
    cycle_minute = now_utc.minute % 20
    cycle_second = cycle_minute * 60 + now_utc.second
    window = 'live' if cycle_minute < 5 else 'queue'
    seconds_until_transition = (5 * 60 - cycle_second) if window == 'live' else (20 * 60 - cycle_second)
    return {
        'window': window,
        'seconds_until_transition': max(1, int(seconds_until_transition)),
    }


def get_competitive_raid_live_window_started_at(now=None):
    """Return UTC timestamp for the current/most-recent :00/:20/:40 live boundary."""
    now_utc = now.astimezone(timezone.utc) if now else datetime.now(timezone.utc)
    minute_floor = now_utc.minute - (now_utc.minute % 20)
    return now_utc.replace(minute=minute_floor, second=0, microsecond=0)


def _collect_payload_field_names(payload):
    field_names = set()
    for node in _walk_payload_nodes(payload):
        if isinstance(node, dict):
            field_names.update(str(key) for key in node.keys())
    return sorted(field_names)


def _extract_raid_streamer_stats(payload, selected_streamer):
    target = normalize_channel_name(selected_streamer)
    if not target:
        return None

    best_match = None
    best_score = -1

    for node in _walk_payload_nodes(payload):
        if not isinstance(node, dict):
            continue

        node_streamer = None
        for key in ('streamer', 'streamer_username', 'streamerUsername', 'channel', 'username', 'twitch', 'name'):
            candidate = normalize_channel_name(node.get(key))
            if candidate:
                node_streamer = candidate
                break

        if node_streamer != target:
            continue

        score = sum(1 for value in node.values() if not isinstance(value, (dict, list)))
        if score > best_score:
            best_score = score
            best_match = node

    if not isinstance(best_match, dict):
        return None

    stats = {}
    for key, value in best_match.items():
        if isinstance(value, (dict, list)):
            continue
        stats[str(key)] = value

    stats['streamer_normalized'] = target
    return stats


def persist_competitive_raid_snapshot(payload, selected_streamer, started_at):
    season_directory = config.get_setting('directory')
    if not season_directory:
        return

    os.makedirs(season_directory, exist_ok=True)

    field_names = _collect_payload_field_names(payload)
    field_path = os.path.join(season_directory, 'competitive_raid_payload_fields.json')
    with open(field_path, 'w', encoding='utf-8', errors='ignore') as field_file:
        json.dump(field_names, field_file, ensure_ascii=False, indent=2)

    stats = _extract_raid_streamer_stats(payload, selected_streamer)
    if not stats:
        return

    record = {
        'captured_at_utc': datetime.now(timezone.utc).isoformat(),
        'raid_started_at_utc': started_at.isoformat() if started_at else None,
        'streamer': normalize_channel_name(selected_streamer),
        'stats': stats,
    }

    stats_path = os.path.join(season_directory, 'competitive_raid_streamer_stats.jsonl')
    with open(stats_path, 'a', encoding='utf-8', errors='ignore') as stats_file:
        stats_file.write(json.dumps(record, ensure_ascii=False) + '\n')



def _extract_phase_streamer_info(payload):
    queue_candidate = None
    queue_score = -1
    live_candidate = None
    live_score = -1

    queue_ts_keys = ('queue_started_at', 'queueStartTime', 'queue_start_time', 'queue_timestamp', 'queue_time')
    live_ts_keys = ('raid_started_at', 'raidStartTime', 'raid_start_time', 'live_started_at', 'liveStartTime', 'start_time', 'startTime', 'started_at', 'startedAt', 'timestamp', 'time')

    for node in _walk_payload_nodes(payload):
        if not isinstance(node, dict):
            continue

        streamer_name = ''
        for key in ('streamer', 'streamer_username', 'streamerUsername', 'channel', 'username', 'twitch', 'name'):
            streamer_name = normalize_channel_name(node.get(key))
            if streamer_name:
                break

        if not streamer_name:
            continue

        status = str(node.get('status') or '').strip().lower()
        context = ' '.join(str(k) for k in node.keys()).lower() + ' ' + ' '.join(str(v) for v in node.values()).lower()

        queue_weight = 0
        if 'queue' in context:
            queue_weight += 3
        if status in {'queued', 'queue', 'waiting', 'upnext', 'next'}:
            queue_weight += 4

        live_weight = 0
        if any(token in context for token in ('live', 'active', 'current', 'in_progress', 'started')):
            live_weight += 2
        if status in {'live', 'active', 'current', 'in_progress', 'started'}:
            live_weight += 4
        for key in ('active', 'is_active', 'isActive', 'current', 'is_current', 'isCurrent'):
            if parse_boolean_token(node.get(key), default=False):
                live_weight += 3
                break

        queue_started_at = None
        for key in queue_ts_keys:
            parsed = _parse_competition_timestamp(node.get(key))
            if parsed is not None:
                queue_started_at = parsed
                break

        live_started_at = None
        for key in live_ts_keys:
            parsed = _parse_competition_timestamp(node.get(key))
            if parsed is not None:
                live_started_at = parsed
                break

        if queue_weight > queue_score:
            queue_score = queue_weight
            queue_candidate = {'streamer': streamer_name, 'started_at': queue_started_at, 'source': node}

        if live_weight > live_score:
            live_score = live_weight
            live_candidate = {'streamer': streamer_name, 'started_at': live_started_at, 'source': node}

    fallback_streamer = get_current_competitive_raid_streamer(payload)
    fallback_started = get_competitive_raid_started_at(payload)

    if queue_candidate is None and fallback_streamer:
        queue_candidate = {'streamer': fallback_streamer, 'started_at': None, 'source': None}

    if live_candidate is None and fallback_streamer:
        live_candidate = {'streamer': fallback_streamer, 'started_at': fallback_started, 'source': None}

    return queue_candidate, live_candidate


def _format_history_summary_for_streamer(entry, streamer_name):
    if not isinstance(entry, dict):
        return f"🏁 Competitive raid summary for {streamer_name}: no history entry found yet."

    rank = entry.get('rank')
    points = entry.get('points')
    score = entry.get('score') if entry.get('score') is not None else points
    wins = entry.get('wins')

    details = [f"streamer: {streamer_name}"]
    if rank is not None:
        details.append(f"rank: {rank}")
    if score is not None:
        details.append(f"score: {score}")
    if wins is not None:
        details.append(f"wins: {wins}")

    return "🏁 Competitive raid summary | " + ' | '.join(details)


def _latest_history_entry_for_streamer(payload, streamer_name):
    target = normalize_channel_name(streamer_name)
    if not target:
        return None

    best = None
    best_ts = None

    for node in _walk_payload_nodes(payload):
        if not isinstance(node, dict):
            continue

        node_name = ''
        for key in ('streamer', 'streamer_username', 'streamerUsername', 'channel', 'username', 'twitch', 'name'):
            node_name = normalize_channel_name(node.get(key))
            if node_name:
                break

        if node_name != target:
            continue

        node_ts = None
        for key in ('raid_started_at', 'raidStartTime', 'raid_start_time', 'start_time', 'startTime', 'started_at', 'startedAt', 'timestamp', 'time', 'created_at', 'createdAt'):
            node_ts = _parse_competition_timestamp(node.get(key))
            if node_ts is not None:
                break

        if best is None or (node_ts is not None and (best_ts is None or node_ts > best_ts)):
            best = node
            best_ts = node_ts

    return best


def _parse_iso_utc(raw_value):
    token = str(raw_value or '').strip()
    if not token:
        return None
    try:
        parsed = parser.parse(token)
    except (TypeError, ValueError, OverflowError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)



def _extract_participant_count(payload, preferred_node=None, streamer_name=None):
    count_keys = (
        'participants', 'participant_count', 'participantCount',
        'players', 'player_count', 'playerCount',
        'entries', 'entry_count', 'entryCount',
        'queued', 'queue_count', 'queueCount'
    )

    candidate_nodes = []
    if isinstance(preferred_node, dict):
        candidate_nodes.append(preferred_node)

    target_streamer = normalize_channel_name(streamer_name)
    for node in _walk_payload_nodes(payload):
        if not isinstance(node, dict):
            continue

        if target_streamer:
            node_streamer = ''
            for key in ('streamer', 'streamer_username', 'streamerUsername', 'channel', 'username', 'twitch', 'name'):
                node_streamer = normalize_channel_name(node.get(key))
                if node_streamer:
                    break
            if node_streamer and node_streamer != target_streamer:
                continue

        candidate_nodes.append(node)

    for node in candidate_nodes:
        for key in count_keys:
            if key not in node:
                continue
            value = node.get(key)
            if isinstance(value, list):
                return len(value)
            if isinstance(value, dict):
                for nested_key in ('count', 'total', 'size', 'length'):
                    if nested_key in value:
                        return _safe_int(value.get(nested_key))
            parsed = _safe_int(value)
            if parsed > 0:
                return parsed

    return None



def parse_tilt_result_row(row):
    """Parse a tilt results row written by `tilted` and return (username, points, run_id)."""
    if len(row) < 5:
        return None

    run_id = row[0].strip()
    username = row[2].strip()

    if not username:
        return None

    try:
        points = int(float(row[4]))
    except (TypeError, ValueError):
        return None

    return username, points, run_id



def parse_tilt_result_detail(row):
    """Parse a tilt results row and return details used by tilt analytics and chat commands."""
    parsed = parse_tilt_result_row(row)
    if parsed is None:
        return None

    username, points, run_id = parsed

    def parse_flag_token(value, allow_numeric=True):
        token = str(value).strip().lower()
        if token in ('true', 'yes', 'y'):
            return True
        if token in ('false', 'no', 'n'):
            return False
        if allow_numeric and token in ('1', '0'):
            return token == '1'
        return None

    is_top_tiltee = False
    # Tilt result exports have evolved over time. We parse from the tail and
    # prefer explicit boolean words first, then fall back to nearby numeric
    # flags (for older 1/0 formats).
    tail_tokens = list(reversed(row[-6:]))

    for candidate in tail_tokens:
        parsed_flag = parse_flag_token(candidate, allow_numeric=False)
        if parsed_flag is not None:
            is_top_tiltee = parsed_flag
            break

    if not is_top_tiltee:
        for candidate in (row[-1], row[-2] if len(row) >= 2 else None, row[-3] if len(row) >= 3 else None):
            token = str(candidate or '').strip()
            if not token or '[' in token or ']' in token or ',' in token:
                continue
            parsed_flag = parse_flag_token(token, allow_numeric=True)
            if parsed_flag is not None:
                is_top_tiltee = parsed_flag
                break

    return {
        'run_id': run_id,
        'username': username,
        'points': points,
        'is_top_tiltee': is_top_tiltee,
    }


def get_tilt_xp_totals_from_results_files(target_date=None):
    """Calculate Tilt XP from season result files.

    Returns a tuple of (season_xp, day_xp). `day_xp` is filtered by `target_date`
    using the MyStats internal Marble Day clock (YYYY-MM-DD).
    """
    data_dir = config.get_setting('directory')
    if not data_dir:
        return 0, 0

    level_survivors = defaultdict(int)
    level_survivors_by_day = defaultdict(int)

    for tilts_file in sorted(glob.glob(os.path.join(data_dir, "tilts_*.csv"))):
        file_date = os.path.basename(tilts_file)[6:16]
        try:
            with open(tilts_file, 'rb') as f:
                raw_data = f.read()
            result = chardet.detect(raw_data)
            encoding = result['encoding'] if result['encoding'] else 'utf-8'

            with open(tilts_file, 'r', encoding=encoding, errors='ignore') as f:
                reader = iter_csv_rows(f)
                for row in reader:
                    parsed = parse_tilt_result_row(row)
                    if parsed is None:
                        continue

                    _, points, run_id = parsed
                    if points <= 0 or len(row) < 2:
                        continue

                    try:
                        level_number = int(''.join(ch for ch in str(row[1]).strip() if ch.isdigit()) or '0')
                    except (TypeError, ValueError):
                        level_number = 0

                    if level_number <= 0:
                        continue

                    level_key = (str(run_id), level_number)
                    level_survivors[level_key] += 1
                    if target_date and file_date == target_date:
                        level_survivors_by_day[level_key] += 1

        except FileNotFoundError:
            continue
        except Exception as e:
            logger.error("Unexpected error", exc_info=True)

    season_xp = int(sum(math.floor(count * get_tilt_multiplier(level)) for (_, level), count in level_survivors.items()))
    day_xp = int(sum(math.floor(count * get_tilt_multiplier(level)) for (_, level), count in level_survivors_by_day.items()))
    return season_xp, day_xp


def is_tilt_top_tiltee_milestone(count):
    if count in (3, 5):
        return True
    return count >= 10 and count % 5 == 0


def normalize_tilt_player_name(value):
    raw = str(value or '').strip().lower().lstrip('@')
    compact = ''.join(ch for ch in raw if ch.isalnum() or ch == '_')
    return compact or raw


def get_tilt_multiplier(level_number):
    if 1 <= level_number <= 14:
        return 1.0 / 3.0
    if 15 <= level_number <= 17:
        return 6.0
    if 18 <= level_number <= 20:
        return 7.0
    if 21 <= level_number <= 23:
        return 12.0
    if 24 <= level_number <= 26:
        return 13.5
    if 27 <= level_number <= 29:
        return 50.0
    if 30 <= level_number <= 32:
        return 66.0
    if 33 <= level_number <= 35:
        return 84.0
    if 36 <= level_number <= 38:
        return 104.0
    if 39 <= level_number <= 41:
        return 126.0
    if level_number >= 42:
        sets_of_three = (level_number - 42) // 3
        return 135.0 + (sets_of_three * 9)
    return 0.0


def write_tilt_output_files(values):
    output_directory = get_tilt_output_directory()
    for filename, value in values.items():
        try:
            with open(os.path.join(output_directory, filename), 'w', encoding='utf-8', errors='ignore') as fp:
                fp.write(str(value))
        except Exception as e:
            logger.warning(f"Failed writing tilt output file '{filename}': {e}")
    logger.info("Data synced: tilt output files updated")


def get_tilt_best_floor_level_num(setting_key):
    """Read a user-entered best level (1-based) and convert to internal 0-based level."""
    configured_level = get_int_setting(setting_key, 1)
    return max(0, configured_level - 1)


def get_int_setting(setting_key, default=0):
    cfg = globals().get("config")
    if cfg is None:
        return default

    raw_value = cfg.get_setting(setting_key)
    if raw_value is None or raw_value == '':
        return default

    normalized = str(raw_value).strip()

    # Accept locale-formatted group separators (e.g. "14.503,472" or "14,503,472").
    if re.fullmatch(r'[+-]?\d{1,3}(?:[.,]\d{3})+', normalized):
        normalized = normalized.replace('.', '').replace(',', '')
        try:
            return int(normalized)
        except (TypeError, ValueError):
            return default

    # Fall back to float-style parsing for values like "12.8" / "12,8".
    float_candidate = normalized
    if ',' in float_candidate and '.' not in float_candidate:
        float_candidate = float_candidate.replace(',', '.')
    else:
        float_candidate = float_candidate.replace(',', '')

    try:
        return int(float(float_candidate))
    except (TypeError, ValueError):
        return default


def _get_season_quest_fallback_completer_name():
    for setting_key in ('TWITCH_USERNAME', 'CHANNEL'):
        raw_value = (config.get_setting(setting_key) or '').strip()
        if raw_value:
            return raw_value.lstrip('#@')
    return 'The streamer'


def _get_season_quest_completer_name(quest_definition, target_value, fallback_name):
    user_stats = get_user_season_stats()
    if not user_stats or target_value <= 0:
        return fallback_name

    quest_value_keys = {
        'races': 'races',
        'points': 'points',
        'race_hs': 'race_hs',
        'br_hs': 'br_hs',
        'tilt_levels': 'tilt_levels',
        'tilt_tops': 'tilt_top_tiltee',
        'tilt_points': 'tilt_points',
    }
    stat_key = quest_value_keys.get(quest_definition['id'])
    if not stat_key:
        return fallback_name

    completer = None
    best_value = -1
    for stats in user_stats.values():
        current_value = int(stats.get(stat_key, 0) or 0)
        if current_value < target_value:
            continue
        if current_value <= best_value:
            continue
        display_name = (stats.get('display_name') or '').strip()
        if not display_name:
            continue
        completer = display_name
        best_value = current_value

    return completer or fallback_name


def _season_quest_value_map(tilt_totals=None):
    if tilt_totals is None:
        tilt_totals, _ = get_tilt_season_stats()
    return {
        'races': get_int_setting('totalcountseason', 0),
        'points': get_int_setting('totalpointsseason', 0),
        'race_hs': get_int_setting('race_hs_season', 0),
        'br_hs': get_int_setting('br_hs_season', 0),
        'tilt_levels': tilt_totals.get('levels', 0),
        'tilt_tops': tilt_totals.get('top_tiltees', 0),
        'tilt_points': tilt_totals.get('points', 0),
    }


def _get_season_scope_key():
    raw_season = str(config.get_setting('season') or '').strip().lower()
    normalized = ''.join(ch for ch in raw_season if ch.isalnum() or ch in ('-', '_'))
    return normalized or 'default'


def _load_season_quest_completion_state():
    raw_state = config.get_setting('season_quest_completion_state') or '{}'
    try:
        parsed = json.loads(raw_state)
    except (TypeError, ValueError, json.JSONDecodeError):
        parsed = {}
    return parsed if isinstance(parsed, dict) else {}


def _save_season_quest_completion_state(state):
    serialized = json.dumps(state, separators=(',', ':'), sort_keys=True)
    config.set_setting('season_quest_completion_state', serialized, persistent=True)


def _is_season_quest_complete(quest_definition, season_key, state):
    season_state = state.get(season_key, {})
    if not isinstance(season_state, dict):
        season_state = {}
    if season_state.get(quest_definition['id']) is True:
        return True

    legacy_flag = str(config.get_setting(quest_definition['legacy_complete_key']) or 'False').lower() == 'true'
    if legacy_flag:
        season_state[quest_definition['id']] = True
        state[season_key] = season_state
        return True
    return False


def get_season_quest_updates():
    if not is_chat_response_enabled("season_quests_enabled"):
        return []

    tilt_totals, _ = get_tilt_season_stats()
    value_map = _season_quest_value_map(tilt_totals)
    completion_state = _load_season_quest_completion_state()
    season_key = _get_season_scope_key()

    quest_messages = []
    fallback_completer_name = _get_season_quest_fallback_completer_name()
    state_updated = False

    for quest in SEASON_QUEST_DEFINITIONS:
        target_value = get_int_setting(quest['target_key'], 0)
        already_complete = _is_season_quest_complete(quest, season_key, completion_state)

        if target_value <= 0 or already_complete:
            continue

        current_value = value_map.get(quest['id'], 0)
        if current_value >= target_value:
            season_state = completion_state.setdefault(season_key, {})
            if not isinstance(season_state, dict):
                season_state = {}
                completion_state[season_key] = season_state
            season_state[quest['id']] = True
            config.set_setting(quest['legacy_complete_key'], 'True', persistent=True)
            completer_name = _get_season_quest_completer_name(quest, target_value, fallback_completer_name)
            quest_messages.append(quest['message'].format(name=completer_name, value=current_value, target=target_value))
            state_updated = True

    if state_updated:
        _save_season_quest_completion_state(completion_state)

    return quest_messages


def get_season_quest_targets():
    return {
        quest['id']: get_int_setting(quest['target_key'], 0)
        for quest in SEASON_QUEST_DEFINITIONS
    }



def _build_files_signature(file_paths):
    signature_parts = []
    for file_path in sorted(file_paths):
        try:
            stat = os.stat(file_path)
            signature_parts.append((os.path.abspath(file_path), int(stat.st_mtime_ns), int(stat.st_size)))
        except OSError:
            continue
    return tuple(signature_parts)


def _load_csv_rows_with_detection(csv_path):
    with open(csv_path, 'rb') as f:
        raw_data = f.read()
    result = chardet.detect(raw_data)
    encoding = result['encoding'] if result['encoding'] else 'utf-8'
    with open(csv_path, 'r', encoding=encoding, errors='ignore') as f:
        for row in iter_csv_rows(f):
            yield row


def get_tilt_season_stats():
    user_stats = {}
    totals = {'levels': 0, 'top_tiltees': 0, 'points': 0}

    directory = config.get_setting('directory')
    if not directory:
        return totals, user_stats

    tilt_files = glob.glob(os.path.join(directory, "tilts_*.csv"))
    signature = _build_files_signature(tilt_files)
    if _tilt_season_stats_cache.get('signature') == signature:
        return copy.deepcopy(_tilt_season_stats_cache.get('value'))

    for tilt_results in tilt_files:
        try:
            for row in _load_csv_rows_with_detection(tilt_results):
                detail = parse_tilt_result_detail(row)
                if detail is None:
                    continue

                username = detail['username'].strip().lower()
                if not username:
                    continue

                if username not in user_stats:
                    user_stats[username] = {
                        'display_name': detail['username'].strip() or username,
                        'tilt_levels': 0,
                        'tilt_top_tiltee': 0,
                        'tilt_points': 0,
                    }

                user_stats[username]['tilt_levels'] += 1
                user_stats[username]['tilt_points'] += detail['points']
                totals['levels'] += 1
                totals['points'] += detail['points']

                if detail['is_top_tiltee']:
                    user_stats[username]['tilt_top_tiltee'] += 1
                    totals['top_tiltees'] += 1
        except FileNotFoundError:
            continue
        except Exception:
            logger.error("Error reading tilt stats from %s", tilt_results, exc_info=True)

    _tilt_season_stats_cache['signature'] = signature
    _tilt_season_stats_cache['value'] = (copy.deepcopy(totals), copy.deepcopy(user_stats))
    return totals, user_stats


def get_user_season_stats():
    user_stats = {}
    data_dir = config.get_setting('directory')
    if not data_dir:
        return {}

    allraces_files = glob.glob(os.path.join(data_dir, "allraces_*.csv"))
    tilt_files = glob.glob(os.path.join(data_dir, "tilts_*.csv"))
    signature = (
        _build_files_signature(allraces_files),
        _build_files_signature(tilt_files),
    )
    if _user_season_stats_cache.get('signature') == signature:
        return copy.deepcopy(_user_season_stats_cache.get('value'))

    cutoff_30d = datetime.now(timezone.utc) - timedelta(days=30)

    for allraces in allraces_files:
        try:
            for row in _load_csv_rows_with_detection(allraces):
                if len(row) < 5:
                    continue
                username = row[1].strip().lower()
                display_name = row[2].strip() if len(row) > 2 else username
                if not username:
                    continue

                if username not in user_stats:
                    user_stats[username] = {
                        'display_name': display_name or username,
                        'races': 0,
                        'points': 0,
                        'race_hs': 0,
                        'br_hs': 0,
                        'tilt_levels': 0,
                        'tilt_top_tiltee': 0,
                        'tilt_points': 0,
                    }

                if display_name:
                    user_stats[username]['display_name'] = display_name

                user_stats[username]['races'] += 1
                row_timestamp = None
                if row:
                    try:
                        row_timestamp = parser.parse(str(row[0]).strip())
                        if row_timestamp.tzinfo is None:
                            row_timestamp = row_timestamp.replace(tzinfo=timezone.utc)
                        else:
                            row_timestamp = row_timestamp.astimezone(timezone.utc)
                    except Exception:
                        row_timestamp = None

                try:
                    points = int(row[3])
                except (TypeError, ValueError):
                    points = 0

                user_stats[username]['points'] += points
                if row_timestamp is not None and row_timestamp >= cutoff_30d:
                    user_stats[username].setdefault('recent_races_30d', 0)
                    user_stats[username].setdefault('recent_points_30d', 0)
                    user_stats[username]['recent_races_30d'] += 1
                    user_stats[username]['recent_points_30d'] += points

                mode = row[4].strip().lower()
                if mode == 'race' and points > user_stats[username]['race_hs']:
                    user_stats[username]['race_hs'] = points
                elif mode == 'br' and points > user_stats[username]['br_hs']:
                    user_stats[username]['br_hs'] = points

        except FileNotFoundError:
            continue
        except Exception:
            logger.error("Error reading season stats from %s", allraces, exc_info=True)

    _, tilt_user_stats = get_tilt_season_stats()
    for username, tilt_stats in tilt_user_stats.items():
        if username not in user_stats:
            user_stats[username] = {
                'display_name': tilt_stats.get('display_name') or username,
                'races': 0,
                'points': 0,
                'race_hs': 0,
                'br_hs': 0,
                'tilt_levels': 0,
                'tilt_top_tiltee': 0,
                'tilt_points': 0,
            }

        user_stats[username]['tilt_levels'] += tilt_stats.get('tilt_levels', 0)
        user_stats[username]['tilt_top_tiltee'] += tilt_stats.get('tilt_top_tiltee', 0)
        user_stats[username]['tilt_points'] += tilt_stats.get('tilt_points', 0)

        if not user_stats[username].get('display_name'):
            user_stats[username]['display_name'] = tilt_stats.get('display_name') or username

    for stats in user_stats.values():
        stats.setdefault('recent_races_30d', 0)
        stats.setdefault('recent_points_30d', 0)

    _user_season_stats_cache['signature'] = signature
    _user_season_stats_cache['value'] = copy.deepcopy(user_stats)
    return user_stats


def get_user_quest_progress(username):
    user_stats = get_user_season_stats()
    if not user_stats:
        return None

    username_lookup = (username or '').strip().lower()
    target_username = None

    if username_lookup in user_stats:
        target_username = username_lookup
    else:
        for uname, stats in user_stats.items():
            if stats.get('display_name', '').strip().lower() == username_lookup:
                target_username = uname
                break

    if target_username is None:
        return None

    targets = get_season_quest_targets()
    stats = user_stats[target_username]
    stat_value_map = {
        'races': stats['races'],
        'points': stats['points'],
        'race_hs': stats['race_hs'],
        'br_hs': stats['br_hs'],
        'tilt_levels': stats.get('tilt_levels', 0),
        'tilt_tops': stats.get('tilt_top_tiltee', 0),
        'tilt_points': stats.get('tilt_points', 0),
    }
    quest_rows = [
        (quest['label'], stat_value_map.get(quest['id'], 0), targets.get(quest['id'], 0))
        for quest in SEASON_QUEST_DEFINITIONS
    ]

    completed = 0
    active_quests = 0
    progress_lines = []
    for quest_name, current, target in quest_rows:
        if target <= 0:
            progress_lines.append(f"{quest_name}: disabled")
            continue
        active_quests += 1
        if current >= target:
            completed += 1
            progress_lines.append(f"{quest_name}: ✅ {current:,}/{target:,}")
        else:
            progress_lines.append(f"{quest_name}: {current:,}/{target:,}")

    return {
        'username': target_username,
        'display_name': stats['display_name'] or target_username,
        'completed': completed,
        'active_quests': active_quests,
        'progress_lines': progress_lines,
        'stats': stats,
    }


def get_quest_completion_leaderboard(limit=100):
    user_stats = get_user_season_stats()
    targets = get_season_quest_targets()

    leaderboard = []
    for username, stats in user_stats.items():
        completed = 0
        active_quests = 0

        checks = [
            ('races', stats['races']),
            ('points', stats['points']),
            ('race_hs', stats['race_hs']),
            ('br_hs', stats['br_hs']),
            ('tilt_levels', stats.get('tilt_levels', 0)),
            ('tilt_tops', stats.get('tilt_top_tiltee', 0)),
            ('tilt_points', stats.get('tilt_points', 0)),
        ]

        for key, current_value in checks:
            target = targets[key]
            if target <= 0:
                continue
            active_quests += 1
            if current_value >= target:
                completed += 1

        if active_quests == 0:
            completed = 0

        leaderboard.append({
            'username': username,
            'display_name': stats['display_name'] or username,
            'completed': completed,
            'active_quests': active_quests,
            'races': stats['races'],
            'points': stats['points'],
            'race_hs': stats['race_hs'],
            'br_hs': stats['br_hs'],
            'tilt_levels': stats.get('tilt_levels', 0),
            'tilt_top_tiltee': stats.get('tilt_top_tiltee', 0),
            'tilt_points': stats.get('tilt_points', 0),
            'recent_points_30d': stats.get('recent_points_30d', 0),
            'recent_races_30d': stats.get('recent_races_30d', 0),
        })

    leaderboard.sort(key=lambda row: (row['completed'], (row['completed'] / row['active_quests']) if row['active_quests'] else 0.0, row.get('recent_points_30d', 0), row['points'], row['races']), reverse=True)
    return leaderboard[:limit]


def get_race_dashboard_leaderboard(limit=250):
    stats_by_user = {}
    data_dir = config.get_setting('directory')
    if not data_dir:
        return []

    for allraces in glob.glob(os.path.join(data_dir, "allraces_*.csv")):
        try:
            with open(allraces, 'rb') as f:
                raw_data = f.read()
            result = chardet.detect(raw_data)
            encoding = result['encoding'] if result['encoding'] else 'utf-8'

            with open(allraces, 'r', encoding=encoding, errors='ignore') as f:
                reader = iter_csv_rows(f)
                for row in reader:
                    if len(row) < 5:
                        continue

                    username = row[1].strip().lower()
                    display_name = row[2].strip() if len(row) > 2 else username
                    if not username:
                        continue

                    mode = row[4].strip().lower()
                    try:
                        points = int(row[3])
                    except (TypeError, ValueError):
                        points = 0

                    if username not in stats_by_user:
                        stats_by_user[username] = {
                            'username': username,
                            'display_name': display_name or username,
                            'race_count': 0,
                            'br_count': 0,
                            'race_points': 0,
                            'br_points': 0,
                            'race_hs': 0,
                            'br_hs': 0,
                        }

                    if display_name:
                        stats_by_user[username]['display_name'] = display_name

                    if mode == 'race':
                        stats_by_user[username]['race_count'] += 1
                        stats_by_user[username]['race_points'] += points
                        if points > stats_by_user[username]['race_hs']:
                            stats_by_user[username]['race_hs'] = points
                    elif mode == 'br':
                        stats_by_user[username]['br_count'] += 1
                        stats_by_user[username]['br_points'] += points
                        if points > stats_by_user[username]['br_hs']:
                            stats_by_user[username]['br_hs'] = points
        except FileNotFoundError:
            continue
        except Exception as e:
            logger.error("Error reading race dashboard data from %s", allraces, exc_info=True)

    leaderboard = []
    for row in stats_by_user.values():
        race_count = int(row.get('race_count', 0))
        br_count = int(row.get('br_count', 0))
        total_events = race_count + br_count
        race_points = int(row.get('race_points', 0))
        br_points = int(row.get('br_points', 0))
        total_points = race_points + br_points

        leaderboard.append({
            **row,
            'total_events': total_events,
            'total_points': total_points,
            'avg_points': round(total_points / total_events, 2) if total_events > 0 else 0,
        })

    leaderboard.sort(
        key=lambda row: (
            row['total_points'],
            row['total_events'],
            row['race_hs'],
            row['br_hs'],
        ),
        reverse=True,
    )
    return leaderboard[:limit]


def get_race_event_totals():
    data_dir = config.get_setting('directory')
    if not data_dir:
        return {
            'race_events': 0,
            'br_events': 0,
            'total_events': 0,
        }

    race_events = 0
    br_events = 0
    for allraces in glob.glob(os.path.join(data_dir, "allraces_*.csv")):
        try:
            with open(allraces, 'rb') as f:
                raw_data = f.read()
            result = chardet.detect(raw_data)
            encoding = result['encoding'] if result['encoding'] else 'utf-8'

            with open(allraces, 'r', encoding=encoding, errors='ignore') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) < 5 or not _is_first_place_row(row):
                        continue
                    mode = (row[4] or '').strip().lower()
                    if mode == 'race':
                        race_events += 1
                    elif mode == 'br':
                        br_events += 1
        except Exception:
            continue

    return {
        'race_events': race_events,
        'br_events': br_events,
        'total_events': race_events + br_events,
    }


def open_quest_completion_window(parent_window):
    leaderboard = get_quest_completion_leaderboard(limit=200)
    if not leaderboard:
        messagebox.showinfo("Season Quests", "No season race data found yet.")
        return

    popup = tk.Toplevel(parent_window)
    popup.title("Season Quest Completion")
    popup.transient(parent_window)
    popup.attributes('-topmost', True)
    center_toplevel(popup, 760, 520)

    ttk.Label(popup, text="Season Quest Completion Leaderboard", style="Small.TLabel").pack(anchor="w", padx=12, pady=(10, 4))

    columns = ("rank", "user", "completed", "races", "points", "race_hs", "br_hs", "tilt_levels", "tilt_tops", "tilt_points")
    tree = ttk.Treeview(popup, columns=columns, show="headings", height=18)
    tree.heading("rank", text="#")
    tree.heading("user", text="User")
    tree.heading("completed", text="Completed")
    tree.heading("races", text="Races")
    tree.heading("points", text="Points")
    tree.heading("race_hs", text="Race HS")
    tree.heading("br_hs", text="BR HS")
    tree.heading("tilt_levels", text="Tilt Lvls")
    tree.heading("tilt_tops", text="Top Tiltees")
    tree.heading("tilt_points", text="Tilt Pts")

    tree.column("rank", width=50, anchor="center")
    tree.column("user", width=190, anchor="w")
    tree.column("completed", width=110, anchor="center")
    tree.column("races", width=90, anchor="e")
    tree.column("points", width=120, anchor="e")
    tree.column("race_hs", width=90, anchor="e")
    tree.column("br_hs", width=90, anchor="e")
    tree.column("tilt_levels", width=90, anchor="e")
    tree.column("tilt_tops", width=100, anchor="e")
    tree.column("tilt_points", width=110, anchor="e")

    for idx, row in enumerate(leaderboard, start=1):
        completed_text = f"{row['completed']}/{row['active_quests']}" if row['active_quests'] > 0 else "0/0"
        tree.insert("", "end", values=(
            idx,
            row['display_name'],
            completed_text,
            f"{row['races']:,}",
            f"{row['points']:,}",
            f"{row['race_hs']:,}",
            f"{row['br_hs']:,}",
            f"{row.get('tilt_levels', 0):,}",
            f"{row.get('tilt_top_tiltee', 0):,}",
            f"{row.get('tilt_points', 0):,}",
        ))

    scrollbar = ttk.Scrollbar(popup, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)

    tree.pack(side="left", fill="both", expand=True, padx=(12, 0), pady=(0, 12))
    scrollbar.pack(side="right", fill="y", padx=(0, 12), pady=(0, 12))


def get_rival_settings():
    min_races = get_int_setting('rivals_min_races', 50)
    max_gap = get_int_setting('rivals_max_point_gap', 1500)
    pair_count = get_int_setting('rivals_pair_count', 25)

    return {
        'min_races': max(1, min(min_races, RIVALS_MAX_MIN_RACES)),
        'max_point_gap': max(0, min(max_gap, RIVALS_MAX_POINT_GAP)),
        'pair_count': max(1, min(pair_count, RIVALS_MAX_PAIRS)),
    }


def _normalize_user_lookup(value):
    clean = unicodedata.normalize('NFKC', str(value or ''))
    clean = re.sub(r'\s+', ' ', clean.strip().lstrip('@')).lower()
    return clean


def resolve_user_in_stats(user_stats, username):
    lookup = _normalize_user_lookup(username)
    if not lookup:
        return None
    if lookup in user_stats:
        return lookup

    matches = []
    for uname, stats in user_stats.items():
        if _normalize_user_lookup(stats.get('display_name', '')) == lookup:
            matches.append(uname)

    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        return {'ambiguous': True, 'matches': matches[:5]}
    return None


def _build_rivalry_row(user_a, stats_a, user_b, stats_b):
    points_a = stats_a.get('points', 0)
    points_b = stats_b.get('points', 0)
    races_a = stats_a.get('races', 0)
    races_b = stats_b.get('races', 0)
    gap = abs(points_a - points_b)
    ppr_a = (points_a / races_a) if races_a else 0.0
    ppr_b = (points_b / races_b) if races_b else 0.0
    ppr_gap = abs(ppr_a - ppr_b)
    race_gap = abs(races_a - races_b)
    recent_gap = abs(stats_a.get('recent_points_30d', 0) - stats_b.get('recent_points_30d', 0))
    trend_delta = gap - recent_gap
    rivalry_score = (100000 - gap) + (5000 - race_gap) + int(max(0, 500 - (ppr_gap * 100))) + int(max(0, trend_delta))

    return {
        'user_a': user_a,
        'display_a': stats_a.get('display_name') or user_a,
        'points_a': points_a,
        'races_a': races_a,
        'recent_points_a_30d': stats_a.get('recent_points_30d', 0),
        'user_b': user_b,
        'display_b': stats_b.get('display_name') or user_b,
        'points_b': points_b,
        'races_b': races_b,
        'recent_points_b_30d': stats_b.get('recent_points_30d', 0),
        'point_gap': gap,
        'race_gap': race_gap,
        'ppr_gap': round(ppr_gap, 4),
        'recent_point_gap_30d': recent_gap,
        'trend_delta_30d': trend_delta,
        'trend_direction': 'closing' if trend_delta > 0 else ('widening' if trend_delta < 0 else 'steady'),
        'rivalry_score': rivalry_score,
    }


def _get_rivals_matrix(user_stats, settings):
    qualified = [
        (username, stats) for username, stats in user_stats.items()
        if stats.get('races', 0) >= settings['min_races'] and stats.get('points', 0) > 0
    ]
    qualified.sort(key=lambda row: row[1].get('points', 0))

    rivalries = []
    for i, (user_a, stats_a) in enumerate(qualified):
        points_a = stats_a.get('points', 0)
        for j in range(i + 1, len(qualified)):
            user_b, stats_b = qualified[j]
            gap = stats_b.get('points', 0) - points_a
            if gap > settings['max_point_gap']:
                break
            rivalries.append(_build_rivalry_row(user_a, stats_a, user_b, stats_b))

    rivalries.sort(key=lambda row: (row['point_gap'], -row['rivalry_score'], -(row['points_a'] + row['points_b'])))

    by_user = defaultdict(list)
    for row in rivalries:
        by_user[row['user_a']].append({
            'username': row['user_b'],
            'display_name': row['display_b'],
            'points': row['points_b'],
            'races': row['races_b'],
            'point_gap': row['point_gap'],
            'rivalry_score': row['rivalry_score'],
            'trend_direction': row['trend_direction'],
            'recent_point_gap_30d': row['recent_point_gap_30d'],
        })
        by_user[row['user_b']].append({
            'username': row['user_a'],
            'display_name': row['display_a'],
            'points': row['points_a'],
            'races': row['races_a'],
            'point_gap': row['point_gap'],
            'rivalry_score': row['rivalry_score'],
            'trend_direction': row['trend_direction'],
            'recent_point_gap_30d': row['recent_point_gap_30d'],
        })

    for user_key in by_user:
        by_user[user_key].sort(key=lambda row: (row['point_gap'], -row['rivalry_score'], -row['points']))

    return {
        'qualified_count': len(qualified),
        'rivalries': rivalries,
        'by_user': by_user,
    }


def _season_stats_fingerprint(user_stats):
    players = len(user_stats)
    races_total = sum(int(row.get('races', 0)) for row in user_stats.values())
    points_total = sum(int(row.get('points', 0)) for row in user_stats.values())
    recent_total = sum(int(row.get('recent_points_30d', 0)) for row in user_stats.values())
    return (players, races_total, points_total, recent_total)


def get_rivals_payload(user_stats=None, settings=None):
    user_stats = user_stats or get_user_season_stats()
    settings = settings or get_rival_settings()
    key = (_season_stats_fingerprint(user_stats), settings['min_races'], settings['max_point_gap'], settings['pair_count'])

    now_ts = time.time()
    if _rivals_cache.get('payload') is not None and _rivals_cache.get('key') == key:
        if (now_ts - float(_rivals_cache.get('created_at', 0.0))) <= RIVALS_CACHE_TTL_S:
            return _rivals_cache['payload']

    payload = _get_rivals_matrix(user_stats, settings)
    _rivals_cache['created_at'] = now_ts
    _rivals_cache['key'] = key
    _rivals_cache['payload'] = payload
    return payload


def _track_rivals_metric(metric_name):
    _rivals_command_metrics[metric_name] += 1


def _is_rivals_command_on_cooldown(author_name):
    now_ts = time.time()
    if (now_ts - _rivals_cooldown_state.get('global_ts', 0.0)) < RIVALS_GLOBAL_COOLDOWN_S:
        return True

    key = _normalize_user_lookup(author_name) or 'unknown'
    user_last = _rivals_cooldown_state['user_ts'].get(key, 0.0)
    if (now_ts - user_last) < RIVALS_USER_COOLDOWN_S:
        return True

    _rivals_cooldown_state['global_ts'] = now_ts
    _rivals_cooldown_state['user_ts'][key] = now_ts
    return False


def _resolve_user_or_error(user_stats, username):
    user_key = resolve_user_in_stats(user_stats, username)
    if isinstance(user_key, dict) and user_key.get('ambiguous'):
        sample = ', '.join(format_user_tag(name) for name in user_key.get('matches', [])[:3])
        return None, f"{format_user_tag(username)} matches multiple users ({sample}). Use exact @handle."
    if user_key is None:
        return None, f"Could not find {format_user_tag(username)} in season stats. Try exact @handle."
    return user_key, None


def get_global_rivalries(limit=None):
    settings = get_rival_settings()
    payload = get_rivals_payload(settings=settings)
    cap = limit if limit is not None else settings['pair_count']
    cap = max(1, min(int(cap), RIVALS_MAX_PAIRS))
    return payload['rivalries'][:cap]


def get_user_rivals(username, limit=5):
    user_stats = get_user_season_stats()
    settings = get_rival_settings()
    user_key = resolve_user_in_stats(user_stats, username)

    if isinstance(user_key, dict) and user_key.get('ambiguous'):
        return {
            'ambiguous': True,
            'matches': user_key.get('matches', []),
        }

    if user_key is None:
        return None

    base = user_stats[user_key]
    if base.get('races', 0) < settings['min_races'] or base.get('points', 0) <= 0:
        return {
            'user': user_key,
            'display_name': base.get('display_name') or user_key,
            'races': base.get('races', 0),
            'points': base.get('points', 0),
            'min_races_required': settings['min_races'],
            'rivals': [],
        }

    payload = get_rivals_payload(user_stats=user_stats, settings=settings)
    rivals = payload['by_user'].get(user_key, [])
    limit = max(1, min(int(limit), RIVALS_MAX_USER_RESULTS))

    return {
        'user': user_key,
        'display_name': base.get('display_name') or user_key,
        'races': base.get('races', 0),
        'points': base.get('points', 0),
        'recent_points_30d': base.get('recent_points_30d', 0),
        'min_races_required': settings['min_races'],
        'rivals': rivals[:limit],
    }


def open_rivalries_window(parent_window):
    rivalries = get_global_rivalries(limit=RIVALS_MAX_PAIRS)
    if not rivalries:
        messagebox.showinfo("Rivals", "No rivalries found with current settings.")
        return

    settings = get_rival_settings()

    popup = tk.Toplevel(parent_window)
    popup.title("Rivalries")
    popup.transient(parent_window)
    popup.attributes('-topmost', True)
    center_toplevel(popup, 940, 560)

    ttk.Label(
        popup,
        text=(
            f"Rivalries Leaderboard • Closest point gaps first • "
            f"Min races: {settings['min_races']:,} • Max gap: {settings['max_point_gap']:,}"
        ),
        style="Small.TLabel"
    ).pack(anchor="w", padx=12, pady=(10, 4))

    columns = ("rank", "player_a", "stats_a", "player_b", "stats_b", "gap")
    tree = ttk.Treeview(popup, columns=columns, show="headings", height=18)
    tree.heading("rank", text="#")
    tree.heading("player_a", text="Player A")
    tree.heading("stats_a", text="A Stats")
    tree.heading("player_b", text="Player B")
    tree.heading("stats_b", text="B Stats")
    tree.heading("gap", text="Gap")

    tree.column("rank", width=45, anchor="center")
    tree.column("player_a", width=180, anchor="w")
    tree.column("stats_a", width=190, anchor="w")
    tree.column("player_b", width=180, anchor="w")
    tree.column("stats_b", width=190, anchor="w")
    tree.column("gap", width=90, anchor="e")

    for idx, row in enumerate(rivalries, start=1):
        tree.insert("", "end", values=(
            idx,
            row['display_a'],
            f"{row['points_a']:,} pts • {row['races_a']:,} races",
            row['display_b'],
            f"{row['points_b']:,} pts • {row['races_b']:,} races",
            f"±{row['point_gap']:,}",
        ))

    scrollbar = ttk.Scrollbar(popup, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)

    tree.pack(side="left", fill="both", expand=True, padx=(12, 0), pady=(0, 12))
    scrollbar.pack(side="right", fill="y", padx=(0, 12), pady=(0, 12))


MYCYCLE_FILE_NAME = "mycycle_data.json"
MYCYCLE_SESSION_PREFIX = "season_"
MYCYCLE_LOCK = threading.Lock()
MYCYCLE_SCHEMA_VERSION = 2
MYCYCLE_HISTORY_MAX = 50
MYCYCLE_SAVE_RETRIES = 3
MYCYCLE_SAVE_RETRY_DELAY_S = 0.15

_dashboard_main_cache = {'value': None, 'created_at': 0.0}
_dashboard_main_cache_ttl_s = 5.0
_mycycle_aggregate_cache = {}
_tilt_season_stats_cache = {'signature': None, 'value': ({'levels': 0, 'top_tiltees': 0, 'points': 0}, {})}
_user_season_stats_cache = {'signature': None, 'value': {}}

RIVALS_MAX_PAIRS = 200
RIVALS_MAX_MIN_RACES = 10000
RIVALS_MAX_POINT_GAP = 50000
RIVALS_MAX_USER_RESULTS = 10
RIVALS_CACHE_TTL_S = 8.0

_rivals_cache = {
    'created_at': 0.0,
    'key': None,
    'payload': None,
}
_rivals_command_metrics = defaultdict(int)
_rivals_cooldown_state = {
    'global_ts': 0.0,
    'user_ts': {},
}
RIVALS_GLOBAL_COOLDOWN_S = 0.75
RIVALS_USER_COOLDOWN_S = 5.0


def _invalidate_dashboard_cache():
    _dashboard_main_cache['value'] = None
    _dashboard_main_cache['created_at'] = 0.0
    _tilt_season_stats_cache['signature'] = None
    _user_season_stats_cache['signature'] = None


def _mycycle_file_path():
    base_dir = config.get_setting('directory') or os.getcwd()
    return os.path.join(base_dir, MYCYCLE_FILE_NAME)


def _empty_placement_counts(min_place, max_place):
    return {str(i): 0 for i in range(min_place, max_place + 1)}


def _normalize_mycycle_username(value):
    return (value or '').strip().lower().lstrip('@')


def _mycycle_leaderboard_sort_key(row):
    cycles = int(row.get('cycles_completed', 0) or 0)
    progress_hits = int(row.get('progress_hits', 0) or 0)
    total_races = int(row.get('total_races', 0) or 0)
    current_cycle_races = int(row.get('current_cycle_races', 0) or 0)
    avg = (total_races / max(1, cycles)) if cycles else float('inf')
    return (-cycles, -progress_hits, avg, current_cycle_races, total_races)


def _mycycle_now_iso(value=None):
    timestamp = value or get_internal_adjusted_time()
    return timestamp.replace(microsecond=0).isoformat()


def _mycycle_now_iso_utc():
    try:
        _, _, _, adjusted_time = time_manager.get_adjusted_time()
        if adjusted_time is not None:
            return _mycycle_now_iso(adjusted_time)
    except Exception:
        logger.error("Falling back to system time for MyCycle timestamp generation.", exc_info=True)
    return _mycycle_now_iso(get_internal_adjusted_time())


def _parse_mycycle_timestamp(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value

    text = str(value).strip()
    if not text:
        return None

    def _coerce_naive_utc(parsed_dt):
        if parsed_dt is None:
            return None
        if parsed_dt.tzinfo is None:
            return parsed_dt
        return parsed_dt.astimezone(timezone.utc).replace(tzinfo=None)

    for fmt in ('%Y-%m-%d %H:%M:%S',):
        try:
            return _coerce_naive_utc(datetime.strptime(text, fmt))
        except (TypeError, ValueError):
            continue

    try:
        normalized = text.replace('Z', '+00:00')
        return _coerce_naive_utc(datetime.fromisoformat(normalized))
    except (TypeError, ValueError):
        return None


def get_mycycle_settings():
    min_place = max(1, get_int_setting('mycycle_min_place', 1))
    max_place = max(1, get_int_setting('mycycle_max_place', 10))
    if min_place > max_place:
        min_place, max_place = 1, 10
    return {
        'enabled': is_chat_response_enabled('mycycle_enabled'),
        'announce': is_chat_response_enabled('mycycle_announcements_enabled'),
        'include_br': is_chat_response_enabled('mycycle_include_br'),
        'min_place': min_place,
        'max_place': max_place,
    }


def load_mycycle_data():
    path = _mycycle_file_path()
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {'version': MYCYCLE_SCHEMA_VERSION, 'sessions': {}}
    except json.JSONDecodeError:
        try:
            backup_path = f"{path}.corrupt.{int(time.time())}.bak"
            os.replace(path, backup_path)
            logger.error("MyCycle data was corrupted and has been moved to backup: %s", backup_path)
        except Exception:
            logger.error("MyCycle data was corrupted and could not be backed up.", exc_info=True)
        data = {'version': MYCYCLE_SCHEMA_VERSION, 'sessions': {}}

    if not isinstance(data, dict):
        data = {'version': MYCYCLE_SCHEMA_VERSION, 'sessions': {}}
    changed = False
    if data.get('version') != MYCYCLE_SCHEMA_VERSION:
        changed = True
    data.setdefault('version', MYCYCLE_SCHEMA_VERSION)
    data.setdefault('sessions', {})

    sessions = data.get('sessions', {}) if isinstance(data.get('sessions', {}), dict) else {}
    data['sessions'] = sessions
    for sid, session in list(sessions.items()):
        if not isinstance(session, dict):
            sessions[sid] = {'id': sid, 'name': str(sid), 'active': True, 'is_default': False, 'stats': {}}
            session = sessions[sid]
            changed = True

        session.setdefault('id', sid)
        session.setdefault('name', str(sid))
        session.setdefault('active', True)
        session.setdefault('is_default', False)
        if 'stats' not in session and isinstance(session.get('users'), dict):
            session['stats'] = session.get('users', {})
            changed = True
        stats = session.setdefault('stats', {})
        if not isinstance(stats, dict):
            session['stats'] = {}
            stats = session['stats']
            changed = True

        normalized = {}
        for username, record in list(stats.items()):
            uname = _normalize_mycycle_username(username)
            if not uname:
                changed = True
                continue
            if not isinstance(record, dict):
                record = {}
                changed = True
            record.setdefault('display_name', uname)
            record.setdefault('history', [])
            if 'cycle_history' in record and not record.get('history'):
                record['history'] = record.get('cycle_history')
                changed = True
            normalized[uname] = record
            if uname != username:
                changed = True
        if normalized != stats:
            session['stats'] = normalized
            changed = True

    data['version'] = MYCYCLE_SCHEMA_VERSION
    data['_changed'] = changed
    return data


def save_mycycle_data(data):
    path = _mycycle_file_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temp_file = f"{path}.tmp"
    payload = dict(data or {})
    payload.pop('_changed', None)
    with open(temp_file, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2)
    for attempt in range(MYCYCLE_SAVE_RETRIES):
        try:
            os.replace(temp_file, path)
            return
        except OSError:
            if attempt >= MYCYCLE_SAVE_RETRIES - 1:
                raise
            time.sleep(MYCYCLE_SAVE_RETRY_DELAY_S)


def ensure_default_mycycle_session(data):
    season = str(config.get_setting('season') or 'unknown')
    session_id = f"{MYCYCLE_SESSION_PREFIX}{season}"
    now_text = _mycycle_now_iso_utc()
    sessions = data.setdefault('sessions', {})
    changed = False
    if session_id not in sessions:
        sessions[session_id] = {
            'id': session_id,
            'name': f"Season {season}",
            'season': season,
            'active': True,
            'is_default': True,
            'created_at': now_text,
            'created_by': 'system',
            'stats': {},
        }
        changed = True

    primary_session_id = config.get_setting('mycycle_primary_session_id')
    if (not primary_session_id or
            (str(primary_session_id).startswith(MYCYCLE_SESSION_PREFIX) and primary_session_id != session_id)):
        config.set_setting('mycycle_primary_session_id', session_id, persistent=True)
    return session_id, changed


def get_mycycle_sessions(include_inactive=True):
    with MYCYCLE_LOCK:
        data = load_mycycle_data()
        migrated = bool(data.pop('_changed', False))
        default_id, changed = ensure_default_mycycle_session(data)
        if changed or migrated:
            save_mycycle_data(data)
    sessions = list(data.get('sessions', {}).values())

    def _session_sort_key(session):
        created_at = session.get('created_at') or ""
        created_dt = _parse_mycycle_timestamp(created_at) or datetime.min
        return created_dt

    sessions.sort(key=_session_sort_key, reverse=True)
    if include_inactive:
        return sessions, default_id
    return [s for s in sessions if s.get('active', True)], default_id




def _get_mycycle_home_session_ids():
    active_sessions, default_session_id = get_mycycle_sessions(include_inactive=False)
    session_ids = [session['id'] for session in active_sessions]

    if not session_ids:
        return [], None

    preferred_session_id = config.get_setting('mycycle_primary_session_id') or default_session_id
    if preferred_session_id not in session_ids:
        preferred_session_id = session_ids[0]

    ordered_session_ids = [preferred_session_id] + [sid for sid in session_ids if sid != preferred_session_id]
    return ordered_session_ids, preferred_session_id

def create_mycycle_session(session_name, created_by='streamer'):
    with MYCYCLE_LOCK:
        data = load_mycycle_data()
        _ = data.pop('_changed', False)
        _, _ = ensure_default_mycycle_session(data)
        now_text = _mycycle_now_iso_utc()
        season = str(config.get_setting('season') or 'unknown')
        session_id = f"custom_{uuid.uuid4().hex[:8]}"
        data['sessions'][session_id] = {
            'id': session_id,
            'name': session_name.strip(),
            'season': season,
            'active': True,
            'is_default': False,
            'created_at': now_text,
            'created_by': created_by,
            'stats': {},
        }
        save_mycycle_data(data)
        _invalidate_dashboard_cache()
    return session_id


def delete_mycycle_session(session_id):
    with MYCYCLE_LOCK:
        data = load_mycycle_data()
        _ = data.pop('_changed', False)
        target = data.get('sessions', {}).get(session_id)
        if not target:
            return False, "Session not found."
        if target.get('is_default'):
            return False, "Default season sessions cannot be deleted."

        del data['sessions'][session_id]

        primary_session_id = config.get_setting('mycycle_primary_session_id')
        if primary_session_id == session_id:
            fallback_id, _ = ensure_default_mycycle_session(data)
            config.set_setting('mycycle_primary_session_id', fallback_id, persistent=True)

        save_mycycle_data(data)
        _invalidate_dashboard_cache()
    return True, "Deleted"


def _resolve_session_id(data):
    primary_id = config.get_setting('mycycle_primary_session_id')
    sessions = data.get('sessions', {})
    if primary_id and primary_id in sessions:
        return primary_id, False
    fallback_id, changed = ensure_default_mycycle_session(data)
    return fallback_id, changed


def _resolve_user_in_session(session_stats, username):
    lookup = _normalize_mycycle_username(username)
    if not lookup:
        return None
    if lookup in session_stats:
        return lookup
    for uname, stats in session_stats.items():
        if (stats.get('display_name') or '').strip().lower() == lookup:
            return uname
    return None


def _ensure_user_cycle_record(session, username, display_name, min_place, max_place):
    stats = session.setdefault('stats', {})
    user_record = stats.get(username)
    if user_record is None:
        user_record = {
            'display_name': display_name or username,
            'placements': _empty_placement_counts(min_place, max_place),
            'current_hits': [],
            'cycles_completed': 0,
            'total_races': 0,
            'race_races': 0,
            'br_races': 0,
            'current_cycle_races': 0,
            'current_cycle_race_races': 0,
            'current_cycle_br_races': 0,
            'last_cycle_races': 0,
            'fastest_cycle_races': 0,
            'slowest_cycle_races': 0,
            'last_cycle_completed_at': None,
            'history': [],
        }
        stats[username] = user_record

    user_record.setdefault('placements', _empty_placement_counts(min_place, max_place))
    for i in range(min_place, max_place + 1):
        user_record['placements'].setdefault(str(i), 0)
    user_record.setdefault('current_hits', [])
    user_record.setdefault('cycles_completed', 0)
    user_record.setdefault('total_races', 0)
    user_record.setdefault('race_races', 0)
    user_record.setdefault('br_races', 0)
    user_record.setdefault('current_cycle_races', 0)
    user_record.setdefault('current_cycle_race_races', 0)
    user_record.setdefault('current_cycle_br_races', 0)
    user_record.setdefault('last_cycle_races', 0)
    user_record.setdefault('fastest_cycle_races', 0)
    user_record.setdefault('slowest_cycle_races', 0)
    user_record.setdefault('last_cycle_completed_at', None)
    user_record.setdefault('history', [])

    if display_name:
        user_record['display_name'] = display_name
    return user_record


def update_mycycle_with_race_rows(racedata):
    settings = get_mycycle_settings()
    if not settings['enabled']:
        return []

    completion_events = []
    with MYCYCLE_LOCK:
        data = load_mycycle_data()
        migrated = bool(data.pop('_changed', False))
        _, changed = ensure_default_mycycle_session(data)
        changed = changed or migrated
        session_id, resolved_changed = _resolve_session_id(data)
        changed = changed or resolved_changed
        session = data.get('sessions', {}).get(session_id)

        if session is None or not session.get('active', True):
            if changed:
                save_mycycle_data(data)
            return completion_events

        for row in racedata:
            if len(row) < 5:
                continue
            race_type = row[4]
            if race_type != 'Race' and not (settings['include_br'] and race_type == 'BR'):
                continue

            username = _normalize_mycycle_username(row[1] if len(row) > 1 else '')
            if not username:
                continue

            try:
                placement = int(row[0])
            except (TypeError, ValueError):
                continue

            display_name = (row[2] or '').strip() if len(row) > 2 else username
            user_record = _ensure_user_cycle_record(session, username, display_name, settings['min_place'], settings['max_place'])

            user_record['total_races'] += 1
            user_record['current_cycle_races'] += 1
            if race_type == 'BR':
                user_record['br_races'] += 1
                user_record['current_cycle_br_races'] += 1
            else:
                user_record['race_races'] += 1
                user_record['current_cycle_race_races'] += 1

            if placement < settings['min_place'] or placement > settings['max_place']:
                continue

            user_record['placements'][str(placement)] += 1

            hits = set(user_record.get('current_hits', []))
            hits.add(placement)
            user_record['current_hits'] = sorted(hits)

            unique_needed = settings['max_place'] - settings['min_place'] + 1
            if len(hits) >= unique_needed:
                completed_in_races = user_record['current_cycle_races']
                user_record['cycles_completed'] += 1
                user_record['last_cycle_races'] = completed_in_races
                fastest = int(user_record.get('fastest_cycle_races', 0) or 0)
                slowest = int(user_record.get('slowest_cycle_races', 0) or 0)
                if fastest <= 0 or completed_in_races < fastest:
                    user_record['fastest_cycle_races'] = completed_in_races
                if slowest <= 0 or completed_in_races > slowest:
                    user_record['slowest_cycle_races'] = completed_in_races
                user_record['last_cycle_completed_at'] = _mycycle_now_iso_utc()
                history = user_record.get('history') if isinstance(user_record.get('history'), list) else []
                history.append({
                    'completed_at': user_record['last_cycle_completed_at'],
                    'races_used': completed_in_races,
                    'race_races': int(user_record.get('current_cycle_race_races', 0) or 0),
                    'br_races': int(user_record.get('current_cycle_br_races', 0) or 0),
                    'session_id': session.get('id'),
                })
                user_record['history'] = history[-MYCYCLE_HISTORY_MAX:]
                completion_events.append({
                    'session_name': session.get('name', 'Unknown Session'),
                    'username': username,
                    'display_name': user_record.get('display_name') or username,
                    'cycles_completed': user_record['cycles_completed'],
                    'races_used': user_record['last_cycle_races'],
                })
                user_record['current_hits'] = []
                user_record['current_cycle_races'] = 0
                user_record['current_cycle_race_races'] = 0
                user_record['current_cycle_br_races'] = 0

        save_mycycle_data(data)
        _invalidate_dashboard_cache()
    return completion_events


def get_mycycle_progress(username=None, session_id=None):
    with MYCYCLE_LOCK:
        data = load_mycycle_data()
        migrated = bool(data.pop('_changed', False))
        changed = False
        if session_id in data.get('sessions', {}):
            resolved_session_id = session_id
        else:
            resolved_session_id, changed = _resolve_session_id(data)
        if changed or migrated:
            save_mycycle_data(data)

    session = data['sessions'].get(resolved_session_id, {})
    stats = session.get('stats', {})
    target_user = _resolve_user_in_session(stats, username) if username else None
    return session, stats, target_user


def _format_mycycle_placement_marks(hits, placement_range):
    marks = [f"{place}{'✅' if place in hits else '❌'}" for place in placement_range]
    if len(marks) <= 10:
        return " ".join(marks), ""

    midpoint = math.ceil(len(marks) / 2)
    return " ".join(marks[:midpoint]), " ".join(marks[midpoint:])


def get_mycycle_leaderboard(limit=200, session_id=None):
    session, stats, _ = get_mycycle_progress(session_id=session_id)
    leaderboard = []
    settings = get_mycycle_settings()
    placement_range = list(range(settings['min_place'], settings['max_place'] + 1))
    for username, row in stats.items():
        hits = {int(p) for p in row.get('current_hits', []) if isinstance(p, int) or str(p).isdigit()}
        missing_places = [place for place in placement_range if place not in hits]
        marks_top, marks_bottom = _format_mycycle_placement_marks(hits, placement_range)
        progress_total = settings['max_place'] - settings['min_place'] + 1
        progress_hits = len(hits)
        completed_at = row.get('last_cycle_completed_at')
        completed_dt = _parse_mycycle_timestamp(completed_at)
        leaderboard.append({
            'username': username,
            'display_name': row.get('display_name') or username,
            'cycles_completed': int(row.get('cycles_completed', 0)),
            'progress_hits': progress_hits,
            'progress_total': progress_total,
            'progress_percent': round((progress_hits / progress_total) * 100, 1) if progress_total > 0 else 0.0,
            'progress_marks_top': marks_top,
            'progress_marks_bottom': marks_bottom,
            'placement_hits': sorted(hits),
            'missing_places': missing_places,
            'current_cycle_races': int(row.get('current_cycle_races', 0)),
            'current_cycle_race_races': int(row.get('current_cycle_race_races', 0)),
            'current_cycle_br_races': int(row.get('current_cycle_br_races', 0)),
            'last_cycle_races': int(row.get('last_cycle_races', 0)),
            'total_races': int(row.get('total_races', 0)),
            'race_races': int(row.get('race_races', 0)),
            'br_races': int(row.get('br_races', 0)),
            'last_cycle_completed_at': completed_at,
            'last_cycle_completed_at_iso': completed_dt.isoformat() if completed_dt else None,
            'last_cycle_completed_at_epoch': int(completed_dt.timestamp()) if completed_dt else None,
        })
    leaderboard.sort(key=_mycycle_leaderboard_sort_key)
    return session, leaderboard[:limit]


def get_next_mycycle_candidates(limit=10, session_id=None):
    session, leaderboard = get_mycycle_leaderboard(limit=5000, session_id=session_id)
    candidates = []

    for row in leaderboard:
        missing_places = list(row.get('missing_places', []))
        if not missing_places:
            continue

        candidates.append({
            'display_name': row.get('display_name') or row.get('username') or 'Unknown',
            'next_cycle_number': int(row.get('cycles_completed', 0) or 0) + 1,
            'missing_positions': missing_places,
            'missing_count': len(missing_places),
            'current_cycle_races': int(row.get('current_cycle_races', 0) or 0),
            'progress_hits': int(row.get('progress_hits', 0) or 0),
        })

    candidates.sort(
        key=lambda row: (
            row['missing_count'],
            -row['current_cycle_races'],
            -row['progress_hits'],
            row['display_name'].lower(),
        )
    )
    return session, candidates[:max(1, limit)]


def get_mycycle_cycle_stats(session_query=None):
    with MYCYCLE_LOCK:
        data = load_mycycle_data()
        migrated = bool(data.pop('_changed', False))
        default_id, changed = ensure_default_mycycle_session(data)
        if changed or migrated:
            save_mycycle_data(data)

    sessions = data.get('sessions', {})
    selected_session_ids = []
    label = ""

    if session_query:
        query = session_query.strip().lower()
        if query == "all":
            selected_session_ids = [sid for sid, session in sessions.items() if session.get('active', True)]
            label = "Active Sessions"
        else:
            for sid, session in sessions.items():
                if session.get('name', '').strip().lower() == query or sid.lower() == query:
                    selected_session_ids = [sid]
                    label = session.get('name', sid)
                    break
    else:
        selected_session_ids = [sid for sid, session in sessions.items() if session.get('active', True)]
        if not selected_session_ids and default_id in sessions:
            selected_session_ids = [default_id]
        label = "Global Active Sessions"

    if not selected_session_ids:
        return None

    cycle_settings = get_mycycle_settings()
    progress_total = max(1, cycle_settings['max_place'] - cycle_settings['min_place'] + 1)

    fastest = None
    slowest = None
    completed_cycles_total = 0
    racers_with_cycles = set()
    total_races_for_cycled = 0
    cycle_rate_leader = None
    near_cycle_leader = None
    consistency_leader = None

    for sid in selected_session_ids:
        session = sessions.get(sid, {})
        stats = session.get('stats', {})
        for username, record in stats.items():
            cycles_completed = int(record.get('cycles_completed', 0) or 0)
            completed_cycles_total += cycles_completed
            total_races = int(record.get('total_races', 0) or 0)
            progress_hits = len(set(record.get('current_hits', [])))
            current_cycle_races = int(record.get('current_cycle_races', 0) or 0)

            display_name = record.get('display_name') or username

            near_row = {
                'name': display_name,
                'hits': progress_hits,
                'needed': progress_total,
                'races': current_cycle_races,
            }
            if near_cycle_leader is None or (near_row['hits'], -near_row['races']) > (near_cycle_leader['hits'], -near_cycle_leader['races']):
                near_cycle_leader = near_row

            if cycles_completed <= 0:
                continue

            racers_with_cycles.add(f"{sid}:{username}")
            total_races_for_cycled += total_races

            fastest_races = int(record.get('fastest_cycle_races', 0) or 0)
            if fastest_races <= 0:
                fastest_races = int(record.get('last_cycle_races', 0) or 0)

            slowest_races = int(record.get('slowest_cycle_races', 0) or 0)
            if slowest_races <= 0:
                slowest_races = int(record.get('last_cycle_races', 0) or 0)

            if fastest_races > 0:
                row = {
                    'name': display_name,
                    'races': fastest_races,
                    'session_name': session.get('name', sid),
                }
                if fastest is None or row['races'] < fastest['races']:
                    fastest = row

            if slowest_races > 0:
                row = {
                    'name': display_name,
                    'races': slowest_races,
                    'session_name': session.get('name', sid),
                }
                if slowest is None or row['races'] > slowest['races']:
                    slowest = row

            if total_races > 0:
                rate = (cycles_completed / total_races) * 100.0
                rate_row = {
                    'name': display_name,
                    'rate': rate,
                    'cycles': cycles_completed,
                }
                if cycle_rate_leader is None or rate_row['rate'] > cycle_rate_leader['rate']:
                    cycle_rate_leader = rate_row

            if cycles_completed >= 2 and fastest_races > 0 and slowest_races > 0:
                spread = slowest_races - fastest_races
                consistency_row = {
                    'name': display_name,
                    'spread': spread,
                    'cycles': cycles_completed,
                }
                if consistency_leader is None or consistency_row['spread'] < consistency_leader['spread']:
                    consistency_leader = consistency_row

    avg_races_per_cycle = 0.0
    if completed_cycles_total > 0 and total_races_for_cycled > 0:
        avg_races_per_cycle = total_races_for_cycled / completed_cycles_total

    return {
        'label': label,
        'session_count': len(selected_session_ids),
        'cycles_total': completed_cycles_total,
        'racers_with_cycles': len(racers_with_cycles),
        'fastest': fastest,
        'slowest': slowest,
        'avg_races_per_cycle': avg_races_per_cycle,
        'cycle_rate_leader': cycle_rate_leader,
        'near_cycle_leader': near_cycle_leader,
        'consistency_leader': consistency_leader,
    }


def get_next_cyclestats_metric_key():
    metric_keys = [
        'avg_races_per_cycle',
        'cycle_rate_leader',
        'near_cycle_leader',
        'consistency_leader',
    ]

    try:
        current_index = int(config.get_setting('mycycle_cyclestats_rotation_index') or 0)
    except (TypeError, ValueError):
        current_index = 0

    key = metric_keys[current_index % len(metric_keys)]
    next_index = (current_index + 1) % len(metric_keys)
    config.set_setting('mycycle_cyclestats_rotation_index', str(next_index), persistent=True)
    return key


def format_rotating_cyclestats_metric(metric_key, stats):
    if metric_key == 'avg_races_per_cycle':
        if stats.get('cycles_total', 0) <= 0:
            return "AvgCycle: n/a"
        return f"AvgCycle: {stats.get('avg_races_per_cycle', 0.0):.1f} races"

    if metric_key == 'cycle_rate_leader':
        leader = stats.get('cycle_rate_leader')
        if not leader:
            return "BestRate: n/a"
        return f"BestRate: {leader['name']} {leader['rate']:.2f}/100r"

    if metric_key == 'near_cycle_leader':
        leader = stats.get('near_cycle_leader')
        if not leader:
            return "NearCycle: n/a"
        return f"NearCycle: {leader['name']} {leader['hits']}/{leader['needed']}"

    if metric_key == 'consistency_leader':
        leader = stats.get('consistency_leader')
        if not leader:
            return "Consistency: n/a"
        return f"Consistency: {leader['name']} ±{leader['spread']}r"

    return "Extra: n/a"


def open_mycycle_leaderboard_window(parent_window, initial_session_id=None):
    active_sessions, default_session_id = get_mycycle_sessions(include_inactive=False)
    if not active_sessions:
        messagebox.showinfo("MyCycle", "No active MyCycle sessions found.")
        return

    session_ids = [session['id'] for session in active_sessions]
    primary_session_id = config.get_setting('mycycle_primary_session_id') or default_session_id
    initial_id = initial_session_id if initial_session_id in session_ids else primary_session_id
    current_index = session_ids.index(initial_id) if initial_id in session_ids else 0

    popup = tk.Toplevel(parent_window)
    popup.title("MyCycle Leaderboard")
    popup.transient(parent_window)
    popup.attributes('-topmost', True)
    center_toplevel(popup, 1320, 600)

    top_bar = ttk.Frame(popup, style="App.TFrame")
    top_bar.pack(fill="x", padx=12, pady=(8, 4))

    session_label_var = tk.StringVar(value="")
    ttk.Label(top_bar, textvariable=session_label_var, style="Small.TLabel").pack(side="left")

    nav_frame = ttk.Frame(top_bar, style="App.TFrame")
    nav_frame.pack(side="right")

    columns = ("rank", "user", "cycles", "progress", "placements_line1", "placements_line2", "cycle_races", "last_cycle")
    leaderboard_tree_style = "MyCycleLeaderboard.Treeview"
    app_style.configure(leaderboard_tree_style, rowheight=30)
    app_style.configure(f"{leaderboard_tree_style}.Heading", padding=(8, 14))
    tree = ttk.Treeview(popup, columns=columns, show="headings", height=22, style=leaderboard_tree_style)
    leaderboard_settings = get_mycycle_settings()
    show_second_placement_line = leaderboard_settings['max_place'] - leaderboard_settings['min_place'] + 1 > 10

    for col, text in (("rank", "#"), ("user", "User"), ("cycles", "Cycles"), ("progress", "Current\nProgress"), ("placements_line1", "Placements\n(1/2)"), ("placements_line2", "Placements\n(2/2)" if show_second_placement_line else ""), ("cycle_races", "Races in\nCurrent Cycle"), ("last_cycle", "Races in Last\nCompleted Cycle")):
        tree.heading(col, text=text)

    tree.column("rank", width=50, anchor="center")
    tree.column("user", width=170, anchor="w")
    tree.column("cycles", width=70, anchor="center")
    tree.column("progress", width=120, anchor="center")
    tree.column("placements_line1", width=330, anchor="w")
    tree.column("placements_line2", width=330 if show_second_placement_line else 0, anchor="w", stretch=show_second_placement_line)
    tree.column("cycle_races", width=140, anchor="center")
    tree.column("last_cycle", width=180, anchor="center")

    def render_session_by_index(index):
        session_id = session_ids[index]
        session, leaderboard = get_mycycle_leaderboard(limit=500, session_id=session_id)
        session_label_var.set(f"Session {index + 1}/{len(session_ids)}: {session.get('name', 'Unknown')}")

        tree.delete(*tree.get_children())
        if not leaderboard:
            tree.insert("", "end", values=("", "No race data for this session yet.", "", "", "", "", "", ""))
            return

        for idx, row in enumerate(leaderboard, start=1):
            tree.insert("", "end", values=(
                idx,
                row['display_name'],
                row['cycles_completed'],
                f"{row['progress_hits']}/{row['progress_total']}",
                row['progress_marks_top'],
                row['progress_marks_bottom'] if show_second_placement_line else "",
                row['current_cycle_races'],
                row['last_cycle_races'],
            ))

    def shift_session(delta):
        nonlocal current_index
        current_index = (current_index + delta) % len(session_ids)
        render_session_by_index(current_index)

    ttk.Button(nav_frame, text="◀ Prev Session", command=lambda: shift_session(-1)).pack(side="left", padx=(0, 6))
    ttk.Button(nav_frame, text="Next Session ▶", command=lambda: shift_session(1)).pack(side="left")

    scrollbar = ttk.Scrollbar(popup, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    tree.pack(side="left", fill="both", expand=True, padx=(12, 0), pady=(0, 12))
    scrollbar.pack(side="right", fill="y", padx=(0, 12), pady=(0, 12))

    render_session_by_index(current_index)


async def send_chat_message(channel, message, category=None, apply_delay=False):
    category_map = {
        "br": "chat_br_results",
        "race": "chat_race_results",
        "tilt": "chat_tilt_results",
        "mystats": "chat_all_commands",
    }

    if category in category_map and not is_chat_response_enabled(category_map[category]):
        return False

    if apply_delay and config.get_setting('announcedelay') == 'True':
        try:
            await asyncio.sleep(int(config.get_setting('announcedelayseconds') or 0))
        except ValueError:
            await asyncio.sleep(0)

    try:
        await channel.send(translate_chat_message(message))
        logger.info("Chat message sent (category=%s)", category)
        return True
    except Exception as e:
        logger.exception(f"Failed to send chat message ({category}): {e}")
        return False


def center_toplevel(window, width, height):
    """Center a Toplevel against the main root window."""
    root.update_idletasks()
    root_x = root.winfo_x()
    root_y = root.winfo_y()
    root_width = root.winfo_width()
    root_height = root.winfo_height()
    pos_x = root_x + (root_width // 2) - (width // 2)
    pos_y = root_y + (root_height // 2) - (height // 2)
    window.geometry(f"{width}x{height}+{pos_x}+{pos_y}")

def build_stats_labels(parent):
    labels = {
        "total_points": ttk.Label(parent, text="Total Points: 0"),
        "total_count": ttk.Label(parent, text="Total Count: 0"),
        "avg_points": ttk.Label(parent, text="Avg Points: 0"),
        "race_hs": ttk.Label(parent, text="Race HS: 0"),
        "br_hs": ttk.Label(parent, text="BR HS: 0"),
    }
    for label in labels.values():
        label.pack(anchor='w')
    return labels


def is_already_running():
    global GLOBAL_SOCKET
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Attempt to bind to localhost:9999
        sock.bind(('127.0.0.1', 9999))
        GLOBAL_SOCKET = sock
        return False  # Bind succeeded -> no other instance
    except OSError:
        return True   # Bind failed -> another instance must be holding this port

def is_mystats_running():
    if is_already_running():
        # Another instance is detected
        root = tk.Tk()
        root.title("MyStats Already Running")

        label = tk.Label(
            root, 
            text="MyStats is currently running.\n"
                 "Please close the other instance before continuing.",
            padx=20, pady=10
        )
        label.pack()

        def on_close():
            root.destroy()
            sys.exit(0)  # End the script entirely

        close_button = tk.Button(root, text="Close", command=on_close)
        close_button.pack(pady=10)

        root.protocol("WM_DELETE_WINDOW", on_close)
        root.mainloop()
    else:
        pass

is_mystats_running()

# Redirect print statements to Tkinter Text widget
class PrintRedirector:
    def __init__(self, widget):
        self.widget = widget

    def write(self, message):
        # Filter out Flask startup messages
        if "Serving Flask app" in message or "Debug mode" in message:
            return  # Ignore these messages

        if self.widget and self.widget.winfo_exists():
            self.widget.insert(tk.END, message)
            self.widget.see(tk.END)
        else:
            sys.__stdout__.write(message)

    def flush(self):
        pass


# Flask server setup
app = Flask(__name__)
oauth_token = None
def _overlay_dir_candidates():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(script_dir, "obs_overlay"),
        os.path.join(os.getcwd(), "obs_overlay"),
    ]

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.insert(0, os.path.join(meipass, "obs_overlay"))

    return candidates


def _resolve_overlay_dir():
    for candidate in _overlay_dir_candidates():
        if os.path.isdir(candidate):
            return candidate
    return _overlay_dir_candidates()[0]


OVERLAY_DIR = _resolve_overlay_dir()


def _dashboard_dir_candidates():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(script_dir, "modern_dashboard"),
        os.path.join(os.getcwd(), "modern_dashboard"),
    ]

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.insert(0, os.path.join(meipass, "modern_dashboard"))

    return candidates


def _readme_file_candidates():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(script_dir, "README.html"),
        os.path.join(os.getcwd(), "README.html"),
    ]

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.insert(0, os.path.join(meipass, "README.html"))

    return candidates


def _resolve_dashboard_dir():
    for candidate in _dashboard_dir_candidates():
        if os.path.isdir(candidate):
            return candidate
    return _dashboard_dir_candidates()[0]


DASHBOARD_DIR = _resolve_dashboard_dir()

# Twitch App Credentials
CLIENT_ID = 'icdintxz5c3h9twd6v3rntautv2o9g'
CLIENT_SECRET = 'qxyur2g933mst8uwaqzzto98t9zuwl'
def _get_redirect_uri():
    return f"http://localhost:{_load_overlay_server_port()}/callback"


# Function to start Flask server
def _load_overlay_server_port(default_port=5000):
    settings_path = SETTINGS_FILE_PATH
    try:
        with open(settings_path, 'r', encoding='utf-8', errors='ignore') as settings_file:
            for raw_line in settings_file:
                line = raw_line.strip()
                if not line or '=' not in line:
                    continue
                key, value = line.split('=', 1)
                if key.strip() == 'overlay_server_port':
                    value = value.strip()
                    if value.isdigit():
                        parsed = int(value)
                        if 1 <= parsed <= 65535:
                            return parsed
                    break
    except FileNotFoundError:
        pass
    return default_port


def run_flask():
    app.run(host='0.0.0.0', port=_load_overlay_server_port(), debug=False, use_reloader=False)


def _find_latest_overlay_results_file(data_dir):
    files = sorted(glob.glob(os.path.join(data_dir, "allraces_*.csv")))
    return files[-1] if files else None


def _safe_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def normalize_overlay_mode(value):
    mode = str(value or '').strip().lower()
    if mode in ('pre-game', 'race', 'br', 'tilt', 'post-race'):
        return mode
    return 'race'


def set_overlay_mode(mode):
    config.set_setting('overlay_active_mode', normalize_overlay_mode(mode), persistent=False)


def get_overlay_mode():
    configured_mode = normalize_overlay_mode(config.get_setting('overlay_active_mode'))
    current_run_id = str(config.get_setting('tilt_current_run_id') or '').strip()
    # Treat tilt as active only when both a run id is present and tilt is still the
    # configured mode. This prevents stale run ids from pinning /overlay to tilt
    # after race/BR handlers explicitly switch modes.
    if current_run_id and configured_mode == 'tilt':
        return 'tilt'
    return configured_mode


def _is_first_place_row(row):
    if not row:
        return False
    placement_text = (row[0] or '').strip()
    placement_digits = ''.join(ch for ch in placement_text if ch.isdigit())
    return _safe_int(placement_digits) == 1


def _build_overlay_header_stats(data_dir):
    season_points = 0
    season_entries = 0
    season_races = 0
    season_unique = set()

    for allraces in glob.glob(os.path.join(data_dir, "allraces_*.csv")):
        try:
            with open(allraces, 'r', encoding='utf-8', errors='ignore') as f:
                for row in iter_csv_rows(f):
                    if len(row) < 5:
                        continue
                    racer = (row[2] or '').strip() or (row[1] or '').strip()
                    if racer:
                        season_unique.add(racer.lower())
                    points = _safe_int(row[3])
                    if points == 0:
                        continue
                    if not racer:
                        continue
                    season_points += points
                    season_entries += 1
                    if _is_first_place_row(row):
                        season_races += 1
        except Exception:
            continue

    today_points = 0
    today_entries = 0
    today_races = 0
    today_unique = set()
    today_br_points = 0
    today_br_entries = 0
    today_br_unique = set()
    today_brs = 0
    today_file = config.get_setting('allraces_file')
    if today_file:
        try:
            with open(today_file, 'r', encoding='utf-8', errors='ignore') as f:
                for row in iter_csv_rows(f):
                    if len(row) < 5:
                        continue
                    racer = (row[2] or '').strip() or (row[1] or '').strip()
                    if racer:
                        today_unique.add(racer.lower())
                    points = _safe_int(row[3])
                    if points == 0:
                        continue
                    if not racer:
                        continue
                    race_mode = str(row[4] or '').strip().lower()
                    today_points += points
                    today_entries += 1
                    if _is_first_place_row(row):
                        today_races += 1
                    if race_mode == 'br':
                        today_br_points += points
                        today_br_entries += 1
                        today_br_unique.add(racer.lower())
                        if _is_first_place_row(row):
                            today_brs += 1
        except Exception:
            pass

    return {
        'avg_points_today': round((today_points / today_entries), 2) if today_entries else 0,
        'avg_points_season': round((season_points / season_entries), 2) if season_entries else 0,
        'unique_racers_today': len(today_unique),
        'unique_racers_season': len(season_unique),
        'total_races_today': today_races,
        'total_races_season': season_races,
        'br_avg_points_today': round((today_br_points / today_br_entries), 2) if today_br_entries else 0,
        'br_racers_today': len(today_br_unique),
        'total_brs_today': today_brs,
    }


def _build_overlay_settings_payload():
    return {
        'rotation_seconds': _safe_int(config.get_setting('overlay_rotation_seconds') or 10) or 10,
        'refresh_seconds': _safe_int(config.get_setting('overlay_refresh_seconds') or 3) or 3,
        'theme': (config.get_setting('overlay_theme') or 'midnight').strip().lower(),
        'card_opacity': _safe_int(config.get_setting('overlay_card_opacity') or 84) or 84,
        'text_scale': _safe_int(config.get_setting('overlay_text_scale') or 100) or 100,
        'show_medals': str(config.get_setting('overlay_show_medals') or 'True'),
        'compact_rows': str(config.get_setting('overlay_compact_rows') or 'False'),
        'horizontal_layout': str(config.get_setting('overlay_horizontal_layout') or 'False'),
        'horizontal_feed_season': str(config.get_setting('overlay_horizontal_feed_season') or 'True'),
        'horizontal_feed_today': str(config.get_setting('overlay_horizontal_feed_today') or 'True'),
        'horizontal_feed_races_season': str(config.get_setting('overlay_horizontal_feed_races_season') or 'True'),
        'horizontal_feed_brs_season': str(config.get_setting('overlay_horizontal_feed_brs_season') or 'True'),
        'horizontal_feed_races_today': str(config.get_setting('overlay_horizontal_feed_races_today') or 'True'),
        'horizontal_feed_brs_today': str(config.get_setting('overlay_horizontal_feed_brs_today') or 'True'),
        'horizontal_feed_myteams': str(config.get_setting('overlay_horizontal_feed_myteams') or 'True'),
        'horizontal_feed_previous_race': str(config.get_setting('overlay_horizontal_feed_previous_race') or 'True'),
        'horizontal_feed_events': str(config.get_setting('overlay_horizontal_feed_events') or 'True'),
        'horizontal_feed_tilt_current': str(config.get_setting('overlay_horizontal_feed_tilt_current') or 'True'),
        'horizontal_feed_tilt_today': str(config.get_setting('overlay_horizontal_feed_tilt_today') or 'True'),
        'horizontal_feed_tilt_season': str(config.get_setting('overlay_horizontal_feed_tilt_season') or 'True'),
        'horizontal_feed_tilt_last_run': str(config.get_setting('overlay_horizontal_feed_tilt_last_run') or 'True'),
        'tilt_theme': (config.get_setting('tilt_overlay_theme') or config.get_setting('overlay_theme') or 'midnight').strip().lower(),
        'tilt_scroll_step_px': _safe_int(config.get_setting('tilt_scroll_step_px') or 1) or 1,
        'tilt_scroll_interval_ms': _safe_int(config.get_setting('tilt_scroll_interval_ms') or 40) or 40,
        'tilt_scroll_pause_ms': _safe_int(config.get_setting('tilt_scroll_pause_ms') or 900) or 900,
        'language': get_ui_language(),
    }


def _parse_overlay_timestamp(value):
    if not value:
        return None

    value = str(value).strip()
    if not value:
        return None

    for fmt in ('%Y-%m-%d %H:%M:%S', '%m/%d/%Y %H:%M:%S', '%Y-%m-%dT%H:%M:%S'):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        pass

    if value.endswith('Z'):
        try:
            return datetime.fromisoformat(value[:-1] + '+00:00')
        except ValueError:
            pass

    return None


def _overlay_now_for_timestamp(race_time):
    """Return a comparable now() for naive or timezone-aware timestamps."""
    internal_now = get_internal_adjusted_time()
    if race_time is None:
        return internal_now
    if race_time.tzinfo is None:
        return internal_now.replace(tzinfo=None)
    return internal_now.astimezone(race_time.tzinfo)


def _overlay_display_name(*candidates):
    """Return the first usable display name candidate, or a safe fallback."""
    invalid_tokens = {'', 'unknown', 'none', 'null', 'undefined', 'n/a', 'na'}
    for candidate in candidates:
        name = str(candidate or '').strip()
        if not name:
            continue
        if name.lower() in invalid_tokens:
            continue
        return name
    return 'Unknown Racer'


def _overlay_points_top10(file_paths):
    return _overlay_points_top10_filtered(file_paths)


def _overlay_points_top10_filtered(file_paths, race_type_filter=None):
    totals = {}

    for file_path in file_paths:
        if not file_path:
            continue
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for row in iter_csv_rows(f):
                    if len(row) < 5:
                        continue
                    race_type = (row[4] or '').strip().lower() if len(row) >= 5 else ''
                    if race_type_filter and race_type != str(race_type_filter).strip().lower():
                        continue
                    name = _overlay_display_name(row[2], row[1])
                    if not name:
                        continue
                    points = _safe_int(row[3])
                    if points <= 0:
                        continue
                    totals[name] = totals.get(name, 0) + points
        except Exception:
            continue

    ranked = sorted(totals.items(), key=lambda item: (-item[1], item[0].lower()))[:10]
    return [
        {'placement': index + 1, 'name': name, 'points': points}
        for index, (name, points) in enumerate(ranked)
    ]


def _overlay_event_log():
    raw = str(config.get_setting('overlay_event_log') or '[]')
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return parsed
    except Exception:
        pass
    return []


def enqueue_overlay_event(event_type, message):
    now_iso = get_internal_now_iso(timespec='seconds')
    next_id = _safe_int(config.get_setting('overlay_event_counter') or 0) + 1
    config.set_setting('overlay_event_counter', str(next_id), persistent=False)

    events = _overlay_event_log()
    events.append({
        'id': next_id,
        'type': str(event_type or 'event').strip().lower(),
        'message': str(message or '').strip(),
        'created_at': now_iso,
    })
    config.set_setting('overlay_event_log', json.dumps(events[-40:]), persistent=False)


def _overlay_data_sources(data_dir):
    season_files = sorted(glob.glob(os.path.join(data_dir, 'allraces_*.csv')))
    today_file = config.get_setting('allraces_file')

    if today_file and os.path.isfile(today_file):
        if today_file not in season_files:
            season_files.append(today_file)
        return season_files, today_file

    latest_file = _find_latest_overlay_results_file(data_dir)
    if latest_file and os.path.isfile(latest_file):
        if latest_file not in season_files:
            season_files.append(latest_file)
        return season_files, latest_file

    return season_files, None


def _overlay_recent_race_payload(race_file):
    if not race_file:
        return {
            'rows': [],
            'top3_rows': [],
            'race_key': None,
            'race_type': None,
            'race_timestamp': None,
            'is_recent': False,
            'is_record_race': False,
            'record_holder_name': None,
            'record_delta_seconds': 0.0,
        }

    race_groups = []
    groups_by_key = {}

    try:
        with open(race_file, 'r', encoding='utf-8', errors='ignore') as f:
            for row in iter_csv_rows(f):
                if len(row) < 4:
                    continue

                placement_text = (row[0] or '').strip()
                placement_digits = ''.join(ch for ch in placement_text if ch.isdigit())
                placement = _safe_int(placement_digits)
                if placement <= 0:
                    continue

                race_id = (row[10] if len(row) >= 11 else '').strip()
                race_timestamp = (row[5] or '').strip()
                race_type = (row[4] or '').strip()
                race_key = f"{race_id}|{race_timestamp}|{race_type}".strip('|')
                if not race_key:
                    race_key = race_timestamp or race_type or f"race-{len(race_groups) + 1}"

                if race_key not in groups_by_key:
                    groups_by_key[race_key] = {
                        'race_key': race_key,
                        'race_timestamp': race_timestamp,
                        'race_type': race_type,
                        'parsed_ts': _parse_overlay_timestamp(race_timestamp),
                        'rows': [],
                        'is_record_race': False,
                        'record_holder_name': None,
                        'record_delta_seconds': 0.0,
                    }
                    race_groups.append(groups_by_key[race_key])

                is_record_row = len(row) > 11 and str(row[11]).strip() == '1'
                if is_record_row:
                    groups_by_key[race_key]['is_record_race'] = True
                    groups_by_key[race_key]['record_holder_name'] = _overlay_display_name(row[2], row[1])
                    try:
                        groups_by_key[race_key]['record_delta_seconds'] = max(0.0, float((row[8] if len(row) > 8 else 0) or 0))
                    except (TypeError, ValueError):
                        groups_by_key[race_key]['record_delta_seconds'] = 0.0

                groups_by_key[race_key]['rows'].append({
                    'placement': placement,
                    'name': _overlay_display_name(row[2], row[1]),
                    'points': _safe_int(row[3]),
                    'finished': not (len(row) >= 8 and str(row[7]).strip().lower() == 'true'),
                })
    except Exception:
        return {
            'rows': [],
            'top3_rows': [],
            'race_key': None,
            'race_type': None,
            'race_timestamp': None,
            'is_recent': False,
            'is_record_race': False,
            'record_holder_name': None,
            'record_delta_seconds': 0.0,
        }

    if not race_groups:
        return {
            'rows': [],
            'top3_rows': [],
            'race_key': None,
            'race_type': None,
            'race_timestamp': None,
            'is_recent': False,
            'is_record_race': False,
            'record_holder_name': None,
            'record_delta_seconds': 0.0,
        }

    latest_group = race_groups[-1]
    latest_rows = sorted(latest_group['rows'], key=lambda r: r['placement'])
    top10_rows = latest_rows[:10]
    top3_rows = [row for row in latest_rows if row.get('finished', True)][:3]

    race_time = latest_group['parsed_ts']
    is_recent = False
    if race_time:
        try:
            is_recent = (_overlay_now_for_timestamp(race_time) - race_time).total_seconds() <= 600
        except Exception:
            is_recent = False
    elif os.path.isfile(race_file):
        try:
            is_recent = (_overlay_now_for_timestamp(None) - datetime.fromtimestamp(os.path.getmtime(race_file))).total_seconds() <= 600
        except Exception:
            is_recent = False

    return {
        'rows': top10_rows,
        'top3_rows': top3_rows,
        'race_key': latest_group['race_key'],
        'race_type': latest_group['race_type'] or None,
        'race_timestamp': latest_group['race_timestamp'] or None,
        'is_recent': is_recent,
        'is_record_race': latest_group['is_record_race'],
        'record_holder_name': latest_group['record_holder_name'],
        'record_delta_seconds': latest_group['record_delta_seconds'],
    }


def _build_overlay_top3_payload():
    data_dir = config.get_setting('directory') or os.getcwd()
    season_files, today_file = _overlay_data_sources(data_dir)
    recent_race = _overlay_recent_race_payload(today_file)

    views = [
        {
            'id': 'season',
            'title': 'Top 10 Season',
            'rows': _overlay_points_top10_filtered(season_files),
        },
        {
            'id': 'today',
            'title': 'Top 10 Today',
            'rows': _overlay_points_top10_filtered([today_file]),
        },
        {
            'id': 'races-season',
            'title': 'Top 10 Races (Season)',
            'rows': _overlay_points_top10_filtered(season_files, race_type_filter='race'),
        },
        {
            'id': 'brs-season',
            'title': 'Top 10 BRs (Season)',
            'rows': _overlay_points_top10_filtered(season_files, race_type_filter='br'),
        },
        {
            'id': 'races-today',
            'title': 'Top 10 Races (Today)',
            'rows': _overlay_points_top10_filtered([today_file], race_type_filter='race'),
        },
        {
            'id': 'brs-today',
            'title': 'Top 10 BRs (Today)',
            'rows': _overlay_points_top10_filtered([today_file], race_type_filter='br'),
        },
    ]

    team_top_today = _build_team_leaderboard_rows(window='daily', limit=10)
    team_top_season = _build_team_leaderboard_rows(window='season', limit=10)
    if team_top_today:
        views.append({
            'id': 'teams-today',
            'title': 'Top MyTeams Today',
            'rows': team_top_today,
        })
    if team_top_season:
        views.append({
            'id': 'teams-season',
            'title': 'Top MyTeams Season',
            'rows': team_top_season,
        })

    if recent_race['rows']:
        views.append({
            'id': 'previous',
            'title': 'Top 10 Previous Race',
            'rows': recent_race['rows'],
            'is_record_race': recent_race['is_record_race'],
        })

    return {
        'updated_at': get_internal_now_iso(timespec='seconds'),
        'title': 'MyStats Live Results',
        'views': views,
        'recent_race_top3': {
            'title': 'Top 3 Latest Race',
            'rows': recent_race['top3_rows'],
            'race_key': recent_race['race_key'],
            'race_type': recent_race['race_type'],
            'race_timestamp': recent_race['race_timestamp'],
            'is_recent': recent_race['is_recent'],
            'is_record_race': recent_race['is_record_race'],
            'record_holder_name': recent_race['record_holder_name'],
            'record_delta_seconds': recent_race['record_delta_seconds'],
        },
        'header_stats': _build_overlay_header_stats(data_dir),
        'settings': _build_overlay_settings_payload(),
        'overlay_events': _overlay_event_log(),
    }




def _build_tilt_overlay_payload():
    def parse_json_setting(setting_key, default):
        raw = config.get_setting(setting_key)
        if not raw:
            return default
        try:
            parsed = json.loads(raw)
            return parsed
        except Exception:
            return default

    run_ledger = parse_json_setting('tilt_run_ledger', {})
    if not isinstance(run_ledger, dict):
        run_ledger = {}

    run_deaths_ledger = parse_json_setting('tilt_run_deaths_ledger', {})
    if not isinstance(run_deaths_ledger, dict):
        run_deaths_ledger = {}

    def build_tilt_today_standings():
        directory = config.get_setting('directory')
        if not directory:
            return []

        todays_file = os.path.join(directory, f"tilts_{get_internal_adjusted_time().strftime('%Y-%m-%d')}.csv")
        if not os.path.isfile(todays_file):
            return []

        totals = {}
        try:
            with open(todays_file, 'rb') as f:
                raw_data = f.read()
            result = chardet.detect(raw_data)
            encoding = result['encoding'] if result and result.get('encoding') else 'utf-8'

            with open(todays_file, 'r', encoding=encoding, errors='ignore') as f:
                for row in iter_csv_rows(f):
                    detail = parse_tilt_result_detail(row)
                    if detail is None:
                        continue
                    username = str(detail.get('username') or '').strip().lower()
                    if not username:
                        continue
                    if username not in totals:
                        totals[username] = {
                            'name': str(detail.get('username') or username).strip() or username,
                            'points': 0,
                            'deaths': 0,
                        }
                    totals[username]['points'] += _safe_int(detail.get('points', 0))
        except Exception:
            return []

        ranked = sorted(
            totals.values(),
            key=lambda row: (-_safe_int(row.get('points', 0)), str(row.get('name', '')).lower()),
        )[:10]

        return [
            {
                'name': row.get('name') or 'Unknown',
                'points': _safe_int(row.get('points', 0)),
                'deaths': _safe_int(row.get('deaths', 0)),
            }
            for row in ranked
        ]

    sorted_run = sorted(
        (
            (str(name), _safe_int(points))
            for name, points in run_ledger.items()
            if _safe_int(points) > 0
        ),
        key=lambda item: item[1],
        reverse=True
    )

    _, tilt_user_stats = get_tilt_season_stats()
    season_standings = sorted(
        (
            {
                'name': (stats.get('display_name') or username),
                'points': _safe_int(stats.get('tilt_points', 0)),
                'deaths': _safe_int(stats.get('tilt_deaths', 0)),
                'levels': _safe_int(stats.get('tilt_levels', 0)),
                'top_tiltee': _safe_int(stats.get('tilt_top_tiltee', 0)),
            }
            for username, stats in tilt_user_stats.items()
            if _safe_int(stats.get('tilt_points', 0)) > 0
        ),
        key=lambda row: row['points'],
        reverse=True,
    )[:10]

    current_run_id = str(config.get_setting('tilt_current_run_id') or '').strip()
    current_level = get_int_setting('tilt_current_level', 0)
    current_elapsed = str(config.get_setting('tilt_current_elapsed') or '0:00')
    current_top_tiltee = str(config.get_setting('tilt_current_top_tiltee') or 'None')
    current_top_tiltee_count = get_int_setting('tilt_current_top_tiltee_count', 0)

    last_run_summary = parse_json_setting('tilt_last_run_summary', {})
    if not isinstance(last_run_summary, dict):
        last_run_summary = {}

    display_standings = sorted_run
    if not current_run_id and not display_standings:
        fallback = last_run_summary.get('standings')
        if isinstance(fallback, list):
            display_standings = [
                (
                    str(item.get('name') or 'Unknown'),
                    _safe_int(item.get('points', 0)),
                    _safe_int(item.get('deaths', item.get('death_count', item.get('run_deaths', 0)))),
                )
                for item in fallback if isinstance(item, dict)
            ]

    current_summary = {
        'run_id': current_run_id,
        'run_short_id': current_run_id[:6] if current_run_id else '',
        'status': 'active' if current_run_id else 'idle',
        'level': current_level,
        'elapsed_time': current_elapsed,
        'top_tiltee': current_top_tiltee,
        'top_tiltee_count': current_top_tiltee_count,
        'run_points': get_int_setting('tilt_run_points', 0),
        'run_deaths': get_int_setting('tilt_run_deaths_total', 0),
        'run_xp': get_int_setting('tilt_run_xp', 0),
        'run_expertise': get_int_setting('tilt_run_xp', 0),
        'best_run_xp_today': get_int_setting('tilt_best_run_xp_today', 0),
        'total_xp_today': get_int_setting('tilt_total_xp_today', 0),
        'total_deaths_today': get_int_setting('tilt_total_deaths_today', 0),
        'lifetime_expertise': get_int_setting('tilt_lifetime_expertise', 0),
        'leader': {'name': display_standings[0][0], 'points': display_standings[0][1]} if display_standings else None,
        'standings': [
            {
                'name': name,
                'points': points,
                'deaths': _safe_int(deaths if len(entry) > 2 else run_deaths_ledger.get(name, 0)),
            }
            for entry in display_standings
            for name, points, deaths in [(
                str(entry[0]) if isinstance(entry, (list, tuple)) and len(entry) > 0 else 'Unknown',
                _safe_int(entry[1]) if isinstance(entry, (list, tuple)) and len(entry) > 1 else 0,
                _safe_int(entry[2]) if isinstance(entry, (list, tuple)) and len(entry) > 2 else 0,
            )]
        ],
    }

    level_completion = parse_json_setting('tilt_level_completion_overlay', {})
    if not isinstance(level_completion, dict):
        level_completion = {}

    run_completion = parse_json_setting('tilt_run_completion_overlay', {})
    if not isinstance(run_completion, dict):
        run_completion = {}

    run_completion_event_id = get_int_setting('tilt_run_completion_event_id', 0)

    settings_payload = _build_overlay_settings_payload()
    settings_payload['theme'] = settings_payload.get('tilt_theme') or settings_payload.get('theme') or 'midnight'

    payload = {
        'updated_at': get_internal_now_iso(timespec='seconds'),
        'title': 'MyStats Tilt Run Tracker',
        'settings': settings_payload,
        'current_run': current_summary,
        'last_run': last_run_summary,
        'level_completion': level_completion,
        'run_completion': run_completion,
        'run_completion_event_id': run_completion_event_id,
        'season_standings': season_standings,
        'today_standings': build_tilt_today_standings(),
        'suppress_initial_recaps': True,
    }
    return payload


def _derive_overlay_active_mode(top3_payload=None):
    active_mode = get_overlay_mode()
    if active_mode == 'tilt':
        return active_mode

    payload = top3_payload if isinstance(top3_payload, dict) else _build_overlay_top3_payload()
    recent_race = payload.get('recent_race_top3') or {}
    has_rows = bool(recent_race.get('rows'))
    race_type = str(recent_race.get('race_type') or '').strip().lower()
    is_recent = bool(recent_race.get('is_recent'))

    if not has_rows:
        return 'pre-game'
    if is_recent and race_type in ('br', 'battle royale', 'royale'):
        return 'br'
    if is_recent:
        return 'race'
    return 'post-race'


def _build_unified_overlay_payload():
    top3_payload = _build_overlay_top3_payload()
    return {
        'updated_at': get_internal_now_iso(timespec='seconds'),
        'active_mode': _derive_overlay_active_mode(top3_payload),
        'top3': top3_payload,
        'tilt': _build_tilt_overlay_payload(),
    }


@app.route('/overlay')
def overlay_page():
    horizontal_layout_enabled = str(config.get_setting('overlay_horizontal_layout') or 'False') == 'True'
    overlay_file = 'index.html' if horizontal_layout_enabled else ('tilt.html' if get_overlay_mode() == 'tilt' else 'index.html')

    for candidate in _overlay_dir_candidates():
        index_file = os.path.join(candidate, overlay_file)
        if os.path.isfile(index_file):
            return send_from_directory(candidate, overlay_file)

    return (f"Overlay files not found. Checked: {', '.join(_overlay_dir_candidates())}", 404)


@app.route('/overlay/tilt')
def overlay_tilt_page():
    return (
        "for tilt overlay, use /overlay instead. Tilt overlay will appear after first completed level.",
        200,
        {'Content-Type': 'text/plain; charset=utf-8'},
    )


@app.route('/overlay/<path:filename>')
def overlay_assets(filename):
    for candidate in _overlay_dir_candidates():
        asset_file = os.path.join(candidate, filename)
        if os.path.isfile(asset_file):
            return send_from_directory(candidate, filename)

    return (f"Overlay asset not found: {filename}", 404)


@app.route('/api/overlay/settings')
def overlay_settings():
    return jsonify(_build_overlay_settings_payload())

@app.route('/api/overlay/top3')
def overlay_top3():
    payload = _build_overlay_top3_payload()
    payload['active_mode'] = _derive_overlay_active_mode(payload)
    return jsonify(payload)


@app.route('/api/overlay/tilt')
def overlay_tilt_payload():
    payload = _build_tilt_overlay_payload()
    payload['active_mode'] = _derive_overlay_active_mode()
    return jsonify(payload)


@app.route('/api/overlay')
def overlay_unified_payload():
    return jsonify(_build_unified_overlay_payload())


@app.route('/api/overlay/stream')
def overlay_stream_payload():
    return _make_sse_response(_build_unified_overlay_payload)


def _build_main_dashboard_payload():
    now_ts = time.time()
    cached = _dashboard_main_cache.get('value')
    if cached is not None and (now_ts - float(_dashboard_main_cache.get('created_at', 0.0))) <= _dashboard_main_cache_ttl_s:
        return cached

    mycycle_session_ids, _ = _get_mycycle_home_session_ids()
    active_session_id = mycycle_session_ids[0] if mycycle_session_ids else None
    mycycle_session, mycycle_rows = get_mycycle_leaderboard(limit=250, session_id=active_session_id)

    season_quest_rows = get_quest_completion_leaderboard(limit=100)
    season_quest_targets = get_season_quest_targets()
    tilt_totals, tilt_users = get_tilt_season_stats()
    tilt_leaderboard_rows = sorted(
        [
            {
                'username': str(username or '').strip().lower(),
                'display_name': str((stats or {}).get('display_name') or username or '').strip(),
                'tilt_levels': _safe_int((stats or {}).get('tilt_levels', 0)),
                'tilt_points': _safe_int((stats or {}).get('tilt_points', 0)),
                'tilt_top_tiltee': _safe_int((stats or {}).get('tilt_top_tiltee', (stats or {}).get('tilt_tops', 0))),
                'tilt_tops': _safe_int((stats or {}).get('tilt_tops', (stats or {}).get('tilt_top_tiltee', 0))),
                'tilt_deaths': _safe_int((stats or {}).get('tilt_deaths', 0)),
            }
            for username, stats in (tilt_users or {}).items()
            if _safe_int((stats or {}).get('tilt_levels', 0)) > 0 or _safe_int((stats or {}).get('tilt_points', 0)) > 0
        ],
        key=lambda row: (
            _safe_int(row.get('tilt_points', 0)),
            _safe_int(row.get('tilt_top_tiltee', 0)),
            -_safe_int(row.get('tilt_deaths', 0)),
            str(row.get('display_name') or row.get('username') or '').lower(),
        ),
        reverse=True,
    )
    analytics_payload = _build_dashboard_analytics_payload(mycycle_rows, tilt_totals, tilt_users)
    race_trends_payload = _build_dashboard_race_trends_payload()

    payload = {
        'updated_at': get_internal_now_iso(timespec='seconds'),
        'season_quests': {
            'rows': season_quest_rows,
            'targets': season_quest_targets,
        },
        'rivals': get_global_rivalries(limit=RIVALS_MAX_PAIRS),
        'races': get_race_dashboard_leaderboard(limit=250),
        'race_totals': get_race_event_totals(),
        'teams': {
            'top_daily': _build_team_leaderboard_rows(window='daily', limit=100),
            'top_weekly': _build_team_leaderboard_rows(window='weekly', limit=100),
            'top_season': _build_team_leaderboard_rows(window='season', limit=100),
        },
        'mycycle': {
            'session': mycycle_session or {},
            'rows': mycycle_rows,
            'settings': get_mycycle_settings(),
        },
        'tilt': {
            'totals': tilt_totals,
            'deaths_today': get_int_setting('tilt_total_deaths_today', 0),
            'participants': len(tilt_users),
            'leaderboard': tilt_leaderboard_rows,
        },
        'settings': {
            'language': get_ui_language(),
            'rivals': get_rival_settings(),
            'rivals_limits': {
                'max_pairs': RIVALS_MAX_PAIRS,
                'max_min_races': RIVALS_MAX_MIN_RACES,
                'max_point_gap': RIVALS_MAX_POINT_GAP,
                'max_user_results': RIVALS_MAX_USER_RESULTS,
            },
        },
        'analytics': analytics_payload,
        'race_trends': race_trends_payload,
    }
    _dashboard_main_cache['value'] = payload
    _dashboard_main_cache['created_at'] = now_ts
    return payload


def _collect_results_season_directories(current_dir):
    current = os.path.abspath(current_dir or '')
    if not current or not os.path.isdir(current):
        return [], False

    def has_allraces_csv(path):
        return bool(glob.glob(os.path.join(path, 'allraces_*.csv')))

    discovered = []
    parent = os.path.dirname(current)
    if parent and os.path.isdir(parent):
        for name in sorted(os.listdir(parent)):
            candidate = os.path.join(parent, name)
            if os.path.isdir(candidate) and has_allraces_csv(candidate):
                discovered.append(candidate)

    if current not in discovered and has_allraces_csv(current):
        discovered.append(current)

    if not discovered:
        nested = [
            os.path.join(current, name)
            for name in sorted(os.listdir(current))
            if os.path.isdir(os.path.join(current, name)) and has_allraces_csv(os.path.join(current, name))
        ]
        if nested:
            discovered = nested

    normalized = []
    for item in discovered:
        abspath = os.path.abspath(item)
        if abspath not in normalized:
            normalized.append(abspath)

    has_prior = len(normalized) > 1
    return normalized, has_prior


def _safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _aggregate_mode_from_directories(directories):
    mode_template = {
        'events': 0,
        'race_events': set(),
        'points': 0,
        'wins': 0,
        'high_score': 0,
        'unique_racers': set(),
        'users': defaultdict(lambda: {'events': 0, 'points': 0}),
    }
    mode_stats = {
        'combined': copy.deepcopy(mode_template),
        'race': copy.deepcopy(mode_template),
        'br': copy.deepcopy(mode_template),
    }

    for directory in directories:
        for allraces_file in glob.glob(os.path.join(directory, 'allraces_*.csv')):
            try:
                with open(allraces_file, 'r', encoding='utf-8', errors='ignore') as f:
                    reader = iter_csv_rows(f)
                    for row in reader:
                        if len(row) < 5:
                            continue

                        mode = str(row[4] or '').strip().lower()
                        if mode not in ('race', 'br'):
                            continue

                        username = str(row[1] or '').strip().lower()
                        display_name = str(row[2] or '').strip() or username
                        if not username:
                            continue

                        points = _safe_int(row[3])
                        place_digits = ''.join(ch for ch in str(row[0] or '') if ch.isdigit())
                        placement = _safe_int(place_digits)
                        race_id = str(row[10] or '').strip() if len(row) > 10 else ''
                        race_ts = str(row[5] or '').strip() if len(row) > 5 else ''
                        race_event_key = f"{mode}|{race_id}|{race_ts}" if (race_id or race_ts) else None

                        for key in ('combined', mode):
                            bucket = mode_stats[key]
                            bucket['events'] += 1
                            if race_event_key:
                                bucket['race_events'].add(race_event_key)
                            bucket['points'] += points
                            bucket['high_score'] = max(bucket['high_score'], points)
                            if placement == 1:
                                bucket['wins'] += 1
                            bucket['unique_racers'].add(display_name or username)
                            bucket['users'][username]['events'] += 1
                            bucket['users'][username]['points'] += points
            except Exception:
                continue

    def finalize(bucket):
        events = int(bucket['events'])
        points = int(bucket['points'])
        wins = int(bucket['wins'])
        high_score = int(bucket['high_score'])
        race_events = len(bucket['race_events'])
        unique_racers = len(bucket['unique_racers'])
        ppr = round((points / events), 2) if events else 0.0
        win_rate = round((wins / events) * 100, 2) if events else 0.0

        best_name = '—'
        best_ppr = 0.0
        best_events = 0
        for username, user_stats in bucket['users'].items():
            user_events = int(user_stats['events'])
            if user_events < 25:
                continue
            user_ppr = _safe_float(user_stats['points']) / max(1, user_events)
            if user_ppr > best_ppr:
                best_ppr = user_ppr
                best_name = username
                best_events = user_events

        return {
            'events': events,
            'race_events': race_events if race_events else events,
            'points': points,
            'wins': wins,
            'win_rate': win_rate,
            'high_score': high_score,
            'unique_racers': unique_racers,
            'ppr': ppr,
            'top_ppr_name': best_name,
            'top_ppr': round(best_ppr, 2),
            'top_ppr_events': best_events,
        }

    return {key: finalize(value) for key, value in mode_stats.items()}


def _aggregate_tilt_from_directories(directories):
    totals = {'points': 0, 'levels': 0, 'top_tiltee': 0, 'deaths': 0}
    users = set()

    for directory in directories:
        for tilt_file in glob.glob(os.path.join(directory, 'tilts_*.csv')):
            try:
                with open(tilt_file, 'r', encoding='utf-8', errors='ignore') as f:
                    for row in iter_csv_rows(f):
                        detail = parse_tilt_result_detail(row)
                        if not detail:
                            continue
                        users.add(detail.get('display_name') or detail.get('username') or 'unknown')
                        totals['points'] += _safe_int(detail.get('points', 0))
                        totals['levels'] += 1
                        if detail.get('is_top_tiltee'):
                            totals['top_tiltee'] += 1
            except Exception:
                continue

    totals['deaths'] = max(0, int(totals['levels']) - int(totals['top_tiltee']))
    totals['participants'] = len(users)
    totals['ppr'] = round((totals['points'] / totals['levels']), 2) if totals['levels'] else 0.0
    totals['survival_rate'] = round(((totals['levels'] - totals['deaths']) / totals['levels']) * 100, 2) if totals['levels'] else 0.0
    return totals


def _aggregate_mycycle_from_directories(directories):
    cache_key_parts = []
    for directory in directories:
        cycle_file = os.path.join(directory, MYCYCLE_FILE_NAME)
        try:
            mtime = os.path.getmtime(cycle_file)
        except OSError:
            mtime = None
        cache_key_parts.append((os.path.abspath(directory), mtime))
    cache_key = tuple(cache_key_parts)
    cached = _mycycle_aggregate_cache.get(cache_key)
    if cached is not None:
        return copy.deepcopy(cached)

    totals = {'tracked_racers': 0, 'cycles_completed': 0, 'near_complete': 0, 'current_cycle_races': 0}

    for directory in directories:
        cycle_file = os.path.join(directory, MYCYCLE_FILE_NAME)
        if not os.path.isfile(cycle_file):
            continue
        try:
            with open(cycle_file, 'r', encoding='utf-8') as f:
                payload = json.load(f)
            sessions = payload.get('sessions') if isinstance(payload, dict) else {}
            merged_users = {}
            if isinstance(sessions, dict):
                for session in sessions.values():
                    users = {}
                    if isinstance(session, dict):
                        users = session.get('stats') or session.get('users') or {}
                    if not isinstance(users, dict):
                        continue
                    for username, row in users.items():
                        if username not in merged_users:
                            merged_users[username] = {'cycles_completed': 0, 'progress_total': 0, 'progress_hits': 0, 'current_cycle_races': 0}
                        merged_users[username]['cycles_completed'] += _safe_int(row.get('cycles_completed', 0))
                        merged_users[username]['progress_total'] = max(_safe_int(row.get('progress_total', 0)), merged_users[username]['progress_total'])
                        merged_users[username]['progress_hits'] = max(_safe_int(row.get('progress_hits', 0)), merged_users[username]['progress_hits'])
                        merged_users[username]['current_cycle_races'] += _safe_int(row.get('current_cycle_races', 0))

            totals['tracked_racers'] += len(merged_users)
            totals['cycles_completed'] += sum(_safe_int(row.get('cycles_completed', 0)) for row in merged_users.values())
            totals['near_complete'] += sum(1 for row in merged_users.values() if (_safe_int(row.get('progress_total', 0)) - _safe_int(row.get('progress_hits', 0))) <= 2)
            totals['current_cycle_races'] += sum(_safe_int(row.get('current_cycle_races', 0)) for row in merged_users.values())
        except Exception:
            continue

    _mycycle_aggregate_cache.clear()
    _mycycle_aggregate_cache[cache_key] = copy.deepcopy(totals)
    return totals


def _build_dashboard_analytics_payload(mycycle_rows, tilt_totals, tilt_users):
    current_dir = config.get_setting('directory') or os.getcwd()
    season_dirs, has_prior = _collect_results_season_directories(current_dir)
    current_only_dirs = [os.path.abspath(current_dir)] if os.path.isdir(current_dir) else []
    all_dirs = season_dirs if season_dirs else current_only_dirs

    season_modes = _aggregate_mode_from_directories(current_only_dirs)
    all_modes = _aggregate_mode_from_directories(all_dirs) if has_prior else None

    tilt_season = {
        'participants': len(tilt_users or {}),
        'points': _safe_int((tilt_totals or {}).get('points', 0)),
        'levels': _safe_int((tilt_totals or {}).get('levels', 0)),
        'top_tiltee': _safe_int((tilt_totals or {}).get('top_tiltee', 0)),
    }
    tilt_season['deaths'] = max(0, tilt_season['levels'] - tilt_season['top_tiltee'])
    tilt_season['ppr'] = round((tilt_season['points'] / tilt_season['levels']), 2) if tilt_season['levels'] else 0.0
    tilt_season['survival_rate'] = round(((tilt_season['levels'] - tilt_season['deaths']) / tilt_season['levels']) * 100, 2) if tilt_season['levels'] else 0.0

    mycycle_season = {
        'tracked_racers': len(mycycle_rows or []),
        'cycles_completed': sum(_safe_int(row.get('cycles_completed', 0)) for row in (mycycle_rows or [])),
        'near_complete': sum(1 for row in (mycycle_rows or []) if (_safe_int(row.get('progress_total', 0)) - _safe_int(row.get('progress_hits', 0))) <= 2),
        'current_cycle_races': sum(_safe_int(row.get('current_cycle_races', 0)) for row in (mycycle_rows or [])),
    }

    return {
        'season_label': f"Season {config.get_setting('season') or 'Current'}",
        'all_seasons_label': 'All Seasons',
        'has_prior_seasons': has_prior,
        'groups': {
            'race_br_combined': {
                'title': 'Race/BR Combined',
                'season': season_modes.get('combined', {}),
                'all_seasons': all_modes.get('combined', {}) if all_modes else None,
            },
            'tilt': {
                'title': 'Tilt',
                'season': tilt_season,
                'all_seasons': _aggregate_tilt_from_directories(all_dirs) if has_prior else None,
            },
            'race_only': {
                'title': 'Race Only',
                'season': season_modes.get('race', {}),
                'all_seasons': all_modes.get('race', {}) if all_modes else None,
            },
            'br_only': {
                'title': 'BR Only',
                'season': season_modes.get('br', {}),
                'all_seasons': all_modes.get('br', {}) if all_modes else None,
            },
            'mycycle': {
                'title': 'MyCycle',
                'season': mycycle_season,
                'all_seasons': _aggregate_mycycle_from_directories(all_dirs) if has_prior else None,
            },
        },
    }


def _extract_race_br_trend_rows_from_directory(directory):
    rows = []
    for allraces_file in glob.glob(os.path.join(directory, 'allraces_*.csv')):
        try:
            with open(allraces_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line_no, row in enumerate(iter_csv_rows(f), start=1):
                    if len(row) < 6:
                        continue
                    # allraces rows are per-player results; keep only first-place rows
                    # so trend race/BR counts represent distinct events.
                    if not _is_first_place_row(row):
                        continue
                    mode = str(row[4] or '').strip().lower()
                    if mode not in ('race', 'br'):
                        continue
                    username = str(row[1] or '').strip().lower()
                    if not username:
                        continue
                    display_name = str(row[2] or '').strip() or username
                    points = _safe_int(row[3])
                    race_ts = _parse_overlay_timestamp(row[5])
                    race_id = str(row[10] or '').strip() if len(row) > 10 else ''
                    race_event_key = race_id or f"{os.path.basename(allraces_file)}:{line_no}"
                    rows.append({
                        'mode': mode,
                        'username': username,
                        'display_name': display_name,
                        'points': points,
                        'date_key': race_ts.strftime('%Y-%m-%d') if race_ts else None,
                        'race_event_key': race_event_key,
                    })
        except Exception:
            continue
    return rows


def _season_label_for_directory(directory):
    base = os.path.basename(os.path.abspath(directory))
    season_digits = ''.join(ch for ch in base if ch.isdigit())
    if season_digits:
        return f"Season {season_digits}"
    return base or 'Current Season'


def _build_dashboard_race_trends_payload():
    current_dir = config.get_setting('directory') or os.getcwd()
    season_dirs, has_prior = _collect_results_season_directories(current_dir)
    current_only_dirs = [os.path.abspath(current_dir)] if os.path.isdir(current_dir) else []
    all_season_dirs = season_dirs if season_dirs else current_only_dirs

    season_series = []
    for directory in all_season_dirs:
        trend_rows = _extract_race_br_trend_rows_from_directory(directory)
        unique_racers = len({row['display_name'] for row in trend_rows})
        race_count = sum(1 for row in trend_rows if row['mode'] == 'race')
        br_count = sum(1 for row in trend_rows if row['mode'] == 'br')
        total_races = race_count + br_count
        total_points = sum(_safe_int(row.get('points', 0)) for row in trend_rows)
        season_series.append({
            'season_label': _season_label_for_directory(directory),
            'unique_racers': unique_racers,
            'race_count': race_count,
            'br_count': br_count,
            'total_races': total_races,
            'ppr': round((total_points / total_races), 2) if total_races else 0.0,
        })

    current_rows = []
    for directory in current_only_dirs:
        current_rows.extend(_extract_race_br_trend_rows_from_directory(directory))

    day_groups = defaultdict(lambda: {
        'date': '',
        'unique_racers': set(),
        'race_events': set(),
        'br_events': set(),
        'points': 0,
    })
    for row in current_rows:
        day = row['date_key']
        if not day:
            continue
        bucket = day_groups[day]
        bucket['date'] = day
        bucket['unique_racers'].add(row['display_name'])
        bucket['points'] += _safe_int(row['points'])
        event_key = row.get('race_event_key')
        if not event_key:
            continue
        if row['mode'] == 'race':
            bucket['race_events'].add(event_key)
        else:
            bucket['br_events'].add(event_key)

    daily_rows = []
    for day in sorted(day_groups.keys()):
        bucket = day_groups[day]
        race_count = len(bucket['race_events'])
        br_count = len(bucket['br_events'])
        total_races = race_count + br_count
        daily_rows.append({
            'date': day,
            'unique_racers': len(bucket['unique_racers']),
            'race_count': race_count,
            'br_count': br_count,
            'total_races': total_races,
            'ppr': round((_safe_int(bucket['points']) / total_races), 2) if total_races else 0.0,
        })

    days_with_data = len(daily_rows)
    avg_racers_per_day = round(sum(row['unique_racers'] for row in daily_rows) / days_with_data, 2) if days_with_data else 0.0
    avg_races_per_day = round(sum(row['total_races'] for row in daily_rows) / days_with_data, 2) if days_with_data else 0.0
    avg_ppr_per_day = round(sum(_safe_float(row['ppr']) for row in daily_rows) / days_with_data, 2) if days_with_data else 0.0

    rolling_window = daily_rows[-7:] if daily_rows else []
    rolling7_avg_racers = round(sum(row['unique_racers'] for row in rolling_window) / len(rolling_window), 2) if rolling_window else 0.0
    rolling7_avg_races = round(sum(row['total_races'] for row in rolling_window) / len(rolling_window), 2) if rolling_window else 0.0

    total_race_count = sum(row['race_count'] for row in daily_rows)
    total_br_count = sum(row['br_count'] for row in daily_rows)
    total_current_races = total_race_count + total_br_count
    race_share = round((total_race_count / total_current_races) * 100, 2) if total_current_races else 0.0
    br_share = round((total_br_count / total_current_races) * 100, 2) if total_current_races else 0.0

    busiest = max(daily_rows, key=lambda row: row['unique_racers']) if daily_rows else None
    max_volume_day = max(daily_rows, key=lambda row: row['total_races']) if daily_rows else None
    best_ppr_day = max(daily_rows, key=lambda row: _safe_float(row['ppr'])) if daily_rows else None

    return {
        'has_prior_seasons': has_prior,
        'season_series': season_series,
        'daily_current_season': daily_rows,
        'summary': {
            'avg_racers_per_day': avg_racers_per_day,
            'avg_races_per_day': avg_races_per_day,
            'avg_ppr_per_day': avg_ppr_per_day,
            'rolling7_avg_racers': rolling7_avg_racers,
            'rolling7_avg_races': rolling7_avg_races,
            'race_share_percent': race_share,
            'br_share_percent': br_share,
            'days_with_data': days_with_data,
            'busiest_day': busiest,
            'highest_volume_day': max_volume_day,
            'best_ppr_day': best_ppr_day,
        },
    }


@app.route('/dashboard')
def dashboard_page():
    for candidate in _dashboard_dir_candidates():
        index_file = os.path.join(candidate, 'index.html')
        if os.path.isfile(index_file):
            return send_from_directory(candidate, 'index.html')

    return (f"Dashboard files not found. Checked: {', '.join(_dashboard_dir_candidates())}", 404)


@app.route('/dashboard/<path:filename>')
def dashboard_assets(filename):
    for candidate in _dashboard_dir_candidates():
        asset_file = os.path.join(candidate, filename)
        if os.path.isfile(asset_file):
            return send_from_directory(candidate, filename)

    return (f"Dashboard asset not found: {filename}", 404)


@app.route('/dashboard/readme')
def dashboard_readme_page():
    for candidate in _readme_file_candidates():
        if os.path.isfile(candidate):
            return send_from_directory(os.path.dirname(candidate), os.path.basename(candidate))

    return (f"README.html not found. Checked: {', '.join(_readme_file_candidates())}", 404)


def _build_dashboard_main_payload_for_args(args):
    payload = _build_main_dashboard_payload()

    q = (args.get('mycycle_query') or '').strip().lower()
    try:
        page = max(1, int(args.get('mycycle_page', 1)))
    except (TypeError, ValueError):
        page = 1
    try:
        page_size = min(250, max(10, int(args.get('mycycle_page_size', 120))))
    except (TypeError, ValueError):
        page_size = 120

    if q or page > 1 or page_size != 120:
        payload = copy.deepcopy(payload)
        rows = list(payload.get('mycycle', {}).get('rows') or [])
        if q:
            rows = [
                row for row in rows
                if q in str(row.get('display_name') or '').lower() or q in str(row.get('username') or '').lower()
            ]
        start = (page - 1) * page_size
        end = start + page_size
        payload['mycycle']['rows'] = rows[start:end]
        payload['mycycle']['pagination'] = {
            'page': page,
            'page_size': page_size,
            'total': len(rows),
            'total_pages': max(1, math.ceil(len(rows) / page_size)) if rows else 1,
            'query': q,
        }

    season_q = (args.get('season_query') or '').strip().lower()
    try:
        season_page = max(1, int(args.get('season_page', 1)))
    except (TypeError, ValueError):
        season_page = 1
    try:
        season_page_size = min(250, max(10, int(args.get('season_page_size', 100))))
    except (TypeError, ValueError):
        season_page_size = 100
    season_sort_by = (args.get('season_sort_by') or 'completed').strip().lower()
    season_sort_order = (args.get('season_sort_order') or 'desc').strip().lower()

    if season_q or season_page > 1 or season_page_size != 100 or season_sort_by != 'completed' or season_sort_order != 'desc':
        payload = copy.deepcopy(payload)
        season_rows = list(payload.get('season_quests', {}).get('rows') or [])
        if season_q:
            season_rows = [
                row for row in season_rows
                if season_q in str(row.get('display_name') or '').lower() or season_q in str(row.get('username') or '').lower()
            ]

        sort_fields = {
            'name': lambda row: str(row.get('display_name') or row.get('username') or '').lower(),
            'completed': lambda row: (
                int(row.get('completed', 0)),
                (int(row.get('completed', 0)) / max(1, int(row.get('active_quests', 0)))) if int(row.get('active_quests', 0)) else 0,
                int(row.get('points', 0)),
            ),
            'points': lambda row: int(row.get('points', 0)),
            'races': lambda row: int(row.get('races', 0)),
            'race_hs': lambda row: int(row.get('race_hs', 0)),
            'br_hs': lambda row: int(row.get('br_hs', 0)),
            'tilt_points': lambda row: int(row.get('tilt_points', 0)),
        }
        sort_key = sort_fields.get(season_sort_by, sort_fields['completed'])
        reverse_sort = season_sort_order != 'asc'
        season_rows.sort(key=sort_key, reverse=reverse_sort)

        season_start = (season_page - 1) * season_page_size
        season_end = season_start + season_page_size
        payload['season_quests']['rows'] = season_rows[season_start:season_end]
        payload['season_quests']['pagination'] = {
            'page': season_page,
            'page_size': season_page_size,
            'total': len(season_rows),
            'total_pages': max(1, math.ceil(len(season_rows) / season_page_size)) if season_rows else 1,
            'query': season_q,
            'sort_by': season_sort_by,
            'sort_order': 'asc' if season_sort_order == 'asc' else 'desc',
        }

    return payload


def _make_sse_response(payload_builder, *, poll_interval_s=1.0, heartbeat_interval_s=15.0):
    def generate():
        last_signature = None
        last_heartbeat = time.monotonic()

        while True:
            payload = payload_builder()
            payload_json = json.dumps(payload, separators=(',', ':'), sort_keys=True, ensure_ascii=False)
            signature = hashlib.sha1(payload_json.encode('utf-8')).hexdigest()

            if signature != last_signature:
                last_signature = signature
                yield f"event: update\ndata: {payload_json}\n\n"
                last_heartbeat = time.monotonic()
            elif (time.monotonic() - last_heartbeat) >= heartbeat_interval_s:
                yield ': keepalive\n\n'
                last_heartbeat = time.monotonic()

            time.sleep(poll_interval_s)

    response = Response(stream_with_context(generate()), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Accel-Buffering'] = 'no'
    return response


@app.route('/api/dashboard/main')
def dashboard_main_payload():
    return jsonify(_build_dashboard_main_payload_for_args(request.args))


@app.route('/api/dashboard/main/stream')
def dashboard_main_stream():
    args_snapshot = request.args.to_dict(flat=True)
    return _make_sse_response(lambda: _build_dashboard_main_payload_for_args(args_snapshot))


# Path to the token file
TOKEN_FILE_PATH = appdata_path('token_data.json')
DEFAULT_BOT_USERNAME = 'mystats_results'
TOKEN_REFRESH_EARLY_SECONDS = 300


def clear_invalid_token_data(reason):
    """Remove unusable OAuth token data and log user-facing recovery guidance."""
    try:
        if os.path.exists(TOKEN_FILE_PATH):
            os.remove(TOKEN_FILE_PATH)
            print(f"Removed invalid token file ({TOKEN_FILE_PATH}): {reason}")
    except OSError as exc:
        print(f"Could not remove invalid token file: {exc}")

    print(
        "Twitch custom bot token failed. Falling back to the default MyStats bot account "
        f"({DEFAULT_BOT_USERNAME}). Click 'Custom Bot Login' to reauthenticate your account."
    )


def _sync_chatbot_identity_from_token(access_token):
    """Refresh UI + config username from a known-good Twitch OAuth token."""
    if not access_token:
        return

    username = fetch_twitch_username(access_token)
    if username:
        update_login_button_text(username)
        try:
            config.set_setting('TWITCH_USERNAME', username, persistent=True)
        except Exception:
            logger.exception("Failed to persist TWITCH_USERNAME after token update")
    else:
        logger.warning("Token update succeeded but username lookup failed; preserving current chatbot label")


# Save token data to a file and reconnect the bot with the new token asynchronously
def save_token_data(token_info):
    token_info['expires_at'] = time.time() + token_info.get('expires_in', 0)
    with open(TOKEN_FILE_PATH, 'w') as f:
        json.dump(token_info, f)

    _sync_chatbot_identity_from_token(token_info.get('access_token'))
    print("Token data saved successfully. Restarting bot...")

    # Reconnect the bot asynchronously with the new token
    restart_bot(token_info['access_token'])


def restart_bot(new_token):
    global bot
    if bot is not None:
        # Ensure bot reconnection happens in the background without blocking
        asyncio.run_coroutine_threadsafe(bot.reconnect_with_new_token(new_token), bot.loop)


# Function to load token data from a file
def load_token_data():
    try:
        with open(TOKEN_FILE_PATH, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return None

# Function to check if the token is expired
def is_token_expired(token_data):
    expires_at = token_data.get("expires_at")
    if not expires_at:
        return True

    # Refresh slightly ahead of hard expiry to reduce churn/reconnect noise.
    return (float(expires_at) - time.time()) <= TOKEN_REFRESH_EARLY_SECONDS

# Function to refresh access token using refresh token
def refresh_access_token():
    token_data = load_token_data()

    if not token_data or 'refresh_token' not in token_data:
        print("No refresh token found.")
        return None

    print("Access token expired or nearing expiry. Refreshing...")

    token_url = "https://id.twitch.tv/oauth2/token"
    refresh_token = token_data['refresh_token']

    token_data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
    }

    logger.info("API call: Twitch token refresh")
    response = requests.post(token_url, data=token_data)

    if response.status_code == 200:
        print("Token refreshed successfully!")
        new_token_info = response.json()
        save_token_data(new_token_info)  # Save the new token info
        return new_token_info['access_token']
    else:
        print(f"Failed to refresh token: {response.text}")
        clear_invalid_token_data("refresh token rejected by Twitch")
        return None

# Function to get the OAuth token (file or ConfigManager)
def get_oauth_token():
    token_data = load_token_data()

    if token_data and not is_token_expired(token_data):
        if verify_token(token_data['access_token']):
            return token_data['access_token']  # Use the valid token
        else:
            print("Token is invalid, refreshing...")
            return refresh_access_token()  # Attempt to refresh the token if invalid

    elif token_data and is_token_expired(token_data):
        return refresh_access_token()  # Refresh the token if expired

    # Only prompt for authentication if no token file exists
    print("No valid token found. Please authenticate.")
    return None


# OAuth flow to get the authorization URL
def get_authorization_url():
    redirect_uri = _get_redirect_uri()
    url = (
        f"https://id.twitch.tv/oauth2/authorize?response_type=code&client_id={CLIENT_ID}"
        f"&redirect_uri={redirect_uri}&scope=chat:read chat:edit&force_verify=true"
    )
    return url

# Function to open the Twitch login URL in the default web browser
def open_login_url():
    url = get_authorization_url()
    webbrowser.open(url)

# Fetch Twitch username based on OAuth token
def fetch_twitch_username(oauth_token):
    headers = {'Authorization': f'Bearer {oauth_token}', 'Client-Id': CLIENT_ID}
    user_info_url = "https://api.twitch.tv/helix/users"
    logger.info("API call: Twitch user info")
    response = requests.get(user_info_url, headers=headers)

    if response.status_code == 200:
        user_info = response.json()
        if 'data' in user_info and len(user_info['data']) > 0:
            return user_info['data'][0]['display_name']
    return None


# Assuming you have this logic to fallback to config username
def fallback_to_saved_username():
    saved_username = config.get_setting('TWITCH_USERNAME')
    if saved_username:
        update_login_button_text(saved_username)
    else:
        update_login_button_text(DEFAULT_BOT_USERNAME)
        print("No saved username in config. Using default account: mystats_results")


def update_login_button_text(text):
    button = globals().get('login_button')
    if button is None:
        return

    def _apply_text():
        if button.winfo_exists():
            button.config(text=text)

    app_root = globals().get('root')
    if app_root is not None and app_root.winfo_exists():
        try:
            app_root.after(0, _apply_text)
            return
        except Exception:
            pass

    _apply_text()


def set_default_bot_login_button(reason):
    update_login_button_text(DEFAULT_BOT_USERNAME)
    print(
        "Switched chatbot display to default account (mystats_results). "
        f"Reason: {reason}"
    )


# Updated logic for setting the login button's username
def set_login_button_text():
    token_data = load_token_data()

    if token_data and 'access_token' in token_data:
        # Use the token from the JSON file to fetch the username
        oauth_token = token_data['access_token']
        username = fetch_twitch_username(oauth_token)

        if username:
            update_login_button_text(username)
        else:
            print("Failed to fetch username from the token.")
            fallback_to_saved_username()  # Use config if fetching the username fails
    else:
        fallback_to_saved_username()  # No token, fallback to config


# OAuth callback after the user authorizes the application
@app.route('/callback')
def callback():
    global oauth_token
    code = request.args.get('code')
    if not code:
        return "Authorization code not found", 400

    redirect_uri = _get_redirect_uri()
    token_url = "https://id.twitch.tv/oauth2/token"
    token_data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri': redirect_uri
    }

    response = requests.post(token_url, data=token_data)

    if response.status_code != 200:
        return f"Failed to obtain access token: {response.text}", 400

    token_info = response.json()
    oauth_token = token_info.get('access_token')

    # Verify the token before proceeding
    if oauth_token and verify_token(oauth_token):
        username = fetch_twitch_username(oauth_token)
        if username:
            update_login_button_text(username)
            save_token_data(token_info)  # Save token info and restart bot
        return "Authentication successful!", 200
    else:
        return "Failed to retrieve or validate access token.", 400


def verify_token(token, emit_console=True):
    verify_url = "https://id.twitch.tv/oauth2/validate"
    headers = {"Authorization": f"OAuth {token}"}
    logger.info("API call: Twitch token validation")
    response = requests.get(verify_url, headers=headers)
    if response.status_code == 200:
        if emit_console:
            print("\nToken is valid.")
        return True
    else:
        if emit_console:
            print(f"Token validation failed: {response.text}")
        return False


# Function to handle menu actions
def show_about_window():
    about_window = tk.Toplevel()
    about_window.title(tr("About"))
    about_window.resizable(False, False)

    # Set the window icon (optional)
    about_window.iconbitmap('circle1.ico')  # Uncomment and provide your icon file if available

    # Ensure the root window updates its position and size information
    root.update_idletasks()

    # Center the window within the main window (root)
    window_width = 400
    window_height = 600

    # Get the position and size of the root window
    root_x = root.winfo_x()
    root_y = root.winfo_y()
    root_width = root.winfo_width()
    root_height = root.winfo_height()

    # Calculate position for the about window to center it over the root window
    x_coordinate = root_x + int((root_width / 2) - (window_width / 2))
    y_coordinate = root_y + int((root_height / 2) - (window_height / 2))
    about_window.geometry(f"{window_width}x{window_height}+{x_coordinate}+{y_coordinate}")

    # Create a frame to hold the content
    content_frame = ttk.Frame(about_window, padding="10")
    content_frame.pack(fill='both', expand=True)

    # Load and display the logo image
    try:
        response = requests.get("https://mystats.camwow.tv/assets/images/mystats_logo.png")
        image_data = BytesIO(response.content)
        logo_image = Image.open(image_data)
        width, height = 100, 100
        logo_image = logo_image.resize((width, height), Image.LANCZOS)
        logo_photo = ImageTk.PhotoImage(logo_image)
        logo_label = ttk.Label(content_frame, image=logo_photo)
        logo_label.image = logo_photo  # Keep a reference to prevent garbage collection
        logo_label.pack(pady=(0, 10))
    except Exception as e:
        logger.error("Error loading logo image", exc_info=True)
        # If the logo can't be loaded, display a text placeholder
        logo_label = ttk.Label(content_frame, text="MyStats", font=("Arial", 14, "bold"))
        logo_label.pack(pady=(0, 10))

    # Application Name and Version
    app_name_label = ttk.Label(content_frame, text=tr("Mystats Application"), font=("Arial", 14, "bold"))
    app_name_label.pack()

    version_label = ttk.Label(content_frame, text=f"{tr('Version')} {version}", font=("Arial", 9))
    version_label.pack(pady=(0, 10))

    # Short Description
    description_text = tr("The application is a companion tool for Marbles On Stream, designed to enhance user engagement and streamline data management. It tracks and processes race data in real-time, handles event management, and posts automated race results to Twitch chat. Key features include Battle Royale crown win tracking, checkpoint processing, event status toggling, and seamless integration with the Twitch API for authenticating users and dynamically updating relevant stats and events. The application provides a user-friendly interface built with Tkinter, ensuring that race results, event statuses, and other critical information are easily accessible to both streamers and their viewers.")

    description_label = ttk.Label(content_frame, text=description_text, font=("Arial", 8),
                                  wraplength=380, justify="center")
    description_label.pack(pady=(0, 10))

    # Author Names
    authors_label = ttk.Label(content_frame, text=tr("Developed by\nCamWOW"), font=("Arial", 10), justify="center")
    authors_label.pack(pady=(0, 10))

    # Contact Information
    contact_label = ttk.Label(
        content_frame,
        text=tr("Contact Information\nDiscord: https://discord.gg/camwow\nWebsite: https://www.camwow.tv"),
        font=("Arial", 9),
        justify="center"
    )
    contact_label.pack(pady=(0, 10))

    # Acknowledgments or Credits
    credits_label = ttk.Label(
        content_frame,
        text=tr("Acknowledgments\nA heartfelt thank you to Vibblez for his incredible contributions, ideas, and unwavering support. His creative vision and technical expertise have been instrumental not only in shaping the MyStats application, but more specifically in elevating the website to new heights. From conceptualizing unique features to refining the user experience, his efforts have left an indelible mark on this project."),
        font=("Arial", 8),
        justify="center",
        wraplength=380
    )

    credits_label.pack(pady=(0, 10))

    # Close Button
    close_button = ttk.Button(content_frame, text=tr("Close"), command=about_window.destroy)
    close_button.pack(pady=(10, 0))

    # Disable resizing
    about_window.grid_rowconfigure(0, weight=1)
    about_window.grid_columnconfigure(0, weight=1)


def open_settings():
    open_settings_window()


# Updated show_help function to display the commands in a messagebox
# Function to display the help window centered in the main window
def show_help(bot_instance, root):
    commands_list = bot_instance.get_commands()
    help_text = f"MyStats commands:\n\n" + "\n".join(commands_list)

    # Create a new Toplevel window for the help content
    help_window = tk.Toplevel(root)
    help_window.title("Help")

    # Add a label with the help text
    help_label = tk.Label(help_window, text=help_text, padx=10, pady=10)
    help_label.pack()

    # Calculate the position to center the help window on the main window
    root_x = root.winfo_rootx()
    root_y = root.winfo_rooty()
    root_width = root.winfo_width()
    root_height = root.winfo_height()

    help_window.update_idletasks()  # Make sure the window size is updated
    help_width = help_window.winfo_width()
    help_height = help_window.winfo_height()

    # Calculate position to center the help window
    x = root_x + (root_width // 2) - (help_width // 2)
    y = root_y + (root_height // 2) - (help_height // 2)

    # Set the geometry to center the help window
    help_window.geometry(f'{help_width}x{help_height}+{x}+{y}')


chunk_alert_button = None


def get_audio_devices():
    devices = sd.query_devices()
    output_devices = [device['name'] for device in devices if device['max_output_channels'] > 0]
    return output_devices


# Function to toggle the chunk_alert setting
def toggle_chunk_alert(button):
    current_value = config.get_setting("chunk_alert") == "True"
    new_value = not current_value  # Toggle the boolean value
    config.set_setting("chunk_alert", "True" if new_value else "False", persistent=True)
    button.config(text="ON" if new_value else "OFF", bg="green" if new_value else "red")


# Function to toggle the announce_delay setting
def toggle_announce_delay(button):
    current_value = config.get_setting("announcedelay") == "True"
    new_value = not current_value  # Toggle the boolean value
    config.set_setting("announcedelay", str(new_value), persistent=True)
    config.save_settings()  # Save the settings to the file
    button.config(text="ON" if new_value else "OFF", bg="green" if new_value else "red")


def toggle_reset_audio(button):
    current_value = config.get_setting("reset_audio") == "True"
    new_value = not current_value  # Toggle the boolean value
    config.set_setting("reset_audio", str(new_value), persistent=True)
    button.config(text="ON" if new_value else "OFF", bg="green" if new_value else "red")


# Function to update the selected chunk alert audio file label
def update_chunk_alert_audio_label(audio_label, file_path):
    if os.path.isfile(file_path):
        file_name = os.path.basename(file_path)
        if len(file_name) > 15:
            file_name = file_name[:11] + '...' + file_name[-4:]  # Redact to 15 characters
        audio_label.config(text=file_name)
    else:
        audio_label.config(text="No file selected")
    config.set_setting("chunk_alert_sound", file_path, persistent=True)


# Function to update the selected reset audio file label
def update_reset_audio_label(reset_audio_label, file_path):
    if os.path.isfile(file_path):
        file_name = os.path.basename(file_path)
        if len(file_name) > 15:
            file_name = file_name[:11] + '...' + file_name[-4:]  # Redact to 15 characters
        reset_audio_label.config(text=file_name)
    else:
        reset_audio_label.config(text="No file selected")
    config.set_setting("reset_audio_sound", file_path, persistent=True)


# Function to select the chunk alert audio file
def select_chunk_alert_sound(chunk_alert_label, settings_window):
    initial_dir = appdata_path("sound files")
    file_path = tk.filedialog.askopenfilename(initialdir=initial_dir, title="Select Sound File",
                                              filetypes=[("Audio Files", "*.mp3;*.wav;*.ogg")])
    if file_path:
        update_chunk_alert_audio_label(chunk_alert_label, file_path)
        settings_window.lift()
        settings_window.focus_force()


# Function to select the reset audio file
def select_reset_audio_sound(reset_audio_label, settings_window):
    initial_dir = appdata_path("sound files")
    file_path = tk.filedialog.askopenfilename(initialdir=initial_dir, title="Select Sound File",
                                              filetypes=[("Audio Files", "*.mp3;*.wav;*.ogg")])
    if file_path:
        update_reset_audio_label(reset_audio_label, file_path)
        settings_window.lift()
        settings_window.focus_force()


def play_audio_file(filename, device_name=None):
    """
    Play an audio file using the specified audio device.

    :param filename: The path to the audio file.
    :param device_name: The name of the audio device to use (optional). If not provided, the default device is used.
    """
    try:
        # Load the audio file
        data, fs = sf.read(filename, dtype='float32')

        # If a specific audio device is provided, set it
        if device_name:
            device_info = next((device for device in sd.query_devices() if device['name'] == device_name), None)
            if device_info:
                sd.default.device = device_info['index']
            else:
                print(f"Device '{device_name}' not found. Using default device.")

        # Play the audio file
        sd.play(data, fs)
        sd.wait()  # Wait until the file is done playing

    except Exception as e:
        logger.error("An error occurred while playing the audio file", exc_info=True)


def open_settings_window():
    settings_window = tk.Toplevel(root)
    settings_window.title(tr("Settings"))
    settings_window.transient(root)
    settings_window.attributes('-topmost', False)

    window_width = 820
    window_height = 700
    center_toplevel(settings_window, window_width, window_height)
    settings_window.minsize(720, 640)
    settings_window.grid_rowconfigure(0, weight=1)
    settings_window.grid_columnconfigure(0, weight=1)

    content_frame = ttk.Frame(settings_window, style="App.TFrame")
    content_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 0))

    notebook = ttk.Notebook(content_frame)
    notebook.pack(fill="both", expand=True)

    general_root_tab = ttk.Frame(notebook, style="App.TFrame", padding=10)
    tilt_root_tab = ttk.Frame(notebook, style="App.TFrame", padding=10)
    race_br_root_tab = ttk.Frame(notebook, style="App.TFrame", padding=10)

    notebook.add(general_root_tab, text=tr("General"))
    notebook.add(tilt_root_tab, text=tr("Tilt"))
    notebook.add(race_br_root_tab, text="Race/BR")

    general_root_tab.grid_columnconfigure(0, weight=1)
    general_root_tab.grid_rowconfigure(0, weight=1)
    tilt_root_tab.grid_columnconfigure(0, weight=1)
    tilt_root_tab.grid_rowconfigure(0, weight=1)
    race_br_root_tab.grid_columnconfigure(0, weight=1)
    race_br_root_tab.grid_rowconfigure(0, weight=1)

    general_sections = ttk.Notebook(general_root_tab)
    general_sections.grid(row=0, column=0, sticky="nsew")

    tilt_sections = ttk.Notebook(tilt_root_tab)
    tilt_sections.grid(row=0, column=0, sticky="nsew")

    race_br_sections = ttk.Notebook(race_br_root_tab)
    race_br_sections.grid(row=0, column=0, sticky="nsew")

    general_tab = ttk.Frame(general_sections, style="App.TFrame", padding=10)
    audio_tab = ttk.Frame(general_sections, style="App.TFrame", padding=10)
    appearance_tab = ttk.Frame(general_sections, style="App.TFrame", padding=10)

    tilt_chat_tab = ttk.Frame(tilt_sections, style="App.TFrame", padding=10)
    tilt_overlay_tab = ttk.Frame(tilt_sections, style="App.TFrame", padding=10)
    tilt_horizontal_overlay_tab = ttk.Frame(tilt_sections, style="App.TFrame", padding=10)
    tilt_thresholds_tab = ttk.Frame(tilt_sections, style="App.TFrame", padding=10)

    race_chat_tab = ttk.Frame(race_br_sections, style="App.TFrame", padding=10)
    race_alerts_tab = ttk.Frame(race_br_sections, style="App.TFrame", padding=10)
    race_overlay_tab = ttk.Frame(race_br_sections, style="App.TFrame", padding=10)
    race_horizontal_overlay_tab = ttk.Frame(race_br_sections, style="App.TFrame", padding=10)
    mycycle_tab = ttk.Frame(race_br_sections, style="App.TFrame", padding=10)
    rivals_tab = ttk.Frame(race_br_sections, style="App.TFrame", padding=10)
    season_quests_tab = ttk.Frame(race_br_sections, style="App.TFrame", padding=10)

    general_sections.add(audio_tab, text=tr("Audio"))
    general_sections.add(appearance_tab, text=tr("Appearance"))
    general_sections.add(general_tab, text=tr("General"))

    tilt_sections.add(tilt_chat_tab, text="Tilt Chat")
    tilt_sections.add(tilt_overlay_tab, text="Tilt Overlay")
    tilt_sections.add(tilt_horizontal_overlay_tab, text="Tilt Horizontal Overlay")
    tilt_sections.add(tilt_thresholds_tab, text="Tilt Command Thresholds")

    race_br_sections.add(race_chat_tab, text=tr("Chat"))
    race_br_sections.add(race_alerts_tab, text="Alerts")
    race_br_sections.add(race_overlay_tab, text=tr("Overlay"))
    race_br_sections.add(race_horizontal_overlay_tab, text="Horizontal Overlay")
    race_br_sections.add(mycycle_tab, text=tr("MyCycle"))
    race_br_sections.add(rivals_tab, text=tr("Rivals"))
    race_br_sections.add(season_quests_tab, text=tr("Season Quests"))

    teams_tab = ttk.Frame(notebook, style="App.TFrame", padding=10)
    notebook.add(teams_tab, text="MyTeams")

    # --- General tab ---
    ttk.Label(general_tab, text=tr("Core app settings"), style="Small.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

    ttk.Label(general_tab, text=tr("Channel")).grid(row=1, column=0, sticky="w", pady=(0, 4))
    channel_entry = ttk.Entry(general_tab, width=28)
    channel_entry.grid(row=1, column=1, sticky="w", pady=(0, 4))
    channel_entry.insert(0, config.get_setting("CHANNEL") or "")

    ttk.Label(general_tab, text=tr("Marble Day")).grid(row=2, column=0, sticky="w", pady=(0, 4))
    ttk.Label(general_tab, text=config.get_setting("marble_day") or "-").grid(row=2, column=1, sticky="w", pady=(0, 4))

    ttk.Label(general_tab, text=tr("Season")).grid(row=3, column=0, sticky="w", pady=(0, 4))
    ttk.Label(general_tab, text=config.get_setting("season") or "-").grid(row=3, column=1, sticky="w", pady=(0, 4))

    ttk.Label(general_tab, text=tr("Language")).grid(row=4, column=0, sticky="w", pady=(0, 8))
    app_language_code_to_name = {code: LANGUAGE_DISPLAY_NAMES.get(code, code) for code in SUPPORTED_UI_LANGUAGES}
    app_language_name_to_code = {name: code for code, name in app_language_code_to_name.items()}
    app_language_var = tk.StringVar(value=app_language_code_to_name.get(get_ui_language(), LANGUAGE_DISPLAY_NAMES['en']))
    ttk.Combobox(general_tab, textvariable=app_language_var, values=[app_language_code_to_name[c] for c in sorted(app_language_code_to_name.keys())], width=16, state="readonly").grid(row=4, column=1, sticky="w", pady=(0, 8))

    ttk.Separator(general_tab, orient="horizontal").grid(row=5, column=0, columnspan=2, sticky="ew", pady=8)

    minimize_to_tray_var = tk.BooleanVar(value=is_minimize_to_tray_enabled())
    tray_support_text = "Minimize to system tray (double-click tray icon to reopen)"
    if not supports_system_tray():
        tray_support_text += " [pystray not available]"
    ttk.Checkbutton(general_tab, text=tray_support_text, variable=minimize_to_tray_var).grid(row=6, column=0, columnspan=2, sticky="w", pady=(0, 4))

    ttk.Label(general_tab, text=tr("Mystats Directory")).grid(row=8, column=0, sticky="w", pady=(0, 4))
    directory_value = appdata_path()
    directory_entry = ttk.Entry(general_tab, width=55)
    directory_entry.grid(row=9, column=0, sticky="ew", pady=(0, 4), columnspan=2)
    directory_entry.insert(0, directory_value)
    directory_entry.config(state="readonly")

    def open_directory():
        directory_path = appdata_path()
        if os.path.exists(directory_path):
            os.startfile(directory_path)
        else:
            messagebox.showerror("Error", "Directory path does not exist.")

    ttk.Button(general_tab, text=tr("Open Location"), command=open_directory).grid(row=10, column=0, sticky="w", pady=(4, 0))
    general_tab.grid_columnconfigure(0, weight=1)

    # --- Audio tab ---
    ttk.Label(audio_tab, text="Audio alerts and output device settings", style="Small.TLabel").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))

    chunk_alert_frame = ttk.LabelFrame(audio_tab, text="Chunk Alert", style="Card.TLabelframe")
    chunk_alert_frame.grid(row=1, column=0, padx=(0, 10), pady=6, sticky="nsew")

    chunk_alert_var = tk.BooleanVar(value=config.get_setting("chunk_alert") == 'True')
    ttk.Checkbutton(chunk_alert_frame, text="Enable Chunk Alert", variable=chunk_alert_var).pack(anchor="w", padx=10, pady=(8, 6))

    ttk.Label(chunk_alert_frame, text="Trigger Amount", style="Small.TLabel").pack(anchor="w", padx=10)
    chunk_alert_trigger_entry = ttk.Entry(chunk_alert_frame, width=12, justify='center')
    chunk_alert_trigger_entry.pack(anchor="w", padx=10, pady=(2, 8))
    chunk_alert_trigger_entry.insert(0, config.get_setting("chunk_alert_value") or "")

    chunk_alert_label = ttk.Label(chunk_alert_frame, text="No file selected", style="Small.TLabel")
    chunk_alert_label.pack(anchor="w", padx=10, pady=(0, 6))

    file_button_frame = ttk.Frame(chunk_alert_frame, style="App.TFrame")
    file_button_frame.pack(anchor="w", padx=10, pady=(0, 8))
    ttk.Button(file_button_frame, text="📁", width=3,
               command=lambda: select_chunk_alert_sound(chunk_alert_label, settings_window)).pack(side="left", padx=(0, 6))
    ttk.Button(file_button_frame, text="🔊", width=3, command=test_chunkaudio_playback).pack(side="left")

    saved_chunk_alert_file_path = config.get_setting("chunk_alert_sound")
    if saved_chunk_alert_file_path:
        update_chunk_alert_audio_label(chunk_alert_label, saved_chunk_alert_file_path)

    marbles_reset_frame = ttk.LabelFrame(audio_tab, text="Marbles Reset", style="Card.TLabelframe")
    marbles_reset_frame.grid(row=1, column=1, pady=6, sticky="nsew")

    reset_audio_var = tk.BooleanVar(value=config.get_setting("reset_audio") == "True")
    ttk.Checkbutton(marbles_reset_frame, text="Enable Reset Audio", variable=reset_audio_var).pack(anchor="w", padx=10, pady=(8, 6))

    reset_audio_label = ttk.Label(marbles_reset_frame, text="No file selected", style="Small.TLabel")
    reset_audio_label.pack(anchor="w", padx=10, pady=(0, 6))

    reset_button_frame = ttk.Frame(marbles_reset_frame, style="App.TFrame")
    reset_button_frame.pack(anchor="w", padx=10, pady=(0, 8))
    ttk.Button(reset_button_frame, text="📁", width=3,
               command=lambda: select_reset_audio_sound(reset_audio_label, settings_window)).pack(side="left", padx=(0, 6))
    ttk.Button(reset_button_frame, text="🔊", width=3, command=test_audio_playback).pack(side="left")

    saved_reset_file_path = config.get_setting("reset_audio_sound")
    if saved_reset_file_path:
        update_reset_audio_label(reset_audio_label, saved_reset_file_path)

    ttk.Label(audio_tab, text="Select Audio Output Device").grid(row=2, column=0, columnspan=3, sticky="w", pady=(8, 4))
    audio_devices = get_audio_devices()
    selected_device = tk.StringVar()
    current_device = config.get_setting('audio_device')
    if not current_device:
        current_device = "Primary Sound Driver"
        config.set_setting('audio_device', current_device)
    selected_device.set(current_device)

    device_combobox = ttk.Combobox(audio_tab, textvariable=selected_device, values=audio_devices, width=62)
    device_combobox.grid(row=3, column=0, columnspan=3, sticky="w")

    def on_device_change(event):
        config.set_setting('audio_device', selected_device.get())

    device_combobox.bind('<<ComboboxSelected>>', on_device_change)

    for idx in range(2):
        audio_tab.grid_columnconfigure(idx, weight=1)

    # --- Chat tab ---
    ttk.Label(race_chat_tab, text="Control what MyStats announces in chat", style="Small.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))

    chat_br_results_var = tk.BooleanVar(value=is_chat_response_enabled("chat_br_results"))
    chat_race_results_var = tk.BooleanVar(value=is_chat_response_enabled("chat_race_results"))
    chat_all_commands_var = tk.BooleanVar(value=is_chat_response_enabled("chat_all_commands"))
    chat_leaderboard_show_medals_var = tk.BooleanVar(value=str(config.get_setting("chat_leaderboard_show_medals") or "True") == "True")
    competitive_raid_monitor_enabled_var = tk.BooleanVar(value=is_chat_response_enabled("competitive_raid_monitor_enabled"))

    ttk.Checkbutton(race_chat_tab, text="BR Results", variable=chat_br_results_var).grid(row=1, column=0, sticky="w", pady=2)
    ttk.Checkbutton(race_chat_tab, text="Race Results", variable=chat_race_results_var).grid(row=2, column=0, sticky="w", pady=2)
    ttk.Checkbutton(race_chat_tab, text="All !commands", variable=chat_all_commands_var).grid(row=3, column=0, sticky="w", pady=2)
    ttk.Checkbutton(race_chat_tab, text="Show top-3 medal emotes in leaderboard commands", variable=chat_leaderboard_show_medals_var).grid(row=4, column=0, sticky="w", pady=2)
    ttk.Checkbutton(race_chat_tab, text="Competitive Raid Alerts (opt-in)", variable=competitive_raid_monitor_enabled_var).grid(row=5, column=0, sticky="w", pady=2)

    race_narrative_alerts_var = tk.BooleanVar(value=is_chat_response_enabled("race_narrative_alerts_enabled"))
    race_narrative_grinder_var = tk.BooleanVar(value=is_chat_response_enabled("race_narrative_grinder_enabled"))
    race_narrative_winmilestone_var = tk.BooleanVar(value=is_chat_response_enabled("race_narrative_winmilestone_enabled"))
    race_narrative_leadchange_var = tk.BooleanVar(value=is_chat_response_enabled("race_narrative_leadchange_enabled"))

    race_alerts_frame = ttk.LabelFrame(race_alerts_tab, text="Race Narrative Player Alerts", style="Card.TLabelframe")
    race_alerts_frame.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(10, 0))

    ttk.Checkbutton(race_alerts_frame, text="Narrative Alerts", variable=race_narrative_alerts_var).grid(row=0, column=0, sticky="w", padx=10, pady=(8, 4))
    ttk.Checkbutton(race_alerts_frame, text="Grinder milestones", variable=race_narrative_grinder_var).grid(row=1, column=0, sticky="w", padx=10, pady=2)
    ttk.Checkbutton(race_alerts_frame, text="Win milestones", variable=race_narrative_winmilestone_var).grid(row=2, column=0, sticky="w", padx=10, pady=2)
    ttk.Checkbutton(race_alerts_frame, text="Lead changes", variable=race_narrative_leadchange_var).grid(row=3, column=0, sticky="w", padx=10, pady=(2, 8))

    ttk.Label(race_alerts_frame, text="Cooldown (races)", style="Small.TLabel").grid(row=1, column=1, sticky="w", padx=(12, 8), pady=(2, 2))
    race_narrative_cooldown_entry = ttk.Entry(race_alerts_frame, width=8, justify='center')
    race_narrative_cooldown_entry.grid(row=1, column=2, sticky="w", padx=(0, 10), pady=(2, 2))
    race_narrative_cooldown_entry.insert(0, config.get_setting("race_narrative_alert_cooldown_races") or "3")

    ttk.Label(race_alerts_frame, text="Min lead gap", style="Small.TLabel").grid(row=2, column=1, sticky="w", padx=(12, 8), pady=2)
    race_narrative_min_gap_entry = ttk.Entry(race_alerts_frame, width=8, justify='center')
    race_narrative_min_gap_entry.grid(row=2, column=2, sticky="w", padx=(0, 10), pady=2)
    race_narrative_min_gap_entry.insert(0, config.get_setting("race_narrative_alert_min_lead_change_points") or "500")

    ttk.Label(race_alerts_frame, text="Max items per alert", style="Small.TLabel").grid(row=3, column=1, sticky="w", padx=(12, 8), pady=(2, 8))
    race_narrative_max_items_entry = ttk.Entry(race_alerts_frame, width=8, justify='center')
    race_narrative_max_items_entry.grid(row=3, column=2, sticky="w", padx=(0, 10), pady=(2, 8))
    race_narrative_max_items_entry.insert(0, config.get_setting("race_narrative_alert_max_items") or "3")

    message_delay_frame = ttk.LabelFrame(race_alerts_tab, text="Message Delay", style="Card.TLabelframe")
    message_delay_frame.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(10, 0))

    announce_delay_var = tk.BooleanVar(value=config.get_setting("announcedelay") == "True")
    ttk.Checkbutton(message_delay_frame, text="Enable Delay", variable=announce_delay_var).grid(row=0, column=0, sticky="w", padx=10, pady=(8, 6))
    ttk.Label(message_delay_frame, text="Delay Seconds", style="Small.TLabel").grid(row=1, column=0, sticky="w", padx=10)
    delay_seconds_entry = ttk.Entry(message_delay_frame, width=12, justify='center')
    delay_seconds_entry.grid(row=1, column=1, sticky="w", padx=(8, 10), pady=(0, 8))
    delay_seconds_entry.insert(0, config.get_setting("announcedelayseconds") or "")
    race_chat_tab.grid_columnconfigure(0, weight=1)
    race_alerts_tab.grid_columnconfigure(0, weight=1)

    # --- Tilt tab ---
    ttk.Label(tilt_chat_tab, text="Configure tilt chat alerts", style="Small.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

    chat_tilt_results_var = tk.BooleanVar(value=is_chat_response_enabled("chat_tilt_results"))
    chat_tilt_suppress_offline_var = tk.BooleanVar(value=is_chat_response_enabled("chat_tilt_suppress_offline"))
    chat_tilt_redact_survivor_names_var = tk.BooleanVar(value=is_chat_response_enabled("chat_tilt_redact_survivor_names"))
    chat_narrative_alerts_var = tk.BooleanVar(value=is_chat_response_enabled("chat_narrative_alerts"))
    narrative_alert_grinder_var = tk.BooleanVar(value=is_chat_response_enabled("narrative_alert_grinder_enabled"))
    narrative_alert_winmilestone_var = tk.BooleanVar(value=is_chat_response_enabled("narrative_alert_winmilestone_enabled"))
    narrative_alert_leadchange_var = tk.BooleanVar(value=is_chat_response_enabled("narrative_alert_leadchange_enabled"))

    tilt_alerts_frame = ttk.LabelFrame(tilt_chat_tab, text="Tilt Chat Alerts", style="Card.TLabelframe")
    tilt_alerts_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 8))

    ttk.Checkbutton(tilt_alerts_frame, text="Tilt Results", variable=chat_tilt_results_var).grid(row=0, column=0, sticky="w", padx=10, pady=(8, 4))
    ttk.Checkbutton(tilt_alerts_frame, text="Narrative Alerts", variable=chat_narrative_alerts_var).grid(row=1, column=0, sticky="w", padx=10, pady=(0, 4))
    ttk.Checkbutton(tilt_alerts_frame, text="Suppress messages when level is offline", variable=chat_tilt_suppress_offline_var).grid(row=2, column=0, sticky="w", padx=10, pady=(0, 4))
    ttk.Checkbutton(tilt_alerts_frame, text="Redact survivor names in chat", variable=chat_tilt_redact_survivor_names_var).grid(row=3, column=0, sticky="w", padx=10, pady=(0, 4))
    ttk.Checkbutton(tilt_alerts_frame, text="Grinder milestones", variable=narrative_alert_grinder_var).grid(row=4, column=0, sticky="w", padx=10, pady=2)
    ttk.Checkbutton(tilt_alerts_frame, text="Win milestones", variable=narrative_alert_winmilestone_var).grid(row=5, column=0, sticky="w", padx=10, pady=2)
    ttk.Checkbutton(tilt_alerts_frame, text="Lead changes", variable=narrative_alert_leadchange_var).grid(row=6, column=0, sticky="w", padx=10, pady=(2, 8))

    ttk.Label(tilt_alerts_frame, text="Cooldown (races)", style="Small.TLabel").grid(row=4, column=1, sticky="w", padx=(12, 8), pady=(2, 2))
    narrative_alert_cooldown_entry = ttk.Entry(tilt_alerts_frame, width=8, justify='center')
    narrative_alert_cooldown_entry.grid(row=4, column=2, sticky="w", padx=(0, 10), pady=(2, 2))
    narrative_alert_cooldown_entry.insert(0, config.get_setting("narrative_alert_cooldown_races") or "3")

    ttk.Label(tilt_alerts_frame, text="Min lead gap", style="Small.TLabel").grid(row=5, column=1, sticky="w", padx=(12, 8), pady=2)
    narrative_alert_min_gap_entry = ttk.Entry(tilt_alerts_frame, width=8, justify='center')
    narrative_alert_min_gap_entry.grid(row=5, column=2, sticky="w", padx=(0, 10), pady=2)
    narrative_alert_min_gap_entry.insert(0, config.get_setting("narrative_alert_min_lead_change_points") or "500")

    ttk.Label(tilt_alerts_frame, text="Max items per alert", style="Small.TLabel").grid(row=6, column=1, sticky="w", padx=(12, 8), pady=(2, 8))
    narrative_alert_max_items_entry = ttk.Entry(tilt_alerts_frame, width=8, justify='center')
    narrative_alert_max_items_entry.grid(row=6, column=2, sticky="w", padx=(0, 10), pady=(2, 8))
    narrative_alert_max_items_entry.insert(0, config.get_setting("narrative_alert_max_items") or "3")

    ttk.Label(tilt_chat_tab, text="Max names announced (Race/Tilt)").grid(row=2, column=0, sticky="w", pady=(2, 4))
    max_name_values = [str(i) for i in range(3, 26)]
    selected_max_names = tk.StringVar(value=str(get_chat_max_names()))
    max_names_combobox = ttk.Combobox(tilt_chat_tab, textvariable=selected_max_names, values=max_name_values, width=5, state="readonly")
    max_names_combobox.grid(row=2, column=1, sticky="w", pady=(2, 4), padx=(8, 0))

    ttk.Label(tilt_thresholds_tab, text="Configure !tiltsurvivors filtering", style="Small.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))
    tiltsurvivors_frame = ttk.LabelFrame(tilt_thresholds_tab, text="Tilt Command Thresholds", style="Card.TLabelframe")
    tiltsurvivors_frame.grid(row=1, column=0, sticky="ew", pady=(0, 8))
    ttk.Label(tiltsurvivors_frame, text="!tiltsurvivors minimum levels participated", style="Small.TLabel").grid(row=0, column=0, sticky="w", padx=(10, 8), pady=(8, 4))
    tiltsurvivors_min_levels_entry = ttk.Entry(tiltsurvivors_frame, width=12, justify='center')
    tiltsurvivors_min_levels_entry.grid(row=0, column=1, sticky="w", padx=(0, 10), pady=(8, 4))
    tiltsurvivors_min_levels_entry.insert(0, config.get_setting("tiltsurvivors_min_levels") or config.get_setting("tiltdeath_min_levels") or "20")
    ttk.Label(tiltsurvivors_frame, text="Players below this threshold are excluded from !tiltsurvivors ranking.", style="Small.TLabel").grid(row=1, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 8))

    # --- Season Quests tab ---
    ttk.Label(season_quests_tab, text="Configure long-term season goals and chat announcements", style="Small.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

    season_quests_enabled_var = tk.BooleanVar(value=is_chat_response_enabled("season_quests_enabled"))
    ttk.Checkbutton(season_quests_tab, text="Enable Season Quests", variable=season_quests_enabled_var).grid(row=1, column=0, sticky="w", pady=(0, 10), columnspan=2)

    ttk.Label(season_quests_tab, text="Season Race Target").grid(row=2, column=0, sticky="w", pady=(2, 4))
    season_quest_races_entry = ttk.Entry(season_quests_tab, width=12, justify='center')
    season_quest_races_entry.grid(row=2, column=1, sticky="w", pady=(2, 4))
    season_quest_races_entry.insert(0, config.get_setting("season_quest_target_races") or "1000")

    ttk.Label(season_quests_tab, text="Season Points Target").grid(row=3, column=0, sticky="w", pady=(2, 4))
    season_quest_points_entry = ttk.Entry(season_quests_tab, width=12, justify='center')
    season_quest_points_entry.grid(row=3, column=1, sticky="w", pady=(2, 4))
    season_quest_points_entry.insert(0, config.get_setting("season_quest_target_points") or "500000")

    ttk.Label(season_quests_tab, text="Race High Score Target").grid(row=4, column=0, sticky="w", pady=(2, 4))
    season_quest_race_hs_entry = ttk.Entry(season_quests_tab, width=12, justify='center')
    season_quest_race_hs_entry.grid(row=4, column=1, sticky="w", pady=(2, 4))
    season_quest_race_hs_entry.insert(0, config.get_setting("season_quest_target_race_hs") or "3000")

    ttk.Label(season_quests_tab, text="BR High Score Target").grid(row=5, column=0, sticky="w", pady=(2, 4))
    season_quest_br_hs_entry = ttk.Entry(season_quests_tab, width=12, justify='center')
    season_quest_br_hs_entry.grid(row=5, column=1, sticky="w", pady=(2, 4))
    season_quest_br_hs_entry.insert(0, config.get_setting("season_quest_target_br_hs") or "3000")

    tilt_quest_frame = ttk.LabelFrame(season_quests_tab, text="Tilt Season Quests", style="Card.TLabelframe")
    tilt_quest_frame.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(8, 4))

    ttk.Label(tilt_quest_frame, text="Tilt Levels Participated", style="Small.TLabel").grid(row=0, column=0, sticky="w", padx=(10, 8), pady=(8, 4))
    season_quest_tilt_levels_entry = ttk.Entry(tilt_quest_frame, width=12, justify='center')
    season_quest_tilt_levels_entry.grid(row=0, column=1, sticky="w", padx=(0, 10), pady=(8, 4))
    season_quest_tilt_levels_entry.insert(0, config.get_setting("season_quest_target_tilt_levels") or "1000")

    ttk.Label(tilt_quest_frame, text="Top Tiltee Finishes", style="Small.TLabel").grid(row=1, column=0, sticky="w", padx=(10, 8), pady=4)
    season_quest_tilt_tops_entry = ttk.Entry(tilt_quest_frame, width=12, justify='center')
    season_quest_tilt_tops_entry.grid(row=1, column=1, sticky="w", padx=(0, 10), pady=4)
    season_quest_tilt_tops_entry.insert(0, config.get_setting("season_quest_target_tilt_tops") or "100")

    ttk.Label(tilt_quest_frame, text="Tilt Points Earned", style="Small.TLabel").grid(row=2, column=0, sticky="w", padx=(10, 8), pady=(4, 8))
    season_quest_tilt_points_entry = ttk.Entry(tilt_quest_frame, width=12, justify='center')
    season_quest_tilt_points_entry.grid(row=2, column=1, sticky="w", padx=(0, 10), pady=(4, 8))
    season_quest_tilt_points_entry.insert(0, config.get_setting("season_quest_target_tilt_points") or "500000")

    ttk.Label(season_quests_tab, text="Tip: Set any target to 0 to disable that specific quest.", style="Small.TLabel").grid(row=7, column=0, columnspan=2, sticky="w", pady=(8, 4))

    def reset_season_quest_progress():
        for completion_key in ("season_quest_complete_races", "season_quest_complete_points", "season_quest_complete_race_hs", "season_quest_complete_br_hs", "season_quest_complete_tilt_levels", "season_quest_complete_tilt_tops", "season_quest_complete_tilt_points"):
            config.set_setting(completion_key, "False", persistent=True)
        completion_state = _load_season_quest_completion_state()
        completion_state[_get_season_scope_key()] = {}
        _save_season_quest_completion_state(completion_state)
        _invalidate_dashboard_cache()
        messagebox.showinfo("Season Quests", "Season quest completion flags have been reset for the active season.")

    ttk.Button(season_quests_tab, text="Reset Quest Progress", command=reset_season_quest_progress).grid(row=8, column=0, sticky="w", pady=(8, 0))
    ttk.Button(season_quests_tab, text="View Quest Completion", command=lambda: open_quest_completion_window(settings_window)).grid(row=8, column=1, sticky="w", pady=(8, 0))

    # --- Rivals tab ---
    ttk.Label(rivals_tab, text="Configure rivalry detection and commands", style="Small.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

    rivals_enabled_var = tk.BooleanVar(value=is_chat_response_enabled("rivals_enabled"))
    ttk.Checkbutton(rivals_tab, text="Enable Rivals", variable=rivals_enabled_var).grid(row=1, column=0, sticky="w", pady=(0, 10), columnspan=2)

    ttk.Label(rivals_tab, text="Minimum Season Races").grid(row=2, column=0, sticky="w", pady=(2, 4))
    rivals_min_races_entry = ttk.Entry(rivals_tab, width=12, justify='center')
    rivals_min_races_entry.grid(row=2, column=1, sticky="w", pady=(2, 4))
    rivals_min_races_entry.insert(0, config.get_setting("rivals_min_races") or "50")

    ttk.Label(rivals_tab, text="Maximum Point Gap").grid(row=3, column=0, sticky="w", pady=(2, 4))
    rivals_max_gap_entry = ttk.Entry(rivals_tab, width=12, justify='center')
    rivals_max_gap_entry.grid(row=3, column=1, sticky="w", pady=(2, 4))
    rivals_max_gap_entry.insert(0, config.get_setting("rivals_max_point_gap") or "1500")

    ttk.Label(rivals_tab, text="Pairs to Show").grid(row=4, column=0, sticky="w", pady=(2, 4))
    rivals_pair_count_entry = ttk.Entry(rivals_tab, width=12, justify='center')
    rivals_pair_count_entry.grid(row=4, column=1, sticky="w", pady=(2, 4))
    rivals_pair_count_entry.insert(0, config.get_setting("rivals_pair_count") or "25")
    ttk.Label(
        rivals_tab,
        text=(
            f"Ranges: min races 1-{RIVALS_MAX_MIN_RACES:,}, max gap 0-{RIVALS_MAX_POINT_GAP:,}, "
            f"pairs 1-{RIVALS_MAX_PAIRS:,}."
        ),
        style="Small.TLabel"
    ).grid(row=5, column=0, columnspan=2, sticky="w", pady=(0, 8))

    ttk.Button(rivals_tab, text="View Rivalries", command=lambda: open_rivalries_window(settings_window)).grid(row=6, column=0, sticky="w", pady=(8, 0))
    ttk.Label(rivals_tab, text="How Rivals works: only players above Minimum Season Races are considered.", style="Small.TLabel").grid(row=7, column=0, columnspan=2, sticky="w", pady=(10, 0))
    ttk.Label(rivals_tab, text="Pairs qualify when their season points are within Maximum Point Gap, then closest gaps are ranked.", style="Small.TLabel").grid(row=8, column=0, columnspan=2, sticky="w", pady=(2, 0))
    ttk.Label(rivals_tab, text="Chat helpers: !rivals <user> [full] for personal rivals and !h2h <user1> <user2> for direct comparison.", style="Small.TLabel").grid(row=9, column=0, columnspan=2, sticky="w", pady=(6, 0))
    ttk.Label(rivals_tab, text="Need a deeper breakdown? Open the Rivals dashboard tab for a guide and live rivalry context.", style="Small.TLabel").grid(row=10, column=0, columnspan=2, sticky="w", pady=(6, 0))
    ttk.Button(rivals_tab, text="Open Rivals Dashboard", command=open_rivals_dashboard).grid(row=11, column=0, sticky="w", pady=(8, 0))

    # --- MyCycle tab ---
    ttk.Label(mycycle_tab, text="Track placement cycles (uses your configured min/max placements) and custom sessions", style="Small.TLabel").grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 8))

    mycycle_enabled_var = tk.BooleanVar(value=is_chat_response_enabled("mycycle_enabled"))
    mycycle_announce_var = tk.BooleanVar(value=is_chat_response_enabled("mycycle_announcements_enabled"))
    mycycle_include_br_var = tk.BooleanVar(value=is_chat_response_enabled("mycycle_include_br"))

    ttk.Checkbutton(mycycle_tab, text="Enable MyCycle tracking", variable=mycycle_enabled_var).grid(row=1, column=0, sticky="w", pady=(0, 4), columnspan=3)
    ttk.Checkbutton(mycycle_tab, text="Announce completed cycles in chat", variable=mycycle_announce_var).grid(row=2, column=0, sticky="w", pady=(0, 4), columnspan=3)
    ttk.Checkbutton(mycycle_tab, text="Include BR placements in cycle tracking", variable=mycycle_include_br_var).grid(row=3, column=0, sticky="w", pady=(0, 10), columnspan=3)

    ttk.Label(mycycle_tab, text="Minimum placement in cycle").grid(row=4, column=0, sticky="w", pady=(2, 4))
    mycycle_min_place_entry = ttk.Entry(mycycle_tab, width=8, justify='center')
    mycycle_min_place_entry.grid(row=4, column=1, sticky="w", pady=(2, 4))
    mycycle_min_place_entry.insert(0, config.get_setting("mycycle_min_place") or "1")

    ttk.Label(mycycle_tab, text="Maximum placement in cycle").grid(row=5, column=0, sticky="w", pady=(2, 4))
    mycycle_max_place_entry = ttk.Entry(mycycle_tab, width=8, justify='center')
    mycycle_max_place_entry.grid(row=5, column=1, sticky="w", pady=(2, 4))
    mycycle_max_place_entry.insert(0, config.get_setting("mycycle_max_place") or "10")

    ttk.Label(mycycle_tab, text="Primary session for !mycycle", style="Small.TLabel").grid(row=6, column=0, sticky="w", pady=(10, 2))
    session_options, default_session_id = get_mycycle_sessions(include_inactive=True)
    session_names = {s['name']: s['id'] for s in session_options}
    current_primary = config.get_setting('mycycle_primary_session_id') or default_session_id
    current_primary_name = next((s['name'] for s in session_options if s['id'] == current_primary), session_options[0]['name'] if session_options else "")
    selected_session_name = tk.StringVar(value=current_primary_name)
    session_dropdown = ttk.Combobox(mycycle_tab, textvariable=selected_session_name, values=list(session_names.keys()), width=30, state="readonly")
    session_dropdown.grid(row=6, column=1, sticky="w", pady=(10, 2), columnspan=2)

    def refresh_session_dropdown(select_id=None):
        sessions, default_id = get_mycycle_sessions(include_inactive=True)
        if not sessions:
            return
        mapping = {s['name']: s['id'] for s in sessions}
        session_names.clear()
        session_names.update(mapping)
        session_dropdown['values'] = list(mapping.keys())
        target_id = select_id or config.get_setting('mycycle_primary_session_id') or default_id
        target_name = next((s['name'] for s in sessions if s['id'] == target_id), sessions[0]['name'])
        selected_session_name.set(target_name)

    def create_cycle_session_prompt():
        session_name = simpledialog.askstring("Create MyCycle Session", "Session name:", parent=settings_window)
        if not session_name or not session_name.strip():
            return
        created_id = create_mycycle_session(session_name.strip(), created_by=config.get_setting("CHANNEL") or "streamer")
        refresh_session_dropdown(select_id=created_id)

    def open_session_manager_window():
        manager = tk.Toplevel(settings_window)
        manager.title("Manage MyCycle Sessions")
        manager.transient(settings_window)
        manager.attributes('-topmost', True)
        center_toplevel(manager, 760, 420)

        ttk.Label(manager, text="Manage active state, view leaderboard, or delete sessions.", style="Small.TLabel").pack(anchor="w", padx=12, pady=(10, 6))
        rows_host = ttk.Frame(manager, style="App.TFrame")
        rows_host.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        def render_manager_rows():
            for child in rows_host.winfo_children():
                child.destroy()

            sessions, _ = get_mycycle_sessions(include_inactive=True)
            for row_index, session in enumerate(sessions):
                row = ttk.Frame(rows_host, style="App.TFrame")
                row.grid(row=row_index, column=0, sticky="ew", pady=3)
                rows_host.grid_columnconfigure(0, weight=1)

                is_active = session.get('active', True)
                state_text = "Active" if is_active else "Inactive"
                session_name = session.get('name', 'Unknown')
                if session.get('is_default'):
                    session_name += " • default"

                ttk.Label(row, text=session_name).pack(side="left")
                ttk.Label(
                    row,
                    text=state_text,
                    style="Success.Small.TLabel" if is_active else "Danger.Small.TLabel"
                ).pack(side="left", padx=(8, 0))

                def toggle_session(sid=session.get('id')):
                    with MYCYCLE_LOCK:
                        data = load_mycycle_data()
                        target = data.get('sessions', {}).get(sid)
                        if not target:
                            return
                        if target.get('is_default'):
                            messagebox.showinfo("MyCycle", "Default season sessions cannot be toggled off.", parent=manager)
                            return
                        target['active'] = not target.get('active', True)
                        save_mycycle_data(data)
                    render_manager_rows()
                    refresh_session_dropdown(select_id=sid)

                def open_session_leaderboard(sid=session.get('id')):
                    open_mycycle_leaderboard_window(settings_window, initial_session_id=sid)

                def delete_session(sid=session.get('id')):
                    ok, msg = delete_mycycle_session(sid)
                    if not ok:
                        messagebox.showinfo("MyCycle", msg, parent=manager)
                        return
                    render_manager_rows()
                    refresh_session_dropdown()

                ttk.Button(row, text="X", width=3, command=delete_session, style="SessionDelete.TButton").pack(side="right", padx=(6, 0))
                ttk.Button(
                    row,
                    text="Deactivate" if is_active else "Activate",
                    command=toggle_session,
                    style="SessionInactive.TButton" if is_active else "SessionActive.TButton"
                ).pack(side="right", padx=(6, 0))
                ttk.Button(row, text="Leaderboard", command=open_session_leaderboard).pack(side="right")

        render_manager_rows()

    ttk.Button(mycycle_tab, text="Manage Sessions", command=open_session_manager_window).grid(row=6, column=3, sticky="w", padx=(8, 0), pady=(10, 2))
    ttk.Button(mycycle_tab, text="Create Session", command=create_cycle_session_prompt).grid(row=7, column=0, sticky="w", pady=(8, 0))
    ttk.Button(mycycle_tab, text="View Leaderboard", command=lambda: open_mycycle_leaderboard_window(settings_window)).grid(row=7, column=1, sticky="w", pady=(8, 0))
    ttk.Label(mycycle_tab, text="Tip: Primary session is shown first in leaderboard pagination across active sessions.", style="Small.TLabel").grid(row=8, column=0, columnspan=4, sticky="w", pady=(8, 0))

    # --- MyTeams tab ---
    teams_sections = ttk.Notebook(teams_tab)
    teams_sections.grid(row=0, column=0, sticky="nsew")
    teams_tab.grid_columnconfigure(0, weight=1)
    teams_tab.grid_rowconfigure(0, weight=1)

    teams_settings_tab = ttk.Frame(teams_sections, style="App.TFrame", padding=10)
    teams_management_tab = ttk.Frame(teams_sections, style="App.TFrame", padding=10)
    teams_sections.add(teams_settings_tab, text="Team Settings")
    teams_sections.add(teams_management_tab, text="Team Management")

    teams_settings_tab.grid_columnconfigure(0, weight=1)
    teams_enabled_var = tk.BooleanVar(value=parse_boolean_token(config.get_setting("teams_enabled"), default=True))
    ttk.Checkbutton(teams_settings_tab, text="Enable MyTeams Commands", variable=teams_enabled_var).grid(row=0, column=0, sticky="w", pady=(0, 10))

    settings_columns = ttk.Frame(teams_settings_tab, style="App.TFrame")
    settings_columns.grid(row=1, column=0, sticky="ew")
    settings_columns.grid_columnconfigure(0, weight=1)
    settings_columns.grid_columnconfigure(1, weight=1)
    settings_columns.grid_rowconfigure(1, weight=1)

    tep_settings_frame = ttk.LabelFrame(settings_columns, text="TEP Settings", padding=10)
    tep_settings_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
    bonus_settings_frame = ttk.LabelFrame(settings_columns, text="Bonus Settings", padding=10)
    bonus_settings_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

    ttk.Label(tep_settings_frame, text="Points Counting Mode").grid(row=0, column=0, sticky="w", pady=(0, 6))
    teams_points_mode_var = tk.StringVar(value=config.get_setting("teams_points_mode") or "active")
    ttk.Combobox(
        tep_settings_frame,
        textvariable=teams_points_mode_var,
        values=["season", "active"],
        width=14,
        state="readonly"
    ).grid(row=0, column=1, sticky="w", pady=(0, 6), padx=(8, 0))

    ttk.Label(tep_settings_frame, text="Max Team Size").grid(row=1, column=0, sticky="w", pady=(0, 6))
    teams_max_size_entry = ttk.Entry(tep_settings_frame, width=12, justify='center')
    teams_max_size_entry.grid(row=1, column=1, sticky="w", pady=(0, 6), padx=(8, 0))
    teams_max_size_entry.insert(0, config.get_setting("teams_max_size") or "25")

    ttk.Label(tep_settings_frame, text="TEP Threshold").grid(row=2, column=0, sticky="w", pady=(0, 6))
    teams_tep_threshold_entry = ttk.Entry(tep_settings_frame, width=12, justify='center')
    teams_tep_threshold_entry.grid(row=2, column=1, sticky="w", pady=(0, 6), padx=(8, 0))
    teams_tep_threshold_entry.insert(0, config.get_setting("teams_tep_threshold") or "40")

    ttk.Label(tep_settings_frame, text="TEP per Race").grid(row=3, column=0, sticky="w", pady=(0, 6))
    teams_tep_per_race_entry = ttk.Entry(tep_settings_frame, width=12, justify='center')
    teams_tep_per_race_entry.grid(row=3, column=1, sticky="w", pady=(0, 6), padx=(8, 0))
    teams_tep_per_race_entry.insert(0, config.get_setting("teams_tep_per_race") or "1")

    ttk.Label(tep_settings_frame, text="TEP Bonus %/Cooldown (min)").grid(row=4, column=0, sticky="w", pady=(0, 6))
    tep_bonus_frame = ttk.Frame(tep_settings_frame, style="App.TFrame")
    tep_bonus_frame.grid(row=4, column=1, sticky="w", pady=(0, 6), padx=(8, 0))
    teams_tep_bonus_duration_entry = ttk.Entry(tep_bonus_frame, width=5, justify='center')
    teams_tep_bonus_duration_entry.pack(side="left")
    teams_tep_bonus_duration_entry.insert(0, config.get_setting("teams_tep_bonus_duration_minutes") or "15")
    ttk.Label(tep_bonus_frame, text="/").pack(side="left", padx=2)
    teams_tep_bits_cooldown_entry = ttk.Entry(tep_bonus_frame, width=5, justify='center')
    teams_tep_bits_cooldown_entry.pack(side="left")
    teams_tep_bits_cooldown_entry.insert(0, config.get_setting("teams_tep_bits_cooldown_minutes") or "60")
    ttk.Label(tep_settings_frame, text="TEP Cap Member/Team (daily)").grid(row=5, column=0, sticky="w", pady=(0, 6))
    tep_caps_frame = ttk.Frame(tep_settings_frame, style="App.TFrame")
    tep_caps_frame.grid(row=5, column=1, sticky="w", pady=(0, 6), padx=(8, 0))
    teams_tep_member_daily_cap_entry = ttk.Entry(tep_caps_frame, width=5, justify='center')
    teams_tep_member_daily_cap_entry.pack(side="left")
    teams_tep_member_daily_cap_entry.insert(0, config.get_setting("teams_tep_member_daily_cap") or "10")
    ttk.Label(tep_caps_frame, text="/").pack(side="left", padx=2)
    teams_tep_team_daily_cap_entry = ttk.Entry(tep_caps_frame, width=5, justify='center')
    teams_tep_team_daily_cap_entry.pack(side="left")
    teams_tep_team_daily_cap_entry.insert(0, config.get_setting("teams_tep_team_daily_cap") or "100")
    ttk.Label(bonus_settings_frame, text="Bonus Bits Threshold").grid(row=0, column=0, sticky="w", pady=(0, 6))
    teams_bonus_bits_threshold_entry = ttk.Entry(bonus_settings_frame, width=10, justify='center')
    teams_bonus_bits_threshold_entry.grid(row=0, column=1, sticky="w", pady=(0, 6), padx=(8, 0))
    teams_bonus_bits_threshold_entry.insert(0, config.get_setting("teams_bonus_bits_threshold") or "1000")

    ttk.Label(bonus_settings_frame, text="Bonus Duration (min)").grid(row=1, column=0, sticky="w", pady=(0, 6))
    teams_bonus_duration_entry = ttk.Entry(bonus_settings_frame, width=10, justify='center')
    teams_bonus_duration_entry.grid(row=1, column=1, sticky="w", pady=(0, 6), padx=(8, 0))
    teams_bonus_duration_entry.insert(0, config.get_setting("teams_bonus_duration_minutes") or "20")

    ttk.Label(bonus_settings_frame, text="Bonus Weights 15%/25%/35%/67%").grid(row=2, column=0, sticky="nw", pady=(0, 6))
    bonus_weights_frame = ttk.Frame(bonus_settings_frame, style="App.TFrame")
    bonus_weights_frame.grid(row=2, column=1, sticky="w", pady=(0, 6), padx=(8, 0))
    ttk.Label(bonus_weights_frame, text="15%", width=4, anchor="w").grid(row=0, column=0, sticky="w")
    teams_bonus_weight_15_entry = ttk.Entry(bonus_weights_frame, width=4, justify='center')
    teams_bonus_weight_15_entry.grid(row=0, column=1, sticky="w", pady=(0, 2))
    teams_bonus_weight_15_entry.insert(0, config.get_setting("teams_bonus_weight_15") or "33")
    ttk.Label(bonus_weights_frame, text="25%", width=4, anchor="w").grid(row=1, column=0, sticky="w")
    teams_bonus_weight_25_entry = ttk.Entry(bonus_weights_frame, width=4, justify='center')
    teams_bonus_weight_25_entry.grid(row=1, column=1, sticky="w", pady=(0, 2))
    teams_bonus_weight_25_entry.insert(0, config.get_setting("teams_bonus_weight_25") or "33")
    ttk.Label(bonus_weights_frame, text="35%", width=4, anchor="w").grid(row=2, column=0, sticky="w")
    teams_bonus_weight_35_entry = ttk.Entry(bonus_weights_frame, width=4, justify='center')
    teams_bonus_weight_35_entry.grid(row=2, column=1, sticky="w", pady=(0, 2))
    teams_bonus_weight_35_entry.insert(0, config.get_setting("teams_bonus_weight_35") or "33")
    ttk.Label(bonus_weights_frame, text="67%", width=4, anchor="w").grid(row=3, column=0, sticky="w")
    teams_bonus_weight_67_entry = ttk.Entry(bonus_weights_frame, width=4, justify='center')
    teams_bonus_weight_67_entry.grid(row=3, column=1, sticky="w")
    teams_bonus_weight_67_entry.insert(0, config.get_setting("teams_bonus_weight_67") or "1")

    tep_helper_frame = ttk.LabelFrame(settings_columns, text="TEP Helper", padding=10)
    tep_helper_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
    ttk.Label(
        tep_helper_frame,
        text=(
            "TEP (Team Effort Points) is earned from team races and runs alongside bits bonus progress.\n"
            "• TEP Threshold: total TEP needed before the automatic TEP bonus triggers.\n"
            "• TEP per Race: TEP added per qualifying team race (before caps).\n"
            "• TEP Bonus %/Cooldown (min): the automatic TEP bonus percent and the minutes it is blocked after bits bonus activity.\n"
            "• TEP Cap Member/Team (daily): maximum TEP gain per member and per team each day to avoid runaway loops.\n"
            "• Points Counting Mode affects team scoreboards only and does not change TEP gain.\n"
            "• Max Team Size controls how many members can contribute to TEP and points."
        ),
        style="Small.TLabel",
        justify="left",
        wraplength=760
    ).grid(row=0, column=0, sticky="w")

    teams_tree = ttk.Treeview(teams_management_tab, columns=("team", "captain", "size", "recruiting", "bonus", "daily", "weekly", "season"), show='headings', height=10)
    for key, label, width in [
        ("team", "Team", 170),
        ("captain", "Captain", 120),
        ("size", "Members", 70),
        ("recruiting", "Recruiting", 90),
        ("bonus", "Bonus", 100),
        ("daily", "Daily Pts", 90),
        ("weekly", "Weekly Pts", 100),
        ("season", "Season Pts", 110),
    ]:
        teams_tree.heading(key, text=label)
        teams_tree.column(key, width=width, anchor='center')
    teams_tree.grid(row=0, column=0, sticky="nsew", pady=(0, 4))

    teams_management_tab.grid_columnconfigure(0, weight=1)
    teams_management_tab.grid_rowconfigure(0, weight=1)

    def refresh_teams_tree():
        for item in teams_tree.get_children():
            teams_tree.delete(item)

        with TEAM_DATA_LOCK:
            data = _load_team_data()
            channel_state = _get_channel_team_state(data, config.get_setting('CHANNEL'))
            channel_state['settings']['points_mode'] = teams_points_mode_var.get() or 'active'
            try:
                channel_state['settings']['max_team_size'] = max(2, int(teams_max_size_entry.get() or 25))
            except ValueError:
                channel_state['settings']['max_team_size'] = 25
            _save_team_data(data)

        for team_name, team in sorted(channel_state.get('teams', {}).items()):
            size = 1 + len(team.get('co_captains', [])) + len(team.get('members', []))
            daily_points = _compute_team_points(channel_state, team_name, window='daily')
            weekly_points = _compute_team_points(channel_state, team_name, window='weekly')
            season_points = _compute_team_points(channel_state, team_name, window='season')
            teams_tree.insert('', 'end', iid=team_name, values=(
                team_name,
                format_user_tag(team.get('captain')),
                size,
                'Yes' if team.get('is_recruiting') else 'No',
                team.get('active_bonus_label') or '—',
                f"{daily_points:,}",
                f"{weekly_points:,}",
                f"{season_points:,}",
            ))

    def generate_team_name_for_clipboard():
        name = _generate_team_name(config.get_setting('CHANNEL'))
        settings_window.clipboard_clear()
        settings_window.clipboard_append(name)
        messagebox.showinfo("MyTeams", f"Generated team name copied to clipboard:\n{name}", parent=settings_window)


    def add_team_from_settings():
        name = simpledialog.askstring("Create Team", "Team name:", parent=settings_window)
        normalized_name = _normalize_team_name(name) if name else ''
        if not normalized_name:
            return

        with TEAM_DATA_LOCK:
            channel_name = config.get_setting('CHANNEL')
            data = _load_team_data()
            channel_state = _get_channel_team_state(data, channel_name)
            taken = any(_normalize_team_name(existing).lower() == normalized_name.lower() for existing in channel_state.get('teams', {}))
            if taken:
                messagebox.showinfo("MyTeams", f"Team name '{normalized_name}' already exists.", parent=settings_window)
                return
            captain = _normalize_username(channel_name)
            channel_state['teams'][normalized_name] = {
                'captain': captain,
                'co_captains': [],
                'members': [],
                'member_meta': {},
                'logo': None,
                'is_recruiting': False,
                'inactive_days': None,
                'bits_bank': 0,
                'active_bonus': None,
                'active_bonus_label': None,
                'bonus_windows': [],
                'effort_bank': 0,
                'effort_daily': {},
                'created_at': datetime.now(timezone.utc).isoformat(),
            }
            _save_team_data(data)

        refresh_teams_tree()

    def delete_selected_team():
        selected = teams_tree.selection()
        if not selected:
            messagebox.showinfo("MyTeams", "Select a team to delete.", parent=settings_window)
            return
        team_name = selected[0]
        if not messagebox.askyesno("MyTeams", f"Delete team '{team_name}'?", parent=settings_window):
            return

        with TEAM_DATA_LOCK:
            channel_name = config.get_setting('CHANNEL')
            season_value = config.get_setting('season') or 'default'
            data = _load_team_data()
            channel_state = _get_channel_team_state(data, channel_name)
            channel_state.get('teams', {}).pop(team_name, None)
            channel_state['invites'] = [inv for inv in channel_state.get('invites', []) if inv.get('team') != team_name]
            _save_team_data(data)
        _remove_team_points_cache_entry(channel_name, season_value, team_name)

        refresh_teams_tree()

    def toggle_selected_team_recruiting():
        selected = teams_tree.selection()
        if not selected:
            messagebox.showinfo("MyTeams", "Select a team to toggle recruiting.", parent=settings_window)
            return
        team_name = selected[0]
        with TEAM_DATA_LOCK:
            data = _load_team_data()
            channel_state = _get_channel_team_state(data, config.get_setting('CHANNEL'))
            team = channel_state.get('teams', {}).get(team_name)
            if team:
                team['is_recruiting'] = not bool(team.get('is_recruiting'))
                _save_team_data(data)
        refresh_teams_tree()

    def rename_selected_team():
        selected = teams_tree.selection()
        if not selected:
            messagebox.showinfo("MyTeams", "Select a team to rename.", parent=settings_window)
            return

        current_name = selected[0]
        requested_name = simpledialog.askstring("Rename Team", f"New name for '{current_name}':", initialvalue=current_name, parent=settings_window)
        normalized_name = _normalize_team_name(requested_name) if requested_name else ''
        if not normalized_name:
            return

        if _normalize_team_name(current_name).lower() == normalized_name.lower():
            return

        with TEAM_DATA_LOCK:
            channel_name = config.get_setting('CHANNEL')
            season_value = config.get_setting('season') or 'default'
            data = _load_team_data()
            channel_state = _get_channel_team_state(data, channel_name)
            teams = channel_state.get('teams', {})
            if current_name not in teams:
                messagebox.showinfo("MyTeams", "Selected team no longer exists.", parent=settings_window)
                return
            taken = any(_normalize_team_name(name).lower() == normalized_name.lower() for name in teams if name != current_name)
            if taken:
                messagebox.showinfo("MyTeams", f"Team name '{normalized_name}' already exists.", parent=settings_window)
                return

            team_payload = teams.pop(current_name)
            teams[normalized_name] = team_payload
            for invite in channel_state.get('invites', []):
                if invite.get('team') == current_name:
                    invite['team'] = normalized_name
            _save_team_data(data)

        _rename_team_points_cache_entry(channel_name, season_value, current_name, normalized_name)
        refresh_teams_tree()

    teams_actions = ttk.Frame(teams_management_tab, style="App.TFrame")
    teams_actions.grid(row=1, column=0, sticky="w", pady=(4, 0))
    ttk.Button(teams_actions, text="Refresh", command=refresh_teams_tree).pack(side="left", padx=(0, 6))
    ttk.Button(teams_actions, text="Generate Team Name", command=generate_team_name_for_clipboard).pack(side="left", padx=(0, 6))
    ttk.Button(teams_actions, text="Add Team", command=add_team_from_settings).pack(side="left", padx=(0, 6))
    ttk.Button(teams_actions, text="Toggle Recruiting", command=toggle_selected_team_recruiting).pack(side="left", padx=(0, 6))
    ttk.Button(teams_actions, text="Rename Team", command=rename_selected_team).pack(side="left", padx=(0, 6))
    ttk.Button(teams_actions, text="Delete Team", command=delete_selected_team).pack(side="left", padx=(0, 6))

    refresh_teams_tree()

    # --- Appearance tab ---
    ttk.Label(appearance_tab, text="Theme and visual preferences", style="Small.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))
    ttk.Label(appearance_tab, text="UI Theme").grid(row=1, column=0, sticky="w", pady=(0, 4))

    selected_theme = tk.StringVar(value=config.get_setting("UI_THEME") or app_style.theme_use())
    available_themes = get_available_ui_themes()
    if selected_theme.get() not in available_themes:
        available_themes = [selected_theme.get()] + available_themes

    theme_combobox = ttk.Combobox(appearance_tab, textvariable=selected_theme, values=available_themes, width=24, state="readonly")
    theme_combobox.grid(row=1, column=1, sticky="w", pady=(0, 4), padx=(8, 0))

    def apply_selected_theme(event=None):
        try:
            apply_theme(selected_theme.get())
            config.set_setting("UI_THEME", selected_theme.get(), persistent=True)
        except Exception as e:
            messagebox.showerror("Theme Error", f"Could not apply theme: {e}")

    theme_combobox.bind('<<ComboboxSelected>>', apply_selected_theme)


    # --- Overlay tabs ---
    race_overlay_tab.grid_columnconfigure(0, weight=1)

    ttk.Label(
        race_overlay_tab,
        text="Control OBS overlay visuals from the desktop app",
        style="Small.TLabel"
    ).grid(row=0, column=0, sticky="w", pady=(0, 8))

    # Race/BR results overlay settings

    core_overlay_frame = ttk.LabelFrame(race_overlay_tab, text="Results Display", style="Card.TLabelframe")
    core_overlay_frame.grid(row=0, column=0, sticky="nsew")
    core_overlay_frame.grid_columnconfigure(0, weight=1)

    overlay_fields_frame = ttk.Frame(core_overlay_frame, style="App.TFrame")
    overlay_fields_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=(8, 6))
    overlay_fields_frame.grid_columnconfigure(0, weight=1)

    ttk.Label(overlay_fields_frame, text="Stats Rotation (seconds)").grid(row=0, column=0, sticky="w", pady=(0, 4))
    overlay_rotation_entry = ttk.Entry(overlay_fields_frame, width=12, justify='center')
    overlay_rotation_entry.grid(row=0, column=1, sticky="w", pady=(0, 4), padx=(12, 0))
    overlay_rotation_entry.insert(0, config.get_setting("overlay_rotation_seconds") or "10")

    ttk.Label(overlay_fields_frame, text="Data Refresh (seconds)").grid(row=1, column=0, sticky="w", pady=(0, 4))
    overlay_refresh_entry = ttk.Entry(overlay_fields_frame, width=12, justify='center')
    overlay_refresh_entry.grid(row=1, column=1, sticky="w", pady=(0, 4), padx=(12, 0))
    overlay_refresh_entry.insert(0, config.get_setting("overlay_refresh_seconds") or "3")

    ttk.Label(overlay_fields_frame, text="Server Port").grid(row=2, column=0, sticky="w", pady=(0, 4))
    overlay_port_entry = ttk.Entry(overlay_fields_frame, width=12, justify='center')
    overlay_port_entry.grid(row=2, column=1, sticky="w", pady=(0, 4), padx=(12, 0))
    overlay_port_entry.insert(0, config.get_setting("overlay_server_port") or "5000")

    ttk.Label(overlay_fields_frame, text="Theme").grid(row=3, column=0, sticky="w", pady=(0, 4))
    overlay_theme_var = tk.StringVar(value=(config.get_setting("overlay_theme") or "midnight"))
    overlay_theme_combo = ttk.Combobox(
        overlay_fields_frame,
        textvariable=overlay_theme_var,
        values=["midnight", "ocean", "sunset", "forest", "mono", "violethearts"],
        width=18,
        state="readonly"
    )
    overlay_theme_combo.grid(row=3, column=1, sticky="w", pady=(0, 4), padx=(12, 0))

    ttk.Label(overlay_fields_frame, text="Card Opacity (65-100)").grid(row=4, column=0, sticky="w", pady=(0, 4))
    overlay_opacity_entry = ttk.Entry(overlay_fields_frame, width=12, justify='center')
    overlay_opacity_entry.grid(row=4, column=1, sticky="w", pady=(0, 4), padx=(12, 0))
    overlay_opacity_entry.insert(0, config.get_setting("overlay_card_opacity") or "84")

    ttk.Label(overlay_fields_frame, text="Text Scale (75-175)").grid(row=5, column=0, sticky="w", pady=(0, 4))
    overlay_text_scale_entry = ttk.Entry(overlay_fields_frame, width=12, justify='center')
    overlay_text_scale_entry.grid(row=5, column=1, sticky="w", pady=(0, 4), padx=(12, 0))
    overlay_text_scale_entry.insert(0, config.get_setting("overlay_text_scale") or "100")

    overlay_show_medals_var = tk.BooleanVar(value=str(config.get_setting("overlay_show_medals") or "True") == "True")
    overlay_compact_rows_var = tk.BooleanVar(value=str(config.get_setting("overlay_compact_rows") or "False") == "True")
    overlay_horizontal_layout_var = tk.BooleanVar(value=str(config.get_setting("overlay_horizontal_layout") or "False") == "True")

    overlay_toggles_frame = ttk.Frame(core_overlay_frame, style="App.TFrame")
    overlay_toggles_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 8))

    ttk.Checkbutton(overlay_toggles_frame, text="Show top-3 medal emotes", variable=overlay_show_medals_var).grid(row=0, column=0, sticky="w", pady=(0, 2))
    ttk.Checkbutton(overlay_toggles_frame, text="Compact row spacing", variable=overlay_compact_rows_var).grid(row=1, column=0, sticky="w", pady=(0, 2))
    ttk.Checkbutton(overlay_toggles_frame, text="Horizontal ticker layout (1080x100)", variable=overlay_horizontal_layout_var).grid(row=2, column=0, sticky="w", pady=(0, 2))

    # Horizontal ticker settings
    race_horizontal_overlay_tab.grid_columnconfigure(0, weight=1)
    horizontal_feed_frame = ttk.LabelFrame(race_horizontal_overlay_tab, text="Feed Items", style="Card.TLabelframe")
    horizontal_feed_frame.grid(row=0, column=0, sticky="nsew")
    horizontal_feed_frame.grid_columnconfigure(0, weight=1)

    overlay_horizontal_feed_season_var = tk.BooleanVar(value=str(config.get_setting("overlay_horizontal_feed_season") or "True") == "True")
    overlay_horizontal_feed_today_var = tk.BooleanVar(value=str(config.get_setting("overlay_horizontal_feed_today") or "True") == "True")
    overlay_horizontal_feed_races_season_var = tk.BooleanVar(value=str(config.get_setting("overlay_horizontal_feed_races_season") or "True") == "True")
    overlay_horizontal_feed_brs_season_var = tk.BooleanVar(value=str(config.get_setting("overlay_horizontal_feed_brs_season") or "True") == "True")
    overlay_horizontal_feed_races_today_var = tk.BooleanVar(value=str(config.get_setting("overlay_horizontal_feed_races_today") or "True") == "True")
    overlay_horizontal_feed_brs_today_var = tk.BooleanVar(value=str(config.get_setting("overlay_horizontal_feed_brs_today") or "True") == "True")
    overlay_horizontal_feed_myteams_var = tk.BooleanVar(value=str(config.get_setting("overlay_horizontal_feed_myteams") or "True") == "True")
    overlay_horizontal_feed_previous_race_var = tk.BooleanVar(value=str(config.get_setting("overlay_horizontal_feed_previous_race") or "True") == "True")
    overlay_horizontal_feed_events_var = tk.BooleanVar(value=str(config.get_setting("overlay_horizontal_feed_events") or "True") == "True")

    race_feed_frame = ttk.Frame(horizontal_feed_frame, style="App.TFrame")
    race_feed_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=(8, 6))
    race_feed_frame.grid_columnconfigure(0, weight=1)
    ttk.Label(race_feed_frame, text="Race and BR ticker feed", style="Small.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 2))
    ttk.Checkbutton(race_feed_frame, text="Top 10 Season", variable=overlay_horizontal_feed_season_var).grid(row=1, column=0, sticky="w", pady=(0, 2))
    ttk.Checkbutton(race_feed_frame, text="Top 10 Today", variable=overlay_horizontal_feed_today_var).grid(row=2, column=0, sticky="w", pady=(0, 2))
    ttk.Checkbutton(race_feed_frame, text="Top 10 Races (Season)", variable=overlay_horizontal_feed_races_season_var).grid(row=3, column=0, sticky="w", pady=(0, 2))
    ttk.Checkbutton(race_feed_frame, text="Top 10 BRs (Season)", variable=overlay_horizontal_feed_brs_season_var).grid(row=4, column=0, sticky="w", pady=(0, 2))
    ttk.Checkbutton(race_feed_frame, text="Top 10 Races (Today)", variable=overlay_horizontal_feed_races_today_var).grid(row=5, column=0, sticky="w", pady=(0, 2))
    ttk.Checkbutton(race_feed_frame, text="Top 10 BRs (Today)", variable=overlay_horizontal_feed_brs_today_var).grid(row=6, column=0, sticky="w", pady=(0, 2))
    ttk.Checkbutton(race_feed_frame, text="Top MyTeams", variable=overlay_horizontal_feed_myteams_var).grid(row=7, column=0, sticky="w", pady=(0, 2))
    ttk.Checkbutton(race_feed_frame, text="Top 10 Previous Race", variable=overlay_horizontal_feed_previous_race_var).grid(row=8, column=0, sticky="w", pady=(0, 2))
    ttk.Checkbutton(race_feed_frame, text="Ticker Events", variable=overlay_horizontal_feed_events_var).grid(row=9, column=0, sticky="w")

    overlay_horizontal_feed_tilt_current_var = tk.BooleanVar(value=str(config.get_setting("overlay_horizontal_feed_tilt_current") or "True") == "True")
    overlay_horizontal_feed_tilt_today_var = tk.BooleanVar(value=str(config.get_setting("overlay_horizontal_feed_tilt_today") or "True") == "True")
    overlay_horizontal_feed_tilt_season_var = tk.BooleanVar(value=str(config.get_setting("overlay_horizontal_feed_tilt_season") or "True") == "True")
    overlay_horizontal_feed_tilt_last_run_var = tk.BooleanVar(value=str(config.get_setting("overlay_horizontal_feed_tilt_last_run") or "True") == "True")

    tilt_horizontal_overlay_tab.grid_columnconfigure(0, weight=1)
    tilt_horizontal_feed_frame = ttk.LabelFrame(tilt_horizontal_overlay_tab, text="Feed Items", style="Card.TLabelframe")
    tilt_horizontal_feed_frame.grid(row=0, column=0, sticky="nsew")
    tilt_horizontal_feed_frame.grid_columnconfigure(0, weight=1)

    tilt_feed_frame = ttk.Frame(tilt_horizontal_feed_frame, style="App.TFrame")
    tilt_feed_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=(8, 8))
    tilt_feed_frame.grid_columnconfigure(0, weight=1)
    ttk.Label(tilt_feed_frame, text="Tilt ticker feed", style="Small.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 2))
    ttk.Checkbutton(tilt_feed_frame, text="Tilt Current Run", variable=overlay_horizontal_feed_tilt_current_var).grid(row=1, column=0, sticky="w", pady=(0, 2))
    ttk.Checkbutton(tilt_feed_frame, text="Tilt Today Standings", variable=overlay_horizontal_feed_tilt_today_var).grid(row=2, column=0, sticky="w", pady=(0, 2))
    ttk.Checkbutton(tilt_feed_frame, text="Tilt Season Standings", variable=overlay_horizontal_feed_tilt_season_var).grid(row=3, column=0, sticky="w", pady=(0, 2))
    ttk.Checkbutton(tilt_feed_frame, text="Tilt Last Run", variable=overlay_horizontal_feed_tilt_last_run_var).grid(row=4, column=0, sticky="w")

    # Tilt overlay settings
    tilt_overlay_tab.grid_columnconfigure(0, weight=1)
    tilt_overlay_frame = ttk.LabelFrame(tilt_overlay_tab, text="Tilt Display", style="Card.TLabelframe")
    tilt_overlay_frame.grid(row=0, column=0, sticky="nsew")
    tilt_overlay_frame.grid_columnconfigure(0, weight=1)

    tilt_fields_frame = ttk.Frame(tilt_overlay_frame, style="App.TFrame")
    tilt_fields_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=(8, 8))
    for col in range(3):
        tilt_fields_frame.grid_columnconfigure(col, weight=1)

    ttk.Label(tilt_fields_frame, text="Starting Lifetime XP", style="Small.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 2))
    tilt_lifetime_base_entry = ttk.Entry(tilt_fields_frame, width=12, justify='center')
    tilt_lifetime_base_entry.grid(row=1, column=0, sticky="w", pady=(0, 6), padx=(0, 12))
    tilt_lifetime_base_entry.insert(0, config.get_setting("tilt_lifetime_base_xp") or "0")

    ttk.Label(tilt_fields_frame, text="Season Best Level", style="Small.TLabel").grid(row=0, column=1, sticky="w", pady=(0, 2))
    tilt_season_best_entry = ttk.Entry(tilt_fields_frame, width=12, justify='center')
    tilt_season_best_entry.grid(row=1, column=1, sticky="w", pady=(0, 6), padx=(0, 12))
    tilt_season_best_entry.insert(0, config.get_setting("tilt_season_best_level") or "1")

    ttk.Label(tilt_fields_frame, text="Personal Best Level", style="Small.TLabel").grid(row=0, column=2, sticky="w", pady=(0, 2))
    tilt_personal_best_entry = ttk.Entry(tilt_fields_frame, width=12, justify='center')
    tilt_personal_best_entry.grid(row=1, column=2, sticky="w", pady=(0, 6))
    tilt_personal_best_entry.insert(0, config.get_setting("tilt_personal_best_level") or "1")

    ttk.Label(tilt_fields_frame, text="Tilt Theme", style="Small.TLabel").grid(row=2, column=0, sticky="w", pady=(0, 2))
    tilt_overlay_theme_var = tk.StringVar(value=(config.get_setting("tilt_overlay_theme") or config.get_setting("overlay_theme") or "midnight"))
    ttk.Combobox(
        tilt_fields_frame,
        textvariable=tilt_overlay_theme_var,
        values=["midnight", "ocean", "sunset", "forest", "mono", "violethearts"],
        width=18,
        state="readonly"
    ).grid(row=3, column=0, sticky="w", pady=(0, 6), padx=(0, 12))

    ttk.Label(tilt_fields_frame, text="Scroll Step (px)", style="Small.TLabel").grid(row=2, column=1, sticky="w", pady=(0, 2))
    tilt_scroll_step_entry = ttk.Entry(tilt_fields_frame, width=12, justify='center')
    tilt_scroll_step_entry.grid(row=3, column=1, sticky="w", pady=(0, 6), padx=(0, 12))
    tilt_scroll_step_entry.insert(0, config.get_setting("tilt_scroll_step_px") or "1")

    ttk.Label(tilt_fields_frame, text="Scroll Tick (ms)", style="Small.TLabel").grid(row=2, column=2, sticky="w", pady=(0, 2))
    tilt_scroll_interval_entry = ttk.Entry(tilt_fields_frame, width=12, justify='center')
    tilt_scroll_interval_entry.grid(row=3, column=2, sticky="w", pady=(0, 6))
    tilt_scroll_interval_entry.insert(0, config.get_setting("tilt_scroll_interval_ms") or "40")

    ttk.Label(tilt_fields_frame, text="Edge Pause (ms)", style="Small.TLabel").grid(row=4, column=0, sticky="w", pady=(0, 2))
    tilt_scroll_pause_entry = ttk.Entry(tilt_fields_frame, width=12, justify='center')
    tilt_scroll_pause_entry.grid(row=5, column=0, sticky="w", pady=(0, 8), padx=(0, 12))
    tilt_scroll_pause_entry.insert(0, config.get_setting("tilt_scroll_pause_ms") or "900")

    ttk.Label(
        tilt_fields_frame,
        text="Tip: Best level settings are minimum floors for Season/Personal Best output files.",
        style="Small.TLabel",
        wraplength=420,
        justify="left"
    ).grid(row=6, column=0, columnspan=3, sticky="w")

    ttk.Label(
        race_overlay_tab,
        text="Restart MyStats after changing port. Visual changes apply on next refresh.",
        style="Small.TLabel"
    ).grid(row=2, column=0, sticky="w", pady=(8, 0))


    def reset_settings_defaults():
        chunk_alert_var.set(True)
        announce_delay_var.set(False)
        reset_audio_var.set(False)
        minimize_to_tray_var.set(False)
        app_language_var.set(LANGUAGE_DISPLAY_NAMES['en'])
        chat_br_results_var.set(True)
        chat_race_results_var.set(True)
        chat_tilt_results_var.set(True)
        chat_all_commands_var.set(True)
        chat_leaderboard_show_medals_var.set(True)
        competitive_raid_monitor_enabled_var.set(False)
        chat_narrative_alerts_var.set(True)
        chat_tilt_suppress_offline_var.set(True)
        chat_tilt_redact_survivor_names_var.set(False)
        narrative_alert_grinder_var.set(True)
        narrative_alert_winmilestone_var.set(True)
        narrative_alert_leadchange_var.set(True)
        narrative_alert_cooldown_entry.delete(0, tk.END)
        narrative_alert_cooldown_entry.insert(0, "3")
        narrative_alert_min_gap_entry.delete(0, tk.END)
        narrative_alert_min_gap_entry.insert(0, "500")
        narrative_alert_max_items_entry.delete(0, tk.END)
        narrative_alert_max_items_entry.insert(0, "3")
        race_narrative_alerts_var.set(True)
        race_narrative_grinder_var.set(True)
        race_narrative_winmilestone_var.set(True)
        race_narrative_leadchange_var.set(True)
        race_narrative_cooldown_entry.delete(0, tk.END)
        race_narrative_cooldown_entry.insert(0, "3")
        race_narrative_min_gap_entry.delete(0, tk.END)
        race_narrative_min_gap_entry.insert(0, "500")
        race_narrative_max_items_entry.delete(0, tk.END)
        race_narrative_max_items_entry.insert(0, "3")
        tiltsurvivors_min_levels_entry.delete(0, tk.END)
        tiltsurvivors_min_levels_entry.insert(0, "20")
        season_quests_enabled_var.set(True)
        rivals_enabled_var.set(True)
        selected_max_names.set("25")
        rivals_min_races_entry.delete(0, tk.END)
        rivals_min_races_entry.insert(0, "50")
        rivals_max_gap_entry.delete(0, tk.END)
        rivals_max_gap_entry.insert(0, "1500")
        rivals_pair_count_entry.delete(0, tk.END)
        rivals_pair_count_entry.insert(0, "25")
        mycycle_enabled_var.set(True)
        mycycle_announce_var.set(True)
        mycycle_include_br_var.set(False)
        mycycle_min_place_entry.delete(0, tk.END)
        mycycle_min_place_entry.insert(0, "1")
        mycycle_max_place_entry.delete(0, tk.END)
        mycycle_max_place_entry.insert(0, "10")
        season_quest_races_entry.delete(0, tk.END)
        season_quest_races_entry.insert(0, "1000")
        season_quest_points_entry.delete(0, tk.END)
        season_quest_points_entry.insert(0, "500000")
        season_quest_race_hs_entry.delete(0, tk.END)
        season_quest_race_hs_entry.insert(0, "3000")
        season_quest_br_hs_entry.delete(0, tk.END)
        season_quest_br_hs_entry.insert(0, "3000")
        season_quest_tilt_levels_entry.delete(0, tk.END)
        season_quest_tilt_levels_entry.insert(0, "1000")
        season_quest_tilt_tops_entry.delete(0, tk.END)
        season_quest_tilt_tops_entry.insert(0, "100")
        season_quest_tilt_points_entry.delete(0, tk.END)
        season_quest_tilt_points_entry.insert(0, "500000")
        chunk_alert_trigger_entry.delete(0, tk.END)
        chunk_alert_trigger_entry.insert(0, "1000")
        delay_seconds_entry.delete(0, tk.END)
        delay_seconds_entry.insert(0, "0")
        overlay_rotation_entry.delete(0, tk.END)
        overlay_rotation_entry.insert(0, "10")
        overlay_refresh_entry.delete(0, tk.END)
        overlay_refresh_entry.insert(0, "3")
        overlay_port_entry.delete(0, tk.END)
        overlay_port_entry.insert(0, "5000")
        overlay_theme_var.set("midnight")
        overlay_opacity_entry.delete(0, tk.END)
        overlay_opacity_entry.insert(0, "84")
        overlay_text_scale_entry.delete(0, tk.END)
        overlay_text_scale_entry.insert(0, "100")
        overlay_show_medals_var.set(True)
        overlay_compact_rows_var.set(False)
        overlay_horizontal_layout_var.set(False)
        overlay_horizontal_feed_season_var.set(True)
        overlay_horizontal_feed_today_var.set(True)
        overlay_horizontal_feed_races_season_var.set(True)
        overlay_horizontal_feed_brs_season_var.set(True)
        overlay_horizontal_feed_races_today_var.set(True)
        overlay_horizontal_feed_brs_today_var.set(True)
        overlay_horizontal_feed_myteams_var.set(True)
        overlay_horizontal_feed_previous_race_var.set(True)
        overlay_horizontal_feed_events_var.set(True)
        overlay_horizontal_feed_tilt_current_var.set(True)
        overlay_horizontal_feed_tilt_today_var.set(True)
        overlay_horizontal_feed_tilt_season_var.set(True)
        overlay_horizontal_feed_tilt_last_run_var.set(True)
        tilt_lifetime_base_entry.delete(0, tk.END)
        tilt_lifetime_base_entry.insert(0, "0")
        tilt_season_best_entry.delete(0, tk.END)
        tilt_season_best_entry.insert(0, "1")
        tilt_personal_best_entry.delete(0, tk.END)
        tilt_personal_best_entry.insert(0, "1")
        tilt_overlay_theme_var.set("midnight")
        tilt_scroll_step_entry.delete(0, tk.END)
        tilt_scroll_step_entry.insert(0, "1")
        tilt_scroll_interval_entry.delete(0, tk.END)
        tilt_scroll_interval_entry.insert(0, "40")
        tilt_scroll_pause_entry.delete(0, tk.END)
        tilt_scroll_pause_entry.insert(0, "900")

    footer = ttk.Frame(settings_window, style="App.TFrame")
    footer.grid(row=1, column=0, sticky="ew", padx=20, pady=10)

    ttk.Button(footer, text=tr("Reset Defaults"), command=reset_settings_defaults).pack(side="left")

    def save_settings_and_close():
        def _bounded_int(raw_value, default_value, min_value, max_value):
            try:
                parsed = int(str(raw_value).strip())
            except (TypeError, ValueError):
                parsed = default_value
            return max(min_value, min(parsed, max_value))

        config.set_setting("CHANNEL", channel_entry.get(), persistent=True)
        selected_language_name = app_language_var.get()
        config.set_setting("app_language", app_language_name_to_code.get(selected_language_name, "en"), persistent=True)
        config.set_setting("minimize_to_tray", str(minimize_to_tray_var.get()), persistent=True)
        config.set_setting("chunk_alert", str(chunk_alert_var.get()), persistent=True)
        config.set_setting("chunk_alert_value", chunk_alert_trigger_entry.get(), persistent=True)
        config.set_setting("announcedelay", str(announce_delay_var.get()), persistent=True)
        config.set_setting("announcedelayseconds", delay_seconds_entry.get(), persistent=True)
        config.set_setting("reset_audio", str(reset_audio_var.get()), persistent=True)
        config.set_setting("audio_device", selected_device.get(), persistent=True)
        config.set_setting("UI_THEME", selected_theme.get(), persistent=True)
        config.set_setting("chat_br_results", str(chat_br_results_var.get()), persistent=True)
        config.set_setting("chat_race_results", str(chat_race_results_var.get()), persistent=True)
        config.set_setting("chat_leaderboard_show_medals", str(chat_leaderboard_show_medals_var.get()), persistent=True)
        config.set_setting("chat_tilt_results", str(chat_tilt_results_var.get()), persistent=True)
        config.set_setting("chat_tilt_suppress_offline", str(chat_tilt_suppress_offline_var.get()), persistent=True)
        config.set_setting("chat_tilt_redact_survivor_names", str(chat_tilt_redact_survivor_names_var.get()), persistent=True)
        config.set_setting("chat_all_commands", str(chat_all_commands_var.get()), persistent=True)
        config.set_setting("competitive_raid_monitor_enabled", str(competitive_raid_monitor_enabled_var.get()), persistent=True)
        config.set_setting("chat_narrative_alerts", str(chat_narrative_alerts_var.get()), persistent=True)
        config.set_setting("narrative_alert_grinder_enabled", str(narrative_alert_grinder_var.get()), persistent=True)
        config.set_setting("narrative_alert_winmilestone_enabled", str(narrative_alert_winmilestone_var.get()), persistent=True)
        config.set_setting("narrative_alert_leadchange_enabled", str(narrative_alert_leadchange_var.get()), persistent=True)
        config.set_setting("narrative_alert_cooldown_races", narrative_alert_cooldown_entry.get(), persistent=True)
        config.set_setting("narrative_alert_min_lead_change_points", narrative_alert_min_gap_entry.get(), persistent=True)
        config.set_setting("narrative_alert_max_items", narrative_alert_max_items_entry.get(), persistent=True)
        config.set_setting("race_narrative_alerts_enabled", str(race_narrative_alerts_var.get()), persistent=True)
        config.set_setting("race_narrative_grinder_enabled", str(race_narrative_grinder_var.get()), persistent=True)
        config.set_setting("race_narrative_winmilestone_enabled", str(race_narrative_winmilestone_var.get()), persistent=True)
        config.set_setting("race_narrative_leadchange_enabled", str(race_narrative_leadchange_var.get()), persistent=True)
        config.set_setting("race_narrative_alert_cooldown_races", race_narrative_cooldown_entry.get(), persistent=True)
        config.set_setting("race_narrative_alert_min_lead_change_points", race_narrative_min_gap_entry.get(), persistent=True)
        config.set_setting("race_narrative_alert_max_items", race_narrative_max_items_entry.get(), persistent=True)
        config.set_setting("tiltsurvivors_min_levels", tiltsurvivors_min_levels_entry.get(), persistent=True)
        config.set_setting("season_quests_enabled", str(season_quests_enabled_var.get()), persistent=True)
        season_target_bounds = {
            "season_quest_target_races": (1000, 0, 10000000),
            "season_quest_target_points": (500000, 0, 500000000),
            "season_quest_target_race_hs": (3000, 0, 1000000),
            "season_quest_target_br_hs": (3000, 0, 1000000),
            "season_quest_target_tilt_levels": (1000, 0, 1000000),
            "season_quest_target_tilt_tops": (100, 0, 1000000),
            "season_quest_target_tilt_points": (500000, 0, 500000000),
        }
        season_target_entries = {
            "season_quest_target_races": season_quest_races_entry,
            "season_quest_target_points": season_quest_points_entry,
            "season_quest_target_race_hs": season_quest_race_hs_entry,
            "season_quest_target_br_hs": season_quest_br_hs_entry,
            "season_quest_target_tilt_levels": season_quest_tilt_levels_entry,
            "season_quest_target_tilt_tops": season_quest_tilt_tops_entry,
            "season_quest_target_tilt_points": season_quest_tilt_points_entry,
        }
        for target_key, entry_widget in season_target_entries.items():
            default_value, min_value, max_value = season_target_bounds[target_key]
            target_value = _bounded_int(entry_widget.get(), default_value, min_value, max_value)
            config.set_setting(target_key, str(target_value), persistent=True)
        config.set_setting("rivals_enabled", str(rivals_enabled_var.get()), persistent=True)
        rivals_min_races = _bounded_int(rivals_min_races_entry.get(), 50, 1, RIVALS_MAX_MIN_RACES)
        rivals_max_gap = _bounded_int(rivals_max_gap_entry.get(), 1500, 0, RIVALS_MAX_POINT_GAP)
        rivals_pair_count = _bounded_int(rivals_pair_count_entry.get(), 25, 1, RIVALS_MAX_PAIRS)
        config.set_setting("rivals_min_races", str(rivals_min_races), persistent=True)
        config.set_setting("rivals_max_point_gap", str(rivals_max_gap), persistent=True)
        config.set_setting("rivals_pair_count", str(rivals_pair_count), persistent=True)
        config.set_setting("mycycle_enabled", str(mycycle_enabled_var.get()), persistent=True)
        config.set_setting("mycycle_announcements_enabled", str(mycycle_announce_var.get()), persistent=True)
        config.set_setting("mycycle_include_br", str(mycycle_include_br_var.get()), persistent=True)
        config.set_setting("mycycle_min_place", mycycle_min_place_entry.get(), persistent=True)
        config.set_setting("mycycle_max_place", mycycle_max_place_entry.get(), persistent=True)
        config.set_setting("teams_enabled", str(teams_enabled_var.get()), persistent=True)
        config.set_setting("teams_points_mode", teams_points_mode_var.get(), persistent=True)
        config.set_setting("teams_max_size", teams_max_size_entry.get(), persistent=True)
        config.set_setting("teams_bonus_bits_threshold", teams_bonus_bits_threshold_entry.get(), persistent=True)
        config.set_setting("teams_bonus_duration_minutes", teams_bonus_duration_entry.get(), persistent=True)
        config.set_setting("teams_tep_threshold", teams_tep_threshold_entry.get(), persistent=True)
        config.set_setting("teams_tep_per_race", teams_tep_per_race_entry.get(), persistent=True)
        config.set_setting("teams_tep_bonus_duration_minutes", teams_tep_bonus_duration_entry.get(), persistent=True)
        config.set_setting("teams_tep_bits_cooldown_minutes", teams_tep_bits_cooldown_entry.get(), persistent=True)
        config.set_setting("teams_tep_member_daily_cap", teams_tep_member_daily_cap_entry.get(), persistent=True)
        config.set_setting("teams_tep_team_daily_cap", teams_tep_team_daily_cap_entry.get(), persistent=True)
        config.set_setting("teams_bonus_weight_15", teams_bonus_weight_15_entry.get(), persistent=True)
        config.set_setting("teams_bonus_weight_25", teams_bonus_weight_25_entry.get(), persistent=True)
        config.set_setting("teams_bonus_weight_35", teams_bonus_weight_35_entry.get(), persistent=True)
        config.set_setting("teams_bonus_weight_67", teams_bonus_weight_67_entry.get(), persistent=True)
        selected_session_id = session_names.get(selected_session_name.get())
        if selected_session_id:
            config.set_setting("mycycle_primary_session_id", selected_session_id, persistent=True)
        config.set_setting("chat_max_names", selected_max_names.get(), persistent=True)
        config.set_setting("overlay_rotation_seconds", overlay_rotation_entry.get(), persistent=True)
        config.set_setting("overlay_refresh_seconds", overlay_refresh_entry.get(), persistent=True)
        config.set_setting("overlay_server_port", overlay_port_entry.get(), persistent=True)
        config.set_setting("overlay_theme", overlay_theme_var.get(), persistent=True)
        config.set_setting("overlay_card_opacity", overlay_opacity_entry.get(), persistent=True)
        config.set_setting("overlay_text_scale", overlay_text_scale_entry.get(), persistent=True)
        config.set_setting("overlay_show_medals", str(overlay_show_medals_var.get()), persistent=True)
        config.set_setting("overlay_compact_rows", str(overlay_compact_rows_var.get()), persistent=True)
        config.set_setting("overlay_horizontal_layout", str(overlay_horizontal_layout_var.get()), persistent=True)
        config.set_setting("overlay_horizontal_feed_season", str(overlay_horizontal_feed_season_var.get()), persistent=True)
        config.set_setting("overlay_horizontal_feed_today", str(overlay_horizontal_feed_today_var.get()), persistent=True)
        config.set_setting("overlay_horizontal_feed_races_season", str(overlay_horizontal_feed_races_season_var.get()), persistent=True)
        config.set_setting("overlay_horizontal_feed_brs_season", str(overlay_horizontal_feed_brs_season_var.get()), persistent=True)
        config.set_setting("overlay_horizontal_feed_races_today", str(overlay_horizontal_feed_races_today_var.get()), persistent=True)
        config.set_setting("overlay_horizontal_feed_brs_today", str(overlay_horizontal_feed_brs_today_var.get()), persistent=True)
        config.set_setting("overlay_horizontal_feed_myteams", str(overlay_horizontal_feed_myteams_var.get()), persistent=True)
        config.set_setting("overlay_horizontal_feed_previous_race", str(overlay_horizontal_feed_previous_race_var.get()), persistent=True)
        config.set_setting("overlay_horizontal_feed_events", str(overlay_horizontal_feed_events_var.get()), persistent=True)
        config.set_setting("overlay_horizontal_feed_tilt_current", str(overlay_horizontal_feed_tilt_current_var.get()), persistent=True)
        config.set_setting("overlay_horizontal_feed_tilt_today", str(overlay_horizontal_feed_tilt_today_var.get()), persistent=True)
        config.set_setting("overlay_horizontal_feed_tilt_season", str(overlay_horizontal_feed_tilt_season_var.get()), persistent=True)
        config.set_setting("overlay_horizontal_feed_tilt_last_run", str(overlay_horizontal_feed_tilt_last_run_var.get()), persistent=True)
        config.set_setting("tilt_lifetime_base_xp", tilt_lifetime_base_entry.get(), persistent=True)
        config.set_setting("tilt_season_best_level", tilt_season_best_entry.get(), persistent=True)
        config.set_setting("tilt_personal_best_level", tilt_personal_best_entry.get(), persistent=True)
        config.set_setting("tilt_overlay_theme", tilt_overlay_theme_var.get(), persistent=True)
        config.set_setting("tilt_scroll_step_px", tilt_scroll_step_entry.get(), persistent=True)
        config.set_setting("tilt_scroll_interval_ms", tilt_scroll_interval_entry.get(), persistent=True)
        config.set_setting("tilt_scroll_pause_ms", tilt_scroll_pause_entry.get(), persistent=True)
        settings_window.destroy()

    ttk.Button(footer, text=tr("Save and Close"), command=save_settings_and_close, style="Primary.TButton").pack(side="right")

def test_chunkaudio_playback():
    """
    Function to test the audio playback using the configured audio device and reset audio sound.
    """
    audio_device = config.get_setting('audio_device')
    audio_file_path = config.get_setting('chunk_alert_sound')

    if audio_file_path:
        play_audio_file(audio_file_path, device_name=audio_device)
    else:
        print("No reset audio file is set in the configuration.")

def test_audio_playback():
    """
    Function to test the audio playback using the configured audio device and reset audio sound.
    """
    audio_device = config.get_setting('audio_device')
    audio_file_path = config.get_setting('reset_audio_sound')

    if audio_file_path:
        play_audio_file(audio_file_path, device_name=audio_device)
    else:
        print("No reset audio file is set in the configuration.")


def on_close():
    global BOT_SHOULD_RUN

    if not is_forced_exit:
        confirm_exit = messagebox.askyesno(
            "Exit MyStats",
            "Are you sure you want to exit MyStats?"
        )
        if not confirm_exit:
            return

        force_exit_application()
        return

    # Disable the root window to prevent interaction
    root.attributes('-disabled', True)

    # Show the "Application is closing" popup
    def show_wait_window():
        wait_window = tk.Toplevel(root)
        wait_window.title("Please Wait")
        wait_window.geometry(
            f"300x100+{root.winfo_x() + (root.winfo_width() // 2) - 150}+"
            f"{root.winfo_y() + (root.winfo_height() // 2) - 50}"
        )
        wait_label = tk.Label(
            wait_window,
            text="Application is closing... please wait.",
            padx=20,
            pady=20
        )
        wait_label.pack()
        wait_window.grab_set()
        wait_window.transient(root)
        return wait_window

    # Create the "Please Wait" window
    wait_window = show_wait_window()

    # Schedule bot shutdown in the bot's event loop (when available)
    BOT_SHOULD_RUN = False
    if bot is not None and getattr(bot, "loop", None) is not None:
        asyncio.run_coroutine_threadsafe(bot.shutdown(), bot.loop)

    # Destroy the Tkinter windows after a delay
    def close_windows():
        sys.stdout = sys.__stdout__  # Reset stdout
        stop_system_tray_icon()
        wait_window.destroy()
        root.destroy()

    root.after(1000, close_windows)  # Adjust delay as necessary




def open_url(event):
    webbrowser.open("https://mystats.camwow.tv")


def open_dashboard():
    dashboard_url = f"http://127.0.0.1:{_load_overlay_server_port()}/dashboard"
    webbrowser.open_new(dashboard_url)


def open_rivals_dashboard():
    dashboard_url = f"http://127.0.0.1:{_load_overlay_server_port()}/dashboard#rivals"
    webbrowser.open_new(dashboard_url)


def build_stats_sidebar(parent):
    global total_points_label, total_count_label, avg_points_label, race_hs_label, br_hs_label
    global total_points_t_label, total_count_t_label, avg_points_t_label, race_hs_t_label, br_hs_t_label

    stats_container_frame = ttk.Frame(parent, style="App.TFrame")
    stats_container_frame.grid(row=0, column=0, rowspan=2, sticky='nw', padx=10, pady=10)

    season_stats_frame = ttk.LabelFrame(stats_container_frame, text="Season Statistics", style="Card.TLabelframe")
    season_stats_frame.pack(fill='x', pady=(0, 10))

    season_stat_labels = build_stats_labels(season_stats_frame)
    total_points_label = season_stat_labels["total_points"]
    total_count_label = season_stat_labels["total_count"]
    avg_points_label = season_stat_labels["avg_points"]
    race_hs_label = season_stat_labels["race_hs"]
    br_hs_label = season_stat_labels["br_hs"]

    todays_stats_frame = ttk.LabelFrame(stats_container_frame, text="Today's Statistics", style="Card.TLabelframe")
    todays_stats_frame.pack(fill='x')

    today_stat_labels = build_stats_labels(todays_stats_frame)
    total_points_t_label = today_stat_labels["total_points"]
    total_count_t_label = today_stat_labels["total_count"]
    avg_points_t_label = today_stat_labels["avg_points"]
    race_hs_t_label = today_stat_labels["race_hs"]
    br_hs_t_label = today_stat_labels["br_hs"]

    button_frame = ttk.Frame(stats_container_frame, style="App.TFrame")
    button_frame.pack(pady=(20, 0))

    button_width = 8
    button_frame.grid_columnconfigure(0, weight=1, uniform="sidebar_actions")
    button_frame.grid_columnconfigure(1, weight=1, uniform="sidebar_actions")

    settings_button = ttk.Button(
        button_frame,
        text="Settings",
        command=open_settings_window,
        width=button_width,
        style="Primary.TButton"
    )
    settings_button.grid(row=0, column=0, padx=5, pady=(0, 5))

    dashboards_button = ttk.Button(
        button_frame,
        text="MyStats Web Dashboards",
        command=open_dashboard,
        style="Primary.TButton"
    )
    dashboards_button.grid(row=1, column=0, columnspan=2, padx=5, pady=(0, 5), sticky='ew')

    events_button = ttk.Button(
        button_frame,
        text="Events",
        command=open_events_window,
        width=button_width,
        style="Primary.TButton"
    )
    events_button.grid(row=0, column=1, padx=5, pady=(0, 5))

    button_frame.grid_rowconfigure(3, weight=1)

    url_label = tk.Label(button_frame, text="https://mystats.camwow.tv", fg="blue", cursor="hand2", font=("Arial", 10, "underline"))
    url_label.grid(row=3, column=0, columnspan=2, pady=(85, 0), sticky="s")
    url_label.bind("<Button-1>", open_url)


def build_main_content(parent):
    global chatbot_label, login_button, text_area
    global season_quest_tree, rivals_tree, mycycle_tree, mycycle_session_label
    global mycycle_session_position_label, mycycle_prev_button, mycycle_next_button, mycycle_export_button

    top_frame1 = ttk.Frame(parent, style="App.TFrame")
    top_frame1.grid(row=0, column=1, sticky='ew', padx=(5, 0))

    title_label = ttk.Label(top_frame1, text="MyStats", style="Heading.TLabel")
    title_label.grid(row=0, column=0, sticky='w', padx=(5, 0))
    top_frame1.grid_columnconfigure(0, weight=1)

    login_button_frame = ttk.Frame(top_frame1, style="App.TFrame")
    login_button_frame.grid(row=0, column=1, sticky='e')

    chatbot_label = ttk.Label(login_button_frame, text="Current ChatBot", style="Small.TLabel")
    chatbot_label.grid(row=0, column=1, sticky='e', padx=(0, 5))

    login_button = ttk.Button(login_button_frame, text="Custom Bot Login", command=open_login_url, style="Primary.TButton")
    login_button.grid(row=1, column=1, sticky='e', padx=(0, 5))

    notebook = ttk.Notebook(parent)
    notebook.grid(row=1, column=1, sticky='nsew', padx=(0, 5), pady=5)

    console_tab = ttk.Frame(notebook, style="App.TFrame")
    season_quests_tab = ttk.Frame(notebook, style="App.TFrame")
    rivals_tab = ttk.Frame(notebook, style="App.TFrame")
    mycycle_tab = ttk.Frame(notebook, style="App.TFrame")

    notebook.add(console_tab, text="Console")
    notebook.add(season_quests_tab, text=tr("Season Quests"))
    notebook.add(rivals_tab, text=tr("Rivals"))
    notebook.add(mycycle_tab, text=tr("MyCycle"))

    console_tab.grid_rowconfigure(0, weight=1)
    console_tab.grid_columnconfigure(0, weight=1)

    text_area = tk.Text(console_tab, wrap='word', height=30, width=60, bg="black", fg="white")
    text_area.grid(row=0, column=0, sticky='nsew')
    console_scrollbar = ttk.Scrollbar(console_tab, orient="vertical", command=text_area.yview)
    console_scrollbar.grid(row=0, column=1, sticky="ns")
    text_area.configure(yscrollcommand=console_scrollbar.set)

    # Season quest leaderboard tab
    ttk.Label(
        season_quests_tab,
        text="Season Quest leaderboard (top 100)",
        style="Small.TLabel"
    ).pack(anchor="w", padx=8, pady=(8, 4))
    season_quest_columns = (
        "rank", "user", "completed", "points", "races", "race_hs", "br_hs", "tilt_levels", "tilt_tops", "tilt_points"
    )
    season_quest_style = "SeasonQuest.Treeview"
    app_style.configure(season_quest_style, rowheight=30)
    app_style.configure(f"{season_quest_style}.Heading", padding=(8, 12))
    season_quest_tree = ttk.Treeview(
        season_quests_tab,
        columns=season_quest_columns,
        show="headings",
        height=20,
        style=season_quest_style,
    )
    season_quest_tree.heading("rank", text="#")
    season_quest_tree.heading("user", text="Player")
    season_quest_tree.heading("completed", text="Completed\nQuests")
    season_quest_tree.heading("points", text="Season\nPoints")
    season_quest_tree.heading("races", text="Season\nRaces")
    season_quest_tree.heading("race_hs", text="Race\nHS")
    season_quest_tree.heading("br_hs", text="BR\nHS")
    season_quest_tree.heading("tilt_levels", text="Tilt\nLevels")
    season_quest_tree.heading("tilt_tops", text="Top\nTiltees")
    season_quest_tree.heading("tilt_points", text="Tilt\nPoints")
    season_quest_tree.column("rank", width=45, anchor="center")
    season_quest_tree.column("user", width=150, anchor="w")
    season_quest_tree.column("completed", width=95, anchor="center")
    season_quest_tree.column("points", width=90, anchor="e")
    season_quest_tree.column("races", width=82, anchor="e")
    season_quest_tree.column("race_hs", width=75, anchor="e")
    season_quest_tree.column("br_hs", width=75, anchor="e")
    season_quest_tree.column("tilt_levels", width=80, anchor="e")
    season_quest_tree.column("tilt_tops", width=90, anchor="e")
    season_quest_tree.column("tilt_points", width=90, anchor="e")
    season_quest_scrollbar = ttk.Scrollbar(season_quests_tab, orient="vertical", command=season_quest_tree.yview)
    season_quest_tree.configure(yscrollcommand=season_quest_scrollbar.set)
    season_quest_tree.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=(0, 8))
    season_quest_scrollbar.pack(side="right", fill="y", padx=(0, 8), pady=(0, 8))

    # Rivals leaderboard tab
    ttk.Label(
        rivals_tab,
        text="Rivals leaderboard (closest point gaps)",
        style="Small.TLabel"
    ).pack(anchor="w", padx=8, pady=(8, 4))
    rivals_columns = ("rank", "player_a", "points_a", "player_b", "points_b", "gap")
    rivals_tree = ttk.Treeview(rivals_tab, columns=rivals_columns, show="headings", height=20)
    rivals_tree.heading("rank", text="#")
    rivals_tree.heading("player_a", text="Player A")
    rivals_tree.heading("points_a", text="A Points")
    rivals_tree.heading("player_b", text="Player B")
    rivals_tree.heading("points_b", text="B Points")
    rivals_tree.heading("gap", text="Gap")
    rivals_tree.column("rank", width=45, anchor="center")
    rivals_tree.column("player_a", width=180, anchor="w")
    rivals_tree.column("points_a", width=120, anchor="e")
    rivals_tree.column("player_b", width=180, anchor="w")
    rivals_tree.column("points_b", width=120, anchor="e")
    rivals_tree.column("gap", width=90, anchor="e")
    rivals_scrollbar = ttk.Scrollbar(rivals_tab, orient="vertical", command=rivals_tree.yview)
    rivals_tree.configure(yscrollcommand=rivals_scrollbar.set)
    rivals_tree.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=(0, 8))
    rivals_scrollbar.pack(side="right", fill="y", padx=(0, 8), pady=(0, 8))

    # MyCycle leaderboard tab
    mycycle_top_bar = ttk.Frame(mycycle_tab, style="App.TFrame")
    mycycle_top_bar.pack(fill="x", padx=8, pady=(8, 4))

    mycycle_session_label = ttk.Label(mycycle_top_bar, text="MyCycle leaderboard", style="Small.TLabel")
    mycycle_session_label.pack(side="left")

    nav_frame = ttk.Frame(mycycle_top_bar, style="App.TFrame")
    nav_frame.pack(side="right")

    mycycle_prev_button = ttk.Button(nav_frame, text="◀", width=3, style="Primary.TButton")
    mycycle_prev_button.pack(side="left", padx=(0, 4))
    mycycle_session_position_label = ttk.Label(nav_frame, text="0/0", style="Small.TLabel")
    mycycle_session_position_label.pack(side="left", padx=(0, 4))
    mycycle_next_button = ttk.Button(nav_frame, text="▶", width=3, style="Primary.TButton")
    mycycle_next_button.pack(side="left", padx=(0, 8))
    mycycle_export_button = ttk.Button(nav_frame, text="Export CSV", style="Primary.TButton")
    mycycle_export_button.pack(side="left")

    mycycle_columns = ("rank", "user", "cycles", "progress", "placements_line1", "placements_line2", "cycle_races", "last_cycle")
    mycycle_style = "MyCycleHome.Treeview"
    app_style.configure(mycycle_style, rowheight=30)
    app_style.configure(f"{mycycle_style}.Heading", padding=(8, 12))
    mycycle_tree = ttk.Treeview(mycycle_tab, columns=mycycle_columns, show="headings", height=20, style=mycycle_style)
    leaderboard_settings = get_mycycle_settings()
    show_second_placement_line = leaderboard_settings['max_place'] - leaderboard_settings['min_place'] + 1 > 10

    for col, text in (("rank", "#"), ("user", "User"), ("cycles", "Cycles"), ("progress", "Current\nProgress"), ("placements_line1", "Placements\n(1/2)"), ("placements_line2", "Placements\n(2/2)" if show_second_placement_line else ""), ("cycle_races", "Races in\nCurrent Cycle"), ("last_cycle", "Races in Last\nCompleted Cycle")):
        mycycle_tree.heading(col, text=text)

    mycycle_tree.column("rank", width=45, anchor="center")
    mycycle_tree.column("user", width=150, anchor="w")
    mycycle_tree.column("cycles", width=65, anchor="center")
    mycycle_tree.column("progress", width=90, anchor="center")
    mycycle_tree.column("placements_line1", width=210, anchor="w")
    mycycle_tree.column("placements_line2", width=210 if show_second_placement_line else 0, anchor="w", stretch=show_second_placement_line)
    mycycle_tree.column("cycle_races", width=105, anchor="center")
    mycycle_tree.column("last_cycle", width=110, anchor="center")

    mycycle_scrollbar = ttk.Scrollbar(mycycle_tab, orient="vertical", command=mycycle_tree.yview)
    mycycle_tree.configure(yscrollcommand=mycycle_scrollbar.set)
    mycycle_tree.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=(0, 8))
    mycycle_scrollbar.pack(side="right", fill="y", padx=(0, 8), pady=(0, 8))


    refresh_main_leaderboards()


def shift_home_mycycle_session(delta):
    global mycycle_home_session_index

    if not mycycle_home_session_ids:
        return

    mycycle_home_session_index = (mycycle_home_session_index + delta) % len(mycycle_home_session_ids)

    refresh_main_leaderboards()


def export_home_mycycle_leaderboard_csv():
    if not mycycle_home_session_ids:
        messagebox.showinfo("MyCycle", "No active MyCycle sessions found.")
        return

    session_id = mycycle_home_session_ids[mycycle_home_session_index]
    session, leaderboard = get_mycycle_leaderboard(limit=5000, session_id=session_id)
    session_name = session.get('name', 'session')
    safe_session_name = ''.join(ch if ch.isalnum() or ch in (' ', '-', '_') else '_' for ch in session_name).strip() or "session"
    default_filename = f"mycycle_leaderboard_{safe_session_name}.csv"

    file_path = filedialog.asksaveasfilename(
        title="Export MyCycle Leaderboard CSV",
        defaultextension=".csv",
        initialfile=default_filename,
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
    )
    if not file_path:
        return

    leaderboard_settings = get_mycycle_settings()
    include_second_line = leaderboard_settings['max_place'] - leaderboard_settings['min_place'] + 1 > 10

    try:
        with open(file_path, "w", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow([
                "rank",
                "username",
                "display_name",
                "cycles_completed",
                "progress_hits",
                "progress_total",
                "progress_marks_line_1",
                "progress_marks_line_2" if include_second_line else "progress_marks_line_2_disabled",
                "current_cycle_races",
                "last_cycle_races",
                "session_name",
                "session_id",
            ])

            for rank, row in enumerate(leaderboard, start=1):
                writer.writerow([
                    rank,
                    row.get('username', ''),
                    row.get('display_name', ''),
                    row.get('cycles_completed', 0),
                    row.get('progress_hits', 0),
                    row.get('progress_total', 0),
                    row.get('progress_marks_top', ''),
                    row.get('progress_marks_bottom', '') if include_second_line else '',
                    row.get('current_cycle_races', 0),
                    row.get('last_cycle_races', 0),
                    session_name,
                    session.get('id', ''),
                ])

        messagebox.showinfo("MyCycle", f"Exported {len(leaderboard)} rows to:\n{file_path}")
    except Exception as error:
        messagebox.showerror("MyCycle", f"Failed to export CSV:\n{error}")


def _render_home_mycycle_leaderboard():
    global mycycle_home_session_ids, mycycle_home_session_index

    if not mycycle_tree or not mycycle_tree.winfo_exists():
        return

    mycycle_tree.delete(*mycycle_tree.get_children())
    active_sessions, default_session_id = get_mycycle_sessions(include_inactive=False)
    mycycle_home_session_ids = [session['id'] for session in active_sessions]

    if not mycycle_home_session_ids:
        if mycycle_session_label and mycycle_session_label.winfo_exists():
            mycycle_session_label.config(text="MyCycle leaderboard • No active session")
        if mycycle_session_position_label and mycycle_session_position_label.winfo_exists():
            mycycle_session_position_label.config(text="0/0")
        if mycycle_prev_button and mycycle_prev_button.winfo_exists():
            mycycle_prev_button.state(["disabled"])
        if mycycle_next_button and mycycle_next_button.winfo_exists():
            mycycle_next_button.state(["disabled"])
        if mycycle_export_button and mycycle_export_button.winfo_exists():
            mycycle_export_button.state(["disabled"])
        return

    current_primary = config.get_setting('mycycle_primary_session_id') or default_session_id
    if current_primary in mycycle_home_session_ids and mycycle_home_session_index >= len(mycycle_home_session_ids):
        mycycle_home_session_index = mycycle_home_session_ids.index(current_primary)
    elif mycycle_home_session_index >= len(mycycle_home_session_ids):
        mycycle_home_session_index = 0

    total_sessions = len(mycycle_home_session_ids)
    session_id = mycycle_home_session_ids[mycycle_home_session_index]
    session, leaderboard = get_mycycle_leaderboard(limit=250, session_id=session_id)

    if mycycle_session_label and mycycle_session_label.winfo_exists():
        mycycle_session_label.config(text=f"MyCycle leaderboard • Session: {session.get('name', 'Unknown')}")
    if mycycle_session_position_label and mycycle_session_position_label.winfo_exists():
        mycycle_session_position_label.config(text=f"{mycycle_home_session_index + 1}/{total_sessions}")

    toggle_state = ["!disabled"] if total_sessions > 1 else ["disabled"]
    if mycycle_prev_button and mycycle_prev_button.winfo_exists():
        mycycle_prev_button.state(toggle_state)
    if mycycle_next_button and mycycle_next_button.winfo_exists():
        mycycle_next_button.state(toggle_state)
    if mycycle_export_button and mycycle_export_button.winfo_exists():
        mycycle_export_button.state(["!disabled"])

    leaderboard_settings = get_mycycle_settings()
    show_second_placement_line = leaderboard_settings['max_place'] - leaderboard_settings['min_place'] + 1 > 10

    if not leaderboard:
        mycycle_tree.insert("", "end", values=("", "No race data for this session yet.", "", "", "", "", "", ""))
        return

    for idx, row in enumerate(leaderboard, start=1):
        mycycle_tree.insert("", "end", values=(
            idx,
            row.get('display_name') or row.get('username') or '-',
            row.get('cycles_completed', 0),
            f"{row.get('progress_hits', 0)}/{row.get('progress_total', 0)}",
            row.get('progress_marks_top') or '-',
            row.get('progress_marks_bottom') if show_second_placement_line else "",
            row.get('current_cycle_races', 0),
            row.get('last_cycle_races', 0),
        ))


def refresh_main_leaderboards():
    if not root or not root.winfo_exists():
        return

    if 'config' not in globals() or config is None:
        root.after(15000, refresh_main_leaderboards)
        return

    try:
        if season_quest_tree and season_quest_tree.winfo_exists():
            season_quest_tree.delete(*season_quest_tree.get_children())
            for idx, row in enumerate(get_quest_completion_leaderboard(limit=100), start=1):
                season_quest_tree.insert("", "end", values=(
                    idx,
                    row.get('display_name') or row.get('username') or '-',
                    f"{row.get('completed', 0):,}/{row.get('active_quests', 0):,}",
                    f"{row.get('points', 0):,}",
                    f"{row.get('races', 0):,}",
                    f"{row.get('race_hs', 0):,}",
                    f"{row.get('br_hs', 0):,}",
                    f"{row.get('tilt_levels', 0):,}",
                    f"{row.get('tilt_top_tiltee', 0):,}",
                    f"{row.get('tilt_points', 0):,}",
                ))

        if rivals_tree and rivals_tree.winfo_exists():
            rivals_tree.delete(*rivals_tree.get_children())
            for idx, row in enumerate(get_global_rivalries(limit=RIVALS_MAX_PAIRS), start=1):
                rivals_tree.insert("", "end", values=(
                    idx,
                    row.get('display_a') or '-',
                    f"{row.get('points_a', 0):,}",
                    row.get('display_b') or '-',
                    f"{row.get('points_b', 0):,}",
                    f"±{row.get('point_gap', 0):,}",
                ))

        if mycycle_tree and mycycle_tree.winfo_exists():
            _render_home_mycycle_leaderboard()
    except Exception as error:
        print(f"Failed to refresh leaderboard tabs: {error}")

    root.after(15000, refresh_main_leaderboards)


def initialize_main_window():
    global app_style, root

    configure_dpi_awareness()

    root_window, app_style = create_root_window()
    apply_ui_styles(app_style)

    # Keep classic tk.Button widgets visually flatter to match ttk style.
    root_window.option_add("*Button.relief", "flat")
    root_window.option_add("*Button.borderWidth", 0)
    root_window.option_add("*Button.highlightThickness", 0)

    root_window.protocol("WM_DELETE_WINDOW", on_close)
    root_window.bind("<Unmap>", handle_root_minimize)
    root_window.title(tr("MyStats - Marbles On Stream Companion Application"))

    window_width = 1040
    window_height = 650
    screen_width = root_window.winfo_screenwidth()
    screen_height = root_window.winfo_screenheight()

    # Ensure the default size remains usable across high-DPI scaling levels.
    window_width = min(window_width, int(screen_width * 0.94))
    window_height = min(window_height, int(screen_height * 0.9))

    pos_x = (screen_width // 2) - (window_width // 2)
    pos_y = (screen_height // 2) - (window_height // 2)
    root_window.geometry(f"{window_width}x{window_height}+{pos_x}+{pos_y}")
    root_window.minsize(920, 560)
    root_window.resizable(True, True)

    root_window.grid_rowconfigure(1, weight=1)
    root_window.grid_columnconfigure(1, weight=1)

    root = root_window
    root.after(250, _drain_tray_queue)

    build_stats_sidebar(root_window)
    build_main_content(root_window)

    if mycycle_prev_button and mycycle_prev_button.winfo_exists():
        mycycle_prev_button.configure(command=lambda: shift_home_mycycle_session(-1))
    if mycycle_next_button and mycycle_next_button.winfo_exists():
        mycycle_next_button.configure(command=lambda: shift_home_mycycle_session(1))
    if mycycle_export_button and mycycle_export_button.winfo_exists():
        mycycle_export_button.configure(command=export_home_mycycle_leaderboard_csv)

    root_window.update_idletasks()
    root_window.grid_columnconfigure(1, weight=1)

    return root_window


def open_events_window():
    root.update_idletasks()
    root_width = root.winfo_width()
    root_height = root.winfo_height()
    root_x = root.winfo_x()
    root_y = root.winfo_y()

    events_window = tk.Toplevel(root)
    events_window.title("Events")

    window_width = 300
    min_window_height = 150
    max_window_height = 500

    def resize_window_based_on_events(num_events):
        event_frame_height = 40
        total_height = event_frame_height * num_events + 100
        total_height = min(max(total_height, min_window_height), max_window_height)

        window_x = root_x + (root_width // 2) - (window_width // 2)
        window_y = root_y + (root_height // 2) - (total_height // 2)

        events_window.geometry(f"{window_width}x{total_height}+{window_x}+{window_y}")

    events_frame = tk.Frame(events_window, padx=10, pady=10)
    events_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 5))

    channel = config.get_setting('CHANNEL')

    def toggle_event(event_id, button):
        # Retrieve active events and paused events from config
        active_events_str = config.get_setting("active_event_ids")
        paused_events_str = config.get_setting("paused_event_ids")

        if not active_events_str:
            active_events_str = "[]"
        if not paused_events_str:
            paused_events_str = "[]"

        try:
            active_events = json.loads(active_events_str)
            paused_events = json.loads(paused_events_str)
        except json.JSONDecodeError:
            active_events = []
            paused_events = []

        event_id_str = str(event_id)

        if event_id_str in paused_events:
            # Resume the paused event
            paused_events.remove(event_id_str)
            active_events.append(event_id_str)
            button.config(text="End", bg="red")
            config.set_setting("paused_event_ids", json.dumps(paused_events))
            config.set_setting("active_event_ids", json.dumps(active_events))
        elif event_id_str in active_events:
            # Show the custom confirmation dialog for End/Pause/Cancel
            show_end_event_confirmation(event_id, button)
        else:
            # Start the event if it's not active or paused
            active_events.append(event_id_str)
            button.config(text="End", bg="red")
            config.set_setting("active_event_ids", json.dumps(active_events))

    def fetch_active_events(channel):
        try:
            active_event_ids_tmp = config.get_setting('active_event_ids')
            if active_event_ids_tmp is not None:
                active_event_ids_tmp = active_event_ids_tmp.strip("[]").split(",")
                # Filter out empty or non-numeric values before converting to integers
                active_event_ids = [
                    int(id.strip().replace('"', ''))
                    for id in active_event_ids_tmp
                    if id.strip().replace('"', '').isdigit()  # Ensure the value is numeric and non-empty
                ]
            else:
                active_event_ids = []

            # Prepare the data payload for the POST request
            data_payload = {
                'activeEventIds': active_event_ids
            } if active_event_ids else {}

            # Send POST request with the data payload
            logger.info("API call: active events for channel %s", channel)
            response = requests.post(
                f"https://mystats.camwow.tv/api/app/get-active-events/{channel}",
                json=data_payload  # Sending the data as JSON
            )

            response.raise_for_status()
            response_data = response.json()

            return response_data

        except requests.RequestException as e:
            error_msg = f"Failed to fetch events: {e.response.text if e.response else str(e)}"
            messagebox.showerror("Error", error_msg)
            return []

    def update_event_list():
        events = fetch_active_events(channel)

        # Clear any existing widgets
        for widget in events_frame.winfo_children():
            widget.destroy()

        active_events_str = config.get_setting("active_event_ids")
        paused_events_str = config.get_setting("paused_event_ids")

        if not active_events_str:
            active_events_str = "[]"
        if not paused_events_str:
            paused_events_str = "[]"

        try:
            active_events = json.loads(active_events_str)
            paused_events = json.loads(paused_events_str)
        except json.JSONDecodeError:
            active_events = []
            paused_events = []

        for event_data in events:
            event_id = event_data['event_id']
            event_series = event_data['event'].get('eventSeries')
            series_name = event_series['name'] if event_series else 'No Series'
            event_name = event_data['event']['name']

            # Create a frame for each event
            event_frame = tk.Frame(events_frame)
            event_frame.pack(fill=tk.X, pady=(0, 5))

            # Set up a grid layout
            event_frame.grid_columnconfigure(0, weight=1)
            event_frame.grid_columnconfigure(1, weight=0)

            # Event label with wrap
            event_label = tk.Label(
                event_frame,
                text=f"{series_name} - {event_name}",
                anchor='w',
                wraplength=175,  # Adjust based on available space
                justify='left'
            )
            event_label.grid(row=0, column=0, sticky='w', padx=5)

            # Event button
            event_button = tk.Button(
                event_frame,
                width=7
            )

            # Button logic based on event status
            if event_data.get('hasSubmittedData', False):
                event_button.config(text="Complete", bg="gray", state="disabled")
            elif str(event_id) in paused_events:
                event_button.config(text="Paused", bg="yellow")
            elif str(event_id) in active_events:
                event_button.config(text="End", bg="red")
            else:
                event_button.config(text="Start", bg="green")

            event_button.config(command=lambda eid=event_id, btn=event_button: toggle_event(eid, btn))
            event_button.grid(row=0, column=1, padx=5)

        resize_window_based_on_events(len(events))

    def show_end_event_confirmation(event_id, button):
        events_window.destroy()

        confirmation_window = tk.Toplevel(root)
        confirmation_window.title("Confirm Event Action")

        window_width, window_height = 400, 200
        confirmation_window.geometry(
            f"{window_width}x{window_height}+{root.winfo_x() + (root_width // 2) - (window_width // 2)}+{root.winfo_y() + (root_height // 2) - (window_height // 2)}")

        message = tk.Label(
            confirmation_window,
            text="Are you sure you want to end this event and transmit your data to the server?\n"
                 "You may pause this to resume collecting data at a later time.",
            wraplength=350
        )
        message.pack(pady=20)

        def end_event():
            active_events_str = config.get_setting("active_event_ids")
            if not active_events_str:
                active_events_str = "[]"

            try:
                active_events = json.loads(active_events_str)
            except json.JSONDecodeError:
                active_events = []

            event_id_str = str(event_id)
            process_event_data(event_id_str)

            if event_id_str in active_events:
                active_events.remove(event_id_str)
                config.set_setting("active_event_ids", json.dumps(active_events))

            confirmation_window.destroy()
            open_events_window()  # Reopen the events window

        def pause_event():
            active_events_str = config.get_setting("active_event_ids")
            paused_events_str = config.get_setting("paused_event_ids")

            if not active_events_str:
                active_events_str = "[]"
            if not paused_events_str:
                paused_events_str = "[]"

            try:
                active_events = json.loads(active_events_str)
                paused_events = json.loads(paused_events_str)
            except json.JSONDecodeError:
                active_events = []
                paused_events = []

            event_id_str = str(event_id)

            # Remove from active events and add to paused events
            if event_id_str in active_events:
                active_events.remove(event_id_str)
                paused_events.append(event_id_str)
                config.set_setting("active_event_ids", json.dumps(active_events))
                config.set_setting("paused_event_ids", json.dumps(paused_events))

            confirmation_window.destroy()
            open_events_window()  # Reopen the events window with updated status

        def cancel_action():
            confirmation_window.destroy()
            open_events_window()  # Reopen the events window

        button_frame = tk.Frame(confirmation_window)
        button_frame.pack(pady=20, padx=20, fill=tk.BOTH, expand=True)

        button_width = 15

        end_button = tk.Button(button_frame, text="End Event", command=end_event, width=button_width)
        end_button.pack(side=tk.LEFT, expand=True, padx=10)

        pause_button = tk.Button(button_frame, text="Pause Event", command=pause_event, width=button_width)
        pause_button.pack(side=tk.LEFT, expand=True, padx=10)

        cancel_button = tk.Button(button_frame, text="Cancel", command=cancel_action, width=button_width)
        cancel_button.pack(side=tk.LEFT, expand=True, padx=10)

    def open_create_event_window():
        events_window.destroy()

        create_event_window = tk.Toplevel(root)
        create_event_window.title("Create Event")
        create_event_window.resizable(False, False)
        center_toplevel(create_event_window, 420, 320)

        def on_create_event_close():
            create_event_window.destroy()
            open_events_window()

        create_event_window.protocol("WM_DELETE_WINDOW", on_create_event_close)

        form_frame = ttk.Frame(create_event_window, style="App.TFrame", padding=(12, 10))
        form_frame.pack(fill="both", expand=True)

        ttk.Label(form_frame, text="Event Name").grid(row=0, column=0, sticky="w", pady=(0, 4))
        event_name_entry = ttk.Entry(form_frame, width=34)
        event_name_entry.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        def build_date_picker(parent, row_index, label_text):
            ttk.Label(parent, text=label_text).grid(row=row_index, column=0, sticky="w", pady=(0, 4))

            value = tk.StringVar(value=get_internal_adjusted_time().strftime('%Y-%m-%d'))
            field_frame = ttk.Frame(parent, style="App.TFrame")
            field_frame.grid(row=row_index + 1, column=0, sticky="w", pady=(0, 10))

            date_entry = ttk.Entry(field_frame, textvariable=value, width=22)
            date_entry.pack(side="left")

            def open_calendar_popup():
                popup = tk.Toplevel(create_event_window)
                popup.title("Select Date")
                popup.resizable(False, False)
                popup.transient(create_event_window)

                calendar = Calendar(popup, date_pattern='y-mm-dd', selectmode='day')
                calendar.pack(padx=10, pady=10)

                if value.get():
                    try:
                        calendar.selection_set(datetime.strptime(value.get(), '%Y-%m-%d').date())
                    except ValueError:
                        pass

                def use_selected_date():
                    value.set(calendar.get_date())
                    popup.destroy()

                ttk.Button(popup, text="Use Date", command=use_selected_date, style="Primary.TButton").pack(pady=(0, 10))

                popup.update_idletasks()
                popup_width = popup.winfo_width()
                popup_height = popup.winfo_height()
                popup_x = create_event_window.winfo_x() + (create_event_window.winfo_width() // 2) - (popup_width // 2)
                popup_y = create_event_window.winfo_y() + (create_event_window.winfo_height() // 2) - (popup_height // 2)
                popup.geometry(f"{popup_width}x{popup_height}+{popup_x}+{popup_y}")
                popup.grab_set()

            ttk.Button(field_frame, text="📅", width=3, command=open_calendar_popup).pack(side="left", padx=(6, 0))
            return value

        event_start_value = build_date_picker(form_frame, 2, "Event Start Date")
        event_end_value = build_date_picker(form_frame, 4, "Event End Date")

        def create_event():
            event_name = event_name_entry.get()
            event_start = event_start_value.get()
            event_end = event_end_value.get()

            confirm = messagebox.askyesno(
                "Confirm Event Creation",
                "Are you sure you want to create this event? If you need to delete this event, "
                "you will need to visit the website."
            )

            if confirm:
                try:
                    response1 = requests.post(
                        f"https://mystats.camwow.tv/api/app/create-event",
                        json={
                            "channel": channel,
                            "name": event_name,
                            "startAt": event_start,
                            "endAt": event_end
                        }
                    )
                    response1.raise_for_status()

                    create_event_window.destroy()
                    open_events_window()

                except requests.RequestException as e:
                    messagebox.showerror("Error", f"Failed to create event: {e}")

        button_row = ttk.Frame(form_frame, style="App.TFrame")
        button_row.grid(row=6, column=0, sticky="e")

        ttk.Button(button_row, text="Create Event", command=create_event, style="Primary.TButton").pack(side="left", padx=(0, 8))
        ttk.Button(button_row, text="Cancel", command=on_create_event_close).pack(side="left")

    create_event_button = tk.Button(events_window, text="Create Event", command=open_create_event_window)
    create_event_button.pack(pady=5)

    events_window.grab_set()

    close_button = tk.Button(events_window, text="Close", command=events_window.destroy)
    close_button.pack(pady=10)

    update_event_list()


# Tkinter Initialization
root = initialize_main_window()

# Start Flask server in a separate thread
flask_thread = threading.Thread(target=run_flask)
flask_thread.daemon = True
flask_thread.start()


def update_config_labels():
    # Update today's statistics with comma-separated values
    total_points_t_label.config(text=f"Total Points: {int(config.get_setting('totalpointstoday')):,}")
    total_count_t_label.config(text=f"Total Count: {int(config.get_setting('totalcounttoday')):,}")
    avg_points_t_label.config(text=f"Avg Points: {float(config.get_setting('avgpointstoday')):,.2f}")
    race_hs_t_label.config(text=f"Race HS: {int(config.get_setting('race_hs_today')):,}")
    br_hs_t_label.config(text=f"BR HS: {int(config.get_setting('br_hs_today')):,}")

    # Update season statistics with comma-separated values
    total_points_label.config(text=f"Total Points: {int(config.get_setting('totalpointsseason')):,}")
    total_count_label.config(text=f"Total Count: {int(config.get_setting('totalcountseason')):,}")

    # Calculate average points for the season
    total_points_season = float(config.get_setting('totalpointsseason'))
    total_count_season = float(config.get_setting('totalcountseason'))

    # Check to avoid division by zero
    if total_count_season > 0:
        avg_points_season = total_points_season / total_count_season
    else:
        avg_points_season = 0.0

    avg_points_label.config(text=f"Avg Points: {avg_points_season:,.2f}")

    race_hs_label.config(text=f"Race HS: {int(config.get_setting('race_hs_season')):,}")
    br_hs_label.config(text=f"BR HS: {int(config.get_setting('br_hs_season')):,}")


# Redirect stdout to the text area after the widget is created
sys.stdout = PrintRedirector(text_area)

# Create a menu bar
menu_bar = Menu(root)

# Create the File menu
file_menu = Menu(menu_bar, tearoff=0)
file_menu.add_command(label="Exit", command=on_close)
menu_bar.add_cascade(label="File", menu=file_menu)

# Create the Edit menu
edit_menu = Menu(menu_bar, tearoff=0)
edit_menu.add_command(label="Settings", command=open_settings)
edit_menu.add_command(label="Events", command=open_events_window)
edit_menu.add_command(label="Dashboards", command=open_dashboard)
menu_bar.add_cascade(label="Edit", menu=edit_menu)

# Create the Help menu
help_menu = Menu(menu_bar, tearoff=0)
help_menu.add_command(label="View Commands", command=lambda: show_help(bot, root))
help_menu.add_command(label=tr("About"), command=show_about_window)
menu_bar.add_cascade(label="Help", menu=help_menu)

# Attach the menu bar to the root window
root.config(menu=menu_bar)


# Classes and Functions
TILT_RUNTIME_PERSISTENT_KEYS = {
    "tilt_current_level", "tilt_current_elapsed", "tilt_current_top_tiltee",
    "tilt_current_run_id", "tilt_run_started_at", "tilt_run_ledger",
    "tilt_run_deaths_ledger", "tilt_top_tiltee_ledger", "tilt_current_top_tiltee_count", "tilt_run_xp",
    "tilt_run_points", "tilt_run_deaths_total", "tilt_run_total_seconds", "tilt_previous_run_xp", "tilt_level_completion_overlay",
    "tilt_run_completion_overlay", "tilt_run_completion_event_id",
    "tilt_last_run_summary", "tilt_best_run_xp_today", "tilt_highest_level_points_today",
    "tilt_highest_level_reached_num", "tilt_season_best_level_num",
    "tilt_personal_best_level_num", "tilt_total_xp_today", "tilt_total_deaths_today",
    "tilt_lifetime_expertise"
}


def set_tilt_runtime_setting(key, value):
    config.set_setting(key, value, persistent=(key in TILT_RUNTIME_PERSISTENT_KEYS))


class ConfigManager:
    def __init__(self):
        self.settings_file = SETTINGS_FILE_PATH
        self.settings = {}
        self.transient_settings = {}
        self.persistent_keys = {'TWITCH_USERNAME', 'TWITCH_TOKEN', 'CHANNEL', 'chunk_alert', 'chunk_alert_value',
                                'marble_day', 'allraces_file', 'announcedelay', 'announcedelayseconds',
                                'directory', 'race_file', 'br_file', 'season', 'reset_audio', 'sync', 'MPL',
                                'chunk_alert_sound', 'reset_audio_sound', 'audio_device', 'checkpoint_file',
                                'tilt_player_file', 'active_event_ids', 'paused_event_ids', 'checkpoint_results_file',
                                'tilts_results_file', 'tilt_level_file', 'map_data_file', 'map_results_file',
                                'UI_THEME', 'chat_br_results', 'chat_race_results', 'chat_leaderboard_show_medals', 'chat_tilt_results',
                                'chat_tilt_suppress_offline', 'chat_tilt_redact_survivor_names',
                                'chat_mystats_command', 'chat_all_commands', 'chat_narrative_alerts', 'competitive_raid_monitor_enabled', 'competitive_raid_phase', 'competitive_raid_queue_started_at', 'competitive_raid_live_started_at', 'competitive_raid_last_summary_live_started_at', 'competitive_raid_last_queue_open_live_started_at',
                                'narrative_alert_grinder_enabled', 'narrative_alert_winmilestone_enabled',
                                'narrative_alert_leadchange_enabled', 'narrative_alert_cooldown_races',
                                'narrative_alert_min_lead_change_points', 'narrative_alert_max_items',
                                'race_narrative_alerts_enabled', 'race_narrative_grinder_enabled',
                                'race_narrative_winmilestone_enabled', 'race_narrative_leadchange_enabled',
                                'race_narrative_alert_cooldown_races', 'race_narrative_alert_min_lead_change_points',
                                'race_narrative_alert_max_items', 'chat_max_names',
                                'season_quests_enabled', 'season_quest_target_races', 'season_quest_target_points',
                                'season_quest_target_race_hs', 'season_quest_target_br_hs', 'season_quest_target_tilt_levels',
                                'season_quest_target_tilt_tops', 'season_quest_target_tilt_points',
                                'season_quest_complete_races', 'season_quest_complete_points', 'season_quest_complete_race_hs',
                                'season_quest_complete_br_hs', 'season_quest_complete_tilt_levels',
                                'season_quest_complete_tilt_tops', 'season_quest_complete_tilt_points',
                                'season_quest_completion_state',
                                'rivals_enabled', 'rivals_min_races', 'rivals_max_point_gap', 'rivals_pair_count',
                                'mycycle_enabled', 'mycycle_announcements_enabled', 'mycycle_include_br',
                                'mycycle_min_place', 'mycycle_max_place', 'mycycle_primary_session_id',
                                'mycycle_cyclestats_rotation_index',
                                'teams_enabled', 'teams_points_mode', 'teams_max_size',
                                'teams_bonus_bits_threshold', 'teams_bonus_duration_minutes',
                                'teams_tep_threshold', 'teams_tep_per_race', 'teams_tep_bonus_duration_minutes', 'teams_tep_bits_cooldown_minutes',
                                'teams_tep_member_daily_cap', 'teams_tep_team_daily_cap',
                                'teams_bonus_weight_15', 'teams_bonus_weight_25', 'teams_bonus_weight_35', 'teams_bonus_weight_67',
                                'overlay_rotation_seconds', 'overlay_refresh_seconds', 'overlay_theme',
                                'overlay_card_opacity', 'overlay_text_scale', 'overlay_show_medals',
                                'overlay_compact_rows', 'overlay_horizontal_layout', 'overlay_horizontal_feed_season', 'overlay_horizontal_feed_today',
                                'overlay_horizontal_feed_races_season', 'overlay_horizontal_feed_brs_season', 'overlay_horizontal_feed_races_today',
                                'overlay_horizontal_feed_brs_today', 'overlay_horizontal_feed_myteams', 'overlay_horizontal_feed_previous_race', 'overlay_horizontal_feed_events',
                                'overlay_horizontal_feed_tilt_current', 'overlay_horizontal_feed_tilt_today',
                                'overlay_horizontal_feed_tilt_season', 'overlay_horizontal_feed_tilt_last_run',
                                'overlay_server_port', 'tilt_lifetime_base_xp',
                                'tilt_season_best_level', 'tilt_personal_best_level', 'tilt_overlay_theme', 'tilt_scroll_step_px', 'tilt_scroll_interval_ms',
                                'tilt_scroll_pause_ms', 'tiltsurvivors_min_levels', 'tiltdeath_min_levels',
                                'update_later_clicks', 'update_later_version', 'pending_update_installer_path',
                                'pending_update_silent_mode', 'pending_update_version_label',
                                'minimize_to_tray', 'tray_hint_toast_shown', 'app_language', *TILT_RUNTIME_PERSISTENT_KEYS}
        self.transient_keys = set([])
        self.defaults = {
            'chat_br_results': 'True',
            'chat_race_results': 'True',
            'chat_leaderboard_show_medals': 'True',
            'chat_tilt_results': 'True',
            'chat_tilt_suppress_offline': 'True',
            'chat_tilt_redact_survivor_names': 'False',
            'chat_mystats_command': 'True',
            'chat_all_commands': 'True',
            'chat_narrative_alerts': 'True',
            'competitive_raid_monitor_enabled': 'False',
            'competitive_raid_phase': 'idle',
            'competitive_raid_queue_started_at': '',
            'competitive_raid_live_started_at': '',
            'competitive_raid_last_summary_live_started_at': '',
            'competitive_raid_last_queue_open_live_started_at': '',
            'narrative_alert_grinder_enabled': 'True',
            'narrative_alert_winmilestone_enabled': 'True',
            'narrative_alert_leadchange_enabled': 'True',
            'narrative_alert_cooldown_races': '3',
            'narrative_alert_min_lead_change_points': '500',
            'narrative_alert_max_items': '3',
            'race_narrative_alerts_enabled': 'True',
            'race_narrative_grinder_enabled': 'True',
            'race_narrative_winmilestone_enabled': 'True',
            'race_narrative_leadchange_enabled': 'True',
            'race_narrative_alert_cooldown_races': '3',
            'race_narrative_alert_min_lead_change_points': '500',
            'race_narrative_alert_max_items': '3',
            'chat_max_names': '25',
            'minimize_to_tray': 'False',
            'tray_hint_toast_shown': 'False',
            'app_language': 'en',
            'season_quests_enabled': 'True',
            'season_quest_target_races': '1000',
            'season_quest_target_points': '500000',
            'season_quest_target_race_hs': '3000',
            'season_quest_target_br_hs': '3000',
            'season_quest_target_tilt_levels': '1000',
            'season_quest_target_tilt_tops': '100',
            'season_quest_target_tilt_points': '500000',
            'season_quest_complete_races': 'False',
            'season_quest_complete_points': 'False',
            'season_quest_complete_race_hs': 'False',
            'season_quest_complete_br_hs': 'False',
            'season_quest_complete_tilt_levels': 'False',
            'season_quest_complete_tilt_tops': 'False',
            'season_quest_complete_tilt_points': 'False',
            'season_quest_completion_state': '{}',
            'rivals_enabled': 'True',
            'rivals_min_races': '50',
            'rivals_max_point_gap': '1500',
            'rivals_pair_count': '25',
            'mycycle_enabled': 'True',
            'mycycle_announcements_enabled': 'True',
            'mycycle_include_br': 'False',
            'mycycle_min_place': '1',
            'mycycle_max_place': '10',
            'mycycle_cyclestats_rotation_index': '0',
            'teams_enabled': 'True',
            'teams_points_mode': 'active',
            'teams_max_size': '25',
            'teams_bonus_bits_threshold': '1000',
            'teams_bonus_duration_minutes': '20',
            'teams_tep_threshold': '40',
            'teams_tep_per_race': '1',
            'teams_tep_bonus_duration_minutes': '15',
            'teams_tep_bits_cooldown_minutes': '60',
            'teams_tep_member_daily_cap': '10',
            'teams_tep_team_daily_cap': '100',
            'teams_bonus_weight_15': '33',
            'teams_bonus_weight_25': '33',
            'teams_bonus_weight_35': '33',
            'teams_bonus_weight_67': '1',
            'UI_THEME': DEFAULT_UI_THEME,
            'announcedelay': 'False',
            'announcedelayseconds': '0',
            'chunk_alert_value': '1000',
            'overlay_rotation_seconds': '10',
            'overlay_refresh_seconds': '3',
            'overlay_server_port': '5000',
            'overlay_theme': 'midnight',
            'overlay_card_opacity': '84',
            'overlay_text_scale': '100',
            'overlay_show_medals': 'True',
            'overlay_compact_rows': 'False',
            'overlay_horizontal_layout': 'False',
            'overlay_horizontal_feed_season': 'True',
            'overlay_horizontal_feed_today': 'True',
            'overlay_horizontal_feed_races_season': 'True',
            'overlay_horizontal_feed_brs_season': 'True',
            'overlay_horizontal_feed_races_today': 'True',
            'overlay_horizontal_feed_brs_today': 'True',
            'overlay_horizontal_feed_myteams': 'True',
            'overlay_horizontal_feed_previous_race': 'True',
            'overlay_horizontal_feed_events': 'True',
            'overlay_horizontal_feed_tilt_current': 'True',
            'overlay_horizontal_feed_tilt_today': 'True',
            'overlay_horizontal_feed_tilt_season': 'True',
            'overlay_horizontal_feed_tilt_last_run': 'True',
            'tilt_lifetime_base_xp': '0',
            'tilt_season_best_level': '1',
            'tilt_personal_best_level': '1',
            'tilt_overlay_theme': 'midnight',
            'tilt_scroll_step_px': '1',
            'tilt_scroll_interval_ms': '40',
            'tilt_scroll_pause_ms': '900',
            'tiltsurvivors_min_levels': '20',
            'tiltdeath_min_levels': '20',
            'tilt_current_level': '0',
            'tilt_current_elapsed': '0:00',
            'tilt_current_top_tiltee': 'None',
            'tilt_current_run_id': '',
            'tilt_run_started_at': '',
            'tilt_run_ledger': '{}',
            'tilt_run_deaths_ledger': '{}',
            'tilt_top_tiltee_ledger': '{}',
            'tilt_current_top_tiltee_count': '0',
            'tilt_run_xp': '0',
            'tilt_run_points': '0',
            'tilt_run_deaths_total': '0',
            'tilt_run_total_seconds': '0',
            'tilt_previous_run_xp': '0',
            'tilt_level_completion_overlay': '{}',
            'tilt_run_completion_overlay': '{}',
            'tilt_run_completion_event_id': '0',
            'tilt_last_run_summary': '{}',
            'tilt_best_run_xp_today': '0',
            'tilt_highest_level_points_today': '0',
            'tilt_highest_level_reached_num': '0',
            'tilt_season_best_level_num': '0',
            'tilt_personal_best_level_num': '0',
            'tilt_total_xp_today': '0',
            'tilt_total_deaths_today': '0',
            'tilt_lifetime_expertise': '0',
            'update_later_clicks': '0',
            'update_later_version': '',
            'pending_update_installer_path': '',
            'pending_update_silent_mode': 'True',
            'pending_update_version_label': ''
        }
        self.load_settings()

    def load_settings(self):
        try:
            with open(self.settings_file, "r") as f:
                for line in f:
                    clean_line = line.strip()
                    if not clean_line or '=' not in clean_line:
                        continue

                    key, value = clean_line.split('=', 1)
                    if key in self.persistent_keys:
                        self.settings[key] = value
                    elif key in self.transient_keys:
                        self.transient_settings[key] = value.strip()
        except FileNotFoundError:
            print("Settings file not found. Please check the file path and filename.")

    def get_setting(self, key):
        if key in self.transient_settings:
            return self.transient_settings[key]
        if key in self.settings:
            return self.settings[key]
        return self.defaults.get(key, None)

    def set_setting(self, key, value, persistent=True):
        if key == "CHANNEL":
            value = value.lower()

        if persistent:
            if key in self.persistent_keys:
                if self.validate_setting(key, value):
                    self.settings[key] = str(value).strip()
                    self.save_settings()
        else:
            if key not in self.transient_keys and key not in self.persistent_keys:
                self.transient_keys.add(key)
            if self.validate_setting(key, value):
                self.transient_settings[key] = str(value).strip()

    def validate_setting(self, key, value):
        if key == "chunk_alert_value":
            if isinstance(value, int) or (isinstance(value, str) and value.isdigit()):
                return True
            else:
                print(f"Invalid value for {key}: {value}. Resetting to default (1000).")
                return False

        if key in {"season_quest_target_races", "season_quest_target_points", "season_quest_target_race_hs", "season_quest_target_br_hs",
                   "season_quest_target_tilt_levels", "season_quest_target_tilt_tops", "season_quest_target_tilt_points",
                   "rivals_min_races", "rivals_max_point_gap", "rivals_pair_count",
                   "narrative_alert_cooldown_races", "narrative_alert_min_lead_change_points", "narrative_alert_max_items",
                   "race_narrative_alert_cooldown_races", "race_narrative_alert_min_lead_change_points", "race_narrative_alert_max_items",
                   "mycycle_min_place", "mycycle_max_place",
                   "overlay_rotation_seconds", "overlay_refresh_seconds", "overlay_card_opacity",
                   "overlay_text_scale", "overlay_server_port", "tilt_lifetime_base_xp",
                   "tilt_season_best_level", "tilt_personal_best_level",
                   "tilt_scroll_step_px", "tilt_scroll_interval_ms", "tilt_scroll_pause_ms",
                   "tiltsurvivors_min_levels", "tiltdeath_min_levels"}:
            if isinstance(value, int) or (isinstance(value, str) and value.isdigit()):
                if key == "overlay_server_port":
                    port = int(value)
                    if not (1 <= port <= 65535):
                        print(f"Invalid value for {key}: {value}. Value must be between 1 and 65535.")
                        return False
                return True
            print(f"Invalid value for {key}: {value}. Value must be a whole number.")
            return False

        return True

    def save_settings(self):
        temp_file = f"{self.settings_file}.tmp"
        with open(temp_file, "w") as f:
            for key, value in self.settings.items():
                if key in self.persistent_keys:
                    f.write(f"{key}={value}\n")
        os.replace(temp_file, self.settings_file)


config = ConfigManager()
tray_hint_toast_shown = str(config.get_setting("tray_hint_toast_shown") or "False").strip().lower() == "true"


class TimeManager:
    def __init__(self):
        self.timestamp = ""
        self.timestampMDY = ""
        self.timestampHMS = ""
        self.adjusted_time = None

    def get_adjusted_time(self):
        eastern = pytz.timezone('America/New_York')
        now_eastern = datetime.now(eastern)

        self.adjusted_time = now_eastern + timedelta(hours=-12)

        self.timestamp = self.adjusted_time.strftime("%Y-%m-%d %H:%M:%S")
        self.timestampMDY = self.adjusted_time.strftime("%Y-%m-%d")
        self.timestampHMS = self.adjusted_time.strftime("%H:%M:%S")

        return self.timestamp, self.timestampMDY, self.timestampHMS, self.adjusted_time


time_manager = TimeManager()


def get_internal_adjusted_time():
    """Return MyStats internal clock datetime aligned to Marble Day boundaries."""
    try:
        _, _, _, adjusted_time = time_manager.get_adjusted_time()
        if adjusted_time is not None:
            return adjusted_time
    except Exception:
        logger.error("Failed to read internal time manager clock.", exc_info=True)
    eastern = pytz.timezone('America/New_York')
    return datetime.now(eastern) + timedelta(hours=-12)


def get_internal_now_iso(timespec='seconds'):
    now_value = get_internal_adjusted_time()
    if timespec == 'seconds':
        now_value = now_value.replace(microsecond=0)
    return now_value.isoformat(timespec=timespec)


def data_sync():
    config.set_setting('data_sync', 'yes', persistent=False)


def process_event_data(event_id):
    api_url = f"https://mystats.camwow.tv/api/app/get-leaderboard-config/{event_id}"

    # Get leaderboard config from the API
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        config_data = response.json()
    except requests.exceptions.RequestException as e:
        print("Error getting leaderboard config:", e)
        return
    except json.JSONDecodeError as e:
        print("Failed to decode JSON from response:", e)
        return

    # Extract points settings from the config
    position_points = {pos['position']: pos['points'] for pos in config_data['positions']}
    participation_points = config_data['participationPoints']
    br_kill_points = config_data['brKillPoints']
    damage_points = config_data['damagePoints']
    give_position_points_on_dnf = config_data['givePositionPointsOnDNF']
    checkpoint_points = config_data['checkpointPoints']

    # Initialize event data structure
    event_data = defaultdict(lambda: {
        'racer_name': '',
        'channel': config.get_setting('CHANNEL'),
        'race_points': 0,
        'race_wins': 0,
        'race_races': 0,
        'br_points': 0,
        'br_wins': 0,
        'br_races': 0,
        'crownwins': 0,
        'br_kills': 0,
        'br_damage': 0,
        'eliminations': 0,
        'event_points': 0
    })

    last_br_win = defaultdict(lambda: None)

    directory = config.get_setting('directory')
    if not os.path.exists(directory):
        return

    # Process all race files
    for allraces in glob.glob(os.path.join(directory, "allraces_*.csv")):
        try:
            with open(allraces, 'rb') as f:
                raw_data = f.read()

            # Detect encoding using chardet
            result = chardet.detect(raw_data)
            encoding = result['encoding'] if result['encoding'] else 'utf-8'

            with open(allraces, 'r', encoding=encoding, errors='ignore') as f:
                reader = iter_csv_rows(f)
                for row in reader:
                    if len(row) < 11:
                        continue

                    if event_id in row[10]:
                        position = int(row[0])
                        racer_name = row[1].lower()
                        points = int(row[3])
                        race_type = row[4]
                        timestamp = datetime.strptime(row[5], "%Y-%m-%d %H:%M:%S")
                        marble_count = int(row[6])
                        eliminated = 1 if row[7].lower() == 'true' else 0
                        br_kills = int(row[8])
                        br_damage = int(row[9])

                        event_data[racer_name]['racer_name'] = racer_name
                        event_data[racer_name]['event_points'] += participation_points

                        if race_type == 'Race':
                            event_data[racer_name]['race_points'] += points
                            event_data[racer_name]['race_races'] += 1
                            if position == 1:
                                event_data[racer_name]['race_wins'] += 1

                        if race_type == 'BR':
                            event_data[racer_name]['br_points'] += points
                            event_data[racer_name]['br_races'] += 1
                            event_data[racer_name]['br_kills'] += br_kills
                            event_data[racer_name]['br_damage'] += br_damage
                            event_data[racer_name]['event_points'] += br_kills * br_kill_points
                            event_data[racer_name]['event_points'] += br_damage * damage_points

                            if position == 1:
                                event_data[racer_name]['br_wins'] += 1
                                if marble_count >= 10:
                                    if last_br_win[racer_name] is not None:
                                        event_data[racer_name]['crownwins'] += 1
                                    last_br_win[racer_name] = timestamp

                        if not eliminated or give_position_points_on_dnf:
                            event_data[racer_name]['event_points'] += position_points.get(position, 0)

        except FileNotFoundError:
            print(f"File not found: {allraces}")
        except Exception as e:
            logger.error("An error occurred while processing the file %s", allraces, exc_info=True)

    # Process checkpoint files similarly to allraces
    for checkpoint_file in glob.glob(os.path.join(directory, "checkpoints_*.csv")):
        try:
            with open(checkpoint_file, 'r', encoding='utf-8', errors='ignore') as f:
                reader = iter_csv_rows(f)
                for row in reader:
                    try:
                        racer_name = row[1].lower()
                        if racer_name in event_data:
                            event_data[racer_name]['event_points'] += checkpoint_points
                            # print(f"Applied {checkpoint_points} to {racer_name} for checkpoint result")
                    except IndexError:
                        # Handle missing columns by skipping the row
                        continue

        except FileNotFoundError:
            print(f"File not found: {checkpoint_file}")
        except Exception as e:
            logger.error("An error occurred while processing the file %s", checkpoint_file, exc_info=True)

    # Use %localappdata%/mystats/data as the save directory
    local_app_data = os.getenv('LOCALAPPDATA')
    save_directory = os.path.join(local_app_data, 'mystats', 'data')

    # Ensure the directory exists
    if not os.path.exists(save_directory):
        try:
            os.makedirs(save_directory)
        except OSError as e:
            print(f"Error creating directory {save_directory}: {e}")
            return

    event_data_csv = os.path.join(save_directory, f"{event_id}_eventdata.csv")
    try:
        with open(event_data_csv, 'w', newline='') as csvfile:
            fieldnames = ['racer_name', 'channel', 'race_points', 'race_wins', 'race_races', 'br_points', 'br_wins',
                          'br_races', 'crownwins', 'br_kills', 'br_damage', 'eliminations', 'event_points']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for racer in event_data.values():
                writer.writerow(racer)
    except Exception as e:
        logger.error("Error saving CSV file", exc_info=True)

    # Upload event data CSV to API
    api_url = f"https://mystats.camwow.tv/api/app/upload-event-data/"
    files = {
        'eventData': open(event_data_csv, 'rb'),
    }
    data = {
        'eventId': event_id
    }
    try:
        response = requests.post(api_url, files=files, data=data)
        response.raise_for_status()
        print(f"Successfully uploaded event {event_id} data.")
    except requests.exceptions.RequestException as e:
        print(f"Error uploading event data: {e}")


def write_overlays():
    with open(appdata_path('race_hs_season.txt'), 'w', encoding='utf-8', errors='ignore') as rhs:
        if config.get_setting('race_hs_season') is not None:
            rhs.write(str(f"{int(config.get_setting('race_hs_season')):,}\n"))
        else:
            rhs.write("0\n")

    with open(appdata_path('br_hs_season.txt'), 'w', encoding='utf-8', errors='ignore') as bhs:
        if config.get_setting('br_hs_season') is not None:
            bhs.write(str(f"{int(config.get_setting('br_hs_season')):,}\n"))
        else:
            bhs.write("0\n")

    with open(appdata_path('race_hs_today.txt'), 'w', encoding='utf-8', errors='ignore') as rhs:
        if config.get_setting('race_hs_today') is not None:
            rhs.write(str(f"{int(config.get_setting('race_hs_today')):,}\n"))
        else:
            rhs.write("0\n")

    with open(appdata_path('br_hs_today.txt'), 'w', encoding='utf-8', errors='ignore') as brhs:
        if config.get_setting('br_hs_today') is not None:
            brhs.write(f"{int(config.get_setting('br_hs_today')):,}\n")
        else:
            brhs.write("0\n")

    with open(appdata_path('TotalPointsToday.txt'), 'w', encoding='utf-8', errors='ignore') as f:
        if config.get_setting('totalpointstoday') is not None:
            f.write(f"{int(config.get_setting('totalpointstoday')):,}\n")
        else:
            f.write("0\n")

    with open(appdata_path('AvgPointsToday.txt'), 'w', encoding='utf-8', errors='ignore') as f:
        if config.get_setting('avgpointstoday') is not None:
            f.write(str(f"{int(float(config.get_setting('avgpointstoday'))):,}\n"))
        else:
            f.write("0\n")

    with open(appdata_path('CountofRaces.txt'), 'w', encoding='utf-8', errors='ignore') as f:
        if config.get_setting('totalcounttoday') is not None:
            f.write(str(f"{int(config.get_setting('totalcounttoday')):,}\n"))
        else:
            f.write("0\n")


def create_results_files():
    timestamp, timestampMDY, timestampHMS, adjusted_time = time_manager.get_adjusted_time()

    base_directory = appdata_path()
    directory = os.path.join(base_directory, "Results", "Season_" + str(config.get_setting('season')))
    config.set_setting('directory', directory, persistent=True)
    if not os.path.exists(directory):
        os.makedirs(directory)

    allraces = os.path.join(directory, "allraces_" + adjusted_time.strftime("%Y-%m-%d") + ".csv")
    config.set_setting('allraces_file', allraces, persistent=True)
    if not os.path.exists(allraces):
        with open(allraces, 'w', encoding='utf-8') as allraces_tmp:
            pass

    checkpoint_results = os.path.join(directory, "checkpoints_" + adjusted_time.strftime("%Y-%m-%d") + ".csv")
    config.set_setting('checkpoint_results_file', checkpoint_results, persistent=True)
    if not os.path.exists(checkpoint_results):
        with open(checkpoint_results, 'w', encoding='utf-8') as chkpoint_tmp:
            pass

    tilt_results = os.path.join(directory, "tilts_" + adjusted_time.strftime("%Y-%m-%d") + ".csv")
    config.set_setting('tilts_results_file', tilt_results, persistent=True)
    if not os.path.exists(tilt_results):
        with open(tilt_results, 'w', encoding='utf-8') as tilt_tmp:
            pass

    map_results = os.path.join(directory, "maps_" + adjusted_time.strftime("%Y-%m-%d") + ".csv")
    config.set_setting('map_results_file', map_results, persistent=True)
    if not os.path.exists(map_results):
        with open(map_results, 'w', encoding='utf-8') as commmap_tmp:
            pass

    br_file = os.path.expanduser(r"~\AppData\Local\MarblesOnStream\Saved\SaveGames\LastSeasonRoyale.csv")
    config.set_setting('br_file', br_file, persistent=True)
    try:
        open(br_file, "r", encoding='utf-8', errors='ignore').close()
    except FileNotFoundError:
        with open(appdata_path('log.txt'), 'a') as f:
            f.write(
                f"[{timestamp}]  - ~\\AppData\\Local\\MarblesOnStream\\Saved\\SaveGames\\LastSeasonRoyale.csv "
                f"does not exist\n")
    except Exception as e:
        logger.error("We see no record of you hosting a Battle Royale.  Do that.", exc_info=True)

    race_file = os.path.expanduser(r"~\AppData\Local\MarblesOnStream\Saved\SaveGames\LastSeasonRace.csv")
    config.set_setting('race_file', race_file, persistent=True)
    try:
        open(race_file, "r", encoding='utf-8', errors='ignore').close()
    except FileNotFoundError:
        with open(appdata_path('log.txt'), 'a') as f:
            f.write(
                f"[{timestamp}]  - ~\\AppData\\Local\\MarblesOnStream\\Saved\\SaveGames\\LastSeasonRace.csv "
                f"does not exist\n")
    except Exception as e:
        logger.error("We see no record of you hosting a map race.  Do that.", exc_info=True)

    tilt_player_file = os.path.expanduser(r"~\AppData\Local\MarblesOnStream\Saved\SaveGames\LastTiltLevelPlayers.csv")
    config.set_setting('tilt_player_file', tilt_player_file, persistent=True)
    try:
        open(tilt_player_file, "r", encoding='utf-8', errors='ignore').close()
    except FileNotFoundError:
        with open(appdata_path('log.txt'), 'a') as f:
            f.write(
                f"[{timestamp}]  - ~\\AppData\\Local\\MarblesOnStream\\Saved\\SaveGames\\LastTiltLevelPlayers.csv "
                f"does not exist\n")
    except Exception as e:
        logger.error("No tilt file, tilt again or get tilted.", exc_info=True)

    tilt_level_file = os.path.expanduser(r"~\AppData\Local\MarblesOnStream\Saved\SaveGames\LastTiltLevel.csv")
    config.set_setting('tilt_level_file', tilt_level_file, persistent=True)
    try:
        open(tilt_level_file, "r", encoding='utf-8', errors='ignore').close()
    except FileNotFoundError:
        with open(appdata_path('log.txt'), 'a') as f:
            f.write(
                f"[{timestamp}]  - ~\\AppData\\Local\\MarblesOnStream\\Saved\\SaveGames\\LastTiltLevel.csv "
                f"does not exist\n")
    except Exception as e:
        logger.error("No tilt file, tilt again or get tilted.", exc_info=True)

    checkpoint_file = os.path.expanduser(r"~\AppData\Local\MarblesOnStream\Saved\SaveGames\LastRaceNumbersHit.csv")
    config.set_setting('checkpoint_file', checkpoint_file, persistent=True)
    try:
        open(checkpoint_file, "r", encoding='utf-8', errors='ignore').close()
    except FileNotFoundError:
        with open(appdata_path('log.txt'), 'a') as f:
            f.write(
                f"[{timestamp}]  - ~\\AppData\\Local\\MarblesOnStream\\Saved\\SaveGames\\LastRaceNumbersHit.csv "
                f"does not exist\n")
    except Exception as e:
        logger.error("We see no record.  Do something.", exc_info=True)

    map_file = os.path.expanduser(r"~\AppData\Local\MarblesOnStream\Saved\SaveGames\LastCustomRaceMapPlayed.csv")
    config.set_setting('map_data_file', map_file, persistent=True)
    try:
        open(map_file, "r", encoding='utf-8', errors='ignore').close()
    except FileNotFoundError:
        with open(appdata_path('log.txt'), 'a') as f:
            f.write(
                f"[{timestamp}]  - ~\\AppData\\Local\\MarblesOnStream\\Saved\\SaveGames\\LastCustomRaceMapPlayed.csv "
                f"does not exist\n")
    except Exception as e:
        logger.error("We see no record.  Do something.", exc_info=True)


def load_racer_data():
    racer_data = defaultdict(lambda: {
        'racer_name': '',
        'race_points': 0,
        'race_wins': 0,
        'race_races': 0,
        'br_points': 0,
        'br_wins': 0,
        'br_races': 0
    })

    current_season = config.get_setting('season')

    for allraces in glob.glob(os.path.join(config.get_setting('directory'), "allraces_*.csv")):
        try:
            with open(allraces, 'rb') as f:
                raw_data = f.read()

            # Detect encoding using chardet
            result = chardet.detect(raw_data)
            encoding = result['encoding'] if result['encoding'] else 'utf-8'
            with open(allraces, 'r', encoding=encoding, errors='ignore') as f:
                reader = iter_csv_rows(f)
                for row in reader:
                    if len(row) < 7:
                        continue

                    position = int(row[0])
                    racer_name = row[1].lower()
                    points = int(row[3])
                    race_type = row[4]

                    racer_data[racer_name]['racer_name'] = racer_name
                    racer_data[racer_name]['season'] = current_season

                    if race_type == 'Race':
                        racer_data[racer_name]['race_points'] += points
                        racer_data[racer_name]['race_races'] += 1
                        if position == 1:
                            racer_data[racer_name]['race_wins'] += 1

                    if race_type == 'BR':
                        racer_data[racer_name]['br_points'] += points
                        racer_data[racer_name]['br_races'] += 1
                        if position == 1:
                            racer_data[racer_name]['br_wins'] += 1

        except FileNotFoundError:
            print(f"File not found: {allraces}")
        except Exception as e:
            logger.error("An error occurred while processing the file %s", allraces, exc_info=True)

    racer_data = dict(racer_data)

    json_data = json.dumps(racer_data, indent=4)
    config.set_setting('allracerdata', json_data, persistent=False)


def load_additional_settings():
    if config.get_setting('directory') in ['', None]:
        create_results_files()

    with MYCYCLE_LOCK:
        cycle_data = load_mycycle_data()
        migrated = bool(cycle_data.pop('_changed', False))
        _, changed = ensure_default_mycycle_session(cycle_data)
        if changed or migrated:
            save_mycycle_data(cycle_data)

    load_race_hs_season = 0
    load_race_hs_today = 0
    load_br_hs_season = 0
    load_br_hs_today = 0
    load_totalpointsseason = 0
    load_totalcountseason = 0
    load_totalpointstoday = 0
    load_totalcounttoday = 0

    for allraces in glob.glob(os.path.join(config.get_setting('directory'), "allraces_*.csv")):
        try:
            with open(allraces, 'rb') as f:
                raw_data = f.read()

            result = chardet.detect(raw_data)
            encoding = result['encoding'] if result['encoding'] else 'utf-8'
            with open(allraces, 'r', encoding=encoding, errors='ignore') as f:
                reader = iter_csv_rows(f)
                for row in reader:
                    if len(row) >= 5:
                        if int(row[0]) == 1:
                            load_totalcountseason += 1
                        if row[4] == 'Race' and int(row[3]) > load_race_hs_season:
                            load_race_hs_season = int(row[3])
                        elif row[4] == 'BR' and int(row[3]) > load_br_hs_season:
                            load_br_hs_season = int(row[3])
                        load_totalpointsseason += int(row[3])
        except FileNotFoundError:
            print(f"File not found: {allraces}")
        except Exception as e:
            logger.error("An error occurred while processing the file %s", allraces, exc_info=True)

    config.set_setting('totalpointsseason', load_totalpointsseason, persistent=False)
    config.set_setting('totalcountseason', load_totalcountseason, persistent=False)
    config.set_setting('race_hs_season', load_race_hs_season, persistent=False)
    config.set_setting('br_hs_season', load_br_hs_season, persistent=False)

    high_score_row = [0, 'No Data', 'No Data', 0, 0, 0, 0]

    try:
        with open(config.get_setting('allraces_file'), 'rb') as f:
            raw_data = f.read()

        # Detect encoding using chardet
        result = chardet.detect(raw_data)
        encoding = result['encoding'] if result['encoding'] else 'utf-8'  # Default to UTF-8 if detection fails

        with open(config.get_setting('allraces_file'), 'r', encoding=encoding, errors='ignore') as t:
            today_reader = iter_csv_rows(t)
            rows = list(today_reader)

            for row in rows:
                if len(row) >= 5:
                    load_totalpointstoday += int(row[3])
                    if int(row[0]) == 1:
                        load_totalcounttoday += 1
                    if row[4] == 'Race' and int(row[3]) > load_race_hs_today:
                        load_race_hs_today = int(row[3])
                    elif row[4] == 'BR' and int(row[3]) > load_br_hs_today:
                        load_br_hs_today = int(row[3])
            high_score_row = max(rows, key=lambda row: int(row[3]) if len(row) >= 5 else 0,
                                 default=[0, 'New Marble Day!', 'New Marble Day!', 0, 0, 0, 0])
    except FileNotFoundError:
        print(f"File not found: " + config.get_setting('allraces_file'))
        with open(config.get_setting('allraces_file'), 'w', encoding='utf-8', errors='ignore'):
            pass
    except csv.Error as e:
        logger.error("Malformed CSV in allraces_file (possible bad quoting): %s", e)

    if load_totalcounttoday == 0:
        load_averagepointstoday = 0
    else:
        load_averagepointstoday = load_totalpointstoday / load_totalcounttoday

    config.set_setting('totalpointstoday', load_totalpointstoday, persistent=False)
    config.set_setting('totalcounttoday', load_totalcounttoday, persistent=False)
    config.set_setting('avgpointstoday', load_averagepointstoday, persistent=False)
    config.set_setting('race_hs_today', load_race_hs_today, persistent=False)
    config.set_setting('br_hs_today', load_br_hs_today, persistent=False)

    if high_score_row[1] != high_score_row[2].lower():
        winnersname = high_score_row[1]
    else:
        winnersname = high_score_row[2]

    config.set_setting('hscore_name', winnersname, persistent=False)
    config.set_setting('hscore', high_score_row[3], persistent=False)


def open_url(url):
    webbrowser.open_new(url)


def _launch_hidden_powershell(script_text):
    encoded = base64.b64encode(script_text.encode('utf-16-le')).decode('ascii')
    startup_info = None
    creation_flags = 0

    if hasattr(subprocess, "STARTUPINFO"):
        startup_info = subprocess.STARTUPINFO()
        startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        creation_flags = subprocess.CREATE_NO_WINDOW

    process = subprocess.Popen(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-EncodedCommand",
            encoded,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        startupinfo=startup_info,
        creationflags=creation_flags,
    )

    return process


def _show_windows_native_toast(title, message):
    if sys.platform != "win32":
        return False

    title_xml = html.escape(str(title), quote=False)
    message_xml = html.escape(str(message), quote=False)

    script = f"""
$ErrorActionPreference = 'Stop'
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
$xmlTemplate = @"
<toast>
  <visual>
    <binding template='ToastGeneric'>
      <text>{title_xml}</text>
      <text>{message_xml}</text>
    </binding>
  </visual>
</toast>
"@
$xmlDoc = New-Object Windows.Data.Xml.Dom.XmlDocument
$xmlDoc.LoadXml($xmlTemplate)
$toast = [Windows.UI.Notifications.ToastNotification]::new($xmlDoc)
$notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('MyStats')
$notifier.Show($toast)
"""

    try:
        process = _launch_hidden_powershell(script)
        exit_code = process.wait(timeout=4)

        if exit_code != 0:
            logger.warning(f"Toast notification failed via native WinRT toast: PowerShell exited with code {exit_code}")
            return False

        return True
    except Exception as exc:
        logger.warning(f"Toast notification failed via native WinRT toast: {exc}")
        return False


def _show_windows_balloon_tip(title, message, duration=6):
    if sys.platform != "win32":
        return False

    script = f"""
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$notify = New-Object System.Windows.Forms.NotifyIcon
$notify.Icon = [System.Drawing.SystemIcons]::Information
$notify.BalloonTipTitle = @"
{title}
"@
$notify.BalloonTipText = @"
{message}
"@
$notify.Visible = $true
$notify.ShowBalloonTip({max(1, int(duration)) * 1000})
Start-Sleep -Milliseconds {max(1, int(duration)) * 1000 + 600}
$notify.Dispose()
"""

    try:
        _launch_hidden_powershell(script)
        return True
    except Exception as exc:
        logger.warning(f"Toast notification failed via PowerShell balloon tip: {exc}")
        return False




def _show_in_app_toast(title, message, duration=6):
    if root is None or not root.winfo_exists():
        return False

    def _render_toast():
        try:
            toast = tk.Toplevel(root)
            toast.overrideredirect(True)
            toast.attributes('-topmost', True)
            toast.configure(bg='#1e1e1e')

            frame = tk.Frame(toast, bg='#1e1e1e', bd=1, relief='solid')
            frame.pack(fill='both', expand=True)

            tk.Label(
                frame,
                text=title,
                bg='#1e1e1e',
                fg='white',
                font=('Segoe UI', 10, 'bold'),
                anchor='w',
                padx=10,
                pady=(8, 2),
            ).pack(fill='x')

            tk.Label(
                frame,
                text=message,
                bg='#1e1e1e',
                fg='white',
                font=('Segoe UI', 9),
                justify='left',
                wraplength=320,
                anchor='w',
                padx=10,
                pady=(0, 8),
            ).pack(fill='x')

            toast.update_idletasks()
            width = max(260, min(380, toast.winfo_reqwidth()))
            height = max(90, min(220, toast.winfo_reqheight()))
            screen_w = toast.winfo_screenwidth()
            screen_h = toast.winfo_screenheight()
            x = screen_w - width - 20
            y = screen_h - height - 60
            toast.geometry(f"{width}x{height}+{x}+{y}")

            toast.after(max(2000, int(duration) * 1000), toast.destroy)
        except Exception as exc:
            logger.warning(f"Toast notification failed via in-app popup: {exc}")

    try:
        root.after(0, _render_toast)
        return True
    except Exception as exc:
        logger.warning(f"Toast notification failed scheduling in-app popup: {exc}")
        return False

def show_windows_toast(title, message, duration=6):
    is_frozen_build = bool(getattr(sys, "frozen", False))

    if win_toaster is not None:
        try:
            win_toaster.show_toast(title, message, duration=duration, threaded=True)
            if not is_frozen_build:
                return
        except Exception as exc:
            logger.warning(f"Toast notification failed via win10toast: {exc}")

    if is_frozen_build:
        # In PyInstaller builds, WinRT toast APIs can report success without displaying
        # anything if the app identity/shortcut registration is missing. Prefer a
        # balloon tip first because it works for unpackaged desktop executables.
        if _show_windows_balloon_tip(title, message, duration=duration):
            return

    if _show_windows_native_toast(title, message):
        return

    if _show_windows_balloon_tip(title, message, duration=duration):
        return

    if tray_icon is not None:
        try:
            tray_icon.notify(message, title)
            return
        except Exception as exc:
            logger.warning(f"Toast notification failed via tray icon: {exc}")

    _show_in_app_toast(title, message, duration=duration)


def is_minimized_to_tray():
    return tray_icon is not None and root is not None and root.winfo_exists() and not root.winfo_viewable()


def _create_update_progress_dialog(version_label):
    progress_window = tk.Toplevel(root)
    progress_window.title("Downloading Update")
    progress_window.geometry("420x160")
    progress_window.transient(root)

    root_x = root.winfo_x()
    root_y = root.winfo_y()
    root_width = root.winfo_width()
    root_height = root.winfo_height()
    pos_x = root_x + (root_width // 2) - 210
    pos_y = root_y + (root_height // 2) - 80
    progress_window.geometry(f"420x160+{pos_x}+{pos_y}")

    ttk.Label(
        progress_window,
        text=f"Downloading MyStats {version_label}...",
        style="Small.TLabel"
    ).pack(anchor='w', padx=16, pady=(14, 8))

    progress_var = tk.DoubleVar(value=0.0)
    progress_bar = ttk.Progressbar(progress_window, mode='determinate', maximum=100, variable=progress_var)
    progress_bar.pack(fill='x', padx=16)

    percent_var = tk.StringVar(value="0%")
    ttk.Label(progress_window, textvariable=percent_var).pack(anchor='e', padx=16, pady=(8, 0))

    status_var = tk.StringVar(value="Preparing download...")
    ttk.Label(progress_window, textvariable=status_var, style="Small.TLabel").pack(anchor='w', padx=16, pady=(6, 10))

    progress_window.protocol("WM_DELETE_WINDOW", lambda: None)
    return progress_window, progress_var, percent_var, status_var


def _launch_update_splash(version_label, installer_pid):
    """Launch a standalone PowerShell splash window that monitors the installer.

    The splash runs as a separate process so it survives MyStats shutting down.
    It shows a branded indeterminate progress bar and closes automatically when
    the installer process (identified by *installer_pid*) exits.
    """
    ps_script = r'''
Add-Type -AssemblyName PresentationFramework
Add-Type -AssemblyName PresentationCore

[xml]$xaml = @"
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        Title="MyStats Update" Height="180" Width="420"
        WindowStartupLocation="CenterScreen" ResizeMode="NoResize"
        WindowStyle="SingleBorderWindow" Topmost="True"
        Background="#1a1a2e">
    <Grid Margin="24">
        <Grid.RowDefinitions>
            <RowDefinition Height="Auto"/>
            <RowDefinition Height="16"/>
            <RowDefinition Height="Auto"/>
            <RowDefinition Height="12"/>
            <RowDefinition Height="Auto"/>
        </Grid.RowDefinitions>
        <TextBlock Grid.Row="0" Text="MYSTATS_VERSION_PLACEHOLDER"
                   Foreground="#00d4ff" FontSize="18" FontWeight="Bold"
                   HorizontalAlignment="Center"/>
        <ProgressBar Grid.Row="2" Height="22" IsIndeterminate="True"
                     Foreground="#00d4ff" Background="#2a2a4a"/>
        <TextBlock Grid.Row="4" Text="Please wait while the update installs..."
                   Foreground="#aaaacc" FontSize="12"
                   HorizontalAlignment="Center"/>
    </Grid>
</Window>
"@

$reader = (New-Object System.Xml.XmlNodeReader $xaml)
$window = [Windows.Markup.XamlReader]::Load($reader)

$installerPid = INSTALLER_PID_PLACEHOLDER
$timer = New-Object System.Windows.Threading.DispatcherTimer
$timer.Interval = [TimeSpan]::FromSeconds(2)
$timer.Add_Tick({
    try {
        $proc = Get-Process -Id $installerPid -ErrorAction Stop
    } catch {
        $timer.Stop()
        $window.Close()
    }
})
$timer.Start()
$window.ShowDialog() | Out-Null
'''.replace('MYSTATS_VERSION_PLACEHOLDER', f'Updating MyStats to {version_label} ...').replace(
        'INSTALLER_PID_PLACEHOLDER', str(installer_pid))

    try:
        subprocess.Popen(
            ['powershell', '-NoProfile', '-WindowStyle', 'Hidden',
             '-ExecutionPolicy', 'Bypass', '-Command', ps_script],
            creationflags=getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.info("Update splash launched for installer PID %s", installer_pid)
    except Exception as exc:
        logger.warning("Could not launch update splash: %s", exc)


def _schedule_installer_bootstrap(installer_path, command_args, version_label, parent_pid):
    """Schedule a one-shot Windows task that launches installer + splash outside MyStats job."""
    if sys.platform != "win32":
        raise RuntimeError("Windows bootstrap scheduling is only available on win32")

    task_name = f"MyStatsUpdate_{uuid.uuid4().hex}"
    escaped_args = ', '.join("'" + str(arg).replace("'", "''") + "'" for arg in command_args)

    ps_script = f"""
$ErrorActionPreference = 'Stop'
$installerPath = {json.dumps(installer_path)}
$installerArgs = @({escaped_args})
$versionLabel = {json.dumps(version_label or 'latest')}
$parentPid = {int(parent_pid)}
$taskName = {json.dumps(task_name)}

try {{
    while (Get-Process -Id $parentPid -ErrorAction SilentlyContinue) {{
        Start-Sleep -Milliseconds 500
    }}

    $installer = Start-Process -FilePath $installerPath -ArgumentList $installerArgs -PassThru -WindowStyle Hidden

    Add-Type -AssemblyName PresentationFramework
    Add-Type -AssemblyName PresentationCore

    [xml]$xaml = @"
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        Title="MyStats Update" Height="180" Width="420"
        WindowStartupLocation="CenterScreen" ResizeMode="NoResize"
        WindowStyle="SingleBorderWindow" Topmost="True"
        Background="#1a1a2e">
    <Grid Margin="24">
        <Grid.RowDefinitions>
            <RowDefinition Height="Auto"/>
            <RowDefinition Height="16"/>
            <RowDefinition Height="Auto"/>
            <RowDefinition Height="12"/>
            <RowDefinition Height="Auto"/>
        </Grid.RowDefinitions>
        <TextBlock Grid.Row="0" Text="Updating MyStats to $($versionLabel) ..."
                   Foreground="#00d4ff" FontSize="18" FontWeight="Bold"
                   HorizontalAlignment="Center"/>
        <ProgressBar Grid.Row="2" Height="22" IsIndeterminate="True"
                     Foreground="#00d4ff" Background="#2a2a4a"/>
        <TextBlock Grid.Row="4" Text="Please wait while the update installs..."
                   Foreground="#aaaacc" FontSize="12"
                   HorizontalAlignment="Center"/>
    </Grid>
</Window>
"@

    $reader = New-Object System.Xml.XmlNodeReader $xaml
    $window = [Windows.Markup.XamlReader]::Load($reader)
    $timer = New-Object System.Windows.Threading.DispatcherTimer
    $timer.Interval = [TimeSpan]::FromSeconds(1)
    $timer.Add_Tick({{
        if (-not (Get-Process -Id $installer.Id -ErrorAction SilentlyContinue)) {{
            $timer.Stop()
            $window.Close()
        }}
    }})
    $timer.Start()
    $window.ShowDialog() | Out-Null
}} finally {{
    schtasks /Delete /TN $taskName /F | Out-Null
}}
""".strip()

    with tempfile.NamedTemporaryFile(delete=False, suffix='.ps1', prefix='mystats_update_bootstrap_', mode='w', encoding='utf-8') as script_file:
        script_file.write(ps_script)
        script_path = script_file.name

    run_time = (get_internal_adjusted_time() + timedelta(minutes=1)).strftime("%H:%M")
    task_command = f'powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "{script_path}"'

    try:
        subprocess.run(
            ['schtasks', '/Create', '/F', '/SC', 'ONCE', '/ST', run_time, '/TN', task_name, '/TR', task_command],
            check=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            ['schtasks', '/Run', '/TN', task_name],
            check=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.info("Installer bootstrap scheduled with task %s", task_name)
    except Exception:
        try:
            os.remove(script_path)
        except OSError:
            pass
        raise


def _launch_installer_process(installer_path, command_args):
    """Launch installer in a way that survives MyStats process shutdown."""
    if sys.platform == "win32":
        # Prefer CreateProcess via subprocess first so we can request breakaway
        # from the parent job object (common when running from packaged apps).
        # Without breakaway, Windows can terminate child processes when MyStats
        # exits, which can kill the updater right after launch.
        try:
            creationflags = 0
            creationflags |= getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0)
            creationflags |= getattr(subprocess, 'DETACHED_PROCESS', 0x00000008)
            creationflags |= getattr(subprocess, 'CREATE_BREAKAWAY_FROM_JOB', 0x01000000)

            proc = subprocess.Popen(
                [installer_path, *command_args],
                creationflags=creationflags,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
            )
            logger.info("Installer launched via CreateProcess (pid=%s)", proc.pid)
            return proc
        except Exception as popen_exc:
            logger.warning("CreateProcess installer launch failed, falling back to ShellExecuteExW: %s", popen_exc)

        params = subprocess.list2cmdline(command_args)

        class SHELLEXECUTEINFOW(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.c_ulong),
                ("fMask", ctypes.c_ulong),
                ("hwnd", ctypes.c_void_p),
                ("lpVerb", ctypes.c_wchar_p),
                ("lpFile", ctypes.c_wchar_p),
                ("lpParameters", ctypes.c_wchar_p),
                ("lpDirectory", ctypes.c_wchar_p),
                ("nShow", ctypes.c_int),
                ("hInstApp", ctypes.c_void_p),
                ("lpIDList", ctypes.c_void_p),
                ("lpClass", ctypes.c_wchar_p),
                ("hkeyClass", ctypes.c_void_p),
                ("dwHotKey", ctypes.c_ulong),
                ("hIconOrMonitor", ctypes.c_void_p),
                ("hProcess", ctypes.c_void_p),
            ]

        sei = SHELLEXECUTEINFOW()
        sei.cbSize = ctypes.sizeof(SHELLEXECUTEINFOW)
        sei.fMask = 0x00000040  # SEE_MASK_NOCLOSEPROCESS
        sei.hwnd = None
        sei.lpVerb = "open"
        sei.lpFile = installer_path
        sei.lpParameters = params
        sei.lpDirectory = None
        sei.nShow = 0

        shell_execute_ex = ctypes.windll.shell32.ShellExecuteExW
        shell_execute_ex.argtypes = [ctypes.POINTER(SHELLEXECUTEINFOW)]
        shell_execute_ex.restype = ctypes.c_int

        if not shell_execute_ex(ctypes.byref(sei)):
            error_code = ctypes.windll.kernel32.GetLastError()
            raise RuntimeError(f"ShellExecuteExW failed with error {error_code}")

        process_handle = sei.hProcess
        process_id = ctypes.windll.kernel32.GetProcessId(process_handle)

        if process_id:
            logger.info("Installer launched via ShellExecuteExW (pid=%s)", process_id)

            class _InstallerProcRef:
                def __init__(self, pid, handle):
                    self.pid = pid
                    self._handle = handle

                def poll(self):
                    if not self._handle:
                        return 0

                    WAIT_OBJECT_0 = 0
                    WAIT_TIMEOUT = 0x00000102
                    wait_status = ctypes.windll.kernel32.WaitForSingleObject(self._handle, 0)
                    if wait_status == WAIT_TIMEOUT:
                        return None
                    if wait_status != WAIT_OBJECT_0:
                        return None

                    exit_code = ctypes.c_ulong()
                    if ctypes.windll.kernel32.GetExitCodeProcess(self._handle, ctypes.byref(exit_code)):
                        ctypes.windll.kernel32.CloseHandle(self._handle)
                        self._handle = None
                        return int(exit_code.value)
                    return None

            return _InstallerProcRef(process_id, process_handle)

        # If process ID was unavailable, keep legacy behavior and continue without PID tracking.
        logger.info("Installer launched via ShellExecuteExW (process id unavailable)")
        if process_handle:
            ctypes.windll.kernel32.CloseHandle(process_handle)
        return None

    creationflags = getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0)
    creationflags |= getattr(subprocess, 'CREATE_BREAKAWAY_FROM_JOB', 0x01000000)
    proc = subprocess.Popen(
        [installer_path, *command_args],
        creationflags=creationflags,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    logger.info("Installer process started, PID=%s", proc.pid)
    return proc

def _launch_installer_detached(installer_path, command_args):
    """Launch installer via an intermediate process so it is not a MyStats child."""
    if sys.platform != "win32":
        return _launch_installer_process(installer_path, command_args)

    installer_path_ps = installer_path.replace("'", "''")
    installer_args_ps = ', '.join("'" + str(arg).replace("'", "''") + "'" for arg in command_args)

    if command_args:
        start_process_line = "Start-Process -FilePath $installerPath -ArgumentList $installerArgs -WindowStyle Normal"
    else:
        start_process_line = "Start-Process -FilePath $installerPath -WindowStyle Normal"

    ps_script = f"""
$installerPath = '{installer_path_ps}'
$installerArgs = @({installer_args_ps})
{start_process_line}
""".strip()

    powershell_exe = os.path.join(os.environ.get('SystemRoot', r'C:\Windows'), 'System32', 'WindowsPowerShell', 'v1.0', 'powershell.exe')
    if not os.path.exists(powershell_exe):
        powershell_exe = 'powershell.exe'

    creationflags = getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0)
    creationflags |= getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)

    try:
        subprocess.Popen(
            [powershell_exe, '-NoProfile', '-WindowStyle', 'Hidden', '-ExecutionPolicy', 'Bypass', '-Command', ps_script],
            creationflags=creationflags,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )
        logger.info("Detached installer bootstrap process launched via %s", powershell_exe)
        return None
    except FileNotFoundError:
        logger.warning("PowerShell was not found. Falling back to direct installer launch.")
    except OSError as exc:
        logger.warning("PowerShell bootstrap launch failed (%s). Falling back to direct installer launch.", exc)

    # Fallback still launches the installer, though as a direct process from MyStats.
    return _launch_installer_process(installer_path, command_args)


def _start_installer_and_exit(installer_path, silent_mode=True):
    if not installer_path or not os.path.exists(installer_path):
        logger.error("Installer not found on disk: %s", installer_path)
        messagebox.showerror("Update Failed", "Downloaded installer was not found on disk.")
        return

    # Validate the file is actually a PE executable (MZ header).
    try:
        with open(installer_path, 'rb') as f:
            header = f.read(2)
        if header != b'MZ':
            logger.error("Downloaded file is not a valid executable (header: %r)", header)
            messagebox.showerror(
                "Update Failed",
                "The downloaded update file is not a valid installer.\n"
                "Please try again or download manually from the website."
            )
            try:
                os.remove(installer_path)
            except OSError:
                pass
            return
    except OSError as exc:
        logger.error("Could not read installer file for validation: %s", exc)
        messagebox.showerror("Update Failed", f"Could not read installer file: {exc}")
        return

    file_size = os.path.getsize(installer_path)
    logger.info("Installer validated: %s (%d bytes)", installer_path, file_size)

    # Launch installer with normal interactive behavior.
    command_args = []
    command = [installer_path, *command_args]

    version_label = str(config.get_setting('pending_update_version_label') or '').strip()

    # Save recovery settings BEFORE launch so if the app crashes mid-launch,
    # recovery can retry on next startup.
    config.set_setting('pending_update_installer_path', installer_path, persistent=True)
    config.set_setting('pending_update_silent_mode', 'True', persistent=True)
    config.set_setting('pending_update_version_label', version_label, persistent=True)

    try:
        logger.info("Launching installer: %s", command)

        proc = _launch_installer_detached(installer_path, command_args)

        # Verify direct child launches are still alive (when we have a process
        # handle). ShellExecute launches do not provide a child PID here.
        if proc is not None:
            import time as _time
            _time.sleep(1)
            exit_code = proc.poll()
            if exit_code is not None:
                logger.error("Installer exited immediately with code %s", exit_code)
                messagebox.showerror(
                    "Update Failed",
                    f"The installer exited immediately (code {exit_code}).\n"
                    "It may have been blocked by antivirus software.\n"
                    "Please try downloading and running the installer manually."
                )
                config.set_setting('pending_update_installer_path', '', persistent=True)
                config.set_setting('pending_update_version_label', '', persistent=True)
                return

        # Installer launch attempt completed — clear recovery settings.
        config.set_setting('pending_update_installer_path', '', persistent=True)
        config.set_setting('pending_update_silent_mode', 'True', persistent=True)
        config.set_setting('pending_update_version_label', '', persistent=True)
        logger.info("Installer launched. Leaving MyStats open for installer-managed shutdown.")

    except Exception as exc:
        logger.error("Failed to launch installer: %s", exc, exc_info=True)
        messagebox.showerror(
            "Update Failed",
            f"Could not start installer: {exc}\n"
            "Please try downloading and running the installer manually."
        )


def recover_pending_update_launch(parent=None):
    installer_path = str(config.get_setting('pending_update_installer_path') or '').strip()
    version_label = str(config.get_setting('pending_update_version_label') or '').strip()

    if not installer_path:
        return False

    if not os.path.exists(installer_path):
        logger.info("Recovery: installer file gone, clearing settings.")
        config.set_setting('pending_update_installer_path', '', persistent=True)
        config.set_setting('pending_update_silent_mode', 'True', persistent=True)
        config.set_setting('pending_update_version_label', '', persistent=True)
        return False

    # Validate PE header.
    try:
        with open(installer_path, 'rb') as f:
            if f.read(2) != b'MZ':
                logger.error("Recovery: installer file is not a valid PE executable.")
                config.set_setting('pending_update_installer_path', '', persistent=True)
                config.set_setting('pending_update_version_label', '', persistent=True)
                return False
    except OSError:
        config.set_setting('pending_update_installer_path', '', persistent=True)
        config.set_setting('pending_update_version_label', '', persistent=True)
        return False

    command_args = []
    command = [installer_path, *command_args]

    try:
        logger.info("Recovery: launching installer %s", command)

        proc = _launch_installer_detached(installer_path, command_args)
        if proc is not None:
            logger.info("Recovery: installer PID=%s", proc.pid)

        config.set_setting('pending_update_installer_path', '', persistent=True)
        config.set_setting('pending_update_silent_mode', 'True', persistent=True)
        config.set_setting('pending_update_version_label', '', persistent=True)

        label_suffix = f" {version_label}" if version_label else ""
        show_windows_toast("MyStats Update", f"Resuming installer launch{label_suffix}.")

        # Do not force-close MyStats here. We only relaunch the pending installer
        # and allow it to coordinate any shutdown it requires.
        return True
    except Exception as exc:
        logger.warning("Pending update installer launch failed: %s", exc)
        if parent is not None and parent.winfo_exists():
            parent.after(0, lambda: messagebox.showwarning(
                "Update Resume Failed",
                "MyStats found a pending update installer but could not launch it. "
                "Please run the installer manually from your temp folder or trigger update again.",
                parent=parent,
            ))
        return False


def download_and_install_update(download_url, version_label, silent_mode=True):
    if not download_url:
        messagebox.showerror("Update Failed", "No download URL was provided by the update service.")
        return

    logger.info("Starting update download from %s", download_url)
    toast_on_progress = is_minimized_to_tray()
    show_windows_toast("MyStats Update", f"Downloading MyStats {version_label} update...")

    progress_window, progress_var, percent_var, status_var = _create_update_progress_dialog(version_label)
    last_toast_bucket = {'value': -1}

    def update_progress(downloaded, total_bytes):
        if total_bytes <= 0:
            status_var.set(f"Downloaded {downloaded / (1024 * 1024):.2f} MB")
            return

        percent = min(100, int((downloaded / total_bytes) * 100))
        progress_var.set(percent)
        percent_var.set(f"{percent}%")
        status_var.set(f"{downloaded / (1024 * 1024):.2f} MB / {total_bytes / (1024 * 1024):.2f} MB")

        if toast_on_progress:
            bucket = percent // 25
            if bucket > last_toast_bucket['value'] and percent not in (0, 100):
                last_toast_bucket['value'] = bucket
                show_windows_toast("MyStats Update", f"Download progress: {percent}%")

    def worker():
        installer_path = None
        try:
            response = requests.get(download_url, stream=True, timeout=60)
            response.raise_for_status()

            # Check content-type to catch accidental HTML page downloads.
            content_type = response.headers.get('content-type', '')
            if 'text/html' in content_type:
                logger.error("Download URL returned HTML instead of a binary: %s", content_type)
                raise RuntimeError(
                    "The update server returned a web page instead of an installer file. "
                    "Please try again later or download manually."
                )

            total_bytes = int(response.headers.get('content-length') or 0)
            logger.info("Download started: %d bytes expected", total_bytes)
            downloaded = 0

            with tempfile.NamedTemporaryFile(delete=False, suffix='.exe', prefix='mystats_update_') as tmp_file:
                installer_path = tmp_file.name
                for chunk in response.iter_content(chunk_size=1024 * 128):
                    if not chunk:
                        continue
                    tmp_file.write(chunk)
                    downloaded += len(chunk)
                    root.after(0, lambda d=downloaded, t=total_bytes: update_progress(d, t))

            logger.info("Download complete: %s (%d bytes)", installer_path, downloaded)
            root.after(0, lambda: progress_var.set(100))
            root.after(0, lambda: percent_var.set("100%"))
            root.after(0, lambda: status_var.set("Download complete. Launching installer..."))
            root.after(0, lambda: show_windows_toast("MyStats Update", "Download complete. Launching installer..."))
            root.after(350, lambda: progress_window.destroy() if progress_window.winfo_exists() else None)
            root.after(500, lambda: _start_installer_and_exit(installer_path))
        except Exception as exc:
            logger.error("Update download/install failed: %s", exc, exc_info=True)
            if installer_path and os.path.exists(installer_path):
                try:
                    os.remove(installer_path)
                except OSError:
                    pass

            def fail():
                if progress_window.winfo_exists():
                    progress_window.destroy()
                messagebox.showerror("Update Failed", f"Could not download/install update: {exc}")

            root.after(0, fail)

    threading.Thread(target=worker, daemon=True).start()


def _get_update_later_clicks(versioncheck):
    tracked_version = config.get_setting('update_later_version') or ''
    if tracked_version != str(versioncheck):
        config.set_setting('update_later_version', str(versioncheck), persistent=True)
        config.set_setting('update_later_clicks', '0', persistent=True)
        return 0

    try:
        return max(0, int(config.get_setting('update_later_clicks') or 0))
    except (TypeError, ValueError):
        config.set_setting('update_later_clicks', '0', persistent=True)
        return 0


def _register_update_later_click(versioncheck):
    clicks = _get_update_later_clicks(versioncheck)
    clicks = min(3, clicks + 1)
    config.set_setting('update_later_clicks', str(clicks), persistent=True)
    return clicks


def show_update_message(versioncheck, download_url):
    # Create a custom popup window
    popup = tk.Toplevel(root)
    popup.title("Update Available")
    popup.geometry("560x360")

    # Center the popup window on the main window
    root_x = root.winfo_x()
    root_y = root.winfo_y()
    root_width = root.winfo_width()
    root_height = root.winfo_height()

    popup_width = 560
    popup_height = 360

    pos_x = root_x + (root_width // 2) - (popup_width // 2)
    pos_y = root_y + (root_height // 2) - (popup_height // 2)
    popup.geometry(f"{popup_width}x{popup_height}+{pos_x}+{pos_y}")

    try:
        image = Image.open("warning.png")
        image = image.resize((90, 90), Image.LANCZOS)
        photo = ImageTk.PhotoImage(image)
    except Exception as e:
        logger.error("Error loading image", exc_info=True)
        photo = None

    if photo:
        icon_label = tk.Label(popup, image=photo)
        icon_label.image = photo
        icon_label.pack(pady=10)

    label = tk.Label(
        popup,
        text=(
            f"An update is available (current: {version}, latest: {versioncheck}).\n"
            "You can update in place now without reinstalling manually."
        ),
        wraplength=390,
        justify='center'
    )
    label.pack(pady=8)

    hyperlink = tk.Label(popup, text="Release/download page", fg="blue", cursor="hand2")
    hyperlink.pack(pady=5)
    hyperlink.bind("<Button-1>", lambda e: open_url("https://mystats.camwow.tv/download"))

    helper_label = tk.Label(
        popup,
        text="If you have issues with the updater not installing, download the full version and install.",
        wraplength=460,
        justify='center'
    )
    helper_label.pack(pady=(4, 0))

    button_frame = ttk.Frame(popup)
    button_frame.pack(pady=16)

    update_now_requested = {'value': False}

    def start_update():
        update_now_requested['value'] = True
        config.set_setting('pending_update_version_label', str(versioncheck), persistent=True)
        popup.destroy()
        download_and_install_update(download_url, versioncheck)

    ttk.Button(
        button_frame,
        text="Update Now",
        command=start_update
    ).pack(side='left', padx=6)

    ttk.Button(
        button_frame,
        text="Remind Me Later",
        command=popup.destroy,
    ).pack(side='left', padx=6)

    popup.protocol("WM_DELETE_WINDOW", popup.destroy)
    popup.transient(root)
    popup.grab_set()
    root.wait_window(popup)
    return update_now_requested['value']


def close_application(popup):
    popup.destroy()  # Close the popup window
    root.destroy()  # Close the main Tkinter window
    sys.exit(0)  # Exit the application


def ensure_channel_name_configured(parent=None):
    """Prompt once per app session for channel name if it is missing."""
    global channel_prompted_this_session

    current_channel = (config.get_setting('CHANNEL') or '').strip().lstrip('@')
    if current_channel:
        return current_channel

    if channel_prompted_this_session:
        return ''

    channel_prompted_this_session = True

    messagebox.showinfo(
        "Channel Required",
        "MyStats could not find your channel in settings. Please enter your channel name now.",
        parent=parent
    )

    while True:
        entered_channel = simpledialog.askstring(
            "Set Channel",
            "Enter your Twitch channel name (without @):",
            parent=parent,
        )

        if entered_channel is None:
            messagebox.showwarning(
                "Channel Missing",
                "Channel is still blank. Some features require a valid channel.",
                parent=parent,
            )
            return ''

        normalized_channel = entered_channel.strip().lstrip('@')
        if normalized_channel:
            config.set_setting('CHANNEL', normalized_channel, persistent=True)
            return normalized_channel

        messagebox.showerror(
            "Invalid Channel",
            "Channel cannot be blank. Please enter a valid channel name.",
            parent=parent,
        )


# Replace messagebox.showwarning with show_update_message in ver_season_only()
def ver_season_only():
    load_racer_data()
    ensure_channel_name_configured(root)

    channel = config.get_setting('CHANNEL')
    api_url = f"https://mystats.camwow.tv/api/app/settings?channel={channel}"

    max_retries = 20
    retry_delay = 1

    def retry_request():
        """Function to retry the API call."""
        nonlocal max_retries, retry_delay
        for attempt in range(max_retries):
            try:
                response = requests.get(api_url)
                if response.status_code == 200:
                    response_data = json.loads(response.text.strip('[]'))

                    # Check if 'exists' is false
                    if not response_data.get('exists', True):
                        # Show popup to prompt login
                        if retry_popup():
                            retry_request()  # Retry the API call
                        else:
                            return  # User canceled, stop retrying

                    season = response_data.get("season", "")
                    versioncheck = response_data.get("version", "")
                    download_url = response_data.get("download_url") or "https://mystats.camwow.tv/download"

                    if not config.get_setting('season'):
                        config.set_setting('season', '56', persistent=True)
                        print(f"Current Season set to default: {config.get_setting('season')}")

                    if str(config.get_setting('season')) != str(season):
                        config.set_setting('new_season', 'True', persistent=False)
                    else:
                        config.set_setting('new_season', 'False', persistent=False)

                    config.set_setting('season', season, persistent=True)

                    if str(versioncheck) == str(version):
                        print("No Updates available.\n")
                        config.set_setting('update_later_clicks', '0', persistent=True)
                        config.set_setting('update_later_version', '', persistent=True)
                        return season
                    else:
                        print(f"An update is available. Current Version: {version} | New Version: {versioncheck}")
                        show_windows_toast("MyStats Update Available", f"New version {versioncheck} is ready to install.")
                        root.after(0, lambda v=versioncheck, u=download_url: show_update_message(v, u))
                        return season
                else:
                    print("API call failed with status code:", response.status_code)
                    print("Error message:", response.text)

                if response.status_code != 200:
                    print(response.text)
                    print("Using Default Season.  If this is not the current season, restart mystats")
                    config.set_setting('season', '56', persistent=True)

            except requests.exceptions.ConnectionError as e:
                print(f"Connection error: {e}. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2
            except json.JSONDecodeError as e:
                print("Failed to decode JSON from response:", e)
                break

        print("All retries have failed.")

        def _fatal_error():
            messagebox.showerror("Error", "Unable to verify season data after multiple attempts.")
            root.destroy()
            sys.exit(0)

        root.after(0, _fatal_error)

    def retry_popup():
        """Show retry popup on the main thread and return the result."""
        result = [None]
        event = threading.Event()

        def _show():
            result[0] = messagebox.askretrycancel(
                "Login Required",
                "You must log in to the website to use MyStats. Click Retry to try again.",
                parent=root
            )
            event.set()

        root.after(0, _show)
        event.wait()
        return result[0]

    retry_request()  # Initial API call


def reset_season_stats():
    config.set_setting('totalpointsseason', 0, persistent=False)
    config.set_setting('totalcountseason', 0, persistent=False)
    config.set_setting('race_hs_season', 0, persistent=False)
    config.set_setting('br_hs_season', 0, persistent=False)

    for completion_key in (
        'season_quest_complete_races',
        'season_quest_complete_points',
        'season_quest_complete_race_hs',
        'season_quest_complete_br_hs',
        'season_quest_complete_tilt_levels',
        'season_quest_complete_tilt_tops',
        'season_quest_complete_tilt_points',
    ):
        config.set_setting(completion_key, 'False', persistent=True)

    config.set_setting('new_season', 'False', persistent=False)


def reset():
    reset_timestamp, reset_timestampmdy, reset_timestamphms, reset_adjusted_time = time_manager.get_adjusted_time()
    if config.get_setting('startup') == 'yes':
        config.set_setting('startup', 'no', persistent=False)
        pass
    else:
        config.set_setting('startup', 'no', persistent=False)
        if config.get_setting('reset_audio') == 'True':
            audio_device = config.get_setting('audio_device')
            audio_file_path = config.get_setting('reset_audio_sound')
            play_audio_file(audio_file_path, device_name=audio_device)
        else:
            pass

    if config.get_setting('new_season') == 'True':
        reset_season_stats()

    config.set_setting('marble_day', reset_timestampmdy, persistent=True)
    config.set_setting('totalpointstoday', 0, persistent=False)
    config.set_setting('avgpointstoday', 0, persistent=False)
    config.set_setting('totalcounttoday', 0, persistent=False)
    config.set_setting('hscore_name', 'New Marble Day!', persistent=False)
    config.set_setting('hscore', 0, persistent=False)
    config.set_setting('br_hs_today', 0, persistent=False)
    config.set_setting('race_hs_today', 0, persistent=False)

    with open(appdata_path('HighScore.txt'), 'w', encoding='utf-8', errors='ignore') as hs:
        hs.write(str(config.get_setting('hscore_name')) + '\n')
        hs.write(str(config.get_setting('hscore')) + '\n')

    write_overlays()
    data_sync()
    ver_season_only()
    create_results_files()
    update_config_labels()


def display_welcome_message(text_widget, version, config, timestamp):
    text_widget.tag_configure("cyan", foreground="cyan")
    text_widget.tag_configure("yellow", foreground="yellow")
    text_widget.tag_configure("bright_yellow", foreground="yellow", font=("Helvetica", 10, "bold"))

    text_widget.insert(tk.END, "\n")
    text_widget.insert(tk.END, "Welcome to MyStats, a companion app for Marbles on Stream.\n", "cyan")
    text_widget.insert(tk.END, "\n")
    text_widget.insert(tk.END, f"Version: {version}\n")
    text_widget.insert(tk.END, f"Season: {config.get_setting('season')}\n")
    text_widget.insert(tk.END, "\n")
    text_widget.insert(tk.END, "This application was developed by ", "yellow")
    text_widget.insert(tk.END, "CamWOW!!!", "bright_yellow")
    text_widget.insert(tk.END, "\nFor any questions, bugs or suggestions, visit our discord.\n")
    text_widget.insert(tk.END, "\n")
    text_widget.insert(tk.END, "https://discord.gg/camwow\n", "yellow")
    text_widget.insert(tk.END, "\n")
    text_widget.insert(tk.END, f"The path to your MyStats files is: {config.get_setting('directory')}\n")
    text_widget.insert(tk.END, "\n")
    text_widget.insert(tk.END, f"The current Marble Day date/time is: {timestamp}\n")
    text_widget.insert(tk.END, "\n")
    text_widget.see(tk.END)


def startup(text_widget):
    print("\nCommunicating with server to check for updates...\n")
    ensure_channel_name_configured(root)
    config.set_setting('startup', 'yes', persistent=False)
    config.set_setting('data_sync', 'yes', persistent=False)
    create_results_files()

    def _post_version_check():
        """Run on main thread once the version-check thread completes."""
        timestamp, timestampMDY, timestampHMS, adjusted_time = time_manager.get_adjusted_time()
        if config.get_setting('new_season') == 'True':
            reset_season_stats()
        if config.get_setting('marble_day') != timestampMDY:
            reset()

    def _run_version_check():
        ver_season_only()
        root.after(0, _post_version_check)

    threading.Thread(target=_run_version_check, daemon=True).start()

    refresh_tilt_lifetime_xp_from_leaderboard()
    load_additional_settings()
    write_overlays()
    update_config_labels()
    set_login_button_text()

    br_hscore = int(config.get_setting('hscore'))
    br_hscore_format = format(br_hscore, ',')
    with open(appdata_path('HighScore.txt'), 'w', encoding='utf-8', errors='ignore') as hs:
        hs.write(str(config.get_setting('hscore_name')) + '\n')
        hs.write(str(br_hscore_format + '\n'))

    timestamp, timestampMDY, timestampHMS, adjusted_time = time_manager.get_adjusted_time()
    display_welcome_message(text_widget, version, config, timestamp)


# Try to recover a previously downloaded installer if a prior update launch was interrupted.
pending_update_resumed = recover_pending_update_launch(root)

# Schedule startup only when the normal UI flow should continue.
if not pending_update_resumed:
    root.after(100, lambda: startup(text_area))
    root.after(250, refresh_main_leaderboards)


# Initialize the Bot
import copy


class Bot(commands.Bot):
    TEAM_COMMAND_NAMES = {
        'createteam', 'invite', 'cocaptain', 'acceptteam', 'denyteam', 'kick', 'leave',
        'myteam', 'teambonus', 'logo', 'renameteam', 'inactive', 'jointeam', 'recruiting', 'dailyteams', 'weeklyteams',
        'tcommands'
    }

    def __init__(self):
        self.channel_name = config.get_setting('CHANNEL').lower()
        self._initial_token_validation_logged = False
        token = self.get_valid_token()  # Get the valid token at initialization
        prefix = '!'

        super().__init__(token=token, prefix=prefix, initial_channels=[self.channel_name])
        self.channel = None
        self.last_command_author = None
        self.config = config

        self.tasks = []  # List to keep track of tasks
        self.stop_event = asyncio.Event()  # Event to signal tasks to stop
        self.background_tasks_started = False
        self.last_competitive_raid_streamer = None
        self.last_competitive_raid_started_at = None
        self.last_competitive_raid_channel_announcement_cycle = None
        self.last_competitive_raid_final_announcement_cycle = None
        self.last_competitive_raid_field_list_signature = None
        self.team_command_last_seen = {}

    def get_valid_token(self):
        emit_validation_console = not self._initial_token_validation_logged

        # Load token from the token file if it exists, otherwise fallback to config token
        token_data = load_token_data()

        if token_data:
            file_access_token = token_data.get('access_token')
            if file_access_token and not is_token_expired(token_data) and verify_token(file_access_token, emit_console=emit_validation_console):
                self._initial_token_validation_logged = True
                return file_access_token

            print("Stored custom token is expired/nearing expiry or invalid, attempting token refresh...")
            new_token = refresh_access_token()  # Try to refresh the token
            if new_token and verify_token(new_token, emit_console=emit_validation_console):
                print("Token refreshed successfully.")
                self._initial_token_validation_logged = True
                return new_token  # Return the refreshed token

            clear_invalid_token_data("custom token expired/invalid and refresh failed")
            set_default_bot_login_button("Custom token could not be used")

        else:
            print("No token file found, falling back to ConfigManager token...")

        config_token = config.get_setting('TWITCH_TOKEN')
        if config_token:
            print("Using ConfigManager token.")
            set_default_bot_login_button("Using MyStats default account token")
            self._initial_token_validation_logged = True
            return config_token  # Use the token from config if no token file exists

        raise Exception("No valid token found in ConfigManager. Please authenticate.")

    async def event_ready(self):
        self.channel = self.get_channel(self.channel_name)
        print(f"Sending message to Twitch as: {self.nick}")
        print(f"Connected to channel: {self.channel_name}\n")

        # Avoid duplicate background tasks if Twitch reconnects this bot instance.
        self.tasks = [task for task in self.tasks if not task.done()]
        if self.background_tasks_started:
            return
        self.background_tasks_started = True

        # Start main tasks and keep track of them
        self.tasks.append(self.loop.create_task(checkpoints(self)))
        self.tasks.append(self.loop.create_task(race(self)))
        self.tasks.append(self.loop.create_task(royale(self)))
        self.tasks.append(self.loop.create_task(tilted(self)))
        self.tasks.append(self.loop.create_task(competitive_raid_monitor(self)))

        # Start background tasks in separate threads
        if config.get_setting('sync').lower() != 'yes':
            self.tasks.append(self.loop.create_task(asyncio.to_thread(one_time_sync)))
        if config.get_setting('data_sync').lower() == 'yes':
            self.tasks.append(self.loop.create_task(asyncio.to_thread(
                process_season,
                config.get_setting('directory'),
                config.get_setting('season')
            )))
            config.set_setting('data_sync', 'no', persistent=False)

    async def event_disconnect(self):
        print("Disconnected from Twitch chat. Waiting for reconnection...")

    async def event_error(self, error, data=None):
        """
        Handle intermittent websocket teardown errors from TwitchIO gracefully.

        Twitch can close the websocket transport while TwitchIO is still sending a
        heartbeat ping, which raises a connection reset error in aiohttp.
        This is transient during reconnects and should not crash or spam users.
        """
        error_message = str(error)
        if isinstance(error, ConnectionResetError) or "Cannot write to closing transport" in error_message:
            print("Twitch websocket closed during ping; waiting for automatic reconnect...")
            return

        raise error

    async def event_message(self, message):
        if message.author is None:
            return

        await self._process_team_bits_bonus(message)

        content = str(message.content or '')
        lowered = content.lower()

        if lowered.startswith('!') and not is_chat_response_enabled("chat_all_commands"):
            return

        new_message = copy.copy(message)
        if content.startswith('!'):
            command_token, separator, remainder = content.partition(' ')
            new_message.content = f"{command_token.lower()}{separator}{remainder}" if separator else command_token.lower()
        else:
            new_message.content = content
        await self.handle_commands(new_message)

    async def shutdown(self):
        print("Shutting down bot and tasks...")
        self.stop_event.set()  # Signal tasks to stop

        # Cancel tasks
        for task in self.tasks:
            task.cancel()

        # Wait for tasks to finish
        await asyncio.gather(*self.tasks, return_exceptions=True)

        # Close the bot
        await self.close()
        print("Bot shutdown complete.")

    async def send_command_response(self, ctx, message):
        await send_chat_message(ctx.channel, message, category="mystats")

    def _teams_feature_enabled(self):
        return parse_boolean_token(config.get_setting("teams_enabled"), default=True)

    def _teams_phase(self):
        return "local"

    async def _with_channel_team_state(self):
        with TEAM_DATA_LOCK:
            data = _load_team_data()
            channel_state = _get_channel_team_state(data, self.channel_name)
            channel_state['settings']['points_mode'] = (config.get_setting("teams_points_mode") or "active").strip().lower()
            try:
                channel_state['settings']['max_team_size'] = max(2, int(config.get_setting("teams_max_size") or 25))
            except ValueError:
                channel_state['settings']['max_team_size'] = 25
            return data, channel_state

    async def _save_channel_team_state(self, data):
        with TEAM_DATA_LOCK:
            _save_team_data(data)

    def _is_team_admin(self, team, username):
        user_key = _normalize_username(username)
        return team.get('captain') == user_key or user_key in team.get('co_captains', [])

    def _is_team_command_rate_limited(self, author_name, command_name, cooldown_seconds=3):
        now_ts = time.time()
        key = (_normalize_username(author_name), str(command_name or '').strip().lower())
        last_ts = self.team_command_last_seen.get(key)
        if last_ts and (now_ts - last_ts) < max(1, cooldown_seconds):
            return True
        self.team_command_last_seen[key] = now_ts
        return False

    def _expire_stale_invites(self, channel_state):
        now = datetime.now(timezone.utc)
        for invite in channel_state.get('invites', []):
            if invite.get('status') != 'pending':
                continue
            expires_at = _parse_iso_datetime(invite.get('expires_at'))
            if expires_at and expires_at < now:
                invite['status'] = 'expired'
                invite['responded_at'] = now.isoformat()

    def _resolve_user_active_team(self, channel_state, username):
        self._expire_stale_invites(channel_state)
        return _find_team_for_user(channel_state, username)

    def _is_verified_subscriber(self, author):
        """Best-effort Helix subscriber verification with graceful fallback to chat badges."""
        if not author:
            return False

        user_id = str(getattr(author, 'id', '') or '')
        if not user_id:
            return _extract_subscriber_status(author)

        broadcaster_id = str(getattr(self.channel, 'id', '') or '')
        token = self.get_valid_token()
        if broadcaster_id and token:
            headers = {
                'Authorization': f'Bearer {token}',
                'Client-Id': CLIENT_ID,
            }
            params = {
                'broadcaster_id': broadcaster_id,
                'user_id': user_id,
            }
            try:
                response = requests.get(
                    'https://api.twitch.tv/helix/subscriptions/user',
                    headers=headers,
                    params=params,
                    timeout=4,
                )
                if response.status_code == 200:
                    payload = response.json() if response.text else {}
                    return bool(payload.get('data'))
            except Exception:
                pass

        return _extract_subscriber_status(author)

    def _resolve_member_sub_tier(self, author):
        if not author:
            return 0

        fallback_tier = _extract_sub_tier(author)
        user_id = str(getattr(author, 'id', '') or '')
        broadcaster_id = str(getattr(self.channel, 'id', '') or '')
        token = self.get_valid_token()
        if not (user_id and broadcaster_id and token):
            return fallback_tier

        headers = {
            'Authorization': f'Bearer {token}',
            'Client-Id': CLIENT_ID,
        }
        params = {
            'broadcaster_id': broadcaster_id,
            'user_id': user_id,
        }
        try:
            response = requests.get(
                'https://api.twitch.tv/helix/subscriptions/user',
                headers=headers,
                params=params,
                timeout=4,
            )
            if response.status_code != 200:
                return fallback_tier
            payload = response.json() if response.text else {}
            rows = payload.get('data') if isinstance(payload, dict) else []
            if not rows:
                return 0
            plan = str((rows[0] or {}).get('tier') or '').strip()
            if plan == '3000':
                return 3
            if plan == '2000':
                return 2
            if plan == '1000':
                return 1
        except Exception:
            return fallback_tier
        return fallback_tier

    def _register_member_metadata(self, team, username, author=None):
        user_key = _normalize_username(username)
        if not user_key:
            return
        member_meta = team.setdefault('member_meta', {})
        existing = member_meta.get(user_key, {}) if isinstance(member_meta.get(user_key), dict) else {}
        tier = self._resolve_member_sub_tier(author) if author else 0
        member_meta[user_key] = {
            'sub_tier': tier,
            'is_subscriber': bool(tier > 0),
            'joined_at': existing.get('joined_at') or datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat(),
        }

    def _current_team_bonus(self, team):
        now = datetime.now(timezone.utc)
        active = team.get('active_bonus')
        if not isinstance(active, dict):
            return None
        if 'bonus_percent' not in active:
            active['bonus_percent'] = _resolve_team_bonus_percent(active, 0)
        end_at = _parse_allraces_timestamp(active.get('end_at'))
        if not end_at or end_at < now:
            team['active_bonus'] = None
            team['active_bonus_label'] = None
            return None
        return active

    def _choose_bonus_percent(self):
        try:
            w15 = max(0, int(config.get_setting('teams_bonus_weight_15') or 33))
        except ValueError:
            w15 = 33
        try:
            w25 = max(0, int(config.get_setting('teams_bonus_weight_25') or 33))
        except ValueError:
            w25 = 33
        try:
            w35 = max(0, int(config.get_setting('teams_bonus_weight_35') or 33))
        except ValueError:
            w35 = 33
        try:
            w67 = max(0, int(config.get_setting('teams_bonus_weight_67') or 1))
        except ValueError:
            w67 = 1
        population = [15, 25, 35, 67]
        weights = [w15, w25, w35, w67]
        if sum(weights) <= 0:
            weights = [33, 33, 33, 1]
        return random.choices(population, weights=weights, k=1)[0]

    async def _process_team_bits_bonus(self, message):
        if not self._teams_feature_enabled() or self._teams_phase() != 'local':
            return
        bits = _extract_message_bits(message)
        if bits <= 0:
            return

        donor = _normalize_username(getattr(message.author, 'name', ''))
        data, channel_state = await self._with_channel_team_state()
        team_name, _ = _find_team_for_user(channel_state, donor)
        if not team_name:
            return

        team = channel_state.get('teams', {}).get(team_name)
        if not team:
            return

        self._register_member_metadata(team, donor, message.author)
        try:
            threshold = max(1, int(config.get_setting('teams_bonus_bits_threshold') or 1000))
        except ValueError:
            threshold = 1000
        try:
            duration_minutes = max(1, int(config.get_setting('teams_bonus_duration_minutes') or 20))
        except ValueError:
            duration_minutes = 20

        bits_bank = int(team.get('bits_bank', 0)) + bits
        team['bits_bank'] = bits_bank

        progress_pct = int(round((team['bits_bank'] / threshold) * 100)) if threshold > 0 else 0
        pool_message = (
            f"💠 {team_name} bits pool: {team['bits_bank']:,}/{threshold:,} "
            f"({min(999, max(0, progress_pct))}%)"
        )
        enqueue_overlay_event('team_bits_pool', pool_message)

        activated_messages = []
        now = datetime.now(timezone.utc)
        active_bonus = self._current_team_bonus(team)
        while team.get('bits_bank', 0) >= threshold:
            if active_bonus and str(active_bonus.get('source') or 'bits').lower() != 'bits':
                break
            team['bits_bank'] -= threshold
            bonus_percent = self._choose_bonus_percent()
            if active_bonus:
                end_at = _parse_allraces_timestamp(active_bonus.get('end_at')) or now
                new_end = end_at + timedelta(minutes=duration_minutes)
                active_bonus['end_at'] = new_end.isoformat()
                active_bonus['bonus_percent'] = max(_resolve_team_bonus_percent(active_bonus, 0), bonus_percent)
                active_bonus['source'] = 'bits'
            else:
                end_at = now + timedelta(minutes=duration_minutes)
                active_bonus = {
                    'bonus_percent': bonus_percent,
                    'source': 'bits',
                    'start_at': now.isoformat(),
                    'end_at': end_at.isoformat(),
                }
                team['active_bonus'] = active_bonus
                team.setdefault('bonus_windows', []).append({
                    'bonus_percent': bonus_percent,
                    'source': 'bits',
                    'start_at': now.isoformat(),
                    'end_at': end_at.isoformat(),
                    'trigger_bits': threshold,
                })

            resolved_bonus_percent = _resolve_team_bonus_percent(active_bonus, bonus_percent)
            team['active_bonus_label'] = f"⚡+{resolved_bonus_percent}%"
            activated_messages.append(
                f"⚡ Team Bonus Activated: {team_name} now has +{resolved_bonus_percent}% points for {duration_minutes}m!"
            )

        await self._save_channel_team_state(data)

        for msg in activated_messages[:1]:
            await send_chat_message(message.channel, msg, category="mystats")

    @commands.command(name='createteam')
    async def createteam(self, ctx, *, team_name: str = None):
        if not self._teams_feature_enabled():
            return
        if self._is_team_command_rate_limited(ctx.author.name, 'createteam'):
            return
        creator = _normalize_username(ctx.author.name)
        if not self._is_verified_subscriber(ctx.author) and creator != self.channel_name:
            await self.send_command_response(ctx, "!createteam is subscriber-only right now.")
            return

        data, channel_state = await self._with_channel_team_state()
        existing_team, _ = self._resolve_user_active_team(channel_state, creator)
        if existing_team:
            await self.send_command_response(ctx, f"{format_user_tag(creator)} you are already in team '{existing_team}'.")
            return

        normalized_name = _normalize_team_name(team_name) if team_name else ''
        if not normalized_name:
            normalized_name = _generate_team_name(creator)

        taken = any(_normalize_team_name(name).lower() == normalized_name.lower() for name in channel_state.get('teams', {}))
        if taken:
            await self.send_command_response(ctx, f"Team name '{normalized_name}' already exists.")
            return

        channel_state['teams'][normalized_name] = {
            'captain': creator,
            'co_captains': [],
            'members': [],
            'member_meta': {},
            'logo': None,
            'is_recruiting': False,
            'inactive_days': None,
            'bits_bank': 0,
            'active_bonus': None,
            'active_bonus_label': None,
            'bonus_windows': [],
            'effort_bank': 0,
            'effort_daily': {},
            'created_at': datetime.now(timezone.utc).isoformat(),
        }
        self._register_member_metadata(channel_state['teams'][normalized_name], creator, ctx.author)
        await self._save_channel_team_state(data)
        await self.send_command_response(ctx, f"✅ Team '{normalized_name}' created. Captain: {format_user_tag(creator)}")

    @commands.command(name='invite')
    async def invite(self, ctx, target: str = None):
        if not self._teams_feature_enabled() or not target:
            return
        if self._is_team_command_rate_limited(ctx.author.name, 'invite'):
            return
        actor = _normalize_username(ctx.author.name)
        target_user = _normalize_username(target)
        if not target_user or target_user == actor:
            return

        data, channel_state = await self._with_channel_team_state()
        actor_team_name, actor_role = self._resolve_user_active_team(channel_state, actor)
        if actor_role not in {'captain', 'co_captain'}:
            await self.send_command_response(ctx, "Only captains/co-captains can invite.")
            return
        target_team_name, _ = self._resolve_user_active_team(channel_state, target_user)
        if target_team_name:
            await self.send_command_response(ctx, f"{format_user_tag(target_user)} is already in a team.")
            return

        invites = channel_state.get('invites', [])
        for invite in invites:
            if invite.get('team') == actor_team_name and invite.get('invitee') == target_user and invite.get('status') == 'pending':
                await self.send_command_response(ctx, f"Invite already pending for {format_user_tag(target_user)}.")
                return

        invites.append({
            'team': actor_team_name,
            'inviter': actor,
            'invitee': target_user,
            'status': 'pending',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'expires_at': (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        })
        channel_state['invites'] = invites
        await self._save_channel_team_state(data)
        await self.send_command_response(ctx, f"📨 {format_user_tag(target_user)} invited to '{actor_team_name}'. Use !acceptteam {actor_team_name}")

    @commands.command(name='acceptteam')
    async def acceptteam(self, ctx, *, team_name: str = None):
        if not self._teams_feature_enabled() or not team_name:
            return
        if self._is_team_command_rate_limited(ctx.author.name, 'acceptteam'):
            return
        username = _normalize_username(ctx.author.name)
        lookup = _normalize_team_name(team_name).lower()
        data, channel_state = await self._with_channel_team_state()
        current_team, _ = self._resolve_user_active_team(channel_state, username)
        if current_team:
            await self.send_command_response(ctx, f"You are already in '{current_team}'.")
            return

        selected_invite = None
        for invite in channel_state.get('invites', []):
            if invite.get('invitee') == username and invite.get('status') == 'pending' and _normalize_team_name(invite.get('team')).lower() == lookup:
                selected_invite = invite
                break
        if not selected_invite:
            await self.send_command_response(ctx, "No pending invite for that team.")
            return

        actual_team_name = selected_invite.get('team')
        team = channel_state.get('teams', {}).get(actual_team_name)
        if not team:
            await self.send_command_response(ctx, "That team no longer exists.")
            return

        max_size = int(channel_state.get('settings', {}).get('max_team_size', 25))
        size = 1 + len(team.get('co_captains', [])) + len(team.get('members', []))
        if size >= max_size:
            await self.send_command_response(ctx, f"'{actual_team_name}' is full ({max_size}).")
            return

        team.setdefault('members', []).append(username)
        self._register_member_metadata(team, username, ctx.author)
        selected_invite['status'] = 'accepted'
        selected_invite['responded_at'] = datetime.now(timezone.utc).isoformat()
        await self._save_channel_team_state(data)
        await self.send_command_response(ctx, f"✅ {format_user_tag(username)} joined '{actual_team_name}'.")

    @commands.command(name='denyteam')
    async def denyteam(self, ctx, *, team_name: str = None):
        if not self._teams_feature_enabled() or not team_name:
            return
        if self._is_team_command_rate_limited(ctx.author.name, 'denyteam'):
            return
        username = _normalize_username(ctx.author.name)
        lookup = _normalize_team_name(team_name).lower()
        data, channel_state = await self._with_channel_team_state()
        for invite in channel_state.get('invites', []):
            if invite.get('invitee') == username and invite.get('status') == 'pending' and _normalize_team_name(invite.get('team')).lower() == lookup:
                invite['status'] = 'denied'
                invite['responded_at'] = datetime.now(timezone.utc).isoformat()
                await self._save_channel_team_state(data)
                await self.send_command_response(ctx, f"Invite to '{invite.get('team')}' denied.")
                return
        await self.send_command_response(ctx, "No pending invite found.")

    @commands.command(name='cocaptain')
    async def cocaptain(self, ctx, target: str = None):
        if not self._teams_feature_enabled() or not target:
            return
        if self._is_team_command_rate_limited(ctx.author.name, 'cocaptain'):
            return
        actor = _normalize_username(ctx.author.name)
        target_user = _normalize_username(target)
        data, channel_state = await self._with_channel_team_state()
        team_name, role = self._resolve_user_active_team(channel_state, actor)
        if role != 'captain':
            await self.send_command_response(ctx, "Only captains can assign co-captains.")
            return
        team = channel_state.get('teams', {}).get(team_name)
        if target_user not in team.get('members', []):
            await self.send_command_response(ctx, "Target must be a current team member.")
            return
        team['members'] = [m for m in team.get('members', []) if m != target_user]
        if target_user not in team.get('co_captains', []):
            team.setdefault('co_captains', []).append(target_user)
        await self._save_channel_team_state(data)
        await self.send_command_response(ctx, f"{format_user_tag(target_user)} is now co-captain of '{team_name}'.")

    @commands.command(name='kick')
    async def kick(self, ctx, target: str = None):
        if not self._teams_feature_enabled() or not target:
            return
        if self._is_team_command_rate_limited(ctx.author.name, 'kick'):
            return
        actor = _normalize_username(ctx.author.name)
        target_user = _normalize_username(target)
        data, channel_state = await self._with_channel_team_state()
        team_name, role = self._resolve_user_active_team(channel_state, actor)
        if role not in {'captain', 'co_captain'}:
            await self.send_command_response(ctx, "Only captains/co-captains can kick members.")
            return
        team = channel_state.get('teams', {}).get(team_name)
        if not team:
            return
        if team.get('captain') == target_user:
            await self.send_command_response(ctx, "Captain cannot be kicked.")
            return
        if target_user in team.get('co_captains', []):
            team['co_captains'] = [u for u in team.get('co_captains', []) if u != target_user]
        elif target_user in team.get('members', []):
            team['members'] = [u for u in team.get('members', []) if u != target_user]
        else:
            await self.send_command_response(ctx, "Target is not in your team.")
            return
        if isinstance(team.get('member_meta'), dict):
            team['member_meta'].pop(target_user, None)
        await self._save_channel_team_state(data)
        await self.send_command_response(ctx, f"{format_user_tag(target_user)} was removed from '{team_name}'.")

    @commands.command(name='leave')
    async def leave(self, ctx):
        if not self._teams_feature_enabled():
            return
        if self._is_team_command_rate_limited(ctx.author.name, 'leave'):
            return
        actor = _normalize_username(ctx.author.name)
        data, channel_state = await self._with_channel_team_state()
        team_name, role = self._resolve_user_active_team(channel_state, actor)
        if not team_name:
            await self.send_command_response(ctx, "You are not in a team.")
            return
        team = channel_state.get('teams', {}).get(team_name)
        if role == 'captain':
            if team.get('co_captains'):
                team['captain'] = team['co_captains'].pop(0)
            elif team.get('members'):
                team['captain'] = team['members'].pop(0)
            else:
                channel_state['teams'].pop(team_name, None)
                channel_state['invites'] = [inv for inv in channel_state.get('invites', []) if inv.get('team') != team_name]
                await self._save_channel_team_state(data)
                _remove_team_points_cache_entry(self.channel_name, self.current_season(), team_name)
                await self.send_command_response(ctx, f"Team '{team_name}' archived (no members left).")
                return
        elif role == 'co_captain':
            team['co_captains'] = [u for u in team.get('co_captains', []) if u != actor]
        else:
            team['members'] = [u for u in team.get('members', []) if u != actor]
        if isinstance(team.get('member_meta'), dict):
            team['member_meta'].pop(actor, None)
        await self._save_channel_team_state(data)
        await self.send_command_response(ctx, f"{format_user_tag(actor)} left '{team_name}'.")

    @commands.command(name='myteam')
    async def myteam(self, ctx, username: str = None):
        if not self._teams_feature_enabled():
            return
        lookup_name = _normalize_username(username or ctx.author.name)
        data, channel_state = await self._with_channel_team_state()
        team_name, role = _find_team_for_user(channel_state, lookup_name)
        if not team_name:
            await self.send_command_response(ctx, f"{format_user_tag(lookup_name)} is not currently on a team.")
            return

        team = channel_state['teams'][team_name]
        if lookup_name == _normalize_username(ctx.author.name):
            self._register_member_metadata(team, lookup_name, ctx.author)
        active_bonus = self._current_team_bonus(team)

        season_points = _compute_team_points(channel_state, team_name, window='season')
        daily_points = _compute_team_points(channel_state, team_name, window='daily')
        bonus_races = _compute_team_bonus_races(channel_state, team_name, days=1)
        effort_bank = int(team.get('effort_bank', 0) or 0)
        try:
            effort_threshold = max(1, int(config.get_setting('teams_tep_threshold') or 40))
        except ValueError:
            effort_threshold = 40
        sub_stats = _compute_team_subscriber_stats(team)
        sub_points = sub_stats.get('tier_points', 0)
        sub_count = sub_stats.get('sub_count', 0)
        sub_total = sub_stats.get('total_members', 0)
        sub_coverage = sub_stats.get('coverage_pct', 0.0)
        est_sub_boost = sub_stats.get('estimated_team_bonus_pct', 0.0)

        leaderboard = []
        for candidate_name in channel_state.get('teams', {}):
            leaderboard.append((candidate_name, _compute_team_points(channel_state, candidate_name, window='season')))
        leaderboard.sort(key=lambda item: item[1], reverse=True)
        rank = next((idx for idx, (name, _) in enumerate(leaderboard, 1) if name == team_name), 0)

        captain_name = team.get('captain') or 'unknown'
        captain_meta = (team.get('member_meta') or {}).get(captain_name, {})
        captain_tier = int(captain_meta.get('sub_tier', 0) or 0)
        captain_tier_text = f"Tier {captain_tier}" if captain_tier > 0 else "Non-Sub"
        max_size = int(channel_state.get('settings', {}).get('max_team_size', 25))
        members = [captain_name] + list(team.get('co_captains', [])) + list(team.get('members', []))
        members = [m for m in members if m]

        kick_days = team.get('inactive_days')
        kick_text = f"{kick_days}d" if kick_days else "Off"
        recruiting_text = ":green_circle: OPEN" if team.get('is_recruiting') else ":red_circle: CLOSED"
        bonus_label = f"⚡+{_resolve_team_bonus_percent(active_bonus, 0)}%" if active_bonus else "⚡+0%"

        icon = team.get('logo') or ':white_check_mark:'
        stats_line = (
            f"{team_name} | Rank: #{rank} | Pts: {season_points:,} (+{daily_points:,}) | "
            f"SubPts: {sub_points} ({sub_count}/{sub_total}, {sub_coverage:.0f}% subs, ~+{est_sub_boost:.1f}% est) | "
            f"{bonus_label} Bonus Races: {bonus_races} | "
            f"TEP: {effort_bank:,}/{effort_threshold:,} | "
            f"Kick: {kick_text} | Recruiting: {recruiting_text} | "
            f"{format_user_tag(lookup_name)} role: {role} | Capt: {captain_name} ({captain_tier_text})"
        )
        members_prefix = f"{icon} {stats_line} | Members [{len(members)}/{max_size}]: "
        member_chunks = chunked_join_messages(
            members_prefix,
            f"{team_name} cont: ",
            members,
            separator=', ',
            max_length=480,
        )
        await self._save_channel_team_state(data)
        for chunk in member_chunks:
            await self.send_command_response(ctx, chunk)

    @commands.command(name='teambonus')
    async def teambonus(self, ctx, username: str = None):
        if not self._teams_feature_enabled():
            return
        if self._is_team_command_rate_limited(ctx.author.name, 'teambonus'):
            return

        lookup_name = _normalize_username(username or ctx.author.name)
        data, channel_state = await self._with_channel_team_state()
        team_name, role = _find_team_for_user(channel_state, lookup_name)
        if not team_name:
            await self.send_command_response(ctx, f"{format_user_tag(lookup_name)} is not currently on a team.")
            return

        team = channel_state.get('teams', {}).get(team_name)
        if not isinstance(team, dict):
            await self.send_command_response(ctx, "Team data unavailable.")
            return

        if lookup_name == _normalize_username(ctx.author.name):
            self._register_member_metadata(team, lookup_name, ctx.author)

        now = datetime.now(timezone.utc)
        active_bonus = self._current_team_bonus(team)
        active_source = str((active_bonus or {}).get('source') or ('bits' if active_bonus else '')).lower()

        bits_bank = int(team.get('bits_bank', 0) or 0)
        effort_bank = int(team.get('effort_bank', 0) or 0)
        try:
            bits_threshold = max(1, int(config.get_setting('teams_bonus_bits_threshold') or 1000))
        except ValueError:
            bits_threshold = 1000
        try:
            effort_threshold = max(1, int(config.get_setting('teams_tep_threshold') or 40))
        except ValueError:
            effort_threshold = 40
        try:
            tep_cooldown_minutes = max(0, int(config.get_setting('teams_tep_bits_cooldown_minutes') or 60))
        except ValueError:
            tep_cooldown_minutes = 60

        bits_pct = min(999, max(0, int(round((bits_bank / bits_threshold) * 100)))) if bits_threshold > 0 else 0
        effort_pct = min(999, max(0, int(round((effort_bank / effort_threshold) * 100)))) if effort_threshold > 0 else 0

        recent_bits_end = _team_most_recent_bits_bonus_end(team)
        cooldown_remaining = 0
        if recent_bits_end and tep_cooldown_minutes > 0:
            cooldown_until = recent_bits_end + timedelta(minutes=tep_cooldown_minutes)
            cooldown_remaining = max(0, int((cooldown_until - now).total_seconds() // 60))

        if active_bonus:
            end_at = _parse_allraces_timestamp(active_bonus.get('end_at'))
            mins_left = max(0, int((end_at - now).total_seconds() // 60)) if end_at else 0
            active_line = f"Active: +{_resolve_team_bonus_percent(active_bonus, 0)}% ({active_source or 'bits'}) {mins_left}m left"
        else:
            active_line = "Active: none"

        if active_bonus:
            tep_state = f"TEP: blocked by active {active_source or 'bonus'} window"
        elif cooldown_remaining > 0:
            tep_state = f"TEP: cooldown {cooldown_remaining}m (after recent bits bonus)"
        elif effort_bank >= effort_threshold:
            tep_state = "TEP: ready to trigger on next processed team race"
        else:
            tep_state = "TEP: charging"

        bits_state = "Bits: ready" if bits_bank >= bits_threshold else "Bits: charging"
        msg = (
            f"{team_name} bonus progress | "
            f"Bits {bits_bank:,}/{bits_threshold:,} ({bits_pct}%) | "
            f"TEP {effort_bank:,}/{effort_threshold:,} ({effort_pct}%) | "
            f"{active_line} | {bits_state} | {tep_state}"
        )
        await self._save_channel_team_state(data)
        await self.send_command_response(ctx, msg)

    @commands.command(name='renameteam')
    async def renameteam(self, ctx, *, requested_name: str = None):
        if not self._teams_feature_enabled():
            return
        if self._is_team_command_rate_limited(ctx.author.name, 'renameteam'):
            return

        actor = _normalize_username(ctx.author.name)
        normalized_name = _normalize_team_name(requested_name) if requested_name else ''
        if not normalized_name:
            await self.send_command_response(ctx, "Usage: !renameteam New Team Name")
            return

        data, channel_state = await self._with_channel_team_state()
        current_team_name, role = self._resolve_user_active_team(channel_state, actor)
        if role != 'captain':
            await self.send_command_response(ctx, "Only captains can rename their team.")
            return

        if _normalize_team_name(current_team_name).lower() == normalized_name.lower():
            await self.send_command_response(ctx, f"Your team is already named '{current_team_name}'.")
            return

        taken = any(
            _normalize_team_name(candidate).lower() == normalized_name.lower()
            for candidate in channel_state.get('teams', {})
            if candidate != current_team_name
        )
        if taken:
            await self.send_command_response(ctx, f"Team name '{normalized_name}' already exists.")
            return

        team = channel_state.get('teams', {}).pop(current_team_name, None)
        if not isinstance(team, dict):
            await self.send_command_response(ctx, "Team not found. Please try again.")
            return

        channel_state['teams'][normalized_name] = team
        for invite in channel_state.get('invites', []):
            if invite.get('team') == current_team_name:
                invite['team'] = normalized_name

        await self._save_channel_team_state(data)
        _rename_team_points_cache_entry(self.channel_name, self.current_season(), current_team_name, normalized_name)

        await self.send_command_response(ctx, f"✅ Team renamed: '{current_team_name}' -> '{normalized_name}'.")


    @commands.command(name='logo')
    async def logo(self, ctx, emote: str = None):
        if not self._teams_feature_enabled() or not emote:
            return
        if self._is_team_command_rate_limited(ctx.author.name, 'logo'):
            return
        actor = _normalize_username(ctx.author.name)
        data, channel_state = await self._with_channel_team_state()
        team_name, role = self._resolve_user_active_team(channel_state, actor)
        if role not in {'captain', 'co_captain'}:
            await self.send_command_response(ctx, "Only captains/co-captains can set logo.")
            return
        channel_state['teams'][team_name]['logo'] = emote.strip()
        await self._save_channel_team_state(data)
        await self.send_command_response(ctx, f"Team '{team_name}' logo set to {emote.strip()}")

    @commands.command(name='inactive')
    async def inactive(self, ctx, days: str = None):
        if not self._teams_feature_enabled() or not days:
            return
        if self._is_team_command_rate_limited(ctx.author.name, 'inactive'):
            return
        actor = _normalize_username(ctx.author.name)
        data, channel_state = await self._with_channel_team_state()
        team_name, role = self._resolve_user_active_team(channel_state, actor)
        if role not in {'captain', 'co_captain'}:
            await self.send_command_response(ctx, "Only captains/co-captains can set inactive policy.")
            return
        try:
            value = max(1, int(days))
        except ValueError:
            await self.send_command_response(ctx, "Usage: !inactive X")
            return
        channel_state['teams'][team_name]['inactive_days'] = value

        # Immediate lightweight sweep based on metadata timestamps.
        team = channel_state['teams'][team_name]
        member_meta = team.get('member_meta', {}) if isinstance(team.get('member_meta'), dict) else {}
        now = datetime.now(timezone.utc)
        threshold = timedelta(days=value)
        removable = []
        for member in list(team.get('members', [])):
            meta = member_meta.get(member, {}) if isinstance(member_meta.get(member), dict) else {}
            updated_at = _parse_iso_datetime(meta.get('updated_at'))
            if updated_at and (now - updated_at) > threshold:
                removable.append(member)
        if removable:
            team['members'] = [m for m in team.get('members', []) if m not in removable]
            for user_key in removable:
                if isinstance(member_meta, dict):
                    member_meta.pop(user_key, None)

        await self._save_channel_team_state(data)
        await self.send_command_response(ctx, f"'{team_name}' inactive policy set to {value} days.")

    @commands.command(name='jointeam')
    async def jointeam(self, ctx):
        if not self._teams_feature_enabled():
            return
        if self._is_team_command_rate_limited(ctx.author.name, 'jointeam'):
            return
        username = _normalize_username(ctx.author.name)
        data, channel_state = await self._with_channel_team_state()
        existing_team, _ = self._resolve_user_active_team(channel_state, username)
        if existing_team:
            await self.send_command_response(ctx, f"You are already in '{existing_team}'.")
            return
        max_size = int(channel_state.get('settings', {}).get('max_team_size', 25))
        candidates = []
        for team_name, team in channel_state.get('teams', {}).items():
            if not team.get('is_recruiting'):
                continue
            size = 1 + len(team.get('co_captains', [])) + len(team.get('members', []))
            if size >= max_size:
                continue
            candidates.append((size, team.get('created_at', ''), team_name))
        if not candidates:
            await self.send_command_response(ctx, "No recruiting teams are currently available.")
            return
        candidates.sort(key=lambda item: (item[0], item[1], item[2].lower()))
        selected_name = candidates[0][2]
        channel_state['teams'][selected_name].setdefault('members', []).append(username)
        self._register_member_metadata(channel_state['teams'][selected_name], username, ctx.author)
        await self._save_channel_team_state(data)
        await self.send_command_response(ctx, f"✅ {format_user_tag(username)} joined recruiting team '{selected_name}'.")

    @commands.command(name='recruiting')
    async def recruiting(self, ctx, state: str = None):
        if not self._teams_feature_enabled() or not state:
            return
        if self._is_team_command_rate_limited(ctx.author.name, 'recruiting'):
            return
        actor = _normalize_username(ctx.author.name)
        data, channel_state = await self._with_channel_team_state()
        team_name, role = self._resolve_user_active_team(channel_state, actor)
        if role not in {'captain', 'co_captain'}:
            await self.send_command_response(ctx, "Only captains/co-captains can toggle recruiting.")
            return
        token = str(state or '').strip().lower()
        if token in {'on', 'open', 'true', 'yes', '1'}:
            channel_state['teams'][team_name]['is_recruiting'] = True
        elif token in {'off', 'closed', 'close', 'false', 'no', '0'}:
            channel_state['teams'][team_name]['is_recruiting'] = False
        else:
            await self.send_command_response(ctx, "Usage: !recruiting on|off")
            return
        await self._save_channel_team_state(data)
        status = 'OPEN' if channel_state['teams'][team_name]['is_recruiting'] else 'CLOSED'
        await self.send_command_response(ctx, f"{team_name} recruiting is now {status}.")

    @commands.command(name='dailyteams')
    async def dailyteams(self, ctx):
        if not self._teams_feature_enabled():
            return
        _, channel_state = await self._with_channel_team_state()
        rows = []
        for team_name in channel_state.get('teams', {}):
            rows.append((team_name, _compute_team_points(channel_state, team_name, window='daily')))
        if not rows:
            await self.send_command_response(ctx, "No teams found.")
            return
        rows.sort(key=lambda item: item[1], reverse=True)
        top = rows[:5]
        await self.send_command_response(ctx, "Daily MyTeams: " + " | ".join([f"#{idx} {name} ({pts:,})" for idx, (name, pts) in enumerate(top, 1)]))

    @commands.command(name='weeklyteams')
    async def weeklyteams(self, ctx):
        if not self._teams_feature_enabled():
            return
        _, channel_state = await self._with_channel_team_state()
        rows = []
        for team_name in channel_state.get('teams', {}):
            rows.append((team_name, _compute_team_points(channel_state, team_name, window='weekly')))
        if not rows:
            await self.send_command_response(ctx, "No teams found.")
            return
        rows.sort(key=lambda item: item[1], reverse=True)
        top = rows[:5]
        await self.send_command_response(ctx, "Weekly MyTeams: " + " | ".join([f"#{idx} {name} ({pts:,})" for idx, (name, pts) in enumerate(top, 1)]))

    @commands.command(name='daily')
    async def daily(self, ctx):
        top = _get_top_players_points(days=1, limit=5)
        if not top:
            await self.send_command_response(ctx, "No daily data available yet.")
            return
        await self.send_command_response(ctx, "Daily: " + " | ".join([f"#{idx} {format_user_tag(name)} ({pts:,})" for idx, (name, pts) in enumerate(top, 1)]))

    @commands.command(name='weekly')
    async def weekly(self, ctx):
        top = _get_top_players_points(days=7, limit=5)
        if not top:
            await self.send_command_response(ctx, "No weekly data available yet.")
            return
        await self.send_command_response(ctx, "Weekly: " + " | ".join([f"#{idx} {format_user_tag(name)} ({pts:,})" for idx, (name, pts) in enumerate(top, 1)]))


    @commands.command(name='info')
    async def info(self, ctx):
        if ctx.author.name.lower() == 'camwow' or ctx.author.name.lower() == config.get_setting(
                'CHANNEL').lower() or ctx.author.name.lower() == 'vibblez':
            await self.send_command_response(ctx, "ℹ️ Version " + str(version) + ", Season: " + str(config.get_setting('season')) +
                                   ' | Total Races: ' + str(format(int(config.get_setting('totalcountseason')), ',')) +
                                   ' | Total Points: ' + str(
                format(int(config.get_setting('totalpointsseason')), ',')) +
                                   ' | Race High Score: ' + str(
                format(int(config.get_setting('race_hs_season')), ',')) +
                                   ' | BR High Score: ' + str(format(int(config.get_setting('br_hs_season')), ',')) +
                                   ' | Marble Day: ' + str(config.get_setting('marble_day')) +
                                   ' | Points Today: ' + format(int(config.get_setting('totalpointstoday')), ',') +
                                   ' | Races Today: ' + format(int(config.get_setting('totalcounttoday')), ',') +
                                   ' | https://mystats.camwow.tv')

    async def send_pixelbypixel_top10(self, ctx, statistic_name, sort_by_stat=False):
        try:
            leaderboard_data = fetch_pixelbypixel_leaderboard(statistic_name)
        except requests.RequestException as exc:
            print(f"Failed to fetch data: {exc}")
            await self.send_command_response(ctx, "Failed to pull leaderboard, please try again")
            return

        if sort_by_stat:
            def get_stat_sort_value(record):
                try:
                    return int(float(record.get("StatValue", 0)))
                except (AttributeError, TypeError, ValueError):
                    return 0

            leaderboard_data = sorted(
                leaderboard_data,
                key=get_stat_sort_value,
                reverse=True
            )

        top_10_records = leaderboard_data[:10]
        if not top_10_records:
            await self.send_command_response(ctx, "No leaderboard data available right now.")
            return

        entries = []
        for rank, record in enumerate(top_10_records, start=1):
            display_name = record.get("DisplayName") or record.get("UserName") or "Unknown"
            try:
                stat_value = format(int(float(record.get("StatValue", 0))), ",")
            except (TypeError, ValueError):
                stat_value = "0"
            entries.append(f"{format_ranked_label(rank)} {display_name} - {stat_value}")

        await self.send_command_response(
            ctx,
            "Leaderboard | " + " | ".join(entries) + " | View the full leaderboard, https://pixelbypixel.studio/hub"
        )

    @commands.command(name='mostop10')
    async def mostop10(self, ctx):
        await self.send_pixelbypixel_top10(ctx, statistic_name="Season_XP", sort_by_stat=False)

    @commands.command(name='top10xp')
    async def top10xp(self, ctx):
        refresh_tilt_lifetime_xp_from_leaderboard()
        await self.send_pixelbypixel_top10(ctx, statistic_name="TiltedExpertise", sort_by_stat=True)


    # @commands.command(name='myenergy')
    async def myenergy(self, ctx):
        api_url = f"https://pixelbypixel.studio/api/user/energy/{ctx.message.author.display_name}"
        response = requests.get(api_url)

        if response.status_code == 200:
            energy_data = response.json()

                # Extract energy, username, daily races, and tiers data
            username = energy_data['username']
            energy = energy_data['energy']
            daily_races = energy_data.get('dailyraces', [])
            tiers = energy_data.get('tiers', [])

            # Start building the message
            message = f"Current Energy for {username}: {energy}/7 | "

            if daily_races:
                # Sorting and categorizing the daily races
                message += self.organize_daily_races(daily_races, tiers)
            else:
                message += "No daily races found."

                await self.send_command_response(ctx, message.strip())
        else:
                print(f"Failed to fetch data: {response.status_code}")
                await self.send_command_response(ctx, "Failed to pull energy data, please try again.")

    def organize_daily_races(self, daily_races, tiers):
        # Define time thresholds as aware datetime objects in UTC
        thirty_minutes_ago = datetime.now(timezone.utc) - timedelta(minutes=30)
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)

        # Get tier race values for comparison
        tier_race_values = {tier['Races'] for tier in tiers}

        # Separate active and inactive streams
        active_streams = []
        inactive_streams = []

        for race in daily_races:
            streamer = race['streamer_username']
            energy = race['races']
            last_updated = parser.parse(race['last_updated'])

            # Check the criteria for inactive streams
            if (last_updated < thirty_minutes_ago and energy in tier_race_values) or \
                (last_updated < one_hour_ago and energy not in tier_race_values):
                inactive_streams.append(f"{streamer}: {energy}")
            else:
               active_streams.append(f"{streamer}: {energy}")

        # Create message strings
        message = ""

        # Add active streams to message
        if active_streams:
            message += "Active Streams: " + ", ".join(active_streams) + ". "

        # Add inactive streams to message
        if inactive_streams:
            message += "Inactive Streams: " + ", ".join(inactive_streams) + "."

        # If no streams are active or inactive, add a default message
        if not message:
            message = "No streams found."

        return message

    @commands.command(name='meta')
    async def meta(self, ctx):
        await self.send_command_response(ctx, 
            "Interested in learning more about the Streamer Meta?  "
            "📖: https://docs.google.com/document/d/1k93YU73QbGZrmfHqm1cto8PzzF2eADPtpGLILfGawVM/edit")

    @commands.command(name='mosapp')
    async def mosapp(self, ctx):
        await self.send_command_response(ctx, 
            "Download the MOS App on Mobile.  Google Play: "
            "https://play.google.com/store/apps/details?id=com.pixelbypixel.mosmobile&hl=en-US.   Apple App Store: "
            "https://apps.apple.com/us/app/marbles-on-stream-mobile/id1443250176")

    @commands.command(name='mosshop')
    async def mosshop(self, ctx):
        await self.send_command_response(ctx, 
            "Purchase Skins or Coins for yourself, or gift them to a friend!  https://pixelbypixel.studio/shop")

    @commands.command(name='wiki')
    async def wiki(self, ctx):
        await self.send_command_response(ctx, "Marbles on Stream Wiki - https://wiki.pixelbypixel.studio/")

    @commands.command(name='highfive')
    async def highfive(self, ctx):
        if ctx.author.name.lower() != 'camwow':
            return

        parts = ctx.message.content.strip().split()
        if len(parts) != 2:
            return

        command_name, mentioned_name = parts
        if command_name.lower() != '!highfive':
            return

        bot_name = (self.nick or '').strip().lower().lstrip('@')
        target_name = mentioned_name.strip().lower().lstrip('@')
        if not bot_name or target_name != bot_name:
            return

        await self.send_command_response(ctx, '!highfive @camwow')

    @commands.command(name='commands')
    async def list_commands(self, ctx):
        team_hidden = self.TEAM_COMMAND_NAMES - {'tcommands'}
        excluded_commands = {'commands', 'mplreset', 'highfive'} | team_hidden
        if not self._teams_feature_enabled():
            excluded_commands.add('teamhelp')
        commands_list = [f'!{cmd.name}' for cmd in self.commands.values() if cmd.name not in excluded_commands]
        commands_description = ', '.join(commands_list)
        await ctx.send(f'MyStats commands: {commands_description}')

    @commands.command(name='teamhelp')
    async def team_help(self, ctx):
        if not self._teams_feature_enabled():
            return
        await ctx.send("MyTeams is live! Type `!tcommands` for team commands. Use `!createteam` to start a team, `!invite` to recruit, `!renameteam` to rename your team (captain only), and `!dailyteams` / `!weeklyteams` / `!myteam` / `!teambonus` to track standings and bonus progress.")

    @commands.command(name='tcommands')
    async def team_commands(self, ctx):
        if not self._teams_feature_enabled():
            return
        team_commands_list = [f'!{cmd.name}' for cmd in self.commands.values() if cmd.name in self.TEAM_COMMAND_NAMES]
        commands_description = ', '.join(sorted(team_commands_list))
        await ctx.send(f'MyTeams commands: {commands_description}')

    # Method to expose the command list outside the class
    def get_commands(self):
        team_hidden = self.TEAM_COMMAND_NAMES - {'tcommands'}
        excluded_commands = {'commands', 'mplreset', 'highfive'} | team_hidden
        if not self._teams_feature_enabled():
            excluded_commands.add('teamhelp')
        return [f'!{cmd.name}' for cmd in self.commands.values() if cmd.name not in excluded_commands]

    @commands.command(name='rivals')
    async def rivals_command(self, ctx, *args):
        if not is_chat_response_enabled("rivals_enabled"):
            return

        if _is_rivals_command_on_cooldown(getattr(ctx.author, 'name', '')):
            _track_rivals_metric('cooldown')
            await self.send_command_response(ctx, "Rivals is cooling down. Please wait a few seconds before retrying.")
            return

        tokens = [str(arg).strip() for arg in args if str(arg).strip()]
        username = tokens[0] if len(tokens) >= 1 else None
        compare_username = tokens[1] if len(tokens) >= 2 else None
        detail_token = tokens[2].lower() if len(tokens) >= 3 else ''
        verbose_requested = detail_token in {'full', 'verbose', '--full', '--verbose'} or (compare_username and compare_username.lower() in {'full', 'verbose'})

        if compare_username and compare_username.lower() in {'full', 'verbose'}:
            compare_username = None

        if username and compare_username:
            user_stats = get_user_season_stats()
            user_a_key, err_a = _resolve_user_or_error(user_stats, username)
            user_b_key, err_b = _resolve_user_or_error(user_stats, compare_username)

            if err_a or err_b:
                _track_rivals_metric('pair_lookup_failed')
                await self.send_command_response(ctx, err_a or err_b)
                return

            stats_a = user_stats[user_a_key]
            stats_b = user_stats[user_b_key]
            settings = get_rival_settings()
            point_gap = abs(stats_a.get('points', 0) - stats_b.get('points', 0))

            qualifies_a = stats_a.get('races', 0) >= settings['min_races'] and stats_a.get('points', 0) > 0
            qualifies_b = stats_b.get('races', 0) >= settings['min_races'] and stats_b.get('points', 0) > 0
            are_rivals = qualifies_a and qualifies_b and point_gap <= settings['max_point_gap']

            rivalry_status = "✅ Rivalry active" if are_rivals else "❌ Not a qualifying rivalry"

            pair_row = _build_rivalry_row(user_a_key, stats_a, user_b_key, stats_b)
            trend_text = "Trend: closing" if pair_row['trend_direction'] == 'closing' else ("Trend: widening" if pair_row['trend_direction'] == 'widening' else "Trend: steady")

            _track_rivals_metric('pair_check')
            await self.send_command_response(ctx, 
                f"Rivals Check • {format_user_tag(stats_a['display_name'])} vs {format_user_tag(stats_b['display_name'])} | "
                f"Gap: ±{point_gap:,} pts | "
                f"{format_user_tag(stats_a['display_name'])}: {stats_a.get('points', 0):,} pts, {stats_a.get('races', 0):,} races | "
                f"{format_user_tag(stats_b['display_name'])}: {stats_b.get('points', 0):,} pts, {stats_b.get('races', 0):,} races | "
                f"{trend_text} | Score: {pair_row['rivalry_score']:,} | "
                f"{rivalry_status}"
            )
            return

        if username:
            limit = RIVALS_MAX_USER_RESULTS if verbose_requested else 5
            rival_data = get_user_rivals(username, limit=limit)
            if rival_data is None:
                _track_rivals_metric('user_lookup_failed')
                await self.send_command_response(ctx, f"{format_user_tag(username)}: no season rival data found. Try exact @handle.")
                return

            if rival_data.get('ambiguous'):
                _track_rivals_metric('user_lookup_ambiguous')
                options = ', '.join(format_user_tag(name) for name in rival_data.get('matches', [])[:3])
                await self.send_command_response(ctx, f"{format_user_tag(username)} matches multiple users ({options}). Use exact @handle.")
                return

            if rival_data['races'] < rival_data['min_races_required']:
                _track_rivals_metric('under_min_races')
                await self.send_command_response(ctx, 
                    f"{format_user_tag(rival_data['display_name'])}: {rival_data['races']:,} races so far. "
                    f"Need {rival_data['min_races_required']:,}+ races for rivals tracking. "
                    f"Tip: lower Minimum Season Races in Settings → Rivals."
                )
                return

            if not rival_data['rivals']:
                _track_rivals_metric('no_rivals_found')
                await self.send_command_response(ctx, 
                    f"{format_user_tag(rival_data['display_name'])}: no close rivals found within configured point gap. "
                    f"Tip: increase Maximum Point Gap in Settings → Rivals."
                )
                return

            entries = [
                f"#{idx} {format_user_tag(row['display_name'])} (±{row['point_gap']:,}, {row['points']:,} pts, {row.get('trend_direction', 'steady')})"
                for idx, row in enumerate(rival_data['rivals'], start=1)
            ]
            _track_rivals_metric('user_rivals')
            await self.send_command_response(ctx, 
                f"Rivals for {format_user_tag(rival_data['display_name'])}, {rival_data['points']:,} pts: " + " | ".join(entries)
            )
            return

        rivalries = get_global_rivalries(limit=5)
        if not rivalries:
            _track_rivals_metric('global_empty')
            await self.send_command_response(ctx, "No rivalries found yet with current rival settings.")
            return

        entries = [
            f"#{idx} {format_user_tag(row['display_a'])} vs {format_user_tag(row['display_b'])} (±{row['point_gap']:,}, {row.get('trend_direction', 'steady')})"
            for idx, row in enumerate(rivalries, start=1)
        ]
        _track_rivals_metric('global_board')
        await self.send_command_response(ctx, "Rivalries Leaderboard: " + " | ".join(entries))

    @commands.command(name='h2h')
    async def head_to_head_command(self, ctx, user_a: str = None, user_b: str = None):
        if not user_a or not user_b:
            await self.send_command_response(ctx, "Usage: !h2h <user1> <user2>")
            return

        user_stats = get_user_season_stats()
        user_a_key, err_a = _resolve_user_or_error(user_stats, user_a)
        user_b_key, err_b = _resolve_user_or_error(user_stats, user_b)

        if err_a or err_b:
            await self.send_command_response(ctx, err_a or err_b)
            return

        stats_a = user_stats[user_a_key]
        stats_b = user_stats[user_b_key]

        leader_name = stats_a['display_name'] if stats_a['points'] >= stats_b['points'] else stats_b['display_name']
        point_gap = abs(stats_a['points'] - stats_b['points'])
        pair_row = _build_rivalry_row(user_a_key, stats_a, user_b_key, stats_b)

        await self.send_command_response(ctx, 
            f"⚔️ H2H {format_user_tag(stats_a['display_name'])} vs {format_user_tag(stats_b['display_name'])} | "
            f"Points: {stats_a['points']:,}, {stats_b['points']:,} | "
            f"Races: {stats_a['races']:,}, {stats_b['races']:,} | "
            f"Race HS: {stats_a['race_hs']:,}, {stats_b['race_hs']:,} | "
            f"BR HS: {stats_a['br_hs']:,}, {stats_b['br_hs']:,} | "
            f"30d Gap: {pair_row['recent_point_gap_30d']:,} | "
            f"Score: {pair_row['rivalry_score']:,} | "
            f"Leader: {format_user_tag(leader_name)} by {point_gap:,}"
        )

    @commands.command(name='mycycle')
    async def mycycle_command(self, ctx, *args):
        if not is_chat_response_enabled('mycycle_enabled'):
            return

        target_name = None
        session_query = None
        tokens = [str(arg).strip() for arg in args if str(arg).strip()]
        idx = 0
        while idx < len(tokens):
            token = tokens[idx]
            lowered = token.lower()
            if lowered in ('--session', '-s'):
                if idx + 1 < len(tokens):
                    session_query = tokens[idx + 1]
                    idx += 2
                    continue
                idx += 1
                continue
            if lowered.startswith('--session='):
                session_query = token.split('=', 1)[1].strip()
                idx += 1
                continue
            if lowered.startswith('session:'):
                session_query = token.split(':', 1)[1].strip()
                idx += 1
                continue
            if target_name is None:
                target_name = token
            idx += 1

        target_name = target_name or ctx.author.name
        requested_session_id = None
        session_query_failed = False
        if session_query:
            sessions, _ = get_mycycle_sessions(include_inactive=True)
            query = session_query.strip().lower()
            for item in sessions:
                sid = str(item.get('id', '')).strip()
                sname = str(item.get('name', '')).strip().lower()
                if sid.lower() == query or sname == query:
                    requested_session_id = sid
                    break
            session_query_failed = not requested_session_id

        if session_query and session_query_failed:
            await self.send_command_response(ctx, f"Unknown MyCycle session '{session_query}'.")
            return

        session, stats, target_user = get_mycycle_progress(target_name, session_id=requested_session_id)
        settings = get_mycycle_settings()

        if not target_user or target_user not in stats:
            await self.send_command_response(ctx, 
                f"{format_user_tag(target_name)}: no MyCycle race data yet in session '{session.get('name', 'Unknown')}'."
            )
            return

        record = stats[target_user]
        hits = set(record.get('current_hits', []))
        required_positions = list(range(settings['min_place'], settings['max_place'] + 1))
        missing = [str(pos) for pos in required_positions if pos not in hits]
        progress_text = f"{len(hits)}/{len(required_positions)}"
        display_name = record.get('display_name') or target_user

        message = (
            f"🔁 {format_user_tag(display_name)} | Session: {session.get('name', 'Unknown')} | "
            f"Cycles: {record.get('cycles_completed', 0)} | Progress: {progress_text} | "
            f"Races this cycle: {record.get('current_cycle_races', 0)} | "
            f"Last cycle races: {record.get('last_cycle_races', 0)}"
        )
        if missing:
            message += f" | Missing: {', '.join(missing)}"

        await self.send_command_response(ctx, message)


    @commands.command(name='nextcycle')
    async def nextcycle_command(self, ctx):
        if not is_chat_response_enabled('mycycle_enabled'):
            return

        session, candidates = get_next_mycycle_candidates(limit=10)
        session_name = (session or {}).get('name', 'Unknown')

        if not candidates:
            await self.send_command_response(ctx, f"🔁 NextCycle [{session_name}] | No upcoming cycles found yet.")
            return

        entries = []
        for row in candidates:
            missing_positions = ','.join(str(pos) for pos in row.get('missing_positions', []))
            entries.append(
                f"{format_user_tag(row['display_name'])} | C{row['next_cycle_number']} | Missing: {missing_positions}"
            )

        await self.send_command_response(
            ctx,
            f"🔁 NextCycle [{session_name}] Top {len(entries)}: " + " || ".join(entries)
        )

    @commands.command(name='cyclestats')
    async def cyclestats_command(self, ctx, session_name: str = None):
        if not is_chat_response_enabled('mycycle_enabled'):
            return

        stats = get_mycycle_cycle_stats(session_name)
        if not stats:
            await self.send_command_response(ctx, "No MyCycle sessions found. Try !cyclestats all")
            return

        fastest = stats.get('fastest')
        slowest = stats.get('slowest')
        if not fastest and not slowest:
            await self.send_command_response(ctx, 
                f"🔁 CycleStats [{stats['label']}] | No completed cycles yet."
            )
            return

        fastest_text = (
            f"{fastest['name']} ({fastest['races']} races)"
            if fastest else
            "n/a"
        )
        slowest_text = (
            f"{slowest['name']} ({slowest['races']} races)"
            if slowest else
            "n/a"
        )

        rotating_metric_key = get_next_cyclestats_metric_key()
        rotating_metric_text = format_rotating_cyclestats_metric(rotating_metric_key, stats)

        await self.send_command_response(ctx, 
            f"🔁 CycleStats [{stats['label']}] | Fastest: {fastest_text} | "
            f"Slowest: {slowest_text} | {rotating_metric_text} | "
            f"Total cycles: {stats['cycles_total']}"
        )

    @commands.command(name='myquests')
    async def myquests_command(self, ctx, username: str = None):
        if not is_chat_response_enabled("season_quests_enabled"):
            return

        lookup_name = username if username else ctx.author.name
        progress = get_user_quest_progress(lookup_name)

        if progress is None:
            await self.send_command_response(ctx, f"{format_user_tag(lookup_name)}: No quest progress found yet.")
            return

        headline = (
            f"{format_user_tag(progress['display_name'])} Quest Progress: "
            f"{progress['completed']}/{progress['active_quests'] if progress['active_quests'] > 0 else 0} quests complete"
        )
        detail_segments = list(progress['progress_lines'])
        if not detail_segments:
            await self.send_command_response(ctx, f"🔎 {headline}")
            return

        max_message_length = 420
        prefix = "🔎 "
        current_message = f"{prefix}{headline}"
        sent_any = False
        for segment in detail_segments:
            candidate = f"{current_message} | {segment}"
            if len(candidate) <= max_message_length:
                current_message = candidate
                continue
            await self.send_command_response(ctx, current_message)
            sent_any = True
            current_message = f"{prefix}{segment}"

        if current_message:
            await self.send_command_response(ctx, current_message if sent_any else current_message)


    @commands.command(name='top10ppr')
    async def top10ppr_command(self, ctx):
        # Dictionary to store stats for each racer
        racers = {}

        # Loop through all CSV files matching the pattern
        for allraces in glob.glob(os.path.join(config.get_setting('directory'), "allraces_*.csv")):
            try:
                # Read the file in binary mode to detect encoding
                with open(allraces, 'rb') as f:
                    raw_data = f.read()
                result = chardet.detect(raw_data)
                encoding = result['encoding'] if result['encoding'] else 'utf-8'

                # Open the file with the detected encoding
                with open(allraces, 'r', encoding=encoding, errors='ignore') as f:
                    reader = iter_csv_rows(f)
                    for row in reader:
                        # Assume:
                        # row[1] contains the racer's name
                        # row[3] contains the points scored in that race
                        racer = row[1].strip()
                        points = int(row[3])
                        
                        # Initialize racer's record if not present
                        if racer not in racers:
                            racers[racer] = {'seasonraces': 0, 'seasonpts': 0}
                        
                        # Update racer's total races and points
                        racers[racer]['seasonraces'] += 1
                        racers[racer]['seasonpts'] += points

            except FileNotFoundError:
                print("File not found.")
                await self.send_command_response(ctx, "No season races recorded yet")
                return
            except Exception as e:
                logger.error("Unexpected error", exc_info=True)
                return

        # Filter for racers with more than 100 races
        qualified_racers = {racer: stats for racer, stats in racers.items() if stats['seasonraces'] > 100}

        # Calculate Points Per Race (PPR) for each qualified racer
        for racer, stats in qualified_racers.items():
            stats['ppr'] = stats['seasonpts'] / stats['seasonraces']

        # Sort the racers by PPR in descending order and select the top 10
        top_racers = sorted(qualified_racers.items(), key=lambda x: x[1]['ppr'], reverse=True)[:10]

        # Build a list of entry strings without a trailing separator
        entries = []
        for place, (racer, stats) in enumerate(top_racers, start=1):
            # Round down the PPR to one decimal place
            ppr_rounded_down = math.floor(stats['ppr'] * 10) / 10
            entry = f"{format_ranked_label(place)} {racer}: {ppr_rounded_down:.1f}"
            entries.append(entry)

        header = "Top 10 Racers by PPR (100+ races): "
        chunks = []
        current_chunk = header

        # Build message chunks ensuring that if adding an entry (with a separator) exceeds 480 characters,
        # the entry is moved to a new message.
        for entry in entries:
            # If current_chunk is still just the header, don't add a separator.
            separator = "" if current_chunk == header else " | "
            if len(current_chunk) + len(separator) + len(entry) > 480:
                chunks.append(current_chunk)
                current_chunk = entry  # start new chunk with this entry (no header)
            else:
                current_chunk += separator + entry

        if current_chunk:
            chunks.append(current_chunk)

        # Send each chunk as a separate message.
        for chunk in chunks:
            await self.send_command_response(ctx, chunk)


    @commands.command(name='mystats')
    async def mystats_command(self, ctx, username: str = None):
        timestamp, timestampMDY, timestampHMS, adjusted_time = time_manager.get_adjusted_time()

        # Use the provided username if available; otherwise default to the command author.
        if username is None:
            winnersname = ctx.author.name
            winnersdisplayname = getattr(ctx.author, 'display_name', None) or ctx.author.name
        else:
            # Split on spaces and remove any leading "@" character.
            winnersname = username.split()[0].lstrip('@')
            winnersdisplayname = winnersname

        today = adjusted_time.strftime("%Y-%m-%d")

        counts = {
            'br_count': 0,
            'race_count': 0,
            'brwins': 0,
            'racewins': 0,
            'racestoday': 0,
            'winstoday': 0,
            'pointstoday': 0,
            'seasonwins': 0,
            'seasonraces': 0,
            'seasonpts': 0,
            'br_points': 0,
            'race_points': 0,
            'number_of_runs_tilt': 0,
            'world_record_count': 0
        }

        for allraces in glob.glob(os.path.join(config.get_setting('directory'), "allraces_*.csv")):
            try:
                with open(allraces, 'rb') as f:
                    raw_data = f.read()

                result = chardet.detect(raw_data)
                encoding = result['encoding'] if result['encoding'] else 'utf-8'

                with open(allraces, 'r', encoding=encoding, errors='ignore') as f:
                    reader = iter_csv_rows(f)
                    for row in reader:
                        race_date = datetime.strptime(row[5], "%Y-%m-%d %H:%M:%S").date()

                        if row[1].lower() == winnersname.lower() and str(race_date) == str(today):
                            counts['racestoday'] += 1
                            counts['pointstoday'] += int(row[3])
                            if int(row[0]) == 1:
                                counts['winstoday'] += 1

                        if row[1].lower() == winnersname.lower():
                            if len(row) > 2 and row[2] and row[2].lower() != row[1].lower():
                                winnersdisplayname = row[2]
                            counts['seasonraces'] += 1
                            counts['seasonpts'] += int(row[3])
                            if int(row[0]) == 1:
                                counts['seasonwins'] += 1
                            # Count world records if the column exists and equals "1"
                            if len(row) > 11 and row[11] == '1':
                                counts['world_record_count'] += 1

                            if len(row) >= 5:
                                if row[4] == 'BR':
                                    counts['br_count'] += 1
                                    counts['br_points'] += int(row[3])
                                    if int(row[0]) == 1:
                                        counts['brwins'] += 1
                                elif row[4] == 'Race':
                                    counts['race_count'] += 1
                                    counts['race_points'] += int(row[3])
                                    if int(row[0]) == 1:
                                        counts['racewins'] += 1

            except FileNotFoundError:
                print("File not found.")
                await self.send_command_response(ctx, "No season races recorded yet")
                return
            except Exception as e:
                logger.error("Unexpected error", exc_info=True)
                return

        # Compute average points per race for different event types.
        br_avg_points = counts['br_points'] / counts['br_count'] if counts['br_count'] > 0 else 0
        race_avg_points = counts['race_points'] / counts['race_count'] if counts['race_count'] > 0 else 0
        season_avg_points = counts['seasonpts'] / counts['seasonraces'] if counts['seasonraces'] > 0 else 0
        today_avg_points = counts['pointstoday'] / counts['racestoday'] if counts['racestoday'] > 0 else 0

        # Compute the rounded down values for presentation.
        br_avg_points_rounded_down = math.floor(br_avg_points * 10) / 10
        race_avg_points_rounded_down = math.floor(race_avg_points * 10) / 10
        season_avg_points_rounded_down = math.floor(season_avg_points * 10) / 10
        today_avg_points_rounded_down = math.floor(today_avg_points * 10) / 10

        # Create string for singular or plural "win" based on the count.
        wins_str = "win" if counts['winstoday'] == 1 else "wins"

        # Format the numbers with commas and rounded down values.
        brwins_formatted = '{:,}'.format(counts['brwins'])
        br_points_formatted = '{:,}'.format(counts['br_points'])
        br_count_formatted = '{:,}'.format(counts['br_count'])
        br_avg_points_formatted = '{:.1f}'.format(br_avg_points_rounded_down)

        racewins_formatted = '{:,}'.format(counts['racewins'])
        race_points_formatted = '{:,}'.format(counts['race_points'])
        race_count_formatted = '{:,}'.format(counts['race_count'])
        race_avg_points_formatted = '{:.1f}'.format(race_avg_points_rounded_down)

        seasonwins_formatted = '{:,}'.format(counts['seasonwins'])
        seasonpts_formatted = '{:,}'.format(counts['seasonpts'])
        seasonraces_formatted = '{:,}'.format(counts['seasonraces'])
        season_avg_points_formatted = '{:.1f}'.format(season_avg_points_rounded_down)

        pointstoday_formatted = '{:,}'.format(counts['pointstoday'])
        racestoday_formatted = '{:,}'.format(counts['racestoday'])
        today_avg_points_formatted = '{:.1f}'.format(today_avg_points_rounded_down)

        # Create the formatted output message using the original syntax style,
        # while preserving modern tag + emote prefix behavior.
        output_msg = (
            f"BRs - {brwins_formatted} wins, {br_points_formatted} points, {br_count_formatted} royales, PPR: {br_avg_points_formatted}. | "
            f"Races - {racewins_formatted} wins, {race_points_formatted} points, {race_count_formatted} races, PPR: {race_avg_points_formatted}. | "
            f"Season - {seasonwins_formatted} wins, {seasonpts_formatted} points, {seasonraces_formatted} races, PPR: {season_avg_points_formatted}. | "
            f"World Records - {counts['world_record_count']}"
        )

        await send_chat_message(
            ctx.channel,
            f"📊 {format_user_tag(winnersdisplayname)}: Today: {counts['winstoday']} {wins_str}, {pointstoday_formatted} points, {racestoday_formatted} races. "
            f"PPR: {today_avg_points_formatted} | Season total: {output_msg}",
            category="mystats"
        )


    @commands.command(name='mytilts')
    async def mytilts_command(self, ctx, username: str = None):
        if username is None:
            target_name = ctx.author.name
            display_name = getattr(ctx.author, 'display_name', None) or ctx.author.name
        else:
            target_name = username.split()[0].lstrip('@')
            display_name = target_name

        _, _, _, adjusted_time = time_manager.get_adjusted_time()
        today_date = adjusted_time.strftime("%Y-%m-%d")

        points_today = 0
        points_season = 0
        points_run = 0
        deaths_today = 0
        deaths_season = 0
        deaths_run = 0
        last_completed_level = 0
        last_completed_seen = False

        current_run_id = (config.get_setting('tilt_current_run_id') or '').strip()
        latest_run_by_user = None
        run_points_tracker = {}

        for tilts_file in sorted(glob.glob(os.path.join(config.get_setting('directory'), "tilts_*.csv"))):
            try:
                file_date = os.path.basename(tilts_file)[6:16]
                with open(tilts_file, 'rb') as f:
                    raw_data = f.read()
                result = chardet.detect(raw_data)
                encoding = result['encoding'] if result['encoding'] else 'utf-8'

                with open(tilts_file, 'r', encoding=encoding, errors='ignore') as f:
                    reader = iter_csv_rows(f)
                    for row in reader:
                        parsed = parse_tilt_result_row(row)
                        if parsed is None:
                            continue

                        racer, points, run_id = parsed
                        if racer.lower() != target_name.lower():
                            continue

                        latest_run_by_user = run_id
                        points_season += points
                        if points <= 0:
                            deaths_season += 1

                        if file_date == today_date:
                            points_today += points
                            if points <= 0:
                                deaths_today += 1

                        if len(row) > 1:
                            try:
                                level_number = int(''.join(ch for ch in str(row[1]).strip() if ch.isdigit()) or '0')
                            except (TypeError, ValueError):
                                level_number = 0

                            previous_points = run_points_tracker.get(run_id)
                            level_completed = False

                            # Tilt result rows can include players who reached a level but
                            # were eliminated on it. Treat a level as completed only when the
                            # player's cumulative score increased from their prior row in the
                            # same run (or from zero when first seen in that run).
                            if previous_points is None:
                                level_completed = points > 0
                            else:
                                level_completed = points > previous_points

                            run_points_tracker[run_id] = points

                            if level_completed:
                                last_completed_level = level_number
                                last_completed_seen = True

                        run_match = bool(current_run_id) and run_id == current_run_id
                        if run_match:
                            points_run += points
                            if points <= 0:
                                deaths_run += 1

            except FileNotFoundError:
                continue
            except Exception as e:
                logger.error("Unexpected error", exc_info=True)

        if not current_run_id and latest_run_by_user:
            current_run_id = latest_run_by_user
            points_run = 0
            deaths_run = 0
            for tilts_file in sorted(glob.glob(os.path.join(config.get_setting('directory'), "tilts_*.csv"))):
                try:
                    with open(tilts_file, 'rb') as f:
                        raw_data = f.read()
                    result = chardet.detect(raw_data)
                    encoding = result['encoding'] if result['encoding'] else 'utf-8'

                    with open(tilts_file, 'r', encoding=encoding, errors='ignore') as f:
                        reader = iter_csv_rows(f)
                        for row in reader:
                            parsed = parse_tilt_result_row(row)
                            if parsed is None:
                                continue
                            racer, points, run_id = parsed
                            if racer.lower() != target_name.lower() or run_id != current_run_id:
                                continue
                            points_run += points
                            if points <= 0:
                                deaths_run += 1
                except Exception:
                    continue

        if points_season == 0 and deaths_season == 0:
            await send_chat_message(
                ctx.channel,
                f"⚖️ {format_user_tag(display_name)}: No tilt data found this season.",
                category="mystats"
            )
            return

        await send_chat_message(
            ctx.channel,
            f"⚖️ {format_user_tag(display_name)} Tilt Stats | Run: {points_run:,} pts, {deaths_run:,} deaths | "
            f"Today: {points_today:,} pts, {deaths_today:,} deaths | "
            f"Season: {points_season:,} pts, {deaths_season:,} deaths | "
            f"Last Level Completed: {last_completed_level if last_completed_seen else 0:,}",
            category="mystats"
        )


    @commands.command(name='thisrun')
    async def thisrun_command(self, ctx):
        current_run_id = str(config.get_setting('tilt_current_run_id') or '').strip()
        run_status = 'Active' if current_run_id else 'Idle'

        if current_run_id:
            standings_raw = config.get_setting('tilt_run_ledger') or '{}'
            try:
                standings = json.loads(standings_raw)
                if not isinstance(standings, dict):
                    standings = {}
            except Exception:
                standings = {}

            sorted_standings = sorted(
                ((str(name), _safe_int(points)) for name, points in standings.items()),
                key=lambda item: item[1],
                reverse=True
            )
            leader_text = f"{sorted_standings[0][0]} ({sorted_standings[0][1]:,} pts)" if sorted_standings else 'None'
            run_points = get_int_setting('tilt_run_points', 0)
            run_xp = get_int_setting('tilt_run_xp', 0)
            run_level = get_int_setting('tilt_current_level', 0)
            run_elapsed = format_tilt_duration(get_int_setting('tilt_run_total_seconds', 0))
            run_deaths = get_int_setting('tilt_run_deaths_total', 0)
            top_tiltee = str(config.get_setting('tilt_current_top_tiltee') or 'None')
            top_tiltee_count = get_int_setting('tilt_current_top_tiltee_count', 0)

            message = (
                f"🏃‍➡️ This Run ({run_status}) | Level: {run_level:,} | Elapsed: {run_elapsed} | "
                f"Leader: {leader_text} | Run Pts: {run_points:,} | "
                f"Run Expertise: {run_xp:,} | Top Tiltee: {top_tiltee} ({top_tiltee_count:,}) | "
                f"Run Deaths: {run_deaths:,}"
            )
        else:
            last_run_raw = config.get_setting('tilt_last_run_summary') or '{}'
            try:
                last_run = json.loads(last_run_raw)
                if not isinstance(last_run, dict):
                    last_run = {}
            except Exception:
                last_run = {}

            if not last_run.get('run_id'):
                await send_chat_message(ctx.channel, "🏃‍➡️ This Run | No active or completed tilt run available yet.", category="mystats")
                return

            total_seconds = _safe_int(last_run.get('run_total_seconds', 0))
            total_time = str(last_run.get('total_time') or format_tilt_duration(total_seconds))
            run_points = _safe_int(last_run.get('run_points', 0))
            run_xp = _safe_int(last_run.get('run_xp', last_run.get('run_expertise', 0)))
            run_deaths = _safe_int(last_run.get('run_deaths', 0))
            if run_deaths <= 0 and isinstance(last_run.get('standings'), list):
                run_deaths = sum(
                    _safe_int(item.get('deaths', item.get('death_count', item.get('run_deaths', 0))))
                    for item in last_run.get('standings', [])
                    if isinstance(item, dict)
                )
            ended_level = _safe_int(last_run.get('ended_level', 0))

            message = (
                f"🏃‍➡️ This Run ({run_status}) | Last Completed Level: {ended_level:,} | "
                f"Total Time: {total_time} | Run Pts: {run_points:,} | "
                f"Run Expertise: {run_xp:,} | Run Deaths: {run_deaths:,}"
            )

        await send_chat_message(ctx.channel, message, category="mystats")


    @commands.command(name='xp')
    async def xp_command(self, ctx):
        last_level_xp = get_int_setting('tilt_last_level_xp', 0)
        last_run_xp = get_int_setting('tilt_previous_run_xp', 0)

        marble_day = str(config.get_setting('marble_day') or '').strip()
        if not marble_day:
            _, _, _, adjusted_time = time_manager.get_adjusted_time()
            marble_day = adjusted_time.strftime("%Y-%m-%d")

        season_xp, today_xp = get_tilt_xp_totals_from_results_files(target_date=marble_day)
        lifetime_xp = get_int_setting('tilt_lifetime_expertise', 0)

        await send_chat_message(
            ctx.channel,
            f"⚖️ Expertise Stats | Last Level XP: {last_level_xp:,} | Last Run XP: {last_run_xp:,} | "
            f"Todays XP: {today_xp:,} | Season XP: {season_xp:,} | Lifetime XP: {lifetime_xp:,}",
            category="mystats"
        )


    @commands.command(name='toptiltees')
    async def toptiltees_command(self, ctx):
        season_points_by_player = defaultdict(int)
        top_tiltee_counts = defaultdict(int)

        for tilts_file in glob.glob(os.path.join(config.get_setting('directory'), "tilts_*.csv")):
            try:
                with open(tilts_file, 'rb') as f:
                    raw_data = f.read()
                result = chardet.detect(raw_data)
                encoding = result['encoding'] if result['encoding'] else 'utf-8'

                with open(tilts_file, 'r', encoding=encoding, errors='ignore') as f:
                    reader = iter_csv_rows(f)
                    for row in reader:
                        detail = parse_tilt_result_detail(row)
                        if detail is None:
                            continue

                        username = detail['username']
                        season_points_by_player[username] += detail['points']
                        if detail['is_top_tiltee']:
                            top_tiltee_counts[username] += 1
            except FileNotFoundError:
                continue
            except Exception as e:
                logger.error("Unexpected error", exc_info=True)

        if not top_tiltee_counts:
            await send_chat_message(ctx.channel, "⚖️ No top tiltee data available yet.", category="mystats")
            return

        ranked = sorted(
            top_tiltee_counts.items(),
            key=lambda item: (item[1], season_points_by_player.get(item[0], 0)),
            reverse=True
        )[:10]

        items = [
            f"{format_ranked_label(idx)} {name}, {tops:,} {pluralize(tops, 'top')}, {season_points_by_player.get(name, 0):,} points"
            for idx, (name, tops) in enumerate(ranked, start=1)
        ]

        message = "⚖️ Top Tiltees | " + " | ".join(items)
        await send_chat_message(ctx.channel, message, category="mystats")


    @commands.command(name='top10tiltees')
    async def top10tiltees_command(self, ctx):
        data = defaultdict(int)

        for tilts_file in glob.glob(os.path.join(config.get_setting('directory'), "tilts_*.csv")):
            try:
                with open(tilts_file, 'rb') as f:
                    raw_data = f.read()
                result = chardet.detect(raw_data)
                encoding = result['encoding'] if result['encoding'] else 'utf-8'

                with open(tilts_file, 'r', encoding=encoding, errors='ignore') as f:
                    reader = iter_csv_rows(f)
                    for row in reader:
                        parsed = parse_tilt_result_row(row)
                        if parsed is None:
                            continue

                        racer, points, _ = parsed
                        data[racer] += points
            except FileNotFoundError:
                continue
            except Exception as e:
                logger.error("Unexpected error", exc_info=True)

        if not data:
            await send_chat_message(ctx.channel, "⚖️ No tilt data available yet.", category="mystats")
            return

        top_tilees = sorted(data.items(), key=lambda x: x[1], reverse=True)[:10]
        entries = [
            f"{format_ranked_label(place)} {racer}, {points:,} points"
            for place, (racer, points) in enumerate(top_tilees, start=1)
        ]
        message = "⚖️ Top 10 Tiltees by Tilt Points | " + " | ".join(entries)

        await send_chat_message(ctx.channel, message, category="mystats")


    @commands.command(name='tiltsurvivors')
    async def tiltsurvivors_command(self, ctx):
        run_max_levels = defaultdict(int)
        player_run_levels = defaultdict(set)

        for tilts_file in glob.glob(os.path.join(config.get_setting('directory'), "tilts_*.csv")):
            try:
                with open(tilts_file, 'rb') as f:
                    raw_data = f.read()
                result = chardet.detect(raw_data)
                encoding = result['encoding'] if result['encoding'] else 'utf-8'

                with open(tilts_file, 'r', encoding=encoding, errors='ignore') as f:
                    reader = iter_csv_rows(f)
                    for row in reader:
                        parsed = parse_tilt_result_row(row)
                        if parsed is None or len(row) < 2:
                            continue

                        username, _, run_id = parsed
                        try:
                            level_number = int(''.join(ch for ch in str(row[1]).strip() if ch.isdigit()) or '0')
                        except (TypeError, ValueError):
                            continue

                        if level_number <= 0:
                            continue

                        run_max_levels[run_id] = max(run_max_levels[run_id], level_number)
                        player_run_levels[(username, run_id)].add(level_number)
            except FileNotFoundError:
                continue
            except Exception as e:
                logger.error("Unexpected error", exc_info=True)

        if not player_run_levels:
            await send_chat_message(ctx.channel, "⚖️ No tilt data available yet.", category="mystats")
            return

        player_totals = defaultdict(lambda: {'deaths': 0, 'levels_participated': 0})

        for (username, run_id), levels_survived in player_run_levels.items():
            run_max_level = run_max_levels.get(run_id, 0)
            if run_max_level <= 0 or not levels_survived:
                continue

            survived_count = len(levels_survived)
            last_survived_level = max(levels_survived)
            died_this_run = 1 if last_survived_level < run_max_level else 0
            levels_participated = survived_count + died_this_run

            player_totals[username]['deaths'] += died_this_run
            player_totals[username]['levels_participated'] += levels_participated

        minimum_levels = max(1, get_int_setting('tiltsurvivors_min_levels', get_int_setting('tiltdeath_min_levels', 20)))

        qualified = []
        for username, totals in player_totals.items():
            levels_participated = totals['levels_participated']
            deaths = totals['deaths']
            if levels_participated < minimum_levels:
                continue

            death_rate = (deaths / levels_participated) * 100
            qualified.append((username, deaths, death_rate))

        if not qualified:
            await send_chat_message(
                ctx.channel,
                f"⚖️ No tilt survivor-rate data yet (minimum {minimum_levels} levels participated required).",
                category="mystats"
            )
            return

        ranked = sorted(qualified, key=lambda item: (item[2], item[1], item[0].lower()))[:10]
        message_items = [
            f"{format_ranked_label(idx)} {username}, {deaths} {pluralize(deaths, 'death')}, {100 - death_rate:.1f}% survive"
            for idx, (username, deaths, death_rate) in enumerate(ranked, start=1)
        ]

        await send_chat_message(
            ctx.channel,
            f"⚖️ Top 10 Best Tilt Survival Rate (min {minimum_levels} {pluralize(minimum_levels, 'level')}) | " + " | ".join(message_items),
            category="mystats"
        )


    
    @commands.command(name='top10nwr')
    async def top10nwr_command(self, ctx):
        self.last_command_author = ctx.author.name
        data = {}
        try:
            with open(config.get_setting('allraces_file'), 'r', encoding='utf-8', errors='ignore') as f:
                reader = iter_csv_rows(f)

                for row in reader:
                    # Check if the row has at least 11 columns and the 11th value is not 1
                    if len(row) >= 12 and int(row[11]) != 1:
                        if len(row) >= 5 and int(''.join(row[3]).replace('\x00', '')) != 0:
                            racer = row[2]
                            points = int(row[3])
                            if racer in data:
                                data[racer] += points
                            else:
                                data[racer] = points

                top_racers = sorted(data.items(), key=lambda x: x[1], reverse=True)[:11]

                entries = [
                    f"{format_ranked_label(place)} {racer}, {points:,} points"
                    for place, (racer, points) in enumerate(top_racers, start=1)
                ]
                message = "Top 10 Today (Excluding WRs) | " + " | ".join(entries)

            await self.send_command_response(ctx, message)
        except FileNotFoundError:
            print("File not found.")
            await self.send_command_response(ctx, self.last_command_author + ": No races have been recorded today.")
        except Exception as e:
            logger.error("Unexpected error", exc_info=True)

    @commands.command(name='top10today')
    async def top10scores_command(self, ctx):
        self.last_command_author = ctx.author.name
        data = {}
        try:
            with open(config.get_setting('allraces_file'), 'r', encoding='utf-8', errors='ignore') as f:
                reader = iter_csv_rows(f)

                for row in reader:
                    if len(row) >= 5 and int(''.join(row[3]).replace('\x00', '')) != 0:
                        racer = row[2]
                        points = int(row[3])
                        if racer in data:
                            data[racer] += points
                        else:
                            data[racer] = points

                top_racers = sorted(data.items(), key=lambda x: x[1], reverse=True)[:10]

                entries = [
                    f"{format_ranked_label(place)} {racer}, {points:,} points"
                    for place, (racer, points) in enumerate(top_racers, start=1)
                ]
                message = "Top 10 Today | " + " | ".join(entries)

            await self.send_command_response(ctx, message)
        except FileNotFoundError:
            print("File not found.")
            await self.send_command_response(ctx, self.last_command_author + ": No races have been recorded today.")
        except Exception as e:
            logger.error("Unexpected error", exc_info=True)

    @commands.command(name='top10races')
    async def top10races_command(self, ctx):
        data = {}
        for allraces in glob.glob(os.path.join(config.get_setting('directory'), "allraces_*.csv")):
            try:
                with open(allraces, 'r', encoding='utf-8', errors='ignore') as f:
                    reader = iter_csv_rows(f)
                    for row in reader:
                        if len(row) >= 5 and row[2]:
                            racer = row[2]
                            if racer in data:
                                data[racer] += 1
                            else:
                                data[racer] = 1

            except FileNotFoundError:
                print("File not found.")
            except Exception as e:
                logger.error("Unexpected error", exc_info=True)

        top_racers = sorted(data.items(), key=lambda x: x[1], reverse=True)[:10]
        entries = [
            f"{format_ranked_label(place)} {racer}, {races:,} {pluralize(races, 'race')}"
            for place, (racer, races) in enumerate(top_racers, start=1)
        ]
        message = "Top 10 Racers by Total Races | " + " | ".join(entries)

        await self.send_command_response(ctx, message)

    @commands.command(name='top10wins')
    async def top10wins_command(self, ctx):
        data = {}
        for allraces in glob.glob(os.path.join(config.get_setting('directory'), "allraces_*.csv")):
            try:
                with open(allraces, 'r', encoding='utf-8', errors='ignore') as f:
                    reader = iter_csv_rows(f)
                    for row in reader:
                        if len(row) >= 5 and int(row[0]) == 1:
                            racer = row[2]
                            wins = int(row[0])
                            if racer in data:
                                data[racer] += wins
                            else:
                                data[racer] = wins
            except FileNotFoundError:
                print("File not found. #609")
            except Exception as e:
                logger.error("Unexpected error", exc_info=True)

        top_racers = sorted(data.items(), key=lambda x: x[1], reverse=True)[:10]
        entries = [
            f"{format_ranked_label(place)} {racer}, {wins:,} {pluralize(wins, 'win')}"
            for place, (racer, wins) in enumerate(top_racers, start=1)
        ]
        message = "Top 10 Wins Season {} | ".format(config.get_setting('season')) + " | ".join(entries)

        await self.send_command_response(ctx, message)

    @commands.command(name='top10season')
    async def top10season_command(self, ctx):
        data = {}
        for allraces in glob.glob(os.path.join(config.get_setting('directory'), "allraces_*.csv")):
            try:
                with open(allraces, 'r', encoding='utf-8', errors='ignore') as f:
                    reader = iter_csv_rows(f)
                    for row in reader:
                        if len(row) >= 5 and int(row[3]) != 0:
                            racer = row[2]
                            points = int(row[3])
                            if racer in data:
                                data[racer] += points
                            else:
                                data[racer] = points
            except FileNotFoundError:
                print("File not found. #651")
            except Exception as e:
                logger.error("Unexpected error", exc_info=True)

        top_racers = sorted(data.items(), key=lambda x: x[1], reverse=True)[:10]
        entries = [
            f"{format_ranked_label(place)} {racer}, {points:,} points"
            for place, (racer, points) in enumerate(top_racers, start=1)
        ]
        message = "Top 10 Season {} | ".format(config.get_setting('season')) + " | ".join(entries)

        await self.send_command_response(ctx, message)

    @commands.command(name='top10wr')
    async def top10worldrecords_command(self, ctx):
        # Dictionary to store world record stats for each racer.
        # Each key maps to a dictionary with 'count' and 'points'
        world_record_stats = {}

        # Loop through all CSV files matching the pattern
        for allraces in glob.glob(os.path.join(config.get_setting('directory'), "allraces_*.csv")):
            try:
                with open(allraces, 'rb') as f:
                    raw_data = f.read()
                result = chardet.detect(raw_data)
                encoding = result['encoding'] if result['encoding'] else 'utf-8'

                with open(allraces, 'r', encoding=encoding, errors='ignore') as f:
                    reader = iter_csv_rows(f)
                    for row in reader:
                        # Check that the row has at least 12 columns and the 12th column equals "1"
                        if len(row) > 11 and row[11] == '1':
                            racer = row[2].strip()
                            try:
                                points = int(row[3])
                            except Exception:
                                points = 0
                            # If the point value is 0, ignore this world record
                            if points == 0:
                                continue
                            if racer not in world_record_stats:
                                world_record_stats[racer] = {'count': 0, 'points': 0}
                            world_record_stats[racer]['count'] += 1
                            world_record_stats[racer]['points'] += points

            except FileNotFoundError:
                print("File not found.")
                await self.send_command_response(ctx, "No season races recorded yet")
                return
            except Exception as e:
                logger.error("Unexpected error", exc_info=True)
                return

        if not world_record_stats:
            await self.send_command_response(ctx, "No world records found.")
            return

        # Sort by world record count first, and if tied, by total points (both descending)
        top_records = sorted(
            world_record_stats.items(),
            key=lambda x: (x[1]['count'], x[1]['points']),
            reverse=True
        )[:10]

        # Build the output message with each entry formatted as "Racer: count (points)"
        # and joined by " | " with no trailing pipe.
        entries = [
            f"{format_ranked_label(place)} {racer}, {stats['count']:,} {pluralize(stats['count'], 'win')}, {stats['points']:,} pts"
            for place, (racer, stats) in enumerate(top_records, start=1)
        ]
        output_msg = " | ".join(entries)

        # Prepend the header to the message.
        final_msg = f"Top 10 World Record Wins | {output_msg}"

        await self.send_command_response(ctx, final_msg)





    @commands.command(name='top10seasonnwr')
    async def top10seasonnwr_command(self, ctx):
        data = {}
        for allraces in glob.glob(os.path.join(config.get_setting('directory'), "allraces_*.csv")):
            try:
                with open(allraces, 'r', encoding='utf-8', errors='ignore') as f:
                    reader = iter_csv_rows(f)
                    for row in reader:
                        # Check 12th value at index 11 (must be 0 or exists)
                        if len(row) >= 12 and int(row[11]) != 1:  # Changed to index 11
                            if len(row) >= 5 and int(row[3]) != 0:
                                racer = row[2]
                                points = int(row[3])
                                data[racer] = data.get(racer, 0) + points
            except FileNotFoundError:
                print("File not found. #651")
            except Exception as e:
                logger.error("Unexpected error", exc_info=True)

        top_racers = sorted(data.items(), key=lambda x: x[1], reverse=True)[:10]
        entries = [
            f"{format_ranked_label(place)} {racer}, {points:,} points"
            for place, (racer, points) in enumerate(top_racers, start=1)
        ]
        message = f"Top 10 Season {config.get_setting('season')} (Excluding WRs) | " + " | ".join(entries)

        await self.send_command_response(ctx, message)

    async def event_command_error(self, ctx, error):
        if isinstance(error, CommandNotFound):
            return
        raise error

    async def reconnect_with_new_token(self, new_token, retries=5, delay=5):
        if retries <= 0:
            print("Max retries reached. Could not reconnect.")
            return

        try:
            print(f"Reconnecting with new token... (Attempt {6 - retries}/5)\n")

            tasks_to_cancel = [task for task in asyncio.all_tasks(self.loop) if not task.done()]
            for task in tasks_to_cancel:
                try:
                    task.cancel()
                    await task
                except asyncio.CancelledError:
                    pass

            await self.close()

            global bot
            bot = Bot()

            bot.token = new_token

            await bot.start()

        except Exception as e:
            logger.error("Failed to reconnect", exc_info=True)
            await asyncio.sleep(delay)
            await self.reconnect_with_new_token(new_token, retries - 1, delay * 2)

    def open_login_url(self):
        url = get_authorization_url()
        webbrowser.open(url)

    def is_token_expired(token_data):
        expires_at = token_data.get('expires_at')
        return expires_at < time.time()

    def refresh_access_token(self):
        token_data = load_token_data()
        if not token_data or 'refresh_token' not in token_data:
            return None

        token_url = "https://id.twitch.tv/oauth2/token"
        refresh_token = token_data['refresh_token']

        refresh_data = {
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token
        }

        response = requests.post(token_url, data=refresh_data)
        if response.status_code == 200:
            new_token_info = response.json()
            save_token_data(new_token_info)


            if verify_token(new_token_info['access_token']):
                return new_token_info['access_token']
            else:
                print("Refreshed token is invalid.")
                return None
        else:
            print(f"Failed to refresh token: {response.text}")
            return None


def log_message(message):
    if text_widget:
        text_widget.insert(tk.END, message + '\n')
        text_widget.see(tk.END)
    else:
        print(message)


def one_time_sync():
    base_directory = appdata_path()
    directory_55 = os.path.join(base_directory, "Results", "Season_" + '55')
    directory_56 = os.path.join(base_directory, "Results", "Season_" + '56')
    directory_57 = os.path.join(base_directory, "Results", "Season_" + '57')

    asyncio.gather(
        process_season(directory_55, 55),
        process_season(directory_56, 56),
	    process_season(directory_57, 57)
    )

    config.set_setting('sync', 'Yes', persistent=True)


def process_season(directory, season):
    if not os.path.exists(directory):
        return

    racer_data = defaultdict(lambda: {
        'racer_name': '',
        'season': season,
        'channel': config.get_setting('CHANNEL'),
        'race_points': 0,
        'race_wins': 0,
        'race_races': 0,
        'br_points': 0,
        'br_wins': 0,
        'br_races': 0,
        'crownwins': 0,
        'br_kills': 0,
        'br_damage': 0,
        'eliminations': 0
    })

    last_br_win = defaultdict(lambda: None)

    race_hs_season = 0
    br_hs_season = 0
    totalpointsseason = 0
    totalcountseason = 0

    for allraces in glob.glob(os.path.join(directory, "allraces_*.csv")):
        try:
            # Open the file in binary mode to detect encoding
            with open(allraces, 'rb') as f:
                raw_data = f.read()

            # Detect encoding using chardet
            result = chardet.detect(raw_data)
            encoding = result['encoding'] if result['encoding'] else 'utf-8'  # Default to UTF-8 if detection fails

            with open(allraces, 'r', encoding=encoding, errors='ignore') as f:
                reader = iter_csv_rows(f)
                for rowrow in reader:
                    if len(rowrow) < 7:
                        continue
                    row = [col.strip().replace('\x00', '') for col in rowrow]

                    position = int(row[0])
                    racer_name = row[1].lower()
                    points = int(row[3])
                    race_type = row[4]
                    timestamp = datetime.strptime(row[5], "%Y-%m-%d %H:%M:%S")
                    marble_count = int(row[6])

                    racer_data[racer_name]['racer_name'] = racer_name
                    racer_data[racer_name]['season'] = season

                    if race_type == 'Race':
                        racer_data[racer_name]['race_points'] += points
                        racer_data[racer_name]['race_races'] += 1
                        if position == 1:
                            racer_data[racer_name]['race_wins'] += 1

                    if race_type == 'BR':
                        racer_data[racer_name]['br_points'] += points
                        racer_data[racer_name]['br_races'] += 1
                        if position == 1:
                            racer_data[racer_name]['br_wins'] += 1

                            if marble_count >= 10:
                                if last_br_win[racer_name] is not None:
                                    racer_data[racer_name]['crownwins'] += 1

                                last_br_win[racer_name] = timestamp

                    if len(row) >= 5:
                        if row[0] == '1':
                            totalcountseason += 1
                        if row[4] == 'Race' and int(row[3]) > race_hs_season:
                            race_hs_season = int(row[3])
                        elif row[4] == 'BR' and int(row[3]) > br_hs_season:
                            br_hs_season = int(row[3])
                        totalpointsseason += int(row[3])

        except FileNotFoundError:
            print(f"File not found: {allraces}")
        except Exception as e:
            logger.error("An error occurred while processing the file %s", allraces, exc_info=True)

    # Use %localappdata%/mystats/data as the save directory
    local_app_data = os.getenv('LOCALAPPDATA')
    save_directory = os.path.join(local_app_data, 'mystats', 'data')

    # Ensure the directory exists
    if not os.path.exists(save_directory):
        try:
            os.makedirs(save_directory)
        except OSError as e:
            print(f"Error creating directory {save_directory}: {e}")
            return

    # Save racer data to CSV using the actual season value
    racer_data_csv = os.path.join(save_directory, f"{season}_racerdata.csv")
    with open(racer_data_csv, 'w', newline='') as csvfile:
        fieldnames = ['racer_name', 'season', 'channel', 'race_points', 'race_wins', 'race_races', 'br_points', 'br_wins',
                      'br_races', 'crownwins', 'br_kills', 'br_damage', 'eliminations']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for racer in racer_data.values():
            writer.writerow(racer)

    streamer_data = {
        'channel': config.get_setting('CHANNEL'),
        'season': season,
        'points': totalpointsseason,
        'total_races': totalcountseason,
        'race_hs': race_hs_season,
        'race_hs_today': 0,
        'br_hs': br_hs_season,
        'br_hs_today': 0,
        'marble_day': config.get_setting('marble_day'),
    }

    streamer_data_csv = os.path.join(save_directory, f"{season}_streamerdata.csv")
    with open(streamer_data_csv, 'w', newline='') as csvfile:
        fieldnames = list(streamer_data.keys())
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(streamer_data)

    api_url = "https://mystats.camwow.tv/api/app/upload-data"
    files = {
        'viewerData': open(racer_data_csv, 'rb'),
        'streamerData': open(streamer_data_csv, 'rb')
    }

    max_retries = 20
    retry_delay = 1

    try:
        response = requests.post(api_url, files=files)
        if response.status_code == 504:
            print("Data Sync Delayed. We will try again on next reboot.")
        if response.status_code != 200 and response.status_code != 504:
            print("Report this error to the mystats discord: " + str(response.text)) + '' + str(response.status_code)
        if response.status_code == 200:
            print("Data synced with MyStats server.")
        else:
            pass
    except requests.exceptions.ConnectionError as e:
        time.sleep(retry_delay)
        retry_delay *= 2
        print("error", e)
    except json.JSONDecodeError as e:
        print("Failed to decode JSON from response:", e)


async def competitive_raid_monitor(bot):
    next_poll_at = None

    while not bot.stop_event.is_set():
        try:
            monitor_enabled = parse_boolean_token(config.get_setting('competitive_raid_monitor_enabled'), default=False)
            if not monitor_enabled:
                next_poll_at = None
                await asyncio.sleep(2)
                continue

            now_monotonic = time.monotonic()
            if next_poll_at is not None and now_monotonic < next_poll_at:
                await asyncio.sleep(min(5, max(0.5, next_poll_at - now_monotonic)))
                continue

            payload = await asyncio.to_thread(fetch_competitions_payload)
            payload_fields = _collect_payload_field_names(payload)
            payload_signature = '|'.join(payload_fields)
            if payload_signature != bot.last_competitive_raid_field_list_signature:
                bot.last_competitive_raid_field_list_signature = payload_signature

            now_utc = datetime.now(timezone.utc)
            local_streamer = normalize_channel_name(bot.channel_name)
            _, live_info = _extract_phase_streamer_info(payload)
            live_streamer = normalize_channel_name((live_info or {}).get('streamer'))

            cycle_state = get_competitive_raid_cycle_state(now_utc)
            cycle_window = cycle_state['window']
            cycle_seconds_remaining = cycle_state['seconds_until_transition']

            derived_live_started_at = get_competitive_raid_live_window_started_at(now_utc)
            live_started_at = (live_info or {}).get('started_at') or derived_live_started_at
            previous_phase = str(config.get_setting('competitive_raid_phase') or '').lower()
            persisted_live_start = _parse_iso_utc(config.get_setting('competitive_raid_live_started_at'))

            if live_streamer:
                bot.last_competitive_raid_streamer = live_streamer
                persist_competitive_raid_snapshot(payload, live_streamer, live_started_at)
            if cycle_window == 'queue':
                queue_started_at = derived_live_started_at + timedelta(minutes=5)
                queue_start_iso = queue_started_at.isoformat()
                if config.get_setting('competitive_raid_queue_started_at') != queue_start_iso:
                    config.set_setting('competitive_raid_queue_started_at', queue_start_iso, persistent=True)
                if previous_phase != 'live':
                    config.set_setting('competitive_raid_phase', 'queue', persistent=True)

            if cycle_window == 'live' and live_streamer == local_streamer and live_started_at is not None:
                live_start_iso = live_started_at.isoformat()
                if config.get_setting('competitive_raid_live_started_at') != live_start_iso:
                    config.set_setting('competitive_raid_live_started_at', live_start_iso, persistent=True)
                    config.set_setting('competitive_raid_phase', 'live', persistent=True)
                    participant_count = _extract_participant_count(
                        payload,
                        preferred_node=(live_info or {}).get('source'),
                        streamer_name=local_streamer,
                    )
                    raider_segment = (
                        f" ({participant_count:,} raiders)" if participant_count is not None else ""
                    )
                    live_message = (
                        f"🏁 Competitive raid host selected: {format_user_tag(local_streamer)}{raider_segment}! "
                        "Welcome competitive raiders—good luck and have fun!"
                    )
                    if bot.channel is not None:
                        await send_chat_message(bot.channel, live_message, category='race')
                    enqueue_overlay_event('raid_selected', live_message)

                # Queue-side visibility: when local streamer is active host, announce queue link once per live window.
                if config.get_setting('competitive_raid_last_queue_open_live_started_at') != live_start_iso:
                    queue_message = (
                        "🧾 Next competitive raid queue is open now: https://pixelbypixel.studio/competitions"
                    )
                    if bot.channel is not None:
                        await send_chat_message(bot.channel, queue_message, category='race')
                    enqueue_overlay_event('raid_queue_open', queue_message)
                    config.set_setting('competitive_raid_last_queue_open_live_started_at', live_start_iso, persistent=True)

            if (
                previous_phase == 'live'
                and persisted_live_start is not None
                and (cycle_window != 'live' or live_streamer != local_streamer)
            ):
                summary_key = persisted_live_start.isoformat()
                if config.get_setting('competitive_raid_last_summary_live_started_at') != summary_key:
                    history_payload = None
                    try:
                        history_payload = await asyncio.to_thread(fetch_competitions_history_payload)
                    except requests.RequestException as history_error:
                        print(f"Competitive raid history request failed: {history_error}")

                    latest_entry = _latest_history_entry_for_streamer(history_payload, local_streamer) if history_payload else None
                    summary_message = _format_history_summary_for_streamer(latest_entry, local_streamer)
                    if bot.channel is not None:
                        await send_chat_message(bot.channel, summary_message, category='race')
                    enqueue_overlay_event('raid_summary', summary_message)
                    config.set_setting('competitive_raid_last_summary_live_started_at', summary_key, persistent=True)
                    config.set_setting('competitive_raid_phase', 'idle', persistent=True)
                    config.set_setting('competitive_raid_live_started_at', '', persistent=True)

            if cycle_window == 'live':
                if live_streamer:
                    next_delay = 10 if cycle_seconds_remaining < 90 else 20
                else:
                    # At go-live, poll aggressively until host assignment appears.
                    next_delay = 8
                next_poll_at = time.monotonic() + max(5, min(30, next_delay))
            else:
                # Queue has no assigned host; poll slower except near live boundary.
                next_delay = 10 if cycle_seconds_remaining < 90 else 30
                next_poll_at = time.monotonic() + max(10, min(60, next_delay))

        except asyncio.CancelledError:
            print("Competitive raid monitor task was cancelled.")
            break
        except requests.RequestException as error:
            print(f"Competitive raid monitor request failed: {error}")
            next_poll_at = time.monotonic() + 60
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            print(f"Competitive raid monitor parse error: {error}")
            next_poll_at = time.monotonic() + 90
        except Exception as error:
            print(f"Competitive raid monitor error: {error}")
            next_poll_at = time.monotonic() + 90

    print("Competitive raid monitor task has exited.")


async def tilted(bot):
    last_modified_tilt = None
    run_id = str(config.get_setting('tilt_current_run_id') or '').strip() or None
    last_tilt_processed_at = 0.0
    tilt_process_cooldown_seconds = 10.0
    max_message_length = 480
    tilt_levels_count = 0
    last_tilt_narrative_alert_level_count = 0
    current_tilt_points_leader = None

    while not bot.stop_event.is_set():
        try:
            tilt_level_file = config.get_setting('tilt_level_file')
            current_modified_tilt = os.path.getmtime(tilt_level_file)
        except FileNotFoundError:
            print("Tilt level file not found. Trying again.")
            await asyncio.sleep(1)
            continue
        except asyncio.CancelledError:
            print("Tilted task was cancelled.")
            break
        except Exception as e:
            logger.error("Error checking modification time", exc_info=True)
            await asyncio.sleep(1)
            continue

        if last_modified_tilt is None:
            last_modified_tilt = current_modified_tilt
            print("Tilted monitoring initiated. System is ready to go!")
            await asyncio.sleep(1)
            continue

        if current_modified_tilt == last_modified_tilt:
            await asyncio.sleep(10)
            continue

        now_monotonic = time.monotonic()
        if (now_monotonic - last_tilt_processed_at) < tilt_process_cooldown_seconds:
            last_modified_tilt = current_modified_tilt
            await asyncio.sleep(1)
            continue

        await asyncio.sleep(1)
        set_overlay_mode('tilt')

        try:
            level_rows = safe_read_csv_rows(tilt_level_file)
            level_state = parse_tilt_level_state(level_rows)
            if level_state is None:
                print("Tilt level data incomplete; waiting for next write.")
                last_modified_tilt = current_modified_tilt
                await asyncio.sleep(1)
                continue

            current_level = level_state['current_level']
            elapsed_time = level_state['elapsed_time']
            top_tiltee = level_state['top_tiltee'] or 'None'
            level_points = level_state['level_xp']
            total_xp = level_state['total_xp']
            level_passed = level_state['level_passed']

            is_level_live = parse_boolean_token(level_state.get('live'), default=True)
            suppress_offline_tilt_chat = is_chat_response_enabled("chat_tilt_suppress_offline")
            should_suppress_tilt_chat = suppress_offline_tilt_chat and not is_level_live

            set_tilt_runtime_setting('tilt_current_level', str(current_level))
            set_tilt_runtime_setting('tilt_current_elapsed', str(elapsed_time))
            set_tilt_runtime_setting('tilt_current_top_tiltee', str(top_tiltee))

            if run_id is None:
                if current_level <= 1:
                    run_id = base64.urlsafe_b64encode(uuid.uuid4().bytes).rstrip(b'=').decode('utf-8')
                    set_tilt_runtime_setting('tilt_run_started_at', get_internal_adjusted_time().strftime('%Y-%m-%d %H:%M:%S'))
                    set_tilt_runtime_setting('tilt_run_ledger', '{}')
                    set_tilt_runtime_setting('tilt_run_deaths_ledger', '{}')
                    set_tilt_runtime_setting('tilt_top_tiltee_ledger', '{}')
                    set_tilt_runtime_setting('tilt_current_top_tiltee_count', '0')
                    set_tilt_runtime_setting('tilt_run_xp', '0')
                    set_tilt_runtime_setting('tilt_run_points', '0')
                    set_tilt_runtime_setting('tilt_run_deaths_total', '0')
                    set_tilt_runtime_setting('tilt_run_total_seconds', '0')
                    set_tilt_runtime_setting('tilt_previous_run_xp', config.get_setting('tilt_run_xp') or '0')
                    set_tilt_runtime_setting('tilt_level_completion_overlay', '{}')
                    set_tilt_runtime_setting('tilt_run_completion_overlay', '{}')
                    current_tilt_points_leader = None
                else:
                    # Recovery path: app restarted or was upgraded mid-run.
                    # If no run id persisted, synthesize one and continue tracking
                    # from the current level instead of dropping all subsequent updates.
                    run_id = base64.urlsafe_b64encode(uuid.uuid4().bytes).rstrip(b'=').decode('utf-8')
                    if not str(config.get_setting('tilt_run_started_at') or '').strip():
                        set_tilt_runtime_setting('tilt_run_started_at', get_internal_adjusted_time().strftime('%Y-%m-%d %H:%M:%S'))
                    logger.info(
                        "Recovered active tilt run without persisted run id at level %s; generated new run_id=%s",
                        current_level,
                        run_id,
                    )

            set_tilt_runtime_setting('tilt_current_run_id', run_id)

            try:
                run_ledger = json.loads(config.get_setting('tilt_run_ledger') or '{}')
                if not isinstance(run_ledger, dict):
                    run_ledger = {}
            except Exception:
                run_ledger = {}

            try:
                run_deaths_ledger = json.loads(config.get_setting('tilt_run_deaths_ledger') or '{}')
                if not isinstance(run_deaths_ledger, dict):
                    run_deaths_ledger = {}
            except Exception:
                run_deaths_ledger = {}

            try:
                tilt_top_tiltee_ledger = json.loads(config.get_setting('tilt_top_tiltee_ledger') or '{}')
                if not isinstance(tilt_top_tiltee_ledger, dict):
                    tilt_top_tiltee_ledger = {}
            except Exception:
                tilt_top_tiltee_ledger = {}

            tilt_player_file = config.get_setting('tilt_player_file')
            tilt_rows = safe_read_csv_rows(tilt_player_file)
            player_data_rows = tilt_rows[1:] if len(tilt_rows) > 1 else []

            active_players = []
            survivors = []
            deaths_this_level = 0

            for row in player_data_rows:
                if len(row) < 5:
                    continue

                username = row[0].strip() if len(row) > 0 else ''
                points_raw = row[2].strip() if len(row) > 2 else '0'
                player_level_raw = row[4].strip() if len(row) > 4 else '0'

                if not username:
                    continue

                try:
                    player_level = int(''.join(ch for ch in player_level_raw if ch.isdigit()) or '0')
                except ValueError:
                    player_level = 0

                if player_level != current_level:
                    continue

                try:
                    player_points = int(float(points_raw))
                except (TypeError, ValueError):
                    player_points = 0

                active_players.append((username, player_points, row))

                if player_points > 0:
                    survivors.append((username, player_points, row))
                    run_ledger[username] = int(run_ledger.get(username, 0)) + level_points
                else:
                    deaths_this_level += 1
                    run_deaths_ledger[username] = int(run_deaths_ledger.get(username, 0)) + 1

            terminal_run_death = 1 if (not level_passed and 1 <= len(survivors) <= 2) else 0
            deaths_this_level += terminal_run_death

            earned_xp = int(math.floor(len(survivors) * get_tilt_multiplier(current_level)))
            level_elapsed_seconds = parse_tilt_elapsed_to_seconds(elapsed_time)
            run_total_seconds = get_int_setting('tilt_run_total_seconds', 0) + level_elapsed_seconds
            run_xp = get_int_setting('tilt_run_xp', 0) + earned_xp
            run_points = get_int_setting('tilt_run_points', 0) + (level_points if survivors else 0)
            run_deaths_total = get_int_setting('tilt_run_deaths_total', 0) + deaths_this_level
            total_xp_today = get_int_setting('tilt_total_xp_today', 0) + earned_xp
            total_deaths_today = get_int_setting('tilt_total_deaths_today', 0) + deaths_this_level

            best_run_xp_today = max(get_int_setting('tilt_best_run_xp_today', 0), run_xp)
            if best_run_xp_today != get_int_setting('tilt_best_run_xp_today', 0):
                set_tilt_runtime_setting('tilt_best_run_xp_today', str(best_run_xp_today))

            season_best_floor_level_num = get_tilt_best_floor_level_num('tilt_season_best_level')
            personal_best_floor_level_num = get_tilt_best_floor_level_num('tilt_personal_best_level')

            if survivors:
                highest_level_points_today = max(get_int_setting('tilt_highest_level_points_today', 0), level_points)
                highest_level_reached_num = max(get_int_setting('tilt_highest_level_reached_num', 0), current_level)
                season_best_level_num = max(get_int_setting('tilt_season_best_level_num', 0), current_level, season_best_floor_level_num)
                personal_best_level_num = max(get_int_setting('tilt_personal_best_level_num', 0), current_level, personal_best_floor_level_num)
            else:
                highest_level_points_today = get_int_setting('tilt_highest_level_points_today', 0)
                highest_level_reached_num = get_int_setting('tilt_highest_level_reached_num', 0)
                season_best_level_num = max(get_int_setting('tilt_season_best_level_num', 0), season_best_floor_level_num)
                personal_best_level_num = max(get_int_setting('tilt_personal_best_level_num', 0), personal_best_floor_level_num)

            set_tilt_runtime_setting('tilt_run_xp', str(run_xp))
            set_tilt_runtime_setting('tilt_last_level_xp', str(earned_xp))
            set_tilt_runtime_setting('tilt_run_points', str(run_points))
            set_tilt_runtime_setting('tilt_run_deaths_total', str(run_deaths_total))
            set_tilt_runtime_setting('tilt_run_total_seconds', str(run_total_seconds))
            set_tilt_runtime_setting('tilt_total_xp_today', str(total_xp_today))
            set_tilt_runtime_setting('tilt_total_deaths_today', str(total_deaths_today))
            set_tilt_runtime_setting('tilt_highest_level_points_today', str(highest_level_points_today))
            set_tilt_runtime_setting('tilt_highest_level_reached_num', str(highest_level_reached_num))
            set_tilt_runtime_setting('tilt_season_best_level_num', str(season_best_level_num))
            set_tilt_runtime_setting('tilt_personal_best_level_num', str(personal_best_level_num))

            season_best_setting_level = get_int_setting('tilt_season_best_level', 1)
            personal_best_setting_level = get_int_setting('tilt_personal_best_level', 1)
            updated_season_best_setting_level = max(season_best_setting_level, season_best_level_num + 1)
            updated_personal_best_setting_level = max(personal_best_setting_level, personal_best_level_num + 1)

            if updated_season_best_setting_level != season_best_setting_level:
                config.set_setting('tilt_season_best_level', str(updated_season_best_setting_level), persistent=True)
            if updated_personal_best_setting_level != personal_best_setting_level:
                config.set_setting('tilt_personal_best_level', str(updated_personal_best_setting_level), persistent=True)

            set_tilt_runtime_setting('tilt_run_ledger', json.dumps(run_ledger))
            set_tilt_runtime_setting('tilt_run_deaths_ledger', json.dumps(run_deaths_ledger))

            lifetime_expertise = get_int_setting('tilt_lifetime_expertise', 0)
            lifetime_base_xp = get_int_setting('tilt_lifetime_base_xp', 0)

            # Some Tilt sources report total expertise including historical baseline,
            # while others report only in-app progression. Normalize to an absolute
            # lifetime total so we never add the configured baseline twice.
            adjusted_total_xp = total_xp if (lifetime_base_xp > 0 and total_xp >= lifetime_base_xp) else (total_xp + lifetime_base_xp)

            # Repair legacy inflated values created by older baseline math
            # (stored ~= adjusted_total + lifetime_base).
            if (
                lifetime_base_xp > 0
                and adjusted_total_xp > 0
                and lifetime_expertise > adjusted_total_xp
                and abs(lifetime_expertise - (adjusted_total_xp + lifetime_base_xp)) <= 5000
            ):
                lifetime_expertise = adjusted_total_xp

            if adjusted_total_xp > lifetime_expertise:
                lifetime_expertise = adjusted_total_xp
            lifetime_expertise += earned_xp
            set_tilt_runtime_setting('tilt_lifetime_expertise', str(lifetime_expertise))

            if level_passed:
                tilt_levels_count += 1

                top_tiltee_run_count = 0
                if top_tiltee and top_tiltee != 'None':
                    top_tiltee_run_count = int(tilt_top_tiltee_ledger.get(top_tiltee, 0)) + 1
                    tilt_top_tiltee_ledger[top_tiltee] = top_tiltee_run_count
                set_tilt_runtime_setting('tilt_top_tiltee_ledger', json.dumps(tilt_top_tiltee_ledger))
                set_tilt_runtime_setting('tilt_current_top_tiltee_count', str(top_tiltee_run_count))

                tilts_results_file = config.get_setting('tilts_results_file')
                if not tilts_results_file:
                    create_results_files()
                    tilts_results_file = config.get_setting('tilts_results_file')

                if is_level_live:
                    try:
                        with open(tilts_results_file, 'a', newline='', encoding='utf-8') as tilts_file:
                            writer = csv.writer(tilts_file)
                            event_ids_tmp = config.get_setting('active_event_ids')
                            if event_ids_tmp is not None:
                                event_ids_tmp = event_ids_tmp.strip("[]").split(",")
                                event_ids = [int(event_id.strip().replace('"', '')) for event_id in event_ids_tmp if event_id.strip().replace('"', '').isdigit()]
                            else:
                                event_ids = [0]

                            normalized_top_tiltee = normalize_tilt_player_name(top_tiltee)
                            for username, _, row in active_players:
                                is_top_tiltee = normalize_tilt_player_name(username) == normalized_top_tiltee
                                data_to_write = [run_id, current_level] + row + [str(is_top_tiltee), event_ids]
                                writer.writerow(data_to_write)
                        logger.info("Data synced: tilt results written to tilts results file")
                    except Exception as e:
                        logger.error("Error opening/writing to tilts_results_file", exc_info=True)

                narrative_messages = []
                if is_chat_response_enabled("chat_narrative_alerts"):
                    if is_chat_response_enabled("narrative_alert_grinder_enabled") and is_tilt_top_tiltee_milestone(top_tiltee_run_count):
                        narrative_messages.append(
                            f"🏁 Grinder: {top_tiltee} reached {top_tiltee_run_count} top-tiltee appearances this run"
                        )

                    if is_chat_response_enabled("narrative_alert_winmilestone_enabled") and top_tiltee_run_count > 0:
                        narrative_messages.append(
                            f"🏆 Top Tiltee Milestone: {top_tiltee} now has {top_tiltee_run_count} tops this run"
                        )

                    if is_chat_response_enabled("narrative_alert_leadchange_enabled") and run_ledger:
                        sorted_points = sorted(run_ledger.items(), key=lambda item: item[1], reverse=True)
                        leader_username, leader_points = sorted_points[0]
                        second_place_points = sorted_points[1][1] if len(sorted_points) > 1 else 0
                        lead_gap = leader_points - second_place_points
                        min_lead_gap = max(0, get_int_setting("narrative_alert_min_lead_change_points", 500))
                        tied_for_lead = len(sorted_points) > 1 and second_place_points == leader_points
                        if (not tied_for_lead and leader_username != current_tilt_points_leader
                                and lead_gap >= min_lead_gap):
                            current_tilt_points_leader = leader_username
                            narrative_messages.append(
                                f"📈 Lead Change: {leader_username} now leads by {lead_gap:,} points"
                            )

                if narrative_messages:
                    cooldown_races = max(0, get_int_setting("narrative_alert_cooldown_races", 3))
                    max_items = max(1, get_int_setting("narrative_alert_max_items", 3))
                    if cooldown_races == 0 or (tilt_levels_count - last_tilt_narrative_alert_level_count) >= cooldown_races:
                        combined_narrative = "📣 Player Alerts: " + " | ".join(narrative_messages[:max_items]) + "."
                        if is_chat_response_enabled("chat_tilt_results") and not should_suppress_tilt_chat:
                            await send_chat_message(bot.channel, combined_narrative, category="tilt")
                        last_tilt_narrative_alert_level_count = tilt_levels_count

                finisher_names = [username for username, _, _ in survivors]
                limited_finishers = finisher_names[:get_chat_max_names()]
                redact_survivors = is_chat_response_enabled("chat_tilt_redact_survivor_names")
                base_msg = (
                    f"✅ End of Tilt Level {current_level} | Level Completion Time: {elapsed_time} | "
                    f"Top Tiltee: {top_tiltee} | Points Earned: {level_points} | Survivors: "
                )

                if limited_finishers:
                    if redact_survivors:
                        survivor_tokens = [f"Redacted x{len(limited_finishers)}"]
                    else:
                        survivor_tokens = limited_finishers

                    chunks = chunked_join_messages(base_msg, f"Level {current_level} Survivors: ", survivor_tokens, max_length=max_message_length)
                    for chunk in chunks:
                        if is_chat_response_enabled("chat_tilt_results") and not should_suppress_tilt_chat:
                            await send_chat_message(bot.channel, chunk, category="tilt")
                    text_area.insert('end', f"\n{base_msg}{', '.join(survivor_tokens)}\n")
                else:
                    print("No player data to send for current level.")

                total_active = len(active_players)
                survivor_count = len(survivors)
                death_rate = round(((deaths_this_level / total_active) * 100), 1) if total_active else 0
                survival_rate = round(((survivor_count / total_active) * 100), 1) if total_active else 0
                completion_summary = {
                    'completed_at': get_internal_now_iso(timespec='seconds'),
                    'level': current_level,
                    'top_tiltee': top_tiltee,
                    'top_tiltee_count': top_tiltee_run_count,
                    'elapsed_time': elapsed_time,
                    'total_time': format_tilt_duration(run_total_seconds),
                    'run_total_seconds': run_total_seconds,
                    'level_points': level_points,
                    'earned_xp': earned_xp,
                    'survivors': survivor_count,
                    'deaths': deaths_this_level,
                    'death_rate': death_rate,
                    'survival_rate': survival_rate,
                }
                set_tilt_runtime_setting('tilt_level_completion_overlay', json.dumps(completion_summary))

                write_tilt_output_files({
                    'LastLevelPoints.txt': f"{level_points:,}",
                    'CurrentLevel.txt': str(current_level + 1),
                    'HighestLevelPoints.txt': f"{highest_level_points_today:,}",
                    'HighestLevelReached.txt': str(highest_level_reached_num + 1 if highest_level_reached_num > 0 else 1),
                    'SeasonBestLevel.txt': str(season_best_level_num + 1 if season_best_level_num > 0 else 1),
                    'PersonalBestLevel.txt': str(personal_best_level_num + 1 if personal_best_level_num > 0 else 1),
                    'CurrentRunExpertise.txt': f"{run_xp:,}",
                    'RunTotalPoints.txt': f"{run_points:,}",
                    'TotalExpertiseToday.txt': f"{total_xp_today:,}",
                    'TotalDeathsToday.txt': f"{total_deaths_today:,}",
                    'LastLevelExpertise.txt': f"{earned_xp:,}",
                    'TotalExpertise.txt': f"{lifetime_expertise:,}"
                })

            else:
                sorted_run_results = sorted(((username, int(points)) for username, points in run_ledger.items()), key=lambda x: x[1], reverse=True)
                limited_run_results = sorted_run_results[:get_chat_max_names()]

                if limited_run_results:
                    redact_survivors = is_chat_response_enabled("chat_tilt_redact_survivor_names")
                    if redact_survivors:
                        standings_items = [f"Redacted #{idx} - {points} points" for idx, (_, points) in enumerate(limited_run_results, start=1)]
                    else:
                        standings_items = [f"{username} - {points} points" for username, points in limited_run_results]
                    chunks = chunked_join_messages(
                        "🏁 Tilt run complete! Final standings: ",
                        "🏁 Run standings cont: ",
                        standings_items,
                        max_length=max_message_length
                    )
                    for chunk in chunks:
                        if is_chat_response_enabled("chat_tilt_results") and not should_suppress_tilt_chat:
                            await send_chat_message(bot.channel, chunk, category="tilt")
                    text_area.insert('end', f"\nTilt run complete! Final standings: {', '.join(standings_items)}\n")
                    show_windows_toast("MyStats Tilt", f"Tilt run complete. Top player: {limited_run_results[0][0]}")
                else:
                    if is_chat_response_enabled("chat_tilt_results") and not should_suppress_tilt_chat:
                        await send_chat_message(bot.channel, "🏁 Tilt run complete! No results to display.", category="tilt")
                    text_area.insert('end', f"\nTilt run complete! No results to display.\n")
                    show_windows_toast("MyStats Tilt", "Tilt run complete. No standings were available.")

                participants_with_points = sorted(
                    ((str(name), _safe_int(points)) for name, points in run_ledger.items() if _safe_int(points) > 0),
                    key=lambda x: x[1],
                    reverse=True
                )
                top_users_today = participants_with_points[:10]
                top_user_names = [name for name, _ in top_users_today]
                write_tilt_output_files({
                    'CurrentLevel.txt': 'FAIL',
                    'PreviousRunExpertise.txt': f"{run_xp:,}",
                    'BestRunXPToday.txt': f"{best_run_xp_today:,}",
                    'Top10Horizontal.txt': ', '.join(top_user_names),
                    'TotalExpertiseToday.txt': f"{total_xp_today:,}",
                    'TotalDeathsToday.txt': f"{total_deaths_today:,}",
                    'TotalExpertise.txt': f"{lifetime_expertise:,}"
                })
                output_dir = get_tilt_output_directory()
                with open(os.path.join(output_dir, 'Top10Today.txt'), 'w', encoding='utf-8', errors='ignore') as fp:
                    for name in top_user_names:
                        fp.write(f"{name}\n")

                last_run_summary = {
                    'run_id': run_id,
                    'run_short_id': run_id[:6] if run_id else '',
                    'ended_at': get_internal_adjusted_time().strftime('%Y-%m-%d %H:%M:%S'),
                    'ended_level': current_level,
                    'elapsed_time': elapsed_time,
                    'total_time': format_tilt_duration(run_total_seconds),
                    'run_total_seconds': run_total_seconds,
                    'top_tiltee': top_tiltee,
                    'top_tiltee_count': get_int_setting('tilt_current_top_tiltee_count', 0),
                    'leader': {'name': participants_with_points[0][0], 'points': int(participants_with_points[0][1])} if participants_with_points else None,
                    'run_points': run_points,
                    'run_deaths': run_deaths_total,
                    'run_xp': run_xp,
                    'run_expertise': run_xp,
                    'best_run_xp_today': best_run_xp_today,
                    'total_xp_today': total_xp_today,
                    'total_deaths_today': total_deaths_today,
                    'standings': [
                        {
                            'name': name,
                            'points': int(points),
                            'deaths': _safe_int(run_deaths_ledger.get(name, 0)),
                        }
                        for name, points in participants_with_points
                    ],
                }
                set_tilt_runtime_setting('tilt_last_run_summary', json.dumps(last_run_summary))
                set_tilt_runtime_setting('tilt_run_completion_overlay', json.dumps(last_run_summary))
                next_run_completion_event_id = get_int_setting('tilt_run_completion_event_id', 0) + 1
                set_tilt_runtime_setting('tilt_run_completion_event_id', str(next_run_completion_event_id))

                set_tilt_runtime_setting('tilt_previous_run_xp', str(run_xp))
                set_tilt_runtime_setting('tilt_current_run_id', '')
                set_tilt_runtime_setting('tilt_run_xp', '0')
                set_tilt_runtime_setting('tilt_run_points', '0')
                set_tilt_runtime_setting('tilt_run_deaths_total', '0')
                set_tilt_runtime_setting('tilt_run_total_seconds', '0')
                set_tilt_runtime_setting('tilt_run_ledger', '{}')
                set_tilt_runtime_setting('tilt_run_deaths_ledger', '{}')
                set_tilt_runtime_setting('tilt_top_tiltee_ledger', '{}')
                set_tilt_runtime_setting('tilt_current_top_tiltee_count', '0')
                set_tilt_runtime_setting('tilt_level_completion_overlay', '{}')
                run_id = str(config.get_setting('tilt_current_run_id') or '').strip() or None
                current_tilt_points_leader = None

            last_modified_tilt = current_modified_tilt
            last_tilt_processed_at = time.monotonic()
        except Exception as e:
            logger.error("An error occurred while processing the tilt file", exc_info=True)
            last_modified_tilt = current_modified_tilt
            last_tilt_processed_at = time.monotonic()

        await asyncio.sleep(7)


async def checkpoints(bot):
    last_modified_checkpoint = None
    totalpointsrace = 0

    # Ensure text_area and root are accessible in this scope
    # You might need to pass them as parameters or define them globally
    global text_area, root

    def insert_colored_text(text_area, text):
        # Since this function interacts with Tkinter widgets, it must be called in the main thread
        if text_area and text_area.winfo_exists():
            text_area.insert(tk.END, text)
            text_area.see(tk.END)

    while not bot.stop_event.is_set():
        # print('Debug: Checkpoints file check')
        try:
            # Use asyncio.to_thread to avoid blocking the event loop
            current_modified_checkpoint = await asyncio.to_thread(
                os.path.getmtime, config.get_setting('checkpoint_file')
            )

            if last_modified_checkpoint is None:
                last_modified_checkpoint = current_modified_checkpoint
                print("Checkpoint monitoring initiated. System is ready to go!")
                continue

            if current_modified_checkpoint != last_modified_checkpoint:
                checkpointdata = []
                last_modified_checkpoint = current_modified_checkpoint
                event_ids_tmp = config.get_setting('active_event_ids')

                if event_ids_tmp is not None:
                    event_ids_tmp = event_ids_tmp.strip("[]").split(",")
                    event_ids = [
                        int(id.strip().replace('"', '')) for id in event_ids_tmp
                        if id.strip().replace('"', '').isdigit()
                    ]
                else:
                    event_ids = [0]

                await asyncio.sleep(3)  # Adjust sleep time as needed

                # Read the file data in a separate thread
                data = await asyncio.to_thread(read_binary_file, config.get_setting('checkpoint_file'))

                # Detect encoding
                result = chardet.detect(data)
                encoding = result['encoding']

                def parse_checkpoint_players(checkpoint_file_path, detected_encoding):
                    with open(checkpoint_file_path, 'r', encoding=detected_encoding, errors='ignore', newline='') as checkpoint_file:
                        reader = iter_csv_rows(checkpoint_file)
                        rows = list(reader)

                    if len(rows) <= 1:
                        return []

                    seen_rows = set()
                    cleaned_rows = []

                    for row in rows[1:]:
                        if not row:
                            continue

                        # Normalize empty trailing columns for stable de-duplication.
                        normalized = tuple(cell.strip() for cell in row)
                        if normalized in seen_rows:
                            continue
                        seen_rows.add(normalized)

                        cleaned_rows.append(row)

                    def checkpoint_sort_key(row):
                        checkpoint_value = row[0].strip() if row and len(row) > 0 else ''
                        try:
                            return (0, int(checkpoint_value))
                        except ValueError:
                            return (1, checkpoint_value)

                    cleaned_rows.sort(key=checkpoint_sort_key)
                    return cleaned_rows

                checkpointplayers = await asyncio.to_thread(
                    parse_checkpoint_players,
                    config.get_setting('checkpoint_file'),
                    encoding,
                )

                if not checkpointplayers:
                    continue
                max_names = get_chat_max_names()
                checkpointplayers = checkpointplayers[:max_names]

                # Concatenated messages
                concatenated_message = ""
                concatenated_text_area_message = ""

                # Process each player
                for player in checkpointplayers:
                    if not player or len(player) < 3 or str(player[0]).strip() == '':
                        break  # Stop processing if an empty row is encountered

                    checkpoint = player[0]
                    name = player[1]
                    checkpoint_row = [checkpoint, name, player[2], player[3], event_ids]

                    concatenated_message += f"{checkpoint} - {player[2]}, "
                    concatenated_text_area_message += f"{checkpoint} - {player[2]}, "

                    checkpointdata.append(checkpoint_row)

                # Remove trailing comma and space
                concatenated_message = concatenated_message.rstrip(', ')
                concatenated_text_area_message = concatenated_text_area_message.rstrip(', ')

                # Prepend header
                concatenated_message = f"Checkpoint Winners: {concatenated_message}"
                concatenated_text_area_message = f"\nCheckpoint Winners: {concatenated_text_area_message}"

                # Send the message to Twitch chat
                if concatenated_message:
                    await send_chat_message(bot.channel, concatenated_message, category="race")

                # Update the Tkinter text_area in the main thread
                if concatenated_text_area_message:
                    root.after(0, insert_colored_text, text_area, concatenated_text_area_message + "\n")

                # Append the processed data to the results file
                await asyncio.to_thread(
                    append_to_csv,
                    config.get_setting('checkpoint_results_file'),
                    checkpointdata
                )
            else:
                await asyncio.sleep(7)  # Adjust sleep time as needed

        except asyncio.CancelledError:
            print("Checkpoints task was cancelled.")
            break  # Exit the loop gracefully

        except FileNotFoundError:
            await asyncio.sleep(5)  # Wait before retrying
            continue

        except Exception as e:
            logger.error("Error in checkpoints task", exc_info=True)
            # Optionally log the exception or take other actions
            await asyncio.sleep(5)  # Prevent tight loop on error

    print("Checkpoints task has exited.")

# Helper functions
def read_binary_file(file_path):
    with open(file_path, 'rb') as f:
        return f.read()

def append_to_csv(file_path, data):
    with open(file_path, 'a', newline='', encoding='utf-8', errors='ignore') as f:
        writer = csv.writer(f)
        writer.writerows(data)


def _parse_mos_date(raw_value):
    value = (raw_value or '').strip().strip('"')
    if not value:
        return None

    for date_format in ('%Y-%m-%dT%H:%M:%S.%fZ', '%Y.%m.%d-%H.%M.%S'):
        try:
            return datetime.strptime(value, date_format).date()
        except ValueError:
            continue
    return None


def read_latest_map_data(map_data_file):
    with open(map_data_file, 'rb') as f:
        map_data = f.read()

    encoding_result = chardet.detect(map_data)
    map_encoding = encoding_result['encoding'] or 'utf-8'
    map_text = map_data.decode(map_encoding, errors='ignore')

    sample = '\n'.join(map_text.splitlines()[:3])
    delimiter = ','
    try:
        sniffed = csv.Sniffer().sniff(sample, delimiters=',\t;')
        delimiter = sniffed.delimiter
    except csv.Error:
        if '\t' in sample:
            delimiter = '\t'

    reader = csv.DictReader(io.StringIO(map_text), delimiter=delimiter)
    first_row = next(reader, None)
    if not first_row:
        return None

    map_name = (first_row.get('MapName') or '').strip()
    map_builder = (first_row.get('CreatorName') or '').strip()

    try:
        play_count = int(float((first_row.get('TotalRaces') or '0').strip() or 0))
    except ValueError:
        play_count = 0

    try:
        elim_rate = float((first_row.get('ElimRate') or '0').strip() or 0)
    except ValueError:
        elim_rate = 0.0

    try:
        avg_finish_time = float((first_row.get('AverageFinishTime') or '0').strip() or 0)
    except ValueError:
        avg_finish_time = 0.0

    try:
        record_time = float((first_row.get('RecordTime') or '0').strip() or 0)
    except ValueError:
        record_time = 0.0

    return {
        'MapName': map_name,
        'MapBuilder': map_builder,
        'MapCreatedDate': _parse_mos_date(first_row.get('DateCreated')),
        'PlayCount': play_count,
        'ElimRate': elim_rate,
        'AvgFinishTime': avg_finish_time,
        'RecordTime': record_time,
        'RecordHolder': (first_row.get('RecordHolderName') or '').strip() or None,
        'RecordSetDate': _parse_mos_date(first_row.get('DateSet')),
        'RecordStreamer': (first_row.get('StreamerRecordHolder') or '').strip() or None,
    }


async def race(bot):
    last_modified_race = None
    last_map_file_mod_time = None
    totalpointsrace = 0
    current_daily_points_leader = None
    last_narrative_alert_race_count = 0
    cached_map_data = {
        'MapName': None,
        'MapBuilder': None,
        'MapCreatedDate': None,
        'PlayCount': 0,
        'ElimRate': 0.0,
        'AvgFinishTime': 0.0,
        'RecordTime': 0.0,
        'RecordHolder': None,
        'RecordSetDate': None,
        'RecordStreamer': None,
    }
    while True:
        try:
            current_modified_race = await asyncio.to_thread(os.path.getmtime, config.get_setting('race_file'))
        except FileNotFoundError:
            continue

        if last_modified_race is None:
            last_modified_race = current_modified_race
            print("Race monitoring initiated. System is ready to go!")
            continue

        timestamp, timestampMDY, timestampHMS, adjusted_time = time_manager.get_adjusted_time()

        if config.get_setting('marble_day') != timestampMDY:
            print()
            print("Marble Day Reset Is Upon Us!")
            print()
            if is_chat_response_enabled("chat_race_results"):
                await send_chat_message(bot.channel, "🎺 Marble Day Reset! 🎺", category="race")
            current_daily_points_leader = None
            last_narrative_alert_race_count = 0
            config.set_setting('data_sync', 'yes', persistent=False)
            await asyncio.sleep(3)
            reset()

        if current_modified_race != last_modified_race:
            set_overlay_mode('race')
            await asyncio.sleep(3)
            racedata = []
            namecolordata = []
            config.set_setting('wr', 'no', persistent=False)
            last_modified_race = current_modified_race
            t_points = int(config.get_setting('totalpointstoday'))
            t_count = int(config.get_setting('totalcounttoday'))
            s_t_points = int(config.get_setting('totalpointsseason'))
            s_t_count = int(config.get_setting('totalcountseason'))

            # Step 1: Process the map file only if the modification time has changed
            map_data_file = config.get_setting('map_data_file')
            map_results_file = config.get_setting('map_results_file')

            try:
                # Get the current modification time of the map file
                current_mod_time = os.path.getmtime(map_data_file)

                # Only process the map file if it has been modified since the last read
                if last_map_file_mod_time is None or current_mod_time > last_map_file_mod_time:
                    last_map_file_mod_time = current_mod_time  # Update the last modification time

                    parsed_map_data = read_latest_map_data(map_data_file)
                    if parsed_map_data:
                        cached_map_data.update(parsed_map_data)
                        with open(map_results_file, 'a', encoding='utf-8', errors='ignore', newline='') as f:
                            f.write(
                                f"{cached_map_data['MapName']},{cached_map_data['MapBuilder']},{cached_map_data['MapCreatedDate']},"
                                f"{cached_map_data['PlayCount']},{cached_map_data['ElimRate']},{cached_map_data['AvgFinishTime']},"
                                f"{cached_map_data['RecordTime']},{cached_map_data['RecordHolder']},{cached_map_data['RecordSetDate']},"
                                f"{cached_map_data['RecordStreamer']}\n")
                    else:
                        print(f"The map data file {map_data_file} does not contain enough data.")
                else:
                    pass

            except FileNotFoundError:
                print(f"Map data file {map_data_file} not found.")
            except Exception as e:
                logger.error("An error occurred while processing the map data file", exc_info=True)

            MapName = cached_map_data['MapName']
            MapBuilder = cached_map_data['MapBuilder']
            MapCreatedDate = cached_map_data['MapCreatedDate']
            PlayCount = cached_map_data['PlayCount']
            ElimRate = cached_map_data['ElimRate']
            AvgFinishTime = cached_map_data['AvgFinishTime']
            RecordTime = cached_map_data['RecordTime']
            RecordHolder = cached_map_data['RecordHolder']
            RecordSetDate = cached_map_data['RecordSetDate']
            RecordStreamer = cached_map_data['RecordStreamer']

            with open(config.get_setting('race_file'), 'rb') as f:
                data = f.read()

            result = chardet.detect(data)
            encoding = result['encoding']

            with open(config.get_setting('race_file'), 'r', encoding=encoding, errors='ignore') as f:
                lines = f.readlines()

            if all(line.split(',')[6].strip() == 'true' for line in lines[1:]):
                nowinner = True
            else:
                nowinner = False

            marbcount = len(lines) - 1
            event_ids_tmp = config.get_setting('active_event_ids')

            if event_ids_tmp is not None:
                event_ids_tmp = event_ids_tmp.strip("[]").split(",")
                event_ids = [int(id.strip().replace('"', '')) for id in event_ids_tmp if
                             id.strip().replace('"', '').isdigit()]
            else:
                event_ids = [0]

            # Step 3: Comparison between race finish time and record time
            first_row_full = lines[1].replace('\x00', '').strip().split(',')
            race_finish_time = float(first_row_full[5])

            if RecordTime and race_finish_time < RecordTime:
                RecordAmount = RecordTime - race_finish_time
                minutes, seconds = divmod(RecordAmount, 60)
                pminutes, pseconds = divmod(RecordTime, 60)
                cminutes, cseconds = divmod(race_finish_time, 60)

                formatted_RecordAmount = f"{int(minutes):02d}:{seconds:06.3f}"
                formatted_PreviousRecord = f"{int(pminutes):02d}:{pseconds:06.3f}"
                formatted_CurrentTime = f"{int(cminutes):02d}:{cseconds:06.3f}"

                print(f"\nRecord Broken by: {formatted_RecordAmount}")
                print(f"Previous Record: {formatted_PreviousRecord}")
                print(f"Current Race Time: {formatted_CurrentTime}")

                config.set_setting('wr', 'yes', persistent=False)
                show_windows_toast(
                    "MyStats World Record",
                    f"New WR by {first_row_full[2]}: {formatted_CurrentTime} (saved {formatted_RecordAmount})"
                )
            else:
                config.set_setting('wr', 'no', persistent=False)

            # first row with WR flagged
            if config.get_setting('wr').lower() == 'yes':
                first_row = [first_row_full[0], first_row_full[1], first_row_full[2], first_row_full[4], 'Race',
                             timestamp, marbcount, first_row_full[6], 0, 0, event_ids, 1]
            else:
                first_row = [first_row_full[0], first_row_full[1], first_row_full[2], first_row_full[4], 'Race',
                             timestamp, marbcount, first_row_full[6], 0, 0, event_ids, 0]

            first_row_color = lines[1].replace('\x00', '').strip().split(',')

            racedata.append(first_row)
            namecolordata.append(first_row_color)

            t_points += int(first_row_full[4])
            t_count += 1
            s_t_points += int(first_row_full[4])
            s_t_count += 1
            totalpointsrace += int(first_row_full[4])

            # Process remaining lines
            for line in lines[2:]:
                cleaned_line = line.replace('\x00', '').strip().split(',')
                row = [cleaned_line[0], cleaned_line[1], cleaned_line[2], cleaned_line[4], 'Race', timestamp, marbcount,
                       cleaned_line[6], 0, 0, event_ids, 0]
                color_row = cleaned_line

                racedata.append(row)
                namecolordata.append(color_row)

                t_points += int(row[3])
                totalpointsrace += int(row[3])
                s_t_points += int(row[3])

            append_csv_rows_safely(config.get_setting('allraces_file'), racedata)

            _record_live_team_points_rows(config.get_setting('CHANNEL'), racedata)

            if DEBUG == True:
                print('Debug: Write Race Data to Data File')
            else:
                pass
            logger.info("Data synced: race results written to allraces file")

            race_counts = {row[1]: 0 for row in racedata}
            points_by_player = {}
            wins_by_player = {}
            with open(config.get_setting('allraces_file'), 'r', encoding='utf-8', errors='ignore') as f:
                reader = iter_csv_rows(f)
                for row in reader:
                    if len(row) < 4:
                        continue
                    racer_username = row[1]
                    if racer_username in race_counts:
                        race_counts[racer_username] += 1
                    if len(row) > 0 and row[0] == '1':
                        wins_by_player[racer_username] = wins_by_player.get(racer_username, 0) + 1
                    try:
                        racer_points = int(row[3])
                    except ValueError:
                        continue
                    points_by_player[racer_username] = points_by_player.get(racer_username, 0) + racer_points

            for player_name, count in race_counts.items():
                if count == 120:
                    announcement_message = (
                        f"🎉 {player_name} has just completed their "
                        f"120th race today! Congratulations! 🎉"
                    )
                    if is_chat_response_enabled("chat_race_results"):
                        await send_chat_message(bot.channel, announcement_message, category="race")

            # MPL Code
            if config.get_setting('MPL') == 'True':
                checkpointdata = []
                with open(config.get_setting('checkpoint_file'), 'r', encoding='utf-8', errors='ignore') as f:
                    checkpointfile = iter_csv_rows(f)
                    for row in checkpointfile:
                        checkpointdata.append(row)

                scope = ['https://spreadsheets.google.com/feeds',
                         'https://www.googleapis.com/auth/drive']
                credentials = ServiceAccountCredentials.from_json_keyfile_name('meta-data-tracking.json', scope)
                client = gspread.authorize(credentials)
                spreadsheet_name = 'MPL Tracking Sheet'

                try:
                    spreadsheet = client.open(spreadsheet_name)
                except SpreadsheetNotFound:
                    print(f"Spreadsheet '{spreadsheet_name}' not found. Creating new one.")
                    spreadsheet = client.create(spreadsheet_name)
                    personal_email = 'camdizzle@gmail.com'
                    spreadsheet.share(personal_email, perm_type='user', role='writer')

                worksheet_name = config.get_setting("CHANNEL")

                try:
                    worksheet = spreadsheet.worksheet(worksheet_name)
                except WorksheetNotFound:
                    print(
                        f"Worksheet '{worksheet_name}' not found in spreadsheet '{spreadsheet_name}'. Creating new one.")
                    worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows='100', cols='20')

                top_five_finishers = [record for record in racedata if int(record[0]) in [1, 2, 3, 4, 5]]
                for finisher in top_five_finishers:
                    placement, name = finisher[0], finisher[1]
                    row_to_append = [name, placement, config.get_setting('MPLWeek'), config.get_setting('MPLSeason')]
                    worksheet.append_row(row_to_append)

                for players in checkpointdata:
                    placement, name = players[0], players[1]
                    row_to_append = [name, placement, config.get_setting('MPLWeek'), config.get_setting('MPLSeason')]
                    worksheet.append_row(row_to_append)

            # Chunk Alert Code
            if int(first_row[3]) >= int(config.get_setting('chunk_alert_value')) and config.get_setting('chunk_alert') == 'True':
                audio_device = config.get_setting('audio_device')
                audio_file_path = config.get_setting('chunk_alert_sound')

                if audio_file_path:
                    play_audio_file(audio_file_path, device_name=audio_device)

            if first_row[1] != first_row[2].lower():
                winnersname = first_row[1]
            else:
                winnersname = first_row[2]

            current_score = int(first_row[3])

            if current_score > int(config.get_setting('hscore')):
                config.set_setting('hscore_name', winnersname, persistent=False)
                config.set_setting('hscore', current_score, persistent=False)
                br_hscore = int(config.get_setting('hscore'))
                br_hscore_format = format(br_hscore, ',')
                with open(appdata_path('HighScore.txt'), 'w', encoding='utf-8', errors='ignore') as hs:
                    hs.write(str(config.get_setting('hscore_name')) + '\n')
                    hs.write(str(br_hscore_format + '\n'))

            if current_score > int(config.get_setting('race_hs_season')):
                config.set_setting('race_hs_season', current_score, persistent=False)

            if current_score > int(config.get_setting('race_hs_today')):
                config.set_setting('race_hs_today', current_score, persistent=False)

            # Write last winners
            lastwinner1 = ""
            lastwinnerh = ""

            for i in range(len(racedata)):
                place = racedata[i][0]
                lastwinner1 += "{} {} {} point{} \n".format("(" + str(place) + ")", racedata[i][2], racedata[i][3],
                                                         "s" if int(racedata[i][3]) != 1 else "")
                lastwinnerh += "{} {} {} point{}".format("(" + str(place) + ")", racedata[i][2], racedata[i][3],
                                                         "s" if int(racedata[i][3]) != 1 else "")

            with open(appdata_path('LatestWinner.txt'), 'w', encoding='utf-8', errors='replace') as lw:
                lw.write("Previous Winners:" + '\n')
                lw.write(lastwinner1 + '\n')

            with open(appdata_path('LatestWinner_horizontal.txt'), 'w', encoding='utf-8', errors='replace') as lwh:
                lwh.write("Previous Winners:" + lastwinnerh)

            logger.info("Data synced: race latest winner files updated")

            config.set_setting('totalpointstoday', t_points, persistent=False)
            config.set_setting('totalcounttoday', t_count, persistent=False)
            config.set_setting('totalpointsseason', s_t_points, persistent=False)
            config.set_setting('totalcountseason', s_t_count, persistent=False)
            update_config_labels()

            t_count_today = int(config.get_setting('totalcounttoday'))
            if t_count_today > 0:
                avgptstoday = int(config.get_setting('totalpointstoday')) / t_count_today
            else:
                avgptstoday = 0

            config.set_setting('avgpointstoday', avgptstoday, persistent=False)

            # Add color tags for the text widget
            def add_color_tag(widget, tag_name, color):
                try:
                    widget.tag_configure(tag_name, foreground=color)
                except tk.TclError as e:
                    print(f"Error configuring color {color}: {e}")
                    widget.tag_configure(tag_name, foreground="white")

            def insert_colored_text(text_widget, text, tag_name):
                text_widget.insert(tk.END, text, tag_name)

            def display_race_winners(text_widget, marbcount, namecolordata, nowinner):
                add_color_tag(text_widget, "cyan", "cyan")
                add_color_tag(text_widget, "yellow", "yellow")
                add_color_tag(text_widget, "white", "white")
                add_color_tag(text_widget, "green", "green")
                add_color_tag(text_widget, "blue", "blue")
                add_color_tag(text_widget, "magenta", "magenta")
                add_color_tag(text_widget, "violet", "violet")
                add_color_tag(text_widget, "red", "red")
                add_color_tag(text_widget, "orange", "orange")

                if nowinner:
                    text_widget.insert(tk.END, "\nRace Winners: (", "white")
                    text_widget.insert(tk.END, f"{marbcount}", "yellow")
                    text_widget.insert(tk.END, ") No Winners!\n", "white")
                    return

                # Filter for racers who earned points
                filtered_data = [item for item in namecolordata if int(item[4]) > 0]

                # Check if there are no racers with points
                if not filtered_data:
                    # No racers earned points, show top 10 finishers regardless of points
                    filtered_top10_data = [item for item in namecolordata if item[6] == 'false'][:10]
                    text_widget.insert(tk.END, "\nTop 10 Finishers: ", "white")
                    text_widget.insert(tk.END, f"({marbcount})", "yellow")

                    for i, data in enumerate(filtered_top10_data):
                        wname = data[1] if data[1] != data[2].lower() else data[2]
                        place = i + 1

                        if data[3] == '6E95FFFF':
                            namecolor = "blue"
                        elif data[3] == 'F91ED2FF':
                            namecolor = "magenta"
                        elif data[3] == 'FF82D6FF':
                            namecolor = "violet"
                        elif data[3] == '79FFC7FF':
                            namecolor = "green"
                        elif data[3] == 'F88688FF':
                            namecolor = "red"
                        elif data[3] == 'DA6700FF':
                            namecolor = "orange"
                        else:
                            namecolor = "white"

                        insert_colored_text(text_widget, f"({place}) ", "cyan")
                        insert_colored_text(text_widget, wname, namecolor)

                        if i < len(filtered_top10_data) - 1:
                            insert_colored_text(text_widget, ", ", "white")
                        else:
                            insert_colored_text(text_widget, ".\n", "white")

                    text_widget.see(tk.END)
                    return

                # If some racers have points, display them
                if config.get_setting('wr').lower() == 'yes':
                    message = "WORLD RECORD!!: "
                    text_widget.insert(tk.END, f"\n{message}", "yellow")
                    text_widget.insert(tk.END, f"(", "white")
                    text_widget.insert(tk.END, f"{marbcount}", "yellow")  # marbcount in yellow
                    text_widget.insert(tk.END, f") ", "white")
                else:
                    message = "Race Winners: "
                    text_widget.insert(tk.END, f"\n{message}", "white")
                    text_widget.insert(tk.END, f"(", "white")
                    text_widget.insert(tk.END, f"{marbcount}", "yellow")  # marbcount in yellow
                    text_widget.insert(tk.END, f") ", "white")

                for i, data in enumerate(filtered_data):
                    wname = data[1] if data[1] != data[2].lower() else data[2]
                    place = i + 1

                    if data[3] == '6E95FFFF':
                        namecolor = "blue"
                    elif data[3] == 'F91ED2FF':
                        namecolor = "magenta"
                    elif data[3] == 'FF82D6FF':
                        namecolor = "violet"
                    elif data[3] == '79FFC7FF':
                        namecolor = "green"
                    elif data[3] == 'F88688FF':
                        namecolor = "red"
                    elif data[3] == 'DA6700FF':
                        namecolor = "orange"
                    else:
                        namecolor = "white"

                    insert_colored_text(text_widget, f"({place}) ", "cyan")
                    insert_colored_text(text_widget, wname, namecolor)
                    insert_colored_text(text_widget, f" {data[4]} ", "white")
                    insert_colored_text(text_widget, "points" if int(data[4]) > 1 else "point", "white")

                    if i < len(filtered_data) - 1:
                        insert_colored_text(text_widget, ", ", "white")
                    else:
                        insert_colored_text(text_widget, ".\n", "white")

                text_widget.see(tk.END)

            # Display in text_area
            display_race_winners(text_area, marbcount, namecolordata, nowinner)

            # Prepare messages for Twitch chat
            messages = []

            narrative_messages = []
            if not nowinner and is_chat_response_enabled("race_narrative_alerts_enabled"):
                winner_username = first_row[1]
                winner_display_name = first_row[2] if first_row[1] != first_row[2].lower() else first_row[1]

                if is_chat_response_enabled("race_narrative_grinder_enabled"):
                    winner_race_count = race_counts.get(winner_username, 0)
                    if winner_race_count in (10, 25, 50, 75, 100):
                        narrative_messages.append(
                            f"🏁 Grinder: {winner_display_name} hit race #{winner_race_count} today"
                        )

                if is_chat_response_enabled("race_narrative_winmilestone_enabled"):
                    winner_win_count = wins_by_player.get(winner_username, 0)
                    if winner_win_count in (3, 5, 10, 15):
                        narrative_messages.append(
                            f"🏆 Win Milestone: {winner_display_name} reached win #{winner_win_count} today"
                        )

                if is_chat_response_enabled("race_narrative_leadchange_enabled") and points_by_player:
                    sorted_points = sorted(points_by_player.items(), key=lambda item: item[1], reverse=True)
                    leader_username, leader_points = sorted_points[0]
                    second_place_points = sorted_points[1][1] if len(sorted_points) > 1 else 0
                    lead_gap = leader_points - second_place_points
                    min_lead_gap = max(0, get_int_setting("race_narrative_alert_min_lead_change_points", 500))
                    tied_for_lead = len(sorted_points) > 1 and second_place_points == leader_points
                    if (not tied_for_lead and leader_username != current_daily_points_leader
                            and lead_gap >= min_lead_gap):
                        current_daily_points_leader = leader_username
                        leader_display_name = next(
                            (row[2] for row in namecolordata if row[1] == leader_username and row[2]),
                            leader_username
                        )
                        narrative_messages.append(
                            f"📈 Lead Change: {leader_display_name} now leads by {lead_gap:,} points"
                        )

            if narrative_messages:
                cooldown_races = max(0, get_int_setting("race_narrative_alert_cooldown_races", 3))
                max_items = max(1, get_int_setting("race_narrative_alert_max_items", 3))
                if cooldown_races == 0 or (t_count - last_narrative_alert_race_count) >= cooldown_races:
                    combined_narrative = "📣 Player Alerts: " + " | ".join(narrative_messages[:max_items]) + "."
                    messages.append(combined_narrative)
                    enqueue_overlay_event('player_alert', combined_narrative)
                    last_narrative_alert_race_count = t_count

            # --- CHUNK ALERT BLOCK ---
            if int(first_row[3]) >= int(config.get_setting('chunk_alert_value')) and config.get_setting('chunk_alert') == 'True':
                if DEBUG:
                    print('Debug: Chunk Alert True')

                if nowinner:
                    message = "Race Winners 🏆: No Winners!"
                    messages.append(message)
                else:
                    # Filter data for racers who earned points
                    filtered_data = [item for item in namecolordata if int(item[4]) > 0]

                    # If no racers earned points, display the top 10 finishers
                    if not filtered_data:
                        filtered_top10_data = namecolordata[:10]
                        if config.get_setting('wr') == 'yes':
                            message = "🧃 WORLD RECORD 🌎"
                        else:
                            message = "🧃 Top 10 Finishers 🏆: "

                        # We'll build `message` in a loop. If adding a name exceeds 480, start a new message.
                        temp_messages = []
                        for i, data in enumerate(filtered_top10_data):
                            winner_name = data[1] if data[1] != data[2].lower() else data[2]
                            line = f"{format_ranked_label(int(data[0]))} {winner_name}"
                            if i < len(filtered_top10_data) - 1:
                                line += " | "

                            # Check the length before appending
                            if len(message + line) > 480:
                                temp_messages.append(message.rstrip(' | '))
                                # Start a new message with the same prefix (or some short prefix, your choice)
                                message = "🧃 Top 10 Finishers 🏆: " + line
                            else:
                                message += line

                        # Append the last chunk
                        temp_messages.append(message.rstrip(' | '))
                        messages.extend(temp_messages)

                    else:
                        # We have some racers with points
                        if config.get_setting('wr') == 'yes':
                            prefix = "🧃 🌎 WORLD RECORD 🌎:"
                        else:
                            prefix = "🧃 Race Winners 🏆: "
                        message = prefix

                        temp_messages = []
                        for i, data in enumerate(filtered_data):  # Show only top 10 with points in Twitch chat
                            winner_name = data[1] if data[1] != data[2].lower() else data[2]
                            formatted_points = '{:,}'.format(int(data[4]))
                            line = f"{format_ranked_label(int(data[0]))} {winner_name} +{formatted_points} {pluralize(int(data[4]), 'point')}"
                            if i < len(filtered_data) - 1:
                                line += " | "

                            # Check length before appending
                            if len(message + line) > 480:
                                temp_messages.append(message.rstrip(' | '))
                                message = prefix + line  # Start fresh with the same prefix
                            else:
                                message += line

                        temp_messages.append(message.rstrip(' | '))
                        messages.extend(temp_messages)

            # --- NON-CHUNK ALERT BLOCK ---
            else:
                if nowinner:
                    message = "Race Winners 🏆: No Winners!"
                    messages.append(message)
                else:
                    filtered_data = [item for item in namecolordata if int(item[4]) > 0]

                    # If no racers earned points, show top 10
                    if not filtered_data:
                        filtered_top10_data = namecolordata[:10]
                        if config.get_setting('wr') == 'yes':
                            message = "WORLD RECORD 🌎"
                        else:
                            message = "Top 10 Finishers 🏆: "

                        temp_messages = []
                        for i, data in enumerate(filtered_top10_data):
                            winner_name = data[1] if data[1] != data[2].lower() else data[2]
                            line = f"{format_ranked_label(int(data[0]))} {winner_name}"
                            if i < len(filtered_top10_data) - 1:
                                line += " | "

                            if len(message + line) > 480:
                                temp_messages.append(message.rstrip(' | '))
                                message = "Top 10 Finishers 🏆: " + line
                            else:
                                message += line

                        temp_messages.append(message.rstrip(' | '))
                        messages.extend(temp_messages)

                    else:
                        # Some racers have points
                        if config.get_setting('wr') == 'yes':
                            prefix = "🌎 WORLD RECORD 🌎:"
                        else:
                            prefix = "Race Winners 🏆: "
                        message = prefix

                        temp_messages = []
                        for i, data in enumerate(filtered_data):
                            winner_name = data[1] if data[1] != data[2].lower() else data[2]
                            formatted_points = '{:,}'.format(int(data[4]))
                            line = f"{format_ranked_label(int(data[0]))} {winner_name} +{formatted_points} {pluralize(int(data[4]), 'point')}"
                            if i < len(filtered_data) - 1:
                                line += " | "

                            if len(message + line) > 480:
                                temp_messages.append(message.rstrip(' | '))
                                message = prefix + line
                            else:
                                message += line

                        temp_messages.append(message.rstrip(' | '))
                        messages.extend(temp_messages)


            # ---- After building up messages, do config updates, etc. ----
            config.set_setting('totalpointstoday', t_points, persistent=False)
            config.set_setting('totalcounttoday', t_count, persistent=False)
            config.set_setting('totalpointsseason', s_t_points, persistent=False)
            config.set_setting('totalcountseason', s_t_count, persistent=False)

            t_count_today = int(config.get_setting('totalcounttoday'))
            if t_count_today > 0:
                avgptstoday = int(config.get_setting('totalpointstoday')) / t_count_today
            else:
                avgptstoday = 0

            config.set_setting('avgpointstoday', avgptstoday, persistent=False)

            cycle_events = update_mycycle_with_race_rows(racedata)
            if is_chat_response_enabled('mycycle_announcements_enabled'):
                for event in cycle_events:
                    cycle_message = (
                        f"🔁 {event['display_name']} completed a MyCycle in {event['session_name']}! "
                        f"Cycle #{event['cycles_completed']} took {event['races_used']} races."
                    )
                    messages.append(cycle_message)
                    enqueue_overlay_event('cycle_completed', cycle_message)

            quest_messages = get_season_quest_updates()
            messages.extend(quest_messages)
            for quest_message in quest_messages:
                enqueue_overlay_event('quest_completed', quest_message)

            channel = bot.get_channel(config.get_setting('CHANNEL'))
            if not channel:
                print(f"Could not find channel: {config.get_setting('CHANNEL')}" + " Restart Mystats.")
            else:
                for msg in messages:
                    if DEBUG:
                        print('Debug:', msg)
                    await channel.send(msg)
                    write_overlays()


            # Ensure any further overlays or updates are done last
            
            write_overlays()

        else:
            await asyncio.sleep(7)


async def royale(bot):
    last_modified_royale = None
    marbcount = 0
    br_cache_loaded = False
    br_user_totals = {}

    def add_color_tag(widget, tag_name, color):
        widget.tag_configure(tag_name, foreground=color)

    def insert_colored_text(text_area, text, tag_name):
        text_area.insert(tk.END, text, tag_name)

    def atomic_write_text(path, content, *, errors='ignore'):
        temp_path = f"{path}.tmp"
        with open(temp_path, 'w', encoding='utf-8', errors=errors) as tmp:
            tmp.write(content)
        os.replace(temp_path, path)

    def map_name_color(color_code):
        color_lookup = {
            '6E95FFFF': 'blue',
            'F91ED2FF': 'magenta',
            'FF82D6FF': 'violet',
            '79FFC7FF': 'green',
            'F88688FF': 'red',
            'DA6700FF': 'orange',
        }
        return color_lookup.get(str(color_code).strip().upper(), 'white')

    def resolve_br_identity(br_winner_row):
        winner_login = str(br_winner_row[1] if len(br_winner_row) > 1 else '').strip().lower()
        winner_display = str(br_winner_row[2] if len(br_winner_row) > 2 else '').strip()
        if not winner_display:
            winner_display = winner_login
        if winner_login and winner_login != winner_display.lower():
            winner_label = f"{winner_display}({winner_login})"
        else:
            winner_label = winner_display
        return winner_login, winner_display, winner_label

    def build_br_winner_message(*, crownwin, chunk_alert, winner_label, points, kills, damage, total_points, wins, races):
        prefix = "🧃 " if chunk_alert else ""
        event_text = "CROWN WIN! 👑" if crownwin else "Battle Royale Champion 🏆"
        wins_int = _safe_int(wins)
        races_int = _safe_int(races)
        return (
            f"{prefix}{event_text}: {winner_label} +{points:,} points, +{kills:,} eliminations, +{damage:,} damage | "
            f"Today's stats: {total_points:,} points, {wins_int} {pluralize(wins_int, 'win')}, {races_int:,} {pluralize(races_int, 'race')}"
        )

    def load_br_user_totals_from_allraces():
        totals = {}
        try:
            with open(config.get_setting('allraces_file'), 'r', encoding='utf-8', errors='ignore') as f:
                for row in iter_csv_rows(f):
                    if len(row) < 5:
                        continue
                    username = str(row[1]).strip().lower()
                    if not username:
                        continue
                    entry = totals.setdefault(username, {'points': 0, 'wins': 0, 'races': 0})
                    entry['races'] += 1
                    entry['points'] += _safe_int(row[3])
                    if str(row[0]).strip() == '1':
                        entry['wins'] += 1
        except FileNotFoundError:
            with open(config.get_setting('allraces_file'), 'w', encoding='utf-8', errors='ignore'):
                pass
        except Exception:
            logger.error("An error occurred while loading BR totals cache", exc_info=True)
        return totals

    def update_br_user_totals_cache(rows):
        for row in rows:
            if len(row) < 4:
                continue
            username = str(row[1]).strip().lower()
            if not username:
                continue
            entry = br_user_totals.setdefault(username, {'points': 0, 'wins': 0, 'races': 0})
            entry['races'] += 1
            entry['points'] += _safe_int(row[3])
            if str(row[0]).strip() == '1':
                entry['wins'] += 1

    # Crown Winner Display
    def display_battle_royale_crownwinner(text_area, marbcount, wname, wpoints, wkills, wdam, wcount, winnertotalpoints, namecolor):
        add_color_tag(text_area, "cyan", "cyan")
        add_color_tag(text_area, "yellow", "yellow")
        add_color_tag(text_area, "white", "white")
        add_color_tag(text_area, "green", "green")
        add_color_tag(text_area, "red", "red")
        add_color_tag(text_area, "blue", "blue")
        add_color_tag(text_area, "magenta", "magenta")
        add_color_tag(text_area, "violet", "violet")
        add_color_tag(text_area, "orange", "orange")

        insert_colored_text(text_area, "\n", "white")
        insert_colored_text(text_area, "CROWN WIN! 👑: ", "yellow")
        insert_colored_text(text_area, "(", "white")
        insert_colored_text(text_area, str(marbcount), "yellow")
        insert_colored_text(text_area, ") ", "white")
        insert_colored_text(text_area, wname, namecolor)
        insert_colored_text(text_area, " with ", "white")
        insert_colored_text(text_area, wpoints, "green")
        insert_colored_text(text_area, " points, ", "white")
        insert_colored_text(text_area, wkills, "red")
        insert_colored_text(text_area, " eliminations and ", "white")
        insert_colored_text(text_area, wdam, "red")
        insert_colored_text(text_area, " damage. Total Wins: ", "white")
        insert_colored_text(text_area, str(wcount), "cyan")
        insert_colored_text(text_area, " Points: ", "white")
        insert_colored_text(text_area, '{:,}'.format(int(winnertotalpoints)), "cyan")
        insert_colored_text(text_area, "\n", "white")
        text_area.see(tk.END)

    # Regular Battle Royale Winner Display
    def display_battle_royale_winner(text_area, marbcount, wname, wpoints, wkills, wdam, wcount, winnertotalpoints, namecolor):
        add_color_tag(text_area, "cyan", "cyan")
        add_color_tag(text_area, "yellow", "yellow")
        add_color_tag(text_area, "white", "white")
        add_color_tag(text_area, "green", "green")
        add_color_tag(text_area, "red", "red")
        add_color_tag(text_area, "blue", "blue")
        add_color_tag(text_area, "magenta", "magenta")
        add_color_tag(text_area, "violet", "violet")
        add_color_tag(text_area, "orange", "orange")

        insert_colored_text(text_area, "\n", "white")
        insert_colored_text(text_area, "Battle Royale: (", "white")
        insert_colored_text(text_area, str(marbcount), "yellow")
        insert_colored_text(text_area, ") ", "white")
        insert_colored_text(text_area, wname, namecolor)
        insert_colored_text(text_area, " with ", "white")
        insert_colored_text(text_area, wpoints, "green")
        insert_colored_text(text_area, " points, ", "white")
        insert_colored_text(text_area, wkills, "red")
        insert_colored_text(text_area, " eliminations and ", "white")
        insert_colored_text(text_area, wdam, "red")
        insert_colored_text(text_area, " damage. Total Wins: ", "white")
        insert_colored_text(text_area, str(wcount), "cyan")
        insert_colored_text(text_area, " Points: ", "white")
        insert_colored_text(text_area, '{:,}'.format(int(winnertotalpoints)), "cyan")
        insert_colored_text(text_area, "\n", "white")
        text_area.see(tk.END)

    while True:
        try:
            current_modified_royale = await asyncio.to_thread(os.path.getmtime, config.get_setting('br_file'))
        except FileNotFoundError:
            await asyncio.sleep(2)
            continue
        if last_modified_royale is None:
            last_modified_royale = current_modified_royale
            print("Royale monitoring initiated. System is ready to go!")
            continue

        timestamp, timestampMDY, timestampHMS, adjusted_time = time_manager.get_adjusted_time()

        if current_modified_royale != last_modified_royale:
            set_overlay_mode('br')
            await asyncio.sleep(3)
            brdata = []
            metadata = []
            total = 0
            winner = ''
            crownwin = False
            last_br_winner = config.get_setting('last_br_winner')
            t_points = _safe_int(config.get_setting('totalpointstoday'))
            t_count = _safe_int(config.get_setting('totalcounttoday'))
            s_t_points = _safe_int(config.get_setting('totalpointsseason'))
            s_t_count = _safe_int(config.get_setting('totalcountseason'))
            last_modified_royale = current_modified_royale

            # Initialize br_winner to None before processing
            br_winner = None  # Add this line

            max_retries = 3  # Number of retry attempts
            retry_delay = 2  # Delay between retries (in seconds)
            attempts = 0  # Track the number of attempts
            parsed_rows = None

            while attempts < max_retries:
                try:
                    # First, attempt to open the br_file and read it as binary to detect encoding
                    with open(config.get_setting('br_file'), 'rb') as f:
                        data = f.read()

                    # Detect the file encoding using chardet
                    result = chardet.detect(data)
                    encoding = result['encoding']

                    # Open the file using the detected encoding and parse CSV rows
                    with open(config.get_setting('br_file'), 'r', encoding=encoding, errors='ignore') as f:
                        parsed_rows = list(iter_csv_rows(f))

                    # If file reading is successful, break out of the retry loop
                    break

                except PermissionError as e:
                    attempts += 1
                    logger.warning("Permission denied: %s. Retrying in %s seconds... (Attempt %d/%d)", e, retry_delay, attempts, max_retries)
                    await asyncio.sleep(retry_delay)

                except Exception as e:
                    attempts += 1
                    logger.warning("An error occurred: %s. Retrying in %s seconds... (Attempt %d/%d)", e, retry_delay, attempts, max_retries)
                    await asyncio.sleep(retry_delay)

            # After retry attempts, handle failure if the file could not be opened
            if parsed_rows is None:
                logger.error("Failed to open BR file after %d attempts.", max_retries)
            else:
                # Ensure that parsed_rows is not empty before accessing elements
                if parsed_rows:
                    first_row = parsed_rows[0]
                    has_header = not str(first_row[0]).strip().isdigit() if first_row else False
                    data_rows = parsed_rows[1:] if has_header else parsed_rows

                    marbcount = len(data_rows)

                    # Handle active_event_ids
                    event_ids_tmp = config.get_setting('active_event_ids')

                    if event_ids_tmp is not None:
                        event_ids_tmp = event_ids_tmp.strip("[]").split(",")
                        event_ids = [int(id.strip().replace('"', '')) for id in event_ids_tmp if id.strip().replace('"', '').isdigit()]
                    else:
                        event_ids = [0]

                    brdata = []  # Initialize brdata

                    # Process each row, skipping a detected header
                    for cleaned_line in data_rows:

                        # Ensure the cleaned_line has the expected length to avoid index errors
                        if len(cleaned_line) < 8:
                            print(f"Skipping invalid line: {cleaned_line}")
                            continue

                        # Create a row with the cleaned data
                        row = [
                            cleaned_line[0],  # Position
                            cleaned_line[1],  # Racer name
                            cleaned_line[2],  # Some value
                            cleaned_line[4],  # Some value
                            'BR',  # Battle Royale type
                            timestamp,  # Assuming timestamp is defined somewhere in your code
                            marbcount,  # Marble count
                            cleaned_line[5],  # Some value
                            cleaned_line[6],  # Some value
                            cleaned_line[7],  # Some value
                            event_ids  # Event IDs
                        ]
                        brdata.append(row)

                        # Process BR winner
                        if cleaned_line[0] == '1':
                            br_winner = cleaned_line

                            winner_login, winner_display, winner_label = resolve_br_identity(br_winner)

                            if winner_login == str(last_br_winner or '').strip().lower():
                                crownwin = True
                            else:
                                crownwin = False
                            config.set_setting('last_br_winner', winner_login, persistent=False)

                            t_count += 1
                            s_t_count += 1

                else:
                    logger.warning("BR file is empty or could not be processed.")

                # Check if br_winner is assigned before using it
                if br_winner is not None and len(br_winner) >= 8:
                    winner_login, winner_display, winner_label = resolve_br_identity(br_winner)
                    current_score = _safe_int(br_winner[4])
                    winner_kills = _safe_int(br_winner[6])
                    winner_damage = _safe_int(br_winner[7])

                    if not winner_login:
                        logger.warning("Skipping BR winner update due to missing winner login: %s", br_winner)
                        continue

                    t_points += current_score
                    s_t_points += current_score

                    _record_live_team_points_rows(config.get_setting('CHANNEL'), brdata)

                    race_counts = {row[1]: 0 for row in brdata}
                    append_csv_rows_safely(config.get_setting('allraces_file'), brdata)

                    if not br_cache_loaded or t_count <= 1:
                        br_user_totals = load_br_user_totals_from_allraces()
                        br_cache_loaded = True
                    else:
                        update_br_user_totals_cache(brdata)

                    for row in brdata:
                        player_name = str(row[1]).strip().lower()
                        player_totals = br_user_totals.get(player_name, {})
                        if player_totals.get('races', 0) == 120 and is_chat_response_enabled("chat_br_results"):
                            announcement_message = (
                                f"🎉 {player_name} has just completed their "
                                f"120th race today! Congratulations! 🎉"
                            )
                            await send_chat_message(bot.channel, announcement_message, category="br")

                    chunk_alert_enabled = config.get_setting('chunk_alert') == 'True'
                    chunk_alert_threshold = _safe_int(config.get_setting('chunk_alert_value'))
                    is_chunk_alert = chunk_alert_enabled and current_score >= chunk_alert_threshold

                    if is_chunk_alert:
                        audio_device = config.get_setting('audio_device')
                        audio_file_path = config.get_setting('chunk_alert_sound')
                        if audio_file_path:
                            play_audio_file(audio_file_path, device_name=audio_device)

                    br_high_score_global = _safe_int(config.get_setting('hscore'))
                    if current_score > br_high_score_global:
                        config.set_setting('hscore_name', winner_display, persistent=False)
                        config.set_setting('hscore', current_score, persistent=False)
                        high_score_payload = f"{config.get_setting('hscore_name')}\n{current_score:,}\n"
                        atomic_write_text(appdata_path('HighScore.txt'), high_score_payload)

                    if current_score > _safe_int(config.get_setting('br_hs_season')):
                        config.set_setting('br_hs_season', current_score, persistent=False)

                    if current_score > _safe_int(config.get_setting('br_hs_today')):
                        config.set_setting('br_hs_today', current_score, persistent=False)

                    latest_winner_summary = f"{winner_label} with {current_score} points, "
                    latest_winner_detail = f"{winner_kills} kills and {winner_damage} damage."
                    atomic_write_text(
                        appdata_path('LatestWinner.txt'),
                        f"Previous Winner:\n{latest_winner_summary}\n{latest_winner_detail}\n"
                    )
                    atomic_write_text(
                        appdata_path('LatestWinner_horizontal.txt'),
                        f"Previous Winner: {latest_winner_summary}{latest_winner_detail}",
                        errors='replace'
                    )

                    logger.info("Data synced: BR latest winner files updated")

                    avgptstoday = (t_points / t_count) if t_count > 0 else 0
                    config.set_setting('avgpointstoday', avgptstoday, persistent=False)
                    config.set_setting('totalpointstoday', t_points, persistent=False)
                    config.set_setting('totalcounttoday', t_count, persistent=False)
                    config.set_setting('totalpointsseason', s_t_points, persistent=False)
                    config.set_setting('totalcountseason', s_t_count, persistent=False)
                    update_config_labels()

                    winner_totals = br_user_totals.get(winner_login, {'points': 0, 'wins': 0, 'races': 0})
                    winnertotalpoints = winner_totals.get('points', 0)
                    wcount = winner_totals.get('wins', 0)
                    totalcount = winner_totals.get('races', 0)

                    wname = winner_display
                    wpoints = f"{current_score:,}"
                    wkills = str(winner_kills)
                    wdam = str(winner_damage)

                    message = build_br_winner_message(
                        crownwin=crownwin,
                        chunk_alert=is_chunk_alert,
                        winner_label=winner_label,
                        points=current_score,
                        kills=winner_kills,
                        damage=winner_damage,
                        total_points=winnertotalpoints,
                        wins=wcount,
                        races=totalcount,
                    )
                    if config.get_setting('announcedelay') == 'True':
                        await send_chat_message(bot.channel, message, category="br", apply_delay=True)
                        write_overlays()
                    else:
                        await send_chat_message(bot.channel, message, category="br")
                        write_overlays()

                    cycle_events = update_mycycle_with_race_rows(brdata)
                    if is_chat_response_enabled('mycycle_announcements_enabled'):
                        for event in cycle_events:
                            cycle_message = (
                                f"🔁 {event['display_name']} completed a MyCycle in {event['session_name']}! "
                                f"Cycle #{event['cycles_completed']} took {event['races_used']} races."
                            )
                            enqueue_overlay_event('cycle_completed', cycle_message)
                            await send_chat_message(
                                bot.channel,
                                cycle_message,
                                category="br"
                            )

                    for quest_message in get_season_quest_updates():
                        enqueue_overlay_event('quest_completed', quest_message)
                        await send_chat_message(bot.channel, quest_message, category="br")

                    namecolor = map_name_color(br_winner[3])
                    if crownwin:
                        display_battle_royale_crownwinner(text_area, marbcount, wname, wpoints, wkills, wdam, wcount,
                                                          winnertotalpoints, namecolor)

                    else:
                        display_battle_royale_winner(text_area, marbcount, wname, wpoints, wkills, wdam, wcount,
                                                     winnertotalpoints, namecolor)
                else:
                    print("No valid winner found after processing the data.")
        else:
            await asyncio.sleep(7)


if __name__ == "__main__":

    # Ensure the lock file is removed when the application exits

    # Function to start the bot in a separate asyncio event loop
    def start_bot():
        global bot

        reconnect_delay = 5

        while BOT_SHOULD_RUN:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                bot = Bot()
                bot.run()

                # If bot.run exits without an exception, only restart if the app is still running.
                if BOT_SHOULD_RUN:
                    print(
                        f"Twitch bot disconnected. Attempting reconnect in {reconnect_delay} seconds..."
                    )
                    time.sleep(reconnect_delay)
                    reconnect_delay = min(reconnect_delay * 2, 60)
                else:
                    break
            except Exception as e:
                logger.error("Bot connection failed", exc_info=True)
                if not BOT_SHOULD_RUN:
                    break
                print(f"Retrying Twitch connection in {reconnect_delay} seconds...")
                time.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, 60)
            finally:
                try:
                    loop.close()
                except Exception:
                    pass


    # Start the bot in a separate thread
    import threading

    bot_thread = threading.Thread(target=start_bot, daemon=True)
    bot_thread.start()

    # Run the Tkinter application
    root.mainloop()
