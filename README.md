# DispML: A Remote ML Job Scheduler

A lightweight, socket-based system to distribute machine learning training jobs from a central server to multiple remote worker machines.  
This project aims to simulate a minimal GPU-renting or compute-sharing platform for ML model training.

- > UNDER PROGRESS
- > Currently supports only CPU workers.

---

## Features

- Send a directory containing full training `datasets + scripts` from server to worker
- Train models remotely on remote worker machines
- Auto job assignment: idle workers are picked automatically and jobs are assigned to them
- Auto-retry: if a worker dies mid-job, the job is reassigned to another worker and dead worker is dropped
- Heartbeat checks: continiously check wheter the worker alive or not
- Logging: in terminal shows which worker is doing what

---

## Architecture Overview

**`SERVER --> WORKER` communication:**

- Workers connect and register
- Workers are listed and they wait to get a job assigned to them by server
- Server maintains a job queue
- if job queue is empty Server waits for jobs, assigns work
- Workers receive scripts, train model, and send back trained model
- Server tracks worker health

---

## Current Limitations 
(working on this)

- No GPU support yet (easy to add)
- No multi-worker distribution per job (1 job → 1 worker)
- No database/backend — everything is socket-based and in-memory

---
## Mandatory Instructions
- > Project directory structure should not be changed
- > If running the server and worker on diffrent devices make sure to change the IP address in main_server.py and main_worker.py to IP_add of host
  

## Setup & Run


```(bash
1. Clone the Repository
git clone https://github.com/Krdhirendra/DispML-A-remote-ML-job-scheduler.git
cd distributed-ml-server

2. Start the Server
python main_server.py

3. Start One or More Workers
(on same or different machines)
python main_worker.py


Project Structure
├── servers
    main_server.py
    server_1.py
    get_info.py
    all_models
      waiting
        #here should be the project directory with main model script as ***modelss.py*** 
      working
        #after the job gets assigned the project directory will be transfered here
├── workers
    main_worker.py
    worker_1.py
```

##  Ideas for Future Expansion
-  worker filtering over available gpu
-  Parallel training (split one job across multiple workers)
-  Web dashboard using FastAPI or Flask
-  Secure file transfer (encryption, verification)

##  About the Creator
- This project was developed by ***DHIRENDRA KUMAR*** (Krdhirendra) as a solo learner.
-  AI tools (like ChatGPT and DeepSeek) has been extensively used to assist with coding, but the architecture, logic, and execution were fully self-built.

⏱️ Built over several fragmented days effort (due to academic load lol).
📫 Contact: krdhirendra2006@gmail.com

### *I’m a learner, so there might be mistakes or bugs in the project.Feel free to contribute, suggest improvements, or just reach out — I'm always open to learning!*
