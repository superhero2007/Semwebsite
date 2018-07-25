import pandas as pd
import numpy as np
import os, sys
import multiprocessing 
import gc
import traceback


## multiprocessing groupby apply
def multiprocessing_groupby_apply(df,groupby_cols,func,*func_args, **kwargs):
    # kwargs:
    #    df = dataframe with index reset
    #    processes = number of processes to run
    #    *func_args are passed to the executed function. Should be in order
    # note: this assumes that the function looks like func(group_name,df,*func_args)
    workers = kwargs.pop('processes')

    if workers <1: # error
        raise Exception ('Invalid number of processes specified')
    elif workers ==1:
        return (df.groupby(groupby_cols).apply(lambda x: func(x.name,x,*func_args)))
    else:
        if 'min_splits' in kwargs.keys():
            min_splits = kwargs.pop('min_splits')
            splits = max(workers,min_splits)
        else:
            splits = workers

        if isinstance(groupby_cols, list) and (len(groupby_cols) >1):
            groups = [[tuple(i) for i in j.values] for j in np.array_split(df[groupby_cols].drop_duplicates(),splits)]
            df_split = [df.set_index(groupby_cols).loc[x].reset_index(drop=False) for x in groups]
        else:
            df_split = [df.set_index(groupby_cols).loc[x].reset_index(drop=False) for x in np.array_split(df[groupby_cols].drop_duplicates(),splits)]
        pool = multiprocessing.Pool(processes=workers)
        results = pool.map(_mga_apply_df, [(d, groupby_cols,func, func_args)
                                       for d in df_split])
        pool.close()
        pool.join()
        gc.collect()
        return pd.concat(results,ignore_index=True)

def _mga_apply_df(args):
    df, groupby_cols,func, func_args = args
    return df.groupby(groupby_cols).apply(lambda x:_mga_apply_error_trap(x.name,x,func,func_args))

def _mga_apply_error_trap(group_name,df,func,func_args):
    try:
        return func(group_name,df,*func_args)
    except:
        print ('Group = %s, Traceback = %s'%(group_name,traceback.format_exc()))
        sys.stdout.flush()
        raise Exception ('Exception in %s'%group_name)
        sys.exit()

