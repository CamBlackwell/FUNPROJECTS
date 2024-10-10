import cv2
import numpy as np
import threading
import argparse
import time
from pythonosc import udp_client
import subprocess
import atexit

# Constants
SAMPLE_RATE = 44100

# Global variables
osc_client = None
sc_server_process = None

def start_supercollider_server():
    global sc_server_process
    sc_server_process = subprocess.Popen(["scsynth", "-u", "57110"])
    time.sleep(2)  # Give some time for the server to start

def stop_supercollider_server():
    global sc_server_process
    if sc_server_process:
        sc_server_process.terminate()
        sc_server_process.wait()

atexit.register(stop_supercollider_server)

def setup_supercollider():
    global osc_client
    start_supercollider_server()
    osc_client = udp_client.SimpleUDPClient("127.0.0.1", 57110)
    
    # Define a simple synth
    synth_def = """
    SynthDef(\colorTone, { |freq = 440, amp = 0.1, gate = 1|
        var sig, env;
        env = EnvGen.kr(Env.adsr(0.01, 0.1, 0.5, 0.1), gate, doneAction: 2);
        sig = SinOsc.ar(freq) * env * amp;
        Out.ar(0, sig ! 2);
    }).add;
    """
    
    osc_client.send_message("/d_recv", [synth_def])

def play_note(freq, duration):
    global osc_client
    synth_id = int(time.time() * 1000) % 1000000  # Generate a unique ID
    osc_client.send_message("/s_new", ["colorTone", synth_id, 0, 0, "freq", freq])
    threading.Timer(duration, stop_note, [synth_id]).start()

def stop_note(synth_id):
    global osc_client
    osc_client.send_message("/n_set", [synth_id, "gate", 0])

def resize_frame(frame, max_size=500):
    height, width = frame.shape[:2]
    scale = max_size / max(height, width)
    return cv2.resize(frame, (int(width * scale), int(height * scale)))

def get_average_color(frame):
    return cv2.mean(cv2.resize(frame, (50, 50)))[:3][::-1]  # Convert BGR to RGB

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
            play_note(frequency, note_duration)

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
    parser = argparse.ArgumentParser(description="Video to Audio Processor using SuperCollider")
    parser.add_argument("video_path", help="Path to the input video file")
    parser.add_argument("--note_duration", type=float, default=0.1, help="Duration of each note in seconds")
    args = parser.parse_args()
    
    setup_supercollider()

    # Process video
    process_video(args.video_path, args.note_duration)