import cv2
import numpy as np
import pyaudio
import threading
import queue
import time 
import tkinter as tk
from tkinter import filedialog, ttk

# Constants
CHUNK_SIZE = 1024
SAMPLE_RATE = 44100
BUFFER_SIZE = 20
FRAME_BUFFER_SIZE = 5

# Global audio queue
audio_queue = queue.Queue(maxsize=BUFFER_SIZE)
frame_buffer = queue.Queue(maxsize=FRAME_BUFFER_SIZE)

# Define notes and their frequencies
NOTES = {
    'C': 261.63, 'C#': 277.18, 'D': 293.66, 'D#': 311.13, 'E': 329.63, 'F': 349.23,
    'F#': 369.99, 'G': 392.00, 'G#': 415.30, 'A': 440.00, 'A#': 466.16, 'B': 493.88
}

# Define scales (patterns of whole and half steps)
SCALES = {
    'major': [0, 2, 4, 5, 7, 9, 11],
    'natural_minor': [0, 2, 3, 5, 7, 8, 10],
    'harmonic_minor': [0, 2, 3, 5, 7, 8, 11],
    'melodic_minor': [0, 2, 3, 5, 7, 9, 11],
    'dorian': [0, 2, 3, 5, 7, 9, 10],
    'phrygian': [0, 1, 3, 5, 7, 8, 10],
    'lydian': [0, 2, 4, 6, 7, 9, 11],
    'mixolydian': [0, 2, 4, 5, 7, 9, 10],
    'locrian': [0, 1, 3, 5, 6, 8, 10],
    'pentatonic_major': [0, 2, 4, 7, 9],
    'pentatonic_minor': [0, 3, 5, 7, 10],
    'blues': [0, 3, 5, 6, 7, 10]
}

# Define common chord types
CHORD_TYPES = {
    'major': [0, 4, 7],
    'minor': [0, 3, 7],
    'diminished': [0, 3, 6],
    'augmented': [0, 4, 8],
    'sus4': [0, 5, 7],
    'sus2': [0, 2, 7],
    '7th': [0, 4, 7, 10],
    'm7': [0, 3, 7, 10],
    'maj7': [0, 4, 7, 11]
}

# Global variables for GUI control
current_key = 'C'
current_scale = 'major'
note_duration = 0.1
is_playing = False
video_source = None

def get_notes_in_key(key, scale_type='major'):
    start_index = list(NOTES.keys()).index(key)
    scale_pattern = SCALES[scale_type]
    return [list(NOTES.keys())[(start_index + interval) % 12] for interval in scale_pattern]

def play_audio():
    global is_playing
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paFloat32,
                    channels=1,
                    rate=SAMPLE_RATE,
                    output=True,
                    frames_per_buffer=CHUNK_SIZE)
    
    while is_playing:
        try:
            chunk = audio_queue.get(timeout=1)
            stream.write(chunk.astype(np.float32).tobytes())
        except queue.Empty:
            continue
        except Exception as e:
            print(f"Error in audio playback: {e}")
            break
    
    stream.stop_stream()
    stream.close()
    p.terminate()

def resize_frame(frame, max_size=500):
    height, width = frame.shape[:2]
    scale = max_size / max(height, width)
    return cv2.resize(frame, (int(width * scale), int(height * scale)))

def get_average_color(frame):
    return cv2.mean(frame)[:3][::-1]  # Convert BGR to RGB

def generate_note(frequency, duration, waveform='sine'):
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), False)
    if waveform == 'sine':
        return np.sin(2 * np.pi * frequency * t)
    elif waveform == 'square':
        return np.sign(np.sin(2 * np.pi * frequency * t))
    elif waveform == 'sawtooth':
        return 2 * (t * frequency - np.floor(0.5 + t * frequency))
    else:
        return np.sin(2 * np.pi * frequency * t)  # Default to sine

def generate_chord(base_freq, chord_type, duration, waveform='sine'):
    chord = np.zeros(int(SAMPLE_RATE * duration))
    for interval in CHORD_TYPES[chord_type]:
        freq = base_freq * (2 ** (interval / 12))
        chord += generate_note(freq, duration, waveform)
    return chord / 3  # Normalize amplitude

