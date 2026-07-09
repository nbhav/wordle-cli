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

    # Terminal cells are ~2:1 (tall:wide), so a square-looking tile needs
    # width == height * 2. Tiles are sized to the terminal each resize.
    CELL_ASPECT = 2
    MIN_CELL_H = 3
    MAX_CELL_H = 8
    # Rows used by everything but the board: header (~4) + input (~4) +
    # keyboard (~16) + footer (1), plus a little headroom so tall terminals
    # never overshoot into a scrollbar. The board gets the rest, so tiles grow
    # as the terminal gets taller while the keyboard stays fully visible.
    VERTICAL_CHROME = 26

    def __init__(self):
        super().__init__()
        self._current_letters = []
        self._game = WordleCliBase(words_file_path=WORDS_FILE_PATH, words_guess_file_path=WORDS_GUESS_PATH)
        self._total_rows = self._game.total_guesses
        self._current_row = 0
        self._game_over = False

    def compose(self) -> ComposeResult:
        # One container holds the whole game so everything sizes relative to it
        # (and thus to the terminal) via the fractional units in the CSS.
        with Vertical(id="game"):
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
        self._resize_board()

    def on_resize(self, event) -> None:
        self._resize_board()

    def _resize_board(self) -> None:
        """Size the tiles to the terminal, keeping them square, limited by
        whichever axis is tighter (leftover height, or width across the columns).
        The keyboard keys track the tile width so the board and keyboard scale
        together."""
        cols, rows = WORD_LENGTH, self._total_rows

        # Tallest a tile can be given the vertical space left for the board.
        board_height = self.size.height - self.VERTICAL_CHROME
        h_from_height = board_height // rows - 1  # minus per-row margin

        # Tallest a tile can be given the horizontal space, kept square.
        board_width = self.size.width - 4
        h_from_width = (board_width // cols - 2) // self.CELL_ASPECT

        cell_h = max(self.MIN_CELL_H, min(h_from_height, h_from_width, self.MAX_CELL_H))
        cell_w = cell_h * self.CELL_ASPECT
        for cell in self.query(".cell"):
            cell.styles.width = cell_w
            cell.styles.height = cell_h

        # Header and input bar span the board width so they read as one column.
        board_w = cols * cell_w + cols + 1  # tiles + collapsed 1-col margins
        self.query_one("#game-header").styles.width = board_w
        self.query_one("#current-word").styles.width = board_w

        # Keys scale with the tile (a bit under a tile wide) so the keyboard
        # stays proportional to the board and the keys aren't thin slivers.
        key_w = max(4, cell_w * 2 // 3)
        for button in self.query(".key"):
            # Wide keys (ENTER / backspace) need room for the "ENTER" label.
            button.styles.width = key_w + 3 if button.has_class("wide") else key_w

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
        align: center top;
    }
    WelcomeScreen {
        align: center middle;
    }
    #welcome-text {
        content-align: center middle;
        text-align: center;
        width: auto;
        height: auto;
    }

    /* The whole game is one relative block: it fills the terminal (up to a max
       width so tiles don't stretch absurdly on very wide screens) and centers.
       Its children divide that space with fractional units, so the board and
       keyboard resize together with the terminal. */
    #game {
        width: 100%;
        height: auto;
        align: center middle;
    }

    #header-bar {
        width: 100%;
        height: auto;
        align: center middle;
    }
    #game-header {
        width: auto;
        height: auto;
        border: round $accent;
        padding: 0 2;
        margin: 0 0 1 0;
        content-align: center middle;
        text-align: center;
        text-style: bold;
    }

    /* The board is content-sized; tile dimensions are set each resize by
       _resize_board (kept square). These are just the initial values. */
    #guess_screen {
        width: 100%;
        height: auto;
        align: center middle;
    }
    .guess-row {
        width: 100%;
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

    #input-bar {
        width: 100%;
        height: auto;
        align: center middle;
    }
    #current-word {
        height: 3;
        width: auto;
        min-width: 16;
        border: solid $accent;
        content-align: center middle;
        text-align: center;
        padding: 0 1;
        margin: 1 0 0 0;
    }

    /* Readable keyboard. Key width is set by _resize_board so the keyboard
       spans about the board width; height stays fixed and legible. */
    #keyboard {
        width: 100%;
        height: auto;
        align: center middle;
        margin-top: 1;
    }
    .key-row {
        width: 100%;
        height: auto;
        align: center middle;
    }
    .key {
        width: 5;
        min-width: 3;
        height: 3;
        margin: 1 1;
        background: #565a63;
        color: white;
    }
    .wide {
        width: 8;
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
    """

    def action_quit(self) -> None:
        self.exit()

    def on_mount(self) -> None:
        self.theme = "atom-one-dark"
        self.push_screen(WelcomeScreen())


if __name__ == "__main__":
    WordleCli().run()
