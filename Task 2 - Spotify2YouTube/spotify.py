import json
import os
import threading
import webbrowser

import requests
from auth import APP_URL, BASE_API_URL, SERVER_PORT, app, get_access_token


def pretty_print(json_object):
    print(json.dumps(json_object, indent=4))


def get_user_details(access_token):
    """
    Get user details from Spotify.

    Args:
        access_token (str): Access token
    Returns:
        user (dict): User details
    """
    r = requests.get(
        f"{BASE_API_URL}/v1/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    if r.status_code != 200:
        raise Exception(f"Status code: {r.status_code} {r.text}")
    user = r.json()
    return user


def authorise():
    """
    Gets the user to authorize this app.
    """
    webbrowser.open(f"{APP_URL}:{SERVER_PORT}/auth")
    print(
        f"Click the following link to authorize this app:\n{APP_URL}:{SERVER_PORT}/auth"
    )

    thread = threading.Thread(
        target=app.run,
        kwargs={"host": APP_URL.removeprefix("http://"), "port": SERVER_PORT},
        daemon=True,
    )
    thread.start()

    # Waiting for user to authorize app
    while not os.path.exists("spotify/token.json"):
        pass


def main():
    if not os.path.exists("spotify/token.json"):
        authorise()

    user = get_user_details(get_access_token())
    print(f"Welcome, {user['display_name']}!")
    pretty_print(user)


if __name__ == "__main__":
    main()
