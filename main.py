from hardware.linear_ccd_sensor import LinearCCDSensor
from hardware.encoder_wheel import EncoderWheelWithTopAndBottomStrips
from processing.line_fitter import LineFitter, split_vertically_by_threshold
from processing.y_shift_estimator import SensorYShiftEstimator, normalize, gauss_4
from visualisation.plotter import Plotter
from simulation.simulate_readouts import ReadoutGenerator
from matplotlib import pyplot
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


def get_longest_line_fragment(raw):
    image = normalize(raw)
    image = gauss_4(image)
    image = np.diff(image, n=2)

    threshold = 0.002  # very carefully chosen!
    fragments = []
    last_line_index = -1
    N = len(image)
    is_line = False
    for i in range(0, N):
        p = abs(image[i])
        if not is_line and p < threshold:
            is_line = True
            last_line_index = i
        if is_line and p > threshold:
            is_line = False
            fragments.append(Fragment(last_line_index, i+1))

    if is_line:
        fragments.append(Fragment(last_line_index, N))

    fragments.sort(key=lambda x: x.length, reverse=True)
    logging.debug(f"Fragments = {fragments}. Longest fragment = {fragments[0]}")
    return fragments[0]


def get_crossings(image, threshold):
    c = []

    s = "above" if image[0] > threshold else "under"
    i = 0
    for p in image:
        if s == "under" and p > threshold:
            c.append(i)
            s = "above"
        elif s == "above" and p < threshold:
            c.append(i)
            s = "under"

        i += 1
    return c


max_crossings = 32

class PointAlgo:
    def __init__(self, x, y, n, p):
        self.x = x
        self.y = y
        self.N = n
        self.percent = p


class RevisitedLineFitter:
    def __init__(self, wheel, sensor):
        self.R_um = wheel.radius_mm * 1000
        self.d_um = wheel.d_um
        self.delta_rad = np.pi * wheel.dphi_deg / 180.0
        self.px_um = sensor.dx

    def get_crossings(self, image):
        image = normalize(image)
        c = []


        k = np.arange(0.1, 1, (1.0/max_crossings))
        for t in k:
            raw_c = get_crossings(image, t)
            c += raw_c

        logger.info(f"Len c = {len(c)}")
        return c

    def get_beta_and_height(self, image):
        image = normalize(image)
        c = []
        k = np.arange(0.1, 1, (1.0/max_crossings))
        for t in k:
            raw_c = get_crossings(image, t)
            c += raw_c

        logger.info(f"Len c = {len(c)}")
        return c


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
    angles = np.arange(begin_angle, begin_angle + 1, 5000)*arcsek

    readout_generator = ReadoutGenerator(sensor, wheel, sensor_tilt_deg=1.4, sensor_shift_um=(3, -765))
    fitter = RevisitedLineFitter(wheel, sensor)

    useful_begin = 15
    useful_end = 112

    index = 0
    for a in angles:
        raw = readout_generator.for_angle(a)
        useful_raw = raw[useful_begin:useful_end]
        logger.info(f"Index = {index}. Angle = {a}")
        crossings = fitter.get_crossings(useful_raw)
        logger.info(f"Len crossings = {len(crossings)}")


        # diffs = [(current - last, t) for (current, last, t) in zip(crossings, last_crossings, thresholds)]
        # last_crossings = crossings
        # logger.info(f"Len diffs = {len(diffs)}")
        # well_behaved = np.array([(k, t) for (k, t) in diffs if abs(k) < c_threshold])
        # logger.info(f"Len well behaved = {len(well_behaved)}")
        # #betas[index, 0:len(well_behaved)] = well_behaved
        # if well_behaved.any() and index > 0:
        #     # print(f"Well behaved = {well_behaved}")
        #     ccccc, ttttt = zip(*well_behaved)
        #     def fffff(k):
        #         return 20*(1.0 - k)
        #     ttttt = np.array(ttttt)
        #     last_angle += np.average(ccccc)
        #     compare_angle += np.average(ccccc, weights=fffff(ttttt))
        # mean_cs[index] = last_angle
        # mean_cs_comp[index] = compare_angle
        # index += 1

    plotter = Plotter()
    angles = [int(3600*a) for a in angles]

    original_raw = useful_raw

    fragment = get_longest_line_fragment(original_raw)
    bbb = fragment.begin
    eee = fragment.end

    plotter.plot_simple(original_raw)
    plotter.get_axes().plot(range(bbb, eee), original_raw[bbb:eee])
    plotter.show_plot()






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
