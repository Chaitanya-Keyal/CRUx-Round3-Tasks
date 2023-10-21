import os

import httplib2
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_httplib2 import AuthorizedHttp
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build as api_build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = [
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/youtube.readonly",
]


def get_creds():
    """
    Authorises the app to access the user's YouTube account.

    Args:
        None
    Returns:
        google.oauth2.credentials.Credentials: YouTube API credentials
    """
    creds = None
    if os.path.exists("youtube/token.json"):
        creds = Credentials.from_authorized_user_file("youtube/token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())  # Refreshes the token if it is expired
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "youtube/credentials.json", SCOPES
            )  # Gets the user to login and authorise the app
            creds = flow.run_local_server(port=0)
        with open("youtube/token.json", "w") as token:
            token.write(creds.to_json())
    return creds


http = AuthorizedHttp(get_creds(), http=httplib2.Http(cache=".cache"))


def youtube_api_request(request, params):
    """
    Makes a request to the YouTube API.

    Args:
        request (googleapiclient.http.HttpRequest): YouTube API request
        params (dict): Parameters for the request
    Returns:
        dict: Response from the YouTube API
    """
    retry_count = 0
    try:
        return request(**params).execute(http=http)
    except HttpError as e:
        if e.error_details[0]["reason"] == "SERVICE_UNAVAILABLE":
            if retry_count < 3:
                retry_count += 1
                return youtube_api_request(request, params)
            else:
                return 503
        elif e.reason == "Channel not found.":
            print(
                "Channel not found. You need to create a channel on your account."
                + "\nTry creating a public playlist on your account and try again."
            )
        elif e.error_details[0]["reason"] == "quotaExceeded":
            print("YouTube API Quota exceeded. Try again tomorrow. :(")
            print(
                "You can also try creating a new project on the Google Cloud Console and using its credentials."
            )
            exit()
        elif e.error_details[0]["reason"] == "subscriptionDuplicate":
            print(e.reason)
        else:
            print(e)


def add_subscription(youtube, channel_name):
    """
    Adds a subscription to the user's YouTube account.

    Args:
        youtube (googleapiclient.discovery.Resource): YouTube API resource
        channel_name (str): Name of the channel to subscribe to
    Returns:
        None
    """
    print(f"\nSearching for {channel_name}...")
    search_response = youtube_api_request(
        youtube.search().list,
        {
            "part": "snippet",
            "q": channel_name,
            "type": "channel",
            "maxResults": 1,
        },
    )
    channel_id = search_response["items"][0]["snippet"]["channelId"]
    print(
        f"\nAdding subscription to {search_response['items'][0]['snippet']['title']}..."
    )
    youtube_api_request(
        youtube.subscriptions().insert,
        {
            "part": "snippet",
            "body": {
                "snippet": {
                    "resourceId": {
                        "kind": "youtube#channel",
                        "channelId": channel_id,
                    }
                }
            },
        },
    )


# region Playlist functions


def get_playlists(youtube):
    """
    Gets the user's playlists.

    Args:
        youtube (googleapiclient.discovery.Resource): YouTube API resource
    Returns:
        list: User's playlists
    """
    playlists_response = youtube_api_request(
        youtube.playlists().list,
        {
            "part": "snippet,status",
            "mine": True,
            "maxResults": 50,
        },
    )
    playlists = []
    for playlist in playlists_response["items"]:
        playlists.append(
            {
                "name": playlist["snippet"]["title"],
                "id": playlist["id"],
                "public": playlist["status"]["privacyStatus"] == "public",
            }
        )
    return playlists


