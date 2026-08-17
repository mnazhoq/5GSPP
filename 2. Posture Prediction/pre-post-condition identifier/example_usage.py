"""
Example Usage - Complete End-to-End Scenario
Demonstrates how to use the Security Breach Analysis as a library
"""

from security_breach_analysis import SecurityBreachAnalyzer
import json


def example_1_single_breach_analysis():
    """Example 1: Analyze a single breach description"""
    print("\n" + "="*80)
    print("EXAMPLE 1: Single Breach Analysis")
    print("="*80)
    
    analyzer = SecurityBreachAnalyzer()
    
    # Real-world breach description
    breach_text = """
    Attacker gained initial access through credential phishing and valid account.
    After authentication, privilege was escalated through kernel exploit.
    Malware was deployed with persistence through scheduled task.
    Agent-based monitoring was disabled. Lateral movement executed across
    network via SMB exploitation. Command and control channel established
    through reverse shell. Sensitive data exfiltrated to external server.
    """
    
    print("\nBreach Description:")
    print(f"  {breach_text.strip()}\n")
    
    # Run analysis
    result = analyzer.analyze_breach(breach_text)
    
    # Display results
    print("STEP A - KEYWORDS EXTRACTED:")
    for keyword in result['step_a_keywords'][:8]:
        print(f"  • {keyword['term'].upper()} (type: {keyword['type']}, confidence: {keyword['confidence']:.2f})")
    
    print("\nSTEP B - TTPs MAPPED:")
    for ttp in result['step_b_ttps'][:4]:
        print(f"  • {ttp['ttp_id']}: {ttp['name']}")
    
    print("\nSTEP C - TOP PRE-CONDITIONS (Root Causes):")
    for pre in result['step_c_preconditions'][:4]:
        print(f"  • [{pre['confidence']:.2f}] {pre['description']}")
    
    print("\nSTEP C - TOP POST-CONDITIONS (Blast Radius):")
    for post in result['step_c_postconditions'][:4]:
        print(f"  • [{post['confidence']:.2f}] {post['description']}")


def example_2_attack_chain_analysis():
    """Example 2: Extract and analyze attack chains"""
    print("\n" + "="*80)
    print("EXAMPLE 2: Attack Chain Analysis")
    print("="*80)
    
    analyzer = SecurityBreachAnalyzer()
    
    breach_text = """
    Session hijacking attack via stolen token led to remote access.
    Attacker deployed agent for command execution and reconnaissance.
    Further lateral movement using valid administrator credentials.
    """
    
    print("\nBreach Description:")
    print(f"  {breach_text.strip()}\n")
    
    result = analyzer.analyze_breach(breach_text)
    
    print("ATTACK CHAIN ANALYSIS:")
    print("  Pre-condition → Post-condition sequences:\n")
    
    chain_num = 1
    for pre_id, connections in result['step_d_connections'].items():
        for conn in connections[:2]:  # Show top 2
            print(f"  Chain {chain_num}:")
            print(f"    START: {conn['pre_condition']}")
            print(f"           (confidence: {conn['pre_confidence']:.2f})")
            print(f"    ↓ TTPs: {', '.join(conn['shared_ttps'])}")
            print(f"    END:   {conn['post_condition']}")
            print(f"           (confidence: {conn['post_confidence']:.2f})")
            print()
            chain_num += 1


def example_3_batch_processing():
    """Example 3: Batch process multiple breaches"""
    print("\n" + "="*80)
    print("EXAMPLE 3: Batch Processing Multiple Breaches")
    print("="*80)
    
    analyzer = SecurityBreachAnalyzer()
    
    breaches = [
        {
            'id': 'B001',
            'description': 'Password brute-force attack compromised user account'
        },
        {
            'id': 'B002',
            'description': 'Malware deployment through infected email attachment'
        },
        {
            'id': 'B003',
            'description': 'Remote SSH vulnerability exploited for shell access'
        }
    ]
    
    print(f"\nProcessing {len(breaches)} breaches...\n")
    
    results_summary = []
    
    for breach in breaches:
        result = analyzer.analyze_breach(breach['description'])
        
        summary = {
            'breach_id': breach['id'],
            'keywords_count': len(result['step_a_keywords']),
            'ttps_count': len(result['step_b_ttps']),
            'preconditions_count': len(result['step_c_preconditions']),
            'postconditions_count': len(result['step_c_postconditions']),
            'connections_count': len(result['step_d_connections']),
            'avg_pre_confidence': sum(p['confidence'] for p in result['step_c_preconditions']) / len(result['step_c_preconditions']) if result['step_c_preconditions'] else 0,
            'avg_post_confidence': sum(p['confidence'] for p in result['step_c_postconditions']) / len(result['step_c_postconditions']) if result['step_c_postconditions'] else 0,
        }
        results_summary.append(summary)
        
        print(f"  {breach['id']}: {len(result['step_a_keywords'])} keywords → {len(result['step_b_ttps'])} TTPs → {len(result['step_c_preconditions']) + len(result['step_c_postconditions'])} conditions")
    
    print("\nSUMMARY TABLE:")
    print("  ID    | Keywords | TTPs | Pre | Post | Connections")
    print("  " + "-"*50)
    for s in results_summary:
        print(f"  {s['breach_id']} | {s['keywords_count']:^8} | {s['ttps_count']:^4} | {s['preconditions_count']:^3} | {s['postconditions_count']:^4} | {s['connections_count']:^11}")


