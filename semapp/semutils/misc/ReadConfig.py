import configparser

def read_config(config_file):
    config = configparser.ConfigParser()
    config.read(config_file)
    return(config)
