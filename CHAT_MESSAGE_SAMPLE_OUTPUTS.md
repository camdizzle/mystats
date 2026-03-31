# Chat Message Sample Outputs (Using Sample Data)

This file lists chat-message outputs from `mystats.py` call sites and renders f-string placeholders with sample values so you can review exact output shape.

| Line | API | Sample output |
|---:|---|---|
| 11851 | `self.send_command_response` | `!createteam is subscriber-only right now.` |
| 11857 | `self.send_command_response` | `@CamWOW you are already in team 'Sample'.` |
| 11866 | `self.send_command_response` | `Team name 'Speed Demons' already exists.` |
| 11887 | `self.send_command_response` | `✅ Team 'Speed Demons' created. Captain: @CamWOW` |
| 11903 | `self.send_command_response` | `Only captains/co-captains can invite.` |
| 11907 | `self.send_command_response` | `@CamWOW is already in a team.` |
| 11913 | `self.send_command_response` | `Invite already pending for @CamWOW.` |
| 11926 | `self.send_command_response` | `📨 @CamWOW invited to 'Speed Demons'. Use !acceptteam Speed Demons` |
| 11939 | `self.send_command_response` | `You are already in 'Speed Demons'.` |
| 11948 | `self.send_command_response` | `No pending invite for that team.` |
| 11954 | `self.send_command_response` | `That team no longer exists.` |
| 11960 | `self.send_command_response` | `'Speed Demons' is full (30).` |
| 11968 | `self.send_command_response` | `✅ @CamWOW joined 'Speed Demons'.` |
| 11984 | `self.send_command_response` | `Invite to 'Sample' denied.` |
| 11986 | `self.send_command_response` | `No pending invite found.` |
| 11999 | `self.send_command_response` | `Only captains can assign co-captains.` |
| 12003 | `self.send_command_response` | `Target must be a current team member.` |
| 12009 | `self.send_command_response` | `@CamWOW is now co-captain of 'Speed Demons'.` |
| 12022 | `self.send_command_response` | `Only captains/co-captains can kick members.` |
| 12028 | `self.send_command_response` | `Captain cannot be kicked.` |
| 12035 | `self.send_command_response` | `Target is not in your team.` |
| 12040 | `self.send_command_response` | `@CamWOW was removed from 'Speed Demons'.` |
| 12052 | `self.send_command_response` | `You are not in a team.` |
| 12065 | `self.send_command_response` | `Team 'Speed Demons' archived (no members left).` |
| 12074 | `self.send_command_response` | `@CamWOW left 'Speed Demons'.` |
| 12084 | `self.send_command_response` | `@CamWOW is not currently on a team.` |
| 12158 | `self.send_command_response` | `@CamWOW is not currently on a team.` |
| 12163 | `self.send_command_response` | `Team data unavailable.` |
| 12233 | `self.send_command_response` | `Usage: !renameteam New Team Name` |
| 12239 | `self.send_command_response` | `Only captains can rename their team.` |
| 12243 | `self.send_command_response` | `Your team is already named 'Speed Demons'.` |
| 12252 | `self.send_command_response` | `Team name 'Speed Demons' already exists.` |
| 12257 | `self.send_command_response` | `Team not found. Please try again.` |
| 12268 | `self.send_command_response` | `✅ Team renamed: 'Speed Demons' -> 'Speed Demons'.` |
| 12281 | `self.send_command_response` | `Only captains/co-captains can set logo.` |
| 12285 | `self.send_command_response` | `Team 'Speed Demons' logo set to Sample` |
| 12297 | `self.send_command_response` | `Only captains/co-captains can set inactive policy.` |
| 12302 | `self.send_command_response` | `Usage: !inactive X` |
| 12324 | `self.send_command_response` | `'Speed Demons' inactive policy set to 50 days.` |
| 12336 | `self.send_command_response` | `You are already in 'Sample'.` |
| 12348 | `self.send_command_response` | `No recruiting teams are currently available.` |
| 12355 | `self.send_command_response` | `✅ @CamWOW joined recruiting team 'Sample'.` |
| 12367 | `self.send_command_response` | `Only captains/co-captains can toggle recruiting.` |
| 12375 | `self.send_command_response` | `Usage: !recruiting on\|off` |
| 12379 | `self.send_command_response` | `Speed Demons recruiting is now Sample.` |
| 12390 | `self.send_command_response` | `No teams found.` |
| 12405 | `self.send_command_response` | `No teams found.` |
| 12415 | `self.send_command_response` | `No daily data available yet.` |
| 12423 | `self.send_command_response` | `No weekly data available yet.` |
| 12449 | `self.send_command_response` | `Failed to pull leaderboard, please try again` |
| 12467 | `self.send_command_response` | `No leaderboard data available right now.` |
| 12520 | `self.send_command_response` | `Failed to pull energy data, please try again.` |
| 12565 | `self.send_command_response` | `Interested in learning more about the Streamer Meta? 📖: https://docs.google.com/document/d/1k93YU73QbGZrmfHqm1cto8PzzF2eADPtpGLILfGawVM/edit` |
| 12571 | `self.send_command_response` | `Download the MOS App on Mobile. Google Play: https://play.google.com/store/apps/details?id=com.pixelbypixel.mosmobile&hl=en-US. Apple App Store: https://apps.apple.com/us/app/marbles-on-stream-mobile/id1443250176` |
| 12578 | `self.send_command_response` | `Purchase Skins or Coins for yourself, or gift them to a friend! https://pixelbypixel.studio/shop` |
| 12583 | `self.send_command_response` | `Marbles on Stream Wiki - https://wiki.pixelbypixel.studio/` |
| 12603 | `self.send_command_response` | `!highfive @camwow` |
| 12644 | `self.send_command_response` | `Rivals is cooling down. Please wait a few seconds before retrying.` |
| 12681 | `self.send_command_response` | `Rivals Check • @CamWOW vs @CamWOW \| Gap: ±1,250 pts \| @CamWOW: 12,345 pts, 321 races \| @CamWOW: 12,345 pts, 321 races \| Trend: closing \| Score: 8,220 \| Sample` |
| 12696 | `self.send_command_response` | `@CamWOW: no season rival data found. Try exact @handle.` |
| 12702 | `self.send_command_response` | `@CamWOW matches multiple users (Sample). Use exact @handle.` |
| 12707 | `self.send_command_response` | `@CamWOW: 321 races so far. Need 321+ races for rivals tracking. Tip: lower Minimum Season Races in Settings → Rivals.` |
| 12716 | `self.send_command_response` | `@CamWOW: no close rivals found within configured point gap. Tip: increase Maximum Point Gap in Settings → Rivals.` |
| 12735 | `self.send_command_response` | `No rivalries found yet with current rival settings.` |
| 12748 | `self.send_command_response` | `Usage: !h2h <user1> <user2>` |
| 12766 | `self.send_command_response` | `⚔️ H2H @CamWOW vs @CamWOW \| Points: 12,345, 12,345 \| Races: 321, 321 \| Race HS: Sample, Sample \| BR HS: Sample, Sample \| 30d Gap: 1,250 \| Score: 8,220 \| Leader: @CamWOW by 1,250` |
| 12823 | `self.send_command_response` | `Unknown MyCycle session 'Sample'.` |
| 12830 | `self.send_command_response` | `@CamWOW: no MyCycle race data yet in session 'Sample'.` |
| 12863 | `self.send_command_response` | `🔁 NextCycle [Season 1] \| No upcoming cycles found yet.` |
| 12885 | `self.send_command_response` | `No MyCycle sessions found. Try !cyclestats all` |
| 12891 | `self.send_command_response` | `🔁 CycleStats [Sample] \| No completed cycles yet.` |
| 12910 | `self.send_command_response` | `🔁 CycleStats [Sample] \| Fastest: Sample \| Slowest: Sample \| Sample \| Total cycles: 123` |
| 12925 | `self.send_command_response` | `@CamWOW: No quest progress found yet.` |
| 12934 | `self.send_command_response` | `🔎 Season Quest Progress` |
| 12988 | `self.send_command_response` | `No season races recorded yet` |
| 13111 | `self.send_command_response` | `No season races recorded yet` |
| 13161 | `send_chat_message` | `📊 @CamWOW: Today: 3 wins, 4,500 points, 12 races. PPR: 375.0 \| Season total: Sample` |
| 13285 | `send_chat_message` | `⚖️ @CamWOW: No tilt data found this season.` |
| 13292 | `send_chat_message` | `⚖️ @CamWOW Tilt Stats \| Run: 12,345 pts, 4 deaths \| Today: 12,345 pts, 4 deaths \| Season: 12,345 pts, 4 deaths \| Last Level Completed: 123` |
| 13346 | `send_chat_message` | `🏃‍➡️ This Run \| No active or completed tilt run available yet.` |
| 13424 | `send_chat_message` | `⚖️ Expertise Stats \| Last Level XP: 123 \| Last Run XP: Sample \| Todays XP: Sample \| Season XP: Sample \| Lifetime XP: Sample` |
| 13461 | `send_chat_message` | `⚖️ No top tiltee data available yet.` |
| 13505 | `send_chat_message` | `⚖️ No tilt data available yet.` |
| 13554 | `send_chat_message` | `⚖️ No tilt data available yet.` |
| 13585 | `send_chat_message` | `⚖️ No tilt survivor-rate data yet (minimum 20 levels participated required).` |
| 13793 | `self.send_command_response` | `No season races recorded yet` |
| 13800 | `self.send_command_response` | `No world records found.` |
| 14627 | `send_chat_message` | `🏁 Tilt run complete! No results to display.` |
| 14980 | `send_chat_message` | `🎺 Marble Day Reset! 🎺` |

