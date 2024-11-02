from collections import OrderedDict
from typing import Callable

from lewis.devices import StateMachineDevice

from .states import DefaultState, State


class SimulatedGroup3HallProbe(StateMachineDevice):
    def _initialize_data(self) -> None:
        """
        Initialize all of the device's attributes.
        """
        pass

    def _get_state_handlers(self) -> dict[str, State]:
        return {
            "default": DefaultState(),
        }

    def _get_initial_state(self) -> str:
        return "default"

    def _get_transition_handlers(self) -> dict[tuple[str, str], Callable[[], bool]]:
        return OrderedDict([])
