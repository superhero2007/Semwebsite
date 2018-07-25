
## Abovelevel
def abovelevel(v, bound):
    return ((v > bound).astype(int).where(v.notnull(),np.NaN))
