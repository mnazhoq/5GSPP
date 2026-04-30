"""
Condition Normalization: NLP Output → Bayesian Model
======================================================

This module converts NLP-extracted conditions (MITRE TTPs, plain text descriptions)
to Bayesian network node names for posture evaluation.

The normalizer is CRITICAL for connecting Issue 3 (NLP) to Posture Evaluation.

Usage:
------
from normalize_conditions import ConditionNormalizer

normalizer = ConditionNormalizer(schema_path='CONDITION_SCHEMA.json')

# Convert NLP results
nlp_output = {
    'keywords': [
        {'term': 'escalate', 'type': 'action', 'confidence': 0.92},
        {'term': 'credential', 'type': 'credential', 'confidence': 0.88},
    ],
    'ttps': [
        {'ttp_id': 'T1134', 'name': 'Access Token Manipulation', 'confidence': 0.89}
    ]
}

# Normalize to model evidence
normalized = normalizer.normalize_nlp_output(nlp_output)
# {'Token_Impersonation': 0.89, 'Bypass_Authentication': 0.88, ...}

# Convert to discrete evidence for Bayesian model
evidence = normalizer.continuous_to_discrete_evidence(normalized, threshold=0.75)
# {'Token_Impersonation': 1, 'Bypass_Authentication': 1, ...}
"""

import json
import logging
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path
import re


logger = logging.getLogger(__name__)


