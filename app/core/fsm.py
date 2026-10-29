"""Motor determinista de Máquinas de Estados Finitos (FSM) para procesos industriales."""

from typing import Generic, TypeVar

from app.core.exceptions import FSMTransitionError

TState = TypeVar("TState", bound=str)
TEvent = TypeVar("TEvent", bound=str)


class FSM(Generic[TState, TEvent]):
    """Máquina de estados finitos determinista y declarativa."""

    def __init__(
        self,
        initial_state: TState,
        transitions: dict[tuple[TState, TEvent], TState],
    ):
        self._current_state = initial_state
        self._transitions = transitions

    @property
    def current_state(self) -> TState:
        return self._current_state

    def trigger(self, event: TEvent) -> TState:
        key = (self._current_state, event)
        if key not in self._transitions:
            raise FSMTransitionError(
                f"Invalid transition from state '{self._current_state}' on event '{event}'"
            )
        self._current_state = self._transitions[key]
        return self._current_state
