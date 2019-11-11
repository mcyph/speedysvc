from cinda.ipc.shm import free
from network_tools.MessagePackQueue import MessagePackQueue, Q_LEN, MSG_SIZE, MODE_RECV, MODE_SEND


free('client_q')
free('serv_q')

recv_q = MessagePackQueue('client_q', Q_LEN, MSG_SIZE)
send_q = MessagePackQueue('serv_q', Q_LEN, MSG_SIZE)

while 1:
    send_q.put(recv_q.get())
