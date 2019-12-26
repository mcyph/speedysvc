===========================
About
===========================

This module provides very low-latency, high-throughput inter-process queues using
`shared memory`_.
It allows for basic client/server remote procedure calls (RPC), potentially with
multiple servers serving multiple clients.

It provides this via custom shared memory queues, synchronised by a hybrid
spinlock/named semaphore. This potentially allows sub-millisecond latencies,
and high throughput, at a cost of some wasted CPU cycles (up to around
1 millisecond per call). In other words, this module is useful when
parallelisation can reduce RAM usage, or when the `Global Interpreter Lock (GIL)`_
is a limiting factor. It was also intended to be a way of allowing for a
separation of concerns, effectively allowing complex programs to be separated
into smaller "blocks" or microservices.

It also allows RPC to be performed via ordinary TCP sockets. It uses a specific
protocol which sends the length of commands and data so as to improve buffering
performance with TCP. This can be around 4-5 times slower than shared memory,
but could allow connections to remote hosts.

A unique port number and service name must be provided by servers. Although the
port can be either an integer or bytes for the shared memory server, it's
normally best to keep this as a number, to allow backwards compatibility with
network sockets.

==============================
Client/Server RPC
==============================

Examples
-----------------------

test_server.py:

.. code-block:: python

    from network_tools import ServerMethodsBase, raw_method

    class TestServerMethods(ServerMethodsBase):
        port = 5555
        name = 'echo_serv'

        # json, msgpack, pickle, marshal etc are options in place of raw,
        # with significantly differing performance, serialisable types
        # and security: please see below.
        @raw_method
        def echo_raw(self, data):
            return data

test_client.py:

.. code-block:: python

    from network_tools import ClientMethodsBase
    from test_server import TestServerMethods

    class TestClientMethods(ClientMethodsBase):
        def __init__(self, client_provider):
            ClientMethodsBase.__init__(self, client_provider)

        # echo_raw = TestServerMethods.echo_raw.as_rpc()
        # can also do the same as the below code.
        def echo_raw(self, data):
            return self.send(TestServerMethods.echo_raw, [])

service.ini:

.. code-block:: ini

    [defaults]
    log_dir=/tmp/test_server_logs/

    [TestServerMethods]
    import_from=server

Then type ``python3 -m network_tools.service service.ini``
from the same directory.

Benchmarks
---------------------------

TODO!

Reference
---------------------------

TODO!

====================================
POSIX Memory Mapped Sockets
====================================

Examples
-----------------------

==============================
Hybrid Spin Semaphore
==============================

To create a hybrid spin semaphore, you need to use the
HybridLock constructor:

.. code-block:: python

    HybridLock(sem_loc, mode, initial_value, permissions)

where mode is one of:

* ``CONNECT_OR_CREATE``: Connect to an existing semaphore if it exists, otherwise
  create one.
* ``CONNECT_TO_EXISTING``: Try to connect to an existing semaphore, raising an
  ``NoSuchSemaphore`` if one couldn't be found by that name.
* ``CREATE_NEW_OVERWRITE`` Create a new semaphore, destroying the existing one
  (if one does exist).
* ``CREATE_NEW_EXCLUSIVE`` Create a new semaphore, raising a ``SemaphoreExists``
  exception if one already does.

``initial_value`` is the initial value of the semaphore (1 or 0 are the only
values possible). Note that this is only set if creating a new semaphore, this
value is otherwise ignored.

``permissions`` is who should be able to access the semaphore. For example, 0666
allows anyone to access the semaphore, whereas 0600 only allows the user who
created it (and root) to access it.

Examples
-----------------------

.. code-block:: python

    sem = HybridLock(
        'test_location', CREATE_NEW_OVERWRITE, 1, 0666
    )
    sem.lock(timeout=1)
    sem.unlock()

That's pretty much it - at the moment it only supports timeout
values in seconds using whole integers, but it should be easy
to support floating point numbers. It also would be nice to allow
for setting the maximum "spin" time.

Why not use...? Or Why?
-----------------------

It's a common situation in the c implementation of python where one is limited
by the `GIL`_, and you can't use more than a single CPU core at once for a
single process. I wanted to separate certain aspects of my software into
different processes, and call them as if they were local, with as little
difference in performance (latency and throughput) as possible.

There are a few solutions to this:

* Have a single process, and just live with only using a single core.
  (Or write modules in c/cython which bypass the GIL).

