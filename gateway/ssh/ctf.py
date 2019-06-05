"""
This file contains data specifically about the COOP-CTF.
It should probably be moved to a non-version controlled configuration file later.
"""

teams = tuple(team.lower() for team in (
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
))

challenge_images = {
    "catwalk": "momothereal/ctf-linux-linux-cat",
    "foreign": "momothereal/ctf-linux-linux-base64",
    "prithee": "momothereal/ctf-linux-chmod",
    "glaf": "momothereal/ctf-linux-linux-grep",
    "squeeze": "momothereal/ctf-linux-linux-gunzip",
    "plainsight": "momothereal/ctf-linux-linux-hidden",
    "soar": "momothereal/ctf-linux-linux-priv-esc",
    "whereabouts": "momothereal/ctf-linux-linux-find",
    "sweep": "momothereal/ctf-linux-linux-nmap",
}
