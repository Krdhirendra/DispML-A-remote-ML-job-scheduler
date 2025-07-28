import socket
import sys
import struct
import os
import subprocess
from worker_1 import Trainer


HOST = "127.0.0.1"
PORT = 5050

# run get_info file to check the available GPUs
def file_op(file_name,client_s:socket.socket):
    result = subprocess.run(
        [sys.executable, file_name],
        capture_output= True,
        text = True
    )
    output = result.stdout
    out_bytes = output.encode()
    client_s.sendall(struct.pack('>I',len(out_bytes)))
    client_s.sendall(out_bytes)


#receive the get_info file 
def receive_file(client_s:socket.socket):
    #receive name
    filename = b''
    while not filename.endswith(b'\n'):
        chunk = client_s.recv(1)
        if not chunk:
            return None
        filename += chunk
    filename = filename[:-1].decode()
    # receive size
    filesize = struct.unpack('>Q',client_s.recv(8))[0]

    #receive file
    with open(filename,'wb') as f:
        remaining_size = filesize
        while remaining_size:
            chunk = client_s.recv(min(remaining_size,1024))
            if not chunk:
                 break
            f.write(chunk)
            remaining_size -= len(chunk)

    return filename



#start the worker socket
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))
    print('\n[+] connected to server\n')

    while True:
        fname = receive_file(s)
        if fname is None:
            print('[*] Server closed the connection, exiting>>>>>>>')
            break

        file_op(file_name=fname,client_s=s)

        try:
            #
            trainer = Trainer(client=s)
            trainer.receive_n_unzip()#Receive the project dir and unzip that
            trainer.train_n_send()#train the model and sendback
        except (ConnectionResetError, BrokenPipeError):
            print("[!] Lost connection during training, exiting.")
            break