"""
Quick Start Guide - Running the Security Breach Analysis
"""

QUICK_START = """
╔════════════════════════════════════════════════════════════════════════════════╗
║        SECURITY BREACH PRE/POST-CONDITION ANALYSIS - QUICK START GUIDE         ║
╚════════════════════════════════════════════════════════════════════════════════╝

1. GENERATE DEMO DATA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   $ python3 generate_demo_data.py
   
   Output: Creates demo_breaches.json with 20 synthetic breach descriptions
   
   Sample breaches include:
   ✓ AC-6: Privilege Escalation
   ✓ LogOn-PB: Password-based Authentication Bypass
   ✓ RemoteAccess-PB: SSH Attack & Lateral Movement
   ✓ Config-PB: Malware Persistence
   ✓ AgentMonitor-PB: Monitoring Evasion
   ✓ Protocol-based Monitoring-PB: C2 Communication


2. RUN EXPERIMENTAL ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   $ python3 experimental_results.py
   
   Output: 
   ✓ Analyzes 5 breach scenarios through 4-step methodology
   ✓ Prints detailed statistics and insights
   ✓ Generates experimental_results.json


3. VIEW COMPLETE DOCUMENTATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   Read: ANALYSIS_DOCUMENTATION.md
   
   Includes:
   ✓ Methodology explanation
   ✓ Code architecture
   ✓ Sample analysis results
   ✓ How to extend and customize


4. USE IN YOUR OWN CODE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   from security_breach_analysis import SecurityBreachAnalyzer
   
   analyzer = SecurityBreachAnalyzer()
   
   # Your breach description
   breach = "Attacker compromised admin account and deployed ransomware..."
   
   # Run analysis
   result = analyzer.analyze_breach(breach)
   
   # Access results
   print("Keywords found:", len(result['step_a_keywords']))
   print("TTPs mapped:", len(result['step_b_ttps']))
   print("Pre-conditions:", result['step_c_preconditions'])
   print("Post-conditions:", result['step_c_postconditions'])


═════════════════════════════════════════════════════════════════════════════════
METHODOLOGY VISUAL FLOW
═════════════════════════════════════════════════════════════════════════════════

   Breach Description (Unstructured Text)
           │
           ▼
   ╔──────────────────────────────────╗
   │ STEP A: Keyword Extraction (NLP) │
   ├──────────────────────────────────┤
   │ INPUT:  Free-form breach text    │
   │ OUTPUT: Keywords (11.6 avg)      │
   │         • action, target, tool   │
   │         • credential, service    │
   │ CONFIDENCE: 0.80-0.90            │
   └──────────────────────────────────┘
           │ [Keywords]
           ▼
   ╔──────────────────────────────────╗
   │ STEP B: TTP Mapping              │
   ├──────────────────────────────────┤
   │ INPUT:  Keywords                 │
   │ OUTPUT: MITRE ATT&CK TTPs (3.4)  │
   │         • T15498: Valid Accounts │
   │         • T1187: Forced Auth     │
   │         • T1563.002: Session Hijack
   │ DATABASE: 7 MITRE techniques     │
   └──────────────────────────────────┘
           │ [TTPs]
           ▼
   ╔──────────────────────────────────╗
   │ STEP C: Cause-Effect Analysis    │
   ├──────────────────────────────────┤
   │ FOR EACH TTP:                    │
   │ • Extract PRE-conditions (causes)│
   │   → 11.0 per breach              │
   │   → 77.5% confidence             │
   │ • Extract POST-conditions (effects)
   │   → 10.2 per breach              │
   │   → 81.5% confidence             │
   │ KNOWLEDGE BASES: Pre/Post DB     │
   └──────────────────────────────────┘
           │ [Pre + Post Conditions]
           ▼
   ╔──────────────────────────────────╗
   │ STEP D: Ranking & Connections    │
   ├──────────────────────────────────┤
   │ RANKING:                         │
   │ • Criticality scores (0.0-1.0)   │
   │ • Adjust confidence scores       │
   │ CONNECTING:                      │
   │ • Link pre→post via shared TTPs  │
   │ • Generate causal chains         │
   │ • 3.4 connections per breach     │
   └──────────────────────────────────┘
           │ [Analysis Results]
           ▼
   Final Output: Complete attack propagation analysis
   ✓ Root causes identified
   ✓ Blast radius calculated
   ✓ Causal chains generated
   ✓ Conditions ranked by criticality


═════════════════════════════════════════════════════════════════════════════════
EXAMPLE OUTPUT
═════════════════════════════════════════════════════════════════════════════════

INPUT BREACH DESCRIPTION:
┌─────────────────────────────────────────────────────────────────────────────┐
│ Attacker executed bypass user account control through deploying malware     │
│ that escalated privileges. Credential token was used to access server and  │
│ authenticate without proper elevation checks.                              │
└─────────────────────────────────────────────────────────────────────────────┘

STEP A - KEYWORD EXTRACTION (15 keywords):
┌─────────────────────────────────────────────────────────────────────────────┐
│ ACTIONS:   execute(0.85), authenticate(0.85), bypass(0.85)                 │
│ TARGETS:   account(0.80), privilege(0.80), credential(0.80), token(0.80)  │
│ TOOLS:     malware(0.90)                                                   │
│ CREDENTIALS: token(0.88), credential(0.88)                                 │
└─────────────────────────────────────────────────────────────────────────────┘

STEP B - TTP MAPPING (4 TTPs):
┌─────────────────────────────────────────────────────────────────────────────┐
│ T15498: Valid Accounts - Password-based Authentication                     │
│   → Tactic: Initial Access                                                 │
│ T1547.006: Boot or Logon Initialization Scripts                            │
│   → Tactic: Persistence                                                    │
│ T1563.002: Remote Service Session Hijacking                                │
│   → Tactic: Lateral Movement                                               │
│ T1187: Forced Authentication                                               │
│   → Tactic: Credential Access                                              │
└─────────────────────────────────────────────────────────────────────────────┘

STEP C - PRE-CONDITIONS (Root Causes):
┌─────────────────────────────────────────────────────────────────────────────┐
│ [0.88] ★ Elevated privileges obtained                                       │
│ [0.86] ★ Valid user account exists                                          │
│ [0.76]   Authentication service is accessible                               │
│ [0.76]   No rate limiting on login attempts                                 │
│ [0.76]   Default credentials not changed                                    │
│ [0.76]   Access to initialization scripts location                          │
└─────────────────────────────────────────────────────────────────────────────┘

STEP C - POST-CONDITIONS (Blast Radius):
┌─────────────────────────────────────────────────────────────────────────────┐
│ [0.90] ★ User account compromised                                           │
│ [0.89] ★ Access server achieved                                             │
│ [0.87]   Session hijacked successfully                                      │
│ [0.86]   Persistent backdoor established                                    │
│ [0.85]   Malware deployed on system                                         │
│ [0.77]   User privilege level obtained                                      │
└─────────────────────────────────────────────────────────────────────────────┘

STEP D - CAUSAL CONNECTIONS:
┌─────────────────────────────────────────────────────────────────────────────┐
│ CHAIN 1:  PRE: "Elevated privileges obtained"                               │
│             ↓ [T1547.006 - Boot Initialization]                             │
│           POST: "Persistent backdoor established"                           │
│           Confidence: Pre(0.88) Post(0.86) = VERY STRONG                    │
│                                                                              │
│ CHAIN 2:  PRE: "Valid user account exists"                                  │
│             ↓ [T15498 - Valid Accounts]                                     │
│           POST: "User account compromised"                                  │
│           Confidence: Pre(0.86) Post(0.90) = VERY STRONG                    │
│                                                                              │
│ CHAIN 3:  PRE: "Authentication service is accessible"                       │
│             ↓ [T1187 - Forced Authentication]                               │
│           POST: "User authentication attempt recorded"                      │
│           Confidence: Pre(0.76) Post(0.77) = STRONG                         │
└─────────────────────────────────────────────────────────────────────────────┘

KEY FINDING: Account compromise was enabled by existing elevated privileges
             and exploitation of initialization scripts for persistence.
             → REMEDIATION: Enforce least privilege + script monitoring


═════════════════════════════════════════════════════════════════════════════════
STATISTICAL SUMMARY (From Experimental Run)
═════════════════════════════════════════════════════════════════════════════════

Dataset: 5 breach incidents analyzed

Step A - Keyword Extraction:
  • 11.6 keywords per breach (range: 9-15)
  • Confidence: 0.843 average
  • Classification: 4 categories (action, target, tool, credential)

Step B - TTP Mapping:
  • 3.4 TTPs per breach (100% coverage)
  • Most common: T15498 (4x), T1563.002 (4x), T1547.006 (4x)
  • Compression ratio: 3.4x (12 keywords → 3.4 TTPs)

Step C - Condition Identification:
  • 11.0 pre-conditions per breach (confidence: 77.5%)
  • 10.2 post-conditions per breach (confidence: 81.5%)
  • Total: 106 conditions identified

Step D - Causal Connections:
  • 3.4 connections per breach
  • 17 total causal chains identified
  • Attack propagation paths: Fully mapped


═════════════════════════════════════════════════════════════════════════════════
USE CASES FOR SOC ANALYSTS
═════════════════════════════════════════════════════════════════════════════════

1. INCIDENT TRIAGE
   └─ Quickly identify "what failed" (pre-conditions) 
      and "what's exposed" (post-conditions)

2. ROOT CAUSE ANALYSIS
   └─ Automated identification of prerequisite conditions
      that allowed breach to occur

3. IMPACT ASSESSMENT
   └─ Understand blast radius through post-condition analysis
      (what can attacker do next?)

4. CONTROL VALIDATION
   └─ Map pre-conditions to security controls
      (which controls failed?)

5. THREAT HUNTING
   └─ Use post-conditions to guide detection signatures
      (what artifacts to look for?)

6. REMEDIATION PRIORITIZATION
   └─ Rank pre-conditions by criticality for fix priority


═════════════════════════════════════════════════════════════════════════════════
FILES REFERENCE
═════════════════════════════════════════════════════════════════════════════════

Core Implementation:
  ✓ security_breach_analysis.py      (380 lines) - Pipeline implementation
  ✓ generate_demo_data.py            (260 lines) - Demo data generator
  ✓ experimental_results.py          (380 lines) - Analysis & reporting

Generated Files:
  ✓ demo_breaches.json               (20 synthetic incidents)
  ✓ experimental_results.json        (Analysis results & statistics)

Documentation:
  ✓ ANALYSIS_DOCUMENTATION.md        (Full methodology + results)
  ✓ QUICKSTART_GUIDE.txt             (This file)


═════════════════════════════════════════════════════════════════════════════════
NEXT STEPS
═════════════════════════════════════════════════════════════════════════════════

1. Run generate_demo_data.py to create sample data
2. Run experimental_results.py to execute analysis
3. Review ANALYSIS_DOCUMENTATION.md for methodology details
4. Examine demo_breaches.json and experimental_results.json outputs
5. Customize TTP database and conditions for your organization
6. Integrate into your SOC automation/SOAR platform


Questions? Refer to ANALYSIS_DOCUMENTATION.md for complete details.
═════════════════════════════════════════════════════════════════════════════════
"""

if __name__ == "__main__":
    print(QUICK_START)
    
    # Save to file
    with open("/home/ubuntu/QUICKSTART_GUIDE.txt", "w") as f:
        f.write(QUICK_START)
    
    print("\n✓ Quick Start Guide saved to: /home/ubuntu/QUICKSTART_GUIDE.txt")
