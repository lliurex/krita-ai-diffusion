Server
======

.. currentmodule:: websockets.asyncio.server

.. admonition:: This FAQ is written for the new :mod:`asyncio` implementation.
    :class: hint

    Answers are also valid for the legacy :mod:`asyncio` implementation.

    They translate to the :mod:`threading` implementation by removing ``await``
    and ``async`` keywords and by using a :class:`~threading.Thread` instead of
    a :class:`~asyncio.Task` for concurrent execution.

Why does the server close the connection prematurely?
-----------------------------------------------------

Your connection handler exits prematurely. Wait for the work to be finished
before returning.

For example, if your handler has a structure similar to::

    async def handler(websocket):
        asyncio.create_task(do_some_work())

change it to::

    async def handler(websocket):
        await do_some_work()

Why does the server close the connection after one message?
-----------------------------------------------------------

Your connection handler exits after processing one message. Write a loop to
process multiple messages.

For example, if your handler looks like this::

    async def handler(websocket):
        print(websocket.recv())

change it like this::

    async def handler(websocket):
        async for message in websocket:
            print(message)

If you have prior experience with an API that relies on callbacks, you may
assume that ``handler()`` is executed every time a message is received. The API
of websockets relies on coroutines instead.

The handler coroutine is started when a new connection is established. Then, it
is responsible for receiving or sending messages throughout the lifetime of that
connection.

Why can only one client connect at a time?
------------------------------------------

Your connection handler blocks the event loop. Look for blocking calls.

Any call that may take some time must be asynchronous.

For example, this connection handler prevents the event loop from running during
one second::

    async def handler(websocket):
        time.sleep(1)
        ...

Change it to::

    async def handler(websocket):
        await asyncio.sleep(1)
        ...

In addition, calling a coroutine doesn't guarantee that it will yield control to
the event loop.

For example, this connection handler blocks the event loop by sending messages
continuously::

    async def handler(websocket):
        while True:
            await websocket.send("firehose!")

:meth:`~ServerConnection.send` completes synchronously as long as there's space
in send buffers. The event loop never runs. (This pattern is uncommon in
real-world applications. It occurs mostly in toy programs.)

You can avoid the issue by yielding control to the event loop explicitly::

    async def handler(websocket):
        while True:
            await websocket.send("firehose!")
            await asyncio.sleep(0)

All this is part of learning asyncio. It isn't specific to websockets.

See also Python's documentation about `running blocking code`_.

.. _running blocking code: https://docs.python.org/3/library/asyncio-dev.html#running-blocking-code

.. _send-message-to-all-users:

How do I send a message to all users?
-------------------------------------

Record all connections in a global variable::

    CONNECTIONS = set()

    async def handler(websocket):
        CONNECTIONS.add(websocket)
        try:
            await websocket.wait_closed()
        finally:
            CONNECTIONS.remove(websocket)

Then, call :func:`~websockets.asyncio.server.broadcast`::

    from websockets.asyncio.server import broadcast

    def message_all(message):
        broadcast(CONNECTIONS, message)

If you're running multiple server processes, make sure you call ``message_all``
in each process.

.. _send-message-to-single-user:

How do I send a message to a single user?
-----------------------------------------

Record connections in a global variable, keyed by user identifier::

    CONNECTIONS = {}

    async def handler(websocket):
        user_id = ...  # identify user in your app's context
        CONNECTIONS[user_id] = websocket
        try:
            await websocket.wait_closed()
        finally:
            del CONNECTIONS[user_id]

Then, call :meth:`~ServerConnection.send`::

    async def message_user(user_id, message):
        websocket = CONNECTIONS[user_id]  # raises KeyError if user disconnected
        await websocket.send(message)  # may raise websockets.exceptions.ConnectionClosed

Add error handling according to the behavior you want if the user disconnected
before the message could be sent.

This example supports only one connection per user. To support concurrent
connections by the same user, you can change ``CONNECTIONS`` to store a set of
connections for each user.

If you're running multiple server processes, call ``message_user`` in each
process. The process managing the user's connection sends the message; other
processes do nothing.

When you reach a scale where server processes cannot keep up with the stream of
all messages, you need a better architecture. For example, you could deploy an
external publish / subscribe system such as Redis_. Server processes would
subscribe their clients. Then, they would receive messages only for the
connections that they're managing.

.. _Redis: https://redis.io/

How do I send a message to a channel, a topic, or some users?
-------------------------------------------------------------

websockets doesn't provide built-in publish / subscribe functionality.

Record connections in a global variable, keyed by user identifier, as shown in
:ref:`How do I send a message to a single user?<send-message-to-single-user>`

Then, build the set of recipients and broadcast the message to them, as shown in
:ref:`How do I send a message to all users?<send-message-to-all-users>`

:doc:`../howto/django` contains a complete implementation of this pattern.

Again, as you scale, you may reach the performance limits of a basic in-process
implementation. You may need an external publish / subscribe system like Redis_.

