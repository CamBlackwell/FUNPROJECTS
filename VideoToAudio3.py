import cv2
import numpy as np
import pyaudio
import threading
import argparse
import queue
import time 
from scipy.io import wavfile
import tkinter as tk
from tkinter import filedialog

# Constants
CHUNK_SIZE = 1024
SAMPLE_RATE = 44100
BUFFER_SIZE = 20
FRAME_BUFFER_SIZE = 5

# Global audio queue
audio_queue = queue.Queue(maxsize=BUFFER_SIZE)
frame_buffer = queue.Queue(maxsize=FRAME_BUFFER_SIZE)

# Define a wider range of notes for chord generation
NOTES = {
    'C': 261.63, 'C#': 277.18, 'D': 293.66, 'D#': 311.13, 'E': 329.63, 'F': 349.23,
    'F#': 369.99, 'G': 392.00, 'G#': 415.30, 'A': 440.00, 'A#': 466.16, 'B': 493.88
}

# Define common chord types
CHORD_TYPES = {
    'major': [0, 4, 7],
    'minor': [0, 3, 7],
    'diminished': [0, 3, 6],
    'augmented': [0, 4, 8]
}

def play_audio():
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paFloat32,
                    channels=1,
                    rate=SAMPLE_RATE,
                    output=True,
                    frames_per_buffer=CHUNK_SIZE)
    
    while True:
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

def color_to_chord(r, g, b):
    # Use hue to determine base note
    h, s, v = cv2.cvtColor(np.uint8([[[b, g, r]]]), cv2.COLOR_RGB2HSV)[0][0]
    note_index = int(h / 180 * len(NOTES))
    base_note = list(NOTES.keys())[note_index]
    base_freq = NOTES[base_note]

    # Use saturation to determine chord type
    chord_types = list(CHORD_TYPES.keys())
    chord_index = int(s / 255 * len(chord_types))
    chord_type = chord_types[chord_index]

    # Use value to determine waveform
    waveforms = ['sine', 'square', 'sawtooth']
    waveform_index = int(v / 255 * len(waveforms))
    waveform = waveforms[waveform_index]

    return base_freq, chord_type, waveform, base_note

def process_frame(frame, note_duration):
    frame = resize_frame(frame)
    r, g, b = get_average_color(frame)
    
    base_freq, chord_type, waveform, base_note = color_to_chord(r, g, b)
    audio_chunk = generate_chord(base_freq, chord_type, note_duration, waveform)
    
    try:
        audio_queue.put(audio_chunk, block=False)
    except queue.Full:
        audio_queue.get()
        audio_queue.put(audio_chunk)
    
    # Display current chord and RGB values
    cv2.putText(frame, f"Chord: {base_note} {chord_type}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(frame, f"RGB: ({int(r)}, {int(g)}, {int(b)})", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(frame, f"Waveform: {waveform}", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    return frame

def process_video(video_source, note_duration):
    try:
        if isinstance(video_source, str):
            cap = cv2.VideoCapture(video_source)
        else:
            cap = video_source
        
        if not cap.isOpened():
            raise IOError(f"Cannot open video source")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_duration = 1 / fps if fps > 0 else 1/30
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_buffer.put(frame)
            if frame_buffer.full():
                frame_to_process = frame_buffer.get()
                processed_frame = process_frame(frame_to_process, note_duration)
                cv2.imshow('Video', processed_frame)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

            time.sleep(max(0, frame_duration - note_duration))

    except Exception as e:
        print(f"Error processing video: {e}")
    finally:
        if isinstance(video_source, str):
            cap.release()
        cv2.destroyAllWindows()

def select_video_source():
    root = tk.Tk()
    root.withdraw()

    choice = tk.messagebox.askquestion("Input Selection", "Do you want to use a webcam?")
    if choice == 'yes':
        return 0
    else:
        file_path = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4 *.avi *.mov")])
        return file_path if file_path else None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Video to Audio Processor with Chord Generation")
    parser.add_argument("--note_duration", type=float, default=0.1, help="Duration of each chord in seconds")
    args = parser.parse_args()

    video_source = select_video_source()
    if video_source is None:
        print("No video source selected. Exiting.")
        exit()

    audio_thread = threading.Thread(target=play_audio, daemon=True)
    audio_thread.start()

    process_video(video_source, args.note_duration)
    
      #python VideoToAudio3.py --note_duration 0.1