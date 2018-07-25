import argparse
import logging
import numpy as np
import pandas as pd

import semutils.db_access.AccessReference   as Database
import semutils.db_access.MasterConfig      as MasterConfig

# The number of days to skip because trading to get in and out of the position takes time.
trade_period    = 1

# Upper and lower bounds on beta
min_beta        = -2.5
max_beta        = 2.5
srp             = 'daily_return_over_rfr_3mo' # Security risk premium   (SRP)
RFR             = 'daily_rfr_3mo'             # Risk free rate          (RFR)

index_mapping   = {
    'MID'       : 'SP400',
    'SP50'      : 'SP500',
    'SML'       : 'SP600',
    'R.1000'    : 'Russell1000',
    'R.2000'    : 'Russell2000',
    'R.3000'    : 'Russell3000'
}

test_ids            = ['S0000181','S000443D']               # AAPL, MSFT
test_ids_2          = test_ids + ['S00034D2', 'S0003221']   # INTC, IBM


###############################################################################
#
###############################################################################    
def compute_metrics(conn = None, sec_ids = None, beta_indexes = ['Russell3000'], beta_windows = [252], 
    windows = [63], metrics = ['alpha'], start_date = pd.Timestamp.min, end_date = pd.Timestamp.max, axioma_model = 'sh') :
    """
    compute_metrics : returns a data frame index by sec_id, data_date with columns for output metrics.

        conn        : A connection to the reference database.
          Default   : None - Create a connection to the database using environment settings.

        sec_ids     : list of identifiers to compute metrics for.  
          Default   : None - All securities with prices.

        beta_indexes : list of index names to use for betas. 
          Default   : ['Russell3000']
          Possible Values : 
              'SP400'
              'SP500'
              'SP600'
              'Russell1000'
              'Russell2000'
              'Russell3000'

        beta_windows : list of integers representing windows to use for beta calculations. 
          Default   : [252]

        windows     : list of integers representing trading window to use. 
          Default   : [63]

        metrics     : Output Metric. 
          Default   : ['alpha']
          Possible Values :
              'abs' - Absolute returns
              'rel' - Relative returns
              'car' - Cumulative abnormal returns
              'spc' - Specific returns
              'spc_basic' - Accumulating specific return
              'alpha' - Alpha returns

        axioma_model : If a spc or spc_basic metric is specified, then axioma_model specifies which model to use. Note case-sensitive.
            'sh'    - Short term and medium term momentum model
            'mh'    - Medium term momentum model only.
            'shs'   - Short term and medium term statistical model

        start_date  : The first date.  If specified, price history will start at 
            (start_date - max(window + beta_windows)) to accommodate historical and forward rolling 
            calculations.
          Default   : pd.NaT - All days before the end_date with prices

        end_date    : The last date.
          Default   : pd.NaT - All days after the start date with prices

    Sample :
         compute_metrics(sec_ids = ['S00034D2', 'S0003221'], beta_indexes = ['SP500'], metrics = ['abs'])         
    """

    # Create a connection if user didn't provide one.
    close_connection = False
    if conn == None :
        server      = MasterConfig.MasterConfig['prod']['sql_source_host']
        conn        = Database.AccessReference(sql_host = server)
        close_connection = True 

    data_start_date = compute_data_start_date(start_date, windows, beta_windows)
    df              = get_reference_data(conn, sec_ids, metrics, beta_indexes, data_start_date, end_date) 
    

    # Get the axioma specific return if spc or spc_basic is specified.
    if 'spc' in metrics or 'spc_basic' in metrics :
        spr         = conn.get_beta_risk(sec_ids = sec_ids, start_date = data_start_date, end_date = end_date, columns = ['Specific_Return', 'data_date', 'sec_id'], axioma_model = axioma_model) \
            .fillna(0) \
            .reset_index()
        spr['Specific_Return'] = spr['Specific_Return'] / 100.0
        df          = df.merge(spr, on = ['data_date', 'sec_id'], how = 'left')

    # Compute the basic metrics.
    df              = df.groupby('sec_id') \
        .apply(lambda x : compute_metrics_one_sec_id(x, beta_indexes, beta_windows, windows, metrics, axioma_model))

    # Compute the complex complete spc metric 
    if 'spc' in metrics :
        spc         = spc_data_prep_and_compute(conn, sec_ids, data_start_date, end_date, windows, axioma_model)        
        df          = df.merge(spc, how = 'left', on = ['sec_id','data_date'])  

    # Drop compute values that occur before the start date for the sake of rolling windows history
    if start_date != pd.Timestamp.min :
        df          = df[df.data_date >= start_date]
    df              = df.set_index(['sec_id','data_date'])
    df.sort_index(inplace = True)

    if close_connection :
        conn.close_connection()

    return df


