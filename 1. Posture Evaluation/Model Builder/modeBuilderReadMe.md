# Model Builder Readme

## Location and dependency correction

The working folders in this repo are:
- /home/ubuntu/5GSPP/1. Posture Evaluation/Model Builder
- /home/ubuntu/5GSPP/1. Posture Evaluation/Sequence Generation

The model builder imports generate_seq from Sequence Generation.

## What this module does

model_builder.py builds a Bayesian Network from generated event sequences and estimates posture probabilities for target events such as goal_node, Exfiltrating_data, Launch_Agent, and Token_Impersonation.

It also includes utilities for:
- sequence/log parsing
- graph traversal
- attacker capability labeling
- exporting experiment/result CSV files

## Environment and requirements

Create a virtual environment and the use it. For example I use the virtual environment already created at:
- /home/ubuntu/5GSPP/venv_5gspp

Activate venv
source /home/ubuntu/5GSPP/venv_5gspp/bin/activate

Install requirements in that environment:

/home/ubuntu/5GSPP/venv_5gspp/bin/python -m pip install --upgrade pip
/home/ubuntu/5GSPP/venv_5gspp/bin/python -m pip install numpy pandas networkx matplotlib scikit-learn scipy pydotplus graphviz pydot "pgmpy<0.1.25"

Important compatibility note:
- model_builder.py imports BDeuScore/BicScore/K2Score from pgmpy.estimators.
- This requires an older pgmpy API.
- Use pgmpy<0.1.25 for this code as currently written.

System package needed for graph rendering:
- sudo apt-get install graphviz

## How to run

Recommended run command:

cd "/home/ubuntu/5GSPP/1. Posture Evaluation/Sequence Generation"
PYTHONPATH="/home/ubuntu/5GSPP/1. Posture Evaluation/Model Builder:/home/ubuntu/5GSPP/1. Posture Evaluation/Sequence Generation" /home/ubuntu/5GSPP/venv_5gspp/bin/python "/home/ubuntu/5GSPP/1. Posture Evaluation/Model Builder/model_builder.py"

Deterministic smoke harness command:

cd "/home/ubuntu/5GSPP/1. Posture Evaluation/Sequence Generation"
PYTHONPATH="/home/ubuntu/5GSPP/1. Posture Evaluation/Model Builder:/home/ubuntu/5GSPP/1. Posture Evaluation/Sequence Generation" /home/ubuntu/5GSPP/venv_5gspp/bin/python "/home/ubuntu/5GSPP/1. Posture Evaluation/Model Builder/model_builder.py" --smoke --smoke-log-file sequence_test.txt --smoke-structure-file structure.json

Why run from Sequence Generation:
- run_model_builder default inputs are sequences.txt and structure.json (expected in current working directory).

## Required input files

Minimum files needed to run defaults:
- sequences.txt (event sequences, one sequence per line, comma-separated events)
- structure.json (event transition dictionary)

Files used by default full run:
- structure_with_loop.json
- structure_with_pattern.json
- sequences_atck_pattern.txt (created/generated during execution)

If structure_with_loop.json is not present in Model Builder, provide it from Sequence Generation (copy or symlink).

## Output files produced

Depending on invoked functions, the module writes:
- synthetic_events.csv
- model.json
- model_struct.dot / model_probs.dot and rendered images
- results_network_scalability_test_upf.csv
- results_no_of_policy_breach - original_8_jan_23.csv
- 09_dec_22_results_more_path_10000_norm_dist.csv
- data_for_exp_ExfData_23Feb.csv
- sequences.txt (append in updt_mdl)

## Function reference (inputs, outputs, behavior)

1) class Graph
- Purpose: directed graph utility with BFS reachability.
- Constructor input: vertices (int)
- Methods:
  - addEdge(u, v): adds a directed edge, returns None
  - isReachable(s, d): returns bool

2) get_f1_score(estimated_model, true_model)
- Input: two networkx-compatible graph models
- Output: returns None, prints F1 score of skeleton adjacency

3) retrieve_data_from_logs(log_file)
- Input: log_file (path to sequence file)
- Output: tuple(event_types, data, line_ops)
  - event_types: sorted unique list of events
  - data: numpy array histogram per sequence
  - line_ops: list of tokenized sequence lines

4) draw_graph(model, title, edges=None)
- Input: model (networkx graph), title (str), edges (dict edge->weight optional)
- Output: writes dot/png artifacts, returns None
- Note: uses Graphviz rendering.

5) build_edges(model)
- Input: fitted pgmpy BayesianNetwork
- Output: tuple(edge_labels, new_BN)
  - edge_labels: dict((u,v)->P(v=1|u=1))
  - new_BN: BayesianNetwork with same edges

6) get_key(val, nodes_dict)
- Input: val (int/object), nodes_dict (dict)
- Output: key for matching value or string "key doesn't exist"

7) run_model_builder(log_file='sequences.txt', file_name='structure.json', tme=0)
- Input:
  - log_file: event sequence file
  - file_name: structure json file
  - tme: placeholder argument for DBN extension
- Output:
  - infer: VariableElimination object
  - bmodel: fitted BayesianNetwork
  - no_of_nodes: int
  - no_of_edges: int
  - posture_value_goal_node: float
  - build_time: float seconds
  - prediction_time: float seconds
- Behavior summary:
  - reads sequence data
  - builds direct structure from adjacent events
  - fits BN with MLE
  - computes edge probabilities and posture query
  - writes synthetic_events.csv and model.json

