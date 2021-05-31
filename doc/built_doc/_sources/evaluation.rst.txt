
Tools for MLN evaluation
========================

PRACMLNs comes with a set of tools for convenient evaluation of an
MLN or learning/inference algorithms.

Confusion Matrices
^^^^^^^^^^^^^^^^^^

.. automodule:: pracmln.utils.eval
    :members: ConfusionMatrix
    
Examples
^^^^^^^^

::

  >>> cm = ConfusionMatrix()
  >>> for _ in range(10):
  ...     cm.addClassificationResult("AAA","A")
  >>> cm.addClassificationResult("AAA","AAA")
  >>> cm.addClassificationResult("AAA","AAA")
  >>> cm.addClassificationResult("AAA","AAA")
  >>> cm.addClassificationResult("AAA","AAA")
  >>> cm.addClassificationResult("AAA","B")
  >>> cm.addClassificationResult("AAA","B")
  >>> cm.addClassificationResult("AAA","C")
  >>> cm.addClassificationResult("B","AAA")
  >>> cm.addClassificationResult("B","AAA")
  >>> cm.addClassificationResult("B","C")
  >>> cm.addClassificationResult("B","B")
  >>> cm.printTable()
  -------------------------------
  | P\C |   A | AAA |   B |   C |
  |-----+-----+-----+-----+-----|
  |   A |   0 |   0 |   0 |   0 |
  |-----+-----+-----+-----+-----|
  | AAA |  10 |   4 |   2 |   1 |
  |-----+-----+-----+-----+-----|
  |   B |   0 |   2 |   1 |   1 |
  |-----+-----+-----+-----+-----|
  |   C |   0 |   0 |   0 |   0 |
  -------------------------------
  
  >>> cm.printPrecisions()
  A: - Acc=0.52, Pre=0.00, Rec=0.00 F1=0.00

  AAA: - Acc=0.29, Pre=0.24, Rec=0.67 F1=0.35

  B: - Acc=0.76, Pre=0.25, Rec=0.33 F1=0.29

  C: - Acc=0.90, Pre=0.00, Rec=0.00 F1=0.00
  
  >>> cm.getLatexTable()
  \footnotesize
  \begin{tabular}{|l|l|l|l|l|}
  \hline
  Prediction/Ground Truth & \begin{turn}{90}A\end{turn} & \begin{turn}{90}AAA\end{turn} & \begin{turn}{90}B\end{turn} & \begin{turn}{90}C\end{turn}\\ \hline
  A & \cellcolor{cfmcolor!0}\textbf{0} & \cellcolor{cfmcolor!0}0 & \cellcolor{cfmcolor!0}0 & \cellcolor{cfmcolor!0}0\\ \hline
  AAA & \cellcolor{cfmcolor!53}10 & \cellcolor{cfmcolor!21}\textbf{4} & \cellcolor{cfmcolor!11}2 & \cellcolor{cfmcolor!5}1\\ \hline
  B & \cellcolor{cfmcolor!0}0 & \cellcolor{cfmcolor!33}2 & \cellcolor{cfmcolor!17}\textbf{1} & \cellcolor{cfmcolor!17}1\\ \hline
  C & \cellcolor{cfmcolor!0}0 & \cellcolor{cfmcolor!0}0 & \cellcolor{cfmcolor!0}0 & \cellcolor{cfmcolor!0}\textbf{0}\\ \hline
  \end{tabular}
  
  >>> cm.getPDF('example.pdf')
  
The last command will produce a PDF ``example.pdf``, which will approzimately 
look like the following:

.. figure:: _static/img/conf_matrix.png
  
  

