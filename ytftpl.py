from colorama import init, Fore, Style      # Colored text
from subprocess import Popen, PIPE, STDOUT  # Opening yt-dlp
from uuid import uuid4  # Getting version 4 uuids
from time import time   # Getting current UNIX timestamp
import json             # JSON
import re               # RegEx
import os               # Path opening and such
import sys              # Check which OS, exit
import argparse         # Clean CLI

class PlaylistDoesntExistException(Exception):
    """Playlist either does not exist or can't be found because it is private."""

    def __init__(self):
        super().__init__("\nYT-DLP Error. If you are trying to transfer a private playlist you have access to, provide cookies to the script.")

def initialize_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="This is a small Python script that transfers YouTube playlists to FreeTube.",
        add_help=True
    )
    parser.add_argument(
        "playlist_url",
        help="Full URL of the playlist you want to transfer",
        type=str
    )
    parser.add_argument(
        "-c", "--browser-cookies",
        help="Use cookies from the specified browser for private playlists or age-restricted videos",
        type=str,
        required=False,
        metavar="NAME OF BROWSER"
    )
    parser.add_argument(
        "-s", "--sleep",help="Time in seconds to sleep between videos. Can be used to combat rate limiting for longer playlists, e.g. a value of 5",
        type=int,
        required=False,
        metavar="SLEEP SECONDS"
    )
    return parser

def get_unprocessed_playlist_json_from_youtube(ytlp_command : str) -> tuple:
    command = Popen(ytlp_command, shell=True, stdout=PIPE, stderr=STDOUT, universal_newlines=True)
    
    output : str = ""
    age_restr_errors : list = []

    cookies_given : bool = ytlp_command.find("--cookies-from-browser") != -1
    age_restr_message = "Sign in to confirm your age. This video may be inappropriate for some users."
    id_pattern : str = "[A-Za-z0-9_-]{10}[AEIMQUYcgkosw048]"
    
    for line in iter(command.stdout.readline, ""):
        if line.startswith("ERROR"):
            is_age_restr_error : bool = line.find(age_restr_message) != -1
            print(Fore.RED + line[0:6], end="")
            print(Style.RESET_ALL + line[6:], end="")

            print("\nis_age_restr_error: " + str(is_age_restr_error))
            print("cookies_given: " + str(cookies_given))
            if is_age_restr_error and cookies_given:
                age_restr_errors.append(re.search(id_pattern, line).group())
        else:
            print(line, end="")
            output += (line)

    return (output, age_restr_errors)

def get_one_unprocessed_video_json_from_youtube(video_id : str) -> dict:
    video_url : str = "https://www.youtube.com/watch?v={}".format(video_id)
    unpr_video_string : str = os.popen(
        "yt-dlp --cookies-from-browser firefox --quiet --no-warnings --skip-download --ignore-errors --print '%(.{id,title,channel,channel_id,duration,timestamp})#j' '" + video_url + "'"
    ).read()
    unpr_video_json : dict = json.loads(unpr_video_string)
    return unpr_video_json

def process_playlist_data(unpr_playlist_json : dict) -> str:
    pr_playlist_json : dict = {
        "playlistName": unpr_playlist_json[0]["playlist_title"],
        "protected": False,
        "description": "",
    }
    pr_videos_json : list = []
    for unpr_video_json in unpr_playlist_json:
        pr_video = process_singular_video_data(unpr_video_json)
        pr_videos_json.append(pr_video)
    pr_playlist_json["videos"] = pr_videos_json
    pr_playlist_json["_id"] = "ft-playlist--" + str(uuid4())
    pr_playlist_json["createdAt"] = int(time())
    pr_playlist_json["lastUpdatedAt"] = int(time())

    processed_json_string = json.dumps(pr_playlist_json)
    return processed_json_string

def process_singular_video_data(unpr_video_json : dict) -> dict:
    return {
        "videoId": unpr_video_json["id"],
        "title": unpr_video_json["title"],
        "author": unpr_video_json["channel"],
        "authorId": unpr_video_json["channel_id"],
        "lengthSeconds": unpr_video_json["duration"],
        "published": unpr_video_json["timestamp"],
        "timeAdded": int(time()),
        "playlistItemId": str(uuid4()),
        "type": "video"
    }

def append_to_playlist_dot_db(data : str):
    home_path : str = os.path.expanduser("~")
    playlist_database_path : str = ""

    if sys.platform == "windows":
        playlist_database_path = os.getenv("APPDATA") + "\\FreeTube\\playlists.db"
    elif sys.platform == "linux":
        # If FreeTube is installied via FlatPak
        if os.path.exists(home_path + "/.var/app/io.freetubeapp.FreeTube/config/FreeTube/"):
            playlist_database_path = home_path + "/.var/app/io.freetubeapp.FreeTube/config/FreeTube/playlists.db"
        else:
            # playlist_database_path = home_path + "/.config/FreeTube/playlistssss.db"
            sys.exit(0)
    elif sys.platform == "darwin":
        playlist_database_path = home_path + "/Library/Application Support/FreeTube/playlists.db"

    if os.path.exists(playlist_database_path):
        # Append new playlist to existing database
        with open(playlist_database_path, "a") as playlist_database_file:
            playlist_database_file.write(data)
        print("\nPlaylist successfully added to {}.".format(playlist_database_path))
    else:
        print("\nThe path {} was NOT FOUND. Check if it's there, open FreeTube if you haven't.".format(playlist_database_path))

def main():
    parser = initialize_parser()
    args = parser.parse_args()

    command : str = "yt-dlp '" + args.playlist_url + "' --quiet --no-warnings --skip-download --ignore-errors --print '%(.{playlist_title,id,title,channel,channel_id,duration,timestamp})#j'"
    if args.browser_cookies is not None:
        command += " --cookies-from-browser {}".format(args.browser_cookies)
    if args.sleep is not None:
        command += " --sleep-requests {}".format(args.sleep)

    try:
        unpr_playlist, errors = get_unprocessed_playlist_json_from_youtube(ytlp_command=command)
        print("\n")
        print(unpr_playlist)
        print("\n")
        print(errors)
    except PlaylistDoesntExistException as error:
        print(error)
        sys.exit(1)
    # pr_playlist_string : str = process_playlist_data(unpr_playlist_json)
    # print("\n" + pr_playlist_string)

main()