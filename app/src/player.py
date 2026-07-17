# Python Imports
from dataclasses import dataclass

# Reference: https://docs.python.org/3/library/dataclasses.html
@dataclass
class Player:
    games_won :int
    games_played :int
