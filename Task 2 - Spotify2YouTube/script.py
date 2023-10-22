import os

import spotify.spotify as spotify
import youtube.youtube as youtube
from util.fuzzy_playlist import search_playlist

YOUTUBE = youtube.api_build("youtube", "v3", credentials=youtube.get_creds())


def top_artists():
    """
    Gets the user's top 10 artists from Spotify and subscribes to their YouTube channels.
    """
    print("Getting top artists from Spotify...")
    top_artists = spotify.get_top(
        spotify.get_access_token(), "artists", 10, "long_term"
    )
    print("Subscribing to artists' YouTube channels...")
    for artist in top_artists:
        youtube.add_subscription(YOUTUBE, artist["name"])
    print("Done!")


def convert_spotify_yt():
    """
    Converts the user's Spotify playlists to YouTube playlists.
    """
    searched_playlist = search_playlist(
        spotify.get_playlists(spotify.get_access_token())
    )
    if searched_playlist:
        print(f"\nYou chose: {searched_playlist['name']}")
        print("\nGetting Spotify playlist items...")
        playlist_items = spotify.get_playlist_items(
            spotify.get_access_token(), searched_playlist["id"], 10
        )
        print("\nCreating YouTube playlist...")
        youtube_playlist_id = youtube.create_playlist(
            YOUTUBE, searched_playlist["name"], searched_playlist["public"]
        )
        print("\nAdding songs to YouTube playlist...")
        for item in playlist_items:
            video_id = youtube.get_video_id(YOUTUBE, item["title"], item["artist"])
            r = youtube.add_video_to_playlist(YOUTUBE, youtube_playlist_id, video_id)
            if r == 409:
                print(f"Error adding {item['title']}")
            else:
                print(f"Added {item['title']}")
        print("\nDone!")
    else:
        print("\nNo playlist selected")


def convert_yt_spotify():
    """
    Converts the user's YouTube playlists to Spotify playlists.
    """
    searched_playlist = search_playlist(youtube.get_playlists(YOUTUBE))
    if searched_playlist:
        print(f"\nYou chose: {searched_playlist['name']}")
        print("\nGetting YouTube playlist items...")
        playlist_items = youtube.get_playlist_items(YOUTUBE, searched_playlist["id"])
        print("\nCreating Spotify playlist...")
        spotify_playlist_id = spotify.create_playlist(
            spotify.get_access_token(),
            spotify.get_user_details(spotify.get_access_token())["id"],
            searched_playlist["name"],
            searched_playlist["public"],
        )
        print("\nAdding songs to Spotify playlist...")
        uris = []
        for item in playlist_items:
            uris.append(
                spotify.get_song_uri(
                    spotify.get_access_token(), item["title"], item["artist"]
                )
            )
        if None in uris:
            uris.remove(None)
        spotify.add_to_playlist(spotify.get_access_token(), spotify_playlist_id, uris)
        print("\nDone!")
    else:
        print("\nNo playlist selected")


def top_tracks():
    """
    Gets the user's top 10 tracks from Spotify and adds them to a YouTube playlist.
    """
    print("Getting top tracks from Spotify...")
    top_tracks = spotify.get_top(spotify.get_access_token(), "tracks", 10, "long_term")
    print("Creating YouTube playlist...")
    youtube_playlist_id = youtube.create_playlist(
        YOUTUBE,
        "Top Tracks",
        True,
    )
    print("Adding songs to YouTube playlist...")
    for track in top_tracks:
        video_id = youtube.get_video_id(
            YOUTUBE, track["name"], track["artists"][0]["name"]
        )
        r = youtube.add_video_to_playlist(YOUTUBE, youtube_playlist_id, video_id)
        if r == 409:
            print(f"Error adding {track['name']}")
        else:
            print(f"Added {track['name']}")
    print("Done!")


def like_saved_songs():
    """
    Gets the user's saved songs from Spotify and likes them on YouTube.
    """
    saved_songs = spotify.get_new_liked_songs(spotify.get_access_token())
    print("Liking songs on YouTube...")
    for song in saved_songs:
        youtube.like_video(YOUTUBE, youtube.get_video_id(YOUTUBE, song[0], song[1]))
        print(f"Liked {song[0]}")
    print("Done!")


def main():
    """
    CLI for Spotify2YouTube.
    """
    while True:
        print(
            """Menu:
1. Subscribe to top 10 artists
2. Create Top Tracks playlist on YouTube
3. Convert Playlists
4. Like Spotify saved songs on YouTube
5. Exit
"""
        )
        choice = input("Enter choice: ")
        if choice == "1":
            top_artists()
        elif choice == "2":
            top_tracks()
        elif choice == "3":
            while True:
                print(
                    """Convert Playlists:
    1. Spotify to YouTube
    2. YouTube to Spotify
    3. Back to main menu
    """
                )
                choice = input("Enter choice: ")
                if choice == "1":
                    convert_spotify_yt()
                elif choice == "2":
                    convert_yt_spotify()
                elif choice == "3":
                    break
                else:
                    print("\nInvalid choice")
                print()
        elif choice == "4":
            like_saved_songs()
        elif choice == "5":
            break
        else:
            print("\nInvalid choice")
        print()


if __name__ == "__main__":
    if not os.path.exists("spotify/token.json"):
        spotify.authorise()
        print()
    main()
