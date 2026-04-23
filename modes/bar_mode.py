"""
Bar Chart Haptic Mode for the Haptic System.

This module renders an interactive bar chart on screen. As the user moves their
finger across different bars, the haptic feedback frequency changes proportionally
to the bar's height — taller bar means higher frequency. Crossing a bar boundary
produces a sharp voltage spike so the user can feel the transition.

Preset datasets can be switched with the 1 / 2 / 3 keys.
"""

import pygame
import math
from core.settings import *

# ---------------------------------------------------------------------------
# Preset Datasets
# ---------------------------------------------------------------------------
PRESETS = [
    {
        "title": "Dataset 1",
        "labels": ["A", "B", "C"],
        "values": [20, 65, 90],
    },
    {
        "title": "Dataset 2",
        "labels": ["A", "B", "C"],
        "values": [80, 30, 55],
    },
    {
        "title": "Dataset 3",
        "labels": ["A", "B", "C"],
        "values": [45, 10, 75],
    },
]

# Colour palette for bars — cycles if there are more bars than colours
BAR_COLORS = [
    ( 54, 162, 235),   # blue
    (255,  99, 132),   # red
    ( 75, 192, 192),   # teal
    (255, 206,  86),   # yellow
    (153, 102, 255),   # purple
    (255, 159,  64),   # orange
    ( 46, 204, 113),   # green
    (231,  76,  60),   # dark red
    ( 52, 152, 219),   # light blue
    (155,  89, 182),   # violet
    ( 26, 188, 156),   # turquoise
    (241, 196,  15),   # gold
]

# Layout constants — chart occupies centre half (width) × 2/3 (height) of screen
CHART_LEFT        = WIDTH  // 4 + 50   # bars start here; Y labels sit to the left
CHART_RIGHT_PAD   = WIDTH  // 4        # right margin so right edge = 3/4 of screen
CHART_BOTTOM      = HEIGHT * 5 // 6   # baseline of bars
CHART_TOP         = HEIGHT // 6        # top of tallest bar
BAR_GAP           = 12    # gap between bars (px)
SPIKE_MS          = 80    # boundary spike duration (ms)
HAS_SPIKE         = True



# ---------------------------------------------------------------------------
# Haptic Config Functions
# Each function takes (value, max_val) and returns (target_freq, target_volt)
# ---------------------------------------------------------------------------

def frequency_config(value: float, max_val: float):
    """Frequency varies with bar height; voltage stays constant at 3.0 V."""
    target_freq = 50 + int((value / max_val) * 200)    # 50–250 Hz
    target_volt = 3.0                                   # sabit
    return target_freq, target_volt


def amplitude_config(value: float, max_val: float):
    """Voltage varies with bar height; frequency stays constant."""
    target_freq = CARRIER_FREQ                          # 125 Hz sabit
    target_volt = 1.0 + (value / max_val) * 3.0        # 1.0–4.0 V
    return target_freq, target_volt


