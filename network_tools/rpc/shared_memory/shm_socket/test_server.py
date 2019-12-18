from network_tools.rpc.shared_memory.shm_socket.SHMSocket import SHMSocketBase

recv_q = SHMSocketBase('client_q', clean_up=True)
send_q = SHMSocketBase('serv_q', clean_up=True)

while 1:
    send_q.put(recv_q.get())
