"""
Training script for Event LSTM Model
Allows configuration of sliding window, prediction steps, and hyperparameters
"""

import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from event_lstm_model import EventLSTMModel
import warnings
warnings.filterwarnings('ignore')


def train_model(data_file, output_dir, config):
    """
    Train LSTM model on event sequence data
    
    Args:
        data_file (str): Path to CSV or TXT data file
        output_dir (str): Directory to save trained model
        config (dict): Configuration parameters
    """
    
    print("=" * 80)
    print("EVENT LSTM MODEL TRAINING")
    print("=" * 80)
    print("\nConfiguration:")
    for key, value in config.items():
        print(f"  {key}: {value}")
    
    # Initialize model
    model = EventLSTMModel(config)
    
    # Load data
    print(f"\nLoading data from {data_file}...")
    data = model.load_data(data_file)
    print(f"Loaded {len(data)} sequences")
    
    if not data:
        print("ERROR: No data loaded!")
        return
    
    # Build vocabulary
    print("\nBuilding vocabulary...")
    model.build_vocabulary(data)
    
    # Create sequences
    print(f"\nCreating sliding window sequences...")
    print(f"  Window size: {model.window_size}")
    print(f"  Prediction steps: {model.prediction_steps}")
    
    X, y, posture_values = model.create_sequences(data)
    print(f"Created {len(X)} training samples")
    print(f"Input shape: {X.shape}, Output shape: {y.shape}")
    
    if len(X) == 0:
        print("ERROR: No sequences created! Check your data format.")
        return
    
    # Build model
    print("\nBuilding LSTM model architecture...")
    vocab_size = len(model.all_events)
    model.build_model(vocab_size)
    
    # Train model
    print("\nTraining model...")
    model.train(X, y)
    
    # Evaluate
    print("\nEvaluating model...")
    metrics = model.evaluate(X, y)
    print(f"  Overall Accuracy: {metrics['overall_accuracy']:.4f}")
    print(f"  Per-step Accuracy: {[f'{acc:.4f}' for acc in metrics['per_step_accuracy']]}")
    print(f"  Test Loss: {metrics['test_loss']:.4f}")
    
    # Save model
    print(f"\nSaving model to {output_dir}...")
    model.save_model(output_dir)
    
    # Save metrics
    metrics_file = Path(output_dir) / 'training_metrics.json'
    with open(metrics_file, 'w') as f:
        json.dump(metrics, f, indent=2)
    
    print("\n" + "=" * 80)
    print("TRAINING COMPLETE")
    print("=" * 80)
    
    return model


def main():
    parser = argparse.ArgumentParser(
        description='Train LSTM model for event sequence prediction'
    )
    
    parser.add_argument(
        '--data-file', '-d',
        required=True,
        help='Path to data file (CSV or TXT)'
    )
    
    parser.add_argument(
        '--output-dir', '-o',
        default='./trained_model',
        help='Directory to save trained model (default: ./trained_model)'
    )
    
    parser.add_argument(
        '--window-size', '-w',
        type=int,
        default=3,
        help='Number of previous events to use (sliding window size, default: 3)'
    )
    
    parser.add_argument(
        '--prediction-steps', '-p',
        type=int,
        default=1,
        help='Number of future events to predict (default: 1)'
    )
    
    parser.add_argument(
        '--lstm-units',
        type=int,
        default=64,
        help='Number of LSTM units (default: 64)'
    )
    
    parser.add_argument(
        '--dropout-rate',
        type=float,
        default=0.2,
        help='Dropout rate (default: 0.2)'
    )
    
    parser.add_argument(
        '--epochs',
        type=int,
        default=50,
        help='Number of training epochs (default: 50)'
    )
    
    parser.add_argument(
        '--batch-size',
        type=int,
        default=32,
        help='Batch size (default: 32)'
    )
    
    parser.add_argument(
        '--validation-split',
        type=float,
        default=0.2,
        help='Validation split ratio (default: 0.2)'
    )
    
    parser.add_argument(
        '--config-file', '-c',
        help='JSON config file with all parameters (overrides command line args)'
    )
    
    args = parser.parse_args()
    
    # Build configuration
    if args.config_file:
        print(f"Loading config from {args.config_file}...")
        with open(args.config_file, 'r') as f:
            config = json.load(f)
    else:
        config = {
            'window_size': args.window_size,
            'prediction_steps': args.prediction_steps,
            'lstm_units': args.lstm_units,
            'dropout_rate': args.dropout_rate,
            'epochs': args.epochs,
            'batch_size': args.batch_size,
            'validation_split': args.validation_split,
        }
    
    # Train model
    train_model(args.data_file, args.output_dir, config)


if __name__ == '__main__':
    main()
