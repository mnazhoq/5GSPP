"""
Security Control Breach Analysis Tool
Implements Step 2: Semi-Automatic Identification of Pre- and Post-Conditions

Methodology:
(a) Extract Keywords from breached control using NLP
(b) Find TTP (Techniques, Tactics, Procedures) mappings
(c) Identify Pre-conditions (Cause) and Post-conditions (Effect)
(d) Rank and connect conditions
"""

import re
from collections import defaultdict
from typing import List, Dict, Tuple, Set
from dataclasses import dataclass
import json


@dataclass
class Keyword:
    """Represents an extracted keyword with its type"""
    term: str
    keyword_type: str  # e.g., "action", "target", "tool", "credential"
    confidence: float


@dataclass
class TTP:
    """Represents a Technique, Tactic, Procedure"""
    ttp_id: str
    name: str
    description: str
    tactic: str
    technique: str
    mitigations: List[str]


@dataclass
class Condition:
    """Represents a pre or post-condition"""
    condition_id: str
    description: str
    condition_type: str  # "pre" or "post"
    related_ttps: List[str]
    confidence: float


class KeywordExtractor:
    """(a) Extracting Keywords from breached control"""
    
    def __init__(self):
        # Define keyword patterns for NLP-like extraction
        self.action_keywords = {
            'execute', 'deploy', 'inject', 'escalate', 'bypass', 'compromise',
            'intercept', 'exfiltrate', 'authenticate', 'access', 'enumerate',
            'reconnaissance', 'lateral-move', 'persistence', 'command', 'shell'
        }
        
        self.target_keywords = {
            'server', 'user', 'account', 'credential', 'token', 'privilege',
            'network', 'firewall', 'authentication', 'database', 'endpoint',
            'domain', 'resource', 'system', 'agent', 'monitoring'
        }
        
        self.tool_keywords = {
            'malware', 'exploit', 'reverse-shell', 'agent', 'trojan',
            'ransomware', 'worm', 'backdoor', 'rootkit', 'sniffer'
        }
        
        self.credential_keywords = {
            'password', 'token', 'credential', 'api-key', 'secret', 'key',
            'authentication', 'session', 'cookie', 'certificate'
        }
    
    def extract_keywords(self, control_breach_description: str) -> List[Keyword]:
        """Extract and classify keywords from breach description"""
        text = control_breach_description.lower()
        keywords = []
        
        # Extract action keywords
        for keyword in self.action_keywords:
            if keyword in text:
                keywords.append(Keyword(
                    term=keyword,
                    keyword_type="action",
                    confidence=0.85
                ))
        
        # Extract target keywords
        for keyword in self.target_keywords:
            if keyword in text:
                keywords.append(Keyword(
                    term=keyword,
                    keyword_type="target",
                    confidence=0.80
                ))
        
        # Extract tool keywords
        for keyword in self.tool_keywords:
            if keyword in text:
                keywords.append(Keyword(
                    term=keyword,
                    keyword_type="tool",
                    confidence=0.90
                ))
        
        # Extract credential keywords
        for keyword in self.credential_keywords:
            if keyword in text:
                keywords.append(Keyword(
                    term=keyword,
                    keyword_type="credential",
                    confidence=0.88
                ))
        
        return keywords


