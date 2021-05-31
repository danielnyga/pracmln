# MLN Stuff
from pracmln.utils.project import mlnpath

import os
import sys
import numpy as np
import pandas as pd

# ML tools
import sklearn
import sklearn.cluster
from .correlation_utils import database_to_dataframe, dataframe_to_pointcloud
from . import cover

from . import plotting
import plotly.express as px
import itertools
from collections import defaultdict
import argparse
import pracmln
import pracmln.mln.mlnpreds
import tqdm
from pracmln.logic.common import GroundLit, GroundAtom, Conjunction, Lit
import scipy.stats
from pracmln.mlnlearning.xgmln.xgmln_utils import are_formulas_equal
from matplotlib import pyplot as plt
from scipy.cluster.hierarchy import dendrogram
from sklearn.cluster import AgglomerativeClustering

def correlation_matrix(mln:pracmln.MLN, dbs:list, db_weights=None, 
                       correlation_function=lambda x,y: scipy.stats.pearsonr(x,y)[0],
                       cluster_domain="cluster", closed_world_assumption=False, return_feature_matrix=False):
    """Compute correlation of all atoms in the database. Resolves all linking predicates.
       Returns a correlation matrix and the meaning of each row/column"""
    dbs = dbs.copy()

    all_clusters = []
    placeholder = "?c"

    #get all predicates that are not dependent on a cluster
    unaffected_predicates = [pred for pred in mln.predicates if cluster_domain not in pred.argdoms]
    unaffected_prednames = [pred.name for pred in unaffected_predicates]

    for db in dbs:
        #get all clusters that exist in this domain
        current_clusters = db.domains[cluster_domain]
        
        #parse all evidence to literals
        current_atoms = []
        for atom in db.evidence:
            true, predname, args = mln.logic.parse_literal(atom)
            atom = mln.logic.gnd_atom(predname, args, mln)
            current_atoms.append(atom)

        for cluster in current_clusters:
            #get all atoms that describe stuff about this cluster
            related_atoms = [ca for ca in current_atoms if cluster in ca.args]
            related_atoms.extend([ca for ca in current_atoms if ca.predname in unaffected_prednames])
            
            #replace the cluster index by a generic one to compare later
            for atom in related_atoms:
                for idx, arg in enumerate(atom.args):
                    if arg in current_clusters:
                        atom.args[idx] = placeholder

            all_clusters.append(related_atoms)

    #construct unified db for utilities
    unified_db = dbs[0].union(dbs[1:], mln)

    #get all domain elementss
    all_domain_elements = []
    [all_domain_elements.extend(e) for e in unified_db.domains.values()]

    #get all now unique atoms
    all_atoms = []
    for cluster in all_clusters:
        for atom in cluster:
            if atom not in all_atoms:
                all_atoms.append(atom)
    
    all_atoms.sort(key=lambda x: str(x))

    #construct feature_matrix
    if not closed_world_assumption:
        feature_matrix = np.zeros((len(all_clusters), len(all_atoms)))
    else:
        feature_matrix = np.full((len(all_clusters), len(all_atoms)), -1)

    #fill feature matrix
    for idx, cluster in enumerate(all_clusters):
        for jdx, atom in enumerate(all_atoms):
            feature_matrix[idx, jdx] = int(atom in cluster)

    correlation_matrix = np.zeros((len(all_atoms), len(all_atoms)))

    for idx, feature in enumerate(feature_matrix.T):
        for jdx, feature_dash in enumerate(feature_matrix.T):
            if all_atoms[idx].predname != all_atoms[jdx].predname:
                correlation_value = correlation_function(feature, feature_dash)
                correlation_matrix[idx,jdx] = correlation_value

    

    #px.imshow(correlation_matrix, x=[str(x) for x in all_atoms], y=[str(x) for x in all_atoms]).show()

    if return_feature_matrix:
        return correlation_matrix, all_atoms, feature_matrix
    else:
        return correlation_matrix, all_atoms

def is_in_with_custom_comperator(element, sequence, comperator):
    for element_ in sequence:
        if comperator(element, element_):
            return True
    return False


