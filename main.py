import os
import sys
import json
import tempfile
import threading
import webbrowser
import ctypes
import time

from flask import Flask, send_from_directory, request, jsonify

from cd_ripper import CDRipper
from metadata_service import MetadataService
from encoder import AudioEncoder

def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller bundle."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)

# ── Flask App ──────────────────────────────────────────────
UI_DIR = get_resource_path("ui")
app = Flask(__name__, static_folder=UI_DIR, static_url_path="")

# ── Backend state ──────────────────────────────────────────
ripper = CDRipper()
metadata_service = MetadataService()
encoder = AudioEncoder()
winmm = ctypes.windll.winmm if sys.platform == 'win32' else None
is_ripping = False
is_playing_audio = False
current_playing_track = None
current_cover_bytes = None
current_cover_mime = "image/jpeg"
rip_progress = {"pct": 0, "status": "", "track": 0, "total": 0, "done": False, "success": False, "detail": ""}

# ── Routes: UI ─────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory(UI_DIR, "index.html")

# ── API Routes ─────────────────────────────────────────────
@app.route("/api/drives", methods=["GET"])
def api_get_drives():
    try:
        drives = ripper.get_cd_drives()
        return jsonify(drives)
    except Exception as e:
        print(f"[API] Error getting drives: {e}")
        return jsonify([])

@app.route("/api/cd_info", methods=["POST"])
def api_read_cd_info():
    global current_cover_bytes, current_cover_mime
    data = request.get_json(silent=True) or {}
    drive_letter = data.get("drive", "")
    if not drive_letter:
        return jsonify({"success": False, "message": "Selecciona una unidad de CD"})

    try:
        toc = ripper.read_toc(drive_letter)
        tracks_raw = toc.get("tracks", [])

        if not tracks_raw:
            return jsonify({
                "success": False,
                "message": f"No se detectaron pistas de audio en la unidad {drive_letter}"
            })

        toc_tracks_for_discid = []
        for tr in tracks_raw:
            toc_tracks_for_discid.append({
                'track': tr['track'],
                'start_sector': tr['start_sector'],
                'length_sectors': tr.get('length_sectors', 0)
            })

        leadout_sector = toc.get("leadout_sector", 0)
        mb_disc_id, freedb_id = metadata_service.calculate_disc_id(toc_tracks_for_discid, leadout_sector)

        # Query MusicBrainz
        mb_data = metadata_service.get_metadata_from_musicbrainz(mb_disc_id)

        cover_preview_b64 = None
        if mb_data and mb_data.get("cover_url"):
            img_tuple = metadata_service.fetch_image_bytes(mb_data["cover_url"])
            if img_tuple:
                current_cover_bytes, current_cover_mime = img_tuple
                cover_preview_b64 = metadata_service.get_image_base64_preview(mb_data["cover_url"])

        parsed_tracks = []
        for i, tr in enumerate(tracks_raw):
            tr_num = tr['track']
            dur_sec = tr['duration_sec']
            dur_str = f"{dur_sec // 60}:{dur_sec % 60:02d}"

            mb_title = None
            if mb_data and "tracks" in mb_data and i < len(mb_data["tracks"]):
                mb_title = mb_data["tracks"][i].get("title")

            track_title = mb_title or f"Pista {tr_num:02d}"
            artist_name = (mb_data.get("artist") if mb_data else None) or "Artista Desconocido"

            parsed_tracks.append({
                "number": tr_num,
                "title": track_title,
                "artist": artist_name,
                "duration": dur_str,
                "duration_sec": dur_sec,
                "cda_path": tr.get("cda_path", ""),
                "start_sector": tr.get("start_sector", 0),
                "length_sectors": tr.get("length_sectors", 0),
                "selected": True
            })

        album_name = (mb_data.get("album") if mb_data else None) or f"Álbum CD ({drive_letter})"
        artist_name = (mb_data.get("artist") if mb_data else None) or "Artista Desconocido"
        year = (mb_data.get("year") if mb_data else None) or ""
        genre = (mb_data.get("genre") if mb_data else None) or "CD Audio"

        return jsonify({
            "success": True,
            "found_online": bool(mb_data),
            "album": album_name,
            "artist": artist_name,
            "year": year,
            "genre": genre,
            "disc_id": mb_disc_id,
            "cover_preview": cover_preview_b64,
            "tracks": parsed_tracks
        })

    except Exception as e:
        print(f"[API] Error reading CD info: {e}")
        return jsonify({"success": False, "message": str(e)})

