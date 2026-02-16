import time
import tkinter as tk
from tkinter import ttk
from tkinter import Menu
from tkinter import filedialog
from tkinter import messagebox
from tkcalendar import DateEntry
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
from flask import Flask, request, redirect
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
from colorama import init, Fore, Style
import atexit
import webbrowser
from datetime import datetime, timedelta
from twitchio.ext.commands.errors import CommandNotFound
import sounddevice as sd
import soundfile as sf
import pandas as pd
import babel
from babel import numbers
from twitchio import errors
from io import BytesIO
from dateutil import parser
from datetime import datetime, timedelta
import atexit
import socket
import subprocess
import importlib.util

# Global Variables
version = '5.7.0'
text_widget = None
bot = None
GLOBAL_SOCKET = None
DEBUG = False
HAS_TTKBOOTSTRAP = importlib.util.find_spec("ttkbootstrap") is not None


def create_root_window():
    """Create the root window, preferring ttkbootstrap when installed."""
    if HAS_TTKBOOTSTRAP:
        ttkbootstrap_module = __import__("ttkbootstrap")
        root_window = ttkbootstrap_module.Window(themename="flatly")
        style = root_window.style
    else:
        root_window = tk.Tk()
        style = ttk.Style(root_window)
        style.theme_use("clam")

    return root_window, style


def apply_ui_styles(style):
    """Central app styles for consistent spacing and typography."""
    style.configure("App.TFrame", padding=6)
    style.configure("Card.TLabelframe", padding=10)
    style.configure("Card.TLabelframe.Label", font=("Segoe UI", 10, "bold"))
    style.configure("Heading.TLabel", font=("Segoe UI", 16, "bold"))
    style.configure("Small.TLabel", font=("Segoe UI", 8))
    style.configure("Primary.TButton", padding=6)


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

# Twitch App Credentials
CLIENT_ID = 'icdintxz5c3h9twd6v3rntautv2o9g'
CLIENT_SECRET = 'qxyur2g933mst8uwaqzzto98t9zuwl'
REDIRECT_URI = 'http://localhost:5000/callback'


