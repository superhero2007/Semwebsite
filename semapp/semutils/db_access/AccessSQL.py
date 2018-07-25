import numpy as np
import pandas as pd
import os, sys
import datetime

from sqlalchemy import create_engine, Table, MetaData, select, Column, text, and_, update, bindparam
from sqlalchemy.dialects.mysql import FLOAT, INTEGER, DATETIME, BOOLEAN, VARCHAR, TIMESTAMP, BIGINT
from sqlalchemy import func as sqlalchemy_func

from collections import OrderedDict

import logging

class Access_SQL_DB(object):
    def __init__(self, host=None,user=os.environ.get('MySQL_UserName'),passwd=os.environ.get('MySQL_Password'),db=None,echo=False):
        self.host = host
        self.user = user
        self.password = passwd
        self.db = db
        self.echo = echo
        self.open_connection()

    def open_connection(self):
        self.ENGINE = create_engine('mysql+mysqldb://%s:%s@%s/%s?local_infile=1'%(self.user,self.password,self.host,self.db),echo=self.echo)
        self.CONN = self.ENGINE.connect()
        self.CONN.execute('set net_write_timeout = 600')
        self.CONN.execute('set net_read_timeout = 600')
        self.META = MetaData(bind=self.ENGINE)

    def close_connection (self):
        if not self.CONN.closed:
            self.CONN.close()
            self.ENGINE.dispose()

    def insert_to_db (self, df, table_name, include_index = False,chunksize=50000): # include index not yet built
        new_table = Table(table_name, self.META, autoload=True)

        splits = np.array_split(np.arange(len(df)), ((np.ceil(len(df)/chunksize)).astype(int)))

        logging.debug('<insert_to_db> %s total inserts of %s chunksize'%(len(splits),chunksize))

        counter = 1
        for split in splits:
            logging.debug('<insert_to_db> Prepping %s of %s chunks'%(counter, str(len(splits))))

            df_split = df.iloc[split]
            df_split = df_split.astype(object).where(pd.notnull(df_split), None)
            df_split_dict = df_split.to_dict(orient='records')

            logging.debug('<insert_to_db> Inserting %s of %s chunks'%(counter, str(len(splits))))

            #self.CONN.execute('set profiling = 1;')
            self.CONN.execute(new_table.insert(), df_split_dict)
            #logging.info (self.CONN.execute('show profiles;').fetchall())
            #logging.info (self.CONN.execute('show profile 2;').fetchall())

            counter +=1


    def update_db (self, df, table_name):
        table = Table(table_name, self.META, autoload=True)
        primary_key_cols = [i.key for i in table.columns if i.primary_key==True]

        if not set(primary_key_cols).issubset(df.columns):
            logging.info('DataFrame missing element of primary key')
            return()

        primary_key_obj = [i for i in table.columns if i.primary_key==True]

        df.dropna(subset=primary_key_cols, axis=0, how='any', inplace=True)
        if not len(df):
            logging.info('Cannot complete update - each primary key record has a null')
            return()

        if 'date_modified' in [i.key for i in table.columns]:
            df['date_modified'] = datetime.datetime.now()

        df.reset_index(drop=True, inplace=True)

        df_not_null = df.dropna(axis=1, how='any').copy()
        df_has_null = df[df.columns[df.isnull().any()].tolist() + primary_key_cols].copy()
            
        if len(df_not_null):
            value_dict = {i:bindparam(i) for i in df_not_null if i not in primary_key_cols}
            for col in primary_key_cols:
                df_not_null['b_'+col] = df_not_null[col]

            where_obj_list = []
            for col in primary_key_obj:
                where_obj_list.append(col==bindparam('b_'+col.key))

            where_stmt = and_(*where_obj_list)
            update_stmt = update(table).where(where_stmt).values(value_dict)
            update_data = df_not_null.to_dict('records')
            self.CONN.execute(update_stmt, update_data)

        if len(df_has_null):
            col_list = [i for i in df_has_null.columns if i not in primary_key_cols]
            for i in col_list:
                df_update = df_has_null[primary_key_cols + [i]].copy()
                df_update.dropna(inplace=True)

                if len(df_update):
                    value_dict = {i:bindparam(i) for i in df_update if i not in primary_key_cols}
                    for col in primary_key_cols:
                        df_update['b_'+col] = df_update[col]

                    where_obj_list = []
                    for col in primary_key_obj:
                        where_obj_list.append(col==bindparam('b_'+col.key))

                    where_stmt = and_(*where_obj_list)
                    update_stmt = update(table).where(where_stmt).values(value_dict)
                    update_data = df_update.to_dict('records')
                    self.CONN.execute(update_stmt, update_data)

        logging.info('Done updating table')


    def create_table (self, df, table_name, partition=False, n_partitions=25, primary_keys=[], partition_keys=[], column_index_keys=[], my_isam=False):
        if self.ENGINE.dialect.has_table(self.CONN,table_name):
            self.CONN.execute("""TRUNCATE """ + table_name + """;""")
            self.CONN.execute("""DROP TABLE """ + table_name + """;""")

        columns = []
        for c in df.columns:
            if df[c].dtype==object:
                dtype = VARCHAR(255)
            elif df[c].dtype in [int,'int64']:
                dtype = INTEGER
            elif df[c].dtype in ['int32','int8']:
                dtype = INTEGER
            elif df[c].dtype in ['float64','float32']:
                dtype = FLOAT
            elif df[c].dtype=='<M8[ns]':
                dtype = DATETIME
            elif df[c].dtype==bool:
                dtype = BOOLEAN
            elif df[c].dtype=='category':
                dtype = VARCHAR(255)
            else:
                raise Exception ('Unknown datatype. Not sure how to map')

            if c in primary_keys:
                columns.append(Column(c,dtype,primary_key=True,autoincrement=False))
            else:
                columns.append(Column(c,dtype,nullable=True))

        columns.append(Column('date_modified', TIMESTAMP, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'),nullable=False))
        columns.append(Column('date_created', TIMESTAMP,server_default = text('CURRENT_TIMESTAMP'),nullable=False))

        if my_isam:
            new_table = Table(table_name, self.META, *columns, mysql_engine='MyISAM')
        else:
            new_table = Table(table_name, self.META, *columns)
        new_table.create()

        for i in column_index_keys:
            self.CONN.execute("""ALTER TABLE """ + table_name + """ ADD INDEX """ + i + """_index""" + """(""" + i + """);""")

        if partition:
            self.CONN.execute("""ALTER TABLE """ + table_name + """ PARTITION BY KEY(""" + ','.join(partition_keys) + """) PARTITIONS """ + str(n_partitions) + """;""")


    def load_infile(self, df, table_name, tmp_dir, verbose = False):
        if verbose:
            logging.info('<load_infile> Pre-processing dataframe...')
        # preprocess
        if 'date_created' not in df.columns:
            df['date_created'] = datetime.datetime.now()
        if 'date_modified' not in df.columns:
            df['date_modified'] = datetime.datetime.now()

        # convert boolean columns to integers, otherwise the conversion to object complains
        bool_cols = df.dtypes[df.dtypes ==bool].index
        df[bool_cols] = df[bool_cols].astype(int)

        # df = df.astype(object).where(df.notnull(),'\\N')

        # write to csv
        logging.debug('Writing df to csv...')
        filename = os.path.join (tmp_dir,table_name + '_temp.csv')
        df.to_csv(filename, index=False, header=True, na_rep='\\N')

        col_string = '(' + ", ".join(df.columns.tolist()) + ')'

        # load csv to mysql
        logging.debug('Loading csv to db...')
        self.CONN.execute("LOAD DATA LOCAL INFILE '" + filename + "' INTO TABLE " + table_name + " FIELDS TERMINATED BY ',' IGNORE 1 LINES " + col_string + ";")
        logging.debug('Done with LOAD INFILE operations')


    def replace_active_table(self,new_table,active_table):
        retired_table = active_table+'_retired'
        if self.ENGINE.dialect.has_table(self.CONN,retired_table):
            self.CONN.execute('TRUNCATE %s;'%retired_table)
            self.CONN.execute('DROP TABLE %s;'%retired_table)

        if self.ENGINE.dialect.has_table(self.CONN,active_table):
            self.CONN.execute('RENAME TABLE %s TO %s, %s TO %s;'%(active_table,retired_table,new_table,active_table))
            self.CONN.execute('TRUNCATE %s;'%retired_table)
            self.CONN.execute('DROP TABLE %s;'%retired_table)
        else:
            self.CONN.execute('RENAME TABLE %s TO %s;'%(new_table,active_table))

    # def get_sec_master(self):
    #     return(pd.read_sql_table('V_sec_master',self.ENGINE,index_col='sec_id'))

    # def get_sec_master_US_active_NonOTC_CommonStock(self):
    #     df = self.get_sec_master()
    #     df = df[(df.exch_code=='US') & (df.is_figi_active==1) & (df.is_otc==0) & (df.security_typ=='Common Stock')]
    #     return(df)

    # def get_zacks_sec_ind_lookup(self):
    #     df = self.get_sec_master()
    #     df = df[['m_ticker','ticker','composite_id_bb_global','comp_cik','zacks_x_sector_code','zacks_x_sector_desc','zacks_m_ind_code',
    #              'zacks_m_ind_desc','zacks_x_ind_code','zacks_x_ind_desc']]
    #     df.reset_index(drop=False,inplace=True)
    #     return(df)

# class Access_SQL_Source(Access_SQL_DB):
#     def __init__(self, host=None, user=os.environ.get('MySQL_UserName'),passwd=os.environ.get('MySQL_Password'), echo=False):
#         self.host = host
#         self.user = user
#         self.password = passwd
#         self.db = 'source_tables'
#         self.echo=echo
#         self.open_connection()

#     def get_data_vendors(self):
#         return(pd.read_sql_table('data_vendors',self.ENGINE,index_col='id'))

#     def get_time_series(self,dataset = None, data_vendor = None, start_date=pd.NaT, end_date = pd.NaT):
#         if pd.isnull(dataset) or pd.isnull(data_vendor):
#             raise Exception ('No dataset defined or data_vendor defined')

#         time_series = Table('time_series',self.META,autoload=True)
#         time_series_data = Table('time_series_data',self.META,autoload=True)
#         data_vendors = Table('data_vendors',self.META,autoload=True)

#         joins = time_series.join(time_series_data,time_series_data.c.id == time_series.c.id)
#         joins = joins.join(data_vendors,time_series.c.data_vendor_id == data_vendors.c.id)

#         query = select([time_series_data.c.data_date,time_series.c.field_name,time_series_data.c.value]).select_from(joins)
#         query = query.where(and_(time_series.c.dataset ==dataset, data_vendors.c.name==data_vendor))

#         if pd.notnull(start_date):
#             query = query.where(time_series_data.c.data_date >= start_date)

#         if pd.notnull(end_date):
#             query = query.where(time_series_data.c.data_date <= end_date)

#         df = pd.read_sql(query,self.ENGINE)

#         if not len(df):
#             raise Exception ('No data found for dataset %s from vendor %s'%(dataset, data_vendor))

#         df = df.pivot(index='data_date',columns='field_name',values='value')
#         df.sort_index(inplace=True)
#         return(df)


#     def get_source_eod_data(self, sec_id = None, m_ticker=None, vendor_ticker = None, vendor=None, start_date=pd.NaT, end_date=pd.NaT, 
#                             columns = ['open','high','low','close','volume','adj_open','adj_high','adj_low','adj_close','adj_vol'],download_all=False):
#         '''
#         Only one of sec_id, m_ticker or vendor_ticker is required
#         sec_id, m_ticker or vendor_ticker can be lists -> note that the return dataframe is a multiindex if its a list
#         Order of precedence sec_id > m_ticker > vendor_ticker
#         Vendor is required
#         '''
#         # figure out mode to run in
#         if not download_all:
#             if isinstance(sec_id,list) or pd.notnull(sec_id):
#                 selector = 'sec_id'
#                 list_mode = isinstance(sec_id,list)
#                 sec_ids = sec_id if list_mode else [sec_id]
#             elif isinstance(m_ticker,list) or pd.notnull(m_ticker):
#                 selector = 'm_ticker'
#                 list_mode = isinstance(m_ticker,list)
#                 m_tickers = m_ticker if list_mode else [m_ticker]
#             elif isinstance(vendor_ticker,list) or pd.notnull(vendor_ticker):
#                 selector = 'vendor_ticker'
#                 list_mode = isinstance(vendor_ticker,list)
#                 vendor_tickers = vendor_ticker if list_mode else [vendor_ticker]
#             else:
#                 raise Exception ('Neither sec_id, m_ticker nor vendor_ticker specified')
#         else:
#             selector = 'All'
#             list_mode = True

#         # vendor checks
#         if pd.isnull(vendor):
#             raise Exception ('No vendor specified')

#         vendors = self.get_data_vendors()
#         if vendor not in vendors.name.values: # note that .values is required else it doesn't work
#             raise Exception ('Incorrect vendor specified')

#         # define tables
#         #sec_master = Table('V_sec_master',self.META,autoload=True)
#         eod_table = Table('eod_data_source',self.META,autoload=True)
#         data_vendors = Table('data_vendors',self.META,autoload=True)

#         # create selects
#         selects = [eod_table.c.sec_id,eod_table.c.m_ticker,eod_table.c.vendor_ticker,eod_table.c.data_date]
#         selects = selects + [eod_table.c[i] for i in columns if i not in ['sec_id','vendor_ticker','data_date']]

#         # join tables
#         #joins = sec_master.join(eod_table,sec_master.c.sec_id==eod_table.c.sec_id) # not needed since m_ticker is in EOD table now
#         joins = eod_table.join(data_vendors,eod_table.c.vendor_id == data_vendors.c.id)

#         # create query
#         if selector =='sec_id':
#             query = select(selects).select_from(joins).where((eod_table.c.sec_id.in_(sec_ids)) & (data_vendors.c.name == vendor))
#         elif selector =='m_ticker':
#             query = select(selects).select_from(joins).where((eod_table.c.m_ticker.in_(m_tickers)) & (data_vendors.c.name == vendor))
#         elif selector == 'vendor_ticker':
#             query = select(selects).select_from(joins).where((eod_table.c.vendor_ticker.in_(vendor_tickers)) & (data_vendors.c.name == vendor))
#         elif selector =='All':
#             query = select(selects).select_from(joins).where(data_vendors.c.name == vendor)

#         if pd.notnull(start_date):
#             query = query.where(eod_table.c.data_date >= start_date)

#         if pd.notnull(end_date):
#             query = query.where(eod_table.c.data_date <= end_date)

#         conn = self.ENGINE.connect()
#         conn.execute('set net_write_timeout=400')
#         conn.execute('set net_read_timeout=120')
#         df = pd.read_sql(query,conn)
#         conn.close()
#         if list_mode:
#             if selector in ['All','sec_id']:
#                 df.set_index(['sec_id','data_date'],inplace=True)
#             elif selector =='m_ticker':
#                 df.set_index(['m_ticker','data_date'],inplace=True)
#             else:
#                 df.set_index(['vendor_ticker','data_date'],inplace=True)
#         else:
#             df.set_index('data_date',inplace=True)
#         df.sort_index(inplace=True)
#         return(df)

# class Access_SQL_Daily(Access_SQL_DB):
#     def __init__(self, host=None,user=os.environ.get('MySQL_UserName'),passwd=os.environ.get('MySQL_Password'),echo=False):
#         self.host = host
#         self.user = user
#         self.password = passwd
#         self.db = 'daily_feature_tables'
#         self.echo=echo
#         self.open_connection()

#     def get_daily_data_dict(self, fields, start_date=None, end_date=None, m_ticker=None,sid_chunksize = None):
#         ## fields must be specified as a dict as {'table1':['field1','field2',...],'table2':['field1','field2',...]}
#         all_tables = fields.keys()
#         field_list = [(i,j) for i in fields.keys() for j in fields[i]]
#         field_list = pd.DataFrame(field_list)
#         field_list.columns = ['Table','Field']

#         data = self._get_daily_data (field_list=field_list, all_tables=all_tables, start_date=start_date, end_date=end_date, m_ticker=m_ticker,sid_chunksize=sid_chunksize)
#         return(data)

#     def get_daily_data_file(self, field_list_file, field_list_column = 'Download', start_date=None, end_date=None, m_ticker=None,sid_chunksize = None):
#         # read table and field list
#         field_list = pd.read_csv(field_list_file)
#         field_list = field_list[field_list[field_list_column]=='Y']
#         all_tables = field_list.Table.unique()

#         data = self._get_daily_data (field_list=field_list, all_tables=all_tables, start_date=start_date, end_date=end_date, m_ticker=m_ticker,sid_chunksize=sid_chunksize)
#         return (data)

#     def _get_daily_data (self, field_list, all_tables, start_date, end_date, m_ticker,sid_chunksize):
#         # error check
#         duplicates = field_list[field_list.duplicated('Field',keep=False)]
#         if len(duplicates):
#             print (duplicates.to_string())
#             raise Exception ('Duplicate column names selected for download')

#         # find name of date_sid_master
#         dsm = field_list[field_list.Field=='data_date'].iloc[0]['Table']

#         # setup sql tables
#         all_tablesT = {x:Table(x,self.META,autoload=True) for x in all_tables}

#         # set up sec_master
#         sec_table = Table('V_sec_master', self.META, autoload=True)

#         # define joins
#         joins = all_tablesT[dsm].outerjoin(sec_table, sec_table.c.sec_id==all_tablesT[dsm].c.sec_id)

#         for tn in all_tablesT.keys():
#             if tn in ['V_sec_master',dsm]: #don't join these again
#                 continue
#             elif tn == 'nprs_sectors_daily':
#                 joins = joins.outerjoin(all_tablesT[tn], (all_tablesT[tn].c.zacks_x_sector_code == sec_table.c.zacks_x_sector_code) & (all_tablesT[tn].c.data_date == all_tablesT[dsm].c.data_date))
#             elif tn == 'nprs_industries_daily':
#                     joins = joins.outerjoin(all_tablesT[tn], (all_tablesT[tn].c.zacks_m_ind_code == sec_table.c.zacks_m_ind_code) & (all_tablesT[tn].c.data_date == all_tablesT[dsm].c.data_date))
#             else:
#                 joins = joins.outerjoin(all_tablesT[tn], (all_tablesT[dsm].c.sec_id == all_tablesT[tn].c.sec_id) & (all_tablesT[dsm].c.data_date == all_tablesT[tn].c.data_date))


#         # define selects
#         cols = []
#         for r,field in field_list.iterrows():
#             cols.append(all_tablesT[field.Table].c[field.Field])

#         # start query
#         query = select(cols).select_from(joins)

#         # add date filters
#         if pd.notnull(start_date):
#             query = query.where(all_tablesT[dsm].c.data_date >= start_date)

#         if pd.notnull(end_date):
#             query = query.where(all_tablesT[dsm].c.data_date <= end_date)

#         # execute query with ticker filters
#         if pd.notnull(m_ticker):
#             query = query.where(sec_table.c.m_ticker == m_ticker)
#             return(pd.read_sql(query,self.ENGINE))
#         elif pd.isnull(sid_chunksize):
#             return(pd.read_sql(query,self.ENGINE))
#         else:
#             sids = pd.read_sql(select([all_tablesT[dsm].c.sec_id]).distinct(),self.ENGINE).sec_id.tolist()

#             splits = np.array_split(sids, ((np.ceil(len(sids)/sid_chunksize)).astype(int)))
#             data = []
#             split_num = 1
#             logging.info('Found %s splits for downloading'%len(splits))
#             for split in splits:
#                 logging.info('Downloading split %s'%split_num)
#                 query_s = query.where(all_tablesT[dsm].c.sec_id.in_(split))
#                 split_num +=1
#                 data.append(pd.read_sql(query_s,self.ENGINE))
#             data = pd.concat(data,ignore_index=True)
#             return(data)


#     # for portfolio model
#     def get_latest_bar_datetime(self):
#         date_master = 'qm_eod_technicals_daily'
#         date_masterT = Table(date_master,self.META,autoload=True)
#         max_date = select([sqlalchemy_func.max(date_masterT.c.data_date)]).execute().first()[0]
#         return(max_date)

#     def get_latest_bar(self, sec_ids =[], data_list = {}):
#         data_list = data_list.copy()
#         data_list['V_sec_master'] = ['sec_id']
#         data_list['qm_eod_technicals_daily'] = data_list['qm_eod_technicals_daily'] + ['data_date']
#         max_date = self.get_latest_bar_datetime()
#         df = self.get_daily_data_dict (fields = data_list, start_date=max_date, end_date=max_date, m_ticker=None,sid_chunksize = None)
#         df.set_index('sec_id',inplace=True)
#         return(df)

#     def get_latest_bars(self, sec_ids, data_list = [], N=1):
#         """
#         Returns the last N bars from the symbol_data list,
#         or N-k if less available.
#         """
#         data_list = data_list.copy()
#         data_list['V_sec_master'] = ['sec_id']
#         data_list['qm_eod_technicals_daily'] = data_list['qm_eod_technicals_daily'] + ['data_date']

#         max_date = self.get_latest_bar_datetime()

#         date_master = 'qm_eod_technicals_daily'
#         date_masterT = Table(date_master,self.META,autoload=True)
#         all_dates = pd.read_sql_query(select([sqlalchemy_func.distinct(date_masterT.c.data_date)]).where(date_masterT.c.data_date > max_date - pd.DateOffset(days = N * 7/5 + 30)), self.ENGINE)
#         all_dates.sort_values('distinct_1',inplace=True)
#         date_slice = all_dates['distinct_1'].tail(N).tolist()

#         if not isinstance(sec_ids,list):
#             sec_ids = [sec_ids]

#         df = self.get_daily_data_dict (fields = data_list, start_date=date_slice[0], end_date=date_slice[-1], m_ticker=None,sid_chunksize = None)
#         df = df[df.sec_id.isin(sec_ids)]
#         df = df.set_index(['data_date','sec_id']).sort_index()

#         return (df)



