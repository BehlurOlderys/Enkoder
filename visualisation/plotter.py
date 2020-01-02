import matplotlib.pyplot as plt
import numpy as np


class Plotter:
    def __init__(self):
        self.reset()
        self.N = 0

    def reset(self):
        self.fig, self.ax = plt.subplots()
        self.ax.set(xlabel='position (px)', ylabel='intensity (a.u.)',
                    title='Odczyt z linijki CCD')
        self.ax.grid()

    def plot_simple(self, y):
        t = np.arange(0.0, len(y))
        self.ax.plot(t, y)

    def plot_points(self, y, xrange):
        self.ax.plot(xrange, y, 'ro')

    def save_plot(self):
        plt.savefig('plot_'+str(self.N))
        self.N += 1

    def show_plot(self):
        plt.show()

    def get_axes(self):
        return self.ax
