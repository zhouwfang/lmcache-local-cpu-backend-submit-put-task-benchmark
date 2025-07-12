# lmcache-local-cpu-backend-submit-put-task-benchmark

Benchmark for https://github.com/LMCache/LMCache/pull/1032

Run `python benchmark.py`

```
Original single-item calls: 0.097 seconds
Optimized single-item calls: 0.095 seconds
Original batched method:      0.093 seconds
Optimized batched method:     0.077 seconds

Speedup for batched method: 1.22x
```
