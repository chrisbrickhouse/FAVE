
class TranscriptProcesor():
	start_uncertain = re.compile(r'(\(\()')                 ## beginning of uncertain transcription
	end_uncertain = re.compile(r'(\)\))')                   ## end of uncertain transcription
	hyphenated = re.compile(r'(\w+)-(\w+)')                 ## hyphenated words
	intended = re.compile(r'^\+\w+')                        ## intended word (inserted by transcribers after truncated word)
	uncertain = re.compile(r"\(\(([\*\+]?['\w]+\-?)\)\)")   ## uncertain transcription (single word)
	## NOTE:  earlier versions allowed uncertain/unclear transcription to use only one parenthesis,
	##        but this is now back to the strict definition
	##        (i.e. uncertain/unclear transcription spans MUST be enclosed in DOUBLE parentheses)
	unclear = re.compile(r'\(\(\s*\)\)')                    ## unclear transcription (empty double parentheses)

	def __init__(self, pronunciation_dictionary, check=False):
		## "flag_uncertain" indicates whether we are currently inside an uncertain section of transcription
	    ## (switched on and off by the beginning or end of double parentheses:  "((", "))")
		self.logger = logging.getLogger(__name__)
		slef.logger.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)

	    self.flag_uncertain = False
	    self.last_beg_uncertain = ''
	    self.last_end_uncertain = ''
		self.check = check
		self.temp_dict_dir = None
		if not isinstance(pronunciation_dictionary,'CMU_Dictionary'):
			raise ValueError('pronunciation_dictionary must be a CMU_Dictionary object')
		self.dictionary = pronunciation_dictionary

	def check_dictionary_entries(self, transcript_lines, wavfile):
		"""checks that all words in lines have an entry in the CMU dictionary;
		if not, prompts user for Arpabet transcription and adds it to the dict file.
		If "check transcription" option is selected, writes list of unknown words to file and exits."""
		## INPUT:  list of lines to check against CMU dictionary
		## OUTPUT:  list newlines = list of list of words for each line (processed)
		## - prompts user to modify CMU dictionary (cmudict) and writes updated version of CMU dictionary to file
		## - if "check transcription" option is selected, writes list of unknown words to file and exits

		newlines = []
		unknown = {}

		for line in transcript_lines:
			newwords = []
			## get list of preprocessed words in each line
			## This may lead to a race condition -CB
			words = self.preprocess_transcription(line.strip().upper())
			## check each word in transcription as to whether it is in the CMU dictionary:
			## (if "check transcription" option is not set, dict unknown will simply remain empty)
			for i, w in enumerate(words):
				if i < len(words) - 1:
					unknown = self.dictionary.check_word(w, words[i+1], unknown, line)
				else:
					unknown = self.dictionary.check_word(w, '', unknown, line)               ## last word in line
				## take "clue words" out of transcription:
				if not self.intended.search(self.uncertain.sub(r'\1', w)):
					newwords.append(w)
			newlines.append(newwords)

		## write new version of the CMU dictionary to file
		## (do this here so that new entries to dictionary will still be saved if "check transcription" option is selected
		## in addition to the "import transcriptions" option)
		#write_dict(options.dict)
		## NOTE:  dict will no longer be re-written to file as people might upload all kinds of junk
		##        Uploaded additional transcriptions will be written to a separate file instead (in add_dictionary_entries),
		##        to be checked manually and merged with the main dictionary at certain intervals


		## write temporary version of the CMU dict to file for use in alignment
		if not self.check:
			temp_dict = os.path.join(os.path.dirname(wavfile), '_'.join(os.path.basename(wavfile).split('_')[:2]) + "_" + "dict")
			self.logger.debug("temp_dict is %s." % temp_dict)
			self.dictionary.write_dict(temp_dict)
			if self.verbose:
				self.logger.debug("Written updated temporary version of CMU dictionary.")
			## forced alignment must use updated cmudict, not original one
			self.temp_dict_dir = temp_dict

		## "CHECK TRANSCRIPTION" OPTION:
		## write list of unknown words and suggested transcriptions for truncated words to file
		if self.check:
			self.write_unknown_words(unknown)
			print "Written list of unknown words in transcription to file %s." % options.check
			if __name__ == "__main__":
				sys.exit()

		## CONTINUE TO ALIGNMENT:
		else:
			## return new transcription (list of lists of words, for each line)
			return newlines

	def preprocess_transcription(self, line):
		"""preprocesses transcription input for CMU dictionary lookup and forced alignment"""
		## INPUT:  string line = line of orthographic transcription
		## OUTPUT:  list words = list of individual words in transcription

		flag_uncertain = self.flag_uncertain
		last_beg_uncertain = self.last_beg_uncertain
		last_end_uncertain = self.last_end_uncertain

		original_line = line

		## make "high school" into one word (for /ay0/ raising)
		line = line.replace('high school', 'highschool')

		## make beginning and end of uncertain transcription spans into separate words
		line = self.start_uncertain.sub(r' (( ', line)
		line = self.end_uncertain.sub(r' )) ', line)
		## correct a common transcription error (one dash instead of two)
		line = line.replace(' - ', ' -- ')
		## delete punctuation marks
		for p in [',', '.', ':', ';', '!', '?', '"', '%', '--']:
			line = line.replace(p, ' ')
		## delete initial apostrophes
		line = re.compile(r"(\s|^)'\b").sub(" ", line)
		## delete variable coding for consonant cluster reduction
		line = re.compile(r"\d\w(\w)?").sub(" ", line)
		## replace unclear transcription markup (empty parentheses):
		line = self.unclear.sub('((xxxx))', line)
		## correct another transcription error:  truncation dash outside of double parentheses will become a word
		line = line.replace(' - ', '')

		## split hyphenated words (but keep truncated words as they are!)
		## NOTE:  This also affects the interjections "huh-uh", "uh-huh" and "uh-oh".
		## However, should work fine just aligning individual components.
		line = self.hyphenated.sub(r'\1 \2', line)
		line = self.hyphenated.sub(r'\1 \2', line)   ## do this twice for words like "daughter-in-law"

		## split line into words:
		words = line.split()

		## add uncertainty parentheses around every word individually
		newwords = []
		for word in words:
			if word == "((":        ## beginning of uncertain transcription span
				if not flag_uncertain:
					self.flag_uncertain = True
					self.last_beg_uncertain = original_line
				else:
					msg = "Beginning of uncertain transcription span detected twice in a row\n"
					msg += ("Please close the the opening double parenthesis in line %s." % last_beg_uncertain)
					raise ValueError( msg )
			elif word == "))":      ## end of uncertain transcription span
				if flag_uncertain:
					self.flag_uncertain = False
					self.last_end_uncertain = original_line
				else:
					msg = "End of uncertain transcription span detected twice in a row\n"
					msg += "No opening double parentheses for line %s." % original_line
					raise ValueError( msg )
			else:  ## process words
				if flag_uncertain:
					newwords.append("((" + word + "))")
				else:
					newwords.append(word)

		return newwords

	def write_unknown_words(self, unknown):
	    """writes the list of unknown words to file"""
	        ## try ASCII output first:
	    try:
	        out = open(options.check, 'w')
	        write_words(out, unknown)
	    except UnicodeEncodeError:  ## encountered some non-ASCII characters
	        out = codecs.open(options.check, 'w', 'utf-16')
	        write_words(out, unknown)
