#!/usr/bin/env python

import asyncio
import signal

from websockets.asyncio.server import serve


async def echo(websocket):
    async for message in websocket:
        await websocket.send(message)


async def main():
    # Set the stop condition when receiving SIGTERM.
    loop = asyncio.get_running_loop()
    stop = loop.create_future()
    loop.add_signal_handler(signal.SIGTERM, stop.set_result, None)

    async with serve(
        echo,
        host="",
        port=8080,
        reuse_port=True,
    ):
        await stop


if __name__ == "__main__":
    asyncio.run(main())
