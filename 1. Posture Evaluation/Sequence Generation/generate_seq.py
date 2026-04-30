#import random
import os
from numpy import random
import numpy as np
import json
import os

dependencies = {}
events = []


#generate_multiple_nodes funciton is used for scalablity test
def generate_multiple_nodes(number_of_nodes = 10, node_name=''):
    DIR = os.path.dirname(os.path.abspath(__file__)) 
    if node_name == '':
        return "Node name is empty"
    
    with open(os.path.join(DIR, 'structure.json')) as f:
        dependencies = json.load(f) #return dictionary
        events = [e for e in dependencies] #return list
        
#    node_keys = dependencies.keys()
    
    if node_name in events:
                 
        node_value = dependencies[node_name]
        for i in range(number_of_nodes):
            new_node_name = node_name+'_'+str((i+1))
            new_prob_val = (1/(i+3))
            dependencies[new_node_name] = node_value
            if node_name == "Connect_UPF":
                dependencies["Connect_SMF"][0].append(new_node_name)
                dependencies["Connect_PCF"][0].append(new_node_name)
                dependencies["Connect_NEF"][0].append(new_node_name)
                
                dependencies["Connect_SMF"][1] = [new_prob_val]*(i+3)
                dependencies["Connect_PCF"][1] = [new_prob_val]*(i+3)
                dependencies["Connect_NEF"][1] = [new_prob_val]*(i+3)
            elif node_name == "Connect_NEF":
                new_prob_val = (1/(i+5))
                dependencies["Connect_NRF"][0].append(new_node_name)
                dependencies["Connect_NRF"][1] = [new_prob_val]*(i+5)
    else:
        return 'node_name is wrong. Input correct node_name'
        dependencies["Connect_SMF"][0] = [new_prob_val]*(i+3)
    
    structure_file_name = 'structure_' + node_name + '_' + str(number_of_nodes) + '.json' 
    with open(structure_file_name, 'w') as f:
        json.dump(dependencies, f)


#used to geenerate events randomly            
def generate_consistent_seq(save_file_name = 'sequences.txt', file_name = 'structure.json', from_start = True, append_with_prev = False):
    DIR = os.path.dirname(os.path.abspath(__file__))
#    DIR = 'H:\\Concordia PHD\\Research\\Network Security\\5 G\\5G Testbed\\From Mahmood\\SourceCode\\'
# 	DIR = "D:\\OneDrive - Concordia University - Canada\Research\\Network Security\\5G\\5G Testbed\\From Mahmood\\SourceCode\\"

	# Clean file
    if os.path.exists(save_file_name):
        if append_with_prev == False:
            os.remove(save_file_name)
    
            
    with open(os.path.join(DIR, file_name)) as f:
        dependencies = json.load(f) #return dictionary
        events = [e for e in dependencies] #return list: all the keys from the JSON
    
    n = 5500
    
    for i in range(n):
        seq =  []
        if from_start:
            # s = [k for k,v in event_keys_values.items() if v == 1]
            s = ['Authentication', 'Logon_PB']
            prob = [0.4, 0.6]
            previous_event = np.random.choice(s, p=prob)
        else:
            previous_event = np.random.choice(events)

        next_event = ''
        seq.append(previous_event)
        # print("i: ", i, previous_event)
        # While it's not last event
        while((previous_event != "end") and (len(dependencies[previous_event][0]) > 0)):
            next_event = np.random.choice(dependencies[previous_event][0], p=dependencies[previous_event][1])
            if next_event not in seq: #check if the event already exists
                seq.append(next_event)
                previous_event = next_event

        # Turn to string, remove "end" event
        string_seq = ','.join(seq[:-1])
        # Write with append mode
        with open(save_file_name, 'a') as w:
            w.write(string_seq+'\n')


generate_consistent_seq(save_file_name='sequence_test.txt', from_start=True)

