"""
SHL Context Builder — Bug Fix Spec Compliant (v5.0)
"""
import re
from typing import List, Dict, Set, Optional
from dataclasses import dataclass, field

SENIORITY_MAP: dict[str, list[str]] = {
    "entry":         ["Entry-Level", "Graduate"],
    "junior":        ["Entry-Level", "Graduate"],
    "entry level":   ["Entry-Level", "Graduate"],
    "entry-level":   ["Entry-Level", "Graduate"],
    "graduate":      ["Graduate", "Entry-Level"],
    "new grad":      ["Graduate", "Entry-Level"],
    "fresh grad":    ["Graduate", "Entry-Level"],
    "mid":           ["Mid-Professional", "Professional Individual Contributor"],
    "mid level":     ["Mid-Professional", "Professional Individual Contributor"],
    "mid-level":     ["Mid-Professional", "Professional Individual Contributor"],
    "intermediate":  ["Mid-Professional", "Professional Individual Contributor"],
    "senior":        ["Manager", "Director", "Professional Individual Contributor"],
    "lead":          ["Manager", "Front Line Manager"],
    "team lead":     ["Manager", "Front Line Manager"],
    "manager":       ["Manager", "Front Line Manager"],
    "director":      ["Director", "Executive"],
    "head of":       ["Director", "Executive"],
    "vp":            ["Executive", "Director"],
    "executive":     ["Executive", "Director"],
    "c-suite":       ["Executive"],
    "supervisor":    ["Supervisor", "Front Line Manager"],
}

class ContextBuilder:
    def __init__(self):
        self.type_map = {
            r"knowledge|technical|coding|skill": "K",
            r"ability|cognitive|aptitude|reasoning": "A",
            r"personality|behavioral|trait|workplace": "P",
            r"situational|judgment|sjt": "B",
            r"simulation|work sample|interactive": "S"
        }

    def build_from_history(self, messages: List[Dict[str, str]]) -> dict:
        """Accumulates all signals from messages history into a compliant dict."""
        signals: dict = {
            "job_title": "",
            "seniority_label": "",
            "responsibilities": [],
            "seniority_levels": [],
            "tech_signals": [],
            "behavioural_signals": [],
            "work_context_signals": [],
            "has_technical": False,
            "has_reasoning": True,
            "has_behavioural": True,
            "has_situational": False,
            "type_constraints": [],
            "adaptive_required": False,
            "language_required": "",
            "has_role_signal": False,
            "is_refinement": False,
            "refine_constraint": "",
        }

        full_text = " ".join([m["content"] for m in messages if m["role"] == "user"]).lower()

        # JD detection
        if len(full_text.split()) > 20 or "job description" in full_text or "jd:" in full_text:
            pass # can set a flag if needed

        for msg in messages:
            if msg["role"] != "user": continue
            text = msg["content"].lower()
            
            # 1. Seniority Mapping
            for key, levels in SENIORITY_MAP.items():
                if key in text:
                    signals["seniority_levels"] = levels # Most recent match wins
                    signals["seniority_label"] = key

            # 2. Assessment Types
            for pattern, t in self.type_map.items():
                if re.search(pattern, text):
                    if t not in signals["type_constraints"]:
                        signals["type_constraints"].append(t)

            # 3. Roles & Skills (Heuristic)
            roles = ["developer", "engineer", "analyst", "manager", "representative", "consultant", "accountant", "sales"]
            for r in roles:
                if r in text:
                    signals["job_title"] = r
                    signals["has_role_signal"] = True

            tech_keywords = ["java", "python", "aws", "sql", "react", "cloud", "azure", "finance", "data", "marketing", "c++", "c#", ".net", "golang", "javascript", "typescript"]
            for tk in tech_keywords:
                if tk in text:
                    if tk not in signals["tech_signals"]:
                        signals["tech_signals"].append(tk)
                        signals["has_technical"] = True
                        signals["has_role_signal"] = True

            # 4. Behavioral & Context
            behavioral = ["collaboration", "teamwork", "leadership", "stakeholder", "communication"]
            for b in behavioral:
                if b in text:
                    if b not in signals["behavioural_signals"]:
                        signals["behavioural_signals"].append(b)
                        signals["has_behavioural"] = True

            context_signals = ["complexity", "autonomy", "adaptability", "change"]
            for cs in context_signals:
                if cs in text:
                    if cs not in signals["work_context_signals"]:
                        signals["work_context_signals"].append(cs)

            if "remote" in text or "hybrid" in text:
                pass # not strictly required for output
            if "adaptive" in text or "efficient" in text or "fast" in text:
                signals["adaptive_required"] = True

        return signals
