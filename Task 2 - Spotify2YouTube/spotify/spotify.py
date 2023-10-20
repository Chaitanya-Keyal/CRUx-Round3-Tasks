import json
import os
import threading
import webbrowser

import rapidfuzz
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


def search_playlist(access_token):
    """
    Search the user's playlists for a playlist using fuzzy matching.

    Args:
        access_token (str): Access token
    Returns:
        playlist (dict): Playlist details
    """

    playlists_response = get_playlists(access_token)

    playlists_names = [playlist["name"] for playlist in playlists_response]

    playlists_names_lower = [name.lower() for name in playlists_names]

    def fuzzy_matched_playlists(search_query):
        """
        Get matched playlists using fuzzy matching.

        Args:
            search_query (str): Search query
        Returns:
            matched_playlists (list): List of matched playlists [(playlist name, score, index)]
        """
        matched_playlists = rapidfuzz.process.extract(
            search_query.lower(),
            playlists_names_lower,
            scorer=rapidfuzz.fuzz.WRatio,
            limit=10,
            score_cutoff=50,
        )

        return [
            (playlists_names[index], str(round(score, 2)) + "%", index)
            for playlist, score, index in matched_playlists
        ]

    matched_playlists = fuzzy_matched_playlists(input("\nSearch for a playlist: "))
    while True:
        if not matched_playlists:
            print("No results found")
            matched_playlists = fuzzy_matched_playlists(input("\nSearch again: "))
            continue
        print("\nSearch results:")
        c = 1
        for playlist, score, id in matched_playlists:
            print(f"{c}. {playlist} ({score})")
            c += 1
        print(f"{c}. Search again")
        print(f"{c + 1}. Exit")

        choice = input("\nChoose a playlist: ")
        if choice == str(c + 1):
            return None
        elif choice == str(c):
            matched_playlists = fuzzy_matched_playlists(
                input("\nSearch for a playlist: ")
            )
        elif "1" <= choice <= str(c - 1):
            return playlists_response[matched_playlists[int(choice) - 1][2]]
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

    searched_playlist = search_playlist(get_access_token())
    if searched_playlist:
        print(f"\nYou chose: {searched_playlist['name']}")


if __name__ == "__main__":
    main()
