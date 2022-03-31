from Process.Tracking_Processes.NavigatorTracking import oneDimensionNavThreshold
import numpy as np
import matplotlib.pyplot as plt
import os
import pickle

dictFilePath = '/home/damien/Code/opentps/tests/DynSeries3DAnd2D.p'

# option for large files
max_bytes = 2 ** 31 - 1
bytes_in = bytearray(0)
input_size = os.path.getsize(dictFilePath)
with open(dictFilePath, 'rb') as f_in:
    for _ in range(0, input_size, max_bytes):
        bytes_in += f_in.read(max_bytes)

patient = pickle.loads(bytes_in).list[0]

print(type(patient))

print(len(patient.Dyn4DSeqList))
print(len(patient.Dyn2DSeqList))


