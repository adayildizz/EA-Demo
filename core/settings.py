"""
Configuration module for the Haptic System.

This file acts as the central hub for all global settings and constants used 
throughout the application. It includes hardware connection details, safety 
limits for voltage, physical display dimensions, and UI color palettes for 
the different haptic modes.
"""

# --- SETTINGS AND CONSTANTS ---

# ==========================================
# Hardware Settings
# ==========================================
# The network address of the signal generator (VISA resource string)
VISA_ADDRESS = 'TCPIP0::169.254.2.20::inst0::INSTR'

# Default carrier frequency in Hertz (Hz)
CARRIER_FREQ = 125

# HARDWARE SAFETY LIMITS: 
# It is critical that MAX_VOLTAGE does not exceed safe limits for the haptic hardware.
MAX_VOLTAGE = 4.0      # UPDATED: Maximum voltage capped at 4.0 Volts
MIN_VOLTAGE = 0.1      # Idle voltage (baseline when no haptic feedback is applied)
OFFSET_V = 0           # DC offset voltage applied to the signal

# ==========================================
# Waveform Types
# ==========================================
# Command strings expected by the signal generator to switch wave types
WAVE_SQUARE = 'SQU'    # Square wave (typically used for sharp, distinct pulses)
WAVE_NOISE = 'NOIS'    # Noise wave (typically used for rough textures like sand)

# ==========================================
# Display Settings
# ==========================================
# Initial window position. Using a negative X value (e.g., -1920) is often used 
# to spawn the window on a secondary monitor located to the left of the main display.
X_KOORDINATI = -1920
Y_KOORDINATI = 0

# Screen resolution dimensions
WIDTH = 1920
HEIGHT = 1080

# Input inversion flags. If the physical touch panel maps coordinates 
# backwards compared to the display, set these to True to flip the axes.
INVERT_X = True
INVERT_Y = True

# ==========================================
# Colors (RGB and RGBA Formats)
# ==========================================

# Basic Colors
COLOR_BLACK = (0, 0, 0)
COLOR_WHITE = (255, 255, 255)
COLOR_TEXT_BG = (0, 0, 0, 150) # Semi-transparent black for readable text backgrounds

# Colors for Heart Mode (Visualizing a beating heart)
COLOR_HEART_DIM = (60, 0, 0)       # Dark red (background/idle)
COLOR_HEART_BEAT = (255, 50, 50)   # Bright red (active heartbeat pulse)
COLOR_HEART_SILENT = (140, 20, 20) # Medium red (resting state)

# Colors for Texture Mode (Sand texture representation)
COLOR_SAND_BG = (238, 214, 175)    # Light beige background
COLOR_SAND_DOTS = (194, 178, 128)  # Darker sandy dots for visual texture
COLOR_BOX_SAND = (160, 82, 45)     # Outline or bounding box for sand areas

# Colors for Texture Mode (Metal grating representation)
COLOR_METAL_BG = (40, 44, 52)      # Dark grey background
COLOR_METAL_GRID = (70, 75, 85)    # Lighter grey for the metal grid lines
COLOR_BOX_METAL = (100, 200, 255)  # Metallic blue for bounding box/highlights

# Colors for Train Mode (Visualizing train tracks and scenery)
COLOR_RAIL = (100, 100, 100)       # Steel grey for the train rails
COLOR_SLEEPER = (139, 69, 19)      # Brown for the wooden railroad ties/sleepers
COLOR_SKY = (20, 20, 40)           # Dark blue for the night sky
COLOR_GROUND = (30, 30, 30)        # Dark grey/brown for the ground