

class BaseException(Exception):
    ...


class NotificationDistanceLimitExitedException(BaseException):
    ...


class DirectionNotFound(BaseException):
    ...


class OutOfRouteException(BaseException):
    ...



class ValidationException(BaseException):
    ...


class SameCoordinateException(ValidationException):
    ...


class ZeroCoordinateException(ValidationException):
    ...


class TimeLimitExitedException(ValidationException):
    ...


class DistanceLimitExited(ValidationException):
    ...


class BufferNotFullException(ValidationException):
    ...


