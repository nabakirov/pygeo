from . import utils, exceptions
import polyline as polylib
import logging
import time
from collections import deque

logger = logging.getLogger('pygeo')


class BasePoint:
    lat = None
    lng = None
    x = None
    y = None
    on_direction_position = None

    def __init__(self, lat=None, lng=None):
        self.lat = lat
        self.lng = lng
        self.x, self.y = utils.flat(lat, lng) if (lat and lng) else (None, None)

    @classmethod
    def from_latlng(cls, lat, lng):
        c = cls()
        c.lat = lat
        c.lng = lng
        c.x, c.y = utils.flat(lat, lng)
        return c

    @classmethod
    def from_xy(cls, x, y):
        c = cls()
        c.x = x
        c.y = y
        c.lat, c.lng = utils.convex(x, y)
        return c

    @property
    def latlng(self):
        return self.lat, self.lng

    @property
    def xy(self):
        return self.x, self.y


class Point(BasePoint):
    original_lat = None
    original_lng = None
    original_x = None
    original_y = None
    timestamp = None
    by_direction = None
    adjustment_lat = None
    adjustment_lng = None
    adjustment_x = None
    adjustment_y = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.by_direction = dict()  # -1, 1 acceptable values
        self.timestamp = time.time()

    @classmethod
    def from_latlng(cls, lat, lng):
        c = cls()
        c.original_lat = lat
        c.original_lng = lng
        c.original_x, c.original_y = utils.flat(lat, lng)
        return c

    @classmethod
    def from_xy(cls, x, y):
        raise Exception('SHOULD NOT USE')

    @property
    def original_latlng(self):
        return self.original_lat, self.original_lng

    @property
    def original_xy(self):
        return self.original_x, self.original_y

    def set_data(self, base_point):
        self.x = base_point.x
        self.y = base_point.y
        self.lat = base_point.lat
        self.lng = base_point.lng
        self.on_direction_position = base_point.on_direction_position

    def set_adjustment_data(self, point):
        self.adjustment_lat = point.lat
        self.adjustment_lng = point.lng
        self.adjustment_x = point.x
        self.adjustment_y = point.y


class Notification(BasePoint):
    id = None
    entry = None                # digit | entry distance in meters
    leave_interval = None       # tuple of digits | leave distances in meters
    entry_trigger = None        # callable
    leave_trigger = None        # callable
    silent_limit = 60 * 30      # in sec | after notification will be silent given seconds
    last_enter_notified = None  # timestamp
    last_leave_notified = None  # timestamp

    def __init__(self, id, lat, lng, entry=None, leave_interval=None, entry_trigger=None, leave_trigger=None):
        super().__init__(lat, lng)
        self.id = id

        # todo: make validation on entry and leave -> must be positive
        assert entry > 0
        self.entry = entry
        # todo: make validation on leave interval -> must be (1, 2)
        assert len(leave_interval) == 2
        for i in leave_interval:
            assert i > 0
        self.leave_interval = leave_interval
        self.entry_trigger = entry_trigger
        self.leave_trigger = leave_trigger

    def __notify_entry(self, layer, point, current, prev, direction):
        self.entry_trigger(layer, current, prev, direction)
        self.last_enter_notified = point.timestamp

    def __notify_leave(self, layer, point, current, next, direction):
        self.leave_trigger(layer, current, next, direction)
        self.last_leave_notified = point.timestamp

    def notify_entry(self, layer, point, prev, direction):
        if self.last_enter_notified:
            if abs(point.timestamp - self.last_enter_notified) > self.silent_limit:
                self.__notify_entry(layer, point, self, prev, direction)
        else:
            self.__notify_entry(layer, point, self, prev, direction)

    def notify_leave(self, layer, point, next, direction):
        if self.last_leave_notified:
            if abs(point.timestamp - self.last_leave_notified) > self.silent_limit:
                self.__notify_leave(layer, point, self, next, direction)
        else:
            self.__notify_leave(layer, point, self, next, direction)


