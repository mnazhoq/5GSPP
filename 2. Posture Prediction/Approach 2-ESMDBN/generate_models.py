"""
Event-State Model Generator
Generates multiple Bayesian Network models with variations and saves them
"""

import os
import json
import pickle
import numpy as np
import pandas as pd
from pathlib import Path
import sys
import warnings
warnings.filterwarnings('ignore')

# Try to import pgmpy
try:
    from pgmpy.models import BayesianNetwork
    from pgmpy.estimators import MaximumLikelihoodEstimator
    from pgmpy.inference import VariableElimination
except ImportError:
    print("Error: pgmpy not found. Please install with: pip install pgmpy")
    sys.exit(1)


class EventStateModelGenerator:
    """Generate multiple event-state Bayesian Network models"""
    
    # Common events in 5G security attack sequences
    COMMON_EVENTS = [
        'Input_Credentials', 'Authentication', 'Access_Server', 'Portable_Execution',
        'Agent_based_MPB', 'Launch_Agent', 'Token_Impersonation', 'Deploy_malware',
        'Config_PB', 'Connect_NRF', 'Connect_SMF', 'Connect_UPF', 'Create_GTP',
        'Connect_UE', 'Rule_based_MPB', 'Exfiltrating_data', 'Bypass_Authentication',
        'Query_SMF', 'Remote_access_PB', 'SystemUseNotPB', 'Logon_PB',
        'Connect_NEF', 'Connect_PCF', 'Connect_C2', 'goal_node'
    ]
    
    def __init__(self, output_dir='./models'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.models = {}
        
    def generate_random_structure(self, num_events=None, density=0.3, seed=None):
        """
        Generate a random Bayesian Network structure (DAG)
        
        Args:
            num_events (int): Number of events to include
            density (float): Edge density (0-1)
            seed (int): Random seed for reproducibility
            
        Returns:
            list: List of edges (tuples)
        """
        if seed is not None:
            np.random.seed(seed)
        
        if num_events is None:
            num_events = np.random.randint(8, 16)
        
        # Select random subset of events
        events = np.random.choice(self.COMMON_EVENTS, min(num_events, len(self.COMMON_EVENTS)), replace=False)
        events = list(events)
        
        # Ensure goal_node is included
        if 'goal_node' not in events:
            events[-1] = 'goal_node'
        
        edges = []
        n = len(events)
        
        # Create a topological order to ensure DAG
        # Always add edges from earlier to later indices only
        for i in range(n):
            for j in range(i+1, n):
                if np.random.random() < density:
                    # Always add edge from i to j (earlier to later) to maintain DAG
                    edges.append((events[i], events[j]))
        
        return edges, events
    
    def generate_attack_path_structure(self, path_type='logon', seed=None):
        """
        Generate realistic attack path structures
        
        Args:
            path_type (str): Type of attack path ('logon', 'remote', 'internal')
            seed (int): Random seed
            
        Returns:
            list: List of edges
        """
        if seed is not None:
            np.random.seed(seed)
        
        attack_paths = {
            'logon': [
                ('Logon_PB', 'Authentication'),
                ('Authentication', 'Access_Server'),
                ('Access_Server', 'Token_Impersonation'),
                ('Token_Impersonation', 'Deploy_malware'),
                ('Deploy_malware', 'Config_PB'),
                ('Config_PB', 'Connect_NRF'),
                ('Connect_NRF', 'Connect_SMF'),
                ('Connect_SMF', 'Exfiltrating_data'),
                ('Exfiltrating_data', 'goal_node'),
            ],
            'remote': [
                ('Remote_access_PB', 'Access_Server'),
                ('Access_Server', 'Agent_based_MPB'),
                ('Agent_based_MPB', 'Launch_Agent'),
                ('Launch_Agent', 'Token_Impersonation'),
                ('Token_Impersonation', 'Exfiltrating_data'),
                ('Exfiltrating_data', 'goal_node'),
            ],
            'internal': [
                ('SystemUseNotPB', 'Access_Server'),
                ('Access_Server', 'Portable_Execution'),
                ('Portable_Execution', 'Agent_based_MPB'),
                ('Agent_based_MPB', 'Deploy_malware'),
                ('Deploy_malware', 'Exfiltrating_data'),
                ('Exfiltrating_data', 'goal_node'),
            ],
            'bypass': [
                ('Input_Credentials', 'Bypass_Authentication'),
                ('Bypass_Authentication', 'Access_Server'),
                ('Access_Server', 'Query_SMF'),
                ('Query_SMF', 'Connect_NRF'),
                ('Connect_NRF', 'Connect_SMF'),
                ('Connect_SMF', 'Connect_UPF'),
                ('Connect_UPF', 'Create_GTP'),
                ('Create_GTP', 'goal_node'),
            ]
        }
        
        edges = attack_paths.get(path_type, attack_paths['logon']).copy()
        
        # Add some random additional edges (only in valid directions)
        events = list(set([e for edge in edges for e in edge]))
        event_to_idx = {e: i for i, e in enumerate(sorted(events))}
        
        for _ in range(np.random.randint(0, 2)):
            attempts = 0
            while attempts < 5:
                e1 = np.random.choice(events)
                e2 = np.random.choice(events)
                
                # Only add if creates DAG (indices maintain order)
                if (e1, e2) not in edges and (e2, e1) not in edges and e1 != e2:
                    if event_to_idx[e1] < event_to_idx[e2]:
                        edges.append((e1, e2))
                        break
                    elif event_to_idx[e2] < event_to_idx[e1]:
                        edges.append((e2, e1))
                        break
                attempts += 1
        
        return edges, events
    
    def create_synthetic_data(self, edges, events, num_samples=1000):
        """
        Create synthetic binary data for given structure
        
        Args:
            edges (list): List of edges
            events (list): List of events
            num_samples (int): Number of samples to generate
            
        Returns:
            pd.DataFrame: Synthetic data
        """
        # Simple approach: generate random binary data
        data = np.random.randint(0, 2, size=(num_samples, len(events)))
        df = pd.DataFrame(data, columns=events)
        
        # Introduce some correlations based on edges
        for parent, child in edges:
            parent_idx = events.index(parent)
            child_idx = events.index(child)
            
            # If parent is 1, child has higher probability of being 1
            for i in range(num_samples):
                if data[i, parent_idx] == 1:
                    if np.random.random() > 0.7:  # 70% correlation
                        df.iloc[i, child_idx] = 1
        
        return df
    
    def fit_bayesian_network(self, edges, data):
        """
        Fit a Bayesian Network to data
        
        Args:
            edges (list): List of edges
            data (pd.DataFrame): Training data
            
        Returns:
            BayesianNetwork: Fitted model or None
        """
        try:
            # Check for cycles and validate edges
            from networkx import DiGraph, is_directed_acyclic_graph
            
            G = DiGraph()
            G.add_edges_from(edges)
            
            if not is_directed_acyclic_graph(G):
                return None  # Skip cyclic structures
            
            model = BayesianNetwork(edges)
            
            # Convert data to binary (1, 0) state names
            state_names = {col: (1, 0) for col in data.columns}
            
            model.fit(data, estimator=MaximumLikelihoodEstimator, state_names=state_names)
            return model
        
        except Exception as e:
            # Skip models that fail to fit
            return None
    
    def get_model_metadata(self, model, data):
        """
        Extract metadata from fitted model
        
        Args:
            model (BayesianNetwork): Fitted model
            data (pd.DataFrame): Data used for training
            
        Returns:
            dict: Metadata
        """
        metadata = {
            'num_nodes': len(model.nodes()),
            'num_edges': len(model.edges()),
            'nodes': list(model.nodes()),
            'edges': list(model.edges()),
            'num_samples': len(data),
            'num_features': len(data.columns)
        }
        
        return metadata
    
    def generate_model_set(self, num_models=20):
        """
        Generate a set of diverse Bayesian Network models
        
        Args:
            num_models (int): Number of models to generate
            
        Returns:
            list: List of (name, model, metadata) tuples
        """
        models_list = []
        
        # Model type 1: Random structures with different densities
        densities = [0.2, 0.3, 0.4, 0.5]
        for density in densities:
            for i in range(2):
                name = f"random_density_{density:.1f}_{i+1}"
                edges, events = self.generate_random_structure(
                    density=density, seed=hash(name) % 2**32
                )
                
                if len(edges) > 0:
                    data = self.create_synthetic_data(edges, events)
                    model = self.fit_bayesian_network(edges, data)
                    
                    if model is not None:
                        metadata = self.get_model_metadata(model, data)
                        models_list.append((name, model, metadata))
                        print(f"Generated: {name}")
                    else:
                        print(f"Skipped: {name} (invalid structure)")
        
        # Model type 2: Attack path structures
        attack_types = ['logon', 'remote', 'internal', 'bypass']
        for attack_type in attack_types:
            for i in range(2):
                name = f"attack_{attack_type}_{i+1}"
                edges, events = self.generate_attack_path_structure(
                    path_type=attack_type, seed=hash(name) % 2**32
                )
                
                if len(edges) > 0:
                    data = self.create_synthetic_data(edges, events)
                    model = self.fit_bayesian_network(edges, data)
                    
                    if model is not None:
                        metadata = self.get_model_metadata(model, data)
                        models_list.append((name, model, metadata))
                        print(f"Generated: {name}")
                    else:
                        print(f"Skipped: {name} (invalid structure)")
        
        # Model type 3: Mixed random variations
        for i in range(4):
            name = f"mixed_variation_{i+1}"
            # Mix of random and attack path
            if i % 2 == 0:
                edges, events = self.generate_random_structure(
                    num_events=12, density=0.35, seed=hash(name) % 2**32
                )
            else:
                attack_type = ['logon', 'remote', 'internal', 'bypass'][i % 4]
                edges, events = self.generate_attack_path_structure(
                    path_type=attack_type, seed=hash(name) % 2**32
                )
            
            if len(edges) > 0:
                data = self.create_synthetic_data(edges, events)
                model = self.fit_bayesian_network(edges, data)
                
                if model is not None:
                    metadata = self.get_model_metadata(model, data)
                    models_list.append((name, model, metadata))
                    print(f"Generated: {name}")
                else:
                    print(f"Skipped: {name} (invalid structure)")
        
        return models_list[:num_models]
    
    def save_models(self, models_list):
        """
        Save models to disk
        
        Args:
            models_list (list): List of (name, model, metadata) tuples
        """
        index_data = {}
        
        for name, model, metadata in models_list:
            # Create model directory
            model_dir = self.output_dir / name
            model_dir.mkdir(parents=True, exist_ok=True)
            
            # Save model pickle
            model_path = model_dir / 'model.pkl'
            with open(model_path, 'wb') as f:
                pickle.dump(model, f)
            
            # Save metadata JSON
            metadata_path = model_dir / 'metadata.json'
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Save model structure as edges
            edges_path = model_dir / 'edges.json'
            with open(edges_path, 'w') as f:
                json.dump(metadata['edges'], f, indent=2)
            
            # Index entry
            index_data[name] = {
                'path': str(model_dir),
                'metadata': metadata,
                'model_file': 'model.pkl',
                'metadata_file': 'metadata.json'
            }
            
            print(f"Saved: {name}")
        
        # Save index file
        index_path = self.output_dir / 'models_index.json'
        with open(index_path, 'w') as f:
            json.dump(index_data, f, indent=2)
        
        print(f"\nAll {len(models_list)} models saved to {self.output_dir}")
        print(f"Index file: {index_path}")
    
    def load_model(self, model_name):
        """
        Load a saved model
        
        Args:
            model_name (str): Name of the model
            
        Returns:
            tuple: (model, metadata)
        """
        model_dir = self.output_dir / model_name
        
        # Load model
        model_path = model_dir / 'model.pkl'
        with open(model_path, 'rb') as f:
            model = pickle.load(f)
        
        # Load metadata
        metadata_path = model_dir / 'metadata.json'
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        return model, metadata


def main():
    """Generate and save event-state models"""
    
    print("=" * 80)
    print("EVENT-STATE MODEL GENERATOR")
    print("=" * 80)
    
    # Create generator
    output_dir = Path(__file__).parent / 'data'
    generator = EventStateModelGenerator(output_dir=str(output_dir))
    
    # Generate models
    print("\nGenerating 20 event-state models...")
    models_list = generator.generate_model_set(num_models=20)
    
    print(f"\nGenerated {len(models_list)} models")
    
    # Save models
    print("\nSaving models...")
    generator.save_models(models_list)
    
    print("\n" + "=" * 80)
    print("COMPLETE: All models saved")
    print("=" * 80)
    
    # Print summary
    print("\nModel Summary:")
    for name, model, metadata in models_list:
        print(f"  {name}: {metadata['num_nodes']} nodes, {metadata['num_edges']} edges")


if __name__ == '__main__':
    main()
