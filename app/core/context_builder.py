"""
SHL Context Builder — Bug Fix Spec Compliant (v5.0)
"""
import re
from typing import List, Dict, Set, Optional
from dataclasses import dataclass, field

@dataclass
class HiringContext:
    role: Optional[str] = None
    seniority_levels: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    behavioral_signals: List[str] = field(default_factory=list)
    context_signals: List[str] = field(default_factory=list)
    assessment_types: Set[str] = field(default_factory=set)
    remote_testing: bool = False
    adaptive_preference: bool = False
    is_jd: bool = False
    full_text: str = ""

class ContextBuilder:
    def __init__(self):
        # SECTION — SENIORITY MAPPING TABLE
        self.SENIORITY_MAP: dict[str, list[str]] = {
            "entry": ["Entry-Level", "Graduate"],
            "junior": ["Entry-Level", "Graduate"],
            "entry level": ["Entry-Level", "Graduate"],
            "entry-level": ["Entry-Level", "Graduate"],
            "0-2 years": ["Entry-Level"],
            "0 to 2 years": ["Entry-Level"],
            "new grad": ["Entry-Level", "Graduate"],
            "fresh grad": ["Graduate", "Entry-Level"],
            "graduate": ["Graduate", "Entry-Level"],
            "mid": ["Mid-Professional", "Professional Individual Contributor"],
            "mid level": ["Mid-Professional", "Professional Individual Contributor"],
            "mid-level": ["Mid-Professional", "Professional Individual Contributor"],
            "intermediate": ["Mid-Professional", "Professional Individual Contributor"],
            "3-5 years": ["Mid-Professional", "Professional Individual Contributor"],
            "3 to 5 years": ["Mid-Professional", "Professional Individual Contributor"],
            "4 years": ["Mid-Professional", "Professional Individual Contributor"],
            "senior": ["Manager", "Director", "Professional Individual Contributor"],
            "senior level": ["Manager", "Director"],
            "sr": ["Manager", "Director"],
            "lead": ["Manager", "Front Line Manager"],
            "team lead": ["Manager", "Front Line Manager"],
            "manager": ["Manager", "Front Line Manager"],
            "people manager": ["Manager"],
            "front line manager": ["Front Line Manager", "Manager"],
            "director": ["Director", "Executive"],
            "head of": ["Director", "Executive"],
            "vp": ["Executive", "Director"],
            "vice president": ["Executive", "Director"],
            "c-suite": ["Executive"],
            "executive": ["Executive", "Director"],
            "ceo": ["Executive"],
            "cto": ["Executive"],
            "cfo": ["Executive"],
            "supervisor": ["Supervisor", "Front Line Manager"],
        }
        
        self.type_map = {
            r"knowledge|technical|coding|skill": "K",
            r"ability|cognitive|aptitude|reasoning": "A",
            r"personality|behavioral|trait|workplace": "P",
            r"situational|judgment|sjt": "B",
            r"simulation|work sample|interactive": "S"
        }

    def build_from_history(self, messages: List[Dict[str, str]]) -> HiringContext:
        """Accumulates all signals from messages history."""
        context = HiringContext()
        full_text = " ".join([m["content"] for m in messages if m["role"] == "user"]).lower()
        context.full_text = full_text
        
        # JD detection
        if len(full_text.split()) > 20 or "job description" in full_text or "jd:" in full_text:
            context.is_jd = True

        for msg in messages:
            if msg["role"] != "user": continue
            text = msg["content"].lower()
            
            # 1. Seniority Mapping
            for key, levels in self.SENIORITY_MAP.items():
                if key in text:
                    context.seniority_levels = levels # Most recent match wins

            # 2. Assessment Types
            for pattern, t in self.type_map.items():
                if re.search(pattern, text):
                    context.assessment_types.add(t)

            # 3. Roles & Skills (Heuristic)
            roles = ["developer", "engineer", "analyst", "manager", "representative", "consultant", "accountant", "sales"]
            for r in roles:
                if r in text:
                    context.role = r

            tech_keywords = ["java", "python", "aws", "sql", "react", "cloud", "azure", "finance", "data", "marketing"]
            for tk in tech_keywords:
                if tk in text:
                    if tk not in context.skills:
                        context.skills.append(tk)

            # 4. Behavioral & Context
            behavioral = ["collaboration", "teamwork", "leadership", "stakeholder", "communication"]
            for b in behavioral:
                if b in text:
                    if b not in context.behavioral_signals:
                        context.behavioral_signals.append(b)

            context_signals = ["complexity", "autonomy", "adaptability", "change"]
            for cs in context_signals:
                if cs in text:
                    if cs not in context.context_signals:
                        context.context_signals.append(cs)

            if "remote" in text or "hybrid" in text:
                context.remote_testing = True
            if "adaptive" in text or "efficient" in text or "fast" in text:
                context.adaptive_preference = True

        return context
