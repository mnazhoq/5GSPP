# Implementation Guide - State-of-the-Art NLP for Security Breach Analysis
---

## Installation & Setup

### Required Python Packages

```bash
# Core dependencies
pip install yake
pip install sentence-transformers
pip install spacy
pip install transformers torch
pip install networkx

# Download spaCy English model
python -m spacy download en_core_web_sm
```

### Quick Test

```python
from security_breach_analysis_v2 import SecurityBreachAnalyzer

analyzer = SecurityBreachAnalyzer()

breach_description = """
Attackers used password spraying to compromise valid user accounts,
bypassing authentication controls to gain server access and achieve
lateral movement through the network.
"""

result = analyzer.analyze_breach(breach_description)

# View results
print("Keywords found:", len(result['step_a_keywords']))
print("TTPs mapped:", len(result['step_b_ttps']))
print("Pre-conditions:", len(result['step_c_preconditions']))
print("Pre→Post chains:", len(result['step_d_connections']))
```

---

## Running the Experimental Analysis

### Execute Full Analysis

```bash
python3 experimental_results_v2.py
```

This will:
1. Print algorithm details and citations
2. Analyze 5 demo breaches
3. Generate statistical summaries
4. Display detailed results with confidence scores
5. Output insights and findings
6. Save results to `experimental_results.json`

### Generate Demo Data

```bash
python3 generate_demo_data.py
```

This creates realistic security incident descriptions for testing.

---