###############################################################################
def compute_data_start_date(start_date, windows, beta_windows) :
    """
    The pricing data needs to stretch back from the start date to accommodate 
    rolling forward and historical beta values.  Pad an extra 5 trade days 
    for extra margin to account for possible weekends and holidays    
    """

    data_start_date = start_date
    if data_start_date != pd.Timestamp.min :
        look_back_days  = np.max(windows)

        if beta_windows is not None and len(beta_windows) > 0 :
            look_back_days  += np.max(beta_windows)

        look_back_days  = (int(look_back_days) * 365 / 252) + 5 
        data_start_date -= pd.Timedelta(days = look_back_days) 

    return data_start_date


###############################################################################
def spc_data_prep_and_compute(conn, sec_ids, data_start_date, end_date, windows, axioma_model) :
    """    
    Gather each factor exposure, factor exposure return and security return per day and 
    then roll it up for each window. 

    All the cum_* data frames store a (1 + cummulative return) data series so that returns 
    for any period can be computed by shifting the data frame

    The reason spc is broken out seperately is because of the amount of intermediate columns 
    that are generated and computed for spc makes it hard to clean up after if they were 
    all placed into the primary df data frame.  New intermediate data frames are created 
    and only the final result of the SPC metric is stored in the primary df.
    """
    if axioma_model == 'mh' :
        table_name = 'axioma_security'
    else :
        table_name = 'axioma_security_' + axioma_model

    axioma_rfr      = get_axioma_risk_free_rate(conn)
    exp_ret         = get_security_exposure_returns(conn, sec_ids, data_start_date, end_date, axioma_model).reset_index()
    sec_ret         = conn \
        .get_security_data(sec_ids, None, None, data_start_date, end_date, ['DayReturn'], table_name) \
        .reset_index()    
   
    daily_returns   = exp_ret \
        .merge(sec_ret, on = ['sec_id','data_date'], how = 'inner') \
        .merge(axioma_rfr, on = ['data_date'], how = 'inner')

    spc             = daily_returns \
        .groupby('sec_id') \
        .apply(lambda x : compute_spc_returns(x, windows))

    return spc


###############################################################################
def compute_spc_returns(df, windows) : 
    cum_returns     = (df.drop(columns = ['sec_id','data_date']) + 1).cumprod()
    x               = df[['sec_id','data_date']]
    
    for w in windows :
        spc         = 'spc_{0}day'.format(w)
        fspc        = 'F_{0}'.format(spc)
        window_return = ((cum_returns / cum_returns.shift(w)) - 1)
        rfr_and_factor_returns = window_return.sum(axis = 1) - window_return['DayReturn']
        x[spc]      = window_return['DayReturn'] - rfr_and_factor_returns 
        x[fspc]     = x[spc].shift(-trade_period-w)  

        # For debugging
        # x[spc + '_cum_day_ret']   = window_return['DayReturn']
        # x[spc + '_cum_rfr']       = window_return[RFR]
        # x[spc + '_cum_fac_ret']   = window_return.sum(axis = 1) - window_return['DayReturn'] - window_return[RFR]

    return x


