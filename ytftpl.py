from uuid import uuid4          
from yt_dlp import YoutubeDL
from time import time
import json
import os
import sys
import platform
import argparse

parser = argparse.ArgumentParser(description="This is a small Python script that transfers YouTube playlists to FreeTube.", add_help=True)

playlist_url = sys.argv[1]
unprocessed_yldlp_string = os.popen("yt-dlp --cookies-from-browser firefox --quiet --no-warnings --skip-download --ignore-errors --print '%(.{playlist_title,id,title,channel,channel_id,duration,timestamp})#j' '" + playlist_url + "'").read()
unprocessed_json = json.loads("[" + unprocessed_yldlp_string.replace("}", "},", unprocessed_yldlp_string.count("}") - 1) + "]")

processed_json_playlist = {
    "playlistName": unprocessed_json[0]["playlist_title"],
    "protected": False,
    "description": "",
}
processed_json_videos = []
for unpr_video in unprocessed_json:
    pr_video = {
        "videoId": unpr_video["id"],
        "title": unpr_video["title"],
        "author": unpr_video["channel"],
        "authorId": unpr_video["channel_id"],
        "lengthSeconds": unpr_video["duration"],
        "published": unpr_video["timestamp"],
        "timeAdded": int(time()),
        "playlistItemId": str(uuid4()),
        "type": "video"
    }
    processed_json_videos.append(pr_video)
processed_json_playlist["videos"] = processed_json_videos
processed_json_playlist["_id"] = "ft-playlist--" + str(uuid4())
processed_json_playlist["createdAt"] = int(time())
processed_json_playlist["lastUpdatedAt"] = int(time())

processed_json_string = json.dumps(processed_json_playlist)
print(processed_json_string)

home_path = os.path.expanduser("~")
playlist_database_path = ""

# https://docs.freetubeapp.io/usage/data-location/
# Windows: %APPDATA%/FreeTube
# Mac: ~/Library/Application Support/FreeTube/
# Linux: ~/.config/FreeTube
# Flatpak: ~/.var/app/io.freetubeapp.FreeTube/config/FreeTube/
if sys.platform == "windows":
    playlist_database_path = os.getenv("APPDATA") + "\\FreeTube\\playlists.db"
elif sys.platform == "linux":
    # if 
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
        playlist_database_file.write(processed_json_string)
    print("\nPlaylist {} successfully added to {}.".format(processed_json_playlist["playlistName"], playlist_database_path))
else:
    print("\nThe path {} was NOT FOUND. Check if it's there, open FreeTube if you haven't.".format(playlist_database_path))