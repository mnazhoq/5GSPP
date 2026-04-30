# INTEGRATION GUIDE: Connecting Log Correlation → NLP → Posture Evaluation

**Status**: Essential for paper reproducibility

**Last Updated**: April 3, 2026

---

## OVERVIEW

This guide explains how to integrate the 4 major components of 5GSPP into a unified, end-to-end pipeline that addresses all three reviewer issues.

```
┌─────────────────────────────────────────────────────────────┐
│                    5GSPP END-TO-END PIPELINE                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ISSUE 1: LOG PARSER                                       │
│  ┌──────────────────────────────────────────┐              │
│  │ Raw Logs (5GC, K8s, Syslog, NetFlow)     │              │
│  │         ↓                                 │              │
│  │ CEF Normalization (Algorithm 2)          │              │
│  │         ↓                                 │              │
│  │ Apply Rules R1-R7                        │              │
│  │         ↓                                 │              │
│  │ Correlated Incidents                     │              │
│  └──────────────────────────────────────────┘              │
│              ↓↓↓ BRIDGE 1 ↓↓↓                              │
│         incident_to_breach_narrative()                     │
│                    ↓                                        │
│  ISSUE 3: NLP PIPELINE                                     │
│  ┌──────────────────────────────────────────┐              │
│  │ Breach Narrative (text)                  │              │
│  │         ↓                                 │              │
│  │ YAKE Keyword Extraction                  │              │
│  │         ↓                                 │              │
│  │ SBERT TTP Mapping                        │              │
│  │         ↓                                 │              │
│  │ spaCy Causal Extraction                  │              │
│  │         ↓                                 │              │
│  │ PageRank Ranking                         │              │
│  │         ↓                                 │              │
│  │ Extracted Conditions (MITRE TTPs +       │              │
│  │                      confidence scores)   │              │
│  └──────────────────────────────────────────┘              │
│              ↓↓↓ BRIDGE 2 ↓↓↓                              │
│         normalize_nlp_output()                             │
│         continuous_to_discrete_evidence()                 │
│                    ↓                                        │
│  POSTURE EVALUATION                                        │
│  ┌──────────────────────────────────────────┐              │
│  │ Discrete Evidence (from Bridge 2)        │              │
│  │         ↓                                 │              │
│  │ Bayesian Network Inference                │              │
│  │         ↓                                 │              │
│  │ Posture Value [0...1]                    │              │
│  │  (0=compromised, 1=secure)               │              │
│  └──────────────────────────────────────────┘              │
│                    ↓                                        │
│  POSTURE PREDICTION                                        │
│  ┌──────────────────────────────────────────┐              │
│  │ Historical Posture Values (time series)  │              │
│  │         ↓                                 │              │
│  │ LSTM / DBN Predictor                     │              │
│  │         ↓                                 │              │
│  │ Predicted Future Posture                 │              │
│  └──────────────────────────────────────────┘              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## STEP-BY-STEP INTEGRATION

### Step 1: Generate Correlated Incidents (Issue 1)

**Code Location**: `Log parser/correlation_rules.py` + `Log parser/correlator.py`

**Input**: Raw logs from 4 sources
**Output**: List[Incident] objects

```python
from log_parser.correlator import MultiSourceCorrelationPipeline

# Initialize pipeline
pipeline = MultiSourceCorrelationPipeline(
    window_s=60,           # 60-second correlation window
    stride_s=30,           # 30-second stride
    threshold=0.20,        # Correlation threshold
    default_weights=[0.10, 0.18, 0.22, 0.25, 0.20, 0.05, 0.00]  # R1-R7 weights
)

# Load logs
raw_logs = load_logs_from_sources()  # 5GC, K8s, syslog, netflow

# Correlate
incidents = pipeline.correlate(raw_logs)
print(f"Found {len(incidents)} correlated incidents")
# Output: [Incident(...), Incident(...), ...]
```

---

### Step 2: Convert Incidents to Breach Narratives (BRIDGE 1)

**Code Location**: `DataSharing/bridge_incident_to_nlp.py`

**Input**: List[Incident]
**Output**: List[str] breach descriptions

```python
from DataSharing.bridge_incident_to_nlp import incident_to_breach_narrative

# Convert each incident to narrative
breach_narratives = []
for incident in incidents:
    narrative = incident_to_breach_narrative(incident)
    breach_narratives.append(narrative)
    
    print(f"Incident {incident.incident_id}:")
    print(narrative)
    print()

