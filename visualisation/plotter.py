import matplotlib.pyplot as plt
import numpy as np


class Plotter:
    def __init__(self):
        self.fig, self.ax = plt.subplots()
        self.ax.set(xlabel='position (px)', ylabel='intensity (a.u.)',
               title='Odczyt z linijki CCD')
        self.ax.grid()

    def plot_simple(self, y):
        t = np.arange(0.0, len(y))
        self.ax.plot(t, y)

    def show_plot(self):
        plt.show()

    def get_axes(self):
        return self.ax