def correlation_clusters(mln:pracmln.MLN, dbs:list, feature_matrix, correlation_matrix, atoms, threshold=.3):

    #a class to simplify the symetrical property of the correlation values
    class s:
        def __init__(self, i, j, score):
            self.i, self.j, self.score = i, j, score

        def __eq__(self, other):
            return (self.i == other.i and self.j == other.j) or (self.i==other.j and self.j==other.i)

        def __hash__(self):
            return hash((min(i,j), max(i,j)))
        
        def __str__(self):
            return str([self.i,self.j, self.score])
        
        def __repr__(self):
            return self.__str__()


    #feature matrix is X
    p = len(correlation_matrix) #p is the number of dimensions

    #use clusters as dict so the features that are described can be reconstructed
    clusters = dict(zip([str(atom) for atom in atoms], np.zeros(p, dtype=int)))
    gamma = 0
    z = p
    
    correlations = set()

    #create correlations s_ij (step 3 of the algorithm)
    for i, i_feature in enumerate(clusters.keys()):
        for j, j_feature in enumerate(list(clusters.keys())[i:]):
            correlations.add(s(i_feature,j_feature,correlation_matrix[i,j]))

    #sort set s. t. the s with the highest scores come first
    sorted_correlations = sorted(correlations, key=lambda x: -abs(x.score))


    for idx, current_s in enumerate(sorted_correlations):

        #case one of step 5
        if z == 0 or abs(current_s.score) < threshold:
            return clusters
        
        #case two of step 5
        if clusters[current_s.i] == 0 and clusters[current_s.j] == 0:
            gamma = gamma + 1
            clusters[current_s.i] = gamma
            clusters[current_s.j] = gamma
            z = z - 2
        
        #case 3 of step 5
        elif clusters[current_s.i] != 0 and clusters[current_s.j] == 0:
            clusters[current_s.j] = clusters[current_s.i]
            z = z - 1
        
        #case 4 of step 5
        elif clusters[current_s.i] == 0 and clusters[current_s.j] != 0:
            clusters[current_s.i] = clusters[current_s.j]
            z = z - 1

        #case 5 of step 5
        elif clusters[current_s.i] != 0 and clusters[current_s.j] != 0 and clusters[current_s.i] != clusters[current_s.j]:
            #forall l with cl = cjk
            cluster_of_j = clusters[current_s.j]
            cluster_members = [c for c in clusters if c == cluster_of_j]
            for cluster_member in cluster_members:
                clusters[cluster_member] = clusters[current_s.i]

        
def formulas_from_correlation_clusters(mln:pracmln.MLN, dbs:list, correlation_clusters, correlation_matrix, atoms):
    inverse_correlation_clusters = defaultdict(list)
    for key, value in correlation_clusters.items():
        inverse_correlation_clusters[value].append(key)
    
    del inverse_correlation_clusters[0]
    chosen_formulas = []

    for correlated_atoms in tqdm.tqdm(inverse_correlation_clusters.values(), desc="Generating formulas"):
        if len(correlated_atoms) > 1:

            correlated_atoms = [mln.logic.Lit(*mln.logic.parse_literal(correlated_atom),mln) 
                                for correlated_atom in correlated_atoms]
            
            grouped_atoms = defaultdict(list)

            for atom in correlated_atoms:
                grouped_atoms[atom.predname].append(atom)
                negated_atom = atom.copy()
                negated_atom.negated = not negated_atom.negated
                grouped_atoms[atom.predname].append(negated_atom)
            
            #construct all domain combionations to adjust for formula length
            all_domain_combinations = []

            for number_of_domains in range(2, len(correlated_atoms)+1):
                all_domain_combinations.extend(list(itertools.combinations(grouped_atoms.keys(), 
                                                                           number_of_domains)))

            for domain_combination in all_domain_combinations:
                
                current_grouped_atoms = dict()
                for domain in domain_combination:
                    current_grouped_atoms[domain] = grouped_atoms[domain]

                #only look at formulas of length > 1
                if len(current_grouped_atoms) > 1:
                    
                    #construct all possible formulas
                    all_combinations = itertools.product(*list(current_grouped_atoms.values()))

                    #for every possible formulas calculate if this makes sense according to the correlation values
                    #and discard or keep it respectivly
                    for combination in all_combinations:
                        acceptable_formula = True

                        for idx in range(len(combination)-1):
                            first_pred = combination[idx]
                            second_pred = combination[idx+1]

                            not_negated_first_pred = first_pred.copy()
                            not_negated_first_pred.negated = False

                            not_negated_second_pred = second_pred.copy()
                            not_negated_second_pred.negated = False

                            first_pred_cm_idx = atoms.index(not_negated_first_pred)
                            second_pred_cm_idx = atoms.index(not_negated_second_pred)
                            correlation_score = correlation_matrix[first_pred_cm_idx, second_pred_cm_idx]

                            if ((correlation_score < 0 and first_pred.negated == second_pred.negated)
                                or (correlation_score > 0 and first_pred.negated != second_pred.negated)):
                                acceptable_formula = False

                        if acceptable_formula:
                            chosen_formulas.append(mln.logic.Conjunction(combination, mln))

    return chosen_formulas


