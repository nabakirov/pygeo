from . import utils, exceptions
import polyline as polylib


class BasePoint:
    lat = None
    lng = None
    x = None
    y = None
    on_direction_position = None

    def __init__(self, lat=None, lng=None):
        self.lat = lat
        self.lng = lng
        self.x, self.y = utils.flat(lat, lng) if (lat and lng) else None, None

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
    ...


class Notification(BasePoint):
    id = None
    entry = None
    leave = None
    entry_trigger = None
    leave_trigger = None

    def __init__(self, id, lat, lng, entry=None, leave=None, enter_trigger=None, leave_trigger=None):
        super().__init__(lat, lng)
        self.id = id
        self.entry = entry
        self.leave = leave
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
    points = []
    notifications = []

    def __init__(self, id, segment_length=segment_length, notification_distance_limit=notification_distance_limit):
        self.id = id
        self.segment_length = segment_length
        self.notification_distance_limit = notification_distance_limit

    def add_notification(self, id, lat, lng, enter=None, leave=None, enter_trigger=None, leave_trigger=None):
        notification = Notification(id, lat, lng, enter, leave, enter_trigger, leave_trigger)
        point, distance = self.project(notification.xy)
        if distance > self.notification_distance_limit:
            raise exceptions.PointToFarException("notification point must be close to direction")
        notification.on_direction_position = point.on_direction_position
        self.notifications.append(notification)

        # todo: sort by on direction position

    def __init_coordinates(self, coordinates):
        total_distance = 0
        first_point = Point().from_latlng(*coordinates[0])
        first_point.on_direction_position = total_distance
        self.points.append(first_point)
        for i in range(1, len(coordinates)):
            point1 = Point().from_latlng(*coordinates[i - 1])
            point2 = Point().from_latlng(*coordinates[i])
            between_points = utils.interpolate(point1.xy, point2.xy, self.segment_length)
            for j in range(1, len(between_points)):
                b_point1 = Point().from_xy(*between_points[j - 1])
                b_point2 = Point().from_xy(*between_points[j])
                total_distance += utils.distance(b_point1.xy, b_point2.xy)
                b_point2.on_direction_position = total_distance
                self.points.append(b_point2)

    def from_polyline(self, polyline):
        coordinates = polylib.decode(polyline)
        self.__init_coordinates(coordinates)

    def from_array(self, coordinates):
        self.__init_coordinates(coordinates)

    def project(self, point):
        min_point = None
        min_distance = 100000
        for line_point in self.points:
            distance = utils.distance(point, (line_point.x, line_point.y))
            if distance < min_distance:
                min_distance = distance
                min_point = line_point




        return min_point, min_distance


    # def __notify(self, point):
    #     for notification in self.notifications:
    #         a = notification.on_direction_position - notification.entry
    #         b = notification.on_direction_position + notification.leave
    #         if a <= point.on_direction_position <= notification.on_direction_position:
    #             notification.notify_entry()
    #         elif notification.on_direction_position <= point



class Geo:
    directions = []

    def add_direction(self, direction):
        self.directions.append(direction)

    def clear(self):
        self.directions = []