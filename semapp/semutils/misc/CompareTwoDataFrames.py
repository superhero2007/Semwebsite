import pandas as pd
import os
import re
import sys


if __name__ == '__main__':
    file1 = sys.argv[1]
    file2 = sys.argv[2]

    df1 = pd.read_csv(file1)
    #df1.sort('AcceptedDate',inplace=True)
    df2 = pd.read_csv(file2)
    #df2.sort('AcceptedDate',inplace=True)

    df2 = df2[df1.columns] # reorder columns to match
    column_check = ((df1!=df2)&(df1==df1)&(df2==df2)).any(0)
    print ('Differences:')
    diff_cols = column_check[column_check==True]
    print (diff_cols)
    differences1 = {}
    differences2 = {}
    for col in diff_cols.index:
        d_mask = ((df1[col]!=df2[col])&(df1[col]==df1[col])&(df2[col]==df2[col]))
        differences1[col] = df1[d_mask][col]
        differences2[col] = df2[d_mask][col]
