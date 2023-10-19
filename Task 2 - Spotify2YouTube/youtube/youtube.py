import json
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build as api_build
from googleapiclient.errors import HttpError

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


# f = open("youtube/api_key.json", "r")
# api_key = json.loads(f.read())["api_key"]
# f.close()


def add_subscription(youtube, channel_name):
    """
    Adds a subscription to the user's YouTube account.

    Args:
        youtube (googleapiclient.discovery.Resource): YouTube API resource
        channel_id (str): Channel ID
    Returns:
        None
    """
    print(f"Searching for {channel_name}...")
    request = youtube.search().list(
        part="snippet",
        maxResults=1,
        q=channel_name,
        type="channel",
    )
    response = request.execute()
    channel_id = response["items"][0]["snippet"]["channelId"]
    print(f"Found {channel_name}! Adding subscription...")
    request = youtube.subscriptions().insert(
        part="snippet",
        body={
            "snippet": {
                "resourceId": {
                    "kind": "youtube#channel",
                    "channelId": channel_id,
                }
            }
        },
    )
    try:
        response = request.execute()
        print(f"Successfully added {channel_name}!")
    except HttpError as e:
        print(e.reason)


def main(creds):
    youtube = api_build("youtube", "v3", credentials=creds)

    list_of_artists = ["Ed Sheeran"]
    for artist in list_of_artists:
        add_subscription(youtube, artist)


if __name__ == "__main__":
    creds = auth()
    main(creds=creds)
