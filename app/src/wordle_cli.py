"""
Wordle Cli game base logic
Note: Likely needs a refactor when incorporating TUI 
Note: Should add user class using pickle to save state between runs for highscore and what not
Note: Should also reset game if user wants to continue
Note: Add option for user to pick word length and num guesses
Note: Save score data
Note: add more options for bigger games like > 5 chars
Note: Add log to denote how many words got loaded from each file
"""

# Python Imports
from collections import Counter
from enum import Enum
import os
import random
from pathlib import Path
from logging import Logger
from dataclasses import dataclass


logger = Logger(__name__)

# Enum class for
class LetterStatus(Enum):
    DOES_NOT_EXIST = "absent"
    EXISTS = "exists"
    MATCH = "match"

class GuessStatus(Enum):
    OK = "ok"
    INVALID_LENGTH = "invalid_length"
    GUESS_ALREADY_MADE = "guess_already_made"
    NOT_IN_WORD_LIST = "not_in_word_list"
    GAME_OVER = "game_over"
    GAME_WON = "game_won"

@dataclass
class GuessResult:
    outcome: GuessStatus
    guess: list[dict]

class WordleCliBase:

    def __init__ (self, words_file_path: str, words_guess_file_path: str, word_length: int = 5, total_guesses: int = 6):
        # Word length and total guesses

        self.__word_length = word_length        
        self.__inputted_total_guesses = total_guesses # Saving orginial total guesses in case of reset state
        self.total_guesses = total_guesses

        # These should be set by __read_file
        self.__words_set = self.__read_file(words_file_path)
        self.__guess_set = self.__read_file(words_guess_file_path)

        if len(self.__words_set) == 0 or len(self.__guess_set) == 0:
            raise ValueError("Words for guessing are not properly ingested")
        
        # Reference: https://www.geeksforgeeks.org/python/select-random-element-from-set-in-python/
        self.__chosen_word = random.choice(list(self.__words_set)) 

        # Get freq count of all the letters in the word
        self.__chosen_word_counter = Counter(self.__chosen_word)

        # To be used during execution
        self.__user_guess_map = {}

    def __read_file(self, file_path) -> set[str]:
        """
            Reads words from the words file and adds it to member attr of
            the class
        """



        words_set = set()
        if file_path is None:
            raise ValueError(f"None used for file_path {file_path}")
        

        file_path = Path(__file__).resolve().parent.joinpath(file_path)
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(file_path) as f:
            for line in f:
                word = line.strip()
                if len(word) == self.__word_length:
                    words_set.add(word.lower())

        if len(words_set) == 0:
            raise ValueError("Found no words from the file to use")
        
        # Only doing this so we can grab word by idx using random.choice  
        return words_set


    def __compare_word_to_guess(self, guess: str) -> bool:
        """Score every letter of the guess and return whether it fully matches
        the chosen word."""
        guess_list = self.__get_guess_from_user_guess_map(guess=guess)

        # make a copy of the freq map, since if count of letter in guess > count of letter in actual
        # then we report as invalid not exists for the letters past the count
        actual_letter_counter = self.__chosen_word_counter.copy()

        letter_key = "letter"
        match_status_key = "match_status"

        valid_matches = Counter(guess_letter[letter_key] for guess_letter, actual_letter in zip (guess_list, self.__chosen_word) if guess_letter[letter_key] == actual_letter)

        # we need to capture how many letters are left over 
        union_diff = actual_letter_counter - valid_matches
        
        for guess_letter, actual_letter in zip (guess_list, self.__chosen_word):
            if guess_letter[letter_key] == actual_letter:
                guess_letter[match_status_key] = LetterStatus.MATCH
            elif  guess_letter[letter_key] in self.__chosen_word and union_diff[guess_letter[letter_key]] > 0:
                guess_letter[match_status_key] = LetterStatus.EXISTS
                union_diff[guess_letter[letter_key]] -= 1
            else:
                guess_letter[match_status_key] = LetterStatus.DOES_NOT_EXIST

        return guess == self.__chosen_word

    def __get_guess_from_user_guess_map(self, guess: str) -> list [dict]:
        """
        gets the dictionary for a given guess, should be pre_genereated already
        """
        return self.__user_guess_map[guess]

    def __add_user_guess_to_guess_dict(self, guess: str) -> None:        
        """
        Adds a user guess to the dict with a mapping of index and match_status for each letter in the word
        """
        self.__user_guess_map[guess] = [{"letter": letter, "match_status": None} for letter in guess]


    def get_user_guess_map(self):
        return self.__user_guess_map.copy()
    
    def print_guess_dict(self) -> None:
        logger.debug(msg="\nGuesses already made:\n")
        for k in self.__user_guess_map.keys():
            logger.debug(f"Guess: {k}")
            logger.debug(self.__user_guess_map[k])


    def submit_guess(self, user_guess: str) -> GuessResult:
        
        if user_guess is None:
            return GuessResult(GuessStatus.INVALID_LENGTH, [])
        
        user_guess = user_guess.strip().lower()

        if len(user_guess) != self.__word_length:
            logger.debug(f"Invalid guess made: {user_guess} incorrect num of characters")
            return GuessResult(GuessStatus.INVALID_LENGTH, [])

        # check to see if guess is a valid guess, the guess words will contain all the base words + extras
        if user_guess not in self.__guess_set:
            logger.debug(f"Invalid word used to guess: {user_guess}")
            return GuessResult(GuessStatus.NOT_IN_WORD_LIST, [])

        if user_guess in self.__user_guess_map:
            logger.debug(f"Guess has already been made {user_guess}")
            return GuessResult(GuessStatus.GUESS_ALREADY_MADE, [])


        # Add user guess to the guess set
        self.__add_user_guess_to_guess_dict(user_guess)
        is_win = self.__compare_word_to_guess(guess=user_guess)
        self.print_guess_dict()
        self.total_guesses -= 1

        guess_list = self.__get_guess_from_user_guess_map(user_guess)
        if is_win:
            return GuessResult(GuessStatus.GAME_WON, guess_list)
        if self.total_guesses <= 0:
            return GuessResult(GuessStatus.GAME_OVER, guess_list)
        return GuessResult(GuessStatus.OK, guess_list)

    @property
    def answer(self) -> str:
        """The current target word (used to reveal it when the game is lost)."""
        return self.__chosen_word


    def reset_game(self):
        logger.debug("Resetting the game")
        self.total_guesses =  self.__inputted_total_guesses
        # Reference: https://www.geeksforgeeks.org/python/select-random-element-from-set-in-python/
        self.__chosen_word = random.choice(list(self.__words_set)) 

        # Get freq count of all the letters in the word
        self.__chosen_word_counter = Counter(self.__chosen_word)

        # To be used during execution
        self.__user_guess_map = {}
