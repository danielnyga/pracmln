from sklearn.base import BaseEstimator, TransformerMixin
import numpy as np

class MLNCover(BaseEstimator, TransformerMixin):
    """
    Calculates a cover for the MLN Ground Atoms in which they overlap given
    the clusters of every detectet Object.
    """
    def __init__(self):
        pass

    def fit(self, X, y=None):
        pass
    
    def transform(self, X, y=None):
        pass

    def fit_transform(self, X, y=None):
        """
        Takes a dataframe generate by the database to dataframe method and generates
        a cover that fits in the mapper pipeline.
        X: the pandas dataframe which has at least the columns 
           ["Predicate", "First Argument", "Second Argument"]
        """
        subcovers = X.loc[X["Predicate"] == "object"]["Second Argument"].unique().tolist()
        Xt = np.zeros(shape=(len(X), len(subcovers)), dtype=bool)

        for index, row in X.iterrows():
            if row["Second Argument"] is not None:
                cover_idx = subcovers.index(row["First Argument"])
                Xt[index][cover_idx] = True

            if row["Predicate"] == "object":
                Xt[index] = np.ones(shape=(len(subcovers),), dtype=bool)
        
        return Xt