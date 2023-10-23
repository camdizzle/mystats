import os
import asyncio
from datetime import datetime
import twitchio
from twitchio.ext import commands
from twitchio.ext.commands.errors import CommandNotFound
import csv
import os
import shutil
import time
import datetime
from datetime import date, timedelta
from datetime import datetime, timedelta
from datetime import datetime
import random
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import pygame
from colorama import init, Fore, Style
import pytz
from io import StringIO
import chardet
import glob
import math
import pyautogui
import copy
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread.exceptions import SpreadsheetNotFound, WorksheetNotFound

init(autoreset=True)  # initialize colorama

#Variables defined globally
AVGPOINTSTODAY = 0
count = 0
TOTALPOINTSTODAY = 0
hscore_name = 'None'
high_score = 0
chunk_alert_points = 1000
chunk_alert = False
AnnounceDelay = False
AnnounceDelayTime = 10
points = 1000
totalpointsrace = 0
marbcount = 0

    
# Twitch bot setup
# Read settings from file for bot creation
with open("settings.txt", "r") as f:
    settings = f.readlines()
    nick = settings[0].split("=")[1].strip()
    bot_token = settings[1].split("=")[1].strip()
    channel_name = settings[2].split("=")[1].strip()
    bot_prefix = '!'

# Define the scope and credentials
scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name('meta-data-tracking.json', scope)

# Authorize and open the Google Sheet
client = gspread.authorize(credentials)

# Specify your spreadsheet name
spreadsheet = 'season'
worksheet = 'season'
sheet = client.open(spreadsheet).worksheet(worksheet)

# Read data
season = sheet.cell(1, 1).value.strip()  # Reads the value in the first cell (A1)


print()
print(Fore.CYAN + "Welcome to the Race Results Announcement Bot for Marbles on Stream." + Style.RESET_ALL)
print("                       v4.20")
print()
print("mystats now included in this version!")
print("Commands to use: !mystats, !top10today, !top10season, !top10wins")
print()
print("Data collection will be based on Season: " + str(season) + ".  If this is the wrong season")
print("please update season.txt with the correct season number.")
print()
print("This application was developed by " + Style.BRIGHT + Fore.YELLOW + "CamWOW!!!" + Style.RESET_ALL)
print("For any questions, bugs or suggestions, visit the discord.") 
print(Style.NORMAL + Fore.YELLOW + "https://discord.gg/camwow" + Style.RESET_ALL)
print()
print("System initializing.....")
print()

# Prompt user to turn on chunk alert and set the alert points
response = input("Turn on chunk alert? (y/n): ")
if response.lower() == 'y' or response.lower() == 'yes':
    points = input("Enter the minimum points to trigger the alert: ")
    try:
        chunk_alert_points = int(points)
        chunk_alert = True
    except ValueError:
        print("Invalid input, using default value of 1000")
else:
    points = 0
    chunk_alert_points = int(points)
    chunk_alert = False
    
print()
print("Chunk alert is", Fore.GREEN + "on " + Style.RESET_ALL + "for wins greater than " + Fore.GREEN + points + Style.RESET_ALL if chunk_alert else Fore.RED + "off " + Style.RESET_ALL + "for wins greater than " + Fore.GREEN + str(points) + Style.RESET_ALL)
print()

# Define the desired offset in hours
offset_hours = -12

# Calculate the offset in seconds
offset_seconds = offset_hours * 3600

# Create a timedelta object with the offset
offset_timedelta = timedelta(seconds=offset_seconds)

# Define the EST timezone
est_tz = pytz.timezone('America/New_York')

# Get the current time in EST
now_est = datetime.now(est_tz)

# Calculate the current time in the custom timezone
now_custom_tz = now_est + offset_timedelta

timestamp = now_custom_tz.strftime("%Y-%m-%d %H:%M:%S")
timestampMDY = now_custom_tz.strftime("%Y-%m-%d")
timestampHMS = now_custom_tz.strftime("%H:%M:%S")

prev_timestamp = timestampMDY
# get the current year and month as strings
year = now_custom_tz.strftime("%Y")
month = now_custom_tz.strftime("%m")

print("The current Marble Day date/time is: " + str(timestamp))
print()
# create the directory path if it does not exist
directory = os.path.join("Results", "Season_" + str(season))
if not os.path.exists(directory):
    os.makedirs(directory)

# create the filename with the full path
filename = os.path.join(directory, "results_" + now_custom_tz.strftime("%Y-%m-%d") + ".csv")
print("The path to your results data is: " + filename)

# create the filename with the full path
allraces = os.path.join(directory, "allraces_" + now_custom_tz.strftime("%Y-%m-%d") + ".csv")
print("The path to your all race data is: " + allraces)
print()

# Use os.path.expanduser to get a universal file path
file_path = os.path.expanduser(r"~/AppData/Local/MarblesOnStream/Saved/SaveGames/LastSeasonRoyale.csv")
try:
    open(file_path, "r", encoding='utf-8', errors='ignore').close()
except FileNotFoundError:
    open(file_path, "w", encoding='utf-8', errors='ignore').close()
    # Write log entry with timestamp
    with open('log.txt', 'a') as f:
        f.write(
            f"[{timestamp}]  - ~/AppData/Local/MarblesOnStream/Saved/SaveGames/LastSeasonRoyale.csv does not exist\n")
except Exception as e:
    print(fFore.RED + "We see no record of you hosting a Battle Royale.  Do that." + Style.RESET_ALL)
count = 0
file_path2 = os.path.expanduser(r"~/AppData/Local/MarblesOnStream/Saved/SaveGames/LastSeasonRace.csv")
try:
    open(file_path2, "r", encoding='utf-8', errors='ignore').close()
except FileNotFoundError:
    open(file_path2, "w", encoding='utf-8', errors='ignore').close()
    # Write log entry with timestamp
    with open('log.txt', 'a') as f:
        f.write(f"[{timestamp}]  - ~/AppData/Local/MarblesOnStream/Saved/SaveGames/LastSeasonRace.csv does not exist\n")
except Exception as e:
    print(fFore.RED + "We see no record of you hosting a map race.  Do that." + Style.RESET_ALL)

