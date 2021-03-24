#!/usr/bin/env python3
"""Simple example of how the event systems of PyGame and the distributed event queue
can be used.
This version adds an example of extrapolation to hide some effects of low update frequencies.
"""
import os
import random
import time
import sys
import pygame
import eventclient_async
from config import SERVER, PORT

# The minimum number of seconds between each time a local object sends an update to the other clients.
# Play with this value to see the effect of the update rate.
RATE_LIMIT = 1.0 / 10    # 1.0s / 10 Hz

SCREEN_X = 640
SCREEN_Y = 480

# Used for get_id and tlocal
_id_max = 0
_id_base = os.getpid()
_time_0 = None


def get_id():
    """Compute a unique ID that can be used for each object."""
    global _id_max
    _id_max += 1
    return f"{_id_base}-{_id_max}"


def tlocal():
    """Returns time passed (in seconds) since the first call to tlocal().
    The main reason for using this instead of time.time() directly is that the smaller values
    makes debugging slightly easier.
    """
    global _time_0
    if _time_0 is None:
        _time_0 = time.time()
        return 0.0
    return time.time() - _time_0


def round_pos(pos):
    return [round(v) for v in pos]


class MovingObject:
    def __init__(self):
        self.pos = [42, 200]
        self.speed = [50 + 60 * random.random(),
                      50 + 60 * random.random()]
        self.size = 20

    def move(self, time_passed):
        self.pos[0] += self.speed[0] * time_passed
        self.pos[1] += self.speed[1] * time_passed

        if self.pos[0] < 0:
            self.speed[0] = abs(self.speed[0])
        if self.pos[1] < 0:
            self.speed[1] = abs(self.speed[1])

        if self.pos[0] > SCREEN_X - self.size:
            self.speed[0] = -abs(self.speed[0])
        if self.pos[1] > SCREEN_Y - self.size:
            self.speed[1] = -abs(self.speed[1])

    def draw(self):
        print("Fyyy")


class LocalObj(MovingObject):
    """Used to represent local objects (where the computation is done locally)"""
    def __init__(self):
        super().__init__()
        self.id = get_id()
        self.col = (255, 0, 0)
        self._last_send = 0
        print("poink")

    def move(self, time_passed):
        super().move(time_passed)
        # Send information about own state to remote clients
        # To limit the amount of data sent, we could limit the transfer rate to lower than the update rate
        # of the clients (ex: client runs at 30Hz, but sends at 5-10Hz). This example shows one way of
        # doing this (only send if it's more than Xs since the last time we sent).
        tnow = tlocal()
        if tnow - self._last_send > RATE_LIMIT:
            event_dist.send_event({'id' : self.id, 'pos': self.pos, 'speed': self.speed, 'time': tnow})
            self._last_send = tnow

    def draw(self):
        pygame.draw.circle(screen, self.col, round_pos(self.pos), round(self.size / 2))


class RemoteObj(MovingObject):
    """Used to represent remote objects"""
    def __init__(self, _id, msg):
        super().__init__()
        self.id = _id
        self.col = (0, 255, 0)
        self.apply_msg(msg)

    def apply_msg(self, msg):
        "Copies relevant information from the event/msg to the local object"
        self.last_msg = msg
        self.pos = msg['pos'].copy()    # make sure to work on a copy, not the original

    def age(self):
        "Returns the number of seconds since an update to this object was received"
        return tlocal() - self.last_msg['t_recv']

    def move(self, time_passed):
        # Could also consider extrapolation to predict position of remote
        # First attempt: extrapolation based on time since received.
        # This version is vulnerable to jitter and lag, but it's a significant improvement to no extrapolation.
        p0 = self.last_msg['pos'].copy()   # make sure to work on a copy, not the original
        v = self.last_msg['speed']
        dt = self.age()
        for i in range(2):
            self.pos[i] = p0[i] + v[i] * dt

    def draw(self):
        pygame.draw.circle(screen, self.col, round_pos(self.pos), round(self.size / 2))


def handle_msg(msg):
    rid = msg.get('id', None)
    if rid:
        if rid in objects:
            objects[rid].apply_msg(msg)
        else:
            print("Adding new object with id", rid)
            objects[rid] = RemoteObj(rid, msg)


pygame.init()
screen = pygame.display.set_mode((SCREEN_X, SCREEN_Y), 0, 32)

event_dist = eventclient_async.ConnHandler(SERVER, PORT)

objects = {}
for i in range(10):
    obj = LocalObj()
    objects[obj.id] = obj

clock = pygame.time.Clock()
while True:
    # Let PyGame deal with internal envent processing, and respond to events from PyGame
    events = pygame.event.get()
    for event in events:
        if event.type == pygame.QUIT:
            sys.exit(0)

    # Let asyncio deal with internal event processing, and respond to events/messages
    # from the event distribution system.
    for event in event_dist.get_events():
        event['t_recv'] = tlocal()  # add timestamp when the object was received
        handle_msg(event)

    time_passed = clock.tick(30) / 1000.0

    for obj in objects.values():
        obj.move(time_passed)

    for obj in list(objects.values()):
        if isinstance(obj, RemoteObj) and obj.age() > 10:
            print("Removing old object with id", obj.id)
            del objects[obj.id]

    screen.fill((0, 0, 0))
    for obj in objects.values():
        obj.draw()

    pygame.display.update()
