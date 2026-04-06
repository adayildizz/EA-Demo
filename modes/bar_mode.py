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
        "title": "Aylık Ortalama Sıcaklık (İstanbul, °C)",
        "labels": ["Oca", "Şub", "Mar", "Nis", "May", "Haz",
                   "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"],
        "values": [6, 7, 9, 14, 19, 24, 27, 27, 23, 17, 13, 8],
    },
    {
        "title": "Haftalık Egzersiz Süresi (Dakika)",
        "labels": ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"],
        "values": [45, 30, 60, 0, 50, 90, 20],
    },
    {
        "title": "Programlama Dili Popülaritesi (%)",
        "labels": ["Python", "JS", "Java", "C++", "C#", "Rust"],
        "values": [30, 25, 18, 12, 10, 5],
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

# Layout constants
CHART_LEFT        = 120   # left margin (px) — room for Y axis labels
CHART_RIGHT_PAD   = 60    # right margin (px)
CHART_BOTTOM      = 800   # Y coordinate of the bar baseline
CHART_TOP         = 120   # Y coordinate of the tallest possible bar top
BAR_GAP           = 12    # gap between bars (px)
SPIKE_MS          = 80    # boundary spike duration (ms)
TOUCH_VOLT        = 3.0   # voltage while inside a bar


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

        # Count down the boundary spike
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
                    if (self.active_bar != self.prev_bar
                            and self.prev_bar != -1):
                        self.border_spike = True
                        self.spike_timer  = current_time

                    self.prev_bar = self.active_bar

                    # Choose output
                    if self.border_spike:
                        target_volt = MAX_VOLTAGE
                        target_freq = CARRIER_FREQ
                    else:
                        target_freq = b["freq"]
                        target_volt = TOUCH_VOLT
                else:
                    # Finger is above the bar top — no feedback
                    self.prev_bar = -1
            else:
                # Outside chart columns
                self.prev_bar = -1

        return (WAVE_SQUARE, target_freq, target_volt)

    # ------------------------------------------------------------------
    # Event handling (preset switching)
    # ------------------------------------------------------------------
    def handle_event(self, event):
        """Call this from main.py's event loop."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_1:
                self.preset_index = 0
                self.load_preset(0)
            elif event.key == pygame.K_2:
                self.preset_index = 1
                self.load_preset(1)
            elif event.key == pygame.K_3:
                self.preset_index = 2
                self.load_preset(2)

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
                f"{b['value']}  —  {b['freq']} Hz",
                True, COLOR_WHITE,
            )
            bg = pygame.Surface(
                (info.get_width() + 30, info.get_height() + 14),
                pygame.SRCALPHA)
            bg.fill((0, 0, 0, 160))
            bg_rect = bg.get_rect(center=(WIDTH // 2, HEIGHT - 80))
            screen.blit(bg, bg_rect)
            screen.blit(info, info.get_rect(center=(WIDTH // 2, HEIGHT - 80)))

        # ── Hint bar ─────────────────────────────────────────────────
        hint = self.font_hint.render(
            "1 / 2 / 3  →  farklı veri seti          ENTER  →  mod değiştir",
            True, (170, 170, 170),
        )
        screen.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT - 36)))

        # ── Touch indicator ──────────────────────────────────────────
        if finger_pos:
            pygame.draw.circle(screen, COLOR_WHITE, finger_pos, 18)
            pygame.draw.circle(screen, COLOR_BLACK, finger_pos, 18, 2)