@app.route("/api/browse_folder", methods=["GET"])
def api_browse_folder():
    import tkinter as tk
    from tkinter import filedialog
    try:
        # Run tkinter isolated root to show folder dialog from background thread
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        folder = filedialog.askdirectory(title="Selecciona la carpeta de destino")
        root.destroy()
        return jsonify({"success": True, "path": folder})
    except Exception as e:
        print(f"[API] Error browsing folder: {e}")
        return jsonify({"success": False})

@app.route("/api/get_default_music_dir", methods=["GET"])
def api_get_default_music_dir():
    try:
        music_dir = os.path.expanduser("~\\Music")
        return jsonify({"success": True, "path": music_dir})
    except Exception:
        return jsonify({"success": True, "path": "C:\\Users\\Public\\Music"})

@app.route("/api/album_search", methods=["POST"])
def api_album_search():
    data = request.get_json(silent=True) or {}
    query = data.get("query", "")
    if not query:
        return jsonify({"success": False, "message": "Consulta vacía."})
    
    results = metadata_service.search_album_musicbrainz(query)
    return jsonify({"success": True, "results": results})

@app.route("/api/eject_cd", methods=["POST"])
def api_eject_cd():
    data = request.get_json(silent=True) or {}
    drive = data.get("drive", "")
    if not drive:
        return jsonify({"success": False})
    try:
        import ctypes
        dl = drive[0].upper()
        # open the drive as cdaudio and alias it to avoid conflicts
        ctypes.windll.winmm.mciSendStringW(f"open {dl}: type cdaudio alias cd_{dl}", None, 0, None)
        ctypes.windll.winmm.mciSendStringW(f"set cd_{dl} door open", None, 0, None)
        # close the alias
        ctypes.windll.winmm.mciSendStringW(f"close cd_{dl}", None, 0, None)
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error ejecting CD: {e}")
        return jsonify({"success": False})

@app.route("/api/open_folder", methods=["POST"])
def api_open_folder():
    data = request.get_json(silent=True) or {}
    path = data.get("path", "")
    try:
        if os.path.exists(path):
            os.startfile(path)
        return jsonify({"success": True})
    except Exception:
        return jsonify({"success": False})

@app.route("/api/play_track", methods=["POST"])
def api_play_track():
    global is_playing_audio, current_playing_track
    if not winmm:
        return jsonify({"success": False, "message": "Plataforma no soportada"})

    data = request.get_json(silent=True) or {}
    drive_letter = data.get("drive", "")
    track_number = data.get("track", 1)

    try:
        api_stop_audio_internal()
        drive = drive_letter.replace('\\', '').replace('/', '')
        winmm.mciSendStringW(f"open {drive} type cdaudio alias cd_player", None, 0, 0)
        winmm.mciSendStringW("set cd_player time format tmsf", None, 0, 0)
        winmm.mciSendStringW(f"play cd_player from {track_number} to {track_number + 1}", None, 0, 0)
        is_playing_audio = True
        current_playing_track = track_number
        return jsonify({"success": True, "track": track_number})
    except Exception as e:
        print(f"[API] Error playing track: {e}")
        return jsonify({"success": False, "message": str(e)})

def api_stop_audio_internal():
    global is_playing_audio, current_playing_track
    # Always attempt to stop — don't rely on state flag
    if winmm:
        try:
            winmm.mciSendStringW("stop cd_player", None, 0, 0)
        except Exception:
            pass
        try:
            winmm.mciSendStringW("close cd_player", None, 0, 0)
        except Exception:
            pass
    is_playing_audio = False
    current_playing_track = None

@app.route("/api/stop_audio", methods=["POST"])
def api_stop_audio():
    api_stop_audio_internal()
    return jsonify({"success": True})

@app.route("/api/search_albums", methods=["POST"])
def api_search_albums():
    data = request.get_json(silent=True) or {}
    query = data.get("query", "")
    try:
        results = metadata_service.search_albums_and_tracks_online(query)
        return jsonify(results)
    except Exception as e:
        print(f"[API] Error searching albums: {e}")
        return jsonify([])

