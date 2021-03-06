import json
import os
from shapely.geometry import Polygon
from shapely import affinity


class LinearCCDSensor:
    """            w
    h [][][][][][][][][][][][][]
    """
    def __init__(self, n, pixel_w_um, pixel_h_um, horizontal_spacing_um):
        self.N = n
        self.pixel_w_um = pixel_w_um
        self.pixel_h_um = pixel_h_um
        self.horizontal_spacing_um = horizontal_spacing_um
        self.dx = pixel_w_um + horizontal_spacing_um

    @property
    def height(self):
        return self.pixel_h_um

    @property
    def pixel_pitch_h_um(self):
        return self.pixel_w_um + self.horizontal_spacing_um

    @property
    def width_um(self):
        return self.N*self.pixel_pitch_h_um

    def get_total_rectangle(self):
        total_w = self.N * self.dx
        return Polygon([
            (0, 0),
            (total_w, 0),
            (total_w, self.pixel_h_um),
            (0, self.pixel_h_um)
        ])

    def get_array_segments(self):
        """
        [] [] [] [] []
        :return: array of segments one by one in x axis
        """
        segments = []
        for i in range(0, self.N):
            segment = Polygon([
                (0, 0),
                (self.pixel_w_um, 0),
                (self.pixel_w_um, self.pixel_h_um),
                (0, self.pixel_h_um)])
            segments.append(affinity.translate(segment, i*self.dx, 0))

        return segments

    def get_data(self, i=0):
        my_dir = os.path.split(__file__)[0].replace("/", "\\")
        dir_below = os.path.split(my_dir)[0]
        default_config_dir = os.path.join(dir_below, "config")
        fake_input_json = os.path.join(default_config_dir, 'fake_inputs.json')
        with open(fake_input_json) as f:
            j = json.load(f)

        data_array_of_readouts = j["data"]
        return data_array_of_readouts[i]

    @classmethod
    def from_json(cls, j):
        n = j["N"]
        w = j["pixel_width_um"]
        h = j["pixel_height_um"]
        h_sp = j["horizontal_spacing_um"]
        return cls(n, w, h, h_sp)

    def __repr__(self):
        return f"Linear CCD Sensor. N={self.N}," \
            f" w={self.pixel_w_um}um," \
            f" h={self.pixel_h_um}um," \
            f" spacing={self.horizontal_spacing_um}um"
