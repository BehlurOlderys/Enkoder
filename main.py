from hardware.linear_ccd_sensor import LinearCCDSensor
from hardware.encoder_wheel import EncoderWheel
from processing.line_fitter import LineFitter, split_vertically_by_threshold
from visualisation.plotter import Plotter
from simulation.simulate_readouts import ReadoutGenerator

from scipy import interpolate
import numpy as np
import json
import argparse
import logging
from config.config_utils import get_default_sensors_config

grubosc_paska = 0.128
N_paskow = 3600
obwod_mm = grubosc_paska*N_paskow
R_mm = obwod_mm / (2*np.pi)

# necessary to disable np debug nonsense:
logging.getLogger("matplotlib").propagate = False

logger = logging.getLogger(__name__)


def smooth(y, box_pts):
    box = np.ones(box_pts)/box_pts
    y_smooth = np.convolve(y, box, mode='same')
    return y_smooth


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


def get_useful_range(image):
    N = len(image)
    b = -1
    e = -1
    for i in range(0, N):
        if image[i] < 0.9:
            b = i
            break

    for i in reversed(range(0, N)):
        if image[i] < 0.9:
            e = i
            break
    return b, e


def normalize(image):
    amax = np.amax(image)
    amin = np.amin(image)
    amp = amax - amin
    image = (image - amin) / amp
    return image

max_crossings = 16

