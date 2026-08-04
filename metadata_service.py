import os
import re
import json
import base64
import urllib.parse
import urllib.request
import hashlib
import requests
from typing import Dict, List, Any, Optional, Tuple

USER_AGENT = "AudioExtractorCD_AOLabs/1.0 ( https://ko-fi.com/aolabs )"

class MetadataService:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    def calculate_disc_id(self, toc_tracks: List[Dict[str, int]], leadout_sector: int) -> Tuple[str, str]:
        """
        Calculates MusicBrainz Disc ID and FreeDB Disc ID from track TOC offsets.
        """
        if not toc_tracks:
            return "", ""
        
        first_track = toc_tracks[0]['track']
        last_track = toc_tracks[-1]['track']
        track_count = len(toc_tracks)

        offsets_str = f"{first_track:02X}{last_track:02X}{leadout_sector + 150:08X}"
        for t in toc_tracks:
            offsets_str += f"{t['start_sector'] + 150:08X}"
        
        sha = hashlib.sha1(offsets_str.encode('ascii')).digest()
        mb_disc_id = base64.b64encode(sha).decode('ascii')
        mb_disc_id = mb_disc_id.replace('+', '.').replace('/', '_').replace('=', '-')

        def cdbid_sum(n):
            ret = 0
            while n > 0:
                ret += (n % 10)
                n //= 10
            return ret

        checksum = 0
        for t in toc_tracks:
            checksum += cdbid_sum((t['start_sector'] + 150) // 75)
        
        total_time = ((leadout_sector + 150) // 75) - ((toc_tracks[0]['start_sector'] + 150) // 75)
        freedb_id = f"{((checksum % 0xff) << 24 | total_time << 8 | track_count):08x}"

        return mb_disc_id, freedb_id

    def get_metadata_from_musicbrainz(self, disc_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetches release details from MusicBrainz API by Disc ID.
        """
        if not disc_id:
            return None
        
        url = f"https://musicbrainz.org/ws/2/discid/{disc_id}?inc=recordings+artist-credits+releases+genres+media&fmt=json"
        try:
            resp = self.session.get(url, timeout=4)
            if resp.status_code == 200:
                data = resp.json()
                releases = data.get("releases", [])
                if releases:
                    rel = releases[0]
                    release_id = rel.get("id", "")
                    title = rel.get("title", "Álbum Desconocido")
                    
                    artist_credits = rel.get("artist-credit", [])
                    artist = "Artista Desconocido"
                    if artist_credits:
                        artist = "".join([a.get("name", "") + a.get("joinphrase", "") for a in artist_credits])
                    
                    date_str = rel.get("date", "")
                    year = date_str[:4] if date_str else ""
                    
                    genres = [g.get("name") for g in rel.get("genres", []) if g.get("name")]
                    genre = ", ".join(genres) if genres else "CD Audio"

                    tracks = []
                    media_list = rel.get("media", [])
                    for media in media_list:
                        for tr in media.get("tracks", []):
                            track_num = tr.get("position", len(tracks) + 1)
                            rec = tr.get("recording", {})
                            track_title = tr.get("title") or rec.get("title") or f"Pista {track_num}"
                            
                            length_ms = tr.get("length") or rec.get("length") or 0
                            duration_sec = length_ms // 1000 if length_ms else 0
                            
                            tracks.append({
                                "number": track_num,
                                "title": track_title,
                                "artist": artist,
                                "duration": duration_sec
                            })
                    
                    cover_url = self.get_cover_art_archive_url(release_id)

                    return {
                        "release_id": release_id,
                        "album": title,
                        "artist": artist,
                        "year": year,
                        "genre": genre,
                        "cover_url": cover_url,
                        "tracks": tracks,
                        "source": "MusicBrainz"
                    }
        except Exception as e:
            print(f"[MetadataService] Error fetching MusicBrainz discid: {e}")
        
        return None

    def search_albums_and_tracks_online(self, query: str) -> List[Dict[str, Any]]:
        """
        Searches internet (iTunes Store & MusicBrainz) for matching albums and complete tracklists.
        Returns list of albums with full track titles.
        """
        results = []
        if not query.strip():
            return results

        # 1. Query iTunes Store Search API
        try:
            itunes_url = f"https://itunes.apple.com/search?term={urllib.parse.quote(query)}&entity=album&limit=20"
            resp = self.session.get(itunes_url, timeout=4)
            if resp.status_code == 200:
                data = resp.json()
                for collection in data.get("results", []):
                    collection_id = collection.get("collectionId")
                    artist = collection.get("artistName", "")
                    album = collection.get("collectionName", "")
                    year = collection.get("releaseDate", "")[:4]
                    genre = collection.get("primaryGenreName", "")
                    art100 = collection.get("artworkUrl100", "")
                    art_hd = art100.replace("100x100bb", "1000x1000bb").replace("100x100", "1000x1000") if art100 else ""

                    # Fetch tracks for this collection
                    tracks = []
                    if collection_id:
                        lookup_url = f"https://itunes.apple.com/lookup?id={collection_id}&entity=song"
                        l_resp = self.session.get(lookup_url, timeout=4)
                        if l_resp.status_code == 200:
                            l_data = l_resp.json()
                            for song in l_data.get("results", []):
                                if song.get("wrapperType") == "track":
                                    tr_num = song.get("trackNumber", len(tracks) + 1)
                                    tr_title = song.get("trackName", f"Pista {tr_num}")
                                    tracks.append({
                                        "number": tr_num,
                                        "title": tr_title,
                                        "artist": artist
                                    })

                    results.append({
                        "album": album,
                        "artist": artist,
                        "year": year,
                        "genre": genre,
                        "cover_url": art_hd,
                        "tracks": tracks,
                        "source": "iTunes Store Web"
                    })
        except Exception as e:
            print(f"[MetadataService] Error searching iTunes albums: {e}")

        # 2. Query MusicBrainz API to get more results (Limit to 5 to avoid long delays)
        try:
            mb_url = f"https://musicbrainz.org/ws/2/release/?query={urllib.parse.quote(query)}&fmt=json&limit=5"
            resp = self.session.get(mb_url, timeout=4)
            if resp.status_code == 200:
                data = resp.json()
                for rel in data.get("releases", []):
                    rel_id = rel.get("id")
                    title = rel.get("title", "")
                    artist_credits = rel.get("artist-credit", [])
                    artist = artist_credits[0].get("name", "") if artist_credits else ""
                    date = rel.get("date", "")[:4]
                    track_count = rel.get("track-count", 0)
                    
                    # Fetch tracks explicitly for this release
                    mb_tracks = []
                    if rel_id:
                        lookup_url = f"https://musicbrainz.org/ws/2/release/{rel_id}?inc=recordings&fmt=json"
                        try:
                            l_resp = self.session.get(lookup_url, timeout=3)
                            if l_resp.status_code == 200:
                                l_data = l_resp.json()
                                for media in l_data.get("media", []):
                                    for tr in media.get("tracks", []):
                                        t_num = tr.get("position", len(mb_tracks) + 1)
                                        rec = tr.get("recording", {})
                                        t_title = tr.get("title") or rec.get("title") or f"Pista {t_num}"
                                        mb_tracks.append({"number": t_num, "title": t_title, "artist": artist})
                        except Exception:
                            pass
                    
                    results.append({
                        "album": title,
                        "artist": artist,
                        "year": date,
                        "genre": "Varios",
                        "cover_url": f"https://coverartarchive.org/release/{rel_id}/front-500",
                        "track_count": track_count,
                        "tracks": mb_tracks,
                        "source": "MusicBrainz"
                    })
        except Exception as e:
            print(f"[MetadataService] Error searching MusicBrainz: {e}")

        return results

    def get_cover_art_archive_url(self, release_id: str) -> str:
        """
        Fetches front cover image from Cover Art Archive for a release ID.
        """
        if not release_id:
            return ""
        url = f"https://coverartarchive.org/release/{release_id}"
        try:
            resp = self.session.get(url, timeout=4)
            if resp.status_code == 200:
                data = resp.json()
                images = data.get("images", [])
                for img in images:
                    if img.get("front"):
                        thumbs = img.get("thumbnails", {})
                        return thumbs.get("large") or img.get("image") or ""
                if images:
                    return images[0].get("image", "")
        except Exception:
            pass
        return ""

    def search_cover_art_online(self, query: str) -> List[Dict[str, str]]:
        """
        Searches internet for album covers matching query.
        """
        results = []
        if not query.strip():
            return results

        try:
            itunes_url = f"https://itunes.apple.com/search?term={urllib.parse.quote(query)}&entity=album&limit=50"
            resp = self.session.get(itunes_url, timeout=4)
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("results", []):
                    art100 = item.get("artworkUrl100", "")
                    if art100:
                        art_hd = art100.replace("100x100bb", "1000x1000bb").replace("100x100", "1000x1000")
                        results.append({
                            "url": art_hd,
                            "thumb": art100,
                            "title": item.get("collectionName", ""),
                            "artist": item.get("artistName", ""),
                            "source": "iTunes Store (HD)"
                        })
        except Exception as e:
            print(f"[MetadataService] Error searching iTunes covers: {e}")

        # Search Cover Art Archive via MusicBrainz
        try:
            mb_url = f"https://musicbrainz.org/ws/2/release/?query={urllib.parse.quote(query)}&fmt=json&limit=15"
            resp = self.session.get(mb_url, timeout=4)
            if resp.status_code == 200:
                data = resp.json()
                for rel in data.get("releases", []):
                    rel_id = rel.get("id")
                    title = rel.get("title", "")
                    artist_credits = rel.get("artist-credit", [])
                    artist = artist_credits[0].get("name", "") if artist_credits else ""
                    if rel_id:
                        thumb = f"https://coverartarchive.org/release/{rel_id}/front-250"
                        full_img = f"https://coverartarchive.org/release/{rel_id}/front-500"
                        results.append({
                            "url": full_img,
                            "thumb": thumb,
                            "title": title,
                            "artist": artist,
                            "source": "MusicBrainz / Cover Art Archive"
                        })
        except Exception as e:
            print(f"[MetadataService] Error searching MusicBrainz covers: {e}")

        return results

    def fetch_image_bytes(self, url_or_path: str) -> Optional[Tuple[bytes, str]]:
        """
        Loads image bytes and MIME type.
        """
        if not url_or_path:
            return None
        
        if os.path.exists(url_or_path):
            try:
                ext = os.path.splitext(url_or_path)[1].lower()
                mime_map = {
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.png': 'image/png',
                    '.webp': 'image/webp',
                    '.bmp': 'image/bmp'
                }
                mime = mime_map.get(ext, 'image/jpeg')
                with open(url_or_path, 'rb') as f:
                    return f.read(), mime
            except Exception as e:
                print(f"[MetadataService] Error reading local image file: {e}")
                return None

        if url_or_path.startswith("data:image/"):
            try:
                header, b64_data = url_or_path.split(",", 1)
                mime = header.split(";")[0].replace("data:", "")
                img_bytes = base64.b64decode(b64_data)
                return img_bytes, mime
            except Exception as e:
                print(f"[MetadataService] Error parsing base64 image: {e}")
                return None

        if url_or_path.startswith("http://") or url_or_path.startswith("https://"):
            try:
                resp = self.session.get(url_or_path, timeout=4)
                if resp.status_code == 200:
                    content_type = resp.headers.get("Content-Type", "image/jpeg")
                    if "png" in content_type:
                        mime = "image/png"
                    elif "webp" in content_type:
                        mime = "image/webp"
                    else:
                        mime = "image/jpeg"
                    return resp.content, mime
            except Exception as e:
                print(f"[MetadataService] Error fetching image URL: {e}")
        
        return None

    def get_image_base64_preview(self, url_or_path: str) -> Optional[str]:
        """
        Converts image to data:image/...;base64 string for HTML.
        """
        result = self.fetch_image_bytes(url_or_path)
        if result:
            img_bytes, mime = result
            b64_str = base64.b64encode(img_bytes).decode('ascii')
            return f"data:{mime};base64,{b64_str}"
        return None
