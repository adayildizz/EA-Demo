"""
Main entry point for the Haptic System application.

This script initializes the Pygame environment, sets up the main display window,
and manages the primary application loop. It handles switching between different 
haptic feedback modes (Heart, Texture, and Train), captures user input (mouse/finger position), 
calculates the corresponding haptic signals, and communicates these signals to the hardware 
via the HapticController.
"""

import pygame
import os
import sys
from core.settings import *
from core.haptics import HapticController
from modes.heart_mode import HeartMode
from modes.train_mode import TrainMode
from modes.texture_mode import TextureMode
from modes.pie_mode import PieMode

# Position the Pygame window on the screen using coordinates defined in settings.py.
# Note: X_KOORDINATI and Y_KOORDINATI are Turkish for X_COORDINATE and Y_COORDINATE.
os.environ['SDL_VIDEO_WINDOW_POS'] = f"{X_KOORDINATI},{Y_KOORDINATI}"

# Initialize all imported pygame modules
pygame.init()

# Set up the display window. NOFRAME is used to remove standard window borders.
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.NOFRAME)
pygame.display.set_caption("Haptic System Main")

# Initialize the hardware controller responsible for sending haptic signals
haptics = HapticController()

# Initialize the different interaction modes for the haptic system
mode_heart = HeartMode()
mode_texture = TextureMode()
mode_train = TrainMode()
mode_pie = PieMode()

# Set the default application state to Heart Mode
current_mode = mode_heart
mode_name = "HEART"

# Flag to control the main application loop
running = True

# Create a clock object to track and control the framerate
clock = pygame.time.Clock()

# Log the successful initialization of the system and display the maximum allowed voltage
print(f"System Initialized. MAX VOLTAGE: {MAX_VOLTAGE}V")

while running:
    # Get the current time in milliseconds since pygame.init() was called
    current_time = pygame.time.get_ticks()
    
    # Initialize finger position as None for the current frame
    finger_pos = None
    
    # --- EVENT HANDLING ---
    events = pygame.event.get()
    for event in events:
        # Handle window close events
        if event.type == pygame.QUIT: 
            running = False
            
        # Handle keyboard input events
        elif event.type == pygame.KEYDOWN:
            # Pressing ESCAPE exits the application
            if event.key == pygame.K_ESCAPE: 
                running = False
                
            # Pressing RETURN (Enter) cycles through the available haptic modes
            elif event.key == pygame.K_RETURN:
                if mode_name == "HEART":
                    current_mode = mode_texture
                    mode_name = "TEXTURE"
                elif mode_name == "TEXTURE":
                    current_mode = mode_train
                    mode_name = "TRAIN"
                elif mode_name == "TRAIN":
                    current_mode = mode_pie
                    mode_name = "PIE"
                else:
                    current_mode = mode_heart
                    mode_name = "HEART"
                
                # Log the active mode change to the console
                print(f"Mode: {mode_name}")

    # --- INPUT PROCESSING ---
    # Get the current mouse pointer coordinates
    mouse_x, mouse_y = pygame.mouse.get_pos()
    
    # Check if the left mouse button is being pressed (acting as a simulated finger touch)
    if pygame.mouse.get_pressed()[0]: 
        # Normalize the coordinates to a 0.0 - 1.0 scale based on screen dimensions
        raw_x = mouse_x / WIDTH
        raw_y = mouse_y / HEIGHT
        
        # Apply inversion flags if set in settings.py 
        # (useful if the physical touch screen orientation is flipped)
        if INVERT_X: 
            raw_x = 1.0 - raw_x
        if INVERT_Y: 
            raw_y = 1.0 - raw_y
            
        # Convert the normalized coordinates back to absolute pixel integer values
        finger_pos = (int(raw_x * WIDTH), int(raw_y * HEIGHT))

    # --- SIGNAL UPDATE ---
    # Calculate the waveform, frequency, and voltage from the active mode
    # based on the user's current finger position and elapsed time.
    wave, freq, volt = current_mode.update(finger_pos, current_time)
    
    # Send the calculated haptic parameters to the hardware controller
    haptics.update_signal(wave, freq, volt)

    # --- RENDERING ---
    # Render the visual elements for the current mode onto the screen
    current_mode.draw(screen, finger_pos)
    
    # Push the updated display surface to the actual screen
    pygame.display.flip()
    
    # Cap the application framerate at 60 frames per second
    clock.tick(60)

# --- CLEANUP ---
# Safely close the hardware connection and terminate Pygame when the loop exits
haptics.close()
pygame.quit()
sys.exit()