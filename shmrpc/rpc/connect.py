import traceback

from hybrid_lock import NoSuchSemaphoreException, SemaphoreDestroyedException
from shmrpc.compression.compression_types import snappy_compression
from shmrpc.rpc.shared_memory.SHMClient import SHMClient
from shmrpc.rpc.network.NetworkClient import NetworkClient


def connect(server_methods, address='shm://',
            compression_inst=snappy_compression):
    """
    Connect to either a shared memory or tcp server.

    :param server_methods: a class (doesn't have to be instantiated)
                           derived from ServerMethodsBase.
    :param address: either a single or multiple addresses.
                    addresses can be either "shm://" or "tcp://address:port",
                    with the ":port" optional, and dervied from server_methods
                    Keeps trying each address/protocol in sequence.
                    Only raises an exception if the last one fails.
                    Otherwise just prints the traceback to stderr.
    :param compression_inst: an instance of one of NullCompression,
                             SnappyCompression or ZLibCompression.
                             SHMClient doesn't use compression, it's
                             only relevant for NetworkClient (tcp).
    :return: either an SHMClient or NetworkClient
    """
    port = server_methods.port
    name = server_methods.name

    if not isinstance(address, (list, tuple)):
        addresses = (address,)
    else:
        addresses = address

    for x, address in enumerate(addresses):
        last_address = x == len(addresses)-1

        try:
            # Currently, only local shared memory and tcp is supported, but I'm using a
            # protocol scheme to allow for later adding other protocols. udp and
            # ssh-tunnelled tcp are protocols I'd like to add, because of latency and
            # security respectively.

            if address.startswith('shm://'):
                # TODO: Allow for prefixes to SHM so that
                #  e.g. multiple copies of services can be run at once!
                return SHMClient(server_methods)

            elif address.startswith('tcp://'):
                ip = address.partition('//')[-1]
                if ':' in ip:
                    # Assume a service is on a different port if there's a colon.
                    # This code should hopefully be forwards-compatible with ipv6
                    # format, but don't have a ipv6-enabled network to test on
                    # currently
                    ip, _, port = ip.rpartition(':')
                    ip = ip.strip('[]')
                    port = int(port)

                return NetworkClient(server_methods,
                                     host=ip, port=port,
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
