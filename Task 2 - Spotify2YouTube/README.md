# Spotify2Youtube

A CLI program to transfer your Spotify library to YouTube.

### Features:
- Subscribes to user's top artists on YouTube.
- Creates a playlist for the user's top tracks.
- Convert a Spotify playlist to a YouTube playlist and vice versa.
- Likes the music video of a song on YouTube if it is liked on Spotify.

### Usage:
- `cd` into the directory containing `script.py`
- Install the required packages using `pip install -r requirements.txt`
- Both Spotify and YouTube developer keys are required to use this script.
- For Spotify:
    - Create an app on the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard).
    - Tick the checkbox for "Web API" in the app settings.
    - Add `http://localhost:8888/callback` as a redirect URI in the app settings.
    - Copy the client ID and client secret from the app settings.
    - Create the file `spotify/credentials.json` with the following contents:
        ```json
        {
            "client_id": "<your_client_id>",
            "client_secret": "<your_client_secret>",
            "redirect_uri": "http://localhost:8888/callback",
            "scope": "playlist-read-private playlist-read-collaborative playlist-modify-public playlist-modify-private user-top-read user-read-private user-read-email user-library-read"
        }
        ```
- For YouTube:
    - Create or select a project in the [Google Cloud Console](https://console.cloud.google.com/).
    - In the [library panel](https://console.cloud.google.com/apis/library), enable the YouTube Data API v3. Click into the listing for that API and make sure the API is enabled for your project.
    - Set up the [OAuth consent screen](https://console.cloud.google.com/apis/credentials/consent), and add your email address as a test user.
    - In the [credentials panel](https://console.cloud.google.com/apis/credentials), create an OAuth client ID.
    - Select "Desktop app" as the type of application.
    - Download the JSON file that contains your OAuth 2.0 credentials to the current directory.
    - Rename the file to `youtube/credentials.json`.
- Run `script.py`. It will prompt you to authorize the script to access your Spotify and YouTube accounts.
- Follow further instructions in the terminal.

### Notes:
- The YouTube API has a quota limit of only 10,000 units per day per project, the script uses these as follows:
    | Function | Units |
    | --- | --- |
    | Search | 100 |
    | Artist subscription | 50 |
    | Video like | 50 |
    | Playlist creation | 50 |
    | Playlist item addition | 50 |
    | Playlists list | 1 |
    | Playlist items list | 1 |

    - Currently the script supports only a few songs per fetch, hoping to not hit the quota limit.
    - To try reduce the number of API calls, the script caches the results of API Calls using `httplib2`'s caching feature.
    - The quota resets at midnight PST (12:30 PM IST).
    - If the quota limit is reached, a workaround is to create a new project on the [Google Cloud Console](https://console.cloud.google.com/) and obtain new credentials. Replace the `youtube/credentials.json` file with the new one and run the script again.
- The script checks for newly liked songs on Spotify based on the "last checked" timestamp (stored locally for each user). For a new user, the songs liked in the last week are added to the YouTube liked videos playlist. (Limited to 10 songs)