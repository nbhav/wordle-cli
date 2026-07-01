from dataclasses import dataclass
from importlib.resources import files

def _read(filename: str) -> set[str]:
    text = files("wordle_cli.data").joinpath(filename).read_text()
    return {line.strip().lower() for line in text.splitlines() if line.strip() and len(line) > 0}

@dataclass(frozen=True)
class WordList:
    valid: frozenset[str]
    allowed: frozenset[str]

    @classmethod
    def load(cls) -> "WordList":
        # importlib.resources work happens here
        valid = frozenset(_read("valid_words.txt"))
        allowed = frozenset(_read("allowed_guess.txt"))
        return cls(valid=valid, allowed=allowed)

    def for_length(self, n: int) -> tuple[set[str], set[str]]:
        return ({w for w in self.valid if len(w) == n},
                {w for w in self.allowed if len(w) == n})