async def reset():
    global last_modified_time2, TOTALPOINTSTODAY, AVGPOINTSTODAY, marbcount, now_custom_tz, last_modified_race, season, channel_name, count, hscore_name, high_score, timestamp, current_modified_race
    # Define the desired offset in hours
    offset_hours = -12
    
    # Calculate the offset in seconds
    offset_seconds = offset_hours * 3600
    
    # Create a timedelta object with the offset
    offset_timedelta = timedelta(seconds=offset_seconds)
    
    # Define the EST timezone
    est_tz = pytz.timezone('America/New_York')
    
    # Get the current time in EST
    now_est = datetime.now(est_tz)
    
    # Calculate the current time in the custom timezone
    now_custom_tz = now_est + offset_timedelta
    
    timestamp = now_custom_tz.strftime("%Y-%m-%d %H:%M:%S")
    timestampMDY = now_custom_tz.strftime("%Y-%m-%d")
    timestampHMS = now_custom_tz.strftime("%H:%M:%S")
    prev_timestamp = timestampMDY
    
    # get the current year and month as strings
    year = now_custom_tz.strftime("%Y")
    month = now_custom_tz.strftime("%m")

    data = []

    try:
        with open(filename, "r", encoding='utf-8', errors='ignore') as f:
            reader = csv.reader(f)
            for row in reader:
                data.append(row)
    except FileNotFoundError:
        print(f"This appears to be your first race today.")
        print("Today's results file will be created when you complete your first race.")
    except Exception as e:
        print(f"Run a race or battle royale to start today's results file")

    for row in data:
        if row[0] == '1':
            count += 1
        TOTALPOINTSTODAY += int(row[3])

    # calculate the average points for the current day
    if count > 0:
        AVGPOINTSTODAY = TOTALPOINTSTODAY / count
        AVGPOINTSTODAY = int(round(AVGPOINTSTODAY))  # round up to nearest integer
    else:
        AVGPOINTSTODAY = 0

    # write TOTALPOINTSTODAY and AVGPOINTSTODAY to their respective files
    with open('TotalPointsToday.txt', 'w', encoding='utf-8', errors='ignore') as f:
        TOTALPOINTSTODAYf = format(TOTALPOINTSTODAY, ',')
        f.write(str(TOTALPOINTSTODAYf))

    with open('AvgPointsToday.txt', 'w', encoding='utf-8', errors='ignore') as f:
        AVGPOINTSTODAYf = format(AVGPOINTSTODAY, ',')						
        f.write(str(AVGPOINTSTODAYf))

    with open('CountofRaces.txt', 'w', encoding='utf-8', errors='ignore') as f:
        countf = format(count, ',')
        f.write(str(countf))

    # Find the highest score in the CSV file
    try:
        high_score_row = max(data, key=lambda row: int(row[3]))
        high_score = int(high_score_row[3])
        if high_score_row[1] != high_score_row[2].lower():
            hscore_name = high_score_row[1]
        else:
            hscore_name = high_score_row[2]
    except ValueError:
        with open('HighScore.txt', 'w', encoding='utf-8', errors='ignore') as hs:
            hs.write(str(hscore_name) + '\n')
            hs.write(str(int(format(high_score, ','))) + '\n')
    except Exception as e:
        print("An error occurred while finding the highest score.")
        
    # compare current score with high score and replace if current score is higher
    with open('HighScore.txt', 'w', encoding='utf-8', errors='ignore') as hs:
        hs.write(str(hscore_name) + '\n')
        hs.write(str(format(high_score, ',')) + '\n')

    # Use os.path.expanduser to get a universal file path
    file_path = os.path.expanduser(r"~/AppData/Local/MarblesOnStream/Saved/SaveGames/LastSeasonRoyale.csv")
    try:
        open(file_path, "r", encoding='utf-8', errors='ignore').close()
    except FileNotFoundError:
        open(file_path, "w", encoding='utf-8', errors='ignore').close()
        # Write log entry with timestamp
        with open('log.txt', 'a') as f:
            f.write(
                f"[{timestamp}]  - ~/AppData/Local/MarblesOnStream/Saved/SaveGames/LastSeasonRoyale.csv does not exist\n")
    except Exception as e:
        print(fFore.RED + "We see no record of you hosting a Battle Royale.  Do that." + Style.RESET_ALL)
    count = 0
    file_path2 = os.path.expanduser(r"~/AppData/Local/MarblesOnStream/Saved/SaveGames/LastSeasonRace.csv")
    try:
        open(file_path2, "r", encoding='utf-8', errors='ignore').close()
    except FileNotFoundError:
        open(file_path2, "w", encoding='utf-8', errors='ignore').close()
        # Write log entry with timestamp
        with open('log.txt', 'a') as f:
            f.write(f"[{timestamp}]  - ~/AppData/Local/MarblesOnStream/Saved/SaveGames/LastSeasonRace.csv does not exist\n")
    except Exception as e:
        print(fFore.RED + "We see no record of you hosting a map race.  Do that." + Style.RESET_ALL)


    pass

