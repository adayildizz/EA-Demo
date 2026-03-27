"""
Train Acceleration Simulation Mode for the Haptic System.

This module simulates the sensation of a train slowly starting and then 
accelerating up to a high speed. It features a 3D perspective visual of 
train tracks and uses an exponential curve to increase both the visual 
speed of the passing railway sleepers and the haptic frequency.
"""

import pygame
import math
from core.settings import *

class TrainMode:
    """
    Manages the logic and visual representation of the Train simulation mode.
    
    This class creates a looping 20-second animation. As the loop progresses, 
    the haptic frequency and visual rendering speed increase exponentially to 
    simulate the heavy, gathering momentum of a train.
    """
    def __init__(self):
        # Record the exact time the mode is initialized to manage the 20-second cycle
        self.start_time = pygame.time.get_ticks()
        self.duration = 20000 # 20 second loop duration in milliseconds
        
        # Initialize an array of railway sleepers (ties) distributed from 0.0 to 1.0.
        # These values represent their position along the track (0 = horizon, 1 = bottom of screen).
        self.sleepers = [i / 20.0 for i in range(20)] 
        
        self.current_freq = 1.0 
        self.speed_factor = 0.0
        
        # --- Font Definitions ---
        self.font_instr = pygame.font.SysFont("Arial", 40, bold=True)
        self.font_info = pygame.font.SysFont("Arial", 30)

    def update(self, finger_pos, current_time):
        """
        Calculates the haptic frequency and updates the visual animation state.
        
        Args:
            finger_pos (tuple/None): (x, y) coordinates of the current touch.
            current_time (int): Elapsed time in milliseconds.
            
        Returns:
            tuple: (Waveform type, Frequency, Voltage) to be sent to hardware.
        """
        # Calculate the loop time (progress will be a float between 0.0 and 1.0)
        cycle_time = (current_time - self.start_time) % self.duration
        progress = cycle_time / self.duration 
        
        # --- LOGARITHMIC / EXPONENTIAL ACCELERATION LOGIC ---
        # A power of 4 curve (progress^4) creates a movement that starts very slow 
        # and then accelerates sharply toward the end of the loop, mimicking heavy momentum.
        self.speed_factor = math.pow(progress, 4)
        
        # Frequency: Scale between 1 Hz (starting) and 200 Hz (max speed)
        target_freq = 1 + (199 * self.speed_factor)
        self.current_freq = target_freq
        
        # Calculate how fast the railway sleepers should visually move down the screen
        move_speed = 0.001 + (0.03 * self.speed_factor)
        
        # Update the position of each visual sleeper on the track
        for i in range(len(self.sleepers)):
            self.sleepers[i] += move_speed
            # If a sleeper passes the bottom of the screen (> 1.0), loop it back to the horizon (0.0)
            if self.sleepers[i] > 1.0:
                self.sleepers[i] -= 1.0
        
        # --- VOLTAGE SETTING ---
        # Request: Train voltage should be constant at 4.0V when touched, to represent 
        # a heavy, powerful, and consistent force regardless of the frequency.
        target_volt = MIN_VOLTAGE
        if finger_pos:
            target_volt = 4.0
            
        return (WAVE_SQUARE, target_freq, target_volt)

    def draw(self, screen, finger_pos):
        """
        Renders the 3D perspective of the train tracks, sky, ground, and text.
        
        Args:
            screen (pygame.Surface): The main display surface.
            finger_pos (tuple/None): The current touch coordinates.
        """
        horizon_y = HEIGHT // 2
        
        # Draw Sky (top half) and Ground (bottom half)
        pygame.draw.rect(screen, COLOR_SKY, (0, 0, WIDTH, horizon_y))
        pygame.draw.rect(screen, COLOR_GROUND, (0, horizon_y, WIDTH, HEIGHT - horizon_y))
        
        # --- Draw 3D Perspective Tracks ---
        center_x = WIDTH // 2
        bottom_width = 800  # Track width at the bottom of the screen (closest to viewer)
        top_width = 20      # Track width at the horizon (furthest from viewer)
        
        # Define the 4 points for the two main rails
        p1 = (center_x - top_width, horizon_y)
        p2 = (center_x - bottom_width, HEIGHT)
        p3 = (center_x + bottom_width, HEIGHT)
        p4 = (center_x + top_width, horizon_y)
        
        # Draw the main rails
        pygame.draw.line(screen, COLOR_RAIL, p1, p2, 5)
        pygame.draw.line(screen, COLOR_RAIL, p4, p3, 5)
        
        # Draw the moving railway sleepers (ties)
        for pos_factor in self.sleepers:
            # Square the position factor to create a faux 3D perspective depth effect
            # (sleepers appear to move faster and get larger as they get closer to the bottom)
            visual_y_factor = pos_factor * pos_factor 
            
            draw_y = horizon_y + (visual_y_factor * (HEIGHT - horizon_y))
            current_width = top_width + (visual_y_factor * (bottom_width - top_width)) * 2
            
            rect_x = center_x - (current_width // 2)
            rect_h = 2 + (20 * visual_y_factor)
            
            pygame.draw.rect(screen, COLOR_SLEEPER, (rect_x, draw_y, current_width, rect_h))

        # --- TEXT RENDERING ---
        # Main Instruction (Circular Movement)
        text_instr = self.font_instr.render("Please perform circular movements on the tracks.", True, COLOR_WHITE)
        
        # Let's add a semi-transparent background behind the text for readability against the tracks
        bg_rect = text_instr.get_rect(center=(WIDTH // 2, 150))
        bg_rect.inflate_ip(40, 20)
        
        bg_surface = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
        bg_surface.fill(COLOR_TEXT_BG) # Uses semi-transparent black setting from settings.py
        screen.blit(bg_surface, bg_rect)
        screen.blit(text_instr, text_instr.get_rect(center=(WIDTH // 2, 150)))

        # Frequency Info (Top left corner)
        freq_text = self.font_info.render(f"Frequency: {int(self.current_freq)} Hz", True, COLOR_WHITE)
        screen.blit(freq_text, (50, 50))

        # Draw touch indicator
        if finger_pos:
            pygame.draw.circle(screen, (255, 100, 100), finger_pos, 30)