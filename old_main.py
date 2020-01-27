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

grubosc_paska_mm = 0.128
N_paskow = 3600
obwod_mm = grubosc_paska_mm*N_paskow
R_mm = obwod_mm / (2*np.pi)
R_um = 1000*R_mm

# necessary to disable np debug nonsense:
logging.getLogger("matplotlib").propagate = False

logger = logging.getLogger(__name__)


class Fragment:
    def __init__(self, begin, end):
        self.begin = begin
        self.end = end

    @property
    def length(self):
        return self.end - self.begin

    def __repr__(self):
        return f"[{self.begin}, {self.end})"


class Correlator:
    def __init__(self, readout_t_us=200):
        self.phi_as = 0
        self.images = []
        self.readout_t_us = readout_t_us
        self.last_readout = 0
        self.N = 10
        self.difference_threshold = 1.0

    def update(self, new_image):
        if not self.images:
            self.images.append(new_image)
            return 0

        if self.N > 0:
            self.N -= 1
        else:
            self.N = 10
            self.images.insert(0, new_image)

        c = self._get_shift_in_pixels_between_images(new_image, self.images[-1])
        if len(self.images) > self.N and abs(self.last_readout - c) > self.difference_threshold:
            self.images.pop()

        self.last_readout = c
        return c

    def _get_shift_in_pixels_between_images(self, new_image, old_image):
        x_corr = np.correlate(new_image, old_image, "same")

        # plotter = Plotter()
        # plotter.plot_simple(new_image)
        # plotter.plot_simple(old_image)
        # plotter.plot_simple(x_corr)
        # plotter.show_plot()
        return np.argmax(x_corr)


def get_longest_line_fragment(image):

    image = savgol_filter(image, 25, 2)
    image = gauss_4(image)
    image = np.diff(image, n=1)[4:-5]
    # plotter = Plotter()
    # plotter.plot_simple(image)
    # # plotter.plot_simple(image)
    # plotter.show_plot()

    threshold = (max(image) - min(image)) / 10.0
    fragments = []
    last_line_index = 0
    N = len(image)
    is_line = True
    for i in range(0, N):
        p = abs(image[i])
        if is_line and p < threshold:
            fragments.append(Fragment(last_line_index, i+2))
            is_line = False
        if not is_line and p > threshold:
            is_line = True
            last_line_index = i

    if is_line:
        fragments.append(Fragment(last_line_index, N))

    fragments.sort(key=lambda x: x.length, reverse=True)
    # logging.info(f"Fragments = {fragments}. Longest fragment = {fragments[0]}")
    return fragments[0]


def get_crossings_of_line_segment(image):
    e2e_diff = image[-1] - image[0]
    if e2e_diff < 0:
        c = get_crossings_of_line_segment([p for p in reversed(image)])
        M = len(c)
        return [M - p for p in c]

    N = len(image)
    image = normalize(image)
    c = []
    last_threshold_index = 0

    thresholds = np.arange(0, 1, 1/N)
    M = len(thresholds)
    for i in range(0, N):
        p = image[i]
        while last_threshold_index < M and p > thresholds[last_threshold_index]:
            c.append(i)
            last_threshold_index += 1
    return c


max_crossings = 32

history_period_arcsek = 1296000.0 / N_paskow


class HistoricalCrossing:
    def __init__(self, value, direction, phi_arcsek):
        self.value = value
        self.direction = direction
        self.phi_arcsek = phi_arcsek
        self.fresh = True

    def get_phi(self):
        return self.phi_arcsek

    def set_ready(self):
        self.fresh = False

    def is_fresh(self):
        return self.fresh

    def is_ok_for_update(self, current_phi_arcsek, current_dir):
        predicted = self.phi_arcsek + history_period_arcsek
        return (current_dir == self.direction) and abs(predicted - current_phi_arcsek) < history_period_arcsek*0.2

    def __repr__(self):
        return ("rising" if self.direction is True else "falling") + f"@{self.phi_arcsek}"


N_pikseli = 128 # tsl1401
history_of_crossings = {}
for i in range(0, N_pikseli):
    history_of_crossings[i] = None


