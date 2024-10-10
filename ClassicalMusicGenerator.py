import music21
import pygame
import tempfile
import os
import random

# Set the path to the MuseScore executable
us = music21.environment.UserSettings()
us['musicxmlPath'] = r'C:\Program Files\MuseScore 3\bin\MuseScore3.exe'  # Update this path

# Verify the path
print("MuseScore path:", us['musicxmlPath'])

# Function to generate a random classical piano piece using music21
def generate_random_midi():
    # Create streams for treble and bass clefs
    treble_stream = music21.stream.Part()
    bass_stream = music21.stream.Part()
    
    # Set clefs
    treble_stream.append(music21.clef.TrebleClef())
    bass_stream.append(music21.clef.BassClef())
    
    # Generate random notes for treble clef
    for _ in range(50):  # Adjust the number of notes as needed
        note = music21.note.Note()
        note.pitch.midi = random.randint(60, 72)  # Random pitch between C4 and C5
        note.quarterLength = random.choice([0.25, 0.5, 1.0, 2.0])  # Random duration
        treble_stream.append(note)
    
    # Generate random notes for bass clef
    for _ in range(50):  # Adjust the number of notes as needed
        note = music21.note.Note()
        note.pitch.midi = random.randint(36, 48)  # Random pitch between C2 and C3
        note.quarterLength = random.choice([0.25, 0.5, 1.0, 2.0])  # Random duration
        bass_stream.append(note)
    
    # Combine treble and bass streams into a single stream
    combined_stream = music21.stream.Score()
    combined_stream.append(treble_stream)
    combined_stream.append(bass_stream)
    
    return combined_stream

# Function to display the sheet music
def display_sheet_music(piece):
    piece.show('musicxml')

# Function to play the MIDI file
def play_midi(piece):
    # Create a temporary MIDI file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mid") as temp_midi:
        temp_midi_path = temp_midi.name
        piece.write('midi', fp=temp_midi_path)
    
    # Initialize pygame mixer
    pygame.mixer.init()
    
    # Load and play the MIDI file
    pygame.mixer.music.load(temp_midi_path)
    pygame.mixer.music.play()
    
    # Wait for the music to finish playing
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)
    
    # Clean up the temporary file
    os.remove(temp_midi_path)

# Generate a random MIDI piece
piece = generate_random_midi()

# Display the sheet music
display_sheet_music(piece)

# Play the MIDI file
play_midi(piece)