class TTPMapper:
    """(b) Finding TTP (using Keywords) - Maps keywords to MITRE ATT&CK TTPs"""
    
    def __init__(self):
        # Simulated MITRE ATT&CK TTP database
        self.ttp_database = self._initialize_ttp_database()
        self.keyword_to_ttp_mapping = self._initialize_keyword_mapping()
    
    def _initialize_ttp_database(self) -> Dict[str, TTP]:
        """Initialize simulated MITRE ATT&CK TTP database"""
        return {
            "T15498": TTP(
                ttp_id="T15498",
                name="Valid Accounts - Password-based Authentication",
                description="Authentication bypass using password-based methods",
                tactic="Initial Access",
                technique="Valid Accounts",
                mitigations=["M1015: Authentication", "M1013: Application Developer Guidance"]
            ),
            "T1547.006": TTP(
                ttp_id="T1547.006",
                name="Boot or Logon Initialization Scripts",
                description="Execute code at startup for persistence",
                tactic="Persistence",
                technique="Boot or Logon Initialization Scripts",
                mitigations=["M1038: Execution Prevention", "M1028: Operating System Configuration"]
            ),
            "T1187": TTP(
                ttp_id="T1187",
                name="Forced Authentication",
                description="Force user authentication attempts",
                tactic="Credential Access",
                technique="Forced Authentication",
                mitigations=["M1015: Authentication"]
            ),
            "T1563.002": TTP(
                ttp_id="T1563.002",
                name="Remote Service Session Hijacking",
                description="Take over established sessions",
                tactic="Lateral Movement",
                technique="Remote Service Session Hijacking",
                mitigations=["M1015: Authentication", "M1030: Network Segmentation"]
            ),
            "T1530": TTP(
                ttp_id="T1530",
                name="Data from Cloud Storage",
                description="Exfiltrate data from cloud storage",
                tactic="Exfiltration",
                technique="Data from Cloud Storage",
                mitigations=["M1047: Audit"]
            ),
            "T1083": TTP(
                ttp_id="T1083",
                name="File and Directory Discovery",
                description="Enumerate files and directories",
                tactic="Discovery",
                technique="File and Directory Discovery",
                mitigations=["M1028: Operating System Configuration"]
            ),
            "T1095": TTP(
                ttp_id="T1095",
                name="Non-Application Layer Protocol",
                description="Communicate using non-standard protocols",
                tactic="Command and Control",
                technique="Non-Application Layer Protocol",
                mitigations=["M1030: Network Segmentation", "M1048: Exfiltration Over Alternative Protocol"]
            ),
        }
    
    def _initialize_keyword_mapping(self) -> Dict[str, List[str]]:
        """Map keywords to TTP IDs"""
        return {
            "authentication": ["T15498", "T1187"],
            "password": ["T15498"],
            "bypass": ["T15498"],
            "persistence": ["T1547.006"],
            "credential": ["T1187", "T15498"],
            "token": ["T1563.002"],
            "session": ["T1563.002"],
            "exfiltrate": ["T1530"],
            "deployment": ["T1547.006"],
            "execute": ["T1547.006"],
            "enumerate": ["T1083"],
            "reconnaissance": ["T1083"],
            "command": ["T1095"],
            "lateral-move": ["T1563.002"],
        }
    
    def map_keywords_to_ttps(self, keywords: List[Keyword]) -> List[TTP]:
        """Map extracted keywords to TTPs"""
        ttp_ids = set()
        
        for keyword in keywords:
            if keyword.term in self.keyword_to_ttp_mapping:
                ttp_ids.update(self.keyword_to_ttp_mapping[keyword.term])
        
        ttps = []
        for ttp_id in ttp_ids:
            if ttp_id in self.ttp_database:
                ttps.append(self.ttp_database[ttp_id])
        
        return ttps


class CauseEffectAnalyzer:
    """(c) Identifying Pre (Cause) and Post (Effect) Conditions"""
    
    def __init__(self):
        self.ttp_to_preconditions = self._initialize_preconditions()
        self.ttp_to_postconditions = self._initialize_postconditions()
    
    def _initialize_preconditions(self) -> Dict[str, List[str]]:
        """Map TTPs to their pre-conditions (what must be true before)"""
        return {
            "T15498": [
                "Valid user account exists",
                "Authentication service is accessible",
                "No rate limiting on login attempts",
                "Default credentials not changed"
            ],
            "T1547.006": [
                "Elevated privileges obtained",
                "Access to initialization scripts location",
                "Persistence mechanism not monitored"
            ],
            "T1187": [
                "Attacker can send network traffic",
                "Target requires authentication for service access",
                "No authentication protocol hardening in place"
            ],
            "T1563.002": [
                "Established session to remote service exists",
                "Session tokens accessible or predictable",
                "Session re-authentication not enforced"
            ],
            "T1530": [
                "Cloud storage credentials obtained",
                "Network access to cloud services",
                "Insufficient access controls on buckets/containers"
            ],
            "T1083": [
                "System access obtained",
                "File system permissions allow browsing",
                "Discovery tools not restricted"
            ],
            "T1095": [
                "Network access available",
                "Firewall allows non-standard protocols",
                "Network monitoring gaps exist"
            ],
        }
    
    def _initialize_postconditions(self) -> Dict[str, List[str]]:
        """Map TTPs to their post-conditions (what results after)"""
        return {
            "T15498": [
                "User account compromised",
                "Access server achieved",
                "User privilege level obtained"
            ],
            "T1547.006": [
                "Malware deployed on system",
                "Persistent backdoor established",
                "System boots with attacker code"
            ],
            "T1187": [
                "Valid credentials captured",
                "User authentication attempt recorded",
                "Access to user account potential"
            ],
            "T1563.002": [
                "Session hijacked successfully",
                "Attacker controls remote session",
                "Data exfiltration possible"
            ],
            "T1530": [
                "Sensitive data exfiltrated",
                "Cloud storage contents compromised",
                "Data breach incident recorded"
            ],
            "T1083": [
                "File and directory structure known",
                "Sensitive data locations identified",
                "Next-stage attack vectors identified"
            ],
            "T1095": [
                "Command and control channel established",
                "Agent-based monitoring bypassed",
                "Protocol-based detection evaded"
            ],
        }
    
    def identify_conditions(self, ttps: List[TTP]) -> Tuple[List[Condition], List[Condition]]:
        """Identify pre and post-conditions from TTPs"""
        preconditions = []
        postconditions = []
        
        for idx, ttp in enumerate(ttps):
            # Extract pre-conditions
            if ttp.ttp_id in self.ttp_to_preconditions:
                for pre_desc in self.ttp_to_preconditions[ttp.ttp_id]:
                    preconditions.append(Condition(
                        condition_id=f"PRE_{ttp.ttp_id}_{idx}",
                        description=pre_desc,
                        condition_type="pre",
                        related_ttps=[ttp.ttp_id],
                        confidence=0.82
                    ))
            
            # Extract post-conditions
            if ttp.ttp_id in self.ttp_to_postconditions:
                for post_desc in self.ttp_to_postconditions[ttp.ttp_id]:
                    postconditions.append(Condition(
                        condition_id=f"POST_{ttp.ttp_id}_{idx}",
                        description=post_desc,
                        condition_type="post",
                        related_ttps=[ttp.ttp_id],
                        confidence=0.85
                    ))
        
        return preconditions, postconditions