def update_history_of_crossings(raw, current_phi_arcsek):
    threshold = 0.5
    image = normalize(raw)
    image = savgol_filter(image, 25, 2)
    image = gauss_4(image)[4:-5]
    rising = True if (image[0] < threshold) else False

    def set_point_in_history(i, rising):
        if history_of_crossings[i] is None:
            history_of_crossings[i] = HistoricalCrossing(i, rising, current_phi_arcsek)
        elif history_of_crossings[i].is_fresh():
            history_of_crossings[i] = HistoricalCrossing(i, rising, current_phi_arcsek)
        elif history_of_crossings[i].is_ok_for_update(current_phi_arcsek, rising):
            updated_phi = history_of_crossings[i].get_phi() + history_period_arcsek
            history_of_crossings[i] = HistoricalCrossing(i, rising, current_phi_arcsek)
            return updated_phi
        return -1.0

    updates = []
    for i in range(0, len(image)):
        p = image[i]
        if rising and p > threshold:
            rising = False
            updates.append(set_point_in_history(i, rising))
        elif not rising and p < threshold:
            rising = True
            updates.append(set_point_in_history(i, rising))

    for i in range(0, len(image)):
        if history_of_crossings[i] is not None:
            history_of_crossings[i].set_ready()

    # logger.info(f"History = {history_of_crossings}")
    updates = [u for u in updates if u > 0]
    if not updates:
        return current_phi_arcsek

    updated_phi = np.average(np.array(updates))

    best_phi = current_phi_arcsek*0.1 + updated_phi*0.9
    logging.info(f"---------UPDATING! {current_phi_arcsek} ===> {best_phi} with {updated_phi}")
    return best_phi



class PointAlgo:
    def __init__(self, x, y, n, p):
        self.x = x
        self.y = y
        self.N = n
        self.percent = p


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

    grubosc_czarnego_um = grubosc_paska_mm*1000*0.5
    odleglosc_dolnego_paska = 6*grubosc_czarnego_um
    grubosc_dolnego_paska = 3*grubosc_czarnego_um
    wheel = EncoderWheelWithTopAndBottomStrips(R_mm, N_paskow, 6.4, odleglosc_dolnego_paska) #, grubosc_dolnego_paska)

    arcsek = 0.1/360  # 1/3600 of one degree
    begin_angle = 100

    readout_generator = ReadoutGenerator(sensor, wheel, sensor_tilt_deg=1.4, sensor_shift_um=(3, -765))
    # fitter = RevisitedLineFitter(wheel, sensor)

    useful_begin = 15
    # useful_end = 112

    last_crossings = np.zeros(128)

    register_r = []
    register_ab = []
    register_c = []
    register_f = []
    register_fi = []
    register_L = []



    actual_estimate_fi = None
    last_fi = 0
    last_dfi = 0

    last_c = None
    index = 0

