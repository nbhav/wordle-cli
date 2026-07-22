"""
Ui for the Wordle cli app
"""
# Python Imports
from enum import StrEnum

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen, ModalScreen
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

# Selector tokens are split by role so each kind has one home. Widget *type*
# selectors (Screen, GameScreen, ...) live only in wordle.tcss as literals —
# they're class names, and Textual has no way to inject Python values into CSS,
# so these two enums are the single source of truth for the *Python* side only
# (query_one / add_class / id= / classes=). The .tcss mirrors the same strings.
class DomId(StrEnum):
    """Widget ids — used as ``#id`` selectors and in ``query_one`` / ``id=``."""
    WELCOME_TEXT = "welcome-text"
    GAME_OVER_DIALOG = "game-over-dialog"
    GAME_OVER_TITLE = "game-over-title"
    GAME_OVER_MESSAGE = "game-over-message"
    GAME_OVER_BUTTONS = "game-over-buttons"
    GAME = "game"
    HEADER_BAR = "header-bar"
    GAME_HEADER = "game-header"
    GUESS_SCREEN = "guess_screen"
    INPUT_BAR = "input-bar"
    CURRENT_WORD = "current-word"
    KEYBOARD = "keyboard"
    PLAY_AGAIN = "play-again"
    QUIT_GAME = "quit-game"


class CssClass(StrEnum):
    """Style classes — used as ``.class`` selectors and in ``add_class`` etc."""
    GUESS_ROW = "guess-row"
    KEY_ROW = "key-row"
    KEY = "key"
    WIDE = "wide"
    CELL = "cell"
    MATCH = "match"
    PRESENT = "present"
    ABSENT = "absent"

