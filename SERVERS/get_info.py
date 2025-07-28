import json
import platform
import shutil
import subprocess
import sys
import re

def run(cmd):
    try:
        return subprocess.check_output(cmd, stderr=subprocess.STDOUT, encoding="utf-8")
    except Exception:
        return None

def try_pytorch():
    try:
        import torch
        if not torch.cuda.is_available():
            return []
        out = []
        for i in range(torch.cuda.device_count()):
            p = torch.cuda.get_device_properties(i)
            out.append({
                "vendor": "NVIDIA (via PyTorch)",
                "name": p.name,
                "vram_GB": round(p.total_memory / 1e9, 2),
                "compute_capability": f"{p.major}.{p.minor}",
                "index": i,
            })
        return out
    except Exception:
        return []

def try_nvidia_smi():
    if not shutil.which("nvidia-smi"):
        return []
    txt = run(["nvidia-smi",
               "--query-gpu=name,memory.total,driver_version,compute_cap",
               "--format=csv,noheader,nounits"])
    if not txt:
        return []
    gpus = []
    for i, line in enumerate(txt.strip().splitlines()):
        parts = [p.strip() for p in line.split(",")]
        if len(parts) == 4:
            name, mem_mb, driver, cc = parts
        else:
            # older nvidia-smi without compute_cap
            name, mem_mb, driver = parts
            cc = "unknown"
        gpus.append({
            "vendor": "NVIDIA",
            "name": name,
            "vram_GB": round(float(mem_mb) / 1024, 2),
            "driver": driver,
            "compute_capability": cc,
            "index": i,
        })
    return gpus

def try_rocm_smi():
    # AMD ROCm
    if not shutil.which("rocm-smi"):
        return []
    txt = run(["rocm-smi", "--showproductname", "--showvbios", "--showmeminfo", "vram"])
    if not txt:
        return []
    gpus = []
    current = {}
    idx = 0
    for line in txt.splitlines():
        if "card" in line and "GPU" in line and "product name" in line.lower():
            # Example: GPU[0] 		: GPU ID: 0x73bf Product Name: Navi 21 ...
            name = line.split("Product Name:")[-1].strip()
            current = {"vendor": "AMD (ROCm)", "name": name, "index": idx}
        m = re.search(r"Total VRAM Memory:\s*([\d.]+)\s*MiB", line)
        if m and current:
            mem_mb = float(m.group(1))
            current["vram_GB"] = round(mem_mb / 1024, 2)
            gpus.append(current)
            current = {}
            idx += 1
    return gpus

def try_system_profiler():
    # macOS
    if platform.system() != "Darwin":
        return []
    txt = run(["system_profiler", "SPDisplaysDataType"])
    if not txt:
        return []
    gpus = []
    name, vram = None, None
    index = 0
    for line in txt.splitlines():
        if "Chipset Model:" in line:
            name = line.split(":", 1)[1].strip()
        if "VRAM" in line and "Total" not in line:
            vram_str = line.split(":", 1)[1].strip()
            m = re.search(r"([\d.]+)\s*GB", vram_str)
            if m:
                vram = float(m.group(1))
        if name and vram is not None:
            gpus.append({"vendor": "Apple/AMD/NVIDIA (macOS)", "name": name, "vram_GB": vram, "index": index})
            name, vram = None, None
            index += 1
    return gpus

def try_windows_wmi():
    if platform.system() != "Windows":
        return []
    # Try wmic first (deprecated but common)
    if shutil.which("wmic"):
        txt = run(["wmic", "path", "win32_VideoController", "get", "Name,AdapterRAM", "/format:csv"])
        if txt:
            gpus = []
            for i, line in enumerate(txt.splitlines()):
                if "," in line and "AdapterRAM" in line:
                    continue
                parts = [p.strip() for p in line.split(",") if p.strip()]
                if len(parts) >= 3:
                    # node,name,AdapterRAM
                    _, name, ram = parts[:3]
                    try:
                        vram_gb = round(int(ram) / (1024**3), 2)
                    except Exception:
                        vram_gb = None
                    gpus.append({"vendor": "Windows WMI", "name": name, "vram_GB": vram_gb, "index": i})
            if gpus:
                return gpus
    # Fallback to PowerShell (if available)
    if shutil.which("powershell"):
        ps = 'Get-CimInstance Win32_VideoController | Select-Object Name,AdapterRAM | ConvertTo-Json'
        txt = run(["powershell", "-NoProfile", "-Command", ps])
        if txt:
            try:
                data = json.loads(txt)
                if isinstance(data, dict):
                    data = [data]
                gpus = []
                for i, d in enumerate(data):
                    ram = d.get("AdapterRAM")
                    gpus.append({
                        "vendor": "Windows CIM",
                        "name": d.get("Name"),
                        "vram_GB": round(ram / (1024**3), 2) if isinstance(ram, int) else None,
                        "index": i
                    })
                return gpus
            except Exception:
                pass
    return []

def try_lspci():
    # Linux generic (gives names, not VRAM)
    if platform.system() != "Linux" or not shutil.which("lspci"):
        return []
    txt = run(["lspci"])
    if not txt:
        return []
    gpus = []
    index = 0
    for line in txt.splitlines():
        if "VGA compatible controller" in line or "3D controller" in line:
            name = line.split(": ", 1)[-1].strip()
            gpus.append({"vendor": "lspci", "name": name, "vram_GB": None, "index": index})
            index += 1
    return gpus

def detect_gpus():
    # Order: higher fidelity first
    for fn in (try_pytorch, try_nvidia_smi, try_rocm_smi, try_system_profiler, try_windows_wmi, try_lspci):
        gpus = fn()
        if gpus:
            return gpus
    return []

if __name__ == "__main__":
    gpus = detect_gpus()
    result = {
        "available": bool(gpus),
        "count": len(gpus),
        "gpus": gpus
    }
    print(json.dumps(result, indent=2))
    if not gpus:
        print("\nNo GPU detected (or no backend tool available).", file=sys.stderr)
