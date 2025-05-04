import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from collections import defaultdict
import re

# ----------- Set your Spotify API credentials here -------------
CLIENT_ID = 'CLIENT_ID'
CLIENT_SECRET = 'CLIENT_SECRET'

# Initialize Spotify client
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=CLIENT_ID,
                                                           client_secret=CLIENT_SECRET))

import time
import requests
from spotipy.exceptions import SpotifyException

def retry_spotify_request(func, max_retries=5, initial_delay=1, backoff_factor=2, *args, **kwargs):
    delay = initial_delay
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError, SpotifyException) as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(delay)
                delay *= backoff_factor
            else:
                print("Max retries reached. Giving up.")
                raise


def get_playlist_id_from_url(url):
    match = re.search(r'playlist/([a-zA-Z0-9]+)', url)
    return match.group(1) if match else None

def get_original_album(track_id):
    track = retry_spotify_request(sp.track, track_id=track_id)
    original_name = track['name'].lower()
    album_type = track['album']['album_type']

    album_name = track['album']['name'].lower()

    # If it's a normal album and not likely a compilation (e.g. no "hits"/"collection" in name)
    if album_type == 'album' and not any(word in album_name for word in ['hits', 'collection', 'essential']):
        return track['album']['id']

    # Search for original version
    query = f"track:{track['name']} artist:{track['artists'][0]['name']}"
    results = retry_spotify_request(sp.search, q=query, type='track', limit=10)

    for item in results['tracks']['items']:
        candidate_name = item['name'].lower()

        # Ensure it's a normal album and track names match closely
        if item['album']['album_type'] == 'album' and candidate_name in original_name:
            return item['album']['id']

    # Fallback to current album if no suitable match
    return track['album']['id']



def analyze_playlist_albums(playlist_id):
    offset = 0
    albums_count = defaultdict(int)
    album_info = {}

    while True:
        response = sp.playlist_items(playlist_id, offset=offset, fields="items.track.id,total,next", additional_types=['track'])
        items = response['items']

        if not items:
            break

        for item in items:
            track = item['track']
            if not track:
                continue

            album_id = get_original_album(track['id'])
            albums_count[album_id] += 1

        if response['next'] is None:
            break
        offset += len(items)

    # Sort albums by frequency
    sorted_albums = sorted(albums_count.items(), key=lambda x: x[1], reverse=True)

    print("\nAlbum Frequencies:")
    for album_id, count in sorted_albums:
        album = retry_spotify_request(sp.album, album_id=album_id)
        name = album['name']
        artist = album['artists'][0]['name']
        print(f"{name} by {artist}: {count} track(s)")

# ---------------- Main Program -------------------
def main():
    url = input("Enter Spotify Playlist URL: ").strip()
    playlist_id = get_playlist_id_from_url(url)

    if not playlist_id:
        print("Invalid Spotify playlist URL.")
        return

    print("\nChoose an option:")
    print("1. Count tracks by original album")
    choice = input("Enter option number: ").strip()

    if choice == '1':
        analyze_playlist_albums(playlist_id)
    else:
        print("Invalid option. Exiting.")

if __name__ == "__main__":
    main()
