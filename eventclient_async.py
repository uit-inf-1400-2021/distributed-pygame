#!/usr/bin/env python3

import asyncio
import time
import json
import logging
from config import SERVER, PORT


def run_once_event_loop():
    """Workaround for missing 'event-catch-up' method on the event loop.
    Add a task to the end of the current 'ready queue' and let the event queue
    catch up a bit by running the current ready tasks until the dummy task is completed.
    The dummy task doesn't have to do anything, it's just there to let the asyncio
    event loop process for a bit (until it reaches the dummy task).
    """
    async def dummy():
        ...
    loop.run_until_complete(dummy())
    # You can also use this method:
    #   future = loop.create_future()
    #   future.set_result(True)
    #   loop.run_until_complete(future)


class ConnHandler:
    """Used as an interface to the simple distributed event distribution system.
    Specify host and port to connect to and use

    - send_event(msg) to send an event to all other (connected) clients

      handler.send_event({'id': 42, 'pos': [200, 300]})

    - get_events() to get events that have been received.

      for event in handler.get_events():
          print(event)
    """
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self._in_queue = asyncio.Queue()
        self._out_queue = asyncio.Queue()
        loop.run_until_complete(self._connect())

    # Major issue: where do we let the event queue run? Is it enough that send_event is called?
    # Periodic sends will let the receiver run as well. Queueing some async routine in the
    # receiver seems to be enough as well.
    async def _connect(self):
        self.in_stream, self.out_stream = await asyncio.open_connection(self.host, self.port)
        asyncio.create_task(self._reader())
        asyncio.create_task(self._writer())

    async def _reader(self):
        while True:
            msg = await self.in_stream.readline()
            if len(msg) == 0 and self.in_stream.at_eof():
                logging.info("Closed stream")
                break
            try:
                await self._in_queue.put(json.loads(msg))
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                logging.error("json decode failed for %s", msg)
                logging.error("exception %s", e)

    async def _writer(self):
        while True:
            msg = await self._out_queue.get()
            if self.out_stream.is_closing():
                break
            self.out_stream.write(msg.encode())
            await self.out_stream.drain()

    def send_event(self, msg):
        """Send an event (typically represented as a dict) to other clients."""
        jstr = json.dumps(msg) + "\n"
        loop.run_until_complete(self._out_queue.put(jstr))

    def get_events(self):
        """Yields incoming events until the queue is empty."""
        run_once_event_loop()
        while True:
            try:
                yield self._in_queue.get_nowait()
            except asyncio.QueueEmpty:
                return


def client_test():
    evconn = ConnHandler(SERVER, PORT)
    print("trying to receive a bit before sending messages to the other side")
    for i in range(60):
        time.sleep(0.3)
        for event in evconn.get_events():
            print(event)
        # Only send after a while to check that sending is not required for receiving messages.
        if i > 30:
            print("sending")
            evconn.send_event({'msg': 'foobar', 'count': i})
    print("Asyncio will now file some complaints because we don't shut down the readers and writers properly.")
    # TODO: should probably close the writer's socket using writer.close(). See https://docs.python.org/3/library/asyncio-stream.html


loop = asyncio.get_event_loop()
if __name__ == "__main__":
    client_test()
