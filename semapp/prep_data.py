import sys,os
import numpy as np
import pandas as pd
import datetime,time
from pandas.tseries.offsets import BDay
import scipy.stats

DataDir = 'semapp/data'

EnterLong = 0.58
EnterShort = 0.42


def trading_create_dashboard_data():
    ah = pd.read_hdf(os.path.join(DataDir,'account_history.hdf'),'table')
    ah['Portfolio_daily_return'] = ah.PnlReturn
    ah['Portfolio_equity_curve'] = (1+ah.CumPnl)

    benchmarks = [('SP500','S&P5'),('SP400','SPMC'),('SP600','S&P6')]

    for b,m_ticker in benchmarks:
        b_data = pd.read_hdf(os.path.join(DataDir,b+'.hdf'),'table')
        ah[b+'_daily_return'] = ah.TradeDate.map(b_data.adj_close.pct_change())
        ah[b+'_equity_curve'] = (1+ah[b+'_daily_return']).cumprod()

    stats_cols = ['Portfolio'] + [x[0] for x in benchmarks]
    stats = pd.DataFrame(columns = stats_cols)

    for c in stats_cols:
        daily_ret = ah[c+'_daily_return'] 
        stats.loc['Cumulative Return (bps)',c] = "{0:.0f}".format((ah[c+'_equity_curve'].iloc[-1]-1) * 10000)
        stats.loc['Winning Days (%)',c] = "{0:.0%}".format((daily_ret >0).mean())
        stats.loc['Min Return (bps)',c] = "{0:.0f}".format(daily_ret.min() * 10000)
        stats.loc['Max Return (bps)',c] = "{0:.0f}".format(daily_ret.max() * 10000)
        stats.loc['Mean Return (bps)',c] = "{0:.0f}".format(daily_ret.mean() * 10000)
        stats.loc['Std Dev Return (bps)',c] = "{0:.0f}".format(daily_ret.std() * 10000)
        stats.loc['Skew',c] = "{0:.1f}".format(scipy.stats.skew(daily_ret))
        stats.loc['Kurtosis',c] = "{0:.1f}".format(scipy.stats.kurtosis(daily_ret))
        stats.loc['Volatility - Annualized (%)',c] = "{0:.1%}".format(np.sqrt(252) * daily_ret.std() )
        stats.loc['Sharpe - Annualized',c] = "{0:.1f}".format(np.sqrt(252) * daily_ret.mean() / daily_ret.std())
        stats.loc['Sortino - Annualized',c] = "{0:.1f}".format(np.sqrt(252) * daily_ret.mean() / daily_ret.clip(upper=0).std())
        drawdown_series,max_drawdown,drawdown_dur = create_drawdowns(ah[c+'_equity_curve'])
        stats.loc['Max Drawdown (bps)',c] = "{0:.0f}".format(max_drawdown * 10000)
        stats.loc['Max Drawdown Days',c] = "{0:.0f}".format(drawdown_dur)
    stats.index.name = 'Metric'

    return (ah,stats)

