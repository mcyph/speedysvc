from time import time
from network_tools.posix_shm_sockets.shared_params import Q_LEN, MSG_SIZE

recv_q = BytesQueue('serv_q', Q_LEN, MSG_SIZE)
send_q = BytesQueue('client_q', Q_LEN, MSG_SIZE)
from_time = time()

for x in range(500000):
    send_q.put(b"my vfdsfdsfsdfsdfsdfdsfsdaluetasdsadasdsadsadsaest")
    recv_q.get()

print(f"DONE in {time()-from_time} seconds")
