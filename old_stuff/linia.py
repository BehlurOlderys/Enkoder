import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from math import sqrt, exp, pi, cos, sin
import cmath
from numpy.fft import fft
import heapq
from operator import itemgetter, attrgetter
from numpy.polynomial.polynomial import Polynomial


class Punkt:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __repr__(self):
        return f"({self.x}, {self.y})"


def sqr(x):
    return x * x


def dist2(a, b):
    return sqr(a.x - b.x) + sqr(a.y - b.y)


def dist_to_segment_squared(c, a, b):
    d2 = dist2(a, b)
    # if (l2 == 0):
    #        return dist2(c, a)
    t = ((c.x - a.x) * (b.x - a.x) + (c.y - a.y) * (b.y - a.y)) / d2
    t = max(0, min(1, t))
    return dist2(c, Punkt(x=a.x + t * (b.x - a.x),
                          y=a.y + t * (b.y - a.y)))


def dist_to_segment(c, a, b):
    return sqrt(dist_to_segment_squared(c, a, b))


def douglas_peucker(lista_punktow, epsilon):
    # Find the point with the maximum distance
    if len(lista_punktow) < 3:
        return lista_punktow

    dmax = 0
    imax = None
    A = lista_punktow[0]
    B = lista_punktow[-1]
    for i in range(1, len(lista_punktow)-1):
        d = dist_to_segment(lista_punktow[i], A, B)
        print(f"d={d}")
        if d > dmax:
            dmax = d
            imax = i

    # If max distance is greater than epsilon, recursively simplify
    if dmax > epsilon:
        print(f"Splitting point: {lista_punktow[imax]}, d={dmax}")
        wyniki1 = douglas_peucker(lista_punktow[0: imax], epsilon)
        wyniki2 = douglas_peucker(lista_punktow[imax+1:-1], epsilon)
        return wyniki1 + wyniki2

    return lista_punktow


def get_derivative(a):
    zz = zip(a[:-5], a[1:-4], a[2:-3], a[3:-2], a[4:-1])
    hh = [-a-3*b+3*d+e for a, b, c, d, e in zz]
    kk = zip(hh[:-2], hh[1:-1])
    return [bb - aa for aa, bb in kk]
    return hh


def DFT_slow(x):
    """Compute the discrete Fourier Transform of the 1D array x"""
    N = len(x)
    output = []
    for k in range(0, N):
        sum = complex(0, 0)
        for t in range(0, N):
            angle = 2 * pi * t * k / N
            sum += complex(x[t] * cos(angle), -x[t] * sin(angle))

        output.append(sum)


def FFT(x):
    """A recursive implementation of the 1D Cooley-Tukey FFT"""
    # N = len(a)
    #
    # if N % 2 > 0:
    #     raise ValueError("size of x must be a power of 2")
    # elif N <= 32:  # this cutoff should be optimized
    #     return DFT_slow(x)
    # else:
    #     X_even = FFT(x[::2])
    #     X_odd = FFT(x[1::2])
    #     factor = np.exp(-2j * np.pi * np.arange(N) / N)
    #     return np.concatenate([X_even + factor[:N / 2] * X_odd,
    #                            X_even + factor[N / 2:] * X_odd])
    return DFT_slow(x)


def zrob_segmenty(a):

    for p in a:
        print(p)


    s = []
    s.append((30, 100, 110, 40))
    return s


def rysuj_segment(ax, segment):
    x0, y0, x1, y1 = segment
    b = [y0, y1]
    u = [x0, x1]
    ax.plot(u, b, color="green")


aa = [146.987, 179.279, 184.847, 171.485, 143.646, 114.694, 110.24, 110.24, 92.4236, 70.1528, 65.6987, 38.9738, 21.1572,
     14.476, 7.79476, 7.79476, 3.34061, 0.0, 1.11354, 3.34061, 6.68122, 7.79476, 16.703, 27.8384, 45.655, 67.9258,
     71.2664, 95.7642, 105.786, 113.581, 154.782, 154.782, 168.144, 188.188, 190.415, 197.096, 201.55, 188.188, 179.279,
     202.664, 189.301, 180.393, 183.734, 140.306, 114.694, 105.786, 85.7423, 80.1747, 70.1528, 44.5415, 23.3843, 14.476,
     10.0218, 6.68122, 4.45415, 3.34061, 3.34061, 6.68122, 10.0218, 14.476, 26.7249, 33.4061, 51.2227, 79.0611, 91.31,
     111.354, 121.376, 132.511, 135.852, 164.803, 192.642, 210.458, 210.458, 208.231, 202.664, 223.821, 229.389,
     189.301, 172.598, 168.144, 145.873, 121.376, 114.694, 103.559, 83.5153, 55.6768, 34.5196, 30.0655, 21.1572,
     17.8166, 12.2489, 7.79476, 10.0218, 13.3624, 14.476, 18.9301, 28.952, 40.0873, 52.3362, 74.607, 105.786, 121.376,
     123.603, 148.1, 178.166, 191.528, 201.55, 211.572, 233.843, 247.205, 248.319, 255.0, 230.502, 229.389, 223.821,
     210.458, 201.55, 189.301, 170.371, 148.1, 114.694, 99.1048, 82.4017, 66.8122, 46.7685, 31.179, 28.952, 25.6113]