def trading_create_exposure_data():
    ## ticker matching doesn't work well. Needs to be converted to CUSIP
    pos = pd.read_hdf(os.path.join(DataDir,'nav_portfolio.hdf'),'table')
    pos.Symbol = pos.Symbol.str.replace(' US','')

    sm = pd.read_hdf(os.path.join(DataDir,'sec_master.hdf'),'table')
    sm.ticker = sm.ticker.str.replace('.','/')

    pos = pos.merge(sm, left_on='Symbol',right_on='ticker',how='left')
    daily_nav = pos.groupby('TradeDate').MarketValueBase.sum()

    pos['nav'] = pos.TradeDate.map(daily_nav)

    #######NEED TO FIX CASH ############
    pos['weight'] = pos.MarketValueBase / pos.nav
    pos['weight_abs'] = pos.weight.abs()

    gross_ind = pos.groupby(['TradeDate','zacks_x_sector_desc','zacks_m_ind_desc']).weight_abs.sum().to_frame('Gross')
    net_ind = pos.groupby(['TradeDate','zacks_x_sector_desc','zacks_m_ind_desc']).weight.sum().to_frame('Net_unadj')
    net_ind = net_ind.join(gross_ind)
    net_ind['Net'] = net_ind['Net_unadj'] / net_ind['Gross']
    net_ind['Net - 1wk delta'] = net_ind.groupby(level=['zacks_x_sector_desc','zacks_m_ind_desc'])['Net'].diff(5)
    net_ind['Net - 1mo delta'] = net_ind.groupby(level=['zacks_x_sector_desc','zacks_m_ind_desc'])['Net'].diff(20)
    net_ind.reset_index(level = ['zacks_x_sector_desc','zacks_m_ind_desc'], drop=False, inplace=True)

    gross_sec = pos.groupby(['TradeDate','zacks_x_sector_desc']).weight_abs.sum().to_frame('Gross')
    net_sec = pos.groupby(['TradeDate','zacks_x_sector_desc']).weight.sum().to_frame('Net_unadj')
    net_sec = net_sec.join(gross_sec)
    net_sec['Net'] = net_sec['Net_unadj'] / net_sec['Gross']
    net_sec['Net - 1wk delta'] = net_sec.groupby(level=['zacks_x_sector_desc'])['Net'].diff(5)
    net_sec['Net - 1mo delta'] = net_sec.groupby(level=['zacks_x_sector_desc'])['Net'].diff(20)
    net_sec.reset_index(level = ['zacks_x_sector_desc'], drop=False, inplace=True)
    net_sec['zacks_m_ind_desc'] ='All'

    max_date = pos.TradeDate.max()

    exposures = pd.concat([net_ind.loc[max_date],net_sec.loc[max_date]],ignore_index=True)
    exposures = exposures.drop('Net_unadj',axis=1)
    
    return (exposures)

def create_drawdowns(returns):
    # Calculate the cumulative returns curve
    # and set up the High Water Mark
    hwm = [0]

    # Create the drawdown and duration series
    idx = returns.index
    drawdown = pd.Series(index=idx)
    duration = pd.Series(index=idx)

    # Loop over the index range
    for t in range(1, len(idx)):
        hwm.append(max(hwm[t - 1], returns.ix[t]))
        drawdown.ix[t] = (hwm[t] - returns.ix[t]) / hwm[t]
        duration.ix[t] = (0 if drawdown.ix[t] == 0 else duration.ix[t - 1] + 1)

    return drawdown, drawdown.max(), duration.max()

def get_insider_transactions_latest_filings():
    filepath = os.path.join(DataDir,'sec_forms_ownership_source.hdf')
    # find max date in file
    start = (datetime.datetime.now() - BDay(5)).strftime('%Y-%m-%d')

    max_date = pd.read_hdf(filepath,'table',where='FilingDate > "%s"'%start,columns=['FilingDate'])['FilingDate'].max()
    max_date = max_date.strftime('%Y-%m-%d')
    forms = pd.read_hdf(filepath,'table',where='FilingDate == "%s"'%max_date)

    # download securities master and merge
    sm = pd.read_hdf(os.path.join(DataDir,'sec_master.hdf'),'table')
    forms = forms.merge(sm,left_on='IssuerCIK',right_on='comp_cik',how='right')
    forms = forms[forms.ticker.notnull() & forms.TransType.notnull()]
    forms = forms[~forms.TransType.isin(['LDG','HO','RB'])]
    #signal_data['AcceptedDate'] = pd.to_datetime(signal_data['AcceptedDate'])

    forms.sort_values('AcceptedDate', ascending=False, inplace=True)
    
    return (forms)

