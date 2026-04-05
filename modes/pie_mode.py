import pygame
import math
from core.settings import *

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def _normalize_angle(a: float) -> float:
    """Wrap an angle into the range [-π, π]."""
    while a >  math.pi: a -= 2 * math.pi
    while a < -math.pi: a += 2 * math.pi
    return a

class PieMode:
    """
    Interactive pie-chart haptic mode.

    Haptic mapping
    ──────────────
    • Inside a slice  →  WAVE_SQUARE at slice-specific frequency, 3 V
    • Crossing a boundary  →  MAX_VOLTAGE spike for SPIKE_MS milliseconds
    • Outside the pie  →  MIN_VOLTAGE (idle)

    Frequency mapping
    ─────────────────
    Larger slice  →  lower frequency  (feels "wide / spacious")
    Smaller slice  →  higher frequency  (feels "tight / dense")
    Range: 30 Hz (largest possible) … 200 Hz (smallest possible)
    """
    SPIKE_MS   = 80     # how long the boundary spike lasts (ms)
    TOUCH_VOLT = 3.0    # voltage while inside a slice
    def __init__(self):
        self.center = (WIDTH // 2, HEIGHT // 2)
        # Leave room for labels — use the shorter screen dimension
        self.radius = min(WIDTH, HEIGHT) // 2 - 80

        self.font_title = pygame.font.SysFont("Arial", 40, bold=True)
        self.font_label = pygame.font.SysFont("Arial", 24)
        self.font_hint  = pygame.font.SysFont("Arial", 22, italic=True)
        self.font_info  = pygame.font.SysFont("Arial", 28, bold=True)

        # Runtime state
        self.active_slice = -1
        self.prev_slice   = -1
        self.border_spike = False
        self.spike_timer  = 0

        # Load first preset
        self.preset_index = 0
        self.load_preset(0)

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------
    def load_preset(self, index: int):
        """Parse a preset dict into per-slice angle + frequency data."""
        preset = PRESETS[index % len(PRESETS)]
        self.title  = preset["title"]
        self.labels = preset["labels"]
        self.values = preset["values"]

        total = sum(self.values)

        # Build slice descriptors
        # Each slice stores: start angle, end angle, haptic frequency
        # Angles are in radians; we start at 12 o'clock (−π/2)
        self.slices: list[dict] = []
        current_angle = -math.pi / 2

        for val in self.values:
            span = (val / total) * 2 * math.pi
            self.slices.append({
                "start": current_angle,
                "end"  : current_angle + span,
                "freq" : self._value_to_freq(val, total),
            })
            current_angle += span

    @staticmethod
    def _value_to_freq(value: float, total: float) -> int:
        """
        Map a slice's percentage to a haptic frequency.
        Large slice (high %)  →  low frequency
        Small slice (low %)   →  high frequency
        """
        ratio = value / total          # 0.0 … 1.0
        freq  = 200 - int(ratio * 170) # 200 Hz … 30 Hz
        return max(30, min(200, freq))

    # ------------------------------------------------------------------
    # Slice lookup — handles the atan2 wrap-around correctly
    # ------------------------------------------------------------------
    def _get_slice_at_angle(self, angle: float) -> int:
        """
        Return the index of the slice that contains `angle`.
        Returns -1 if no slice matches (shouldn't happen for a full 360° chart).

        atan2 returns values in (-π, π].  Our slices also live in that range
        because we start from -π/2 and add positive spans that sum to 2π,
        so the last slice may end at 3π/2 — outside (-π, π].

        Strategy: normalise the query angle into (-π, π], then for each slice
        check if the angle falls inside [start, end).  For slices that cross
        the +π/-π boundary we do a wrap-aware check.
        """
        a = _normalize_angle(angle)

        for i, s in enumerate(self.slices):
            start = s["start"]
            end   = s["end"]

            # Does this slice cross the ±π seam?
            if end > math.pi:
                # Split check: [start, π] ∪ [−π, end − 2π]
                if start <= a <= math.pi or -math.pi <= a < end - 2 * math.pi:
                    return i
            else:
                if start <= a < end:
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
        self.active_slice = -1

        # Count down the boundary spike
        if self.border_spike and (current_time - self.spike_timer) > self.SPIKE_MS:
            self.border_spike = False

        if finger_pos:
            fx, fy = finger_pos
            cx, cy = self.center

            dist = math.sqrt((fx - cx) ** 2 + (fy - cy) ** 2)

            if dist < self.radius:
                angle = math.atan2(fy - cy, fx - cx)
                self.active_slice = self._get_slice_at_angle(angle)

                # Detect slice crossing → trigger spike
                if (self.active_slice != self.prev_slice
                        and self.prev_slice != -1
                        and self.active_slice != -1):
                    self.border_spike = True
                    self.spike_timer  = current_time

                self.prev_slice = self.active_slice

                # Choose output
                if self.border_spike:
                    # Sharp spike — signals boundary crossing
                    target_volt = MAX_VOLTAGE
                    target_freq = CARRIER_FREQ
                elif self.active_slice >= 0:
                    target_freq = self.slices[self.active_slice]["freq"]
                    target_volt = self.TOUCH_VOLT
            else:
                # Finger lifted off the pie — reset slice memory
                self.prev_slice = -1

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
        """Render the pie chart, labels, and UI text."""
        screen.fill(COLOR_BLACK)
        cx, cy = self.center

        # ── Draw slices ──────────────────────────────────────────────
        for i, s in enumerate(self.slices):
            color = PIE_COLORS[i % len(PIE_COLORS)]

            # Highlight: push the active slice outward from the centre
            offset     = 18 if i == self.active_slice else 0
            mid_angle  = (s["start"] + s["end"]) / 2
            ox = int(math.cos(mid_angle) * offset)
            oy = int(math.sin(mid_angle) * offset)

            # Build a polygon that fills the slice
            # We walk from start_deg to end_deg in small steps
            start_deg = math.degrees(s["start"])
            end_deg   = math.degrees(s["end"])

            points = [(cx + ox, cy + oy)]
            step = 1  # degree resolution
            deg  = start_deg
            while deg <= end_deg + step:
                rad = math.radians(min(deg, end_deg))
                points.append((
                    cx + ox + math.cos(rad) * self.radius,
                    cy + oy + math.sin(rad) * self.radius,
                ))
                deg += step

            if len(points) > 2:
                pygame.draw.polygon(screen, color, points)
                pygame.draw.polygon(screen, COLOR_BLACK, points, 2)

            # ── Slice label ──────────────────────────────────────────
            label_r = self.radius * 0.65
            lx = cx + ox + math.cos(mid_angle) * label_r
            ly = cy + oy + math.sin(mid_angle) * label_r

            label_surf = self.font_label.render(
                f"{self.labels[i]}\n{self.values[i]}%", True, COLOR_WHITE
            )
            # pygame.font doesn't support \n — render two lines manually
            line1 = self.font_label.render(self.labels[i],           True, COLOR_WHITE)
            line2 = self.font_label.render(f"{self.values[i]}%",     True, COLOR_WHITE)
            screen.blit(line1, line1.get_rect(center=(int(lx), int(ly) - 12)))
            screen.blit(line2, line2.get_rect(center=(int(lx), int(ly) + 12)))

        # ── Title ────────────────────────────────────────────────────
        title_surf = self.font_title.render(self.title, True, COLOR_WHITE)
        screen.blit(title_surf, title_surf.get_rect(center=(WIDTH // 2, 48)))

        # ── Active slice info bar ────────────────────────────────────
        if self.active_slice >= 0:
            s    = self.slices[self.active_slice]
            info = self.font_info.render(
                f"► {self.labels[self.active_slice]}  —  "
                f"{self.values[self.active_slice]}%  —  {s['freq']} Hz",
                True, COLOR_WHITE,
            )
            # Semi-transparent background behind the info text
            bg = pygame.Surface((info.get_width() + 30, info.get_height() + 14),
                                 pygame.SRCALPHA)
            bg.fill((0, 0, 0, 160))
            bg_rect = bg.get_rect(center=(WIDTH // 2, HEIGHT - 80))
            screen.blit(bg, bg_rect)
            screen.blit(info, info.get_rect(center=(WIDTH // 2, HEIGHT - 80)))

        # ── Hint bar at the bottom ───────────────────────────────────
        hint = self.font_hint.render(
            "1 / 2 / 3  →  farklı veri seti          ENTER  →  mod değiştir",
            True, (170, 170, 170),
        )
        screen.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT - 36)))

        # ── Touch indicator ──────────────────────────────────────────
        if finger_pos:
            pygame.draw.circle(screen, COLOR_WHITE, finger_pos, 18)
            pygame.draw.circle(screen, COLOR_BLACK, finger_pos, 18, 2)
