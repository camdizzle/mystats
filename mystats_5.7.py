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
import tkinter.simpledialog as simpledialog
from PIL import Image, ImageTk
from twitchio.ext import commands
from flask import Flask, jsonify, request, send_from_directory
import threading
import glob
import math
import json
import copy
import chardet
from collections import defaultdict
import csv
import pytz
from collections import defaultdict
from colorama import Fore, Style
import atexit
import webbrowser
from datetime import datetime, timedelta
from twitchio.ext.commands.errors import CommandNotFound
import sounddevice as sd
import soundfile as sf
from twitchio import errors
import io
from io import BytesIO
from dateutil import parser
from datetime import datetime, timedelta
import atexit
import socket
import importlib.util
import logging

try:
    import ttkbootstrap as ttkbootstrap_module
except ImportError:
    ttkbootstrap_module = None

# Global Variables
version = '6.0.0'
text_widget = None
bot = None
GLOBAL_SOCKET = None
DEBUG = False
HAS_TTKBOOTSTRAP = ttkbootstrap_module is not None
DEFAULT_UI_THEME = "darkly"
app_style = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("mystats")


def get_initial_ui_theme():
    try:
        with open("settings.txt", "r", encoding="utf-8", errors="ignore") as f:
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

    return root_window, style


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
    setting_value = config.get_setting(setting_key)

    # Backward compatibility for old setting name.
    if setting_value is None and setting_key == "chat_all_commands":
        setting_value = config.get_setting("chat_mystats_command")

    if setting_value is None:
        return True
    return str(setting_value).strip().lower() == "true"


def get_chat_max_names():
    try:
        value = int(config.get_setting("chat_max_names") or 25)
    except (TypeError, ValueError):
        value = 25

    return min(25, max(3, value))


def get_tilt_output_directory():
    output_directory = os.path.join(os.path.expanduser("~\\AppData\\Local\\MyStats\\"), "TiltedOutputFiles")
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
            return list(csv.reader(io.StringIO(decoded)))
        except Exception:
            time.sleep(retry_delay)

    return []


def chunked_join_messages(prefix, continuation_prefix, items, separator=', ', max_length=480):
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

    is_top_tiltee = False
    if len(row) >= 2:
        raw_top_value = str(row[-2]).strip().lower()
        is_top_tiltee = raw_top_value in ('1', 'true', 'yes', 'y')

    return {
        'run_id': run_id,
        'username': username,
        'points': points,
        'is_top_tiltee': is_top_tiltee,
    }


def is_tilt_top_tiltee_milestone(count):
    if count in (3, 5):
        return True
    return count >= 10 and count % 5 == 0


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


def get_int_setting(setting_key, default=0):
    try:
        return int(config.get_setting(setting_key) or default)
    except (TypeError, ValueError):
        return default


def get_season_quest_updates():
    if not is_chat_response_enabled("season_quests_enabled"):
        return []

    quest_definitions = [
        {
            'target_key': 'season_quest_target_races',
            'complete_key': 'season_quest_complete_races',
            'value': get_int_setting('totalcountseason', 0),
            'message': "🎯 Season Quest Complete: {value:,} / {target:,} season races finished!"
        },
        {
            'target_key': 'season_quest_target_points',
            'complete_key': 'season_quest_complete_points',
            'value': get_int_setting('totalpointsseason', 0),
            'message': "🎯 Season Quest Complete: {value:,} / {target:,} season points earned!"
        },
        {
            'target_key': 'season_quest_target_race_hs',
            'complete_key': 'season_quest_complete_race_hs',
            'value': get_int_setting('race_hs_season', 0),
            'message': "🎯 Season Quest Complete: Race high score reached {value:,} (target {target:,})!"
        },
        {
            'target_key': 'season_quest_target_br_hs',
            'complete_key': 'season_quest_complete_br_hs',
            'value': get_int_setting('br_hs_season', 0),
            'message': "🎯 Season Quest Complete: BR high score reached {value:,} (target {target:,})!"
        },
    ]

    quest_messages = []

    for quest in quest_definitions:
        target_value = get_int_setting(quest['target_key'], 0)
        already_complete = str(config.get_setting(quest['complete_key']) or 'False').lower() == 'true'

        if target_value <= 0 or already_complete:
            continue

        if quest['value'] >= target_value:
            config.set_setting(quest['complete_key'], 'True', persistent=True)
            quest_messages.append(quest['message'].format(value=quest['value'], target=target_value))

    return quest_messages


def get_season_quest_targets():
    return {
        'races': get_int_setting('season_quest_target_races', 0),
        'points': get_int_setting('season_quest_target_points', 0),
        'race_hs': get_int_setting('season_quest_target_race_hs', 0),
        'br_hs': get_int_setting('season_quest_target_br_hs', 0),
    }


def get_user_season_stats():
    user_stats = {}
    for allraces in glob.glob(os.path.join(config.get_setting('directory'), "allraces_*.csv")):
        try:
            with open(allraces, 'rb') as f:
                raw_data = f.read()
            result = chardet.detect(raw_data)
            encoding = result['encoding'] if result['encoding'] else 'utf-8'

            with open(allraces, 'r', encoding=encoding, errors='ignore') as f:
                reader = csv.reader(f)
                for row in reader:
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
                        }

                    if display_name:
                        user_stats[username]['display_name'] = display_name

                    user_stats[username]['races'] += 1
                    try:
                        points = int(row[3])
                    except (TypeError, ValueError):
                        points = 0

                    user_stats[username]['points'] += points
                    mode = row[4].strip().lower()
                    if mode == 'race' and points > user_stats[username]['race_hs']:
                        user_stats[username]['race_hs'] = points
                    elif mode == 'br' and points > user_stats[username]['br_hs']:
                        user_stats[username]['br_hs'] = points

        except FileNotFoundError:
            continue
        except Exception as e:
            print(f"Error reading season stats from {allraces}: {e}")

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
    quest_rows = [
        ("Season Races", stats['races'], targets['races']),
        ("Season Points", stats['points'], targets['points']),
        ("Race High Score", stats['race_hs'], targets['race_hs']),
        ("BR High Score", stats['br_hs'], targets['br_hs']),
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
        })

    leaderboard.sort(key=lambda row: (row['completed'], row['points'], row['races']), reverse=True)
    return leaderboard[:limit]


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

    columns = ("rank", "user", "completed", "races", "points", "race_hs", "br_hs")
    tree = ttk.Treeview(popup, columns=columns, show="headings", height=18)
    tree.heading("rank", text="#")
    tree.heading("user", text="User")
    tree.heading("completed", text="Completed")
    tree.heading("races", text="Races")
    tree.heading("points", text="Points")
    tree.heading("race_hs", text="Race HS")
    tree.heading("br_hs", text="BR HS")

    tree.column("rank", width=50, anchor="center")
    tree.column("user", width=190, anchor="w")
    tree.column("completed", width=110, anchor="center")
    tree.column("races", width=90, anchor="e")
    tree.column("points", width=120, anchor="e")
    tree.column("race_hs", width=90, anchor="e")
    tree.column("br_hs", width=90, anchor="e")

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
        ))

    scrollbar = ttk.Scrollbar(popup, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)

    tree.pack(side="left", fill="both", expand=True, padx=(12, 0), pady=(0, 12))
    scrollbar.pack(side="right", fill="y", padx=(0, 12), pady=(0, 12))


def get_rival_settings():
    return {
        'min_races': max(1, get_int_setting('rivals_min_races', 50)),
        'max_point_gap': max(0, get_int_setting('rivals_max_point_gap', 1500)),
        'pair_count': max(1, get_int_setting('rivals_pair_count', 25)),
    }


def resolve_user_in_stats(user_stats, username):
    lookup = (username or '').strip().lstrip('@').lower()
    if not lookup:
        return None
    if lookup in user_stats:
        return lookup
    for uname, stats in user_stats.items():
        if stats.get('display_name', '').strip().lower() == lookup:
            return uname
    return None


def get_global_rivalries(limit=None):
    user_stats = get_user_season_stats()
    settings = get_rival_settings()

    qualified = [
        (username, stats) for username, stats in user_stats.items()
        if stats.get('races', 0) >= settings['min_races'] and stats.get('points', 0) > 0
    ]

    rivalries = []
    for i in range(len(qualified)):
        user_a, stats_a = qualified[i]
        for j in range(i + 1, len(qualified)):
            user_b, stats_b = qualified[j]
            gap = abs(stats_a['points'] - stats_b['points'])
            if gap <= settings['max_point_gap']:
                rivalries.append({
                    'user_a': user_a,
                    'display_a': stats_a.get('display_name') or user_a,
                    'points_a': stats_a.get('points', 0),
                    'races_a': stats_a.get('races', 0),
                    'user_b': user_b,
                    'display_b': stats_b.get('display_name') or user_b,
                    'points_b': stats_b.get('points', 0),
                    'races_b': stats_b.get('races', 0),
                    'point_gap': gap,
                })

    rivalries.sort(key=lambda row: (row['point_gap'], -(row['points_a'] + row['points_b'])))
    cap = limit if limit is not None else settings['pair_count']
    return rivalries[:cap]


def get_user_rivals(username, limit=5):
    user_stats = get_user_season_stats()
    settings = get_rival_settings()
    user_key = resolve_user_in_stats(user_stats, username)

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

    rivals = []
    for other_key, other_stats in user_stats.items():
        if other_key == user_key:
            continue
        if other_stats.get('races', 0) < settings['min_races']:
            continue
        if other_stats.get('points', 0) <= 0:
            continue

        gap = abs(base.get('points', 0) - other_stats.get('points', 0))
        if gap > settings['max_point_gap']:
            continue

        rivals.append({
            'username': other_key,
            'display_name': other_stats.get('display_name') or other_key,
            'points': other_stats.get('points', 0),
            'races': other_stats.get('races', 0),
            'point_gap': gap,
        })

    rivals.sort(key=lambda row: (row['point_gap'], -row['points']))

    return {
        'user': user_key,
        'display_name': base.get('display_name') or user_key,
        'races': base.get('races', 0),
        'points': base.get('points', 0),
        'min_races_required': settings['min_races'],
        'rivals': rivals[:limit],
    }


def open_rivalries_window(parent_window):
    rivalries = get_global_rivalries(limit=200)
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


def _mycycle_file_path():
    base_dir = config.get_setting('directory') or os.getcwd()
    return os.path.join(base_dir, MYCYCLE_FILE_NAME)


def _empty_placement_counts(min_place, max_place):
    return {str(i): 0 for i in range(min_place, max_place + 1)}


def get_mycycle_settings():
    min_place = max(1, get_int_setting('mycycle_min_place', 1))
    max_place = min(10, get_int_setting('mycycle_max_place', 10))
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
    except (FileNotFoundError, json.JSONDecodeError):
        data = {'version': 1, 'sessions': {}}

    if not isinstance(data, dict):
        data = {'version': 1, 'sessions': {}}
    data.setdefault('version', 1)
    data.setdefault('sessions', {})
    return data


def save_mycycle_data(data):
    path = _mycycle_file_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temp_file = f"{path}.tmp"
    with open(temp_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    os.replace(temp_file, path)


def ensure_default_mycycle_session(data):
    season = str(config.get_setting('season') or 'unknown')
    session_id = f"{MYCYCLE_SESSION_PREFIX}{season}"
    now_text = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    sessions = data.setdefault('sessions', {})
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

    primary_session_id = config.get_setting('mycycle_primary_session_id')
    if (not primary_session_id or
            (str(primary_session_id).startswith(MYCYCLE_SESSION_PREFIX) and primary_session_id != session_id)):
        config.set_setting('mycycle_primary_session_id', session_id, persistent=True)
    return session_id


def get_mycycle_sessions(include_inactive=True):
    with MYCYCLE_LOCK:
        data = load_mycycle_data()
        default_id = ensure_default_mycycle_session(data)
        save_mycycle_data(data)
    sessions = list(data.get('sessions', {}).values())
    sessions.sort(key=lambda s: (not s.get('is_default', False), s.get('name', '').lower()))
    if include_inactive:
        return sessions, default_id
    return [s for s in sessions if s.get('active', True)], default_id


def create_mycycle_session(session_name, created_by='streamer'):
    with MYCYCLE_LOCK:
        data = load_mycycle_data()
        ensure_default_mycycle_session(data)
        now_text = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
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
    return session_id


def _resolve_session_id(data):
    primary_id = config.get_setting('mycycle_primary_session_id')
    sessions = data.get('sessions', {})
    if primary_id and primary_id in sessions:
        return primary_id
    return ensure_default_mycycle_session(data)


def _resolve_user_in_session(session_stats, username):
    lookup = (username or '').strip().lower().lstrip('@')
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
            'current_cycle_races': 0,
            'last_cycle_races': 0,
            'fastest_cycle_races': 0,
            'slowest_cycle_races': 0,
            'last_cycle_completed_at': None,
        }
        stats[username] = user_record

    user_record.setdefault('placements', _empty_placement_counts(min_place, max_place))
    for i in range(min_place, max_place + 1):
        user_record['placements'].setdefault(str(i), 0)
    user_record.setdefault('current_hits', [])
    user_record.setdefault('cycles_completed', 0)
    user_record.setdefault('total_races', 0)
    user_record.setdefault('current_cycle_races', 0)
    user_record.setdefault('last_cycle_races', 0)
    user_record.setdefault('fastest_cycle_races', 0)
    user_record.setdefault('slowest_cycle_races', 0)
    user_record.setdefault('last_cycle_completed_at', None)

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
        ensure_default_mycycle_session(data)
        session_id = _resolve_session_id(data)
        session = data.get('sessions', {}).get(session_id)

        if session is None or not session.get('active', True):
            save_mycycle_data(data)
            return completion_events

        for row in racedata:
            if len(row) < 5:
                continue
            race_type = row[4]
            if race_type != 'Race' and not (settings['include_br'] and race_type == 'BR'):
                continue

            username = (row[1] or '').strip().lower()
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
                user_record['last_cycle_completed_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                completion_events.append({
                    'session_name': session.get('name', 'Unknown Session'),
                    'username': username,
                    'display_name': user_record.get('display_name') or username,
                    'cycles_completed': user_record['cycles_completed'],
                    'races_used': user_record['last_cycle_races'],
                })
                user_record['current_hits'] = []
                user_record['current_cycle_races'] = 0

        save_mycycle_data(data)
    return completion_events


def get_mycycle_progress(username=None):
    with MYCYCLE_LOCK:
        data = load_mycycle_data()
        session_id = _resolve_session_id(data)
        save_mycycle_data(data)

    session = data['sessions'].get(session_id, {})
    stats = session.get('stats', {})
    target_user = _resolve_user_in_session(stats, username) if username else None
    return session, stats, target_user


def get_mycycle_leaderboard(limit=200):
    session, stats, _ = get_mycycle_progress()
    leaderboard = []
    settings = get_mycycle_settings()
    placement_range = list(range(settings['min_place'], settings['max_place'] + 1))
    for username, row in stats.items():
        hits = set(row.get('current_hits', []))
        hit_marks = [f"{place}{'✅' if place in hits else '❌'}" for place in placement_range]
        leaderboard.append({
            'username': username,
            'display_name': row.get('display_name') or username,
            'cycles_completed': int(row.get('cycles_completed', 0)),
            'progress_hits': len(hits),
            'progress_total': settings['max_place'] - settings['min_place'] + 1,
            'progress_marks': " ".join(hit_marks),
            'current_cycle_races': int(row.get('current_cycle_races', 0)),
            'last_cycle_races': int(row.get('last_cycle_races', 0)),
        })
    leaderboard.sort(key=lambda r: (r['cycles_completed'], r['progress_hits'], -r['current_cycle_races']), reverse=True)
    return session, leaderboard[:limit]


def get_mycycle_cycle_stats(session_query=None):
    with MYCYCLE_LOCK:
        data = load_mycycle_data()
        default_id = ensure_default_mycycle_session(data)
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


