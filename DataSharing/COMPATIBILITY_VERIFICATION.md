# COMPATIBILITY VERIFICATION & INTEGRATION ANALYSIS

**Status**: CRITICAL for paper quality - ensures all 4 code modules work together

---

## PART 1: COMPONENT INVENTORY & ANALYSIS

### 1.1 Code Categories Across Modules

| Module | Component | Location | Purpose | Status |
|--------|-----------|----------|---------|--------|
| **Issue 1** | Correlation Rules | Log parser/correlation_rules.py | R1-R7 rule implementation | ✅ Strong |
| **Issue 1** | Log Normalizer | Log parser/correlator.py | CEF conversion | ✅ Strong |
| **Issue 1** | Event-State Model | Log parser/correlator.py | Temporal windowing | ✅ Strong |
| **Issue 3** | YAKE Extractor | pre-post/security_breach_analysis_v2.py | Keyword extraction | ✅ Strong |
| **Issue 3** | TTP Mapper | pre-post/security_breach_analysis_v2.py | SBERT integration | ✅ Strong |
| **Issue 3** | Causal Extractor | pre-post/security_breach_analysis_v2.py | spaCy NLP | ✅ Strong |
| **Posture Eval** | Bayesian Network | 1. Posture Evaluation/... | Condition probability | ⚠️ Needs integration |
| **Posture Pred** | LSTM Predictor | 2. Posture Prediction/LSTM_multi_feature_posture_prediction.py | Time series | ⚠️ Needs integration |
| **Posture Pred** | DBN Predictor | 2. Posture Prediction/5GSPP_DBN.py | Dynamic Bayesian | ⚠️ Needs integration |

---

## PART 2: DATA FLOW COMPATIBILITY ANALYSIS

### 2.1 End-to-End Pipeline Data Flow

```
[RAW LOGS] 
  ↓ (Issue 1 - Log Parser)
├─→ Free5GC logs, K8s events, syslog, NetFlow
├─  CEF Normalization
│   • Timestamp: ISO8601 UTC
│   • Severity: [1-5]
│   • Fields: (ts, source, actor, target, action, event_type, label, corr_id)
│
├─  Apply Correlation Rules R1-R7
│   • R1: Temporal window (60s default)
│   • R2: Entity identity (actor/target overlap) 
│   • R3: Session key matching
│   • R4: Transaction ID matching
│   • R5: Causal dependency (3GPP DAG)
│   • R6: Semantic similarity (TF-IDF)
│   • R7: Statistical co-occurrence
│
├─  Output: Correlated Incidents
│   ├─ incident_id: UUID
│   ├─ events: [LogEvent, LogEvent, ...]
│   ├─ correlation_score: float [0-1]
│   └─ correlation_rules_fired: [R4, R5]
│
├─ (Issue 3 - NLP Pipeline)
├─→ Incident → Breach Description (narrative)
├─  YAKE Keyword Extraction
│   • Output: [Keyword(term, type, confidence), ...]
│
├─  SBERT TTP Mapping
│   • Output: [TTP(id, name, tactic, confidence), ...]
│
├─  spaCy Causal Extraction
│   • Output: [(pre_condition, post_condition, confidence), ...]
│
├─  PageRank Ranking
│   • Output: ranked_conditions with centrality scores
│
├─ (Posture Evaluation)
├─→ Pre/Post-Conditions → Event-State Model
├─  Build Bayesian Network
│   • Nodes: {conditions, events, goal_node}
│   • Edges: causal relationships
│   • CPD: Conditional probability distributions
│
├─  Inference (Variable Elimination)
│   • Query: P(goal_node | observed_conditions)
│   • Output: posture_value ∈ [0, 1]
│       (0 = compromised, 1 = secure)
│
├─ (Posture Prediction)
├─→ Historical Posture Values → Time Series Models
├─  LSTM Path
│   • Input: [posture_t, posture_t+1, ..., posture_t+k]
│   • Output: predicted_posture_t+k+1
│
├─  DBN Path  
│   • Input: Multiple time-slice Bayesian networks + conditions
│   • Output: predicted_posture_t+k+1
│
└─ Final Output: Security score forecast
```

### 2.2 Data Format Compatibility Check

**Level 1: CEF Format** ✅
- All sources normalize to same CEF tuple
- Timestamp precision: microsecond (supports all source precision)
- Severity: unified [1-5] scale
- Status: COMPATIBLE

**Level 2: Incident Aggregation** ✅
- Correlated events grouped by incident_id
-Each incident has metadata (start time, end time, correlation score)
- Status: COMPATIBLE

