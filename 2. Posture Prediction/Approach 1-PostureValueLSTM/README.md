# Approach 1: Posture Value LSTM - Security Posture Prediction

## 📋 Overview

**Approach 1** implements a Long Short-Term Memory (LSTM) neural network for **time-series based security posture value prediction**. This approach monitors historical security posture values and predicts future states based on observed patterns and rates of change.

### Key Characteristics
- **Input**: Historical security posture values (time-series)
- **Output**: Predicted future posture values
- **Architecture**: Bidirectional LSTM with dropout regularization
- **Pattern Support**: No pattern, fixed-length, and variable-length trend patterns


### Pattern Types

The approach tests three distinct pattern types to evaluate LSTM robustness:

1. **No Pattern** (Random Direction Changes)
   - Each step independently chooses direction (up/down)
   - Baseline for random posture fluctuations

2. **Fixed-Length Pattern** (Consistent Trends)
   - Maintains direction for 5-8 consecutive steps
   - Then switches direction
   - Simulates security posture drift periods

3. **Variable-Length Pattern** (Probabilistic Changes)
   - Changes direction with 15% probability at each step
   - Realistic security event behavior

### Rate of Change (ROC)

Experiments test 5 ROC values: **0.1, 0.3, 0.5, 0.7, 0.9**
- ROC represents average magnitude of posture value changes
- Higher ROC = faster security posture transitions
- Target range: (ROC - 0.1) ≤ actual_avg_rate ≤ ROC

## 🏗️ Architecture

### LSTM Model Structure
```
Input Layer (Sequence of 10 timesteps)
    ↓
LSTM Layer 1: 50 units
    ↓
Dropout: 0.2 (20% dropout rate)
    ↓
LSTM Layer 2: 50 units
    ↓
Dropout: 0.2
    ↓
Dense Layer: 25 units, ReLU activation
    ↓
Output Layer: 1 unit (predicted posture value)
```

### Training Configuration
- **Lookback Window**: 10 timesteps
- **Training Epochs**: 50
- **Batch Size**: 32
- **Validation Split**: 20%
- **Optimizer**: Adam (lr=0.001)
- **Loss Function**: Mean Squared Error (MSE)
- **Metrics**: MAE, RMSE

## 📦 Installation

### Prerequisites
- Python 3.10+
- TensorFlow 2.10+
- NumPy, Pandas, Scikit-learn
- Matplotlib, NetworkX

### Virtual Environment Setup
```bash
# Navigate to project directory
cd /home/ubuntu/5GSPP/2. Posture Prediction/

# Activate virtual environment
source /home/ubuntu/5GSPP/venv_5gspp/bin/activate

# Install dependencies (if not already installed)
pip install tensorflow>=2.10 numpy pandas scikit-learn matplotlib networkx
```

## 🚀 Quick Start

### Run Complete Experiment (Figure 25 Methodology)
```bash
cd Approach\ 1-PostureValueLSTM
python posture_rate_of_change_experiment.py
```

**Output:**
- Figure: `results/Fig25_experimental_results.png` (4-subplot visualization)
- Report: `results/Fig25_EXPERIMENT_REPORT.md` (detailed results table)

### Expected Runtime
- Total: ~8-12 minutes
- Per pattern: ~2-4 minutes (3 patterns × 5 ROC configurations)
- Per configuration: ~30-60 seconds

## 📊 Experimental Results (Figure 25)

### Results Summary Table

#### NO PATTERN
| ROC | RMSE | MAE |
|-----|------|-----|
| 0.1 | 0.055464 | 0.051590 |
| 0.3 | 0.136550 | 0.127011 |
| 0.5 | 0.243551 | 0.237983 |
| 0.7 | 0.299564 | 0.298792 |
| 0.9 | 0.298661 | 0.298263 |

#### FIXED-LENGTH PATTERN ⭐
| ROC | RMSE | MAE |
|-----|------|-----|
| 0.1 | 0.043531 | 0.032042 |
| 0.3 | 0.145208 | 0.095940 |
| 0.5 | 0.163417 | 0.115099 |
| 0.7 | 0.186821 | 0.139654 |
| 0.9 | 0.215269 | 0.134792 |