class ConditionNormalizer:
    """Maps NLP-extracted conditions to Bayesian model nodes."""
    
    def __init__(self, schema_path: Optional[str] = None):
        """
        Initialize with condition mapping schema.
        
        Parameters
        ----------
        schema_path : str
            Path to CONDITION_SCHEMA.json
            If None, uses embedded default schema
        """
        self.schema = self._load_schema(schema_path)
        self._build_indexes()
    
    def _load_schema(self, schema_path: Optional[str]) -> Dict:
        """Load condition mapping schema from JSON file or use defaults."""
        
        if schema_path and Path(schema_path).exists():
            with open(schema_path) as f:
                return json.load(f)
        else:
            logger.warning("Schema file not found, using embedded defaults")
            return self._get_default_schema()
    
    def _get_default_schema(self) -> Dict:
        """Built-in default schema (matches CONDITION_SCHEMA.json)."""
        return {
            "mitre_techniques": {
                "T1134": {"name": "Access Token Manipulation", 
                         "posture_model_node": "Token_Impersonation"},
                "T1187": {"name": "Forced Authentication",
                         "posture_model_node": "Logon_PB"},
                # ... (truncated, see CONDITION_SCHEMA.json for full)
            },
            "plain_text_keywords": {
                "authentication": {
                    "posture_model_node": "Bypass_Authentication",
                    "keywords": ["password", "credential", "logon", "authentication"]
                },
                # ... (truncated)
            }
        }
    
    def _build_indexes(self):
        """Build efficient lookup indexes."""
        
        # Index: MITRE ID → node name
        self.mitre_to_node = {}
        for ttp_id, ttp_info in self.schema.get("mitre_techniques", {}).items():
            self.mitre_to_node[ttp_id] = ttp_info["posture_model_node"]
        
        # Index: keyword → node name
        self.keyword_to_node = {}
        for category, info in self.schema.get("plain_text_keywords", {}).items():
            node = info["posture_model_node"]
            for keyword in info.get("keywords", []):
                self.keyword_to_node[keyword.lower()] = node
    
    def normalize_nlp_output(self, nlp_result: Dict) -> Dict[str, float]:
        """
        Convert NLP pipeline output to normalized condition scores.
        
        Parameters
        ----------
        nlp_result : Dict
            Output from NLP pipeline with structure:
            {
                'keywords': [{'term': str, 'confidence': float}, ...],
                'ttps': [{'ttp_id': str, 'name': str, 'confidence': float}, ...],
                'conditions': [{'description': str, 'confidence': float}, ...]
            }
            
        Returns
        -------
        Dict[str, float]
            Mapping from Bayesian node names to normalized confidence scores
            {
                'Token_Impersonation': 0.89,
                'Bypass_Authentication': 0.88,
                ...
            }
        """
        
        normalized_scores = {}  # node_name → confidence
        
        # Process MITRE TTPs (highest priority - most specific)
        for ttp in nlp_result.get('ttps', []):
            ttp_id = ttp.get('ttp_id')
            if ttp_id in self.mitre_to_node:
                node = self.mitre_to_node[ttp_id]
                confidence = ttp.get('confidence', 0.0)
                # Keep max confidence for each node (multiple TTPs may map to same node)
                normalized_scores[node] = max(
                    normalized_scores.get(node, 0),
                    confidence
                )
        
        # Process keywords (medium priority)
        for keyword in nlp_result.get('keywords', []):
            term = keyword.get('term', '').lower()
            
            # Exact match in keyword index
            if term in self.keyword_to_node:
                node = self.keyword_to_node[term]
                confidence = keyword.get('confidence', 0.0)
                # Apply confidence boost for keyword matches
                boost = self.schema.get('plain_text_keywords', {}) \
                    .get(term, {}).get('confidence_boost', 0.0)
                normalized_scores[node] = max(
                    normalized_scores.get(node, 0),
                    confidence + boost
                )
            
            # Fuzzy substring matching
            for keyword_base, node in self.keyword_to_node.items():
                if keyword_base in term or term in keyword_base:
                    confidence = keyword.get('confidence', 0.0) * 0.8  # Reduce for fuzzy match
                    normalized_scores[node] = max(
                        normalized_scores.get(node, 0),
                        confidence
                    )
        
        # Process free-form conditions (lowest priority - most uncertain)
        for condition in nlp_result.get('conditions', []):
            description = condition.get('description', '').lower()
            confidence = condition.get('confidence', 0.0)
            
            # Try to match description to known conditions
            for keyword, node in self.keyword_to_node.items():
                if keyword in description:
                    normalized_scores[node] = max(
                        normalized_scores.get(node, 0),
                        confidence * 0.7  # Lower confidence for indirect match
                    )
        
        # Clamp all scores to [0, 1]
        for node in normalized_scores:
            normalized_scores[node] = min(1.0, max(0.0, normalized_scores[node]))
        
        return normalized_scores
    
    def continuous_to_discrete_evidence(self,
                                       normalized_scores: Dict[str, float],
                                       threshold: float = 0.75) -> Dict[str, int]:
        """
        Convert continuous confidence scores to discrete model evidence.
        
        Parameters
        ----------
        normalized_scores : Dict[str, float]
            Continuous scores from normalize_nlp_output()
            
        threshold : float
            Confidence threshold for evidence inclusion (default 0.75)
            - Scores >= threshold → evidence = 1 (condition observed)
            - Scores < threshold → evidence = 0 (condition not observed)
            
        Returns
        -------
        Dict[str, int]
            Discrete evidence for Bayesian model:
            {
                'Token_Impersonation': 1,
                'Access_Server': 0,
                ...
            }
        """
        
        evidence = {}
        for node, score in normalized_scores.items():
            evidence[node] = 1 if score >= threshold else 0
        
        return evidence
    
    def get_evidence_confidence(self,
                              normalized_scores: Dict[str, float],
                              use_default_threshold: bool = True) -> Dict[str, Dict]:
        """
        Return evidence with associated confidence values for debugging.
        
        Useful for model interpretability and debugging evidence decisions.
        """
        
        threshold = self.schema.get('confidence_thresholds', {}) \
            .get('condition_inclusion', {}).get('recommended', 0.75) \
            if use_default_threshold else 0.5
        
        result = {}
        for node, score in normalized_scores.items():
            result[node] = {
                'evidence': 1 if score >= threshold else 0,
                'confidence': score,
                'threshold': threshold,
                'exceeded_threshold': score >= threshold
            }
        
        return result
    
    def explain_mapping(self, nlp_result: Dict) -> str:
        """
        Generate human-readable explanation of NLP→Model mapping.
        
        Useful for debugging and validation.
        """
        
        lines = []
        lines.append("=" * 60)
        lines.append("NLP OUTPUT → BAYESIAN MODEL MAPPING")
        lines.append("=" * 60)
        
        # Show MITRE mappings
        ttps = nlp_result.get('ttps', [])
        if ttps:
            lines.append("\nMITRE TECHNIQUES:")
            for ttp in ttps:
                ttp_id = ttp.get('ttp_id')
                name = ttp.get('name')
                conf = ttp.get('confidence', 0.0)
                node = self.mitre_to_node.get(ttp_id, "UNKNOWN")
                lines.append(f"  {ttp_id}: {name}")
                lines.append(f"    Confidence: {conf:.2f} → Node: {node}")
        
        # Show keyword mappings
        keywords = nlp_result.get('keywords', [])
        if keywords:
            lines.append("\nKEYWORDS:")
            for kw in keywords[:5]:  # Show top 5
                term = kw.get('term')
                conf = kw.get('confidence', 0.0)
                node = self.keyword_to_node.get(term.lower(), "NO MATCH")
                lines.append(f"  '{term}' (conf: {conf:.2f}) → {node}")
        
        # Show final normalized scores
        normalized = self.normalize_nlp_output(nlp_result)
        if normalized:
            lines.append("\nFINAL NORMALIZED SCORES:")
            for node, score in sorted(normalized.items(), key=lambda x: x[1], reverse=True):
                lines.append(f"  {node}: {score:.3f}")
        
        lines.append("=" * 60)
        
        return "\n".join(lines)


