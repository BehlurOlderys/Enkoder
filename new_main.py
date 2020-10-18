import sys
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from shapely import affinity
from shapely.geometry import Polygon
from estimators import EstimatorPreviousN, smooth

sensor_N = 128
grubosc_paska_mm = 0.128
N_paskow = 3600
pasek_as = 1296000 / N_paskow
obwod_mm = grubosc_paska_mm*N_paskow
R_mm = obwod_mm / (2*np.pi)
R_um = 1000*R_mm


sensor_rect = None
global_geom_ax = None
global_read_ax = None
global_fig = None
global_readout = np.zeros(sensor_N)
global_line = None
global_line_smooth = None
global_phi = 0
global_errors = []

class DrawableRectangleObject:
    def __init__(self, xy, w, h, c, a):
        self.xy = xy
        self.w = w
        self.h = h
        self.rect = mpl.patches.Rectangle(self.xy, self.w, self.h, angle=a, color=c, alpha=0.5)


    def update_xy(self, xy):
        self.xy = xy
        self.rect.set_xy(self.xy)

    def add_xy(self, xy):
        self.xy = (self.xy[0] + xy[0], self.xy[1] + xy[1])
        self.rect.set_xy(self.xy)

    def get_xy(self):
        return self.xy

    def get_rect(self):
        return self.rect


class Sensor:
    def __init__(self, **kwargs):
        self.angle_deg = 0
        self.offset_um = 0
        if 'angle_deg' in kwargs:
            self.angle_deg = kwargs['angle_deg']
        if 'offset_um' in kwargs:
            self.offset_um = kwargs['offset_um']

        self.N = 128
        spacing = 64
        width = 55.5
        height = 63.5
        total_width = self.N*spacing

        self.pieces = [
            DrawableRectangleObject((R_um + i*spacing, 0), width, height, 'green', 0)
            for i in range(0, self.N)
        ]
        self.border = Polygon([
            (R_um, 0),
            (R_um + total_width, 0),
            (R_um + total_width, height),
            (R_um, height)
        ])
        self.polys = [Polygon([
            (R_um + i*spacing, 0),
            (R_um + width + i*spacing, 0),
            (R_um + width + i*spacing, height),
            (R_um + i*spacing, height)]) for i in range(0, self.N)]
        self._prepare()

    def _prepare(self):
        offset_x, offset_y = self.offset_um

        self.border = affinity.rotate(self.border, self.angle_deg, origin=(0, 0), use_radians=False)
        self.border = affinity.translate(self.border, offset_x, offset_y, 0)
        for i in range(0, self.N):
            self.polys[i] = affinity.rotate(self.polys[i], self.angle_deg, origin=(0, 0), use_radians=False)
            self.polys[i] = affinity.translate(self.polys[i], offset_x, offset_y, 0)

            t = mpl.transforms.Affine2D().rotate_deg_around(0, 0, self.angle_deg)\
                                         .translate(offset_x, offset_y) + global_geom_ax.transData
            self.pieces[i].rect.set_transform(t)

    def get_n(self):
        return self.N

    def get_rects(self):
        return [r.get_rect() for r in self.pieces]

    def get_border(self):
        return self.border

    def get_polys(self):
        return self.polys


class Strips:
    def __init__(self):
        self.N = 10
        self.angle_step_deg = 0.1

        width = 10000
        height = 64

        self.pieces = [DrawableRectangleObject((R_um, 0), 10000, 64, 'orange', 0) for i in range(0, self.N)]
        self.angles = []
        self.polys = [Polygon([
            (R_um, 0),
            (R_um + width, 0),
            (R_um + width, height),
            (R_um, height)]) for i in range(0, self.N)]

        self._prepare()

    def _prepare(self):
        angle = -0.5*self.angle_step_deg*self.N

        for i in range(0, self.N):
            self.angles.append(angle)
            self.polys[i] = affinity.rotate(self.polys[i], angle, origin=(0, 0), use_radians=False)
            t = mpl.transforms.Affine2D().rotate_deg_around(0, 0, angle) + global_geom_ax.transData
            self.pieces[i].rect.set_transform(t)
            angle += self.angle_step_deg

    def rotate(self, angle_deg):
        for i in range(0, self.N):
            new_angle = self.angles[i] + angle_deg
            max_angle = 0.5*self.N * self.angle_step_deg
            while new_angle > max_angle:
                new_angle -= 2.0*max_angle
            t = mpl.transforms.Affine2D().rotate_deg_around(0, 0, new_angle) + global_geom_ax.transData
            self.angles[i] = new_angle
            self.pieces[i].rect.set_transform(t)
            self.polys[i] = affinity.rotate(self.polys[i], angle_deg, origin=(0, 0), use_radians=False)

    def get_rects(self):
        return [r.get_rect() for r in self.pieces]

    def get_polys(self):
        return self.polys


class CollisionChecker:
    def __init__(self):
        self.sensor = None
        self.strips = None

    def set_sensor(self, sensor):
        self.sensor = sensor

    def set_strips(self, strips):
        self.strips = strips

    def check_collisions(self):
        set_of_intersecting = [s for s in self.strips.get_polys() if s.intersects(self.sensor.get_border())]
        max_area = self.sensor.get_polys()[0].area
        readout = max_area * np.ones(self.sensor.N)
        for i in range(0, self.sensor.N):
            segment = self.sensor.get_polys()[i]
            for strip in set_of_intersecting:
                readout[i] -= segment.intersection(strip).area

        return readout + 0.1 * max_area * (-0.5 * np.ones(self.sensor.N) + np.random.rand(self.sensor.N))


collision_checker = CollisionChecker()

estimator = EstimatorPreviousN(1)

def update():
    global global_fig
    global global_line
    global global_line_smooth
    global global_phi
    global global_errors

    random_angle_arcsec = 10*np.random.rand()
    global_phi += random_angle_arcsec
    random_angle_deg = 360.0 * random_angle_arcsec / 1296000
    # rotate wheel:
    test_strip.rotate(random_angle_deg)

    # read sensor:
    readout = collision_checker.check_collisions()

    # estimate position:
    estimate_arcsec = estimator.estimate(readout)
    error_arcsec = estimate_arcsec - random_angle_arcsec
    global_errors.append(error_arcsec)

    print(f"Total phi: {global_phi}\", last delta = {random_angle_arcsec}\", est. delta ={estimate_arcsec}")

    # update plots:
    global_line.set_ydata(readout)
    global_line_smooth.set_ydata(smooth(readout, 5))
    global_fig.canvas.draw()
    global_fig.canvas.flush_events()


def press(event):
    if event.key == 'r':
        update()
    elif event.key == 'escape':
        sys.exit(0)


global_fig, (global_geom_ax, global_read_ax) = plt.subplots(1, 2)
global_fig.canvas.mpl_connect('key_press_event', press)

global_line, = global_read_ax.plot(range(0, len(global_readout)), global_readout, color='black')
global_line_smooth, = global_read_ax.plot(range(0, len(global_readout)), global_readout, color='green')

global_geom_ax.set_xlim(R_um - 1000, 85000)
global_geom_ax.set_ylim(-1000, 1500)

global_read_ax.set_ylim(0, 3600)


my_sensor = Sensor(angle_deg=1.3, offset_um=(500, -2000))
for r in my_sensor.get_rects():
    global_geom_ax.add_patch(r)


test_strip = Strips()
for r in test_strip.get_rects():
    global_geom_ax.add_patch(r)

collision_checker.set_sensor(my_sensor)
collision_checker.set_strips(test_strip)

plt.show()

fig, ax = plt.subplots()
ax.plot(global_errors)
plt.show()




