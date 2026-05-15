# ─── TYPE DERIVATION ────────────────────────────────────────────────────────
# The catalogue has no assessment_type field.
# Derive it from the "keys" array using priority order.
# Priority: A > P > B > S > K (most specific to least specific)

_KEY_TO_TYPE: dict[str, str] = {
    "Ability & Aptitude":            "A",
    "Personality & Behavior":        "P",
    "Biodata & Situational Judgment": "B",
    "Simulations":                   "S",
    "Knowledge & Skills":            "K",
    "Competencies":                  "P",   # behavioural competency = personality proxy
    "Development & 360":             "P",   # 360 feedback = personality proxy
    "Assessment Exercises":          "S",   # exercise = simulation proxy
}

_TYPE_PRIORITY: list[str] = [
    "Ability & Aptitude",
    "Personality & Behavior",
    "Biodata & Situational Judgment",
    "Simulations",
    "Knowledge & Skills",
    "Competencies",
    "Development & 360",
    "Assessment Exercises",
]

def derive_type(item: dict) -> str:
    """
    Derive the assessment type code from the catalogue 'keys' field.
    Uses priority order: A > P > B > S > K.
    Returns 'K' as fallback if no known key is found.
    """
    item_keys = item.get("keys", [])
    for priority_key in _TYPE_PRIORITY:
        if priority_key in item_keys:
            return _KEY_TO_TYPE[priority_key]
    return "K"  # safe fallback

def enforce_battery_diversity(
    ranked: list[dict],
    all_items: list[dict],
    signals: dict,
    max_results: int = 10
) -> list[dict]:
    """
    After scoring and ranking, ensure the battery covers required types.
    """
    result = list(ranked[:max_results])
    result_types = {derive_type(item) for item in result}
    
    required: list[str] = []
    if signals.get("has_technical", False):
        required.append("K")
    if signals.get("has_reasoning", True):   # default True — always add ability
        required.append("A")
    if signals.get("has_behavioural", True): # default True — always add personality
        required.append("P")
    if signals.get("has_situational", False):
        required.append("B")
    
    seniority_levels = signals.get("seniority_levels", [])
    result_ids = {item["entity_id"] for item in result}
    
    for required_type in required:
        if required_type in result_types:
            continue  # already covered — skip
        
        # Find best available item of required_type not already in result
        candidates = [
            item for item in all_items
            if derive_type(item) == required_type
            and item["entity_id"] not in result_ids
        ]
        
        if not candidates:
            continue
        
        # Prefer items matching seniority if possible
        if seniority_levels:
            level_matched = [
                c for c in candidates
                if any(lvl in c.get("job_levels", []) for lvl in seniority_levels)
            ]
            if level_matched:
                candidates = level_matched
        
        # Pick first candidate (candidates are already in catalogue order)
        best = candidates[0]
        
        # If result is at max, replace the lowest-scored item of an over-represented type
        if len(result) >= max_results:
            # Find type with most representation
            from collections import Counter
            type_counts = Counter(derive_type(i) for i in result)
            most_common_type = type_counts.most_common(1)[0][0]
            
            # Only replace if it's over-represented (count > 1)
            if type_counts[most_common_type] > 1:
                # Find last item of most common type (lowest scored)
                for i in range(len(result) - 1, -1, -1):
                    if derive_type(result[i]) == most_common_type:
                        result[i] = best
                        break
        else:
            result.append(best)
        
        result_ids.add(best["entity_id"])
        result_types.add(required_type)
    
    return result[:max_results]

class Ranker:
    def score_item(self, item: dict, signals: dict) -> int:
        """
        Deterministic additive scoring.
        """
        score = 0
        name_lower = item.get("name", "").lower()
        desc_lower = item.get("description", "").lower()
        item_keys = item.get("keys", [])
        item_levels = item.get("job_levels", [])
        
        tech_signals: list[str] = signals.get("tech_signals", [])
        seniority_levels: list[str] = signals.get("seniority_levels", [])
        behavioural_signals: list[str] = signals.get("behavioural_signals", [])
        work_context_signals: list[str] = signals.get("work_context_signals", [])
        remote_required: bool = signals.get("remote_required", False)
        adaptive_required: bool = signals.get("adaptive_required", False)
        type_constraints: list[str] = signals.get("type_constraints", [])
        
        # +3: technical skill keyword match in name (most precise)
        for sig in tech_signals:
            if sig.lower() in name_lower:
                score += 3
                break
        
        # +2: technical skill keyword match in description only (less precise)
        if score == 0:   # only if name didn't already match
            for sig in tech_signals:
                if sig.lower() in desc_lower:
                    score += 2
                    break
        
        # +2: seniority match
        if seniority_levels and any(lvl in item_levels for lvl in seniority_levels):
            score += 2
        
        # +2: behavioural requirement match (in description or keys)
        for sig in behavioural_signals:
            if sig.lower() in desc_lower or sig.lower() in " ".join(item_keys).lower():
                score += 2
                break
        
        # +1: work context match
        for sig in work_context_signals:
            if sig.lower() in desc_lower:
                score += 1
                break
        
        # +1: remote support
        if remote_required and item.get("remote", "no") == "yes":
            score += 1
        
        # +1: adaptive support
        if adaptive_required and item.get("adaptive", "no") == "yes":
            score += 1
        
        # +2: explicit type constraint match
        if type_constraints:
            item_type = derive_type(item)
            if item_type in type_constraints:
                score += 2
        
        return score

    def filter_catalogue(self, catalogue: list[dict], signals: dict, relax_seniority: bool = False) -> list[dict]:
        """Simplified filter logic matching Section 10."""
        seniority_levels = signals.get("seniority_levels", [])
        tech_signals = [s.lower() for s in signals.get("tech_signals", [])]
        behavioural_signals = [s.lower() for s in signals.get("behavioural_signals", [])]
        
        filtered = []
        for item in catalogue:
            # Seniority overlap
            seniority_match = False
            if seniority_levels and not relax_seniority:
                if any(lvl in item.get("job_levels", []) for lvl in seniority_levels):
                    seniority_match = True
            else:
                seniority_match = True # Keep all if no seniority or relaxed
            
            # Key/Description overlap
            content_match = False
            keys_text = " ".join(item.get("keys", [])).lower()
            desc_text = item.get("description", "").lower()
            
            if any(s in keys_text or s in desc_text for s in tech_signals + behavioural_signals):
                content_match = True
            
            if seniority_match and (content_match or not tech_signals):
                filtered.append(item)
        
        return filtered

    def retrieve_and_rank(self, signals: dict, catalogue: list[dict]) -> list[dict]:
        # Step 1: filter
        filtered = self.filter_catalogue(catalogue, signals)
        if not filtered:
            filtered = self.filter_catalogue(catalogue, signals, relax_seniority=True)
        if not filtered:
            return []  # triggers FALLBACK in agent.py
        
        # Step 2: score
        scored = [(self.score_item(item, signals), item) for item in filtered]
        
        # Step 3: rank (descending score, tie-break by entity_id alphabetical)
        scored.sort(key=lambda x: (-x[0], x[1]["entity_id"]))
        
        # Step 4: remove zero-score items (unless nothing else available)
        nonzero = [item for score, item in scored if score > 0]
        ranked = nonzero if nonzero else [item for _, item in scored]
        
        # Step 5: enforce diversity
        result = enforce_battery_diversity(ranked, catalogue, signals)
        
        return result
