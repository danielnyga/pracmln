import pandas as pd
import collections 
from pracmln.logic.common import Lit, GroundAtom, GroundLit
import plotly.graph_objects as go
import plotly.subplots

def replace_objects_with_clusters(df):
    """
    Takes a database as dataframe and replaces concrete objects with cluster like
    c0 to cn. Also adds the object(c0, object) rows.
    """

    #create cluster ids for the objects
    clusters = dict([(obj, "c"+str(idx)) for idx, obj in enumerate(df["First Argument"].unique())])

    for idx, row in df.iterrows():
        row["First Argument"] = clusters[row["First Argument"]]
    
    object_preds = [["object", clusters[obj], obj] for obj in clusters]
    return df.append(pd.DataFrame(data=object_preds, columns=df.columns))

def remove_predicates_from_dataframe(predicates, dataframe):
    """
    Removes every predicate in predicates from the dataframe
    predicates: a list of predicates
    dataframe: the dataframe to remove it from
    """
    return dataframe[~dataframe["Predicate"].isin(predicates)]

def dataframe_to_database(dataframe):
    result = []
    for idx, row in dataframe.iterrows():
        result.append(row["Predicate"] + "(" + row["First Argument"] + ", " + row["Second Argument"] + ")")
    return result

def merge_mlns(mln1, mln2):
    """
    Merges the formulas of mln2 into mln1
    """
    for idx, formula in mln2.iterformulas():
        added_formula = False
        for jdx, formula_ in mln1.iterformulas():
            if are_formulas_equal(formula, formula_):
                mln1._weights[jdx] =  float(mln1._weights[jdx]) + float(mln2.weights[idx])
                added_formula = True
            
        if not added_formula:
            mln1.formula(formula, mln2.weights[idx])
    return mln1

def are_formulas_equal(f1,f2):
    """
    Checks if the two formulas would result in an equal truth table
    by comparing the elements of their conjunctive normal forms with each other.
    """
    if isinstance(f1, Lit) or isinstance(f1, GroundAtom):
        f1 = [str(f1)]
    else:
        f1=list(map(lambda x: str(x), f1.cnf().children))
    if isinstance(f2, Lit) or isinstance(f2, GroundAtom):
        f2 = [str(f2)]
    else:
        f2=list(map(lambda x: str(x), f2.cnf().children))
    return collections.Counter(f1) == collections.Counter(f2)
    