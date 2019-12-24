import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib as mpl
import numpy as np
from shapely.geometry import Polygon
from shapely import affinity

polygon = Polygon([(3, 3), (5, 3), (5, 5), (3, 5)])
other_polygon = Polygon([(1, 1), (4, 1), (4, 3.5), (1, 3.5)])
intersection = polygon.intersection(other_polygon)
print(intersection.area)

# Data for plotting
N = 128
M = 3600
O = 3600 * (25.4 / 200)
R = O / (2 * np.pi)
rw = O / (2 * M)
rh = 12

sensor_w = rw
sensor_h = rh


stripes = []

angle_increment = 2 * np.pi / M
pol_w = rw / 2

#
# plt.figure()
# ax = plt.gca()
# ax.set_xlim([-R - 1.5 * rh, R + 1.5 * rh])
# ax.set_ylim([-R - 1.5 * rh, R + 1.5 * rh])

start_fi = 0
for i in range(0, M):
    fi = start_fi + i * angle_increment
    mi = (i + 0.5) * angle_increment
    xx = R * np.sin(fi) - pol_w * np.cos(fi)
    yy = R * np.cos(fi) + pol_w * np.sin(mi)
    xxxx = R * np.sin(mi) - pol_w * np.cos(mi)
    yyyy = R * np.cos(mi) + pol_w * np.sin(mi)
    rect = patches.Rectangle((xx, yy), rw, rh, edgecolor='None', facecolor='black', alpha=0.5, angle=-180 * fi / np.pi)
    rect2 = patches.Rectangle((xxxx, yyyy), rw, rh, edgecolor='None', facecolor='red', alpha=0.5,
                              angle=-180 * (fi + angle_increment / 2) / np.pi)
    # trans = mpl.transforms.Affine2D().rotate_around(xx, yy, -fi) + ax.transData
    # rect.set_transform(trans)
    p = Polygon([(xx, yy), (xx + rw, yy), (xx + rw, yy + rh), (xx, yy + rh)])
    stripes.append(affinity.rotate(p, -fi, origin=(xx, yy), use_radians=True))
    # ax.add_patch(rect)
    # ax.add_patch(rect2)

print(f"N of stripes={len(stripes)}")

sx = 0 - sensor_w / 2
sy = R

# sensor_angle = 4 * 180 * angle_increment / np.pi
# sensor = patches.Rectangle((sx, sy), sensor_w, sensor_h, color='green', alpha=0.3, angle=sensor_angle)


y_inc = sensor_h / N
y_space = 0.01
s = []
pr = np.zeros((4, 2))
for i in range(0, N):
    sy = R + i*y_inc + i*y_space
    p = Polygon([(sx, sy), (sx + sensor_w, sy), (sx + sensor_w, sy + y_inc), (sx, sy + y_inc)])
    p = affinity.rotate(p, 40 * angle_increment, use_radians=True, origin=(sx, R))
    # pr[0:] = [sx, sy]
    # pr[1:] = [sx + sensor_w, sy]
    # pr[2:] = [sx + sensor_w, sy + y_inc]
    # pr[3:] = [sx, sy +
    xy = p.exterior.coords.xy
    # ax.add_patch(patches.Polygon(np.transpose(xy)))
    print(p)
    s.append(p)

area = []

K = 10
relevant_indices = [i for i in range(M-K, M)] + [j for j in range(0, K)]

for ssensor_index in range(0, N):
    area_s = 0
    for stripe_index in relevant_indices:
        area_s += stripes[stripe_index].intersection(s[sensor_index]).area
        # if stripes[stripe_index].intersects(s[sensor_index]):
            # print(f"Rectangle nb {stripe_index} is INTERSECTING sensor {sensor_index}. Area = {area_s}")
    area.append(sensor_w * y_inc - area_s)


# rect = patches.Rectangle((20, 40), 40, 30, linewidth=1, edgecolor='black', facecolor='black')
#
# # Add the patch to the Axes
# ax.add_patch(rect)



plt.figure()
ax = plt.gca()
ax.plot(range(0, N), area)
ax.set(xlabel='position (px)', ylabel='intensity (a.u.)',
       title='About as simple as it gets, folks')
ax.grid()

plt.show()
