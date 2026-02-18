"""Per-agent LLM cost tracking with daily rotation."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field


@dataclass
class _AgentBudget:
    spent: float = 0.0
    day: int = 0  # day number since epoch


class BudgetTracker:
    """Thread-safe per-agent daily LLM cost tracker."""

    def __init__(self) -> None:
        self._budgets: dict[str, _AgentBudget] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _current_day() -> int:
        return int(time.time() // 86400)

    def check(self, agent_id: str, max_cost_per_day: float) -> float:
        """Return remaining budget for today. Resets on new day."""
        today = self._current_day()
        with self._lock:
            budget = self._budgets.get(agent_id)
            if budget is None or budget.day != today:
                return max_cost_per_day
            return max(0.0, max_cost_per_day - budget.spent)

    def record(self, agent_id: str, cost: float) -> None:
        """Record a cost charge for an agent."""
        today = self._current_day()
        with self._lock:
            budget = self._budgets.get(agent_id)
            if budget is None or budget.day != today:
                budget = _AgentBudget(spent=0.0, day=today)
                self._budgets[agent_id] = budget
            budget.spent += cost

    def spent_today(self, agent_id: str) -> float:
        """Return total spent today for an agent."""
        today = self._current_day()
        with self._lock:
            budget = self._budgets.get(agent_id)
            if budget is None or budget.day != today:
                return 0.0
            return budget.spent
