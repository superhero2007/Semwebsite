MasterConfig = {'prod':{'sql_source_host' : '104.197.188.90',
                        'sql_write_host' : '104.197.188.90',
                        'sql_ref_host' : '104.197.188.90',
                        'redis_host' : '10.128.0.9',
                        'slack_error_channel': 'productionissues'},
                'dev':{'sql_source_host' : '104.197.188.90',
                        'sql_write_host' : 'dione',
                        'sql_ref_host' : '104.197.188.90',
                        'redis_host' : '10.128.0.9',
                        'slack_error_channel': 'testing'},
                'devlocal':{'sql_source_host' : 'pythia',
                            'sql_write_host' : 'dione',
                            'slack_error_channel': 'testing'}}


