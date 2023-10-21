import datetime
import json
import os
import threading
import webbrowser

import requests
from spotify.auth import (
    APP_URL,
    BASE_API_URL,
    SERVER_PORT,
    get_access_token,
    start_auth_listener,
)

# region Utility functions


def pretty_print(json_object):
    print(json.dumps(json_object, indent=4))


def spotify_api_request(url, access_token, params=None, method="GET", data=None):
    """
    Make an API request to Spotify.

    Args:
        url (str): URL to make request to
        access_token (str): Access token
        params (dict): Parameters
    Returns:
        json (dict): JSON response
    """
    methods = {
        "GET": requests.get,
        "POST": requests.post,
        "PUT": requests.put,
        "DELETE": requests.delete,
    }
    r = methods[method](
        url,
        headers={"Authorization": f"Bearer {access_token}"},
        params=params,
        data=data,
    )
    if r.status_code not in [200, 201]:
        raise Exception(f"Status code: {r.status_code} {r.text}")
    return r.json()


# endregion


def get_user_details(access_token):
    """
    Get user details from Spotify.

    Args:
        access_token (str): Access token
    Returns:
        user (dict): User details
    """
    user = spotify_api_request(BASE_API_URL + "/v1/me", access_token)
    return user


def get_top(access_token, top_type, num=10, time_range="long_term"):
    """
    Get the user's top artists or tracks from Spotify.

    Args:
        access_token (str): Access token
        top_type (str): "artists" or "tracks"
        num (int): Number of artists or tracks to get
        time_range (str): Time range to calculate top artists or tracks for
            - long_term (several years of data)
            - medium_term (approximately last 6 months)
            - short_term (approximately last 4 weeks)
    Returns:
        items (list): List of top artists or tracks
    """
    r = spotify_api_request(
        BASE_API_URL + "/v1/me/top/" + top_type,
        access_token,
        params={"limit": num, "time_range": time_range},
    )
    items = r["items"]
    while len(items) < num:
        r = spotify_api_request(
            r["next"],
            access_token,
            params={"limit": num - len(items), "time_range": time_range},
        )
        items.extend(r["items"])
    return items


# region Playlist functions


def get_playlists(access_token):
    """
    Get the user's playlists from Spotify.

    Args:
        access_token (str): Access token
    Returns:
        playlists (list): List of playlists
    """
    r = spotify_api_request(BASE_API_URL + "/v1/me/playlists", access_token)
    playlists = r["items"]
    while r["next"]:
        r = spotify_api_request(r["next"], access_token)
        playlists.extend(r["items"])

    return playlists


def get_playlist_items(access_token, playlist_id, limit=10):
    """
    Get the items in a playlist from Spotify.

    Args:
        access_token (str): Access token
        playlist_id (str): Playlist ID
        limit (int): Number of items to get
    Returns:
        items (list): List of playlist items
    """
    r = spotify_api_request(
        BASE_API_URL + f"/v1/playlists/{playlist_id}/tracks",
        access_token,
        params={"limit": limit},
    )
    items = r["items"]
    if not r["next"]:
        return items
    while len(items) < limit:
        r = spotify_api_request(
            r["next"],
            access_token,
            params={"limit": limit - len(items)},
        )
        items.extend(r["items"])
    return items


def create_playlist(access_token, user_id, name, public=True):
    """
    Create a playlist on Spotify or overwrite an existing one.

    Args:
        access_token (str): Access token
        user_id (str): User ID
        name (str): Playlist name
        public (bool): Whether the playlist is public
    Returns:
        playlist_id (str): Playlist ID
    """
    # check if playlist already exists
    playlists = get_playlists(access_token)
    for playlist in playlists:
        if playlist["name"] == name:
            f = (
                input(
                    f"'{name}' Playlist already exists. Do you want to overwrite it? (y/n): "
                )
                .lower()
                .strip()
            )
            if f == "y":
                return playlist["id"]
    playlist = spotify_api_request(
        BASE_API_URL + f"/v1/users/{user_id}/playlists",
        access_token,
        method="POST",
        data=json.dumps(
            {
                "name": name,
                "public": public,
            }
        ),
    )
    return playlist["id"]


