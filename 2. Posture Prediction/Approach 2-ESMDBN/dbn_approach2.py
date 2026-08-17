"""
Approach 2: Event-State Model-based DBN (Dynamic Bayesian Network)
Implements inference on temporal event sequences using DBN for multi-time-step prediction
Based on Fig. 16 methodology
"""

import numpy as np
import pandas as pd
import pickle
import json
from pathlib import Path
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')

try:
    from pgmpy.models import DynamicBayesianNetwork as DBN
    from pgmpy.models import BayesianNetwork
    from pgmpy.inference import VariableElimination
    from pgmpy.factors.discrete import TabularCPD
except ImportError:
    print("Error: pgmpy not found. Please install with: pip install pgmpy")
    import sys
    sys.exit(1)


class EventStateDBNModel:
    """
    Event-State Model-based DBN for sequence prediction
    Implements temporal reasoning over multiple time slices
    """
    
    def __init__(self, model_path=None, num_time_slices=3):
        """
        Initialize DBN model
        
        Args:
            model_path (str): Path to pickled Bayesian Network model
            num_time_slices (int): Number of time slices for DBN
        """
        self.num_time_slices = num_time_slices
        self.bn_model = None
        self.dbn_model = None
        self.inference = None
        self.events = []
        self.event_to_idx = {}
        
        if model_path:
            self.load_model(model_path)
    
    def load_model(self, model_path):
        """
        Load a pre-trained Bayesian Network
        
        Args:
            model_path (str): Path to model.pkl file
        """
        with open(model_path, 'rb') as f:
            self.bn_model = pickle.load(f)
        
        # Extract events from model
        self.events = list(self.bn_model.nodes())
        self.event_to_idx = {event: idx for idx, event in enumerate(self.events)}
        
        print(f"Loaded model with {len(self.events)} events")
    
    def build_dbn(self):
        """
        Build Dynamic Bayesian Network from static Bayesian Network
        Creates connections across time slices
        """
        if self.bn_model is None:
            raise ValueError("No model loaded. Call load_model() first.")
        
        # Create DBN
        self.dbn_model = DBN()
        
        # Add edges for each time slice
        for t in range(self.num_time_slices):
            # Add intra-time-slice edges (from current model)
            for edge in self.bn_model.edges():
                parent, child = edge
                self.dbn_model.add_edges_from([
                    ((parent, t), (child, t))
                ])
            
            # Add inter-time-slice edges (temporal connections)
            if t < self.num_time_slices - 1:
                for event in self.events:
                    # Each event at time t influences the same event at time t+1
                    self.dbn_model.add_edges_from([
                        ((event, t), (event, t+1))
                    ])
        
        print(f"Built DBN with {len(self.dbn_model.nodes())} nodes and " 
              f"{len(self.dbn_model.edges())} edges across {self.num_time_slices} time slices")
    
    def add_cpds_from_bn(self):
        """
        Add CPDs (Conditional Probability Distributions) from static BN to DBN
        """
        if self.dbn_model is None:
            self.build_dbn()
        
        if self.bn_model is None:
            raise ValueError("No model loaded")
        
        # Get CPDs from the static Bayesian Network
        cpds_static = self.bn_model.get_cpds()
        
        # For each time slice, replicate the CPDs with temporal variables
        for t in range(self.num_time_slices):
            for cpd in cpds_static:
                # Get variable and evidence variables
                var = cpd.variable
                evidence_vars = cpd.variables[1:]  # All except the first are evidence
                
                # Create new variable names with time index
                new_var = (var, t)
                new_evidence = [(ev, t) for ev in evidence_vars]
                
                try:
                    # Get evidence cardinality
                    evidence_card = [len(self.bn_model.get_cardinality(ev)) 
                                   for ev in evidence_vars]
                    
                    # Create new CPD for temporal variable
                    new_cpd = TabularCPD(
                        variable=new_var,
                        variable_card=len(self.bn_model.get_cardinality(var)),
                        evidence=new_evidence,
                        evidence_card=evidence_card,
                        values=cpd.values
                    )
                    
                    self.dbn_model.add_cpds(new_cpd)
                except Exception as e:
                    # Skip if CPD creation fails
                    pass
        
        print("Added CPDs from static model to DBN")
    
    def perform_inference(self, observations, query_vars, time_step=-1):
        """
        Perform inference on the DBN
        
        Args:
            observations (dict): Event observations as {event: value}
            query_vars (list): Events to query
            time_step (int): Time slice to query (-1 for last)
            
        Returns:
            dict: Query results with probabilities
        """
        if self.dbn_model is None:
            self.build_dbn()
        
        if time_step == -1:
            time_step = self.num_time_slices - 1
        
        try:
            # Create inference engine
            infer = VariableElimination(self.dbn_model)
            
            # Convert observations to temporal format (all time slices)
            evidence = {}
            for event, value in observations.items():
                # Apply evidence to first time slice
                evidence[(event, 0)] = value
            
            # Query the specified time slice
            results = {}
            for query_var in query_vars:
                query_tuple = (query_var, time_step)
                
                if query_tuple in self.dbn_model.nodes():
                    try:
                        result = infer.query([query_tuple], evidence=evidence)
                        # Extract probability
                        prob = result.values[1] if len(result.values) > 1 else result.values[0]
                        results[query_var] = float(prob)
                    except:
                        results[query_var] = 0.5  # Default to 0.5 if inference fails
                else:
                    results[query_var] = None
            
            return results
        
        except Exception as e:
            print(f"Inference error: {e}")
            return {var: 0.5 for var in query_vars}
    
    def predict_sequence(self, initial_events, num_steps=3):
        """
        Predict future events based on initial sequence
        
        Args:
            initial_events (dict): Initial event states
            num_steps (int): Number of steps to predict
            
        Returns:
            list: Predicted sequences
        """
        predictions = [initial_events.copy()]
        current_state = initial_events.copy()
        
        for step in range(num_steps):
            # Get inference for next state
            next_state = {}
            
            for event in self.events:
                # Query probability of each event
                if event in current_state:
                    prob = current_state[event]
                else:
                    prob = 0.5
                
                # Simple forward propagation
                next_state[event] = 1 if prob > 0.5 else 0
            
            predictions.append(next_state.copy())
            current_state = next_state
        
        return predictions
    
    def get_inference_table(self, observations, query_vars):
        """
        Generate inference results table (as in Fig. 16)
        
        Args:
            observations (dict): Observed conditions
            query_vars (list): Variables to infer
            
        Returns:
            pd.DataFrame: Inference results table
        """
        # Perform inference for different condition combinations
        results_list = []
        
        # Generate combinations of observations
        cond_keys = list(observations.keys())
        num_conds = len(cond_keys)
        
        # Try different combinations
        for i in range(2 ** num_conds):
            obs_combo = {}
            cond_list = []
            
            for j, key in enumerate(cond_keys):
                if (i >> j) & 1:
                    obs_combo[key] = 1
                    cond_list.append(f"{key}:1")
                else:
                    obs_combo[key] = 0
                    cond_list.append(f"{key}:0")
            
            # Run inference
            results = self.perform_inference(obs_combo, query_vars)
            
            # Create row
            row = {
                'conditions': ', '.join(cond_list),
                **obs_combo,
                **{f'{var}_prob': results.get(var, 0.5) for var in query_vars}
            }
            results_list.append(row)
        
        return pd.DataFrame(results_list)


