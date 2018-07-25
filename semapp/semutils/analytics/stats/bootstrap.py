
import numpy as np
import random

## Bootstrap
def bootstrap(data, num_samples, statistic, alpha, random_seed=None,low_memory=True):
    """Returns bootstrap estimate of 100.0*(1-alpha) CI for statistic."""
    np.random.seed(random_seed)
    n = len(data)
    if not n:
        return(np.NaN,np.NaN)

    if not low_memory:
        idx = np.random.randint(0, n, (num_samples, n))
        samples = data[idx]
        stat = np.sort(statistic(samples, 1))
    else:
        stat = []
        for i in range(num_samples):
            idx = np.random.randint(0, n, n)
            sample = data[idx]
            stat.append(statistic(sample))
        stat = np.sort(stat)
    return (stat[int((alpha/2.0)*num_samples)],
            stat[int((1-alpha/2.0)*num_samples)])
