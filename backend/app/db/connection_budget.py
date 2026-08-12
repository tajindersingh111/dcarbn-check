from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


DatabaseProcessRole = Literal["api", "worker"]


@dataclass(frozen=True, slots=True)
class DatabaseConnectionBudget:
    connection_limit: int
    safety_margin_percent: int
    operator_reserve: int
    monitoring_connections: int
    migration_connections: int
    api_replicas: int
    api_pool_size: int
    api_max_overflow: int
    worker_replicas: int
    worker_pool_size: int
    worker_max_overflow: int

    @property
    def safety_margin(self) -> int:
        return self.connection_limit * self.safety_margin_percent // 100

    @property
    def api_connections(self) -> int:
        return self.api_replicas * (self.api_pool_size + self.api_max_overflow)

    @property
    def worker_connections(self) -> int:
        return self.worker_replicas * (
            self.worker_pool_size + self.worker_max_overflow
        )

    @property
    def fixed_connections(self) -> int:
        return (
            self.operator_reserve
            + self.monitoring_connections
            + self.migration_connections
        )

    @property
    def allocated_connections(self) -> int:
        return self.api_connections + self.worker_connections + self.fixed_connections

    @property
    def required_connections(self) -> int:
        return self.allocated_connections + self.safety_margin

    def validate(self) -> None:
        if self.required_connections > self.connection_limit:
            raise ValueError(
                "Unsafe database connection budget: API, worker, migration, "
                "monitoring, operator reserve and safety margin require "
                f"{self.required_connections} connections but "
                f"DATABASE_CONNECTION_LIMIT is {self.connection_limit}."
            )

    def process_pool(self, role: DatabaseProcessRole) -> tuple[int, int]:
        if role == "api":
            return self.api_pool_size, self.api_max_overflow
        return self.worker_pool_size, self.worker_max_overflow
