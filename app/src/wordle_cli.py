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

# Reference: https://github.com/Kinkelin/WordleCompetition/tree/main/data/official
# Words list from wordle offical
# File path for all the valid words that will be shown to users
WORDS_FILE_PATH="../../valid_words.txt"

# File path so users can guess a large variety of words
WORDS_GUESS_PATH="../../allowed_guess.txt"


# Enum class for
class WordStatus(Enum):
    DOES_NOT_EXIST = "Grey"
    EXISTS = "Yellow"
    MATCH = "Green"


class WordleCli:

    def __init__ (self, words_file_path: str, words_guess_file_path: str, word_length: int = 5, total_guesses: int = 6):
        # Word length and total guesses
        self.__word_length = word_length
        self.__total_guesses = total_guesses
        
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
        self.__user_guess_invalid_letters_set = set()
        self.__user_guess_valid_letters_set = set()
        self.__user_guess_map = {}

    def __read_file(self, file_path) -> set[str]:
        """
            Reads words from the words file and adds it to member attr of
            the class
        """
        words_set = set()
        if file_path is None:
            raise ValueError(f"None used for file_path {file_path}")
        
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

        if guess == self.__chosen_word:
            return True

        guess_list = self.__get_guess_from_user_guess_map(guess=guess)

        # make a copy of the freq map, since if count of letter in guess > count of letter in actual
        # then we report as invalid not exists for the letters past the count
        actual_letter_counter = self.__chosen_word_counter.copy()

        letter_key = "letter"
        match_status_key = "match_status"

        valid_matches = Counter(guess_letter[letter_key] for guess_letter, actual_letter in zip (guess_list, self.__chosen_word) if guess_letter[letter_key] == actual_letter)

        union_diff = actual_letter_counter - valid_matches
        
        for guess_letter, actual_letter in zip (guess_list, self.__chosen_word):
            if guess_letter[letter_key] == actual_letter:
                guess_letter[match_status_key] = WordStatus.MATCH
            elif  guess_letter[letter_key] in self.__chosen_word and union_diff[guess_letter[letter_key]] > 0:
                guess_letter[match_status_key] = WordStatus.EXISTS
                union_diff[letter_key] -= 1
            else:
                guess_letter[match_status_key] = WordStatus.DOES_NOT_EXIST

        return False

    def __get_guess_from_user_guess_map(self, guess: str) -> dict:
        """
        gets the dictionary for a given guess, should be pre_genereated already
        """
        return self.__user_guess_map[guess]

    def __add_user_guess_to_guess_dict(self, guess: str) -> None:        
        """
        Adds a user guess to the dict with a mapping of index and match_status for each letter in the word
        """
        self.__user_guess_map[guess] = [{"letter": letter, "match_status": None} for letter in guess]

    
    def print_guess_dict(self) -> None:
        print("\nGuesses already made:\n")
        for k in self.__user_guess_map.keys():
            print(f"Guess: {k}")
            print(self.__user_guess_map[k])


    def run_game(self) -> None:
        try:
            print(self.__chosen_word)
            while( self.__total_guesses > 0 ):
                user_guess = input(f"Guess a word?, Guess must be {self.__word_length} letters\n")
                user_guess = user_guess.strip().lower()

                # For future expansion to multiple word lengths 
                if len(user_guess) != self.__word_length:
                    print(f"Invalid guess made: {user_guess} incorrect num of characters")
                    continue

                # check to see if guess is a valid guess, the guess words will contain all the base words + extras
                if user_guess not in self.__guess_set:
                    print(f"Invalid word used to guess: {user_guess}")
                    continue

                if user_guess in self.__user_guess_map:
                    print(f"Guess has already been made {user_guess}")
                    continue
                


                # Add user guess to the guess set
                self.__add_user_guess_to_guess_dict(user_guess)
                self.__compare_word_to_guess(guess=user_guess)
                self.print_guess_dict()
                self.__total_guesses -= 1

                if self.__total_guesses == 0:
                    print(f"Sorry you have run out guesses the word was {self.__chosen_word}")
        
        except KeyboardInterrupt:
            raise SystemExit(0, "Thank you for playing!!")



def main():
    cli_game = WordleCli(words_file_path=WORDS_FILE_PATH, words_guess_file_path=WORDS_GUESS_PATH)
    cli_game.run_game()

if __name__ == "__main__":
    main()

    