# Function to start Flask server
def run_flask():
    app.run(port=5000, debug=False, use_reloader=False)


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
    url = (
        f"https://id.twitch.tv/oauth2/authorize?response_type=code&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}&scope=chat:read chat:edit&force_verify=true"
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

    token_url = "https://id.twitch.tv/oauth2/token"
    token_data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri': REDIRECT_URI
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
    settings_window.attributes('-topmost', False)  # Temporarily remove topmost attribute
    file_path = tk.filedialog.askopenfilename(initialdir=initial_dir, title="Select Sound File",
                                              filetypes=[("Audio Files", "*.mp3;*.wav;*.ogg")])
    settings_window.attributes('-topmost', True)  # Restore topmost attribute
    if file_path:
        update_chunk_alert_audio_label(chunk_alert_label, file_path)
        settings_window.lift()  # Bring settings window back to the front


# Function to select the reset audio file
def select_reset_audio_sound(reset_audio_label, settings_window):
    initial_dir = os.path.expandvars(r"%localappdata%\\mystats\\sound files\\")
    settings_window.attributes('-topmost', False)  # Temporarily remove topmost attribute
    file_path = tk.filedialog.askopenfilename(initialdir=initial_dir, title="Select Sound File",
                                              filetypes=[("Audio Files", "*.mp3;*.wav;*.ogg")])
    settings_window.attributes('-topmost', True)  # Restore topmost attribute
    if file_path:
        update_reset_audio_label(reset_audio_label, file_path)
        settings_window.lift()  # Bring settings window back to the front


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
    # Create a new Toplevel window
    settings_window = tk.Toplevel(root)
    settings_window.title("Settings")

    # Make the settings window stay on top of the main window
    settings_window.transient(root)
    settings_window.attributes('-topmost', True)

    # Get the main window's position and size
    main_x = root.winfo_x()
    main_y = root.winfo_y()
    main_width = root.winfo_width()
    main_height = root.winfo_height()

    # Calculate the position for the settings window to be centered
    window_width = 475  # Set to 475 pixels wide
    window_height = 400
    pos_x = main_x + (main_width // 2) - (window_width // 2)
    pos_y = main_y + (main_height // 2) - (window_height // 2)

    center_toplevel(settings_window, window_width, window_height)

    # Create a frame to contain the canvas and scrollbar
    frame_with_scrollbar = ttk.Frame(settings_window, style="App.TFrame")
    frame_with_scrollbar.pack(fill="both", expand=True)

    # Create a Canvas and Scrollbar
    canvas = tk.Canvas(frame_with_scrollbar)
    scrollbar = tk.Scrollbar(frame_with_scrollbar, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas)

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")
        )
    )

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    # Pack the Canvas and Scrollbar
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # Create a top frame to hold individual frames for Channel, Marble Day, and Season
    top_frame = ttk.Frame(scrollable_frame, style="App.TFrame")
    top_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=5, sticky='ew')

    # Create individual frames for each item
    channel_frame = ttk.Frame(top_frame, style="App.TFrame")
    channel_frame.grid(row=0, column=0, padx=10, pady=(0, 5))

    marble_day_frame = ttk.Frame(top_frame, style="App.TFrame")
    marble_day_frame.grid(row=0, column=1, padx=10, pady=(0, 5))

    season_frame = ttk.Frame(top_frame, style="App.TFrame")
    season_frame.grid(row=0, column=2, padx=10, pady=(0, 5))

    # Configure the grid to center the frames without expansion
    top_frame.grid_columnconfigure(0, weight=1)
    top_frame.grid_columnconfigure(1, weight=1)
    top_frame.grid_columnconfigure(2, weight=1)

    # Add Channel label and entry to channel_frame
    channel_label = ttk.Label(channel_frame, text="Channel")
    channel_label.pack(anchor="center")

    channel_entry = ttk.Entry(channel_frame, width=16, justify="center")
    channel_entry.pack(anchor="center")
    channel_entry.insert(0, config.get_setting("CHANNEL"))

    # Add a label for "Marble Day"
    marble_day_text_label = ttk.Label(marble_day_frame, text="Marble Day")
    marble_day_text_label.pack(anchor="center")

    # Add a label to display the marble day value
    marble_day_value = config.get_setting("marble_day")  # Get the current marble day value
    marble_day_value_label = ttk.Label(marble_day_frame, text=marble_day_value, anchor="center")
    marble_day_value_label.pack(anchor="center")


    # Add a label for "Season"
    season_text_label = ttk.Label(season_frame, text="Season")
    season_text_label.pack(anchor="center")

    # Add a label to display the season value
    season_value = config.get_setting("season")  # Get the current season value
    season_label = ttk.Label(season_frame, text=season_value, anchor="center")
    season_label.pack(anchor="center")


    # Create a middle frame to hold the chunk alert settings and other frames
    middle_frame = ttk.Frame(scrollable_frame, style="App.TFrame")
    middle_frame.grid(row=1, column=0, columnspan=2, pady=(0, 10), sticky="nsew")

    # Configure the grid to distribute space equally among the three rows
    middle_frame.grid_rowconfigure(0, weight=1)

    # Create a frame for Chunk Alert settings inside the middle_frame
    chunk_alert_frame = ttk.LabelFrame(middle_frame, text="Chunk Alert", style="Card.TLabelframe")
    chunk_alert_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

    # Convert the config value to a boolean
    chunk_alert_value = config.get_setting("chunk_alert") == 'True'

    # Chunk Alert Toggle Button (first item)
    chunk_alert_button = tk.Button(
        chunk_alert_frame,
        text="ON" if chunk_alert_value else "OFF",
        command=lambda: toggle_chunk_alert(chunk_alert_button),
        bg="green" if chunk_alert_value else "red",
        width=8,
        font=("Arial", 10)
    )
    chunk_alert_button.pack(anchor="center", pady=(5, 5))

    # Add the Chunk Alert Trigger label (second item)
    chunk_alert_trigger_label = ttk.Label(chunk_alert_frame, text="Trigger Amt", style="Small.TLabel")
    chunk_alert_trigger_label.pack(anchor="center", pady=(5, 0))

    # Entry for the Chunk Alert Trigger value (third item)
    chunk_alert_trigger_entry = ttk.Entry(chunk_alert_frame, width=10, justify='center')
    chunk_alert_trigger_entry.pack(anchor="center", pady=(5, 5))
    chunk_alert_trigger_entry.insert(0, config.get_setting("chunk_alert_value"))

    # Chunk Alert Settings label (fourth item)
    chunk_alert_label = ttk.Label(chunk_alert_frame, text="No file selected", anchor="center", style="Small.TLabel")
    chunk_alert_label.pack(anchor="center", pady=(5, 5))

    # Create a frame for the file and test buttons (fifth item, side by side)
    file_button_frame = ttk.Frame(chunk_alert_frame, style="App.TFrame")
    file_button_frame.pack(anchor="center", pady=(5, 0))

    # File selection button with file folder emoji, centered
    file_button = ttk.Button(
        file_button_frame,
        text="📁",
        command=lambda: select_chunk_alert_sound(chunk_alert_label, settings_window),
        width=3
    )
    file_button.pack(side="left", padx=5)

    # New test audio playback button with speaker emoji, centered
    test_audio_button = ttk.Button(
        file_button_frame,
        text="🔊",
        command=test_chunkaudio_playback,
        width=3
    )
    test_audio_button.pack(side="left", padx=5)

    # Set the label to the saved file name if it exists when the settings window is opened
    saved_chunk_alert_file_path = config.get_setting("chunk_alert_sound")
    if saved_chunk_alert_file_path:
        update_chunk_alert_audio_label(chunk_alert_label, saved_chunk_alert_file_path)

    # Create a frame for Message Delay settings inside the middle_frame
    message_delay_frame = ttk.LabelFrame(middle_frame, text="Message Delay", style="Card.TLabelframe")
    message_delay_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

    # Announce Delay toggle button (first item)
    announce_delay_value = config.get_setting("announcedelay") == "True"
    announce_delay_button = tk.Button(
        message_delay_frame,
        text="ON" if announce_delay_value else "OFF",
        command=lambda: toggle_announce_delay(announce_delay_button),
        bg="green" if announce_delay_value else "red",
        width=8,
        font=("Arial", 10)
    )
    announce_delay_button.pack(anchor="center", pady=(5, 5))

    # Delay Seconds label (second item)
    delay_seconds_label = ttk.Label(message_delay_frame, text="Delay Seconds", style="Small.TLabel")
    delay_seconds_label.pack(anchor="center", pady=(5, 0))

    # Delay Seconds entry box (third item)
    delay_seconds_entry = ttk.Entry(message_delay_frame, width=10, justify='center')
    delay_seconds_entry.pack(anchor="center", pady=(5, 5))
    delay_seconds_entry.insert(0, config.get_setting("announcedelayseconds"))

    # Create a new frame for Marbles Reset Settings inside the middle_frame
    marbles_reset_frame = ttk.LabelFrame(middle_frame, text="Marbles Reset", style="Card.TLabelframe")
    marbles_reset_frame.grid(row=0, column=2, padx=10, pady=10, sticky="nsew")

    # Reset Audio Toggle Button (first item)
    reset_audio_value = config.get_setting("reset_audio") == "True"
    reset_audio_button = tk.Button(
        marbles_reset_frame,
        text="ON" if reset_audio_value else "OFF",
        command=lambda: toggle_reset_audio(reset_audio_button),
        bg="green" if reset_audio_value else "red",
        width=8,
        font=("Arial", 10)
    )
    reset_audio_button.pack(anchor="center", pady=(5, 5))

    # Reset Audio Label (second item)
    reset_audio_label = ttk.Label(marbles_reset_frame, text="No file selected", anchor="center", style="Small.TLabel")
    reset_audio_label.pack(anchor="center", pady=(5, 5))

    # Create a frame for side-by-side buttons (third item)
    reset_button_frame = ttk.Frame(marbles_reset_frame, style="App.TFrame")
    reset_button_frame.pack(anchor="center", pady=(5, 0))

    # Placeholder button for potential testing or other functionality
    test_reset_button = ttk.Button(
        reset_button_frame,
        text="📁",  # Placeholder button, can be replaced with actual functionality
        command=lambda: select_reset_audio_sound(reset_audio_label, settings_window),
        width=3
    )
    test_reset_button.pack(side="left", padx=5)

    # Button for selecting reset audio sound, side by side
    reset_speaker_button = ttk.Button(
        reset_button_frame,
        text="🔊",
        command=lambda: test_audio_playback(),
        width=3
    )
    reset_speaker_button.pack(side="left", padx=5)

    # Set the label to the saved file name if it exists when the settings window is opened
    saved_reset_file_path = config.get_setting("reset_audio_sound")
    if saved_reset_file_path:
        update_reset_audio_label(reset_audio_label, saved_reset_file_path)

    # Centering the contents within the frame
    marbles_reset_frame.grid_columnconfigure(0, weight=1)


    # Create a frame for the Directory setting inside the scrollable_frame
    directory_frame = ttk.Frame(scrollable_frame, style="App.TFrame")
    directory_frame.grid(row=2, column=0, columnspan=2, pady=(0, 10), sticky="nsew")

    # Add the Directory label
    directory_label = ttk.Label(directory_frame, text="Mystats Directory", wraplength=300, anchor="nw", justify="left")
    directory_label.grid(row=0, column=0, sticky="w", padx=(10, 10), pady=(5, 5))

    # Add the Directory entry
    directory_value = os.path.expandvars(r"%localappdata%/mystats/")
    directory_entry = ttk.Entry(directory_frame, width=60)
    directory_entry.grid(row=1, column=0, sticky="w", padx=(5,0), pady=(5, 5))
    directory_entry.insert(0, directory_value)
    directory_entry.config(state="readonly")

    # Function to open the directory in Windows Explorer
    def open_directory():
        directory_path = os.path.expandvars(r"%localappdata%/mystats/")
        if os.path.exists(directory_path):
            os.startfile(directory_path)
        else:
            messagebox.showerror("Error", "Directory path does not exist.")

    # Add the Open Location button with folder icon
    open_location_button = ttk.Button(directory_frame, text="📁", command=open_directory, width=3)
    open_location_button.grid(row=1, column=1, padx=(10, 0), pady=(5, 5))

    # Create a new row in top_frame and merge all three columns for the audio device selection
    label = ttk.Label(top_frame, text="Select Audio Output Device:")
    label.grid(row=1, column=0, columnspan=3, sticky="w", padx=10, pady=(10, 5))

    audio_devices = get_audio_devices()
    selected_device = tk.StringVar()

    # Retrieve the current audio device setting or use "Primary Sound Driver" as default
    current_device = config.get_setting('audio_device')
    if not current_device:
        current_device = "Primary Sound Driver"
        config.set_setting('audio_device', current_device)

    selected_device.set(current_device)

    device_combobox = ttk.Combobox(top_frame, textvariable=selected_device, values=audio_devices, width=60)
    device_combobox.grid(row=2, column=0, columnspan=3, sticky="w", padx=10, pady=(0, 10))

    # Save the selection back to config when user makes a selection
    def on_device_change(event):
        config.set_setting('audio_device', selected_device.get())

    device_combobox.bind('<<ComboboxSelected>>', on_device_change)

    def save_settings_and_close():
        # -- Example: Channel entry --
        config.set_setting("CHANNEL", channel_entry.get(), persistent=True)

        # -- Example: Chunk Alert Toggle --
        chunk_alert_is_on = (chunk_alert_button["text"] == "ON")
        config.set_setting("chunk_alert", str(chunk_alert_is_on), persistent=True)

        # -- Example: Chunk Alert Trigger Amount --
        config.set_setting("chunk_alert_value", chunk_alert_trigger_entry.get(), persistent=True)

        # -- Example: Announce Delay Toggle and Seconds --
        announce_delay_is_on = (announce_delay_button["text"] == "ON")
        config.set_setting("announcedelay", str(announce_delay_is_on), persistent=True)
        config.set_setting("announcedelayseconds", delay_seconds_entry.get(), persistent=True)

        # -- Example: Reset Audio Toggle --
        reset_audio_is_on = (reset_audio_button["text"] == "ON")
        config.set_setting("reset_audio", str(reset_audio_is_on), persistent=True)

        # -- Example: Audio Device Selection --
        config.set_setting("audio_device", selected_device.get(), persistent=True)
        
        # Since set_setting(persistent=True) automatically calls config.save_settings() 
        # for each item that is in persistent_keys, we do *not* need to manually call
        # config.save_settings() again (unless you want to).

        # 2) Close the settings window
        settings_window.destroy()

    # 3) Create a Save button that calls 'save_settings_and_close'
    #    Or you can modify your existing "Close" button to do this instead of just destroying the window.
    close_button_frame = ttk.Frame(settings_window, style="App.TFrame")
    close_button_frame.pack(side="bottom", fill="x", padx=20, pady=10)

    close_button = ttk.Button(close_button_frame, text="Save and Close", command=save_settings_and_close, style="Primary.TButton")
    close_button.pack(side="right")

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

    settings_button = ttk.Button(
        button_frame,
        text="Settings",
        command=open_settings_window,
        width=8,
        style="Primary.TButton"
    )
    settings_button.grid(row=0, column=0, padx=5, pady=(0, 5))
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
    root_window, app_style = create_root_window()
    apply_ui_styles(app_style)

    root_window.protocol("WM_DELETE_WINDOW", on_close)
    root_window.title("MyStats - Marbles On Stream Companion Application")
    root_window.geometry("800x500")
    root_window.resizable(False, False)

    root_window.grid_rowconfigure(1, weight=1)
    root_window.grid_columnconfigure(1, weight=1)

    build_stats_sidebar(root_window)
    build_main_content(root_window)

    root_window.update_idletasks()
    root_window.grid_columnconfigure(1, weight=1)

    return root_window


