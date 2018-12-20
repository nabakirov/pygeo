import math
from logging import getLogger

logger = getLogger('pygeo utils')


EARTH_RADIUS_M = 6371008  # meters


def flat(lat, lng):
    r_lat, r_lng = degrees_to_radians(lat), degrees_to_radians(lng)
    x = r_lng * math.cos(r_lat) * EARTH_RADIUS_M
    y = r_lat * EARTH_RADIUS_M
    return x, y


def convex(x, y):
    r_lat = y / EARTH_RADIUS_M
    r_lng = x / (EARTH_RADIUS_M * math.cos(r_lat))
    lat, lng = radians_to_degrees(r_lat), radians_to_degrees(r_lng)
    return lat, lng


def distance(point1, point2):
    x1, y1 = point1
    x2, y2 = point2
    distance = math.sqrt(math.pow((x2 - x1), 2) + math.pow((y2 - y1), 2))
    return distance


def degrees_to_radians(x):
    return x * (math.pi / 180)


def radians_to_degrees(x):
    return x / (math.pi / 180)


def interpolate(point1, point2, segment_length=10):
    # includes parameter points

    sign = lambda x: -1 if x < 0 else 1

    x1, y1 = point1
    x2, y2 = point2
    new_points = [point1]
    _distance = distance(point1, point2)
    logger.debug('interpolated distance {}'.format(_distance))

    if _distance <= segment_length:
        new_points.append(point2)
        return new_points
    segment_quantity = int(_distance / segment_length) + 1  # step = slices + 1



    if abs(x1 - x2) <= abs(y1 - y2):
        y_len = abs(y2 - y1)
        if y_len == 0:
            return
        step = y_len / segment_quantity
        delta = (x2 - x1) / (y2 - y1)
        step *= sign(y2 - y1)
        y = y1
        for i in range(segment_quantity):
            y += step
            x = x1 + delta * (y - y1)
            new_points.append((x, y))
    else:
        x_len = abs(x2 - x1)
        if x_len == 0:
            return
        step = x_len / segment_quantity
        delta = (y2 - y1) / (x2 - x1)
        step *= sign(x2 - x1)
        x = x1
        for i in range(segment_quantity):
            x += step
            y = y1 + delta * (x - x1)
            new_points.append((x, y))
    new_points.append(point2)
    return new_points