def example_4_json_export():
    """Example 4: Export results to JSON for downstream processing"""
    print("\n" + "="*80)
    print("EXAMPLE 4: JSON Export for Integration")
    print("="*80)
    
    analyzer = SecurityBreachAnalyzer()
    
    breach_text = "Unauthorized admin access through valid credential compromise"
    result = analyzer.analyze_breach(breach_text)
    
    # Create exportable format
    export_result = {
        'metadata': {
            'breach_description': breach_text,
            'analysis_version': '1.0',
        },
        'analysis': {
            'step_a_keywords': result['step_a_keywords'],
            'step_b_ttps': result['step_b_ttps'],
            'step_c_conditions': {
                'preconditions': result['step_c_preconditions'][:3],
                'postconditions': result['step_c_postconditions'][:3],
            },
            'step_d_chains': {k: v[:1] for k, v in result['step_d_connections'].items()}  # Top 1 per pre
        }
    }
    
    print("\nJSON Export Sample (for SOAR/downstream systems):")
    print(json.dumps(export_result, indent=2)[:1000] + "...")
    
    # Save to file
    with open('/tmp/example_export.json', 'w') as f:
        json.dump(export_result, f, indent=2)
    
    print("\n✓ Full export saved to: /tmp/example_export.json")


def example_5_analyst_workflow():
    """Example 5: Incident Response Analyst Workflow"""
    print("\n" + "="*80)
    print("EXAMPLE 5: SOC Analyst Incident Response Workflow")
    print("="*80)
    
    analyzer = SecurityBreachAnalyzer()
    
    # Step 1: Triage
    incident_log = """
    Alert triggered: Suspicious process execution detected on SERVER-25.
    Investigation revealed: WinRM service used to execute PowerShell script
    loading malware payload. Known C2 domain contacted. Administrator
    account used for lateral movement.
    """
    
    print("\n[STEP 1] INCIDENT TRIAGE")
    print("Log Entry:")
    print(f"  {incident_log.strip()}\n")
    
    result = analyzer.analyze_breach(incident_log)
    
    # Step 2: Identify root causes
    print("[STEP 2] ROOT CAUSE ANALYSIS")
    preconditions = sorted(result['step_c_preconditions'], key=lambda x: x['confidence'], reverse=True)
    print("  Top root causes (what went wrong?):")
    for pre in preconditions[:3]:
        print(f"    • {pre['description']} (confidence: {pre['confidence']:.1%})")
    
    # Step 3: Identify blast radius
    print("\n[STEP 3] BLAST RADIUS ASSESSMENT")
    postconditions = sorted(result['step_c_postconditions'], key=lambda x: x['confidence'], reverse=True)
    print("  Top impacts (what's exposed?):")
    for post in postconditions[:3]:
        print(f"    • {post['description']} (confidence: {post['confidence']:.1%})")
    
    # Step 4: Hunting checklist
    print("\n[STEP 4] THREAT HUNTING CHECKLIST")
    print("  Look for evidence of:")
    for post in postconditions[:4]:
        print(f"    ☐ {post['description']}")
    
    # Step 5: Remediation
    print("\n[STEP 5] REMEDIATION PRIORITIES")
    print("  Fix these conditions (in order):")
    for idx, pre in enumerate(preconditions[:4], 1):
        print(f"    {idx}. Ensure: {pre['description']}")


def example_6_custom_keyword_analysis():
    """Example 6: Using analyzer with custom keyword extraction"""
    print("\n" + "="*80)
    print("EXAMPLE 6: Custom Keyword Analysis")
    print("="*80)
    
    analyzer = SecurityBreachAnalyzer()
    
    # Analyze with focus on extracting specific threat indicators
    breach_text = "Ransomware deployed through phishing email attachment"
    
    print("\nTarget: Identify ransomware indicators\n")
    
    result = analyzer.analyze_breach(breach_text)
    
    # Filter for tools
    tools = [k for k in result['step_a_keywords'] if k['type'] == 'tool']
    actions = [k for k in result['step_a_keywords'] if k['type'] == 'action']
    
    print(f"Tools identified: {[t['term'] for t in tools]}")
    print(f"Actions identified: {[a['term'] for a in actions]}")
    
    # Show related TTPs
    print("\nRelated TTPs:")
    for ttp in result['step_b_ttps']:
        print(f"  • {ttp['name']} ({ttp['tactic']})")


if __name__ == "__main__":
    print("\n" + "#"*80)
    print("# SECURITY BREACH ANALYSIS - USAGE EXAMPLES")
    print("# Demonstrating the SecurityBreachAnalyzer library")
    print("#"*80)
    
    # Run all examples
    example_1_single_breach_analysis()
    example_2_attack_chain_analysis()
    example_3_batch_processing()
    example_4_json_export()
    example_5_analyst_workflow()
    example_6_custom_keyword_analysis()
    
    print("\n" + "#"*80)
    print("# All examples completed successfully!")
    print("#"*80)
    print("\nUse these patterns as templates for your own breach analysis workflows.")
