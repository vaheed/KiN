from __future__ import annotations

from .config import Settings
from .db import Database
from .repositories import EventRepository, GoalRepository
from .services.autonomy import AutonomyPolicy
from .services.bifrost import BifrostClient
from .services.decision import DecisionMaker
from .services.memory import MemoryService
from .services.trueforge import TrueForgeClient


class Container:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.db = Database(settings)
        self.bifrost = BifrostClient(settings)
        self.memories = None
        self.goals = None
        self.events = None
        self.decision_maker = DecisionMaker(settings, self.bifrost)
        self.autonomy = AutonomyPolicy(settings)
        self.trueforge = TrueForgeClient(settings)

    def startup(self) -> None:
        self.db.open()
        self.memories = MemoryService(settings=self.settings, redis_client=self.db.redis)
        self.goals = GoalRepository(self.db)
        self.events = EventRepository(self.db)

    def shutdown(self) -> None:
        if self.memories is not None:
            self.memories.close()
        self.bifrost.close()
        self.db.close()
