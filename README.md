# pygeo
library for working with geo coordinates, polyline   

## usage
enable loggin with level DEBUG
```python
import logging
logging.basicConfig(level='DEBUG')
```

```python
from pygeo import Geo, Direction
# layer for notifications
PLATFORM_LAYER = 'platforms'

# limit how many points to hold to determine direction, greater value greater accuracy
BUFFER_LIMIT = 10
# limit of time is acceptable, if difference between pings out of limit the app is reloaded
PING_TIME_LIMIT = 60 * 5
# limit of distance is acceptable, if distance between pings out of limit the app is reloaded
PING_DISTANCE_LIMIT = 300
# limit of distance to determine out of route status
OUT_OF_ROUTE_DISTANCE = 300
# layer of notification used to make shuttle buses between given layer
ADJUSTMENT_LAYER = PLATFORM_LAYER
# initialize the main class
geo = Geo(buffer_limit=BUFFER_LIMIT, 
          pings_time_limit=PING_TIME_LIMIT, 
          pings_distance_limit=PING_DISTANCE_LIMIT,
          out_of_route_distance_limit=OUT_OF_ROUTE_DISTANCE, 
          adjustment_layer=ADJUSTMENT_LAYER)

# creating the directions
ID = 1
# length of segment to split the direction
SEGMENT_LENGTH = 10
# limit of distance between direction and notification than can be safely added
NOTIFICATION_DISTANCE_LIMIT = 300
direction = Direction(id=ID, 
                      segment_length=SEGMENT_LENGTH, notification_distance_limit=NOTIFICATION_DISTANCE_LIMIT)
# initialize direction with polyline
direction.from_polyline('valid pilyline')
# or with valid [[lat, lng]] array
direction.from_latlng([[0,0]])

# append notification point to direction
NOTIFICATION_ID = 1
NOTIFICATION_LAT = 0
NOTIFICATION_LNG = 0
NOTIFICATION_ENTRY_DISTANCE = 30
NOTIFICATION_LEAVE_INTERVAL = (10, 50)
def notification_entry_trigger(*args, **kwargs):
    ...
def notification_leave_trigger(*args, **kwargs):
    ... 
# in inobi terminology
# notification - platform (bus stop)
direction.add_notification(id=ID, 
                           lat=NOTIFICATION_LAT, 
                           lng=NOTIFICATION_LNG,
                           layer=PLATFORM_LAYER,
                           entry_distance=NOTIFICATION_ENTRY_DISTANCE,
                           leave_interval=NOTIFICATION_LEAVE_INTERVAL,
                           entry_trigger=notification_entry_trigger,
                           leave_trigger=notification_leave_trigger)
                           
                           
geo.ping(0, 0)


```