class ConditionRanker:
    """(d) Ranking and Connecting Conditions"""
    
    def __init__(self):
        self.condition_criticality = self._initialize_criticality()
    
    def _initialize_criticality(self) -> Dict[str, float]:
        """Criticality scores for conditions (1.0 = most critical)"""
        return {
            "User account compromised": 0.95,
            "Valid user account exists": 0.90,
            "Access server achieved": 0.92,
            "Elevated privileges obtained": 0.93,
            "Persistent backdoor established": 0.88,
            "Sensitive data exfiltrated": 0.96,
            "Session hijacked successfully": 0.89,
            "Cloud storage credentials obtained": 0.91,
            "Command and control channel established": 0.87,
            "Malware deployed on system": 0.85,
        }
    
    def rank_conditions(self, conditions: List[Condition]) -> List[Condition]:
        """Rank conditions by criticality and confidence"""
        ranked = []
        
        for condition in conditions:
            # Boost confidence based on criticality
            criticality = self.condition_criticality.get(
                condition.description, 0.70
            )
            condition.confidence = (condition.confidence + criticality) / 2
            ranked.append(condition)
        
        # Sort by confidence descending
        ranked.sort(key=lambda x: x.confidence, reverse=True)
        return ranked
    
    def connect_conditions(self, preconditions: List[Condition], 
                          postconditions: List[Condition]) -> Dict:
        """Connect pre and post-conditions by related TTPs"""
        connections = defaultdict(list)
        
        for pre in preconditions:
            for post in postconditions:
                # Connect if they share related TTPs
                if set(pre.related_ttps) & set(post.related_ttps):
                    connections[pre.condition_id].append({
                        'pre_condition': pre.description,
                        'post_condition': post.description,
                        'pre_confidence': pre.confidence,
                        'post_confidence': post.confidence,
                        'shared_ttps': list(set(pre.related_ttps) & set(post.related_ttps))
                    })
        
        return connections


class SecurityBreachAnalyzer:
    """Main orchestrator for the analysis pipeline"""
    
    def __init__(self):
        self.keyword_extractor = KeywordExtractor()
        self.ttp_mapper = TTPMapper()
        self.cause_effect_analyzer = CauseEffectAnalyzer()
        self.condition_ranker = ConditionRanker()
    
    def analyze_breach(self, control_breach_description: str) -> Dict:
        """Execute the full 4-step methodology"""
        
        # Step (a): Extract Keywords
        keywords = self.keyword_extractor.extract_keywords(control_breach_description)
        
        # Step (b): Find TTPs
        ttps = self.ttp_mapper.map_keywords_to_ttps(keywords)
        
        # Step (c): Identify Conditions
        preconditions, postconditions = self.cause_effect_analyzer.identify_conditions(ttps)
        
        # Step (d): Rank and Connect Conditions
        ranked_pre = self.condition_ranker.rank_conditions(preconditions)
        ranked_post = self.condition_ranker.rank_conditions(postconditions)
        connections = self.condition_ranker.connect_conditions(ranked_pre, ranked_post)
        
        return {
            'control_breach': control_breach_description,
            'step_a_keywords': [
                {
                    'term': k.term,
                    'type': k.keyword_type,
                    'confidence': k.confidence
                } for k in keywords
            ],
            'step_b_ttps': [
                {
                    'ttp_id': t.ttp_id,
                    'name': t.name,
                    'tactic': t.tactic,
                    'technique': t.technique
                } for t in ttps
            ],
            'step_c_preconditions': [
                {
                    'id': pc.condition_id,
                    'description': pc.description,
                    'confidence': pc.confidence,
                    'related_ttps': pc.related_ttps
                } for pc in ranked_pre
            ],
            'step_c_postconditions': [
                {
                    'id': pc.condition_id,
                    'description': pc.description,
                    'confidence': pc.confidence,
                    'related_ttps': pc.related_ttps
                } for pc in ranked_post
            ],
            'step_d_connections': {
                k: v for k, v in connections.items()
            }
        }


if __name__ == "__main__":
    # Example usage will be in the separate demo script
    pass
