===========================
About
===========================

This module provides extremely low-latency, high-throughput
inter-process queues.

It provides this via custom shared memory queues,
synchronised by a hybrid spinlock/named semaphore.
This potentially allows sub-millisecond latencies, and extremely
high throughput, at a cost of some wasted CPU cycles
(up to around 1 millisecond per call).

==============================
Memory Mapped Sockets
==============================

TODO!

====================================
POSIX Memory Mapped Sockets
====================================

CONNECT_OR_CREATE

CONNECT_TO_EXISTING

CREATE_NEW_OVERWRITE

CREATE_NEW_EXCLUSIVE

==============================
Hybrid Spin Semaphore
==============================

TODO!

Why not use...? Or Why?
-----------------------

It's a common situation in the c implementation of python
where one is limited by the `Global Interpreter Lock (GIL)`_,
and you can't use more than a single CPU core at once for a
single process.

There are a few solutions to this:

* Have a single process, and just live with only using a
  single core. (Or write modules in c/cython which
  bypass the GIL).

* Have multiple processes. Load modules with relevant
  in-memory data in every process.
  This can make good use of CPU, but use huge amounts
  of memory if you have more than a few worker processes
  (in my case many gigabytes). This can get quite expensive on
  cloud servers where RAM is at a premium, and limit options.

* Use the `multiprocessing module`_. However, this is mainly
  useful for communication between the parent process and child
  processes managed by the multiprocessing module. It also
  uses pipe2_ for communication, and so it can be slower
  than shared memory, as described below.

* Still have multiple processes, but move modules into external
  processes or "microservices", and use inter-process
  communication, or IPC to reduce wastage of RAM and
  other resources.

There are a number of different kinds of IPC on Linux/Unix:

* Using methods which use kernel-level synchronisation, such as
  sockets (`Unix(tm) domain sockets`_, or `TCP sockets`_),
  `message queues`_, or `pipe/pipe2`_.
  This can have a high latency, and was
  limited to 10-20,000 requests a second in my benchmarks.

* Using shared memory, which requires process-level
  synchronisation to be performed manually by processes.
  Synchronisation can be performed by spinlocks_,
  `named semaphores`_ or mutexes_.
  This is the approach used by this module.

A spinlock_ as the title suggests "spins", or keeps looping
asking "are you done yet?" until the task is complete. In a
single-processor system, this will slow things down, but in a
multi-processor system that uses `pre-emptive multitasking`_
this can be faster, if the task can be completed in less than the
`process time slice`_, which often is `between 0.75ms and 6ms`_
on Linux.

By contrast, using mutexes, or using binary
named semaphores can prevent wasting CPU cycles, but this can
run the risk of blocking a process while waiting for a task
that takes a fraction of a millisecond. This can increase
latency by orders of magnitude for non-cpu/io-bound calls.

Currently, this module is hardcoded to spin for up
to 1ms before leaving it up to named semaphores to block.

===========================
TODO
===========================

It would be nice to be able to transparently call methods using
REST, so as to allow services to use the same code.

===========================
Bugs/Limitations
===========================

The shared spinlock implementation could probably be optimised,
and there may be bugs when clients or servers try to
reconnect through previously used "port"s.

Please report any such bugs to [[FIXME...]]


.. _Global Interpreter Lock (GIL): https://en.wikipedia.org/wiki/Global_interpreter_lock
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
