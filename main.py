from hardware.linear_ccd_sensor import LinearCCDSensor
from hardware.encoder_wheel import EncoderWheelWithTopAndBottomStrips
from processing.line_fitter import LineFitter, split_vertically_by_threshold
from scipy.ndimage import gaussian_filter1d
from processing.y_shift_estimator import SensorYShiftEstimator, normalize, gauss_4, gauss_5, gauss_6
from visualisation.plotter import Plotter
from simulation.simulate_readouts import ReadoutGenerator
from matplotlib import pyplot
from scipy.interpolate import interp1d
from scipy.signal import savgol_filter
import numpy as np
import json
import argparse
import logging
from config.config_utils import get_default_sensors_config

useful_begin = 15
constant_as_to_deg = 0.1/360  # 1/3600 of one degree
constant_deg_to_as = 3600
sensitivity_threshold_as = 100
grubosc_paska_mm = 0.128
N_paskow = 3600
pasek_as = 1296000 / N_paskow
obwod_mm = grubosc_paska_mm*N_paskow
R_mm = obwod_mm / (2*np.pi)
R_um = 1000*R_mm
grubosc_czarnego_um = grubosc_paska_mm*1000*0.5
stripe_width_um = grubosc_czarnego_um
odleglosc_dolnego_paska = 6*grubosc_czarnego_um

constant_um_to_as = 1296000.0 / (2.0 * np.pi * R_um)

# necessary to disable np debug nonsense:
logging.getLogger("matplotlib").propagate = False

logger = logging.getLogger(__name__)

history_period_arcsek = 1296000.0 / N_paskow


def get_one_width(image, threshold):
    rising = True if image[0] < threshold else False
    map_of_crossings = {}
    larger = False
    for i in range(0, len(image)):
        p = image[i]
        if rising and p > threshold:
            map_of_crossings[rising] = i
            larger = rising
            rising = False
        if not rising and p < (1.0 - threshold):
            map_of_crossings[rising] = i
            larger = rising
            rising = True

    if True in map_of_crossings and False in map_of_crossings:
        return map_of_crossings[larger] - map_of_crossings[not larger]
    return 0


def get_width_of_stripe_in_pixels(raw, sane_estimate):
    threshold_of_sanity = 0.8
    image = normalize(raw)
    thresholds = np.arange(0, 1, 0.1)
    samples = [get_one_width(image, p) for p in thresholds]

    def is_sane(x):
        return abs(x - sane_estimate) < threshold_of_sanity * sane_estimate

    useful_samples = np.array([p for p in samples if is_sane(p)])
    return np.median(useful_samples) if useful_samples.any() else 0



class HistoricalCrossing:
    def __init__(self, value, direction, phi_arcsek):
        self.value = value
        self.direction = direction
        self.ready = False
        self.phi_arcsek = phi_arcsek
        self.fresh = True

    def get_phi(self):
        return self.phi_arcsek

    def set_ready(self):
        self.ready = True

    def change_direction(self):
        self.direction = not self.direction

    def is_ready(self):
        return self.ready

    def is_old_enough(self, current_fi_as):
        if self.phi_arcsek is None:
            return False
        predicted = self.phi_arcsek + history_period_arcsek
        return abs(predicted - current_fi_as) < history_period_arcsek*0.2

    def is_ok_for_update(self, current_fi_as, current_dir):
        return (not (current_dir == self.direction)) and self.is_old_enough(current_fi_as)

    def __repr__(self):
        phi_to_repr = self.phi_arcsek if self.phi_arcsek is not None else "NONE"
        return ("rising" if self.direction is True else "falling") + f"@{phi_to_repr}"


threshold_first = 0.5


class ImageGetter:
    def __init__(self, image):
        self.image = image
        self.normalized = None

    def get_normalized(self):
        if self.normalized is None:
            self.normalized = normalize(self.image)
        return self.normalized