.. _Redis: https://redis.io/

How do I pass arguments to the connection handler?
--------------------------------------------------

You can bind additional arguments to the connection handler with
:func:`functools.partial`::

    import functools

    async def handler(websocket, extra_argument):
        ...

    bound_handler = functools.partial(handler, extra_argument=42)

Another way to achieve this result is to define the ``handler`` coroutine in
a scope where the ``extra_argument`` variable exists instead of injecting it
through an argument.

How do I access the request path?
---------------------------------

It is available in the :attr:`~ServerConnection.request` object.

You may route a connection to different handlers depending on the request path::

    async def handler(websocket):
        if websocket.request.path == "/blue":
            await blue_handler(websocket)
        elif websocket.request.path == "/green":
            await green_handler(websocket)
        else:
            # No handler for this path; close the connection.
            return

You may also route the connection based on the first message received from the
client, as shown in the :doc:`tutorial <../intro/tutorial2>`. When you want to
authenticate the connection before routing it, this is usually more convenient.

Generally speaking, there is far less emphasis on the request path in WebSocket
servers than in HTTP servers. When a WebSocket server provides a single endpoint,
it may ignore the request path entirely.

How do I access HTTP headers?
-----------------------------

You can access HTTP headers during the WebSocket handshake by providing a
``process_request`` callable or coroutine::

    def process_request(connection, request):
        authorization = request.headers["Authorization"]
        ...

    async with serve(handler, process_request=process_request):
        ...

Once the connection is established, HTTP headers are available in the
:attr:`~ServerConnection.request` and :attr:`~ServerConnection.response`
objects::

    async def handler(websocket):
        authorization = websocket.request.headers["Authorization"]

How do I set HTTP headers?
--------------------------

To set the ``Sec-WebSocket-Extensions`` or ``Sec-WebSocket-Protocol`` headers in
the WebSocket handshake response, use the ``extensions`` or ``subprotocols``
arguments of :func:`~serve`.

To override the ``Server`` header, use the ``server_header`` argument. Set it to
:obj:`None` to remove the header.

To set other HTTP headers, provide a ``process_response`` callable or
coroutine::

    def process_response(connection, request, response):
        response.headers["X-Blessing"] = "May the network be with you"

    async with serve(handler, process_response=process_response):
        ...

How do I get the IP address of the client?
------------------------------------------

It's available in :attr:`~ServerConnection.remote_address`::

    async def handler(websocket):
        remote_ip = websocket.remote_address[0]

How do I set the IP addresses that my server listens on?
--------------------------------------------------------

Use the ``host`` argument of :meth:`~serve`::

    async with serve(handler, host="192.168.0.1", port=8080):
        ...

:func:`~serve` accepts the same arguments as
:meth:`~asyncio.loop.create_server` and passes them through.

What does ``OSError: [Errno 99] error while attempting to bind on address ('::1', 80, 0, 0): address not available`` mean?
--------------------------------------------------------------------------------------------------------------------------

You are calling :func:`~serve` without a ``host`` argument in a context where
IPv6 isn't available.

To listen only on IPv4, specify ``host="0.0.0.0"`` or ``family=socket.AF_INET``.

Refer to the documentation of :meth:`~asyncio.loop.create_server` for details.

How do I close a connection?
----------------------------

websockets takes care of closing the connection when the handler exits.

How do I stop a server?
-----------------------

Exit the :func:`~serve` context manager.

Here's an example that terminates cleanly when it receives SIGTERM on Unix:

.. literalinclude:: ../../example/faq/shutdown_server.py
    :emphasize-lines: 13-16,19

How do I stop a server while keeping existing connections open?
---------------------------------------------------------------

Call the server's :meth:`~Server.close` method with ``close_connections=False``.

Here's how to adapt the example just above::

    async def server():
        ...

        server = await serve(echo, "localhost", 8765)
        await stop
        server.close(close_connections=False)
        await server.wait_closed()

How do I implement a health check?
----------------------------------

Intercept requests with the ``process_request`` hook. When a request is sent to
the health check endpoint, treat is as an HTTP request and return a response:

.. literalinclude:: ../../example/faq/health_check_server.py
    :emphasize-lines: 7-9,16

:meth:`~ServerConnection.respond` makes it easy to send a plain text response.
You can also construct a :class:`~websockets.http11.Response` object directly.

How do I run HTTP and WebSocket servers on the same port?
---------------------------------------------------------

You don't.

HTTP and WebSocket have widely different operational characteristics. Running
them with the same server becomes inconvenient when you scale.

Providing an HTTP server is out of scope for websockets. It only aims at
providing a WebSocket server.

There's limited support for returning HTTP responses with the
``process_request`` hook.

If you need more, pick an HTTP server and run it separately.

Alternatively, pick an HTTP framework that builds on top of ``websockets`` to
support WebSocket connections, like Sanic_.

.. _Sanic: https://sanicframework.org/en/
