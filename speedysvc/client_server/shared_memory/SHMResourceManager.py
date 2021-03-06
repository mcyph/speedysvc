import sys
import json
import time
import psutil
import _thread
from psutil import pid_exists

from speedysvc.hybrid_lock import HybridLock, CONNECT_TO_EXISTING, CREATE_NEW_OVERWRITE, \
    NoSuchSemaphoreException, SemaphoreExistsException
from speedysvc.kill_pid_and_children import kill_pid_and_children
from speedysvc.is_pid_still_alive import is_pid_still_alive
from speedysvc.ipc.JSONMMapBase import JSONMMapBase
# TODO: Move get_mmap somewhere more appropriate!
from speedysvc.client_server.shared_memory.shared_params import get_mmap, unlink_shared_memory
from speedysvc.client_server.shared_memory.shared_params import INVALID, SERVER, CLIENT


def debug(*s):
    if False:
        print(*s)


def lock_fn(old_fn):
    """
    Decorator for a function which needs a lock
    for shared encode/decode operations
    """
    def new_fn(self, *args, **kw):
        self.lock.lock(spin=0)
        self.lock_acquired = True
        try:
            r = old_fn(self, *args, **kw)
        finally:
            try:
                self.lock.unlock()
            except:
                pass
            self.lock_acquired = False
        return r

    return new_fn


def lock_fn_timeout(old_fn):
    """
    Decorator for a function which needs a lock
    for shared encode/decode operations
    """
    def new_fn(self, *args, **kw):
        self.lock.lock(spin=0, timeout=5)
        self.lock_acquired = True
        try:
            r = old_fn(self, *args, **kw)
        finally:
            try:
                self.lock.unlock()
            except:
                pass
            self.lock_acquired = False
        return r

    return new_fn


_DResourceManagers = {}


def SHMResourceManager(port, name, monitor_pids=False):
    if not (port, name) in _DResourceManagers:
        _DResourceManagers[port, name] = _SHMResourceManager(port, name, monitor_pids)
    return _DResourceManagers[port, name]


