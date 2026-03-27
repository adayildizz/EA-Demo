"""
Hardware communication module for the Haptic System.

This module uses the pyvisa library to communicate with an external signal
generator or similar hardware device over a standard VISA interface. 
It handles the connection lifecycle, manages the device state to prevent 
redundant commands over the serial/USB connection, and safely limits output voltages.
"""

import pyvisa
# UPDATED IMPORT: Points to the new core directory
from core.settings import *

class HapticController:
    """
    Manages the connection and signal updates to the haptic hardware.
    
    This class maintains a persistent connection to the device and tracks the 
    currently active waveform, frequency, and voltage to optimize communication 
    by only sending commands when values actually change.
    """
    def __init__(self):
        # Initialize the VISA Resource Manager
        self.rm = pyvisa.ResourceManager()
        self.device = None
        self.is_connected = False
        
        # --- State Tracking ---
        # These variables store the last known state of the hardware.
        # This prevents sending redundant commands, reducing latency.
        self.current_freq = 0
        self.current_volt = 0.0
        self.current_wave = WAVE_SQUARE # The current waveform type
        
        # Attempt to establish a connection upon instantiation
        self.connect()

    def connect(self):
        """
        Attempts to connect to the hardware device using the VISA_ADDRESS 
        defined in settings.py. It also performs a factory reset and applies 
        the necessary baseline configurations.
        """
        try:
            # Open the resource connection
            self.device = self.rm.open_resource(VISA_ADDRESS)
            
            # Set communication termination characters
            self.device.write_termination = '\n'
            self.device.read_termination = '\n'
            
            # Query the device ID string to confirm communication
            print(f"Connected to: {self.device.query('*IDN?')}")
            
            # --- Reset and Basic Settings ---
            self.device.write('*RST')                      # Reset to default state
            self.device.write('VOLT:UNIT VPP')             # Set voltage unit to Volts Peak-to-Peak
            self.device.write('OUTP:LOAD INF')             # Set output impedance to High Z (Infinite)
            self.device.write(f'VOLT:OFFS {OFFSET_V}')     # Apply DC offset voltage
            
            # --- Default Waveform Configuration: Square Wave ---
            self.device.write(f'FUNC {WAVE_SQUARE}')
            self.device.write('FUNC:SQU:DCYC 50')          # Set square wave duty cycle to 50%
            
            # --- Initial Values ---
            self.device.write(f'FREQ {CARRIER_FREQ}')
            self.device.write(f'VOLT {MIN_VOLTAGE}')
            
            # --- ALWAYS ON Principle ---
            # The output is turned on immediately, and intensity is modulated 
            # by changing the voltage, rather than toggling the output on/off.
            self.device.write('OUTP ON')
            
            # Sync our local state variables with the hardware's initial state
            self.current_wave = WAVE_SQUARE
            self.current_freq = CARRIER_FREQ
            self.current_volt = MIN_VOLTAGE
            self.is_connected = True
            
        except Exception as e:
            # Fallback to a "dummy mode" if hardware is not found, allowing 
            # the software to run for testing without crashing.
            print(f"ERROR: Connection failed ({e}). Running in Dummy mode.")
            self.is_connected = False

    def update_signal(self, waveform, frequency, voltage):
        """
        Updates the output signal parameters on the hardware.
        
        Args:
            waveform (str): The desired waveform (e.g., WAVE_SQUARE or WAVE_NOISE).
            frequency (int/float): The desired frequency in Hz.
            voltage (float): The desired amplitude in Volts Peak-to-Peak.
        """
        # Abort if we are running in dummy mode or lost connection
        if not self.is_connected or not self.device:
            return

        # 1. Voltage Limiting (Safety Check based on MAX_VOLTAGE from settings)
        if voltage > MAX_VOLTAGE: 
            voltage = MAX_VOLTAGE
        if voltage < MIN_VOLTAGE: 
            voltage = MIN_VOLTAGE
        
        try:
            # 2. Waveform Type Change
            # Only send the command if the requested waveform is different from the current one
            if waveform != self.current_wave:
                self.device.write(f'FUNC {waveform}')
                self.current_wave = waveform

            # 3. Parameter Updates
            # The FREQ command is usually invalid or ignored in Noise mode, 
            # so we only send frequency updates when outputting a Square wave.
            if waveform == WAVE_SQUARE:
                # Compare as integers to ignore minor floating-point jitter
                if int(frequency) != int(self.current_freq):
                    self.device.write(f'FREQ {int(frequency)}')
                    self.current_freq = int(frequency)
            
            # Voltage Update (Valid in both Square and Noise modes)
            # To prevent flooding the device with commands, ignore changes smaller than 0.05V
            if abs(voltage - self.current_volt) > 0.05:
                # Format the voltage to 2 decimal places before sending
                self.device.write(f'VOLT {voltage:.2f}')
                self.current_volt = voltage
                
        except Exception as e:
            # Catch and log any communication errors that occur during the update loop
            print(f"Command Error: {e}")

    def close(self):
        """
        Safely shuts down the hardware connection.
        Sets voltage to minimum, turns off the output, and closes the VISA resource.
        """
        if self.is_connected and self.device:
            try:
                self.device.write(f'VOLT {MIN_VOLTAGE}')
                self.device.write('OUTP OFF')
                self.device.close()
            except: 
                pass # Fail silently during shutdown if the device is already gone