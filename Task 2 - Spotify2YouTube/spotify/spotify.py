import json
import os
import sys
import threading
import webbrowser

import requests
from auth import (
    APP_URL,
    BASE_API_URL,
    SERVER_PORT,
    get_access_token,
    start_auth_listener,
)

sys.path.append(os.curdir)
from util.fuzzy_playlist import search_playlist


def pretty_print(json_object):
    print(json.dumps(json_object, indent=4))


def spotify_api_request(url, access_token, params=None):
    """
    Make an API request to Spotify.

    Args:
        url (str): URL to make request to
        access_token (str): Access token
        params (dict): Parameters
    Returns:
        json (dict): JSON response
    """
    r = requests.get(
        url,
        headers={"Authorization": f"Bearer {access_token}"},
        params=params,
    )
    if r.status_code != 200:
        raise Exception(f"Status code: {r.status_code} {r.text}")
    return r.json()


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


def main():
    if not os.path.exists("spotify/token.json"):
        authorise()

    user = get_user_details(get_access_token())
    print(f"Welcome, {user['display_name']}!")

    # tracks = get_top(get_access_token(), "tracks", 15, "medium_term")
    # print("\nYour top tracks are:")
    # for track in tracks:
    #     print(f"{track['name']} by {track['artists'][0]['name']}")

    # artists = get_top(get_access_token(), "artists", 15, "long_term")
    # print("\nYour top artists are:")
    # for artist in artists:
    #     print(f"{artist['name']}")

    searched_playlist = search_playlist(get_playlists(get_access_token()))
    if searched_playlist:
        print(f"\nYou chose: {searched_playlist['name']}")

    # searched_song = search_song(get_access_token())
    # if searched_song:
    #     print(
    #         f"\nYou chose {searched_song['name']} by {searched_song['artists'][0]['name']}"
    #     )


if __name__ == "__main__":
    main()
