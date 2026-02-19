# mp3-player
this is a remake of an mp3 player i made using winforms

## FFmpeg
- The app uses `ffmpeg` from your system `PATH` (Linux/Windows).
- If `ffmpeg` is missing, downloads that require conversion will fail and show an error.

## PyInstaller builds
- Linux: `pyinstaller linux/app.spec`
- Windows: `pyinstaller win/app.spec`