@app.route("/api/search_covers", methods=["POST"])
def api_search_covers():
    data = request.get_json(silent=True) or {}
    query = data.get("query", "")
    try:
        results = metadata_service.search_cover_art_online(query)
        return jsonify(results)
    except Exception as e:
        print(f"[API] Error searching covers: {e}")
        return jsonify([])

@app.route("/api/set_cover_url", methods=["POST"])
def api_set_cover_url():
    global current_cover_bytes, current_cover_mime
    data = request.get_json(silent=True) or {}
    url = data.get("url", "")
    try:
        img_tuple = metadata_service.fetch_image_bytes(url)
        if img_tuple:
            current_cover_bytes, current_cover_mime = img_tuple
            preview = metadata_service.get_image_base64_preview(url)
            return jsonify({"success": True, "preview": preview})
        return jsonify({"success": False, "message": "No se pudo descargar la imagen"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route("/api/kofi", methods=["POST"])
def api_kofi():
    try:
        webbrowser.open("https://ko-fi.com/aolabs")
        return jsonify({"success": True})
    except Exception:
        return jsonify({"success": False})

@app.route("/api/start_rip", methods=["POST"])
def api_start_rip():
    global is_ripping, rip_progress
    if is_ripping:
        return jsonify({"success": False, "message": "Ya hay un proceso de extracción en curso"})

    data = request.get_json(silent=True) or {}
    drive_letter = data.get("drive", "")
    output_dir = data.get("output_dir", "")
    format_type = data.get("format", "flac")
    quality_setting = data.get("quality", "max")
    album_meta = data.get("album_meta", {})
    tracks = data.get("tracks", [])

    api_stop_audio_internal()

    if not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            return jsonify({"success": False, "message": f"No se pudo crear el directorio: {e}"})

    selected_tracks = [t for t in tracks if t.get("selected", True)]
    if not selected_tracks:
        return jsonify({"success": False, "message": "Selecciona al menos una pista"})

    is_ripping = True
    rip_progress = {"pct": 0, "status": "Iniciando...", "track": 0, "total": len(selected_tracks), "done": False, "success": False, "detail": ""}

    thread = threading.Thread(
        target=rip_worker,
        args=(drive_letter, output_dir, format_type, quality_setting, album_meta, selected_tracks),
        daemon=True
    )
    thread.start()
    return jsonify({"success": True, "message": "Proceso iniciado"})

@app.route("/api/rip_progress", methods=["GET"])
def api_rip_progress():
    return jsonify(rip_progress)

@app.route("/api/cancel_rip", methods=["POST"])
def api_cancel_rip():
    global is_ripping
    is_ripping = False
    return jsonify({"success": True})

def rip_worker(drive_letter, output_dir, format_type, quality_setting, album_meta, selected_tracks):
    global is_ripping, rip_progress
    total_tracks = len(selected_tracks)
    temp_dir = tempfile.mkdtemp(prefix="audio_extractor_")

    try:
        clean_artist = "".join(c for c in album_meta.get("artist", "Artista") if c.isalnum() or c in " -_.").strip()
        clean_album = "".join(c for c in album_meta.get("album", "Álbum") if c.isalnum() or c in " -_.").strip()
        dest_folder = os.path.join(output_dir, f"{clean_artist} - {clean_album}")
        os.makedirs(dest_folder, exist_ok=True)

        for index, tr in enumerate(selected_tracks):
            if not is_ripping:
                break

            tr_num = tr.get("number", index + 1)
            tr_title = tr.get("title", f"Pista {tr_num:02d}")
            clean_title = "".join(c for c in tr_title if c.isalnum() or c in " -_.").strip()

            ext_map = {
                "flac": ".flac", "mp3": ".mp3", "wav": ".wav",
                "aac": ".m4a", "m4a": ".m4a", "ogg": ".ogg",
                "opus": ".opus", "alac": ".m4a"
            }
            ext = ext_map.get(format_type.lower(), ".flac")
            output_filename = f"{tr_num:02d} - {clean_title}{ext}"
            final_output_path = os.path.join(dest_folder, output_filename)

            progress_pct = int((index / total_tracks) * 100)
            rip_progress["pct"] = progress_pct
            rip_progress["status"] = f"Extrayendo Pista {tr_num} de {total_tracks}: {tr_title}..."
            rip_progress["track"] = index + 1

            temp_wav = os.path.join(temp_dir, f"temp_track_{tr_num:02d}.wav")
            cda_path = tr.get("cda_path") or os.path.join(f"{drive_letter}\\", f"Track{tr_num:02d}.cda")

            def rip_callback(pct):
                track_base = int((index / total_tracks) * 100)
                track_alloc = 100 / total_tracks
                current_pct = track_base + int((pct / 100) * (track_alloc * 0.95))
                rip_progress["pct"] = current_pct

            start_lba = tr.get("start_sector", 0)
            total_sectors_tr = tr.get("length_sectors", 0)

            ripped_ok = ripper.rip_track_to_wav(cda_path, start_lba, total_sectors_tr, temp_wav, rip_callback)

            if ripped_ok:
                rip_progress["status"] = f"Codificando {format_type.upper()} ({tr_title})..."
                rip_progress["pct"] = progress_pct + int((95 * (100 / total_tracks)) / 100)

                track_metadata = {
                    "title": tr_title,
                    "artist": tr.get("artist") or album_meta.get("artist", "Artista Desconocido"),
                    "album": album_meta.get("album", "Álbum Desconocido"),
                    "year": album_meta.get("year", ""),
                    "genre": album_meta.get("genre", ""),
                    "track_num": tr_num,
                    "total_tracks": total_tracks
                }

                encoder.encode_and_tag(
                    temp_wav, final_output_path, format_type, quality_setting,
                    track_metadata, current_cover_bytes, current_cover_mime
                )

            if os.path.exists(temp_wav):
                try:
                    os.remove(temp_wav)
                except Exception:
                    pass

        is_ripping = False
        rip_progress["pct"] = 100
        rip_progress["done"] = True
        rip_progress["success"] = True
        rip_progress["detail"] = dest_folder.replace('\\', '/')

    except Exception as e:
        print(f"[API] Worker error: {e}")
        is_ripping = False
        rip_progress["done"] = True
        rip_progress["success"] = False
        rip_progress["detail"] = str(e)


# ── Cleanup: stop CD audio on shutdown ─────────────────────
import atexit
import signal

def cleanup_audio():
    """Stop CD audio when server exits for any reason."""
    print("[Cleanup] Deteniendo audio del CD...")
    api_stop_audio_internal()

atexit.register(cleanup_audio)

def signal_handler(sig, frame):
    cleanup_audio()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Endpoint for browser beforeunload — stops audio when tab is closed
@app.route("/api/page_unload", methods=["POST"])
def api_page_unload():
    api_stop_audio_internal()
    return jsonify({"success": True})


# ── Main ───────────────────────────────────────────────────
import webview
from werkzeug.serving import make_server

class ServerThread(threading.Thread):
    def __init__(self, app, host, port):
        threading.Thread.__init__(self)
        self.server = make_server(host, port, app)
        self.ctx = app.app_context()
        self.ctx.push()

    def run(self):
        print("Starting Flask server...")
        self.server.serve_forever()

    def shutdown(self):
        self.server.shutdown()

def main():
    port = 8745
    url = f"http://127.0.0.1:{port}"

    print(f"")
    print(f"  +----------------------------------------------+")
    print(f"  |   Audio Extractor CD by AO Labs               |")
    print(f"  |   Servidor local: {url:<25s}  |")
    print(f"  |   Abriendo ventana de aplicacion...           |")
    print(f"  +----------------------------------------------+")
    print(f"")

    # Start Flask in a background thread
    server = ServerThread(app, "127.0.0.1", port)
    server.start()

    # Create a pure webview window pointing to the Flask URL
    # By separating Flask and pywebview this way, we avoid all COM/WinForms deadlocks.
    window = webview.create_window(
        title="Audio Extractor CD by AO Labs",
        url=url,
        width=1000,
        height=800,
        min_size=(800, 600),
        background_color='#0d101a'
    )
    
    def on_closing():
        return window.create_confirmation_dialog('Salir', '¿Deseas cerrar Audio Extractor CD?')
        
    window.events.closing += on_closing
    
    # Start the GUI loop (this blocks until the window is closed)
    webview.start()
    
    # When the window is closed, shut down the server
    print("Shutting down server...")
    server.shutdown()
    server.join()
    cleanup_audio()

if __name__ == "__main__":
    main()
