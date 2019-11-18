from config.config_utils import get_default_sensors_config
from hardware.linear_ccd_sensor import LinearCCDSensor
from hardware.encoder_wheel import EncoderWheel
from shapely.geometry import Polygon
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from shapely import affinity
import numpy as np
import json
import logging
import argparse


logger = logging.getLogger(__name__)
logging.getLogger("matplotlib").setLevel(logging.WARNING)


class Plotter:
    def __init__(self):
        self.prepared_patches = []

    def add_polygon(self, p, color='black', units='mm'):
        points = get_polygons_points(p)
        if units == 'um':
            points = np.divide(points, 1000)
        logger.debug(f"Plotter received something with shape {np.shape(points)}")
        xy = np.transpose(points)
        logger.debug(f"Coords= \n{xy}\nShape = {np.shape(xy)}")
        self.prepared_patches.append(patches.Polygon(xy, edgecolor='None', facecolor=color, alpha=0.5))

    def execute(self):
        plt.figure()
        ax = plt.gca()

        for p in self.prepared_patches:
            ax.add_patch(p)

        ax.set_xlim(-1, 1)
        ax.set_ylim(70, 80)

        ax.set(xlabel='position (px)',
               ylabel='intensity (a.u.)',
               title='About as simple as it gets, folks')
        ax.grid()

        plt.show()


def get_polygons_points(polygon):
    return polygon.exterior.coords.xy


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
            (-self.sensor.height/2, 0),
            (self.sensor.height/2, 0),
            (self.sensor.height/2, 0 + self.sensor.width),
            (-self.sensor.height/2, 0 + self.sensor.width)
        ])
        logger.debug(f"Sensor rectangle before tilt= {sensor_rectangle}")

        sensor_rectangle = affinity.rotate(sensor_rectangle,
                                           sensor_tilt_deg,
                                           origin=(0, 0),
                                           use_radians=False)

        logger.debug(f"Sensor rectangle before shift= {sensor_rectangle}")
        (x, y) = sensor_shift_um
        R_um = self.wheel.radius_mm*1000
        return affinity.translate(sensor_rectangle, x, y + R_um)

    def for_angle(self, angle):
        """
        On encoder wheel with radius R and coordinates starting at center of wheel it would be (0, R).
        :param angle:
        :return:
        """
        logger.debug(f"Sensor rectangle= {self.sensor_rectangle}")

        margin = 10
        interesting_strips = self.wheel.strips[-margin:]
        interesting_strips += self.wheel.strips[:margin]
        logger.debug(f"Interesting strips: {interesting_strips}")
        # for strip in self.wheel.strips[-10, ]:
        plotter = Plotter()
        plotter.add_polygon(self.sensor_rectangle, color='green', units='um')
        for s in interesting_strips:
            plotter.add_polygon(s)

        plotter.execute()

        readout = np.zeros(self.sensor.N)
        return readout


obwod_mm = 0.128*3600
R_mm = obwod_mm / (2*np.pi)

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

    readout_generator = ReadoutGenerator(sensor, wheel, sensor_tilt_deg=5, sensor_shift_um=(27, -64))
    readout = readout_generator.for_angle(0)
    logger.info(f"Readout = [N={sensor.N}] {readout}")
