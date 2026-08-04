import os
import sys
import subprocess

def build_portable_exe():
    print("=== Compilando Audio Extractor CD by AO Labs ===")
    
    app_dir = os.path.dirname(os.path.abspath(__file__))
    main_py = os.path.join(app_dir, "main.py")
    ui_dir = os.path.join(app_dir, "ui")

    if sys.platform == 'win32':
        add_data_flag = "ui;ui"
        ffmpeg_add_data = "bin;bin"
    else:
        add_data_flag = "ui:ui"
        ffmpeg_add_data = "bin:bin"

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",  # No console window — pure GUI app
        "--name=Audio_Extractor_CD_AO_Labs",
        f"--add-data={add_data_flag}",
        f"--add-data={ffmpeg_add_data}",
        "--hidden-import=webview",
        "--hidden-import=flask",
        "--hidden-import=jinja2",
        "--hidden-import=werkzeug",
        "--hidden-import=markupsafe",
        "--hidden-import=itsdangerous",
        "--hidden-import=blinker",
        "--hidden-import=click",
        "--hidden-import=mutagen",
        "--hidden-import=requests",
        main_py
    ]

    print("Ejecutando PyInstaller...")
    result = subprocess.run(cmd, cwd=app_dir)

    if result.returncode == 0:
        dist_dir = os.path.join(app_dir, "dist", "Audio_Extractor_CD_AO_Labs")
        print("\n========================================================")
        print(" COMPILACION EXITOSA!")
        print(f" Ejecutable generado en: {dist_dir}")
        print("========================================================\n")
    else:
        print("\n[ERROR] Fallo la compilacion de PyInstaller.")

if __name__ == "__main__":
    build_portable_exe()
