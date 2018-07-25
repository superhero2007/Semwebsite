import pandas as pd

def build_date_mapper (original_dates,master_dates):
    # original dates should be a unique list
    # master dates should be a sorted pandas index
    mapper = pd.DataFrame()
    mapper['original'] = original_dates
    mapper = mapper[mapper.original <= master_dates.max()]
    mapper['new'] = mapper.original.apply(lambda x: master_dates[master_dates.get_loc(x,method='bfill')])
    return(mapper.set_index('original')['new'])

