"""
This file contains data specifically about the COOP-CTF.
It should probably be moved to a non-version controlled configuration file later.
"""

# _teams = (
#     "HungryMarauders",
#     "Cannibals",
#     "StellarExplorers",
#     "MidtownMVPs",
#     "RedTeam",
#     "CleverBoulders",
#     "UptownPanthers",
#     "QuantumQuandaries",
#     "RenownedTigers",
#     "RiddlesReloaded",
#     "PowerfulPowerhouse",
#     "QubitsGeneral",
#     "ArcticAvengers",
#     "MuddyKings",
#     "RuthlessDetectives",
#     "CrimsonAstronauts"
# )
import json
from pathlib import Path
from typing import Tuple, Dict


class CTF:
    _teams: Dict[str, str] = {}

    @staticmethod
    def team_names() -> Tuple[str]:
        return tuple(CTF._teams.keys())

    @staticmethod
    def team_names_lowercase() -> Tuple[str]:
        return tuple(team.lower() for team in CTF._teams.keys())

    challenge_images = {
        "catwalk": "momothereal/ctf-linux-linux-cat",
        "foreign": "momothereal/ctf-linux-linux-base64",
        "prithee": "momothereal/ctf-linux-linux-chmod",
        "glaf": "momothereal/ctf-linux-linux-grep",
        "squeeze": "momothereal/ctf-linux-linux-gunzip",
        "plainsight": "momothereal/ctf-linux-linux-hidden",
        "soar": "momothereal/ctf-linux-linux-priv-esc",
        "whereabouts": "momothereal/ctf-linux-linux-find",
        "sweep": "momothereal/ctf-linux-linux-nmap",
    }

    @staticmethod
    def capitalize_team_name(team_name: str):
        for team in CTF._teams:
            if team.lower() == team_name.lower():
                return team
        return team_name

    @staticmethod
    def load_teams() -> None:
        CTF._teams = json.loads(Path("teams.json").read_text())

    @staticmethod
    def check_password(team: str, password: str):
        return CTF._teams.get(CTF.capitalize_team_name(team)) == password
