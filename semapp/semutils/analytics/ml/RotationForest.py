from sklearn.metrics import classification_report
from sklearn.decomposition import PCA
from sklearn.tree import DecisionTreeClassifier
import numpy as np
from sklearn.model_selection import train_test_split
import pandas as pd
import datetime
import sys

class RotationForestClassifier (object):
    def __init__(self,tree_count = 25, feature_sample_size=1,verbose=0,max_depth=None, min_samples_split=2, min_samples_leaf=1, 
                 min_weight_fraction_leaf=0.0, max_features=None, random_state=None, max_leaf_nodes=None, class_weight=None, presort=False):
        self.tree_count = tree_count
        self.feature_sample_size = feature_sample_size
        self.verbose = verbose
        self.models = []
        self.r_matrices = []
        self.feature_subsets = []
        self.max_depth=None
        self.min_samples_split=2
        self.min_samples_leaf=1
        self.min_weight_fraction_leaf=0.0
        self.max_features=None
        self.random_state=None
        self.max_leaf_nodes=None
        self.class_weight=None
        self.presort=False
       

    def get_random_subset(self,iterable,k):
        subsets = []
        iteration = 0
        np.random.shuffle(iterable)
        subset = 0
        limit = len(iterable)/k
        while iteration < limit:
            if k <= len(iterable):
                subset = k
            else:
                subset = len(iterable)
            subsets.append(iterable[-subset:])
            del iterable[-subset:]
            iteration+=1
        return subsets

    def fit(self,x_train,y_train):
        if type(x_train)==pd.DataFrame:
            x_train = x_train.values
        if type(y_train)==pd.Series:
            y_train = y_train.values

        d = self.tree_count
        k = self.feature_sample_size
        models = []
        r_matrices = []
        feature_subsets = []
        for i in range(d):
            if self.verbose:
                print ('%s: Creating tree %s out of %s'%(datetime.datetime.today().replace(microsecond=0),i+1,d))
                sys.stdout.flush()
            x,_,_,_ = train_test_split(x_train,y_train,test_size=0.3,random_state=7)
            # Features ids
            feature_index = range(x.shape[1])
            # Get subsets of features
            random_k_subset = self.get_random_subset([i for i in feature_index],k)
            feature_subsets.append(random_k_subset)
            # Rotation matrix
            R_matrix = np.zeros((x.shape[1],x.shape[1]),dtype=float)
            pca_count = 0
            for each_subset in random_k_subset:
                pca_count +=1
                if self.verbose:
                    print ('%s: Tree-%s PCA-%s'%(datetime.datetime.today().replace(microsecond=0),i+1,pca_count))
                    sys.stdout.flush()

                pca = PCA()
                x_subset = x[:,each_subset]
                pca.fit(x_subset)
                for ii in range(0,len(pca.components_)):
                    for jj in range(0,len(pca.components_)):
                        R_matrix[each_subset[ii],each_subset[jj]] = pca.components_[ii,jj]

            x_transformed = x_train.dot(R_matrix)

            model = DecisionTreeClassifier(max_depth=self.max_depth, min_samples_split=self.min_samples_split, min_samples_leaf=self.min_samples_leaf, 
                                           min_weight_fraction_leaf=self.min_weight_fraction_leaf, max_features=self.max_features, random_state=self.random_state, 
                                           max_leaf_nodes=self.max_leaf_nodes, class_weight=self.class_weight, presort=self.presort)
            model.fit(x_transformed,y_train)
            models.append(model)
            r_matrices.append(R_matrix)
        self.models = models
        self.r_matrices = r_matrices
        self.feature_subsets = feature_subsets

    def predict(self,x):
        if type(x)==pd.DataFrame:
            x = x.values

        predicted_ys = []
        for i,model in enumerate(self.models):
            x_mod =  x.dot(self.r_matrices[i])
            predicted_y = model.predict(x_mod)
            predicted_ys.append(predicted_y)

        predicted_matrix = np.asmatrix(predicted_ys)
        final_prediction = []
        for i in range(x.shape[0]):
            pred_from_all_models = np.ravel(predicted_matrix[:,i])
            non_zero_pred = np.nonzero(pred_from_all_models)[0]  
            is_one = len(non_zero_pred) > len(self.models)/2
            final_prediction.append(is_one)

        return (np.array(final_prediction).astype(int))

    def predict_proba(self,x):
        if type(x)==pd.DataFrame:
            x = x.values
        predicted_ys = []
        for i,model in enumerate(self.models):
            x_mod =  x.dot(self.r_matrices[i])
            predicted_y = model.predict(x_mod)
            predicted_ys.append(predicted_y)

        predicted_matrix = np.asmatrix(predicted_ys)
        final_prediction = []
        for i in range(x.shape[0]):
            pred_from_all_models = np.ravel(predicted_matrix[:,i])
            non_zero_pred = np.nonzero(pred_from_all_models)[0]  
            proba = len(non_zero_pred) / len(self.models)
            final_prediction.append(proba)
        pred = np.array(final_prediction)
        return (np.array([1-pred,pred]).T)


    def model_worth(self,x,y):
        if type(x)==pd.DataFrame:
            x = x.values
        if type(y)==pd.DataFrame:
            y = y.values

        predicted_ys = []
        for i,model in enumerate(self.models):
            x_mod =  x.dot(self.r_matrices[i])
            predicted_y = model.predict(x_mod)
            predicted_ys.append(predicted_y)

        predicted_matrix = np.asmatrix(predicted_ys)
        final_prediction = []
        for i in range(len(y)):
            pred_from_all_models = np.ravel(predicted_matrix[:,i])
            non_zero_pred = np.nonzero(pred_from_all_models)[0]  
            is_one = len(non_zero_pred) > len(self.models)/2
            final_prediction.append(is_one)

        print (classification_report(y, final_prediction))

