import pandas as pd
import numpy as np
from numpy import random
import networkx as nx
import matplotlib.pyplot as plt
import json
import os
import csv
import argparse
from time import time
from pgmpy.models import BayesianNetwork
from sklearn.metrics import f1_score
from collections import defaultdict

from pgmpy.estimators import PC, ExhaustiveSearch, HillClimbSearch, BayesianEstimator, MmhcEstimator, TreeSearch, StructureScore, MaximumLikelihoodEstimator
from pgmpy.estimators import BDeuScore, BicScore, K2Score
from pgmpy.independencies import Independencies
from pgmpy.inference import VariableElimination
from graphviz import Source
import generate_seq as gs
from pgmpy.readwrite import XMLBIFReader
from itertools import combinations
from collections import Counter
from scipy.stats import expon
import datetime


os.environ["KMP_DUPLICATE_LIB_OK"]="TRUE"   # To solve OMP: Error #15: Initializing libiomp5md.dll, but found libiomp5md.dll already initialized.
try:
    import pygraphviz
    from networkx.drawing.nx_agraph import graphviz_layout
except ImportError:
    try:
        import pydotplus
        from networkx.drawing.nx_pydot import graphviz_layout
    except ImportError:
        raise ImportError("This example needs Graphviz and either "
                              "PyGraphviz or PyDotPlus")


DIR = os.path.dirname(os.path.abspath(__file__))

