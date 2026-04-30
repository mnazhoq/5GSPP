# TDSC MAJOR REVISION: IMPLEMENTATION CHECKLIST & FILE INVENTORY

**Complete analysis package created April 3, 2026**
**All files ready for implementation**

---

## FILES CREATED IN `/5GSPP/DataS haring/`

### Documentation Files (Read First)
- [x] **EXECUTIVE_SUMMARY_AND_ROADMAP.md** (8.2 KB)
  - Overall strategy for addressing all 3 issues
  - Timeline and effort estimates
  - Messages to respond to reviewers
  - Critical success factors

- [x] **FLAWS_AND_RESOLUTIONS.md** (12.4 KB)
  - 12 specific flaws identified with solutions
  - Paper section locations for additions
  - Cost-benefit analysis per fix
  - Summary table of all flaws

- [x] **ISSUE2_PUBLIC_DATA_SHARING_STRATEGY.md** (18.7 KB)
  - Complete dataset directory structure
  - Public repository options analysis
  - Metadata file specifications
  - Code licensing recommendations
  - Data Availability Statement template

- [x] **COMPATIBILITY_VERIFICATION.md** (15.3 KB)
  - Component inventory and analysis
  - Data flow compatibility check
  - 4 critical integration issues identified
  - Implementation checklist for integration

- [x] **INTEGRATION_GUIDE.md** (12.8 KB)
  - Step-by-step integration of all 4 modules
  - Code examples for each step
  - Complete end-to-end pipeline example
  - Debugging and troubleshooting guide

### Code Files (Bridge Components)
- [x] **bridge_incident_to_nlp.py** (8.5 KB)
  - Convert Incident objects → Breach narratives
  - Enable Issue 1 → Issue 3 integration
  - Includes metadata extraction functions

- [x] **normalize_conditions.py** (12.2 KB)
  - NLP output → Bayesian model nodes
  - Continuous scores → Discrete evidence
  - Enable Issue 3 → Posture Evaluation integration

### Schema & Configuration
- [x] **CONDITION_SCHEMA.json** (6.1 KB)
  - Mapping: MITRE techniques → Model nodes
  - Keyword mappings for plain text conditions
  - Confidence thresholds
  - 5G-specific event mappings

---

## IMPLEMENTATION CHECKLIST

### PHASE 0: Read & Understand (2-4 hours)
- [ ] Read EXECUTIVE_SUMMARY_AND_ROADMAP.md (priority: HIGH)
- [ ] Skim FLAWS_AND_RESOLUTIONS.md (reference)
- [ ] Read COMPATIBILITY_VERIFICATION.md (priority: HIGH)
- [ ] Read INTEGRATION_GUIDE.md (needed for implementation)

**Estimated time**: 2-4 hours

---

### PHASE 1: Paper Additions (4-6 hours)

#### Issue 1 Additions (Section V-A)
- [ ] Add Figure 6 caption explaining Rule R5 (0.25 pages)
  - Reference: FLAWS_AND_RESOLUTIONS.md Flaw 1.1
  - Location: Section V-A, Figure 6

- [ ] Add Algorithm 2B text (CEF normalization) (0.5 pages)
  - Reference: FLAWS_AND_RESOLUTIONS.md Flaw 1.2
  - Location: Section V-A, after Algorithm 2

- [ ] Add Table: Timestamp Normalization Strategy (0.25 pages)
  - Reference: FLAWS_AND_RESOLUTIONS.md Flaw 1.3
  - Location: Section V-A, new paragraph

- [ ] Expand Section I-E on learned weights (0.5 pages)
  - Reference: FLAWS_AND_RESOLUTIONS.md Flaw 1.4
  - Location: Section I-E, after Equation 1

#### Issue 2 Additions (Section II-A)
- [ ] Add Algorithm 4 pseudocode (0.75 pages)
  - Reference: FLAWS_AND_RESOLUTIONS.md Flaw 2.1
  - Location: Section II-A, new subsection

- [ ] Add Dataset Schema Specification (0.5 pages)
  - Reference: FLAWS_AND_RESOLUTIONS.md Flaw 2.2
  - Location: Section II-A, after Algorithm 4

#### Issue 3 Additions (Section V-B)
- [ ] Add Algorithm section with 4 citations (0.75 pages)
  - Reference: FLAWS_AND_RESOLUTIONS.md Flaw 3.1
  - Location: Section V-B, new subsection "NLP Algorithms"

- [ ] Add confidence score calculation explanation (0.5 pages)
  - Reference: FLAWS_AND_RESOLUTIONS.md Flaw 3.2
  - Location: Section V-B, after algorithm section

