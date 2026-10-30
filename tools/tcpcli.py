import socket,time,sys
H=sys.argv[1]; buf=bytearray(256*1024)
def run(mode):
    c=socket.create_connection((H,5201)); c.sendall(mode); n=0; t=time.time()
    if mode==b"S":
        mv=memoryview(buf)
        while True:
            k=c.recv_into(mv)
            if not k: break
            n+=k
    else:
        end=t+10
        while time.time()<end: c.sendall(buf); n+=len(buf)
        c.shutdown(socket.SHUT_WR); c.recv(1)
    dt=time.time()-t; c.close(); return n*8/dt/1e6
print("board -> PC (board TX): %.1f Mbit/s"%run(b"S")); time.sleep(1)
print("PC -> board (board RX): %.1f Mbit/s"%run(b"R"))
