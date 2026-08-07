"""Compatibility parser for Marbles on Stream race save-game exports."""

import csv
import io
import re


def _key(value):
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


ALIASES = {
    "position": ("position", "place", "placement", "rank", "finishposition"),
    "login": ("username", "user", "login", "twitchusername", "twitchname", "playername", "marbleowner", "marbleownername"),
    "display": ("displayname", "twitchdisplayname", "marblename", "name", "playerdisplayname", "marbleownerdisplayname"),
    "color": ("color", "namecolor", "usernamecolor", "hexcolor", "colour", "marbleownercolor"),
    "points": ("points", "pointsearned", "pointsawarded", "racepoints", "score", "seasonpoints"),
    "time": ("time", "finishtime", "finishtimeseconds", "racetime", "racetimeseconds", "completiontime"),
    "eliminated": ("eliminated", "iseliminated", "dnf", "didnotfinish"),
    "id": ("id", "playerid", "marbleid", "userguid", "steamid", "twitchid"),
}


def _read_table(path):
    if not path:
        return []
    with open(path, "rb") as source:
        raw = source.read()
    text = raw.decode("utf-8-sig", errors="replace").replace("\x00", "")
    sample = "\n".join(text.splitlines()[:5])
    try:
        delimiter = csv.Sniffer().sniff(sample, delimiters=",\t;").delimiter
    except csv.Error:
        delimiter = "\t" if "\t" in sample else ","
    return list(csv.reader(io.StringIO(text), delimiter=delimiter))


def _records(path):
    try:
        rows = [row for row in _read_table(path) if any(str(cell).strip() for cell in row)]
    except FileNotFoundError:
        return []
    if not rows:
        return []
    normalized = [_key(cell) for cell in rows[0]]
    known = {_key(alias) for aliases in ALIASES.values() for alias in aliases}
    if not any(cell in known for cell in normalized):
        return [{str(index): value for index, value in enumerate(row)} for row in rows]
    return [dict(zip(normalized, row)) for row in rows[1:]]


def _get(record, field, default=""):
    for alias in ALIASES[field]:
        value = record.get(_key(alias))
        if value is not None and str(value).strip() != "":
            return str(value).strip()
    return default


def _merge_key(record):
    return _get(record, "id") or _get(record, "login").lower() or _get(record, "position")


def parse_race_exports(race_path, summary_path=None, watched_path=None):
    """Return the legacy seven race fields while accepting the new split exports.

    The returned fields remain position, login, display name, name color, points,
    finish time, and eliminated.  Keeping this contract prevents changes to the
    allraces file and the command/API upload formats.
    """
    race_records = _records(race_path)
    extra_tables = [_records(summary_path), _records(watched_path)]
    extra_records = [record for table in extra_tables for record in table]
    extras_by_key = {}
    for row in extra_records:
        key = _merge_key(row)
        if key:
            extras_by_key.setdefault(key, {}).update(
                {field: value for field, value in row.items() if str(value).strip()}
            )

    parsed = []
    for index, race in enumerate(race_records):
        # Headerless files retain the pre-update, positional layout.
        if "0" in race:
            parsed.append([race.get(str(column), "").strip() for column in range(7)])
            continue

        extra = {}
        # Some exports have no shared ID but retain identical result ordering.
        for table in extra_tables:
            if index < len(table):
                extra.update(table[index])
        extra.update(extras_by_key.get(_merge_key(race), {}))

        def combined(field, default=""):
            return _get(race, field) or _get(extra, field) or default

        position = combined("position", str(index + 1))
        login = combined("login")
        display = combined("display", login)
        if not login:
            login = display.lower()
        parsed.append([
            position,
            login,
            display,
            combined("color"),
            combined("points", "0"),
            combined("time", "0"),
            combined("eliminated", "false"),
        ])
    return parsed