class Direction:
    id = None
    segment_length = 10
    notification_distance_limit = 200
    points = None
    notifications = None

    def __init__(self, id, segment_length=segment_length, notification_distance_limit=notification_distance_limit):
        self.id = id
        self.segment_length = segment_length
        self.notification_distance_limit = notification_distance_limit
        self.points = []
        self.notifications = {}

    def add_notification(self, id, lat, lng, layer, entry_distance=None, leave_interval=None, entry_trigger=None, leave_trigger=None):
        notification = Notification(id, lat, lng, entry_distance, leave_interval, entry_trigger, leave_trigger)
        point, distance = self.project(notification.xy)
        if distance > self.notification_distance_limit:
            raise exceptions.NotificationDistanceLimitExitedException("notification point must be close to direction")
        notification.on_direction_position = point.on_direction_position
        if layer not in self.notifications:
            self.notifications[layer] = []
        self.notifications[layer].append(notification)
        self.notifications[layer] = sorted(self.notifications[layer], key=lambda x: x.on_direction_position)

    def __init_coordinates(self, coordinates):
        logger.debug('init direction coordinates {}'.format(len(coordinates)))
        total_distance = 0
        first = True
        total_interpolation = 0
        for i in range(1, len(coordinates)):
            logger.debug('{} out of {}'.format(i, len(coordinates)))
            point1 = BasePoint.from_latlng(*coordinates[i - 1])
            point2 = BasePoint.from_latlng(*coordinates[i])
            between_points = utils.interpolate(point1.xy, point2.xy, self.segment_length)
            logger.debug('interpolated {}'.format(len(between_points) - 2))
            total_interpolation += len(between_points) - 2
            for j in range(1, len(between_points)):
                b_point1 = BasePoint.from_xy(*between_points[j - 1])
                b_point2 = BasePoint.from_xy(*between_points[j])
                if first:
                    first = False
                    b_point1.on_direction_position = total_distance
                    self.points.append(b_point1)
                total_distance += utils.distance(b_point1.xy, b_point2.xy)
                b_point2.on_direction_position = total_distance

                self.points.append(b_point2)

    def from_polyline(self, polyline):
        coordinates = polylib.decode(polyline)
        self.__init_coordinates(coordinates)

    def from_latlng(self, coordinates):
        self.__init_coordinates(coordinates)

    def project(self, xy):
        # todo: find nearest point
        min_point = None
        min_distance = None
        for line_point in self.points:
            distance = utils.distance(xy, line_point.xy)
            if min_distance is None:
                min_distance = distance
                min_point = line_point
            if distance < min_distance:
                min_distance = distance
                min_point = line_point

        return min_point, min_distance

    def find_between(self, point, layer):
        for i in range(1, len(self.notifications[layer])):
            if self.notifications[layer][i - 1].on_direction_position <= \
                    point.on_direction_position <= \
                    self.notifications[layer][i].on_direction_position:
                return self.notifications[layer][i - 1], self.notifications[layer][i]
        return None, None

    def notify(self, point):
        # todo: make binary search
        layers_between = {}
        for layer, notifications in self.notifications.items():
            for i, notification in enumerate(notifications):
                a = notification.on_direction_position - notification.entry
                b = notification.on_direction_position + notification.leave_interval[0]
                c = notification.on_direction_position + notification.leave_interval[1]
                if a <= point.on_direction_position <= notification.on_direction_position:
                    if i != 0:
                        try:
                            prev_notification = self.notifications[layer][i - 1]
                        except IndexError:
                            prev_notification = None
                    else:
                        prev_notification = None
                    notification.notify_entry(layer, point, prev_notification, direction=self)
                    layers_between[layer] = (prev_notification, point)
                    break
                elif b <= point.on_direction_position <= c:
                    try:
                        next_notification = self.notifications[layer][i + 1]
                    except IndexError:
                        next_notification = None
                    notification.notify_leave(layer, point, next_notification, direction=self)
                    layers_between[layer] = (point, next_notification)
                    break
            if layer not in layers_between:
                layers_between[layer] = self.find_between(point, layer)
        return layers_between

    def point_by_position(self, meters):
        for point in self.points:
            if point.on_direction_position >= meters:
                return point
        return None