def open_mycycle_leaderboard_window(parent_window):
    session, leaderboard = get_mycycle_leaderboard(limit=500)
    if not leaderboard:
        messagebox.showinfo("MyCycle", "No cycle data yet for the selected session.")
        return

    popup = tk.Toplevel(parent_window)
    popup.title("MyCycle Leaderboard")
    popup.transient(parent_window)
    popup.attributes('-topmost', True)
    center_toplevel(popup, 1120, 540)

    ttk.Label(popup, text=f"Session: {session.get('name', 'Unknown')}", style="Small.TLabel").pack(anchor="w", padx=12, pady=(10, 4))
    columns = ("rank", "user", "cycles", "progress", "placements", "cycle_races", "last_cycle")
    tree = ttk.Treeview(popup, columns=columns, show="headings", height=20)
    for col, text in (("rank", "#"), ("user", "User"), ("cycles", "Cycles"), ("progress", "Current Progress"), ("placements", "Placements (Hit/Miss)"), ("cycle_races", "Races in Current Cycle"), ("last_cycle", "Races in Last Completed Cycle")):
        tree.heading(col, text=text)

    tree.column("rank", width=50, anchor="center")
    tree.column("user", width=170, anchor="w")
    tree.column("cycles", width=70, anchor="center")
    tree.column("progress", width=120, anchor="center")
    tree.column("placements", width=260, anchor="w")
    tree.column("cycle_races", width=140, anchor="center")
    tree.column("last_cycle", width=180, anchor="center")

    for idx, row in enumerate(leaderboard, start=1):
        tree.insert("", "end", values=(
            idx,
            row['display_name'],
            row['cycles_completed'],
            f"{row['progress_hits']}/{row['progress_total']}",
            row['progress_marks'],
            row['current_cycle_races'],
            row['last_cycle_races'],
        ))

    scrollbar = ttk.Scrollbar(popup, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    tree.pack(side="left", fill="both", expand=True, padx=(12, 0), pady=(0, 12))
    scrollbar.pack(side="right", fill="y", padx=(0, 12), pady=(0, 12))


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
        await channel.send(message)
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

# Twitch App Credentials
CLIENT_ID = 'icdintxz5c3h9twd6v3rntautv2o9g'
CLIENT_SECRET = 'qxyur2g933mst8uwaqzzto98t9zuwl'
def _get_redirect_uri():
    return f"http://localhost:{_load_overlay_server_port()}/callback"


# Function to start Flask server
def _load_overlay_server_port(default_port=5000):
    settings_path = 'settings.txt'
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
    app.run(port=_load_overlay_server_port(), debug=False, use_reloader=False)


def _find_latest_overlay_results_file(data_dir):
    files = sorted(glob.glob(os.path.join(data_dir, "allraces_*.csv")))
    return files[-1] if files else None


def _safe_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _build_overlay_header_stats(data_dir):
    season_points = 0
    season_races = 0
    season_unique = set()

    for allraces in glob.glob(os.path.join(data_dir, "allraces_*.csv")):
        try:
            with open(allraces, 'r', encoding='utf-8', errors='ignore') as f:
                for row in csv.reader(f):
                    if len(row) < 5:
                        continue
                    points = _safe_int(row[3])
                    if points == 0:
                        continue
                    racer = (row[2] or '').strip() or (row[1] or '').strip()
                    if not racer:
                        continue
                    season_points += points
                    season_races += 1
                    season_unique.add(racer.lower())
        except Exception:
            continue

    today_points = 0
    today_races = 0
    today_unique = set()
    today_file = config.get_setting('allraces_file')
    if today_file:
        try:
            with open(today_file, 'r', encoding='utf-8', errors='ignore') as f:
                for row in csv.reader(f):
                    if len(row) < 5:
                        continue
                    points = _safe_int(row[3])
                    if points == 0:
                        continue
                    racer = (row[2] or '').strip() or (row[1] or '').strip()
                    if not racer:
                        continue
                    today_points += points
                    today_races += 1
                    today_unique.add(racer.lower())
        except Exception:
            pass

    return {
        'avg_points_today': round((today_points / today_races), 2) if today_races else 0,
        'avg_points_season': round((season_points / season_races), 2) if season_races else 0,
        'unique_racers_today': len(today_unique),
        'unique_racers_season': len(season_unique),
        'total_races_today': today_races,
        'total_races_season': season_races,
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
        'tilt_theme': (config.get_setting('tilt_overlay_theme') or config.get_setting('overlay_theme') or 'midnight').strip().lower(),
        'tilt_scroll_step_px': _safe_int(config.get_setting('tilt_scroll_step_px') or 1) or 1,
        'tilt_scroll_interval_ms': _safe_int(config.get_setting('tilt_scroll_interval_ms') or 40) or 40,
        'tilt_scroll_pause_ms': _safe_int(config.get_setting('tilt_scroll_pause_ms') or 900) or 900,
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
        return None


def _overlay_now_for_timestamp(race_time):
    """Return a comparable now() for naive or timezone-aware timestamps."""
    if race_time is None:
        return datetime.now()
    if race_time.tzinfo is None:
        return datetime.now()
    return datetime.now(race_time.tzinfo)


def _overlay_points_top10(file_paths):
    totals = {}

    for file_path in file_paths:
        if not file_path:
            continue
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for row in csv.reader(f):
                    if len(row) < 5:
                        continue
                    name = (row[2] or '').strip() or (row[1] or '').strip()
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
        return {'rows': [], 'top3_rows': [], 'race_key': None, 'race_type': None, 'race_timestamp': None, 'is_recent': False}

    race_groups = []
    groups_by_key = {}

    try:
        with open(race_file, 'r', encoding='utf-8', errors='ignore') as f:
            for row in csv.reader(f):
                if len(row) < 6:
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
                    }
                    race_groups.append(groups_by_key[race_key])

                groups_by_key[race_key]['rows'].append({
                    'placement': placement,
                    'name': (row[2] or '').strip() or (row[1] or '').strip(),
                    'points': _safe_int(row[3]),
                })
    except Exception:
        return {'rows': [], 'top3_rows': [], 'race_key': None, 'race_type': None, 'race_timestamp': None, 'is_recent': False}

    if not race_groups:
        return {'rows': [], 'top3_rows': [], 'race_key': None, 'race_type': None, 'race_timestamp': None, 'is_recent': False}

    latest_group = race_groups[-1]
    latest_rows = sorted(latest_group['rows'], key=lambda r: r['placement'])
    top10_rows = latest_rows[:10]
    top3_rows = latest_rows[:3]

    race_time = latest_group['parsed_ts']
    is_recent = False
    if race_time:
        try:
            is_recent = (_overlay_now_for_timestamp(race_time) - race_time).total_seconds() <= 600
        except Exception:
            is_recent = False

    return {
        'rows': top10_rows,
        'top3_rows': top3_rows,
        'race_key': latest_group['race_key'],
        'race_type': latest_group['race_type'] or None,
        'race_timestamp': latest_group['race_timestamp'] or None,
        'is_recent': is_recent,
    }


def _build_overlay_top3_payload():
    data_dir = config.get_setting('directory') or os.getcwd()
    season_files, today_file = _overlay_data_sources(data_dir)
    recent_race = _overlay_recent_race_payload(today_file)

    views = [
        {
            'id': 'season',
            'title': 'Top 10 Season',
            'rows': _overlay_points_top10(season_files),
        },
        {
            'id': 'today',
            'title': 'Top 10 Today',
            'rows': _overlay_points_top10([today_file]),
        },
    ]

    if recent_race['is_recent'] and recent_race['rows']:
        views.append({
            'id': 'previous',
            'title': 'Top 10 Previous Race',
            'rows': recent_race['rows'],
        })

    return {
        'updated_at': datetime.now().isoformat(timespec='seconds'),
        'title': 'MyStats Live Results',
        'views': views,
        'recent_race_top3': {
            'title': 'Top 3 Latest Race',
            'rows': recent_race['top3_rows'],
            'race_key': recent_race['race_key'],
            'race_type': recent_race['race_type'],
            'race_timestamp': recent_race['race_timestamp'],
        },
        'header_stats': _build_overlay_header_stats(data_dir),
        'settings': _build_overlay_settings_payload(),
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

    sorted_run = sorted(
        ((str(name), _safe_int(points)) for name, points in run_ledger.items()),
        key=lambda item: item[1],
        reverse=True
    )

    current_run_id = str(config.get_setting('tilt_current_run_id') or '').strip()
    current_level = get_int_setting('tilt_current_level', 0)
    current_elapsed = str(config.get_setting('tilt_current_elapsed') or '0:00')
    current_top_tiltee = str(config.get_setting('tilt_current_top_tiltee') or 'None')
    current_top_tiltee_count = get_int_setting('tilt_current_top_tiltee_count', 0)

    lifetime_base_xp = get_int_setting('tilt_lifetime_base_xp', 0)

    current_summary = {
        'run_id': current_run_id,
        'run_short_id': current_run_id[:6] if current_run_id else '',
        'status': 'active' if current_run_id else 'idle',
        'level': current_level,
        'elapsed_time': current_elapsed,
        'top_tiltee': current_top_tiltee,
        'top_tiltee_count': current_top_tiltee_count,
        'run_points': get_int_setting('tilt_run_points', 0),
        'run_xp': get_int_setting('tilt_run_xp', 0),
        'best_run_xp_today': get_int_setting('tilt_best_run_xp_today', 0),
        'total_xp_today': get_int_setting('tilt_total_xp_today', 0),
        'total_deaths_today': get_int_setting('tilt_total_deaths_today', 0),
        'lifetime_expertise': get_int_setting('tilt_lifetime_expertise', 0) + lifetime_base_xp,
        'leader': {'name': sorted_run[0][0], 'points': sorted_run[0][1]} if sorted_run else None,
        'standings': [{'name': name, 'points': points} for name, points in sorted_run],
    }

    last_run_summary = parse_json_setting('tilt_last_run_summary', {})
    if not isinstance(last_run_summary, dict):
        last_run_summary = {}

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
        'updated_at': datetime.now().isoformat(timespec='seconds'),
        'title': 'MyStats Tilt Run Tracker',
        'settings': settings_payload,
        'current_run': current_summary,
        'last_run': last_run_summary,
        'level_completion': level_completion,
        'run_completion': run_completion,
        'run_completion_event_id': run_completion_event_id,
        'suppress_initial_recaps': True,
    }
    return payload


@app.route('/overlay')
def overlay_page():
    for candidate in _overlay_dir_candidates():
        index_file = os.path.join(candidate, 'index.html')
        if os.path.isfile(index_file):
            return send_from_directory(candidate, 'index.html')

    return (f"Overlay files not found. Checked: {', '.join(_overlay_dir_candidates())}", 404)


@app.route('/overlay/tilt')
def overlay_tilt_page():
    for candidate in _overlay_dir_candidates():
        index_file = os.path.join(candidate, 'tilt.html')
        if os.path.isfile(index_file):
            return send_from_directory(candidate, 'tilt.html')

    return (f"Tilt overlay files not found. Checked: {', '.join(_overlay_dir_candidates())}", 404)


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
    return jsonify(_build_overlay_top3_payload())


@app.route('/api/overlay/tilt')
def overlay_tilt_payload():
    return jsonify(_build_tilt_overlay_payload())


# Path to the token file
TOKEN_FILE_PATH = 'token_data.json'


# Save token data to a file and reconnect the bot with the new token asynchronously
def save_token_data(token_info):
    token_info['expires_at'] = time.time() + token_info.get('expires_in', 0)
    with open(TOKEN_FILE_PATH, 'w') as f:
        json.dump(token_info, f)
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
    return expires_at < time.time() if expires_at else True

# Function to refresh access token using refresh token
def refresh_access_token():
    token_data = load_token_data()

    if not token_data or 'refresh_token' not in token_data:
        print("No refresh token found.")
        return None

    print("Access token expired. Refreshing...")

    token_url = "https://id.twitch.tv/oauth2/token"
    refresh_token = token_data['refresh_token']

    token_data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
    }

    response = requests.post(token_url, data=token_data)

    if response.status_code == 200:
        print("Token refreshed successfully!")
        new_token_info = response.json()
        save_token_data(new_token_info)  # Save the new token info
        return new_token_info['access_token']
    else:
        print(f"Failed to refresh token: {response.text}")
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
        login_button.config(text=saved_username)
    else:
        print("No saved username in config.")


# Updated logic for setting the login button's username
def set_login_button_text():
    token_data = load_token_data()

    if token_data and 'access_token' in token_data:
        # Use the token from the JSON file to fetch the username
        oauth_token = token_data['access_token']
        username = fetch_twitch_username(oauth_token)

        if username:
            login_button.config(text=username)
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
            login_button.config(text=username)
            save_token_data(token_info)  # Save token info and restart bot
        return "Authentication successful!", 200
    else:
        return "Failed to retrieve or validate access token.", 400


def verify_token(token):
    verify_url = "https://id.twitch.tv/oauth2/validate"
    headers = {"Authorization": f"OAuth {token}"}
    response = requests.get(verify_url, headers=headers)
    if response.status_code == 200:
        print("\nToken is valid.")
        return True
    else:
        print(f"Token validation failed: {response.text}")
        return False


# Function to handle menu actions
def show_about_window():
    about_window = tk.Toplevel()
    about_window.title("About")
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
        print(f"Error loading logo image: {e}")
        # If the logo can't be loaded, display a text placeholder
        logo_label = ttk.Label(content_frame, text="MyStats", font=("Arial", 14, "bold"))
        logo_label.pack(pady=(0, 10))

    # Application Name and Version
    app_name_label = ttk.Label(content_frame, text="Mystats Application", font=("Arial", 14, "bold"))
    app_name_label.pack()

    version_label = ttk.Label(content_frame, text="Version " + str(version), font=("Arial", 9))
    version_label.pack(pady=(0, 10))

    # Short Description
    description_text = (
        "The application is a companion tool for Marbles On Stream, designed to enhance user "
        "engagement and streamline data management. It tracks and processes race data in real-time, "
        "handles event management, and posts automated race results to Twitch chat. Key features "
        "include Battle Royale crown win tracking, checkpoint processing, event status toggling, "
        "and seamless integration with the Twitch API for authenticating users and dynamically updating "
        "relevant stats and events. The application provides a user-friendly interface built with Tkinter, "
        "ensuring that race results, event statuses, and other critical information are easily accessible "
        "to both streamers and their viewers."
    )

    description_label = ttk.Label(content_frame, text=description_text, font=("Arial", 8),
                                  wraplength=380, justify="center")
    description_label.pack(pady=(0, 10))

    # Author Names
    authors_label = ttk.Label(content_frame, text="Developed by:\nCamWOW", font=("Arial", 10), justify="center")
    authors_label.pack(pady=(0, 10))

    # Contact Information
    contact_label = ttk.Label(
        content_frame,
        text="Contact Information:\nDiscord: https://discord.gg/camwow\nWebsite: https://www.camwow.tv",
        font=("Arial", 9),
        justify="center"
    )
    contact_label.pack(pady=(0, 10))

    # Acknowledgments or Credits
    credits_label = ttk.Label(
        content_frame,
        text="Acknowledgments:\nA heartfelt thank you to Vibblez for his incredible contributions, ideas, "
             "and unwavering support. His creative vision and technical expertise have been instrumental "
             "not only in shaping the MyStats application, but more specifically in elevating the website "
             "to new heights. From conceptualizing unique features to refining the user experience, his "
             "efforts have left an indelible mark on this project.",
        font=("Arial", 8),
        justify="center",
        wraplength=380
    )

    credits_label.pack(pady=(0, 10))

    # Close Button
    close_button = ttk.Button(content_frame, text="Close", command=about_window.destroy)
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
    initial_dir = os.path.expandvars(r"%localappdata%/mystats/sound files/")
    file_path = tk.filedialog.askopenfilename(initialdir=initial_dir, title="Select Sound File",
                                              filetypes=[("Audio Files", "*.mp3;*.wav;*.ogg")])
    if file_path:
        update_chunk_alert_audio_label(chunk_alert_label, file_path)
        settings_window.lift()
        settings_window.focus_force()


# Function to select the reset audio file
def select_reset_audio_sound(reset_audio_label, settings_window):
    initial_dir = os.path.expandvars(r"%localappdata%\\mystats\\sound files\\")
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
        print(f"An error occurred while playing the audio file: {e}")