def formulas_from_correlation_matrix(mln:pracmln.MLN, dbs:list, correlation_matrix, atoms, positive_threshold=0.5, negative_threshold=-0.5):
    generated_formulas = []
    for idx, row in enumerate(correlation_matrix):
        positive_correlations = [jdx for jdx,value in enumerate(row) if value > positive_threshold and jdx!=idx]
        negative_correlations = [jdx for jdx,value in enumerate(row) if value < negative_threshold]
        
        #never correlate gnd atoms with the same predicate name


        #create conjunctions (e. g. (a and b))
        gf = [Conjunction([Lit(predname=atoms[idx].predname, args=atoms[idx].args, negated=False, mln=mln), 
                           Lit(predname=atoms[jdx].predname, args=atoms[jdx].args, negated=False, mln=mln)], mln) 
                          for jdx in positive_correlations if atoms[idx].predname != atoms[jdx].predname]
        generated_formulas.extend(gf)        

        #create the complete negated conjunctions (e. g. (not a and not b)) because the correlation means that they
        #are most of the times equal
        gf = [Conjunction([Lit(predname=atoms[idx].predname, args=atoms[idx].args, negated=True, mln=mln), 
                           Lit(predname=atoms[jdx].predname, args=atoms[jdx].args, negated=True, mln=mln)], mln) 
                          for jdx in positive_correlations if atoms[idx].predname != atoms[jdx].predname]
        generated_formulas.extend(gf)      

        #create negated conjunctions (e. g. (a and not b))
        #here we dont need the other case because it will get added later because of the symetry of the matrix
        gnf = [Conjunction([Lit(predname=atoms[idx].predname, args=atoms[idx].args, negated=False, mln=mln),
                            Lit(predname=atoms[jdx].predname, args=atoms[jdx].args, negated=True, mln=mln)], mln) 
               for jdx in negative_correlations if atoms[idx].predname != atoms[jdx].predname]
        generated_formulas.extend(gnf)       

    selected_formulas = []
    
    for formula in generated_formulas:
        if not is_in_with_custom_comperator(formula, selected_formulas, are_formulas_equal):
            selected_formulas.append(formula)

    return selected_formulas


