Warning: here be dragons!  (Plenty of them). 
==========================

This was quickly whipped together to provide a starting point for
making a distributed version of the third mandatory assignment. 

The example code has three files so far:

* eventserver.py   - intended to run on a computer that the clients can reach
* eventclient_async.py - asyncio based event library that can be used in the client
* async_and_pygame.py - example program based on one of the PyGame examples in the course. 
   Shows how to combine the distributed event system with PyGame. 

The intented use is to start eventserver.py on a node reachable by the
clients. You can specify the port number that the server should use to
listen for clients. Try to pick a port number that other people don't
use, or you might have multiple different games sharing events.

The example program shows how to use the event library to connect to a
host+port and send events to other clients as well as listen to events
from the clients.

The main interface to look for is how to create a local proxy for the
event distribution system (this is the object you use for sending and
receiving events):

```Python
event_dist = eventclient_async.ConnHandler('localhost', 32100)

```

The way to send an event is to represent the event as something that
can be encoded as JSON. Use basic data types from Python, such as
dicts, strings and lists.


```Python
event_dist.send_event({'id' : self.id, 'pos': self.pos})
```

To receive events, you can use a similar method to how you get events from 
PyGame: 

```Python
for event in event_dist.get_events():
    print(event)
```

That should be it. 


Running the server on ifilab100
-------------------

TK has opened up port TCP/UDP 32000-33000 on ifilab100.stud.cs.uit.no.

This computer is restarted around 05:05 every day to clean up after
people that forgot to remove things.

To run the server, pick a port number that is not used by somebody
else already. You could use the course Discord to coordinate this.

Note that the computer has a fairly old distribution of Linux, and the
default Python 3 version is a bit too old. To run the server, you can
use a newer version of Python from /opt:

``` 
/opt/python387/bin/python3 eventserver.py
```

Or, if you want to specify a port number: 

``` 
/opt/python387/bin/python3 eventserver.py 32105
```

Some warnings
-------------

There are, of course, several potential problems with distributed systems: 

* lag - if the network is slow between clients, the time between a
  send in one client to another client rendering the update can be
  high. This may not just be the network. It can also be that the
  client is slow to apply the update.

* lag spikes - events may flow fine for a bit and something might
  happen that causes them pile up somewhere. 
  
* too high demand on network throughput - if you try to send too many
  messages per second, you might end up sending more than your
  network, client or server can handle.

And plenty more, but this should be an easy starting point. 

One of the ways to handle lag and throughput issues is to limit the
number of updates you send per second. Look for `RATE_LIMIT` in the
pygame example to see one way of this this. 

The drawback of limiting rate is that objects get a less fluid motion
on the screen: with a low rate, they jump around on the screen every
time they get an update. To deal with this, you could try
extrapolation, which again is a whole subject in itself, but the basic
idea is to either

* get both position and speed and then look use the speed to guess
  where the object might be based on the time elapse since the update
  event was received.
* use a history of updates for an object (along with timestamps) to
  try to compute a likely future position of the object.

These can also be combined in fairly elaborate ways to make the
objects appear to move smoother.

Be careful. Extrapolation and distributed real time gaming are rabbit
holes where you can spend a lifetime ;-)

Notes for the curious 
======================

You don't necessarily need to read this to use the library, but it
might help you spot some issues.

Using multiple event systems together
---------------------------

This easily causes several issues. One of the key problems is that
event based libraries expect to let their "event loop" take control
and handle events that happen in the system. Now we have two event
systems (PyGame and asyncio) that both need control to be able to wait
for things to happen and to respond to them.

This example code alternates between the two by first letting PyGame
be in control for a little bit and then doing the same with asyncio:

```Python
    # Let PyGame deal with internal envent processing, and respond to events from PyGame
    events = pygame.event.get()
    for event in events:
        if event.type == pygame.QUIT:
            exit(0)

    # Let asyncio deal with internal event processing, and respond to events/messages
    # from the event distribution system.
    for event in event_dist.get_events():
        handle_msg(event)
```

There are other ways of dealing with this, but this was a quick way
that didn't introduce too many strange things. 

Another issue is that asyncio is based on suspending and resuming
coroutines, and that this is controlled by the asyncio event
loop. Fetching events from an asyncio Queue using get_nowait() (see
get_events()) doesn't let the event queue run. The effect is that the
sender and receiver tasks don't get to run. To deal with this, the
code uses a small dirty trick: spawn a dummy task and use
asyncio.run_until_complete() to wait for that dummy task to
complete. This lets the event loop run for a bit.

Again, there are other ways of dealing with this, but this was a quick
fix.


/ John Markus Bjørndalen, 2021-03-12
