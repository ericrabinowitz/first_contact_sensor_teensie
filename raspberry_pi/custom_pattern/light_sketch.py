#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["Pillow", "pygame", "numpy"]
# ///

# Install
# wget -qO- https://astral.sh/uv/install.sh | sh

# Execute
# ./light_sketch.py

import time
import math
from collections import deque

import numpy as np
from PIL import Image
import pygame

pygame_available = True
connection_healthy = True

TRANSITION_TIME = 1500  # ms
TRAVEL_SPEED = 100  # LED/sec
GREEN_MIX = 50
SEGMENT_1_LENGTH = 100
SEGMENT_2_LENGTH = 100
SEGMENT_3_LENGTH = 100

# setup noise
img = Image.open("Perlin128.png")
width, height = img.size
noise = []
for y in range(height):
    for x in range(width):
        noise.append(img.getpixel((x, y)))


last_update_time = time.time()
fade = 0  # ∈{0..1}
# mask = deque([0]*300, maxlen=300) #static length, no need for POP
segment1 = np.zeros((100, 3), dtype=np.uint8)  # 100 RGB LEDs, Elektra, Segment5, Hoop1
segment2 = np.zeros((100, 3), dtype=np.uint8)  # 100 RGB LEDs, Elektra, Segment6, Hoop2
segment3 = np.zeros((100, 3), dtype=np.uint8)  # 100 RGB LEDs, Eros, Segment5, Hoop3
blue_noise = deque([0] * 300, maxlen=300)  # blue noise left to right
red_noise = deque([0] * 300, maxlen=300)  # red noise right to left

# Setup visualization
VIZ_ENABLED = True
if VIZ_ENABLED:
    VIZ_WIDTH = 800
    VIZ_HEIGHT = 600
    VIZ_LED_SIZE = 5

    # Calculate arch points
    arch_points = []
    arch_center_X = VIZ_WIDTH / 2.0
    arch_center_Y = VIZ_HEIGHT * 0.75
    arch_radius = VIZ_WIDTH * 0.45

    # Left ground to point A (segment 1)
    for i in range(100):
        x = arch_center_X + math.cos(math.radians(120 + i * 0.60)) * arch_radius
        y = arch_center_Y - math.sin(math.radians(120 + i * 0.60)) * arch_radius
        arch_points.append((int(x), int(y)))

    # Point A over arch to point B (segment 2)
    for i in range(100):
        x = arch_center_X + math.cos(math.radians(120 - i * 0.60)) * arch_radius
        y = arch_center_Y - math.sin(math.radians(120 - i * 0.60)) * arch_radius
        arch_points.append((int(x), int(y)))

    # Point B to right ground (segment 3)
    for i in range(100):
        x = arch_center_X + math.cos(math.radians(60 - i * 0.60)) * arch_radius
        y = arch_center_Y - math.sin(math.radians(60 - i * 0.60)) * arch_radius
        arch_points.append((int(x), int(y)))


def init_visualization():
    pygame.init()
    screen = pygame.display.set_mode((VIZ_WIDTH, VIZ_HEIGHT))
    pygame.display.set_caption("Arch Light Show Visualization")
    clock = pygame.time.Clock()

    # Load fonts
    pygame.font.init()

    return screen, clock


def draw_visualization(screen, segment1, segment2, segment3):
    if not VIZ_ENABLED or screen is None or not pygame_available:
        return

    # Clear screen
    screen.fill((0, 0, 0))

    # Draw arch structure (gray line)
    pygame.draw.lines(screen, (50, 50, 50), False, arch_points, 2)

    # Draw LEDs
    for i, point in enumerate(arch_points):

        if i < 100:
            color = segment1[i]
        elif i < 200:
            color = segment2[i - 100]
        else:
            color = segment3[index - 200]

        pygame.draw.circle(screen, color, point, VIZ_LED_SIZE)

    # Draw labels
    font = pygame.font.SysFont("Arial", 16)

    # Draw point labels
    pygame.draw.circle(screen, (255, 255, 255), arch_points[SEGMENT_1_LENGTH - 1], 8)
    point_a_label = font.render("Point A", True, (255, 255, 255))
    screen.blit(
        point_a_label,
        (
            arch_points[SEGMENT_1_LENGTH - 1][0] - 30,
            arch_points[SEGMENT_1_LENGTH - 1][1] - 25,
        ),
    )

    pygame.draw.circle(
        screen, (255, 255, 255), arch_points[SEGMENT_1_LENGTH + SEGMENT_2_LENGTH - 1], 8
    )
    point_b_label = font.render("Point B", True, (255, 255, 255))
    screen.blit(
        point_b_label,
        (
            arch_points[SEGMENT_1_LENGTH + SEGMENT_2_LENGTH - 1][0] - 30,
            arch_points[SEGMENT_1_LENGTH + SEGMENT_2_LENGTH - 1][1] - 25,
        ),
    )

    pygame.display.flip()


noise_offset1 = 0
noise_offset2 = 0

running = True
screen, clock = init_visualization()
counter = 0
while running:
    current_time = time.time()
    elapsed = current_time - last_update_time
    last_update_time = current_time
    active_mode = True

    # Update transition mask
    delta = int(elapsed / TRANSITION_TIME * 256)

    if active_mode == True:
        fade += delta
        if fade >= 255:
            fade = 255
    else:
        fade -= delta
        if fade <= 0:
            fade = 0
    # mask.appendleft(fade)

    # Calculate noise offset for animation
    noise_offset1 = (noise_offset1 + 3) % 8192
    noise_offset2 = noise_offset1 + 8192
    if noise_offset1 >= 8192:
        noise_offset1 = 0

    # Prepare LED arrays for each segment
    blue_noise.appendleft(min(fade, noise[noise_offset1]))
    red_noise.append(min(fade, noise[noise_offset2]))
    for i in range(100):
        index = i + 200
        blue_noise[index] = min(blue_noise[index], 255 - i * 2)
        red_noise[100 - i] = min(red_noise[100 - i], 255 - i * 2)

    # populate RGB values from noise streams
    for i in range(100):
        segment1[i] = [red_noise[i], GREEN_MIX, blue_noise[i]]
        segment2[i] = [red_noise[i + 100], GREEN_MIX, blue_noise[i + 100]]
        segment3[i] = [red_noise[i + 200], GREEN_MIX, blue_noise[i + 200]]

    # print (segment1)
    # Update visualization
    if VIZ_ENABLED and screen and pygame_available:
        draw_visualization(screen, segment1, segment2, segment3)