**Level 3: Incident → NLP Input** ⚠️ NEEDS CLARIFICATION
- **Issue**: How is incident converted to "breach description"?
- **Current**: No code shows incident → narrative conversion
- **Required**: Function that takes Incident object and generates text description
- **Recommendation**: Add function like:
```python
def incident_to_breach_narrative(incident: Incident) -> str:
    """Generate narrative from correlated incident events."""
    # Extract attack sequence from incident.events
    # Format into natural language description
    # Return for NLP pipeline input
    pass
```

**Level 4: NLP Output → Posture Model** ⚠️ NEEDS VALIDATION
- NLP outputs: {keywords, TTPs, pre/post_conditions, scores}
- Posture model expects: StateModel with pre-conditions and post-conditions
- **Issue**: NLP condition names vs Bayesian network node names must match
- **Required**: Mapping table from MITRE techniques to model nodes
- **Recommendation**: Create mapping file conditions_mapping.json

**Level 5: Posture Values → Time Series**  ✓ COMPATIBLE
- Posture evaluator outputs: float ∈ [0, 1]
- LSTM/DBN predictors expect: time series of floats
- Status: Data types align

---

## PART 3: IDENTIFIED COMPATIBILITY ISSUES

### Issue A: Missing Incident-to-Narrative Conversion

**Problem**: Code flow breaks from Log Parser to NLP Pipeline
```
Incident (structured data) → [GAP] → Breach Description (text)
```

**Current State**: 
- `correlation_rules.py` outputs: Incident object with correlated events
- `security_breach_analysis.py` inputs: String breach description
- **No code connects these two**

**Solution**: Create Bridge Function
```python
# In: new file /5GSPP/integration/bridge_incident_to_nlp.py

def incident_to_breach_description(incident: Incident) -> str:
    """
    Convert structured incident (from log correlator) to narrative.
    
    Args:
        incident: Incident object with correlated events
        
    Returns:
        String description suitable for NLP pipeline
    """
    events = incident.events
    attack_sequence = []
    
    # Extract key events
    for event in events:
        if event.label == "ATTACK":
            attack_sequence.append({
                'action': event.action,
                'actor': event.actor,
                'target': event.target,
                'type': event.event_type,
                'ts': event.ts
            })
    
    # Generate narrative
    narrative = f"""
    Attack incident {incident.incident_id} progressed over {incident.duration} seconds:
    """
    
    for i, event in enumerate(attack_sequence):
        narrative += f"\n{i+1}. {event['action']} by {event['actor']}"
        if event['target']:
            narrative += f" targeting {event['target']}"
    
    # Add systems affected
    systems = set(e.actor for e in events if e.source == "5gnf")
    if systems:
        narrative += f"\nAffected 5G systems: {', '.join(systems)}"
    
    return narrative
```

**Impact**: Enables integration of Issue 1 → Issue 3

---

### Issue B: NLP Condition Names vs Bayesian Network Nodes

**Problem**: Name Mismatch
- NLP outputs: "Password Spraying Attack", "Bypass User Account Control"
- Bayesian model expects: "Logon_PB", "Access_Server", "Bypass_Authentication"

**Current State**:
- `security_breach_analysis.py` uses MITRE technique names
- `5GSPP_DBN.py` and posture model use custom short names
- **No name normalization implemented**

**Solution**: Create Standardized Taxonomy Mapping

File: `/5GSPP/DataSharing/CONDITION_SCHEMA.json`
```json
{
  "mapping": {
    "mitre_technique": {
      "T1187": {
        "name": "Forced Authentication",
        "posture_model_node": "LogOn_PB",
        "breach_control": "AC-7"
      },
      "T1134": {
        "name": "Access Token Manipulation", 
        "posture_model_node": "Bypass_Authentication",
        "breach_control": "AC-6"
      }
    }
  }
}
```

**Code to Generate Mapping** (new file):
```python
# In: /5GSPP/DataSharing/normalize_conditions.py

CONDITION_MAPPING = {
    # Keyword/MITRE → Posture Model Node
    "bypass": "Bypass_Authentication",
    "malware": "Deploy_malware",
    "escalate": "Token_Impersonation",
    "access server": "Access_Server",
    "exfiltrate": "Exfiltrating_data",
    # ... (complete mapping)
}

def normalize_condition_name(nlp_output: str) -> str:
    """Convert NLP output to model node name."""
    nlp_lower = nlp_output.lower()
    for nlp_term, model_node in CONDITION_MAPPING.items():
        if nlp_term in nlp_lower:
            return model_node
    return None  # Unknown condition
```