def open_settings_window():
    settings_window = tk.Toplevel(root)
    settings_window.title("Settings")
    settings_window.transient(root)
    settings_window.attributes('-topmost', False)

    window_width = 760
    window_height = 700
    center_toplevel(settings_window, window_width, window_height)
    settings_window.minsize(720, 640)

    content_frame = ttk.Frame(settings_window, style="App.TFrame")
    content_frame.pack(fill="both", expand=True, padx=10, pady=(10, 0))

    notebook = ttk.Notebook(content_frame)
    notebook.pack(fill="both", expand=True)

    general_tab = ttk.Frame(notebook, style="App.TFrame", padding=10)
    audio_tab = ttk.Frame(notebook, style="App.TFrame", padding=10)
    chat_tab = ttk.Frame(notebook, style="App.TFrame", padding=10)
    season_quests_tab = ttk.Frame(notebook, style="App.TFrame", padding=10)
    rivals_tab = ttk.Frame(notebook, style="App.TFrame", padding=10)
    mycycle_tab = ttk.Frame(notebook, style="App.TFrame", padding=10)
    appearance_tab = ttk.Frame(notebook, style="App.TFrame", padding=10)
    overlay_tab = ttk.Frame(notebook, style="App.TFrame", padding=10)

    notebook.add(general_tab, text="General")
    notebook.add(audio_tab, text="Audio")
    notebook.add(chat_tab, text="Chat")
    notebook.add(season_quests_tab, text="Season Quests")
    notebook.add(rivals_tab, text="Rivals")
    notebook.add(mycycle_tab, text="MyCycle")
    notebook.add(appearance_tab, text="Appearance")
    notebook.add(overlay_tab, text="Overlay")

    # --- General tab ---
    ttk.Label(general_tab, text="Core app settings", style="Small.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

    ttk.Label(general_tab, text="Channel").grid(row=1, column=0, sticky="w", pady=(0, 4))
    channel_entry = ttk.Entry(general_tab, width=28)
    channel_entry.grid(row=1, column=1, sticky="w", pady=(0, 4))
    channel_entry.insert(0, config.get_setting("CHANNEL") or "")

    ttk.Label(general_tab, text="Marble Day").grid(row=2, column=0, sticky="w", pady=(0, 4))
    ttk.Label(general_tab, text=config.get_setting("marble_day") or "-").grid(row=2, column=1, sticky="w", pady=(0, 4))

    ttk.Label(general_tab, text="Season").grid(row=3, column=0, sticky="w", pady=(0, 8))
    ttk.Label(general_tab, text=config.get_setting("season") or "-").grid(row=3, column=1, sticky="w", pady=(0, 8))

    ttk.Separator(general_tab, orient="horizontal").grid(row=4, column=0, columnspan=2, sticky="ew", pady=8)

    ttk.Label(general_tab, text="Mystats Directory").grid(row=5, column=0, sticky="w", pady=(0, 4))
    directory_value = os.path.expandvars(r"%localappdata%/mystats/")
    directory_entry = ttk.Entry(general_tab, width=55)
    directory_entry.grid(row=6, column=0, sticky="ew", pady=(0, 4), columnspan=2)
    directory_entry.insert(0, directory_value)
    directory_entry.config(state="readonly")

    def open_directory():
        directory_path = os.path.expandvars(r"%localappdata%/mystats/")
        if os.path.exists(directory_path):
            os.startfile(directory_path)
        else:
            messagebox.showerror("Error", "Directory path does not exist.")

    ttk.Button(general_tab, text="Open Location", command=open_directory).grid(row=7, column=0, sticky="w", pady=(4, 0))
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
    ttk.Label(chat_tab, text="Control what MyStats announces in chat", style="Small.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))

    chat_br_results_var = tk.BooleanVar(value=is_chat_response_enabled("chat_br_results"))
    chat_race_results_var = tk.BooleanVar(value=is_chat_response_enabled("chat_race_results"))
    chat_tilt_results_var = tk.BooleanVar(value=is_chat_response_enabled("chat_tilt_results"))
    chat_all_commands_var = tk.BooleanVar(value=is_chat_response_enabled("chat_all_commands"))
    chat_narrative_alerts_var = tk.BooleanVar(value=is_chat_response_enabled("chat_narrative_alerts"))
    narrative_alert_grinder_var = tk.BooleanVar(value=is_chat_response_enabled("narrative_alert_grinder_enabled"))
    narrative_alert_winmilestone_var = tk.BooleanVar(value=is_chat_response_enabled("narrative_alert_winmilestone_enabled"))
    narrative_alert_leadchange_var = tk.BooleanVar(value=is_chat_response_enabled("narrative_alert_leadchange_enabled"))

    ttk.Checkbutton(chat_tab, text="BR Results", variable=chat_br_results_var).grid(row=1, column=0, sticky="w", pady=2)
    ttk.Checkbutton(chat_tab, text="Race Results", variable=chat_race_results_var).grid(row=2, column=0, sticky="w", pady=2)
    ttk.Checkbutton(chat_tab, text="Tilt Results", variable=chat_tilt_results_var).grid(row=3, column=0, sticky="w", pady=2)
    ttk.Checkbutton(chat_tab, text="All !commands", variable=chat_all_commands_var).grid(row=4, column=0, sticky="w", pady=2)
    ttk.Checkbutton(chat_tab, text="Narrative Alerts", variable=chat_narrative_alerts_var).grid(row=5, column=0, sticky="w", pady=(2, 6))

    narrative_alert_frame = ttk.LabelFrame(chat_tab, text="Narrative Alert Frequency", style="Card.TLabelframe")
    narrative_alert_frame.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(2, 8))

    ttk.Checkbutton(narrative_alert_frame, text="Grinder milestones", variable=narrative_alert_grinder_var).grid(row=0, column=0, sticky="w", padx=10, pady=(8, 4))
    ttk.Checkbutton(narrative_alert_frame, text="Win milestones", variable=narrative_alert_winmilestone_var).grid(row=1, column=0, sticky="w", padx=10, pady=2)
    ttk.Checkbutton(narrative_alert_frame, text="Lead changes", variable=narrative_alert_leadchange_var).grid(row=2, column=0, sticky="w", padx=10, pady=(2, 8))

    ttk.Label(narrative_alert_frame, text="Cooldown (races)", style="Small.TLabel").grid(row=0, column=1, sticky="w", padx=(12, 8), pady=(8, 2))
    narrative_alert_cooldown_entry = ttk.Entry(narrative_alert_frame, width=8, justify='center')
    narrative_alert_cooldown_entry.grid(row=0, column=2, sticky="w", padx=(0, 10), pady=(8, 2))
    narrative_alert_cooldown_entry.insert(0, config.get_setting("narrative_alert_cooldown_races") or "3")

    ttk.Label(narrative_alert_frame, text="Min lead gap", style="Small.TLabel").grid(row=1, column=1, sticky="w", padx=(12, 8), pady=2)
    narrative_alert_min_gap_entry = ttk.Entry(narrative_alert_frame, width=8, justify='center')
    narrative_alert_min_gap_entry.grid(row=1, column=2, sticky="w", padx=(0, 10), pady=2)
    narrative_alert_min_gap_entry.insert(0, config.get_setting("narrative_alert_min_lead_change_points") or "500")

    ttk.Label(narrative_alert_frame, text="Max items per alert", style="Small.TLabel").grid(row=2, column=1, sticky="w", padx=(12, 8), pady=(2, 8))
    narrative_alert_max_items_entry = ttk.Entry(narrative_alert_frame, width=8, justify='center')
    narrative_alert_max_items_entry.grid(row=2, column=2, sticky="w", padx=(0, 10), pady=(2, 8))
    narrative_alert_max_items_entry.insert(0, config.get_setting("narrative_alert_max_items") or "3")

    ttk.Label(chat_tab, text="Max names announced (Race/Tilt)").grid(row=7, column=0, sticky="w", pady=(4, 4))
    max_name_values = [str(i) for i in range(3, 26)]
    selected_max_names = tk.StringVar(value=str(get_chat_max_names()))
    max_names_combobox = ttk.Combobox(chat_tab, textvariable=selected_max_names, values=max_name_values, width=5, state="readonly")
    max_names_combobox.grid(row=7, column=1, sticky="w", pady=(4, 4), padx=(8, 0))

    message_delay_frame = ttk.LabelFrame(chat_tab, text="Message Delay", style="Card.TLabelframe")
    message_delay_frame.grid(row=8, column=0, columnspan=2, sticky="ew", pady=(10, 0))

    announce_delay_var = tk.BooleanVar(value=config.get_setting("announcedelay") == "True")
    ttk.Checkbutton(message_delay_frame, text="Enable Delay", variable=announce_delay_var).grid(row=0, column=0, sticky="w", padx=10, pady=(8, 6))
    ttk.Label(message_delay_frame, text="Delay Seconds", style="Small.TLabel").grid(row=1, column=0, sticky="w", padx=10)
    delay_seconds_entry = ttk.Entry(message_delay_frame, width=12, justify='center')
    delay_seconds_entry.grid(row=1, column=1, sticky="w", padx=(8, 10), pady=(0, 8))
    delay_seconds_entry.insert(0, config.get_setting("announcedelayseconds") or "")

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

    ttk.Label(season_quests_tab, text="Tip: Set any target to 0 to disable that specific quest.", style="Small.TLabel").grid(row=6, column=0, columnspan=2, sticky="w", pady=(8, 4))

    def reset_season_quest_progress():
        for completion_key in ("season_quest_complete_races", "season_quest_complete_points", "season_quest_complete_race_hs", "season_quest_complete_br_hs"):
            config.set_setting(completion_key, "False", persistent=True)
        messagebox.showinfo("Season Quests", "Season quest completion flags have been reset.")

    ttk.Button(season_quests_tab, text="Reset Quest Progress", command=reset_season_quest_progress).grid(row=7, column=0, sticky="w", pady=(8, 0))
    ttk.Button(season_quests_tab, text="View Quest Completion", command=lambda: open_quest_completion_window(settings_window)).grid(row=7, column=1, sticky="w", pady=(8, 0))

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

    ttk.Button(rivals_tab, text="View Rivalries", command=lambda: open_rivalries_window(settings_window)).grid(row=5, column=0, sticky="w", pady=(8, 0))

    # --- MyCycle tab ---
    ttk.Label(mycycle_tab, text="Track placement cycles (positions 1-10) and custom sessions", style="Small.TLabel").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))

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
        create_mycycle_session(session_name.strip(), created_by=config.get_setting("CHANNEL") or "streamer")
        refresh_session_dropdown()

    def toggle_selected_session():
        selected_name = selected_session_name.get()
        session_id = session_names.get(selected_name)
        if not session_id:
            return

        with MYCYCLE_LOCK:
            data = load_mycycle_data()
            session = data.get('sessions', {}).get(session_id)
            if not session:
                return
            if session.get('is_default'):
                messagebox.showinfo("MyCycle", "Default season sessions cannot be toggled off.")
                return
            session['active'] = not session.get('active', True)
            save_mycycle_data(data)

        state_text = "active" if session.get('active', True) else "inactive"
        messagebox.showinfo("MyCycle", f"Session '{selected_name}' is now {state_text}.")

    ttk.Button(mycycle_tab, text="Create Session", command=create_cycle_session_prompt).grid(row=7, column=0, sticky="w", pady=(8, 0))
    ttk.Button(mycycle_tab, text="Toggle Session Active", command=toggle_selected_session).grid(row=7, column=1, sticky="w", pady=(8, 0))
    ttk.Button(mycycle_tab, text="View Leaderboard", command=lambda: open_mycycle_leaderboard_window(settings_window)).grid(row=7, column=2, sticky="w", pady=(8, 0))
    ttk.Label(mycycle_tab, text="Tip: Streamers can create event-specific sessions and toggle them on/off at any time.", style="Small.TLabel").grid(row=8, column=0, columnspan=3, sticky="w", pady=(8, 0))

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


    # --- Overlay tab ---
    ttk.Label(overlay_tab, text="Control OBS overlay visuals from the desktop app", style="Small.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

    ttk.Label(overlay_tab, text="Stats Rotation (seconds)").grid(row=1, column=0, sticky="w", pady=(0, 4))
    overlay_rotation_entry = ttk.Entry(overlay_tab, width=12, justify='center')
    overlay_rotation_entry.grid(row=1, column=1, sticky="w", pady=(0, 4), padx=(8, 0))
    overlay_rotation_entry.insert(0, config.get_setting("overlay_rotation_seconds") or "10")

    ttk.Label(overlay_tab, text="Data Refresh (seconds)").grid(row=2, column=0, sticky="w", pady=(0, 4))
    overlay_refresh_entry = ttk.Entry(overlay_tab, width=12, justify='center')
    overlay_refresh_entry.grid(row=2, column=1, sticky="w", pady=(0, 4), padx=(8, 0))
    overlay_refresh_entry.insert(0, config.get_setting("overlay_refresh_seconds") or "3")

    ttk.Label(overlay_tab, text="Server Port").grid(row=3, column=0, sticky="w", pady=(0, 4))
    overlay_port_entry = ttk.Entry(overlay_tab, width=12, justify='center')
    overlay_port_entry.grid(row=3, column=1, sticky="w", pady=(0, 4), padx=(8, 0))
    overlay_port_entry.insert(0, config.get_setting("overlay_server_port") or "5000")

    ttk.Label(overlay_tab, text="Theme").grid(row=4, column=0, sticky="w", pady=(0, 4))
    overlay_theme_var = tk.StringVar(value=(config.get_setting("overlay_theme") or "midnight"))
    overlay_theme_combo = ttk.Combobox(overlay_tab, textvariable=overlay_theme_var, values=["midnight", "ocean", "sunset", "forest", "mono"], width=18, state="readonly")
    overlay_theme_combo.grid(row=4, column=1, sticky="w", pady=(0, 4), padx=(8, 0))

    ttk.Label(overlay_tab, text="Card Opacity (65-100)").grid(row=5, column=0, sticky="w", pady=(0, 4))
    overlay_opacity_entry = ttk.Entry(overlay_tab, width=12, justify='center')
    overlay_opacity_entry.grid(row=5, column=1, sticky="w", pady=(0, 4), padx=(8, 0))
    overlay_opacity_entry.insert(0, config.get_setting("overlay_card_opacity") or "84")

    ttk.Label(overlay_tab, text="Text Scale (90-125)").grid(row=6, column=0, sticky="w", pady=(0, 4))
    overlay_text_scale_entry = ttk.Entry(overlay_tab, width=12, justify='center')
    overlay_text_scale_entry.grid(row=6, column=1, sticky="w", pady=(0, 4), padx=(8, 0))
    overlay_text_scale_entry.insert(0, config.get_setting("overlay_text_scale") or "100")

    overlay_show_medals_var = tk.BooleanVar(value=str(config.get_setting("overlay_show_medals") or "True") == "True")
    overlay_compact_rows_var = tk.BooleanVar(value=str(config.get_setting("overlay_compact_rows") or "False") == "True")
    ttk.Checkbutton(overlay_tab, text="Show top-3 medal emotes", variable=overlay_show_medals_var).grid(row=7, column=0, sticky="w", pady=(6, 2), columnspan=2)
    ttk.Checkbutton(overlay_tab, text="Compact row spacing", variable=overlay_compact_rows_var).grid(row=8, column=0, sticky="w", pady=(0, 2), columnspan=2)
    ttk.Label(overlay_tab, text="Restart MyStats after changing port. Visual changes apply on next refresh.", style="Small.TLabel").grid(row=9, column=0, columnspan=2, sticky="w", pady=(8, 0))


    tilt_overlay_frame = ttk.LabelFrame(overlay_tab, text="Tilt Overlay", style="Card.TLabelframe")
    tilt_overlay_frame.grid(row=10, column=0, columnspan=2, sticky="ew", pady=(10, 0))

    ttk.Label(tilt_overlay_frame, text="Starting Lifetime XP", style="Small.TLabel").grid(row=0, column=0, sticky="w", padx=(10, 8), pady=(8, 4))
    tilt_lifetime_base_entry = ttk.Entry(tilt_overlay_frame, width=12, justify='center')
    tilt_lifetime_base_entry.grid(row=0, column=1, sticky="w", padx=(0, 10), pady=(8, 4))
    tilt_lifetime_base_entry.insert(0, config.get_setting("tilt_lifetime_base_xp") or "0")

    ttk.Label(tilt_overlay_frame, text="Tilt Theme", style="Small.TLabel").grid(row=1, column=0, sticky="w", padx=(10, 8), pady=4)
    tilt_overlay_theme_var = tk.StringVar(value=(config.get_setting("tilt_overlay_theme") or config.get_setting("overlay_theme") or "midnight"))
    ttk.Combobox(tilt_overlay_frame, textvariable=tilt_overlay_theme_var, values=["midnight", "ocean", "sunset", "forest", "mono"], width=18, state="readonly").grid(row=1, column=1, sticky="w", padx=(0, 10), pady=4)

    ttk.Label(tilt_overlay_frame, text="Scroll Step (px)", style="Small.TLabel").grid(row=2, column=0, sticky="w", padx=(10, 8), pady=4)
    tilt_scroll_step_entry = ttk.Entry(tilt_overlay_frame, width=12, justify='center')
    tilt_scroll_step_entry.grid(row=2, column=1, sticky="w", padx=(0, 10), pady=4)
    tilt_scroll_step_entry.insert(0, config.get_setting("tilt_scroll_step_px") or "1")

    ttk.Label(tilt_overlay_frame, text="Scroll Tick (ms)", style="Small.TLabel").grid(row=3, column=0, sticky="w", padx=(10, 8), pady=4)
    tilt_scroll_interval_entry = ttk.Entry(tilt_overlay_frame, width=12, justify='center')
    tilt_scroll_interval_entry.grid(row=3, column=1, sticky="w", padx=(0, 10), pady=4)
    tilt_scroll_interval_entry.insert(0, config.get_setting("tilt_scroll_interval_ms") or "40")

    ttk.Label(tilt_overlay_frame, text="Edge Pause (ms)", style="Small.TLabel").grid(row=4, column=0, sticky="w", padx=(10, 8), pady=(4, 8))
    tilt_scroll_pause_entry = ttk.Entry(tilt_overlay_frame, width=12, justify='center')
    tilt_scroll_pause_entry.grid(row=4, column=1, sticky="w", padx=(0, 10), pady=(4, 8))
    tilt_scroll_pause_entry.insert(0, config.get_setting("tilt_scroll_pause_ms") or "900")

    ttk.Label(tilt_overlay_frame, text="Tip: Starting Lifetime XP lets you align totals with existing channel progress.", style="Small.TLabel").grid(row=5, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 8))

    def reset_settings_defaults():
        chunk_alert_var.set(True)
        announce_delay_var.set(False)
        reset_audio_var.set(False)
        chat_br_results_var.set(True)
        chat_race_results_var.set(True)
        chat_tilt_results_var.set(True)
        chat_all_commands_var.set(True)
        chat_narrative_alerts_var.set(True)
        narrative_alert_grinder_var.set(True)
        narrative_alert_winmilestone_var.set(True)
        narrative_alert_leadchange_var.set(True)
        narrative_alert_cooldown_entry.delete(0, tk.END)
        narrative_alert_cooldown_entry.insert(0, "3")
        narrative_alert_min_gap_entry.delete(0, tk.END)
        narrative_alert_min_gap_entry.insert(0, "500")
        narrative_alert_max_items_entry.delete(0, tk.END)
        narrative_alert_max_items_entry.insert(0, "3")
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
        tilt_lifetime_base_entry.delete(0, tk.END)
        tilt_lifetime_base_entry.insert(0, "0")
        tilt_overlay_theme_var.set("midnight")
        tilt_scroll_step_entry.delete(0, tk.END)
        tilt_scroll_step_entry.insert(0, "1")
        tilt_scroll_interval_entry.delete(0, tk.END)
        tilt_scroll_interval_entry.insert(0, "40")
        tilt_scroll_pause_entry.delete(0, tk.END)
        tilt_scroll_pause_entry.insert(0, "900")

    footer = ttk.Frame(settings_window, style="App.TFrame")
    footer.pack(side="bottom", fill="x", padx=20, pady=10)

    ttk.Button(footer, text="Reset Defaults", command=reset_settings_defaults).pack(side="left")

    def save_settings_and_close():
        config.set_setting("CHANNEL", channel_entry.get(), persistent=True)
        config.set_setting("chunk_alert", str(chunk_alert_var.get()), persistent=True)
        config.set_setting("chunk_alert_value", chunk_alert_trigger_entry.get(), persistent=True)
        config.set_setting("announcedelay", str(announce_delay_var.get()), persistent=True)
        config.set_setting("announcedelayseconds", delay_seconds_entry.get(), persistent=True)
        config.set_setting("reset_audio", str(reset_audio_var.get()), persistent=True)
        config.set_setting("audio_device", selected_device.get(), persistent=True)
        config.set_setting("UI_THEME", selected_theme.get(), persistent=True)
        config.set_setting("chat_br_results", str(chat_br_results_var.get()), persistent=True)
        config.set_setting("chat_race_results", str(chat_race_results_var.get()), persistent=True)
        config.set_setting("chat_tilt_results", str(chat_tilt_results_var.get()), persistent=True)
        config.set_setting("chat_all_commands", str(chat_all_commands_var.get()), persistent=True)
        config.set_setting("chat_narrative_alerts", str(chat_narrative_alerts_var.get()), persistent=True)
        config.set_setting("narrative_alert_grinder_enabled", str(narrative_alert_grinder_var.get()), persistent=True)
        config.set_setting("narrative_alert_winmilestone_enabled", str(narrative_alert_winmilestone_var.get()), persistent=True)
        config.set_setting("narrative_alert_leadchange_enabled", str(narrative_alert_leadchange_var.get()), persistent=True)
        config.set_setting("narrative_alert_cooldown_races", narrative_alert_cooldown_entry.get(), persistent=True)
        config.set_setting("narrative_alert_min_lead_change_points", narrative_alert_min_gap_entry.get(), persistent=True)
        config.set_setting("narrative_alert_max_items", narrative_alert_max_items_entry.get(), persistent=True)
        config.set_setting("season_quests_enabled", str(season_quests_enabled_var.get()), persistent=True)
        config.set_setting("season_quest_target_races", season_quest_races_entry.get(), persistent=True)
        config.set_setting("season_quest_target_points", season_quest_points_entry.get(), persistent=True)
        config.set_setting("season_quest_target_race_hs", season_quest_race_hs_entry.get(), persistent=True)
        config.set_setting("season_quest_target_br_hs", season_quest_br_hs_entry.get(), persistent=True)
        config.set_setting("rivals_enabled", str(rivals_enabled_var.get()), persistent=True)
        config.set_setting("rivals_min_races", rivals_min_races_entry.get(), persistent=True)
        config.set_setting("rivals_max_point_gap", rivals_max_gap_entry.get(), persistent=True)
        config.set_setting("rivals_pair_count", rivals_pair_count_entry.get(), persistent=True)
        config.set_setting("mycycle_enabled", str(mycycle_enabled_var.get()), persistent=True)
        config.set_setting("mycycle_announcements_enabled", str(mycycle_announce_var.get()), persistent=True)
        config.set_setting("mycycle_include_br", str(mycycle_include_br_var.get()), persistent=True)
        config.set_setting("mycycle_min_place", mycycle_min_place_entry.get(), persistent=True)
        config.set_setting("mycycle_max_place", mycycle_max_place_entry.get(), persistent=True)
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
        config.set_setting("tilt_lifetime_base_xp", tilt_lifetime_base_entry.get(), persistent=True)
        config.set_setting("tilt_overlay_theme", tilt_overlay_theme_var.get(), persistent=True)
        config.set_setting("tilt_scroll_step_px", tilt_scroll_step_entry.get(), persistent=True)
        config.set_setting("tilt_scroll_interval_ms", tilt_scroll_interval_entry.get(), persistent=True)
        config.set_setting("tilt_scroll_pause_ms", tilt_scroll_pause_entry.get(), persistent=True)
        settings_window.destroy()

    ttk.Button(footer, text="Save and Close", command=save_settings_and_close, style="Primary.TButton").pack(side="right")

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
    if bot is not None and getattr(bot, "loop", None) is not None:
        asyncio.run_coroutine_threadsafe(bot.shutdown(), bot.loop)

    # Destroy the Tkinter windows after a delay
    def close_windows():
        sys.stdout = sys.__stdout__  # Reset stdout
        wait_window.destroy()
        root.destroy()

    root.after(1000, close_windows)  # Adjust delay as necessary




