import cv2
import threading
import pygame.midi
import time
import numpy as np
from cvzone.HandTrackingModule import HandDetector

# 🎹 Initialize Pygame MIDI
pygame.midi.init()
player = pygame.midi.Output(0)
player.set_instrument(0)  # 0 = Acoustic Grand Piano

# 🎐 Initialize Hand Detector
cap = cv2.VideoCapture(0)
detector = HandDetector(detectionCon=0.8)

# 🎺 Chord Mapping for Fingers (D Major Scale)
chords = {
    "left": {
        "thumb": [62, 66, 69],   # D Major (D, F#, A)
        "index": [64, 67, 71],   # E Minor (E, G, B)
        "middle": [66, 69, 73],  # F# Minor (F#, A, C#)
        "ring": [67, 71, 74],    # G Major (G, B, D)
        "pinky": [69, 73, 76]    # A Major (A, C#, E)
    },
    "right": {
        "thumb": [62, 66, 69],   # D Major (D, F#, A)
        "index": [64, 67, 71],   # E Minor (E, G, B)
        "middle": [66, 69, 73],  # F# Minor (F#, A, C#)
        "ring": [67, 71, 74],    # G Major (G, B, D)
        "pinky": [69, 73, 76]    # A Major (A, C#, E)
    }
}

# Sustain Time (in seconds) after the finger is lowered
SUSTAIN_TIME = 2.0

# Track Previous States to Stop Chords
prev_states = {hand: {finger: 0 for finger in chords[hand]} for hand in chords}

# 🎵 Function to Play a Chord
def play_chord(chord_notes):
    for note in chord_notes:
        player.note_on(note, 127)  # Start playing

# 🎵 Function to Stop a Chord After a Delay
def stop_chord_after_delay(chord_notes):
    time.sleep(SUSTAIN_TIME)  # Sustain for specified time
    for note in chord_notes:
        player.note_off(note, 127)  # Stop playing

# 🎹 Function to Draw Virtual Piano and Highlight Notes
def draw_virtual_piano(img, active_notes):
    height, width, _ = img.shape  # Get the dimensions of the camera frame
    piano_height = 200  # Fixed height for the piano
    piano_width = width  # Match the width of the camera frame dynamically
    piano_img = np.zeros((piano_height, piano_width, 3), dtype=np.uint8)
    key_width = piano_width // 14  # Adjust key width based on the frame width

    # Draw white keys
    for i in range(14):
        x = i * key_width
        color = (255, 255, 255)
        if 60 + i in active_notes:  # Highlight active notes
            color = (0, 255, 0)
        cv2.rectangle(piano_img, (x, 0), (x + key_width, piano_height), color, -1)
        cv2.rectangle(piano_img, (x, 0), (x + key_width, piano_height), (0, 0, 0), 2)

    # Draw black keys
    black_key_offsets = [1, 3, 6, 8, 10]  # Black key positions in an octave
    for i in range(2):  # Two octaves
        for offset in black_key_offsets:
            x = (i * 7 + offset) * key_width - key_width // 4
            if 61 + i * 12 + offset in active_notes:  # Highlight active notes
                color = (0, 255, 0)
            else:
                color = (0, 0, 0)
            cv2.rectangle(piano_img, (x, 0), (x + key_width // 2, piano_height // 2), color, -1)
            cv2.rectangle(piano_img, (x, 0), (x + key_width // 2, piano_height // 2), (255, 255, 255), 1)

    # Combine piano image with main frame
    img[-piano_height:, :piano_width] = piano_img
    return img

while True:
    success, img = cap.read()
    if not success:
        print("❌ Camera not capturing frames")
        continue

    hands, img = detector.findHands(img, draw=True)
    active_notes = []  # Track active notes for visual feedback

    if hands:
        for hand in hands:
            hand_type = "left" if hand["type"] == "Left" else "right"
            fingers = detector.fingersUp(hand)
            finger_names = ["thumb", "index", "middle", "ring", "pinky"]

            for i, finger in enumerate(finger_names):
                if finger in chords[hand_type]:  # Only check assigned chords
                    if fingers[i] == 1 and prev_states[hand_type][finger] == 0:
                        play_chord(chords[hand_type][finger])  # Play chord
                        active_notes.extend(chords[hand_type][finger])  # Add to active notes
                    elif fingers[i] == 0 and prev_states[hand_type][finger] == 1:
                        threading.Thread(target=stop_chord_after_delay, args=(chords[hand_type][finger],), daemon=True).start()
                    prev_states[hand_type][finger] = fingers[i]  # Update state
    else:
        # If no hands detected, stop all chords after delay
        for hand in chords:
            for finger in chords[hand]:
                threading.Thread(target=stop_chord_after_delay, args=(chords[hand][finger],), daemon=True).start()
        prev_states = {hand: {finger: 0 for finger in chords[hand]} for hand in chords}

    # Draw virtual piano and highlight active notes
    img = draw_virtual_piano(img, active_notes)

    # Display chord names
    if active_notes:
        chord_name = " + ".join([f"Note {note}" for note in active_notes])
        cv2.putText(img, f"Playing: {chord_name}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    cv2.imshow("Hand Tracking MIDI Chords", img)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
pygame.midi.quit()
