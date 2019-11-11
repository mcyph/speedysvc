from time import time
from network_tools.MessagePackQueue import MessagePackQueue, Q_LEN, MSG_SIZE, MODE_RECV, MODE_SEND

recv_q = MessagePackQueue('serv_q', Q_LEN, MSG_SIZE)
send_q = MessagePackQueue('client_q', Q_LEN, MSG_SIZE)
from_time = time()

for x in range(500000):
    send_q.put({"my vfdsfdsfsdfsdfsdfdsfsdalue": "tasdsadasdsadsadsaest"})
    recv_q.get()

print(f"DONE in {time()-from_time} seconds")