**Impact**: Enables Issue 3 → Posture Evaluation connection

---

### Issue C: Timestamp Format Consistency in Predictors

**Problem**: Time Series Models Expect Different Timestamp Formats
- LSTM model expects: Unix timestamp (seconds since epoch)
- Posture trajectories: (timestamp, posture_value) pairs
- Ground truth: ISO8601 strings

**Current State**:
- `LSTM_multi_feature_posture_prediction.py` line 28: reads CSV with timestamp column
- No validation that timestamp format matches what model expects

**Solution**: Implement Timestamp Normalization
```python
# In predictor files, add:

def normalize_timestamps(timestamps):
    """Convert mixed timestamp formats to Unix seconds."""
    normalized = []
    for ts in timestamps:
        if isinstance(ts, str):
            # ISO8601 string
            dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            normalized.append(dt.timestamp())
        elif isinstance(ts, datetime):
            normalized.append(ts.timestamp())
        else:
            # Assume already Unix timestamp
            normalized.append(ts)
    return normalized
```

**Impact**: Ensures Posture Evaluation → Posture Prediction compatibility

---

### Issue D: Missing Unit Tests for Integration Points

**Problem**: All components have internal tests, but integration tests missing

**Current State**:
- `Log parser/*_test.py`: Tests correlation rules individually
- `pre-post/*_test.py`: Tests NLP pipeline individually
- **No tests for**: Incident → NLP → Posture → Prediction pipeline

**Solution**: Create Integration Test Suite
```python
# In: /5GSPP/tests/test_integration_e2e.py

def test_incident_to_nlp_to_posture():
    """End-to-end test: Log Correlation → NLP → Posture Evaluation"""
    
    # Step 1: Generate test incident
    incident = create_test_incident(
        events=[attack_event_1, attack_event_2, ...],
        duration_seconds=60
    )
    
    # Step 2: Convert to breach narrative
    narrative = bridge.incident_to_breach_description(incident)
    assert isinstance(narrative, str)
    assert len(narrative) > 50  # Reasonably long description
    
    # Step 3: Run NLP pipeline
    nlp_result = nlp_engine.analyze_breach(narrative)
    assert len(nlp_result['keywords']) > 5
    assert len(nlp_result['ttps']) > 0
    
    # Step 4: Normalize conditions
    conditions = {}
    for cond in nlp_result['conditions']:
        model_node = normalize_condition_name(cond['description'])
        assert model_node is not None, f"Unknown condition: {cond}"
        conditions[model_node] = cond['confidence']
    
    # Step 5: Evaluate posture
    posture_value = posture_eval(conditions)
    assert 0.0 <= posture_value <= 1.0
    
    # Step 6: Run predictor (optional)
    future_posture = posture_pred.predict([posture_value])
    assert isinstance(future_posture, float)
```

**Impact**: Validates all 4 components work together

---

## PART 4: COMPATIBILITY REQUIREMENTS TABLE

| From Module | To Module | Data Format | Status | Fix Required |
|-------------|-----------|-------------|--------|--------------|
| Correlation Rules | NLP Pipeline | Incident object | ❌ Missing | Bridge function + test |
| NLP Pipeline | Posture Eval | Condition strings | ⚠️ Name mismatch | Mapping table + converter |
| NLP Pipeline | Posture Pred | Confidence scores | ✅ Compatible | Validation only |
| Posture Eval | Posture Pred | (timestamp, posture) | ⚠️ Format inconsistent | Timestamp normalizer |
| Posture Pred | Results | Predictions | ✅ Compatible | No changes needed |

---

## PART 5: IMPLEMENTATION CHECKLIST FOR COMPATIBILITY

### Phase 1: Create Missing Bridge Components
- [ ] `bridge_incident_to_nlp.py` - Convert incident to narrative (Week 1)
- [ ] `normalize_conditions.py` - Map NLP terms to model nodes (Week 1)
- [ ] `timestamp_normalizer.py` - Unify timestamp formats (Week 1)

### Phase 2: Create Integration Tests
- [ ] `test_integration_e2e.py` - Full pipeline test (Week 2)
- [ ] `test_data_flow_compatibility.py` - Data format validation (Week 2)
- [ ] All integration tests must pass before paper submission (Week 2)

### Phase 3: Update Documentation
- [ ] Data flow diagram in ARCHITECTURE.md (Week 2)
- [ ] Integration guide in DataSharing folder (Week 2)
- [ ] Mapping schema documentation (Week 2)

### Phase 4: Add to DataSharing Folder
- [ ] All bridge code files (Week 2)
- [ ] All integration tests (Week 2)
- [ ] INTEGRATION_GUIDE.md explaining connections (Week 2)

