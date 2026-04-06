"""
Image Haptic Mode for the Haptic System.

This module loads any image and converts it into a haptic experience.
As the user moves their finger across the screen, two layers of feedback
are combined:

  1. Edge layer (Canny)    — crossing an edge produces a MAX_VOLTAGE spike
  2. Brightness layer      — pixel brightness maps to frequency
                             dark area  →  low frequency
                             bright area →  high frequency

Usage (from command line):
    python3 main.py --image path/to/image.png

If no --image argument is given, a built-in test pattern is generated.
"""

import pygame
import math
import numpy as np
import cv2
from core.settings import *


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
EDGE_THRESHOLD_LOW  = 30    # Canny lower threshold
EDGE_THRESHOLD_HIGH = 100   # Canny upper threshold
EDGE_VOLT           = MAX_VOLTAGE   # voltage spike on edge
EDGE_SPIKE_MS       = 150           # how long the edge spike lasts (ms)
TOUCH_VOLT          = 4.0          # base voltage while touching
FREQ_MIN            = 30            # Hz — darkest pixel
FREQ_MAX            = 200           # Hz — brightest pixel


class ImageMode:
    """
    Haptic image explorer mode.

    The loaded image is scaled to fill the screen. Two numpy arrays are
    pre-computed once at load time:

        self.freq_map   — uint8 array (HEIGHT x WIDTH), each pixel stores
                          the haptic frequency (30–200 Hz) derived from
                          the greyscale brightness of that pixel.

        self.edge_map   — uint8 binary array (HEIGHT x WIDTH), non-zero
                          where Canny detected an edge.

    Every frame, update() samples these arrays at the finger position and
    returns the appropriate (waveform, frequency, voltage).
    """

    def __init__(self, image_path=None):
        self.font_title  = pygame.font.SysFont("Arial", 36, bold=True)
        self.font_hint   = pygame.font.SysFont("Arial", 22, italic=True)
        self.font_info   = pygame.font.SysFont("Arial", 26, bold=True)

        # Edge spike state
        self.on_edge      = False
        self.spike_timer  = 0

        # Last known haptic values (for the info bar)
        self.last_freq    = CARRIER_FREQ
        self.last_volt    = MIN_VOLTAGE

        # E tuşuyla edge görünümü toggle
        self.show_edges   = False

        # Load image (or generate test pattern)
        if image_path:
            self.image_name = image_path.split("/")[-1].split("\\")[-1]
            self._load_image(image_path)
        else:
            self.image_name = "test pattern"
            self._generate_test_pattern()

    # ------------------------------------------------------------------
    # Image loading & preprocessing
    # ------------------------------------------------------------------
    def _load_image(self, path: str):
        """Load an image from disk, scale it to screen size, and precompute maps."""
        # OpenCV loads BGR — convert to RGB for pygame
        img_bgr = cv2.imread(path)
        if img_bgr is None:
            print(f"ImageMode: could not read '{path}', falling back to test pattern.")
            self._generate_test_pattern()
            return

        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        self._preprocess(img_rgb)

    def _generate_test_pattern(self):
        """
        Generate a simple built-in test image when no file is provided.
        Pattern: concentric circles on a gradient background — gives a
        mix of edges and smooth brightness transitions to test both
        haptic layers.
        """
        # Create a gradient background (dark left → bright right)
        base = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        for x in range(WIDTH):
            val = int((x / WIDTH) * 200)
            base[:, x, :] = val

        # Draw white concentric circles
        cx, cy = WIDTH // 2, HEIGHT // 2
        for r in range(80, min(WIDTH, HEIGHT) // 2, 80):
            cv2.circle(base, (cx, cy), r, (255, 255, 255), 6)

        # Draw a filled white rectangle in one corner
        cv2.rectangle(base, (80, 80), (320, 280), (220, 220, 220), -1)

        self._preprocess(base)

    def _preprocess(self, img_rgb: np.ndarray):
        """
        Scale image to screen, compute freq_map and edge_map, create pygame surface.

        Steps
        ─────
        1. Resize to (WIDTH, HEIGHT)
        2. Convert to greyscale → freq_map  (brightness → frequency)
        3. Apply Canny edge detection → edge_map
        4. Convert RGB array to a pygame Surface for display
        """
        # 1. Resize
        img_resized = cv2.resize(img_rgb, (WIDTH, HEIGHT),
                                 interpolation=cv2.INTER_CUBIC)

        # 2. Greyscale → frequency map
        grey = cv2.cvtColor(img_resized, cv2.COLOR_RGB2GRAY)  # 0–255
        # Map brightness linearly to [FREQ_MIN, FREQ_MAX]
        self.freq_map = (
            FREQ_MIN + (grey.astype(np.float32) / 255.0) * (FREQ_MAX - FREQ_MIN)
        ).astype(np.int32)

        # 3. Edge map via Canny
        # Slight Gaussian blur first to reduce noise-induced false edges
        edges_combined = np.zeros((HEIGHT, WIDTH), dtype=np.uint8)
        for channel in cv2.split(img_resized):
            blurred = cv2.GaussianBlur(channel, (5, 5), 0)
            edges = cv2.Canny(blurred, EDGE_THRESHOLD_LOW, EDGE_THRESHOLD_HIGH)
            edges_combined = cv2.bitwise_or(edges_combined, edges)
        self.edge_map = edges_combined
        # Kenarları şişir — mouse ile test ederken daha kolay yakalanır
        self.edge_map = cv2.dilate(
            self.edge_map, np.ones((3, 3), np.uint8), iterations=2)

        # Edge map'i pygame surface'e çevir — E tuşu görsel için
        edge_rgb = cv2.cvtColor(self.edge_map, cv2.COLOR_GRAY2RGB)
        edge_array = np.transpose(edge_rgb, (1, 0, 2))
        self.edge_surface = pygame.surfarray.make_surface(edge_array)

        # 4. Pygame display surface
        # pygame.surfarray expects (WIDTH, HEIGHT) ordering — transpose needed
        surface_array   = np.transpose(img_resized, (1, 0, 2))
        self.display_surface = pygame.surfarray.make_surface(surface_array)

        # Dim the image slightly so white UI text stays readable
        dim_overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        dim_overlay.fill((0, 0, 0, 80))
        self.display_surface.blit(dim_overlay, (0, 0))

    # ------------------------------------------------------------------
    # Update (called every frame)
    # ------------------------------------------------------------------
    def update(self, finger_pos, current_time: int):
        """
        Sample freq_map and edge_map at the finger position.

        Priority:
            edge detected  →  MAX_VOLTAGE spike (overrides brightness)
            no edge        →  brightness-derived frequency at TOUCH_VOLT
            no touch       →  MIN_VOLTAGE idle
        """
        target_freq = CARRIER_FREQ
        target_volt = MIN_VOLTAGE

        # Count down edge spike
        if self.on_edge and (current_time - self.spike_timer) > EDGE_SPIKE_MS:
            self.on_edge = False

        if finger_pos:
            fx, fy = finger_pos

            # Clamp to valid array indices (finger may be at screen edge)
            fx = max(0, min(WIDTH  - 1, fx))
            fy = max(0, min(HEIGHT - 1, fy))

            # Sample edge map
            is_edge = self.edge_map[fy, fx] > 0

            if is_edge and not self.on_edge:
                self.on_edge     = True
                self.spike_timer = current_time

            if self.on_edge:
                # Edge spike — sharp, attention-grabbing
                target_volt = EDGE_VOLT
                target_freq = CARRIER_FREQ
            else:
                # Brightness-derived frequency
                target_freq = int(self.freq_map[fy, fx])
                target_volt = TOUCH_VOLT

        self.last_freq = target_freq
        self.last_volt = target_volt

        return (WAVE_SQUARE, target_freq, target_volt)

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------
    def handle_event(self, event):
        """E tuşuyla edge görünümünü toggle et."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_e:
                self.show_edges = not self.show_edges

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------
    def draw(self, screen, finger_pos):
        """Render the image, edge overlay toggle, and UI."""

        # ── Background image / edge toggle ───────────────────────────
        if self.show_edges:
            screen.blit(self.edge_surface, (0, 0))
        else:
            screen.blit(self.display_surface, (0, 0))

        # ── Title bar ────────────────────────────────────────────────
        title_surf = self.font_title.render(
            f"Image Mode  —  {self.image_name}", True, COLOR_WHITE)
        bg = pygame.Surface(
            (title_surf.get_width() + 30, title_surf.get_height() + 12),
            pygame.SRCALPHA)
        bg.fill((0, 0, 0, 170))
        bg_rect = bg.get_rect(center=(WIDTH // 2, 44))
        screen.blit(bg, bg_rect)
        screen.blit(title_surf, title_surf.get_rect(center=(WIDTH // 2, 44)))

        # ── Active haptic info ───────────────────────────────────────
        if finger_pos:
            if self.on_edge:
                info_text = f"► KENAR  —  {EDGE_VOLT:.1f} V  spike"
                info_color = (255, 80, 80)
            else:
                info_text  = f"► {self.last_freq} Hz  —  {self.last_volt:.1f} V"
                info_color = COLOR_WHITE

            info_surf = self.font_info.render(info_text, True, info_color)
            bg2 = pygame.Surface(
                (info_surf.get_width() + 30, info_surf.get_height() + 14),
                pygame.SRCALPHA)
            bg2.fill((0, 0, 0, 160))
            bg2_rect = bg2.get_rect(center=(WIDTH // 2, HEIGHT - 80))
            screen.blit(bg2, bg2_rect)
            screen.blit(info_surf, info_surf.get_rect(center=(WIDTH // 2, HEIGHT - 80)))

        # ── Hint bar ─────────────────────────────────────────────────
        hint = self.font_hint.render(
            "E  →  kenar görünümü          ENTER  →  mod değiştir          python3 main.py --image <dosya>  →  resim yükle",
            True, (200, 200, 200),
        )
        screen.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT - 36)))

        # ── Touch indicator ──────────────────────────────────────────
        if finger_pos:
            color = (255, 80, 80) if self.on_edge else COLOR_WHITE
            pygame.draw.circle(screen, color,        finger_pos, 18)
            pygame.draw.circle(screen, COLOR_BLACK,  finger_pos, 18, 2)