class SequenceAnalyzer:
    """Analyze and compare sequences for attack detection"""
    
    def __init__(self, dbn_model):
        """
        Initialize analyzer
        
        Args:
            dbn_model (EventStateDBNModel): Trained DBN model
        """
        self.dbn_model = dbn_model
    
    def analyze_sequence(self, events, goal_events):
        """
        Analyze a sequence for goal achievement likelihood
        
        Args:
            events (list): Sequence of events
            goal_events (list): Events indicating goal achievement
            
        Returns:
            dict: Analysis results
        """
        # Convert event sequence to observation dict
        observations = {}
        for event in self.dbn_model.events:
            observations[event] = 1 if event in events else 0
        
        # Perform inference for goal nodes
        results = self.dbn_model.perform_inference(observations, goal_events)
        
        return {
            'sequence': events,
            'goal_probabilities': results,
            'max_goal_prob': max(results.values()) if results else 0,
            'risk_level': self._compute_risk_level(results)
        }
    
    def _compute_risk_level(self, probabilities):
        """
        Compute overall risk level from probabilities
        
        Args:
            probabilities (dict): Event probabilities
            
        Returns:
            str: Risk level ('low', 'medium', 'high')
        """
        max_prob = max(probabilities.values()) if probabilities else 0
        
        if max_prob < 0.3:
            return 'low'
        elif max_prob < 0.7:
            return 'medium'
        else:
            return 'high'
    
    def detect_attack_patterns(self, sequence, pattern_library):
        """
        Detect known attack patterns in sequence
        
        Args:
            sequence (list): Event sequence
            pattern_library (list): Known attack patterns
            
        Returns:
            list: Matched patterns with confidence
        """
        matches = []
        
        for pattern in pattern_library:
            # Simple pattern matching: check if pattern events are in sequence
            pattern_events = set(pattern.get('events', []))
            sequence_events = set(sequence)
            
            match_ratio = len(pattern_events & sequence_events) / len(pattern_events) if pattern_events else 0
            
            if match_ratio > 0.5:  # At least 50% match
                matches.append({
                    'pattern': pattern.get('name', 'unknown'),
                    'confidence': match_ratio,
                    'risk_level': pattern.get('risk_level', 'medium')
                })
        
        return sorted(matches, key=lambda x: x['confidence'], reverse=True)
