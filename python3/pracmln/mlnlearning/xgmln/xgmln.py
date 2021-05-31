import random
from pracmln.structure.correlation.correlation_utils import database_to_dataframe, remove_predicates_from_database, formula_to_row, string_to_formula
from pracmln.structure.correlation.correlation import theils_u, generate_formulas_from_theils_u, correlation_matrix, formulas_from_correlation_matrix
from pracmln import Database, MLN
from pracmln import MLNLearn, MLNQuery
from . import xgmln_utils
from sklearn.metrics import log_loss
import tqdm
import pandasgui
import pandas as pd
import numpy as np
from pracmln.mln.methods import LearningMethods
from math import exp

class XGMLN:
    def __init__(self, mln, learning_rate, max_mlns=float("inf"), max_conjunctions=float("inf"), 
                 max_role_depth=float("inf"), n_best=5, min_score=0.2, verbosity=3) -> None:
        """
        Creates an instance for gradient boosted mlns. 
        """
        self.mln = mln
        self.learning_rate = learning_rate
        self.max_mlns = max_mlns
        self.max_conjunctions = max_conjunctions
        self.max_role_depth = max_role_depth
        self.current_mlns = 0
        self.verbosity = verbosity
        self.query = "object"
        self.n_best = n_best
        self.min_score = min_score
        self.db_weight_history = []
        self.db_pll_history = []
        
    def prep_scenes(self, scenes, weights):
        #load databases into usable forms
        dataframe = database_to_dataframe(dbs=scenes, mln=self.mln, db_weights=weights, replace_clusters=True)
        
        #select relevant rows
        dataframe = dataframe[["Predicate", "First Argument", "Second Argument", "weight"]]

        #remove the scene entries
        dataframe = xgmln_utils.remove_predicates_from_dataframe(["scene"], dataframe)
        
        return dataframe

    def fit(self, dbs, max_iterations=25):
        """
        Learns the mln
        """
        self.mln._rmformulas()
        self.mln = self.mln.materialize(*dbs, discard_unused_predicates=False)

        #initialize weights as all equal
        weights = np.full((len(dbs),), 1/len(dbs))

        cm, atoms = correlation_matrix(self.mln, dbs)
        formulas = formulas_from_correlation_matrix(self.mln, dbs, cm, atoms)
        

        if self.verbosity >= 1:
            pbar = tqdm.tqdm(desc="Learning Progress", total=max_iterations)

        for iteration in range(max_iterations):
            self.db_weight_history.append(weights.copy())
            #create an mln to model the data
            dataframe = self.prep_scenes(dbs, weights)

            #calculate the similarity of categories
            uc = theils_u(dataframe, weighted_observations=True)

            #generate formulas from similarities and ignore negative correlations
            mln_formulas = generate_formulas_from_theils_u(uc, n_best=self.n_best,
            positive_threshold=self.min_score, output=list,)

            #create an mln that learns this data from the similarities
            current_mln = self.mln.copy()
            current_mln._rmformulas()
            for formula in mln_formulas:
                current_mln << formula
            #dbpll_cg ausprobieren
            current_mln, learners = current_mln.learn(dbs, method=LearningMethods.clazz("DBPLL_CG"), 
                                            db_weights=weights, discard_unused_predicates=False,
                                            verbose=False, return_pll=True, qpreds=["object"])
            
            plls = np.zeros((len(dbs)))
            # nur die PLL des neuen MLNsund die gewichte multiplizieren
            for i, learner in enumerate(learners):
                weights[i] += (abs(learner._pseudo_log_likelihood))
                plls[i] = (abs(learner._pseudo_log_likelihood))
            weights /= sum(weights)
            self.db_pll_history.append(plls.copy())
            
            self.mln = xgmln_utils.merge_mlns(self.mln, current_mln)

            if self.verbosity >= 1:
                pbar.set_postfix(dict(mln_formulas=len(self.mln._formulas)))
                pbar.update()

    def predict(self, X):
        pass