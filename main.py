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
arcsek_in_deg = 0.1/360  # 1/3600 of one degree
sensitivity_threshold_as = 100
grubosc_paska_mm = 0.128
N_paskow = 3600
obwod_mm = grubosc_paska_mm*N_paskow
R_mm = obwod_mm / (2*np.pi)
R_um = 1000*R_mm
grubosc_czarnego_um = grubosc_paska_mm*1000*0.5
stripe_width_um = grubosc_czarnego_um
odleglosc_dolnego_paska = 6*grubosc_czarnego_um

# necessary to disable np debug nonsense:
logging.getLogger("matplotlib").propagate = False

logger = logging.getLogger(__name__)

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

    wheel = EncoderWheelWithTopAndBottomStrips(R_mm, N_paskow, 6.4, odleglosc_dolnego_paska) #, grubosc_dolnego_paska)

    # Main loop:
    begin_angle_as = 0
    actual_estimate_fi_as = None  # as is short for arcsecond, obviously
    last_dfi_as = 0
    index = 0
    angles_deg = np.arange(begin_angle_as, begin_angle_as + 720, 2)*arcsek_in_deg

    readout_generator = ReadoutGenerator(sensor, wheel, sensor_tilt_deg=1.4, sensor_shift_um=(0, -765))
    for angle_deg in angles_deg:
        raw = readout_generator.for_angle(angle_deg)
        #raw = [ 0.0, 5.39682, 12.1429, 21.5873, 32.3809, 37.7778, 41.8254, 47.2222, 52.619, 163.254, 248.254, 255.0, 215.873, 147.063, 111.984, 110.635, 125.476, 117.381, 125.476, 129.524, 130.873, 138.968, 145.714, 149.762, 151.111, 151.111, 155.159, 155.159, 168.651, 175.397, 170.0, 170.0, 178.095, 183.492, 184.841, 190.238, 190.238, 203.73, 201.032, 210.476, 203.73, 219.921, 226.667, 226.667, 236.111, 238.809, 241.508, 245.555, 241.508, 241.508, 246.905, 226.667, 228.016, 233.413, 225.317, 240.159, 238.809, 240.159, 241.508, 249.603, 238.809, 223.968, 242.857, 252.302, 248.254, 245.555, 238.809, 238.809, 222.619, 219.921, 222.619, 222.619, 213.174, 211.825, 203.73, 198.333, 201.032, 201.032, 194.286, 196.984, 190.238, 184.841, 187.54, 186.19, 176.746, 174.048, 168.651, 170.0, 167.302, 167.302, 167.302, 161.905, 160.555, 149.762, 148.413, 149.762, 144.365, 137.619, 143.016, 134.921, 137.619, 133.571, 126.825, 120.079, 116.032, 114.682, 116.032, 114.682, 114.682, 114.682, 113.333, 113.333, 113.333, 114.682, 113.333, 113.333, 114.682, 114.682, 114.682, 114.682, 114.682, 114.682, 114.682, 116.032, 116.032, 136.27, 174.048, 179.444 ]
        #raw = [ 0.0, 2.41706, 6.04265, 8.45971, 10.8768, 41.09, 170.403, 240.498, 255.0, 134.147, 53.1753, 42.2986, 39.8815, 38.673, 39.8815, 41.09, 41.09, 41.09, 39.8815, 39.8815, 39.8815, 39.8815, 41.09, 41.09, 42.2986, 42.2986, 43.5071, 47.1327, 45.9241, 44.7156, 49.5497, 55.5924, 56.8009, 54.3839, 64.0521, 74.9289, 73.7203, 78.5545, 89.4312, 101.517, 96.6824, 97.891, 113.602, 126.896, 122.062, 125.687, 138.981, 134.147, 145.024, 154.692, 161.943, 166.777, 155.9, 165.569, 180.071, 167.986, 172.82, 182.488, 187.322, 190.948, 189.739, 189.739, 188.531, 184.905, 180.071, 188.531, 201.825, 201.825, 171.611, 184.905, 182.488, 189.739, 196.99, 167.986, 166.777, 174.028, 174.028, 163.152, 152.275, 152.275, 143.815, 136.564, 130.521, 128.104, 113.602, 111.185, 102.725, 99.0995, 87.0142, 78.5545, 76.1374, 68.8862, 61.635, 65.2606, 64.0521, 61.635, 60.4265, 56.8009, 54.3839, 54.3839, 54.3839, 55.5924, 55.5924, 55.5924, 56.8009, 56.8009, 55.5924, 55.5924, 55.5924, 56.8009, 56.8009, 60.4265, 61.635, 64.0521, 65.2606, 65.2606, 66.4692, 64.0521, 65.2606, 72.5118, 83.3886, 84.5971, 88.2227, 96.6824, 108.768, 138.981, 143.815, 132.938 ]
        useful_raw = raw[useful_begin:]

        pixel_difference_from_last_reading = 0  # TODO
        width_of_stripe_px = 0  # TODO

        # To first approximation this should not change much:
        pixel_to_xaxis_um_coefficient = float(stripe_width_um) / width_of_stripe_px
        dx_um = pixel_difference_from_last_reading * pixel_to_xaxis_um_coefficient
        dfi_as = 1296000 * dx_um / (2.0 * np.pi * R_um)

        if actual_estimate_fi_as is None:
            actual_estimate_fi_as = 0
        else:
            actual_estimate_fi_as += (dfi_as if abs(dfi_as) < sensitivity_threshold_as else last_dfi_as)
            last_dfi_as = dfi_as

        # actual_estimate_fi_as = update_with_other(actual_estimate_fi_as)

        relative_angle_as = angle_deg/arcsek_in_deg - begin_angle_as
        logger.info(f"Index = {index}. "
                    f"Angle = {relative_angle_as}\". "
                    f"Actual estimate = {actual_estimate_fi_as}\"")
        index += 1