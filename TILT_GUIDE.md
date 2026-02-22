# MyStats Tilt Mode Guide (Streamer-Friendly)

Welcome to your **Tilt hype hub**. This guide explains how Tilt tracking, the web dashboard, and the overlay work together so your stream always has a clear story.

---

## What Tilt tracking gives you

MyStats turns Tilt sessions into a complete viewing experience:

- **Live run status** so everyone knows what is happening right now.
- **Leader + top-tiltee callouts** so your top performers get instant spotlight.
- **Run, daily, and lifetime progression** updates without manual spreadsheet math.
- **Level and run recaps** to create natural hype checkpoints.
- **Dashboard + OBS overlay support** for polished visuals.
- **Chat-ready summaries and commands** to keep engagement high.

---

## Dashboard + Overlay: what each one does

### Dashboard (Web)
The MyStats web dashboard is your live control-glance view. It now opens from the app sidebar as **MyStats Web Dashboards** and includes the title **MyStats Dashboard Hub**.

Use the dashboard to:

- Watch leaderboard movement in near real time.
- Track Tilt KPIs (run points, run XP, lifetime progress cues).
- Swap between MyCycle, Season Quests, and Tilt views from one page.

### Overlay (OBS)
The overlay is viewer-facing and designed for stream scenes.

Use the overlay to:

- Show current run/level context.
- Surface leaders and top tiltees while the match evolves.
- Display recap moments after clears and at run end.

**Best practice:** Keep the web dashboard on a side monitor for you, and the overlay in OBS for chat.

---

## Important startup behavior (latest EXP sync)

When MyStats loads, it can refresh your base Tilt lifetime EXP from the leaderboard so the session starts with your most recent value.

Why this matters:

- You avoid stale local values.
- Lifetime progress calculations are based on your latest known API total.
- Every new app launch starts from the freshest EXP anchor available.

In short: **launching MyStats updates the Tilt experience baseline from leaderboard data, so your EXP progression starts accurate each time.**

---

## How to use Tilt mode (quick flow)

1. Launch MyStats.
2. Ensure your channel/settings are configured.
3. Open **MyStats Web Dashboards** from the sidebar for live monitoring.
4. Add the Tilt overlay source in OBS.
5. Play Tilt as normal; MyStats handles updates, recaps, and progression outputs.

---

## Math behind Tilt progression (simple explainers)

You do not need to calculate this manually, but it helps to understand what viewers are seeing.

### 1) Run totals
MyStats aggregates per-level performance into run totals:

- **Run Points** = sum of points/events credited during the active run.
- **Run XP** = cumulative XP earned during the active run.

This is the “how strong is this run” layer.

### 2) Daily progression
Daily progression is the sum of all run gains within the current day window:

- **Daily XP** = Σ(run XP for today)
- **Daily points** = Σ(run points for today)

This is the “how today is going overall” layer.

### 3) Lifetime progression anchor
Lifetime progress starts from a base value and adds current-session gains:

- **Lifetime Base XP** = leaderboard-synced starting value at app load.
- **Current Lifetime XP** ≈ Lifetime Base XP + session/day gains tracked since startup.

This is the “long-term account trajectory” layer.

### 4) Milestone-style thinking
Milestones are just threshold checks against totals:

- If total XP crosses target bands, you can trigger recap/chat hype moments.
- If run or daily totals break prior marks, you can spotlight momentum.

So the system is basically: **collect events → aggregate totals → compare to thresholds → surface hype outputs**.

---

## What your viewers feel

With dashboard + overlay + recap flow, viewers get:

- A clear run narrative (start, swings, finish).
- Frequent “checkpoint hype” moments.
- Easy visibility into leaders, top tiltees, and progression.
- Confidence that EXP/progress numbers are current from app launch.

---

## TL;DR

- MyStats provides live Tilt tracking, recap beats, and chat-ready outputs.
- **MyStats Web Dashboards** gives you the control-glance web view.
- The overlay powers polished viewer-facing OBS scenes.
- On load, MyStats can sync lifetime EXP from leaderboard data so you begin with your latest value.
- Progress math is straightforward aggregation + milestone checks under the hood.
