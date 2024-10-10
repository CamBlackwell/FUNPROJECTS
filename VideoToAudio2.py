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
BUFFER_SIZE = 20  # Increased buffer size to reduce stuttering
FRAME_BUFFER_SIZE = 5  # Number of frames to buffer for smoother processing

# Global audio queue
audio_queue = queue.Queue(maxsize=BUFFER_SIZE)
frame_buffer = queue.Queue(maxsize=FRAME_BUFFER_SIZE)

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

def color_to_note(r, g, b):
    # Define a pentatonic scale
    scale = [261.63, 293.66, 329.63, 392.00, 440.00]  # C4, D4, E4, G4, A4
    
    # Use individual color channels to determine the note and waveform
    note_index = int((r + g + b) / (3 * 255) * len(scale))
    frequency = scale[note_index]
    
    # Choose waveform based on dominant color
    if r > g and r > b:
        waveform = 'sine'
    elif g > r and g > b:
        waveform = 'square'
    else:
        waveform = 'sawtooth'
    
    return frequency, waveform

def process_frame(frame, note_duration):
    frame = resize_frame(frame)
    r, g, b = get_average_color(frame)
    
    frequency, waveform = color_to_note(r, g, b)
    audio_chunk = generate_note(frequency, note_duration, waveform)
    
    try:
        audio_queue.put(audio_chunk, block=False)
    except queue.Full:
        # If queue is full, remove the oldest item and add the new one
        audio_queue.get()
        audio_queue.put(audio_chunk)
    
    # Display current note and RGB values
    cv2.putText(frame, f"Note: {frequency:.2f}Hz", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(frame, f"RGB: ({int(r)}, {int(g)}, {int(b)})", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
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

            # Introduce a small delay to match video frame rate
            time.sleep(max(0, frame_duration - note_duration))

    except Exception as e:
        print(f"Error processing video: {e}")
    finally:
        if isinstance(video_source, str):
            cap.release()
        cv2.destroyAllWindows()

def select_video_source():
    root = tk.Tk()
    root.withdraw()  # Hide the main window

    choice = tk.messagebox.askquestion("Input Selection", "Do you want to use a webcam?")
    if choice == 'yes':
        return 0  # Use default webcam
    else:
        file_path = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4 *.avi *.mov")])
        return file_path if file_path else None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Video to Audio Processor")
    parser.add_argument("--note_duration", type=float, default=0.1, help="Duration of each note in seconds")
    args = parser.parse_args()

    video_source = select_video_source()
    if video_source is None:
        print("No video source selected. Exiting.")
        exit()

    # Start audio playback thread
    audio_thread = threading.Thread(target=play_audio, daemon=True)
    audio_thread.start()

    # Process video
    process_video(video_source, args.note_duration)
    
    #python VideoToAudio2.py --note_duration 0.1