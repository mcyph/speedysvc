===========================
About
===========================

    NOTE: This module's status is still alpha - I'm using it in my projects, but
    is still under active development. There are likely bugs and there will be
    breaking changes to the API.

This module provides low-latency, high-throughput interprocess queues using
`shared memory`_. It allows for basic client/server interprocess method
calls using these queues, with multiple server workers serving
multiple clients. It is released under the MIT License.

When the server is on a different PC to the client, remote procedure calls
(RPC) are also supported over standard TCP/IP, with a fast and efficient
protocol.

While there are multiple libraries for python that can allow for interprocess
communication, most don't use shared memory, or use synchronisation that can make
them orders of magnitude slower. Unlike the python mmap_ module, this does not page
written data to file on disk (is not `copy-on-write`_) often resulting in performance
not much less than if functions were called in-process.

Other capabilities:

* A management web interface based on flask, showing logs/performance data for each
  service, and allowing stopping/starting services individually.
* Multiple servers can serve to multiple clients: additional server worker processes
  can optionally start when overall CPU usage exceeds a certain %. This helps to work
  around the often-cited GIL_ limitations of python.
* Not much boilerplate code required, with the server only requiring an encoding type
  decorator, like ``@json_method``. Clients verify all their method names match with
  the server's. They copy the port/name from the server, so as to reduce the amount of
  places things need to be kept up-to-date.

Install/Dependencies
------------------------------

Use pip:

.. code-block:: bash

    pip3 install git+https://github.com/mcyph/shmrpc/shmrpc.git

Or install manually:

.. code-block:: bash

    git clone https://github.com/mcyph/shmrpc
    cd shmrpc
    python setup.py build_ext --inplace
    python setup.py install

This module has only been tested on Linux (specifically Ubuntu 18.04 LTS),
but should work on other Linuxes, and potentially some other POSIX-compliant
systems. It may never work on Windows except for via the `Windows
Subsystem for Linux`_ due to its reliance on POSIX named semaphores and shared
memory.

It has the following dependencies:

* msgpack - for faster IPC serialisation with JSON-supported types
* flask - for the monitoring/management web interface
* posix_ipc - for shared memory support
* python-snappy - for fast compression in combination with remote TCP sockets
* psutil - for monitoring child worker processes

Example
-----------------------

echoserver.py:

.. code-block:: python

    from shmrpc import ServerMethodsBase, raw_method, json_method

    class EchoServer(ServerMethodsBase):
        port = 5555
        name = 'echo_serv'

        # Note that raw_method can only send data as the "bytes" type.
        # json, msgpack, pickle, marshal etc are options in place of raw,
        # with significantly differing performance, serialisable types
        # and security: please see below.
        @raw_method
        def echo_raw(self, data):
            return data

        @json_method
        def echo_json(self, data):
            return data

echoclient.py:

.. code-block:: python

    from shmrpc import ClientMethodsBase, SHMClient
    from echoserver import EchoServer

    class EchoClient(ClientMethodsBase):
        def __init__(self, client_provider):
            ClientMethodsBase.__init__(self, client_provider)

        # echo_raw = TestServerMethods.echo_raw.as_rpc()
        # can also do the same as the below code.
        def echo_raw(self, data):
            return self.send(EchoServer.echo_raw, data)

        # Note that "data" is actually a list of arguments
        # for non-raw serialisers.
        def echo_json(self, data):
            return self.send(EchoServer.echo_json, [data])

    if __name__ == '__main__':
        # client can be replaced with NetworkClient(host_address)
        # to allow for remote connections. The tcp_bind ini setting
        # must be set in this case: see below.
        client = connect()
        methods = EchoClient(client)
        print("Received data:", methods.echo_raw(b"Lorem ipsum"))

service.ini:

.. code-block:: ini

    [defaults]
    #tcp_bind=127.0.0.1
    log_dir=/tmp/test_server_logs/

    [EchoServer]
    import_from=echoserver

Then type ``python3 -m shmrpc.service service.ini &``
from the same directory to start the server; and
``python3 test_client.py`` to test a connection to it.