---

## PART 6: SPECIFIC COMPATIBILITY ISSUES FOR EACH CODE MODULE

### 6.1 Log Parser (Issue 1) ✅ STRONG

**Status**: Well-integrated internally
- Correlation rules work on normalized CEF events
- Output: Incident objects with incident_id, events[], correlation_score
- No issues with this module

**Recommendation**: No changes needed, just needs documentation of Incident object schema

---

### 6.2 Pre-Post-Conditions (Issue 3) ✅ STRONG

**Status**: Well-implemented NLP pipeline
- YAKE, SBERT, spaCy all integrated
- Outputs structured: keywords[], TTPs[], conditions[]
- Each output has confidence scores

**Issue**: Expects string input (breach description), doesn't link to Log Parser output

**Fix**: Add bridge function to connect Log Parser → NLP

---

### 6.3 Posture Evaluation (Module 1) ⚠️ NEEDS REVIEW

**File**: `1. Posture Evaluation/Sequence Generation/synthetic_result_data_generator.py`

**Issues Found**:
1. **Incomplete code**: Lines show DBN inference setup but no complete class definition
2. **No input validation**: Expects pre-built Bayesian network model object
3. **NLP integration unclear**: How do pre/post-conditions from NLP become model evidence?

**What's Missing**:
```python
# Missing: How are NLP-derived conditions converted to evidence?

# Input from NLP:
# {
#   "Access_Server": 0.85,
#   "Deploy_malware": 0.92,
#   "Bypass_Authentication": 0.78
# }

# Model expects:
# evidence = {'Access_Server': 1, 'Deploy_malware': 1, 'Bypass_Authentication': 1}
# (Boolean values from continuous confidence scores)

# Missing function:
def nlp_scores_to_model_evidence(nlp_scores: Dict[str, float], 
                                   threshold: float = 0.5) -> Dict[str, int]:
    """Convert NLP confidence scores to Bayesian model evidence."""
    evidence = {}
    for node, score in nlp_scores.items():
        evidence[node] = 1 if score >= threshold else 0
    return evidence
```

**Fix Required**: Create function to convert continuous NLP scores → discrete model evidence

---

### 6.4 Posture Prediction (Module 2) ⚠️ NEEDS REVIEW

**Files**: `LSTM_multi_feature_posture_prediction.py`, `5GSPP_DBN.py`

**Issues Found**:
1. **Data path hardcoded**: Line 15 references `"D:\\OneDrive - Concordia..."`
2. **No input validation**: Doesn't check input shape/format
3. **Separate from Posture Eval**: Doesn't consume Posture Eval outputs directly

**What's Missing**:
```python
# Current: LSTM reads CSV file
data_path = "D:\\OneDrive - Concordia University - Canada\..."  # ❌ Hardcoded!

# Should be:
data_path = os.getenv('5GSPP_DATA_PATH', './data/')

# Also missing: Function to consume Posture Eval outputs
def create_timeseries_from_posture_eval(posture_values: List[float],
                                        timestamps: List[datetime]) -> pd.DataFrame:
    """Convert Posture Evaluation results to time series for LSTM."""
    df = pd.DataFrame({
        'timestamp': timestamps,
        'posture_value_goal_node': posture_values,
    })
    return df
```

**Fix Required**: 
1. Remove hardcoded paths
2. Create input function to consume Posture Eval outputs
3. Add input shape/format validation

---

## PART 7: CRITICAL ISSUES SUMMARY

| Issue | Severity | Impact | Fix Effort |
|-------|----------|--------|-----------|
| Missing Incident→Narrative bridge | HIGH | Blocks Issue 1→3 integration | 2 hours |
| Condition name mapping | HIGH | Blocks Issue 3→Posture integration | 4 hours |
| Hardcoded paths in predictors | MEDIUM | Blocks reproducibility | 1 hour |
| No integration tests | MEDIUM | Can't validate pipeline | 6 hours |
| Threshold conversion (NLP→Model) | HIGH | Blocks Posture Eval logic | 3 hours |
| Timestamp format mismatch | MEDIUM | Breaks time-series | 2 hours |

**Total Effort to Resolve**: ~18-20 hours

---

## NEXT STEPS

1. **IMMEDIATE** (Today): Create bridge components (4 hours)
2. **TODAY**: Create integration tests (6 hours)
3. **TOMORROW**: Fix hardcoded paths and thresholds (4 hours)
4. **TOMORROW**: Run full e2e test and validate (2 hours)
5. **WITHIN 48 HOURS**: Update paper with integration evidence

