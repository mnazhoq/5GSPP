"""
Generate Demo Data for Security Breach Analysis
Creates realistic breach scenarios based on the Bayesian network from the first image
"""

import json
from typing import List, Dict
import random


class DemoBreach:
    """Represents a demo security control breach"""
    
    def __init__(self, breach_id: str, control_name: str, description: str, 
                 severity: str, breach_type: str):
        self.breach_id = breach_id
        self.control_name = control_name
        self.description = description
        self.severity = severity
        self.breach_type = breach_type


def generate_demo_breaches() -> List[DemoBreach]:
    """
    Generate demo data based on the attack flow from the first image.
    Maps to non-compliant states: LogOn PB, Remote Access PB, Configuration PB,
    Agent-based Monitoring PB, Protocol-based Monitoring PB
    """
    
    breaches = [
        # ===== AC-6: Least Privilege Control Bypasses =====
        DemoBreach(
            breach_id="AC-6-001",
            control_name="AC-6 (Least Privilege)",
            description="Attacker executed bypass user account control through deploying malware that escalated privileges. "
                       "Credential token was used to access server and authenticate without proper elevation checks.",
            severity="CRITICAL",
            breach_type="Privilege Escalation"
        ),
        
        # ===== LogOn PB: Password-based Authentication Failures =====
        DemoBreach(
            breach_id="LogOn-PB-001",
            control_name="SI-2 (Information System Monitoring) - LogOn PB",
            description="Password-based authentication was bypassed through forced authentication attack. "
                       "Input credentials were captured, and attacker executed lateral movement using valid accounts. "
                       "Access server was compromised without enforcement of consecutive invalid logon.",
            severity="CRITICAL",
            breach_type="Authentication Bypass"
        ),
        
        DemoBreach(
            breach_id="LogOn-PB-002",
            control_name="SI-2 (Information System Monitoring) - LogOn PB",
            description="Attack involved password spraying against authentication service to compromise user account. "
                       "Malware was deployed on access server after credential token was obtained through token impersonation.",
            severity="HIGH",
            breach_type="Password Attack"
        ),
        
        # ===== Remote Access PB: Remote SSH Attack Vector =====
        DemoBreach(
            breach_id="RemoteAccess-PB-001",
            control_name="AC-3 (Access Enforcement) - Remote Access PB",
            description="Remote SSH attack bypassed access control through session hijacking. "
                       "Attacker executed command and lateral movement by creating GTP tunnel and establishing persistence. "
                       "Agent-based monitoring was evaded through protocol-based C2 communication.",
            severity="CRITICAL",
            breach_type="Remote Access Attack"
        ),
        
        DemoBreach(
            breach_id="RemoteAccess-PB-002",
            control_name="AC-3 (Access Enforcement) - Remote Access PB",
            description="Remote SSH compromise allowed attacker to execute reconnaissance and enumerate system resources. "
                       "Session hijacking led to deployment of persistent backdoor and creation of GTP tunnel for data exfiltration.",
            severity="HIGH",
            breach_type="Lateral Movement"
        ),
        
        # ===== Configuration PB: Malware Deployment & Persistence =====
        DemoBreach(
            breach_id="Config-PB-001",
            control_name="CM-2 (Baseline Configuration) - Configuration PB",
            description="Malware deployment achieved persistence through boot initialization script injection. "
                       "Configuration was modified to execute malware on system startup without detection. "
                       "Attacker then established command and control channel through non-application layer protocol.",
            severity="CRITICAL",
            breach_type="Malware Persistence"
        ),
        
        DemoBreach(
            breach_id="Config-PB-002",
            control_name="CM-2 (Baseline Configuration) - Configuration PB",
            description="Token impersonation attack followed by malware deployment changed system configuration. "
                       "Trojan was installed to enable persistent remote access and enable portability of execution environment.",
            severity="HIGH",
            breach_type="System Compromise"
        ),
        
        # ===== Agent-based Monitoring PB: Monitoring Evasion =====
        DemoBreach(
            breach_id="AgentMonitor-PB-001",
            control_name="SI-4 (Information System Monitoring) - Agent-based Monitoring PB",
            description="Agent-based monitoring was compromised through execution of rootkit malware. "
                       "Launch agent was deployed to disable endpoint monitoring and create blind spots. "
                       "Attacker gained portable execution capability to move laterally without detection.",
            severity="CRITICAL",
            breach_type="Monitoring Evasion"
        ),
        
        DemoBreach(
            breach_id="AgentMonitor-PB-002",
            control_name="SI-4 (Information System Monitoring) - Agent-based Monitoring PB",
            description="Agent-based monitoring evasion allowed attacker to execute file and directory discovery. "
                       "Backdoor installation created persistent channel bypassing agent-based security controls.",
            severity="HIGH",
            breach_type="Discovery & Evasion"
        ),
        
        # ===== Protocol-based Monitoring PB: C2 Communication =====
        DemoBreach(
            breach_id="ProtocolMonitor-PB-001",
            control_name="SI-4 (Information System Monitoring) - Protocol-based Monitoring PB",
            description="Protocol-based monitoring was bypassed through non-application layer protocol communication. "
                       "Attacker established command and control server connection using TCP/IP tunneling. "
                       "Data exfiltration occurred through protocol-based C2 channel not detected by standard monitoring.",
            severity="CRITICAL",
            breach_type="C2 Communication"
        ),
        
        DemoBreach(
            breach_id="ProtocolMonitor-PB-002",
            control_name="SI-4 (Information System Monitoring) - Protocol-based Monitoring PB",
            description="Protocol-based monitoring evasion enabled attacker to communicate with C2 server. "
                       "Portable execution launched through GTP tunnel creation to exfiltrate sensitive data from DN (Data Node). "
                       "Exfiltration achieved without protocol-based detection.",
            severity="HIGH",
            breach_type="Data Exfiltration"
        ),
        
        # ===== Combined Goal Attacks =====
        DemoBreach(
            breach_id="Combined-Goal-001",
            control_name="Combined Security Goals",
            description="Multi-stage attack combined password-based authentication bypass, malware deployment, "
                       "and protocol-based monitoring evasion. Query to SMF executed after remote access compromise. "
                       "Final objective: exfiltrate sensitive data from system.",
            severity="CRITICAL",
            breach_type="Advanced Persistent Threat"
        ),
    ]
    
    return breaches


