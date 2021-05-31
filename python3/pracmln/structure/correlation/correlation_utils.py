# MLN Stuff
from pracmln.utils.project import MLNProject
from pracmln.utils.project import mlnpath
from pracmln.mln.database import parse_db
from pracmln.mln.base import parse_mln

import os
import numpy as np
import pandas as pd


def string_to_formula(formula_string):
    """
    Takes a formula from the MLN database and 
    extracts the predicate and the 1 to 2 arguments
    formulate_string: the string from the database
    """
    split = formula_string.split("(")
    predicate = split[0]
    arguments = split[1][:-1]
    if "," in arguments:
        arguments = arguments.split(",")
    else:
        arguments = [arguments]
    return predicate, arguments

def formula_to_vector(pred, args, database, mln):
    """
    Takes a formula and converts it to a 3d Vector, where 
    the number encodes the nth value of that dimension that belong to the feature.
    pred: The predicate of the formula
    args: The one ore two arguments of the predicate
    database: The database where this comes from
    mln: The mln that belong to this database
    """
    result = np.zeros(3)
    
    for idx, pn in enumerate(sorted(mln.prednames)):
        if pn == pred:
            result[0] = idx+1
            break

    for idx,arg in enumerate(args):
        for domain in database.domains.values():
            domain = sorted(domain)
            if arg in domain:
                result[idx+1] = domain.index(arg)+1
                break
    return result


def formula_to_row(pred,args,database=None,mln=None):
    """
    Takes a predicate and its arguments together with the database
    and return a list which cointains the Predicate, Domain of first Argument,
    First Argument, Domain of second Argument, Second Argument
    pred: The predicate of the formula
    args: The one ore two arguments of the predicate
    database: The database where this comes from
    mln: The mln that belong to this database
    """

    if database is not None and mln is not None:
        result = []

        result.append(pred)

        for arg in args:
            for domain,values in zip(database.domains, database.domains.values()):
                if arg in values:
                    result.append(domain)
                    result.append(arg)
                    break
        return result
    
    else:
        result = [pred]
        result.extend(args)
        return result

        
def databases_to_pointcloud(path):
    """
    Converts a database to a pointcloud, so it can be interacted with it graphically.
    path: The path to the database
    """
    project = MLNProject().open(path)
    dbs = project.dbs[0]        
    mln = project.mlns[0]

    pointcloud = []

    for db in dbs:
        for e in db.evidence:
            pred, args = string_to_formula(e)
            if pred != "scene":
                vector = formula_to_vector(pred,args,db,mln)
                pointcloud.append(vector)
    return np.array(pointcloud)

def database_to_dataframe(path=None, mln=None, dbs=None, amount=None, 
                          replace_clusters=True, mln_name=None, db_name=None,
                          db_weights=None):
    """
    Converts an MLN projects database to a dataframe containing the ground atoms
    of the mln. Then it infers the clusters to the actual objects they are.
    E. g.: c1 gets replaced by "Milk"
    path: The path to the database
    mln: If the project has been loaded, the desired mln
    dbs: If the project has been loaded, the desired databases
    amount: Take only the first amounth databases, if wanted
    replace_clusters: Replaces the cluster (c1, c2, c3,....) with the correct object
    mln_name: If the project has not been loaded, the name of the mln that will be used
    db_name: If the project has not been loaded, the name of the databases that will be used
    """
    if path:
        project = MLNProject().open(path)

        if mln_name:
            mln = project.mlns[mln_name]
        else:
            mln = list(project.mlns.values())[0]

        if db_name:
            dbs = project.dbs[db_name]
        else:
            dbs = list(project.dbs.values())[0]
        
        mln = parse_mln(mln)
        dbs = parse_db(mln, dbs)

    dataframe = []

    for idx, db in enumerate(dbs):
        if amount is not None and idx == amount:
            break
        for e in db.evidence:
            pred, args = string_to_formula(e)
            if db_weights is None:
                dataframe.append(formula_to_row(pred, args, db, mln))
            else:
                dataframe.append(formula_to_row(pred, args, db, mln) + [db_weights[idx]])

    if db_weights is None:
        df = pd.DataFrame(data=dataframe, 
            columns = ["Predicate", "Domain of first Argument", "First Argument",
                                    "Domain of second Argument", "Second Argument"])
    else:
            df = pd.DataFrame(data=dataframe, 
        columns = ["Predicate", "Domain of first Argument", "First Argument",
                                "Domain of second Argument", "Second Argument", "weight"])

    cluster_meaning = {}

    replaced_rows = []
    if replace_clusters:
        for index, row in df.iterrows():
            if row["Predicate"] == "scene":
                for _, elem in df.loc[index+1:].iterrows():
                    if elem["Predicate"] == "scene":
                        break
                    if elem["Predicate"] == "object":
                        cluster_meaning[elem["First Argument"]] = elem["Second Argument"]

            if row["Second Argument"] is not None:
                row["First Argument"] = cluster_meaning[row["First Argument"]]
            replaced_rows.append(row.to_numpy())
        df = pd.DataFrame(data=replaced_rows, columns=df.columns)
    
    return df


def dataframe_to_pointcloud(dataframe):
    """
    Takes a dataframe generated from an MLN database and converts it
    to a pointcloud where the ground atoms are encoded via the pandas codes
    dataframe: The dataframe that will be converted
    """
    ps = pd.Categorical(dataframe["Predicate"]).codes
    fs = pd.Categorical(dataframe["First Argument"]).codes
    ss = pd.Categorical(dataframe["Second Argument"]).codes
    result = [np.array(x) for x in zip(ps,fs,ss)]
    return np.array(result)    

def remove_predicates_from_database(predicates, database):
    """
    Removes every predicate in predicates from the database evidence
    and returns a dictionary of formulas which remain with their truth values.
    (This is the input for pracmln.Databse)
    predicates: a list of predicates
    database: the database to remove it from
    """
    result = []
    for evidence in database.evidence:
        predicate, _ = string_to_formula(evidence)
        if predicate not in predicates:
            result.append(evidence)

    return dict(zip(result, [True for _ in result]))