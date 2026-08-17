#!/bin/bash
# Quick Reference Commands for Event LSTM Model

# ============================================================================
# SETUP
# ============================================================================

# Activate the virtual environment
source /home/ubuntu/5GSPP/venv_5gspp/bin/activate

# Navigate to project directory
cd /home/ubuntu/5GSPP/2.\ Posture\ Prediction/Approach\ 3-EventsLSTM

# ============================================================================
# BASIC USAGE
# ============================================================================

# 1. Train a basic model (fastest - 1 minute)
python train_lstm.py --data-file data/sequences_atck_goal.txt --epochs 10

# 2. Train with custom window size and prediction steps
python train_lstm.py \
    --data-file data/sequences_atck_goal.txt \
    --window-size 5 \
    --prediction-steps 2 \
    --epochs 30

# 3. Train from config file
python train_lstm.py \
    --data-file data/sequences_atck_goal.txt \
    --config-file config_light.json \
    --output-dir ./my_light_model

# ============================================================================
# EXPERIMENTS (Figure 26 style analysis)
# ============================================================================

# Run E1: Window size effect (2, 3, 5, 10)
python run_experiments.py \
    --data-file data/sequences_atck_goal.txt \
    --experiments e1 \
    --output-dir ./results

# Run E2: Prediction steps effect (1, 2, 3, 4)
python run_experiments.py \
    --data-file data/sequences_atck_goal.txt \
    --experiments e2 \
    --output-dir ./results

# Run all 5 experiments (E1-E5)
python run_experiments.py \
    --data-file data/sequences_atck_goal.txt \
    --output-dir ./results

# Generate results without plots
python run_experiments.py \
    --data-file data/sequences_atck_goal.txt \
    --experiments e1 e2 e3 \
    --no-plot

# ============================================================================
# DEMO & TESTING
# ============================================================================

# Run interactive demo (shows training, prediction, model loading)
python demo.py

# ============================================================================
# QUICK PREDICTIONS IN PYTHON
# ============================================================================

# Start Python interactive shell
python

# --- Inside Python ---
from event_lstm_model import EventLSTMModel

# Load trained model
model = EventLSTMModel()
model.load_model('./test_model')

# Predict next event
seq = ['Logon_PB', 'Access_Server', 'Token_Impersonation']
next_events = model.predict_events(seq)
print(f"Predicted: {next_events}")

# Predict with confidence scores
predictions = model.predict_with_confidence(seq)
for event, conf in predictions:
    print(f"{event}: {conf:.4f}")

# Exit Python
exit()

# ============================================================================
# DATA FILES AVAILABLE
# ============================================================================

# List available data files
ls -la data/

# Available datasets:
# - sequences_atck_goal.txt (short sequences with goal node)
# - sequences_atck_pattern.txt (pattern-based attack sequences)
# - data_for_exp_16_Feb.csv (with posture values)
# - data_for_exp_TokenImp_22Feb.csv
# - data_for_exp_ExfData_23Feb.csv
# - ... and more

# ============================================================================
# VIEW RESULTS
# ============================================================================

# View experiment report
cat results/EXPERIMENT_REPORT.md

# View training metrics from specific run
cat ./test_model/training_metrics.json

# View model metadata
cat ./test_model/metadata.json

# View result plots
# Look in ./results/ for PNG images:
# - e1_window_size_results.png
# - e2_prediction_steps_results.png
# - e3_combined_conditions_results.png
# - e4_lstm_units_results.png
# - e5_dropout_results.png

# ============================================================================
# CONFIGURATION TEMPLATES
# ============================================================================

# Light config (fastest, smallest)
# - window_size: 2
# - prediction_steps: 1
# - lstm_units: 32
# - epochs: 20
# Usage: --config-file config_light.json

# Example config (balanced)
# - window_size: 3
# - prediction_steps: 1
# - lstm_units: 64
# - epochs: 50
# Usage: --config-file config_example.json

# Heavy config (best accuracy, slowest)
# - window_size: 5
# - prediction_steps: 3
# - lstm_units: 128
# - epochs: 100
# Usage: --config-file config_heavy.json

# ============================================================================
# PARAMETER GUIDE
# ============================================================================

# --window-size (or -w)
#   Default: 3
#   Range: 2-10
#   Meaning: How many previous events to consider
#   Effect: Larger = more context, slower training

# --prediction-steps (or -p)
#   Default: 1
#   Range: 1-4
#   Meaning: How many future events to predict
#   Effect: More steps = harder to predict, lower accuracy

# --lstm-units
#   Default: 64
#   Range: 32-256
#   Meaning: Number of neurons in LSTM layers
#   Effect: More units = more capacity, slower training

# --dropout-rate
#   Default: 0.2
#   Range: 0.0-0.7
#   Meaning: Regularization during training
#   Effect: Higher = more regularization, may reduce overfitting

# --epochs
#   Default: 50
#   Range: 10-200+
#   Meaning: Number of training iterations
#   Effect: More = better but slower

# --batch-size
#   Default: 32
#   Range: 16-128
#   Meaning: Samples per training step
#   Effect: Larger = faster but less stable

# ============================================================================
# TROUBLESHOOTING
# ============================================================================

# If virtual env not found:
source /home/ubuntu/5GSPP/venv_5gspp/bin/activate

# If packages not found:
cd /home/ubuntu/5GSPP/2.\ Posture\ Prediction/Approach\ 3-EventsLSTM
pip install -r requirements.txt

# If model file not found:
python train_lstm.py --data-file data/sequences_atck_goal.txt --output-dir ./my_model

# If data not loading:
# Check: ls data/ (data files exist)
# Check: head data/sequences_atck_goal.txt (format is correct)

# ============================================================================
# SAVING YOUR WORK
# ============================================================================

# Trained models are saved in: ./trained_model/
# Experimental results saved in: ./results/
# These persist between sessions

# To backup your model:
cp -r ./trained_model ./trained_model_backup_DATE

# ============================================================================
# NEXT STEPS
# ============================================================================

# 1. Read README.md for complete documentation
# 2. Run demo.py to see all features
# 3. Try different window sizes with E1 experiment
# 4. Try different prediction steps with E2 experiment
# 5. Integrate with your log parser pipeline
# 6. Tune hyperparameters based on E4-E5 experiments

echo "✓ Event LSTM Model Ready!"
echo "Start with: python demo.py"
