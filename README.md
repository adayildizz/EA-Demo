# 🖐️ Haptic Feedback Simulator

A Python-based interactive application that synchronizes visual graphics with real-time electrovibration haptic hardware. Built with **Pygame** and **PyVISA**, this system allows users to "feel" digital textures and rhythms through a connected signal generator and voltage amplifier.

---

## ✨ Features & Interaction Modes

The application features three distinct haptic experiences. Press `Enter` to cycle through them:

* ❤️ **Heart Mode**: Simulates a human heartbeat. Touch the on-screen heart to feel a synchronized, pulsing "lub-dub" rhythm driven by voltage spikes.
* 🏖️ **Texture Mode**: A split-screen simulation for surface textures. 
    * **Sand (Left):** Dragging the box generates randomized, low-frequency signals simulating a gritty, rough texture.
    * **Metal Grating (Right):** Dragging the box generates a constant, very low-frequency, high-voltage signal simulating heavy "thuds" across a metal grid.
* 🚂 **Train Mode**: Simulates the gathering momentum of a train. As the 3D visual track speeds up, the haptic frequency exponentially increases from a slow crawl to a high-speed vibration.

---

## 🛠️ Hardware Requirements

* A signal generator or haptic controller compatible with standard VISA communication.
* An infrared frame or touch screen for user input.
* **⚠️ IMPORTANT SAFETY NOTE regarding Voltage:** The `MAX_VOLTAGE` defined in `settings.py` (Default: 4.0V) represents the peak-to-peak voltage (Vpp) output of the signal generator. **This specific setup utilizes a 50x voltage amplifier.** Therefore, a 4Vpp signal from the generator results in a **100V peak** on the physical touchscreen side. Ensure your hardware and touch interface are rated to safely handle these amplified voltages.

---

## 💻 Software Requirements

* **Python 3.x**
* **Pygame** (for the visual interface and input handling)
* **PyVISA** (for hardware communication)

---

## 🚀 Installation & Setup

**1. Clone the repository**
```bash
git clone https://github.com/emirbahadirunsal/EA-Demo.git
cd EA-Demo
```

**2. Install dependencies**
```bash
pip install -r requirements.txt
```

**3. Configure your hardware**
Open `core/settings.py` and update the `VISA_ADDRESS` to match your signal generator's IP address or connection string:
```python
VISA_ADDRESS = 'TCPIP0::169.254.2.20::inst0::INSTR'
```

**4. Run the application**
```bash
python main.py
```

---

## 🎮 Controls

* **Touch**: Interact with the visual elements to trigger haptic feedback.
* **Enter (Return)**: Switch to the next haptic mode.
* **Escape (ESC)**: Safely close the hardware connection and exit the application.

---

## ⚙️ Configuration (`core/settings.py`)

Core parameters can be easily adjusted in the `core/settings.py` file without modifying the main logic:
* **Safety Limits**: Adjust the `MAX_VOLTAGE` output for the signal generator (remember to account for your amplifier's multiplier).
* **Frequencies**: Change the default `CARRIER_FREQ`.
* **Display**: Modify window resolution (`WIDTH`, `HEIGHT`) or invert touch axes (`INVERT_X`, `INVERT_Y`) if your hardware frame requires it.