def batch_normalize(nlp_results: List[Dict],
                   schema_path: Optional[str] = None) -> List[Dict[str, int]]:
    """
    Normalize multiple NLP results to discrete evidence in batch.
    
    Parameters
    ----------
    nlp_results : List[Dict]
        Multiple NLP pipeline outputs
        
    schema_path : str
        Path to CONDITION_SCHEMA.json
        
    Returns
    -------
    List[Dict[str, int]]
        Discrete evidence for each input
    """
    
    normalizer = ConditionNormalizer(schema_path)
    batch_evidence = []
    
    for nlp_result in nlp_results:
        normalized = normalizer.normalize_nlp_output(nlp_result)
        evidence = normalizer.continuous_to_discrete_evidence(normalized)
        batch_evidence.append(evidence)
    
    return batch_evidence


if __name__ == "__main__":
    # Example usage
    print("Condition Normalization Module")
    print("================================")
    print()
    
    # Create normalizer
    normalizer = ConditionNormalizer()
    
    # Example NLP output
    example_nlp = {
        'keywords': [
            {'term': 'escalate', 'type': 'action', 'confidence': 0.92},
            {'term': 'credential', 'type': 'credential', 'confidence': 0.88},
            {'term': 'malware', 'type': 'tool', 'confidence': 0.85},
        ],
        'ttps': [
            {'ttp_id': 'T1134', 'name': 'Access Token Manipulation', 'confidence': 0.89},
        ]
    }
    
    # Normalize
    print("Example NLP Output:")
    print(json.dumps(example_nlp, indent=2))
    print()
    
    normalized = normalizer.normalize_nlp_output(example_nlp)
    print("Normalized Scores:")
    print(json.dumps(normalized, indent=2))
    print()
    
    evidence = normalizer.continuous_to_discrete_evidence(normalized, threshold=0.75)
    print("Discrete Evidence (threshold=0.75):")
    print(json.dumps(evidence, indent=2))
    print()
    
    # Show explanation
    print(normalizer.explain_mapping(example_nlp))
