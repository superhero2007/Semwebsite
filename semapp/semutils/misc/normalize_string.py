import pandas as pd
import numpy as np
import datetime
import os, sys
import string
 
def normalize_string(s):
    for p in string.punctuation:
        s = s.replace(p, '')
 
    return s.lower().strip()

