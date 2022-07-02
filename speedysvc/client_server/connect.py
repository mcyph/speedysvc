import traceback
from typing import Union, List, Tuple

from speedysvc.client_server.shared_memory.SHMClient import SHMClient
from speedysvc.compression.compression_types import snappy_compression
from speedysvc.client_server.network.NetworkClient import NetworkClient
from speedysvc.hybrid_lock import NoSuchSemaphoreException, SemaphoreDestroyedException


def connect(address: Union[List, Tuple, str],
            use_spinlock=True,
            use_in_process_lock=True,
            compression_inst=snappy_compression):
    """
    Connect to either a shared memory or tcp server.

    :param address:
        either a single or multiple addresses. addresses can be either "shm://(service name)" or "tcp://address:port",
        with the ":port" optional, and dervied from server_methods. Keeps trying each address/protocol in sequence.
        Only raises an exception if the last one fails, therwise just prints the traceback to stderr.
    :param compression_inst:
        an instance of one of NullCompression, SnappyCompression or ZLibCompression. SHMClient doesn't use
        compression, it's only relevant for NetworkClient (tcp).
    :param use_spinlock:
    :param use_in_process_lock:
    :return: either an SHMClient or NetworkClient
    """

    if not isinstance(address, (list, tuple)):
        addresses = (address,)
    else:
        addresses = address

    for x, address in enumerate(addresses):
        last_address = x == (len(addresses) - 1)

        try:
            # Currently, only local shared memory and tcp is supported, but I'm using a
            # protocol scheme to allow for later adding other protocols. udp and
            # ssh-tunnelled tcp are protocols I'd like to add, because of latency and
            # security respectively.

            if address.startswith('shm://'):
                # TODO: Allow for prefixes to SHM so that
                #  e.g. multiple copies of services can be run at once!
                service_name = address.partition('//')[-1]
                return SHMClient(service_name=service_name,
                                 use_spinlock=use_spinlock,
                                 use_in_process_lock=use_in_process_lock)

            elif address.startswith('tcp://'):
                ip = address.partition('//')[-1]

                # A service needs a port along with an ip/hostname.
                # This code should hopefully be forwards-compatible with ipv6
                # format, but don't have an ipv6-enabled network to test on
                # currently
                ip, _, port = ip.rpartition(':')
                ip = ip.strip('[]')
                port = int(port)

                return NetworkClient(port=port,
                                     host=ip,
                                     compression_inst=compression_inst)
            else:
                raise Exception("Unknown protocol scheme: %s" % address)

        except OSError:
            # An error connecting to socket
            if last_address: raise
            traceback.print_exc()
        except NoSuchSemaphoreException:
            # SHM doesn't exist (hasn't been created)
            if last_address: raise
            traceback.print_exc()
        except SemaphoreDestroyedException:
            # SHM no longer exists
            if last_address: raise
            traceback.print_exc()
