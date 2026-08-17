#!/bin/bash
# Approach 2: Event-State Model-based DBN
# Quick Start Guide

# ============================================================================
# SETUP
# ============================================================================

# Activate virtual environment
source /home/ubuntu/5GSPP/venv_5gspp/bin/activate

# Navigate to Approach 2 directory
cd /home/ubuntu/5GSPP/2.\ Posture\ Prediction/Approach\ 2-ESMDBN

# ============================================================================
# STEP 1: GENERATE EVENT-STATE MODELS
# ============================================================================

echo "Step 1: Generating event-state models..."
python generate_models.py

# This generates 20 diverse Bayesian Network models:
# - Random structures with different densities
# - Attack path structures (logon, remote, internal, bypass)
# - Mixed variations
#
# Output:
# - data/ folder with 20 model directories
# - data/models_index.json - index of all models
# - Each model contains: model.pkl, metadata.json, edges.json

# ============================================================================
# STEP 2: BUILD DBN AND TEST INFERENCE
# ============================================================================

echo "Step 2: Building DBN and testing inference..."

python3 << 'EOF'
from dbn_approach2 import EventStateDBNModel

# Load first model
model = EventStateDBNModel(model_path='data/attack_logon_1/model.pkl')
print(f"Model has {len(model.events)} events")

# Build DBN with 3 time slices
model.build_dbn()
print(f"DBN built with {len(model.dbn_model.nodes())} nodes")

# Example inference
observations = {'Logon_PB': 1, 'Access_Server': 1}
results = model.perform_inference(observations, model.events[-3:])
print("Inference results:", results)
EOF

# ============================================================================
# STEP 3: RUN EXPERIMENTAL EVALUATION
# ============================================================================

echo "Step 3: Running experimental evaluation..."
python run_experiments.py

# This generates:
# - results/EXPERIMENT_REPORT.md - detailed report
# - results/experimental_results_fig27.png - visualization (similar to Fig. 27)
# - results/*_results.csv - data files for each experiment

# ============================================================================
# STEP 4: RUN INTERACTIVE DEMO
# ============================================================================

echo "Step 4: Running interactive demo..."
python demo.py

# This demonstrates:
# 1. Model generation
# 2. DBN building and inference
# 3. Sequence analysis
# 4. Experimental evaluation

# ============================================================================
# VIEWING RESULTS
# ============================================================================

# View generated models
echo "Generated models:"
ls -la data/*/

# View results
echo "Experimental results:"
ls -la results/

# View detailed report
cat results/EXPERIMENT_REPORT.md

# View result plots (open in image viewer)
# results/experimental_results_fig27.png

# ============================================================================
# PYTHON API USAGE
# ============================================================================

# 1. Generate models programmatically
cat << 'PYEOF'
from generate_models import EventStateModelGenerator

generator = EventStateModelGenerator()
models = generator.generate_model_set(num_models=20)
generator.save_models(models)
PYEOF

# 2. Use DBN for inference
cat << 'PYEOF'
from dbn_approach2 import EventStateDBNModel

# Load model
model = EventStateDBNModel(model_path='data/attack_logon_1/model.pkl')
model.build_dbn()

# Inference
observations = {'Logon_PB': 1, 'Access_Server': 1}
results = model.perform_inference(observations, ['goal_node'])
print(f"Goal probability: {results['goal_node']:.4f}")

# Prediction
initial = {e: 0 for e in model.events}
predictions = model.predict_sequence(initial, num_steps=3)
PYEOF

# 3. Analyze sequences
cat << 'PYEOF'
from dbn_approach2 import SequenceAnalyzer

analyzer = SequenceAnalyzer(model)

sequence = ['Logon_PB', 'Authentication', 'Access_Server', 'Exfiltrating_data']
analysis = analyzer.analyze_sequence(sequence, ['goal_node'])

print(f"Risk: {analysis['risk_level']}")
print(f"Goal prob: {analysis['max_goal_prob']:.4f}")
PYEOF

# 4. Run experiments
cat << 'PYEOF'
from run_experiments import ExperimentRunner

runner = ExperimentRunner()
runner.load_models()
runner.experiment_1_accuracy_vs_data_size()
runner.experiment_2_num_predicted_events()
runner.experiment_3_accuracy_time_comparison()
runner.experiment_4_prediction_time_comparison()
runner.plot_results()
runner.generate_report()
PYEOF

# ============================================================================
# TROUBLESHOOTING
# ============================================================================

# Check if pgmpy is installed
python -c "import pgmpy; print('pgmpy version:', pgmpy.__version__)"

# Check if models were generated
ls -la data/models_index.json

# Run single demo component
python3 -c "from demo import demo_1_generate_models; demo_1_generate_models()"

# Debug model loading
python3 << 'EOF'
from dbn_approach2 import EventStateDBNModel
try:
    model = EventStateDBNModel(model_path='data/attack_logon_1/model.pkl')
    print("Model loaded successfully")
    print(f"Events: {model.events}")
except Exception as e:
    print(f"Error: {e}")
EOF

# ============================================================================
# PARAMETER GUIDE
# ============================================================================

# generate_models.py
# - num_models (20): Number of models to generate
# - density (0.2-0.5): Edge density for random structures
# - num_events (8-16): Number of events per model

# dbn_approach2.py
# - num_time_slices (3): Temporal slices for DBN
# - observations (dict): Event evidence {event: 0/1}
# - query_vars (list): Events to infer

# run_experiments.py
# - data_sizes: [1000, 5000, 10000, 20000]
# - num_steps_list: [1, 2, 3, 4]
# - roc_values: [0.1, 0.3, 0.5, 0.7]

# ============================================================================
# NEXT STEPS
# ============================================================================

echo "✓ Approach 2 Quick Start Complete!"
echo ""
echo "Next steps:"
echo "1. Review generated models: ls -la data/"
echo "2. Check results: cat results/EXPERIMENT_REPORT.md"
echo "3. View visualizations: results/experimental_results_fig27.png"
echo "4. Integrate with your pipeline: import dbn_approach2"
echo ""
echo "For more information, see README.md"
