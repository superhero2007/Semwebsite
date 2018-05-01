import sys,os
import numpy as np
import pandas as pd
import datetime,time
import logging
import traceback

from semutils.logging import setup_logger
setup_logger('download_data.log')
from semutils.messaging import Slack
from semutils.db_access import Access_SQL_DB, Access_SQL_Source
from sqlalchemy import select,Table, Column
DataDir = 'data_prod'
RemoteDir = '/home/web/projects/semwebsite/semapp'

EnterLong = 0.55
EnterShort = 0.45

def download_sec_master_and_pricing():
    sql_source = Access_SQL_Source(os.environ.get('MySQL_Server'))

    #securities master
    logging.info('Downloading trading securities master')
    sm = sql_source.get_sec_master()
    sm.to_hdf(os.path.join(DataDir,'sec_master.hdf'),'table')

    #benchmarks 
    logging.info('Downloading benchmark data')
    benchmarks = [('SP500','S&P5'),('SP400','SPMC'),('SP600','S&P6')]
    for b,m_ticker in benchmarks:
        b_data = sql_source.get_source_eod_data(m_ticker = m_ticker,vendor='EODData')
        b_data.to_hdf(os.path.join(DataDir,b+'.hdf'),'table')

    #prices
    logging.info('Downloading pricing data')
    cols = ['sec_id','m_ticker','data_date','adj_close','close']
    pricesT = Table('eod_data_source', sql_source.META, autoload=True)
    filepath = os.path.join(DataDir,'qm_eod_source.hdf')

    if os.path.exists(filepath):
        prices = pd.read_hdf(filepath,'table')
        max_date = prices.data_date.max()
        df = pd.read_sql(select([pricesT.c[x] for x in cols]).where((pricesT.c.vendor_id==3)&(pricesT.c.data_data>max_date)),sql_source.CONN)
        prices = pd.concat([prices,df],ignore_index=True)
    else:
        prices = pd.read_sql(select([pricesT.c[x] for x in cols]).where((pricesT.c.vendor_id==3)),sql_source.CONN)

    prices = prices[prices.data_date >= '2003-01-01']
    prices.to_hdf(filepath,'table',format='table',data_columns=['data_date','sec_id'],mode='w')

    sql_source.close_connection()


def download_portfolio_data(): 
    sql_semoms = Access_SQL_DB(os.environ.get('MySQL_Server'),db='semoms')
    #account history
    logging.info('Downloading trading account history')
    ah = pd.read_sql_table('account_history',sql_semoms.CONN)
    ah.to_hdf(os.path.join(DataDir,'account_history.hdf'),'table')

    #account positions
    logging.info('Downloading trading account positions')
    pos = pd.read_sql_table('nav_portfolio',sql_semoms.CONN)
    pos.to_hdf(os.path.join(DataDir,'nav_portfolio.hdf'),'table')
    sql_semoms.close_connection()

def download_sec_ownership_data(): 
    sql_source = Access_SQL_Source(os.environ.get('MySQL_Server'))
    logging.info('Downloading sec_forms_ownership_source')
    cols = ['SECAccNumber','IssuerCIK','FilerCIK','URL','AcceptedDate','FilerName','InsiderTitle','Director','TenPercentOwner',
            'TransType','DollarValue','valid_purchase','valid_sale','FilingDate']
    formsT = Table('sec_forms_ownership_source', sql_source.META, autoload=True)
    filepath = os.path.join(DataDir,'sec_forms_ownership_source.hdf')

    if os.path.exists(filepath):
        forms = pd.read_hdf(filepath,'table')
        max_date = forms.FilingDate.max()
        df = pd.read_sql(select([formsT.c[x] for x in cols]).where(forms.c.FilingDate>max_date),sql_source.CONN)
        forms = pd.concat([forms,df],ignore_index=True)
    else:
        forms = pd.read_sql(select([formsT.c[x] for x in cols]),sql_source.CONN)

    forms.to_hdf(filepath,'table',format='table',data_columns=['IssuerCIK','FilingDate'],mode='w')
    sql_source.close_connect()

