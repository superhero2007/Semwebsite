import os,sys

try:
    if os.getpgrp() == os.tcgetpgrp(sys.stdout.fileno()):
        import ipdb
except:
    pass
