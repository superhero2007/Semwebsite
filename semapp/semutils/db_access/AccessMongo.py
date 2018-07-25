from pymongo import MongoClient
import gridfs
from bson.objectid import ObjectId
import re
import sys
import pandas as pd
import socket

class AccessMongo(object):
    def __init__(self,host='localhost', port=27017, username=None, password=None):
        localhost = socket.gethostname()
        if host ==localhost:
            host='localhost'
        if username and password:
            mongo_uri = 'mongodb://%s:%s@%s:%s/%s' % (username, password, host, port, db)
            self.conn = MongoClient(mongo_uri)
        else:
            self.conn = MongoClient(host, port)

    def close_connection (self):
        self.conn.close()

    def connect_sec_filings_db(self):
        return (self.conn.sec_filings_db.sec_filings)

    def connect_transactions_db(self):
        form_status = self.conn.transactions_db.form_status
        processed_forms = self.conn.transactions_db.processed_forms
        processed_forms_with_features = self.conn.transactions_db.processed_forms_with_features
        return(form_status,processed_forms,processed_forms_with_features)

    def connect_sec_filings_raw_files_db(self):
        collections = self.conn.sec_filings_raw_files_db.collection_names()
        tags = []
        for n in collections:
            tags= tags + re.findall('^(y\d\d)',n)
        tags = set(tags)

        files_collections = {}
        for tag in tags:
            files_collections[tag] = gridfs.GridFS(self.conn.sec_filings_raw_files_db,collection=tag)
        return (files_collections)

    def connect_insider_signals_table(self):
        return (self.conn.signals_db.insider_signals)

    def reset_all_of_transaction_db(self,confirm='NO'):
        if confirm =='YES':
            print ('Deleteing transaction_db')
            sys.stdout.flush()
            self.conn.drop_database('transactions_db')
            print ('Resetting AddedToStatusTable column in sec_filings collection')
            sys.stdout.flush()
            self.conn.sec_filings_db.sec_filings.update({},{'$set':{'AddedToStatusTable':False}},multi=True)
        else:
            print ('Set confirm to YES if you really want to do this')

    def reset_processed_forms(self,confirm='NO'):
        if confirm =='YES':
            print ('Deleteing processed_forms collection')
            sys.stdout.flush()
            self.conn.transactions_db.drop_collection('processed_forms')
            print ('Deleteing processed_forms_with_features collection')
            sys.stdout.flush()
            self.conn.transactions_db.drop_collection('processed_forms_with_features')
            print ('Resetting ProcessingStatus column in Status table to PENDING')
            sys.stdout.flush()
            self.conn.transactions_db.form_status.update({},{'$set':{'ProcessingStatus':'PENDING'}},multi=True)
        else:
            print ('Set confirm to YES if you really want to do this')

    def reset_processed_forms_with_features(self,confirm='NO'):
        if confirm =='YES':
            print ('Deleteing processed_forms_with_features collection')
            sys.stdout.flush()
            self.conn.transactions_db.drop_collection('processed_forms_with_features')
            print ('Resetting LoadedIntoFeaturesDB column in processed_forms db to False')
            sys.stdout.flush()
            self.conn.transactions_db.processed_forms.update({},{'$set':{'LoadedIntoFeaturesDB':False}},multi=True)
        else:
            print ('Set confirm to YES if you really want to do this')


    def get_data_as_df(self,collection,rows_limit=None): 
        if not(number_of_rows):
            df = pd.DataFrame(list(collection.find()))
        else:
            df = pd.DataFrame(list(collection.find().limit(number_of_rows)))
        return(df)

    def reset_insider_signals_table(self,confirm='NO'):
        if confirm =='YES':
            print ('Deleteing insider_signals collection')
            sys.stdout.flush()
            self.conn.signals_db.drop_collection('insider_signals')
            print ('Resetting LoadedIntoSignalsDB column in processed_forms_with_features table to False')
            sys.stdout.flush()
            self.conn.transactions_db.processed_forms_with_features.update({},{'$set':{'LoadedIntoSignalsDB':False}},multi=True)
        else:
            print ('Set confirm to YES if you really want to do this')