## Race and BR dynamic outputs (explicit samples)

The table above captures direct call-site string arguments. Race/BR pipelines also build messages dynamically before sending; here are exact sample outputs for those runtime-built messages.

### Race (sample outputs)
- `🏁 Competitive raid host selected: @CamWOW (128 raiders)! Welcome competitive raiders—good luck and have fun!`
- `🧾 Next competitive raid queue is open now: https://pixelbypixel.studio/competitions`
- `🏁 Competitive raid summary | streamer: camwow | rank: 1 | score: 4200 | wins: 3`
- `🎉 camwow has just completed their 120th race today! Congratulations! 🎉`
- `Race Winners 🏆: No Winners!`
- `🧃 WORLD RECORD 🌎`
- `🧃 Top 10 Finishers 🏆: 🥇 CamWOW | 🥈 RacerX | 🥉 MarblePro`
- `🧃 🌎 WORLD RECORD 🌎: 🥇 CamWOW +12,345 points | 🥈 RacerX +9,876 points`
- `🧃 Race Winners 🏆: 🥇 CamWOW +4,500 points | 🥈 RacerX +3,900 points | 🥉 MarblePro +3,100 points`
- `WORLD RECORD 🌎`
- `Top 10 Finishers 🏆: 🥇 CamWOW | 🥈 RacerX | 🥉 MarblePro`
- `🌎 WORLD RECORD 🌎: 🥇 CamWOW +12,345 points | 🥈 RacerX +9,876 points`
- `Race Winners 🏆: 🥇 CamWOW +4,500 points | 🥈 RacerX +3,900 points | 🥉 MarblePro +3,100 points`
- `Checkpoint Winners: CP1 - CamWOW, CP2 - RacerX, CP3 - MarblePro`
- `🎺 Marble Day Reset! 🎺`

### Battle Royale (sample outputs)
- `🎉 camwow has just completed their 120th race today! Congratulations! 🎉`
- `Battle Royale Champion 🏆: CamWOW +4,200 points, +18 eliminations, +7,900 damage | Today's stats: 55,000 points, 12 wins, 120 races`
- `CROWN WIN! 👑: CamWOW +5,100 points, +22 eliminations, +8,300 damage | Today's stats: 60,100 points, 13 wins, 121 races`
- `🧃 JUICE ALERT! Battle Royale Champion 🏆: CamWOW +7,800 points, +31 eliminations, +11,400 damage | Today's stats: 67,900 points, 14 wins, 122 races`
- `💥 MEGA WIN! Battle Royale Champion 🏆: CamWOW +12,345 points, +41 eliminations, +16,200 damage | Today's stats: 80,245 points, 15 wins, 123 races`
- `🔁 CamWOW completed a MyCycle in Season 1! Cycle #3 took 27 races.`
- `🎯 Season Quest Complete: CamWOW finished 1,000 / 1,000 season races!`
