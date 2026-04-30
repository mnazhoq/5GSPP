# 5G Security Posture Event Sequence Generator

## Overview

This module generates synthetic event sequences for 5G security posture analysis. It creates realistic attack event sequences based on a probabilistic dependency graph that models how different 5G network components interact during attack scenarios.

## Features

- **Probabilistic Event Sequence Generation**: Creates realistic event sequences based on conditional probabilities
- **Scalability Testing**: Support for duplicating nodes to test scalability
- **Flexible Configuration**: Multiple output formats and customizable parameters
- **Attack Path Simulation**: Models realistic attack paths through 5G network components

---

## Setup Instructions

### 1. Create and Activate Virtual Environment

```bash
# Navigate to the 5GSPP folder
cd /home/ubuntu/5GSPP

# Activate the virtual environment
source venv_5gspp/bin/activate

# On Windows:
# venv_5gspp\Scripts\activate

# Install dependencies
pip install numpy
```

### 2. Required Dependencies

- **Python**: 3.7 or higher
- **NumPy**: 2.2.6 (for random number generation and array operations)

To install manually:
```bash
pip install numpy
```

---

## File Structure

```
5GSPP/1. Posture Evaluation/Sequence Generation/
├── generate_seq.py                    # Main script with all functions
├── structure.json                     # Base event dependency graph
├── structure_[NODE]_[N].json         # Generated structure files with scaled nodes
├── sequence_test.txt                 # Generated event sequences (output)
└── README.md                          # This file
```

---

## Data Structures

### Structure File Format (structure.json)

The structure file is a JSON dictionary where each key is an event name and the value is a dependency specification:

```json
{
  "EventName": [
    ["NextEvent1", "NextEvent2", "end"],  // Possible next events
    [0.6, 0.3, 0.1]                       // Probability for each next event
  ]
}
```

**Example**:
```json
{
  "Authentication": [
    ["SystemUseNotPB", "Access_Server", "end"],
    [0.2, 0.6, 0.2]
  ]
}
```

This means:
- From "Authentication", transition to:
  - "SystemUseNotPB" with 20% probability
  - "Access_Server" with 60% probability
  - "end" (terminate sequence) with 20% probability

### Output File Format (sequence_test.txt)

Each line contains a comma-separated sequence of events:
```
Authentication,Access_Server,Deploy_malware,Config_PB,Token_Impersonation,Connect_NRF
Logon_PB,Bypass_Authentication,Access_Server,Query_SMF,Connect_NRF
Authentication,SystemUseNotPB,Access_Server,Deploy_malware,Config_PB
```

---

## Functions

### 1. `generate_consistent_seq()`

**Purpose**: Generate random event sequences based on the probabilistic dependency graph.

**Parameters**:
- `save_file_name` (str, default: `'sequences.txt'`)
  - Name of the output file where sequences will be saved
  - Example: `'sequence_test.txt'`

- `file_name` (str, default: `'structure.json'`)
  - Name of the input structure file containing the dependency graph
  - Should be a JSON file in the same directory
  - Example: `'structure.json'` or `'structure_Connect_UPF_10.json'`

- `from_start` (bool, default: `True`)
  - If `True`: Start all sequences from predefined initial events (Authentication or Logon_PB)
  - If `False`: Start from any random event in the structure
  - Recommended: `True` for realistic attack simulations

- `append_with_prev` (bool, default: `False`)
  - If `True`: Append new sequences to existing file (keeps previous sequences)
  - If `False`: Overwrite the file (creates new file with fresh sequences)
  - Use `True` for incremental data generation

**Returns**: None (writes sequences to file)

**Output**: Text file with one sequence per line, events separated by commas

**Example**:
```python
# Generate 5500 sequences starting from initial events
generate_consistent_seq(
    save_file_name='sequence_test.txt',
    file_name='structure.json',
    from_start=True,
    append_with_prev=False
)

# Append 1000 more sequences to existing file
generate_consistent_seq(
    save_file_name='sequence_test.txt',
    file_name='structure.json',
    from_start=True,
    append_with_prev=True
)
Change value of n to generate different number (lines) of sequences.
n = 1000
```

**How It Works**:
1. Loads the structure file (JSON with event dependencies)
2. Generates 5500 sequences by:
   - Starting with initial event(s) based on `from_start` parameter
   - Randomly selecting next events based on probabilities
   - Continuing until reaching "end" event
   - Removing duplicate events in a sequence
3. Writes sequences to output file

---

### 2. `generate_multiple_nodes()`

**Purpose**: Create multiple instances of a specific node for scalability testing. Used to generate new structure files with duplicated/scaled nodes.

**Parameters**:
- `number_of_nodes` (int, default: `10`)
  - Number of duplicate instances to create for the target node
  - Example: `10` creates node_1, node_2, ..., node_10

- `node_name` (str, default: `''`)
  - Name of the event node to duplicate
  - Must be an existing key in `structure.json`
  - Supported nodes: `'Connect_UPF'`, `'Connect_NEF'`
  - Example: `'Connect_UPF'` or `'Connect_NEF'`

**Returns**: String error message if `node_name` is invalid, None otherwise

**Output**: Creates a new JSON file named `structure_[NODE_NAME]_[NUMBER].json`

**Example**:
```python
# Create 10 instances of Connect_UPF node
generate_multiple_nodes(number_of_nodes=10, node_name='Connect_UPF')
# Creates: structure_Connect_UPF_10.json

# Create 25 instances of Connect_NEF node
generate_multiple_nodes(number_of_nodes=25, node_name='Connect_NEF')
# Creates: structure_Connect_NEF_25.json
```