# This function is to resolve the path of the structure file, it checks in multiple locations and returns the correct path if found, 
# otherwise raises a FileNotFoundError
def _resolve_structure_path(structure_file):
    candidates = [
        os.path.join(DIR, structure_file),
        os.path.join(os.path.dirname(DIR), 'Sequence Generation', structure_file),
        os.path.join(os.getcwd(), structure_file),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    raise FileNotFoundError(f"Could not find structure file: {structure_file}")

#This class is to create a graph and check if there is a path between two nodes using BFS algorithm, 
# it is used to create the complete structure of the model by checking if there is a path between two nodes in the direct structure derived from the logs
class Graph:

	def __init__(self, vertices):
		self.V = vertices  # No. of vertices
		self.graph = defaultdict(list)  # default dictionary to store graph

	# function to add an edge to graph
	def addEdge(self, u, v):
		self.graph[u].append(v)

	 # Use BFS to check path between s and d
	def isReachable(self, s, d):
		# Mark all the vertices as not visited
		visited = [False]*(self.V)

		# Create a queue for BFS
		queue = []

		# Mark the source node as visited and enqueue it
		queue.append(s)
		visited[s] = True

		while queue:

			# Dequeue a vertex from queue
			n = queue.pop(0)

			# If this adjacent node is the destination node,
			# then return true
			if n == d:
				 return True

			#  Else, continue to do BFS
			for i in self.graph[n]:
				if visited[i] == False:
					queue.append(i)
					visited[i] = True

		# If BFS is complete without visited d
		return False

# Funtion to evaluate the learned model structures.
def get_f1_score(estimated_model, true_model):
	nodes = estimated_model.nodes()
	est_adj = nx.to_numpy_matrix(estimated_model.to_undirected(), nodelist=nodes, weight=None)
	true_adj = nx.to_numpy_matrix(true_model.to_undirected(), nodelist=nodes, weight=None)

	f1 = f1_score(np.ravel(true_adj), np.ravel(est_adj))
	print("F1-score for the model skeleton: ", f1)

# Input: log_file = sequences.txt, it contains the sequences of events in each line, where each event is separated by a comma. 
# Tasks: The function reads the log file, extracts the event types and creates a data matrix where each row represents a sequence of events and
#       each column represents an event type, with the value being the count of that event type in the sequence. 
#       It also returns the list of event types and the raw sequences of events.
# Output: returns the data matrix, the list of event types and the raw sequences of events.
def retrieve_data_from_logs(log_file):
	event_types = []

	with open(log_file,'r') as f:
		lines = f.readlines()
		line_ops = []

		# Get all possible event type for hist encoding
		for line in lines:
			ops = [i.strip() for i in line.split(',')] #convert string sequence to list sequence of events
			#if len(ops) >= 2:
			line_ops.append(ops)
			for o in ops:
				event_types.append(o) #to get all the events in one single list
		event_types = sorted(list(set(event_types)))
# 		print(event_types)
		data = np.zeros((len(line_ops),len(event_types)))
		for i,line in enumerate(line_ops):
			for j,event in enumerate(line):
				data[i][event_types.index(event)] += 1

	return(event_types, data, line_ops)

# Plot graph and print parameters
#Input: model: the learned Bayesian Network model, title: the title of the graph, edges: the edges with probabilities to be printed on the graph
#Tasks: The function takes the learned model and the edges with probabilities, and plots the graph using networkx and graphviz, with the edges labeled with their probabilities.
#Output: the function does not return anything, it just plots the graph and saves it as a png file.
def draw_graph(model, title, edges=None):
    plt.figure(figsize=(30,30))
    ax = plt.gca()
    ax.set_title(title)
    # Graphviz Layout (struct and probs)
    model.name = title
    # nx.draw_networkx(model, pos=nx.planar_layout(model))pos = nx.circular_layout(graph_model)
    # nx.draw_networkx(model, pos=nx.circular_layout(model))
    
    if edges:
        # last_probs = 0
        # all_edges = dict()
        for i in model.edges:
            u = i[0]
            v = i [1]
            weight = edges[(i[0],i[1])]
            
            model[u][v]['label'] =  weight
            model[u][v]['color'] =  'green'
            model[u][v]['fontcolor'] =  'red'
            
        #nx.draw_networkx_edge_labels(model, pos=nx.planar_layout(model), edge_labels=edges, rotate=False)
        nx.nx_pydot.write_dot(model, 'model_probs.dot')
        s = Source.from_file('model_probs.dot')
        s.render(format='png', view=True)
    else:
        nx.nx_pydot.write_dot(model, 'model_struct.dot')
        s = Source.from_file('model_struct.dot')
        s.render(format='png', view=True)


# Build the edges with probability
#Input: model: the learned Bayesian Network model
#Tasks: The function takes the learned model and calculates the probability of each edge being active (i.e., the probability of the child node being 1 given that the parent node is 1) using variable elimination inference. It returns a dictionary of edges with their probabilities and a new Bayesian Network with the same edges but without the probabilities.
#Output: the function returns a dictionary of edges with their probabilities and a new Bayesian Network with the same edges but without the probabilities.
def build_edges(model):
	# Generate weights to print on graph
    edge_labels = dict()
    infer = VariableElimination(model)
    
    edge_list=[]
    new_BN = BayesianNetwork()
    
    for edge in model.edges():
        test = infer.query([edge[1]], evidence={edge[0]: 1})
        
        # Get the value (1,1) in the CPD, two digit round
        # print(test.values[1])
        edge_labels[edge] = round(test.values[1],2)
        edge_list.append(edge)
    new_BN.add_edges_from(edge_list)
    return edge_labels,new_BN


# This function is to get the key from the value in a dictionary, it is used to get the event name from the event index in the nodes_dic dictionary
def get_key(val, nodes_dict):
	for key, value in nodes_dict.items():
		 if val == value:
			 return key
	return "key doesn't exist"


#Input: log_file = sequences.txt, it contains the sequences of events in each line, where each event is separated by a comma. 
#       file_name = structure.json, it contains the structure of the model in terms of the dependencies between the events. 
#       tme = 0, it is used to create the column names for the data matrix when using Dynamic Bayesian Network (DBN) to convert columns with time series.
#Tasks: The function reads the log file and the structure file, extracts the event types and creates a data matrix where each row represents a sequence of events and each column 
#       represents an event type, with the value being the count of that event type in the sequence. 
#       It then builds the Bayesian Network model using the structure file and fits the model to the data. 
#       Finally, it returns the inference object, the learned model, the number of nodes, number of edges, posture value of the goal node, build time and prediction time.
#Output: the function returns the inference object, the learned model, the number of nodes, number of edges, posture value of the goal node, build time and prediction time.
#       synthetic_events_file.csv file is also created which contains the data matrix with the event types as columns and the sequences as rows.
#       model.json file is also created which contains the structure of the learned model in terms of the edges and their probabilities.
#       The function also plots the graph of the learned model with the edges labeled with their probabilities and saves it as a png file.
def run_model_builder(log_file = 'sequences.txt', file_name = 'structure.json', tme=0):
    
        
    event_types, data, raw_data = retrieve_data_from_logs(log_file)
    # print(f"len event types: no of ndoes = {len(event_types)}")
    
    
    
    # Build data from encoded hist and event_types
    data = pd.DataFrame(data, columns=event_types)
    synthetic_events_file = os.path.join(DIR, 'synthetic_events.csv')
    data.to_csv(synthetic_events_file)
    
    #this is for Dynamic Bayesian Network (DBN) to convert columns with time series
    # new_columns = []
    # for column in data.columns:
    #   myTuple = tuple([column, tme])
    #   new_columns.append(myTuple)
    
    # data.columns = new_columns
    # event_types = new_columns
    
    # print(f'structure file name is: {file_name}')
    
    # Generate the dependencies from the structure.json file
    true_structure = []  #generated directly from the dependency "structure" file: create the edges or node pairs
    with open(file_name, 'r') as f:
        dependencies = json.load(f)
        for e in dependencies:
            for f in dependencies[e][0]:
                # Don't count "end" events
                if f != "end":
                    true_structure.append((e,f))
    # true_model = BayesianNetwork(true_structure)
    
    # print("Structure learning")
    # First create the "direct structure" from logs then derive the conditional dependency structure
    direct_structure = dict()
    direct_structure_array = []
    
    for seq in raw_data:
    	for i, event in enumerate(seq[:-1]):
    		if not((event, seq[i+1]) in direct_structure.keys()):
    			direct_structure[(event,seq[i+1])] = 1
    
    for key in direct_structure.keys():
    	direct_structure_array.append(key) #generated from the event sequence data "sequence.txt" file
    
    # Direct_structure_array is the direct structure derived from the logs
    # print(direct_structure_array)
    
    # Now we create the complete structure with BFS
    
    nodes_dic = dict()
    j = 0
    for i in event_types:
    	nodes_dic[i] = j
    	j = j + 1
    # print(nodes_dic)
    
    # Create a graph given in the above diagram
    # print(len(event_types))
    
    g = Graph(len(event_types))
    for i in direct_structure_array:
    	g.addEdge(nodes_dic[i[0]], nodes_dic[i[1]])
    	# print(nodes_dic[i[0]],nodes_dic[i[1]])
     
    complete_structure = []
    for u in range(len(event_types)):
    	for v in range(len(event_types)):
    		if g.isReachable(u, v):
    			if (u != v):
    				complete_structure.append((get_key(u,nodes_dic),get_key(v,nodes_dic)))
    
    # pr int(complete_structure) #generated considering all possible edges which are connected
    
    # PC = PC(data=data)
    # HC = HillClimbSearch(data=data)
    
    # structure = HC.estimate(scoring_method='k2score')
    # structure = PC.estimate(max_cond_vars=6)
    
    #print("Structure: \n")
    #print(structure)
    state = dict()
    for e in event_types:
        state[e] = (1, 0)
    
    
    build_start_time = time()
    # bmodel = BayesianNetwork(complete_structure)
    bmodel = BayesianNetwork(direct_structure_array)
    # bmodel = BayesianNetwork(true_structure)
    
    
    # print(f"len edges/ no of edges = {len(bmodel.edges())}")
    
    G = nx.DiGraph(bmodel.edges())
    # draw_graph(G, "Structure only")
    
    # print("Learning ...")
    
    bmodel.fit(data, estimator=MaximumLikelihoodEstimator, state_names=state)
    
    print("Done !")
    
    # for cpd in bmodel.get_cpds():
    # 	print(cpd)
    build_end_time = time()
    
    edges,new_bmodel = build_edges(bmodel)
    
    draw_graph(G, "5G BN", edges=edges)
    
    # print(edges)
    
    with open('model.json', 'w') as f:
    	k = edges.keys()
    	v = edges.values()
    	k1 = [str(i) for i in k]
    	json.dump(json.dumps(dict(zip(*[k1,v]))),f)
        
    predict_start_time = time()
    infer = VariableElimination(bmodel)
    test = infer.query(['goal_node'], evidence={'Agent_based_MPB': 0,  'Rule_based_MPB': 0})
    
    # Get the value (1,1) in the CPD, two digit round
    posture_value_goal_node = round(test.values[1],4)
    # print(test)
    
    predict_end_time = time()
    
    prediction_time = (predict_end_time - predict_start_time)
    build_time = (build_end_time - build_start_time)
    list_edges_values = list(edges.values())
    no_of_edges = len(list_edges_values)
    no_of_nodes = len(event_types)
    
    
    print(f'model size = {no_of_nodes+no_of_edges} \nposture_value = {posture_value_goal_node}, \nbuild_time = {build_time}, \nprediction_time = {prediction_time}')
    
    return infer, bmodel, no_of_nodes, no_of_edges, posture_value_goal_node, build_time, prediction_time



def effect_of_no_of_breach(node_count='', no_of_time = 1):
    stage_1_breach_list = ['Logon_PB', 'Remote_access_PB', 'SystemUseNotPB']
    stage_2_breach_list = ['Logon_PB', 'Remote_access_PB', 'SystemUseNotPB', 'Config_PB', 'Agent_based_MPB']
    
    all_comb = return_all_combination_list(stage_2_breach_list)
    
    for items_list in all_comb:
        event_seq_evidence = {key: 1 for key in items_list}
        for i in range(no_of_time):
            gs.generate_consistent_seq()
# test, model,...() 
            get_result(model, event_seq_evidence, items_list, 0)


def network_scalability_test(no_of_time = 2):
    
    all_result_file = os.path.join(DIR, 'results_network_scalability_test_upf.csv')
    
    columns_res=["node_name", "no_of_node", "Net size", "Build time", "Prediction time", "posture_value_goal_node", "posture_value_exfiltrate", "posture_value_Launch_Agent", 
                 "posture_value_Token_Impersonation", "posture_value_bypass","posture_value_deploy",]
    
    if os.path.exists(all_result_file) == False:#if not exist file create it
      with open (all_result_file, 'a') as filedata: 
        writer = csv.writer(filedata, delimiter=',')
        writer.writerow(columns_res)
        
    evidences={'Logon_PB' : 1, 'Bypass_Authentication' : 1, 'Access_Server' : 1, 'Query_SMF' : 1, 'Connect_NRF' : 1, 
               'Connect_PCF' : 1, 'Connect_UPF' : 1, 'Connect_C2' : 1, 'Rule_based_MPB' : 1, 'Exfiltrating_data' : 1, 'goal_node' : 1}
    node_name='Connect_NEF' 
    
    node_limit = 100
    node_count = 0
    while (node_count <= node_limit):
        print(f"{node_name} {node_count} started")
        if node_count == 0:
            structure_file_name = 'structure'
        else:
            gs.generate_multiple_nodes(node_count, node_name)
            structure_file_name = 'structure_' + node_name + '_' + str(node_count)  
                 
        gs.generate_consistent_seq(structure_file_name+ '.json', from_start = False)
        node_count = node_count + 5
        
        for i in range(no_of_time):
            test, model, no_of_nodes, no_of_edges, posture_value_goal_node, build_time, prediction_time = run_model_builder(structure_file_name+'.json' ) 
            print(f'no of nodes = {no_of_nodes}, and no of edges = {no_of_edges}')
            predict_start_time = time()
            
            infer = VariableElimination(model)
            
            dc = {k: v for k, v in evidences.items() if k != 'goal_node'} #take all evidence except goal_node
            test_goal = infer.query(['goal_node'], evidence=dc)
            posture_value_goal_node = round(test_goal.values[1], 4)
            # print('------------posture_value_goal_node', posture_value_goal_node)
            # print(test_goal)
            predict_end_time = time()
            
            dc = {k: v for k, v in evidences.items() if k != 'Exfiltrating_data'}
            test_exfiltrate = infer.query(['Exfiltrating_data'], evidence=dc)
            posture_value_exfiltrate = round(test_exfiltrate.values[1], 4)
            # print('------------posture_value_exfiltrate', posture_value_exfiltrate)
            
            dc = {k: v for k, v in evidences.items() if k != 'Bypass_Authentication'}
            test_exfiltrate = infer.query(['Bypass_Authentication'], evidence=dc)
            posture_value_bypass = round(test_exfiltrate.values[1], 4)
            # print('------------posture_value_exfiltrate', posture_value_bypass)
            
            
            dc = {k: v for k, v in evidences.items() if k != 'Deploy_malware'}
            test_exfiltrate = infer.query(['Deploy_malware'], evidence=dc)
            posture_value_deploy = round(test_exfiltrate.values[1], 4)
            # print('------------posture_value_exfiltrate', posture_value_exfiltrate)
            
            dc = {k: v for k, v in evidences.items() if k != 'Launch_Agent'}
            test_Launch_Agent = infer.query(['Launch_Agent'], evidence=dc)
            posture_value_Launch_Agent = round(test_Launch_Agent.values[1], 4)
            # print('------------posture_value_Launch_Agent', posture_value_Launch_Agent)
            
            
            dc = {k: v for k, v in evidences.items() if k != 'Token_Impersonation'}
            test_Token_Impersonation = infer.query(['Token_Impersonation'], evidence=dc)
            posture_value_Token_Impersonation = round(test_Token_Impersonation.values[1], 4)
            # print('------------test_Token_Impersonation', posture_value_Token_Impersonation)
            
         
            prediction_time = (predict_end_time - predict_start_time)
            
            #open the csv file and save result
            all_results = {"node_name": node_name, "no_of_node":no_of_nodes, "Net size": str(no_of_nodes + no_of_edges),  "Build time": build_time,
                           "Prediction time": prediction_time, "posture_value_goal_node": posture_value_goal_node, 
                           "posture_value_exfiltrate": posture_value_exfiltrate, "posture_value_Launch_Agent": posture_value_Launch_Agent, 
                         "posture_value_Token_Impersonation": posture_value_Token_Impersonation, "posture_value_bypass": posture_value_bypass, 
                         "posture_value_deploy": posture_value_deploy,}
            with open (all_result_file, 'a') as filedata: 
                writer = csv.DictWriter(filedata, delimiter=',', fieldnames=columns_res)
                writer.writerow(all_results)
            print(f" repitiong {i+1} finished")
        print(f"{node_name} {node_count} finished")


def number_of_policy_breach_effect_test(no_of_time = 2):
    
    all_result_file = os.path.join(DIR, 'results_no_of_policy_breach - original_8_jan_23.csv')
    
    columns_res=["node_name", "no_of_node", "Net size", "Build time", "Prediction time", "posture_value_goal_node", "posture_value_exfiltrate", "posture_value_Launch_Agent", 
                 "posture_value_Token_Impersonation", "posture_value_bypass","posture_value_deploy",]
    
    if os.path.exists(all_result_file) == False:#if not exist file create it
      with open (all_result_file, 'a') as filedata: 
        writer = csv.writer(filedata, delimiter=',')
        writer.writerow(columns_res)
    
    # evidences={'Logon_PB' : 1, 'Bypass_Authentication' : 1, 'Access_Server' : 1, 'Query_SMF' : 1, 'Connect_NRF' : 1, 
    #        'Connect_PCF' : 1, 'Connect_UPF' : 1, 'Connect_C2' : 1, 'Rule_based_MPB' : 1, 'Exfiltrating_data' : 1, 'goal_node' : 1}        
    evidences={ 'Access_Server' : 1, 'Query_SMF' : 1, 'Connect_NRF' : 1, 
               'Connect_PCF' : 1, 'Connect_UPF' : 1, 'Connect_C2' : 1, 'Rule_based_MPB' : 1, 'Exfiltrating_data' : 1, 'goal_node' : 1}
    
    
    
    node_name = 'No'
    structure_file_name = 'structure'
    
    
    # node_name = 'Logon, RemoteAccess, SystemUseNot'
    # structure_file_name = 'all3'
    
    # node_name = 'LogOn and RemoteAccess'
    # structure_file_name = 'structure_without_SystemUseNot_pb'
    # node_name = 'LogOn and SystemUseNot'
    # structure_file_name = 'structure_without_RemoteAccess_pb'
    # node_name = 'RemoteAccess and SystemUseNPB'
    # structure_file_name = 'structure_without_logOn_pb'
    
    
    # node_name = 'RemoteAccess'
    # structure_file_name = 'structure_without_Log_ON and SystemUseNPB'
    # node_name = 'SystemUseNot'
    # structure_file_name = 'structure_without_Log_ON and RemoteAccess_pb'
    # node_name = 'LogOn'
    # structure_file_name = 'structure_without_SystemUseNot_pb and RemoteAccessPB'
    
    # gs.generate_consistent_seq(structure_file_name+ '.json', from_start = False)
    
    for i in range(no_of_time):
        test, model, no_of_nodes, no_of_edges, posture_value_goal_node, build_time, prediction_time = run_model_builder(structure_file_name+'.json' ) 
        print(f'no of nodes = {no_of_nodes}, and no of edges = {no_of_edges}')
        predict_start_time = time()
        
        infer = VariableElimination(model)
        
        dc = {k: v for k, v in evidences.items() if k != 'goal_node'} #take all evidence except goal_node
        test_goal = infer.query(['goal_node'], evidence=dc)
        posture_value_goal_node = round(test_goal.values[1], 4)
        # print('------------posture_value_goal_node', posture_value_goal_node)
        # print(test_goal)
        predict_end_time = time()
        
        dc = {k: v for k, v in evidences.items() if k != 'Exfiltrating_data'}
        test_exfiltrate = infer.query(['Exfiltrating_data'], evidence=dc)
        posture_value_exfiltrate = round(test_exfiltrate.values[1], 4)
        # print('------------posture_value_exfiltrate', posture_value_exfiltrate)
        
        # dc = {k: v for k, v in evidences.items() if k != 'Bypass_Authentication'}
        # test_exfiltrate = infer.query(['Bypass_Authentication'], evidence=dc)
        # posture_value_bypass = round(test_exfiltrate.values[1], 4)
        # print('------------posture_value_exfiltrate', posture_value_bypass)
        posture_value_bypass = 'NAN'
        
        dc = {k: v for k, v in evidences.items() if k != 'Deploy_malware'}
        test_exfiltrate = infer.query(['Deploy_malware'], evidence=dc)
        posture_value_deploy = round(test_exfiltrate.values[1], 4)
        # print('------------posture_value_exfiltrate', posture_value_exfiltrate)
        
        dc = {k: v for k, v in evidences.items() if k != 'Launch_Agent'}
        test_Launch_Agent = infer.query(['Launch_Agent'], evidence=dc)
        posture_value_Launch_Agent = round(test_Launch_Agent.values[1], 4)
        # print('------------posture_value_Launch_Agent', posture_value_Launch_Agent)
        
        
        dc = {k: v for k, v in evidences.items() if k != 'Token_Impersonation'}
        test_Token_Impersonation = infer.query(['Token_Impersonation'], evidence=dc)
        posture_value_Token_Impersonation = round(test_Token_Impersonation.values[1], 4)
        # print('------------test_Token_Impersonation', posture_value_Token_Impersonation)
        
     
        prediction_time = (predict_end_time - predict_start_time)
        
        #open the csv file and save result
        all_results = {"node_name": node_name, "no_of_node":no_of_nodes, "Net size": str(no_of_nodes + no_of_edges),  "Build time": build_time,
                       "Prediction time": prediction_time, "posture_value_goal_node": posture_value_goal_node, 
                       "posture_value_exfiltrate": posture_value_exfiltrate, "posture_value_Launch_Agent": posture_value_Launch_Agent, 
                     "posture_value_Token_Impersonation": posture_value_Token_Impersonation, "posture_value_bypass": posture_value_bypass, 
                     "posture_value_deploy": posture_value_deploy,}
        with open (all_result_file, 'a') as filedata: 
            writer = csv.DictWriter(filedata, delimiter=',', fieldnames=columns_res)
            writer.writerow(all_results)
        print(f" repitotion {i+1} finished")

# ['Remote_access_PB',  'Bypass_Authentication',  'Access_Server', 'Query_SMF', 'Portable_Execution',  'Deploy_malware', 'Config_PB', 'Token_Impersonation',  'goal_node']
def generate_single_sequence(events, dependencies, from_start=True):
       
    seq =  []
    if from_start:
        s = [k for k,v in event_keys_values.items() if v == 1] #get all the events in level 1
        # s = ['Input_Credentials', 'Logon_PB', 'Remote_access_PB']
        previous_event = np.random.choice(s)
    else:
        previous_event = np.random.choice(events)
    #previous_event = 'create_pod'
    next_event = ''
    seq.append(previous_event)
    
    while((previous_event != "end") and (len(dependencies[previous_event][0]) > 0) and (previous_event in events)):
        next_event = np.random.choice(dependencies[previous_event][0], p=dependencies[previous_event][1])
        if next_event not in seq: #check if the event already exists
            seq.append(next_event)
            previous_event = next_event
        # Turn to string, remove "end" event
    string_seq = ','.join(seq[:-1])
    # return string_seq
    return seq[:-1]
 
def generate_attacker_capability(no_of_attacker, events, dependencies):
    attacker_capabilities = []
    attacker_actual_capabilities = []
    
    successfull_attacker_count = 0
    test, model, no_of_nodes, no_of_edges, posture_value_goal_node, build_time, prediction_time = run_model_builder()
    
    # ex = random.exponential(size=len(events))
    upper = 14
    beta = -(upper - 2)/np.log(1 - 0.999) #set highest value
    
    # randomNums = np.random.normal(loc=7, scale=beta, size = no_of_attacker)
    randomNums = np.random.power(a=2.5, size = no_of_attacker)
    randomInts = np.round(randomNums*15)
    randomInts = [item for item in randomInts if (item >0 and item <15)] #check all the random generated values are in the range
    counts = Counter(randomInts) #count the occurance of all values in the array and return a dictionary
        
    # randomNums = np.random.normal(loc=7, scale=beta, size = no_of_attacker)
    # randomInts = np.round(randomNums)
    # randomInts = [item for item in randomInts if (item >0 and item <15)] #check all the random generated values are in the range
    # counts = Counter(randomInts) #count the occurance of all values in the array and return a dictionary
    
    
    # randomNums = np.random.exponential(scale = beta, size=no_of_attacker)
    # randomInts = np.round(randomNums)
    # randomInts = randomInts + 1
    # randomInts = [item for item in randomInts if (item >0 and item <15)] #check all the random generated values are in the range
    # counts = Counter(randomInts) #count the occurance of all values in the array and return a dictionary
   

    axis = np.arange(start=min(randomInts), stop = max(randomInts) + 1)
    plt.hist(randomInts, bins = axis)
    counts
    
    while (any(x != 0 for x in counts.values())) :  #return true if any value in the dicitonary is not zero
        gen_seq = generate_single_sequence(events, dependencies, from_start=True)
        len_gen_seq = len(gen_seq)
        if counts[len_gen_seq] != 0:
            counts[len_gen_seq] = counts[len_gen_seq] - 1
            attacker_capabilities.append(gen_seq)
        # print(gen_seq)
        print(f'counts[{len_gen_seq}] = {counts[len_gen_seq]}')
    
    
    # len_cap = [ len(x) for x in attacker_capabilities]
    # index_of_val =  np.where(np.array(len_cap) == 15)[0]    
    # event_seq_list = attacker_capabilities[index_of_val[0]]
    
    
    # ex = random.normal(loc = 0.5, scale = 0.01, size=25)
    # ex = random.lognormal(size=len(events))
    
    
    
    for event_seq_list in attacker_capabilities: #geenrate attacker capabilities
        # size_of_subset = randomInts[i]
        # print('size_of_subset = ', size_of_subset)    
        # # a_c = random.choice(events, size_of_subset, p=ex/sum(ex), replace=False)
        # # actuall_a_c = get_attacker_actual_capabiliteis(a_c)
        # a_c = get_attacker_events_list_capabiliteis(size_of_subset)
        # attacker_capabilities.append(a_c)
        # # attacker_actual_capabilities.append(actuall_a_c)
        
        #generate events based on the stage 1 events list and event_dependencies
        # event_seq_list = attacker_capabilities
        # event_seq_list = event_seq.split(',')
        # print("============ generated_seq:  ", event_seq)
        
        event_seq_evidence = {key: 1 for key in event_seq_list}
        
        if('goal_node' in event_seq_list):
            successfull_attacker_count += 1
            get_result(model, event_seq_evidence, event_seq_list, successfull_attacker_count)
        else:
            get_result(model, event_seq_evidence, event_seq_list, 0) #set successfull_attacker_count to 0 
        
        
        # updt_mdl(model, event_seq, events) #update the model with current data
        # test, model, no_of_nodes, no_of_edges, posture_value_goal_node, build_time, prediction_time = run_model_builder()
        
    return attacker_capabilities



def get_result(bmodel, evidences, event_seq, successfull_attacker_count):
    
    all_result_file = os.path.join(DIR, '09_dec_22_results_more_path_10000_norm_dist.csv')
    predict_start_time = time()
    
    infer = VariableElimination(bmodel)
    
    dc = {k: v for k, v in evidences.items() if k != 'goal_node'} #take all evidence except goal_node
    test_goal = infer.query(['goal_node'], evidence=dc)
    posture_value_goal_node = round(test_goal.values[1], 4)
    # print('------------posture_value_goal_node', posture_value_goal_node)
    # print(test_goal)
    predict_end_time = time()
    
    dc = {k: v for k, v in evidences.items() if k != 'Exfiltrating_data'}
    test_exfiltrate = infer.query(['Exfiltrating_data'], evidence=dc)
    posture_value_exfiltrate = round(test_exfiltrate.values[1], 4)
    # print('------------posture_value_exfiltrate', posture_value_exfiltrate)
    
    dc = {k: v for k, v in evidences.items() if k != 'Bypass_Authentication'}
    test_exfiltrate = infer.query(['Bypass_Authentication'], evidence=dc)
    posture_value_bypass = round(test_exfiltrate.values[1], 4)
    # print('------------posture_value_exfiltrate', posture_value_bypass)
    
    
    dc = {k: v for k, v in evidences.items() if k != 'Deploy_malware'}
    test_exfiltrate = infer.query(['Deploy_malware'], evidence=dc)
    posture_value_deploy = round(test_exfiltrate.values[1], 4)
    # print('------------posture_value_exfiltrate', posture_value_exfiltrate)
    
    dc = {k: v for k, v in evidences.items() if k != 'Launch_Agent'}
    test_Launch_Agent = infer.query(['Launch_Agent'], evidence=dc)
    posture_value_Launch_Agent = round(test_Launch_Agent.values[1], 4)
    # print('------------posture_value_Launch_Agent', posture_value_Launch_Agent)
    
    
    dc = {k: v for k, v in evidences.items() if k != 'Token_Impersonation'}
    test_Token_Impersonation = infer.query(['Token_Impersonation'], evidence=dc)
    posture_value_Token_Impersonation = round(test_Token_Impersonation.values[1], 4)
    # print('------------test_Token_Impersonation', posture_value_Token_Impersonation)
    
    attack_stage = identify_attack_stage(event_seq)
    attacker_capability = identify__attacker_capability(event_seq)
    prediction_time = (predict_end_time - predict_start_time)
    
    
    
    
    columns_res=["attacker_capability", "stage_name", "node_seq", "posture_value_goal_node", "posture_value_exfiltrate", "posture_value_Launch_Agent", 
                 "posture_value_Token_Impersonation", "posture_value_bypass","posture_value_deploy","prediction_time time", "no_of_attacker_reach"]
    if os.path.exists(all_result_file) == False:#if not exist file create it
      with open (all_result_file, 'a') as filedata: 
        writer = csv.writer(filedata, delimiter=',')
        writer.writerow(columns_res)
    
    #open the csv file and save result
    all_results = {"attacker_capability": attacker_capability, "stage_name": attack_stage, "node_seq": event_seq, "posture_value_goal_node": posture_value_goal_node, 
                   "posture_value_exfiltrate": posture_value_exfiltrate, "posture_value_Launch_Agent": posture_value_Launch_Agent, 
                 "posture_value_Token_Impersonation": posture_value_Token_Impersonation, "posture_value_bypass": posture_value_bypass, 
                 "posture_value_deploy": posture_value_deploy, "prediction_time time": prediction_time, 
                 "no_of_attacker_reach": successfull_attacker_count}
    
    with open (all_result_file, 'a') as filedata: 
        writer = csv.DictWriter(filedata, delimiter=',', fieldnames=columns_res)
        writer.writerow(all_results)

file_name = 'structure_with_loop.json'
with open(_resolve_structure_path(file_name)) as f:
    dependencies = json.load(f) #return dictionary
    events = [e for e in dependencies] #return list: all the keys from the JSO



stage_1_events_list = ['Input_Credentials',  'Authentication',  'SystemUseNotPB',
 'Logon_PB',  'Remote_access_PB',  'Bypass_Authentication',  'Access_Server']
stage_1_dependencies = {key: value for key, value in dependencies.items() if (key in stage_1_events_list)}



stage_2_events_list = ['Deploy_malware', 'Config_PB', 'Portable_Execution',
'Agent_based_MPB', 'Token_Impersonation', 'Query_SMF', 'Connect_NRF', 'Launch_Agent']
stage_2_dependencies = {key: value for key, value in dependencies.items() if (key in stage_2_events_list)}
stage_2_dependencies.update(stage_1_dependencies)

stage_3_events_list = ['Connect_SMF', 'Connect_PCF', 'Connect_NEF', 'Connect_UPF', 'Create_GTP',
'Connect_C2', 'Rule_based_MPB', 'Exfiltrating_data', 'Connect_UE', 'goal_node']
stage_3_dependencies = dependencies
 

#creating a dictionary to get the highest level of an attacker
event_keys_values = {'Access_Server': 4, 
 'Agent_based_MPB': 6,
 'Authentication': 2,
 'Bypass_Authentication': 2,
 'Config_PB': 6,
 'Connect_C2': 11,
 'Connect_NEF': 9,
 'Connect_NRF': 8,
 'Connect_PCF': 9,
 'Connect_SMF': 9,
 'Connect_UE': 12,
 'Connect_UPF': 10,
 'Create_GTP': 11,
 'Deploy_malware': 5,
 'Exfiltrating_data': 13,
 'Input_Credentials': 1,
 'Launch_Agent': 7,
 'Logon_PB': 1,
 'Portable_Execution': 5,
 'Query_SMF': 5,
 'Remote_access_PB': 1,
 'Rule_based_MPB': 12,
 'SystemUseNotPB': 3,
 'Token_Impersonation': 7,
 'goal_node': 8}

# Logon_PB, Remote_access_PB, SystemUseNotPB, Config_PB, Rule_based_MPB, Agent_based_MPB
def get_attacker_events_list_capabiliteis(no_of_events):
    s = [k for k,v in event_keys_values.items() if v <= no_of_events] #get all keys with same value
    return s

#will return the sequential events up to highest event levels
def get_attacker_actual_capabiliteis(attacker_capability):    
    capabilitiy_values = [event_keys_values[k] for k in attacker_capability]
    max_val = max(capabilitiy_values)
    s = [k for k,v in event_keys_values.items() if v <= max_val] #get all keys with same value
    return s



def identify_attack_stage(generated_seq): 
    last_node = generated_seq[-1] #check the last node 
    # print(last_node)
    if last_node in stage_1_events_list:
        stage_name = "Stage 1"
        # print("Stage 1")
    elif last_node in stage_2_events_list:
        stage_name = "Stage 2"
        # print("Stage 2")
    else:
        stage_name = "Stage 3"
        # print("Stage 3")
    
    return stage_name
        
def identify__attacker_capability(generated_seq):
    
    capability = ''
    seq_list = generated_seq
    # breach_list = ['Logon_PB', 'Remote_access_PB', 'SystemUseNotPB', 'Config_PB', 'Agent_based_MPB', 'Rule_based_MPB']
    # x = set(seq_list).intersection(set(breach_list))
    len_cap = len(generated_seq)        
    
    if (len_cap <=2):
        capability = 1
    elif (len_cap >2 and len_cap<=4):
        capability = 2
    elif (len_cap >4 and len_cap<=7):
        capability = 3
    elif (len_cap >7 and len_cap<=16):
        capability = 4
    elif (len_cap >16):
        capability = 5
    return capability
    
# node_limit = 100
# node_count = 1
# while (node_count <= node_limit):
#     node_name='Connect_UPF'    
# #    node_name='Access_eDNS'   
#     gs.generate_multiple_nodes(node_count, node_name)
#     structure_file_name = 'structure_' + node_name + '_' + str(node_count)                   
#     gs.generate_consistent_seq(structure_file_name+ '.json' )
#     node_count = node_count + 5
#     get_average_score(node_count)
    
    
# #    
# #df = pd.read_csv('results.csv')
# #draw_result_graph(pd)


def updt_mdl(model, seq, event_types):
    # event_seq_val = np.zeros(len(event_types))
    # ops = [i.strip() for i in seq.split(',')]
    # for event in ops:
    #     event_seq_val[event_types.index(event)] += 1
        
    # new_data = pd.DataFrame([event_seq_val], columns=event_types )
    # n_model = model.update(new_data)
    
    if os.path.exists('sequences.txt'):
        with open('sequences.txt', 'a') as w:
            w.write(seq+'\n')
            
    else:
        print('sequences.txt File does not exist')
    
    # return n_model

def return_all_combination_list(given_list):
     
    output = sum([list(map(list, combinations(given_list, i))) for i in range(len(given_list) + 1)], [])
    output.pop(0) #remove first element as it is empty
    return output

# def update_model():
    
# # create Bayesian Network and store BN into bn.xml.If bn.xml exists, read it and update with new data
#     bmodel =BayesianNetwork()
    # if os.path.exists('bn.xml'):
    # # if Path('bn.xml').is_file():
    #   reader=XMLBIFReader('bn.xml')
    #   bmodel = reader.get_model()
    #   new_nodes =[x for x in event_types if x not in list(bmodel.nodes)]
    #   new_edges =[x for x in direct_structure_array if x not in list(bmodel.edges)]
    #   bmodel.add_nodes_from(nodes=new_nodes)
    #   bmodel.add_edges_from(ebunch=new_edges)
    #   bmodel.add_cpds()
    #   node_list = bmodel.nodes
    #   df_rows = len(data.index)
    #   filled_data = ['no' for i in range(df_rows)]
    #   column_list = [column for column in data]
    #   for node in node_list:
    #       if not node in column_list:
    #           data[node] = filled_data
    #   #maintain the previous learned paras and update probs with new data.
    #   print(data)
    #   bmodel.fit_update(data)
    
    # else:
    #     bmodel = BayesianNetwork(direct_structure_array)
    #     state = dict()
    #     for i in event_types:
    #         state[i]=('yes','no')
    #     bmodel.fit(data, estimator=MaximumLikelihoodEstimator,state_names=state)
    #     bmodel.save('bn.xml', filetype='xmlbif')


# number_of_policy_breach_effect_test(no_of_time = 2)
# network_scalability_test()
# generate_attacker_capability(10000, events, dependencies)

#to generate the test data sequences

# gs.generate_consistent_seq(save_file_name = 'sequences_atck_goal.txt', file_name = 'structure_with_attackGoal.json', from_start = True)
# test, model,...( log_file = 'sequences_atck_goal.txt', file_name = 'structure_with_attackGoal.json', tme=1)

gs.generate_consistent_seq(save_file_name = 'sequences_atck_pattern.txt', file_name = 'structure_with_pattern.json', from_start = True)
# test, model,...( log_file = 'sequences_atck_pattern.txt', file_name = 'structure_with_pattern.json', tme=1)





############ for geenrating test data with result form the model ###########
def generate_data_file_for_exp(target_goal_node='Exfiltrating_data', inference_engine=None,
                               log_file='sequences_atck_pattern.txt',
                               structure_file='structure_with_pattern.json'):
    all_result_file = os.path.join(DIR, 'data_for_exp_ExfData_23Feb.csv')

    if inference_engine is None:
        inference_engine, _, _, _, _, _, _ = run_model_builder(
            log_file=log_file,
            file_name=structure_file,
            tme=1,
        )
    
    columns_res=["date_time", "sequence", "posturevalue"]
    
    if os.path.exists(all_result_file) == False:#if not exist file create it
      with open (all_result_file, 'a') as filedata: 
        writer = csv.writer(filedata, delimiter=',')
        writer.writerow(columns_res)
    

    with open(log_file,'r') as f:
        lines = f.readlines()
        line_ops = []
        time_val = datetime.datetime(2018,1,1,0,0,0)
        # Get all possible event type for hist encoding
        for line in lines:
            seq = [i.strip() for i in line.split(',')] #convert string sequence to list sequence of events
            line_ops.append(seq)
            print(seq)
            if(target_goal_node in seq):
                seq.remove(target_goal_node)
            evidence_val = {i: 1 for i in seq} #convert string sequence to list sequence of events
            print(evidence_val)
            post_val = inference_engine.query([target_goal_node], evidence=evidence_val).values[1]
            print(post_val)#get value at index 1
            #open the csv file and save result
            all_results = {"date_time": time_val, "sequence": seq, "posturevalue": post_val}
            time_val += datetime.timedelta(hours=1)
            with open (all_result_file, 'a') as filedata: 
                writer = csv.DictWriter(filedata, delimiter=',', fieldnames=columns_res)
                writer.writerow(all_results)

######################### TEMP
paths = []
def myDFS(graph,start,end,path=[]):
    path=path+[start]
    if start==end:
        paths.append(path)
    for node in graph.get_children(start):
        if node not in path:
            myDFS(graph,node,end,path)

    return path


def run_smoke_harness(log_file='sequence_test.txt', structure_file='structure.json'):
    """Run deterministic, lightweight checks for core utilities."""
    results = {}

    try:
        graph = Graph(3)
        graph.addEdge(0, 1)
        graph.addEdge(1, 2)
        results['Graph.isReachable'] = graph.isReachable(0, 2)
    except Exception as exc:
        results['Graph.isReachable'] = f'FAIL: {exc}'

    try:
        event_types, data, _ = retrieve_data_from_logs(log_file)
        results['retrieve_data_from_logs'] = {
            'event_type_count': len(event_types),
            'rows': int(data.shape[0]),
            'cols': int(data.shape[1]),
        }
    except Exception as exc:
        results['retrieve_data_from_logs'] = f'FAIL: {exc}'

    try:
        results['get_key'] = get_key(0, {'a': 0})
        results['return_all_combination_list'] = len(return_all_combination_list(['a', 'b', 'c']))
        results['get_attacker_events_list_capabiliteis'] = len(get_attacker_events_list_capabiliteis(3))
        results['identify_attack_stage'] = identify_attack_stage(['Authentication', 'Access_Server'])
        results['identify__attacker_capability'] = identify__attacker_capability(['a', 'b', 'c'])
    except Exception as exc:
        results['utility_functions'] = f'FAIL: {exc}'

    original_draw_graph = draw_graph
    try:
        # Keep harness deterministic and headless by disabling graph rendering.
        globals()['draw_graph'] = lambda *args, **kwargs: None
        _, _, no_of_nodes, no_of_edges, posture_value_goal_node, _, _ = run_model_builder(
            log_file=log_file,
            file_name=structure_file,
            tme=1,
        )
        results['run_model_builder'] = {
            'no_of_nodes': no_of_nodes,
            'no_of_edges': no_of_edges,
            'posture_value_goal_node': posture_value_goal_node,
        }
    except Exception as exc:
        results['run_model_builder'] = f'FAIL: {exc}'
    finally:
        globals()['draw_graph'] = original_draw_graph

    return results


def main():
    parser = argparse.ArgumentParser(description='Model builder runner and smoke harness')
    parser.add_argument('--smoke', action='store_true', help='Run deterministic smoke harness and exit')
    parser.add_argument('--smoke-log-file', default='sequence_test.txt', help='Log file used by smoke harness')
    parser.add_argument('--smoke-structure-file', default='structure.json', help='Structure file used by smoke harness')
    parser.add_argument('--log-file', default='sequences_atck_pattern.txt', help='Log file for full run')
    parser.add_argument('--structure-file', default='structure_with_pattern.json', help='Structure file for full run')
    parser.add_argument('--target-goal-node', default='Exfiltrating_data', help='Target node for experiment export')
    parser.add_argument('--skip-sequence-generation', action='store_true', help='Skip generating sequences before training')
    args = parser.parse_args()

    if args.smoke:
        print(run_smoke_harness(args.smoke_log_file, args.smoke_structure_file))
        return

    if not args.skip_sequence_generation:
        gs.generate_consistent_seq(
            save_file_name=args.log_file,
            file_name=args.structure_file,
            from_start=True,
        )

    infer, model, no_of_nodes, no_of_edges, posture_value_goal_node, build_time, prediction_time = run_model_builder(
        log_file=args.log_file,
        file_name=args.structure_file,
        tme=1,
    )
    print(
        f'run summary: nodes={no_of_nodes}, edges={no_of_edges}, '
        f'posture={posture_value_goal_node}, build_time={build_time}, prediction_time={prediction_time}'
    )

    generate_data_file_for_exp(
        target_goal_node=args.target_goal_node,
        inference_engine=infer,
        log_file=args.log_file,
        structure_file=args.structure_file,
    )


if __name__ == '__main__':
    main()
