from apps.exercises.kinds.base import Brief, ExerciseKind
from apps.exercises.kinds.listen_write import ListenWrite

KINDS: dict[str, ExerciseKind] = {kind.name: kind for kind in (ListenWrite(),)}

__all__ = ["KINDS", "Brief", "ExerciseKind"]
