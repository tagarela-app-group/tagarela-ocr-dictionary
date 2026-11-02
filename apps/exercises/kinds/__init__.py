from apps.exercises.kinds.base import Brief, Effort, ExerciseKind
from apps.exercises.kinds.listen_write import ListenWrite
from apps.exercises.kinds.reply import Reply

KINDS: dict[str, ExerciseKind] = {kind.name: kind for kind in (ListenWrite(), Reply())}

__all__ = ["KINDS", "Brief", "Effort", "ExerciseKind"]