- [ ] Add hyperparameters table (0.5 pages)
  - Reference: FLAWS_AND_RESOLUTIONS.md Flaw 3.4
  - Location: Section V-B, "Implementation Details"

#### Data Availability Statement
- [ ] Add "Reproducibility" section after Conclusion (0.25 pages)
  - Reference: ISSUE2_PUBLIC_DATA_SHARING_STRATEGY.md Part 4
  - Specify GitHub repo + Zenodo DOI
  - Include reproduction instructions

**Total Paper Impact**: +5.5-6.5 pages

**Estimated time**: 4-6 hours

---

### PHASE 2: Bridge Components & Testing (12-16 hours)

#### Create/Test Bridge Code
- [ ] Copy `bridge_incident_to_nlp.py` to project
  - Location: Copy from DataSharing/ to project
  - Test: `python bridge_incident_to_nlp.py`

- [ ] Copy `normalize_conditions.py` to project
  - Location: Copy from DataSharing/ to project
  - Test: `python normalize_conditions.py`

- [ ] Copy `CONDITION_SCHEMA.json` to project
  - Location: Copy from DataSharing/ to project
  - Update path references in `normalize_conditions.py`

#### Create Integration Tests
- [ ] Create `tests/test_integration_e2e.py`
  - Template provided in INTEGRATION_GUIDE.md
  - Test all 6 pipeline steps

- [ ] Create `tests/test_data_flow_compatibility.py`
  - Template provided in COMPATIBILITY_VERIFICATION.md
  - Validate data formats between components

#### Fix Existing Code
- [ ] Remove hardcoded Windows paths from Posture Prediction
  - File: `2. Posture Prediction/LSTM_multi_feature_posture_prediction.py`
  - Line: 15 (data_path = "D:\\OneDrive...")
  - Replace: `os.getenv('5GSPP_DATA_PATH', './data/')`

- [ ] Add input validation to Posture modules
  - Ensure they accept Bridge 2 output format

#### Run Tests
- [ ] Execute `test_integration_e2e.py`
  - Expected: ALL tests PASS
  - If failed: Use COMPATIBILITY_VERIFICATION.md debugging section

**Estimated time**: 12-16 hours

---

### PHASE 3: Dataset Organization (8-10 hours)

#### Organize Synthetic Data
- [ ] Sort 25,000 events into scenario directories
  - Structure: See ISSUE2_PUBLIC_DATA_SHARING_STRATEGY.md
  - Create: dos_amf/, lateral_movement/, priv_escalation/, signaling_storm/, data_exfil/

- [ ] Create ground_truth.json for each incident
  - Schema provided in ISSUE2_PUBLIC_DATA_SHARING_STRATEGY.md
  - Content: incident_id, attack_chains, affected_systems, correlation_ids

- [ ] Create metadata.json for each incident
  - Content: narrative, NIST controls, MITRE tactics

- [ ] Compress into archive format
  - Total size should be ~4.2 GB compressed

**Estimated time**: 8-10 hours

---

### PHASE 4: Public Release (6-8 hours)

#### GitHub Repository
- [ ] Create GitHub repo: `5GSPP-Framework` or `5GSPP`
- [ ] Upload source code (all Log Parser + Pre-Post + integration)
- [ ] Set up Git LFS for large files
- [ ] Create releases/v1.0 release tag

#### Zenodo Archive
- [ ] Package complete dataset (4.2 GB)
- [ ] Submit to Zenodo
- [ ] Obtain permanent DOI
- [ ] Record DOI for paper

#### Documentation
- [ ] Create public-facing README (GitHub)
- [ ] Create SCHEMA.md with field definitions
- [ ] Create 6 Jupyter demonstration notebooks
- [ ] API documentation (auto-generated or manual)

**Estimated time**: 6-8 hours

---

### PHASE 5: Final Validation (4-6 hours)

- [ ] Paper review: All 5.5-6.5 pages added
- [ ] Code review: All bridge components integrated
- [ ] Integration test: Full e2e pipeline runs successfully
- [ ] Dataset validation: 25,000 events organized + compressed
- [ ] GitHub/Zenodo: Links work, DOI issued
- [ ] Paper grammar/formatting check
- [ ] Final internal review before submission

**Estimated time**: 4-6 hours

---

## TOTAL IMPLEMENTATION EFFORT

| Phase | Hours | Timeline |
|-------|-------|----------|
| 0. Reading & Understanding | 2-4 | Day 1 |
| 1. Paper Additions | 4-6 | Day 1-2 |
| 2. Bridge Components & Tests | 12-16 | Day 2-5 |
| 3. Dataset Organization | 8-10 | Day 3-5 |
| 4. Public Release | 6-8 | Day 8-10 |
| 5. Final Validation | 4-6 | Day 10-12 |
| **TOTAL** | **36-50 hours** | **~2 weeks** |