z
    c3 = 0
    last_image = None
    correlator = Correlator()

    angles = np.arange(begin_angle, begin_angle + 720, 2)*arcsek
    for angle in angles:
        raw = readout_generator.for_angle(angle)
        #raw = [ 0.0, 5.39682, 12.1429, 21.5873, 32.3809, 37.7778, 41.8254, 47.2222, 52.619, 163.254, 248.254, 255.0, 215.873, 147.063, 111.984, 110.635, 125.476, 117.381, 125.476, 129.524, 130.873, 138.968, 145.714, 149.762, 151.111, 151.111, 155.159, 155.159, 168.651, 175.397, 170.0, 170.0, 178.095, 183.492, 184.841, 190.238, 190.238, 203.73, 201.032, 210.476, 203.73, 219.921, 226.667, 226.667, 236.111, 238.809, 241.508, 245.555, 241.508, 241.508, 246.905, 226.667, 228.016, 233.413, 225.317, 240.159, 238.809, 240.159, 241.508, 249.603, 238.809, 223.968, 242.857, 252.302, 248.254, 245.555, 238.809, 238.809, 222.619, 219.921, 222.619, 222.619, 213.174, 211.825, 203.73, 198.333, 201.032, 201.032, 194.286, 196.984, 190.238, 184.841, 187.54, 186.19, 176.746, 174.048, 168.651, 170.0, 167.302, 167.302, 167.302, 161.905, 160.555, 149.762, 148.413, 149.762, 144.365, 137.619, 143.016, 134.921, 137.619, 133.571, 126.825, 120.079, 116.032, 114.682, 116.032, 114.682, 114.682, 114.682, 113.333, 113.333, 113.333, 114.682, 113.333, 113.333, 114.682, 114.682, 114.682, 114.682, 114.682, 114.682, 114.682, 116.032, 116.032, 136.27, 174.048, 179.444 ]
        #raw = [ 0.0, 2.41706, 6.04265, 8.45971, 10.8768, 41.09, 170.403, 240.498, 255.0, 134.147, 53.1753, 42.2986, 39.8815, 38.673, 39.8815, 41.09, 41.09, 41.09, 39.8815, 39.8815, 39.8815, 39.8815, 41.09, 41.09, 42.2986, 42.2986, 43.5071, 47.1327, 45.9241, 44.7156, 49.5497, 55.5924, 56.8009, 54.3839, 64.0521, 74.9289, 73.7203, 78.5545, 89.4312, 101.517, 96.6824, 97.891, 113.602, 126.896, 122.062, 125.687, 138.981, 134.147, 145.024, 154.692, 161.943, 166.777, 155.9, 165.569, 180.071, 167.986, 172.82, 182.488, 187.322, 190.948, 189.739, 189.739, 188.531, 184.905, 180.071, 188.531, 201.825, 201.825, 171.611, 184.905, 182.488, 189.739, 196.99, 167.986, 166.777, 174.028, 174.028, 163.152, 152.275, 152.275, 143.815, 136.564, 130.521, 128.104, 113.602, 111.185, 102.725, 99.0995, 87.0142, 78.5545, 76.1374, 68.8862, 61.635, 65.2606, 64.0521, 61.635, 60.4265, 56.8009, 54.3839, 54.3839, 54.3839, 55.5924, 55.5924, 55.5924, 56.8009, 56.8009, 55.5924, 55.5924, 55.5924, 56.8009, 56.8009, 60.4265, 61.635, 64.0521, 65.2606, 65.2606, 66.4692, 64.0521, 65.2606, 72.5118, 83.3886, 84.5971, 88.2227, 96.6824, 108.768, 138.981, 143.815, 132.938 ]
        useful_raw = raw[useful_begin:]


        c3 = correlator.update(useful_raw[:97])



        #register_r.append(useful_raw)
        fragment = get_longest_line_fragment(useful_raw)
        # logger.info(f"Fragment = {fragment}")

        bbb = fragment.begin
        eee = fragment.end
        x = range(bbb, eee)
        y = useful_raw[bbb:eee]


        # plotter = Plotter()
        # plotter.plot_simple(useful_raw)
        # plotter.get_axes().plot(x, y)
        # plotter.show_plot()

        linef = np.polyfit(x, y, 1)
        a, b = linef
        c = -b/a

        L = len(y)
        Lt = int(L/4)
        # crossings are pixel indices for which image is above certain thresholds
        c2 = bbb+np.average(get_crossings_of_line_segment(y)[Lt: -Lt])
        # c2 is ignored anyway. It gives also nice estimate

        c = c3

        #register_c.append(c)

        dy_inaccurate_but_sane = fragment.length
        dy = get_width_of_stripe_in_pixels(useful_raw[:97], dy_inaccurate_but_sane)
        used = "calculated"
        threshold_of_sanity = 0.8
        if (abs(dy - dy_inaccurate_but_sane) > threshold_of_sanity*dy_inaccurate_but_sane):
            dy = dy_inaccurate_but_sane
            used = "sane"

        # logger.info(f"DY calculated = {dy}, DY working nice = {fragment.length+5}, used = {used}")

        aaa = 64.0 / dy
        if last_c is None:
            c_diff = 0
        else:
            c_diff = c - last_c

        last_c = c

        dx = c_diff * aaa
        R_real = R_um
        dfi = 1296000 * dx / (2.0 * np.pi * R_real)
        # logger.info(f"c = {c}[px], c_diff={c_diff}[px], aaa={aaa}[um/px], dx = {dx}[um], dfi = {dfi}[arcsek]")
        #register_fi.append(dfi)

        if actual_estimate_fi is None:
            actual_estimate_fi = 0
            register_f.append(0)
        else:
            actual_estimate_fi += (dfi if abs(dfi) < 100 else last_dfi)
            register_f.append(actual_estimate_fi)

        actual_estimate_fi = update_history_of_crossings(useful_raw[:97], actual_estimate_fi)

        logger.info(f"Index = {index}. Angle = {angle/arcsek - begin_angle}\". Actual estimate = {actual_estimate_fi}\"")
        last_dfi = dfi
        # dx = c - last_c
        # last_c = c
        # Real_R = R_um + c*63.5
        # dfi = 3600 * 180 * dx / (np.pi * Real_R)
        # if not first_fi:
        #     first_fi = dfi
        #     register_f.append(0)
        # else:
        #     last_fi += dfi
        #     register_f.append(last_fi)


        #register_ab.append(linef)

        index += 1

    plotter = Plotter()
    A = 0.05
    B = 6159
    # plotter.plot_simple(register_fi) #[90.0*(b - 1.8829)
    plotter.plot_simple(register_f) #[90.0*(b - 1.8829)
    # pyplot.hist(register_fi)
    # plotter.plot_simple(register_c) #[90.0*(b - 1.8829)
    angles = [int(3600*a) - begin_angle for a in angles]
    plotter.plot_simple(angles)
    plotter.plot_simple([a - b for (a, b) in zip(angles, register_f)])
    # plotter.plot_simple([a/b if b is not 0 else 0 for a, b in zip(angles, register_f)])

    def plot_fragment(index):
        r = register_f[index]
        y = register_r[index]
        x = range(r.begin, r.end)
        plotter.get_axes().plot(x, y[r.begin: r.end])

    plotter.show_plot()

    original_raw = useful_raw

    fragment = get_longest_line_fragment(original_raw)
    bbb = fragment.begin
    eee = fragment.end

    plotter.plot_simple(original_raw)

    # line_to_measure = normalize(before_measure)
    # crossings = get_crossings_of_line_segment(line_to_measure)


