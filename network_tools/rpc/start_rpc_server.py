from time import sleep
import multiprocessing


def start_rpc_server(
    server_factory,
    worker_processes=1,

    start_network_server=False,
    network_bind_on_ip='0.0.0.0',

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

    assert worker_processes >= 1
    if worker_processes > 1:
        assert worker_processes

        for x in range(worker_processes-1):
            multiprocessing.Process(
                target=start_rpc_server,
                kwargs=dict(
                    server_factory=server_factory,
                    worker_processes=1,

                    start_network_server=False,
                    network_bind_on_ip=network_bind_on_ip,

                    blocking=True
                )
            )

    server = server_factory()
    shm = SHMServer(server=server)

    if start_network_server:
        rest = NetworkServer(
            server=server,
            network_bind_on_ip=network_bind_on_ip
        )

    if blocking:
        while 1:
            sleep(10)
