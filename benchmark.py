import threading
import time
from collections import OrderedDict
from typing import List

# Mock classes to simulate the environment
class DummyMemoryObj:
    def ref_count_up(self): pass
    def ref_count_down(self): pass
    def get_size(self): return 1

class DummyKey:
    def __init__(self, idx): self.idx = idx
    @property
    def worker_id(self): return 0
    @property
    def chunk_hash(self): return self.idx
    def __hash__(self): return hash(self.idx)
    def __eq__(self, other): return isinstance(other, DummyKey) and self.idx == other.idx

class DummyWorker:
    def put_msg(self, msg): pass

class LocalCPUBackendMock:
    def __init__(self):
        self.hot_cache = OrderedDict()
        self.cpu_lock = threading.Lock()
        self.usage = 0
        self.lmcache_worker = DummyWorker()
        self.stats_monitor = self

    def update_local_cache_usage(self, usage): pass

    # --- Start of Method Implementations ---

    def _unlocked_put(self, key: DummyKey, memory_obj: DummyMemoryObj) -> int:
        size_change = 0
        if key in self.hot_cache:
            old = self.hot_cache.pop(key)
            old.ref_count_down()
            size_change -= old.get_size()
        self.hot_cache[key] = memory_obj
        memory_obj.ref_count_up()
        size_change += memory_obj.get_size()
        return size_change

    def submit_put_task_original(self, key: DummyKey, memory_obj: DummyMemoryObj):
        with self.cpu_lock:
            if key in self.hot_cache:
                old = self.hot_cache.pop(key)
                old.ref_count_down()
                self.usage -= old.get_size()
            self.hot_cache[key] = memory_obj
            memory_obj.ref_count_up()
            self.usage += memory_obj.get_size()
        self.stats_monitor.update_local_cache_usage(self.usage)
        if self.lmcache_worker: self.lmcache_worker.put_msg(None)

    def submit_put_task_optimized(self, key: DummyKey, memory_obj: DummyMemoryObj):
        with self.cpu_lock:
            size_change = self._unlocked_put(key, memory_obj)
            self.usage += size_change
        self.stats_monitor.update_local_cache_usage(self.usage)
        if self.lmcache_worker: self.lmcache_worker.put_msg(None)

    def batched_submit_put_task_original(self, keys: List[DummyKey], memory_objs: List[DummyMemoryObj]):
        for key, memory_obj in zip(keys, memory_objs):
            self.submit_put_task_original(key, memory_obj)

    def batched_submit_put_task_optimized(self, keys: List[DummyKey], memory_objs: List[DummyMemoryObj]):
        total_size_change = 0
        with self.cpu_lock:
            for key, memory_obj in zip(keys, memory_objs):
                total_size_change += self._unlocked_put(key, memory_obj)
            self.usage += total_size_change
        self.stats_monitor.update_local_cache_usage(self.usage)
        if self.lmcache_worker:
            for key in keys: self.lmcache_worker.put_msg(None)

# --- End of Method Implementations ---

def benchmark_runner(backend, num_threads, num_batches, batch_size, method_to_test):
    # Worker function for each thread
    def worker_fn():
        for _ in range(num_batches):
            keys = [DummyKey(i) for i in range(batch_size)]
            memory_objs = [DummyMemoryObj() for _ in range(batch_size)]
            
            if method_to_test == 'batched_optimized':
                backend.batched_submit_put_task_optimized(keys, memory_objs)
            elif method_to_test == 'batched_original':
                backend.batched_submit_put_task_original(keys, memory_objs)
            elif method_to_test == 'single_optimized':
                for k, m in zip(keys, memory_objs): backend.submit_put_task_optimized(k, m)
            elif method_to_test == 'single_original':
                for k, m in zip(keys, memory_objs): backend.submit_put_task_original(k, m)

    threads = [threading.Thread(target=worker_fn) for _ in range(num_threads)]
    start_time = time.perf_counter()
    for t in threads: t.start()
    for t in threads: t.join()
    end_time = time.perf_counter()
    return end_time - start_time

if __name__ == "__main__":
    # Benchmark parameters
    params = {'num_threads': 8, 'num_batches': 200, 'batch_size': 64}

    # Run tests
    backend = LocalCPUBackendMock()
    t_orig_single = benchmark_runner(backend, **params, method_to_test='single_original')
    t_opt_single = benchmark_runner(backend, **params, method_to_test='single_optimized')
    t_orig_batched = benchmark_runner(backend, **params, method_to_test='batched_original')
    t_opt_batched = benchmark_runner(backend, **params, method_to_test='batched_optimized')

    # Print results
    print(f"Original single-item calls: {t_orig_single:.3f} seconds")
    print(f"Optimized single-item calls: {t_opt_single:.3f} seconds")
    print(f"Original batched method:      {t_orig_batched:.3f} seconds")
    print(f"Optimized batched method:     {t_opt_batched:.3f} seconds")
    print(f"\nImprovement for batched method: {(t_orig_batched - t_opt_batched) / t_orig_batched:.2f}%")
