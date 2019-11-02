import logging
import numpy as np
import heapq

logger = logging.getLogger(__name__)


def smooth(y, box_pts):
    box = np.ones(box_pts)/box_pts
    return np.convolve(y, box, mode='same')


threshold_coefficient = 0.5


def strip_outliners(t, max_points, initial_tan):
    return heapq.nsmallest(max_points, t,
                           key=lambda x: abs(x.tan - initial_tan))


def split_vertically_by_threshold(data, threshold, raw_data=None):
    """
    Split data into continuous parts lying above and under threshold
    :param raw_data: data that will actually be sampled (default = same as data)
    :param data:
    :param threshold:
    :return: crossings is array of indices where crossing above/under threshold occurs
    """
    if raw_data is not None:
        raw_data = data
    crossings = []
    hills = []
    current_hill = []

    direction = "minus" if data[0] < threshold else "plus"

    p_index = 0
    for p in data:
        current_hill.append(raw_data[p_index])
        if direction == "minus":
            if p > threshold:
                direction = "plus"
                crossings.append(p_index)
                hills.append(current_hill.copy())
                current_hill = []
        elif direction == "plus":
            if p < threshold:
                direction = "minus"
                crossings.append(p_index)
                hills.append(current_hill.copy())
                current_hill = []
        p_index += 1
    hills.append(current_hill.copy())
    return crossings, hills


class PointWithProps:
    def __init__(self, x, y, tan, raw_data):
        self.x = x
        self.y = y
        self.raw_y = raw_data
        self.tan = tan

    def __repr__(self):
        return f"tan={self.tan}"


class LineFitter:
    def __init__(self, sensor):
        self.sensor = sensor

    def fit_line(self, raw_data):
        N = self.sensor.N
        smooth_data = smooth(raw_data, 5)
        data_y_range = np.ptp(raw_data)
        logger.debug(f"Data range = {data_y_range}")
        threshold = data_y_range*threshold_coefficient
        logger.debug(f"Treshold = {threshold}")
        crossings, hills = split_vertically_by_threshold(smooth_data, threshold, raw_data)
        logger.info(f"Found {len(hills)} hills and {len(crossings)} crossings.")
        logger.info(f"Crossings: {crossings}")

        hills.pop(0)
        hills.pop(-1)
        init = crossings[0]+1
        logger.debug(f"Found {len(hills)} hills and {len(crossings)} crossings.")

        full_stripes = len(hills)/2
        max_length_for_slopes = 100  # for 128
        av_slope_lenght = int((max_length_for_slopes / 2)/full_stripes)
        half_av_slope_len = int(av_slope_lenght / 2)
        two_thirds_av_slope = int(0.66*av_slope_lenght)
        logger.debug(f"Average length of slope: {av_slope_lenght}")
        for h in hills:
            r = [i for i in range(init, init + len(h))]
            print(len(h))
            # ax.plot(r, h)
            init += len(h)

        init_linear_range = 3
        slopes = []
        coefficients = []
        for c_index in crossings:
            logger.debug(f"Processing crossing at {c_index}")
            beg_slope = max(1,   c_index-half_av_slope_len)
            end_slope = min(N-1, c_index+half_av_slope_len)
            slope_len = end_slope-beg_slope
            logger.debug(f"Slope length = {slope_len}")
            if slope_len < av_slope_lenght:
                continue
            slopes.append([i for i in range(beg_slope, end_slope)])
            bx = c_index - init_linear_range
            ex = c_index + init_linear_range
            by = raw_data[c_index-init_linear_range]
            ey = raw_data[c_index+init_linear_range]
            inital_slope_tan = (ey - by)/(ex - bx)
            tans = [PointWithProps(i, smooth_data[i], (smooth_data[i] - smooth_data[i - 1]), raw_data[i]) for i in range(beg_slope, end_slope)]

            tans = strip_outliners(tans, two_thirds_av_slope, inital_slope_tan)

            min_x = min(tans, key=lambda e: e.x)
            max_x = max(tans, key=lambda e: e.x)
            logger.debug(f"Min x = {min_x.x}, max x = {max_x.x}")

            new_x = [p.x for p in tans]
            new_y = [p.raw_y for p in tans]
            [coeff_a, coeff_b] = np.polyfit(new_x, new_y, 1)
            coefficients.append({"a": coeff_a, "b": coeff_b})
            logger.debug(f"Model: y = {coeff_a}*x + {coeff_b}")



            logger.debug(f"Lenght of slope: {end_slope - beg_slope}, tans = {tans}")

            logger.debug(f"Initial_slope = {inital_slope_tan}")

            ttt = range(min_x.x, max_x.x)
            ttttt = range(min_x.x - 5, max_x.x + 5)
            fit_y = [coeff_a*x + coeff_b for x in ttt]
            fit_yyy = [coeff_a*x + coeff_b for x in ttttt]
            # ax.plot(ttttt, fit_yyy, color="blue")
            # ax.plot(ttt, fit_y, color="green")
            #rysuj_segment(ax, (beg_slope, aa[beg_slope], end_slope, aa[end_slope]))
        return crossings, coefficients, hills

