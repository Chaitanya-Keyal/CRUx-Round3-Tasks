import json
import os
import sys

import httplib2
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_httplib2 import AuthorizedHttp
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build as api_build
from googleapiclient.errors import HttpError

sys.path.append(os.curdir)
from util.fuzzy_playlist import search_playlist

# If modifying these scopes, delete the file token.json.
SCOPES = [
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube.download",
]


def auth():
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


http = AuthorizedHttp(auth(), http=httplib2.Http(cache=".cache"))


def youtube_api_request(request, params):
    """
    Makes a request to the YouTube API.

    Args:
        request (googleapiclient.http.HttpRequest): YouTube API request
        params (dict): Parameters for the request
    Returns:
        dict: Response from the YouTube API
    """
    try:
        return request(**params).execute(http=http)
    except HttpError as e:
        if e.reason == "Channel not found.":
            print(
                "Channel not found. You need to create a channel on your account."
                + "\nTry creating a public playlist on your account and try again."
            )
        else:
            print(e.reason)


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
            "part": "snippet",
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
    for video in playlist_items_response["items"]:
        videos.append(
            {
                "title": video["snippet"]["title"],
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
            videos.append(
                {
                    "title": video["snippet"]["title"],
                    "id": video["contentDetails"]["videoId"],
                }
            )
    return videos


def main(creds):
    youtube = api_build("youtube", "v3", credentials=creds)

    playlists = get_playlists(youtube)
    search_response = search_playlist(playlists)
    if search_response:
        videos = get_playlist_items(youtube, search_response["id"])
        print(videos)


if __name__ == "__main__":
    creds = auth()
    main(creds=creds)
