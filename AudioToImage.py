import numpy as np
import matplotlib.pyplot as plt
import simpleaudio as sa
import tkinter as tk
from tkinter import ttk

# Function to generate a random audio tone
def generate_random_tone(duration_ms=1000, sample_rate=44100):
    # Generate a random frequency between 200 Hz and 2000 Hz
    frequency = np.random.uniform(200, 2000)
    
    # Generate the time axis
    t = np.linspace(0, duration_ms / 1000, int(sample_rate * duration_ms / 1000), endpoint=False)
    
    # Generate the audio signal
    audio_signal = 0.5 * np.sin(2 * np.pi * frequency * t)
    
    # Convert the audio signal to 16-bit PCM format
    audio_signal = np.int16(audio_signal * 32767)
    
    return audio_signal, sample_rate

# Function to mix multiple audio signals
def mix_audio_signals(signals):
    mixed_signal = np.sum(signals, axis=0)
    # Normalize the mixed signal to prevent clipping
    mixed_signal = mixed_signal / np.max(np.abs(mixed_signal))
    mixed_signal = np.int16(mixed_signal * 32767)
    return mixed_signal

# Function to generate and display the spectrogram
def generate_and_display_spectrogram():
    num_tones = 5
    duration_ms = 1000
    sample_rate = 44100
    signals = []
    
    for _ in range(num_tones):
        audio_signal, _ = generate_random_tone(duration_ms, sample_rate)
        signals.append(audio_signal)
    
    # Mix the audio signals
    mixed_signal = mix_audio_signals(signals)
    
    # Play the mixed audio signal
    play_obj = sa.play_buffer(mixed_signal, 1, 2, sample_rate)
    play_obj.wait_done()
    
    # Create a spectrogram
    plt.figure(figsize=(12, 6))
    plt.specgram(mixed_signal, Fs=sample_rate, NFFT=1024, noverlap=512, cmap='viridis')
    plt.title("Spectrogram of Mixed Audio Signal")
    plt.xlabel("Time (s)")
    plt.ylabel("Frequency (Hz)")
    plt.colorbar(label="Intensity (dB)")
    plt.show()

# Create the main window
root = tk.Tk()
root.title("Audio to Image Generator")

# Create a button to generate a new audio-to-image visualization
generate_button = ttk.Button(root, text="Generate New Audio to Image", command=generate_and_display_spectrogram)
generate_button.pack(pady=20)

# Run the application
root.mainloop()
