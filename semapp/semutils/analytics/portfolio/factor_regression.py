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

# In House Libraries
import semutils.db_access.AccessReference       as Database
import semutils.db_access.MasterConfig          as MasterConfig


def compute_regression(df, regression_type = 'lasso', lasso_alpha = 1e-6, axioma_model = 'sh') :
    """
    Do regression analysis of portfolio returns against factor model returns from axioma.

    Parameters
    ----------

    df : Time series data frame of portfolio returns

    regression_type :  Can be OLS or lasso
    
    lasso_seed : Seed factor when performing lasso analysis

    axioma_model : 'mh', 'sh' or 'shs' as the underlying factor model to use from Axioma
    """

    # Get all the factor returns for the given model.
    result          = None
    conn            = Database.AccessReference(sql_host = MasterConfig.MasterConfig['prod']['sql_source_host'])
    factor_returns  = conn.get_factor_returns(start_date = df.index.min(), end_date = df.index.max(), axioma_model = axioma_model) \
        .drop(columns = ['date_modified', 'date_created'])
    
    if regression_type == 'lasso' :
        model       = LM.Lasso(alpha = lasso_alpha)
        y           = df
        x           = factor_returns
        result      = model.fit(x, y)

    if regression_type == 'OLS' :
        y           = df
        x           = factor_returns
        x           = sm.add_constant(x)  # to compute intercept
        model       = smf.OLS(y,x)
        result      = model.fit()

    return (model, result, x, y, factor_returns)


def get_test_data_() :
    df              = pd.read_csv(io.StringIO(test_data))
    df['data_date'] = df['data_date'].astype('datetime64[ns]')
    df              = df.set_index('data_date')

    return df


def run_sample_() :
    """
    Helper test function for compute regression
    """
    df              = td()
    # stats           = compute_regression(df, 'lasso', 0)
    stats           = compute_regression(df, 'lasso', 17)
    # print(stats)

    return stats

#  This is the portfolio return series from Jan to Mid June 2018
test_data = """ 
data_date,pnl
2018-01-02,-0.0002
2018-01-03,-0.0001
2018-01-04,0.0002
2018-01-05,0.0005
2018-01-08,0.0015
2018-01-09,0.0009
2018-01-10,-0.0073
2018-01-11,-0.003413
2018-01-12,0.000705
2018-01-16,0.014306
2018-01-17,-0.003179
2018-01-18,-0.001517
2018-01-19,-0.000338
2018-01-22,-0.004373
2018-01-23,-0.001566
2018-01-24,-9.6e-05
2018-01-25,0.004693
2018-01-26,-0.003513
2018-01-29,0.00125
2018-01-30,0.004864
2018-01-31,0.004911
2018-02-01,0.001331
2018-02-02,-0.000203
2018-02-05,-0.001459
2018-02-06,-0.007479
2018-02-07,-0.009407
2018-02-08,-0.00952
2018-02-09,0.006159
2018-02-12,0.005007
2018-02-13,-0.004686
2018-02-14,-0.012949
2018-02-15,0.002516
2018-02-16,0.008147
2018-02-20,-0.003895
2018-02-21,-0.000513
2018-02-22,-0.005288
2018-02-23,-0.007818
2018-02-26,-0.007322
2018-02-27,-9.5e-05
2018-02-28,-0.005327
2018-03-01,-0.010853
2018-03-02,-0.012037
2018-03-05,0.00315
2018-03-06,0.00606
2018-03-07,0.00596
2018-03-08,-0.002082
2018-03-09,0.006175
2018-03-12,-0.002983
2018-03-13,0.003443
2018-03-14,-0.001486
2018-03-15,0.005226
2018-03-16,0.003883
2018-03-19,0.005762
2018-03-20,0.004039
2018-03-21,-0.011526
2018-03-22,-0.000149
2018-03-23,-0.007282
2018-03-26,0.004912
2018-03-27,0.009718
2018-03-28,0.006341
2018-03-29,-0.001519
2018-04-02,-0.000791
2018-04-03,-0.000216
2018-04-04,-0.006739
2018-04-05,-0.001231
2018-04-06,-0.002207
2018-04-09,0.004358
2018-04-10,-0.010328
2018-04-11,-0.007997
2018-04-12,-0.009012
2018-04-13,-0.003069
2018-04-16,0.010497
2018-04-17,0.001246
2018-04-18,0.003742
2018-04-19,-0.006567
2018-04-20,0.000535
2018-04-23,0.005937
2018-04-24,-0.00733
2018-04-25,-0.004085
2018-04-26,0.013259
2018-04-27,0.000272
2018-04-30,-0.000435
2018-05-01,-0.002231
2018-05-02,-0.009143
2018-05-03,-0.002055
2018-05-04,0.001399
2018-05-07,-0.007555
2018-05-08,-0.005837
2018-05-09,0.001622
2018-05-10,-0.005636
2018-05-11,0.00241
2018-05-14,-0.002954
2018-05-15,0.002375
2018-05-16,-0.00091
2018-05-17,-0.001999
2018-05-18,0.008037
2018-05-21,0.004049
2018-05-22,-0.000247
2018-05-23,0.00436
2018-05-24,0.000937
2018-05-25,0.00013
2018-05-29,-0.003824
2018-05-30,-0.000314
2018-05-31,-0.003006
2018-06-01,0.005443
2018-06-04,-0.000525
2018-06-05,-0.00034
2018-06-06,0.000917
2018-06-07,-0.004371
2018-06-08,-0.000106
2018-06-11,-0.000624
2018-06-12,5.2e-05
2018-06-13,-0.001259
2018-06-14,0.00337
2018-06-15,-0.001173
2018-06-18,-0.004916
2018-06-19,-0.005479
2018-06-20,-0.00629
2018-06-21,0.001364
2018-06-22,-0.001697
"""
