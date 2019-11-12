from network_tools.posix_shm_sockets.shared_params import Q_LEN
from network_tools.posix_shm_sockets.SHMSocket import SHMSocket

recv_q = SHMSocket('client_q', clean_up=True)
send_q = SHMSocket('serv_q', clean_up=True)
#recv_q = send_q

while 1:
    send_q.put(recv_q.get())
