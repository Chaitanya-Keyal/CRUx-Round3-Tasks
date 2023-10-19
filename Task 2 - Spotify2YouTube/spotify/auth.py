import json
import logging
import secrets
import threading

import requests
from flask import Flask, cli, redirect, request

app = Flask(__name__)

# Disable Flask banner and Werkzeug logger
cli.show_server_banner = lambda *args: None
log = logging.getLogger("werkzeug")
log.setLevel(logging.ERROR)


# Spotify app credentials
f = open("spotify/credentials.json", "r")
spotify_credentials = json.load(f)
client_id = spotify_credentials["client_id"]
client_secret = spotify_credentials["client_secret"]
redirect_uri = spotify_credentials["redirect_uri"]
scope = spotify_credentials["scope"].replace(" ", "%20")
f.close()

BASE_API_URL = "https://api.spotify.com"
APP_URL, SERVER_PORT = "http://localhost", 8888

state = secrets.token_hex(16)

auth_event = None


@app.route("/auth", methods=["GET"])
def get_auth_code():
    """
    Redirect user to Spotify login page.

    Args:
        None
    Returns:
        auth_code (str): Authorization code
    """
    return redirect(
        "https://accounts.spotify.com/authorize?"
        + f"client_id={client_id}"
        + "&response_type=code"
        + f"&redirect_uri={redirect_uri}"
        + f"&scope={scope}"
        + f"&state={state}"
    )


@app.route("/callback", methods=["GET"])
def callback():
    """
    Stores token in JSON file.
    """
    recv_state = request.args.get("state")
    if not recv_state:
        raise Exception("No state received.")
    else:
        if recv_state != state:
            raise Exception("State mismatch.")
    try:
        auth_code = request.args.get("code")
        r = requests.post(
            "https://accounts.spotify.com/api/token",
            data={
                "grant_type": "authorization_code",
                "code": auth_code,
                "redirect_uri": redirect_uri,
                "client_id": client_id,
                "client_secret": client_secret,
            },
        )
        if r.status_code != 200:
            raise Exception(f"Status code: {r.status_code}, {r.text}")
        token = r.json()
        with open("spotify/token.json", "w") as f:
            json.dump(token, f)
        auth_event.set()
        return "Authorisation Successful. You can close this tab and return to the application."
    except ValueError:
        error = request.args.get("error")
        raise Exception(f"Error: {error}")


def start_auth_listener(event: threading.Event):
    """
    Starts Flask server to listen for auth code.
    """
    global auth_event
    auth_event = event
    app.run(host=APP_URL.removeprefix("http://"), port=SERVER_PORT)


def get_access_token():
    """
    Gets access token from JSON file.
    If access token is invalid or expired, refreshes access token.

    Args:
        None
    Returns:
        access_token (str): Access token
    """
    token = {}
    with open("spotify/token.json", "r+") as f:
        token = json.load(f)
        r = requests.get(
            f"{BASE_API_URL}/v1/me",
            headers={"Authorization": f"Bearer {token['access_token']}"},
        )
        if r.status_code != 200:
            r = requests.post(
                "https://accounts.spotify.com/api/token",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": token["refresh_token"],
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
            )
            if r.status_code != 200:
                raise Exception(f"Status code: {r.status_code} {r.text}")
            token.update(r.json())
            f.seek(0)
            f.truncate()
            json.dump(token, f)
    return token["access_token"]


if __name__ == "__main__":
    app.run(host=APP_URL.removeprefix("http://"), port=SERVER_PORT)
