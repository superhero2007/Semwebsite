# Python Libraries
import io
import logging
import os
import sys

# Site Libraries
import numpy as np
import pandas as pd
import sklearn.linear_model as LM
import statsmodels.api as sm
import statsmodels.formula.api as smf


def compute_attribution(conn, df, axioma_model = 'sh') :
    """
    Do attribution analysis of portfolio returns against factor model returns from axioma.

    Parameters
    ----------

    df : Time series data frame of portfolio position weights with data_date as index and 'sec_id' and 'weight' as columns

    axioma_model : 'mh', 'sh' or 'shs' as the underlying factor model to use from Axioma
    """

    # Get all the factor returns for the given model.

    fret            = conn.get_factor_returns(start_date = df.index.min(), end_date = df.index.max(), axioma_model = axioma_model) \
        .drop(columns = ['date_modified', 'date_created'])

    fexp            = conn.get_exp(sec_ids = df.sec_id.unique(), start_date = df.index.min(), end_date = df.index.max(), axioma_model = axioma_model) \
        .drop(columns = ['AxiomaID','date_modified', 'date_created']) \
        .fillna(0)

    assert (sorted(fret.columns) == sorted(fexp.columns))    
    #fexp.Market_Intercept = fexp.Market_Intercept.fillna(1) # not really necessary if all sec_ids are found
    
    df              = df \
        .reset_index() \
        .set_index(['sec_id','data_date']) \
        .sort_index()

    df[fexp.columns] = fexp

    assert df.notnull().any().any()

    exposures       = df[fexp.columns] \
        .multiply(df.weight, axis='index') \
        .groupby(level='data_date') \
        .sum()
    
    exposures       = exposures.shift(1) # shift forward to align exposure with returns
    att             = exposures * fret[exposures.columns]

    results         = exposures.iloc[0].to_frame('starting_exposure')
    results['ending_exposure'] = exposures.iloc[-1]
    results['mean_exposure'] = exposures.mean()
    results['contribution'] = att.sum().sum()

    return results, att



'''
def test() :
    # For reference to use for real pytest unit test later.
    import reference.common.Database    as Database
    import semutils.db_access.AccessReference   as AR

    appl = 'S0000181'
    msft = 'S000443D'

    ticker = appl

    weight = 1
    portfolio   = [
        {'data_date' : pd.Timestamp('2018-07-05'), 'sec_id' : ticker, 'weight' : weight},
        {'data_date' : pd.Timestamp('2018-07-06'), 'sec_id' : ticker, 'weight' : weight},
        {'data_date' : pd.Timestamp('2018-07-09'), 'sec_id' : ticker, 'weight' : weight},
        {'data_date' : pd.Timestamp('2018-07-10'), 'sec_id' : ticker, 'weight' : weight}
    ]

    conn        = Database.get_conn('prod', database = 'semoms')
    access_ref  = AR.AccessReference(conn.host)

    pw          = pd.DataFrame(portfolio).set_index('data_date')
    (r, att)    = compute_attribution(access_ref, pw)

    print(att.sum(axis = 1))

    return att


When weight of appl is 1.0
In [143]: df = FA.test()
data_date
2018-07-05   0.0000
2018-07-06   0.0120
2018-07-09   0.0154
2018-07-10   0.0110
dtype: float64

When weight of appl is 0.5
In [144]: df = FA.test()
data_date
2018-07-05   0.0000
2018-07-06   0.0060
2018-07-09   0.0077
2018-07-10   0.0055
dtype: float64
'''