def smooth(y, box_pts):
    box = np.ones(box_pts)/box_pts
    y_smooth = np.convolve(y, box, mode='same')
    return y_smooth


class PointWithProps:
    def __init__(self, x, y, tan):
        self.x = x
        self.y = y
        self.raw_y = aa[self.x]
        self.tan = tan

    def __repr__(self):
        return str(self.tan)


def strip_outliners(t, max_points, initial_tan):
    return  heapq.nsmallest(max_points,
                            t,
                            key=lambda x: abs(x.tan - initial_tan))


if __name__ == "__main__":
    N = 128
    # Data for plotting
    t = np.arange(0.0, len(aa))

    fig, ax = plt.subplots()

    ax.plot(t, aa, color="black", linewidth="3")
    a = smooth(aa, 5)
    #ax.plot(t, a, color="blue")

    threshold = (max(aa) - min(aa))*0.4
    print(f"Treshold = {threshold}")
    direction = "minus" if aa[0] < threshold else "plus"
    crossings = []

    hills = []
    current_hill = []

    p_index = 0
    for p in aa:
        current_hill.append(p)
        if direction == "minus":
            if p > threshold:
                direction = "plus"
                crossings.append(p_index)
                hills.append(current_hill.copy())
                current_hill = []
        elif direction == "plus":
            if p < threshold:
                direction = "minus"
                crossings.append(p_index)
                hills.append(current_hill.copy())
                current_hill = []
        p_index += 1

    hills.pop(0)
    print(crossings)
    init = crossings[0]+1
    print(f"Found {len(hills)} hills and {len(crossings)} crossings.")

    full_stripes = len(hills)/2
    max_length_for_slopes = 100  # for 128
    av_slope_lenght = int((max_length_for_slopes / 2)/full_stripes)
    half_av_slope_len = int(av_slope_lenght / 2)
    two_thirds_av_slope = int(0.66*av_slope_lenght)
    print(f"Average length of slope: {av_slope_lenght}")
    for h in hills:
        r = [i for i in range(init, init + len(h))]
        print(len(h))
        ax.plot(r, h)
        init += len(h)

    init_linear_range = 3
    slopes = []
    for c_index in crossings:
        beg_slope = max(1,   c_index-half_av_slope_len)
        end_slope = min(N-1, c_index+half_av_slope_len)
        slope_len = end_slope-beg_slope
        if slope_len < av_slope_lenght:
            continue
        slopes.append([i for i in range(beg_slope, end_slope)])
        bx = c_index - init_linear_range
        ex = c_index + init_linear_range
        by = a[c_index-init_linear_range]
        ey = a[c_index+init_linear_range]
        inital_slope_tan = (ey - by)/(ex - bx)
        tans = []
        tans = [PointWithProps(i, a[i], (a[i] - a[i - 1])) for i in range(beg_slope, end_slope)]

        tans = strip_outliners(tans, two_thirds_av_slope, inital_slope_tan)

        min_x = min(tans, key=lambda e: e.x)
        max_x = max(tans, key=lambda e: e.x)
        print(f"Min x = {min_x.x}, max x = {max_x.x}")

        new_x = [p.x for p in tans]
        new_y = [p.raw_y for p in tans]
        [coeff_a, coeff_b] = np.polyfit(new_x, new_y, 1)
        print(f"Model: y = {coeff_a}*x + {coeff_b}")



        print(f"Lenght of slope: {end_slope - beg_slope}, tans = {tans}")

        print(f"Initial_slope = {inital_slope_tan}")

        ttt = range(min_x.x, max_x.x)
        ttttt = range(min_x.x - 5, max_x.x + 5)
        fit_y = [coeff_a*x + coeff_b for x in ttt]
        fit_yyy = [coeff_a*x + coeff_b for x in ttttt]
        # ax.plot(ttttt, fit_yyy, color="blue")
        # ax.plot(ttt, fit_y, color="green")
        #rysuj_segment(ax, (beg_slope, aa[beg_slope], end_slope, aa[end_slope]))



    ax.set(xlabel='position (px)', ylabel='intensity (a.u.)',
           title='Odczyt z linijki CCD')
    ax.grid()

    fig.savefig("test.png")
    plt.show()
