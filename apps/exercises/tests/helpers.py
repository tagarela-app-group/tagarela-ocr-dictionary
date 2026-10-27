from collections.abc import Mapping

FENCE_ITEMS: list[dict[str, str]] = [
    {
        "source_sentence": "I'm still on the fence about moving to Lisbon.",
        "source_answer": "on the fence",
        "source_syllables": "on the fence",
        "target_translation": "Ainda tô em cima do muro sobre me mudar pra Lisboa.",
        "target_extra_note": "Depois vem *about*: *on the fence about* alguma coisa.",
        "source_extra_say": "on the fence about",
    },
    {
        "source_sentence": "She stayed on the fence during the whole meeting.",
        "source_answer": "on the fence",
        "source_syllables": "on the fence",
        "target_translation": "Ela ficou em cima do muro a reunião inteira.",
        "target_extra_note": "Com *stay* fica *stay on the fence*: continuar sem decidir.",
        "source_extra_say": "stay on the fence",
    },
    {
        "source_sentence": "Stop sitting on the fence and pick a restaurant!",
        "source_answer": "on the fence",
        "source_syllables": "on the fence",
        "target_translation": "Para de ficar em cima do muro e escolhe um restaurante!",
        "target_extra_note": "*Sit on the fence* é o jeito mais comum de dizer isso.",
        "source_extra_say": "sit on the fence",
    },
]


class StubProvider:
    def __init__(
        self,
        response: Mapping[str, object] | None = None,
        error: Exception | None = None,
    ):
        self.calls: list[dict[str, object]] = []
        self.response = response if response is not None else {"items": FENCE_ITEMS}
        self.error = error

    def generate(
        self, prompt: str, *, system_instruction: str, schema: Mapping[str, object]
    ) -> Mapping[str, object]:
        self.calls.append(
            {"prompt": prompt, "system_instruction": system_instruction, "schema": schema}
        )
        if self.error:
            raise self.error
        return self.response
