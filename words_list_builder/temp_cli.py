"""
Wordle Cli game base logic
Note: Likely needs a refactor when incorporating TUI 
"""

import os
import random

WORDS_FILE_PATH="temp.txt"

class WordleCli:

    def __init__ (self, words_file_path: str, word_length: int = 5, total_guesses: int = 5):
        # Word length and total guesses
        self.word_length = word_length
        self.total_guesses = total_guesses
        
        # These should be set by __read_file
        self.words_list = list()
        self.words_set = set()

        # Reading data from file
        self.__read_file(words_file_path)
        self.chosen_word = random.choice(self.words_list)

        # To be used during execution
        self.user_guess_set = set()


    def __read_file(self, file_path):
        """
            Reads words from the words file and adds it to member attr of
            the class
        """
        if file_path is None:
            raise ValueError(f"None used for file_path {file_path}")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(file_path) as f:
            for line in f:
                word = line.strip()
                if len(word) == self.word_length:
                    self.words_set.add(word.lower())

        if len(self.words_set) == 0:
            raise ValueError("Found no words from the file to use")
        
        # Only doing this so we can grab word by idx using random.choice  
        self.words_list = list(self.words_set)


    def compare_word_to_guess(self, guess: str, actual: str):
    
    
    
        word_match = True
        for guess_letter, actual_letter in zip(guess, actual):
            if guess_letter != actual_letter:
                print(f"{guess_letter} is invalid")
                word_match = False
            else:
                print(f"{guess_letter} is valid")
        
        return word_match



    def run_game(self):
        try:
            while( self.total_guesses > 0 ):
                user_guess = input("Guess a word?, Guess must be five letters\n")
                user_guess = user_guess.lower()
                
                if user_guess == self.chosen_word:
                    print("Congrats you have guessed the right word")
                    break
                
                if len(user_guess) != 5:
                    print(f"Invalid guess made: {user_guess} not enough chars")
                    continue

                if user_guess not in words_set:
                    print(f"Invalid word used to guess: {user_guess}")
                    continue

                if user_guess in user_guess_list:
                    print(f"Guess has already been made {user_guess}")
                    continue
                
                user_guess_list.add(user_guess)
                compare_bool = compare_word_to_guess(user_guess, word_to_guess)
                if compare_bool:
                    print("Conrgats you finished the puzzle")
                    break

                
                
                
                cur_guesses -= 1
                print("Guesses already made:")
                for guess in user_guess_list:
                    print(f"-- {guess}\n")

                if cur_guesses == 0:
                    print(f"Sorry you  have run out guesses the word was {word_to_guess}")
        except KeyboardInterrupt:
            print("Thank you for playing!")



def main():
    cli_game = WordleCli(words_file_path=WORDS_FILE_PATH)
    cli_game.run_game()

if __name__ == "__main__":
    main()

    

