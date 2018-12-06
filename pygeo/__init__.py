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
    by_direction = None  # -1, 1 acceptable values

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



class Notification(BasePoint):
    id = None
    entry = None
    leave_interval = None
    entry_trigger = None
    leave_trigger = None

    def __init__(self, id, lat, lng, entry=None, leave_interval=None, enter_trigger=None, leave_trigger=None):
        super().__init__(lat, lng)
        self.id = id

        # todo: make validation on entry and leave -> must be positive

        self.entry = entry
        # todo: make validation on leave interval -> must be (1, 2)
        self.leave_interval = leave_interval
        self.entry_trigger = enter_trigger
        self.leave_trigger = leave_trigger

    def notify_entry(self):
        self.entry_trigger(self.id)

    def notify_leave(self):
        self.leave_trigger(self.id)


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
        self.notifications = []

    def add_notification(self, id, lat, lng, enter=None, leave=None, enter_trigger=None, leave_trigger=None):
        notification = Notification(id, lat, lng, enter, leave, enter_trigger, leave_trigger)
        point, distance = self.project(notification.xy)
        if distance > self.notification_distance_limit:
            raise exceptions.NotificationDistanceLimitExitedException("notification point must be close to direction")
        notification.on_direction_position = point.on_direction_position
        self.notifications.append(notification)
        self.notifications = sorted(self.notifications, key=lambda x: x.on_direction_position)

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

    def project(self, xy, raise_exception=True):
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

    def notify(self, point):
        # todo: make binary search
        for notification in self.notifications:
            a = notification.on_direction_position - notification.entry
            b = notification.on_direction_position + notification.leave_interval[0]
            c = notification.on_direction_position + notification.leave_interval[1]
            if a <= point.on_direction_position <= notification.on_direction_position:
                notification.notify_entry()
            elif b <= point.on_direction_position <= c:
                notification.notify_leave()


class Geo:
    directions = []
    current_direction = None
    buffer_limit = 10
    time_limit = 60 * 5
    distance_limit = 200
    out_of_route_distance_limit = 200

    buffer = deque(maxlen=buffer_limit)
    clean_buffer = deque(maxlen=buffer_limit)

    def add_direction(self, direction):
        assert type(direction) == Direction
        self.directions.append(direction)

    def clear(self):
        self.directions = []

    def ping(self, lat, lng):
        self.__pretty_point(lat, lng)
        self.__point_on_direction()
        self.current_direction.notify(self.buffer[0])
        logger.debug('ok')
        return self.buffer[0]

    def __point_on_direction(self):
        if not self.current_direction:
            direction = self.__determine_direction()
            self.current_direction = direction
        else:
            self.__going_by_direction()
            if not self.__am_i_going_forward():
                direction = self.__determine_direction()
                self.current_direction = direction

    @staticmethod
    def __project_on_direction(point, direction):
        n_point, distance = direction.project(point.original_xy)
        point.set_data(n_point)
        return point, distance

    # defines if point is going forward for given direction
    def __going_by_direction(self, points=None, direction=None, raise_exception=True, clean=True):
        if not points:
            points = self.buffer[1], self.buffer[0]
        prev_point, current_point = points
        if not direction:
            direction = self.current_direction
        if not prev_point.by_direction.get(direction.id):
            prev_point, distance = self.__project_on_direction(prev_point, direction)

        if not current_point.by_direction.get(direction.id):
            current_point, distance = self.__project_on_direction(current_point, direction)
            if distance > self.out_of_route_distance_limit and raise_exception:
                logger.debug('out of route')
                if clean:
                    self.__clean()
                raise exceptions.OutOfRouteException()
        delta = current_point.on_direction_position - prev_point.on_direction_position
        if delta > 0:
            forward_direction = 1  # going forward by direction
            self.clean_buffer.append(current_point)
        elif delta < 0:
            forward_direction = -1  # going backward by direction
            self.clean_buffer.append(current_point)
        else:
            forward_direction = 0  # not moving

        current_point.by_direction[direction.id] = forward_direction
        return forward_direction

    def __am_i_going_forward(self, points=None, direction=None):
        if not points:
            points = self.clean_buffer
        if not direction:
            direction = self.current_direction
        forward_direction = sum([p.by_direction[direction.id] for p in points])
        if forward_direction > 0:
            return True
        else:
            return False

    def __determine_direction(self):
        for direction in self.directions:
            first_point = self.buffer[self.buffer_limit - 1]
            if not first_point.by_direction.get(direction.id):
                first_point.by_direction[direction.id] = 0

            try:
                # buffer deque is backward, index = 0 is latest
                for i in range(self.buffer_limit - 2, -1, -1):

                    self.__going_by_direction(points=(self.buffer[i+1],
                                                      self.buffer[i]),
                                              direction=direction,
                                              raise_exception=True,
                                              clean=False)

            except exceptions.OutOfRouteException:
                continue
            if self.__am_i_going_forward(points=self.buffer,
                                         direction=direction):
                return direction
        self.__clean()
        logger.debug('direction not found')
        raise exceptions.OutOfRouteException()

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

            if abs(point.timestamp - self.buffer[0].timestamp) >= self.time_limit:
                logger.debug('time limit reached')
                self.__clean()
                raise exceptions.TimeLimitExitedException()
            distance = utils.distance(point.original_xy, self.buffer[0].original_xy)
            if distance > self.distance_limit:
                logger.debug('distance limit reached')
                self.__clean()
                raise exceptions.DistanceLimitExited(str(distance))

            self.buffer.appendleft(point)
            if len(self.buffer) < self.buffer_limit:
                logger.debug('filling up buffer')
                raise exceptions.BufferNotFullException()

    def __clean(self):
        self.current_direction = None
        self.buffer.clear()
        self.clean_buffer.clear()



