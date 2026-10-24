# Chat Message Comparison Evaluation (MyStats)

## Scope
This review covers message templates and message-construction patterns in `mystats.py` for outputs sent to Twitch chat via:
- `send_chat_message(...)`
- `self.send_command_response(...)`

It focuses on **comparative consistency** (format, tone, symbols, fallback behavior, and readability), so you can decide what to change next.

---

## 1) Channel/type comparison

| Message family | Typical transport | Purpose | Relative consistency |
|---|---|---|---|
| Team management (`!createteam`, `!invite`, `!acceptteam`, etc.) | `self.send_command_response` | Command feedback and moderation flow | **High** |
| Rivals / H2H | `self.send_command_response` | Comparative stat snapshots | **High** |
| MyCycle / Quests | `self.send_command_response` | Progress + lifecycle | **Medium-High** |
| Tilt/Race personal stats (`!mystats`, `!mytilts`, etc.) | `send_chat_message` | User-facing stat summaries | **High** |
| System auto-announcements (race/tilt/BR lifecycle) | `send_chat_message` + dynamic builders | Real-time broadcast alerts | **Medium** |

---

## 2) Formatting comparison

### Prefix & structure patterns

**Strong patterns already in use**
- `Category | segment | segment` style is common and readable.
- Emoji-prefixed headers are frequently used (`⚖️`, `🏃‍➡️`, `🔁`, `🎺`, etc.).
- Long payloads are often chunked to avoid chat length overflow.

**Inconsistencies observed**
1. **Separator drift**: some messages use `|`, others use punctuation-heavy sentence style, especially in help/info responses.
2. **Header naming drift**: similar concepts differ (`Top 10 Finishers 🏆:` vs `🧃 Top 10 Finishers 🏆:` vs `WORLD RECORD 🌎`).
3. **Success marker drift**: some command successes use `✅`, others omit status symbol.
4. **Capitalization drift**: examples like `Todays XP` vs otherwise polished labels.

---

## 3) Tone comparison

| Dimension | Command replies | Auto alerts |
|---|---|---|
| Directiveness | Strong (usage prompts, permission checks) | Medium |
| Verbosity | Medium | Medium-High during event bursts |
| Emotional tone | Utility-first with occasional celebratory emoji | More expressive / hype-oriented |
| Error handling style | Clear and actionable | Sometimes terse (`No ... yet`) |

**Assessment**
- Command replies are generally well-structured for moderation and user correction.
- Auto alerts are energetic but less normalized in naming/taxonomy.

---

## 4) Comparative quality findings (what stands out)

### Best-aligned families
1. **Team command suite**: consistent permission language and corrective prompts.
2. **Rivals/H2H outputs**: dense, comparable fields with stable ordering.
3. **Cycle stats summaries**: clear headline-first format.

### Lowest-aligned families
1. **Race result / leaderboard announcement variants**: multiple close-but-different headline variants for similar payloads.
2. **No-data fallbacks**: semantically similar responses differ in wording (`No ... found`, `No ... available yet`, `No ... recorded yet`).
3. **Info/help link commands**: style shifts to sentence/paragraph mode instead of house format.

---

## 5) Concrete normalization opportunities

If you want to issue change instructions next, these are the highest impact:

1. **Define a single message grammar**
   - Recommendation: `EMOJI Header | Key: Value | Key: Value`.

2. **Standardize fallback text taxonomy**
   - Recommendation:
     - `No <dataset> recorded yet` (historical logs)
     - `No <dataset> available right now` (live API pull)
     - `No <result> found for <query>` (user-specific lookup)

3. **Create shared header constants**
   - Normalize labels for:
     - Top finishers
     - World record
     - Race winners
     - Tilt survivors
     - Cycle completion

4. **Standardize success/error markers**
   - Recommendation:
     - Success = `✅`
     - Warning/usage = `ℹ️` or `⚠️`
     - Denial/invalid permission = `⛔`

5. **Normalize capitalization and microcopy**
   - Example fix: `Todays XP` -> `Today's XP`.

---

## 6) Suggested next-step change plan (for your approval)

1. Add a **message style guide section** in code comments near chat helper functions.
2. Add small formatting helpers:
   - `format_no_data(scope, subject)`
   - `format_success(subject, detail)`
   - `format_usage(command, args)`
3. Refactor highest-traffic message families first:
   - Race winners / top finishers
   - No-data fallbacks
   - Team command success/error responses
4. Run one pass for punctuation and title consistency.

---

## 7) Source extraction note

This evaluation was based on direct scan/extraction of `send_chat_message(...)` and `self.send_command_response(...)` call sites plus surrounding dynamic builders in `mystats.py`.
