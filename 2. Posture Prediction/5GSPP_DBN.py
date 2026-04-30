# -*- coding: utf-8 -*-
"""
Created on Wed Jan 31 19:58:26 2024

@author: umroot
"""

# Import required libraries
import pgmpy.models
import pgmpy.inference
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# import pygraphviz
# from graphviz import Source

# import networkx as nx
# from networkx.drawing.nx_agraph import graphviz_layout

from pgmpy.models import DynamicBayesianNetwork as DBN

# from IPython.display import Image #to show image




# Create dataset synthetically
data = np.random.randint(low=0, high=2, size=(1000, 75))
colnames = []
for t in range(3):
    colnames.extend([("Access_Server", t), ("Agent_based_MPB", t), ("Authentication", t), ("Bypass_Authentication", t), ("Config_PB", t), ("Connect_C2", t), ("Connect_NEF", t), ("Connect_NRF", t), ("Connect_PCF", t), ("Connect_SMF", t), ("Connect_UE", t), ("Connect_UPF", t), ("Create_GTP", t), ("Deploy_malware", t), ("Exfiltrating_data", t), ("Input_Credentials", t), ("Launch_Agent", t), ("Logon_PB", t), ("Portable_Execution", t), ("Query_SMF", t), ("Remote_access_PB", t), ("Rule_based_MPB", t),  ("SystemUseNotPB", t), ("Token_Impersonation", t), ("goal_node", t)])
df = pd.DataFrame(data, columns=colnames)



# create model 
model = DBN()