def get_insider_transactions_ticker_data(ticker):
    ## find cik
    sm = pd.read_hdf(os.path.join(DataDir,'sec_master.hdf'),'table')
    sm = sm[sm.ticker==ticker]
    if len(sm)==1:
        cik = sm.iloc[0].comp_cik
        m_ticker = sm.iloc[0].m_ticker
        sec_id = sm.index[0]
    else:
        return (pd.DataFrame(),pd.DataFrame(),None)

    # get cik forms
    filepath = os.path.join(DataDir,'sec_forms_ownership_source.hdf')
    forms = pd.read_hdf(filepath,'table',where='IssuerCIK == "%s"'%cik)

    forms = forms.merge(sm, left_on='IssuerCIK', right_on = 'comp_cik',how='left')
    forms.sort_values('AcceptedDate', ascending=False, inplace=True)
    forms = forms[(forms.valid_purchase + forms.valid_sale)!=0]
    forms['SignalDirection'] = 'LONG'
    forms['SignalDirection'] = forms.SignalDirection.where(forms.valid_purchase,'SHORT')
    forms = forms[~forms.TransType.isin(['LDG','HO','RB'])]

    #get stock prices
    filepath = os.path.join(DataDir,'qm_eod_source.hdf')
    prices = pd.read_hdf(filepath,'table',where='sec_id=="%s"'%sec_id,columns=['data_date','adj_close'])
    prices.set_index('data_date',inplace=True)

    return(forms,prices,sm.iloc[0])
    
def get_latest_equities_signals():

    filepath = os.path.join(DataDir,'equities_signals.hdf')

    # find max date in file
    start = (datetime.datetime.now() - BDay(5)).strftime('%Y-%m-%d')
    max_date = pd.read_hdf(filepath,'table',where='data_date > "%s"'%start,columns=['data_date'])['data_date'].max()
    max_date = max_date.strftime('%Y-%m-%d')
    signal_data = pd.read_hdf(filepath,'table',where='data_date == "%s"'%max_date)

    signal_data['SignalDirection'] = signal_data.SignalConfidence.apply(lambda x: 'Long' if x >= EnterLong else 'Short' if x <= EnterShort else 'Neutral')

    return(signal_data)

def get_equities_signal_ticker_data(ticker): 
    ticker = ticker.upper()
    signal_data_columns = ['data_date','market_cap','ticker','volume','zacks_x_sector_desc','zacks_m_ind_desc','close','adj_close','SignalConfidence']

    sql = Access_SQL_DB(MySQL_Server,db='equity_models')
    signals = Table('signals_daily_2017_07_01', sql.META, autoload=True)
    query = select([signals.c[x] for x in signal_data_columns]).where(signals.c.ticker ==ticker) 

    st_df = pd.read_sql_query(query, sql.ENGINE, index_col=None, parse_dates=['data_date']).sort_index()

    ## Check if stacked signal data exists
    if (not(len(st_df))):
        return (render,'site_app/ticker_not_found.html',{'ticker':ticker})


    st_df['SignalDirection'] = st_df.SignalConfidence.apply(lambda x: None if pd.isnull(x) else 'Long' if x >= EnterLong else 'Short' if x <= EnterShort else 'Neutral')
    st_df.zacks_m_ind_desc = st_df.zacks_m_ind_desc.astype(str).map(lambda x: x.title())

    ## add some info to st_df
    st_df['volume_sma30'] = pd.rolling_mean(st_df.volume,30)
    st_df['daily_average_trading_value'] = st_df['volume_sma30'] * st_df.close

    ## sort and reset index 
    st_df.sort_values('data_date', ascending=True, inplace=True)
    st_df.set_index('data_date',inplace = True) 

    ## latest signal 
    st_df_f = st_df[st_df.SignalDirection.notnull()]
    latest_signal = st_df_f.SignalDirection.iloc[-1]
    latest_signal_date = st_df_f.index[-1].strftime('%m/%d/%Y')

    st_df['data_date'] = st_df.index
    st_df.reset_index(inplace = True,drop=True)

    #convert to JSON for exchange with JS
    chart_data = st_df.to_json(orient='records', date_format='iso') 

    
    context = {'ticker':ticker,
               'latest_bar':st_df.iloc[-1].to_dict(),
               'chart_data':chart_data,
               'latest_signal':latest_signal,
               'latest_signal_date':latest_signal_date}


if __name__ == '__main__':
    trading_create_dashboard_data()
    exposures = trading_create_exposure_data()

