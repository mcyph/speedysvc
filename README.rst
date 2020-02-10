===========================
About
===========================

    NOTE: ``speedysvc``'s status is still alpha - I'm using it in my project 
    https://langlynx.com, but is still under active development. There are 
    likely bugs and there will be breaking changes to the API.

This module for python 3.6+ on Linux allows separating larger, more complex 
applications into smaller components (microservices). For example, you could 
build a text-to-speech service, a fulltext search service,
an optical character recognition service, etc. Then, you could 
have web frontends or other clients communicate with these services. 
This can often require less RAM, as there is no need to load the components 
in every web worker process.

Unlike other similar modules for client-server communication
(which typically use sockets or HTTP REST), this module uses local `shared
memory`_, which typically performs around 5-20 times faster with much lower latency.
``speedysvc`` servers can also be remotely communicated with over the network 
using TCP sockets. The TCP protocol is fast and efficient, and optionally compresses 
traffic using snappy_/zlib to minimise bandwidth.

In order to work around limitations of python's `Global Interpreter Lock`_ 
which normally restricts applications from using more than a single CPU core,
services can have multiple worker processes. They optionally can increase 
or decrease worker processes as needed, depending on CPU usage. This helps
to make sure server resources are more effectively used. While this is possible
with the ``multiprocessing`` module, ``multiprocessing`` on Linux uses ``pipe2`` for 
communication between processes which is much slower than using shared memory.

There is a service management web interface that shows logs/performance data for each
service and allows stopping/starting services individually.
Each service is started separately in individual processes with individual 
logs so as to be able to track down events and errors without being overwhelmed 
with too much information.

  .. image:: docs/web_index_screenshot.png

See also `Implementation Considerations`_.


Requirements
-------------------

* OS: Linux (tested on Ubuntu 18.04 LTS, other POSIX systems may also be supported)
* Python: 3.6 or above
* Module Dependencies: cython, msgpack, posix_ipc, python-snappy, flask, psutil

Install
-------------------

.. code-block:: bash

    pip3 install git+https://github.com/mcyph/speedysvc/speedysvc.git

See also `Install/Dependencies`_.

Quick Example
-------------------

echoserver.py:

.. code-block:: python

    from speedysvc import ServerMethodsBase, json_method

    class EchoServer(ServerMethodsBase):
        port = 5555
        name = 'echo_serv'

        @json_method
        def echo_json(self, data):
            return data

echoclient.py:

.. code-block:: python

    from speedysvc import ClientMethodsBase, connect
    from echoserver import EchoServer

    class EchoClient(ClientMethodsBase):
        def echo_json(self, data):
            return self.send(EchoServer.echo_json, [data])

    if __name__ == '__main__':
        # Note: Replace 'shm://' with 'tcp://(host)' for remote services
        methods = EchoClient(connect(EchoServer, 'shm://'))
        print(methods.echo_json("Hello World!"))

service.ini:

.. code-block:: python

    [defaults]
    # Uncomment this line to listen on the network
    #bind_tcp=(host adaptor)
    log_dir=/tmp/test_server_logs/

    [EchoServer]
    import_from=echoserver
    max_proc_num=3
    min_proc_num=3

Then type ``python3 -m speedysvc.service service.ini &`` from the same directory
to start the server. The web management interface will start on
http://127.0.0.1:5155, where you can monitor the status and logs of the server.

Then, type ``python3 echoclient.py`` to test a connection to the server.

See `Example`_ for a a more complex example.

See Also
--------

* `Client/Server API Reference`_
* `Hybrid Spin Semaphore`_
* `TODO`_

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

.. _Detailed feature list: https://github.com/mcyph/speedysvc/wiki/Detailed-Feature-List
.. _Install/Dependencies: https://github.com/mcyph/speedysvc/wiki/Install-and-Dependencies
.. _Example: https://github.com/mcyph/speedysvc/wiki/Example-Client-Server
.. _Client/Server API Reference: https://github.com/mcyph/speedysvc/wiki/Client-Server-Service-Reference
.. _Hybrid Spin Semaphore: https://github.com/mcyph/speedysvc/wiki/Hybrid-Spin-Semaphore-API
.. _Implementation Considerations: https://github.com/mcyph/speedysvc/wiki/Technical-Implementation-Details
.. _TODO: https://github.com/mcyph/speedysvc/wiki/TODO
.. _Global Interpreter Lock: https://wiki.python.org/moin/GlobalInterpreterLock
.. _snappy: https://github.com/google/snappy
.. _shared memory: https://developer.ibm.com/articles/au-spunix_sharedmemory/
