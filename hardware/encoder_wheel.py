from shapely.geometry import Polygon
from numpy import pi
from shapely import affinity


class EncoderWheel:
    def __init__(self, r_mm, cpr, h_mm):
        self.radius_mm = r_mm
        self.count = cpr
        self.line_height_mm = h_mm
        self.circ_um = 2.0*pi*1000*self.radius_mm
        self.d_um = self.circ_um / (2.0 * self.count)
        self.dphi_deg = 360/(self.count)
        self.mm_to_um = 1000

    @property
    def line_height_um(self):
        return self.mm_to_um * self.line_height_mm

    @property
    def strip_min_y_um(self):
        return self.mm_to_um * self.radius_mm

    @property
    def strip_max_y_um(self):
        return self.strip_min_y_um + self.line_height_um

    def strips(self, angle_deg):
        return self._create_strips_polygons(angle_deg)

    def _create_strips_polygons(self, angle_deg):
        ss = []
        margin = 10

        strip = Polygon([
            (-self.d_um/2, self.strip_min_y_um),
            (self.d_um/2, self.strip_min_y_um),
            (self.d_um/2, self.strip_max_y_um),
            (-self.d_um/2, self.strip_max_y_um)])
        for i in range(-margin, margin):
            ss.append(affinity.rotate(strip,
                                      i*self.dphi_deg + angle_deg,
                                      origin=(0, 0),
                                      use_radians=False))
        return ss


class EncoderWheelWithTopAndBottomStrips(EncoderWheel):
    def __init__(self, r_mm, cpr, h_mm, d_bottom_um, h_line_um=4000):
        EncoderWheel.__init__(self, r_mm, cpr, h_mm)
        self.distance_to_bottom_line_um = d_bottom_um
        self.distance_to_top_line_um = d_bottom_um
        self.bottom_line_width_um = h_line_um
        self.top_line_width_um = h_line_um

    def _create_strips_polygons(self, angle_deg):
        x0 = -40000
        x1 = 40000
        y0 = self.strip_min_y_um - self.distance_to_bottom_line_um
        y1 = self.strip_min_y_um - (self.distance_to_bottom_line_um + self.bottom_line_width_um)

        line_bottom = Polygon([
            (x0, y0),
            (x1, y0),
            (x1, y1),
            (x0, y1)
        ])

        y0 = self.strip_max_y_um + self.distance_to_top_line_um
        y1 = self.strip_max_y_um + (self.distance_to_top_line_um + self.top_line_width_um)

        line_top = Polygon([
            (x0, y0),
            (x1, y0),
            (x1, y1),
            (x0, y1)
        ])

        return [line_bottom, line_top] + EncoderWheel._create_strips_polygons(self, angle_deg)