class Geo:
    directions = []
    current_direction = None
    buffer_limit = None
    pings_time_limit = None
    pings_distance_limit = None
    out_of_route_distance_limit = None
    adjustment_layer = None

    buffer = None
    clean_buffer = None
    vector = None

    def __init__(self, buffer_limit=10, pings_time_limit=60 * 5, pings_distance_limit=300,
                 out_of_route_distance_limit=300, adjustment_layer=None):
        self.buffer_limit = buffer_limit
        self.pings_time_limit = pings_time_limit
        self.pings_distance_limit = pings_distance_limit
        self.out_of_route_distance_limit = out_of_route_distance_limit
        self.adjustment_layer = adjustment_layer
        self.buffer = deque(maxlen=buffer_limit)
        self.clean_buffer = deque(maxlen=buffer_limit)

    def add_direction(self, direction):
        assert type(direction) == Direction
        self.directions.append(direction)

    def clear(self):
        self.directions = []

    def ping(self, lat, lng):
        self.__pretty_point(lat, lng)
        self.__point_on_direction()
        between = self.current_direction.notify(self.buffer[0])
        if self.adjustment_layer:
            self.__make_adjustment(self.buffer[0], *between[self.adjustment_layer])
        logger.debug('ok direction - {}; vector - {}'.format(self.current_direction.id, self.vector))
        return self.buffer[0]

    def __make_adjustment(self, point, prev_point, next_point):
        if not prev_point or not next_point:
            return
        position = (prev_point.on_direction_position + next_point.on_direction_position) / 2
        adj_point = self.current_direction.point_by_position(position)
        point.set_adjustment_data(adj_point)

    def __point_on_direction(self):
        if not self.current_direction:
            direction = self.__determine_direction()
            self.current_direction = direction
        else:
            self.__going_by_direction()
            if not self.__am_i_going_forward():
                direction = self.__determine_direction()
                logger.info('DIRECTION CHANGED')
                self.current_direction = direction

    @staticmethod
    def __project_on_direction(point, direction):
        n_point, distance = direction.project(point.original_xy)
        point.set_data(n_point)
        return point, distance

    # defines if point is going forward for given direction
    def __going_by_direction(self, points=None, direction=None, clean_up=True):
        if not points:
            points = self.buffer[1], self.buffer[0]
        prev_point, current_point = points
        if not direction:
            direction = self.current_direction
        if not prev_point.by_direction.get(direction.id):
            prev_point, distance = self.__project_on_direction(prev_point, direction)
            prev_point.by_direction[direction.id] = 0
        delta = None
        if not current_point.by_direction.get(direction.id):
            current_point, distance = self.__project_on_direction(current_point, direction)
            if distance > self.out_of_route_distance_limit:
                if clean_up:
                    self.__clean()
                raise exceptions.OutOfRouteException()

        delta = current_point.on_direction_position - prev_point.on_direction_position if delta is None else delta
        if delta > 0:
            forward_direction = 1  # going forward by direction
        elif delta < 0:
            forward_direction = -1  # going backward by direction
        else:
            forward_direction = 0  # not moving
        if forward_direction != 0:
            self.clean_buffer.append(current_point)
        current_point.by_direction[direction.id] = forward_direction
        return forward_direction

    def __am_i_going_forward(self, points=None, direction=None):
        if not points:
            points = self.clean_buffer
        if not direction:
            direction = self.current_direction
        forward_direction = sum([p.by_direction.get(direction.id, 0) for p in points])
        self.vector = forward_direction
        if forward_direction > 0:
            return True
        else:
            return False

    def __determine_direction(self):
        out_of_route_count = 0
        for direction in self.directions:
            first_point = self.buffer[self.buffer_limit - 1]
            if not first_point.by_direction.get(direction.id):
                first_point.by_direction[direction.id] = 0

            # buffer deque is backward, index = 0 is latest
            for i in range(self.buffer_limit - 2, -1, -1):
                try:
                    self.__going_by_direction(points=(self.buffer[i+1],
                                                      self.buffer[i]),
                                              direction=direction,
                                              clean_up=False)
                except exceptions.OutOfRouteException:
                    self.buffer[i].by_direction[direction.id] = -1
                    out_of_route_count += 1
                    break

            if self.__am_i_going_forward(points=self.buffer,
                                         direction=direction):
                return direction
        self.__clean()
        if len(self.directions) == out_of_route_count:
            raise exceptions.OutOfRouteException()
        logger.debug('direction not found')
        raise exceptions.DirectionNotFound()

    def __pretty_point(self, lat, lng):
        if int(lat) == 0 and int(lng) == 0:
            logger.debug("zeroes")
            self.__clean()
            raise exceptions.ZeroCoordinateException()
        point = Point.from_latlng(lat, lng)
        if not self.buffer:
            logger.debug('first point')
            self.buffer.appendleft(point)
            raise exceptions.BufferNotFullException()
        else:
            if self.buffer[0].original_latlng == point.original_latlng:
                logger.debug("same coordinates")
                raise exceptions.SameCoordinateException()

            if abs(point.timestamp - self.buffer[0].timestamp) >= self.pings_time_limit:
                logger.debug('time limit reached')
                self.__clean()
                raise exceptions.TimeLimitExitedException()
            # distance = utils.distance(point.original_xy, self.buffer[0].original_xy)
            # if distance > self.pings_distance_limit:
            #     logger.debug('distance limit reached')
            #     self.__clean()
            #     raise exceptions.DistanceLimitExited(str(distance))

            self.buffer.appendleft(point)
            if len(self.buffer) < self.buffer_limit:
                logger.debug('filling up buffer')
                raise exceptions.BufferNotFullException()

    def __clean(self):
        self.current_direction = None
        self.buffer.clear()
        self.clean_buffer.clear()
        self.vector = None



