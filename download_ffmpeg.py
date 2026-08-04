import os
import urllib.request
import zipfile
import tempfile
import shutil

print("Downloading FFmpeg...")
url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
temp_zip = os.path.join(tempfile.gettempdir(), "ffmpeg.zip")

urllib.request.urlretrieve(url, temp_zip)
print("Downloaded. Extracting...")

with zipfile.ZipFile(temp_zip, 'r') as zf:
    for file_info in zf.infolist():
        if file_info.filename.endswith("ffmpeg.exe"):
            print("Found ffmpeg.exe, extracting...")
            zf.extract(file_info, tempfile.gettempdir())
            extracted_path = os.path.join(tempfile.gettempdir(), file_info.filename)
            
            bin_dir = "e:/Antigravity/AO Labs/sonic_rip_app/bin"
            os.makedirs(bin_dir, exist_ok=True)
            final_path = os.path.join(bin_dir, "ffmpeg.exe")
            
            shutil.move(extracted_path, final_path)
            print(f"Moved ffmpeg to {final_path}")
            break

if os.path.exists(temp_zip):
    os.remove(temp_zip)

print("Done!")
