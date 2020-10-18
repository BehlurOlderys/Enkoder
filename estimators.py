
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


def get_fragments(image):
    image = smooth(image, 7)
    working_image = image[7:-7]
    ranges_above = []
    ranges_under = []
    above_b = -1
    under_b = -1
    threshold = 0.5
    threshold_above = 1 - threshold
    threshold_under = threshold
    is_above = False
    is_under = False
    for i in range(0, len(working_image)):
        p = working_image[i]
        if p < threshold_under and not is_under:
            under_b = i
            is_under = True
        elif p > threshold_under and is_under:
            ranges_under.append((under_b, i))
            is_under = False

        if p > threshold_above and not is_above:
            above_b = i
            is_above = True
        elif p < threshold_above and is_above:
            ranges_above.append((above_b, i))
            is_above = False

    M = len(working_image)-1
    if is_above:
        ranges_above.append((above_b, M))
    elif is_under:
        ranges_under.append((under_b, M))


    print(f"Ranges above = {ranges_above}, ranges under = {ranges_under}")
    return ranges_above, ranges_under



    # fragments.sort(key=lambda x: x.length, reverse=True)
    # logging.info(f"Fragments = {fragments}. Longest fragment = {fragments[0]}")


class EstimatorPreviousN:
    def __init__(self, N):
        self.N = N
        y_offset = 0.2
        self.x_offset = 10
        b_range = y_offset
        e_range = 1-y_offset
        self.thresholds = np.linspace(b_range, e_range, self.N)
        self.previous = np.zeros(N)
        self.actual = np.zeros(N)

    def estimate(self, readout):
        normalized_readout = normalize(readout)

        get_fragments(normalized_readout)

        actual_threshold_index = 0
        actual_threshold = self.thresholds[actual_threshold_index]
        for i in range(self.x_offset, len(readout)-self.x_offset):

            sample = normalized_readout[i]
            print(f"Sample = {sample}, actual_t = {actual_threshold}")
            if sample > actual_threshold:
                self.actual[actual_threshold_index] = i
                actual_threshold_index+=1
                if actual_threshold_index >= self.N:
                    break
                actual_threshold = self.thresholds[actual_threshold_index]

        diff = np.subtract(self.actual, self.previous)
        estimate = np.average(diff)
        print(f"Previous = {self.previous},\n actual = {self.actual},\n diff = {diff},\n mean diff = {estimate}")

        self.previous = self.actual.copy()

        return estimate