**Recommended pace**: 
- **Week 1**: Phases 0-3 (30-40 hours)
- **Week 2**: Phases 4-5 (6-14 hours)
- **Slack**: 2-3 days buffer for unexpected issues

---

## HOW TO USE THIS PACKAGE

### For Reviewers/Readers
1. Start with **EXECUTIVE_SUMMARY_AND_ROADMAP.md** (5 min) - high-level overview
2. Review **FLAWS_AND_RESOLUTIONS.md** (15 min) - understand each flaw
3. Browse **ISSUE2_PUBLIC_DATA_SHARING_STRATEGY.md** (10 min) - data strategy
4. Optional: Read **COMPATIBILITY_VERIFICATION.md** (20 min) - technical details

### For Implementation
1. **Day 1**: Read INTEGRATION_GUIDE.md carefully
2. **Days 2-4**: Follow Phase 1-3 checklist sequentially
3. **Days 5-6**: Execute Phase 4-5
4. **Throughout**: Reference specific flaws in FLAWS_AND_RESOLUTIONS.md

---

## QUICK REFERENCE: Which Document to Read When?

| Question | Answer | Document |
|----------|--------|----------|
| "How do I fix all issues?" | Read this roadmap | THIS FILE |
| "What are the 12 flaws?" | Detailed list + solutions | FLAWS_AND_RESOLUTIONS.md |
| "How do I share dataset publicly?" | GitHub + Zenodo structure | ISSUE2_PUBLIC_DATA_SHARING_STRATEGY.md |
| "How do the components connect?" | Data flow + integration | COMPATIBILITY_VERIFICATION.md |
| "How do I code the integration?" | Step-by-step examples | INTEGRATION_GUIDE.md |
| "What code files do I need?" | Bridge components | bridge_incident_to_nlp.py, normalize_conditions.py |
| "How do I map conditions?" | NLP → Model nodes | CONDITION_SCHEMA.json |

---

## SUCCESS CRITERIA

### Paper Submission Checklist
- [ ] Paper word count within limit (typically 15-20 pages)
- [ ] All 5.5-6.5 pages of Issue 1-3 fixes added
- [ ] Data Availability Statement present
- [ ] All figure captions updated
- [ ] All citations complete and formatted
- [ ] Grammar/spelling check complete

### Code Release Checklist
- [ ] All source code uploaded to GitHub
- [ ] Bridge components (`bridge_*.py`, `normalize_*.py`) present
- [ ] Integration tests written and PASSING
- [ ] README with installation instructions
- [ ] 6 Jupyter notebooks demonstrating usage
- [ ] License file (Apache 2.0) included
- [ ] requirements.txt with all dependencies

### Dataset Release Checklist
- [ ] 25,000 events sorted into 5 scenario directories
- [ ] ground_truth.json for each incident
- [ ] Complete archive compressed to ~4.2 GB
- [ ] Uploaded to Zenodo with DOI obtained
- [ ] Dataset README with schema

### Expected Reviewer Response
- ✅ Issue 1 "Data processing unclear" → RESOLVED
- ✅ Issue 2 "Lack of dataset" → RESOLVED  
- ✅ Issue 3 "NLP unclear" → RESOLVED
- ✅ Code reproduction possible
- ✅ Dataset accessible and documented
- ✅ Integration working end-to-end

**Expected Outcome**: MINOR REVISION or ACCEPT

---

## FINAL NOTES

1. **Document everything**: Each file from this package is extensively documented. Read the docstrings and comments carefully.

2. **Test frequently**: After each phase, run the relevant tests to catch issues early.

3. **Keep GitHub repo public**: Makes reviewers' lives easier if they can access code immediately.

4. **Update paper links**: Before final submission, verify all GitHub + Zenodo URLs are correct and accessible.

5. **Communication**: When submitting revision, include a brief note (like the one in EXECUTIVE_SUMMARY_AND_ROADMAP.md Part 6) summarizing the changes made.

---

## SUPPORT

For questions about specific files, refer to:
- **Paper questions** → FLAWS_AND_RESOLUTIONS.md
- **Data sharing questions** → ISSUE2_PUBLIC_DATA_SHARING_STRATEGY.md
- **Integration questions** → INTEGRATION_GUIDE.md
- **Code examples** → bridge_incident_to_nlp.py, normalize_conditions.py
- **Mapping questions** → CONDITION_SCHEMA.json

**Questions not covered?** Create an issue on GitHub or refer back to the original paper sections cited in each flaw fix.

