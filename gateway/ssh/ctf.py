"""
This file contains data specifically about the COOP-CTF.
It should probably be moved to a non-version controlled configuration file later.
"""

_teams = (
    "HungryMarauders",
    "Cannibals",
    "StellarExplorers",
    "MidtownMVPs",
    "RedTeam",
    "CleverBoulders",
    "UptownPanthers",
    "QuantumQuandaries",
    "RenownedTigers",
    "RiddlesReloaded",
    "PowerfulPowerhouse",
    "QubitsGeneral",
    "ArcticAvengers",
    "MuddyKings",
    "RuthlessDetectives",
    "CrimsonAstronauts"
)

teams = tuple(team.lower() for team in _teams)

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


def capitalize_team_name(team_name: str):
    for team in _teams:
        if team.lower() == team_name.lower():
            return team
    return team_name
