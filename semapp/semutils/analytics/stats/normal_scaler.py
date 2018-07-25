import pdb
import numpy as np
import pandas as pd
from scipy.special import erfinv, erf
from scipy.stats import normaltest

class cdf_trans(object):
    def __init__(self, name=None, eps=1e-8, 
                 nan_policy='drop', trunc_normal=True, std_cut=3):
        """
        iparam name: Specific name for this transformation
        iparam eps: in case it is not trunc_normal this value helps to avoid the infinity
        iparam nan_policy: for now it just drops it
        iparam trunc_normal: if True it uses the truncated normal distribution
        iparam std_cut: the limit of the std for truncated normal distribution

	output: fit distribution
        """
        self.name = name
        self.eps = eps
        self.log_ = True
        self.nan_policy = nan_policy
        self.trunc_normal = trunc_normal
        self.std_cut = std_cut

    def _cdf(self, x):
        x = np.sort(x)
        p = 1. * np.arange(len(x)) / (len(x) - 1)
        return x, p   

    def _maping(self, x, y):
        xx = np.matrix(x)
        pp = np.matrix(y)
        
        x_tab = np.concatenate((xx.T, pp.T), axis=1)
        
        # TODO: invert the matrix and use unique command
        x_tab = pd.DataFrame(x_tab)
        x_tab.drop_duplicates(subset=0, keep='last', inplace=True)   

        fit_x = x_tab[0].values
        fit_y = x_tab[1].values
        return fit_x, fit_y

    
    def fit(self, x, a1=None, a2=None):

        # if the input is a pandas series
        if type(x) == pd.core.series.Series:
            msk = x.copy()
            if not x[x.isnull()].empty:
                if self.nan_policy == 'drop':
                    x = x.dropna()
                else:
                    raise ValueError('Define a policy for nan')
            x = x.values
            pdFlag = True
 
        else:
            msk = x.copy()
            if self.nan_policy == 'drop':
                x = x[~np.isnan(x)]
            else:
                if np.isnan(x).sum() != 0:
                    raise ValueError('Define a policy for nan')
            pdFlag = False

        if x.size==0:
            return msk            

        # log scale for non zero numbers.
        # if a1 is None:
        #     a1 = 1
        # if a2 is None:
        #     a2 = np.abs(2 * x.min()) + 0.01
        #     
        # self.a1 = a1
        # self.a2 = a2
        # # import pdb; pdb.set_trace()

        # # check if the log helps
        # norm_dist, _ = normaltest(x)
        # x_log = np.log(a1 * x + a2)
        # norm_dist_log, _ = normaltest(x_log)
        # if norm_dist < norm_dist_log:
        #     # print("Log didn't help")
        #     x_log = a1 * x + a2
        #     self.log_ = False
            
        # calculating the cdf
        x_c, p_c = self._cdf(x)
        
        phi_inv = lambda y:np.sqrt(2) * erfinv(2 * y - 1)
        phi = lambda y: (1 + erf(y / np.sqrt(2))) / 2
 
        # for truncated normal         
        if self.trunc_normal:
            a = -self.std_cut
            b = self.std_cut
            p_c_ = phi(a) + p_c * (phi(b) - phi(a))
            x_n = phi_inv(p_c_)
            
            # for finding the outliers
            # correcting for infinities 
            p_c[0] += self.eps
            p_c[-1] -= self.eps
            x_outs = phi_inv(p_c)
                              
        # for normal    
        else:
            # correcting for infinities 
            p_c[0] += self.eps
            p_c[-1] -= self.eps

            # converting p_c to normal x_n
            x_n = phi_inv(p_c)
            
            # for finding the outliers
            x_outs = x_n.copy()

        # removing the duplicates
        self.fit_x, self.fit_y = self._maping(x_c, x_n)       
        fit_x_outs, fit_y_outs = self._maping(x_c, x_outs)       

        self.outliers = np.concatenate((fit_x_outs[fit_y_outs < -self.std_cut], 
                                        fit_x_outs[fit_y_outs > self.std_cut]),
                                       )
                                        
        # matching x_n with x
        x_t = np.interp(x, self.fit_x, self.fit_y)

        if pdFlag:
            msk[msk.notnull()] = x_t
        else:
            msk[~np.isnan(msk)] = x_t
            
        return msk
    
    
    def transfer(self, x):
        if type(x) == pd.core.series.Series:
            msk = x.copy()
            if not x[x.isnull()].empty:
                if self.nan_policy == 'drop':
                    x = x.dropna()
                else:
                    raise ValueError('Define a policy for nan')
            x = x.values
            pdFlag = True
        else:
            msk = x.copy()
            x = x[~np.isnan(x)] 
        
        if x.size==0:
            return msk

        x_log = self.a1 * x + self.a2
        if self.log_:
            x_log = np.log(x_log)
        x_t = np.interp(x_log, self.fit_x, self.fit_y)
       
        if pdFlag:
            msk[msk.notnull()] = x_t
        else:
            msk[~np.isnan(msk)] = x_t            

        return msk

def test_nan():
    # test all nan 
    a = np.array(100 * [np.nan])
    b = pd.Series(a)
    x1 = cdf_trans().fit(a)    
    x2 = cdf_trans().fit(b)
    assert (x1[~np.isnan(x1)]).size == 0
    assert x2.dropna().empty
  
    # partially nan
    a = np.random.rand(1000)
    a[10] = a[50] = a[100] = np.nan
    b = pd.Series(a)
    x1 = cdf_trans().fit(a)
    x2 = cdf_trans().fit(b) 
    assert np.isnan(x1[10]) & np.isnan(x1[50]) & np.isnan(x1[100])
    
def test():
    test_nan()

if __name__=='__main__':
    test()
