from typing import Dict, List


def compress_step_data(step: Dict) -> Dict:
    """Truncate long strings in a step dictionary to keep memory footprint small."""
    result = {}
    for key, value in step.items():
        if isinstance(value, str) and len(value) > 500:
            result[key] = value[:500] + "..."
        else:
            result[key] = value
    return result


def _compress_memory(memory: List[Dict]) -> List[Dict]:
    """Compress memory to first 10 + summary + last 10 when length > 20."""
    if len(memory) <= 20:
        return memory

    first_10 = [compress_step_data(item) for item in memory[:10]]
    last_10 = [compress_step_data(item) for item in memory[-10:]]

    total_steps = len(memory)
    middle_indices = f"{10}-{total_steps - 11}"
    # Build a concise summary of the dropped middle section
    summary: Dict = {
        "role": "system",
        "content": f"[Memory compressed: dropped {total_steps - 20} middle steps (indices {middle_indices})]",
        "summary": True,
    }

    return first_10 + [summary] + last_10


class SessionMemory:
    """In-memory conversation memory storage (demo). Production would use Redis."""

    _sessions: Dict[str, List[Dict]] = {}

    @classmethod
    def get(cls, session_id: str) -> List[Dict]:
        """Retrieve memory for a session."""
        return cls._sessions.get(session_id, [])

    @classmethod
    def save(cls, session_id: str, memory: List[Dict]) -> None:
        """Save memory for a session, compressing if longer than 20 steps."""
        compressed_memory = _compress_memory(memory)
        cls._sessions[session_id] = compressed_memory