* Have multiple processes. Load modules with relevant in-memory data in
  every process. This can make good use of CPU, but use huge amounts of
  memory if you have more than a few worker processes (in my case many
  gigabytes). This can get quite expensive on cloud servers where RAM is
  at a premium, and limit options.

* Use the `multiprocessing module`_. However, this is mainly useful for
  communication between the parent process and child processes managed by the
  multiprocessing module. It also uses pipe2_ for communication, and so it
  can be slower than shared memory, as described below.

* Still have multiple processes, but move modules into external processes or
  "microservices", and use inter-process communication, or IPC to reduce
  wastage of RAM and other resources. This is the approach I decided on.

There are a number of different kinds of IPC on Linux/Unix:

* Using methods which use kernel-level synchronisation, such as sockets
  (`Unix(tm) domain sockets`_, or `TCP sockets`_), `message queues`_, or
  `pipe/pipe2`_. This can have a high latency, and was limited to 10-20,000
  requests a second in my benchmarks.

* Using shared memory, which requires process-level synchronisation to be
  performed manually by processes. Synchronisation can be performed by
  spinlocks_, `named semaphores`_ or mutexes_. This is the approach used by
  this module.

A spinlock_ as the title suggests "spins", or keeps looping asking
"are you done yet?" until the task is complete. In a single-processor
system, this will slow things down, but in a multi-processor system that
uses `pre-emptive multitasking`_ this can be faster if the task can be
completed in less than the `process time slice`_, which often is
`between 0.75ms and 6ms`_ on Linux.

By contrast, using mutexes or using binary named semaphores can prevent
wasting CPU cycles, but this can run the risk of blocking a process while
waiting for a task that takes a fraction of a millisecond. This can increase
latency by orders of magnitude for non-cpu/io-bound calls.

Currently, this module is hardcoded to spin for up to 1ms, and thereafter
leaves it up to named semaphores to block.

===========================
TODO
===========================

* It would be nice to be able to transparently call methods using
  REST, so as to allow services to use the same code.
  If this was to be implemented, it would likely allow requests
  via GET/POST only using the the encoding defined using
  server method decorators. Swagger/OpenAPI are interesting, but requires
  a fair amount of boilerplate and would require maintaining
  documentation multiple times, so are not a goal of this project.

* Docker integration would be useful. I've tried to keep this in mind
  for future refactors, making it so that the management interface
  is separate to the process managers/worker processes, the latter
  two which would be ideally be individual containers communicating
  with the host (or a dedicated management interface container).
  I'm hoping this will make this possible in the future.

* It would be nice to be able to have version-specific servers/clients,
  so that previous applications can continue to function while allowing
  for breaking changes in APIs.

===========================
Bugs/Limitations
===========================

The shared spinlock implementation could probably be optimised,
and there may be bugs when clients or servers try to
reconnect through previously used "port"s.

Please report any such bugs to [[FIXME...]]


.. _shared memory: https://en.wikipedia.org/wiki/Shared_memory
.. _Global Interpreter Lock (GIL): https://en.wikipedia.org/wiki/Global_interpreter_lock
.. _GIL: https://en.wikipedia.org/wiki/Global_interpreter_lock
.. _`multiprocessing module`: https://docs.python.org/3/library/multiprocessing.html
.. _pipe2: https://linux.die.net/man/2/pipe2
.. _Unix(tm) domain sockets: https://en.wikipedia.org/wiki/Unix_domain_socket
.. _pipe/pipe2: https://linux.die.net/man/2/pipe2
.. _message queues: http://man7.org/linux/man-pages/man7/mq_overview.7.html
.. _TCP sockets: https://en.wikipedia.org/wiki/Transmission_Control_Protocol
.. _spinlocks: https://en.wikipedia.org/wiki/Spinlock
.. _named semaphores: http://man7.org/linux/man-pages/man7/sem_overview.7.html
.. _mutexes: https://en.wikipedia.org/wiki/Lock_(computer_science)
.. _spinlock: https://en.wikipedia.org/wiki/Spinlock
.. _between 0.75ms and 6ms: https://stackoverflow.com/questions/16401294/how-to-know-linux-scheduler-time-slice
.. _pre-emptive multitasking: https://en.wikipedia.org/wiki/Preemption_(computing)#Preemptive_multitasking
.. _process time slice: https://en.wikipedia.org/wiki/Preemption_(computing)#Time_slice
