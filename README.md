# yt_to_ft_playlists

This is a small Python script that transfers YouTube playlists to [FreeTube](https://github.com/FreeTubeApp/FreeTube/tree/f1030e984791d07c3e4a4c53991a195df53b6bee). It uses [yt-dlp](https://github.com/yt-dlp/yt-dlp) to extract the data of the given playlist.

#### Table of Contents:
- [Usage](#usage)
- [Result](#result)
- [Requirements](#requirements)
- [Possible Errors and Issues](#possible-errors-and-issues)
    - [Unavailable videos](#unavailable-videos)
    - [Long playlists](#long-playlists)
    - [Missing user authentication](#missing-user-authentication)
- [Technical Details](#technical-details)

## Usage
Make sure that _FreeTube_ is closed, none of its processes are running and backup your ``playlists.db`` file before running the script.
 
```
ytftpl.py [-h] [-q] [-i] [-c NAME OF BROWSER] [-s SLEEP SECONDS] [-p DB PATH] playlist_url

This is a small Python script that transfers YouTube playlists to FreeTube.

positional arguments:
    playlist_url                           Full URL of the playlist you want to transfer

options:
    -h, --help                             show this help message and exit
    -q, --quiet                            Only output JSON at the end, don't show each video as it is being extracted
    -i, --silent                           Only output ytftpl's error or success messages
    -c, --browser-cookies NAME OF BROWSER  Use cookies from the specified browser for private playlists or age-restricted videos
    -s, --sleep SLEEP SECONDS              Time in seconds to sleep between videos. Can be used to combat rate limiting for longer playlists, e.g. a value of 5
    -p, --path DB PATH                     Absolute path to playlists.db if it is not in the usual location
```

Example:
```
python3 ytftpl.py -c firefox -s 5 "https://www.youtube.com/playlist?list=PLmXxqSJJq-yUvMWKuZQAB_8yxnjZaOZUp"
```

## Result
If everything goes correctly, the program outputs the processed playlist data to the console for easy copying (if ``--silent`` is _not_ specified), and then attempts to append the playlist to _FreeTube's_ ``playlists.db`` file.

## Requirements
[Python](https://www.Python.org/downloads/) and [yt-dlp](https://github.com/yt-dlp/yt-dlp) are required to run the source code. [Colorama](https://pypi.org/project/colorama/) is used for colored output.
Last used versions for development:
* Python version 3.13.2
* Colorama version 0.4.6-5
* yt-dlp version 2025.02.19

## Possible Errors and Issues 
Listed in this segment are a few errors I've encountered when trying to extract playlist data using _yt-dlp_. So far I've tested the program using a few playlists with video counts ranging from 5 to 1500. Below that you can find more info on using cookies.

These errors do not not hinder the program from running, but your playlists might not have been transferred 100% correctly. The error entries are output at the end of execution so you can investigate which videos failed to be loaded.

### Unavailable videos
The following errors occur when trying to access videos that have become unavailable due to copyright claims, TOS violations or other (unspecified) reasons, as well as videos that have been privated by the owner. Unfortunately, neither _yt-dlp_ or I can do anything about this.
```
ERROR: [youtube] [VIDEO ID]: Video unavailable. This video contains content from [LEGAL PERSON], who has blocked it in your country on copyright grounds

ERROR: [youtube] [VIDEO ID]: Video unavailable. This video is no longer available due to a copyright claim by [LEGAL PERSON]

ERROR: [youtube] [VIDEO ID]: Video unavailable. This video is no longer available because the YouTube account associated with this video has been terminated.

ERROR: [youtube] [VIDEO ID]: Video unavailable. This video is not available
```

### Long playlists
When getting the data from a long playlist, _yt-dlp_ may not be able to access every video after a certain threshold due to rate-limiting. This tends to occur with playlists with more than 100 or 200 entries. To combat this, use the ``--sleep`` flag with a low value, like ``3`` seconds.
```
ERROR: [youtube] [VIDEO ID]: This content isn't available, try again later.
```

### Missing user authentication
When attempting to access age-restricted videos (**Error 1**), your own private playlist (**Error 2**), or other videos that are only available when authenticated (**Errors 3 and 4**), you may need to pass cookies to ``ytftpl.py`` in order to make it work. See [Usage](#usage) and the [yt-dlp](https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp) documentation for more information.
```
ERROR: [youtube] [VIDEO ID]: Sign in to confirm your age. This video may be inappropriate for some users. Use --cookies-from-browser or --cookies for the authentication. See  https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp  for how to manually pass cookies. Also see  https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies  for tips on effectively exporting YouTube cookies

ERROR: [youtube:tab] [PLAYLIST ID]: YouTube said: The playlist does not exist.

ERROR: [youtube] [VIDEO ID]: Join this channel to get access to members-only content like this video, and other exclusive perks.

ERROR: [youtube] [VIDEO ID]: Private video. Sign in if you've been granted access to this video. Use --cookies-from-browser or --cookies for the authentication. See  https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp  for how to manually pass cookies. Also see  https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies  for tips on effectively exporting YouTube cookies
```

I've found that when exporting a larger playlist (e.g. around 150 videos), age-restricted videos may give you **Error 1** despite passing cookies to _yt-dlp_ and being able to work through the rest of even a private playlist without problem. To solve this problem, I wrote the program so it would check when these age-restriction errors happen, save the affected video IDs in an array, and then open ``yt-dlp`` again for each of these IDs and get the data that way.

## Technical Details
_FreeTube_ uses a NPM module called [nedb](https://www.npmjs.com/package/@seald-io/nedb) to save data locally, including the user's playlists. They are stored in a file called ``playlists.db`` in a JSON-like format in one of the following locations, according to the [FreeTube documentation](https://docs.freetubeapp.io/usage/data-location/):
* Windows: ``%APPDATA%/FreeTube``
* Mac: ``~/Library/Application Support/FreeTube/``
* Linux: ``~/.config/FreeTube``
* Flatpak: ``~/.var/app/io.freetubeapp.FreeTube/config/FreeTube/``

**Note**: I say JSON-_like_ because the format is technically not valid according to the JSON standard. Playlists are stored in objects which are NOT comma separated. Here's an example featuring two playlist objects:

```
{
  "playlistName": "Watch Later",
  "protected": false,
  "description": "Videos to watch later",
  "videos": [
    
  ],
  "_id": "watchLater",
  "createdAt": 1741031171228,
  "lastUpdatedAt": 1741031171228
}
{
    "playlistName": "DNB",
    "protected": false,
    "description": "",
    "videos": [
        {
            "videoId": "CEJKG6fO6Ws",
            "title": "P.B.K. - Third Space Translocation (2008)",
            "author": "Ambiance",
            "authorId": "UCAw0NyC_6y-se4zcQGbEgHA",
            "lengthSeconds": 4091,
            "published": 1528270842,
            "timeAdded": 1741116781,
            "playlistItemId": "1dccfbda-d63e-4112-9b10-1681faa9b571",
            "type": "video"
        },
        {
            "videoId": "27nU1Ek4qfo",
            "title": "Roller Coaster III / Late Night Expressions (2002)",
            "author": "Ambiance",
            "authorId": "UCAw0NyC_6y-se4zcQGbEgHA",
            "lengthSeconds": 4501,
            "published": 1520991646,
            "timeAdded": 1741116781,
            "playlistItemId": "bdf3639f-4c44-42b5-9b12-2bd44c18ce42",
            "type": "video"
        },
    ],
    "_id": "ft-playlist--87c2c4c5-1c82-4508-9481-2ed6a0f56460",
    "createdAt": 1741116781,
    "lastUpdatedAt": 1741116781
}
```

The playlist fields ``createdAt`` and ``lastUpdatedAt`` as well as the video fields ``published`` and ``timeAdded`` are not represented as regular dates, but use the Unix time format. This format instead saves the time as an integer number of seconds that have passed since 00:00:00 UTC on 1 January 1970. (See: [FreeTube source code](https://github.com/FreeTubeApp/FreeTube/blob/f1030e984791d07c3e4a4c53991a195df53b6bee/src/renderer/store/modules/playlists.js#L92))

The video field ``playlistItemId`` is a randomly generated Version 4 UUID according to the [RFC 4122](https://datatracker.ietf.org/doc/html/rfc4122.html) standard. The same applies to the playlist field ``_id``, it just has the string ``"ft-playlist--"`` tacked onto the front. (See: [FT source code](https://github.com/FreeTubeApp/FreeTube/blob/f1030e984791d07c3e4a4c53991a195df53b6bee/src/renderer/store/modules/playlists.js#L4))

These values are generated in my Python code. A few are hardcoded to expected values (E.g. ``protected`` is set to ``false``), and all the other data is acquired using _yt-dlp_. This is the _yt-dlp_ command I've used in the script:
```
yt-dlp --quiet --no-warnings --skip-download --ignore-errors --print '%(.{playlist_title,id,title,channel,channel_id,duration,timestamp})#j' "[YOUR PLAYLIST URL]"
```

This outputs each video of the given playlist to the console in the following format:
```
{
    "playlist_title": "90s Hits Playlist | Best 90s Music Playlist",
    "id": "nZXRV4MezEw",
    "title": "Cher - Believe (Official Music Video) [4K Remaster]",
    "channel": "Cher",
    "channel_id": "UCmoUgBTHRydApyOeqlDF1oQ",
    "duration": 237,
    "timestamp": 1539968408
}
{
    "playlist_title": "90s Hits Playlist | Best 90s Music Playlist",
    "id": "uB1D9wWxd2w",
    "title": "Mark Morrison - Return of the Mack (Official Music Video)",
    "channel": "Mark Morrison",
    "channel_id": "UC9f-u24P4TP4bUcmSiA6JEw",
    "duration": 226,
    "timestamp": 1182641291
}
```

I wasn't able to output the name of the playlist separately, so unfortunately for now it is included in every video object.

This data is then processed to the correct format in Python, as seen at the top of this section. Here is a table of the fields, from _yt-dlp_ on the left to the corresponding values in _FreeTube's_ ``playists.db`` on the right:

| **yt-dlp**     | **FreeTube**  |
|----------------|---------------|
| playlist_title | playlistName  |
| id             | videoId       |
| title          | title         |
| channel        | author        |
| channel_id     | authorId      |
| duration       | lengthSeconds |
| timestamp      | published     |