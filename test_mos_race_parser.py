import csv
import tempfile
import unittest
from pathlib import Path

from mos_race_parser import parse_race_exports


class RaceExportParserTests(unittest.TestCase):
    def write_csv(self, directory, name, rows):
        path = Path(directory) / name
        with path.open("w", newline="", encoding="utf-8") as output:
            csv.writer(output).writerows(rows)
        return str(path)

    def test_keeps_legacy_layout(self):
        with tempfile.TemporaryDirectory() as directory:
            race = self.write_csv(directory, "race.csv", [["Position", "UserName", "DisplayName", "Color", "Points", "FinishTime", "Eliminated"], [1, "user", "User", "blue", 42, 12.5, "false"]])
            self.assertEqual(parse_race_exports(race)[0], ["1", "user", "User", "blue", "42", "12.5", "false"])

    def test_combines_new_split_files_without_changing_output_shape(self):
        with tempfile.TemporaryDirectory() as directory:
            race = self.write_csv(directory, "race.csv", [["Rank", "MarbleId", "FinishTime", "DNF"], [1, "abc", 8.2, "false"]])
            summary = self.write_csv(directory, "summary.csv", [["MarbleId", "PointsEarned"], ["abc", 100]])
            watched = self.write_csv(directory, "watched.csv", [["MarbleId", "TwitchUsername", "DisplayName", "NameColor"], ["abc", "viewer", "Viewer", "green"]])
            result = parse_race_exports(race, summary, watched)
            self.assertEqual(result, [["1", "viewer", "Viewer", "green", "100", "8.2", "false"]])
            self.assertEqual(len(result[0]), 7)


if __name__ == "__main__":
    unittest.main()