def formulas_from_correlation_matrix_discriminative(mln:pracmln.MLN, dbs:list, correlation_matrix, atoms, query = "object", 
    positive_threshold=0.3, negative_threshold=-0.3, max_atoms_per_pred=10, use_negated_query=True, max_formula_length = 4):
    #get rows of matrix that describe the query
    query_atoms = [atom for atom in atoms if atom.predname == query]
    query_rows = [row for idx, row in enumerate(correlation_matrix) if atoms[idx].predname == query ]
    
    generated_formulas = []

    for idx, (row, query_atom) in tqdm.tqdm(enumerate(zip(query_rows, query_atoms)), desc="Generating Formulas", total=len(query_rows)):

        #get all atoms that have a correlation score < negative_threshhold or > positive_threshhold
        relevant_atoms = []
        for jdx, correlation_value in enumerate(row):
            other_atom = atoms[jdx]
            if other_atom.predname != query and (correlation_value > positive_threshold or correlation_value < negative_threshold):
                relevant_atoms.append((other_atom, correlation_value))

        #take the max_atoms_per_pred best atoms if they exceed the amount of allowed atoms
        #sort by importance
        relevant_atoms = sorted(relevant_atoms, key=lambda x: abs(x[1]))

        #remove correlation_value
        relevant_atoms = [rv[0] for rv in relevant_atoms]

        #take n best
        relevant_atoms = relevant_atoms[-max_atoms_per_pred:]
        

        grouped_atoms = defaultdict(list)

        for atom in relevant_atoms:
            grouped_atoms[atom.predname].append(atom)
        
        all_domain_combinations = []

        for number_of_domains in range(1, min(len(relevant_atoms)+1, max_formula_length+1)):
                all_domain_combinations.extend(list(itertools.combinations(grouped_atoms.keys(), 
                                                                           number_of_domains)))


        for domain_combination in all_domain_combinations:
            current_grouped_atoms = dict()
            for domain in domain_combination:
                current_grouped_atoms[domain] = grouped_atoms[domain]

                #construct all possible formulas
                all_combinations = itertools.product(*list(current_grouped_atoms.values()))

                #generate every possible formula that makes sense according to the correlation value
                for combination in all_combinations:
                    formula = [Lit(predname=query_atom.predname, args=query_atom.args, negated=False, mln=mln)]
                    negated_formula = [Lit(predname=query_atom.predname, args=query_atom.args, negated=True, mln=mln)]
                    for kdx, combi_atom in enumerate(combination):
                        
                        correlation_value = row[atoms.index(combi_atom)]

                        #the case for (a and b) and (not a and not b)
                        if correlation_value > 0:
                            formula.append(Lit(predname=combi_atom.predname, args=combi_atom.args, negated=False, mln=mln))
                            negated_formula.append(Lit(predname=combi_atom.predname, args=combi_atom.args, negated=True, mln=mln))
                        
                        #the case for (not a and b) and (a and not b)
                        if correlation_value < 0:
                            negated_formula.append(Lit(predname=combi_atom.predname, args=combi_atom.args, negated=False, mln=mln))
                            formula.append(Lit(predname=combi_atom.predname, args=combi_atom.args, negated=True, mln=mln))
                        
                    generated_formulas.append(mln.logic.Conjunction(formula, mln))
                    if use_negated_query:
                        generated_formulas.append(mln.logic.Conjunction(negated_formula, mln))

    selected_formulas = []
    for formula in generated_formulas:
        if not is_in_with_custom_comperator(formula, selected_formulas, are_formulas_equal):
            selected_formulas.append(formula)

    return selected_formulas


def theils_u(X, y=None, weighted_observations=False):
    """
    Calculates the occurencies of an object given a predicate.
    E. g. the amount of time cereals where observed when something big was found
    X: The dataframe of an MLN and its database
    y: Will be ignored, is listed only for interface reasons
    """

    # contstruc a the columns for a new dataframe such that every predicate has an
    # every object as "feature" 
    columns = ["Predicate", "Second Argument"]
    objects = X.loc[X["Predicate"] != "scene"]["First Argument"].unique()
    columns.extend(objects)

    #the new dataframe
    data = []

    #for every predicate
    for predicate in X["Predicate"].unique():

        #skip scene because thats just a delimiter
        if not predicate == "scene":

            #get all rows of this predicate
            relevant_rows = X.loc[X["Predicate"] == predicate]

            #for every observation of the current predicate
            for element in relevant_rows["Second Argument"].unique():

                #the row for the new dataframe begins with predicate and predicate value 
                row = [predicate, element]

                #for every object calculate how often the predicate were true for it and
                # append it to the current row
                for obj in objects:
                    posterior = relevant_rows.loc[(relevant_rows["First Argument"] == obj) &
                        (relevant_rows["Second Argument"] == element)]
                    if weighted_observations:
                        row.append(sum(posterior["weight"]))
                    else:
                        row.append(len(posterior))

                #Normalize
                if not weighted_observations:
                    max_v = max(row[2:])
                    row[2:] = list(map(lambda x: x/max_v, row[2:]))
                data.append(row)

    dataframe = pd.DataFrame(data=data, columns=columns)
    dataframe = dataframe[dataframe["Predicate"] != "object"]
    return dataframe

