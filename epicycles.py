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
from numpy.fft import ifft
import argparse
from pprint import pprint

# os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import pygame as pg


# TODO: Load harmonics from file if given a filename. Modify the file format
# output by the R script, i.e. remove the brackets and trailing commas.

# aalines don't look right. They always have some gaps in between them.
# So instead of using aalines I draw non-aalines but onto a big surface
# which gets smoothscaled down into the window. This produces a nice looking
# result, is fast and easy.

# This is the formula:
# a * exp(bj * t) + c
# a is the start position, abs(a) is the circle radius
# b is the speed and direction of the rotation (negative values rotate anticlockwise)
# j is sqrt(-1), usually denoted "i" in math and physics
# c is the position of the circle center

SAVE_IMAGES = False
SCREEN_WIDTH = 700
SCREEN_HEIGHT = 700
SMOOTH_SCALE_FACTOR = 2
SCREEN_CENTER = (
    SCREEN_WIDTH // 2 * SMOOTH_SCALE_FACTOR,
    SCREEN_HEIGHT // 2 * SMOOTH_SCALE_FACTOR
)
FPS = 60
BACKGROUND_COLOR = (255, 255, 255)
LINE_COLOR = (255, 0, 0)
CIRCLE_COLOR = (170, 170, 170)
CIRCLE_LINE_COLOR = (60, 60, 60)  # (255, 0, 0)
MIN_SPEED = 1/16
MAX_SPEED = 16
DEFAULT_SCALE_FACTOR = 0.8

EXAMPLE_DIAMOND = [
    [250, 1j],
    [250/9, -3j],
    [250/25, 5j],
    [250/49, -7j],
    [250/81, 9j],
    [250/121, -11j]
]
EXAMPLE_SQUARE_WAVE = [
    [180, 1j],
    [60, 3j],
    [36, 5j],
    [180/7, 7j],
    [20, 9j]
]