class Bot(commands.Bot):

    def __init__(self):
        super().__init__(token=bot_token, prefix=bot_prefix, initial_channels=[channel_name])
        self.channel = None
        self.last_command_author = None  # new instance variable

    async def event_ready(self):
        print("Connected successfully as " + Fore.GREEN + self.nick + Style.RESET_ALL + ", joined successfully to " + Fore.GREEN + channel_name + Style.RESET_ALL)
        print()
        self.channel = self.get_channel(channel_name)
        # Start the file watcher when the bot is ready
        self.loop.create_task(race(self))
        self.loop.create_task(royale(self))
        self.loop.create_task(reset())

    async def event_message(self, message):
        # ignore messages from the bot itself
        if message.author is None:
            return

        # convert the command to lowercase
        content = message.content.lower()
        new_message = copy.copy(message)
        new_message.content = content
        await self.handle_commands(new_message)

    @commands.command(name='info')
    async def info(self, ctx):
        data = []
        totalcount = 0
        totalpointsseason = 0
        if ctx.author.name.lower() == 'camwow' or ctx.author.name.lower() == channel_name:
            for allraces in glob.glob(os.path.join(directory, "allraces_*.csv")):
                try:
                    with open(allraces, 'r', encoding='utf-8', errors='ignore') as f:
                        reader = csv.reader(f)
                        for row in reader:
                            if row[0] == '1':
                                totalcount += 1
                            totalpointsseason += int(row[3])
                except FileNotFoundError:
                    print(f"This appears to be your first race today.")
                    print("Today's results file will be created when you complete your first race.")
                except Exception as e:
                    print(f"Run a race or battle royale to start today's results file")
                    print(e)


            await ctx.channel.send("Version 4.20 | Season: " + season + " | Total Races: " + str(format(totalcount, ',')) + " | Total Points: " + str(format(totalpointsseason, ',')))
        else:
            pass

    @commands.command(name='areyouok?')
    async def areyouok(self, ctx):
        if ctx.author.name.lower() == 'camwow':
            await ctx.channel.send("Oh, its my creator! I'm doing great, father. " + channel_name + " is treating me well, feeding me and letting me rest between streams.  Thank you for introducing me to this amazing streamer!")
        else:
            pass

    @commands.command(name='alertoff')
    async def alertoff(self, ctx, chunk_alert=False):
        if ctx.author.name.lower() == channel_name:
            chunk_alert = False
            chunk_alert_points = 0
            await ctx.channel.send("Chunk Alert: Off.")
            print("Chunk Alert: Off. " + str(chunk_alert) + " value")
        else:
            pass

    @commands.command(name='alerton')
    async def alerton(self, ctx, chunk_alert=True):
        if ctx.author.name.lower() == channel_name:
            chunk_alert = True
            chunk_alert_points = 1000
            await ctx.channel.send("Chunk Alert: On.  Alert will sound for all wins over " + str(chunk_alert_points))
            print("Chunk Alert: On.  Alert will sound for all wins over " + str(chunk_alert_points))
        else:
            pass

    @commands.command(name='alertpoints')
    async def alertpoints(self, ctx, chunk_alert_points: int):
        if ctx.author.name.lower() == channel_name and chunk_alert:
            print(chunk_alert_points)
            print(chunk_alert)
            await ctx.channel.send("Alert will sound for all wins over " + str(chunk_alert_points))
        elif ctx.author.name.lower() == channel_name and not chunk_alert:
            await ctx.channel.send("Chunk Alerts are OFF.  Use !alerton to turn them on first, then try again.")
        else:
            pass

    @commands.command(name='mystats')
    async def mystats_command(self, ctx):
        self.last_command_author = ctx.author.name
        winnersname = self.last_command_author
        winnersdisplayname = self.last_command_author
        today = now_custom_tz.strftime("%Y-%m-%d")

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
            'race_points': 0
        }

        for allraces in glob.glob(os.path.join(directory, "allraces_*.csv")):
            try:
                with open(allraces, 'r', encoding='utf-8', errors='ignore') as f:
                    reader = csv.reader(f)
                    for row in reader:
                        race_date = datetime.strptime(row[5], "%Y-%m-%d %H:%M:%S").date()  # date of the race

                        if row[1].lower() == winnersname.lower() and str(race_date) == str(today):
                            counts['racestoday'] += 1
                            counts['pointstoday'] += int(row[3])
                            if row[0] == '1':
                                counts['winstoday'] += 1

                        if row[1].lower() == winnersname.lower():
                            counts['seasonraces'] += 1
                            counts['seasonpts'] += int(row[3])
                            if row[0] == '1':
                                counts['seasonwins'] += 1
                            if len(row) >= 5:
                                if row[4] == 'BR':
                                    counts['br_count'] += 1
                                    counts['br_points'] += int(row[3])
                                    if row[0] == '1':
                                        counts['brwins'] += 1
                                elif row[4] == 'Race':
                                    counts['race_count'] += 1
                                    counts['race_points'] += int(row[3])
                                    if row[0] == '1':
                                        counts['racewins'] += 1

            except FileNotFoundError:
                print("File not found.")
                await ctx.channel.send("No season races recorded yet")
            except Exception as e:
                print(e)

        # Compute average points per race for different event types
        br_avg_points = counts['br_points'] / counts['br_count'] if counts['br_count'] > 0 else 0
        race_avg_points = counts['race_points'] / counts['race_count'] if counts['race_count'] > 0 else 0

        # Compute average points per race for the season
        season_avg_points = counts['seasonpts'] / counts['seasonraces'] if counts['seasonraces'] > 0 else 0

        # Compute average points per race for today
        today_avg_points = counts['pointstoday'] / counts['racestoday'] if counts['racestoday'] > 0 else 0

        # Computing the rounded down values for presentation
        br_avg_points_rounded_down = math.floor(br_avg_points * 10) / 10
        race_avg_points_rounded_down = math.floor(race_avg_points * 10) / 10
        season_avg_points_rounded_down = math.floor(season_avg_points * 10) / 10
        today_avg_points_rounded_down = math.floor(today_avg_points * 10) / 10

        # Create string for singular or plural "win" based on the count
        wins_str = "win" if counts['winstoday'] == 1 else "wins"
        seasonwins_str = "win" if counts['seasonwins'] == 1 else "wins"

        # Format the numbers with commas and rounded down values
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

        # Create the formatted output message
        output_msg = (
            f"BRs - {brwins_formatted} wins, {br_points_formatted} points, {br_count_formatted} royales, PPR: {br_avg_points_formatted}. | "
            f"Races - {racewins_formatted} wins, {race_points_formatted} points, {race_count_formatted} races, PPR: {race_avg_points_formatted}. | "
            f"Season - {seasonwins_formatted} wins, {seasonpts_formatted} points, {seasonraces_formatted} races, PPR: {season_avg_points_formatted}.")

        await ctx.channel.send(
            f"{winnersdisplayname}: Today: {counts['winstoday']} {wins_str}, {pointstoday_formatted} points, {racestoday_formatted} races. PPR: {today_avg_points_formatted} | Season total: {output_msg}")

        
        
    @commands.command(name='top10today')
    async def top10scores_command(self, ctx):
        self.last_command_author = ctx.author.name
        # Call the class here when !test1 command is detected in chat

        data = {}
        try:
            with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.reader(f)
    
                # Read the remaining rows and add them to the data dict	ionary if they meet the condition
                for row in reader:
                    if len(row) >= 5 and int(''.join(row[3]).replace('\x00', '')) != 0:
                        racer = row[2]
                        points = int(row[3])
                        if racer in data:
                            data[racer] += points
                        else:
                            data[racer] = points
    
                # Sort the dictionary by values (total points) in descending order and get the top 10 racers
                top_racers = sorted(data.items(), key=lambda x: x[1], reverse=True)[:10]
    
                message = "Top 10 Today: "
                for i, (racer, points) in enumerate(top_racers):
                    place = i + 1
                    message += "{} {} {} points{}".format("(" + str(place) + ")", racer, format(points, ','),
                                                          ", " if i < len(top_racers) - 1 else ".")
    
            await bot.channel.send(message)
        except FileNotFoundError:
            print("File not found.")
            await bot.channel.send(self.last_command_author + ": No races have been recorded today.")
        except Exception as e:
            pass
            print(e)

    @commands.command(name='top10races')
    async def top10races_command(self, ctx):
        data = {}

        # Iterate over all CSV files in the directory that start with "allraces_"
        for allraces in glob.glob(os.path.join(directory, "allraces_*.csv")):
            try:
                with open(allraces, 'r', encoding='utf-8', errors='ignore') as f:
                    reader = csv.reader(f)

                    # Read the remaining rows and add them to the data dictionary if they meet the condition
                    for row in reader:
                        if len(row) >= 5 and row[2]:  # Make sure row[2] (racer name) is not empty
                            racer = row[2]
                            if racer in data:
                                data[racer] += 1  # Counting races instead of wins
                            else:
                                data[racer] = 1

            except FileNotFoundError:
                print("File not found.")
            except Exception as e:
                pass
                print(e)

        # Sort the dictionary by values (total races) in descending order and get the top 10 racers
        top_racers = sorted(data.items(), key=lambda x: x[1], reverse=True)[:10]
        message = "Top 10 Racers by Total Races: "
        for i, (racer, races) in enumerate(top_racers):
            place = i + 1
            message += "{} {} {} races{}".format("(" + str(place) + ")", racer, format(races, ','), ", " if i < len(top_racers) - 1 else ".")

        await ctx.send(message)




    @commands.command(name='top10wins')
    async def top10wins_command(self, ctx):
        # Call the class here when !top10wins command is detected in chat
                
        data = {}
        
        # Iterate over all CSV files in the directory that start with "allraces_"
        for allraces in glob.glob(os.path.join(directory, "allraces_*.csv")):
            try:
                with open(allraces, 'r', encoding='utf-8', errors='ignore') as f:
                    reader = csv.reader(f)
        
                    # Read the remaining rows and add them to the data dictionary if they meet the condition
                    for row in reader:
                        if len(row) >= 5 and int(row[0]) == 1:
                            # if row[4] == 'BR':
                            racer = row[2]
                            wins = int(row[0])
                            if racer in data:
                                data[racer] += wins
                            else:
                                data[racer] = wins
            except FileNotFoundError:
                print("File not found.")
            except Exception as e:
                pass
                print(e)
        
        # Sort the dictionary by values (total points) in descending order and get the top 10 racers
        top_racers = sorted(data.items(), key=lambda x: x[1], reverse=True)[:10]
        message = "Top 10 Wins Season {}: ".format(season)
        for i, (racer, wins) in enumerate(top_racers):
            place = i + 1
            message += "{} {} {} wins{}".format("(" + str(place) + ")", racer, format(wins, ','),
                                                ", " if i < len(top_racers) - 1 else ".")
        
        await bot.channel.send(message)





    @commands.command(name='top10season')
    async def top10season_command(self, ctx):
        # Call the class here when !top10season command is detected in chat
                
        data = {}
        
        # Iterate over all CSV files in the directory that start with "allraces_"
        for allraces in glob.glob(os.path.join(directory, "allraces_*.csv")):
            try:
                with open(allraces, 'r', encoding='utf-8', errors='ignore') as f:
                    reader = csv.reader(f)
        
                    # Read the remaining rows and add them to the data dictionary if they meet the condition
                    for row in reader:
                        if len(row) >= 5 and int(row[3]) != 0:
                            # if row[4] == 'BR':
                            racer = row[2]
                            points = int(row[3])
                            if racer in data:
                                data[racer] += points
                            else:
                                data[racer] = points
            except FileNotFoundError:
                print("File not found.")
            except Exception as e:
                pass
                print(e)
        
        # Sort the dictionary by values (total points) in descending order and get the top 10 racers
        top_racers = sorted(data.items(), key=lambda x: x[1], reverse=True)[:10]
        message = "Top 10 Season {}: ".format(season)
        for i, (racer, points) in enumerate(top_racers):
            place = i + 1
            message += "{} {} {} points{}".format("(" + str(place) + ")", racer, format(points, ','),
                                                  ", " if i < len(top_racers) - 1 else ".")
        
        await bot.channel.send(message)



    async def event_command_error(self, ctx, error):
        # Ignore the CommandNotFound exception
        if isinstance(error, CommandNotFound):
            return
        raise error

