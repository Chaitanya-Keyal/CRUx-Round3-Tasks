import rapidfuzz


def search_playlist(playlists_response):
    """
    Search the user's playlists for a playlist using fuzzy matching.

    Args:
        playlists (list): List of playlists
    Returns:
        playlist (dict): Playlist details
    """
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
        print(f"\n{c}. Search again")
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