def texture_config(value: float, max_val: float, current_time: int):
    """Pulse speed proportional to bar height — short bar: slow pulse, tall bar: fast pulse."""
    target_freq = CARRIER_FREQ                          # 125 Hz sabit

    # pulse_period inversely proportional to value: yüksek bar → kısa period → hızlı pulse
    max_period  = 400                                   # ms — en yavaş (kısa bar)
    min_period  = 60                                    # ms — en hızlı (uzun bar)
    pulse_period = int(max_period - (value / max_val) * (max_period - min_period))

    target_volt = 4.0 if (current_time % pulse_period) < (pulse_period // 2) else MIN_VOLTAGE
    return target_freq, target_volt

# ---------------------------------------------------------------------------

class BarMode:
    """
    Interactive bar-chart haptic mode.

    Haptic mapping
    ──────────────
    • Inside a bar          →  WAVE_SQUARE at height-proportional frequency, 3 V
    • Above a bar (empty)   →  MIN_VOLTAGE (idle — user is above the bar top)
    • Crossing a boundary   →  MAX_VOLTAGE spike for SPIKE_MS milliseconds
    • Outside chart area    →  MIN_VOLTAGE

    Frequency mapping
    ─────────────────
    Taller bar  →  higher frequency   (feels "more data / taller")
    Shorter bar →  lower frequency
    Range: 30 Hz (shortest) … 200 Hz (tallest)
    """

    def __init__(self):
        self.font_title  = pygame.font.SysFont("Arial", 40, bold=True)
        self.font_label  = pygame.font.SysFont("Arial", 22)
        self.font_value  = pygame.font.SysFont("Arial", 20, bold=True)
        self.font_hint   = pygame.font.SysFont("Arial", 22, italic=True)
        self.font_info   = pygame.font.SysFont("Arial", 28, bold=True)
        self.font_axis   = pygame.font.SysFont("Arial", 18)

        # Runtime state
        self.active_bar  = -1
        self.prev_bar    = -1
        self.border_spike = False
        self.spike_timer  = 0
        self.has_spike = True

        # Haptic config
        self.config_index = 0
        self.config_names = ["Frequency", "Amplitude", "Texture"]

        # Load first preset
        self.preset_index = 0
        self.load_preset(0)

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------
    def load_preset(self, index: int):
        """Compute bar rectangles and haptic frequencies from a preset."""
        preset = PRESETS[index % len(PRESETS)]
        self.title  = preset["title"]
        self.labels = preset["labels"]
        self.values = preset["values"]

        n          = len(self.values)
        max_val    = max(self.values)
        chart_w    = WIDTH - CHART_LEFT - CHART_RIGHT_PAD
        bar_w      = (chart_w - BAR_GAP * (n - 1)) // n
        chart_h    = CHART_BOTTOM - CHART_TOP

        self.bars: list[dict] = []

        for i, val in enumerate(self.values):
            bar_h  = int((val / max_val) * chart_h)
            bar_x  = CHART_LEFT + i * (bar_w + BAR_GAP)
            bar_y  = CHART_BOTTOM - bar_h

            self.bars.append({
                "rect" : pygame.Rect(bar_x, bar_y, bar_w, bar_h),
                "value": val,
                "freq" : self._value_to_freq(val, max_val),
                "color": BAR_COLORS[i % len(BAR_COLORS)],
            })

        # Keep bar_w for hit-testing columns (finger X only)
        self.bar_w = bar_w

    @staticmethod
    def _value_to_freq(value: float, max_val: float) -> int:
        """
        Map a bar's value to a haptic frequency.
        Tallest bar → 200 Hz, shortest bar → 30 Hz.
        """
        ratio = value / max_val        # 0.0 … 1.0
        freq  = 30 + int(ratio * 170)  # 30 Hz … 200 Hz
        return max(30, min(200, freq))

    # ------------------------------------------------------------------
    # Hit testing
    # ------------------------------------------------------------------
    def _get_bar_at(self, finger_pos) -> int:
        """
        Return the index of the bar column the finger is over, or -1.
        We only check the X axis for column detection — the Y check
        (is the finger below the bar top?) happens in update().
        """
        fx = finger_pos[0]
        for i, b in enumerate(self.bars):
            if b["rect"].x <= fx < b["rect"].x + b["rect"].width:
                return i
        return -1

    # ------------------------------------------------------------------
    # Update (called every frame)
    # ------------------------------------------------------------------
    def update(self, finger_pos, current_time: int):
        """
        Calculate haptic output based on touch position.

        Returns:
            (waveform, frequency, voltage)
        """
        target_freq = CARRIER_FREQ
        target_volt = MIN_VOLTAGE
        self.active_bar = -1
        self.last_freq = target_freq
        self.last_volt = target_volt

        # Count down the boundary spike
        if self.has_spike:
            if self.border_spike and (current_time - self.spike_timer) > SPIKE_MS:
                self.border_spike = False

        if finger_pos:
            fx, fy = finger_pos
            col = self._get_bar_at(finger_pos)

            if col >= 0:
                b = self.bars[col]

                # Is the finger below the bar top (inside the bar area)?
                finger_inside_bar = fy >= b["rect"].top and fy <= CHART_BOTTOM

                if finger_inside_bar:
                    self.active_bar = col

                    # Detect column crossing → trigger spike
                    if self.has_spike:
                        if (self.active_bar != self.prev_bar
                                and self.prev_bar != -1):
                            self.border_spike = True
                            self.spike_timer  = current_time

                    self.prev_bar = self.active_bar

                    # Choose output
                    if self.has_spike and self.border_spike:
                        target_volt = MAX_VOLTAGE
                        target_freq = CARRIER_FREQ
                    else:
                        val     = b["value"]
                        max_val = max(self.values)
                        if self.config_index == 0:
                            target_freq, target_volt = frequency_config(val, max_val)
                        elif self.config_index == 1:
                            target_freq, target_volt = amplitude_config(val, max_val)
                        else:
                            target_freq, target_volt = texture_config(val, max_val, current_time)
                else:
                    # Finger is above the bar top — no feedback
                    self.prev_bar = -1
            else:
                # Outside chart columns — only reset prev_bar if spike is disabled
                if not self.has_spike:
                    self.prev_bar = -1

        self.last_freq = target_freq
        self.last_volt = target_volt
        return (WAVE_SQUARE, target_freq, target_volt)

    # ------------------------------------------------------------------
    # Event handling (preset switching)
    # ------------------------------------------------------------------
    def handle_event(self, event):
        """Call this from main.py's event loop."""
        if event.type == pygame.KEYDOWN:
            # Preset switching — 1 / 2 / 3
            if event.key == pygame.K_1:
                self.preset_index = 0
                self.load_preset(0)
            elif event.key == pygame.K_2:
                self.preset_index = 1
                self.load_preset(1)
            elif event.key == pygame.K_3:
                self.preset_index = 2
                self.load_preset(2)
            # Haptic config switching — Q / W / E
            elif event.key == pygame.K_q:
                self.config_index = 0
            elif event.key == pygame.K_w:
                self.config_index = 1
            elif event.key == pygame.K_e:
                self.config_index = 2
            elif event.key == pygame.K_s:
                self.has_spike = not self.has_spike

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------
    def draw(self, screen, finger_pos):
        """Render the bar chart, axes, labels, and UI text."""
        screen.fill(COLOR_BLACK)

        # ── Y axis grid lines ────────────────────────────────────────
        max_val   = max(self.values)
        chart_h   = CHART_BOTTOM - CHART_TOP
        n_lines   = 5

        for i in range(n_lines + 1):
            ratio  = i / n_lines
            y      = CHART_BOTTOM - int(ratio * chart_h)
            label  = int(ratio * max_val)

            # Faint grid line
            pygame.draw.line(screen, (50, 50, 50),
                             (CHART_LEFT, y), (WIDTH - CHART_RIGHT_PAD, y), 1)

            # Y axis label
            txt = self.font_axis.render(str(label), True, (150, 150, 150))
            screen.blit(txt, txt.get_rect(midright=(CHART_LEFT - 8, y)))

        # ── Bars ─────────────────────────────────────────────────────
        for i, b in enumerate(self.bars):
            color = b["color"]

            # Brighten the active bar
            if i == self.active_bar:
                color = tuple(min(255, c + 60) for c in color)

            pygame.draw.rect(screen, color, b["rect"])
            pygame.draw.rect(screen, COLOR_BLACK, b["rect"], 2)  # outline

            # Value label above the bar
            val_surf = self.font_value.render(str(b["value"]), True, COLOR_WHITE)
            screen.blit(val_surf, val_surf.get_rect(
                center=(b["rect"].centerx, b["rect"].top - 16)))

            # Category label below the baseline
            lbl_surf = self.font_label.render(
                self.labels[i], True, (200, 200, 200))
            screen.blit(lbl_surf, lbl_surf.get_rect(
                center=(b["rect"].centerx, CHART_BOTTOM + 24)))

        # ── Baseline ─────────────────────────────────────────────────
        pygame.draw.line(screen, (180, 180, 180),
                         (CHART_LEFT, CHART_BOTTOM),
                         (WIDTH - CHART_RIGHT_PAD, CHART_BOTTOM), 2)

        # ── Title ────────────────────────────────────────────────────
        title_surf = self.font_title.render(self.title, True, COLOR_WHITE)
        screen.blit(title_surf, title_surf.get_rect(center=(WIDTH // 2, 52)))

        # ── Active bar info ──────────────────────────────────────────
        if self.active_bar >= 0:
            b    = self.bars[self.active_bar]
            info = self.font_info.render(
                f"► {self.labels[self.active_bar]}  —  "
                f"{b['value']}  —  {self.last_freq} Hz  —  {self.last_volt:.2f} V",
                True, COLOR_WHITE,
            )
            bg = pygame.Surface(
                (info.get_width() + 30, info.get_height() + 14),
                pygame.SRCALPHA)
            bg.fill((0, 0, 0, 160))
            bg_rect = bg.get_rect(center=(WIDTH // 2, HEIGHT - 80))
            screen.blit(bg, bg_rect)
            screen.blit(info, info.get_rect(center=(WIDTH // 2, HEIGHT - 80)))

        # ── Active config indicator ──────────────────────────────────
        config_surf = self.font_info.render(
            f"Haptic: {self.config_names[self.config_index]}",
            True, (120, 220, 120),
        )
        screen.blit(config_surf, config_surf.get_rect(topleft=(CHART_LEFT, CHART_TOP - 48)))

        # ── Hint bar ─────────────────────────────────────────────────
        hint = self.font_hint.render(
            "1/2/3  →  veri seti     Q/W/E  →  haptic config     ENTER  →  mod değiştir",
            True, (170, 170, 170),
        )
        screen.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT - 36)))

        # ── Touch indicator ──────────────────────────────────────────
        if finger_pos:
            pygame.draw.circle(screen, COLOR_WHITE, finger_pos, 18)
            pygame.draw.circle(screen, COLOR_BLACK, finger_pos, 18, 2)