###############################################################################
def compute_metrics_one_sec_id(df, beta_indexes, beta_windows, windows, metrics, axioma_model) :
    """
    abs, rel, car and alpha are compute ed here. spc returns are compute seperately due to the additional complexity of exposures
    """
    df              = df.sort_values('data_date')

    if 'abs' in metrics :
        df          = compute_abs_returns(df, windows)

    if 'rel' in metrics :
        df          = compute_rel_returns(df, beta_indexes, windows)

    if 'spc_basic' in metrics :
        df          = compute_spc_basic_returns(df, windows, axioma_model)

    if 'car' in metrics :
        df          = compute_car_returns(df, beta_indexes, beta_windows, windows)    

    if 'alpha' in metrics :
        df          = compute_alpha_returns(df, beta_indexes, beta_windows, windows)        

    return df


###############################################################################
def compute_abs_returns(df, windows):
    """
    df must have adj_close column
    """
    for w in windows:
        far         = 'F_abs_ret_{0}day'.format(w)
        df[far]     = df.adj_close.pct_change(w).shift(-trade_period-w)

    return df


###############################################################################
def compute_spc_basic_returns(df, windows, axioma_model) :
    """
    df must have Specific_Return column
    """
    for w in windows:
        spc         = 'spc_basic_ret_{0}day'.format(w)
        fspc        = 'F_spc_basic_ret_{0}day'.format(w)

        df[spc]     = df['Specific_Return'].rolling(w).sum()
        df[fspc]    = df[spc].shift(-trade_period-w)

    return df


###############################################################################
def compute_rel_returns(df, beta_indexes, windows) :
    """
    Historical and future relative returns (rel)
    df must have index price columns for each beta_indexes
    """
    for w in windows :
        for index in beta_indexes :
            rr          = '{0}_rel_ret_{1}day'.format(index,w)
            frr         = 'F_{0}_rel_ret_{1}day'.format(index, w)

            df[rr]      = df.adj_close.pct_change(w) - df[index].pct_change(w)
            df[frr]     = df[rr].shift(-trade_period-w)

    return df


###############################################################################
def compute_car_returns(df, beta_indexes, beta_windows, windows) :
    """
    CAR (Cummulative Abnormal Return) 
        Cummulate 1 day alpha over different windows
    """

    # Compute the 1 day alpha first
    df = compute_alpha_returns(df, beta_indexes, beta_windows, windows = [1])

    for w in windows:
        for bw in beta_windows : 
            for index in beta_indexes :            
                car         = '{0}_car_ret_{1}day'.format(index,w)
                fcar        = 'F_{0}_car_ret_{1}day'.format(index, w)
                alpha       = '{0}_alpha_{1}day_{2}beta'.format(index, 1, bw)

                df[car]     = df[alpha].rolling(w).sum()
                df[fcar]    = df[car].shift(-trade_period-w)

    return df


###############################################################################
def compute_alpha_returns(df, beta_indexes, beta_windows, windows) :
    # Compute beta adjusted future returns based on different betas.

    df[srp]         = df['daily_return'] - df[RFR]
    cum_rfr         = (df[RFR] + 1).cumprod()    

    for index in beta_indexes :
        # Calculate Market Risk Premium (MRP) - index risk adjusted daily returns
        mrp         = '{0}_mrp'.format(index)
        df[mrp]     = df[index].pct_change() - df[RFR]

        # Compute different period betas.  
        for bw in beta_windows :
            beta    = '{0}_beta_{1}day'.format(index, bw)
            r2      = '{0}_beta_R2_{1}day'.format(index, bw)
            df[beta] = (df[srp].rolling(bw).cov(df[mrp]) / df[mrp].rolling(bw).var()).clip(min_beta, max_beta)
            df[r2]  = (df[srp].rolling(bw).corr(df[mrp]))**2
        
            for w in windows :
                # Historical and future alpha for different betas        
                beta        = '{0}_beta_{1}day'.format(index, bw)
                alpha       = '{0}_alpha_{1}day_{2}beta'.format(index, w, bw)
                fa          = 'F_{0}_alpha_{1}day_{2}beta'.format(index, w, bw)
               
                # Security Expected Return (ser)
                window_rfr  = (cum_rfr / cum_rfr.shift(w)) - 1

                ser         = (df.adj_close.pct_change(w) - window_rfr)
                # Market Expected Return (mer)
                mer         = df[beta] * (df[index].pct_change(w) - window_rfr)
                # Alpha is the security return 
                df[alpha]   = ser - mer
                df[fa]      = df[alpha].shift(-trade_period-w)                

    return df


