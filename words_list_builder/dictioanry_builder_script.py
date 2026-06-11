from wordfreq import zipf_frequency
from nltk.corpus import words

all_words = {w.lower() for w in words.words() if w.isalpha()}

# Existing: 5-letter words directly from corpus
five_letter = {w for w in all_words if len(w) == 5}

# Filter by frequency
THRESHOLD = 2.2
word_list = [w for w in five_letter if zipf_frequency(w, "en") >= THRESHOLD]

print(len(word_list))


textfile_words_lst = []
with open(file="words.txt") as f:
   textfile_words_lst = [ line.strip() for line in f if len(line.strip()) == 5]

print(len(textfile_words_lst))

text_file_post_freq_map = [w for w in textfile_words_lst if zipf_frequency(w, "en") >= THRESHOLD]

print(len(text_file_post_freq_map))

words_set =set(word_list + text_file_post_freq_map)

print(len(words_set))

with open("temp.txt", 'w') as f:
   for word in words_set:
      f.write(word + "\n")