# Output example:
# "Security incident INC001 detected over 53 seconds.
#  Attack progression:
#  1. ssh_auth via syslog:vagrant@10.0.2.2 targeting k8s-master
#  2. nf_register via 5G network function SMF targeting UDM
#  ..."
```

---

### Step 3: Extract Conditions via NLP (Issue 3)

**Code Location**: `pre-post-condition identifier/security_breach_analysis_v2.py`

**Input**: Breach narratives (text strings)
**Output**: NLP results with keywords, TTPs, conditions

```python
from pre_post_condition_identifier.security_breach_analysis_v2 import (
    KeywordExtractorYAKE,
    TTPointsExtractor,
    CausalRelationExtractor,
    PrePostConditionRanker
)

# Step A: Extract keywords
kw_extractor = KeywordExtractorYAKE(top_n=15)
keywords = kw_extractor.extract_keywords(breach_narrative)
# Output: [Keyword(term='escalate', confidence=0.92), ...]

# Step B: Map to TTPs
ttp_extractor = TTPointsExtractor()
ttps = ttp_extractor.extract_ttps_from_keywords(keywords)
# Output: [TTP(ttp_id='T1134', confidence=0.89), ...]

# Step C: Extract causal relations
causal_ext = CausalRelationExtractor()
causal_pairs = causal_ext.extract_causal_pairs(breach_narrative, ttps)
# Output: [(pre_condition, post_condition, confidence), ...]

# Step D: Rank
ranker = PrePostConditionRanker()
ranked = ranker.rank_conditions(causal_pairs)

# Collect all NLP results
nlp_result = {
    'keywords': [kw.__dict__ for kw in keywords],
    'ttps': [ttp.__dict__ for ttp in ttps],
    'conditions': ranked
}
```

---

### Step 4: Normalize Conditions (BRIDGE 2)

**Code Location**: `DataSharing/normalize_conditions.py`

**Input**: NLP results (with MITRE TTPs, keywords, confidence scores)
**Output**: Discrete evidence for Bayesian model

```python
from DataSharing.normalize_conditions import ConditionNormalizer

# Load schema mapping MITRE TTPs → Model nodes
normalizer = ConditionNormalizer(schema_path='DataSharing/CONDITION_SCHEMA.json')

# Normalize continuous scores to model nodes
normalized_scores = normalizer.normalize_nlp_output(nlp_result)
# Output: {'Token_Impersonation': 0.89, 'Deploy_malware': 0.85, ...}

# Explain mapping (for debugging)
print(normalizer.explain_mapping(nlp_result))

# Convert to discrete evidence (0 or 1)
evidence = normalizer.continuous_to_discrete_evidence(
    normalized_scores,
    threshold=0.75  # Confidence threshold
)
# Output: {'Token_Impersonation': 1, 'Deploy_malware': 1, ...}
```

---

### Step 5: Evaluate Security Posture (Posture Evaluation)

**Code Location**: `1. Posture Evaluation/...` modules

**Input**: Discrete evidence from Bridge 2
**Output**: Posture value ∈ [0, 1]

```python
from pgmpy.models import BayesianNetwork
from pgmpy.factors.discrete import TabularCPD
from pgmpy.inference import VariableElimination

# Load pre-built Bayesian network model
# (Should be created from Posture Evaluation modules)
model = load_bayesian_network_model()

# Run inference with evidence from Bridge 2
infer = VariableElimination(model)

# Query goal node given observed conditions
result = infer.query(
    variables=['goal_node'],  # What we want to predict
    evidence=evidence          # What we observed (from Bridge 2)
)

# Extract posture value
posture_value = result.values[1]  # P(goal_node=True | evidence)
print(f"Security Posture: {posture_value:.3f}")
# Output: {0.0, 1.0} interval, where 1.0 = secure, 0.0 = compromised
```

---

### Step 6: Predict Future Posture (Posture Prediction)

**Code Location**: `2. Posture Prediction/LSTM_multi_feature_posture_prediction.py`

**Input**: Historical posture values (time series)
**Output**: Predicted future posture

```python
from sklearn.preprocessing import StandardScaler
import numpy as np
from tensorflow.keras.models import load_model

# Collect historical posture values
# (From Step 5, but collected over multiple time periods)
# Example: [0.98, 0.95, 0.92, 0.88, 0.85, ...]
historical_posture = np.array([
    (timestamp_0, posture_value_0),
    (timestamp_1, posture_value_1),
    # ... more historical data
])

