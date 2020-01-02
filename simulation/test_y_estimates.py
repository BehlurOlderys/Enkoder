from hardware.linear_ccd_sensor import LinearCCDSensor
from hardware.encoder_wheel import EncoderWheelWithTopAndBottomStrips
from processing.y_shift_estimator import SensorYShiftEstimator
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

    dev = []
    rev = []
    y_estimator = SensorYShiftEstimator(sensor, wheel)
    for i in range(0, 200):
        tested_y_shift = -831.4724514 + 164.0*np.random.rand()
        readout_generator = ReadoutGenerator(sensor, wheel, sensor_tilt_deg=1.3925103, sensor_shift_um=(0, tested_y_shift))

        tested_angle_deg = 0.02784789

        raw = readout_generator.for_angle(tested_angle_deg)
        y_estimate_bot = y_estimator.estimate_bottom_edge(raw)
        y_estimate_top = y_estimator.estimate_top_edge(raw)
        print(f"{i} ESTIMATE BOT = {y_estimate_bot}, REAL = {tested_y_shift}, ERROR = {tested_y_shift + y_estimate_bot}")
        print(f"{i} ESTIMATE TOP = {y_estimate_top}, REAL = {tested_y_shift}, ERROR = {tested_y_shift + y_estimate_top}")

        y_estimate = 0.5*y_estimate_bot + 0.5*y_estimate_top

        dev.append(tested_y_shift + y_estimate)
        rev.append(tested_y_shift + y_estimate_top)


    plotter = Plotter()

    # plotter.plot_simple(raw)
    pyplot.hist(dev, bins=16)
    pyplot.hist(rev, color='red', bins=16)

    plotter.show_plot()
