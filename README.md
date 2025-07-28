# DispML-A-remote-ML-job-scheduler

🚀A lightweight, socket-based system to distribute machine learning training jobs from a central server to multiple worker machines. This project aims to simulate a minimal GPU-renting or compute-sharing platform for ML model training — but currently runs on CPU workers only.


🚀 Features
1. Send full training datasets + scripts from server to worker
2. Train models remotely on worker machines
3. Auto job assignment: Idle workers are picked when new jobs arrive
4. Auto-retry: If a worker disconnects mid-job, job is reassigned to next worker
5. Heartbeat checks: Periodic ping from server to detect dead workers
6. Logs & status tracking: logging in terminal of server to know which worker is doing what
7. Plug-n-play worker registration


🖥️ Architecture Overview
'''SERVER --> WORKER'''
 - Connects & registers        - Maintains job queue
 - Waits for assignment        - Assigns work
 - Tracks worker health        - Trains model using dataset


🧪 Current Limitations
❗ No GPU support yet (but easy to integrate)
❗ No multi-worker distribution per job (1 job → 1 worker)
❗ No cloud or database backend — entirely socket-based


🛠️ Setup & Run
1. Clone this repo
'''git clone https://github.com/your-username/distributed-ml-server.git
'''cd distributed-ml-server

3. Start Server
'''python server.py

5. Start One or More Workers (on same/different machines)
'''python worker.py
📂 Project Structure
bash
Copy
Edit
distributed-ml-server/
├── server.py            # Main server logic
├── worker.py            # Client device script
├── Sender.py            # Utility to send zipped directories
├── job_queue/           # Contains job files to be assigned
├── logs/                # Logs of completed jobs
├── LICENSE              # Custom license
└── README.md



💡 Ideas for Future Expansion
 1. GPU capability detection + preference
 2. Parallel training (split job across multiple workers)
 3. Web dashboard using FastAPI or Flask
 4. Secure file transfer (e.g., encryption)

🧑‍💻 About the Creator
This project was developed by **DHIRENDRA KUMAR** Krdhirendra as a solo learning endeavor, with extensive use of AI tools like ChatGPT and DeepSeek. While around 20-30% of the code was AI-assisted. all logic, architecture, and execution is self built.

📄 License
This project uses a custom license that allows fair use and collaboration, but prohibits unauthorized commercial use without agreement.
