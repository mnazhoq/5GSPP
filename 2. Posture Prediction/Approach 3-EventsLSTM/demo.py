"""
Quick Start Demo Script
Shows how to train and use the Event LSTM Model
"""

import sys
from pathlib import Path
from event_lstm_model import EventLSTMModel
import json

def demo_basic_training():
    """Demo 1: Basic model training"""
    print("\n" + "="*80)
    print("DEMO 1: Basic Model Training")
    print("="*80)
    
    # Configuration
    config = {
        'window_size': 3,
        'prediction_steps': 1,
        'lstm_units': 64,
        'epochs': 20,
        'batch_size': 32
    }
    
    # Initialize model
    print("\n1. Initializing model with configuration...")
    print(json.dumps(config, indent=2))
    model = EventLSTMModel(config)
    
    # Load data
    print("\n2. Loading data from sequences_atck_goal.txt...")
    data_file = Path(__file__).parent / 'data' / 'sequences_atck_goal.txt'
    
    if not data_file.exists():
        print(f"ERROR: Data file not found: {data_file}")
        return
    
    data = model.load_data(str(data_file))
    print(f"   Loaded {len(data)} event sequences")
    
    # Build vocabulary
    print("\n3. Building vocabulary...")
    model.build_vocabulary(data)
    
    # Create sequences
    print("\n4. Creating training sequences...")
    X, y, posture_values = model.create_sequences(data)
    print(f"   Created {len(X)} training samples")
    print(f"   Input shape: {X.shape}, Output shape: {y.shape}")
    
    # Build model
    print("\n5. Building LSTM model...")
    model.build_model(len(model.all_events))
    
    # Train model
    print("\n6. Training model (this may take a while)...")
    model.train(X, y)
    
    # Evaluate
    print("\n7. Evaluating model...")
    metrics = model.evaluate(X, y)
    print(f"   Accuracy: {metrics['overall_accuracy']:.4f}")
    print(f"   Loss: {metrics['test_loss']:.4f}")
    
    # Save model
    output_dir = Path(__file__).parent / 'demo_model'
    print(f"\n8. Saving model to {output_dir}...")
    model.save_model(str(output_dir))
    
    return model


def demo_prediction(model):
    """Demo 2: Make predictions"""
    print("\n" + "="*80)
    print("DEMO 2: Making Predictions")
    print("="*80)
    
    # Example sequences
    test_sequences = [
        ['Logon_PB', 'Access_Server', 'Token_Impersonation'],
        ['Authentication', 'Access_Server'],
        ['Logon_PB', 'Access_Server'],
    ]
    
    print("\nPredicting next events based on historical sequences:\n")
    
    for i, seq in enumerate(test_sequences, 1):
        print(f"Example {i}:")
        print(f"  Input sequence: {seq}")
        
        # Predict events
        next_events = model.predict_events(seq)
        print(f"  Predicted events: {next_events}")
        
        # Predict with confidence
        predictions_with_conf = model.predict_with_confidence(seq)
        print(f"  With confidence:")
        for event, conf in predictions_with_conf:
            print(f"    - {event}: {conf:.4f}")
        print()


def demo_load_model():
    """Demo 3: Load pre-trained model"""
    print("\n" + "="*80)
    print("DEMO 3: Loading Pre-trained Model")
    print("="*80)
    
    model_dir = Path(__file__).parent / 'demo_model'
    
    if not model_dir.exists():
        print(f"ERROR: Model directory not found: {model_dir}")
        print("Please run demo_basic_training() first to create the model.")
        return None
    
    print(f"\nLoading model from {model_dir}...")
    model = EventLSTMModel()
    model.load_model(str(model_dir))
    
    print("Model loaded successfully!")
    print(f"  Window size: {model.window_size}")
    print(f"  Prediction steps: {model.prediction_steps}")
    print(f"  Vocabulary size: {len(model.all_events)}")
    print(f"  Events: {model.all_events[:10]}...")
    
    return model


def demo_custom_config():
    """Demo 4: Training with custom configuration"""
    print("\n" + "="*80)
    print("DEMO 4: Training with Custom Configuration")
    print("="*80)
    
    # Different configurations to try
    configs = [
        {
            'name': 'Small Window',
            'window_size': 2,
            'prediction_steps': 1,
            'lstm_units': 32,
            'epochs': 15
        },
        {
            'name': 'Large Predictions',
            'window_size': 5,
            'prediction_steps': 3,
            'lstm_units': 128,
            'epochs': 20
        },
    ]
    
    data_file = Path(__file__).parent / 'data' / 'sequences_atck_goal.txt'
    
    if not data_file.exists():
        print(f"ERROR: Data file not found: {data_file}")
        return
    
    for cfg in configs:
        print(f"\n--- Training: {cfg['name']} ---")
        config = {k: v for k, v in cfg.items() if k != 'name'}
        
        model = EventLSTMModel(config)
        data = model.load_data(str(data_file))
        model.build_vocabulary(data)
        X, y, _ = model.create_sequences(data)
        
        print(f"Samples: {len(X)}")
        
        if len(X) > 0:
            model.build_model(len(model.all_events))
            model.train(X, y)
            metrics = model.evaluate(X, y)
            print(f"Accuracy: {metrics['overall_accuracy']:.4f}")


def main():
    """Run all demos"""
    
    print("\n" + "="*80)
    print("EVENT LSTM MODEL - QUICK START DEMO")
    print("="*80)
    
    # Check if data exists
    data_file = Path(__file__).parent / 'data' / 'sequences_atck_goal.txt'
    if not data_file.exists():
        print(f"ERROR: Data file not found at {data_file}")
        print("Please ensure the data folder contains the necessary data files.")
        return
    
    # Run demos
    try:
        print("\nRunning Demo 1: Basic Training...")
        model = demo_basic_training()
        
        if model:
            print("\nRunning Demo 2: Making Predictions...")
            demo_prediction(model)
        
        print("\nRunning Demo 3: Loading Model...")
        loaded_model = demo_load_model()
        
        if loaded_model:
            print("\nMaking predictions with loaded model...")
            demo_prediction(loaded_model)
        
        print("\nRunning Demo 4: Custom Configurations...")
        demo_custom_config()
        
        print("\n" + "="*80)
        print("DEMO COMPLETE")
        print("="*80)
        print("\nNext steps:")
        print("1. Try different window sizes with: python train_lstm.py --window-size N")
        print("2. Run experiments with: python run_experiments.py --data-file data/sequences_atck_goal.txt")
        print("3. Use pre-trained model in your Python code with EventLSTMModel")
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
