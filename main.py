from hardware.linear_ccd_sensor import LinearCCDSensor
from config.config_utils import get_default_sensors_config
from processing.line_fitter import LineFitter
from visualisation.plotter import Plotter
import json
import argparse
import logging
import numpy as np

# necessary to disable np debug nonsense:
logging.getLogger("matplotlib").propagate = False

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config_for_sensors", default=default_file_for_sensor_config)
    parser.add_argument("-l", "--log_level", default=0)
    args = parser.parse_args()

    logging.basicConfig(level=args.log_level,
                        format="%(asctime)s %(levelname)s [%(name)s] %(message)s")

    logger.debug(f"Opening config file from {args.config_for_sensors}")
    with open(args.config_for_sensors) as f:
        sensor_config_json = json.load(f)

    logger.debug(f"Creating instance of sensor...")
    sensor = get_simple_sensor()
    logger.info(sensor)
    logger.debug(f"Creating line fitter...")
    fitter = LineFitter(sensor)

    raw_stack = np.zeros(128)
    for i in range(0, 10):
        np.add(raw_stack, sensor.get_data(), out=raw_stack)

    plotter = Plotter()
    plotter.plot_simple(raw_stack)

    crossings, coefficients, hills = fitter.fit_line(raw_stack)


    crossings.pop(0)
    hills.pop(0)

    init = crossings[0] + 1

    logger.info(f"Acquired {len(crossings)} crossings: {crossings}")
    logger.info(f"Acquired {len(coefficients)} lines: {coefficients}")
    logger.info(f"Acquired {len(hills)} hills: {hills}")

    for h in hills:
        r = [i for i in range(init, init + len(h))]
        print(len(h))
        plotter.get_axes().plot(r, h)
        init += len(h)

    for cross, coef in zip(crossings, coefficients):
        logger.debug(f"Crossing = {cross}")
        t = range(cross-10, cross+10)
        fit_y = [coef["a"] * x + coef["b"] for x in t]
        plotter.get_axes().plot(t, fit_y, color="green")

    plotter.show_plot()
