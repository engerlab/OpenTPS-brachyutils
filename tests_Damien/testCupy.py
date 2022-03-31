import cupy as cp
import numpy as np

cp.show_config()

x_cpu = np.array([1, 2, 3])
l2_cpu = np.linalg.norm(x_cpu)
x_gpu = cp.array([1, 2, 3])
l2_gpu = cp.linalg.norm(x_gpu)

# from cupyx.profiler import benchmark
#
# def my_func(a):
#     return cp.sqrt(cp.sum(a**2, axis=-1))
#
# a = cp.random.random((256, 1024))
# print(benchmark(my_func, (a,), n_repeat=20))
#
#
# x_gpu = cp.array([1, 2, 3])
# l2_gpu = cp.linalg.norm(x_gpu)