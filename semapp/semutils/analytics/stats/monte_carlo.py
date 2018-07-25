
import pandas as pd
import numpy as np
import random

## Monte Carlo
def monte_carlo(data, n,num_samples, statistic, alpha,test_value=None,random_seed=None):
    """Returns monte carlo simulation estimate of 100.0*(1-alpha) CI for statistic."""
    random.seed(random_seed)
    #idx = np.array([random.sample(range(len(data)),n) for i in range(num_samples)])
    idx = np.array([np.random.choice(len(data),n,replace=False) for i in range(num_samples)])
    samples = data[idx]
    stat = np.sort(statistic(samples, 1))
    #stat = np.sort(np.array([np.mean(np.random.choice(data,size = n,replace=False)) for i in range (0,num_samples)]))
    if pd.isnull(test_value):
        return (stat[int((alpha/2.0)*num_samples)],
                stat[int((1-alpha/2.0)*num_samples)])
    else: # return p-value of test_value
        return ((num_samples - bisect(stat,test_value)-1)/num_samples)

