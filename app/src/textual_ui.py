"""
Ui for the Wordle cli app
"""
# Python Imports
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Static

# Custom Imports
from wordle_cli import WordleCliBase, LetterStatus

KEYBOARD_ROWS = [
    list("QWERTYUIOP"),
    list("ASDFGHJKL"),
    ["ENTER"] + list("ZXCVBNM") + ["⌫"],
]

WORD_LENGTH = 5


# Reference: https://github.com/Kinkelin/WordleCompetition/tree/main/data/official
# Words list from wordle offical
# File path for all the valid words that will be shown to users
WORDS_FILE_PATH="data/valid_words.txt"

# File path so users can guess a large variety of words
WORDS_GUESS_PATH="data/allowed_guess.txt"




class WelcomeScreen(Screen):
    BINDINGS = [("enter", "start_game", "Start")]

    def compose(self) -> ComposeResult:
        yield Static("Welcome to Wordle CLI\n\nHit Enter to start", id="welcome-text")
        yield Footer()

    def action_start_game(self) -> None:
        self.app.switch_screen(GameScreen())


class GameScreen(Screen):
    BINDINGS = [("ctrl+r", "restart", "Restart"), ("ctrl+c", "quit", "Quit")]

    def __init__(self):
        super().__init__()
        self._game = WordleCliBase(words_file_path=WORDS_FILE_PATH, words_guess_file_path=WORDS_GUESS_PATH)

    def compose(self) -> ComposeResult:
        with Vertical(id="guess_screen"):
            for row_idx in range(self._game.total_guesses):
                with Horizontal(classes="guess-row"):
                    for col_idx in range(WORD_LENGTH):
                        yield Static("", id=f"cell-{row_idx}-{col_idx}", classes="cell")

        yield Static("", id="current-word")


        with Vertical(id="keyboard"):
            for row in KEYBOARD_ROWS:
                with Horizontal(classes="key-row"):
                    for key in row:
                        btn_id = "key-backspace" if key == "⌫" else f"key-{key}"
                        wide = key in ("ENTER", "⌫")
                        yield Button(key, id=btn_id, classes="key wide" if wide else "key")

   
        yield Footer()

    def on_mount(self) -> None:
        self._current_letters: list[str] = []
        for button in self.query(Button):
            button.can_focus = False

    def action_restart(self) -> None:
        self._game.reset_game()
        self._current_letters = []
        self.query_one("#current-word", Static).update("")
        for button in self.query(Button):
            button.remove_class("match")
            button.remove_class("present")
            button.remove_class("absent")

    def _process_input(self, key: str) -> None:
        """key is 'ENTER', 'BACKSPACE', or a single uppercase letter."""
        if key == "ENTER":
            self._submit_guess()
            return
        if key == "BACKSPACE":
            if self._current_letters:
                self._current_letters.pop()
        elif len(key) == 1 and key.isalpha() and len(self._current_letters) < WORD_LENGTH:
            self._current_letters.append(key.lower())
        self.query_one("#current-word", Static).update("".join(self._current_letters).upper())

    def on_button_pressed(self, event: Button.Pressed) -> None:
        label = str(event.button.label)
        if label == "⌫":
            label = "BACKSPACE"
        self._process_input(label.upper())

    def on_key(self, event) -> None:
        if event.key == "enter":
            button_id = "#key-ENTER"
        elif event.key == "backspace":
            button_id = "#key-backspace"
        elif event.character and event.character.isalpha() and len(event.character) == 1:
            button_id = f"#key-{event.character.upper()}"
        else:
            return
        self.query_one(button_id, Button).press()

    def _submit_guess(self) -> None:
        if len(self._current_letters) < WORD_LENGTH:
            # Shake guess screen on invalid guess and show bright red
            return    
        self._current_letters = []
        self.query_one("#current-word", Static).update("")

    def update_key_status(self, letter: str, status: LetterStatus) -> None:
        button = self.query_one(f"#key-{letter.upper()}", Button)
        if status == LetterStatus.MATCH:
            button.set_classes("key match")
        elif status == LetterStatus.EXISTS and not button.has_class("match"):
            button.set_classes("key present")
        elif status == LetterStatus.DOES_NOT_EXIST and not button.has_class("match") and not button.has_class("present"):
            button.set_classes("key absent")


class WordleCli(App):
    BINDINGS = [("ctrl+r", "restart", "Restart"), ("ctrl+c", "quit", "Quit")]

    CSS = """
    Screen {
        align: center middle;
    }
    #welcome-text {
        content-align: center middle;
        text-align: center;
        width: auto;
        height: auto;
    }
    #keyboard {
        width: auto;
        height: auto;
        align: center middle;
    }
    .key-row {
        width: auto;
        height: auto;
        align: center middle;
    }
    .key {
        min-width: 4;
        height: 3;
        margin: 0 1;
    }
    .wide {
        min-width: 6;
    }
    .match {
        background: green;
        color: white;
    }
    .present {
        background: yellow;
        color: black;
    }
    .absent {
        background: $surface;
        color: $text-muted;
    }
    #current-word {
        height: 3;
        width: auto;
        min-width: 20;
        border: solid $accent;
        background: $surface;
        content-align: center middle;
        text-align: center;
        padding: 0 1;
        margin: 1 0;
    }
    #guess_screen {
        width: auto;
        height: auto;
        align: center middle;
    }
    .guess-row {
        width: auto;
        height: auto;
        align: center middle;
    }
    .cell {
        width: 5;
        height: 3;
        border: heavy $accent;
        content-align: center middle;
        text-align: center;
        margin: 0 1;
    }
    """

    def action_quit(self) -> None:
        self.exit()

    def on_mount(self) -> None:
        self.theme = "atom-one-dark"
        self.push_screen(WelcomeScreen())


if __name__ == "__main__":
    WordleCli().run()
