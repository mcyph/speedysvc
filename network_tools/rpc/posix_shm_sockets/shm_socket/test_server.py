from network_tools.rpc.posix_shm_sockets.shm_socket.SHMSocket import SHMSocket

recv_q = SHMSocket('client_q', clean_up=True)
send_q = SHMSocket('serv_q', clean_up=True)

while 1:
    send_q.put(recv_q.get())