# Prepare time series
X_train, y_train = prepare_sliding_windows(
    historical_posture,
    window_size=7,  # Use 7 historical values to predict next
    stride=1
)

# Normalize
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)

# Train LSTM model (or load pre-trained)
lstm_model = create_lstm_model(input_dim=X_train.shape[2])
lstm_model.fit(X_train_scaled, y_train, epochs=50, batch_size=16)

# Predict next value
X_test = np.array([historical_posture[-7:, 1]])  # Last 7 values
X_test_scaled = scaler.transform(X_test)
predicted_posture = lstm_model.predict(X_test_scaled)[0]

print(f"Predicted future posture: {predicted_posture:.3f}")
```

---

## COMPLETE END-TO-END EXAMPLE

```python
#!/usr/bin/env python3
"""Complete 5GSPP pipeline example (requires all components installed)"""

import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# STEP 1: LOG CORRELATION (Issue 1)
# ============================================================================
logger.info("=" * 60)
logger.info("STEP 1: Log Correlation")
logger.info("=" * 60)

from log_parser.correlator import MultiSourceCorrelationPipeline

pipeline = MultiSourceCorrelationPipeline(window_s=60, threshold=0.20)
raw_logs = load_logs_from_5g_testbed()  # Load from free5GC, K8s, syslog, netflow
incidents = pipeline.correlate(raw_logs)
logger.info(f"✓ Found {len(incidents)} correlated incidents")

# ============================================================================
# STEP 2: NARRATIVES (Bridge 1)
# ============================================================================
logger.info("=" * 60)
logger.info("STEP 2: Convert Incidents to Breach Narratives")
logger.info("=" * 60)

from DataSharing.bridge_incident_to_nlp import incident_to_breach_narrative

breach_narratives = []
for incident in incidents[:5]:  # Process first 5
    narrative = incident_to_breach_narrative(incident)
    breach_narratives.append(narrative)
    logger.info(f"Incident {incident.incident_id}: {len(narrative)} chars")

logger.info(f"✓ Generated {len(breach_narratives)} breach narratives")

# ============================================================================
# STEP 3: NLP ANALYSIS (Issue 3)
# ============================================================================
logger.info("=" * 60)
logger.info("STEP 3: NLP Analysis (Keywords, TTPs, Causality)")
logger.info("=" * 60)

from pre_post_condition_identifier.security_breach_analysis_v2 import (
    KeywordExtractorYAKE,
    TTPointsExtractor,
    CausalRelationExtractor
)

nlp_results = []
for narrative in breach_narratives:
    kw_ext = KeywordExtractorYAKE()
    keywords = kw_ext.extract_keywords(narrative)
    
    ttp_ext = TTPointsExtractor()
    ttps = ttp_ext.extract_ttps_from_keywords(keywords)
    
    causal_ext = CausalRelationExtractor()
    causals = causal_ext.extract_causal_pairs(narrative, ttps)
    
    nlp_results.append({
        'keywords': [kw.__dict__ for kw in keywords],
        'ttps': [ttp.__dict__ for ttp in ttps],
        'conditions': causals
    })

logger.info(f"✓ Extracted NLP features from {len(nlp_results)} narratives")

# ============================================================================
# STEP 4: NORMALIZATION (Bridge 2)
# ============================================================================
logger.info("=" * 60)
logger.info("STEP 4: Normalize NLP Output to Model Evidence")
logger.info("=" * 60)

from DataSharing.normalize_conditions import ConditionNormalizer

normalizer = ConditionNormalizer(schema_path='DataSharing/CONDITION_SCHEMA.json')

evidence_list = []
for nlp_result in nlp_results:
    normalized = normalizer.normalize_nlp_output(nlp_result)
    evidence = normalizer.continuous_to_discrete_evidence(normalized)
    evidence_list.append(evidence)
    logger.info(f"✓ Normalized {len(evidence)} conditions")

# ============================================================================
# STEP 5: POSTURE EVALUATION
# ============================================================================
logger.info("=" * 60)
logger.info("STEP 5: Bayesian Network Inference")
logger.info("=" * 60)

from pgmpy.inference import VariableElimination

model = load_posture_model()  # Load from Posture Evaluation module
infer = VariableElimination(model)

posture_values = []
for evidence in evidence_list:
    result = infer.query(['goal_node'], evidence=evidence)
    posture = result.values[1]
    posture_values.append(posture)
    logger.info(f"✓ Posture = {posture:.3f}")

