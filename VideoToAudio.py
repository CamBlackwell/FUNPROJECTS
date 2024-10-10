import cv2
import numpy as np
import pyaudio
import threading
import argparse
import queue
import time 
from scipy.io import wavfile

# Constants
CHUNK_SIZE = 1024
SAMPLE_RATE = 44100
BUFFER_SIZE = 10  # Number of audio chunks to buffer

# Global audio queue
audio_queue = queue.Queue(maxsize=BUFFER_SIZE)

def play_audio():
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paFloat32,
                    channels=1,
                    rate=SAMPLE_RATE,
                    output=True)
    
    while True:
        try:
            chunk = audio_queue.get()
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
    return cv2.mean(cv2.resize(frame, (50, 50)))[:3][::-1]  # Convert BGR to RGB

def generate_note(frequency, duration):
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), False)
    return np.sin(2 * np.pi * frequency * t)

def color_to_note(r, g, b):
    # Define a pentatonic scale
    scale = [261.63, 293.66, 329.63, 392.00, 440.00]  # C4, D4, E4, G4, A4
    
    # Use the average color to determine the note
    avg_color = (r + g + b) / 3
    note_index = int(avg_color / 255 * len(scale))
    return scale[note_index]

def process_video(video_path, note_duration):
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise IOError(f"Cannot open video file: {video_path}")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_duration = 1 / fps
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame = resize_frame(frame)
            r, g, b = get_average_color(frame)
            
            frequency = color_to_note(r, g, b)
            audio_chunk = generate_note(frequency, note_duration)
            
            try:
                audio_queue.put(audio_chunk, block=False)
            except queue.Full:
                # If queue is full, remove the oldest item and add the new one
                audio_queue.get()
                audio_queue.put(audio_chunk)

            cv2.imshow('Video', frame)
            if cv2.waitKey(int(frame_duration * 1000)) & 0xFF == ord('q'):
                break

            # Introduce a small delay to match video frame rate
            time.sleep(max(0, frame_duration - note_duration))

    except Exception as e:
        print(f"Error processing video: {e}")
    finally:
        if 'cap' in locals():
            cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Video to Audio Processor")
    parser.add_argument("video_path", help="Path to the input video file")
    parser.add_argument("--note_duration", type=float, default=0.1, help="Duration of each note in seconds")
    args = parser.parse_args()

    # Start audio playback thread
    audio_thread = threading.Thread(target=play_audio, daemon=True)
    audio_thread.start()

    # Process video
    process_video(args.video_path, args.note_duration)
    
    # to starts code type python script_name.py path/to/your/video.mp4 --note_duration 0.1
    #C:\Users\DB\Desktop\FunSideProjects\ShibuyaWalk.mp4
    # python VideoToAudio.py C:\Users\DB\Desktop\FunSideProjects\ShibuyaWalk.mp4 --note_duration 0.1