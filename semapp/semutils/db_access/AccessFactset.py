import pandas as pd
import sqlalchemy
import os
from .AccessSQL import Access_SQL_DB

table_indexes = {
    'fe_v4_fe_basic_act_af'      : ('fe_fp_end', ['fsym_id', 'fe_fp_end', 'fe_item']),
    'fe_v4_fe_basic_act_qf'      : ('fe_fp_end', ['fsym_id', 'fe_fp_end', 'fe_item']),
    'fe_v4_fe_basic_act_saf'     : ('fe_fp_end', ['fsym_id', 'fe_fp_end', 'fe_item']),
    'fe_v4_fe_basic_conh_af'     : ('fe_fp_end', ['fsym_id', 'fe_fp_end', 'fe_item', 'cons_start_date']),
    'fe_v4_fe_basic_conh_lt'     : ('cons_start_date', ['fsym_id', 'fe_item', 'cons_start_date']),
    'fe_v4_fe_basic_conh_qf'     : ('fe_fp_end', ['fsym_id', 'fe_fp_end', 'fe_item', 'cons_start_date']),
    'fe_v4_fe_basic_conh_rec'    : ('cons_start_date', ['fsym_id', 'fe_item', 'cons_start_date']),
    'fe_v4_fe_basic_conh_saf'    : ('fe_fp_end', ['fsym_id', 'fe_fp_end', 'fe_item', 'cons_start_date']),
    'fe_v4_fe_basic_guid_af'     : ('fe_fp_end', ['fsym_id', 'fe_fp_end', 'fe_item', 'guidance_date', 'guidance_type']),
    'fe_v4_fe_basic_guid_qf'     : ('fe_fp_end', ['fsym_id', 'fe_fp_end', 'fe_item', 'guidance_date', 'guidance_type']),
    'fe_v4_fe_basic_guid_saf'    : ('fe_fp_end', ['fsym_id', 'fe_fp_end', 'fe_item', 'guidance_date', 'guidance_type']),
    'ff_v3_ff_segreg_af'         : ('date',      ['fsym_id', 'date', 'ff_segment_num', 'ff_segment_type']),
    'ff_v3_ff_segbus_af'         : ('date',      ['fsym_id', 'date', 'ff_segment_num', 'ff_segment_type']),
    'ff_v3_ff_basic_cf'          : ('adjdate',   ['fsym_id', 'adjdate'])
}

class AccessFactset(object) :
    def __init__(self, sql_host=None,sql_user=os.environ.get('MySQL_UserName'),sql_passwd=os.environ.get('MySQL_Password'),sql_db='factset',sql_echo=False) :
        self.sql    = Access_SQL_DB(host=sql_host,user=sql_user,passwd=sql_passwd,db=sql_db,echo=sql_echo)

    # table_name, 
    # , 
    # fsym_regional_id = 'MH33D6-R'


    def get_security_data(self, table_name, fsym_id, start_date=pd.NaT, end_date = pd.NaT, columns = ['*']) :
        '''        
        fundamentals             : primary key   
        ------------------------ : ---------------
        ff_v3_ff_basic_af        : date, fsym_id
        ff_v3_ff_basic_cf        : fsym_id        # one row per security
        ff_v3_ff_basic_der_af    : date, fsym_id            
        ff_v3_ff_basic_der_ltm   : date, fsym_id            
        ff_v3_ff_basic_der_qf    : date, fsym_id            
        ff_v3_ff_basic_der_r_af  : date, fsym_id            
        ff_v3_ff_basic_der_saf   : date, fsym_id            
        ff_v3_ff_basic_ltm       : date, fsym_id            
        ff_v3_ff_basic_qf        : date, fsym_id            
        ff_v3_ff_basic_r_af      : date, fsym_id            
        ff_v3_ff_basic_saf       : date, fsym_id
        ff_v3_ff_segbus_af       : date, fsym_id, ff_segment_num , ff_segment_type
        ff_v3_ff_segreg_af       : date, fsym_id, ff_segment_num , ff_segment_type            
        ff_v3_ff_stitch_af       : date, fsym_id            
        ff_v3_ff_stitch_ltm      : date, fsym_id            
        ff_v3_ff_stitch_qf       : date, fsym_id 
        ff_v3_ff_stitch_saf      : date, fsym_id

        estimates                : primary key               
        -------------------------:------------------------
        fe_v4_fe_basic_act_af    : fsym_id, fe_fp_end, fe_item 
        fe_v4_fe_basic_act_qf    : fsym_id, fe_fp_end, fe_item
        fe_v4_fe_basic_act_saf   : fsym_id, fe_fp_end, fe_item
        fe_v4_fe_basic_conh_af   : fsym_id, fe_fp_end, fe_item, cons_start_date
        fe_v4_fe_basic_conh_lt   : fsym_id, fe_item, cons_start_dat
        fe_v4_fe_basic_conh_qf   : fsym_id, fe_fp_end, fe_item, cons_start_date
        fe_v4_fe_basic_conh_rec  : fsym_id, fe_item, cons_start_dat
        fe_v4_fe_basic_conh_saf  : fsym_id, fe_fp_end, fe_item, cons_start_date
        fe_v4_fe_basic_guid_af   : fsym_id, fe_fp_end, fe_item, guidance_date  , guidance_type
        fe_v4_fe_basic_guid_qf   : fsym_id, fe_fp_end, fe_item, guidance_date  , guidance_type
        fe_v4_fe_basic_guid_saf  : fsym_id, fe_fp_end, fe_item, guidance_date  , guidance_type
        '''

        date_column     = 'date'
        
        if table_name in table_indexes :
            date_column = table_indexes[table_name][0]
                
        # Convert signal symbol queries into lists and set index to just the date column.
        if isinstance(fsym_id, str) :
            fsym_id     = [fsym_id]           

        # All queries must have the fsym_id included.
        if 'fsym_id' not in columns  :
            columns.append('fsym_id')    
            
        if date_column not in columns  :
            columns.append(date_column)                      

        df              = self.get_security_data_basic(fsym_id, start_date, end_date, columns, table_name, date_column)

        return(df)
   

    def get_security_data_basic(self, fsym_id, start_date, end_date, columns, table_name, date_column) :
        '''
        Get prices and return the data frame.
        '''
        data_table = sqlalchemy.Table(table_name, self.sql.META, autoload=True)
        if '*' in columns :
            selects = ['*']
        else :
            selects = [data_table.c[i] for i in columns]

        query       = sqlalchemy.select(selects).select_from(data_table)

        if fsym_id is not None :
            query   = query.where((data_table.c.fsym_id.in_(fsym_id)))

        if pd.notnull(start_date) :
            query   = query.where(data_table.c[date_column] >= start_date)

        if pd.notnull(end_date) :
            query   = query.where(data_table.c[date_column] <= end_date)
        
        df          = pd.read_sql(query, self.sql.ENGINE)

        return df