def open_url(event):
    webbrowser.open("https://mystats.camwow.tv")


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

    settings_button = ttk.Button(
        button_frame,
        text="Settings",
        command=open_settings_window,
        width=button_width,
        style="Primary.TButton"
    )
    settings_button.grid(row=0, column=0, padx=5, pady=(0, 5))

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

    text_area = tk.Text(parent, wrap='word', height=30, width=60, bg="black", fg="white")
    text_area.grid(row=1, column=1, sticky='nsew', padx=(0, 5), pady=5)


def initialize_main_window():
    global app_style

    root_window, app_style = create_root_window()
    apply_ui_styles(app_style)

    # Keep classic tk.Button widgets visually flatter to match ttk style.
    root_window.option_add("*Button.relief", "flat")
    root_window.option_add("*Button.borderWidth", 0)
    root_window.option_add("*Button.highlightThickness", 0)

    root_window.protocol("WM_DELETE_WINDOW", on_close)
    root_window.title("MyStats - Marbles On Stream Companion Application")

    window_width = 800
    window_height = 500
    screen_width = root_window.winfo_screenwidth()
    screen_height = root_window.winfo_screenheight()
    pos_x = (screen_width // 2) - (window_width // 2)
    pos_y = (screen_height // 2) - (window_height // 2)
    root_window.geometry(f"{window_width}x{window_height}+{pos_x}+{pos_y}")
    root_window.resizable(False, False)

    root_window.grid_rowconfigure(1, weight=1)
    root_window.grid_columnconfigure(1, weight=1)

    build_stats_sidebar(root_window)
    build_main_content(root_window)

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

            value = tk.StringVar(value=datetime.now().strftime('%Y-%m-%d'))
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
menu_bar.add_cascade(label="Edit", menu=edit_menu)

# Create the Help menu
help_menu = Menu(menu_bar, tearoff=0)
help_menu.add_command(label="View Commands", command=lambda: show_help(bot, root))
help_menu.add_command(label="About", command=show_about_window)
menu_bar.add_cascade(label="Help", menu=help_menu)

# Attach the menu bar to the root window
root.config(menu=menu_bar)


# Classes and Functions
class ConfigManager:
    def __init__(self):
        self.settings_file = 'settings.txt'
        self.settings = {}
        self.transient_settings = {}
        self.persistent_keys = {'TWITCH_USERNAME', 'TWITCH_TOKEN', 'CHANNEL', 'chunk_alert', 'chunk_alert_value',
                                'marble_day', 'allraces_file', 'announcedelay', 'announcedelayseconds',
                                'directory', 'race_file', 'br_file', 'season', 'reset_audio', 'sync', 'MPL',
                                'chunk_alert_sound', 'reset_audio_sound', 'audio_device', 'checkpoint_file',
                                'tilt_player_file', 'active_event_ids', 'paused_event_ids', 'checkpoint_results_file',
                                'tilts_results_file', 'tilt_level_file', 'map_data_file', 'map_results_file',
                                'UI_THEME', 'chat_br_results', 'chat_race_results', 'chat_tilt_results',
                                'chat_mystats_command', 'chat_all_commands', 'chat_narrative_alerts',
                                'narrative_alert_grinder_enabled', 'narrative_alert_winmilestone_enabled',
                                'narrative_alert_leadchange_enabled', 'narrative_alert_cooldown_races',
                                'narrative_alert_min_lead_change_points', 'narrative_alert_max_items', 'chat_max_names',
                                'season_quests_enabled', 'season_quest_target_races', 'season_quest_target_points',
                                'season_quest_target_race_hs', 'season_quest_target_br_hs', 'season_quest_complete_races',
                                'season_quest_complete_points', 'season_quest_complete_race_hs', 'season_quest_complete_br_hs',
                                'rivals_enabled', 'rivals_min_races', 'rivals_max_point_gap', 'rivals_pair_count',
                                'mycycle_enabled', 'mycycle_announcements_enabled', 'mycycle_include_br',
                                'mycycle_min_place', 'mycycle_max_place', 'mycycle_primary_session_id',
                                'mycycle_cyclestats_rotation_index',
                                'overlay_rotation_seconds', 'overlay_refresh_seconds', 'overlay_theme',
                                'overlay_card_opacity', 'overlay_text_scale', 'overlay_show_medals',
                                'overlay_compact_rows', 'overlay_server_port', 'tilt_lifetime_base_xp',
                                'tilt_overlay_theme', 'tilt_scroll_step_px', 'tilt_scroll_interval_ms',
                                'tilt_scroll_pause_ms'}
        self.transient_keys = set([])
        self.defaults = {
            'chat_br_results': 'True',
            'chat_race_results': 'True',
            'chat_tilt_results': 'True',
            'chat_mystats_command': 'True',
            'chat_all_commands': 'True',
            'chat_narrative_alerts': 'True',
            'narrative_alert_grinder_enabled': 'True',
            'narrative_alert_winmilestone_enabled': 'True',
            'narrative_alert_leadchange_enabled': 'True',
            'narrative_alert_cooldown_races': '3',
            'narrative_alert_min_lead_change_points': '500',
            'narrative_alert_max_items': '3',
            'chat_max_names': '25',
            'season_quests_enabled': 'True',
            'season_quest_target_races': '1000',
            'season_quest_target_points': '500000',
            'season_quest_target_race_hs': '3000',
            'season_quest_target_br_hs': '3000',
            'season_quest_complete_races': 'False',
            'season_quest_complete_points': 'False',
            'season_quest_complete_race_hs': 'False',
            'season_quest_complete_br_hs': 'False',
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
            'tilt_lifetime_base_xp': '0',
            'tilt_overlay_theme': 'midnight',
            'tilt_scroll_step_px': '1',
            'tilt_scroll_interval_ms': '40',
            'tilt_scroll_pause_ms': '900'
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
                   "rivals_min_races", "rivals_max_point_gap", "rivals_pair_count",
                   "narrative_alert_cooldown_races", "narrative_alert_min_lead_change_points", "narrative_alert_max_items",
                   "mycycle_min_place", "mycycle_max_place",
                   "overlay_rotation_seconds", "overlay_refresh_seconds", "overlay_card_opacity",
                   "overlay_text_scale", "overlay_server_port", "tilt_lifetime_base_xp",
                   "tilt_scroll_step_px", "tilt_scroll_interval_ms", "tilt_scroll_pause_ms"}:
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
                reader = csv.reader(f)
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
            print(f"An error occurred while processing the file {allraces}: {e}")

    # Process checkpoint files similarly to allraces
    for checkpoint_file in glob.glob(os.path.join(directory, "checkpoints_*.csv")):
        try:
            with open(checkpoint_file, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.reader(f)
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
            print(f"An error occurred while processing the file {checkpoint_file}: {e}")

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
        print(f"Error saving CSV file: {e}")

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
    with open('race_hs_season.txt', 'w', encoding='utf-8', errors='ignore') as rhs:
        if config.get_setting('race_hs_season') is not None:
            rhs.write(str(f"{int(config.get_setting('race_hs_season')):,}\n"))
        else:
            rhs.write("0\n")

    with open('br_hs_season.txt', 'w', encoding='utf-8', errors='ignore') as bhs:
        if config.get_setting('br_hs_season') is not None:
            bhs.write(str(f"{int(config.get_setting('br_hs_season')):,}\n"))
        else:
            bhs.write("0\n")

    with open('race_hs_today.txt', 'w', encoding='utf-8', errors='ignore') as rhs:
        if config.get_setting('race_hs_today') is not None:
            rhs.write(str(f"{int(config.get_setting('race_hs_today')):,}\n"))
        else:
            rhs.write("0\n")

    with open('br_hs_today.txt', 'w', encoding='utf-8', errors='ignore') as brhs:
        if config.get_setting('br_hs_today') is not None:
            brhs.write(f"{int(config.get_setting('br_hs_today')):,}\n")
        else:
            brhs.write("0\n")

    with open('TotalPointsToday.txt', 'w', encoding='utf-8', errors='ignore') as f:
        if config.get_setting('totalpointstoday') is not None:
            f.write(f"{int(config.get_setting('totalpointstoday')):,}\n")
        else:
            f.write("0\n")

    with open('AvgPointsToday.txt', 'w', encoding='utf-8', errors='ignore') as f:
        if config.get_setting('avgpointstoday') is not None:
            f.write(str(f"{int(float(config.get_setting('avgpointstoday'))):,}\n"))
        else:
            f.write("0\n")

    with open('CountofRaces.txt', 'w', encoding='utf-8', errors='ignore') as f:
        if config.get_setting('totalcounttoday') is not None:
            f.write(str(f"{int(config.get_setting('totalcounttoday')):,}\n"))
        else:
            f.write("0\n")


def create_results_files():
    timestamp, timestampMDY, timestampHMS, adjusted_time = time_manager.get_adjusted_time()

    base_directory = os.path.expanduser("~\\AppData\\Local\\MyStats\\")
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
        open(br_file, "w", encoding='utf-8', errors='ignore').close()
        with open('log.txt', 'a') as f:
            f.write(
                f"[{timestamp}]  - ~\\AppData\\Local\\MarblesOnStream\\Saved\\SaveGames\\LastSeasonRoyale.csv "
                f"does not exist\n")
    except Exception as e:
        print(f"{Fore.RED}We see no record of you hosting a Battle Royale.  Do that.{Style.RESET_ALL}")

    race_file = os.path.expanduser(r"~\AppData\Local\MarblesOnStream\Saved\SaveGames\LastSeasonRace.csv")
    config.set_setting('race_file', race_file, persistent=True)
    try:
        open(race_file, "r", encoding='utf-8', errors='ignore').close()
    except FileNotFoundError:
        open(race_file, "w", encoding='utf-8', errors='ignore').close()
        with open('log.txt', 'a') as f:
            f.write(
                f"[{timestamp}]  - ~\\AppData\\Local\\MarblesOnStream\\Saved\\SaveGames\\LastSeasonRace.csv "
                f"does not exist\n")
    except Exception as e:
        print(f"{Fore.RED}We see no record of you hosting a map race.  Do that.{Style.RESET_ALL}")

    tilt_player_file = os.path.expanduser(r"~\AppData\Local\MarblesOnStream\Saved\SaveGames\LastTiltLevelPlayers.csv")
    config.set_setting('tilt_player_file', tilt_player_file, persistent=True)
    try:
        open(tilt_player_file, "r", encoding='utf-8', errors='ignore').close()
    except FileNotFoundError:
        open(tilt_player_file, "w", encoding='utf-8', errors='ignore').close()
        with open('log.txt', 'a') as f:
            f.write(
                f"[{timestamp}]  - ~\\AppData\\Local\\MarblesOnStream\\Saved\\SaveGames\\LastTiltLevelPlayers.csv "
                f"does not exist\n")
    except Exception as e:
        print(f"{Fore.RED}No tilt file, tilt again or get tilted.{Style.RESET_ALL}")

    tilt_level_file = os.path.expanduser(r"~\AppData\Local\MarblesOnStream\Saved\SaveGames\LastTiltLevel.csv")
    config.set_setting('tilt_level_file', tilt_level_file, persistent=True)
    try:
        open(tilt_level_file, "r", encoding='utf-8', errors='ignore').close()
    except FileNotFoundError:
        open(tilt_level_file, "w", encoding='utf-8', errors='ignore').close()
        with open('log.txt', 'a') as f:
            f.write(
                f"[{timestamp}]  - ~\\AppData\\Local\\MarblesOnStream\\Saved\\SaveGames\\LastTiltLevel.csv "
                f"does not exist\n")
    except Exception as e:
        print(f"{Fore.RED}No tilt file, tilt again or get tilted.{Style.RESET_ALL}")

    checkpoint_file = os.path.expanduser(r"~\AppData\Local\MarblesOnStream\Saved\SaveGames\LastRaceNumbersHit.csv")
    config.set_setting('checkpoint_file', checkpoint_file, persistent=True)
    try:
        open(checkpoint_file, "r", encoding='utf-8', errors='ignore').close()
    except FileNotFoundError:
        open(checkpoint_file, "w", encoding='utf-8', errors='ignore').close()
        with open('log.txt', 'a') as f:
            f.write(
                f"[{timestamp}]  - ~\\AppData\\Local\\MarblesOnStream\\Saved\\SaveGames\\LastRaceNumbersHit.csv "
                f"does not exist\n")
    except Exception as e:
        print(f"{Fore.RED}We see no record.  Do something.{Style.RESET_ALL}")

    map_file = os.path.expanduser(r"~\AppData\Local\MarblesOnStream\Saved\SaveGames\LastCustomRaceMapPlayed.csv")
    config.set_setting('map_data_file', map_file, persistent=True)
    try:
        open(map_file, "r", encoding='utf-8', errors='ignore').close()
    except FileNotFoundError:
        open(map_file, "w", encoding='utf-8', errors='ignore').close()
        with open('log.txt', 'a') as f:
            f.write(
                f"[{timestamp}]  - ~\\AppData\\Local\\MarblesOnStream\\Saved\\SaveGames\\LastCustomRaceMapPlayed.csv "
                f"does not exist\n")
    except Exception as e:
        print(f"{Fore.RED}We see no record.  Do something.{Style.RESET_ALL}")


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
                reader = csv.reader(f)
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
            print(f"An error occurred while processing the file {allraces}: {e}")
            print(e)

    racer_data = dict(racer_data)

    json_data = json.dumps(racer_data, indent=4)
    config.set_setting('allracerdata', json_data, persistent=False)


def load_additional_settings():
    if config.get_setting('directory') in ['', None]:
        create_results_files()

    with MYCYCLE_LOCK:
        cycle_data = load_mycycle_data()
        ensure_default_mycycle_session(cycle_data)
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
                reader = csv.reader(f)
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
            print(f"An error occurred while processing the file {allraces}: {e}")
            print(e)

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
            today_reader = csv.reader(t)
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


def show_update_message():
    # Create a custom popup window
    popup = tk.Toplevel(root)
    popup.title("Update Required")
    popup.geometry("400x300")

    # Center the popup window on the main window
    root_x = root.winfo_x()
    root_y = root.winfo_y()
    root_width = root.winfo_width()
    root_height = root.winfo_height()

    popup_width = 400
    popup_height = 300

    pos_x = root_x + (root_width // 2) - (popup_width // 2)
    pos_y = root_y + (root_height // 2) - (popup_height // 2)
    popup.geometry(f"{popup_width}x{popup_height}+{pos_x}+{pos_y}")

    # Load and resize the update icon
    try:
        image = Image.open("warning.png")  # Load the image
        image = image.resize((100, 100), Image.LANCZOS)  # Resize to 100x100 pixels using LANCZOS filter
        photo = ImageTk.PhotoImage(image)
    except Exception as e:
        print(f"Error loading image: {e}")
        photo = None

    if photo:
        icon_label = tk.Label(popup, image=photo)
        icon_label.image = photo  # Keep a reference to avoid garbage collection
        icon_label.pack(pady=10)
    else:
        print("Update icon not displayed due to image loading issue.")

    # Add text label
    label = tk.Label(popup, text="An update is available. Please download the latest version to continue.",
                     wraplength=380)
    label.pack(pady=10)

    # Hyperlink label
    hyperlink = tk.Label(popup, text="Click here to download the update", fg="blue", cursor="hand2")
    hyperlink.pack(pady=5)
    hyperlink.bind("<Button-1>", lambda e: open_url("https://mystats.camwow.tv/download"))

    # Close button
    close_button = tk.Button(popup, text="Close", command=lambda: on_close())
    close_button.pack(pady=20)

    popup.transient(root)  # Set the popup to be modal (disables main window)
    popup.grab_set()
    root.wait_window(popup)  # Wait until the popup window is closed


def close_application(popup):
    popup.destroy()  # Close the popup window
    root.destroy()  # Close the main Tkinter window
    sys.exit(0)  # Exit the application


# Replace messagebox.showwarning with show_update_message in ver_season_only()
def ver_season_only():
    load_racer_data()

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
                        return season
                    else:
                        print(f"An update is available, check discord (https://discord.gg/camwow) "
                              f"for an updated installation file")
                        print(f"Current Version: {version} | New Version: {versioncheck}")
                        show_update_message()  # Show custom popup with hyperlink
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
        messagebox.showerror("Error", "Unable to verify season data after multiple attempts.")
        root.destroy()
        sys.exit(0)

    def retry_popup():
        """Show retry popup to prompt user login and retry."""
        return messagebox.askretrycancel(
            "Login Required",
            "You must log in to the website to use MyStats. Click Retry to try again.",
            parent=root
        )

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

    with open('HighScore.txt', 'w', encoding='utf-8', errors='ignore') as hs:
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
    config.set_setting('startup', 'yes', persistent=False)
    config.set_setting('data_sync', 'yes', persistent=False)
    create_results_files()
    ver_season_only()
    load_additional_settings()
    write_overlays()
    update_config_labels()
    set_login_button_text()

    br_hscore = int(config.get_setting('hscore'))
    br_hscore_format = format(br_hscore, ',')
    with open('HighScore.txt', 'w', encoding='utf-8', errors='ignore') as hs:
        hs.write(str(config.get_setting('hscore_name')) + '\n')
        hs.write(str(br_hscore_format + '\n'))

    timestamp, timestampMDY, timestampHMS, adjusted_time = time_manager.get_adjusted_time()

    if config.get_setting('new_season') == 'True':
        reset_season_stats()

    if config.get_setting('marble_day') != timestampMDY:
        reset()

    display_welcome_message(text_widget, version, config, timestamp)


# Schedule the startup function to run after the window is ready
root.after(100, lambda: startup(text_area))


# Initialize the Bot
import copy


class Bot(commands.Bot):
    def __init__(self):
        self.channel_name = config.get_setting('CHANNEL').lower()
        token = self.get_valid_token()  # Get the valid token at initialization
        prefix = '!'

        super().__init__(token=token, prefix=prefix, initial_channels=[self.channel_name])
        self.channel = None
        self.last_command_author = None
        self.config = config

        self.tasks = []  # List to keep track of tasks
        self.stop_event = asyncio.Event()  # Event to signal tasks to stop

    def get_valid_token(self):
        # Load token from the token file if it exists, otherwise fallback to config token
        token_data = load_token_data()

        if token_data:
            # Check if token is expired and refresh if needed
            if is_token_expired(token_data):
                print("Token expired, attempting to refresh...")
                new_token = refresh_access_token()  # Try to refresh the token
                if new_token:
                    print("Token refreshed successfully.")
                    return new_token  # Return the refreshed token
                else:
                    raise Exception("Failed to refresh token. Please reauthenticate.")
            else:
                return token_data['access_token']  # Return valid token from the file
        else:
            print("No token file found, falling back to ConfigManager token...")
            config_token = config.get_setting('TWITCH_TOKEN')
            if config_token:
                print("Using ConfigManager token.")
                return config_token  # Use the token from config if no token file exists
            else:
                raise Exception("No valid token found in ConfigManager. Please authenticate.")

    async def event_ready(self):
        self.channel = self.get_channel(self.channel_name)
        print(f"Sending message to Twitch as: {self.nick}")
        print(f"Connected to channel: {self.channel_name}\n")

        # Start main tasks and keep track of them
        self.tasks.append(self.loop.create_task(checkpoints(self)))
        self.tasks.append(self.loop.create_task(race(self)))
        self.tasks.append(self.loop.create_task(royale(self)))
        self.tasks.append(self.loop.create_task(tilted(self)))

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

    async def event_message(self, message):
        if message.author is None:
            return

        content = message.content.lower()

        if content.startswith('!') and not is_chat_response_enabled("chat_all_commands"):
            return

        new_message = copy.copy(message)
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


    @commands.command(name='info')
    async def info(self, ctx):
        if ctx.author.name.lower() == 'camwow' or ctx.author.name.lower() == config.get_setting(
                'CHANNEL').lower() or ctx.author.name.lower() == 'vibblez':
            await ctx.channel.send("Version " + str(version) + " | Season: " + str(config.get_setting('season')) +
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

    @commands.command(name='mostop10')
    async def mostop10(self, ctx):
        api_url = (
            "https://pixelbypixel.studio/api/leaderboards"
            f"?offset=0&statisticName=Season_XP&seasonNumber={config.get_setting('season')}"
        )
        response = requests.get(api_url)

        if response.status_code == 200:
            # The response now has {"Version": ..., "Leaderboard": [...]}.
            data = response.json()

            # Grab the Leaderboard array from the dictionary
            leaderboard_data = data["Leaderboard"]  # This is now a list

            # Slice the top 10
            top_10_records = leaderboard_data[:10]

            leaderboard_message = ""
            emotes = {1: " 🥇", 2: " 🥈", 3: " 🥉"}
            for rank, record in enumerate(top_10_records, start=1):
                emote = emotes.get(rank, "")
                stat_value = format(record["StatValue"], ",")
                display_name = record["DisplayName"]
                leaderboard_message += f"{emote} {rank}. {display_name} - {stat_value}\n"

            await ctx.channel.send(
                leaderboard_message + " | View the full leaderboard at: https://pixelbypixel.studio/hub"
            )
        else:
            print(f"Failed to fetch data: {response.status_code}")
            await ctx.channel.send("Failed to pull leaderboard, please try again")


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

                await ctx.channel.send(message.strip())
        else:
                print(f"Failed to fetch data: {response.status_code}")
                await ctx.channel.send("Failed to pull energy data, please try again.")

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
        await ctx.channel.send(
            "Interested in learning more about the Streamer Meta?  "
            "📖: https://docs.google.com/document/d/1k93YU73QbGZrmfHqm1cto8PzzF2eADPtpGLILfGawVM/edit")

    @commands.command(name='energy')
    async def energy(self, ctx):
        await ctx.channel.send(
            "Energy is the system by which viewers exchange their energy with streamers, for points. "
            "You start the day at 12:00pm EST, with 7 energy. This is the daily energy reset time. "
            "Every 3 races with the same streamer, your energy will be returned to you. If you run out of energy, "
            "you will no longer earn points, but you can still race. Once you complete 120 races with a streamer, "
            "that energy spent will no longer be returned.")

    @commands.command(name='mosapp')
    async def mosapp(self, ctx):
        await ctx.channel.send(
            "Download the MOS App on Mobile.  Google Play: "
            "https://play.google.com/store/apps/details?id=com.pixelbypixel.mosmobile&hl=en-US.   Apple App Store: "
            "https://apps.apple.com/us/app/marbles-on-stream-mobile/id1443250176")

    @commands.command(name='mosshop')
    async def mosshop(self, ctx):
        await ctx.channel.send(
            "Purchase Skins or Coins for yourself, or gift them to a friend!  https://pixelbypixel.studio/shop")

    @commands.command(name='wiki')
    async def wiki(self, ctx):
        await ctx.channel.send("Marbles on Stream Wiki - https://wiki.pixelbypixel.studio/")

    @commands.command(name='commands')
    async def list_commands(self, ctx):
        excluded_commands = ['commands', 'mplreset']
        commands_list = [f'!{cmd.name}' for cmd in self.commands.values() if cmd.name not in excluded_commands]
        commands_description = ', '.join(commands_list)
        await ctx.send(f'MyStats commands: {commands_description}')

    # Method to expose the command list outside the class
    def get_commands(self):
        excluded_commands = ['commands', 'mplreset']
        return [f'!{cmd.name}' for cmd in self.commands.values() if cmd.name not in excluded_commands]

    @commands.command(name='rivals')
    async def rivals_command(self, ctx, username: str = None, compare_username: str = None):
        if not is_chat_response_enabled("rivals_enabled"):
            await ctx.channel.send("Rivals are currently disabled.")
            return

        if username and compare_username:
            user_stats = get_user_season_stats()
            user_a_key = resolve_user_in_stats(user_stats, username)
            user_b_key = resolve_user_in_stats(user_stats, compare_username)

            if user_a_key is None or user_b_key is None:
                await ctx.channel.send("Could not find one or both users in season stats.")
                return

            stats_a = user_stats[user_a_key]
            stats_b = user_stats[user_b_key]
            settings = get_rival_settings()
            point_gap = abs(stats_a.get('points', 0) - stats_b.get('points', 0))

            qualifies_a = stats_a.get('races', 0) >= settings['min_races'] and stats_a.get('points', 0) > 0
            qualifies_b = stats_b.get('races', 0) >= settings['min_races'] and stats_b.get('points', 0) > 0
            are_rivals = qualifies_a and qualifies_b and point_gap <= settings['max_point_gap']

            rivalry_status = "✅ Rivalry active" if are_rivals else "❌ Not a qualifying rivalry"

            await ctx.channel.send(
                f"Rivals Check • {stats_a['display_name']} vs {stats_b['display_name']} | "
                f"Gap: ±{point_gap:,} pts | "
                f"{stats_a['display_name']}: {stats_a.get('points', 0):,} pts ({stats_a.get('races', 0):,} races) | "
                f"{stats_b['display_name']}: {stats_b.get('points', 0):,} pts ({stats_b.get('races', 0):,} races) | "
                f"{rivalry_status}"
            )
            return

        if username:
            rival_data = get_user_rivals(username, limit=5)
            if rival_data is None:
                await ctx.channel.send(f"{username}: no season rival data found.")
                return

            if rival_data['races'] < rival_data['min_races_required']:
                await ctx.channel.send(
                    f"{rival_data['display_name']}: {rival_data['races']:,} races so far. "
                    f"Need {rival_data['min_races_required']:,}+ races for rivals tracking."
                )
                return

            if not rival_data['rivals']:
                await ctx.channel.send(
                    f"{rival_data['display_name']}: no close rivals found within configured point gap."
                )
                return

            entries = [
                f"#{idx} {row['display_name']} (±{row['point_gap']:,}, {row['points']:,} pts)"
                for idx, row in enumerate(rival_data['rivals'], start=1)
            ]
            await ctx.channel.send(
                f"Rivals for {rival_data['display_name']} ({rival_data['points']:,} pts): " + " | ".join(entries)
            )
            return

        rivalries = get_global_rivalries(limit=5)
        if not rivalries:
            await ctx.channel.send("No rivalries found yet with current rival settings.")
            return

        entries = [
            f"#{idx} {row['display_a']} vs {row['display_b']} (±{row['point_gap']:,})"
            for idx, row in enumerate(rivalries, start=1)
        ]
        await ctx.channel.send("Rivalries Leaderboard: " + " | ".join(entries))

    @commands.command(name='h2h')
    async def head_to_head_command(self, ctx, user_a: str = None, user_b: str = None):
        if not is_chat_response_enabled("rivals_enabled"):
            await ctx.channel.send("Rivals are currently disabled.")
            return

        if not user_a or not user_b:
            await ctx.channel.send("Usage: !h2h <user1> <user2>")
            return

        user_stats = get_user_season_stats()
        user_a_key = resolve_user_in_stats(user_stats, user_a)
        user_b_key = resolve_user_in_stats(user_stats, user_b)

        if user_a_key is None or user_b_key is None:
            await ctx.channel.send("Could not find one or both users in season stats.")
            return

        stats_a = user_stats[user_a_key]
        stats_b = user_stats[user_b_key]

        leader_name = stats_a['display_name'] if stats_a['points'] >= stats_b['points'] else stats_b['display_name']
        point_gap = abs(stats_a['points'] - stats_b['points'])

        await ctx.channel.send(
            f"H2H {stats_a['display_name']} vs {stats_b['display_name']} | "
            f"Points: {stats_a['points']:,}-{stats_b['points']:,} | "
            f"Races: {stats_a['races']:,}-{stats_b['races']:,} | "
            f"Race HS: {stats_a['race_hs']:,}-{stats_b['race_hs']:,} | "
            f"BR HS: {stats_a['br_hs']:,}-{stats_b['br_hs']:,} | "
            f"Leader: {leader_name} by {point_gap:,}"
        )

    @commands.command(name='mycycle')
    async def mycycle_command(self, ctx, username: str = None):
        if not is_chat_response_enabled('mycycle_enabled'):
            await ctx.channel.send("MyCycle tracking is currently disabled.")
            return

        target_name = username or ctx.author.name
        session, stats, target_user = get_mycycle_progress(target_name)
        settings = get_mycycle_settings()

        if not target_user or target_user not in stats:
            await ctx.channel.send(
                f"{target_name}: no MyCycle race data yet in session '{session.get('name', 'Unknown')}'."
            )
            return

        record = stats[target_user]
        hits = set(record.get('current_hits', []))
        required_positions = list(range(settings['min_place'], settings['max_place'] + 1))
        missing = [str(pos) for pos in required_positions if pos not in hits]
        progress_text = f"{len(hits)}/{len(required_positions)}"
        display_name = record.get('display_name') or target_user

        message = (
            f"🔁 {display_name} | Session: {session.get('name', 'Unknown')} | "
            f"Cycles: {record.get('cycles_completed', 0)} | Progress: {progress_text} | "
            f"Races this cycle: {record.get('current_cycle_races', 0)} | "
            f"Last cycle races: {record.get('last_cycle_races', 0)}"
        )
        if missing:
            message += f" | Missing: {','.join(missing)}"

        await ctx.channel.send(message)

    @commands.command(name='cyclestats')
    async def cyclestats_command(self, ctx, session_name: str = None):
        if not is_chat_response_enabled('mycycle_enabled'):
            await ctx.channel.send("MyCycle tracking is currently disabled.")
            return

        stats = get_mycycle_cycle_stats(session_name)
        if not stats:
            await ctx.channel.send("No MyCycle sessions found. Try !cyclestats all")
            return

        fastest = stats.get('fastest')
        slowest = stats.get('slowest')
        if not fastest and not slowest:
            await ctx.channel.send(
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

        await ctx.channel.send(
            f"🔁 CycleStats [{stats['label']}] | Fastest: {fastest_text} | "
            f"Slowest: {slowest_text} | {rotating_metric_text} | "
            f"Total cycles: {stats['cycles_total']}"
        )

    @commands.command(name='myquests')
    async def myquests_command(self, ctx, username: str = None):
        lookup_name = username if username else ctx.author.name
        progress = get_user_quest_progress(lookup_name)

        if progress is None:
            await ctx.channel.send(f"{lookup_name}: No quest progress found yet.")
            return

        headline = (
            f"{progress['display_name']} Quest Progress: "
            f"{progress['completed']}/{progress['active_quests'] if progress['active_quests'] > 0 else 0} quests complete"
        )
        details = " | ".join(progress['progress_lines'])
        await ctx.channel.send(f"{headline} | {details}")


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
                    reader = csv.reader(f)
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
                await ctx.channel.send("No season races recorded yet")
                return
            except Exception as e:
                print(e)
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
        for racer, stats in top_racers:
            # Round down the PPR to one decimal place
            ppr_rounded_down = math.floor(stats['ppr'] * 10) / 10
            entry = f"{racer}: {ppr_rounded_down:.1f}"
            entries.append(entry)

        header = "Top 10 Racers by PPR (with +100 races): \n"
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
            await ctx.channel.send(chunk)


    @commands.command(name='mystats')
    async def mystats_command(self, ctx, username: str = None):
        timestamp, timestampMDY, timestampHMS, adjusted_time = time_manager.get_adjusted_time()

        # Use the provided username if available; otherwise default to the command author.
        if username is None:
            winnersname = ctx.author.name
            winnersdisplayname = ctx.author.name
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
                    reader = csv.reader(f)
                    for row in reader:
                        race_date = datetime.strptime(row[5], "%Y-%m-%d %H:%M:%S").date()

                        if row[1].lower() == winnersname.lower() and str(race_date) == str(today):
                            counts['racestoday'] += 1
                            counts['pointstoday'] += int(row[3])
                            if int(row[0]) == 1:
                                counts['winstoday'] += 1

                        if row[1].lower() == winnersname.lower():
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
                await ctx.channel.send("No season races recorded yet")
                return
            except Exception as e:
                print(e)
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
        seasonwins_str = "win" if counts['seasonwins'] == 1 else "wins"

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

        # Create the formatted output message.
        output_msg = (
            f"BRs - {brwins_formatted} wins, {br_points_formatted} points, {br_count_formatted} royales, PPR: {br_avg_points_formatted}. | "
            f"Races - {racewins_formatted} wins, {race_points_formatted} points, {race_count_formatted} races, PPR: {race_avg_points_formatted}. | "
            f"Season - {seasonwins_formatted} wins, {seasonpts_formatted} points, {seasonraces_formatted} races, PPR: {season_avg_points_formatted}. | "
            f"World Records - {counts['world_record_count']}"
        )

        await send_chat_message(
            ctx.channel,
            f"{winnersdisplayname}: Today: {counts['winstoday']} {wins_str}, {pointstoday_formatted} points, {racestoday_formatted} races. "
            f"PPR: {today_avg_points_formatted} | Season total: {output_msg}",
            category="mystats"
        )


    @commands.command(name='mytilts')
    async def mytilts_command(self, ctx, username: str = None):
        if username is None:
            target_name = ctx.author.name
            display_name = ctx.author.name
        else:
            target_name = username.split()[0].lstrip('@')
            display_name = target_name

        runs_today = set()
        season_runs = set()
        levels_today = 0
        levels_season = 0
        points_today = 0
        points_season = 0

        _, _, _, adjusted_time = time_manager.get_adjusted_time()
        today_date = adjusted_time.strftime("%Y-%m-%d")

        for tilts_file in glob.glob(os.path.join(config.get_setting('directory'), "tilts_*.csv")):
            try:
                with open(tilts_file, 'rb') as f:
                    raw_data = f.read()
                result = chardet.detect(raw_data)
                encoding = result['encoding'] if result['encoding'] else 'utf-8'

                with open(tilts_file, 'r', encoding=encoding, errors='ignore') as f:
                    reader = csv.reader(f)
                    for row in reader:
                        parsed = parse_tilt_result_row(row)
                        if parsed is None:
                            continue

                        racer, points, run_id = parsed
                        if racer.lower() != target_name.lower():
                            continue

                        file_date = os.path.basename(tilts_file)[6:16]
                        levels_season += 1
                        points_season += points
                        season_runs.add(run_id)

                        if file_date == today_date:
                            levels_today += 1
                            points_today += points
                            runs_today.add(run_id)


            except FileNotFoundError:
                continue
            except Exception as e:
                print(e)

        if points_season == 0 and levels_season == 0:
            await send_chat_message(
                ctx.channel,
                f"{display_name}: No tilt data found this season.",
                category="mystats"
            )
            return

        avg_today = points_today / levels_today if levels_today else 0
        avg_season = points_season / levels_season if levels_season else 0

        avg_today_rounded_down = math.floor(avg_today * 10) / 10
        avg_season_rounded_down = math.floor(avg_season * 10) / 10

        await send_chat_message(
            ctx.channel,
            f"{display_name}: Today Tilt - {len(runs_today)} runs, {points_today:,} points, {levels_today:,} levels, PPL: {avg_today_rounded_down:.1f} | "
            f"Season Tilt - {len(season_runs)} runs, {points_season:,} points, {levels_season:,} levels, PPL: {avg_season_rounded_down:.1f}",
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
                    reader = csv.reader(f)
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
                print(e)

        if not top_tiltee_counts:
            await send_chat_message(ctx.channel, "No top tiltee data available yet.", category="mystats")
            return

        ranked = sorted(
            top_tiltee_counts.items(),
            key=lambda item: (item[1], season_points_by_player.get(item[0], 0)),
            reverse=True
        )[:10]

        items = [
            f"({idx}) {name} {tops} tops, {season_points_by_player.get(name, 0):,} points"
            for idx, (name, tops) in enumerate(ranked, start=1)
        ]

        message = "Top Tiltees: " + ", ".join(items) + "."
        await send_chat_message(ctx.channel, message, category="mystats")


    @commands.command(name='top10tilees')
    async def top10tilees_command(self, ctx):
        data = defaultdict(int)

        for tilts_file in glob.glob(os.path.join(config.get_setting('directory'), "tilts_*.csv")):
            try:
                with open(tilts_file, 'rb') as f:
                    raw_data = f.read()
                result = chardet.detect(raw_data)
                encoding = result['encoding'] if result['encoding'] else 'utf-8'

                with open(tilts_file, 'r', encoding=encoding, errors='ignore') as f:
                    reader = csv.reader(f)
                    for row in reader:
                        parsed = parse_tilt_result_row(row)
                        if parsed is None:
                            continue

                        racer, points, _ = parsed
                        data[racer] += points
            except FileNotFoundError:
                continue
            except Exception as e:
                print(e)

        if not data:
            await send_chat_message(ctx.channel, "No tilt data available yet.", category="mystats")
            return

        top_tilees = sorted(data.items(), key=lambda x: x[1], reverse=True)[:10]
        message = "Top 10 Tilees by Tilt Points: "
        for i, (racer, points) in enumerate(top_tilees):
            place = i + 1
            message += "{} {} {} points{}".format(
                "(" + str(place) + ")", racer, format(points, ','), ", " if i < len(top_tilees) - 1 else "."
            )

        await send_chat_message(ctx.channel, message, category="mystats")


    
    @commands.command(name='top10nwr')
    async def top10nwr_command(self, ctx):
        self.last_command_author = ctx.author.name
        data = {}
        try:
            with open(config.get_setting('allraces_file'), 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.reader(f)

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

                message = "Top 10 Today (Excluding WRs): "
                for i, (racer, points) in enumerate(top_racers):
                    place = i + 1
                    message += "{} {} {} points{}".format("(" + str(place) + ")", racer, format(points, ','),
                                                        ", " if i < len(top_racers) - 1 else ".")

            await ctx.channel.send(message)
        except FileNotFoundError:
            print("File not found.")
            await ctx.channel.send(self.last_command_author + ": No races have been recorded today.")
        except Exception as e:
            pass
            print(e)

    @commands.command(name='top10today')
    async def top10scores_command(self, ctx):
        self.last_command_author = ctx.author.name
        data = {}
        try:
            with open(config.get_setting('allraces_file'), 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.reader(f)

                for row in reader:
                    if len(row) >= 5 and int(''.join(row[3]).replace('\x00', '')) != 0:
                        racer = row[2]
                        points = int(row[3])
                        if racer in data:
                            data[racer] += points
                        else:
                            data[racer] = points

                top_racers = sorted(data.items(), key=lambda x: x[1], reverse=True)[:10]

                message = "Top 10 Today: "
                for i, (racer, points) in enumerate(top_racers):
                    place = i + 1
                    message += "{} {} {} points{}".format("(" + str(place) + ")", racer, format(points, ','),
                                                          ", " if i < len(top_racers) - 1 else ".")

            await ctx.channel.send(message)
        except FileNotFoundError:
            print("File not found.")
            await ctx.channel.send(self.last_command_author + ": No races have been recorded today.")
        except Exception as e:
            pass
            print(e)

    @commands.command(name='top10races')
    async def top10races_command(self, ctx):
        data = {}
        for allraces in glob.glob(os.path.join(config.get_setting('directory'), "allraces_*.csv")):
            try:
                with open(allraces, 'r', encoding='utf-8', errors='ignore') as f:
                    reader = csv.reader(f)
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
                pass
                print(e)

        top_racers = sorted(data.items(), key=lambda x: x[1], reverse=True)[:10]
        message = "Top 10 Racers by Total Races: "
        for i, (racer, races) in enumerate(top_racers):
            place = i + 1
            message += "{} {} {} races{}".format("(" + str(place) + ")", racer, format(races, ','),
                                                 ", " if i < len(top_racers) - 1 else ".")

        await ctx.channel.send(message)

    @commands.command(name='top10wins')
    async def top10wins_command(self, ctx):
        data = {}
        for allraces in glob.glob(os.path.join(config.get_setting('directory'), "allraces_*.csv")):
            try:
                with open(allraces, 'r', encoding='utf-8', errors='ignore') as f:
                    reader = csv.reader(f)
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
                pass
                print(e)

        top_racers = sorted(data.items(), key=lambda x: x[1], reverse=True)[:10]
        message = "Top 10 Wins Season {}: ".format(config.get_setting('season'))
        for i, (racer, wins) in enumerate(top_racers):
            place = i + 1
            message += "{} {} {} wins{}".format("(" + str(place) + ")", racer, format(wins, ','),
                                                ", " if i < len(top_racers) - 1 else ".")

        await ctx.channel.send(message)

    @commands.command(name='top10season')
    async def top10season_command(self, ctx):
        data = {}
        for allraces in glob.glob(os.path.join(config.get_setting('directory'), "allraces_*.csv")):
            try:
                with open(allraces, 'r', encoding='utf-8', errors='ignore') as f:
                    reader = csv.reader(f)
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
                pass
                print(e)

        top_racers = sorted(data.items(), key=lambda x: x[1], reverse=True)[:10]
        message = "Top 10 Season {}: ".format(config.get_setting('season'))
        for i, (racer, points) in enumerate(top_racers):
            place = i + 1
            message += "{} {} {} points{}".format("(" + str(place) + ")", racer, format(points, ','),
                                                  ", " if i < len(top_racers) - 1 else ".")

        await bot.channel.send(message)

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
                    reader = csv.reader(f)
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
                await ctx.channel.send("No season races recorded yet")
                return
            except Exception as e:
                print(e)
                return

        if not world_record_stats:
            await ctx.channel.send("No world records found.")
            return

        # Sort by world record count first, and if tied, by total points (both descending)
        top_records = sorted(
            world_record_stats.items(),
            key=lambda x: (x[1]['count'], x[1]['points']),
            reverse=True
        )[:10]

        # Build the output message with each entry formatted as "Racer: count (points)"
        # and joined by " | " with no trailing pipe.
        entries = [f"{racer}: {stats['count']} ({stats['points']} pts)" for racer, stats in top_records]
        output_msg = " | ".join(entries)

        # Prepend the header to the message.
        final_msg = f"Top 10 World Record Wins: {output_msg}"

        await ctx.channel.send(final_msg)





    @commands.command(name='top10seasonnwr')
    async def top10seasonnwr_command(self, ctx):
        data = {}
        for allraces in glob.glob(os.path.join(config.get_setting('directory'), "allraces_*.csv")):
            try:
                with open(allraces, 'r', encoding='utf-8', errors='ignore') as f:
                    reader = csv.reader(f)
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
                print(e)

        top_racers = sorted(data.items(), key=lambda x: x[1], reverse=True)[:10]
        message = f"Top 10 Season {config.get_setting('season')} (Excluding WRs): "
        for i, (racer, points) in enumerate(top_racers):
            separator = ", " if i < len(top_racers) - 1 else "."
            message += f"({i+1}) {racer} {format(points, ',')} points{separator}"

        await ctx.channel.send(message)

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
            print(f"Failed to reconnect: {e}")
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
    base_directory = os.path.expanduser("~\\AppData\\Local\\MyStats\\")
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
                reader = csv.reader(f)
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
            print(f"An error occurred while processing the file {allraces}: {e}")
            print(e)

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


async def tilted(bot):
    last_modified_tilt = None
    run_id = None
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
            print(f"Error checking modification time: {e}")
            await asyncio.sleep(1)
            continue

        if last_modified_tilt is None:
            last_modified_tilt = current_modified_tilt
            print("Tilted monitoring initiated. System is ready to go!")
            await asyncio.sleep(1)
            continue

        if current_modified_tilt == last_modified_tilt:
            await asyncio.sleep(7)
            continue

        await asyncio.sleep(3)

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

            config.set_setting('tilt_current_level', str(current_level), persistent=False)
            config.set_setting('tilt_current_elapsed', str(elapsed_time), persistent=False)
            config.set_setting('tilt_current_top_tiltee', str(top_tiltee), persistent=False)

            if current_level == 1 and run_id is None:
                run_id = base64.urlsafe_b64encode(uuid.uuid4().bytes).rstrip(b'=').decode('utf-8')
                config.set_setting('tilt_run_started_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S'), persistent=False)
                config.set_setting('tilt_run_ledger', '{}', persistent=False)
                config.set_setting('tilt_top_tiltee_ledger', '{}', persistent=False)
                config.set_setting('tilt_current_top_tiltee_count', '0', persistent=False)
                config.set_setting('tilt_run_xp', '0', persistent=False)
                config.set_setting('tilt_run_points', '0', persistent=False)
                config.set_setting('tilt_previous_run_xp', config.get_setting('tilt_run_xp') or '0', persistent=False)
                config.set_setting('tilt_level_completion_overlay', '{}', persistent=False)
                config.set_setting('tilt_run_completion_overlay', '{}', persistent=False)
                current_tilt_points_leader = None

            if run_id is None:
                run_id = base64.urlsafe_b64encode(uuid.uuid4().bytes).rstrip(b'=').decode('utf-8')

            config.set_setting('tilt_current_run_id', run_id, persistent=False)

            try:
                run_ledger = json.loads(config.get_setting('tilt_run_ledger') or '{}')
                if not isinstance(run_ledger, dict):
                    run_ledger = {}
            except Exception:
                run_ledger = {}

            try:
                tilt_top_tiltee_ledger = json.loads(config.get_setting('tilt_top_tiltee_ledger') or '{}')
                if not isinstance(tilt_top_tiltee_ledger, dict):
                    tilt_top_tiltee_ledger = {}
            except Exception:
                tilt_top_tiltee_ledger = {}

            tilt_player_file = config.get_setting('tilt_player_file')
            tilt_rows = safe_read_csv_rows(tilt_player_file)
            player_data_rows = tilt_rows[1:] if len(tilt_rows) > 1 else []

            active_users = []
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

                active_users.append(username)
                try:
                    player_points = int(float(points_raw))
                except (TypeError, ValueError):
                    player_points = 0

                if player_points > 0:
                    survivors.append((username, player_points, row))
                    run_ledger[username] = int(run_ledger.get(username, 0)) + level_points
                else:
                    deaths_this_level += 1

            earned_xp = int(math.floor(len(survivors) * get_tilt_multiplier(current_level)))
            run_xp = get_int_setting('tilt_run_xp', 0) + earned_xp
            run_points = get_int_setting('tilt_run_points', 0) + (level_points if survivors else 0)
            total_xp_today = get_int_setting('tilt_total_xp_today', 0) + earned_xp
            total_deaths_today = get_int_setting('tilt_total_deaths_today', 0) + deaths_this_level

            best_run_xp_today = max(get_int_setting('tilt_best_run_xp_today', 0), run_xp)
            if best_run_xp_today != get_int_setting('tilt_best_run_xp_today', 0):
                config.set_setting('tilt_best_run_xp_today', str(best_run_xp_today), persistent=False)

            if survivors:
                highest_level_points_today = max(get_int_setting('tilt_highest_level_points_today', 0), level_points)
                highest_level_reached_num = max(get_int_setting('tilt_highest_level_reached_num', 0), current_level)
                season_best_level_num = max(get_int_setting('tilt_season_best_level_num', 0), current_level)
                personal_best_level_num = max(get_int_setting('tilt_personal_best_level_num', 0), current_level)
            else:
                highest_level_points_today = get_int_setting('tilt_highest_level_points_today', 0)
                highest_level_reached_num = get_int_setting('tilt_highest_level_reached_num', 0)
                season_best_level_num = get_int_setting('tilt_season_best_level_num', 0)
                personal_best_level_num = get_int_setting('tilt_personal_best_level_num', 0)

            config.set_setting('tilt_run_xp', str(run_xp), persistent=False)
            config.set_setting('tilt_run_points', str(run_points), persistent=False)
            config.set_setting('tilt_total_xp_today', str(total_xp_today), persistent=False)
            config.set_setting('tilt_total_deaths_today', str(total_deaths_today), persistent=False)
            config.set_setting('tilt_highest_level_points_today', str(highest_level_points_today), persistent=False)
            config.set_setting('tilt_highest_level_reached_num', str(highest_level_reached_num), persistent=False)
            config.set_setting('tilt_season_best_level_num', str(season_best_level_num), persistent=False)
            config.set_setting('tilt_personal_best_level_num', str(personal_best_level_num), persistent=False)
            config.set_setting('tilt_run_ledger', json.dumps(run_ledger), persistent=False)

            lifetime_expertise = get_int_setting('tilt_lifetime_expertise', 0)
            lifetime_base_xp = get_int_setting('tilt_lifetime_base_xp', 0)
            adjusted_total_xp = total_xp + lifetime_base_xp
            if adjusted_total_xp > lifetime_expertise:
                lifetime_expertise = adjusted_total_xp
            lifetime_expertise += earned_xp
            config.set_setting('tilt_lifetime_expertise', str(lifetime_expertise), persistent=False)

            if level_passed:
                tilt_levels_count += 1

                top_tiltee_run_count = 0
                if top_tiltee and top_tiltee != 'None':
                    top_tiltee_run_count = int(tilt_top_tiltee_ledger.get(top_tiltee, 0)) + 1
                    tilt_top_tiltee_ledger[top_tiltee] = top_tiltee_run_count
                config.set_setting('tilt_top_tiltee_ledger', json.dumps(tilt_top_tiltee_ledger), persistent=False)
                config.set_setting('tilt_current_top_tiltee_count', str(top_tiltee_run_count), persistent=False)

                tilts_results_file = config.get_setting('tilts_results_file')
                if not tilts_results_file:
                    create_results_files()
                    tilts_results_file = config.get_setting('tilts_results_file')

                try:
                    with open(tilts_results_file, 'a', newline='', encoding='utf-8') as tilts_file:
                        writer = csv.writer(tilts_file)
                        event_ids_tmp = config.get_setting('active_event_ids')
                        if event_ids_tmp is not None:
                            event_ids_tmp = event_ids_tmp.strip("[]").split(",")
                            event_ids = [int(event_id.strip().replace('"', '')) for event_id in event_ids_tmp if event_id.strip().replace('"', '').isdigit()]
                        else:
                            event_ids = [0]

                        for _, _, row in survivors:
                            is_top_tiltee = str(row[0]).strip().lower() == top_tiltee.lower()
                            data_to_write = [run_id, current_level] + row + [str(is_top_tiltee), event_ids]
                            writer.writerow(data_to_write)
                except Exception as e:
                    print(f"Error opening/writing to tilts_results_file: {e}")

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
                        if is_chat_response_enabled("chat_tilt_results"):
                            await send_chat_message(bot.channel, combined_narrative, category="tilt")
                        last_tilt_narrative_alert_level_count = tilt_levels_count

                finisher_names = [username for username, _, _ in survivors]
                limited_finishers = finisher_names[:get_chat_max_names()]
                base_msg = (
                    f"End of Tilt Level {current_level} | Level Completion Time: {elapsed_time} | "
                    f"Top Tiltee: {top_tiltee} | Points Earned: {level_points} | Survivors: "
                )

                if limited_finishers:
                    chunks = chunked_join_messages(base_msg, f"Level {current_level} Survivors: ", limited_finishers, max_length=max_message_length)
                    for chunk in chunks:
                        if is_chat_response_enabled("chat_tilt_results"):
                            await send_chat_message(bot.channel, chunk, category="tilt")
                    text_area.insert('end', f"\n{base_msg}{', '.join(limited_finishers)}\n")
                else:
                    print("No player data to send for current level.")

                total_active = len(active_users)
                survivor_count = len(survivors)
                death_rate = round(((deaths_this_level / total_active) * 100), 1) if total_active else 0
                survival_rate = round(((survivor_count / total_active) * 100), 1) if total_active else 0
                completion_summary = {
                    'completed_at': datetime.now().isoformat(timespec='seconds'),
                    'level': current_level,
                    'top_tiltee': top_tiltee,
                    'top_tiltee_count': top_tiltee_run_count,
                    'elapsed_time': elapsed_time,
                    'level_points': level_points,
                    'earned_xp': earned_xp,
                    'survivors': survivor_count,
                    'deaths': deaths_this_level,
                    'death_rate': death_rate,
                    'survival_rate': survival_rate,
                }
                config.set_setting('tilt_level_completion_overlay', json.dumps(completion_summary), persistent=False)

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
                    standings_items = [f"{username} - {points} points" for username, points in limited_run_results]
                    chunks = chunked_join_messages(
                        "Tilt run complete! Final standings: ",
                        "Run standings cont: ",
                        standings_items,
                        max_length=max_message_length
                    )
                    for chunk in chunks:
                        if is_chat_response_enabled("chat_tilt_results"):
                            await send_chat_message(bot.channel, chunk, category="tilt")
                    text_area.insert('end', f"\nTilt run complete! Final standings: {', '.join(standings_items)}\n")
                else:
                    if is_chat_response_enabled("chat_tilt_results"):
                        await send_chat_message(bot.channel, "Tilt run complete! No results to display.", category="tilt")
                    text_area.insert('end', f"\nTilt run complete! No results to display.\n")

                top_users_today = sorted(run_ledger.items(), key=lambda x: x[1], reverse=True)[:10]
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
                    'ended_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'ended_level': current_level,
                    'elapsed_time': elapsed_time,
                    'top_tiltee': top_tiltee,
                    'top_tiltee_count': get_int_setting('tilt_current_top_tiltee_count', 0),
                    'leader': {'name': top_user_names[0], 'points': int(top_users_today[0][1])} if top_users_today else None,
                    'run_points': run_points,
                    'run_xp': run_xp,
                    'best_run_xp_today': best_run_xp_today,
                    'total_xp_today': total_xp_today,
                    'total_deaths_today': total_deaths_today,
                    'standings': [{'name': name, 'points': int(points)} for name, points in top_users_today],
                }
                config.set_setting('tilt_last_run_summary', json.dumps(last_run_summary), persistent=False)
                config.set_setting('tilt_run_completion_overlay', json.dumps(last_run_summary), persistent=False)
                next_run_completion_event_id = get_int_setting('tilt_run_completion_event_id', 0) + 1
                config.set_setting('tilt_run_completion_event_id', str(next_run_completion_event_id), persistent=False)

                config.set_setting('tilt_previous_run_xp', str(run_xp), persistent=False)
                config.set_setting('tilt_current_run_id', '', persistent=False)
                config.set_setting('tilt_run_xp', '0', persistent=False)
                config.set_setting('tilt_run_points', '0', persistent=False)
                config.set_setting('tilt_run_ledger', '{}', persistent=False)
                config.set_setting('tilt_top_tiltee_ledger', '{}', persistent=False)
                config.set_setting('tilt_current_top_tiltee_count', '0', persistent=False)
                config.set_setting('tilt_level_completion_overlay', '{}', persistent=False)
                run_id = None
                current_tilt_points_leader = None

            last_modified_tilt = current_modified_tilt
        except Exception as e:
            print(f"An error occurred while processing the tilt file: {e}")

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
                        reader = csv.reader(checkpoint_file)
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
            print(f"Error in checkpoints task: {e}")
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

    if DEBUG == True:
        print('Debug: Read Map Data File')

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
        if DEBUG == True:
            print('Debug: Race file check')
        else:
            pass
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
                    if DEBUG == True:
                        print("Debug: Map file has not been modified; reusing cached map data.")

            except FileNotFoundError:
                print(f"Map data file {map_data_file} not found.")
            except Exception as e:
                print(f"An error occurred while processing the map data file: {e}")

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
                if DEBUG == True:
                    print('Debug: Read Race File')
                else:
                    pass

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
            if DEBUG == True:
                print('Debug: Calculating World Record')
            else:
                pass

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
            else:
                config.set_setting('wr', 'no', persistent=False)

            # first row with WR flagged
            if config.get_setting('wr').lower() == 'yes':
                if DEBUG == True:
                    print('Debug: World Record Detected, processing')
                else:
                    pass
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
            if DEBUG == True:
                print('Debug: Processing Race File Rows, Cleaning Data')
            else:
                pass
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

            with open(config.get_setting('allraces_file'), 'a', newline='', encoding='utf-8', errors='ignore') as f:
                writer = csv.writer(f)
                for row in racedata:
                    writer.writerow(row)

            if DEBUG == True:
                print('Debug: Write Race Data to Data File')
            else:
                pass

            race_counts = {row[1]: 0 for row in racedata}
            points_by_player = {}
            wins_by_player = {}
            with open(config.get_setting('allraces_file'), 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.reader(f)
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

            if DEBUG == True:
                print('Debug: Check for 120 Race Checkmark')
            else:
                pass

            for player_name, count in race_counts.items():
                if count == 120:
                    announcement_message = (
                        f"🎉 {player_name} has just completed their "
                        f"120th race today! Congratulations! 🎉"
                    )
                    if is_chat_response_enabled("chat_race_results"):
                        await send_chat_message(bot.channel, announcement_message, category="race")

            # MPL Code
            if DEBUG == True:
                print('Debug: Skipping MPL Code, Not MPL event')
            else:
                pass
            if config.get_setting('MPL') == 'True':
                checkpointdata = []
                with open(config.get_setting('checkpoint_file'), 'r', encoding='utf-8', errors='ignore') as f:
                    checkpointfile = csv.reader(f)
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
            if DEBUG == True:
                print('Debug: Checking for Chunk Alert Threshold')
            else:
                pass
            if int(first_row[3]) >= int(config.get_setting('chunk_alert_value')) and config.get_setting('chunk_alert') == 'True':
                audio_device = config.get_setting('audio_device')
                audio_file_path = config.get_setting('chunk_alert_sound')

                if audio_file_path:
                    play_audio_file(audio_file_path, device_name=audio_device)
                    if DEBUG == True:
                        print('Debug: Play Chunk Alert Audio')
                    else:
                        pass

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
                with open('HighScore.txt', 'w', encoding='utf-8', errors='ignore') as hs:
                    hs.write(str(config.get_setting('hscore_name')) + '\n')
                    hs.write(str(br_hscore_format + '\n'))

            if current_score > int(config.get_setting('race_hs_season')):
                config.set_setting('race_hs_season', current_score, persistent=False)

            if current_score > int(config.get_setting('race_hs_today')):
                config.set_setting('race_hs_today', current_score, persistent=False)

            if DEBUG == True:
                print('Debug: Process High Score check')
            else:
                pass

            # Write last winners
            lastwinner1 = ""
            lastwinnerh = ""

            for i in range(len(racedata)):
                place = racedata[i][0]
                lastwinner1 += "{} {} {} point{} \n".format("(" + str(place) + ")", racedata[i][2], racedata[i][3],
                                                         "s" if int(racedata[i][3]) != 1 else "")
                lastwinnerh += "{} {} {} point{}".format("(" + str(place) + ")", racedata[i][2], racedata[i][3],
                                                         "s" if int(racedata[i][3]) != 1 else "")

            with open('LatestWinner.txt', 'w', encoding='utf-8', errors='replace') as lw:
                lw.write("Previous Winners:" + '\n')
                lw.write(lastwinner1 + '\n')

            with open('LatestWinner_horizontal.txt', 'w', encoding='utf-8', errors='replace') as lwh:
                lwh.write("Previous Winners:" + lastwinnerh)

            config.set_setting('totalpointstoday', t_points, persistent=False)
            config.set_setting('totalcounttoday', t_count, persistent=False)
            config.set_setting('totalpointsseason', s_t_points, persistent=False)
            config.set_setting('totalcountseason', s_t_count, persistent=False)
            update_config_labels()

            if config.get_setting('totalpointstoday') != 0:
                avgptstoday = int(config.get_setting('totalpointstoday')) / int(config.get_setting('totalcounttoday'))
            else:
                avgptstoday = 0

            config.set_setting('avgpointstoday', avgptstoday, persistent=False)

            # Add color tags for the text widget
            if DEBUG == True:
                print('Debug: Calculate colors for application output')
            else:
                pass
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
            if DEBUG == True:
                print('Debug: Display Winners in Application')
            else:
                pass
            display_race_winners(text_area, marbcount, namecolordata, nowinner)

            # Prepare messages for Twitch chat
            messages = []

            narrative_messages = []
            if not nowinner and is_chat_response_enabled("chat_narrative_alerts"):
                winner_username = first_row[1]
                winner_display_name = first_row[2] if first_row[1] != first_row[2].lower() else first_row[1]

                if is_chat_response_enabled("narrative_alert_grinder_enabled"):
                    winner_race_count = race_counts.get(winner_username, 0)
                    if winner_race_count in (10, 25, 50, 75, 100):
                        narrative_messages.append(
                            f"🏁 Grinder: {winner_display_name} hit race #{winner_race_count} today"
                        )

                if is_chat_response_enabled("narrative_alert_winmilestone_enabled"):
                    winner_win_count = wins_by_player.get(winner_username, 0)
                    if winner_win_count in (3, 5, 10, 15):
                        narrative_messages.append(
                            f"🏆 Win Milestone: {winner_display_name} reached win #{winner_win_count} today"
                        )

                if is_chat_response_enabled("narrative_alert_leadchange_enabled") and points_by_player:
                    sorted_points = sorted(points_by_player.items(), key=lambda item: item[1], reverse=True)
                    leader_username, leader_points = sorted_points[0]
                    second_place_points = sorted_points[1][1] if len(sorted_points) > 1 else 0
                    lead_gap = leader_points - second_place_points
                    min_lead_gap = max(0, get_int_setting("narrative_alert_min_lead_change_points", 500))
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
                cooldown_races = max(0, get_int_setting("narrative_alert_cooldown_races", 3))
                max_items = max(1, get_int_setting("narrative_alert_max_items", 3))
                if cooldown_races == 0 or (t_count - last_narrative_alert_race_count) >= cooldown_races:
                    combined_narrative = "📣 Player Alerts: " + " | ".join(narrative_messages[:max_items]) + "."
                    messages.append(combined_narrative)
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
                            line = f"({data[0]}) {winner_name}"
                            if i < len(filtered_top10_data) - 1:
                                line += ", "
                            else:
                                line += "."

                            # Check the length before appending
                            if len(message + line) > 480:
                                temp_messages.append(message.rstrip(', '))
                                # Start a new message with the same prefix (or some short prefix, your choice)
                                message = "🧃 Top 10 Finishers 🏆: " + line
                            else:
                                message += line

                        # Append the last chunk
                        temp_messages.append(message.rstrip(', '))
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
                            line = f"({data[0]}) {winner_name} {formatted_points} point"
                            if int(data[4]) != 1:
                                line += "s"
                            # Add comma or period
                            if i < len(filtered_data) - 1:
                                line += ", "
                            else:
                                line += "."

                            # Check length before appending
                            if len(message + line) > 480:
                                temp_messages.append(message.rstrip(', '))
                                message = prefix + line  # Start fresh with the same prefix
                            else:
                                message += line

                        temp_messages.append(message.rstrip(', '))
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
                            line = f"({data[0]}) {winner_name}"
                            if i < len(filtered_top10_data) - 1:
                                line += ", "
                            else:
                                line += "."

                            if len(message + line) > 480:
                                temp_messages.append(message.rstrip(', '))
                                message = "Top 10 Finishers 🏆: " + line
                            else:
                                message += line

                        temp_messages.append(message.rstrip(', '))
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
                            line = f"({data[0]}) {winner_name} {formatted_points} point"
                            if int(data[4]) != 1:
                                line += "s"
                            if i < len(filtered_data) - 1:
                                line += ", "
                            else:
                                line += "."

                            if len(message + line) > 480:
                                temp_messages.append(message.rstrip(', '))
                                message = prefix + line
                            else:
                                message += line

                        temp_messages.append(message.rstrip(', '))
                        messages.extend(temp_messages)


            # ---- After building up messages, do config updates, etc. ----
            config.set_setting('totalpointstoday', t_points, persistent=False)
            config.set_setting('totalcounttoday', t_count, persistent=False)
            config.set_setting('totalpointsseason', s_t_points, persistent=False)
            config.set_setting('totalcountseason', s_t_count, persistent=False)

            if config.get_setting('totalpointstoday') != 0:
                avgptstoday = int(config.get_setting('totalpointstoday')) / int(config.get_setting('totalcounttoday'))
            else:
                avgptstoday = 0

            config.set_setting('avgpointstoday', avgptstoday, persistent=False)

            cycle_events = update_mycycle_with_race_rows(racedata)
            if is_chat_response_enabled('mycycle_announcements_enabled'):
                for event in cycle_events:
                    messages.append(
                        f"🔁 {event['display_name']} completed a MyCycle in {event['session_name']}! "
                        f"Cycle #{event['cycles_completed']} took {event['races_used']} races."
                    )

            messages.extend(get_season_quest_updates())

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

    def add_color_tag(widget, tag_name, color):
        widget.tag_configure(tag_name, foreground=color)

    def insert_colored_text(text_area, text, tag_name):
        text_area.insert(tk.END, text, tag_name)

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
        if DEBUG == True:
            print('Debug: BR file check')
        else:
            pass
        try:
            current_modified_royale = await asyncio.to_thread(os.path.getmtime, config.get_setting('br_file'))
        except FileNotFoundError:
            continue
        if last_modified_royale is None:
            last_modified_royale = current_modified_royale
            print("Royale monitoring initiated. System is ready to go!")
            continue

        timestamp, timestampMDY, timestampHMS, adjusted_time = time_manager.get_adjusted_time()

        if current_modified_royale != last_modified_royale:
            await asyncio.sleep(3)
            brdata = []
            metadata = []
            total = 0
            winner = ''
            crownwin = False
            last_br_winner = config.get_setting('last_br_winner')
            t_points = int(config.get_setting('totalpointstoday'))
            t_count = int(config.get_setting('totalcounttoday'))
            s_t_points = int(config.get_setting('totalpointsseason'))
            s_t_count = int(config.get_setting('totalcountseason'))
            last_modified_royale = current_modified_royale

            # Initialize br_winner to None before processing
            br_winner = None  # Add this line

            max_retries = 3  # Number of retry attempts
            retry_delay = 2  # Delay between retries (in seconds)
            attempts = 0  # Track the number of attempts
            lines = None  # Initialize lines variable

            while attempts < max_retries:
                try:
                    # First, attempt to open the br_file and read it as binary to detect encoding
                    with open(config.get_setting('br_file'), 'rb') as f:
                        data = f.read()

                    # Detect the file encoding using chardet
                    result = chardet.detect(data)
                    encoding = result['encoding']

                    # Open the file using the detected encoding and read the lines
                    with open(config.get_setting('br_file'), 'r', encoding=encoding, errors='ignore') as f:
                        lines = f.readlines()

                    # If file reading is successful, break out of the retry loop
                    break

                except PermissionError as e:
                    attempts += 1
                    print(f"Permission denied: {e}. Retrying in {retry_delay} seconds... (Attempt {attempts}/{max_retries})")
                    time.sleep(retry_delay)  # Wait before retrying

                except Exception as e:
                    attempts += 1
                    print(f"An error occurred: {e}. Retrying in {retry_delay} seconds... (Attempt {attempts}/{max_retries})")
                    time.sleep(retry_delay)

            # After retry attempts, handle failure if the file could not be opened
            if attempts == max_retries or lines is None:
                print(f"Failed to open the file after {max_retries} attempts.")
            else:
                # Ensure that lines is not empty before accessing elements
                if lines:
                    # Process the header
                    header = lines[0].replace('\x00', '').strip().split(',')

                    marbcount = len(lines)

                    # Handle active_event_ids
                    event_ids_tmp = config.get_setting('active_event_ids')

                    if event_ids_tmp is not None:
                        event_ids_tmp = event_ids_tmp.strip("[]").split(",")
                        event_ids = [int(id.strip().replace('"', '')) for id in event_ids_tmp if id.strip().replace('"', '').isdigit()]
                    else:
                        event_ids = [0]

                    brdata = []  # Initialize brdata

                    # Process each line, starting from the second line (skip header)
                    for line in lines[1:]:
                        # Clean and split the line
                        cleaned_line = line.replace('\x00', '').strip().split(',')

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

                            if br_winner[1] == last_br_winner:
                                crownwin = True
                            else:
                                crownwin = False
                            config.set_setting('last_br_winner', br_winner[1], persistent=False)

                            t_count += 1
                            s_t_count += 1

                else:
                    print("The file is empty or could not be processed.")

                # Check if br_winner is assigned before using it
                if br_winner is not None and len(br_winner) >= 5 and br_winner[4]:
                    t_points += int(br_winner[4])
                    s_t_points += int(br_winner[4])

                    with open(config.get_setting('allraces_file'), 'a', newline='', encoding='utf-8',
                              errors='ignore') as f:
                        writer = csv.writer(f)
                        writer.writerows(brdata)

                    race_counts = {row[1]: 0 for row in brdata}

                    with open(config.get_setting('allraces_file'), 'r', encoding='utf-8', errors='ignore') as f:
                        reader = csv.reader(f)
                        for row in reader:
                            if row[1] in race_counts:
                                race_counts[row[1]] += 1

                    for player_name, count in race_counts.items():
                        if count == 120:
                            announcement_message = (
                                f"🎉 {player_name} has just completed their "
                                f"120th race today! Congratulations! 🎉"
                            )
                            if is_chat_response_enabled("chat_br_results"):
                                await send_chat_message(bot.channel, announcement_message, category="br")

                    if int(br_winner[4]) >= int(config.get_setting('chunk_alert_value')) and config.get_setting(
                            'chunk_alert') == 'True':
                        audio_device = config.get_setting('audio_device')
                        audio_file_path = config.get_setting('chunk_alert_sound')

                        if audio_file_path:
                            play_audio_file(audio_file_path, device_name=audio_device)
                            if DEBUG == True:
                                print('Debug: Audio Chunk Alert Played')
                                print('Points for winner ' + str(br_winner[4]))
                            else:
                                pass

                    if br_winner[1] != br_winner[2].lower():
                        winnersname = br_winner[1]
                    else:
                        winnersname = br_winner[2]

                    current_score = int(br_winner[4])

                    if current_score > int(config.get_setting('hscore')):
                        config.set_setting('hscore_name', winnersname, persistent=False)
                        config.set_setting('hscore', current_score, persistent=False)
                        br_hscore = int(config.get_setting('hscore'))
                        br_hscore_format = format(br_hscore, ',')
                        with open('HighScore.txt', 'w', encoding='utf-8', errors='ignore') as hs:
                            hs.write(str(config.get_setting('hscore_name')) + '\n')
                            hs.write(str(br_hscore_format + '\n'))

                    if current_score > int(config.get_setting('br_hs_season')):
                        config.set_setting('br_hs_season', current_score, persistent=False)

                    if current_score > int(config.get_setting('br_hs_today')):
                        config.set_setting('br_hs_today', current_score, persistent=False)
                    if DEBUG == True:
                        print('Debug: High Score File Updated')
                    else:
                        pass
                    lastwinner1 = ""

                    if br_winner[1] != br_winner[2].lower():
                        lastwinner1 = "{} ({}) with {} points, ".format(br_winner[2], br_winner[1], br_winner[4])
                    else:
                        lastwinner1 = "{} with {} points, ".format(br_winner[2], br_winner[4])

                    lastwinner2 = "{} kills and {} damage.".format(br_winner[6], br_winner[7])

                    with open('LatestWinner.txt', 'w', encoding='utf-8', errors='ignore') as hs:
                        hs.write("Previous Winner:" + '\n')
                        hs.write(lastwinner1 + '\n')
                        hs.write(lastwinner2 + '\n')

                    with open('LatestWinner_horizontal.txt', 'w', encoding='utf-8', errors='replace') as lwh:
                        lwh.write("Previous Winner: " + lastwinner1 + lastwinner2)
                        if DEBUG == True:
                            print('Debug: Latest Winner File Updated')
                        else:
                            pass

                    if config.get_setting('totalpointstoday') != 0:
                        avgptstoday = t_points / t_count
                    else:
                        avgptstoday = 0

                    config.set_setting('avgpointstoday', avgptstoday, persistent=False)
                    config.set_setting('totalpointstoday', t_points, persistent=False)
                    config.set_setting('totalcounttoday', t_count, persistent=False)
                    config.set_setting('totalpointsseason', s_t_points, persistent=False)
                    config.set_setting('totalcountseason', s_t_count, persistent=False)
                    update_config_labels()
                    if DEBUG == True:
                        print('Debug: Counts and Points Updated in UI and Config Manager')
                    else:
                        pass
                    winnertotalpoints = 0
                    wcount = 0
                    totalcount = 0

                    try:
                        with open(config.get_setting('allraces_file'), 'r', encoding='utf-8', errors='ignore') as f:
                            reader = csv.reader(f)
                            for row in reader:
                                if row[1] == winnersname.lower():
                                    winnertotalpoints += int(row[3])
                                    if row[0] == '1':
                                        wcount += 1
                                if row[1] == br_winner[1]:
                                    totalcount += 1
                    except FileNotFoundError:
                        print("File not found. " + config.get_setting('allraces_file'))
                        with open(config.get_setting('allraces_file'), 'w', encoding='utf-8', errors='ignore'):
                            pass
                    except Exception as e:
                        print("An error occurred while processing the file:", e)

                    if br_winner[1] != br_winner[2].lower():
                        wname = br_winner[1]
                    else:
                        wname = br_winner[2]
                    wpoints = '{:,}'.format(int(br_winner[4]))
                    wkills = br_winner[6]
                    wdam = br_winner[7]

                    if DEBUG == True:
                        print(config.get_setting('chunk_alert'))
                        print(int(config.get_setting('chunk_alert_value')))
                        print(str(wpoints))
                        print(str(crownwin))
                    else:
                        pass

                    if int(br_winner[4]) >= int(config.get_setting('chunk_alert_value')) and config.get_setting(
                            'chunk_alert') == 'True':
                        if DEBUG == True:
                            print('Debug: Chunk Alert: True, Winner Points: ' + str(wpoints))
                        else:
                            pass
                        if crownwin:
                            if DEBUG == True:
                                print('Debug: Chunk Alert: True, Crown Win: True')
                            else:
                                pass
                            if br_winner[1] != br_winner[2].lower():
                                message = "🧃 CROWN WIN! 👑: {}({}) | {} points | {} eliminations | {} damage | ".format(
                                    br_winner[2], br_winner[1], '{:,}'.format(int(br_winner[4])), br_winner[6],
                                    br_winner[7]) + "Today's stats: " + str(
                                    '{:,}'.format(int(winnertotalpoints))) + " points | " + str(
                                    wcount) + " wins | " + " " + str('{:,}'.format(int(totalcount))) + " races"
                            else:
                                message = "🧃 CROWN WIN! 👑: {} | {} points | {} eliminations | {} damage | ".format(
                                    br_winner[2], '{:,}'.format(int(br_winner[4])), br_winner[6],
                                    br_winner[7]) + "Today's stats: " + str(
                                    '{:,}'.format(int(winnertotalpoints))) + " points | " + str(
                                    wcount) + " wins | " + " " + str('{:,}'.format(int(totalcount))) + " races"
                        else:
                            if br_winner[1] != br_winner[2].lower():
                                message = "🧃 Battle Royale Champion 🏆: {}({}) | {} points | {} eliminations | {} damage | ".format(
                                    br_winner[2], br_winner[1], '{:,}'.format(int(br_winner[4])), br_winner[6],
                                    br_winner[7]) + "Today's stats: " + str(
                                    '{:,}'.format(int(winnertotalpoints))) + " points | " + str(
                                    wcount) + " wins | " + " " + str('{:,}'.format(int(totalcount))) + " races"
                            else:
                                message = "🧃 Battle Royale Champion 🏆: {} | {} points | {} eliminations | {} damage | ".format(
                                    br_winner[2], '{:,}'.format(int(br_winner[4])), br_winner[6],
                                    br_winner[7]) + "Today's stats: " + str(
                                    '{:,}'.format(int(winnertotalpoints))) + " points | " + str(
                                    wcount) + " wins | " + " " + str('{:,}'.format(int(totalcount))) + " races"
                    else:
                        if crownwin:
                            if br_winner[1] != br_winner[2].lower():
                                message = "CROWN WIN! 👑: {}({}) | {} points | {} eliminations | {} damage | ".format(
                                    br_winner[2], br_winner[1], '{:,}'.format(int(br_winner[4])), br_winner[6],
                                    br_winner[7]) + "Today's stats: " + str(
                                    '{:,}'.format(int(winnertotalpoints))) + " points | " + str(
                                    wcount) + " wins | " + " " + str('{:,}'.format(int(totalcount))) + " races"
                            else:
                                message = "CROWN WIN! 👑: {} | {} points | {} eliminations | {} damage | ".format(
                                    br_winner[2], '{:,}'.format(int(br_winner[4])), br_winner[6],
                                    br_winner[7]) + "Today's stats: " + str(
                                    '{:,}'.format(int(winnertotalpoints))) + " points | " + str(
                                    wcount) + " wins | " + " " + str('{:,}'.format(int(totalcount))) + " races"
                        else:
                            if br_winner[1] != br_winner[2].lower():
                                message = "Battle Royale Champion 🏆: {}({}) | {} points | {} eliminations | {} damage | ".format(
                                    br_winner[2], br_winner[1], '{:,}'.format(int(br_winner[4])), br_winner[6],
                                    br_winner[7]) + "Today's stats: " + str(
                                    '{:,}'.format(int(winnertotalpoints))) + " points | " + str(
                                    wcount) + " wins | " + " " + str('{:,}'.format(int(totalcount))) + " races"
                            else:
                                message = "Battle Royale Champion 🏆: {} | {} points | {} eliminations | {} damage | ".format(
                                    br_winner[2], '{:,}'.format(int(br_winner[4])), br_winner[6],
                                    br_winner[7]) + "Today's stats: " + str(
                                    '{:,}'.format(int(winnertotalpoints))) + " points | " + str(
                                    wcount) + " wins | " + " " + str('{:,}'.format(int(totalcount))) + " races"
                    if DEBUG == True:
                        print('Debug: Chat Message Created, Not Sent')
                    else:
                        pass
                    if config.get_setting('announcedelay') == 'True':
                        if DEBUG == True:
                            print('Debug: Announcement Delay: True')
                        else:
                            pass
                        await send_chat_message(bot.channel, message, category="br", apply_delay=True)
                        write_overlays()
                    else:
                        if DEBUG == True:
                            print('Debug: Announcement Delay: False')
                        else:
                            pass
                        await send_chat_message(bot.channel, message, category="br")
                        write_overlays()

                    cycle_events = update_mycycle_with_race_rows(brdata)
                    if is_chat_response_enabled('mycycle_announcements_enabled'):
                        for event in cycle_events:
                            await send_chat_message(
                                bot.channel,
                                f"🔁 {event['display_name']} completed a MyCycle in {event['session_name']}! "
                                f"Cycle #{event['cycles_completed']} took {event['races_used']} races.",
                                category="br"
                            )

                    for quest_message in get_season_quest_updates():
                        await send_chat_message(bot.channel, quest_message, category="br")

                    if crownwin:
                        # Determine the name color based on the br_winner color code
                        if br_winner[3] == '6E95FFFF':
                            namecolor = "blue"
                        elif br_winner[3] == 'F91ED2FF':
                            namecolor = "magenta"
                        elif br_winner[3] == 'FF82D6FF':  # Change to violet
                            namecolor = "violet"
                        elif br_winner[3] == '79FFC7FF':
                            namecolor = "green"
                        elif br_winner[3] == 'F88688FF':
                            namecolor = "red"
                        elif br_winner[3] == 'DA6700FF':
                            namecolor = "orange"
                        else:
                            namecolor = "white"
                        display_battle_royale_crownwinner(text_area, marbcount, wname, wpoints, wkills, wdam, wcount,
                                                          winnertotalpoints, namecolor)

                    else:
                        # Determine the name color based on the br_winner color code
                        if br_winner[3] == '6E95FFFF':
                            namecolor = "blue"
                        elif br_winner[3] == 'F91ED2FF':
                            namecolor = "magenta"
                        elif br_winner[3] == 'FF82D6FF':  # Change to violet
                            namecolor = "violet"
                        elif br_winner[3] == '79FFC7FF':
                            namecolor = "green"
                        elif br_winner[3] == 'F88688FF':
                            namecolor = "red"
                        elif br_winner[3] == 'DA6700FF':
                            namecolor = "orange"
                        else:
                            namecolor = "white"
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
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        bot = Bot()
        bot.run()


    # Start the bot in a separate thread
    import threading

    bot_thread = threading.Thread(target=start_bot, daemon=True)
    bot_thread.start()

    # Run the Tkinter application
    root.mainloop()