def generate_formulas_from_theils_u(df, positive_threshold=0.8, negative_threshold = 0.2,
                                    output=str, n_best=None):
    """
    Takes the result from theils u and converts it into MLN formulas which are most likely
    to have a high value.
    df: Result dataframe from theils u
    positive_threshhold: The threshhold at which a formula will be included
    negative_threshhold: If the value of a formula is below this, the negation of the formula
                         will be included
    n_best: Activates the option to chose the the n best formulas (according to the correlation). 
            Can return less than n formulas, if none of them have a better score then positive_threshold.
    output: string or list. String is for direct parsing into a database, list is for further
            processing of the data.
    """

    #dicts which contain the relevant formulas
    formulas = dict()
    negated_formulas = dict()

    #initialize them for every objects
    for obj in df.columns[2:]:
        formulas[obj] = []
        negated_formulas[obj] = []

    #for every row (atom) in the df, append predicate and attribute to the dict entry
    #if they are relevant
    for _, row in df.iterrows():
        current_predicate = row[0]
        current_attribute = row[1]

        #calculate order of the weights for n_best selection
        ordered_scores = sorted(row[2:].copy())

        #go through every object and get the correlation value 
        for obj, value in zip(df.columns[2:], row[2:]):
            if n_best is not None:
                #select the atoms with a weight higher then the n best weights
                if value >= ordered_scores[-n_best] and value >= positive_threshold:
                    formulas[obj].append([current_predicate, current_attribute])
            else:
                if value >= positive_threshold:
                    formulas[obj].append([current_predicate, current_attribute])
                elif value <= negative_threshold:
                    negated_formulas[obj].append([current_predicate, current_attribute])

    #for every formula create the MLN formula
    result = []
    for obj, formula in zip(formulas.keys(), formulas.values()):
        conjuncts = defaultdict(list)
        conjuncts["object"] = ["object(?c," + obj + ")"]
        for atom in formula:
            conjuncts[atom[0]].append(atom[0] + "(?c," + atom[1] + ")")
        result.extend(list(itertools.product(*conjuncts.values())))

    #for every negative correlation create a negated formula
    negation_result = []
    for obj, formula in zip(negated_formulas.keys(), negated_formulas.values()):
        conjunction = "object(?c," + obj + ")"
        for atom in formula:
            conjunction += " ^ !" + atom[0] + "(?c," + atom[1] + ")"
        negation_result.append([conjunction])



    #Create the desired return value
    mln_formulas = [] if output == list else "" 
    for formula in result + negation_result:
        row = "0 "
        for atom in formula:
            if row == "0 ":
                row += atom
            else:
                row += " ^ " + atom

        if output == list:
            mln_formulas.append(row)
        else:
            mln_formulas += row + "\n"

    return mln_formulas

def main(args):
    bar = tqdm.tqdm(desc="Progess", total= 4 if args.plot else 3)
    # The path to the MLN project
    # path = os.path.join("~","agki-tda", "pracmln", "examples", "object-recognition", 
    # "object-recognition.pracmln")

    #Prep the data and organize it
    dataframe = database_to_dataframe(args.mlnproject)
    dataframe = dataframe[["Predicate", "First Argument", "Second Argument"]]
    bar.update(1)

    #calculate the similarity of categories
    uc = theils_u(dataframe)

    #generate formulas from similarities
    mln_formulas = generate_formulas_from_theils_u(uc)
    bar.update(1)

    #write formulas to file
    with open(args.outputfile, "w") as f:
        f.write(mln_formulas)
        bar.update(1)

    #plot everything
    if args.plot:
        #calculate the cover of the mln dataframe
        covers = cover.MLNCover().fit_transform(dataframe)
        plotting.plot_dataframe_cover(dataframe, covers).show()
        plotting.plot_theils_u(uc).show()
        bar.update(1)

    
    if args.learn:
        learner = pracmln.MLNLearn(db=dbs, method="BPLL_CG", multicore=True, mln=mln, verbose=True)
        mln = learner.run()
        with open(args.learn, "w") as f:
            mln.write(f)


    


if __name__ == "__main__":

    #Handling input arguments
    parser = argparse.ArgumentParser(description="""Calculates formulas for an MLN
    based on the covariance of the predicates and the objects.""")
    parser.add_argument("--mlnproject", type=str, help="Path to the MLN project")
    parser.add_argument("--outputfile", type=str, help="File to write the MLN formulas in")
    parser.add_argument("--plot", action="store_true", help="Rather to plot the statistics of the MLN or not")
    parser.add_argument("--learn", required=False, type=str, 
                        help="""Rather themformulas should be learned and if 
                             so the save file of the mln""")
    args = parser.parse_args()
    
    main(args)