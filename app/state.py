from typing import Any, Dict, List, TypedDict


class AgentState(TypedDict, total=False):
    user_id: str
    question: str

    manager_plan: Dict[str, Any]

    transport_result: Dict[str, Any]
    context_result: Dict[str, Any]

    draft_answer: str
    critic_result: Dict[str, Any]
    final_answer: str

    used_agents: List[str]
    trace: Dict[str, Any]
    revision_count: int