class CrudestEstimator:
    def __init__(self):
        self.history = None
        self.control_pixel_index = None

    def get_control_pixel_index(self, image):
        starting_dir = image[0] < threshold_first
        for i in range(0, len(image)):
            direction = image[i] < threshold_first
            if direction is not starting_dir:
                return i

        raise Exception("something is bad")

    def update_with_global(self, fi_as, raw_image):
        image = normalize(raw_image)
        if self.control_pixel_index is None:
            self.control_pixel_index = self.get_control_pixel_index(image)

        v = image[self.control_pixel_index]
        direction = v > threshold_first
        if self.history is None:
            self.history = HistoricalCrossing(v, direction, 0)
            return 0

        if self.history.is_ok_for_update(fi_as, direction):
            logger.info(f"----------- update!")
            previous = self.history.phi_arcsek
            new_phi = previous + pasek_as
            self.history = HistoricalCrossing(v, not direction, new_phi)
            return new_phi
        #
        #
        #
        # else:
        #     if not self.history.direction == direction:
        #         logger.info("-----------direction changed!")
        #         if not self.history.is_ready():
        #             self.history.set_ready()
        #             self.history.change_direction()
        #         else:
        #             if previous is None:
        #                 self.history = HistoricalCrossing(v, direction, 0)
        #                 return 0
        #             new_phi = previous + pasek_as
        #             self.history = HistoricalCrossing(v, direction, new_phi)
        #             return new_phi

        return fi_as


finer_threshold = 2


class FinerEstimator:
    def __init__(self):
        self.last_x = None
        self.last_image = None
        self.oldest_image = None
        self.middle_px = None
        self.xcorr_scale = 10.0

    def prepare_image(self, raw):
        image = np.array(raw) - np.average(raw)

        x = np.arange(0, len(image))
        f = interp1d(x, image, 'quadratic')
        tick = 1.0 / self.xcorr_scale
        xnew = np.arange(0, len(raw)-1, tick)
        ynew = f(xnew)  # use interpolation function returned by `interp1d`
        return ynew

    def calculate_shift_px(self, prepared):
        x_corr = np.correlate(prepared[100:-100], self.last_image, "valid")
        # plotter = Plotter()
        # plotter.plot_simple(prepared)
        # plotter.plot_simple(self.last_image)
        # plotter.plot_simple(normalize(x_corr))
        # plotter.show_plot()

        N = len(self.last_image)
        maximum_x = np.argmax(x_corr) - 100
        return maximum_x / self.xcorr_scale

    def get_dx_px(self, image):
        if self.last_image is None:
            self.last_image = self.prepare_image(image)
            self.last_x = 0
            return 0

        interpolated = self.prepare_image(image)
        raw_shift = self.calculate_shift_px(interpolated)
        shift_px = raw_shift - self.last_x
        # logger.info(f"shift_px = {shift_px}")
        if abs(raw_shift) > finer_threshold:
            self.last_image = interpolated
            self.last_x = 0
        else:
            self.last_x += shift_px
        return shift_px


 # for i in range(0, len(image)):
 #        p = image[i]
 #        if rising and p > threshold:
 #            rising = False
 #            updates.append(set_point_in_history(i, rising))
 #        elif not rising and p < threshold:
 #            rising = True
 #            updates.append(set_point_in_history(i, rising))


def calculate_dfi_as(width_of_stripe_px, pixel_difference_from_last_reading):
    if width_of_stripe_px == 0 or R_um == 0:
        return 0

    pixel_to_xaxis_um_coefficient = float(stripe_width_um) / float(width_of_stripe_px)
    dx_um = float(pixel_difference_from_last_reading) * pixel_to_xaxis_um_coefficient
    dfi_as = constant_um_to_as * dx_um
    return dfi_as


