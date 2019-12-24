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
        self.strips = self._create_strips_polygons()

    def _create_strips_polygons(self):
        m = 1000 # ums in mm
        s = []
        r = m*self.radius_mm
        strip = Polygon([
            (-self.d_um/2, r),
            (self.d_um/2, r),
            (self.d_um/2, r + m*self.line_height_mm),
            (-self.d_um/2, r + m*self.line_height_mm)])
        for i in range(0, self.count):
            s.append(affinity.rotate(strip,
                                     i*self.dphi_deg,
                                     origin=(0, 0),
                                     use_radians=False))
        return s