def generate_extended_demo_data(num_breaches: int = 20) -> List[Dict]:
    """Generate extended demo dataset with variations"""
    
    base_breaches = generate_demo_breaches()
    extended_data = []
    
    # Add base breaches
    for breach in base_breaches:
        extended_data.append({
            'breach_id': breach.breach_id,
            'control_name': breach.control_name,
            'description': breach.description,
            'severity': breach.severity,
            'breach_type': breach.breach_type,
            'timestamp': f"2025-{random.randint(1,12):02d}-{random.randint(1,28):02d} "
                        f"{random.randint(0,23):02d}:{random.randint(0,59):02d}:00"
        })
    
    # Generate additional variations for extended dataset
    additional_descriptions = [
        "Attacker obtained valid credentials through social engineering and executed lateral movement across network. "
        "Privilege escalation achieved after deploying agent-based remote access tool.",
        
        "Configuration management failure allowed deployment of unvetted malware. "
        "Attacker maintained persistence through initialization script injection and evaded monitoring.",
        
        "Authentication service was compromised enabling attacker to bypass account controls. "
        "Session token hijacking allowed creation of backdoor and tunneling for command execution.",
        
        "File and directory discovery led to identification of sensitive data storage. "
        "Attacker executed token impersonation to gain elevated credentials and initiate data exfiltration.",
        
        "Remote access vulnerability exploited through SSH brute force attack. "
        "Malware deployment established persistent C2 channel using non-standard protocols.",
        
        "Weak credential management enabled password spraying attack. "
        "Compromise of user account led to lateral movement and server access completion.",
        
        "Network segmentation failure allowed creation of GTP tunnel. "
        "Attacker established portable execution environment bypassing endpoint protection.",
        
        "Monitoring gap enabled attacker to deploy rootkit malware without detection. "
        "Protocol-based evasion established covert command and control channel.",
    ]
    
    control_names = [
        "AC-2 (Account Management)",
        "AC-3 (Access Enforcement)",
        "AC-6 (Least Privilege)",
        "CM-2 (Baseline Configuration)",
        "IA-2 (Authentication)",
        "IA-4 (Identifier Management)",
        "SI-2 (Information System Monitoring)",
        "SI-4 (Information System Monitoring)",
        "SC-7 (Boundary Protection)",
        "AU-2 (Audit Events)",
    ]
    
    # Add extended variations
    while len(extended_data) < num_breaches:
        extended_data.append({
            'breach_id': f"EXT-{len(extended_data):03d}",
            'control_name': random.choice(control_names),
            'description': random.choice(additional_descriptions),
            'severity': random.choice(['CRITICAL', 'HIGH', 'MEDIUM']),
            'breach_type': random.choice([
                'Privilege Escalation', 'Authentication Bypass', 'Password Attack',
                'Remote Access Attack', 'Lateral Movement', 'Malware Persistence',
                'System Compromise', 'Monitoring Evasion', 'Discovery & Evasion',
                'C2 Communication', 'Data Exfiltration', 'Advanced Persistent Threat'
            ]),
            'timestamp': f"2025-{random.randint(1,12):02d}-{random.randint(1,28):02d} "
                        f"{random.randint(0,23):02d}:{random.randint(0,59):02d}:00"
        })
    
    return extended_data


def save_demo_data(output_file: str = "/home/ubuntu/demo_breaches.json"):
    """Save demo data to JSON file"""
    demo_data = generate_extended_demo_data(num_breaches=20)
    
    with open(output_file, 'w') as f:
        json.dump(demo_data, f, indent=2)
    
    print(f"✓ Generated {len(demo_data)} demo breach records")
    print(f"✓ Saved to {output_file}")
    
    return demo_data


def print_sample_breaches(num_samples: int = 5):
    """Print sample breaches for verification"""
    breaches = generate_demo_breaches()[:num_samples]
    
    print("\n" + "="*80)
    print("SAMPLE DEMO BREACHES")
    print("="*80)
    
    for breach in breaches:
        print(f"\nBreach ID: {breach.breach_id}")
        print(f"Control: {breach.control_name}")
        print(f"Type: {breach.breach_type} | Severity: {breach.severity}")
        print(f"Description:\n  {breach.description}")


if __name__ == "__main__":
    print("Generating Demo Data for Security Breach Analysis")
    print("="*80)
    
    # Print samples
    print_sample_breaches()
    
    # Save to file
    demo_data = save_demo_data()
    
    print(f"\n✓ Demo data generation complete!")