bot = Bot()

# File watcher setup
watch_file_path_race = os.path.expanduser(r"~/AppData/Local/MarblesOnStream/Saved/SaveGames/LastSeasonRace.csv")
last_modified_race = None
PPMformula = 0
avg_finish_time_all = 0

async def race(bot):
    global TOTALPOINTSTODAY, AVGPOINTSTODAY, marbcount, now_custom_tz, last_modified_race, season, channel_name, count, hscore_name, high_score, watch_file_path_race, totalpointsrace, current_modified_race, filename, allraces, prev_timestamp
    race_file_missing = False   
    nowinner = False 
    totalpointsrace = 0
    sum_of_values_all = 0
    number_of_values_all = 0
    while True:
            try:
                    
                # Get the modification time of the file in seconds since the epoch
                current_modified_race = await asyncio.to_thread(os.path.getmtime, watch_file_path_race)


            except FileNotFoundError:
                continue
            if last_modified_race is None:
                last_modified_race = current_modified_race
                print("Race monitoring initiated. System is ready to go!")
                continue                
            # Define the desired offset in hours
            offset_hours = -12
    
            # Calculate the offset in seconds
            offset_seconds = offset_hours * 3600
    
            # Create a timedelta object with the offset
            offset_timedelta = timedelta(seconds=offset_seconds)
    
            # Define the EST timezone
            est_tz = pytz.timezone('America/New_York')
    
            # Get the current time in EST
            now_est = datetime.now(est_tz)
    
            # Calculate the current time in the custom timezone
            now_custom_tz = now_est + offset_timedelta
    
            timestamp = now_custom_tz.strftime("%Y-%m-%d %H:%M:%S")
            timestampMDY = now_custom_tz.strftime("%Y-%m-%d")
            timestampHMS = now_custom_tz.strftime("%H:%M:%S")
    
            # get the current year and month as strings
            year = now_custom_tz.strftime("%Y")
            month = now_custom_tz.strftime("%m")
            
            if prev_timestamp != timestampMDY:
                prev_timestamp = timestampMDY
                
                # Define the desired offset in hours
                offset_hours = -12
    
                # Calculate the offset in seconds
                offset_seconds = offset_hours * 3600
    
                # Create a timedelta object with the offset
                offset_timedelta = timedelta(seconds=offset_seconds)
    
                # Define the EST timezone
                est_tz = pytz.timezone('America/New_York')
    
                # Get the current time in EST
                now_est = datetime.now(est_tz)
    
                # Calculate the current time in the custom timezone
                now_custom_tz = now_est + offset_timedelta
    
                timestamp = now_custom_tz.strftime("%Y-%m-%d %H:%M:%S")
                timestampMDY = now_custom_tz.strftime("%Y-%m-%d")
                timestampHMS = now_custom_tz.strftime("%H:%M:%S")
    
                # get the current year and month as strings
                year = now_custom_tz.strftime("%Y")
                month = now_custom_tz.strftime("%m")

                print("Previous: " + prev_timestamp)
                print("Current: " + timestampMDY)
                print("Marble Day Reset Is Upon Us! RACES")
                AVGPOINTSTODAY = 0
                count = 0
                TOTALPOINTSTODAY = 0
                hscore_name = 'Marble Reset Day'
                high_score = 0
                #reset high score file to reset overlay
                with open('HighScore.txt', 'w', encoding='utf-8', errors='replace') as hs:
                    hs.write(hscore_name + '\n')
                    hs.write(str(high_score) + '\n')

                #reset total points, avg points and count files to reset overlay
                with open('TotalPointsToday.txt', 'w', encoding='utf-8', errors='ignore') as f:
                    TOTALPOINTSTODAYf = format(TOTALPOINTSTODAY, ',')
                    f.write(str(TOTALPOINTSTODAYf))

                with open('AvgPointsToday.txt', 'w', encoding='utf-8', errors='ignore') as f:
                    AVGPOINTSTODAYf = format(AVGPOINTSTODAY, ',')						
                    f.write(str(AVGPOINTSTODAYf))

                with open('CountofRaces.txt', 'w', encoding='utf-8', errors='ignore') as f:
                    countf = format(count, ',')
                    f.write(str(countf))
                # create the directory path if it does not exist
                directory = os.path.join("Results", "Season_" + str(season))
                if not os.path.exists(directory):
                    os.makedirs(directory)

                # create the filename with the full path
                filename = os.path.join(directory, "results_" + now_custom_tz.strftime("%Y-%m-%d") + ".csv")
                print("The path to your results data is: " + filename)

                # create the filename with the full path
                allraces = os.path.join(directory, "allraces_" + now_custom_tz.strftime("%Y-%m-%d") + ".csv")
                print("The path to your all race data is: " + allraces)
                print()
                # Use os.path.expanduser to get a universal file path
                file_path = os.path.expanduser(r"~/AppData/Local/MarblesOnStream/Saved/SaveGames/LastSeasonRoyale.csv")
                try:
                    open(file_path, "r", encoding='utf-8', errors='ignore').close()
                except FileNotFoundError:
                    open(file_path, "w", encoding='utf-8', errors='ignore').close()
                    # Write log entry with timestamp
                    with open('log.txt', 'a') as f:
                        f.write(
                            f"[{timestamp}]  - ~/AppData/Local/MarblesOnStream/Saved/SaveGames/LastSeasonRoyale.csv does not exist\n")
                except Exception as e:
                    print(fFore.RED + "We see no record of you hosting a Battle Royale.  Do that." + Style.RESET_ALL)
                count = 0
                file_path2 = os.path.expanduser(r"~/AppData/Local/MarblesOnStream/Saved/SaveGames/LastSeasonRace.csv")
                try:
                    open(file_path2, "r", encoding='utf-8', errors='ignore').close()
                except FileNotFoundError:
                    open(file_path2, "w", encoding='utf-8', errors='ignore').close()
                    # Write log entry with timestamp
                    with open('log.txt', 'a') as f:
                        f.write(f"[{timestamp}]  - ~/AppData/Local/MarblesOnStream/Saved/SaveGames/LastSeasonRace.csv does not exist\n")
   # except Exception as f:
       # print(fFore.RED + "We see no record of you hosting a map race.  Do that." + Style.RESET_ALL)
            if current_modified_race != last_modified_race:
                last_modified_race = current_modified_race
                
                # START OF RACE RESULTS CODE
                # get the current year and month as strings
                # Get the current time in UTC
                # Define the desired offset in hours
                offset_hours = -12
            
                # Calculate the offset in seconds
                offset_seconds = offset_hours * 3600
            
                # Create a timedelta object with the offset
                offset_timedelta = timedelta(seconds=offset_seconds)
            
                # Define the EST timezone
                est_tz = pytz.timezone('America/New_York')
            
                # Get the current time in EST
                now_est = datetime.now(est_tz)
            
                # Calculate the current time in the custom timezone
                now_custom_tz = now_est + offset_timedelta
            
                timestamp = now_custom_tz.strftime("%Y-%m-%d %H:%M:%S")
            
                # get the current year and month as strings
                year = now_custom_tz.strftime("%Y")
                month = now_custom_tz.strftime("%m")
                
                # print("timestamp: " + timestamp)
                racedata = []
                allracedata = []
                metadata = []

                # read file as bytes
                with open(watch_file_path_race, 'rb') as f:
                    data = f.read()
            
                # detect encoding of bytes
                result = chardet.detect(data)
                encoding = result['encoding']
            
                # read file with detected encoding
                with open(watch_file_path_race, 'r', encoding=encoding, errors='ignore') as f:
                    lines = f.readlines()

                # Initialize first_row
                first_row = None

                # Check if all values in 7th column are 'true'
                if all(line.split(',')[6].strip() == 'true' for line in lines[1:]):
                    await bot.channel.send("Race Winners  🏆: No Winners!")
                    print("Race Winners: No Winners!")
                    nowinner = True
                else:
                    nowinner = False
                    

                # Get Marble Count for Race
                marbcount = len(lines) - 1
                
                # process lines as before
                totalpointsrace = 0
                header = lines[0].replace('\x00', '').strip().split(',')
                first_row_full = lines[1].replace('\x00', '').strip().split(',')
                first_row = [first_row_full[0], first_row_full[1], first_row_full[2], first_row_full[4], 'Race', timestamp,
                             marbcount]
                racedata.append(first_row)
                allracedata.append(first_row)
                metadata.append(first_row_full)
                TOTALPOINTSTODAY += int(first_row_full[4])
                totalpointsrace += int(first_row_full[4])
                
                
                # read the remaining rows and add them to the data list if they meet the condition
                for line in lines[2:]:
                    cleaned_line = line.replace('\x00', '').strip().split(',')
                    row = [cleaned_line[0], cleaned_line[1], cleaned_line[2], cleaned_line[4], 'Race', timestamp, marbcount]
                
                    allracedata.append(row)
                    metadata.append(cleaned_line)
                
                    if len(row) >= 5 and int(row[3]) != 0:
                        racedata.append(row)
                        TOTALPOINTSTODAY += int(row[3])
                        totalpointsrace += int(row[3])
                        
                # print(totalpointsrace)
                # write data to results file
                with open(filename, 'a', newline='', encoding='utf-8', errors='ignore') as f:
                    writer = csv.writer(f)
                    for row in racedata:
                        writer.writerow([row[0], row[1], row[2], row[3], row[4], row[5], row[6]])
                
                # write all race data for tier calculations
                with open(allraces, 'a', newline='', encoding='utf-8', errors='ignore') as f:
                    writer = csv.writer(f)
                    for row in allracedata:
                        writer.writerow([row[0], row[1], row[2], row[3], row[4], row[5], row[6]])
                
                # Get the race count only counting row[0] equals 1
                try:
                    with open(filename, "r", encoding='utf-8', errors='replace') as f:
                        reader = csv.reader(f)
                        count = 0
                        for row in reader:
                            if len(row) >= 4 and row[0] == '1':
                                count += 1
                except FileNotFoundError:
                    count = 0
                    print("File Not Found")
                except Exception as e:
                    print()


                # Extract the values in row[5] where row[6] is 'false' and print them
                values_where_false = [float(row[5]) for row in metadata if row[6] == 'false']                

                # Check if the list is empty
                if values_where_false:
                    # If the list is not empty, find the minimum among these values
                    lowest_value = min(values_where_false)
                    # print("Lowest value where row[6] is 'false':", lowest_value)
                else:
                    # If the list is empty, assign a default value (None or any other value)
                    lowest_value = 0
                    # print("There are no rows where row[6] is 'false'")

                # 2) Extract the highest value in row[5]
                highest_value = max(float(row[5]) for row in metadata)
                

                # 3) Subtract these 2 values to find the spread
                spread = highest_value - lowest_value
                

                # 4) Count the number of False in row[6]
                false_count = sum(1 for row in metadata if row[6] == 'false')
                


                # 5) Count the number of True in row[6]
                true_count = sum(1 for row in metadata if row[6] == 'true')
                

                # 6) Subtract the count of False from the count of True, then divide that number by the largest value in row[0]
                largest_value_in_row_0 = max(float(row[0]) for row in metadata)
                calculation_result = true_count / largest_value_in_row_0 if largest_value_in_row_0 != 0 else 0

                # 7) Calculate the average of all values in row[5]
                sum_of_values = sum(float(row[5]) for row in metadata if row[6] == "false")
                sum_of_values_all = sum(float(row[5]) for row in metadata)
                number_of_values = len([row for row in metadata if row[6] == "false"])
                number_of_values_all = len([row for row in metadata])
                avg_finish_time = sum_of_values / number_of_values if number_of_values > 0 else 0
                avg_finish_time_all = sum_of_values_all / number_of_values_all if number_of_values_all > 0 else 0
          
                # 8) Calculate # of finishers
                num_of_earners = sum(1 for row in metadata if int(row[4]) > 0)            
          
                # Define the scope and credentials
                scope = ['https://spreadsheets.google.com/feeds',
                         'https://www.googleapis.com/auth/drive']
                credentials = ServiceAccountCredentials.from_json_keyfile_name('meta-data-tracking.json', scope)


                # Authorize and open the Google Sheet
                client = gspread.authorize(credentials)

                # Specify your spreadsheet name
                spreadsheet_name = 'meta_tracking'

                try:
                    # Try to open the spreadsheet
                    spreadsheet = client.open(spreadsheet_name)
                except SpreadsheetNotFound:
                    # If the spreadsheet does not exist, create it
                    print(f"Spreadsheet '{spreadsheet_name}' not found. Creating new one.")
                    spreadsheet = client.create(spreadsheet_name)

                # Specify your worksheet name
                worksheet_name = channel_name  # assuming channel_name is a string variable with your worksheet name

                try:
                    # Try to get the worksheet
                    worksheet = spreadsheet.worksheet(worksheet_name)
                except WorksheetNotFound:
                    # If the worksheet does not exist, add it
                    # print(f"Worksheet '{worksheet_name}' not found in spreadsheet '{spreadsheet_name}'. Creating new one.")
                    worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows="100", cols="20")


                # Find the last row number
                last_row_number = len(worksheet.get_all_values()) + 1

                # Calculate PPMPM for use in console print of stats
                ppmpm_calc = totalpointsrace / largest_value_in_row_0

                # Format ppmpm with two decimal places
                ppmpm = format(ppmpm_calc, ".2f")


                # Append the results to the Google Sheet without the formula
                result_row = [lowest_value, highest_value, spread, avg_finish_time, avg_finish_time_all, calculation_result, 0, '', "Enter Map Name", largest_value_in_row_0, num_of_earners, totalpointsrace]
                worksheet.append_row(result_row)

                # Define the formula with the dynamic row number
                PPMformula = f"=(G{last_row_number}/B{last_row_number})*60"
                PPMformula2 = f"=(L{last_row_number}/J{last_row_number})"
                PPMPMformula = f"=(M{last_row_number}/B{last_row_number})*60"

                # Update the specific cell with the formula
                formula_cell = f'H{last_row_number}' # assuming the formula should go in column J
                points_per_marble_cell = f'M{last_row_number}' # assuming the formula should go in column 
                ppmpm_cell = f'N{last_row_number}' # assuming the formula should go in column

                worksheet.update_acell(formula_cell, PPMformula)
                worksheet.update_acell(points_per_marble_cell, PPMformula2)
                worksheet.update_acell(ppmpm_cell, PPMPMformula)


                # Chunk Alert Sounds when alert point threshold is hit
                
                if int(first_row[3]) >= chunk_alert_points and chunk_alert:
                    import pygame
                    pygame.mixer.init()
                    pygame.mixer.music.load('Sound Files/chunkalert.mp3')
                    pygame.mixer.music.play()
                
                # read the current high score from the file
                if first_row[1] != first_row[2].lower():
                    winnersname = first_row[1]
                else:
                    winnersname = first_row[2]
                with open('HighScore.txt', 'r', encoding='utf-8', errors='replace') as hs:
                    hs_lines = hs.readlines()
                    if len(hs_lines) >= 2:
                        high_score_file = int(hs_lines[1].strip().replace(',', ''))
                    else:
                        high_score_file = 0
                
                # compare current score with high score and replace if current score is higher
                current_score = int(first_row[3])
                if current_score > high_score_file:
                    with open('HighScore.txt', 'w', encoding='utf-8', errors='replace') as hs:
                        hs.write(winnersname + '\n')
                        hs.write(str(format(current_score, ',')) + '\n')
                        # pyautogui.keyDown('ctrl')
                        # pyautogui.press('F23')
                        # pyautogui.keyUp('ctrl')                



                # latest race winner saved
                lastwinner1 = ""
                for i in range(len(racedata)):
                    place = racedata[i][0]
                    lastwinner1 += "{} {} {} points{}".format("(" + str(place) + ")", racedata[i][2], racedata[i][3],
                                                              ",\n" if i < len(racedata) - 1 else ".")
                with open('LatestWinner.txt', 'w', encoding='utf-8', errors='replace') as hs:
                    hs.write("Previous Winners:" + '\n')
                    hs.write(lastwinner1 + '\n')
                
                # increment count and calculate AVGPOINTSTODAY
                AVGPOINTSTODAY = TOTALPOINTSTODAY / count
                AVGPOINTSTODAY = int(round(AVGPOINTSTODAY))  # round up to nearest integer
                AVGPOINTSTODAYf = format(AVGPOINTSTODAY, ',')
                with open('AvgPointsToday.txt', 'w', encoding='utf-8', errors='replace') as f:
                    f.write(str(AVGPOINTSTODAYf))
                
                # update TOTALPOINTSTODAY and export to file
                TOTALPOINTSTODAY = max(0, TOTALPOINTSTODAY)
                TOTALPOINTSTODAYf = format(TOTALPOINTSTODAY, ',')
                with open('TotalPointsToday.txt', 'w', encoding='utf-8', errors='replace') as f:
                    f.write(str(TOTALPOINTSTODAYf))
                
                # write the count to the text file
                countf = format(count, ',')
                with open('CountofRaces.txt', 'w', encoding='utf-8', errors='replace') as f:
                    f.write(str(count))
                
                message = "Race Winners: "
                message1 = ""
                for i in range(len(racedata)):
                    if racedata[i][1] != racedata[i][2].lower():
                        wname = racedata[i][1]
                    else:
                        wname = racedata[i][2]
                    if racedata[i][3] == 'ABCFF7FF':
                        namecolor = Fore.BLUE + Style.BRIGHT + wname + Fore.RESET
                    elif racedata[i][3] == 'F91ED2FF':
                        namecolor = Fore.MAGENTA + Style.BRIGHT + wname + Fore.RESET
                    elif racedata[i][3] == 'FF82D6FF':
                        namecolor = Fore.MAGENTA + Style.NORMAL + wname + Fore.RESET
                    elif racedata[i][3] == '79FFC7FF':
                        namecolor = Fore.GREEN + Style.BRIGHT + wname + Fore.RESET
                    elif racedata[i][3] == 'F88688FF':
                        namecolor = Fore.RED + Style.BRIGHT + wname + Fore.RESET
                    else:
                        namecolor = Fore.WHITE + Style.BRIGHT + wname + Fore.RESET
                    place = i + 1
                    message1 += "(" + Fore.CYAN + "{}".format(place) + Fore.RESET + ") " + namecolor + Fore.GREEN + " {}".format(
                        racedata[i][3]) + Fore.RESET + " points{}".format(", " if i < len(racedata) - 1 else ".")
                if nowinner == True:
                    continue
                else:
                    print(message + Fore.YELLOW + str(marbcount) + Style.RESET_ALL + " " + message1  + " (" + ppmpm + ")")
                
                messages = []  # list to hold messages
                message = "Race Winners  🏆: "  # initial message
                
                for i in range(len(racedata)):
                    
                    place = racedata[i][0]
                    racepoints = '{:,}'.format(int(racedata[i][3]))
                    if racedata[i][1] != racedata[i][2].lower():
                        line = "{} {}({}) {} points{}".format("(" + str(place) + ")", racedata[i][2], racedata[i][1], racepoints,
                                                              ", " if i < len(racedata) - 1 else ".")
                    else:
                        line = "{} {} {} points{}".format("(" + str(place) + ")", racedata[i][2], racepoints,
                                                          ", " if i < len(racedata) - 1 else ".")
                    if len(message + line) > 480:  # check if adding line would exceed limit
                        messages.append(message.rstrip(', '))  # save current message, removing trailing comma
                        message = "Race Winners  🏆: " + line  # start new message with current line
                    else:
                        message += line  # append line to current message
                messages.append(message.rstrip(', '))  # add last message, removing trailing comma
                
                if AnnounceDelay == True:
                    await asyncio.sleep(AnnounceDelayTime)
                channel = bot.get_channel(channel_name)
                if not channel:
                    print(f"Could not find channel: {channel_name}")
                else:
                    if nowinner == False:
                        for msg in messages:
                            await channel.send(msg)  # send each message individually
                    else:
                        continue




            await asyncio.sleep(7)

