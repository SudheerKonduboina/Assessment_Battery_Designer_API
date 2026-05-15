from enum import Enum

class DialogMode(str, Enum):
    DISCOVERY = "DISCOVERY"
    CLARIFICATION = "CLARIFICATION"
    RECOMMEND = "RECOMMEND"
    CLOSE = "CLOSE"
