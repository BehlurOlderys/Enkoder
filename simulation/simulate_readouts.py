from config.config_utils import get_default_sensors_config
from hardware.linear_ccd_sensor import LinearCCDSensor
from hardware.encoder_wheel import EncoderWheel
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from shapely import affinity
from visualisation.plotter import Plotter
import numpy as np
import json
import logging
import argparse


logger = logging.getLogger(__name__)
logging.getLogger("matplotlib").setLevel(logging.WARNING)


class Plotter:
    def __init__(self):
        self.prepared_patches = []

    def add_polygon(self, p, color='black'):
        points = get_polygons_points(p)
        logger.debug(f"Plotter received something with shape {np.shape(points)}")
        xy = np.transpose(points)
        logger.debug(f"Coords= \n{xy}\nShape = {np.shape(xy)}")
        self.prepared_patches.append(patches.Polygon(xy, edgecolor='None', facecolor=color, alpha=0.5))

    def execute(self):
        plt.figure()
        ax = plt.gca()

        for p in self.prepared_patches:
            ax.add_patch(p)

        ax.set_xlim(-1000, 1000)
        ax.set_ylim(70000, 86000)

        ax.set(xlabel='x [um]',
               ylabel='y [um]',
               title='View of encoder')
        ax.grid()

        plt.show()


def get_polygons_points(polygon):
    return polygon.exterior.coords.xy


class ReadoutGenerator:
    def __init__(self, sensor, wheel, sensor_tilt_deg=0, sensor_shift_um=(0, 0)):
        self.sensor = sensor
        self.wheel = wheel
        self.tilt_deg = sensor_tilt_deg
        self.shift_um = sensor_shift_um

    def _shift_object_like_sensor(self, p):
        (x, y) = self.shift_um
        r_um = self.wheel.radius_mm * 1000
        p = affinity.rotate(p,
                            90+self.tilt_deg,
                            origin=(0, 0),
                            use_radians=False)
        return affinity.translate(p, x, y + r_um)

    def for_angle(self, angle_deg):
        """
        On encoder wheel with radius R and coordinates starting at center of wheel it would be (0, R).
        :param angle_deg:
        :return:
        """

        sensor_rectangle = self._shift_object_like_sensor(self.sensor.get_total_rectangle())
        original_segments = self.sensor.get_array_segments()
        sensor_segments = [self._shift_object_like_sensor(s) for s in original_segments]

        # margin = 10
        # original_strips = self.wheel.strips[-margin:]
        # original_strips += self.wheel.strips[:margin]
        rotated_strips = self.wheel.strips(angle_deg)

        logger.debug(f"Interesting strips: {rotated_strips}")
        logger.debug(f"Sensor rectangle= {sensor_rectangle}")
        logger.debug(f"Sensor segments: {sensor_segments}")

        # plotter = Plotter()
        # plotter.add_polygon(sensor_rectangle, color='green')
        # for s in rotated_strips:
        #     plotter.add_polygon(s, color='red')
        # #
        # for s in sensor_segments:
        #     plotter.add_polygon(s, color='blue')
        #
        # plotter.execute()


        max_area = sensor_segments[0].area
        readout = max_area*np.ones(self.sensor.N)

        set_of_intersecting = [s for s in rotated_strips if s.intersects(sensor_rectangle)]
        # logger.info(f"Set of intersecting strips: {set_of_intersecting}")

        for i in range(0, self.sensor.N):
            segment = sensor_segments[i]
            for strip in set_of_intersecting:
                readout[i] -= segment.intersection(strip).area #* (1.06-0.12*np.random.rand()) # stripes are black so we subtract light when they are

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
    wheel = EncoderWheel(R_mm, 3600, 7.5)

    readout_generator = ReadoutGenerator(sensor, wheel, sensor_tilt_deg=4, sensor_shift_um=(27, -300))
    readout = readout_generator.for_angle(0)
    logger.info(f"Readout = [N={sensor.N}] {readout}")

    plt.figure()
    ax = plt.gca()
    ax.plot(range(0, len(readout)), readout_generator.for_angle(0), color='black')
    ax.plot(range(0, len(readout)), readout_generator.for_angle(0.02), color='green')
    ax.plot(range(0, len(readout)), readout_generator.for_angle(0.04), color='blue')
    ax.plot(range(0, len(readout)), readout_generator.for_angle(0.06), color='red')
    ax.set(xlabel='position (px)', ylabel='intensity (a.u.)',
           title='Linear scan of encoder')
    ax.grid()

    plt.show()
