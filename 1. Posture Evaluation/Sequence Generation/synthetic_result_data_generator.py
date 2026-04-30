# -*- coding: utf-8 -*-
"""
Created on Tue Feb 28 09:07:39 2023

@author: umroot
"""

file_name = 'synthetic_historical_data_results.csv'  
no_of_time  = 20000 #how many row wil be in the CSV

for i in range(no_of_time):
    no_of_nodes, no_of_edges, posture_value_goal_node, build_time, prediction_time
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