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
        return c #[M - p for p in c]

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

class PointAlgo:
    def __init__(self, x, y, n, p):
        self.x = x
        self.y = y
        self.N = n
        self.percent = p


# class RevisitedLineFitter:
#     def __init__(self, wheel, sensor):
#         self.R_um = wheel.radius_mm * 1000
#         self.d_um = wheel.d_um
#         self.delta_rad = np.pi * wheel.dphi_deg / 180.0
#         self.px_um = sensor.dx
#
#     def get_crossings(self, image):
#         image = normalize(image)
#         c = []
#
#
#         k = np.arange(0.1, 1, (1.0/max_crossings))
#         for t in k:
#             raw_c = get_crossings(image, t)
#             c += raw_c
#
#         logger.info(f"Len c = {len(c)}")
#         return c
#
#     def get_beta_and_height(self, image):
#         image = normalize(image)
#         c = []
#         k = np.arange(0.1, 1, (1.0/max_crossings))
#         for t in k:
#             raw_c = get_crossings(image, t)
#             c += raw_c
#
#         logger.info(f"Len c = {len(c)}")
#         return c


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
    logger.debug(f"Creating line fitter...")

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



    index = 0
    angles = np.arange(begin_angle, begin_angle + 100, 1)*arcsek
    for a in angles:
        raw = readout_generator.for_angle(a)
        # raw = [ 0.0, 2.41706, 6.04265, 8.45971, 10.8768, 41.09, 170.403, 240.498, 255.0, 134.147, 53.1753, 42.2986, 39.8815, 38.673, 39.8815, 41.09, 41.09, 41.09, 39.8815, 39.8815, 39.8815, 39.8815, 41.09, 41.09, 42.2986, 42.2986, 43.5071, 47.1327, 45.9241, 44.7156, 49.5497, 55.5924, 56.8009, 54.3839, 64.0521, 74.9289, 73.7203, 78.5545, 89.4312, 101.517, 96.6824, 97.891, 113.602, 126.896, 122.062, 125.687, 138.981, 134.147, 145.024, 154.692, 161.943, 166.777, 155.9, 165.569, 180.071, 167.986, 172.82, 182.488, 187.322, 190.948, 189.739, 189.739, 188.531, 184.905, 180.071, 188.531, 201.825, 201.825, 171.611, 184.905, 182.488, 189.739, 196.99, 167.986, 166.777, 174.028, 174.028, 163.152, 152.275, 152.275, 143.815, 136.564, 130.521, 128.104, 113.602, 111.185, 102.725, 99.0995, 87.0142, 78.5545, 76.1374, 68.8862, 61.635, 65.2606, 64.0521, 61.635, 60.4265, 56.8009, 54.3839, 54.3839, 54.3839, 55.5924, 55.5924, 55.5924, 56.8009, 56.8009, 55.5924, 55.5924, 55.5924, 56.8009, 56.8009, 60.4265, 61.635, 64.0521, 65.2606, 65.2606, 66.4692, 64.0521, 65.2606, 72.5118, 83.3886, 84.5971, 88.2227, 96.6824, 108.768, 138.981, 143.815, 132.938 ]
        useful_raw = raw[useful_begin:]
        register_r.append(useful_raw)
        logger.info(f"Index = {index}. Angle = {a}")
        fragment = get_longest_line_fragment(useful_raw)
        logger.info(f"Fragment = {fragment}")
        bbb = fragment.begin
        eee = fragment.end
        x = range(bbb, eee)
        y = useful_raw[bbb:eee]
        linef = np.polyfit(x, y, 1)
        register_ab.append(linef)

        index += 1

    plotter = Plotter()
    A = 0.05
    B = 6159
    plotter.plot_simple([ A*(b - B) for (a, b) in register_ab]) #[90.0*(b - 1.8829)
    angles = [int(3600*a) - begin_angle for a in angles]
    plotter.plot_simple(angles)

    def plot_fragment(index):
        r = register_f[index]
        y = register_r[index]
        x = range(r.begin, r.end)
        plotter.get_axes().plot(x, y[r.begin: r.end])



    # x = range(r.begin, r.end)
    # plotter.plot_simple(register_f[0])
    # plotter.plot_simple(register_f[1])
    # plotter.plot_simple(register_c[3])
    # plotter.plot_simple(register_c[4])
    # plotter.plot_simple(register_c[5])
    # plotter.plot_simple(register_c[6])
    plotter.show_plot()

    original_raw = useful_raw

    # to consider:
    # register_f.append(fragment)
    #
    # before_measure = gauss_4(useful_raw[bbb:eee])[4:-4]
    #
    # crossings = get_crossings_of_line_segment(before_measure)
    # crossings = [p + bbb for p in crossings]
    # register_c.append(crossings)
    # diff_c = [new_c - old_c for (new_c, old_c) in zip(crossings, last_crossings)]
    # logger.info(f"AVERAGE diff = {np.average(diff_c)}")
    # last_crossings = crossings


    fragment = get_longest_line_fragment(original_raw)
    bbb = fragment.begin
    eee = fragment.end

    plotter.plot_simple(original_raw)
    plotter.plot_simple(original_raw)

    # line_to_measure = normalize(before_measure)
    # crossings = get_crossings_of_line_segment(line_to_measure)


    # plotter.plot_simple(30*normalize(before_measure))
    # plotter.get_axes().plot(range(4, -4), before_measure)






    # for k in range(0, max_readings):
    #    plotter.get_axes().plot(angles, betas[:, k])

    # plotter.get_axes().plot(angles, betas)
    # plotter.get_axes().plot(angles, hhhs)
    # plotter.get_axes().plot(angles, ttts)
    # plotter.get_axes().plot(angles, kkks)
    # plotter.show_plot()
    # plotter.reset()
    # plotter.plot_simple(normalize(raw_init))
    # plotter.plot_simple(normalize(raws[0]))
    # plotter.plot_simple(normalize(raws[1]))
    # plotter.plot_simple(normalize(raws[2]))
    # plotter.plot_simple(normalize(raws[3]))
    # plotter.plot_simple(normalize(raws[4]))
    # plotter.plot_simple(normalize(raws[5]))
    # plotter.plot_simple(normalize(raws[6]))
    # plotter.plot_simple(normalize(raws[7]))
    # plotter.plot_simple(normalize(raws[14]))
    # plotter.plot_simple(normalize(raws[15]))
    # plotter.plot_simple(normalize(raws[16]))
    # plotter.plot_simple(normalize(raws[17]))
    # plotter.plot_simple(normalize(raws[18]))
    # plotter.plot_simple(normalize(raws[19]))
    # plotter.plot_simple(normalize(raws[20]))
    # plotter.plot_simple(normalize(raws[21]))
    # plotter.plot_simple(raws[30])
    # plotter.plot_simple(raws[31])
    # plotter.plot_simple(raws[32])
    # plotter.plot_simple(raws[33])
    # plotter.plot_simple(raws[34])
    # plotter.plot_simple(raws[35])
    # plotter.plot_simple(raws[36])
    # plotter.plot_simple(raws[37])
    # N = 128
    # plotter.get_axes().plot(range(0, N), 0.25*np.ones(N))
    # plotter.get_axes().plot(range(0, N), 0.5*np.ones(N))
    # plotter.get_axes().plot(range(0, N), 0.75*np.ones(N))

    # plotter.plot_simple(np.correlate(raw_init, raws[1], "same"))
    # plotter.plot_simple(np.correlate(raw_init, raws[2], "same"))
    # plotter.get_axes().plot(angles, [h for (h, g) in hhhs])
    # plotter.get_axes().plot(angles, [g for (h, g) in hhhs])
    # plotter.get_axes().plot(angles, [180*b/np.pi for b in betas])
    # plotter.save_plot()
    # plotter.show_plot()
    # plotter.plot_simple(p_angles)
    # N = len(raw_stack)
    # crossings, coefficients, hills = fitter.fit_line(raw_stack)
    #
    #
    # crossings.pop(0)
    # hills.pop(0)
    #
    # init = crossings[0] + 1
    #
    # logger.info(f"Acquired {len(crossings)} crossings: {crossings}")
    # logger.info(f"Acquired {len(coefficients)} lines: {coefficients}")
    # logger.info(f"Acquired {len(hills)} hills: {hills}")
    #
    # for h in hills:
    #     r = [i for i in range(init, init + len(h))]
    #     print(len(h))
    #     plotter.get_axes().plot(r, h)
    #     init += len(h)
    #
    # for cross, coef in zip(crossings, coefficients):
    #     logger.debug(f"Crossing = {cross}")
    #     t = range(cross-10, cross+10)
    #     fit_y = [coef["a"] * x + coef["b"] for x in t]
    #     plotter.get_axes().plot(t, fit_y, color="green")
    #