###############################################################################
def get_reference_data(conn, sec_ids = None, metrics = ['alpha'], beta_indexes = ['Russell3000']
    , start_date = pd.Timestamp.min, end_date = pd.Timestamp.max) :

    df_rfr          = get_risk_free_rate(conn)
    indices         = get_index_prices(conn, beta_indexes)
    prices          = get_prices(conn, sec_ids, start_date, end_date)

    indices         = indices.merge(df_rfr, on = 'data_date', how = 'left') \
        .fillna(method='ffill')

    reference       = prices.merge(indices, on = 'data_date', how = 'inner')

    return reference


###############################################################################
def get_risk_free_rate(conn) :
    """
    3 month treasury rates (as percentages)
    """

    # convert to decimal percentage and then to a daily rate.
    # NMT FIX - need to test.
    df              = ((conn.get_time_series('DTB3', 'FRED') / 100.0 + 1) ** (1/252)) - 1
    df              = df.reset_index().rename(columns = {'Value' : RFR})

    return df


###############################################################################
def get_axioma_risk_free_rate(conn) :
    """
    Get the USD risk free rate provided by Axioma and converted it into 
    a daily risk free rate assuming a 252 trading data calendar.
    """

    query           = """
        select 
            data_date, 
            Risk_Free_Rate 
        from 
            axioma_currency 
        where 
            currencycode = 'USD' 
        order by 
            data_date
    """

    df              = pd.read_sql_query(query, conn.sql.CONN)
    df['Risk_Free_Rate'] = df['Risk_Free_Rate'].astype('float32')
    df[RFR]         = (1 + df['Risk_Free_Rate']) ** (1.0/252.0) - 1
    df.drop(columns = ['Risk_Free_Rate'], inplace = True)

    return df
    

###############################################################################
def get_index_prices(conn, beta_indexes) :

    df = conn.get_index_prices() \
        .reset_index() \
        .pivot(index = 'data_date', columns = 'BENCHMARK_ID', values = 'IDX_PRICE') \
        .rename(columns = index_mapping) \
        [beta_indexes] \
        .reset_index()

    return df


###############################################################################
def get_prices(conn, sec_ids = None, start_date = pd.Timestamp.min, end_date = pd.Timestamp.max, source = 'database') :
    df              = None
    price_columns   = ['sec_id', 'data_date', 'daily_return', 'adj_close']
    
    if source == 'database' :
        df          = conn.get_daily_prices(sec_ids = sec_ids, columns = price_columns, start_date = start_date, end_date = end_date)

    elif source == 'file cache' :
        try : 
            import reference.common.FileCache as FileCache
            cache   = FileCache.Cache()
            cache.set_previous_tradeday()
            df      = cache.get('price', columns = price_columns)
            if df is not None and sec_ids is not None :
                df  = df[df['sec_id'].isin(sec_ids)]
            df      = df[df.data_date >= start_date]
            df      = df[df.data_date <= end_date]
        except :
            df      = None

    return df.reset_index()


###############################################################################
def get_security_exposure_returns(conn, sec_ids, start_date, end_date, axioma_model) :
    """
    """
    expo            = conn \
        .get_exp(sec_ids = sec_ids, start_date = start_date, end_date = end_date, axioma_model = axioma_model) \
        .drop(columns = ['date_modified', 'date_created'])
        
    factor_returns  = conn \
        .get_factor_returns(start_date = start_date, end_date = end_date, axioma_model = axioma_model) \
        .drop(columns = ['date_modified', 'date_created'])

    df              = expo.groupby('sec_id').apply(lambda x : compute_security_exposure_returns(x, factor_returns))

    return df


###############################################################################
def compute_security_exposure_returns(exposures, factor_returns) :
    """
    Computes
    """   
    exposures       = exposures.reset_index().sort_values('data_date').set_index('data_date')
    (e1, r1)        = exposures.align(factor_returns, join = 'inner')

    # security factor returns
    df              = r1 * e1.shift(1)

    return df
