import socket,time
s=socket.socket(); s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1); s.bind(("0.0.0.0",5201)); s.listen(1)
buf=bytearray(256*1024)
for _ in range(2):
    c,_=s.accept(); m=c.recv(1)
    if m==b"S":
        end=time.time()+10
        while time.time()<end: c.sendall(buf)
    else:
        mv=memoryview(buf)
        while c.recv_into(mv): pass
    c.close()
