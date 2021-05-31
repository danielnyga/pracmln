from .correlation import (theils_u, generate_formulas_from_theils_u, correlation_matrix, 
                          formulas_from_correlation_matrix, correlation_clusters,
                          formulas_from_correlation_clusters, formulas_from_correlation_matrix_discriminative)
from pracmln import Database
from pracmln import MLN
from pracmln.utils import eval
#import pracmln.Database
#import pracmln.MLN
#import pracmln.utils.eval
import os
import pracmln
from .correlation_utils import database_to_dataframe, string_to_formula, formula_to_row, remove_predicates_from_database
import time
from sklearn import metrics
from . import plotting
import pandas as pd
import tqdm
import plotly.express as px

def eval_mln(mln, dbs, loading_bar=False, query="object", cluster_domain="cluster"):
    """
    Evaluates an mln with the evidence from the databases.
    mln: The mln which is to be evaluated
    dbs: The databases which will be tested
    loading_bar: Rather to show or not show a progress bar
    """

    #cm = pracmln.utils.eval.ConfusionMatrix()
    all_predictions, all_labels = [], []
    dbs = dbs.copy()


    for db in tqdm.tqdm(dbs, desc="Evaluation Progress for " + query) if loading_bar else dbs:
        #copy db and retract the query
        original_db = db.copy()
        db.retractall(query)

        #Run the query
        mln_query = pracmln.MLNQuery(mln=mln,db = db, verbose=False, multicore=False,
                                method="WCSP (exact MPE with toulbar2)",
                                queries=[query], cw=False)
        mln_query = mln_query.run()
        #for every cluster get the label and the prediction
        for cluster in original_db.domain(cluster_domain):
            labels = [atom for atom,truth in list(original_db.gndatoms([query])) if cluster in mln.logic.parse_literal(atom)[2]]
            label = labels[0]
            true, predname, args = mln.logic.parse_literal(label)
            label, = [arg for arg in args if arg!=cluster]


            predictions = [atom for atom in [key for key, value in mln_query.results.items() if value==1] if cluster in mln.logic.parse_literal(atom)[2]]
            prediction = predictions[0]
            true, predname, args = mln.logic.parse_literal(prediction)
            prediction, = [arg for arg in args if arg!=cluster]
            all_predictions.append(prediction)
            all_labels.append(label)


        #[cm.addClassificationResult(pred, truth) for pred, truth in zip(predictions["Second Argument"], labels["Second Argument"])]
        
    #cm.toPDF("results")
    if len(all_labels) > 0:
        cm = metrics.confusion_matrix(all_labels, all_predictions, normalize="true",
            labels=list(set(all_labels + all_predictions)))

        px.imshow(cm, x=list(set(all_labels + all_predictions)), 
                    y=list(set(all_labels + all_predictions)),
                    labels=dict(y="Ground Truth", x="Prediciton"), title="Query: " + query).show()


def train_and_eval(path, mln_name=None, db_name=None, use_correlation=True):
    """
    Loads, trains and evaluates an MLN
    path: The path to the mlnproject
    mln_name: The name of the MLN
    db_name: The name of the database on which data shall be trained
    """

    #Prep the data and organize it
    dataframe = database_to_dataframe(path, mln_name=mln_name,
                                        db_name=db_name)
    dataframe = dataframe[["Predicate", "First Argument", "Second Argument"]]

    # # The MLN template of the project is loaded as object
    mln = pracmln.MLN.load(path + ":" + mln_name)
    
    # # Load the database with training data
    dbs = pracmln.Database.load(mln, path + ":" + db_name)

    if use_correlation:
        #calculate the similarity of categories
        uc = theils_u(dataframe)

        #generate formulas from similarities
        mln_formulas = generate_formulas_from_theils_u(uc, positive_threshold=0.5,
                                                    negative_threshold=0, output=list)

        #clear old formulas, but not predicates
        mln._rmformulas()

        for formula in tqdm.tqdm(mln_formulas, desc="Writing formulas"):
            mln << formula
    
    print("start learning")
    start = time.perf_counter()

    if use_correlation:
        learner = pracmln.MLNLearn(db=dbs, method="BPLL_CG", multicore=True, mln=mln, verbose=True)
    else:
        learner = pracmln.MLNLearn(db=dbs, method="BPLL", mln=mln, verbose=True)
    mln = learner.run()
    end = time.perf_counter()
    print(f"learning took {end - start:0.4f} seconds")
    with open("learned_" + mln_name,"w") as f:
        mln.write(f)

    mln = pracmln.MLN.load("learned_" + mln_name)
    eval_mln(mln, dbs, loading_bar=True)

def train_and_eval_new(path, mln_name=None, db_name=None):

    # # The MLN template of the project is loaded as object
    mln = pracmln.MLN.load(path + ":" + mln_name)
    
    # # Load the database with training data
    dbs = pracmln.Database.load(mln, path + ":" + db_name)


    #calculate the similarity of categories
    cm, atoms, fm = correlation_matrix(mln, dbs, return_feature_matrix=True)

    mln_formulas = formulas_from_correlation_matrix_discriminative(mln, dbs, cm, atoms)

    # clusters = correlation_clusters(mln, dbs, fm, cm, atoms, threshold=0.35)
    
    # mln_formulas = formulas_from_correlation_clusters(mln, dbs, clusters, cm, atoms)

    #clear old formulas, but not predicates
    mln._rmformulas()

    for formula in tqdm.tqdm(mln_formulas, desc="Writing formulas"):
        mln.formula(formula)
    
    print("start learning")
    start = time.perf_counter()

    learner = pracmln.MLNLearn(db=dbs, method="DBPLL_CG", multicore=False, mln=mln, verbose=True, qpreds="object")

    mln = learner.run()
    end = time.perf_counter()
    print(f"learning took {end - start:0.4f} seconds")
    with open("learned_" + mln_name,"w") as f:
        mln.write(f)

    mln = pracmln.MLN.load("learned_" + mln_name)

    eval_mln(mln, dbs, loading_bar=True, query="object")

def main():
    # The path to the MLN project

    work_list = [(os.path.join("~","agki-tda", "pracmln", "examples", "object-recognition", 
    "object-recognition.pracmln"), "object-detection.mln", "scenes-new.db"),]
    # work_list = [(os.path.join("~","agki-tda", "pracmln", "examples", "alarm", 
    # "alarm.pracmln"), "alarm-noisyor.mln", "query2.db"),]


    for (path, mln_name, db_name) in work_list:
        train_and_eval_new(path, mln_name, db_name)



if __name__ == "__main__":
    main()