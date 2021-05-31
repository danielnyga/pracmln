from . import xgmln
from pracmln.utils.project import MLNProject
from pracmln import MLN, Database, MLNQuery
from pracmln.structure.correlation.correlation_utils import database_to_dataframe, remove_predicates_from_database, formula_to_row, string_to_formula
from sklearn import metrics

import os
import plotly.express as px
import numpy as np
import tqdm
import pandas as pd

def eval_mln(mln, dbs, loading_bar=False):
    """
    Evaluates an mln with the evidence from the databases.
    mln: The mln which is to be evaluated
    dbs: The databases which will be tested
    loading_bar: Rather to show or not show a progress bar
    """

    #cm = pracmln.utils.eval.ConfusionMatrix()
    all_predictions, all_labels = [], []
    for db in tqdm.tqdm(dbs, desc="Evaluation Progress") if loading_bar else dbs:

        #Load labels from database
        df = database_to_dataframe(mln=mln, dbs=[db],replace_clusters=False)
        df = df [["Predicate", "First Argument", "Second Argument"]]

        #Remove evidence for asked predicate
        evidence = remove_predicates_from_database(["object", "scene"], db)
        db = Database(mln, evidence=evidence)

        #Run the query
        query = MLNQuery(mln=mln,db = db, verbose=False, multicore=False,
                                method="WCSP (exact MPE with toulbar2)",
                                queries=["object"], cw=True)
        query = query.run()

    
        #translate predictions dictionary to dataframe
        predictions = [formula_to_row(*string_to_formula(key)) for key,value in query.results.items() if value == 1]
        predictions = pd.DataFrame(data=predictions, 
                                   columns=["Predicate", "First Argument", "Second Argument"])

        #get the labels
        labels = df[df["Predicate"] == "object"]

        #sort both by the clusters
        labels = labels.sort_values(by="First Argument")
        predictions = predictions.sort_values(by="First Argument")

        #add results to confusion matrix
        #[cm.addClassificationResult(pred, truth) for pred, truth in zip(predictions["Second Argument"], labels["Second Argument"])]
        [(all_predictions.append(pred), all_labels.append(truth)) for pred, truth in zip(predictions["Second Argument"], labels["Second Argument"])]

    #cm.toPDF("results")
    cm = metrics.confusion_matrix(all_labels, all_predictions, normalize="true",
         labels=list(set(all_labels + all_predictions)))

    px.imshow(cm, x=list(set(all_labels + all_predictions)), 
                y=list(set(all_labels + all_predictions)),
                labels=dict(y="Ground Truth", x="Prediciton")).show()

def main():
    path =os.path.join("~","agki-tda", "pracmln", "examples", "object-recognition", 
    "object-recognition.pracmln")
    project = MLNProject().open(path)

    # The MLN template of the project is loaded as object
    mln = MLN(mlnfile=path + ":" + "object-detection.mln")
    # Load the database with training data
    dbs = Database.load(mln, dbfiles=path + ":" + "scenes-new.db")
    
    model = xgmln.XGMLN(mln=mln, learning_rate=0.1, verbosity=1)
    model.fit(dbs, max_iterations=20)

    px.imshow(np.array(model.db_weight_history).T, aspect="auto",
              labels=dict(x="Iteration", y="Database Index"),
              title="History of the weights of the databases").show()
    px.imshow(np.array(model.db_pll_history).T, aspect="auto",
              labels=dict(x="Iteration", y="Database Index"),
              title="History of the Pseudo Log Likelihoods of the databases").show()

    eval_mln(model.mln, dbs, loading_bar=True)
    model.mln.write()

if __name__ == "__main__":
    main()