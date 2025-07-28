import socket 
import struct
import zipfile
import os
from pathlib import Path


#class
class Sender:
    def __init__(self, client:socket.socket,dir_path):
        # self.server = server
        self.client = client
        self.BUFFER_SIZE = 1024
        self.DIR_TO_SEND = dir_path
        self.ZIP_NAME = f"{Path(dir_path).name}.zip" 

    # method to zip and send the project dir to worker
    def zip_and_send(self):
        # 
        zip_path = os.path.join(self.DIR_TO_SEND, self.ZIP_NAME)
        if os.path.exists(zip_path):  # cleanup old zip
            os.remove(zip_path)

        # 1: Zip the directory which will be sent
        zip_path = os.path.join(self.DIR_TO_SEND, self.ZIP_NAME)
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(self.DIR_TO_SEND):
                for file in files:
                    org_file_path = os.path.join(root, file)
                    arcname = os.path.relpath(org_file_path, start=self.DIR_TO_SEND)
                    zipf.write(org_file_path, arcname)


        # 3: Send Dir name and size
        self.client.send((self.ZIP_NAME+'\n').encode())
        # send size
        dir_size = os.path.getsize(zip_path)
        self.client.send(struct.pack('>Q',dir_size))

        # 5: Send the Directory
        print('server says: Sending the dir>>>>>>>\n')
        with open(zip_path,'rb') as f:
            while True:
                chunk = f.read(self.BUFFER_SIZE)
                if not chunk:
                    break
                self.client.sendall(chunk)
        print(f'server says: Directory {self.ZIP_NAME} sent successfully.\n')
        
        # receiving confirmation from worker
        confirmation = b''
        while b'\n' not in confirmation:
            confirmation = self.client.recv(self.BUFFER_SIZE)
        confirmation = confirmation.split(b'\n')[0].decode()
        print(f'server says: {confirmation}')


    #receive the trained model
    def receive_model(self,final_path):
        # 6.Recieve model_file Name and size
        model_name = b''
        while b'\n' not in model_name:
            model_name = self.client.recv(self.BUFFER_SIZE)
        model_name = model_name.split(b'\n')[0].decode()
        
        #size
        model_size = struct.unpack('>Q', self.client.recv(8))[0]
        zip_model_path = os.path.join(final_path,model_name)
        
        #7. Recieve model content
        with open(zip_model_path,'wb') as f1:
            received = 0
            while received<model_size:
                chunk = self.client.recv(min(self.BUFFER_SIZE, model_size-received))
                if not chunk:
                    break
                f1.write(chunk)
                received+=len(chunk)

        print(f"server says: Received trained model: {model_name}")

