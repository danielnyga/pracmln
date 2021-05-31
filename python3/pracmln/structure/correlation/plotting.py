import plotly
import plotly.express as px
import plotly.graph_objects as go

import pracmln
import pandas as pd
import numpy as np
import collections
from sklearn import metrics

def plot_ground_atoms(dataframe):  
    """
    Plot the ground atoms as scatter plot.
    dataframe: The dataframe of an MLN
    """
    dataframe = dataframe.loc[dataframe["Domain of first Argument"] != "scene"]
    dataframe = dataframe.rename(columns={"First Argument" : "Cluster"})
    fig = px.scatter_3d(data_frame=dataframe, x="Predicate", 
        y="Cluster", z="Second Argument", title="Ground Atoms of MLN")
    return fig

def plot_dataframe_cover(dataframe, cover):
    """
    Plots the coverings as connected point cloud.
    dataframe: The dataframe of an MLN
    cover: The covers of the MLN as boolean matrix of shape len(dataframe) * len(objects)
    """
    layout = dict(title="Covers of the MLN")
    fig = go.Figure(layout=layout)
    names = dataframe.loc[dataframe["Predicate"] == "object"]["Second Argument"].unique().tolist()
    subcovers = [pd.DataFrame(columns=dataframe.columns)] * cover.shape[1]
    for idx, row in dataframe.iterrows():
        idxs = [i for i,x in enumerate(cover[idx]) if x]
        if len(idxs) == 1:
            row["First Argument"] = names[idxs[0]]
        elif len(idxs) > 1:
            row["First Argument"] = row["Second Argument"]
        for i in idxs:
            subcovers[i] = subcovers[i].append(row)
    
    for idx, subcover in enumerate(subcovers):
        fig.add_trace(go.Scatter3d(x=subcover["Predicate"], 
            y=subcover["First Argument"], z=subcover["Second Argument"],
            name="Cover of " + names[idx]))

    return fig


def plot_cluster(pointcloud, clusters):
    colored_pointcloud = []
    for point, cluster in zip(pointcloud, clusters):
        colored_pointcloud.append(np.append(point,cluster))
    
    clusters = np.array(colored_pointcloud)
    fig = px.scatter_3d(x=clusters[:,0], y=clusters[:,1], z=clusters[:,2], 
            color=clusters[:,3], title="Clustering of Ground Atoms")
    return fig

def plot_theils_u(uc):
    """
    Plots the occurencies of objects in an MLN given their predicates.
    A scatter plot for exact introspection and a heatmap for overall view is produced.
    uc: The preprocessed dataframe of an MLN
    """
    layout = dict()
    fig = go.Figure(layout=layout)
    fig = plotly.subplots.make_subplots(rows=2, cols=1, 
                                        specs=[[{"type" : "scatter3d"}],
                                               [{"type" : "image"}]],)
    x, z = [], []
    for idx, row in uc.iterrows():
        visible = True #if idx % int(len(uc)/4) == 0 else "legendonly" 
        fig.add_trace(go.Scatter3d(x=[row[0] + " = " + row[1]] * len(row[2:]),
                                   y=uc.columns[2:],
                                   z=row[2:], name=row[0] + " = " + row[1],
                                   visible=visible, showlegend=True),
                                   row=1, col=1)

        x.append(row[0] + " = " + row[1])
        z.append(row[2:])

    z = np.array(z).T

    fig.add_trace(go.Heatmap(x=x,
                             y=uc.columns[2:],
                             z=z, showscale=False))

    fig.update_layout(title="Numbers of Occurencies of Ground Atoms of the MLN",
                      height=2000)

    return fig

def plot_metrics(labels, predictions):
    """
    labels and predictions as dataframe which stores the inferred object predicates
    """

    cm = metrics.confusion_matrix(labels["Second Argument"].to_numpy(), 
                                  predictions["Second Argument"].to_numpy())


    fig = px.imshow(cm,x=labels["Second Argument"].unique(), 
                       y=labels["Second Argument"].unique())
    return fig