def get_playlist_items(youtube, playlist_id, limit=10):
    """
    Gets the items in a playlist.

    Args:
        youtube (googleapiclient.discovery.Resource): YouTube API resource
        playlist_id (str): Playlist ID
        limit (int): Number of items to get
    Returns:
        list: Playlist items
    """
    playlist_items_response = youtube_api_request(
        youtube.playlistItems().list,
        {
            "part": "snippet,contentDetails",
            "playlistId": playlist_id,
            "maxResults": limit,
        },
    )
    videos = []

    def get_title_artist(s):
        title = (
            s.split(" - ")[1].split(" (")[0]
            if "(" in s
            else s.split(" - ")[1].split(" [")[0]
        )
        artist = s.split(" - ")[0]
        return title, artist

    for video in playlist_items_response["items"]:
        title, artist = get_title_artist(video["snippet"]["title"])
        videos.append(
            {
                "title": title,
                "artist": artist,
                "id": video["contentDetails"]["videoId"],
            }
        )
    while playlist_items_response.get("nextPageToken"):
        playlist_items_response = youtube_api_request(
            youtube.playlistItems().list,
            {
                "part": "snippet,contentDetails",
                "playlistId": playlist_id,
                "maxResults": 50,
                "pageToken": playlist_items_response["nextPageToken"],
            },
        )
        for video in playlist_items_response["items"]:
            title, artist = get_title_artist(video["snippet"]["title"])
            videos.append(
                {
                    "title": title,
                    "artist": artist,
                    "id": video["contentDetails"]["videoId"],
                }
            )
    return videos


def create_playlist(youtube, name, public=True):
    """
    Creates a new playlist or returns the id of existing playlist with same name

    Args:
        youtube (googleapiclient.discovery.Resource): YouTube API resource
        name (str): Name of the playlist
        public (bool): Whether the playlist is public
    Returns:
        str: Playlist ID
    """
    playlists = get_playlists(youtube)
    for playlist in playlists:
        if playlist["name"] == name:
            f = (
                input(
                    f"'{name}' Playlist already exists. Do you want to overwrite it? (y/n): "
                )
                .strip()
                .lower()
            )
            if f == "y":
                return playlist["id"]
            else:
                break

    playlist_response = youtube_api_request(
        youtube.playlists().insert,
        {
            "part": "snippet,status",
            "body": {
                "snippet": {
                    "title": name,
                },
                "status": {
                    "privacyStatus": "public" if public else "private",
                },
            },
        },
    )
    return playlist_response["id"]


def add_video_to_playlist(youtube, playlist_id, video_id):
    """
    Adds a video to a playlist.

    Args:
        youtube (googleapiclient.discovery.Resource): YouTube API resource
        playlist_id (str): Playlist ID
        video_id (str): Video ID
    Returns:
        response: Response from the YouTube API
    """

    # check if video is already in playlist
    playlist_items_response = youtube_api_request(
        youtube.playlistItems().list,
        {
            "part": "snippet",
            "playlistId": playlist_id,
            "maxResults": 50,
        },
    )
    for video in playlist_items_response["items"]:
        if video["snippet"]["resourceId"]["videoId"] == video_id:
            return

    r = youtube_api_request(
        youtube.playlistItems().insert,
        {
            "part": "snippet",
            "body": {
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": video_id,
                    },
                }
            },
        },
    )
    return r


# endregion


def get_video_id(youtube, name, artist):
    """
    Gets the ID of a video on YouTube.

    Args:
        youtube (googleapiclient.discovery.Resource): YouTube API resource
        name (str): Name of the song
        artist (str): Name of the artist
    Returns:
        str: Video ID
    """
    search_response = youtube_api_request(
        youtube.search().list,
        {
            "part": "snippet",
            "q": f"{name} {artist}",
            "type": "video",
            "maxResults": 1,
            "videoCategoryId": "10",
        },
    )
    return search_response["items"][0]["id"]["videoId"]


def like_video(youtube, video_id):
    """
    Likes a video on YouTube.

    Args:
        youtube (googleapiclient.discovery.Resource): YouTube API resource
        video_id (str): Video ID
    Returns:
        None
    """
    youtube_api_request(
        youtube.videos().rate,
        {
            "id": video_id,
            "rating": "like",
        },
    )
