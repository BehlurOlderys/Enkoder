import numpy as np


def normalize(image):
    amax = np.amax(image)
    amin = np.amin(image)
    amp = amax - amin
    if amp > 0.000001:
        image = (image - amin) / amp
    return image


def gauss_4(y):
    kernel = (1.0 / 64.0) * np.array([1, 6, 15, 20, 15, 6, 1])
    y_smooth = np.convolve(y, kernel, mode='same')
    return y_smooth


def gauss_5(y):
    kernel = (1.0 / 256.0) * np.array([1, 8, 28, 56, 70, 56, 28, 8, 1])
    y_smooth = np.convolve(y, kernel, mode='same')
    return y_smooth


def gauss_6(y):
    kernel = (1.0 / 1024.0) * np.array([1, 10, 45, 120, 210, 252, 210, 120, 45, 10, 1])
    y_smooth = np.convolve(y, kernel, mode='same')
    return y_smooth


def derivative(y):
    kernel = np.array([-0.5, 0, 0.5])
    y_smooth = np.convolve(y, kernel, mode='same')
    return y_smooth


def fit_parabola_to_three(x1, y1, x2, y2, x3, y3):
    denom = (x1 - x2) * (x1 - x3) * (x2 - x3)
    A = (x3 * (y2 - y1) + x2 * (y1 - y3) + x1 * (y3 - y2)) / denom
    B = (x3 * x3 * (y1 - y2) + x2 * x2 * (y3 - y1) + x1 * x1 * (y2 - y3)) / denom
    C = (x2 * x3 * (x2 - x3) * y1 + x3 * x1 * (x3 - x1) * y2 + x1 * x2 * (x1 - x2) * y3) / denom
    return A, B, C


def parabola_vertex(a, b, c):
    return -b / (2.0 * a), c - (b * b) / (4.0 * a)


def get_min_index(s):
    return np.argmin(s)


def get_max_index(s):
    return np.argmax(s)


def get_vertex_from_point(p_index, s):
    x1 = p_index
    x2 = x1 - 1
    x3 = x1 + 1
    y1 = s[x1]
    y2 = s[x2]
    y3 = s[x3]
    return parabola_vertex(*fit_parabola_to_three(x1, y1, x2, y2, x3, y3))


def get_extreme_subpixel(s, method=get_min_index):
    p_index = method(s)
    x, y = get_vertex_from_point(p_index, s)
    return x


class SensorYShiftEstimator:
    def __init__(self, sensor, wheel, N_first=28):
        self.sensor = sensor
        self.wheel = wheel
        self.N_first = N_first

    def _estimate(self, sample, method):
        g_sample = gauss_4(sample)  # todo: maybe 5? maybe 3?
        d_sample = derivative(g_sample)
        hhh = self.sensor.pixel_pitch_h_um
        extreme = get_extreme_subpixel(d_sample, method)
        y_subpixel = extreme * hhh
        return y_subpixel

    def estimate_bottom_edge(self, raw):
        ddd = self.sensor.pixel_w_um
        ad = self.wheel.distance_to_bottom_line_um + (ddd / 2.0)
        sample = normalize(raw[:self.N_first])
        return self._estimate(sample, method=get_min_index) + ad

    def estimate_top_edge(self, raw):
        sample = normalize(raw[-self.N_first:])
        hhh = self.sensor.pixel_pitch_h_um
        ddd = self.sensor.pixel_w_um
        y = self._estimate(sample, method=get_max_index)
        rev = hhh * self.N_first - y

        return -rev + self.sensor.width_um \
               - (self.wheel.distance_to_bottom_line_um +
                  self.wheel.line_height_um) + (ddd / 2.0)