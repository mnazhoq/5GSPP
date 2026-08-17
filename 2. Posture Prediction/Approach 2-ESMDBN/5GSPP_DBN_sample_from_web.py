# -*- coding: utf-8 -*-
"""
Created on Tue Feb  6 19:37:29 2024

@author: umroot
"""

# Import libraries
import pgmpy.models
import pgmpy.inference
import numpy as np

# The main entry point for this module
def ma():
    # Create a dynamic bayesian network
    model = pgmpy.models.DynamicBayesianNetwork()
    # Add nodes
    model.add_nodes_from(['Weather', 'Umbrella'])
    # Print nodes
    print('--- Nodes ---')
    print(model.nodes())
    # Add edges
    model.add_edges_from([(('Umbrella',0), ('Weather',0)),
                          (('Weather',0), ('Weather',1)),
                          (('Umbrella',0), ('Umbrella',1))])
    # Print edges
    print('--- Edges ---')
    print(model.edges())
    print()
    # Print parents
    print('--- Parents ---')
    print('Umbrella 0: {0}'.format(model.get_parents(('Umbrella', 0))))
    print('Weather 0: {0}'.format(model.get_parents(('Weather', 0))))
    print('Weather 1: {0}'.format(model.get_parents(('Weather', 1))))
    print('Umbrella 1: {0}'.format(model.get_parents(('Umbrella', 1))))
    print()
    # Add probabilities
    weather_cpd = pgmpy.factors.discrete.TabularCPD(('Weather', 0), 2, [[0.1, 0.8], 
                                                                        [0.9, 0.2]], 
                                                       evidence=[('Umbrella', 0)], 
                                                       evidence_card=[2])
    umbrella_cpd = pgmpy.factors.discrete.TabularCPD(('Umbrella', 1), 2, [[0.5, 0.5], 
                                                                          [0.5, 0.5]], 
                                                     evidence=[('Umbrella', 0)], 
                                                     evidence_card=[2])
    transition_cpd = pgmpy.factors.discrete.TabularCPD(('Weather', 1), 2, [[0.25, 0.9, 0.1, 0.25], 
                                                                           [0.75, 0.1, 0.9, 0.75]], 
                                                   evidence=[('Weather', 0), ('Umbrella', 1)], 
                                                   evidence_card=[2, 2])
    # Add conditional probability distributions (cpd:s)
    model.add_cpds(weather_cpd, umbrella_cpd, transition_cpd)
    # This method will automatically re-adjust the cpds and the edges added to the bayesian network.
    model.initialize_initial_state()
    # Check if the model is valid, throw an exception otherwise
    model.check_model()
    # Print probability distributions
    print('Probability distribution, P(Weather(0) | Umbrella(0)')
    print(weather_cpd)
    print()
    print('Probability distribution, P(Umbrella(1) | Umbrella(0)')
    print(umbrella_cpd)
    print()
    print('Probability distribution, P(Weather(1) | Umbrella(1), Weather(0)')
    print(transition_cpd)
    print()
    # Make inference
    map = {0: 'Sunny', 1: 'Rainy' }
    dbn_inf = pgmpy.inference.DBNInference(model)
    result = dbn_inf.forward_inference([('Weather', 1)], {('Umbrella', 1):0, ('Weather', 0):0})
    arr = result[('Weather', 1)].values
    print()
    print('Prediction (Umbrella(1) : Yes, Weather(0): Sunny): {0} ({1} %)'.format(map[np.argmax(arr)], np.max(arr) * 100))
    print()
    result = dbn_inf.forward_inference([('Weather', 1)], {('Umbrella', 1):0, ('Weather', 0):1})
    arr = result[('Weather', 1)].values
    print()
    print('Prediction (Umbrella(1) : Yes, Weather(0): Rainy): {0} ({1} %)'.format(map[np.argmax(arr)], np.max(arr) * 100))
    print()
    result = dbn_inf.forward_inference([('Weather', 1)], {('Umbrella', 1):1, ('Weather', 0):0})
    arr = result[('Weather', 1)].values
    print()
    print('Prediction (Umbrella(1) : No, Weather(0): Sunny): {0} ({1} %)'.format(map[np.argmax(arr)], np.max(arr) * 100))
    print()
    result = dbn_inf.forward_inference([('Weather', 1)], {('Umbrella', 1):1, ('Weather', 0):1})
    arr = result[('Weather', 1)].values
    print()
    print('Prediction (Umbrella(1) : No, Weather(0): Rainy): {0} ({1} %)'.format(map[np.argmax(arr)], np.max(arr) * 100))
    print()
    
# Tell python to run main method
ma()