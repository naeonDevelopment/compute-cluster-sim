"""Original synthetic simulator. Status: IMPLEMENTED_UNVERIFIED.

Copyright 2026 Theo Georgiev (Naevum). SPDX-License-Identifier: Apache-2.0
"""

from .model import Scenario, ScenarioError, load_scenario
from .simulator import simulate

__all__ = ["Scenario", "ScenarioError", "load_scenario", "simulate"]
__version__ = "0.2.0"