class WelcomeScreen(Screen):
    BINDINGS = [("enter", "start_game", "Start")]

    def compose(self) -> ComposeResult:
        yield Static("Welcome to Wordle CLI\n\nHit Enter to start", id=DomId.WELCOME_TEXT)
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

    _STATUS_CLASS = {
        LetterStatus.MATCH: CssClass.MATCH,
        LetterStatus.EXISTS: CssClass.PRESENT,
        LetterStatus.DOES_NOT_EXIST: CssClass.ABSENT,
    }

    def __init__(self):
        super().__init__()
        self._current_letters = []
        self._game = WordleCliBase(words_file_path=WORDS_FILE_PATH, words_guess_file_path=WORDS_GUESS_PATH, word_length=WORD_LENGTH)
        self._total_rows = self._game.total_guesses
        self._current_row = 0
        self._game_over = False

    def compose(self) -> ComposeResult:
        # One container holds the whole game so everything sizes relative to it
        # (and thus to the terminal) via the fractional units in the CSS.
        with Vertical(id=DomId.GAME):
            with Horizontal(id=DomId.HEADER_BAR):
                yield Static("WordleCli", id=DomId.GAME_HEADER)

            with Vertical(id=DomId.GUESS_SCREEN):
                for row_idx in range(self._total_rows):
                    with Horizontal(classes=CssClass.GUESS_ROW):
                        for col_idx in range(WORD_LENGTH):
                            yield Static("", id=f"cell-{row_idx}-{col_idx}", classes=CssClass.CELL)

            with Horizontal(id=DomId.INPUT_BAR):
                yield Static("", id=DomId.CURRENT_WORD)

            with Vertical(id=DomId.KEYBOARD):
                for row in KEYBOARD_ROWS:
                    with Horizontal(classes=CssClass.KEY_ROW):
                        for key in row:
                            btn_id = "key-backspace" if key == "⌫" else f"key-{key}"
                            wide = key in ("ENTER", "⌫")
                            classes = f"{CssClass.KEY} {CssClass.WIDE}" if wide else CssClass.KEY
                            yield Button(key, id=btn_id, classes=classes)

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
        for cell in self.query(f".{CssClass.CELL}"):
            cell.styles.width = cell_w
            cell.styles.height = cell_h

        # Header and input bar span the board width so they read as one column.
        board_w = cols * cell_w + cols + 1  # tiles + collapsed 1-col margins
        self.query_one(f"#{DomId.GAME_HEADER}").styles.width = board_w
        self.query_one(f"#{DomId.CURRENT_WORD}").styles.width = board_w

        # Keys scale with the tile (a bit under a tile wide) so the keyboard
        # stays proportional to the board and the keys aren't thin slivers.
        key_w = max(4, cell_w * 2 // 3)
        for button in self.query(f".{CssClass.KEY}"):
            # Wide keys (ENTER / backspace) need room for the "ENTER" label.
            button.styles.width = key_w + 3 if button.has_class("wide") else key_w

    def action_restart(self) -> None:
        self._game.reset_game()
        self._current_letters = []
        self._current_row = 0
        self._game_over = False
        self.query_one(f"#{DomId.CURRENT_WORD}", Static).update("")

        for cell in self.query(f".{CssClass.CELL}").results(Static):
            cell.update("")
            cell.remove_class(CssClass.MATCH)
            cell.remove_class(CssClass.PRESENT)
            cell.remove_class(CssClass.ABSENT)
        for button in self.query(Button):
            button.remove_class(CssClass.MATCH)
            button.remove_class(CssClass.PRESENT)
            button.remove_class(CssClass.ABSENT)

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
        self.query_one(f"#{DomId.CURRENT_WORD}", Static).update("".join(self._current_letters).upper())

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
        self.query_one(f"#{DomId.CURRENT_WORD}", Static).update("")

        if result.outcome == GuessStatus.GAME_WON:
            self._game_over = True
            self._show_game_over(won=True)
        elif result.outcome == GuessStatus.GAME_OVER:
            self._game_over = True
            self._show_game_over(won=False)

    def _show_game_over(self, won: bool) -> None:
        """Overlay the end-of-game dialog on top of the final board."""
        self.app.push_screen(
            GameOverScreen(
                won=won,
                answer=self._game.answer,
                guesses_used=self._current_row,  # already advanced past the last guess
                total_guesses=self._total_rows,
            ),
            self._on_game_over_result,
        )

    def _on_game_over_result(self, play_again: bool | None) -> None:
        if play_again:
            # Reuse the existing restart path (clears board, keyboard, state) and
            # hand keys back to the screen so the next round types normally.
            self.action_restart()
            self.set_focus(None)
        else:
            self.app.exit()

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
            button.set_classes(f"{CssClass.KEY} {CssClass.MATCH}")
        elif status == LetterStatus.EXISTS and not button.has_class(CssClass.MATCH):
            button.set_classes(f"{CssClass.KEY} {CssClass.PRESENT}")
        elif status == LetterStatus.DOES_NOT_EXIST and not button.has_class(CssClass.MATCH) and not button.has_class(CssClass.PRESENT):
            button.set_classes(f"{CssClass.KEY} {CssClass.ABSENT}")


class GameOverScreen(ModalScreen[bool]):
    """End-of-game overlay. Dismisses True to play again, False to quit."""

    BINDINGS = [("escape", "quit", "Quit")]

    def __init__(self, won: bool, answer: str, guesses_used: int, total_guesses: int):
        super().__init__()
        self._won = won
        self._answer = answer
        self._guesses_used = guesses_used
        self._total_guesses = total_guesses

    def compose(self) -> ComposeResult:
        answer_line = f"The word was {self._answer.upper()}"
        if self._won:
            title = "You win \U0001F389"
            message = f"Solved in {self._guesses_used}/{self._total_guesses}\n{answer_line}"
        else:
            title = "Game over"
            message = answer_line

        with Vertical(id=DomId.GAME_OVER_DIALOG):
            yield Static(title, id=DomId.GAME_OVER_TITLE)
            yield Static(message, id=DomId.GAME_OVER_MESSAGE)
            with Horizontal(id=DomId.GAME_OVER_BUTTONS):
                yield Button("Play again", id=DomId.PLAY_AGAIN, variant="success")
                yield Button("Quit", id=DomId.QUIT_GAME, variant="error")

    def on_mount(self) -> None:
        # Affirmative default: a stray Enter (e.g. left over from the winning
        # guess) plays again rather than quitting the app.
        self.query_one(f"#{DomId.PLAY_AGAIN}", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == DomId.PLAY_AGAIN)

    def action_quit(self) -> None:
        self.dismiss(False)


class WordleCli(App):
    BINDINGS = [("ctrl+r", "restart", "Restart"), ("ctrl+c", "quit", "Quit")]

    # CSS lives in a sibling .tcss so it gets real CSS tooling (highlighting,
    # `textual run --dev` hot reload) with no brace-escaping. Textual resolves
    # the path against this module's directory.
    CSS_PATH = "wordle.tcss"

    def action_quit(self) -> None:
        self.exit()

    def action_restart(self) -> None:
        """Start a fresh game (new word, clean board) from any screen.

        While playing, GameScreen's own ctrl+r binding takes priority and
        resets in place; this backs the app-wide binding so ctrl+r also works
        from the welcome screen."""
        self.switch_screen(GameScreen())

    def on_mount(self) -> None:
        self.theme = "atom-one-dark"
        self.push_screen(WelcomeScreen())


if __name__ == "__main__":
    WordleCli().run()
