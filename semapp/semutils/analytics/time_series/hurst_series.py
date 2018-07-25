
import pandas as pd
import numpy as np
import random

## Hurst
def hurst_series(x, N):
    def _hurst(x):
        segs = 4.00 #5.0
        N = len(x)
        mlarge = np.floor(N/segs)
        M = np.array([np.floor(np.logspace(0,np.log10(mlarge),50))])
        M = np.unique(M[M>1])
        n = len(M)
        cut_min = int(np.ceil(n/10.0))
        cut_max = int(np.floor(6.0*n/10.0))
        V= np.zeros(n)
        for i in range(n):
                m = int(M[i])
                k = int(np.floor(N/m))
                matrix_sequence = np.array(x[:m*k]).reshape((k,m))
                V[i] = np.var(np.sum(matrix_sequence,1)/float(m))
        x = np.log10(M)
        y = np.log10(V)
        y1 = -x+y[0]+x[0]
        X = x[cut_min:cut_max]
        Y = y[cut_min:cut_max]
        p1 = np.polyfit(X,Y,1)
        Yfit = np.polyval(p1,X)
        yfit = np.polyval(p1,x)
        beta = -(Yfit[-1]-Yfit[0])/(X[-1]-X[0]);
        H = 1.0-beta/2.0
        return H

    if len(x) < N:
        return (pd.Series(index = x.index,data = np.NaN))
    v = np.zeros(len(x) - N + 1)
    for i in range(len(x) - N +1):
       # print i, x[i:i+N]
        v[i] = _hurst( x[i:i+N] )

    return pd.Series(index = x.index,data=np.append((N-1)*[np.NaN],v))
