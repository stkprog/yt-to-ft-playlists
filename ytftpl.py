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
        super().__init__("YT-DLP Error. If you are trying to transfer a private playlist you have access to, provide cookies to the script.")

def print_colorful_error(error_message : str) -> None:
    print(Fore.RED + error_message[0:6], end="")
    print(Style.RESET_ALL + error_message[6:], end="")

def initialize_parser() -> argparse.ArgumentParser:
    """Creates and returns the command line argument parser."""
    parser = argparse.ArgumentParser(
        description="This is a small Python script that transfers YouTube playlists to FreeTube.",
        add_help=True
    )
    # Positional Argument
    parser.add_argument(
        "playlist_url",
        help="Full URL of the playlist you want to transfer",
        type=str
    )
    # Optional
    parser.add_argument(
        "-c", "--browser-cookies",
        help="Use cookies from the specified browser for private playlists or age-restricted videos",
        type=str,
        required=False,
        metavar="NAME OF BROWSER"
    )
    # Optional
    parser.add_argument(
        "-s", "--sleep",help="Time in seconds to sleep between videos. Can be used to combat rate limiting for longer playlists, e.g. a value of 5",
        type=int,
        required=False,
        metavar="SLEEP SECONDS"
    )
    return parser

def get_unprocessed_playlist_json_from_yt(cli_args : argparse.Namespace) -> tuple:
    """
    Opens yt-dlp and returns a JSON string containing the data as well as
    a list of video IDs which failed to be extracted due to age-restriction
    despite the user passing cookies to the program.
    """
    ytdlp_command : str = "yt-dlp '" + cli_args.playlist_url + "' --quiet --no-warnings --skip-download --ignore-errors --print '%(.{playlist_title,id,title,channel,channel_id,duration,timestamp})#j'"
    if cli_args.browser_cookies is not None:
        ytdlp_command += " --cookies-from-browser {}".format(cli_args.browser_cookies)
    if cli_args.sleep is not None:
        ytdlp_command += " --sleep-requests {}".format(cli_args.sleep)

    popen = Popen(ytdlp_command, shell=True, stdout=PIPE, stderr=STDOUT, universal_newlines=True)
    
    output : str = ""
    age_restr_errors : list = []

    cookies_given : bool = ytdlp_command.find("--cookies-from-browser") != -1
    age_restr_message = "Sign in to confirm your age. This video may be inappropriate for some users."
    id_pattern : str = "[A-Za-z0-9_-]{10}[AEIMQUYcgkosw048]"

    first_line = popen.stdout.readline()
    if first_line.find("YouTube said: The playlist does not exist.") != -1:
        print_colorful_error(first_line)
        raise PlaylistDoesntExistException()

    for line in popen.stdout:
        if line.startswith("ERROR"):
            is_age_restr_error : bool = line.find(age_restr_message) != -1
            print_colorful_error(line)

            if is_age_restr_error and cookies_given:
                age_restr_errors.append(re.search(id_pattern, line).group())
        else:
            print(line, end="")
            output += line

    output = "[{" + output.replace("}", "},", output.count("}") - 1) + "]"
    output_dict = json.loads(output)

    return (output_dict, age_restr_errors)

def get_unprocessed_video_json_from_yt(video_id : str, browser : str, sleep : int) -> dict:
    """Executes a yt-dlp command for a single video and returns the data."""
    video_url : str = "https://www.youtube.com/watch?v={}".format(video_id)
    ytdlp_command : str = "yt-dlp '" + video_url + "' --quiet --no-warnings --skip-download --ignore-errors --print '%(.{id,title,channel,channel_id,duration,timestamp})#j' --cookies-from-browser " + browser
    if sleep is not None:
        ytdlp_command += " --sleep-requests {}".format(sleep)

    output : str = os.popen(ytdlp_command).read()
    print(output)
    return json.loads(output)

def process_playlist_data(unpr_playlist_json : dict) -> dict:
    """Takes the yt-dlp JSON playlist data and converts it to the right format for FreeTube."""
    finished_data : dict = {
        "playlistName": unpr_playlist_json[0]["playlist_title"],
        "protected": False,
        "description": "",
    }
    pr_videos_json : list = []
    for video in unpr_playlist_json:
        pr_video : dict = process_video_data(video)
        pr_videos_json.append(pr_video)
    finished_data["videos"] = pr_videos_json
    finished_data["_id"] = "ft-playlist--" + str(uuid4())
    finished_data["createdAt"] = int(time())
    finished_data["lastUpdatedAt"] = int(time())

    return finished_data

def process_video_data(unpr_video_json : dict) -> dict:
    """Takes a video JSON object and converts it to the right format for FreeTube."""
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
    """Will make an attempt to append the processed data to FreeTube's playlist database."""
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
    """Entrypoint for the script."""
    init()  # Initialize colorama
    parser = initialize_parser()
    args = parser.parse_args()

    try:
        unpr_playlist, errors = get_unprocessed_playlist_json_from_yt(cli_args=args)
    except PlaylistDoesntExistException as error:
        print(error)
        sys.exit(1)
    
    print("\n\nErrors: " + str(errors) + "\n\n")
    pr_playlist : dict = process_playlist_data(unpr_playlist)
    
    for error in errors:
        age_restricted_video : dict = process_video_data(get_unprocessed_video_json_from_yt(video_id=error))
        pr_playlist["videos"].append(age_restricted_video)

    print(pr_playlist)

main()