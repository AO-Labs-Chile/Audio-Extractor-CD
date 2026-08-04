import os
import sys
import subprocess
import mutagen
from mutagen.flac import FLAC, Picture as FLACPicture
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB, TDRC, TCON, TRCK, ID3NoHeaderError
from mutagen.mp4 import MP4, MP4Cover
from mutagen.oggvorbis import OggVorbis
from mutagen.oggopus import OggOpus
from typing import Dict, Any, Optional

class AudioEncoder:
    def __init__(self):
        pass

    def encode_and_tag(self, wav_input_path: str, output_path: str, format_type: str, quality_setting: str, metadata: Dict[str, Any], cover_bytes: Optional[bytes] = None, cover_mime: str = "image/jpeg") -> bool:
        """
        Encodes a WAV audio file into target format (FLAC, MP3, WAV, AAC, OGG, OPUS, ALAC)
        and embeds full metadata tags + album cover art image.
        """
        format_type = format_type.lower().strip()
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        # 1. Encoding Step using FFmpeg
        encoded_ok = self.encode_with_ffmpeg(wav_input_path, output_path, format_type, quality_setting)
        if not encoded_ok:
            return False

        # 2. Embed Tags & Cover Art Step using Mutagen
        try:
            self.embed_metadata_and_cover(output_path, format_type, metadata, cover_bytes, cover_mime)
            return True
        except Exception as e:
            print(f"[AudioEncoder] Error embedding metadata into {output_path}: {e}")
            return True  # File is encoded even if tagging failed

    def encode_with_ffmpeg(self, wav_input: str, output_file: str, fmt: str, quality: str) -> bool:
        """
        Executes FFmpeg encoder for requested format.
        """
        ffmpeg_path = "ffmpeg"
        if hasattr(sys, '_MEIPASS'):
            local_ffmpeg = os.path.join(sys._MEIPASS, 'bin', 'ffmpeg.exe')
            if os.path.exists(local_ffmpeg):
                ffmpeg_path = local_ffmpeg
        else:
            local_ffmpeg = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bin', 'ffmpeg.exe')
            if os.path.exists(local_ffmpeg):
                ffmpeg_path = local_ffmpeg
                
        cmd = [ffmpeg_path, "-y", "-i", wav_input, "-vn"]

        if fmt == "flac":
            # Lossless FLAC
            comp_level = "8" if quality == "max" else "5"
            cmd.extend(["-c:a", "flac", "-compression_level", comp_level])
        
        elif fmt == "mp3":
            # MP3 encoding
            if quality == "320":
                cmd.extend(["-c:a", "libmp3lame", "-b:a", "320k"])
            elif quality == "256":
                cmd.extend(["-c:a", "libmp3lame", "-b:a", "256k"])
            elif quality == "v0":
                cmd.extend(["-c:a", "libmp3lame", "-q:a", "0"])
            else: # Default 320k
                cmd.extend(["-c:a", "libmp3lame", "-b:a", "320k"])
        
        elif fmt in ["aac", "m4a"]:
            cmd.extend(["-c:a", "aac", "-b:a", "256k"])
        
        elif fmt == "ogg":
            cmd.extend(["-c:a", "libvorbis", "-q:a", "6"])
        
        elif fmt == "opus":
            cmd.extend(["-c:a", "libopus", "-b:a", "160k"])

        elif fmt == "alac":
            cmd.extend(["-c:a", "alac"])

        elif fmt == "wav":
            # Copy PCM wav directly
            cmd.extend(["-c:a", "pcm_s16le"])

        else:
            # Default FLAC fallback
            cmd.extend(["-c:a", "flac"])

        cmd.append(output_file)

        try:
            startupinfo = None
            if sys.platform == 'win32':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                startupinfo=startupinfo
            )
            _, stderr = process.communicate()
            return process.returncode == 0 and os.path.exists(output_file)
        except Exception as e:
            print(f"[AudioEncoder] FFmpeg encoding error for {fmt}: {e}")
            return False

    def embed_metadata_and_cover(self, file_path: str, fmt: str, meta: Dict[str, Any], cover_bytes: Optional[bytes], cover_mime: str):
        """
        Embeds tags and artwork into encoded file using Mutagen.
        meta keys: title, artist, album, year, genre, track_num, total_tracks
        """
        title = meta.get("title", "")
        artist = meta.get("artist", "")
        album = meta.get("album", "")
        year = str(meta.get("year", ""))
        genre = meta.get("genre", "")
        track_num = meta.get("track_num", 1)

        # FLAC Tagging
        if fmt == "flac":
            audio = FLAC(file_path)
            audio["TITLE"] = title
            audio["ARTIST"] = artist
            audio["ALBUM"] = album
            if year:
                audio["DATE"] = year
            if genre:
                audio["GENRE"] = genre
            audio["TRACKNUMBER"] = str(track_num)

            # Embed cover art picture
            if cover_bytes:
                picture = FLACPicture()
                picture.data = cover_bytes
                picture.type = 3  # Cover (front)
                picture.mime = cover_mime
                picture.description = "Front Cover"
                audio.clear_pictures()
                audio.add_picture(picture)
            audio.save()

        # MP3 Tagging (ID3v2.4)
        elif fmt == "mp3":
            try:
                tags = ID3(file_path)
            except ID3NoHeaderError:
                tags = ID3()

            tags.add(TIT2(encoding=3, text=title))
            tags.add(TPE1(encoding=3, text=artist))
            tags.add(TALB(encoding=3, text=album))
            if year:
                tags.add(TDRC(encoding=3, text=year))
            if genre:
                tags.add(TCON(encoding=3, text=genre))
            tags.add(TRCK(encoding=3, text=str(track_num)))

            if cover_bytes:
                # Remove existing APIC frames
                tags.delall("APIC")
                tags.add(APIC(
                    encoding=3,
                    mime=cover_mime,
                    type=3,  # Front cover
                    desc='Front Cover',
                    data=cover_bytes
                ))
            tags.save(file_path)

        # M4A / AAC / ALAC Tagging (MP4 Atoms)
        elif fmt in ["m4a", "aac", "alac"]:
            audio = MP4(file_path)
            audio["\xa9nam"] = [title]
            audio["\xa9ART"] = [artist]
            audio["\xa9alb"] = [album]
            if year:
                audio["\xa9day"] = [year]
            if genre:
                audio["\xa9gen"] = [genre]
            audio["trkn"] = [(track_num, 0)]

            if cover_bytes:
                fmt_enum = MP4Cover.FORMAT_PNG if "png" in cover_mime else MP4Cover.FORMAT_JPEG
                audio["covr"] = [MP4Cover(cover_bytes, imageformat=fmt_enum)]
            audio.save()

        # OGG Vorbis Tagging
        elif fmt == "ogg":
            audio = OggVorbis(file_path)
            audio["TITLE"] = title
            audio["ARTIST"] = artist
            audio["ALBUM"] = album
            if year:
                audio["DATE"] = year
            if genre:
                audio["GENRE"] = genre
            audio["TRACKNUMBER"] = str(track_num)
            
            if cover_bytes:
                picture = FLACPicture()
                picture.data = cover_bytes
                picture.type = 3
                picture.mime = cover_mime
                picture.description = "Front Cover"
                encoded_pic = base64.b64encode(picture.write()).decode('ascii')
                audio["METADATA_BLOCK_PICTURE"] = [encoded_pic]
            audio.save()

        # OPUS Tagging
        elif fmt == "opus":
            audio = OggOpus(file_path)
            audio["TITLE"] = title
            audio["ARTIST"] = artist
            audio["ALBUM"] = album
            if year:
                audio["DATE"] = year
            if genre:
                audio["GENRE"] = genre
            audio["TRACKNUMBER"] = str(track_num)

            if cover_bytes:
                picture = FLACPicture()
                picture.data = cover_bytes
                picture.type = 3
                picture.mime = cover_mime
                picture.description = "Front Cover"
                encoded_pic = base64.b64encode(picture.write()).decode('ascii')
                audio["METADATA_BLOCK_PICTURE"] = [encoded_pic]
            audio.save()
