import pandas as pd
import sqlalchemy
import os
from .AccessSQL import Access_SQL_DB

class AccessReference(object):
    def __init__(self, sql_host=None,sql_user=os.environ.get('MySQL_UserName'),sql_passwd=os.environ.get('MySQL_Password'),sql_db='reference',sql_echo=False):
        self.sql    = Access_SQL_DB(host=sql_host,user=sql_user,passwd=sql_passwd,db=sql_db,echo=sql_echo)

    def get_sec_master(self, active_only = False) :
        query       = '''
        select
            f.sec_id, 
            f.ticker, 
            f.proper_name, 
            f.fref_security_type, 
            f.fsym_regional_id,
            f.active_flag, 
            f.fref_listing_exchange, 
            f.isin, 
            f.cusip,
            f.sedol, 
            f.bbg_id, 
            f.bbg_ticker,   
            a.AxiomaID, 
            f.fsym_id, 
            f.factset_entity_id, 
            a.MIC, 
            a.AssetType, 
            a.AssetClass, 
            a.AssetSubclass, 
            a.Industry, 
            a.IndustryGroup, 
            a.Sector,
            f.cik
        from 
            factset_security_view f 
            join axioma_security_view a on f.sec_id = a.sec_id
            
        ''' 

        df          = pd.read_sql_query(query, self.sql.CONN)

        if active_only : 
            active  = (df['active_flag'] == 1)
            common  = (df.fref_security_type == 'SHARE') | (df.fref_security_type == 'ADR')
            sub_class = (df.AssetSubclass == 'Common Stock-S') | (df.AssetSubclass == 'ADR-S') | (df.AssetSubclass == 'REIT-S')
            non_otc = (df.fref_listing_exchange != 'OTC') & (df.fref_listing_exchange != 'ZZUS') & (df.fref_listing_exchange != 'PINX') & (df.fref_listing_exchange != 'ADF')
            df      = df[active & common & non_otc & sub_class]

        # Making a seperate query for zacks asset_type because adding it to the join above increases runtime greatly.
        zacks_df    = pd.read_sql_query('select asset_type, cusip from zacks_security', self.sql.CONN)
        df          = df.merge(zacks_df, on = 'cusip', how = 'left')

        return df
        

    def close_connection(self) :
        self.sql.close_connection()


    def get_daily_prices(self, sec_ids = None, cusips = None, tickers = None, start_date = pd.NaT, end_date = pd.NaT, 
        columns = ['data_date', 'sec_id', 'open','high','low','close','volume', 'adj_close', 'adj_open', 'adj_high', 'adj_low', 'adj_vol', 'daily_return']) :
        '''
        A convenience wrapper around get_security_data()) that enables user to request for prices in a number of different ways.

        sec_ids     - single sec_id, list of sec_ids, default is all securities.
        cusips      - if sec_ids is left None and a single/list of cusips are specified, then those cusips are translated into sec_ids
        tickers     - if sec_ids and cusips are left None and a single/list of tickers are specified, then those tickers are translated into sec_ids

        start_date, end_date - date range for prices, default is all dates (pd.Nat)

        columns     - pricing columns to include in the result set.

        Default Columns :
            'data_date', 'sec_id', 'adj_close', 'adj_open', 'adj_high', 'adj_low', 'adj_vol', 'daily_return'

        Possible Columns :
            'data_date', 'sec_id', 'fsym_id', 'fsym_regional_id', 
            'close', 'open', 'high', 'low', 'volume', 'adv10', 'adv20', 'mdv20' 
            'adj_close', 'adj_open', 'adj_high', 'adj_low', 'adj_vol',
            'cum_return', 'daily_return', 'dividend', 'marketcap', 'marketcap_group', 'shares_outstanding', 'split'            

        To specify all columns pass :
            '*'
        '''
        return self.get_security_data(sec_ids, cusips, tickers, start_date, end_date, columns, 'factset_price', 'data_date')


    def get_zacks_fundamentals(self, sec_ids = None, cusips = None, tickers = None, start_date = pd.NaT, end_date = pd.NaT, 
        columns = ['*']) :
        """
        Sample :
            conn.get_zacks_fundamentals(sec_ids = 'S0000181')
        """
        return self.get_security_data(sec_ids, cusips, tickers, start_date, end_date, columns, 'zacks_fundamentals', 'per_end_date')

        
    def convert_cusips_to_sec_ids(self, cusips) :
        sec_master_table    = sqlalchemy.Table('factset_security_view', self.sql.META, autoload=True)
        query       = sqlalchemy \
            .select([sec_master_table.c.cusip, sec_master_table.c.sec_id]) \
            .select_from(sec_master_table) \
            .where((sec_master_table.c.cusip.in_(cusips)))

        df          = pd.read_sql(query, self.sql.CONN)

        return df


    def convert_tickers_to_sec_ids(self, tickers) :
        sec_master_table    = sqlalchemy.Table('factset_security_view', self.sql.META, autoload=True)
        query       = sqlalchemy \
            .select([sec_master_table.c.ticker, sec_master_table.c.sec_id]) \
            .select_from(sec_master_table) \
            .where((sec_master_table.c.ticker.in_(tickers)))

        df          = pd.read_sql(query, self.sql.CONN)

        return df


    def get_index_prices(self, benchmark_id = None, benchmark_name = None, start_date = pd.NaT, end_date = pd.NaT) :
        index_table = sqlalchemy.Table('factset_index', self.sql.META, autoload=True)
        query       = sqlalchemy.select('*').select_from(index_table)

        if benchmark_id is not None :            
            query   = query.where((index_table.c.BENCHMARK_ID == benchmark_id))
            
        elif benchmark_name is not None :
            query   = query.where((index_table.c.IDX_NAME == benchmark_name))
            
        if pd.notnull(start_date) :
            query   = query.where(index_table.c.data_date >= start_date)

        if pd.notnull(end_date) :
            query   = query.where(index_table.c.data_date <= end_date)
        
        df          = pd.read_sql(query, self.sql.CONN)

        if len(df.BENCHMARK_ID.unique()) == 1 :
            df.set_index(['data_date'], inplace = True)            
        else :
            df.set_index(['BENCHMARK_ID', 'data_date'], inplace = True)

        df.sort_index(inplace=True)
        
        return df


    def get_short_interest(self, sec_ids = None, cusips = None, tickers = None, start_date = pd.NaT, end_date = pd.NaT, columns = ['*']) :
        '''
        sec_ids     - single sec_id, list of sec_ids, default is all securities.
        cusips      - if sec_ids is left None and a single/list of cusips are specified, then those cusips are translated into sec_ids
        tickers     - if sec_ids and cusips are left None and a single/list of tickers are specified, then those tickers are translated into sec_ids

        start_date, end_date - date range for prices, default is all dates (pd.Nat)

        columns     - pricing columns to include in the result set.

        Default Columns :

        Possible Columns :

        To specify all columns pass :
            '*'
        '''
        return self.get_security_data(sec_ids, cusips, tickers, start_date, end_date, columns, 'markit_short_interest')


    def get_beta_risk(self, sec_ids = None, cusips = None, tickers = None, start_date = pd.NaT, end_date = pd.NaT, columns = ['*'], axioma_model = 'sh') :
        table_name  = 'axioma_beta_risk_' + axioma_model
        if axioma_model == 'mh' :
            table_name  = 'axioma_beta_risk'

        return self.get_security_data(sec_ids, cusips, tickers, start_date, end_date, columns, table_name, 'data_date')


    def get_exp(self, sec_ids = None, cusips = None, tickers = None, start_date = pd.NaT, end_date = pd.NaT, columns = ['*'], axioma_model = 'sh') :
        table_name  = 'axioma_exposure_' + axioma_model
        if axioma_model == 'mh' :
            table_name  = 'axioma_exposure'

        return self.get_security_data(sec_ids, cusips, tickers, start_date, end_date, columns, table_name, 'data_date')


    def get_cov(self, start_date = pd.NaT, end_date = pd.NaT, axioma_model = 'sh') :
        table_name  = 'axioma_cov_' + axioma_model
        if axioma_model == 'mh' :
            table_name  = 'axioma_cov'

        sql_table   = sqlalchemy.Table(table_name, self.sql.META, autoload=True)
        query       = sqlalchemy.select('*').select_from(sql_table)
            
        if pd.notnull(start_date) :
            query   = query.where(sql_table.c.data_date >= start_date)

        if pd.notnull(end_date) :
            query   = query.where(sql_table.c.data_date <= end_date)
        
        df          = pd.read_sql(query, self.sql.CONN)
        df.set_index(['FactorName', 'data_date'], inplace = True)
        df.sort_index(inplace=True)
        
        return df


    def get_factor_returns(self, start_date = pd.NaT, end_date = pd.NaT, axioma_model = 'sh') :
        table_name  = 'axioma_ret_' + axioma_model
        if axioma_model == 'mh' :
            table_name  = 'axioma_ret'

        sql_table   = sqlalchemy.Table(table_name, self.sql.META, autoload=True)
        query       = sqlalchemy.select('*').select_from(sql_table)
            
        if pd.notnull(start_date) :
            query   = query.where(sql_table.c.data_date >= start_date)

        if pd.notnull(end_date) :
            query   = query.where(sql_table.c.data_date <= end_date)
        
        df          = pd.read_sql(query, self.sql.CONN)
        df.set_index(['data_date'], inplace = True)
        df.sort_index(inplace=True)
        
        return df


    def get_time_series(self,dataset = None, data_vendor = None, start_date=pd.NaT, end_date = pd.NaT):
        if pd.isnull(dataset) or pd.isnull(data_vendor):
            raise Exception ('Dataset or data_vendor missing')

        time_series = sqlalchemy.Table('time_series',self.sql.META,autoload=True)
        time_series_data = sqlalchemy.Table('time_series_data',self.sql.META,autoload=True)
        data_vendors = sqlalchemy.Table('data_vendors',self.sql.META,autoload=True)

        joins = time_series.join(time_series_data,time_series_data.c.id == time_series.c.id)
        joins = joins.join(data_vendors,time_series.c.data_vendor_id == data_vendors.c.id)

        query = sqlalchemy.select([time_series_data.c.data_date,time_series.c.field_name,time_series_data.c.value]).select_from(joins)
        query = query.where(sqlalchemy.and_(time_series.c.dataset ==dataset, data_vendors.c.name==data_vendor))

        if pd.notnull(start_date):
            query = query.where(time_series_data.c.data_date >= start_date)

        if pd.notnull(end_date):
            query = query.where(time_series_data.c.data_date <= end_date)

        df = pd.read_sql(query,self.sql.CONN)

        if not len(df):
            raise Exception ('No data found for dataset %s from vendor %s'%(dataset, data_vendor))

        df = df.pivot(index='data_date',columns='field_name',values='value')
        df.sort_index(inplace=True)

        return(df)


    def get_security_data(self, sec_ids, cusips, tickers, start_date, end_date, columns, table_name, date_column = 'data_date') :        
        columns         = columns.copy()
        index_columns   = ['sec_id', date_column]
        lookup          = None

        # Convert signal symbol queries into lists and set index to just the trade date.
        if isinstance(sec_ids, str) :
            sec_ids     = [sec_ids]
            index_columns = [date_column]

        if isinstance(cusips, str) :
            cusips      = [cusips]
            index_columns = [date_column]

        if isinstance(tickers, str) :
            tickers     = [tickers]
            index_columns = [date_column]

        # All queries must have the sec_id included.
        if 'sec_id' not in columns  :
            columns.append('sec_id')

        if date_column not in columns  :
            columns.append(date_column)
        
        if sec_ids is None :
            # In case user passed some other type of identifier
            if cusips is not None :
                lookup  = self.convert_cusips_to_sec_ids(cusips)
                sec_ids = lookup['sec_id']

            elif tickers is not None :
                lookup  = self.convert_tickers_to_sec_ids(tickers)
                sec_ids = lookup['sec_id']

        df              = self.get_security_data_basic(sec_ids, start_date, end_date, columns, table_name, date_column)

        if lookup is not None :
            df          = df.merge(lookup, on = 'sec_id', how = 'left')
                
        df.set_index(index_columns, inplace=True)
        df.sort_index(inplace=True)

        return(df)
   

    def get_security_data_basic(self, sec_ids, start_date, end_date, columns, table_name, date_column = 'data_date') :
        '''
        Get prices and return the data frame.
        '''
        data_table = sqlalchemy.Table(table_name, self.sql.META, autoload=True)
        if '*' in columns :
            selects = ['*']
        else :
            selects = [data_table.c[i] for i in columns]

        query       = sqlalchemy.select(selects).select_from(data_table)

        if sec_ids is not None :
            query   = query.where((data_table.c.sec_id.in_(sec_ids)))

        if pd.notnull(start_date) :
            query   = query.where(data_table.c[date_column] >= start_date)

        if pd.notnull(end_date) :
            query   = query.where(data_table.c[date_column] <= end_date)
        
        df          = pd.read_sql(query, self.sql.CONN)

        return df