"""
Approach 2 Demo - Event-State Model-based DBN
Complete workflow demonstration
"""

import os
import sys
from pathlib import Path
import json
import pickle

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from generate_models import EventStateModelGenerator
from dbn_approach2 import EventStateDBNModel, SequenceAnalyzer
from run_experiments import ExperimentRunner


def demo_1_generate_models():
    """Demo 1: Generate event-state models"""
    
    print("\n" + "="*80)
    print("DEMO 1: GENERATE EVENT-STATE MODELS")
    print("="*80)
    
    output_dir = Path(__file__).parent / 'data'
    generator = EventStateModelGenerator(output_dir=str(output_dir))
    
    print("\nGenerating 20 diverse event-state models...")
    models_list = generator.generate_model_set(num_models=20)
    
    print(f"\nGenerated {len(models_list)} models:")
    for name, model, metadata in models_list[:5]:
        print(f"  {name}: {metadata['num_nodes']} nodes, {metadata['num_edges']} edges")
    print(f"  ... and {len(models_list) - 5} more")
    
    print("\nSaving models...")
    generator.save_models(models_list)
    
    print(f"\nModels saved to: {output_dir}")
    return output_dir


def demo_2_build_dbn():
    """Demo 2: Build and use DBN for inference"""
    
    print("\n" + "="*80)
    print("DEMO 2: BUILD AND USE DBN FOR INFERENCE")
    print("="*80)
    
    # Find first model
    data_dir = Path(__file__).parent / 'data'
    models_dir = list(data_dir.glob('**/model.pkl'))
    
    if not models_dir:
        print("No models found. Please run demo_1 first.")
        return
    
    model_path = models_dir[0]
    print(f"\nLoading model: {model_path}")
    
    # Load model
    dbn = EventStateDBNModel(model_path=str(model_path), num_time_slices=3)
    
    print(f"Loaded model with events: {dbn.events[:5]}...")
    
    # Build DBN
    print("\nBuilding Dynamic Bayesian Network...")
    dbn.build_dbn()
    
    # Example inference
    print("\nPerforming inference...")
    observations = {
        'Logon_PB': 1,
        'Access_Server': 1,
        'Token_Impersonation': 0
    }
    
    query_vars = ['goal_node'] if 'goal_node' in dbn.events else dbn.events[-3:]
    
    results = dbn.perform_inference(observations, query_vars)
    
    print(f"\nInference Results:")
    print(f"  Observations: {observations}")
    print(f"  Query Variables: {query_vars}")
    print(f"  Results:")
    for var, prob in results.items():
        print(f"    {var}: {prob:.4f}")
    
    # Sequence prediction
    print("\nPredicting future events...")
    initial_state = {e: 0 for e in dbn.events}
    initial_state['Input_Credentials'] = 1
    
    predictions = dbn.predict_sequence(initial_state, num_steps=3)
    
    print(f"Initial state: {sum(initial_state.values())} events active")
    for i, pred in enumerate(predictions[1:], 1):
        print(f"Step {i}: {sum(pred.values())} events predicted active")


def demo_3_analyze_sequences():
    """Demo 3: Analyze sequences using DBN"""
    
    print("\n" + "="*80)
    print("DEMO 3: ANALYZE SECURITY SEQUENCES")
    print("="*80)
    
    # Find first model
    data_dir = Path(__file__).parent / 'data'
    models_dir = list(data_dir.glob('**/model.pkl'))
    
    if not models_dir:
        print("No models found. Please run demo_1 first.")
        return
    
    model_path = models_dir[0]
    dbn = EventStateDBNModel(model_path=str(model_path))
    dbn.build_dbn()
    
    analyzer = SequenceAnalyzer(dbn)
    
    # Example attack sequences
    attack_sequences = [
        ['Logon_PB', 'Authentication', 'Access_Server', 'Token_Impersonation', 'Exfiltrating_data'],
        ['Input_Credentials', 'Authentication', 'Access_Server'],
        ['Remote_access_PB', 'Access_Server', 'Agent_based_MPB', 'Launch_Agent']
    ]
    
    goal_events = ['Exfiltrating_data', 'goal_node']
    goal_events = [e for e in goal_events if e in dbn.events]
    
    print("\nAnalyzing attack sequences...\n")
    
    for i, seq in enumerate(attack_sequences, 1):
        # Filter to valid events
        valid_seq = [e for e in seq if e in dbn.events]
        
        analysis = analyzer.analyze_sequence(valid_seq, goal_events)
        
        print(f"Sequence {i}: {valid_seq}")
        print(f"  Goal Probabilities: {analysis['goal_probabilities']}")
        print(f"  Max Goal Probability: {analysis['max_goal_prob']:.4f}")
        print(f"  Risk Level: {analysis['risk_level']}")
        print()


def demo_4_run_experiments():
    """Demo 4: Run experimental evaluation"""
    
    print("\n" + "="*80)
    print("DEMO 4: RUN EXPERIMENTAL EVALUATION")
    print("="*80)
    
    output_dir = Path(__file__).parent / 'results'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    runner = ExperimentRunner(
        models_dir=str(Path(__file__).parent / 'data'),
        output_dir=str(output_dir)
    )
    
    print("\nLoading models...")
    runner.load_models()
    
    print("\nRunning experiments...")
    
    # Run each experiment
    print("\n1. Accuracy vs Data Size...")
    runner.experiment_1_accuracy_vs_data_size()
    
    print("\n2. Number of Predicted Events...")
    runner.experiment_2_num_predicted_events()
    
    print("\n3. Accuracy vs Time Comparison...")
    runner.experiment_3_accuracy_time_comparison()
    
    print("\n4. Prediction Time Comparison...")
    runner.experiment_4_prediction_time_comparison()
    
    print("\nGenerating visualizations and reports...")
    runner.plot_results()
    runner.generate_report()
    runner.save_results_csv()
    
    print(f"\nResults saved to: {output_dir}")


def main():
    """Run all demos"""
    
    print("\n" + "="*80)
    print("APPROACH 2: EVENT-STATE MODEL-BASED DBN")
    print("Complete Workflow Demonstration")
    print("="*80)
    
    try:
        # Demo 1: Generate models
        print("\n>>> Running Demo 1: Generate Models")
        demo_1_generate_models()
        
        # Demo 2: Build DBN and perform inference
        print("\n>>> Running Demo 2: Build DBN")
        demo_2_build_dbn()
        
        # Demo 3: Analyze sequences
        print("\n>>> Running Demo 3: Analyze Sequences")
        demo_3_analyze_sequences()
        
        # Demo 4: Run experiments
        print("\n>>> Running Demo 4: Experiments")
        demo_4_run_experiments()
        
        print("\n" + "="*80)
        print("ALL DEMOS COMPLETE")
        print("="*80)
        
    except Exception as e:
        print(f"\nError during demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