Implementation details
------------------------

This provides RPC via custom shared memory queues, synchronised by a hybrid
spinlock_/`named semaphore`_. This potentially allows sub-millisecond latencies,
and high throughput, at a cost of some wasted CPU cycles (up to around
1 millisecond per call).

This module is useful when moving functions/in-memory data to dedicated
process(es) rather than in each webserver worker process,
which can use less RAM. This can also be useful when the
`Global Interpreter Lock (GIL)`_ is a limiting factor, as it can scale up or
down worker processes depending on CPU usage over time.

It was also intended to be a way of allowing for a
`separation of concerns`_, effectively allowing larger complex programs to be moved
into smaller "blocks" or microservices. Each shared memory client to server
"connection" allocates a shared memory block, which starts at >=2048 bytes, and expands
when requests/responses are larger than can be written. It does this in increments of
powers of 2 of the operating system's `page size`_.

Each client connection needs a single shared memory block and thread on each
worker server. The latter also has some overhead, but in my case I thought this would
be low enough for most situations I would be likely to use this.
Currently only a single connection can be made to a service for each individual process,
as shared memory is referenced by the client process' PID.

It also allows RPC to be performed via ordinary TCP sockets. It uses a specific
protocol which sends the length of data prior to sending the data
itself so as to improve buffering performance. This can be around 4-5 times slower
than shared memory, but could allow connections to remote hosts.

A unique port number and service name must be provided by servers. Although the
port can be either an integer or bytes for the shared memory server, it's
normally best to keep this as a number, to allow compatibility with
network sockets.

A management interface (by default on 127.0.0.1:5155) can allow viewing each
service's status as defined in the .ini file, and view memory, io and cpu usage over
time, as well as stdout/stderr logs.

License
-----------------------

Licensed under the MIT License.

Copyright 2020 Dave Morrissey

Permission is hereby granted, free of charge, to any person obtaining a copy of this
software and associated documentation files (the "Software"), to deal in the Software
without restriction, including without limitation the rights to use, copy, modify,
merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be included in all copies
or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

==============================
Client/Server RPC
==============================

Reference
---------------------------

* ``.ini`` file format

.. code-block:: ini

    # Flask web monitor related
    [web monitor]
    port=5155
    host=127.0.0.1

    # The values in "defaults" will be used if they aren't
    # overridden in individual methods
    [defaults]
    # The location for the time series data (memory data etc)
    # and stdout/stderr logs
    log_dir=/tmp/test_server_logs/
    # The address to bind to (if you want to also allow connection via TCP).
    # If you don't, a NetworkServer will not be created.
    tcp_bind=127.0.0.1

    # The maximum number of worker processes
    # Defaults to the number of CPU cores
    max_proc_num=X
    # The minumum number of workers. Defaults to 1
    min_proc_num=X
    # Whether to wait for the service to boot before moving on to the next
    # entry: each entry is executed in sequential order if True
    wait_until_completed=True
    # Whether to allow insecure serialisation methods like pickle/marshal
    # in combination with NetworkServer
    force_insecure_serialisation=False

    # The name of the ServerMethodsBase-derived class to import,
    # and the module from which to import the class.
    # This is basically the same as
    # from module_name import MethodsClassName
    # in python.
    [MethodsClassName]
    import_from=module_name


* ``ClientMethodsBase``: The class from which client methods must derive from.
  This might include logic that allows for creating e.g. class instances from
  basic types like lists, which can be better supported by JSON and other
  encoders.
  The ``__init__`` method takes a single parameter - ``client_provider``, which
  may be either an ``SHMClient`` or a ``NetworkClient`` instance.
* ``ServerMethodsBase``: The class from which client server methods must derive.
  Subclasses must have a unique ``port`` number, and a unique ``name`` for
  identification in logs.
* ``NetworkClient``/``SHMClient``: Instances of one of these must be provided to
  ``ClientMethodsBase``-derived classes. The ``NetworkClient`` requires a single
  parameter of ``host``.

Different kinds of encoders/decoders:

* ``@raw_method``: Define a method which sends/receives data using the python raw
  ``bytes`` type
