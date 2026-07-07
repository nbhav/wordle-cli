"""
Ui for the Wordle cli app
"""
# Python Imports
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Static

# Custom Imports
from wordle_cli import WordleCliBase, LetterStatus, GuessStatus

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
        self._current_letters = []
        self._game = WordleCliBase(words_file_path=WORDS_FILE_PATH, words_guess_file_path=WORDS_GUESS_PATH)
        self._total_rows = self._game.total_guesses
        self._current_row = 0
        self._game_over = False

    def compose(self) -> ComposeResult:
        with Horizontal(id="header-bar"):
            yield Static("WordleCli", id="game-header")

        with Vertical(id="guess_screen"):
            for row_idx in range(self._total_rows):
                with Horizontal(classes="guess-row"):
                    for col_idx in range(WORD_LENGTH):
                        yield Static("", id=f"cell-{row_idx}-{col_idx}", classes="cell")

        with Horizontal(id="input-bar"):
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
        # Compose auto-focuses the first button (Q) before can_focus is cleared,
        # leaving a stray focus ring on it; drop focus so the screen owns keys.
        self.set_focus(None)
        self._resize_keyboard()
        self.call_after_refresh(self._sync_column_widths)

    def on_resize(self, event) -> None:
        self._resize_keyboard()
        self._sync_column_widths()

    def _sync_column_widths(self) -> None:
        """Header and input bar mirror the fixed guess-box width so the whole
        center column lines up, whatever the cell size works out to."""
        rows = self.query(".guess-row")
        if not rows:
            return
        grid_width = rows.first().region.width
        if grid_width <= 0:
            return
        self.query_one("#game-header").styles.width = grid_width
        self.query_one("#current-word").styles.width = grid_width

    def _resize_keyboard(self) -> None:
        """Pick one uniform key width that fits the terminal, so keys grow to
        fill wide terminals and shrink (without overflowing) on narrow ones."""
        available = self.size.width - 2  # small breathing room at the edges
        key_width = 3  # floor for readability
        # Widest rows: QWERTYUIOP (10 keys) and ENTER + 7 + ⌫ (wide keys = key+3).
        # Row span with 1-col gaps: top = 10*k + 9, bottom = 9*k + 14.
        for candidate in range(8, 3, -1):
            if max(10 * candidate + 9, 9 * candidate + 14) <= available:
                key_width = candidate
                break
        for button in self.query(".key"):
            button.styles.min_width = key_width + 3 if button.has_class("wide") else key_width

    def action_restart(self) -> None:
        self._game.reset_game()
        self._current_letters = []
        self._current_row = 0
        self._game_over = False
        self.query_one("#current-word", Static).update("")
        for cell in self.query(".cell"):
            cell.update("")
            cell.remove_class("match")
            cell.remove_class("present")
            cell.remove_class("absent")
        for button in self.query(Button):
            button.remove_class("match")
            button.remove_class("present")
            button.remove_class("absent")

    def _process_input(self, key: str) -> None:
        """key is 'ENTER', 'BACKSPACE', or a single uppercase letter."""
        if self._game_over:
            return
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

    _STATUS_CLASS = {
        LetterStatus.MATCH: "match",
        LetterStatus.EXISTS: "present",
        LetterStatus.DOES_NOT_EXIST: "absent",
    }

    def _submit_guess(self) -> None:
        if len(self._current_letters) < WORD_LENGTH:
            self.notify(
                "Not enough letters",
                title="Invalid guess",
                severity="error",
                timeout=3,
            )
            return

        result = self._game.submit_guess("".join(self._current_letters))

        if result.outcome == GuessStatus.NOT_IN_WORD_LIST:
            self.notify("Not in the word list", title="Invalid guess", severity="error", timeout=3)
            return
        if result.outcome == GuessStatus.GUESS_ALREADY_MADE:
            self.notify("You already guessed that word", title="Invalid guess", severity="warning", timeout=3)
            return
        if result.outcome == GuessStatus.INVALID_LENGTH:
            self.notify("Not enough letters", title="Invalid guess", severity="error", timeout=3)
            return

        # Valid guess: fill the row, colour the keyboard, and advance.
        self._render_guess(result.guess)
        self._current_letters = []
        self._current_row += 1
        self.query_one("#current-word", Static).update("")

        if result.outcome == GuessStatus.GAME_WON:
            self._game_over = True
            self.notify("You solved it!", title="You win \U0001F389", severity="information", timeout=6)
        elif result.outcome == GuessStatus.GAME_OVER:
            self._game_over = True
            self.notify(
                f"Out of guesses - the word was {self._game.answer.upper()}",
                title="Game over",
                severity="error",
                timeout=6,
            )

    def _render_guess(self, guess: list[dict]) -> None:
        """Fill the current row's cells with the guessed letters and colour each
        cell (and its keyboard key) by its match status."""
        for col, item in enumerate(guess):
            letter = item["letter"]
            status = item["match_status"]
            cell = self.query_one(f"#cell-{self._current_row}-{col}", Static)
            cell.update(letter.upper())
            cell.add_class(self._STATUS_CLASS[status])
            self.update_key_status(letter, status)

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
        /* Anchor to the top so, when the terminal is too short, the header and
           grid stay visible and only the (decorative) keyboard scrolls off the
           bottom -- centering would instead clip the top of the board. */
        align: center top;
    }
    /* The board (GameScreen) top-anchors, but the welcome screen has little
       content, so center it fully. */
    WelcomeScreen {
        align: center middle;
    }
    #welcome-text {
        content-align: center middle;
        text-align: center;
        width: auto;
        height: auto;
    }
    #keyboard {
        width: 100%;
        height: auto;
        align: center middle;
    }
    .key-row {
        width: 100%;
        height: auto;
        align: center middle;
    }
    .key {
        min-width: 4;
        height: 3;
        margin: 1 1;
        background: #565a63;   /* unused: still available */
        color: white;
    }
    .wide {
        min-width: 7;
    }
    .match {
        background: #538d4e;   /* in the word, correct spot */
        color: white;
    }
    .present {
        background: #b59f3b;   /* in the word, wrong spot */
        color: white;
    }
    .absent {
        background: #3a3a3c;   /* used, not in the word */
        color: #8a8d94;
    }
    /* On a scored cell, match the border to the fill so the tile reads as one
       solid block instead of the fill bleeding around the accent border. */
    .cell.match {
        border: heavy #538d4e;
    }
    .cell.present {
        border: heavy #b59f3b;
    }
    .cell.absent {
        border: heavy #3a3a3c;
    }
    #current-word {
        height: 3;
        width: auto;
        min-width: 10;
        border: solid $accent;
        content-align: center middle;
        text-align: center;
        padding: 0 1;
        margin: 1 0 0 0;
    }
    #header-bar {
        width: 100%;
        height: auto;
        align: center middle;
    }
    #game-header {
        width: 50%;
        min-width: 20;
        height: auto;
        border: round $accent;
        padding: 0 2;
        margin: 0 0 1 0;
        content-align: center middle;
        text-align: center;
        text-style: bold;
    }
    #guess_screen {
        width: 100%;
        height: auto;
        align: center middle;
    }
    #input-bar {
        width: 100%;
        height: auto;
        align: center middle;
    }
    .guess-row {
        width: auto;
        height: auto;
        align: center middle;
        margin-bottom: 1;
    }
    .cell {
        width: 6;
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
