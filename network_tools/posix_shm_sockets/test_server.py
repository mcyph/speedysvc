from network_tools.posix_shm_sockets.SHMSocket import SHMSocket

recv_q = SHMSocket('client_q', clean_up=True)
send_q = SHMSocket('serv_q', clean_up=True)

while 1:
    send_q.put(recv_q.get())
