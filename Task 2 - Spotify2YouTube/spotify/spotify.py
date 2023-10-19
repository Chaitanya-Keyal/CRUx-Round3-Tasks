import json
import os
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


def get_top_artists(access_token, num_artists=10, time_range="long_term"):
    """
    Get the user's top artists from Spotify.

    Args:
        access_token (str): Access token
        num_artists (int): Number of artists to return
        time_range (str): Time range of top artists
            - long_term (several years of data)
            - medium_term (approximately last 6 months)
            - short_term (approximately last 4 weeks)
    Returns:
        artists (list): List of artists
    """
    r = spotify_api_request(
        BASE_API_URL + "/v1/me/top/artists",
        access_token,
        params={"limit": num_artists, "time_range": time_range},
    )
    artists = r["items"]
    while len(artists) < num_artists:
        r = spotify_api_request(
            r["next"],
            access_token,
            params={"limit": num_artists - len(artists), "time_range": time_range},
        )
        artists.extend(r["items"])
    return artists


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
    artists = get_top_artists(get_access_token(), 15, "long_term")
    print("Your top artists are:")
    for artist in artists:
        print(
            f"{artist['name']}"
            + (f" ({artist['genres'][0]})" if artist["genres"] else "")
        )


if __name__ == "__main__":
    main()
