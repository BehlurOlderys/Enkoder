from shapely.geometry import Polygon
from numpy import pi
from shapely import affinity


class EncoderWheel:
    def __init__(self, r_mm, cpr, h_mm):
        self.radius_mm = r_mm
        self.count = cpr
        self.line_height_mm = h_mm
        self.strips = self._create_strips_polygons()

    def _create_strips_polygons(self):
        s = []
        circ = 2.0*pi*self.radius_mm
        d = circ / (2.0 * self.count)
        strip = Polygon([
            (-d/2, self.radius_mm),
            (d/2, self.radius_mm),
            (d/2, self.radius_mm + self.line_height_mm),
            (-d/2, self.radius_mm + self.line_height_mm)])
        dphi = 360/(self.count)
        for i in range(0, self.count):
            s.append(affinity.rotate(strip,
                                     i*dphi,
                                     origin=(0, 0),
                                     use_radians=False))
        return s
