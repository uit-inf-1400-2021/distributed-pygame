#!/usr/bin/env python3

"""
TK has opened up port TCP/UDP 32000-33000 on ifilab100.stud.cs.uit.no.

This computer is restarted around 05:05 every day to clean up after people that forgot
to remove things.

This is a very simple version of a cetralized event pub/sub system.


"""

import sys
import asyncio

DEBUG = False
PORT = int(sys.argv[1]) if len(sys.argv) >= 2 else 32100


async def send_to_clients(msg, sender):
    """Queue message with all clients except sender"""
    for cl in ClientHandler.clients:
        if cl == sender:
            continue
        await cl.add(msg)


class ClientHandler:
    clients = []

    def __init__(self, reader, writer):
        print("new client", reader, writer)
        self.in_stream = reader
        self.out_stream = writer
        self._send_queue = asyncio.Queue()
        self.clients.append(self)

    async def add(self, msg):
        "Add message to outgoing queue"
        await self._send_queue.put(msg)

    async def close(self):
        "Close connection and remove client from list"
        self.out_stream.close()
        await self.out_stream.wait_closed()
        print(self.clients)
        self.clients.remove(self)
        print(self.clients)

    async def _sender(self):
        "Task that waits for queued messages and sends them to the client one by one"
        while True:
            msg = await self._send_queue.get()
            if self.out_stream.is_closing():
                print("sender:socket closed")
                break
            if DEBUG:
                print("sender:sending", msg)
            self.out_stream.write(msg)
            await self.out_stream.drain()

    async def _receiver(self):
        "Receives from client and forwards the received message to other clients"
        while True:
            msg = await self.in_stream.readline()
            if DEBUG:
                print("_receiver:received", msg)
            if len(msg) == 0 and self.in_stream.at_eof():
                print("_receiver:Lost client")
                break
            await send_to_clients(msg, self)
        await self.close()

    async def run(self):
        "Starts sender and receiver tasks and waits for them to complete"
        subtasks = [
            asyncio.create_task(self._receiver()),
            asyncio.create_task(self._sender())
        ]
        for task in subtasks:
            await task


async def client_connection(reader, writer):
    "handler for incoming connections"
    await ClientHandler(reader, writer).run()


# Based on
# https://asyncio.readthedocs.io/en/latest/tcp_echo.html
loop = asyncio.get_event_loop()
server = loop.run_until_complete(asyncio.start_server(client_connection, '0.0.0.0', PORT, loop=loop))

print(f"Server running on {server.sockets[0].getsockname()}")
try:
    loop.run_forever()
except KeyboardInterrupt:
    pass

server.close()
loop.run_until_complete(server.wait_closed())
loop.close()