def add_to_playlist(access_token, playlist_id, uris):
    """
    Add tracks to a playlist on Spotify.

    Args:
        access_token (str): Access token
        playlist_id (str): Playlist ID
        uris (list): List of track URIs
    Returns:
        None
    """
    # check if song already exists in playlist
    playlist_items = get_playlist_items(access_token, playlist_id)
    for item in playlist_items:
        if item["track"]["uri"] in uris:
            uris.remove(item["track"]["uri"])
    if not uris:
        print("No new songs to add")
        return

    spotify_api_request(
        BASE_API_URL + f"/v1/playlists/{playlist_id}/tracks",
        access_token,
        method="POST",
        data=json.dumps(
            {
                "uris": uris,
            }
        ),
    )


# endregion


def get_new_liked_songs(access_token):
    """
    Get the user's new liked songs from Spotify.
    Last checked is stored in liked_times.json
    For new users, last checked is 7 days ago

    Args:
        access_token (str): Access token
    Returns:
        songs (list): List of songs [(name, artist)]
    """
    print("\nGetting new liked songs...")
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    if os.path.exists("spotify/liked_timestamps.json"):
        with open("spotify/liked_timestamps.json", "r") as f:
            last_checked = json.load(f)[get_user_details(access_token)["id"]]
    else:
        with open("spotify/liked_timestamps.json", "w") as f:
            json.dump({}, f)
        last_checked = (now - datetime.timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")

    r = spotify_api_request(
        BASE_API_URL + "/v1/me/tracks",
        access_token,
    )
    songs = []
    for item in r["items"]:
        if item["added_at"] > last_checked:
            songs.append((item["track"]["name"], item["track"]["artists"][0]["name"]))
    if r["next"]:
        while r["next"]:
            r = spotify_api_request(r["next"], access_token)
            for item in r["items"]:
                if item["added_at"] > last_checked:
                    songs.append(
                        (item["track"]["name"], item["track"]["artists"][0]["name"])
                    )
    with open("spotify/liked_timestamps.json", "r+") as f:
        d = json.load(f)
        d[get_user_details(access_token)["id"]] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        f.seek(0)
        f.truncate()
        json.dump(d, f)
    return songs


def get_song_uri(access_token, name, artist):
    """
    Get the URI of a song on Spotify.

    Args:
        access_token (str): Access token
        name (str): Song name
        artist (str): Artist name
    Returns:
        uri (str): Song URI
    """
    r = spotify_api_request(
        BASE_API_URL + "/v1/search",
        access_token,
        params={
            "q": f"track:{name} artist:{artist}",
            "type": "track",
            "limit": 1,
        },
    )
    try:
        return r["tracks"]["items"][0]["uri"]
    except IndexError:
        print(f"Song not found: {name} by {artist}")
        return None


def search_song(access_token):
    """
    Search for a song on spotify

    Args:
        access_token (str): Access token
    Returns:
        song (dict): Song details
    """

    def request_songs(search_query):
        """
        Get songs from Spotify.
        """
        r = spotify_api_request(
            BASE_API_URL + "/v1/search",
            access_token,
            params={
                "q": search_query,
                "type": "track",
                "limit": 10,
            },
        )
        return r["tracks"]["items"]

    songs = request_songs(input("\nSearch for a song: "))
    while True:
        if not songs:
            print("No results found")
            songs = request_songs(input("\nSearch again: "))
            continue
        print("\nSearch results:")
        c = 1
        for song in songs:
            print(f"{c}. {song['name']} by {song['artists'][0]['name']}")
            c += 1
        print(f"\n{c}. Search again")
        print(f"{c + 1}. Exit")

        choice = input("\nChoose a song: ")
        if choice == str(c + 1):
            return None
        elif choice == str(c):
            songs = request_songs(input("\nSearch for a song: "))
        elif "1" <= choice <= str(c - 1):
            return songs[int(choice) - 1]
        else:
            print("\nInvalid choice")


def get_song_details(access_token, song_id):
    """
    Get the details of a song on Spotify.

    Args:
        access_token (str): Access token
        song_id (str): Song ID
    Returns:
        song (dict): Song details
    """
    song = spotify_api_request(
        BASE_API_URL + f"/v1/tracks/{song_id}",
        access_token,
    )
    return song


def authorise():
    """
    Gets the user to authorize this app.
    """
    webbrowser.open(f"{APP_URL}:{SERVER_PORT}/auth")
    print(
        f"Click the following link to authorize this app:\n{APP_URL}:{SERVER_PORT}/auth"
    )
    event = threading.Event()
    thread = threading.Thread(target=start_auth_listener, args=(event,), daemon=True)
    thread.start()
    event.wait(timeout=120)
    if not event.is_set():
        raise Exception("Authorisation timed out.")