# ============================================================================
# STEP 6: POSTURE PREDICTION
# ============================================================================
logger.info("=" * 60)
logger.info("STEP 6: Time Series Prediction (Future Posture)")
logger.info("=" * 60)

lstm_model = load_lstm_model()  #Load from Posture Prediction module
X_test = prepare_prediction_input(posture_values, window_size=7)
predicted_posture = lstm_model.predict(X_test)[0]
logger.info(f"✓ Predicted future posture = {predicted_posture:.3f}")

# ============================================================================
# SUMMARY
# ============================================================================
logger.info("=" * 60)
logger.info("5GSPP END-TO-END PIPELINE COMPLETE")
logger.info("=" * 60)
logger.info(f"Incidents Processed:      {len(incidents)}")
logger.info(f"Breach Narratives:        {len(breach_narratives)}")
logger.info(f"NLP Conditions Extracted: {sum(len(r['ttps']) for r in nlp_results)}")
logger.info(f"Current Posture:          {posture_values[-1]:.3f}")
logger.info(f"Predicted Posture:        {predicted_posture:.3f}")
```

---

## FILES & DEPENDENCIES

### Required Files

| File | Purpose | Location |
|------|---------|----------|
| `correlation_rules.py` | R1-R7 rule implementations | Log parser/ |
| `correlator.py` | Main correlation engine | Log parser/ |
| `security_breach_analysis_v2.py` | YAKE, SBERT, spaCy | pre-post-condition/ |
| `bridge_incident_to_nlp.py` | **BRIDGE 1** | DataSharing/ |
| `normalize_conditions.py` | **BRIDGE 2** | DataSharing/ |
| `CONDITION_SCHEMA.json` | NLP → Model mapping | DataSharing/ |
| Posture Eval modules | Bayesian network | 1. Posture Evaluation/ |
| Posture Pred modules | LSTM/DBN | 2. Posture Prediction/ |

### Python Dependencies

```
# For Log Correlation
numpy≥1.20
pandas≥1.3
networkx≥2.6

# For NLP
sentence-transformers≥2.2
yake≥0.4
spacy≥3.5

# For Bayesian Inference
pgmpy≥0.1.20

# For Prediction
tensorflow≥2.10
scikit-learn≥1.0

# Testing
pytest≥7.0
pytest-cov≥4.0
```

---

## DEBUGGING & VALIDATION

### Test Individual Bridges

```python
# Test Bridge 1: Incident → Narrative
incident = load_test_incident()
narrative = incident_to_breach_narrative(incident)
assert isinstance(narrative, str)
assert len(narrative) > 50
print("✓ Bridge 1 OK")

# Test Bridge 2: NLP → Evidence
nlp_result = {'keywords': [...], 'ttps': [...]}
normalized = normalizer.normalize_nlp_output(nlp_result)
evidence = normalizer.continuous_to_discrete_evidence(normalized)
assert all(v in [0, 1] for v in evidence.values())
print("✓ Bridge 2 OK")
```

### End-to-End Validation

```bash
# Run complete pipeline test
python tests/test_integration_e2e.py

# Expected output:
# ✓ Log Correlation: PASSED
# ✓ Bridge 1 (Incident→Narrative): PASSED
# ✓ NLP Pipeline: PASSED
# ✓ Bridge 2 (NLP→Evidence): PASSED
# ✓ Posture Evaluation: PASSED
# ✓ Posture Prediction: PASSED
# ✓ FULL PIPELINE: PASSED
```

---

## TROUBLESHOOTING

| Issue | Cause | Fix |
|-------|-------|-----|
| "No matching nodes" in Bridge 2 | CONDITION_SCHEMA.json not found | Check path in normalizer init |
| NLP conditions not mapping | MITRE technique not in schema | Add to CONDITION_SCHEMA.json |
| Posture value NaN | Empty evidence dictionary | Debug NLP output |
| Prediction fails | Hardcoded paths in code | Use environment variables |
| Integration test fails | Components not installed | pip install -r requirements.txt |

---

## NEXT STEPS

1. ✅ **Create Bridge Components** (done: `bridge_incident_to_nlp.py`, `normalize_conditions.py`)
2. ✅ **Create Schema** (done: `CONDITION_SCHEMA.json`)
3. **Create Integration Tests** (`test_integration_e2e.py` - needs implementation)
4. **Validate End-to-End** (run full pipeline on sample data)
5. **Paper Documentation** (add sections referencing this guide)