class _SHMResourceManager(JSONMMapBase):
    MMAP_TEMPLATE = 'service_%(port)s_%(pid)s_%(qid)s'
    LOCK_TEMPLATE = 'lock_%(port)s_pid_%(pid)s_%(qid)s'

    def __init__(self, port, name, monitor_pids=False):
        """
        A manager to keep track of creation, deletion, modifying
        shared HybridLock's and mmaps for a single service.

        :param port: port number of the service
        :param name: unique name of the service
        :param monitor_pids: whether to monitor the PIDs in a loop.
                             Many times it might be better to simply
                             poll check_for_missing_pids rather than using
                             this, which creates a new thread
        """
        self.port = port
        self.name = name

        # TODO: Specify the actual mmap location of the JSON Map!!
        try:
            JSONMMapBase.__init__(self, port, create=False)
            debug(f"SHMResourceManager for {name}:{port}: connected")
        except NoSuchSemaphoreException:
            JSONMMapBase.__init__(self, port, create=True)
            debug(f"SHMResourceManager for {name}:{port}: created")

        pid_holding_lock = self.lock.get_pid_holding_lock()
        if (pid_holding_lock and not is_pid_still_alive(pid_holding_lock)) or not pid_holding_lock:
            # If the process which is holding the
            # lock no longer exists, force unlock
            try:
                debug(f"SHMResourceManager for {name}: "
                      f"PID {pid_holding_lock} no longer exists - unlocking!")
                self.lock.unlock()
            except:
                pass

        self.__init_value()

        if monitor_pids:
            _thread.start_new_thread(self.__monitor_pids_loop, ())

        _DResourceManagers[port, name] = self

    @lock_fn_timeout
    def __init_value(self):
        try:
            if not self._decode():
                self._encode([[], []])
        except json.decoder.JSONDecodeError:
            self._encode([[], []])

    #===============================================================#
    #                         Monitor PIDs                          #
    #===============================================================#

    def __monitor_pids_loop(self):
        while True:
            try:
                self.check_for_missing_pids()
            except:
                import traceback
                traceback.print_exc()
            time.sleep(5)

    @lock_fn
    def check_for_missing_pids(self):
        """
        Check for PIDs of clients and servers which don't
        exist any more, and clean up their resources!
        """
        LServerPIDs, LClientPIDs = self._decode()

        n_LServerPIDs = []
        for pid in LServerPIDs:
            if is_pid_still_alive(pid):
                n_LServerPIDs.append(pid)
            else:
                # Won't do anything if doesn't exist - we'll leave the
                # resources there so that potential new server PIDs
                # can take over from the old one
                pass

        n_LClientPIDs = []
        for pid, qid in LClientPIDs:
            if is_pid_still_alive(pid):
                n_LClientPIDs.append((pid, qid))
            else:
                self.unlink_resources(pid, qid)

        self._encode([n_LServerPIDs, n_LClientPIDs])

    #===============================================================#
    #           Create/Open/Destroy Client Locks+MMaps              #
    #===============================================================#

    def create_resources(self, pid, qid):
        """
        Create new client resources for a given pid/qid
        and adds the PID/QID to the service info,
        so as to inform servers to respond to requests
        :return: (the shared mmap, client HybridLock, server HybridLock)
        """
        mmap = self.create_pid_mmap(min_size=1024, pid=pid, qid=qid)
        lock = self.get_lock(pid, qid, CREATE_NEW_OVERWRITE)

        # Inform servers
        self.add_client_pid_qid(pid, qid)
        return mmap, lock

    def open_existing_resources(self, pid, qid):
        """
        Create existing client resources for a given pid/qid
        :return: (the shared mmap, client HybridLock, server HybridLock)
        """
        mmap = self.connect_to_pid_mmap(pid, qid)
        lock = self.get_lock(pid, qid, CONNECT_TO_EXISTING)
        return mmap, lock

    def get_lock(self, pid, qid, mode):
        """
        Get the locks for a client connection to the servers
        :return: HybridLock
        """
        client_loc = self.LOCK_TEMPLATE % dict(port=self.port, pid=pid, qid=qid)
        client_lock = HybridLock(client_loc.encode('ascii'), mode=mode, initial_value=1)
        return client_lock

    def unlink_resources(self, pid, qid):
        """
        Remove the locks and memory map associated with the process ID/in-process ID

        (i.e. the in-process "qid" allows a process to have multiple clients sending
         commands to multiple server workers at once)
        """
        try:
            client_loc = self.LOCK_TEMPLATE % dict(port=self.port, pid=pid, qid=qid)
            client_lock = HybridLock(client_loc.encode('utf-8'), CONNECT_TO_EXISTING)
            client_lock.destroy()
        except NoSuchSemaphoreException:
            pass

        mmap_loc = self.MMAP_TEMPLATE % dict(port=self.port, pid=pid, qid=qid)
        try:
            unlink_shared_memory(mmap_loc)
        except FileNotFoundError:
            pass

    #===============================================================#
    #             Create/Connect to Shared Memory Map               #
    #===============================================================#

    def create_pid_mmap(self, min_size, pid, qid):
        """
        Create/overwrite a memory map for a given client connection.
        Often is called more than once with a larger min_size, if the
        memory map isn't large enough to send the required data.

        :param min_size: minimum size of the mmap in bytes. If less than
                         the OS's page size, then it will be made a
                         multiple of it.
        :param pid: the process ID
        :param qid: the in-process ID
        :return: a mmap object
        """

        # get_mmap makes it so that the size is always within a power of 2
        # so as to prevent needing to keep reallocating
        # (hopefully an ok balance between too little and too much)
        #
        # The alternatives like just raising an error, or having multipart
        # mode seemed too limiting and too complicated/high overhead
        # for it to be worthwhile.
        socket_name = self.MMAP_TEMPLATE % dict(port=self.port, pid=pid, qid=qid)
        mmap = get_mmap(socket_name.encode('utf-8'), create=True, new_size=min_size)
        mmap[0] = CLIENT
        return mmap

    def connect_to_pid_mmap(self, pid, qid):
        """
        Connect to an existing shared mmap
        Same as above, but don't use in "create" mode as we're
        connecting to a semaphore/shared memory that
        (should've been) already created.
        """
        socket_name = self.MMAP_TEMPLATE % dict(port=self.port, pid=pid, qid=qid)
        return get_mmap(socket_name.encode('utf-8'), create=False)

    #===============================================================#
    #                     Server PID management                     #
    #===============================================================#

    @lock_fn
    def get_server_pids(self):
        LServerPIDs, LClientPIDs = self._decode()
        return LServerPIDs

    @lock_fn
    def add_server_pid(self, pid):
        """
        Add to a list of PIDs which are associated with this service
        to allow clients checking they still exist
        """
        LServerPIDs, LClientPIDs = self._decode()
        if not pid in LServerPIDs:
            LServerPIDs.append(pid)
        self._encode([LServerPIDs, LClientPIDs])

    @lock_fn
    def del_server_pid(self, pid):
        """
        Remove from the list of PIDs which provide this service.
        This can help clients to figure out when to give up
        """
        LServerPIDs, LClientPIDs = self._decode()
        while pid in LServerPIDs:
            LServerPIDs.remove(pid)
        self._encode([LServerPIDs, LClientPIDs])

    @lock_fn
    def server_pid_active(self, pid):
        """
        A means for servers to check whether they should
        shut down as a result of a new MultiProcessManager taking
        over. This might happen as a result of MultiProcessManager
        not shutting down cleanly.
        """
        LServerPIDs, LClientPIDs = self._decode()
        return pid in LServerPIDs

    @lock_fn
    def reset_all_server_pids(self, kill=True):
        """
        Remove all of the PIDs of the servers

        Note that while the clients still exist, their locks/shm
        resources will still be there, so as to allow restarting
        servers and continuing from where they left off
        """
        LServerPIDs, LClientPIDs = self._decode()

        if kill:
            num_to_kill = [len(LServerPIDs)]

            def _kill(pid):
                num_to_kill[0] -= 1
                try:
                    kill_pid_and_children(pid)
                except psutil.NoSuchProcess:
                    # doesn't exist any more -
                    # no need to do anything!
                    pass

            for pid in LServerPIDs:
                _thread.start_new_thread(_kill, (pid,))

            while num_to_kill[0] != 0:
                time.sleep(0.01)

        self._encode([[], LClientPIDs])

    #===============================================================#
    #                     Client PID management                     #
    #===============================================================#

    @lock_fn
    def get_created_exited_client_pids(self, SPIDs):
        """
        :param SPIDs: a set of {(pid, qid), ...}
        :return: (created pids/qids, exited pids/qids) as two sets
        """
        LServerPIDs, LClientPIDs = self._decode()
        SClientPIDs = set(tuple(i) for i in LClientPIDs if is_pid_still_alive(i[0]))
        return SClientPIDs-SPIDs, SPIDs-SClientPIDs

    @lock_fn
    def get_client_pids(self):
        LServerPIDs, LClientPIDs = self._decode()
        return LClientPIDs

    @lock_fn
    def add_client_pid_qid(self, pid, qid):
        """
        Add to a list of PIDs which are using a service. Servers
        can then respond and create new threads as needed
        """
        LServerPIDs, LClientPIDs = self._decode()
        if not [pid, qid] in LClientPIDs:
            LClientPIDs.append([pid, qid])
        self._encode([LServerPIDs, LClientPIDs])

    @lock_fn
    def del_client_pid_qid(self, pid, qid):
        """
        Remove one of the connections from a client to the servers
        """
        LServerPIDs, LClientPIDs = self._decode()
        while [pid, qid] in LClientPIDs:
            LClientPIDs.remove([pid, qid])
        self.unlink_resources(pid, qid)
        self._encode([LServerPIDs, LClientPIDs])

    @lock_fn
    def reset_all_client_pids(self):
        """
        Remove all of the PIDs of the clients
        """
        LServerPIDs, LClientPIDs = self._decode()
        for pid, qid in LClientPIDs:
            self.unlink_resources(pid, qid)
        self._encode([LServerPIDs, []])
