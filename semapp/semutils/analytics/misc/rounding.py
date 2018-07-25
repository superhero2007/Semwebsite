
import numpy as np

def round_to(n, precision):
    correction = 0.5 if n >= 0 else -0.5
    return int( n/precision+correction ) * precision

def floor_to(n, precision):
    return np.floor(n/precision) * precision