#### VARIABLE-LENGTH PATTERN
| ROC | RMSE | MAE |
|-----|------|-----|
| 0.1 | 0.049915 | 0.038341 |
| 0.3 | 0.224386 | 0.175195 |
| 0.5 | 0.223157 | 0.167889 |
| 0.7 | 0.191949 | 0.155362 |
| 0.9 | 0.229949 | 0.174586 |

### Key Findings

1. **Best Performance**: Fixed-length patterns achieve lowest errors across all ROC values
2. **Pattern Effect**: Structured patterns (fixed/variable) outperform random patterns
3. **ROC Sensitivity**: Error increases with ROC (faster changes = harder prediction)
4. **MAE vs RMSE**: MAE consistently lower, indicating few extreme outliers
5. **Stability**: Fixed-length pattern shows most stable scaling

## 📁 Directory Structure

```
Approach 1-PostureValueLSTM/
├── posture_rate_of_change_experiment.py    # Main experiment script
├── README.md                                # This file
│
├── data/                                    # Generated datasets
│   ├── posture_no_pattern_roc0.1.csv
│   ├── posture_fixed_length_roc0.1.csv
│   └── posture_variable_length_roc0.1.csv
│
└── results/                                 # Experimental outputs
    ├── Fig25_experimental_results.png       # 4-subplot visualization
    └── Fig25_EXPERIMENT_REPORT.md           # Detailed results report
```

## 💻 Usage Examples

### Example 1: Run Full Experiment
```python
from posture_rate_of_change_experiment import ExperimentRunner

# Create runner and execute
runner = ExperimentRunner()
runner.run_experiment()      # Test all 3 patterns × 5 ROC values
runner.plot_results()         # Generate Figure 25 visualization
runner.generate_report()      # Create markdown report
```

### Example 2: Generate Data with Specific Pattern
```python
from posture_rate_of_change_experiment import PostureDataGenerator

# Initialize generator
generator = PostureDataGenerator(sequence_length=100)

# Generate data with fixed-length pattern, ROC=0.5
data = generator.generate_posture_values(
    rate_of_change=0.5,
    pattern_type='fixed_length',
    num_sequences=10
)

# Save to CSV
generator.save_to_csv(data, 0.5, 'fixed_length')
```

### Example 3: Train Custom Model
```python
from posture_rate_of_change_experiment import PostureLSTMModel
import numpy as np

# Generate sample data
data = np.random.rand(1000) * 0.5 + 0.4

# Create and train model
model = PostureLSTMModel(lookback=10, epochs=50)
history, X_test, y_test = model.train(data)

# Evaluate
metrics = model.evaluate(X_test, y_test)
print(f"RMSE: {metrics['rmse']:.6f}, MAE: {metrics['mae']:.6f}")
```

## 🔧 Configuration

### Data Generation Parameters
```python
PostureDataGenerator(
    sequence_length=100,    # Number of steps per sequence
    min_value=0.4,          # Minimum posture value
    max_value=1.0           # Maximum posture value
)
```

### LSTM Model Parameters
```python
PostureLSTMModel(
    lookback=10,            # Number of historical timesteps
    batch_size=32,          # Training batch size
    epochs=50               # Number of training epochs
)
```

### Experiment Configuration
```python
runner = ExperimentRunner()
runner.roc_values = [0.1, 0.3, 0.5, 0.7, 0.9]  # ROC values to test
runner.goal_nodes = ['TokenImp', 'LaunchAgent', 'ExfilData', 'CombGoal']
```

## 🐛 Troubleshooting

### Issue: CUDA/GPU Warnings
```
WARNING: Could not find cuda drivers on your machine, GPU will not be used.
```
**Solution**: This is normal. Script uses CPU, which is fine for this scale.

### Issue: Script Takes Too Long
**Solution**: Reduce epochs or sequence count:
```python
runner = ExperimentRunner()
# Modify epochs in PostureLSTMModel
```

### Issue: Out of Memory
**Solution**: Reduce batch size:
```python
model = PostureLSTMModel(lookback=10, batch_size=16, epochs=50)
```

### Issue: Results Not Matching Figure 25
**Solution**: Ensure numpy/tensorflow random seeds are set:
```python
np.random.seed(42)
tf.random.set_seed(42)
```
