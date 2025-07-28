# 

import socket
import threading
import os
import struct
import shutil
from server_1 import Sender
from collections import OrderedDict
from pathlib import Path
import time
import queue
import logging


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger()


# define some constants
HOST = '127.0.0.1'
PORT = 5050        
get_info_file = r'get_info.py'
src_dir = r'all_models\waiting'
dst_dir = r'all_models\worked'


#initializing
waiting_projects = [p for p in Path(src_dir).iterdir() if p.is_dir()]
workers_info = OrderedDict()#just to keep track of active connections
waiting_workers = [] #active workers waiting to get a job
working_workers = [] #active workers which are working on a job
lock = threading.Lock()
input_lock = threading.Lock()
active_jobs = {} #keep track of active jobs
job_queue = queue.Queue()



#get information about available GPU of active workers
def get_info(file_add,client:socket.socket):
    #send name and size
    filename = os.path.basename(file_add)+'\n'
    client.send(filename.encode())
    #send size of file
    size = os.path.getsize(file_add)
    client.send(struct.pack('>Q',size))

    with open(file_add,'rb') as f:
        while True:
            chunk = f.read(1024)
            if not chunk:
                break
            client.sendall(chunk)



# get the info about the worker device back
def recv_info(client: socket.socket):
    # <3u
    #receive output size
    size = struct.unpack('>I',client.recv(4))[0]
    # receive output
    output = b''
    while len(output)<size:
        chunk = client.recv(size-len(output))
        if not chunk:
            raise ConnectionError("Socket closed before full output was received")
        output += chunk
    return output.decode()



# when a new worker connects to server it gets added to a waiting list from which server can pick it and assign a job
def add_worker(worker):
    try:
        get_info(get_info_file, worker) #
        worker_info = recv_info(worker)
        with lock:
            workers_info[worker] = worker_info
            waiting_workers.append(worker)

            logger.info(f'Worker Added: {worker.getpeername()}')
            logger.info(f"Workers: {len(workers_info)} | Waiting: {len(waiting_workers)} | Working: {len(working_workers)}")
    except Exception as e:
        logger.error(f'Error adding worker: {e}')#333



#drop a worker
def drop_worker(conn):
    try:
        addr = conn.getpeername() # get peer address first
    except:
        addr = "<unknown>"
    with lock:
        workers_info.pop(conn, None) #drop from workers info 
        if conn in waiting_workers:    waiting_workers.remove(conn) #from waiting list
        if conn in working_workers:    working_workers.remove(conn) #from working list
    try:
        conn.close() #finally close the connection with the worker
    except:
        pass
    logger.info(f"Worker removed: {addr}") #show in terminal



# when job is assigned to a worker from waiting list that worker is transferred to working list 
# this ensure that a single worker does not get assigned to muiitiple jobs
def transfer_to_workin(worker):
    with lock:
        if worker in waiting_workers:
            waiting_workers.remove(worker)
        working_workers.append(worker)



# after the worker completes its job it is again transferred back to waiting list so that it can be assigned another job
# this ensures smooth worker rotation 
def transfer_to_waitin(worker):
    with lock:
        if worker in working_workers:
            working_workers.remove(worker)
        waiting_workers.append(worker)


# this function is used to transfer the job directory from waiting to worked
# this ensures one job does not get reassigned to multiple worker
# if job fails due to any reason the same function is used to transfer back the job directory to waiting so that it can be reassigned to another worker
def transfer_dir(dst_dir,project_dir):#params:    dst_dir= the directory where job dir need to transfered       #project_dir = the path of project dir
    dst_dir = Path(dst_dir).resolve()
    #choose a directory amd then transfer that to worked dir
    chosen_dir = project_dir
    dst_dir.mkdir(parents=True,exist_ok = True)
    shutil.move(str(chosen_dir),dst_dir)

    return dst_dir / project_dir.name


