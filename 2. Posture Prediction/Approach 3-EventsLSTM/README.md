# Event-based LSTM Model for Event Prediction

This is Approach 3 of the Posture Prediction system, which uses LSTM (Long Short-Term Memory) neural networks to predict future security events based on historical event sequences.

## Overview

The model implements a sliding window-based LSTM architecture that:
- **Trains** on historical event sequences (from CSV or TXT files)
- **Predicts** future events with configurable sliding window and prediction steps


### Key Features

- Flexible sliding window configuration (how many previous events to use)
- Multi-step prediction (predict multiple future events)
- Support for CSV and TXT data formats

## Architecture

```
Historical Event Sequences → [Sliding Window] → LSTM Model → Predicted Events
                                    ↓
                            (window_size events)
                                    ↓
                     [Embedding] → [LSTM] → [Dense] → Predictions
```

## File Structure

```
Approach 3-EventsLSTM/
├── data/                          # Data folder 
│   ├── sequences_atck_goal.txt
│   ├── data_for_exp_16_Feb.csv
│   └── ... (other data files)
├── event_lstm_model.py           # Core LSTM model class
├── train_lstm.py                 # Training 
└── README.md                      # This file
```

## Data Format

### CSV Format (Recommended)
```
date_time,sequence,posturevalue
2018-01-01 00:00:00,"['Input_Credentials', 'Authentication', 'Access_Server']",0.29
2018-01-01 01:00:00,"['Logon_PB', 'Bypass_Authentication', 'Access_Server']",0.83
```

### TXT Format
```
Logon_PB,Access_Server,Token_Impersonation,goal_node
Authentication,Access_Server,Portable_Execution,Agent_based_MPB,Launch_Agent
Logon_PB,Access_Server,Launch_Agent,goal_node
```

## Usage

### 1. Basic Training

Train a model with default configuration:

```bash
python train_lstm.py --data-file data/sequences_atck_goal.txt
```

### 2. Training with Custom Parameters

Train with configurable sliding window and prediction steps:

```bash
python train_lstm.py \
    --data-file data/data_for_exp_16_Feb.csv \
    --window-size 5 \
    --prediction-steps 3 \
    --lstm-units 128 \
    --epochs 100 \
    --output-dir ./my_model
```

**Parameters:**
- `--window-size` (int): Number of previous events to use for prediction (default: 3)
- `--prediction-steps` (int): Number of future events to predict (default: 1)
- `--lstm-units` (int): Number of LSTM units (default: 64)
- `--dropout-rate` (float): Dropout rate (default: 0.2)
- `--epochs` (int): Number of training epochs (default: 50)
- `--batch-size` (int): Batch size (default: 32)
- `--validation-split` (float): Validation split ratio (default: 0.2)

### 3. Training with Config File

Create a JSON config file:

```json
{
  "window_size": 3,
  "prediction_steps": 2,
  "lstm_units": 64,
  "dropout_rate": 0.2,
  "epochs": 50,
  "batch_size": 32,
  "validation_split": 0.2
}
```

Then train:

```bash
python train_lstm.py \
    --data-file data/sequences_atck_goal.txt \
    --config-file config.json
```

### 4. Run Comprehensive Experiments

Run all experiments 

```bash
python run_experiments.py \
    --data-file data/sequences_atck_goal.txt \
    --output-dir ./results
```


Run specific experiments:

```bash
python run_experiments.py \
    --data-file data/sequences_atck_goal.txt \
    --experiments e1 e2 e3
```

### 5. Using Trained Model for Prediction

```python
from event_lstm_model import EventLSTMModel

# Load trained model
model = EventLSTMModel()
model.load_model('./trained_model')

# Predict next events
history = ['Logon_PB', 'Access_Server', 'Token_Impersonation']
predictions = model.predict_events(history)
print(f"Next predicted events: {predictions}")

# Get predictions with confidence scores
predictions_with_conf = model.predict_with_confidence(history)
for event, confidence in predictions_with_conf:
    print(f"{event}: {confidence:.4f}")
```


## Output

### After Training

```
trained_model/
├── lstm_model.h5           # Trained Keras model
├── metadata.json           # Model metadata and vocabulary
└── training_metrics.json   # Training metrics
```

## Python API Reference

### EventLSTMModel Class

```python
from event_lstm_model import EventLSTMModel

# Initialize
config = {
    'window_size': 3,
    'prediction_steps': 2,
    'lstm_units': 64,
    'epochs': 50,
    'batch_size': 32
}
model = EventLSTMModel(config)

# Load data
data = model.load_data('data.csv')  # or .txt

# Build vocabulary
model.build_vocabulary(data)

# Create sequences for training
X, y, posture_values = model.create_sequences(data)

# Build and train
model.build_model(len(model.all_events))
model.train(X, y)

# Evaluate
metrics = model.evaluate(X, y)

# Predict
events_to_predict = ['Event1', 'Event2', 'Event3']
next_events = model.predict_events(events_to_predict)

# Save/Load
model.save_model('./my_model')
model.load_model('./my_model')
```

## Key Parameters Explained

### Window Size
- **Definition**: Number of previous events used to predict the next event(s)
- **Effect**: Larger windows capture more context but may be slower
- **Typical range**: 2-10
- **Trade-off**: 
  - Small (2-3): Fast, less contextual
  - Large (5-10): More contextual, slower

### Prediction Steps
- **Definition**: Number of future events to predict at once
- **Effect**: More steps = harder to predict
- **Typical range**: 1-4
- **Trade-off**:
  - 1 step: Easier, lower accuracy
  - 3+ steps: Harder, much lower accuracy

### LSTM Units
- **Definition**: Number of neurons in LSTM layers
- **Effect**: More units = more capacity
- **Typical range**: 32-256
- **Trade-off**:
  - Small (32): Fast, may underfit
  - Large (128+): Slower, better fit

## Dependencies

Install required packages:

```bash
pip install tensorflow numpy pandas scikit-learn matplotlib
```

Or use requirements.txt:

```bash
pip install -r requirements.txt
```

## Example Workflow

```bash
# Train a model
python train_lstm.py \
    --data-file data/sequences_atck_goal.txt \
    --window-size 3 \
    --prediction-steps 2 \
    --output-dir ./trained_model

## Common Issues

### No sequences created
- **Cause**: Data format not recognized
- **Solution**: Check if sequence format is correct (list or comma-separated)

### Model doesn't train
- **Cause**: Vocabulary size too small
- **Solution**: Ensure you have enough unique events (minimum 10-20)

### Low accuracy
- **Cause**: Window size too small or data too variable
- **Solution**: Increase window size or data preprocessing

