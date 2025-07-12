# lmcache-local-cpu-backend-submit-put-task-benchmark

Benchmark for https://github.com/LMCache/LMCache/pull/1032

Run `python benchmark.py`

```
Original single-item calls: 0.100 seconds
Optimized single-item calls: 0.096 seconds
Original batched method:      0.092 seconds
Optimized batched method:     0.077 seconds

Improvement for batched method: 0.16%
```
