from os import getpid
from hybrid_lock import CREATE_NEW_OVERWRITE
from network_tools.serialisation.RawSerialisation import RawSerialisation
from network_tools.rpc.shared_memory.SHMBase import SHMBase
from network_tools.rpc.shared_memory.shared_params import \
    PENDING, INVALID, SERVER, CLIENT
from network_tools.rpc.shared_memory.JSONMMapArray import JSONMMapArray
from network_tools.rpc.base_classes.ClientProviderBase import ClientProviderBase


class SHMClient(ClientProviderBase, SHMBase):
    def __init__(self, server_methods, port=None):
        # Create the shared mmap space/client+server semaphores.

        # Connect to a shared shm/semaphore which stores the
        # current processes which are associated with this service,
        # and add this process' PID.
        ClientProviderBase.__init__(self, server_methods, port)

        self.mmap = self.create_pid_mmap(
            2048, self.port, getpid()
        )
        self.client_lock, self.server_lock = self.get_pid_semaphores(
            self.port, getpid(), CREATE_NEW_OVERWRITE
        )

        # Make myself known to the server (my PID)
        #
        # TODO: Figure out what to do in the case
        #  of the PID already being in the array!
        # In that case, we will be overwriting the resources
        # previously allocated by SHMClient, and so either
        # we won't be able to connect properly, or will make
        # the previous resources invalid

        self.pids_array = pids_array = JSONMMapArray(
            self.port, create=False
        )
        with pids_array:
            pids_array.append(getpid())

    def get_server_methods(self):
        return self.server_methods

    def send(self, cmd, args, timeout=-1):
        if isinstance(cmd, bytes):
            # cmd -> a bytes object, most likely heartbeat or shutdown
            serialiser = RawSerialisation
        else:
            # cmd -> a function in the ServerMethods subclass
            serialiser = cmd.serialiser
            cmd = cmd.__name__.encode('ascii')

        # Encode the request command/arguments
        # (I've put the encoding/decoding outside the critical area,
        #  so as to potentially allow for more remote commands from
        #  different threads)
        args = serialiser.dumps(args)
        encoded_request = self.request_serialiser.pack(
            len(cmd), len(args)
        ) + cmd + args

        self.client_lock.lock(timeout=timeout)
        try:
            # Next line must be in critical area!
            mmap = self.mmap

            # Send the result to the server!
            if len(encoded_request) >= (len(mmap)-1):
                print(f"Client: Recreating memory map to be at "
                      f"least {len(encoded_request) + 1} bytes")
                old_mmap = mmap
                mmap = self.create_pid_mmap(
                    len(encoded_request) + 1, self.port, getpid()
                )
                mmap[0] = old_mmap[0]
                self.mmap = mmap
                old_mmap[0] = INVALID
                print(f"Client: New mmap size is {len(mmap)} bytes "
                      f"for encoded_request length {len(encoded_request)}")

            assert len(mmap) > len(encoded_request), \
                (len(mmap), len(encoded_request))
            mmap[1:1+len(encoded_request)] = encoded_request

            # Wait for the server to begin processing
            mmap[0] = PENDING
            #print("BEFORE SERVER UNLOCK:",
            #      self.server_lock.get_value(),
            #      self.client_lock.get_value())
            self.server_lock.unlock()

            while mmap[0] == PENDING:
                # TODO: Give up and try to reconnect if this goes on
                #  for too long - in that case, chances are something's
                #  gone wrong on the server end

                # Spin! - should check to make sure this isn't being called too often
                pass

            self.server_lock.lock(timeout=-1)  # CHECK ME!!!!
            try:
                # Make sure response state ok,
                # reconnecting to mmap if resized
                while True: # WARNING
                    if mmap[0] == CLIENT:
                        break  # OK

                    elif mmap[0] == INVALID:
                        print(f"Client: memory map has been marked as invalid")
                        prev_len = len(mmap)
                        mmap = self.mmap = self.connect_to_pid_mmap(self.port, getpid())

                        # Make sure it actually is larger than the previous one,
                        # so as to reduce the risk of an infinite loop
                        assert len(mmap) > prev_len, \
                            "New memory map should be larger than the previous one!"

                    elif mmap[0] == SERVER:
                        raise Exception("Should never get here!")
                    else:
                        raise Exception("Unknown state: %s" % mmap[0])

                # Decode the result!
                response_status, data_size = self.response_serialiser.unpack(
                    mmap[1:1+self.response_serialiser.size]
                )
                response_data = mmap[
                    1+self.response_serialiser.size:
                    1+self.response_serialiser.size+data_size
                ]
            finally:
                pass
        finally:
            self.client_lock.unlock()

        if response_status == b'+':
            return serialiser.loads(response_data)
        elif response_status == b'-':
            raise Exception(response_data)
        else:
            raise Exception("Unknown status response %s" % response_status)