class RevisitedLineFitter:
    def __init__(self, wheel, sensor):
        self.R_um = wheel.radius_mm * 1000
        self.d_um = wheel.d_um
        self.delta_rad = np.pi * wheel.dphi_deg / 180.0
        self.px_um = sensor.dx

    def get_beta_and_height(self, image):
        image = normalize(image)
        logger.info(f"Min image = {min(image)}, max = {max(image)}")

        signal_begin, signal_end = get_useful_range(image)
        image = image[8:120]
        c = []
        k = np.arange(0.1, 1, (1.0/max_crossings))
        for t in k:
            raw_c = get_crossings(image, t)
            ys = [t] * len(raw_c)
            c += zip(raw_c, ys)
        # c = get_crossings(image, 0.7)

        logger.info(f"Len c = {len(c)}")
        return c

        if len(c) < 3:
            return c[0], c[1], 0, 0

        if len(c) < 4:
            return 0, 0, 0, 0

        return c[0], c[1], c[2], c[3]
        #logger.info(f"Len of c: {len(c)}, Len of h {len(hills)}")
        logger.info(f"Crossings: {c}")
        begin_i = c[2]
        end_i = c[3]
        h = image[6:120]
        t = np.average(range(begin_i, end_i), weights=h)

        ch = zip(c, hills[1:])
        mass_centers = []
        for (c, h) in ch:
            begin_i = c
            end_i = c + len(h)
            mass_center = np.average(range(begin_i, end_i), weights=h)
            mass_centers.append((mass_center, h[0] > threshold))

        # centers_above = [c for (c, is_above) in mass_centers if is_above]
        centers_under = [c for (c, is_above) in mass_centers if not is_above]

        # logger.debug(f"Mass centers above: {centers_above}")
        # logger.debug(f"Mass centers under: {centers_under}")
        # L1 = self.px_um * (centers_under[2] - centers_under[1])
        # L2 = self.px_um * (centers_under[3] - centers_under[2])
        if len(centers_under) < 4:
            return 0, 0, 0
        L1 = (centers_under[2] - centers_under[1])
        #beta = 2.0 * (self.d_um) / (L1 * self.px_um)
        h = (centers_under[1], centers_under[2])
        # L2 = (centers_under[3] - centers_under[2])

        #print(f"L1 = {L1} as integer ratio: {L1.as_integer_ratio()}")
        #print(f"L2 = {L2} as integer ratio: {L2.as_integer_ratio()}")
        # K = (L2 - L1)
        #print(f"K={K}, K as integer ratio: {K.as_integer_ratio()}")
        # dp2 = self.delta_rad/2.0
        # beta = dp2 * ((3.0 * L2 + L1) / K)
        #print(f"beta = {dp2*((3.0*L2 + L1)/(L2 - L1 + 0.001))}")

        #logger.debug(f"beta={beta}, L1 = {L1}, L2 = {L2}, K= {K} R={self.R_um}, R*(L1-L2)={self.R_um*(L1 - L2)}, L1^2 = {L1*L1}, L1^2/(L2-L1) = {L1*L1/(L2-L1)}, delta = {180*self.delta_rad/np.pi}")
        # h = (self.R_um*(L1 - L2) + L1*L1)/(L2 - L1)
        # beta = np.pi/2.0 - (self.d_um+h*self.delta_rad)/L1
        # for h in hills[1:]:
        #     mass_center = np.average(range(h, weights=range(10,0,-1))

        return beta, h, threshold


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


    wheel = EncoderWheel(R_mm, N_paskow, 28)

    arcsek = 0.1/360
    begin_a = 30*arcsek

    angles = np.arange(begin_a, begin_a+10*arcsek, 0.5*arcsek)
    p_angles = [4 + a for a in angles]
    "for angle 4.6 - median of 50 betas = 4.24(3, 6, 4.25) - 36"
    "for angle 4.5 - median of 50 betas = 4.18(1-5) - 32"
    "for angle 4.4 - median of 50 betas = 4.13(0-3) -27"
    "for angle 4.3 - median of 50 betas = 4.06(9, 4.08, 4.08) -24"
    readout_generator = ReadoutGenerator(sensor, wheel, sensor_tilt_deg=1.2, sensor_shift_um=(30, -200))

    fitter = RevisitedLineFitter(wheel, sensor)  # LineFitter(sensor)

    raw_init = readout_generator.for_angle(0)
    raws = []
    betas = []
    hhhs = []
    ttts = []
    kkks = []
    b_init = fitter.get_beta_and_height(raw_init)
    index = 0
    min_l = 10
    NNN = len(angles)
    mean_cs = np.zeros(NNN)
    mean_cs[0] = 0

    max_readings = max_crossings*3
    last_crossings = np.zeros(max_readings)
    betas = np.zeros([NNN, max_readings])
    last_angle = 0
    c_threshold = 2 # 128 is max

    hhh = [[0, 1], [1, 2]]

    with open("test.json", 'w') as f:
        json.dump(hhh, f)

    hhh = []


    for a in angles:
        raw = readout_generator.for_angle(a)
        raws.append(raw)
        logger.info(f"Index = {index}. Angle = {a}")
        crossings = fitter.get_beta_and_height(raw)
        hhh.append(crossings)
        logger.info(f"Len crossings = {len(crossings)}")

        diffs = [current - last for (current, last) in zip(crossings, last_crossings)]
        last_crossings = crossings
        logger.info(f"Len diffs = {len(diffs)}")
        well_behaved = np.array([k for k in diffs if abs(k) < c_threshold])
        logger.info(f"Len well behaved = {len(well_behaved)}")
        betas[index, 0:len(well_behaved)] = well_behaved
        if well_behaved.any() and index > 0:
            last_angle += np.mean(well_behaved)
        mean_cs[index] = last_angle
        index += 1

    with open("log.json", 'w') as f:
        json.dump(hhh, f)
    # logger.info(f"Minl = {min_l}")
    #
    #

    # result = open("result.txt", "w")
    # for i in range(0, len(betas)):
    #     written = f"{i}\t{angles[i]}"
    #     for k in range(0, min_l):
    #         written += f"\t{betas[i][k]}"
    #     written += "\n"
    #     result.write(written)
    # result.close()
    #
    # betas = np.array(betas)
    #
    # print(f"SHape betas = {betas.shape}")
    # cs = np.array([[c[i] for c in betas] for i in range(0, min_l)])
    # print(f"Shape cs={cs.shape}")
    #
    # B = len(betas)
    #
    # diffs = np.zeros((min_l, B))
    # for i in range(1, B):
    #     for k in range(0, min_l):
    #         diffs[k][i] = cs[k][i] - cs[k][i-1]
    #
    # # for i in range(0, min_l):
    # #     cs[i] = [c - cs[i][0] for c in cs[i]]
    #
    # cs_mean = np.zeros(B)
    # for i in range(0, B):
    #     well_behaved = [k for k in diffs[:, i] if abs(k) < c_threshold]
    #     cs_mean[i] = np.mean(well_behaved)
    #     if i > 0:
    #         cs_mean[i] += cs_mean[i-1]
    #
    #
    # # for i in range(0, min_l):
    # #     plotter.get_axes().plot(angles, cs_mean[i])
    plotter = Plotter()
    angles = [int(3600*a) for a in angles]
    plotter.get_axes().plot(angles, mean_cs)



    # plotter.plot_simple(normalize(raws[0]))


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
    plotter.save_plot()
    plotter.show_plot()
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