class SimplestEstimator:
    def __init__(self):
        self.last_difference = {}
        self.last_index = {}
        self.gaussed = None

    def get_first_above(self, image, threshold=0.5):
        starting_dir = image[0] < threshold
        for i in range(0, len(image)):
            direction = image[i] < threshold
            if direction is not starting_dir:
                return i

    def get_first_under(self, image, threshold):
        starting_dir = image[0] > threshold
        for i in range(0, len(image)):
            direction = image[i] > threshold
            if direction is not starting_dir:
                return i

    def get_dx_px(self, raw, percents=50, low=False):
        image = gauss_6(raw)[6:-6]
        image = normalize(image)


        # plotter = Plotter()
        # plotter.plot_simple(image)
        # plotter.show_plot()


        current_index = self.get_first_under(image, percents/100.0) if low else self.get_first_above(image, percents/100.0)
        if percents not in self.last_index:
            self.last_index[percents] = {low: current_index}
            self.last_difference[percents] = {low: 0}
            return 0, None
        elif low not in self.last_index[percents]:
            self.last_index[percents][low] = current_index
            self.last_difference[percents][low] = 0
            return 0, None
        else:
            low_threshold_px = 3
            high_threshold_px = 20

            difference_px = current_index - self.last_index[percents][low]
            if difference_px > 0 and difference_px < low_threshold_px:
                self.last_index[percents][low] = current_index
                self.last_difference[percents][low] = difference_px
                return difference_px, current_index
            elif difference_px < -low_threshold_px:
                temp_last_index = self.last_index[percents][low]
                self.last_index[percents][low] = current_index
                return self.last_difference[percents][low], temp_last_index
            else:
                return 0, None


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config_for_sensors", default=get_default_sensors_config())
    parser.add_argument("-l", "--log_level", default=20)
    args = parser.parse_args()

    logging.basicConfig(level=args.log_level,
                        format="%(asctime)s %(levelname)s [%(name)s] %(message)s")

    logger.debug(f"Opening config file from {args.config_for_sensors}")
    with open(args.config_for_sensors) as f:
        sensor_config_json = json.load(f)

    logger.debug(f"Creating instance of sensor...")
    sensor = LinearCCDSensor.from_json(sensor_config_json["TSL1401"])
    logger.info(sensor)

    wheel = EncoderWheelWithTopAndBottomStrips(R_mm, N_paskow, 10, odleglosc_dolnego_paska) #, grubosc_dolnego_paska)

    # Main loop:
    begin_angle_as = 0
    actual_estimate_fi_as = None  # as is short for arcsecond, obviously
    last_dfi_as = 0
    index = 0
    angles_deg = np.arange(begin_angle_as, begin_angle_as + 720, 0.5)*constant_as_to_deg
    r_angles = constant_as_to_deg * (0.5 - np.random.rand(len(angles_deg)))
    angles_deg = np.add(angles_deg, r_angles)
    register_fi = []

    readout_generator = ReadoutGenerator(sensor, wheel, sensor_tilt_deg=1.4, sensor_shift_um=(0, -765))
    crudest_estimator = CrudestEstimator()
    finer_estimator = FinerEstimator()
    simplest_estimator = SimplestEstimator()

    for angle_deg in angles_deg:
        raw = readout_generator.for_angle(angle_deg)
        #raw = [ 0.0, 5.39682, 12.1429, 21.5873, 32.3809, 37.7778, 41.8254, 47.2222, 52.619, 163.254, 248.254, 255.0, 215.873, 147.063, 111.984, 110.635, 125.476, 117.381, 125.476, 129.524, 130.873, 138.968, 145.714, 149.762, 151.111, 151.111, 155.159, 155.159, 168.651, 175.397, 170.0, 170.0, 178.095, 183.492, 184.841, 190.238, 190.238, 203.73, 201.032, 210.476, 203.73, 219.921, 226.667, 226.667, 236.111, 238.809, 241.508, 245.555, 241.508, 241.508, 246.905, 226.667, 228.016, 233.413, 225.317, 240.159, 238.809, 240.159, 241.508, 249.603, 238.809, 223.968, 242.857, 252.302, 248.254, 245.555, 238.809, 238.809, 222.619, 219.921, 222.619, 222.619, 213.174, 211.825, 203.73, 198.333, 201.032, 201.032, 194.286, 196.984, 190.238, 184.841, 187.54, 186.19, 176.746, 174.048, 168.651, 170.0, 167.302, 167.302, 167.302, 161.905, 160.555, 149.762, 148.413, 149.762, 144.365, 137.619, 143.016, 134.921, 137.619, 133.571, 126.825, 120.079, 116.032, 114.682, 116.032, 114.682, 114.682, 114.682, 113.333, 113.333, 113.333, 114.682, 113.333, 113.333, 114.682, 114.682, 114.682, 114.682, 114.682, 114.682, 114.682, 116.032, 116.032, 136.27, 174.048, 179.444 ]
        #raw = [ 0.0, 2.41706, 6.04265, 8.45971, 10.8768, 41.09, 170.403, 240.498, 255.0, 134.147, 53.1753, 42.2986, 39.8815, 38.673, 39.8815, 41.09, 41.09, 41.09, 39.8815, 39.8815, 39.8815, 39.8815, 41.09, 41.09, 42.2986, 42.2986, 43.5071, 47.1327, 45.9241, 44.7156, 49.5497, 55.5924, 56.8009, 54.3839, 64.0521, 74.9289, 73.7203, 78.5545, 89.4312, 101.517, 96.6824, 97.891, 113.602, 126.896, 122.062, 125.687, 138.981, 134.147, 145.024, 154.692, 161.943, 166.777, 155.9, 165.569, 180.071, 167.986, 172.82, 182.488, 187.322, 190.948, 189.739, 189.739, 188.531, 184.905, 180.071, 188.531, 201.825, 201.825, 171.611, 184.905, 182.488, 189.739, 196.99, 167.986, 166.777, 174.028, 174.028, 163.152, 152.275, 152.275, 143.815, 136.564, 130.521, 128.104, 113.602, 111.185, 102.725, 99.0995, 87.0142, 78.5545, 76.1374, 68.8862, 61.635, 65.2606, 64.0521, 61.635, 60.4265, 56.8009, 54.3839, 54.3839, 54.3839, 55.5924, 55.5924, 55.5924, 56.8009, 56.8009, 55.5924, 55.5924, 55.5924, 56.8009, 56.8009, 60.4265, 61.635, 64.0521, 65.2606, 65.2606, 66.4692, 64.0521, 65.2606, 72.5118, 83.3886, 84.5971, 88.2227, 96.6824, 108.768, 138.981, 143.815, 132.938 ]
        useful_raw = raw[useful_begin:]

        # plotter = Plotter()
        # plotter.plot_simple(useful_raw)
        # plotter.show_plot()

        # pixel_difference_from_last_reading = finer_estimator.get_dx_px(useful_raw)

        # dx1, i = simplest_estimator.get_dx_px(useful_raw, 20, True)
        dx2, i = simplest_estimator.get_dx_px(useful_raw, 25, True)
        # dx3, i = simplest_estimator.get_dx_px(useful_raw, 40, True)
        dx4, i = simplest_estimator.get_dx_px(useful_raw, 50, True)
        # dx5, i = simplest_estimator.get_dx_px(useful_raw, 60, True)
        dx6, i = simplest_estimator.get_dx_px(useful_raw, 75, True)
        # dx7, i = simplest_estimator.get_dx_px(useful_raw, 80, True)
        pixel_difference_from_last_reading = 0.3333 * (dx2 + dx4 + dx6) #dx4 #(dx1 + dx2 + dx3 + dx4 + dx5 + dx6 + dx7) / 7.0
        # dx_values = []
        # for i in range(1, 10):
        #     i_threshold = 10*i
        #     dx_value, dx_index = simplest_estimator.get_dx_px(useful_raw, i_threshold, True)
        #     dx_values.append((dx_value, dx_index))
        #     dx_value, dx_index = simplest_estimator.get_dx_px(useful_raw, i_threshold, False)
        #     dx_values.append((dx_value, dx_index))
        #
        # dx_values = [(d, i) for (d, i) in dx_values if i is not None]
        # dx_values = sorted(dx_values, reverse=False, key=lambda d: d[-1])
        #
        # logger.info(f"Values = {dx_values}")
        #
        # dx_values = [d for (d, i) in dx_values[:10]]
        # # dx_values =
        #
        # logger.info(f"Values = {dx_values}")
        # pixel_difference_from_last_reading = np.mean([d for d in dx_values if d < 32]) if dx_values else 0
        # pixel_difference_from_last_reading, dx_index = simplest_estimator.get_dx_px(useful_raw, 50)
        width_of_stripe_px = 45.0  # TODO

        #############
        dy_inaccurate_but_sane = 45.0
        dy = get_width_of_stripe_in_pixels(useful_raw, dy_inaccurate_but_sane)
        threshold_of_sanity = 0.8
        if (abs(dy - dy_inaccurate_but_sane) > threshold_of_sanity * dy_inaccurate_but_sane):
            dy = dy_inaccurate_but_sane
        ##########
        # width_of_stripe_px = dy

        # logger.info(f"DY calculated = {dy}, DY working nice = {fragment.length+5}, used = {used}")


        # To first approximation this should not change much:
        dfi_as = calculate_dfi_as(width_of_stripe_px, pixel_difference_from_last_reading)

        if actual_estimate_fi_as is None:
            actual_estimate_fi_as = 0
        else:
            actual_estimate_fi_as += (dfi_as if abs(dfi_as) < sensitivity_threshold_as else last_dfi_as)
            last_dfi_as = dfi_as

        actual_estimate_fi_as = crudest_estimator.update_with_global(actual_estimate_fi_as, useful_raw)

        relative_angle_as = angle_deg*constant_deg_to_as - begin_angle_as
        logger.info(f"Index = {index}. "
                    f"Angle = {relative_angle_as}\". "
                    f"Actual estimate = {actual_estimate_fi_as}\"")

        register_fi.append(actual_estimate_fi_as)
        index += 1

    plotter = Plotter()
    plotter.plot_simple(register_fi)
    angles = [int(3600 * a) - begin_angle_as for a in angles_deg]
    plotter.plot_simple(angles)
    plotter.plot_simple([a - b for (a, b) in zip(angles, register_fi)])
    plotter.show_plot()
    plotter.save_plot()
