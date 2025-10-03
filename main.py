import tkinter as tk
from tkinter import filedialog, messagebox
import pygame
import os
import glob
import random
import threading
import time
import yt_dlp
import sys
import io
import requests # was gonna use this
import json

IMAGE_SIZE = (250,250)
#need to break this up into files or something
try:
    from mutagen.mp3 import MP3
    from mutagen.id3 import ID3
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False
    print("Mutagen not available. try installing mutagen")

try:
    from PIL import Image, ImageTk, ImageOps
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False
    print("Pillow not available. try installing pillow ")

def get_ffmpeg_path():
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS 
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, 'tools', 'ffmpeg.exe') 

class MusicPlayer:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("MP3 Player")

        self.window.geometry("750x450")
        self.window.resizable(False, False)
        
        pygame.mixer.init()
        
        self.current_folder = None
        self.is_filtering = False
        self.playlist = []
        self.filtered_playlist = []
        self.current_index = 0
        self.current_song_name = None
        self.is_playing = False
        self.is_paused = False
        self.is_downloading = False

        self.cover_art_image = None
        self.setup_ui()
        self.media_controls = None
        
        self.monitor_playback()
    
    def setup_ui(self):
        search_frame = tk.Frame(self.window)
        search_frame.pack(fill="x",padx=10,pady=2)
        self.search_label = tk.Label(search_frame, text="Search Playlist: ").pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self.handle_playlist_search)
        self.search_box = tk.Entry(search_frame, textvariable=self.search_var)
        self.search_box.pack(fill="x")

        folder_frame = tk.Frame(self.window)
        folder_frame.pack(fill="x", padx=10, pady=2)
        tk.Label(folder_frame, text="Folder:             ").pack(side="left")
        self.folder_label = tk.Label(folder_frame, text="No folder selected", bg="lightgrey", relief="sunken")
        self.folder_label.pack(side="left", fill="x", expand=True, padx=(5, 5))
        self.browse_btn = tk.Button(folder_frame, text="Browse", command=self.browse_folder)
        self.browse_btn.pack(side="right")

        
        current_frame = tk.Frame(self.window)
        current_frame.pack(fill="x", padx=10, pady=2)
        tk.Label(current_frame, text="Now Playing:  ").pack(side="left")
        self.current_song_label = tk.Label(current_frame, text="None", bg="lightgray", relief="sunken")
        self.current_song_label.pack(side="left", fill="x", expand=True, padx=(5, 0))

        main_content_frame = tk.Frame(self.window)
        main_content_frame.pack(fill="both", expand=True, padx=10, pady=2)

        playlist_frame = tk.Frame(main_content_frame)
        playlist_frame.pack(side="left", fill="both", expand=True)
        list_frame = tk.Frame(playlist_frame)
        list_frame.pack(fill="both", expand=True)
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        self.playlist_box = tk.Listbox(list_frame, yscrollcommand=scrollbar.set)
        self.playlist_box.pack(side="left", fill="both", expand=True)
        self.playlist_box.bind('<<ListboxSelect>>', self.on_song_select)
        scrollbar.config(command=self.playlist_box.yview)

        image_frame = tk.Frame(main_content_frame, width=IMAGE_SIZE[0], height=IMAGE_SIZE[1])
        image_frame.pack(side="right", fill="y", padx=(0, 0))
        image_frame.pack_propagate(False) 
        self.album_art_label = tk.Label(image_frame, bg="gray85", text="No Art", relief="sunken")
        self.album_art_label.pack(fill="both", expand=True, pady=2)


        download_frame = tk.Frame(self.window)
        download_frame.pack(fill="x", padx=10, pady=2)
        tk.Label(download_frame, text="Song URL(YT, SoundCloud, etc):").pack(side="left")
        self.url_entry = tk.Entry(download_frame, width=50)
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(5, 5))
        self.url_entry.bind('<Return>', lambda e: self.download_song())
        self.download_btn = tk.Button(download_frame, text="Download", command=self.download_song)
        self.download_btn.pack(side="right")

        status_frame = tk.Frame(self.window)
        status_frame.pack(fill="x", padx=10, pady=2)
        self.status_label = tk.Label(status_frame, text="Ready", fg="black", bg="lightgray", relief="sunken")
        self.status_label.pack(fill="x")
    
        control_frame = tk.Frame(self.window)
        control_frame.pack(fill="x", padx=10, pady=0)
        self.prev_btn = tk.Button(control_frame, text="Previous", command=self.previous_song)
        self.prev_btn.pack(side="left", padx=5)
        self.play_btn = tk.Button(control_frame, text="Play", command=self.toggle_play, bg="lightgreen")
        self.play_btn.pack(side="left", padx=5)
        self.next_btn = tk.Button(control_frame, text="Next", command=self.next_song)
        self.next_btn.pack(side="left", padx=5)
        self.shuffle_btn = tk.Button(control_frame, text="Shuffle", command=self.shuffle_playlist)
        self.shuffle_btn.pack(side="left", padx=5)
        volume_frame = tk.Frame(control_frame)
        volume_frame.pack(side="right", padx=5)
        tk.Label(volume_frame, text="Volume: ").pack(side="left", padx=5, pady=0)
        self.volume_scale = tk.Scale(volume_frame, from_=0, to=100, orient="horizontal", command=self.set_volume, length=100)
        self.volume_scale.set(70)
        self.volume_scale.pack(side="right", pady=(0,12))

    def browse_folder(self):
        folder = filedialog.askdirectory(title="Select Music Folder")
        if folder:
            self.current_folder = folder
            self.folder_label.config(text=folder)
            self.load_playlist()
            self.update_status("Folder loaded successfully", "green")
    
    def update_status(self, message, color="black"):
        self.status_label.config(text=message, fg=color)
        if color != "red":
            self.window.after(5000, lambda: self.status_label.config(text="Ready", fg="black"))
    
    #somewhere i forgot to switch between the full playlist and the ui
    #but zybooks is due in an hour
    def handle_playlist_search(self, *args):
        query = self.search_var.get().strip()
        self.playlist_box.delete(0, tk.END)

        if not query:
            self.is_filtering = False
            self.ui_playlist = self.playlist.copy()
        else:
            self.is_filtering = True
            self.ui_playlist = []
            for song in self.playlist:
                if query.lower() in song.lower():
                    self.ui_playlist.append(song)
        
        for song in self.ui_playlist: self.playlist_box.insert(tk.END, song)
        

    def download_song(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("No URL", "Enter a valid URL")
            return
        if not self.current_folder:
            messagebox.showwarning("No Folder", "Select a folder first")
            return
        if self.is_downloading:
            messagebox.showinfo("Download in Progress", "A download is already in progress")
            return
        download_thread = threading.Thread(target=self._download_song_thread, args=(url,), daemon=True)
        download_thread.start()
    
    def _download_song_thread(self, url):
        self.is_downloading = True
        self.window.after(0, lambda: self.update_status("Starting download...", "blue"))
        self.window.after(0, lambda: self.download_btn.config(state="disabled", text="Downloading..."))
        try:
            ydl_opts = {
                'ffmpeg_location': get_ffmpeg_path(), 'format': 'bestaudio/best',
                'postprocessors': [
                    {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '0'},
                    {'key': 'EmbedThumbnail'}, {'key': 'FFmpegMetadata', 'add_metadata': True},
                ],
                'outtmpl': os.path.join(self.current_folder, '%(title)s.%(ext)s'),
                'writethumbnail': True, 'quiet': True, 'no_warnings': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                video_title = info.get('title', 'Unknown')
                self.window.after(0, lambda: self.update_status(f"Downloading: {video_title[:50]}...", "blue"))
                ydl.download([url])

            self.window.after(0, lambda: self.update_status(f"Downloaded: {video_title[:40]}...", "green"))
            self.window.after(0, lambda: self.url_entry.delete(0, tk.END))
            self.window.after(0, self.load_playlist)
        except Exception as e:
            error_msg = str(e)
            if "Video unavailable" in error_msg: error_msg = "Video is unavailable or private"
            elif "network" in error_msg.lower(): error_msg = "Network error"
            elif "ffmpeg" in error_msg.lower(): error_msg = "FFmpeg not found"
            else: error_msg = f"Download failed: {error_msg[:50]}..."
            self.window.after(0, lambda: self.update_status(f"{error_msg}", "red"))
        finally:
            self.is_downloading = False
            self.window.after(0, lambda: self.download_btn.config(state="normal", text="Download"))
    
    def load_playlist(self):
        self.is_filtering = False
        self.search_box.delete(0, tk.END)
        if not self.current_folder: return
        mp3_files = glob.glob(os.path.join(self.current_folder, "*.mp3"))
        self.playlist = [os.path.basename(f) for f in mp3_files]
        self.ui_playlist = self.playlist.copy()
        self.playlist_box.delete(0, tk.END)
        for song in self.ui_playlist: self.playlist_box.insert(tk.END, song)
        if self.ui_playlist:
            self.current_index = 0
            self.playlist_box.select_set(0)
            self.current_song_label.config(text="Ready to play: " + self.ui_playlist[0])
            self.clear_album_art()
        elif self.current_folder:
            self.update_status("No MP3 files found in selected folder", "orange")
    
    def toggle_play(self):
        if not self.ui_playlist:
            messagebox.showwarning("No Music", "No songs in queue")
            return
        if self.is_playing:
            if self.is_paused:
                pygame.mixer.music.unpause()
                self.is_paused = False
                self.play_btn.config(text="Pause")
            else:
                pygame.mixer.music.pause()
                self.is_paused = True
                self.play_btn.config(text="Play")
        else:
            self.play_current_song()


    def play_current_song(self):
        if not self.ui_playlist or self.current_index >= len(self.ui_playlist):
            self.is_playing = False
            pygame.mixer.music.stop()
            self.clear_album_art()
            return
        
        song_path = os.path.join(self.current_folder, self.ui_playlist[self.current_index])
        try:
            pygame.mixer.music.load(song_path)
            pygame.mixer.music.play()
            self.is_playing = True
            self.is_paused = False
            self.play_btn.config(text="Pause")
            self.current_song_name = self.ui_playlist[self.current_index]
            self.current_song_label.config(text=self.current_song_name)
            self.playlist_box.selection_clear(0, tk.END)
            self.playlist_box.select_set(self.current_index)
            self.playlist_box.see(self.current_index)
            
            self.update_album_art(song_path)

        except Exception as e:
            messagebox.showerror("Playback Error", f"Couldn't play {song_path}\nError: {str(e)}")
            self.is_playing = False
            self.clear_album_art()
    
    def clear_album_art(self):
        if self.album_art_label:
            self.album_art_label.config(image='', text="No Art")
            self.cover_art_image = None

    def update_album_art(self, song_path):
        if not MUTAGEN_AVAILABLE or not PILLOW_AVAILABLE:
            self.album_art_label.config(text="Libs Missing", image='')
            return

        try:
            audio = MP3(song_path, ID3=ID3)
            found_image = False
            for key, value in audio.tags.items():
                if key.startswith('APIC'):
                    cover = value.data
                    img = Image.open(io.BytesIO(cover))
                    frame_width = IMAGE_SIZE[0]  
                    frame_height = IMAGE_SIZE[1]
                    img = ImageOps.fit(img, (frame_width, frame_height), Image.Resampling.LANCZOS)
                    tk_image = ImageTk.PhotoImage(img)
                    self.album_art_label.config(image=tk_image, text="")
                    self.cover_art_image = tk_image
                    found_image = True
                    break
            if not found_image:
                print("apic not found")
                self.clear_album_art()
        except Exception as e:
            print(f"error reading album art: {e}")
            self.clear_album_art()

    def next_song(self):
        if not self.ui_playlist: return
        self.current_index = (self.current_index + 1) % len(self.ui_playlist)
        if self.is_playing or self.is_paused:
            self.play_current_song()
        else:
            self.playlist_box.selection_clear(0, tk.END)
            self.playlist_box.select_set(self.current_index)
            self.current_song_label.config(text=f"Ready: {self.ui_playlist[self.current_index]}")
    
    def previous_song(self):
        if not self.ui_playlist: return
        self.current_index = (self.current_index - 1 + len(self.ui_playlist)) % len(self.ui_playlist)
        if self.is_playing or self.is_paused:
            self.play_current_song()
        else:
            self.playlist_box.selection_clear(0, tk.END)
            self.playlist_box.select_set(self.current_index)
            self.current_song_label.config(text=f"Ready: {self.ui_playlist[self.current_index]}")
    
    def shuffle_playlist(self):
        if not self.playlist:
            messagebox.showwarning("No Playlist", "Load songs first")
            return
        current_song = self.ui_playlist[self.current_index] if self.current_index < len(self.ui_playlist) else None
        self.search_box.delete(0, tk.END) # will reset self.ui_playlist

        random.shuffle(self.ui_playlist)
        self.playlist_box.delete(0, tk.END)
        for song in self.ui_playlist: self.playlist_box.insert(tk.END, song)
        try:
            self.current_index = self.ui_playlist.index(current_song) if current_song else 0
        except ValueError:
            self.current_index = 0
        if self.playlist: self.playlist_box.select_set(self.current_index)
        self.update_status("Playlist shuffled", "green")
    
    def on_song_select(self, event):
        selection = self.playlist_box.curselection()
        if selection and selection[0] < len(self.ui_playlist) and self.current_song_name != self.ui_playlist[selection[0]]:
            self.current_index = selection[0]
            if self.is_playing or self.is_paused:
                self.play_current_song()

    def set_volume(self, value):
        pygame.mixer.music.set_volume(int(value) / 100.0)
    
    def monitor_playback(self):
        def check_music():
            while True:
                if self.is_playing and not self.is_paused and not pygame.mixer.music.get_busy():
                    self.window.after(0, self.next_song)
                time.sleep(0.5)
        monitor_thread = threading.Thread(target=check_music, daemon=True)
        monitor_thread.start()
    
    def on_closing(self):
        pygame.mixer.quit()
        self.window.destroy()

    def run(self):
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        try:
            self.window.mainloop()
        except KeyboardInterrupt:
            self.on_closing()

if __name__ == "__main__":
    print("Checking dependencies...")
    try: import pygame; print("Pygame available")
    except ImportError: print("Pygame not found (required for the app)"); sys.exit(1)
    try: import yt_dlp; print("yt-dlp available")
    except ImportError: print("yt-dlp not found (required for the app)"); sys.exit(1)
    if MUTAGEN_AVAILABLE: print("Mutagen available (for metadata)")
    if PILLOW_AVAILABLE: print("Pillow available (for images)")
    print("\nStarting player...")
    app = MusicPlayer()
    app.run()