* ``@json_method``: Define a method sends/receives data using the built-in json
  module. Tested the most, and quite interoperable: I generally use this, unless
  there's a good reason not to.
* ``@msgpack_method``: Define a method that sends/receives data using the msgpack
  module. Supports most/all the types supported by json, but typically is 2x+
  faster, at the expense of (potentially) losing interoperability.
* ``@pickle_method``: Define a method that sends/receives data using the ``pickle``
  module. **Potentially insecure** as arbitrary code could be sent, but is
  fast, and supports many python types. Supports int/tuple etc keys in dicts,
  which json/msgpack don't.
* ``@marshal_method``: Define a method that sends/receives data using the ``pickle``
  module. **Potentially insecure** as there could be potential buffer overflow
  vulnerabilities etc, but is fast.

==============================
Hybrid Spin Semaphore
==============================

To create a hybrid spin semaphore, you need to use the
HybridLock constructor:

.. code-block:: python

    HybridLock(sem_loc, mode, initial_value, permissions)

``mode`` is one of:

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
values in seconds using whole integers.

Implementation Considerations
--------------------------------

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
  server method decorators. Swagger/OpenAPI are interesting, but require
  a fair amount of boilerplate and would require maintaining
  documentation multiple times, so are not a goal of this project.

* Docker integration would be useful. I've tried to keep this in mind
  for future refactors, making it so that the management interface
  is separate to the process managers/worker processes. The latter
  two would be ideally be individual containers communicating
  with the host (or a dedicated management interface container).

* The ability to communicate with services using other languages,
  such as JavaScript, Java or Kotlin using TCP sockets. The reverse
  direction probably is a lower priority, as I only have so much time
  to maintain my existing python services.
  I suspect shared memory and named semaphore locks might be easier to do
  with something like Rust or GoLang, but would probably only attempt this
  if python is too slow/won't scale.

* Currently the HybridLock only allows locking for whole seconds, but it
  should be easy to support floating point numbers. It also would be
  nice to allow for setting the maximum "spin" time.

* Possibly improve spinlock performance.
  https://probablydance.com/2019/12/30/measuring-mutexes-spinlocks-and-how-bad-the-linux-scheduler-really-is/
  https://matklad.github.io/2020/01/04/mutexes-are-faster-than-spinlocks.html and
  https://www.realworldtech.com/forum/?threadid=189711&curpostid=189723
  may be worth referring to. Currently the spinlock is just a simple
  variable (not atomic/volatile) and it falls back to named semaphores
  whether it's acquired in time or not. The current one is relatively
  simple in implementation which in my opinion is a big advantage, and
  I'm not sure much performance would be gained, except when there are lots of
  servers for a single service (as each client has its own spinlock/
  named semaphore).

* Add transparent compression support for NetworkServer/NetworkClient,
  with the client receiving the compression type before first commands.

===========================
Bugs/Limitations
===========================

The shared spinlock implementation could probably be optimised,
and there may be bugs when clients or servers try to
reconnect through previously used "port"s.

.. _separation of concerns: https://en.wikipedia.org/wiki/Separation_of_concerns
.. _copy-on-write: https://en.wikipedia.org/wiki/Copy-on-write
.. _mmap: https://docs.python.org/3/library/mmap.html
.. _Windows Subsystem for Linux: https://en.wikipedia.org/wiki/Windows_Subsystem_for_Linux
.. _page size: https://en.wikipedia.org/wiki/Page_(computer_memory)
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
.. _named semaphore: http://man7.org/linux/man-pages/man7/sem_overview.7.html
.. _mutexes: https://en.wikipedia.org/wiki/Lock_(computer_science)
.. _spinlock: https://en.wikipedia.org/wiki/Spinlock
.. _between 0.75ms and 6ms: https://stackoverflow.com/questions/16401294/how-to-know-linux-scheduler-time-slice
.. _pre-emptive multitasking: https://en.wikipedia.org/wiki/Preemption_(computing)#Preemptive_multitasking
.. _process time slice: https://en.wikipedia.org/wiki/Preemption_(computing)#Time_slice
