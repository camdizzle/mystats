ALL SETTINGS ARE UPDATED IN settings.txt.  PLEASE UPDATE THAT FILE BEFORE USING.

You can obtain your oauth token by going to: 

https://twitchapps.com/tmi/ 

Log in with the account that you wish to use to make the announcements in chat.  The TWITCH_USERNAME in the settings file will need to match the account that you use to obtain the token.

A sample of how the settings file could look with a bot:

TWITCH_USERNAME:shipcaptain
TWITCH_TOKEN=96j1jnjtnl7iajonl7iajo
CHANNEL=camwow

A sample of how the settings file could look with you:

TWITCH_USERNAME:camwow
TWITCH_TOKEN=96j1jnjtnl7iajonl7iajo
CHANNEL=camwow

****** YOUR TWITCH_USERNAME AND CHANNEL NAME MUST BE ALL LOWERCASE LETTERS!!!!!!! ******

To run the program, double click on Announce Race Results Bot 2.3.exe, if it disappears, open again.  Sometimes the connection to twitch chat fails and you need to re-run the application.

OBS OVERLAY FILES:
CountofRaces.txt (The number of races recorded in the results file for today)
AvgPointsToday.txt (Avg of points earned / Races completed)
HighScore.txt (Name and Points of the high score of the day!)
LatestWinner.txt (Text output displaying the last race winner)
TotalPointsToday.txt (Total points earned today)
WinnerTotalPoints.txt (Total points of the last race winner)

If you have any questions, or issues, or suggestions, visit discord.gg/camwow and contact CamWOW!!!.

Version 2.5.2
- FINALLY RESOLVED FOREIGN CHARACTER ISSUES!!!!!!
- Added Total Race Count to Message output in chat
- Overhaul for speed of processing data
- Timezone adjusted to reset data files at marbles reset. 
- Added Season.txt file to keep season number to update each offseason.

Version 2.5.1
- Fixed a bug where a big race (10 winners) would exceed the # of characters for a twitch message (500).  I removed the word with from the message so instead of (1) CamWOW with 100 points, its (1) CamWOW 100 Points.  This allows all 10 to fit without crashing.

Version 2.5
- Final bug fixes
- Race count was included non-first place race finishes, fixed.

Version 2.4.3
- Fixed a bug where the winner's points of a standard race were not being added to the total file.  Thanks x24 for this one.
- Fixed high score for race winner, was double printing the points with no name.  Thanks x24.
- Fixed marble count missing from first race in results file


Version 2.4.2
- Sorry for the multiple revisions, I got ahead of myself with some of the coding and didn't test it properly, my bad.  
- Fixed foreign character issue with race results
- enhanced coloring for race results in black window
- added marble count to race results
- add marble count to data results file
- fixed issue with delay, when set to yes it would fail
- fixed alert sound not firing


Version 2.4.1
- Fixed a bug where a lap race with 0 points givens crashes the application.  I fixed it to ensure first row always is pulled so there will be no failure.  Found this during clean up tonight.  Fixed a high score calculation bug in race data too.

Version 2.4
- Fixed a typo in the output results in chat
- Add marble count and winners days total stats to black window
- Made some efficiency improvements to the code
- Still some bugs in regular races, especially due to foreign characters.  Still working on this.

Version 2.3
- Fixed foreign characters data issues, hopefully for good.
- Added “biggest chunk” overlay text file. This will take the largest point win of the day and retain that value for your overlay. 
- Added chunk alert option. You can choose whether to turn it on or off and how many points you would like the threshold to trigger at. Default is 1000.  You can change the mp3 sound and instructions will be added to ReadMe file.
- added an option to increase or decrease the delay of the results posting to chat. Current delay is too long for fast grinders.
- Changed format of data results storage, included time stamp.
- Added Previous winner results in a text file to allow you to mimic what Vibblez is doing on screen. 
- Added High Score for the day, includes name and points


Version 2.2
- Fixed a bug where if you have never run a race or BR, and the CSV file hasnt been created yet, the script would fail.  Corrected this by only warning the file is missing and not ending the script.  Thanks to ghost_of_tuhhh for finding this bug.
- Fixed a bug where someone with scuffed energy tricked the results bot into thinking that there were no longer any more point earners (because of 0 points).  This caused others below the scuffed player to not get recorded.  Thank you to x24rocks for finding this bug.  Bug fixed!
- Error reading marbles file when non-english characters were in a display name.  This issue still persists. The script will not fail, but the data recorded is not properly encoded.  Thank you Iceprincessbibi for exposing this bug.
- Fixed a bug when a new day ticks over (midnight) the script fails to find the new results file and errors out.  Removed the error.
- Added additional 10 second delay to display results in chat. In total, the message could appear as late as 20 seconds after the race completed.  This will allow the streamer a few more moments to react, or create suspense, to the race results.
- Cleaned up functionality, improved speed.

Version 2.1
- Fixed Ping issue, i hope.
- Changed Standard Race reporting, by grabbing all users have points and not restricting to just the top 3.  This improved the quality of the results files and for other features mentioned below.
- Reworked the results file, added race placement to first column.  Nested results in directories Results\Year\Month\results_date.csv.
- After every race, Counting the number of races per day and storing the value in a text file called COUNTOFRACES.txt
- After every race, Adding the total points for races per day and storing the value in a text file called TotalPointsToday.txt
- After every race, calculating the average points per race and saving the value in a text file called AvgPointsToday.txt
- Minor code clean up and improvements for efficiency


Version 2.0
- Ping to keep chat connection alive longer than 5 minutes.  Script was dying on long races.
- Added support for standard race results
- Modified format of output into client terminal (black window)
- Store results to a file (results.csv)
- In development - Streamer.bot version (discord.gg/camwow)


Version 1.0
- Connect to twitch chat
- Monitor battleroyale CSV for changes
- Take values from CSV and announce in twitch chat


## OBS Overlay (Built-in Flask)
Use Browser Source: `http://127.0.0.1:5000/overlay`
Health check endpoint: `http://127.0.0.1:5000/api/overlay/health`

Overlay assets now use `/overlay/...` absolute paths so loading `/overlay` works consistently without requiring a trailing slash.

If `/overlay` returns Not Found, open desktop app Settings once and confirm your install includes the `obs_overlay` folder (the app now checks multiple locations automatically, including packaged and working-directory paths).

If `/overlay` still shows Not Found, fully restart the desktop app so Flask reloads the latest routes, then try both `http://127.0.0.1:5000/overlay` and `http://127.0.0.1:5000/overlay/`.

Header stats now show 6 pills:
- Avg Pts Today
- Avg Pts Season
- Unique Racers Today
- Unique Racers Season
- Total Races Today
- Total Races Season

Responsive tweaks are included for smaller OBS source sizes.

Header pills rotate every 10 seconds between Today stats and Season stats.

Overlay settings are controlled from the desktop app (Settings → Overlay) and pushed to the browser source:
- Top stat rotation speed (default 10s)
- Data refresh interval
- Background theme presets
- Card opacity
- Text scale
- Top-3 medal emote visibility
- Compact row spacing