def download_equities_signal_data(): 
    sql_equities = Access_SQL_DB(os.environ.get('MySQL_Server'),db = 'equity_models')
    logging.info('Downloading equities_signal_data')
    # full signals file
    filepath_full = os.path.join(DataDir,'equities_signals_full.hdf')
    if os.path.exists(filepath_full):
        signalsT = Table('V_website',sql_equities.META,autoload=True)
        signals = pd.read_hdf(filepath_ful,'table',columns=['data_date'])
        max_date = signals.data_date.max()
        df = pd.read_sql(signalsT.select().where(signalsT.c.data_date>max_date),sql_equities.CONN)
        signals = pd.concat([signals,df],ignore_index=True)
    else:
        signals = pd.read_sql_table('V_website',sql_equities.CONN)

    signals['Long'] = (signals.SignalConfidence > EnterLong).astype(int)
    signals['Short'] = (signals.SignalConfidence < EnterShort).astype(int)
    signals['Neutral'] = 1-(signals['Long'] | signals['Short'])
    signals['SignalDirection'] = signals.apply(lambda x: 'Long' if x.Long==1 else 'Short' if x.Short==1 else 'Neutral',axis=1)
        
    signals.to_hdf(filepath_full,'table',format='table',data_columns=['data_date','ticker','zacks_x_sector_desc','zacks_m_ind_desc'],mode='w')
    max_date = signals.data_date.max()

    # write latest signal file
    filepath_latest = os.path.join(DataDir,'equities_signals_latest.hdf')
    latest = signals[signals.data_date == max_date]
    latest.to_hdf(filepath_latest,'table')
    
    # sec ind signals file
    filepath_sec_ind = os.path.join(DataDir,'equities_signals_sec_ind.hdf')
    
    ind = signals.groupby(['data_date','zacks_x_sector_desc','zacks_m_ind_desc']).sum()[['Long','Short','Neutral']]
    ind['Net'] = (ind['Long'] - ind['Short'] / (ind['Long']+ind['Short'])
    ind['Net - 1wk delta'] = ind.groupby(level=['zacks_x_sector_desc','zacks_m_ind_desc'])['Net'].diff(5)
    ind['Net - 1mo delta'] = ind.groupby(level=['zacks_x_sector_desc','zacks_m_ind_desc'])['Net'].diff(20)
    ind.reset_index(level = ['zacks_x_sector_desc','zacks_m_ind_desc'], drop=False, inplace=True)

    sec = signals.groupby(['data_date','zacks_x_sector_desc']).sum()[['Long','Short','Neutral']]
    sec['Net'] = (sec['Long'] - sec['Short']) / (sec['Long']+sec['Short'])
    sec['Net - 1wk delta'] = sec.groupby(level=['zacks_x_sector_desc'])['Net'].diff(5)
    sec['Net - 1mo delta'] = sec.groupby(level=['zacks_x_sector_desc'])['Net'].diff(20)

    sec.reset_index(level = ['zacks_x_sector_desc'], drop=False, inplace=True)
    sec['zacks_m_ind_desc'] ='All'

    sec_ind = pd.concat([ind.loc[max_date],sec.loc[max_date]],ignore_index=True)
    sec_ind = sec_ind.fillna(0)
    sec_ind.to_hdf(filepath_sec_ind,'table')
    sql_equities.close_connection()

def prep_correlation_data ():
    ### Unzip downloaded files
    dest = '/home/tony/projects/networks/datasets/sp500_minute_dataset.zip'
    zipfile = zp.ZipFile(dest, 'r')
    zipfile.extractall('/home/tony/projects/networks/datasets/')
    zipfile.close()

    x_list = []
    yz_list = []
    for year in [2018]:
        x_df = pd.read_hdf('/home/shared/test/vendor_data/axioma/2000_2018/' + str(year) + '/Composite-ETF-US_cst.hdf')
        y_df = pd.read_hdf('/home/shared/test/vendor_data/axioma/2000_2018/' + str(year) + '/Composite-ETF-US_idm.hdf').drop(labels=['Currency'], axis=1)
        z_df = pd.read_hdf('/home/shared/test/vendor_data/axioma/2000_2018/' + str(year) + '/Composite-ETF-US_att.hdf')

        yz_df = pd.merge(y_df, z_df, on=['data_date','AxiomaID'])
        
        x_list.append(x_df)
        yz_list.append(y_df)

    x_df = pd.concat(x_list, ignore_index=True)
    yz_df = pd.concat(yz_list, ignore_index=True)

    sp500_ax_list = x_df[(x_df['Composite AxiomaID']=='37P4NKR33') & (x_df['data_date']=='2018-03-26')]['Constituent AxiomaID'].tolist()

    ax_prices = pd.read_hdf('/home/shared/test/vendor_data/axioma/master.hdf',key='table')
    ax_prices.sort_values(by=['data_date','AxiomaID'], inplace=True)

    ax_prices = ax_prices[ax_prices.data_date=='2018-03-26'].copy()
    ax_prices = ax_prices[ax_prices.AxiomaID.isin(sp500_ax_list)].copy()

    ax_prices = ax_prices[ax_prices.AxiomaID.isin(sp500_ax_list)]
    # ax_prices.to_csv('./sp500_list_axioma.csv')
    # ax_prices = pd.read_csv('./sp500_list_axioma.csv').drop(labels=['Unnamed: 0'], axis=1)


    sp500_ticker_list = ax_prices['Ticker'].tolist()

    y_df = ax_prices[['Ticker','Company Name','Industry','Industry Group','Sector']].copy()
    y_df.rename(columns={'Ticker':'ticker','Company Name':'comp_name'}, inplace=True)

    y_df.to_csv('./correlation_network_files/node_info.csv', index=False)

    df = pd.read_csv('./datasets/dataset.csv', index_col=0, header=[0,1]).sort_index(axis=1).reset_index(drop=False)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index(keys=['timestamp'], drop=True, inplace=True)

    df = df.iloc[:,df.columns.get_level_values(1)=='close']
    df.columns = df.columns.droplevel(1)
    df.index.name = 'data_date'

    df.sort_index(inplace=True)
    df.fillna(method='pad', inplace=True)
    
    sp500_list = [i for i in sp500_ticker_list if i in df.columns.tolist()]
    df = df[sp500_list].copy()
    df.sort_index(inplace=True)

    max_date = df.index.max()
    max_date = max_date.replace(hour=0, minute=0)

    for aggregation in [1,5,15,30,60]:
        for lookback in [1,4,12]:
            if aggregation!=1:
                df = df.resample(str(aggregation)+'T').last()

            df.dropna(how='all', inplace=True)
            df.sort_index(inplace=True)

            df = df.pct_change()
            df = df[df.index>=max_date-pd.DateOffset(weeks=lookback)].copy()

            df_corrmat = df.corr()
            df_list = df_corrmat.unstack()

            df_list = pd.DataFrame(df_list, columns=['weight'])
            df_list.index.names = ['ticker1','ticker2']
            df_list = df_list.reset_index(drop=False)    

            df_list = df_list[df_list.weight!=1].copy()

            df_prices = pd.read_hdf('./datasets/price_data.hdf', key='table')
            df_prices = df_prices[df_prices.ticker.isin(sp500_ticker_list)][['ticker','data_date','adj_close']].copy()
            df_prices.sort_values(by=['ticker','data_date'], inplace=True)

            df_prices['adj_close_daily_return'] = df_prices.groupby('ticker')['adj_close'].pct_change()

            for i in [1,2,3,4,5]:
                df_prices['F_'+str(i)+'day_abs_return'] = df_prices.groupby('ticker')['adj_close'].pct_change(i).shift(-1-i)

            df_prices = df_prices[df_prices.data_date==max_date].drop(labels=['data_date','adj_close'], axis=1).reset_index(drop=True)

            new_df = pd.merge(df_list, df_prices, left_on='ticker1', right_on='ticker').drop(labels=['ticker'], axis=1)
            new_df.rename(columns={i:'comp1_'+i for i in new_df.filter(regex='F_').columns}, inplace=True)
            new_df.rename(columns={'adj_close_daily_return':'comp1_adj_close_daily_return'}, inplace=True)

            new_df = pd.merge(new_df, df_prices, left_on='ticker2', right_on='ticker').drop(labels=['ticker'], axis=1)
            new_df.rename(columns={i:'comp2_'+i for i in new_df.filter(regex='F_').columns if 'comp1_' not in i}, inplace=True)
            new_df.rename(columns={'adj_close_daily_return':'comp2_adj_close_daily_return'}, inplace=True)

            new_df['delta'] = new_df['comp1_adj_close_daily_return'] - new_df['comp2_adj_close_daily_return']

            if lookback==1:
                df_corrmat.to_csv('./correlation_network_files/corr_matrix_'+str(aggregation)+'minute_1week_lookback.csv')
                new_df.to_csv('./correlation_network_files/dislocations_'+str(aggregation)+'minute_1week_lookback.csv', index=False)
            elif lookback==4:
                df_corrmat.to_csv('./correlation_network_files/corr_matrix_'+str(aggregation)+'minute_1month_lookback.csv')
                new_df.to_csv('./correlation_network_files/dislocations_'+str(aggregation)+'minute_1month_lookback.csv', index=False)
            elif lookback==12:
                df_corrmat.to_csv('./correlation_network_files/corr_matrix_'+str(aggregation)+'minute_1qtr_lookback.csv')
                new_df.to_csv('./correlation_network_files/dislocations_'+str(aggregation)+'minute_1qtr_lookback.csv', index=False)

    return()
    
    
    
if __name__ == '__main__':
    functions = [download_sec_master_and_pricing, 
                 download_portfolio_data,
                 #download_sec_ownership_data, 
                 download_equities_signal_data]

    functions = []
    logging.info('Starting website data download')
    for func in functions:
        try:
           func()
        except:
            message = 'Website data update: Unable to complete %s function'%func.__name__
            logging.error(message)
            logging.error(traceback.format_exc())

            response = Slack().send_slack_message(post_to = 'productionissues', message=message,
                                                  post_as_username=os.path.basename(__file__))

    logging.info('Copying files to remote')
    os.system("gcloud compute copy-files %s --project website-200703 web@semwebserver:%s --zone us-central1-a"%(DataDir,RemoteDir))

