import argparse
from AccessSQL import *

TABLES_LIST = ['V_sec_master',
               'market_cap_daily',
               'qm_eod_technicals_daily',
               'zfa_features_daily',
               'short_interest_daily',
               'zacks_estimates_daily',
               'it_features_daily',
               'nprs_sids_daily',
               'nprs_sectors_daily',
               'nprs_industries_daily']


if __name__ == "__main__":
    # parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-H','--hostname', type = str,required=True) # used for mysql hostname
    parser.add_argument('-i','--input_filename', type = str,required=True) 
    parser.add_argument('-o','--output_filename', type = str,default =None)
    parser.add_argument('-D','--remove_deleted_fields', action='store_true',default=False) 

    options = parser.parse_args()

    #connect to daily features tables
    sql_daily = Access_SQL_Daily(host=options.hostname)

    # create new table
    df_new = []
    for i in TABLES_LIST:
        x = Table(i, sql_daily.META, autoload=True)
        df_new = df_new + ([{'Table':i,'Field':j} for j in x.columns.keys()])

    df_new = pd.DataFrame(df_new)[['Table','Field']].sort_values(['Table','Field'])
    df_new = df_new[~df_new.Field.isin(['date_created','date_modified'])]
    df_new['row_key'] = df_new.Table+'_'+df_new.Field

    # read existing file
    if os.path.exists(options.input_filename):
        df_old = pd.read_csv(options.input_filename)
        df_old['row_key'] = df_old.Table+'_'+df_old.Field
        col_order = df_old.columns
    else:
        df_old = pd.DataFrame(columns = ['Table','Field','row_key'])

    # add new fields
    new_fields = df_new[~df_new.row_key.isin(df_old.row_key)].reset_index(drop=True)
    new_fields['Download'] = 'XXX'
    print ('Adding %s new fields'%len(new_fields))
    print (new_fields.drop('row_key',axis=1).to_string())
    df = pd.concat([df_old,new_fields],ignore_index=True)
    df = df[col_order]

    # remove deleted fields
    if options.remove_deleted_fields:
        dropped_fields = df[~df.row_key.isin(df_new.row_key)].reset_index(drop=True)
        print ('Removing %s fields'%len(dropped_fields))
        print (dropped_fields.drop('row_key',axis=1).to_string())
        df = df[~df.row_key.isin(dropped_fields.row_key)]

    df.sort_values(['Table','Field'],inplace=True)
    df.drop('row_key',axis=1,inplace=True)

    # write file
    if pd.notnull(options.output_filename):
        df.to_csv(options.output_filename,index=False)
    else:
        print ('No output file defined. Not saving')



