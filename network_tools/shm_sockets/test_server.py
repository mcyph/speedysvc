from cinda.ipc.shm import free
from network_tools.shm_sockets.shared_params import Q_LEN, MSG_SIZE
from cinda.ipc.queue import BytesQueue

free('client_q')
free('serv_q')

recv_q = BytesQueue('client_q', Q_LEN, MSG_SIZE)
send_q = BytesQueue('serv_q', Q_LEN, MSG_SIZE)
#recv_q = send_q

while 1:
    send_q.put(recv_q.get())
