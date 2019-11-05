from config.config_utils import get_default_sensors_config
from hardware.linear_ccd_sensor import LinearCCDSensor
from hardware.encoder_wheel import EncoderWheel
from shapely.geometry import Polygon
from shapely import affinity
import numpy as np
import json
import logging
import argparse


logger = logging.getLogger(__name__)


class ReadoutGenerator:
    def __init__(self, sensor, wheel, sensor_tilt_deg=0, sensor_shift_um=(0, 0)):
        self.sensor = sensor
        self.wheel = wheel
        self.sensor_rectangle = self._create_sensor_rectangle(sensor_tilt_deg, sensor_shift_um)

    def _create_sensor_rectangle(self, sensor_tilt_deg, sensor_shift_um):
        """
        starting tilt is 90deg so we assume sensor is standing on shorter side (on height)
        Width is longer!
        :param sensor_tilt_deg:
        :param sensor_shift_um:
        :return:
        """
        sensor_rectangle = Polygon([
            (0, 0),
            (self.sensor.height, 0),
            (self.sensor.height, self.sensor.width),
            (0, self.sensor.width)
        ])
        logger.debug(f"Sensor rectangle before tilt= {sensor_rectangle}")

        sensor_rectangle = affinity.rotate(sensor_rectangle,
                                           sensor_tilt_deg,
                                           origin=(0, self.sensor.width/2),
                                           use_radians=False)

        logger.debug(f"Sensor rectangle before shift= {sensor_rectangle}")

        return affinity.translate(sensor_rectangle, *sensor_shift_um)

    def for_angle(self, angle):
        """
        We are using coordinate system where 0,0 is on twelve oclock on encoder wheel just at beginning of stripes.
        On encoder wheel with radius R and coordinates starting at center of wheel it would be (0, R).
        :param angle:
        :return:
        """
        logger.debug(f"Sensor rectangle= {self.sensor_rectangle}")

        readout = np.zeros(self.sensor.N)
        return readout


obwod_mm = 0.128*3600
R_mm = obwod_mm / np.pi

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--log_level", default=0)
    args = parser.parse_args()

    logging.basicConfig(level=args.log_level,
                        format="%(asctime)s %(levelname)s [%(name)s] %(message)s")

    with open(get_default_sensors_config()) as f:
        config = json.load(f)

    sensor = LinearCCDSensor.from_json(config["TSL1401"])
    wheel = EncoderWheel(R_mm, 3600, 12)

    readout_generator = ReadoutGenerator(sensor, wheel, sensor_tilt_deg=5, sensor_shift_um=(1, 5))
    readout = readout_generator.for_angle(0)
    logger.info(f"Readout = [N={sensor.N}] {readout}")
