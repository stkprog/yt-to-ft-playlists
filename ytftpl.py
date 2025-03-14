from colorama import init, Fore             # Colored text
from subprocess import Popen, PIPE, STDOUT  # Opening yt-dlp
from uuid import uuid4  # Getting version 4 uuids
from time import time   # Getting current UNIX timestamp
import json             # JSON
import re               # RegEx
import os               # Path opening and such
import sys              # Check which OS, exit
import argparse         # Clean CLI

class PlaylistDoesntExistError(Exception):
    """Playlist either does not exist or can't be found because it is private."""
    pass

class UnsupportedBrowserError(Exception):
    """The user specified a browser with the -c option that yt-dlp does not support."""
    pass

class PlaylistDatabaseNotFoundError(Exception):
    """playlists.db cannot be found on the user's hard drive."""

    def __init__(self, database_path : str):
        super().__init__("")
        self.database_path = database_path

def print_colorful_message(message_color : str, message_white : str, color : str) -> None:
    """Colorful output for error or success messages."""
    print(color + message_color, end="")
    print(Fore.RESET + message_white)

def initialize_parser() -> argparse.ArgumentParser:
    """Creates and returns the command line argument parser."""
    # Initialize parser with a help option & nice formatting
    parser = argparse.ArgumentParser(
        description="This is a small Python script that transfers YouTube playlists to FreeTube.",
        add_help=True,
        formatter_class=lambda prog: argparse.RawDescriptionHelpFormatter(prog="ytftpl.py", indent_increment=4, max_help_position=48, width=None)
    )
    # Positional Argument
    parser.add_argument(
        "playlist_url",
        help="Full URL of the playlist you want to transfer",
        type=str
    )
    # Flag
    parser.add_argument(
        "-q", "--quiet",
        help="Only output JSON at the end, don't show each video as it is being extracted",
        action="store_true"
    )
    # Flag
    parser.add_argument(
        "-i", "--silent",
        help="Only output ytftpl's error or success messages",
        action="store_true"
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
        "-s", "--sleep",
        help="Time in seconds to sleep between videos. Can be used to combat rate limiting for longer playlists, e.g. a value of 5",
        type=int,
        required=False,
        metavar="SLEEP SECONDS"
    )
    # Optional
    parser.add_argument(
        "-p", "--path",
        help="Absolute path to playlists.db if it is not in the usual location",
        type=str,
        required=False,
        metavar="DB PATH"
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
        print_colorful_message(
            message_color=first_line[0:6], 
            message_white=first_line[6:],
            color=Fore.RED
        )
        raise PlaylistDoesntExistError()

    for line in popen.stdout:
        # Error, usually regarding a video, simply output these
        if line.startswith("ERROR"):
            is_age_restr_error : bool = line.find(age_restr_message) != -1
            print_colorful_message(
                message_color=line[0:6],
                message_white=line[6:],
                color=Fore.RED
            )

            if is_age_restr_error and cookies_given:
                age_restr_errors.append(re.search(id_pattern, line).group())
        # Unsupported browser, yt-dlp help message gets output
        elif line.find("unsupported browser specified for cookies") != -1:
            print_colorful_message(
                message_color=line[0:7],
                message_white=line[7:],
                color=Fore.RED
            )
            raise UnsupportedBrowserError()
        # Don't print in case of an error that shows yt-dlp's CLI help
        elif line.startswith("Usage") or line.startswith("\n"):
            pass
        # Error-less line, add to output
        else:
            if not (cli_args.quiet or cli_args.silent):
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
    finished_data["createdAt"] = int(round(time() * 1000))
    finished_data["lastUpdatedAt"] = int(round(time() * 1000))

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
        "timeAdded": int(round(time() * 1000)),
        "playlistItemId": str(uuid4()),
        "type": "video"
    }

def append_to_playlist_dot_db(data : str, user_specified_path : str = None) -> None:
    """Will make an attempt to append the processed data to FreeTube's playlist database."""
    
    playlist_database_path : str = ""
    database_name : str = "playlists.db"

    if user_specified_path is None:
        home_path : str = os.path.expanduser("~")

        if sys.platform == "windows":
            playlist_database_path = os.path.join(os.getenv("APPDATA"), "FreeTube")
        elif sys.platform == "linux":
            # If FreeTube is installied via FlatPak
            if os.path.exists(os.path.join(home_path, ".var/app/io.freetubeapp.FreeTube/config/FreeTube")):
                playlist_database_path = os.path.join(home_path, ".var/app/io.freetubeapp.FreeTube/config/FreeTube")
            else:
                playlist_database_path = os.path.join(home_path, ".config/FreeTube")
        elif sys.platform == "darwin":
            playlist_database_path = os.path.join(home_path, "Library/Application Support/FreeTube")
        playlist_database_path = os.path.join(playlist_database_path, database_name)
    else:
        playlist_database_path = user_specified_path
        if user_specified_path.find("playlists.db") == -1:
            playlist_database_path = os.path.join(user_specified_path, database_name)

    if not os.path.exists(playlist_database_path):
        raise PlaylistDatabaseNotFoundError(playlist_database_path)
    else:
        # Append new playlist to existing database
        with open(playlist_database_path, "a") as playlist_database_file:
            playlist_database_file.write(data)

def main() -> None:
    """Entrypoint for the script."""
    init()  # Initialize colorama
    parser = initialize_parser()
    args = parser.parse_args()

    # Get unprocessed playlist data including video IDs with an age-restriction error
    try:
        unpr_playlist, errors = get_unprocessed_playlist_json_from_yt(cli_args=args)
    except PlaylistDoesntExistError as e:
        print_colorful_message(
            message_color="ytftpl - " + e.__class__.__name__ + ": ",
            message_white="Playlist either doesn't exist or you are trying to access a private playlist without cookies.",
            color=Fore.YELLOW
        )
        sys.exit(1)
    except UnsupportedBrowserError as e:
        print_colorful_message(
            message_color="ytftpl - " + e.__class__.__name__ + ": ",
            message_white="Unsupported browser specified in -c / --browser-cookies flag.",
            color=Fore.YELLOW
        )
        sys.exit(1)
    
    # Get the playlist in the correct format for FreeTube
    pr_playlist : dict = process_playlist_data(unpr_playlist)
    
    # Loop through each age-restricted video and add them to the videos list of the playlist
    for error in errors:
        age_restricted_video : dict = process_video_data(
            get_unprocessed_video_json_from_yt(video_id=error, browser=args.browser_cookies, sleep=args.sleep)
        )
        pr_playlist["videos"].append(age_restricted_video)

    if not args.silent:
        print(pr_playlist)

    # Attempt to append the data to the user's existing playlists.db file
    try:
        append_to_playlist_dot_db(json.dumps(pr_playlist), args.path)
    except PlaylistDatabaseNotFoundError as e:
        print_colorful_message(
            message_color="ytftpl - " + e.__class__.__name__ + ": ",
            message_white="The path '" + e.database_path + "' couldn't be found.",
            color=Fore.YELLOW
        )
        sys.exit(1)

    # Done :)
    print_colorful_message(
        message_color="ytftpl: ",
        message_white="Playlist '" + pr_playlist["playlistName"] + "' successfully added to FreeTube!",
        color=Fore.GREEN
    )

main()