#-------------------------------------------------------------------------------------------------------------------------------------#
# this function executes the actual work
def run_job(worker, project_path): #params:   #worker=to which job will be assigned  #project_path=path of project dir which to be assigned
    try:
        peer = worker.getpeername()
    except:
        peer = "<unknown>"
    success = False
    try:
        # first transfet the worker to working list
        transfer_to_workin(worker)
        logger.info(f"Workers: {len(workers_info)} | Waiting: {len(waiting_workers)} | Working: {len(working_workers)}")#333
        logger.info(f"Starting job: {project_path.name} with worker {peer}")

        #create a object of sender class
        sender = Sender(client=worker,dir_path=project_path)#object of sender class
        sender.zip_and_send()#zip the job and send it to worker

        # transferring the project directory
        final_path = transfer_dir(dst_dir=dst_dir,project_dir=project_path)#transfer the job to worked dir so it doesn't gets re-assigned
        logger.info(f"Moved project: {project_path.name} to worked")

        #receive the trained model back from worker
        sender.receive_model(final_path=final_path)
        logger.info(f"Received model from worker {peer}")
        success = True
    except(BrokenPipeError, ConnectionResetError, OSError) as e: #if worker dies or any other error
        logger.error(f'\nERROR:\n{e}\n')
        drop_worker(worker)

        # transfer project back to source if job failed
        transfer_dir(dst_dir=src_dir,project_dir=project_path)
        logger.warning(f'Returned Project to queue: {project_path.name}')
    finally:
        if worker in working_workers:
            transfer_to_waitin(worker)#after job completion transfer the worker back to waiting list
        
        if worker in active_jobs:
            active_jobs.pop(worker)#remove the job from active job no matter if job is completed or not
        
        if success: #if job is successfully completed by worker
            job_queue.put(worker)
            logger.info(f"Job completed by worker {peer}")



#-------------------------------------------------------------------------------------------------------------------------------------#
#functiom to auto assign available work to idle waiting worker
def assign_job():
    """Auto-assign jobs to available workers"""
    while True:
        try:
            with lock:#refresh waiting directory each time 
                if not waiting_projects:
                    waiting_projects[:] = [p for p in Path(src_dir).iterdir() if p.is_dir()]

                    if waiting_projects:
                        logger.info(f'Refreshed projects: {len(waiting_projects)} available')
                        
                #assigning job if available
                if waiting_projects and waiting_workers:
                    worker = waiting_workers[0] #get a worker from waiting worker list
                    project_path = waiting_projects.pop(0) #get a project from waiting project path

                    #create and track job thread
                    #seperate job thread for each worker
                    job_thread = threading.Thread(
                        target=run_job,
                        args=(worker,project_path),
                        daemon=True
                        )
                    active_jobs[worker] = job_thread
                    job_thread.start()
                    logger.info(f'Assigned {project_path.name} to {worker.getpeername()}')

        except Exception as e:
            logger.error(f'Assignment error: {e}')

        time.sleep(1)



#-------------------------------------------------------------------------------------------------------------------------------------#
#keep checking wheter the worker is alive or not
def handle_wokrer(conn, addr):
    logger.info(f'[+] Connection established with {addr}')
    add_worker(conn)

    try:
        while True:
            time.sleep(10)
            try:
                conn.send(b'')
            except:
                logger.warning(f'Connection lost with {addr}')
                break
    except Exception as e: #if not show error in terminal
        logger.error(f'Handler error: {e}')
    finally: #drop the dead worker
        drop_worker(conn)



#-------------------------------------------------------------------------------------------------------------------------------------#
# Start the server
def start_server():
    #start the assigner thread
    assigner_thread = threading.Thread(target=assign_job,daemon=True)
    assigner_thread.start()


    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((HOST, PORT))
        server_socket.listen()
        print(f"\nServer listening on {HOST}: {PORT}...\n")
        
        while True:
            conn, addr = server_socket.accept()
            thread = threading.Thread(target=handle_wokrer, args=(conn,addr),daemon=True)
            thread.start()
        
if __name__ == "__main__":
    start_server()


    