# File watcher setup
watch_file_path_royale = os.path.expanduser(r"~/AppData/Local/MarblesOnStream/Saved/SaveGames/LastSeasonRoyale.csv")
last_modified_royale = None

async def royale(bot):
    global TOTALPOINTSTODAY, AVGPOINTSTODAY, marbcount, now_custom_tz, last_modified_race, season, channel_name, count, hscore_name, high_score, last_modified_royale, watch_file_path_royale, current_modified_royale, prev_timestamp, file_path, filename, allraces
    
    while True:
        try:    
            current_modified_royale = await asyncio.to_thread(os.path.getmtime, watch_file_path_royale)
        except FileNotFoundError:
            continue
        if last_modified_royale is None:
            last_modified_royale = current_modified_royale
            print("Royale monitoring initiated. System is ready to go!")
            continue
        # Define the desired offset in hours
        offset_hours = -12
    
        # Calculate the offset in seconds
        offset_seconds = offset_hours * 3600
    
        # Create a timedelta object with the offset
        offset_timedelta = timedelta(seconds=offset_seconds)
    
        # Define the EST timezone
        est_tz = pytz.timezone('America/New_York')
    
        # Get the current time in EST
        now_est = datetime.now(est_tz)
    
        # Calculate the current time in the custom timezone
        now_custom_tz = now_est + offset_timedelta
    
        timestamp = now_custom_tz.strftime("%Y-%m-%d %H:%M:%S")
        timestampMDY = now_custom_tz.strftime("%Y-%m-%d")
        timestampHMS = now_custom_tz.strftime("%H:%M:%S")
    
        # get the current year and month as strings
        year = now_custom_tz.strftime("%Y")
        month = now_custom_tz.strftime("%m")
            
        if prev_timestamp != timestampMDY:
            prev_timestamp = timestampMDY
            print("Marble Day Reset Is Upon Us!")
            AVGPOINTSTODAY = 0
            count = 0
            TOTALPOINTSTODAY = 0
            hscore_name = 'Marble Reset Day'
            high_score = 0
            #reset high score file to reset overlay
            with open('HighScore.txt', 'w', encoding='utf-8', errors='replace') as hs:
                hs.write(hscore_name + '\n')
                hs.write(str(high_score) + '\n')

            #reset total points, avg points and count files to reset overlay
            with open('TotalPointsToday.txt', 'w', encoding='utf-8', errors='ignore') as f:
                TOTALPOINTSTODAYf = format(TOTALPOINTSTODAY, ',')
                f.write(str(TOTALPOINTSTODAYf))

            with open('AvgPointsToday.txt', 'w', encoding='utf-8', errors='ignore') as f:
                AVGPOINTSTODAYf = format(AVGPOINTSTODAY, ',')						
                f.write(str(AVGPOINTSTODAYf))

            with open('CountofRaces.txt', 'w', encoding='utf-8', errors='ignore') as f:
                countf = format(count, ',')
                f.write(str(countf))

            # create the directory path if it does not exist
            directory = os.path.join("Results", "Season_" + str(season))
            if not os.path.exists(directory):
                os.makedirs(directory)

            # create the filename with the full path
            filename = os.path.join(directory, "results_" + now_custom_tz.strftime("%Y-%m-%d") + ".csv")
            print("The path to your results data is: " + filename)

            # create the filename with the full path
            allraces = os.path.join(directory, "allraces_" + now_custom_tz.strftime("%Y-%m-%d") + ".csv")
            print("The path to your all race data is: " + allraces)
            print()
            # Use os.path.expanduser to get a universal file path
            file_path = os.path.expanduser(r"~/AppData/Local/MarblesOnStream/Saved/SaveGames/LastSeasonRoyale.csv")
            try:
                open(file_path, "r", encoding='utf-8', errors='ignore').close()
            except FileNotFoundError:
                open(file_path, "w", encoding='utf-8', errors='ignore').close()
                # Write log entry with timestamp
                with open('log.txt', 'a') as f:
                    f.write(
                        f"[{timestamp}]  - ~/AppData/Local/MarblesOnStream/Saved/SaveGames/LastSeasonRoyale.csv does not exist\n")
            except Exception as e:
                print(fFore.RED + "We see no record of you hosting a Battle Royale.  Do that." + Style.RESET_ALL)
            count = 0
            file_path2 = os.path.expanduser(r"~/AppData/Local/MarblesOnStream/Saved/SaveGames/LastSeasonRace.csv")
            try:
                open(file_path2, "r", encoding='utf-8', errors='ignore').close()
            except FileNotFoundError:
                open(file_path2, "w", encoding='utf-8', errors='ignore').close()
                # Write log entry with timestamp
                with open('log.txt', 'a') as f:
                    f.write(f"[{timestamp}]  - ~/AppData/Local/MarblesOnStream/Saved/SaveGames/LastSeasonRace.csv does not exist\n")
        if current_modified_royale != last_modified_royale:
            last_modified_royale = current_modified_royale

            # Define the desired offset in hours
            offset_hours = -12
            
            # Calculate the offset in seconds
            offset_seconds = offset_hours * 3600
            
            # Create a timedelta object with the offset
            offset_timedelta = timedelta(seconds=offset_seconds)
            
            # Define the EST timezone
            est_tz = pytz.timezone('America/New_York')
            
            # Get the current time in EST
            now_est = datetime.now(est_tz)
            
            # Calculate the current time in the custom timezone
            now_custom_tz = now_est + offset_timedelta
            
            timestamp = now_custom_tz.strftime("%Y-%m-%d %H:%M:%S")
            
            # get the current year and month as strings
            year = now_custom_tz.strftime("%Y")
            month = now_custom_tz.strftime("%m")
            brdata = []
            mission = []
            metadata = []
            total = 0
            try:
                # read file as bytes
                with open(file_path, 'rb') as f:
                    data = f.read()
            
                # detect encoding of bytes
                result = chardet.detect(data)
                encoding = result['encoding']
            
                # read file with detected encoding
                with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                    lines = f.readlines()
            
                # process lines as before
                header = lines[0].replace('\x00', '').strip().split(',')
                winner = lines[1].replace('\x00', '').strip().split(',')
            
                # Get Marble Count for Race
                marbcount = len(lines) - 1
            
                # read the remaining rows and add them to the data list if they meet the condition
                for line in lines[1:]:
                    cleaned_line = line.replace('\x00', '').strip().split(',')
                    row = [cleaned_line[0], cleaned_line[1], cleaned_line[2], cleaned_line[4], 'BR', timestamp, marbcount]
                    brdata.append(row)
                    metadata.append(cleaned_line)
  
            
            except FileNotFoundError:
                print(f"This appears to be your first race today.")
                print("Today's results file will be created when you complete your first race.")
            except Exception as e:
                print("An error occurred:", e)
            
            if winner:
                if len(winner) >= 5 and winner[4]:
                    TOTALPOINTSTODAY += int(winner[4])
            
                    # create a list containing the data to be written to the CSV file
                    data = [
                        [winner[0], winner[1], winner[2], winner[4], 'BR', timestamp, marbcount]
                    ]
            
                    # open results file for writing and create a CSV writer object
                    with open(filename, 'a', newline='', encoding='utf-8', errors='ignore') as f:
                        writer = csv.writer(f)
            
                        # write winner the results data to the file
                        writer.writerows(data)
            
                    # write all race data for tier calculations
                    with open(allraces, 'a', newline='', encoding='utf-8', errors='ignore') as f:
                        writer = csv.writer(f)
                        writer.writerows(brdata)
            
                    # Chunk Alert Sounds when alert point threshold is hit
                    if int(''.join(winner[4]).replace('\x00', '')) >= chunk_alert_points and chunk_alert:
                        import pygame
            
                        pygame.mixer.init()
                        pygame.mixer.music.load('Sound Files/chunkalert.mp3')
                        pygame.mixer.music.play()
            
                    # calculate the average and export to file
                    count += 1
                    AVGPOINTSTODAY = TOTALPOINTSTODAY / count
                    AVGPOINTSTODAY = int(round(AVGPOINTSTODAY))  # round up to nearest integer
                    AVGPOINTSTODAYf = format(AVGPOINTSTODAY, ',')
                    with open('AvgPointsToday.txt', 'w', encoding='utf-8', errors='ignore') as f:
                        f.write(str(AVGPOINTSTODAYf))
            
                    # update TOTALPOINTSTODAY and export to file
                    TOTALPOINTSTODAY = max(0, TOTALPOINTSTODAY)
                    TOTALPOINTSTODAYf = format(TOTALPOINTSTODAY, ',')
                    with open('TotalPointsToday.txt', 'w', encoding='utf-8', errors='ignore') as f:
                        f.write(str(TOTALPOINTSTODAYf))
            
                    # write the count to the text file
                    countf = format(count, ',')
                    with open("CountofRaces.txt", "w", encoding='utf-8', errors='ignore') as f:
                        f.write(str(countf))
            
                    # Calculate total points earned today and win count
                    winnertotalpoints = 0
                    wcount = 0
                    if winner[1] != winner[2].lower():
                        winnersname = winner[1]
                    else:
                        winnersname = winner[2]
            
                    try:
                        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
                            reader = csv.reader(f)
                            for row in reader:
                                if row[1] == winnersname.lower():
                                    winnertotalpoints += int(row[3])
                                    if row[0] == '1':
                                        wcount += 1
                    except FileNotFoundError:
                        print("File not found.")
                    except Exception as e:
                        print("An error occurred while processing the file.")
            
                    # update winnertotalpoints and export to file
                    with open('WinnerTotalPoints.txt', 'w', encoding='utf-8', errors='replace') as f:
                        f.write(str(winnertotalpoints))
            
                    # read the current high score from the file
                    with open('HighScore.txt', 'r', encoding='utf-8', errors='replace') as hs:
                        hs_lines = hs.readlines()
                        if len(hs_lines) >= 2:
                            high_score_file = int(hs_lines[1].strip().replace(',', ''))
                        else:
                            high_score_file = 0

                    # compare current score with high score and replace if current score is higher
                    current_score = int(winner[4])
                    # current_scoref = format(current_score, ',')
                    if current_score > high_score_file:
                        with open('HighScore.txt', 'w', encoding='utf-8', errors='ignore') as hs:
                            hs.write(str(winnersname) + '\n')
                            hs.write(str(format(current_score, ',')) + '\n')
                            # pyautogui.keyDown('ctrl')
                            # pyautogui.press('F23')
                            # pyautogui.keyUp('ctrl')

                    # *** GOOGLE SHEET BR UPDATE ***


                    total = sum(int(row[7]) for row in metadata)


                    # 2) Extract the highest value in row[5]
                    # highest_value = max(float(row[5]) for row in metadata)

                    # Define the scope and credentials
                    scope = ['https://spreadsheets.google.com/feeds',
                             'https://www.googleapis.com/auth/drive']
                    credentials = ServiceAccountCredentials.from_json_keyfile_name('meta-data-tracking.json', scope)


                    # Authorize and open the Google Sheet
                    client = gspread.authorize(credentials)

                    # Specify your spreadsheet name
                    spreadsheet_name = 'meta_tracking'

                    try:
                        # Try to open the spreadsheet
                        spreadsheet = client.open(spreadsheet_name)
                    except SpreadsheetNotFound:
                        # If the spreadsheet does not exist, create it
                        print(f"Spreadsheet '{spreadsheet_name}' not found. Creating new one.")
                        spreadsheet = client.create(spreadsheet_name)

                    # Specify your worksheet name
                    worksheet_name = 'BR Data'  

                    try:
                        # Try to get the worksheet
                        worksheet = spreadsheet.worksheet(worksheet_name)
                    except WorksheetNotFound:
                        # If the worksheet does not exist, add it
                        # print(f"Worksheet '{worksheet_name}' not found in spreadsheet '{spreadsheet_name}'. Creating new one.")
                        worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows="100", cols="20")


                    # Find the last row number
                    last_row_number = len(worksheet.get_all_values()) + 1


                    # Append the results to the Google Sheet without the formula
                    result_row = [channel_name, "Enter Map Name", " ", int(winner[6]), int(winner[7]), total, marbcount, int(winner[4]), " ", " ", " "]
                    worksheet.append_row(result_row)

                    # Define the formula with the dynamic row number
                    points_per_marble_calc = f"=(H{last_row_number}/G{last_row_number})"
                    PPMformula2 = f"=(K{last_row_number}/C{last_row_number})*60"
                    PPMPMformula = f"=(I{last_row_number}/C{last_row_number})*60"

                    # Update the specific cell with the formula
                    points_per_marble = f'I{last_row_number}' # assuming the formula should go in column J
                    streamerPPM = f'L{last_row_number}' # assuming the formula should go in column 
                    ppmpm_cell = f'J{last_row_number}' # assuming the formula should go in column

                    worksheet.update_acell(points_per_marble, points_per_marble_calc)
                    worksheet.update_acell(streamerPPM, PPMformula2)
                    worksheet.update_acell(ppmpm_cell, PPMPMformula)


           
                    # latest battle royale winner saved
                    if winner[1] != winner[2].lower():
                        lastwinner1 = "{} ({}) with {} points, ".format(winner[2], winner[1], winner[4])
                    else:
                        lastwinner1 = "{} with {} points, ".format(winner[2], winner[4])
            
                    lastwinner2 = "{} kills and {} damage.".format(winner[6], winner[7])
                    with open('LatestWinner.txt', 'w', encoding='utf-8', errors='ignore') as hs:
                        hs.write("Previous Winner:" + '\n')
                        hs.write(lastwinner1 + '\n')
                        hs.write(lastwinner2 + '\n')
            
                    # Count Race Winners Total Races Completed
                    totalcount = 0
                    with open(allraces, 'r', encoding='utf-8', errors='ignore') as rc:
                        reader = csv.reader(rc)
                        for row in reader:
                            if row[1] == winner[1]:
                                totalcount += 1
            
                    # variables for output
                    if winner[1] != winner[2].lower():
                        wname = winner[1]
                    else:
                        wname = winner[2]
                    wpoints = '{:,}'.format(int(winner[4]))
                    wkills = winner[6]
                    wdam = winner[7]
            
                    if winner[3] == 'ABCFF7FF':
                        namecolor = Fore.BLUE + Style.BRIGHT + wname + Fore.RESET
                    elif winner[3] == 'F91ED2FF':
                        namecolor = Fore.MAGENTA + Style.BRIGHT + wname + Fore.RESET
                    elif winner[3] == 'FF82D6FF':
                        namecolor = Fore.MAGENTA + Style.NORMAL + wname + Fore.RESET
                    elif winner[3] == '79FFC7FF':
                        namecolor = Fore.GREEN + Style.BRIGHT + wname + Fore.RESET
                    elif winner[3] == 'F88688FF':
                        namecolor = Fore.RED + Style.BRIGHT + wname + Fore.RESET
                    else:
                        namecolor = Fore.WHITE + Style.BRIGHT + wname + Fore.RESET
            
                    if winner[1] != winner[2].lower():
                        message = "Battle Royale Champion 🏆: {}({}) with {} points, {} eliminations and {} damage.".format(
                            winner[2], winner[1], '{:,}'.format(int(winner[4])), winner[6], winner[7]) + " " + winner[2] + "(" + winner[
                                      1] + ")" + " has earned " + str('{:,}'.format(int(winnertotalpoints))) + " total points today with " + str(
                            wcount) + " wins in " + " " + str('{:,}'.format(int(totalcount))) + " total races."
                    else:
                        message = "Battle Royale Champion 🏆: {} with {} points, {} eliminations and {} damage.".format(winner[2],
                                                                                                                       '{:,}'.format(int(winner[4])),
                                                                                                                       winner[6],
                                                                                                                       winner[
                                                                                                                           7]) + " " + \
                                  winner[2] + " has earned " + str('{:,}'.format(int(winnertotalpoints))) + " total points today with " + str(
                            wcount) + " wins in " + str('{:,}'.format(int(totalcount))) + " total races."
                    # message2 = winner[2] + " Stats: " + str(wcount) + " wins and " + str('{:,}'.format(int(winnertotalpoints))) + " total points today.".format(winner[2])
                    print("Battle Royale: " + Fore.YELLOW + str(
                        marbcount) + Style.RESET_ALL + " " + namecolor + " with " + Fore.GREEN + wpoints + Style.RESET_ALL + " points, " + Fore.RED + wkills + Style.RESET_ALL + " eliminations and " + Fore.RED + wdam + Style.RESET_ALL + " damage." + " Total Wins: " + Fore.CYAN + str(
                        wcount) + Style.RESET_ALL + " Points: " + Fore.CYAN + str('{:,}'.format(int(winnertotalpoints))) + Style.RESET_ALL.format(
                        winner[2], '{:,}'.format(int(winner[4])), winner[6], winner[7]))
                    if AnnounceDelay == True:
                        await asyncio.sleep(AnnounceDelayTime)
                        await bot.channel.send(message)
            
                    else:
                        await bot.channel.send(message)
                else:
                    print("CSV file is empty.")

        await asyncio.sleep(7)

# Start the bot in the main thread
bot.run()
