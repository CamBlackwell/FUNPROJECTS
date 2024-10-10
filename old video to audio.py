import cv2
import numpy as np
import simpleaudio as sa
import time
import threading

# Function to play audio in a separate thread
def play_audio(audio_data):
    try:
        play_obj = sa.play_buffer(audio_data, 1, 2, 44100)
        play_obj.wait_done()
    except Exception as e:
        print("Error playing audio:", e)

# Function to resize frames for faster processing
def resize_frame(frame, max_size=500):
    height, width, _ = frame.shape
    scale = max_size / max(height, width)
    return cv2.resize(frame, (int(width * scale), int(height * scale)))

def get_average_color(frame):
    # Resize the frame to 50x50 for faster processing
    frame = cv2.resize(frame, (50, 50))
    avg_color = cv2.mean(frame)[:3][::-1]  # Convert BGR to RGB
    return avg_color

def generate_waveform(t, frequency, waveform_type):
    if waveform_type == 'sine':
        return np.sin(2 * np.pi * frequency * t)
    elif waveform_type == 'square':
        return np.sign(np.sin(2 * np.pi * frequency * t))
    elif waveform_type == 'sawtooth':
        return 2 * (frequency * t - np.floor(0.5 + frequency * t))
    else:  # triangle
        return 2 * np.abs(2 * (frequency * t - np.floor(0.5 + frequency * t))) - 1

def generate_note(root_freq, duration, sample_rate=44100):
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    note = np.sin(2 * np.pi * root_freq * t)
    note = np.int16(note / np.max(np.abs(note)) * 32767)
    return note

def process_video(video_path):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)

    note_duration = 0.3  # Duration of each note in seconds

    while True:
        try:
            ret, frame = cap.read()
            if not ret:
                break

            # Resize frame for faster processing
            frame = resize_frame(frame)

            # Get average color
            r, g, b = get_average_color(frame)
            avg_color = (r + g + b) / 3

            # Print debugging info
            print(f"Frame shape: {frame.shape}, Average color: {avg_color}")

            # If the frame is primarily black, play a single sine wave
            if avg_color < 50:
                # Generate a random note between C4 and B4
                root_freq = 261.63 * (2 ** ((np.random.randint(0, 12) - 3) / 12))
                new_audio = generate_note(root_freq, note_duration)

                # Create and start a thread for audio playback
                audio_thread = threading.Thread(target=play_audio, args=(new_audio,))
                audio_thread.start()

            # Determine root note (based on blue value)
            root_freq = 220 + (b / 255) * 440

            # Generate audio data
            new_audio = generate_note(root_freq, note_duration)

            # Create and start a thread for audio playback
            audio_thread = threading.Thread(target=play_audio, args=(new_audio,))
            audio_thread.start()

            # Display the frame
            cv2.imshow('Video', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        except Exception as e:
            print("Error processing video:", e)

    cap.release()
    cv2.destroyAllWindows()
# Main execution
process_video(r"C:\Users\DB\Desktop\FunSideProjects\ShibuyaWalk.mp4")