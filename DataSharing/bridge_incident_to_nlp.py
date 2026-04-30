"""
Bridge: Log Correlation Incident → NLP Pipeline
================================================

This module converts structured Incident objects (output from log correlation engine)
into free-form breach narratives suitable for NLP analysis.

The bridge is CRITICAL for connecting Issue 1 (Log Correlation) to Issue 3 (NLP).
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime
import json


@dataclass
class LogEvent:
    """Normalized log event (CEF format)"""
    ts: datetime
    source: str  # '5gnf', 'k8s', 'syslog', 'netflow'
    host: str
    severity: int  # [1-5]
    actor: str
    target: str
    action: str
    message: str
    session_key: Optional[tuple]
    txn_id: Optional[str]
    event_type: str
    label: str  # 'ATTACK' or 'NORMAL'
    corr_id: Optional[str] = None  # Correlation ID linking to incident


@dataclass
class Incident:
    """Correlated incident with metadata"""
    incident_id: str
    events: List[LogEvent]
    ts_start: datetime
    ts_end: datetime
    correlation_score: float
    rules_fired: List[str]  # ['R4', 'R5', ...]
    affected_systems: set  # {'AMF', 'UDM', 'SMF'}


def incident_to_breach_narrative(incident: Incident) -> str:
    """
    Convert structured Incident to natural language breach description.
    
    This is the CRITICAL BRIDGE function that enables:
        Incident (from Log Correlation) → NLP Pipeline → Posture Model
    
    Parameters
    ----------
    incident : Incident
        Correlated incident with attack events
        
    Returns
    -------
    str
        Natural language description of the attack suitable for NLP analysis
        
    Example
    -------
    >>> incident = create_test_incident([ssh_auth_event, nrf_register_event])
    >>> narrative = incident_to_breach_narrative(incident)
    >>> print(narrative)
    'Attack incident INC001 executed over 53 seconds targeting 5G core...'
    """
    
    # Extract attack events (filter out normal background noise)
    attack_events = [e for e in incident.events if e.label == "ATTACK"]
    
    if not attack_events:
        return f"Incident {incident.incident_id}: No attack events detected"
    
    # Build narrative
    narrative_parts = []
    
    # Header: Incident summary
    duration = (incident.ts_end - incident.ts_start).total_seconds()
    narrative_parts.append(
        f"Security incident {incident.incident_id} detected over {duration:.0f} seconds. "
        f"Correlation confidence: {incident.correlation_score:.1%}. "
    )
    
    # Attack progression
    narrative_parts.append("Attack progression:")
    
    for idx, event in enumerate(attack_events, 1):
        # Extract key event properties
        action = event.action or event.event_type
        actor = event.actor or "Unknown"
        target_text = f" targeting {event.target}" if event.target else ""
        
        # Determine source context
        source_context = {
            "5gnf": f"5G network function {actor}",
            "k8s": f"Kubernetes component '{actor}'",
            "syslog": f"System user {actor}",
            "netflow": f"Network flow from {actor}"
        }.get(event.source, f"{event.source}:{actor}")
        
        # Create event description
        event_desc = f"{idx}. {action} via {source_context}"
        if target_text:
            event_desc += target_text
        
        narrative_parts.append(event_desc)
    
    # Affected systems
    if incident.affected_systems:
        systems_text = ", ".join(sorted(incident.affected_systems))
        narrative_parts.append(f"Affected 5G systems: {systems_text}")
    
    # Impact assessment
    breach_controls = extract_breached_controls(attack_events)
    if breach_controls:
        controls_text = ", ".join(sorted(breach_controls))
        narrative_parts.append(f"Breached security controls: {controls_text}")
    
    # Correlation rules fired
    if incident.rules_fired:
        rules_text = ", ".join(incident.rules_fired)
        narrative_parts.append(
            f"Event correlation validated via rules: {rules_text}. "
            f"Temporal gaps bridged using causal dependencies."
        )
    
    # Severity assessment
    max_severity = max((e.severity for e in attack_events), default=2)
    severity_level = {
        5: "CRITICAL",
        4: "HIGH",
        3: "MEDIUM",
        2: "LOW",
        1: "INFO"
    }.get(max_severity, "UNKNOWN")
    
    narrative_parts.append(f"Severity assessment: {severity_level}")
    
    return "\n".join(narrative_parts)


def extract_breached_controls(events: List[LogEvent]) -> set:
    """
    Extract likely breached NIST controls from attack event sequence.
    
    Heuristic mapping (can be enhanced with external data):
    """
    
    breaches = set()
    event_types = {e.event_type for e in events}
    
    # Simple heuristic mappings
    mapping = {
        "ssh_auth": "AC-7",              # Logon Policy
        "nf_register": "AC-3",           # Access Enforcement
        "bypass_authentication": "AC-6", # Least Privilege
        "deploy_malware": "CM-7",        # Least Functionality
        "data_exfil": "SC-7",            # Boundary Protection
        "lateral_movement": "AC-3",      # Access Enforcement
    }
    
    for event_type in event_types:
        if event_type.lower() in mapping:
            breaches.add(mapping[event_type.lower()])
    
    return breaches


def get_incident_metadata_for_nlp(incident: Incident) -> Dict:
    """
    Extract structured metadata about incident for NLP context.
    
    Useful for multi-stage NLP pipelines that need context beyond narrative.
    """
    
    attack_events = [e for e in incident.events if e.label == "ATTACK"]
    
    # Extract event types for topic modeling
    event_topics = {}
    for event in attack_events:
        topic = categorize_event(event.event_type)
        event_topics[topic] = event_topics.get(topic, 0) + 1
    
    # Find primary attack path
    attack_sequence = [e.event_type for e in attack_events]
    
    return {
        "incident_id": incident.incident_id,
        "duration_seconds": (incident.ts_end - incident.ts_start).total_seconds(),
        "correlation_score": incident.correlation_score,
        "num_attack_events": len(attack_events),
        "affected_systems": sorted(incident.affected_systems),
        "event_types": attack_sequence,
        "event_topics": event_topics,
        "correlation_rules": incident.rules_fired,
        "severity": max((e.severity for e in attack_events), default=2),
    }


def categorize_event(event_type: str) -> str:
    """Map low-level event types to high-level attack categories."""
    
    event_lower = event_type.lower()
    
    if any(t in event_lower for t in ["auth", "logon", "login", "credential"]):
        return "authentication"
    elif any(t in event_lower for t in ["access", "privilege", "escalat"]):
        return "privilege_escalation"
    elif any(t in event_lower for t in ["move", "lateral", "traverse"]):
        return "lateral_movement"
    elif any(t in event_lower for t in ["deploy", "malware", "inject", "exec"]):
        return "malware_execution"
    elif any(t in event_lower for t in ["exfil", "steal", "extract", "copy"]):
        return "data_exfiltration"
    elif any(t in event_lower for t in ["connect", "c2", "command"]):
        return "command_and_control"
    else:
        return "other"


def incidents_to_nlp_batch(incidents: List[Incident]) -> List[Dict]:
    """
    Convert multiple incidents to NLP-ready batch.
    
    Useful for batch processing multiple incidents through NLP pipeline.
    """
    
    batch = []
    for incident in incidents:
        narrative = incident_to_breach_narrative(incident)
        metadata = get_incident_metadata_for_nlp(incident)
        
        batch.append({
            "incident_id": incident.incident_id,
            "narrative": narrative,
            "metadata": metadata,
        })
    
    return batch


if __name__ == "__main__":
    # Example usage
    print("Bridge module: Incident → Breach Narrative")
    print("This module is imported by the NLP pipeline")
    print("See docstrings for usage examples")
