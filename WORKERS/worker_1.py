import socket 
import struct
import zipfile
import os
import subprocess

# the model script should be named modelss.py
class Trainer:
    def __init__(self,client:socket.socket):
        self.client_socket = client
        self.BUFFER_SIZE = 1024
        self.RECEIVED_ZIP = 'received_dir.zip'
        self.EXTRACTED_DIR = 'received_dir'
        self.TRAINED_MODEL_ZIP = "trained_model.zip"



    def receive_n_unzip(self):
        # 2: Recieve the Dir_name, Dir_size
        zip_name = b''
        while b'\n' not in zip_name:
            zip_name += self.client_socket.recv(self.BUFFER_SIZE)
        zip_name = zip_name.split(b'\n')[0].decode()
        #Dir_size
        zip_dir_size = struct.unpack('>Q',self.client_socket.recv(8))[0]

        # 3: Receive the dir 
        print(f'worker says: started receiving the dir {zip_name}\n')
        with open(self.RECEIVED_ZIP,'wb') as f:
            remaining_size = zip_dir_size
            while remaining_size:
                chunk = self.client_socket.recv(min(self.BUFFER_SIZE,remaining_size))
                if not chunk:
                    break
                f.write(chunk)
                remaining_size-=len(chunk)
        print(f'worker says: Received Directory {self.RECEIVED_ZIP} : {zip_dir_size} bytes\n')

        # 4: unzip the received file
        with zipfile.ZipFile(self.RECEIVED_ZIP,'r') as zipf:
            zipf.extractall(self.EXTRACTED_DIR)
        print(f'Excracted Dir {self.EXTRACTED_DIR}')

        #subpart: send confirmation to server that dir recieved and model is being trained
        self.client_socket.send('worker says: Directory Received >>>> Training model>>>>>>\n'.encode())



    def train_n_send(self):
        #5. Run the script and train the  model
        model_script_path = os.path.join(self.EXTRACTED_DIR,'modelss.py')
        print('worker says: Training Model>>>>>>>\n')
        subprocess.run(['python', model_script_path], check=True)
        print('worker says: Training complete.\n')

        #6. zip the trained model
        with zipfile.ZipFile(self.TRAINED_MODEL_ZIP, 'w', zipfile.ZIP_DEFLATED) as zipf1:
            for root, _, files in os.walk(self.EXTRACTED_DIR):
                for file in files:
                    if file.endswith(('.pkl','.joblib','.h5','sav')):
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path,start=self.EXTRACTED_DIR)
                        zipf1.write(file_path, arcname)

        print(f"worker says: Trained model zipped as {self.TRAINED_MODEL_ZIP}\n")

        # send back model size and name
        model_size = os.path.getsize(self.TRAINED_MODEL_ZIP)
        self.client_socket.send((self.TRAINED_MODEL_ZIP + '\n').encode())
        self.client_socket.send(struct.pack('>Q', model_size))  

        #7. send back zipped model file
        with open(self.TRAINED_MODEL_ZIP,'rb') as f1:
            while True:
                chunk = f1.read(self.BUFFER_SIZE)
                if not chunk:
                    break
                self.client_socket.sendall(chunk)


        print("worker says: Sent trained model back to server.\n")
