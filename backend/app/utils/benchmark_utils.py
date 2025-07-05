import time
import psutil
from pynvml import (
    nvmlInit, nvmlShutdown,
    nvmlDeviceGetHandleByIndex, nvmlDeviceGetUtilizationRates,
    nvmlDeviceGetMemoryInfo
)

def log_system_usage(logger):
    # CPU and RAM
    process = psutil.Process()
    mem = process.memory_info()
    logger.info(f"[Benchmark] CPU Memory RSS: {mem.rss / 1024**2:.2f} MB")

    # GPU usage
    try:
        nvmlInit()
        handle = nvmlDeviceGetHandleByIndex(0)  # 0 = first GPU
        util = nvmlDeviceGetUtilizationRates(handle)
        mem_info = nvmlDeviceGetMemoryInfo(handle)
        logger.info(f"[Benchmark] GPU Utilization: {util.gpu}%")
        logger.info(f"[Benchmark] GPU Memory Used: {mem_info.used / 1024**2:.2f} MB / {mem_info.total / 1024**2:.2f} MB")
    except Exception as e:
        logger.warning(f"[Benchmark] GPU info unavailable: {e}")
    finally:
        try:
            nvmlShutdown()
        except:
            pass

class Timer:
    def __init__(self, label, logger):
        self.label = label
        self.logger = logger

    def __enter__(self):
        self.start = time.perf_counter()
        self.logger.info(f"[Benchmark] Started: {self.label}")
        return self

    def __exit__(self, *args):
        elapsed = time.perf_counter() - self.start
        self.logger.info(f"[Benchmark] Finished: {self.label} in {elapsed:.2f} seconds")