8) effect_of_no_of_breach(node_count='', no_of_time=1)
- Input: node_count (unused), no_of_time (int)
- Output: None
- Behavior: iterates breach combinations, regenerates sequences/models, writes results via get_result.

9) network_scalability_test(no_of_time=2)
- Input: no_of_time repetitions per node scale
- Output: None (writes results CSV)
- Behavior: scales nodes using generate_seq dependency and evaluates build/prediction/posture metrics.

10) number_of_policy_breach_effect_test(no_of_time=2)
- Input: no_of_time repetitions
- Output: None (writes results CSV)
- Behavior: evaluates posture metrics under selected evidence configurations.

11) generate_single_sequence(events, dependencies, from_start=True)
- Input:
  - events: list of event names
  - dependencies: structure dictionary
  - from_start: bool
- Output: list of events in generated path (without terminal end)

12) generate_attacker_capability(no_of_attacker, events, dependencies)
- Input: attacker count, event list, dependency dict
- Output: attacker_capabilities (list of generated event sequences)
- Behavior: samples capability lengths, generates sequences, computes outcomes via get_result.
- You can use multiple statstical distribution which are commented.

13) get_result(bmodel, evidences, event_seq, successfull_attacker_count)
- Input:
  - bmodel: fitted BayesianNetwork
  - evidences: dict(event->state)
  - event_seq: list
  - successfull_attacker_count: int
- Output: None (appends one row to result CSV)

14) get_attacker_events_list_capabiliteis(no_of_events)
- Input: capability threshold level (int)
- Output: list of events whose predefined level <= no_of_events

15) get_attacker_actual_capabiliteis(attacker_capability)
- Input: attacker_capability list of events
- Output: list of events up to maximum level found in attacker_capability

16) identify_attack_stage(generated_seq)
- Input: generated_seq list
- Output: stage label string: Stage 1, Stage 2, or Stage 3

17) identify__attacker_capability(generated_seq)
- Input: generated_seq list
- Output: capability bucket integer 1..5 based on sequence length

18) updt_mdl(model, seq, event_types)
- Input: model (unused in current implementation), seq string, event_types (unused)
- Output: None
- Behavior: appends seq to sequences.txt if file exists.

19) return_all_combination_list(given_list)
- Input: list
- Output: all non-empty combinations as list of lists

20) generate_data_file_for_exp(target_goal_node='Exfiltrating_data')
- Input: target goal node string
- Output: None (writes timestamped posture rows to CSV)

21) myDFS(graph, start, end, path=[])
- Input: graph with get_children(node), start node, end node, path accumulator
- Output: current traversal path; also appends full paths to global paths list

## Test status run on April 21, 2026

Verified with project venv and compatible pgmpy version:
- Passed smoke checks:
  - Graph.addEdge and Graph.isReachable
  - retrieve_data_from_logs
  - get_key
  - return_all_combination_list
  - get_attacker_events_list_capabiliteis
  - get_attacker_actual_capabiliteis
  - identify_attack_stage
  - identify__attacker_capability
  - generate_single_sequence
  - run_model_builder
  - get_result
  - updt_mdl
  - effect_of_no_of_breach(no_of_time=0)
  - number_of_policy_breach_effect_test(no_of_time=0)
  - myDFS (with tiny test graph wrapper)

- Heavy-path execution status:
  - network_scalability_test: executed and passed in terminal run
  - generate_attacker_capability: executed and failed in terminal run with runtime/index issues (observed errors included np.str_('Logon_PB') and list index out of range)


## Practical modification guide

1) Change input data source
- Update log_file argument in run_model_builder to any sequence file.

2) Change dependency graph
- Update file_name argument in run_model_builder to another structure json.

3) Change experiment size/repetition
- Adjust no_of_time in experiment functions.

4) Import behavior
- Import-time side effects are removed.
- Script execution is now under if __name__ == '__main__': and supports CLI flags.

5) Resolve path assumptions
- Prefer absolute paths or compute paths from DIR for log_file and structure file inputs.

## Quick execution examples

Single model run:

cd "/home/ubuntu/5GSPP/1. Posture Evaluation/Sequence Generation"
PYTHONPATH="/home/ubuntu/5GSPP/1. Posture Evaluation/Model Builder:/home/ubuntu/5GSPP/1. Posture Evaluation/Sequence Generation" /home/ubuntu/5GSPP/venv_5gspp/bin/python -c "import model_builder as mb; out=mb.run_model_builder(log_file='sequence_test.txt', file_name='structure.json', tme=1); print(out[2], out[3], out[4])"

Smoke harness run:

cd "/home/ubuntu/5GSPP/1. Posture Evaluation/Sequence Generation"
PYTHONPATH="/home/ubuntu/5GSPP/1. Posture Evaluation/Model Builder:/home/ubuntu/5GSPP/1. Posture Evaluation/Sequence Generation" /home/ubuntu/5GSPP/venv_5gspp/bin/python "/home/ubuntu/5GSPP/1. Posture Evaluation/Model Builder/model_builder.py" --smoke

Generate only combinations utility check:

PYTHONPATH="/home/ubuntu/5GSPP/1. Posture Evaluation/Model Builder" /home/ubuntu/5GSPP/venv_5gspp/bin/python -c "import model_builder as mb; print(mb.return_all_combination_list(['a','b','c']))"
