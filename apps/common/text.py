def clean_text(text: str) -> str:
    return " ".join(text.split())


def term_key(text: str) -> str:
    return clean_text(text).casefold()
