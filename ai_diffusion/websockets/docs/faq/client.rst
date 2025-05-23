Client
======

.. currentmodule:: websockets.asyncio.client

.. admonition:: This FAQ is written for the new :mod:`asyncio` implementation.
    :class: hint

    Answers are also valid for the legacy :mod:`asyncio` implementation.

    They translate to the :mod:`threading` implementation by removing ``await``
    and ``async`` keywords and by using a :class:`~threading.Thread` instead of
    a :class:`~asyncio.Task` for concurrent execution.

Why does the client close the connection prematurely?
-----------------------------------------------------

You're exiting the context manager prematurely. Wait for the work to be
finished before exiting.

For example, if your code has a structure similar to::

    async with connect(...) as websocket:
        asyncio.create_task(do_some_work())

change it to::

    async with connect(...) as websocket:
        await do_some_work()

How do I access HTTP headers?
-----------------------------

Once the connection is established, HTTP headers are available in the
:attr:`~ClientConnection.request` and :attr:`~ClientConnection.response`
objects::

    async with connect(...) as websocket:
        websocket.request.headers
        websocket.response.headers

How do I set HTTP headers?
--------------------------

To set the ``Origin``, ``Sec-WebSocket-Extensions``, or
``Sec-WebSocket-Protocol`` headers in the WebSocket handshake request, use the
``origin``, ``extensions``, or ``subprotocols`` arguments of :func:`~connect`.

To override the ``User-Agent`` header, use the ``user_agent_header`` argument.
Set it to :obj:`None` to remove the header.

To set other HTTP headers, for example the ``Authorization`` header, use the
``additional_headers`` argument::

    async with connect(..., additional_headers={"Authorization": ...}) as websocket:
        ...

In the legacy :mod:`asyncio` API, this argument is named ``extra_headers``.

How do I force the IP address that the client connects to?
----------------------------------------------------------

Use the ``host`` argument :func:`~connect`::

    async with connect(..., host="192.168.0.1") as websocket:
        ...

:func:`~connect` accepts the same arguments as
:meth:`~asyncio.loop.create_connection` and passes them through.

How do I close a connection?
----------------------------

The easiest is to use :func:`~connect` as a context manager::

    async with connect(...) as websocket:
        ...

The connection is closed when exiting the context manager.

How do I reconnect when the connection drops?
---------------------------------------------

Use :func:`~websockets.asyncio.client.connect` as an asynchronous iterator::

    from websockets.asyncio.client import connect
    from websockets.exceptions import ConnectionClosed

    async for websocket in connect(...):
        try:
            ...
        except ConnectionClosed:
            continue

Make sure you handle exceptions in the ``async for`` loop. Uncaught exceptions
will break out of the loop.

How do I stop a client that is processing messages in a loop?
-------------------------------------------------------------

You can close the connection.

Here's an example that terminates cleanly when it receives SIGTERM on Unix:

.. literalinclude:: ../../example/faq/shutdown_client.py
    :emphasize-lines: 11-13

How do I disable TLS/SSL certificate verification?
--------------------------------------------------

Look at the ``ssl`` argument of :meth:`~asyncio.loop.create_connection`.

:func:`~connect` accepts the same arguments as
:meth:`~asyncio.loop.create_connection` and passes them through.
