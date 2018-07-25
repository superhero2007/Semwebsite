

import math
import sys, getopt
import datetime
import time
import csv #import CSV Reading and Writing Module
import re # import regular expressions
import os
import itertools

from datetime import date

import pandas as pd
import numpy as np
import pandas.io.data


import math

USER = os.getlogin() # Set to User Apoorv's/Rajat's  settings

if (USER == 'Rajat' or USER == 'lalr'):
    #Rajat's Settings
    ROOT_DIR = r'C:\Users\Rajat\Documents\GitHub'
    TRANSACTION_DB_DIR = os.path.join(ROOT_DIR,'transaction_database')
    STOCKS_TO_PROCESS_FILE = os.path.join(ROOT_DIR,'insider_transactions','database','Russell 3000 Companies-withCIK.csv')
    HISTORICAL_STOCK_DATA_DIR = os.path.join(ROOT_DIR,'historical_stock_price_database')
    OUTPUT_DIR = os.path.join(ROOT_DIR,'output')
    LOG_FILE_DIR = os.path.join(ROOT_DIR,'log_files')
    SCRATCH_DIR = os.path.join(ROOT_DIR,'scratch_folder')
    EARNINGS_CALENDAR_FILE = os.path.join(ROOT_DIR,'insider_transactions','database','earnings_calendar.csv')
    QUANDL_AUTH_TOKEN = 'RLLwTQhz_ht6ag7jrAhC'
else:
    #Apoorv's Settings
    ROOT_DIR = r'C:\Users\Apoorv\Documents\Projects\Semanteon\Working GitHub Copy'
    TRANSACTION_DB_DIR = os.path.join(ROOT_DIR,'transaction_database')
    STOCKS_TO_PROCESS_FILE = os.path.join(ROOT_DIR,'database','Russell 3000 Companies-withCIK.csv') # TestList.csv - AKAM, 102StockList
    #STOCKS_TO_PROCESS_FILE = os.path.join(ROOT_DIR,'database','TestTWOU.csv') # TestList.csv - AKAM, 102StockList
    HISTORICAL_STOCK_DATA_DIR = os.path.join(ROOT_DIR,'historical_stock_price_database')
    OUTPUT_DIR = os.path.join(ROOT_DIR,'output')
    LOG_FILE_DIR = os.path.join(ROOT_DIR,'log_files')
    SCRATCH_DIR = os.path.join(ROOT_DIR,'scratch_folder')
    QUANDL_AUTH_TOKEN = 'xxx'
                       
if __name__ == '__main__':

    filename = 'All-transactions'
    data = pd.read_csv(os.path.join(OUTPUT_DIR,filename+'.csv'))

    columns_for_deletion = ['Unnamed: 0','FormType','FilingDate','FilerCIK','InsiderTitle',
                            'TransType','TransDateTo','TransPriceLow','TransPriceHigh',
                            'TotalHolding','OwnedDelta','TransactionCode','InconsistentEntry','Buy',
                            'URL','SECACCNumber','AcceptedDate']

    for column in columns_for_deletion:
        data.drop(column,axis = 1,inplace = True)

    print ('Mapping Tickers')
    columns_for_mapping = ['Ticker','FilerName']

    tickers = sorted (set (data['Ticker']))
    ticker_map = pd.DataFrame (index = tickers)
    for ticker in tickers:
        ticker_map.loc[ticker,'Map'] = 'T-'+str(ticker_map.index.searchsorted(ticker))

    data.insert(data.columns.get_loc('Ticker'),'TickerNew',None)
    data['TickerNew'] = data['Ticker'].apply(lambda x: ticker_map.loc[x,'Map'])


    print ('Mapping Insiders')
    
    
    insiders = sorted (set(data['FilerName']))
    insider_map = pd.DataFrame (index = insiders)
    for insider in insider_map.index:
        insider_map.loc[insider,'Map'] = 'F-'+str(insider_map.index.searchsorted(insider))

    data.insert(data.columns.get_loc('FilerName'),'FilerNameNew',None)
    data['FilerNameNew'] = data['FilerName'].apply(lambda x: insider_map.loc[x,'Map'])

    output_cols = ['1yr_abs_return',
    '1yr_rel_return', '1yr_abs_hit', '1yr_rel_hit', '2q_abs_return',
    '2q_rel_return', '2q_abs_hit', '2q_rel_hit',
    'max_abs_return_in_1yr', 'days_to_max_abs_return',
    'min_abs_return_in_1yr', 'days_to_min_abs_return',
    'max_rel_return_in_1yr', 'days_to_max_rel_return',
    'min_rel_return_in_1yr', 'days_to_min_rel_return', 'abs_hit_in_1yr',
    'abs_hit_date', 'days_to_abs_hit', 'rel_hit_in_1yr', 'rel_hit_date',
    'days_to_rel_hit']

    column_map = []
    output_counter = 1
    input_counter = 1
    for column in data.columns:
           if column in output_cols:
                column_map.append('O'+str(output_counter))
                output_counter += 1
           else:
                column_map.append('I'+str(input_counter))
                input_counter +=1
    column_map_df = pd.DataFrame(columns = data.columns, data = [column_map])

    print ('Writing mapping file')
    output_filename = filename + '-with_mapping.csv'
    column_map_df.to_csv (os.path.join(OUTPUT_DIR,output_filename))
    data.to_csv(os.path.join(OUTPUT_DIR,output_filename),mode='a',header=False)
                


    input_cols = [x for x in data.columns if x not in output_cols]

