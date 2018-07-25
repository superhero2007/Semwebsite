import logging 

# set up logger
def setup_logger(log_filename, log_filemode = 'w'):
    recfmt = '%(asctime)s %(filename)s(%(lineno)d) %(levelname)s: %(message)s'
    timefmt = '%y-%m-%d %H:%M:%S'
    
    # clear existing loggers
    logging.getLogger().handlers = []

    # add a basic file logger
    logging.basicConfig(filename=log_filename,
                        filemode=log_filemode,
                        level=logging.DEBUG,
                        format=recfmt, datefmt=timefmt)

    # add a console logger    
    logger = logging.getLogger()
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter(recfmt,datefmt=timefmt))
    console.setLevel(logging.INFO)
    logger.addHandler(console)
