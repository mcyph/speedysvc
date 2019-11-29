from time import sleep
import multiprocessing


def start_rpc_server(
    server_factory,

    serve_using_shared_memory=False,
    shared_memory_processes=1,

    serve_using_rest=False,
    rest_bind_on_ip=None,

    blocking=True
):
    """

    :param server_factory:
    :param serve_using_shared_memory:
    :param serve_using_rest:
    :param blocking:
    :param number_processes:
    :return:
    """

    assert shared_memory_processes >= 1
    if shared_memory_processes > 1:
        assert shared_memory_processes

        for x in range(shared_memory_processes-1):
            multiprocessing.Process(
                target=start_rpc_server,
                kwargs=dict(
                    server_factory=server_factory,

                    serve_using_shared_memory=serve_using_shared_memory,
                    shared_memory_processes=1,

                    serve_using_rest=False,
                    rest_bind_on_ip=rest_bind_on_ip,

                    blocking=True
                )
            )

    server = server_factory()

    if serve_using_shared_memory:
        shm = SHMServer(server=server)

    if serve_using_rest:
        rest = NetworkServer(server=server)

    if blocking:
        while 1:
            sleep(10)