# Tkinter Initialization
root = initialize_main_window()


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
        root.update_idletasks()
        root_width = root.winfo_width()
        root_height = root.winfo_height()
        root_x = root.winfo_x()
        root_y = root.winfo_y()

        create_event_window = tk.Toplevel(root)
        create_event_window.title("Create Event")
        create_event_window.geometry("300x300")

        window_width = 300
        window_height = 300
        window_x = root_x + (root_width // 2) - (window_width // 2)
        window_y = root_y + (root_height // 2) - (window_height // 2)
        create_event_window.geometry(f"{window_width}x{window_height}+{window_x}+{window_y}")

        def on_create_event_close():
            create_event_window.destroy()
            open_events_window()

        create_event_window.protocol("WM_DELETE_WINDOW", on_create_event_close)

        tk.Label(create_event_window, text="Event Name").pack(pady=5)
        event_name_entry = tk.Entry(create_event_window)
        event_name_entry.pack(pady=5)

        tk.Label(create_event_window, text="Event Start Date").pack(pady=5)
        event_start_entry = DateEntry(create_event_window, date_pattern='y-mm-dd')
        event_start_entry.pack(pady=5)

        tk.Label(create_event_window, text="Event End Date").pack(pady=5)
        event_end_entry = DateEntry(create_event_window, date_pattern='y-mm-dd')
        event_end_entry.pack(pady=5)

        def create_event():
            event_name = event_name_entry.get()
            event_start = event_start_entry.get_date().strftime('%Y-%m-%d')
            event_end = event_end_entry.get_date().strftime('%Y-%m-%d')

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

        tk.Button(create_event_window, text="Create Event", command=create_event).pack(pady=10)
        tk.Button(create_event_window, text="Cancel", command=on_create_event_close).pack(pady=5)

    create_event_button = tk.Button(events_window, text="Create Event", command=open_create_event_window)
    create_event_button.pack(pady=5)

    events_window.grab_set()

    close_button = tk.Button(events_window, text="Close", command=events_window.destroy)
    close_button.pack(pady=10)

    update_event_list()


# Call the open_events_window function to open the events window
# Add the events button next to the settings button in the main window
events_button = ttk.Button(button_frame, text="Events", command=open_events_window, width=button_width, style="Primary.TButton")
events_button.grid(row=0, column=1, padx=5, pady=(0, 5))

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
                                'tilts_results_file', 'tilt_level_file', 'map_data_file', 'map_results_file'}
        self.transient_keys = set([])
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
        return self.settings.get(key, None)

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
        return True

    def save_settings(self):
        with open(self.settings_file, "w") as f:
            for key, value in self.settings.items():
                if key in self.persistent_keys:
                    f.write(f"{key}={value}\n")


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
        retry_window = tk.Tk()
        retry_window.withdraw()  # Hide root window
        result = messagebox.askretrycancel("Login Required",
                                           "You must log in to the website to use MyStats. Click Retry to try again.")
        retry_window.destroy()  # Close the popup window
        return result

    retry_request()  # Initial API call


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
        config.set_setting('totalpointsseason', 0, persistent=False)
        config.set_setting('totalcountseason', 0, persistent=False)
    else:
        pass

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

        await ctx.channel.send(
            f"{winnersdisplayname}: Today: {counts['winstoday']} {wins_str}, {pointstoday_formatted} points, {racestoday_formatted} races. "
            f"PPR: {today_avg_points_formatted} | Season total: {output_msg}"
        )


    
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
    MAX_MESSAGE_LENGTH = 480
    while not bot.stop_event.is_set():
        # print('Debug: Tilted file check')
        try:
            tilt_level_file = config.get_setting('tilt_level_file')
            current_modified_tilt = os.path.getmtime(tilt_level_file)

        except FileNotFoundError:
            print("Tilt level file not found. Trying again.")
            await asyncio.sleep(1)
            continue

        except Exception as e:
            print(f"Error checking modification time: {e}")
            await asyncio.sleep(1)
            continue
        
        except asyncio.CancelledError:
            # Task was cancelled; exit gracefully
            print("Tilted task was cancelled.")
            break

        if last_modified_tilt is None:
            last_modified_tilt = current_modified_tilt
            print("Tilted monitoring initiated. System is ready to go!")
            await asyncio.sleep(1)
            continue

        if current_modified_tilt != last_modified_tilt:
            await asyncio.sleep(3)

            try:
                with open(tilt_level_file, 'rb') as f:
                    data = f.read()
                result = chardet.detect(data)
                encoding = result['encoding']

                with open(tilt_level_file, 'r', encoding=encoding, errors='ignore') as f:
                    reader = csv.reader(f)
                    leveldata = list(reader)

                level_header = leveldata[0]
                level_row = leveldata[1]

                current_level = int(level_row[0])
                elapsed_time = level_row[1]
                top_tiltee = level_row[2]
                level_xp = level_row[3]
                total_xp = level_row[4]
                live = level_row[5]
                level_passed = level_row[6].strip().lower() == 'true'

                if current_level == 1 and run_id is None:
                    run_id = base64.urlsafe_b64encode(uuid.uuid4().bytes).rstrip(b'=').decode('utf-8')

                if not level_passed:
                    tilts_results_file = config.get_setting('tilts_results_file')
                    if not tilts_results_file:
                        create_results_files()

                    run_results = {}
                    if os.path.exists(tilts_results_file):
                        with open(tilts_results_file, 'rb') as f:
                            raw_data = f.read()

                        result = chardet.detect(raw_data)
                        encoding = result['encoding'] if result['encoding'] else 'utf-8'
                        with open(tilts_results_file, 'r', newline='', encoding=encoding) as tilt_file:
                            reader = csv.reader(tilt_file)
                            for row in reader:
                                if row[0] == run_id:
                                    username = row[2]
                                    points = int(row[4])
                                    run_results[username] = run_results.get(username, 0) + points

                    sorted_run_results = sorted(run_results.items(), key=lambda x: x[1], reverse=True)

                    if sorted_run_results:
                        full_summary_message = f"Run {run_id[:6]} is over! Final standings: "
                        for username, points in sorted_run_results:
                            player_summary = f"{username} - {points} points, "
                            if len(full_summary_message) + len(player_summary) > MAX_MESSAGE_LENGTH:
                                await bot.channel.send(full_summary_message.strip(", "))
                                full_summary_message = player_summary
                            else:
                                full_summary_message += player_summary

                        if full_summary_message:
                            await bot.channel.send(full_summary_message.strip(", "))

                        text_area.insert('end', f"\nRun {run_id[:6]} is over! Final standings: {', '.join([f'{username} - {points} points' for username, points in sorted_run_results])}\n")
                    else:
                        # If no results found for the run_id
                        await bot.channel.send(f"Run {run_id[:6]} is over! No results to display.")
                        text_area.insert('end', f"\nRun {run_id[:6]} is over! No results to display.\n")
                        print("No results found for this run.")

                    run_id = None

                else:
                    tilt_player_file = config.get_setting('tilt_player_file')
                    with open(tilt_player_file, 'rb') as f:
                        data = f.read()
                    result = chardet.detect(data)
                    encoding = result['encoding']

                    with open(tilt_player_file, 'r', encoding=encoding, errors='ignore') as fp:
                        reader = csv.reader(fp)
                        tiltdata = list(reader)

                    current_level_data = [row for row in tiltdata[1:] if int(row[4]) == current_level and int(row[2]) > 0]

                    top_tiltee_message = f"End of Tilt Level {current_level} | Level Completion Time: {elapsed_time} | " \
                                         f"Top Tiltee: {top_tiltee} | Points Earned: {level_xp} | Finishers: " if top_tiltee \
                        else f"End of Tilt Level {current_level} | Level Completion Time: {elapsed_time} | Top Tiltee: None | Points Earned: {level_xp} | Finishers: "

                    if current_level_data:
                        full_message = top_tiltee_message
                        for row in current_level_data:
                            player_result = f"{row[0]}, "
                            if len(full_message) + len(player_result) > MAX_MESSAGE_LENGTH:
                                await bot.channel.send(full_message.strip(", "))
                                full_message = player_result
                            else:
                                full_message += player_result

                        if full_message:
                            await bot.channel.send(full_message.strip(", "))
                        # print("Sent current level results to chat.")

                        text_area.insert('end', f"\n{top_tiltee_message} | Finishers: {', '.join([f'{row[0]}' for row in current_level_data])}\n")
                    else:
                        print("No player data to send for current level.")

                    tilts_results_file = config.get_setting('tilts_results_file')

                    try:
                        with open(tilts_results_file, 'rb') as f:
                            raw_data = f.read()

                        result = chardet.detect(raw_data)
                        encoding = result['encoding'] if result['encoding'] else 'utf-8'
                        with open(tilts_results_file, 'a', newline='', encoding='utf-8') as tilts_file:
                            writer = csv.writer(tilts_file)
                            for row in tiltdata[1:]:
                                try:
                                    event_ids_tmp = config.get_setting('active_event_ids')
                                    if event_ids_tmp is not None:
                                        event_ids_tmp = event_ids_tmp.strip("[]").split(",")
                                        event_ids = [int(id.strip().replace('"', '')) for id in event_ids_tmp if
                                                     id.strip().replace('"', '').isdigit()]

                                    else:
                                        event_ids = [0]
                                    data_to_write = [run_id, current_level] + row + [event_ids]
                                    writer.writerow(data_to_write)
                                except Exception as e:
                                    pass
                                    print(f"Error writing row {row} to {tilts_results_file}: {e}")
                    except Exception as e:
                        print(f"Error opening/writing to tilts_results_file: {e}")

                last_modified_tilt = current_modified_tilt

            except Exception as e:
                print(f"An error occurred while processing the tilt file: {e}")

        else:
            pass

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

                # Read CSV in a separate thread
                df = await asyncio.to_thread(
                    pd.read_csv,
                    config.get_setting('checkpoint_file'),
                    encoding=encoding,
                    header=None
                )

                # Check if the file contains only the header row
                if len(df) <= 1:
                    continue  # Skip processing if only header exists

                df_cleaned = df.drop(index=0).drop_duplicates().reset_index(drop=True)
                df_sorted = df_cleaned.sort_values(by=0, ascending=True)

                checkpointplayers = df_sorted.values.tolist()

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
                    await bot.channel.send(concatenated_message)

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


async def race(bot):
    last_modified_race = None
    last_map_file_mod_time = None
    totalpointsrace = 0
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
            await bot.channel.send("🎺 Marble Day Reset! 🎺")
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

            # Initialize variables to store map data
            MapName, MapBuilder, MapCreatedDate, PlayCount, ElimRate, AvgFinishTime, RecordTime, RecordHolder, RecordSetDate, RecordStreamer = (
                None, None, None, 0, 0.0, 0.0, 0.0, None, None, None)

            # Step 1: Process the map file only if the modification time has changed
            map_data_file = config.get_setting('map_data_file')
            map_results_file = config.get_setting('map_results_file')

            try:
                # Get the current modification time of the map file
                current_mod_time = os.path.getmtime(map_data_file)

                # Only process the map file if it has been modified since the last read
                if last_map_file_mod_time is None or current_mod_time > last_map_file_mod_time:
                    last_map_file_mod_time = current_mod_time  # Update the last modification time

                    # Read the map data file with encoding detection
                    with open(map_data_file, 'rb') as f:
                        map_data = f.read()

                    encoding_result = chardet.detect(map_data)
                    map_encoding = encoding_result['encoding'] or 'utf-8'  # Default to 'utf-8' if detection fails

                    # Read the file using the detected encoding
                    with open(map_data_file, 'r', encoding=map_encoding, errors='ignore') as f:
                        map_lines = f.readlines()
                        if DEBUG == True:
                            print('Debug: Read Map Data File')
                        else:
                            pass

                    if len(map_lines) > 1:
                        # Ignore the header row and get the first data row
                        map_data_first_row = map_lines[1].strip()
                        map_data_fields = [field.strip().strip('"') for field in map_data_first_row.split(',')]

                        if len(map_data_fields) >= 10:
                            # Parse map data fields
                            MapName = map_data_fields[0]
                            MapBuilder = map_data_fields[1]

                            try:
                                MapCreatedDate = datetime.strptime(map_data_fields[2], '%Y-%m-%dT%H:%M:%S.%fZ').date()
                            except ValueError:
                                MapCreatedDate = None

                            try:
                                PlayCount = int(map_data_fields[3])
                            except ValueError:
                                PlayCount = 0

                            try:
                                ElimRate = float(map_data_fields[4])
                            except ValueError:
                                ElimRate = 0.0

                            try:
                                AvgFinishTime = float(map_data_fields[5])
                            except ValueError:
                                AvgFinishTime = 0.0

                            try:
                                RecordTime = float(map_data_fields[6])
                            except ValueError:
                                RecordTime = 0.0

                            RecordHolder = map_data_fields[7]

                            try:
                                RecordSetDate = datetime.strptime(map_data_fields[8], '%Y-%m-%dT%H:%M:%S.%fZ').date()
                            except ValueError:
                                RecordSetDate = None

                            RecordStreamer = map_data_fields[9]

                            # Write the parsed data to the map_results_file
                            with open(map_results_file, 'a', encoding='utf-8', errors='ignore', newline='') as f:
                                f.write(
                                    f'{MapName},{MapBuilder},{MapCreatedDate},{PlayCount},{ElimRate},'
                                    f'{AvgFinishTime},{RecordTime},{RecordHolder},{RecordSetDate},'
                                    f'{RecordStreamer}\n')
                        else:
                            print("Not enough data fields in map_data_first_row.")
                    else:
                        print(f"The map data file {map_data_file} does not contain enough data.")
                else:
                    print("Map file has not been modified since last read.")
                    # Reset map data since we're not reading the file
                    MapName, MapBuilder, PlayCount, ElimRate, AvgFinishTime, RecordTime, RecordHolder, RecordSetDate, RecordStreamer = (
                        None, None, 0, 0.0, 0.0, 0.0, None, None, None)

            except FileNotFoundError:
                print(f"Map data file {map_data_file} not found.")
            except Exception as e:
                print(f"An error occurred while processing the map data file: {e}")

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
            with open(config.get_setting('allraces_file'), 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.reader(f)
                for row in reader:
                    if row[1] in race_counts:
                        race_counts[row[1]] += 1

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
                    await bot.channel.send(announcement_message)

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
                            await bot.channel.send(announcement_message)

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
                        await asyncio.sleep(int(config.get_setting('announcedelayseconds')))
                        await bot.channel.send(message)
                        write_overlays()
                    else:
                        if DEBUG == True:
                            print('Debug: Announcement Delay: False')
                        else:
                            pass
                        await bot.channel.send(message)
                        write_overlays()

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
