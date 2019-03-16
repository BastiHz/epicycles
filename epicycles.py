"""Draw various intricate shapes by adding rotating circles.


Copyright (C) 2019 Sebastian Henz

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""


import os
import math

import pygame as pg


# TODO: Load harmonics from file if given a filename. Modify the file format
# outputtet by the R script, i.e. remove the brackets and trailing commas.
# TODO: When importing a path rescale so that it fits the screen.

# This is the formula:
# a * exp(bj * t) + c
# a is the start position, abs(a) is the circle radius
# b is the speed and direction of the rotation (negative values rotate anticlockwise)
# j is sqrt(-1), usually denoted "i" in math and physics
# c is the position of the circle center

SAVE_IMAGES = False
SCREEN_WIDTH = 900
SCREEN_HEIGHT = 900
SCREEN_CENTER = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
FPS = 60
FPS_GIF = 25
BACKGROUND_COLOR = (255, 255, 255)
LINE_COLOR = [0, 0, 0]
CIRCLE_COLOR = (128, 128, 128)
CIRCLE_LINE_COLOR = (60, 60, 60)  # (255, 0, 0)
CENTER_CIRCLE_RADIUS = 400  # Adjust manually for different shapes
MIN_SPEED = 1/16
EXAMPLE_FLOWER = [
    [0.3, 1j],
    [0.3, 10j]
]
EXAMPLE_DIAMOND = [
    [1, 1j],
    [1/9, -3j],
    [1/25, 5j],
    [1/49, -7j]
]
EXAMPLE_SQUARE_WAVE = [
    [1, 1j],
    [1/3, 3j],
    [1/5, 5j],
    [1/7, 7j],
    [1/9, 9j]
]
EXAMPLE_STAR = [
    [0.5447818+0.1770103j, 2j],
    [0.2421415+0.0786765j, -3j],
    [0.0444989+0.0144586j, 7j],
    [0.0340763+0.0110721j, -8j]
]


class Epicycles:
    def __init__(self, harmonics, screenshot_path="screenshots/"):
        self.harmonics = harmonics
        # Sort by radius:
        self.harmonics = sorted(
            self.harmonics,
            key=lambda i: abs(i[0]),
            reverse=True
        )
        # Invert y-axis for pygame window:
        for i, h in enumerate(self.harmonics):
            z = h[0]
            self.harmonics[i][0] = complex(z.real, z.imag * -1)
        self.screenshot_path = screenshot_path
        self.running = True
        self.last_point = None
        self.angle = 0  # angle in radians
        self.paused = False
        self.circles_visible = True
        self.speed = 1  # speed of the innermost circle in radians/second
        self.main_surface = pg.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.line_surface = self.main_surface.copy()
        self.line_surface.fill(BACKGROUND_COLOR)
        self.surface_storage = [None] * 1000  # TODO: automatically expand list if length is not enough
        pg.display.set_caption("Epicycles")
        # Scale all radii to the center circle:
        for i in range(len(self.harmonics)):
            self.harmonics[i][0] *= CENTER_CIRCLE_RADIUS
        self.circle_points = [0 for i in range(len(self.harmonics)+1)]
        self.circle_points[0] = self.to_complex(SCREEN_CENTER)
        self.update_circles(0)
        self.last_point = self.from_complex(self.circle_points[-1])

    @staticmethod
    def to_complex(xy):
        return complex(xy[0], xy[1])

    @staticmethod
    def from_complex(z):
        return [z.real, z.imag]

    def handle_input(self):
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.running = False
            elif event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    self.running = False
                elif event.key == pg.K_p or event.key == pg.K_SPACE:
                    self.paused = not self.paused
                elif event.key == pg.K_c:
                    self.circles_visible = not self.circles_visible
                elif event.key == pg.K_UP:
                    self.speed *= 2
                elif event.key == pg.K_DOWN:
                    self.speed = max(self.speed / 2, MIN_SPEED)
                elif event.key == pg.K_BACKSPACE:
                    self.line_surface.fill(BACKGROUND_COLOR)
                elif event.key == pg.K_a:
                    print(self.angle)

    def update_circles(self, dt):
        self.angle += self.speed * dt
        if self.angle > math.tau:
            self.angle -= math.tau
            if SAVE_IMAGES:
                self.running = False

        for i, h in enumerate(self.harmonics):
            p = h[0] * math.e ** (h[1] * self.angle) + self.circle_points[i]
            self.circle_points[i+1] = p

    def draw(self):
        # Convert to complex coordinates to xy for drawing:
        xy_points = [self.from_complex(i) for i in self.circle_points]
        # print(xy_points[-1])
        # print(self.last_point)
        #if self.last_point is not None:
        pg.draw.line(
            self.line_surface,
            LINE_COLOR,
            self.last_point,
            xy_points[-1],
            2
        )
        self.last_point = xy_points[-1]

        self.main_surface.blit(self.line_surface, (0, 0))
        if not self.circles_visible:
            return
        for i, k in enumerate(self.harmonics):
            pg.draw.circle(
                self.main_surface,
                CIRCLE_COLOR,
                [int(f) for f in xy_points[i]],
                max(int(abs(k[0])), 1),
                1
            )
            pg.draw.line(
                self.main_surface,
                CIRCLE_LINE_COLOR,
                xy_points[i],
                xy_points[i+1]
            )

    def run(self):
        dt = 0
        clock = pg.time.Clock()
        frame_counter = 0
        screenshot_index = 0

        while self.running:
            dt = clock.tick(FPS) / 1000  # seconds
            frame_counter += 1
            self.handle_input()
            if not self.paused:
                self.update_circles(dt)
            self.draw()
            pg.display.update()

            if SAVE_IMAGES and frame_counter % FPS_GIF == 1:
                # FIXME: frame_counter is the wront method for this!
                # I should use a cumulative dt instead.
                self.surface_storage[screenshot_index] = self.main_surface.copy()
                screenshot_index += 1

        if SAVE_IMAGES:
            self.save_screenshots(screenshot_index)

    def save_screenshots(self, max_len):
        # FIXME: If screenshot folder does not exist maybe ask user if they
        # want to create it?
        self.surface_storage = self.surface_storage[:max_len]
        print(f"Saving {len(self.surface_storage)} screenshots...", end = "")
        for i, s in enumerate(self.surface_storage):
            pg.image.save(
                s,
                self.screenshot_path + str(i).zfill(6) + ".png"
            )
        print(" done.")

if __name__ == "__main__":
    os.environ["SDL_VIDEO_CENTERED"] = "1"
    pg.init()
    Epicycles(EXAMPLE_STAR).run()
