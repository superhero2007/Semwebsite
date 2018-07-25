import pandas as pd
import numpy as np

def integral(r, c):
    r = r[np.argsort(c)]
    c = np.sort(c)
    return np.trapz(r, c)

def rt_curve(ret, conf, consol_by_date = False, long_short_boundary=0.5, N=100):
    '''
    ret, conf = series with data date as index
    '''
    assert ret.index.name =='data_date'
    assert conf.index.name =='data_date'

    df = pd.concat([ret,conf],axis=1)
    df.columns = ['ret','conf']

    # calculate longs area
    res = []
    for t in np.linspace(long_short_boundary, df.conf.max(), N):
        dff = df[df.conf >= t]
        if consol_by_date:
            res.append((dff.groupby('data_date').ret.mean().mean(),dff.groupby('data_date').ret.count().mean()))
        else:
            res.append((dff.ret.mean(), len(dff)))

    res = np.nan_to_num(np.array(res))
    along = integral(res[:,0],res[:,1])

    # calculate shorts area
    res = []
    for t in np.linspace(df.conf.min(), long_short_boundary, N):
        dff = df[df.conf <= t]
        if consol_by_date:
            res.append((-1 * dff.groupby('data_date').ret.mean().mean(),dff.groupby('data_date').ret.count().mean()))
        else:
            res.append((-1 * dff.ret.mean(), len(dff)))

    res = np.nan_to_num(np.array(res))
    ashort = integral(res[:,0],res[:,1])
    
    return(along, ashort,(along+ashort)/2)


def test():
    for f in ['data_with_signals_test3_w_nondzs_F_spc_20day_class.parquet',
              'data_with_signals_test3_w_nondzs_F_spc_20day_class_nosw.parquet',   
              'data_with_signals_test3_w_nondzs_F_spc_20day_class_nosw_cwbal.parquet',   
              'data_with_signals_test3_w_nondzs_noit_nosi_F_spc_20day_class.parquet']:
        cols = ['data_date', 'SignalConfidence', 'F_spc_1day_clipped', 'Tradeable']
        df = pd.read_parquet(f, columns=cols)
        df = df[df.Tradeable & df.SignalConfidence.notnull()]

        longs = df[df.SignalConfidence >= 0.5]
        l = rt_curve(longs.F_spc_1day_clipped,longs.SignalConfidence)
        shorts = df[df.SignalConfidence < 0.5]
        s = -1 * rt_curve(shorts.F_spc_1day_clipped,shorts.SignalConfidence,'down')
        print (f)
        print (l)
        print (s)
        print (np.sqrt(l*s))


if __name__=='__main__':
    test()