model.add_edges_from(
    [
        (("Input_Credentials", 0), ("Authentication", 0)),
        (("Authentication", 0), ("Access_Server", 0)),
        (("Access_Server", 0), ("Deploy_malware", 0)),
        (("Deploy_malware", 0), ("Config_PB", 0)),
        (("Config_PB", 0), ("Token_Impersonation", 0)),
        (("Token_Impersonation", 0), ("Connect_NRF", 0)),
        (("Connect_NRF", 0), ("Connect_SMF", 0)),
        (("Connect_SMF", 0), ("Connect_UPF", 0)),
        (("Connect_UPF", 0), ("Create_GTP", 0)),
        (("Create_GTP", 0), ("Connect_UE", 0)),
        (("Connect_UPF", 0), ("Connect_C2", 0)),
        (("Connect_C2", 0), ("Rule_based_MPB", 0)),
        (("Rule_based_MPB", 0), ("Exfiltrating_data", 0)),
        (("Exfiltrating_data", 0), ("goal_node", 0)),
        (("Access_Server", 0), ("Portable_Execution", 0)),
        (("Portable_Execution", 0), ("Agent_based_MPB", 0)),
        (("Agent_based_MPB", 0), ("Launch_Agent", 0)),
        (("Launch_Agent", 0), ("goal_node", 0)),
        (("Access_Server", 0), ("Query_SMF", 0)),
        (("Query_SMF", 0), ("Connect_NRF", 0)),
        (("Connect_NRF", 0), ("Connect_NEF", 0)),
        (("Logon_PB", 0), ("Bypass_Authentication", 0)),
        (("Bypass_Authentication", 0), ("Access_Server", 0)),
        (("Remote_access_PB", 0), ("Bypass_Authentication", 0)),
 (("Input_Credentials", 1), ("Authentication", 1)),
        (("Authentication", 1), ("Access_Server", 1)),
        (("Access_Server", 1), ("Deploy_malware", 1)),
        (("Deploy_malware", 1), ("Config_PB", 1)),
        (("Config_PB", 1), ("Token_Impersonation", 1)),
        (("Token_Impersonation", 1), ("Connect_NRF", 1)),
        (("Connect_NRF", 1), ("Connect_SMF", 1)),
        (("Connect_SMF", 1), ("Connect_UPF", 1)),
        (("Connect_UPF", 1), ("Create_GTP", 1)),
        (("Create_GTP", 1), ("Connect_UE", 1)),
        (("Connect_UPF", 1), ("Connect_C2", 1)),
        (("Connect_C2", 1), ("Rule_based_MPB", 1)),
        (("Rule_based_MPB", 1), ("Exfiltrating_data", 1)),
        (("Exfiltrating_data", 1), ("goal_node", 1)),
        (("Access_Server", 1), ("Portable_Execution", 1)),
        (("Portable_Execution", 1), ("Agent_based_MPB",1)),
        (("Agent_based_MPB", 1), ("Launch_Agent", 1)),
        (("Launch_Agent", 1), ("goal_node", 1)),
        (("Access_Server", 1), ("Query_SMF", 1)),
        (("Query_SMF", 1), ("Connect_NRF", 1)),
        (("Connect_NRF", 1), ("Connect_NEF", 1)),
        (("Logon_PB", 1), ("Bypass_Authentication", 1)),
        (("Bypass_Authentication", 1), ("Access_Server", 1)),
        (("Remote_access_PB", 1), ("Bypass_Authentication", 1)),
        (("Input_Credentials", 1), ("Authentication", 1)),
        (("Authentication", 1), ("Access_Server", 1)),
        (("Access_Server", 1), ("Deploy_malware", 1)),
        (("Deploy_malware", 1), ("Config_PB", 1)),
        (("Config_PB", 1), ("Token_Impersonation", 1)),
        (("Token_Impersonation", 1), ("Connect_NRF", 1)),
(("Input_Credentials", 2), ("Authentication", 2)),
        (("Authentication", 2), ("Access_Server", 2)),
        (("Access_Server", 2), ("Deploy_malware", 2)),
        (("Deploy_malware", 2), ("Config_PB", 2)),
        (("Config_PB", 2), ("Token_Impersonation", 2)),
        (("Token_Impersonation", 2), ("Connect_NRF", 2)),
        (("Connect_NRF", 2), ("Connect_SMF", 2)),
        (("Connect_SMF", 2), ("Connect_UPF", 2)),
        (("Connect_UPF", 2), ("Create_GTP", 2)),
        (("Create_GTP", 2), ("Connect_UE", 2)),
        (("Connect_UPF", 2), ("Connect_C2", 2)),
        (("Connect_C2", 2), ("Rule_based_MPB", 2)),
        (("Rule_based_MPB", 2), ("Exfiltrating_data", 2)),
        (("Exfiltrating_data", 2), ("goal_node", 2)),
        (("Access_Server", 2), ("Portable_Execution", 2)),
        (("Portable_Execution", 2), ("Agent_based_MPB", 2)),
        (("Agent_based_MPB", 2), ("Launch_Agent", 2)),
        (("Launch_Agent", 2), ("goal_node", 2)),
        (("Access_Server", 2), ("Query_SMF", 2)),
        (("Query_SMF", 2), ("Connect_NRF", 2)),
        (("Connect_NRF", 2), ("Connect_NEF", 2)),
        (("Logon_PB", 2), ("Bypass_Authentication", 2)),
        (("Bypass_Authentication", 2), ("Access_Server", 2)),
        (("Remote_access_PB", 2), ("Bypass_Authentication", 2)),
(("Connect_NRF", 0), ("Connect_SMF", 1)),
        (("Connect_SMF", 0), ("Connect_UPF", 1)),
        (("Connect_UPF", 0), ("Create_GTP", 1)),
        (("Create_GTP", 0), ("Connect_UE", 1)),
        (("Connect_UPF", 0), ("Connect_C2", 1)),
        (("Connect_C2", 0), ("Rule_based_MPB", 1)),
        (("Rule_based_MPB", 0), ("Exfiltrating_data", 1)),
        (("Exfiltrating_data", 0), ("goal_node", 1)),
        (("Access_Server", 0), ("Portable_Execution", 1)),
        (("Portable_Execution", 0), ("Agent_based_MPB",1)),
        (("Agent_based_MPB", 0), ("Launch_Agent", 1)),
        (("Launch_Agent", 0), ("goal_node", 1)),
        (("Access_Server", 0), ("Query_SMF", 1)),
        (("Query_SMF", 0), ("Connect_NRF", 1)),
        (("Connect_NRF", 0), ("Connect_NEF", 1)),
        (("Logon_PB", 0), ("Bypass_Authentication", 1)),
        (("Bypass_Authentication", 0), ("Access_Server", 1)),
        (("Remote_access_PB", 0), ("Bypass_Authentication", 1)),
(("Input_Credentials", 1), ("Authentication", 2)),
        (("Authentication", 1), ("Access_Server", 2)),
        (("Access_Server", 1), ("Deploy_malware", 2)),
        (("Deploy_malware", 1), ("Config_PB", 2)),
        (("Config_PB", 1), ("Token_Impersonation", 2)),
        (("Token_Impersonation", 1), ("Connect_NRF", 2)),
        (("Connect_NRF", 1), ("Connect_SMF", 2)),
        (("Connect_SMF", 1), ("Connect_UPF", 2)),
        (("Connect_UPF", 1), ("Create_GTP", 2)),
        (("Create_GTP", 1), ("Connect_UE", 2)),
        (("Connect_UPF", 1), ("Connect_C2", 2)),
        (("Connect_C2", 1), ("Rule_based_MPB", 2)),
        (("Rule_based_MPB", 1), ("Exfiltrating_data", 2)),
        (("Exfiltrating_data", 1), ("goal_node", 2)),
        (("Access_Server", 1), ("Portable_Execution", 2)),
        (("Portable_Execution", 1), ("Agent_based_MPB", 2)),
        (("Agent_based_MPB", 1), ("Launch_Agent", 2)),
        (("Launch_Agent",1), ("goal_node", 2)),
        (("Access_Server", 1), ("Query_SMF", 2)),
        (("Query_SMF", 1), ("Connect_NRF", 2)),
        (("Connect_NRF", 1), ("Connect_NEF", 2)),
        (("Logon_PB", 1), ("Bypass_Authentication", 2)),
        (("Bypass_Authentication", 1), ("Access_Server", 2)),
        (("Remote_access_PB", 1), ("Bypass_Authentication", 2)),
    ]
)
model.fit(df)

# nx.nx_pydot.write_dot(model, 'model_struct.dot')
# s = Source.from_file('model_struct.dot')
# s.render(format='png', view=True)
# Image(filename='model_struct.dot.png')


#try inference
map = {0: 'False', 1: 'True' }
dbn_inf = pgmpy.inference.DBNInference(model)
result = dbn_inf.forward_inference([('Access_Server', 1)], {('Logon_PB', 0):1, ('Logon_PB', 1):1, ('Access_Server', 0):1})
arr = result[('Access_Server', 1)].values
print()
print('(Logon_PB, 0):1, (Logon_PB, 1):1, (Access_Server, 0):1: {0} ({1} %)'.format(map[np.argmax(arr)], np.max(arr) * 100))
print()