def color_to_chord(r, g, b, key_notes):
    h, s, v = cv2.cvtColor(np.uint8([[[b, g, r]]]), cv2.COLOR_RGB2HSV)[0][0]
    note_index = int(h / 180 * len(key_notes))
    base_note = key_notes[note_index]
    base_freq = NOTES[base_note]

    chord_types = list(CHORD_TYPES.keys())
    chord_index = int(s / 255 * len(chord_types))
    chord_type = chord_types[chord_index]

    waveforms = ['sine', 'square', 'sawtooth']
    waveform_index = int(v / 255 * len(waveforms))
    waveform = waveforms[waveform_index]

    return base_freq, chord_type, waveform, base_note

def process_frame(frame, key_notes):
    frame = resize_frame(frame)
    r, g, b = get_average_color(frame)
    
    base_freq, chord_type, waveform, base_note = color_to_chord(r, g, b, key_notes)
    audio_chunk = generate_chord(base_freq, chord_type, note_duration, waveform)
    
    try:
        audio_queue.put(audio_chunk, block=False)
    except queue.Full:
        audio_queue.get()
        audio_queue.put(audio_chunk)
    
    cv2.putText(frame, f"Chord: {base_note} {chord_type}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(frame, f"RGB: ({int(r)}, {int(g)}, {int(b)})", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(frame, f"Waveform: {waveform}", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    return frame

def process_video():
    global is_playing, video_source
    key_notes = get_notes_in_key(current_key, current_scale)
    
    try:
        if isinstance(video_source, str):
            cap = cv2.VideoCapture(video_source)
        else:
            cap = cv2.VideoCapture(0)  # Use default camera
        
        if not cap.isOpened():
            raise IOError(f"Cannot open video source")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_duration = 1 / fps if fps > 0 else 1/30
        
        while is_playing:
            ret, frame = cap.read()
            if not ret:
                break

            frame_buffer.put(frame)
            if frame_buffer.full():
                frame_to_process = frame_buffer.get()
                processed_frame = process_frame(frame_to_process, key_notes)
                cv2.imshow('Video', processed_frame)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

            time.sleep(max(0, frame_duration - note_duration))

    except Exception as e:
        print(f"Error processing video: {e}")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        is_playing = False

def select_video_source():
    global video_source
    file_path = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4 *.avi *.mov")])
    if file_path:
        video_source = file_path
        start_button.config(state=tk.NORMAL)

def use_webcam():
    global video_source
    video_source = 0  # Use default camera
    start_button.config(state=tk.NORMAL)

def start_processing():
    global is_playing
    if not is_playing:
        is_playing = True
        threading.Thread(target=play_audio, daemon=True).start()
        threading.Thread(target=process_video, daemon=True).start()
        start_button.config(text="Stop", command=stop_processing)

def stop_processing():
    global is_playing
    is_playing = False
    start_button.config(text="Start", command=start_processing)

def update_key(new_key):
    global current_key
    current_key = new_key

def update_scale(new_scale):
    global current_scale
    current_scale = new_scale

def update_duration(new_duration):
    global note_duration
    note_duration = float(new_duration)


# Create main window
root = tk.Tk()
root.title("Video to Audio Converter")

# Create and pack widgets
frame = ttk.Frame(root, padding="10")
frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

ttk.Button(frame, text="Select Video", command=select_video_source).grid(column=0, row=0, padx=5, pady=5)
ttk.Button(frame, text="Use Webcam", command=use_webcam).grid(column=1, row=0, padx=5, pady=5)

ttk.Label(frame, text="Key:").grid(column=0, row=1, padx=5, pady=5)
key_var = tk.StringVar(value="C")
ttk.Combobox(frame, textvariable=key_var, values=list(NOTES.keys()), state="readonly", width=5).grid(column=1, row=1, padx=5, pady=5)
key_var.trace("w", lambda *args: update_key(key_var.get()))

ttk.Label(frame, text="Scale:").grid(column=2, row=1, padx=5, pady=5)
scale_var = tk.StringVar(value="major")
ttk.Combobox(frame, textvariable=scale_var, values=list(SCALES.keys()), state="readonly", width=15).grid(column=3, row=1, padx=5, pady=5)
scale_var.trace("w", lambda *args: update_scale(scale_var.get()))

ttk.Label(frame, text="Note Duration:").grid(column=0, row=2, padx=5, pady=5)
duration_var = tk.StringVar(value="0.1")
ttk.Entry(frame, textvariable=duration_var, width=5).grid(column=1, row=2, padx=5, pady=5)
duration_var.trace("w", lambda *args: update_duration(duration_var.get()))

start_button = ttk.Button(frame, text="Start", command=start_processing, state=tk.DISABLED)
start_button.grid(column=0, row=3, columnspan=2, padx=5, pady=5)

root.mainloop()

#python VideoToAudio5.py