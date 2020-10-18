
import numpy as np


def normalize(image):
    amax = 3600 #np.amax(image)
    amin = 0 #np.amin(image)
    amp = amax - amin
    if amp > 0.000001:
        image = (image - amin) / amp
    return image


def smooth(y, box_pts):
    box = np.ones(box_pts)/box_pts
    y_smooth = np.convolve(y, box, mode='same')
    return y_smooth


def get_first_above(y, threshold=0.5):
    starting_dir = y[0] < threshold
    for i in range(0, len(y)):
        direction = y[i] < threshold
        if direction is not starting_dir:
            return i


class Fragment:
    def __init__(self, begin, end):
        self.begin = begin
        self.end = end

    @property
    def length(self):
        return self.end - self.begin

    def __repr__(self):
        return f"[{self.begin}, {self.end})"


def get_slope_ranges(y):
    s = smooth(y, 5)
    i = get_first_above(s)
    print(f"Index of first above = {i}")
    return 0, 0


def get_estimate(image):
    image = smooth(image, 7)
    working_image = image[7:-7]


class Marker:
    def __init__(self, image, begin_index=10):
        self.image = image
        smoothed = smooth(image, 7)
        self.begin_index = begin_index
        self.working_image = smoothed[self.begin_index:-self.begin_index]

    def get_marks(self, thresholds):
        marks = []
        is_unders = []
        T = len(thresholds)
        for t in range(0, T):
            marks.append([])
            threshold = thresholds[t]
            is_unders.append(self.working_image[0] < threshold)

        for i in range(0, len(self.working_image)):
            p = self.working_image[i]
            for t in range(0, T):
                threshold = thresholds[t]
                if p < threshold and not is_unders[t]:
                    marks[t].append(i + self.begin_index)
                    is_unders[t] = True
                elif p > threshold and is_unders[t]:
                    marks[t].append(i + self.begin_index)
                    is_unders[t] = False

        print(f"Marks = {marks}")
        return marks


class EstimatorPreviousN:
    def __init__(self, N):
        self.N = N
        y_offset = 0.3
        self.x_offset = 10
        b_range = y_offset
        e_range = 1.0-y_offset
        self.thresholds = np.linspace(b_range, e_range, self.N)
        print(self.thresholds)
        self.previous = np.zeros(N)
        self.actual = np.zeros(N)
        self.T = len(self.thresholds)
        self.previous_marks = np.zeros(self.T)
        self.estimates = np.zeros(self.T)

    def estimate(self, readout):
        normalized_readout = normalize(readout)
        marker = Marker(normalized_readout)
        marks = marker.get_marks(self.thresholds)

        for t in range(0, self.T):
            if len(marks[t]) < 2:
                self.estimates[t] = -100
                continue

            mark_value = marks[t][-1]
            self.estimates[t] = mark_value - self.previous_marks[t]
            self.previous_marks[t] = mark_value

        print(f"Estimates = {self.estimates}")

        good_estimates = [e for e in self.estimates if e > -10 and e < 10]


        return np.average(good_estimates)