class Epicycles:
    """
    points_file: File containing the points of the image as x and y coordinates
        separated by whitespace and on seprate lines.
    n: Maximum number of harmonics.
    scale_factor: A number > 0 and <= 1 indicating how much of the width and
        height of the window the shape should occupy. To disable rescaling
        leave it at the default (None).
    """
    def __init__(self, points_file, n, scale_factor, fade):
        self.harmonics = self.transform(self.load_path(
            points_file, scale_factor
        ))
        if n is not None:
            if n > 0:
                self.harmonics = self.harmonics[:n]
            else:
                raise ValueError("n must be positive.")
        # pprint(self.harmonics)
        # Invert y-axis for pygame window:
        for i, h in enumerate(self.harmonics):
            z = h[0]
            self.harmonics[i][0] = complex(z.real, z.imag * -1)
        self.running = True
        self.last_point = None
        self.fade = fade
        self.angle = 0  # angle in radians
        self.angle_increment = 0
        self.paused = False
        self.circles_visible = True
        self.speed = 1  # speed of the innermost circle in radians/second
        self.main_surface = pg.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.big_surface = pg.Surface((
            SCREEN_WIDTH * SMOOTH_SCALE_FACTOR,
            SCREEN_WIDTH * SMOOTH_SCALE_FACTOR
        ))
        self.line_surface = self.big_surface.copy()
        self.line_surface.fill(BACKGROUND_COLOR)
        self.alpha_angle = 0
        # self.alpha_increment is best left at 10. Smaller numbers cause more
        # blits per frame of the transparent surface which may cause framerate
        # issues. Larger numbers make the line fade in a choppy looking way.
        self.alpha_increment = 10
        self.angle_per_alpha = math.tau / 255 * self.alpha_increment
        self.transp_surface = self.line_surface.copy()
        self.transp_surface.fill(
            (self.alpha_increment, self.alpha_increment, self.alpha_increment)
        )
        self.circle_points = [0j] * (len(self.harmonics) + 1)
        self.circle_points[0] = self.to_complex(SCREEN_CENTER)
        self.point = []
        self.update_circles(0)
        self.previous_point = self.point
        pg.display.set_caption("Epicycles")

    @staticmethod
    def to_complex(xy):
        return complex(xy[0], xy[1])

    @staticmethod
    def from_complex(z):
        return [z.real, z.imag]

    @staticmethod
    def load_path(points_file, scale_factor):
        x = []
        y = []
        with open(points_file, "r") as file:
            for line in file:
                xy = [float(i) for i in line.split()]
                x.append(xy[0])
                y.append(xy[1])

        if scale_factor != 0:
            if 0 < scale_factor <= 1:
                scale_factor *= SMOOTH_SCALE_FACTOR
                max_shape_x = SCREEN_WIDTH / 2 * scale_factor
                max_shape_y = SCREEN_HEIGHT / 2 * scale_factor
                if max_shape_x <= max_shape_y:
                    max_x = max(map(abs, x))
                    x = [i/max_x*max_shape_x for i in x]
                    y = [i/max_x*max_shape_x for i in y]
                else:
                    max_y = max(map(abs, y))
                    x = [i/max_y*max_shape_y for i in x]
                    y = [i/max_y*max_shape_y for i in y]
            else:
                raise ValueError(
                    "Argument 'scale_factor' must be between 0 and 1."
                )
        return [complex(*i) for i in zip(x, y)]

    @staticmethod
    def transform(path):
        transformed = ifft(path)
        transformed = list(transformed)
        transformed.pop(0)
        h = []
        i = 1
        sign = -1
        pop_back = True  # pop from the front or the back
        while transformed:
            radius = transformed.pop(-pop_back)
            if abs(radius) >= 0.1:
                h.append([radius, complex(0, sign * i)])
            if sign > 0:
                i += 1
            sign *= -1
            pop_back = not pop_back
        return h

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
                    self.speed = min(self.speed * 2, MAX_SPEED)
                elif event.key == pg.K_DOWN:
                    self.speed = max(self.speed / 2, MIN_SPEED)
                elif event.key == pg.K_BACKSPACE:
                    self.line_surface.fill(BACKGROUND_COLOR)
                # elif event.key == pg.K_a:
                #     print(self.angle)

    def update_circles(self, dt):
        self.angle_increment = self.speed * dt
        self.angle += self.angle_increment
        if self.angle > math.tau:
            self.angle -= math.tau

        for i, h in enumerate(self.harmonics):
            p = h[0] * math.e ** (h[1] * self.angle) + self.circle_points[i]
            self.circle_points[i+1] = p
        self.previous_point = self.point
        self.point = self.from_complex(self.circle_points[-1])

    def draw(self):
        if not self.paused:
            if self.fade:
                self.alpha_angle += self.angle_increment
                while self.alpha_angle > self.angle_per_alpha:
                    self.line_surface.blit(
                        self.transp_surface,
                        (0, 0),
                        special_flags=pg.BLEND_RGBA_ADD
                    )
                    self.alpha_angle -= self.angle_per_alpha
            pg.draw.line(
                self.line_surface,
                LINE_COLOR,
                self.previous_point,
                self.point,
                4
            )
            self.big_surface.blit(self.line_surface, (0, 0))

        if self.circles_visible:
            xy_points = [[int(xy) for xy in self.from_complex(i)]
                         for i in self.circle_points]
            for i, k in enumerate(self.harmonics):
                pg.draw.circle(
                    self.big_surface,
                    CIRCLE_COLOR,
                    xy_points[i],
                    max(int(abs(k[0])), 2),
                    2
                )
                pg.draw.line(
                    self.big_surface,
                    CIRCLE_LINE_COLOR,
                    xy_points[i],
                    xy_points[i+1],
                    2
                )
        pg.transform.smoothscale(
            self.big_surface,
            (SCREEN_WIDTH, SCREEN_HEIGHT),
            self.main_surface
        )

    def run(self):
        clock = pg.time.Clock()

        while self.running:
            dt = clock.tick(FPS) / 1000  # seconds
            self.handle_input()
            if not self.paused:
                self.update_circles(dt)
            self.draw()
            pg.display.update()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "file",
        help="Path to file containing the points of the shape."
    )
    parser.add_argument(
        "-n",
        type=int,
        help="Maximum number of harmonics or circles.",
        metavar="",
        default = None
    )
    parser.add_argument(
        "-s",
        "--scale_factor",
        type=float,
        metavar="",
        help="A number > 0 and <= 1 indicating how much of the width and " +
             "height of the window the shape should occupy. To disable " +
             f"rescaling set it to 0. Defaults to {DEFAULT_SCALE_FACTOR}.",
        default=DEFAULT_SCALE_FACTOR
    )
    parser.add_argument(
        "-f",
        "--fade",
        action="store_true",
        help="Fade the line over time so that it vanishes after one cycle."
    )
    args = parser.parse_args()

    os.environ["SDL_VIDEO_CENTERED"] = "1"
    pg.init()
    ec = Epicycles(
        args.file,
        args.n,
        args.scale_factor,
        args.fade
    )
    ec.run()
