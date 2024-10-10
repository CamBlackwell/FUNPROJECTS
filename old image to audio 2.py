import cv2
import numpy as np
import simpleaudio as sa
import time

def get_average_color(image_path):
    img = cv2.imread(image_path)
    img = cv2.resize(img, (50, 50))  # Resize to 50x50 for faster processing
    avg_color = cv2.mean(img)[:3][::-1]  # Convert BGR to RGB
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

def generate_chord(root_freq, is_major, waveform_type, extension, octaves, duration=1, sample_rate=44100):
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    
    # Generate frequencies for root, third, fifth, and bass
    frequencies = [
        root_freq / 4,  # Bass note (2 octaves below)
        root_freq,
        root_freq * (5/4 if is_major else 6/5),
        root_freq * 3/2
    ]
    
    # Add extension if applicable
    if extension == '9th':
        frequencies.append(root_freq * 9/8)
    elif extension == '13th':
        frequencies.append(root_freq * 13/8)
    
    # Generate chord with multiple octaves
    chord = sum(
        generate_waveform(t, freq * (2**octave), waveform_type)
        for freq in frequencies
        for octave in range(octaves)
    )
    
    # Normalize and convert to 16-bit PCM
    chord = np.int16(chord / np.max(np.abs(chord)) * 32767)
    return chord

def generate_melody(root_freq, scale, duration=1, sample_rate=44100):
    t = np.linspace(0, duration / 3, int(sample_rate * duration / 3), False)
    melody = np.concatenate([
        generate_waveform(t, root_freq * interval, 'sine')
        for interval in scale
    ])
    return np.int16(melody / np.max(np.abs(melody)) * 32767)

def play_color_chord(image_path):
    start_time = time.time()
    
    # Get average color
    r, g, b = get_average_color(image_path)
    print(f"Average color: R:{r:.0f}, G:{g:.0f}, B:{b:.0f}")
    
    # Determine chord type (major/minor)
    is_major = g > 127
    chord_type = "major" if is_major else "minor"
    
    # Determine root note (based on blue value)
    root_freq = 220 + (b / 255) * 440  # Map blue to frequency range 220-660 Hz
    
    # Determine waveform type (based on red value)
    waveform_types = ['sine', 'square', 'sawtooth', 'triangle']
    waveform_type = waveform_types[int(r / 64)]  # Divide red value into 4 ranges
    
    # Determine chord extension (based on green/blue ratio)
    gb_ratio = g / b if b > 0 else 0
    extension = '13th' if gb_ratio > 1.2 else '9th' if gb_ratio > 0.8 else None
    
    # Determine number of octaves (based on red/green ratio)
    rg_ratio = r / g if g > 0 else 0
    octaves = min(3, max(1, int(rg_ratio * 3)))
    
    # Determine melody scale (based on red/blue ratio)
    rb_ratio = r / b if b > 0 else 0
    if is_major:
        scales = [[1, 9/8, 5/4], [1, 5/4, 3/2], [1, 3/2, 15/8]]
    else:
        scales = [[1, 6/5, 3/2], [1, 3/2, 9/5], [1, 9/5, 2]]
    scale = scales[min(2, int(rb_ratio * 3))]
    
    print(f"Generating {chord_type} chord with root {root_freq:.2f} Hz")
    print(f"Using {waveform_type} waveform, {extension or 'no'} extension, {octaves} octaves")
    print(f"Melody scale: {scale}")
    
    # Generate and play chord
    chord = generate_chord(root_freq, is_major, waveform_type, extension, octaves)
    melody = generate_melody(root_freq, scale)
    audio = np.concatenate([chord, melody])
    
    play_obj = sa.play_buffer(audio, 1, 2, 44100)
    play_obj.wait_done()
    
    end_time = time.time()
    print(f"Total execution time: {end_time - start_time:.3f} seconds")

# Main execution
image_path = r"C:\Users\DB\Desktop\FunSideProjects\dog.jpeg"
#image_path = r"C:\Users\DB\Desktop\FunSideProjects\dog2.jpg"
play_color_chord(image_path) 