**How It Works**:
1. Loads the base structure from `structure.json`
2. Finds the specified node
3. Creates multiple copies: `[NodeName]_1`, `[NodeName]_2`, etc.
4. Updates probabilities for dependent nodes
5. Saves as a new structure file for scalability testing

**Valid Nodes**:
- `'Connect_UPF'`: Updates dependencies for SMF, PCF, NEF nodes
- `'Connect_NEF'`: Updates dependency for NRF node

---

## Usage Examples

### Basic Usage: Generate Sequences

```bash
# Activate virtual environment
source /home/ubuntu/5GSPP/venv_5gspp/bin/activate

# Run the script
cd /home/ubuntu/5GSPP/1.\ Posture\ Evaluation/Sequence\ Generation/
python3 generate_seq.py
```

### Modify and Run in Python

Create a custom script `custom_sequence_gen.py`:

```python
#!/usr/bin/env python3
import os
import json
from numpy import random
import numpy as np

# Import or copy the functions from generate_seq.py

# Generate sequences from different structure files
def main():
    # Generate with default parameters
    generate_consistent_seq()
    print("✓ Default sequences generated: sequences.txt")
    
    # Generate with specific structure file
    generate_consistent_seq(
        save_file_name='seq_upf_scaled.txt',
        file_name='structure_Connect_UPF_10.json',
        from_start=True,
        append_with_prev=False
    )
    print("✓ Scaled UPF sequences generated: seq_upf_scaled.txt")
    
    # Generate multiple node instances for scalability test
    generate_multiple_nodes(number_of_nodes=15, node_name='Connect_UPF')
    
    # Generate sequences from the newly created structure
    generate_consistent_seq(
        save_file_name='seq_upf_15nodes.txt',
        file_name='structure_Connect_UPF_15.json',
        from_start=True,
        append_with_prev=False
    )
    print("✓ Sequences from scaled structure generated: seq_upf_15nodes.txt")

if __name__ == "__main__":
    main()
```

Run the custom script:
```bash
python3 custom_sequence_gen.py
```

---

## Customization Guide

### Modifying Event Probabilities

Edit `structure.json` to change probability values:

```json
{
  "Authentication": [
    ["SystemUseNotPB", "Access_Server", "end"],
    [0.1, 0.7, 0.2]  // Changed from [0.2, 0.6, 0.2]
  ]
}
```

The probabilities must sum to 1.0.

### Adding New Events

1. Add the new event to `structure.json`:
```json
{
  "new_event": [
    ["next_event1", "next_event2", "end"],
    [0.6, 0.3, 0.1]
  ]
}
```

2. Update existing events to include the new event as a possible transition:
```json
{
  "some_event": [
    ["new_event", "other_event", "end"],
    [0.4, 0.4, 0.2]
  ]
}
```

### Changing Number of Generated Sequences

Modify the `n` variable in `generate_consistent_seq()`:

```python
# Original: n = 5500
# Change to your desired number:
n = 10000  # Generate 10,000 sequences
```

### Changing Initial Events

Modify the initial event selection in `generate_consistent_seq()`:

```python
# Original initial events
if from_start:
    s = ['Authentication', 'Logon_PB']
    prob = [0.4, 0.6]
    previous_event = np.random.choice(s, p=prob)

# Custom example:
# if from_start:
#     s = ['Authentication', 'Logon_PB', 'Remote_access_PB']
#     prob = [0.5, 0.3, 0.2]
#     previous_event = np.random.choice(s, p=prob)
```

---

## Performance Notes

- **Default**: 5,500 sequences take approximately 5-10 seconds to generate
- **Memory**: ~329 KB for 5,500 sequences
- **Scalability**: Tested with 10-25 node duplications without performance issues

---

## Troubleshooting

| Issue | Solution |
|---|---|
| `ModuleNotFoundError: No module named 'numpy'` | Run `pip install numpy` in the activated venv |
| `FileNotFoundError: structure.json` | Ensure you're in the correct directory: `Sequence Generation/` |
| `KeyError: node_name` in `generate_multiple_nodes()` | Check that node_name exists in structure.json |
| Output file not created | Ensure write permissions in the directory |
| Very slow sequence generation | Check JSON file syntax, may have invalid probabilities |

---

## Output Examples

**Input (structure.json)**:
```json
"Authentication": [["SystemUseNotPB", "Access_Server", "end"], [0.2, 0.6, 0.2]]
```

**Sample Output Sequences**:
```
Authentication,Access_Server,Deploy_malware,Config_PB,Token_Impersonation,goal_node
Authentication,SystemUseNotPB,Access_Server,Query_SMF,Connect_NRF,Connect_SMF,Connect_UPF
Authentication,Access_Server,Portable_Execution,Agent_based_MPB,Launch_Agent
```

---

## File Operations Summary

| Function | Input Files | Output Files | Purpose |
|---|---|---|---|
| `generate_consistent_seq()` | `structure.json` (or custom) | `sequences.txt` | Generate event sequences |
| `generate_multiple_nodes()` | `structure.json` | `structure_[NODE]_[N].json` | Create scaled structure files |


---


## Notes

- The "end" event marks the termination of a sequence
- The "goal_node" represents successful attack completion
- Sequences are deduplicated (no repeated events within a single sequence)
- The dependency graph models realistic attack progression in 5G networks
- Probabilities are empirically derived from security research testbed implemented with free5GC on Kubernetes.

---