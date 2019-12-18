from time import time
from network_tools.rpc.shared_memory.shm_socket.SHMSocket import SHMSocketBase

recv_q = SHMSocketBase('serv_q', clean_up=False)
send_q = SHMSocketBase('client_q', clean_up=False)
from_time = time()

for x in range(500000):
    send_q.put(b"my vfdsfdsfsdfsdfsdfdsfsdaluetasdsadasdsadsadsaest")
    recv_q.get()

print(f"DONE in {time()-from_time} seconds")
