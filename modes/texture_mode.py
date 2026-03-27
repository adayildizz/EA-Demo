"""
Texture Simulation Mode for the Haptic System.

This module splits the screen into two interactive zones: Sand (Left) and Metal (Right).
It allows the user to click and drag a box across these virtual surfaces. The haptic 
feedback changes based on which box is being dragged to simulate the distinct textures 
of rough sand and a segmented metal grid.
"""

import pygame
import random
from core.settings import *

class TextureMode:
    """
    Manages the logic and visual representation of the Texture simulation mode.
    
    This class handles the creation of draggable boxes, collision detection, 
    and the dynamic generation of haptic parameters (frequency and voltage) 
    designed to mimic specific physical textures.
    """
    def __init__(self):
        # Define the size of the interactive draggable boxes
        box_size = 150
        
        # Initialize the Sand box on the left side of the screen
        self.box_sand = pygame.Rect(WIDTH * 0.25 - box_size//2, HEIGHT//2 - box_size//2, box_size, box_size)
        
        # Initialize the Metal box on the right side of the screen
        self.box_metal = pygame.Rect(WIDTH * 0.75 - box_size//2, HEIGHT//2 - box_size//2, box_size, box_size)
        
        # State flags to track if a specific box is currently being dragged
        self.dragging_sand = False
        self.dragging_metal = False
        
        # Offset variables to keep the box grabbed exactly where the user clicked it, 
        # rather than snapping the box's top-left corner to the cursor.
        self.offset_x = 0
        self.offset_y = 0
        
        # Pre-generate 200 random dot coordinates for the visual sand texture background
        self.sand_dots = [(random.randint(0, WIDTH // 2), random.randint(0, HEIGHT)) for _ in range(200)]
        
        self.prev_finger_pos = (0, 0)
        
        # --- Font Definitions ---
        # Fonts for on-screen instructions and labels
        self.font_instr = pygame.font.SysFont("Arial", 40, bold=True)
        self.font_label = pygame.font.SysFont("Arial", 30, bold=True)

    def update(self, finger_pos, current_time):
        """
        Processes touch input to drag boxes and calculates texture-specific haptic signals.
        
        Args:
            finger_pos (tuple/None): (x, y) coordinates of the current touch.
            current_time (int): Elapsed time in milliseconds (unused in this mode, but required by interface).
            
        Returns:
            tuple: (Waveform type, Frequency, Voltage) to be sent to hardware.
        """
        # Default target values assuming no interaction
        target_wave = WAVE_SQUARE
        target_freq = CARRIER_FREQ
        target_volt = MIN_VOLTAGE
        
        # If there is no touch input, drop any currently held boxes and return minimum voltage
        if not finger_pos:
            self.dragging_sand = False
            self.dragging_metal = False
            # Note: Returning a tuple with 125 frequency directly here as a hardcoded 
            # safety fallback, though it effectively matches CARRIER_FREQ.
            return (WAVE_SQUARE, 125, MIN_VOLTAGE)

        # --- Box Grabbing Logic ---
        # If we aren't already dragging a box, check if the touch lands inside one of them
        if not self.dragging_sand and not self.dragging_metal:
            if self.box_sand.collidepoint(finger_pos):
                self.dragging_sand = True
                # Calculate the offset between the touch point and the box's top-left corner
                self.offset_x = finger_pos[0] - self.box_sand.x
                self.offset_y = finger_pos[1] - self.box_sand.y
            elif self.box_metal.collidepoint(finger_pos):
                self.dragging_metal = True
                self.offset_x = finger_pos[0] - self.box_metal.x
                self.offset_y = finger_pos[1] - self.box_metal.y

        # --- SAND TEXTURE (LEFT) - RANDOM LOW FREQUENCY ---
        if self.dragging_sand:
            # Update the box position based on the finger position minus the initial offset
            self.box_sand.x = finger_pos[0] - self.offset_x
            self.box_sand.y = finger_pos[1] - self.offset_y
            
            target_wave = WAVE_SQUARE
            # Rapidly shift between slightly different lower frequencies to create 
            # a chaotic, "gritty" feeling characteristic of sand.
            target_freq = random.choice([30, 40, 50, 60])
            # Keep voltage relatively high for strong feedback
            target_volt = random.uniform(3.5, 4.0) 

        # --- METAL TEXTURE (RIGHT) - CONSTANT VERY LOW FREQUENCY ---
        elif self.dragging_metal:
            self.box_metal.x = finger_pos[0] - self.offset_x
            self.box_metal.y = finger_pos[1] - self.offset_y
            
            target_wave = WAVE_SQUARE
            # Very low frequency (2Hz) paired with Maximum Voltage (4V).
            # This will create a very sharp, distinct "thud-thud-thud" impact feeling, 
            # simulating dragging an object across heavy metal grating.
            target_freq = 2
            target_volt = 4.0

        return (target_wave, target_freq, target_volt)

    def draw(self, screen, finger_pos):
        """
        Renders the split-screen backgrounds, the interactive boxes, and the UI text.
        
        Args:
            screen (pygame.Surface): The main display surface.
            finger_pos (tuple/None): The current touch coordinates.
        """
        # --- Draw Left Side (Sand) ---
        pygame.draw.rect(screen, COLOR_SAND_BG, (0, 0, WIDTH//2, HEIGHT))
        # Draw the pre-generated dots to create a visual texture
        for dot in self.sand_dots:
            pygame.draw.circle(screen, COLOR_SAND_DOTS, dot, 2)
        # Draw the draggable sand box
        pygame.draw.rect(screen, COLOR_BOX_SAND, self.box_sand)
        
        # --- Draw Right Side (Metal Grating) ---
        pygame.draw.rect(screen, COLOR_METAL_BG, (WIDTH//2, 0, WIDTH//2, HEIGHT))
        # Draw vertical grid lines
        for x in range(WIDTH // 2, WIDTH, 40):
            pygame.draw.line(screen, COLOR_METAL_GRID, (x, 0), (x, HEIGHT), 2)
        # Draw horizontal grid lines
        for y in range(0, HEIGHT, 40):
            pygame.draw.line(screen, COLOR_METAL_GRID, (WIDTH // 2, y), (WIDTH, y), 2)
        # Draw the draggable metal box
        pygame.draw.rect(screen, COLOR_BOX_METAL, self.box_metal)
        
        # Draw a thick black dividing line down the exact center of the screen
        pygame.draw.line(screen, COLOR_BLACK, (WIDTH // 2, 0), (WIDTH // 2, HEIGHT), 5)
        
        # --- TEXT RENDERING ---
        # Top Instruction Text
        text_instr = self.font_instr.render("Please drag the boxes to feel the different surfaces.", True, COLOR_BLACK)
        
        # Create a semi-transparent background box behind the instruction text to ensure readability
        bg_rect = text_instr.get_rect(center=(WIDTH // 2, 100))
        bg_rect.inflate_ip(20, 20) # Inflate the rect slightly for padding
        
        # A separate surface is required to draw shapes with alpha transparency
        bg_surface = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
        bg_surface.fill((255, 255, 255, 180)) # Semi-transparent white
        
        # Blit the background, then blit the text over it
        screen.blit(bg_surface, bg_rect)
        screen.blit(text_instr, text_instr.get_rect(center=(WIDTH // 2, 100)))

        # Box Labels
        label_sand = self.font_label.render("Sand (Rough)", True, COLOR_WHITE)
        screen.blit(label_sand, label_sand.get_rect(center=(WIDTH * 0.25, HEIGHT - 100)))
        
        label_metal = self.font_label.render("Metal (Impact)", True, COLOR_WHITE)
        screen.blit(label_metal, label_metal.get_rect(center=(WIDTH * 0.75, HEIGHT - 100)))
        
        # Draw a white circle to visually represent where the user is touching
        if finger_pos:
            pygame.draw.circle(screen, (255, 255, 255), finger_pos, 20)