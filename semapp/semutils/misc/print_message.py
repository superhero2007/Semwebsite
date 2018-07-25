import datetime
import sys

# print_message
def print_message(message):
    print ('%s: %s'%(datetime.datetime.now().replace(microsecond=0),message))
    sys.stdout.flush()

