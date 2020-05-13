import re
import os
import logging

class CMU_Dictionary():
	truncated = re.compile(r'\w+\-$')                       ## truncated words
	intended = re.compile(r'^\+\w+')                        ## intended word (inserted by transcribers after truncated word)
	ing = re.compile(r"IN'$")                               ## words ending in "in'"
	CONSONANTS = ['B', 'CH', 'D', 'DH','F', 'G', 'HH', 'JH', 'K', 'L', 'M', 'N', 'NG', 'P', 'R', 'S', 'SH', 'T', 'TH', 'V', 'W', 'Y', 'Z', 'ZH']
	VOWELS = ['AA', 'AE', 'AH', 'AO', 'AW', 'AY', 'EH', 'ER', 'EY', 'IH', 'IY', 'OW', 'OY', 'UH', 'UW']
	DICT_ADDITIONS = "added_dict_entries.txt"               ## file for collecting uploaded additions to the dictionary

	def __init__(self, dictionary_file, *args, **kwargs):
		"""
		Initializes object by reading in CMU dictionary (or similar)

		@param string dictionary_file
		@param bool verbose: Whether to print debug information
		@param bool prompt: Whether to prompt the user to fix errors
		@author Keelan Evanini
		@author Christian Brickhouse
		"""
		self.logger = logging.getLogger(__name__)
		slef.logger.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)

		self.__config_flags( *args, **kwargs )

		self.dict_dir = dictionary_file
		self.cmu_dict = self.read(dictionary_file)
		## check that cmudict has entries
	    if len(self.cmu_dict) == 0:
			self.logger.warning('Dictionary %s is empty' % dictionary_file)
	    if verbose:
	        self.logger.debug("Read dictionary from file %s" % dictionary_file)

	def __config_flags( self, *args, **kwargs ):
		self.verbose = False
		self.prompt = False
		self.check = False
		if kwargs['verbose']:
			self.verbose = kwargs['verbose']
		if kwargs['prompt']:
			self.prompt = kwargs['prompt']
		if kwargs['check']:
			self.check = kwargs['check']

	def read(self,dictionary_file):
		"""
		@author Keelan Evanini
		"""
		cmu_dict = {}
		pat = re.compile('  *')                ## two spaces separating CMU dict entries
		with open(dictionary_file,'r') as cmu_dict_file:
			for line in cmu_dict_file.readlines():
				line = line.rstrip()
		        line = re.sub(pat, ' ', line)      ## reduce all spaces to one
		        word = line.split(' ')[0]          ## orthographic transcription
		        phones = line.split(' ')[1:]       ## phonemic transcription
		        if word not in cmu_dict:
		            cmu_dict[word] = [phones]       ## phonemic transcriptions represented as list of lists of phones
		        else:
		            if phones not in cmu_dict[word]:
		                cmu_dict[word].append(phones)   ## add alternative pronunciation to list of pronunciations
		return cmu_dict

	def add_dictionary_entries(self, infile, path='.'):
	    """
		Reads additional dictionary entries from file and adds them to the CMU dictionary

		@param string infile
		@param string path
		@raises IndexError
		"""

		cmu_dict = self.cmu_dict
		add_dict = {}

		with open(infile,'r') as f:
			lines = f.readlines()

	    ## process entries
	    for line in lines:
	        try:
				columns = line.strip().split('\t')
	            word = columns[0].upper()
	            transcriptions = [check_transcription(t.strip()) for t in columns[1].replace('"', '').split(',')]
				if len(transcriptions) == 0:
					continue
	        except IndexError as err:
	            self.logger.error("Incorrect format of dictionary input file %s:  Problem with line \"%s\"." % (infile, line))
				raise ValueError('Incorrect dictionary input file') from err
	        ## add new entry to CMU dictionary
	        if word not in cmu_dict:
	            cmudict[word] = transcriptions
	            add_dict[word] = transcriptions
	        else:   ## word might be in dict but transcriber might want to add alternative pronunciation
	            for t in trans:
	                if t not in cmudict[word]:  ## check that new transcription is not already in dictionary
	                    cmudict[word].append(t)
					if word not in add_dict:
						add_dict = []
					if t not in add_dict[word]:
                    	add_dict[word].append(t)

	    if self.verbose:
	        self.logger.debug("Added all entries in file %s to CMU dictionary." % os.path.basename(infile))

	    ## add new entries to the file for additional transcription entries
	    ## (merge with the existing DICT_ADDITIONS file to avoid duplicates)
		added_items_file = os.path.join(path,self.DICT_ADDITIONS)
	    if os.path.exists(added_items_file):  ## check whether dictionary additions file exists already
	        added_already = self.read(added_items_file)
	        new_dict = self.merge_dicts(added_already, add_dict)
	    else:
	        new_dict = add_dict
	    write_dict(added_items_file, dictionary=new_dict, mode='w')
	    if self.verbose:
	        self.logger.debug("Added new entries from file %s to file %s." % (os.path.basename(infile), DICT_ADDITIONS))

	def check_transcription(self, transcription):
	    """checks that the transcription entered for a word conforms to the Arpabet style"""
	    ## INPUT:  string w = phonetic transcription of a word (phones should be separated by spaces)
	    ## OUTPUT:  list final_trans = list of individual phones (upper case, checked for correct format)

	    ## convert to upper case and split into phones
	    phones = transcription.upper().split()

	    ## check that phones are separated by spaces
	    ## (len(w) > 3:  transcription could just consist of a single phone!)
	    if len(transcription) > 3 and len(phones) < 2:
			p = ("Something is wrong with your transcription:  %s.\n" % w)
			self.logger.warning(p)
			## Maybe worth raising an exception if self.prompt == False
			if self.prompt == True:
	        	p += "Did you forget to enter spaces between individual phones?\n"
				p += "Please enter new transcription:  "
	        	new_trans = input(p)
	        	transcription = check_transcription(new_trans)
	    else:
			for index, phone in enumerate(phones):
				try:
					check_phone(phone, transcription, index)
				except ValueError as err:
					raise err
	    return transcription

	def check_phone(self, phone, transcription, index):
	    """checks that a phone entered by the user is part of the Arpabet"""
	    ## INPUT:
	    ## string p = phone
	    ## string w = word the contains the phone (normal orthographic representation)
	    ## int i = index of phone in word (starts at 0)
	    ## OUTPUT:
	    ## string final_p or p = phone in correct format
		if len(p) == 3:
			if str(p[-1]) not in ['0', '1', '2']:
				raise ValueError("Unknown stress digit %s for vowel %s (at position %i) in word %s!\n" % (p[-1], p, i+1, w))
			if p[:-1] not in self.VOWELS:
				raise ValueError("Unknown vowel %s (at position %i) in word %s!\n" % (p[:-1], i+1, w))
		elif len(p) <= 2:
			if p in self.VOWELS:
				raise ValueError("You forgot to enter the stress digit for vowel %s (at position %i) in word %s!\n" % (p, i+1, w))
			if p not in self.CONSONANTS:
				raise ValueError("Unknown phone %s (at position %i) in word %s!\n" % (p, i+1, w))
		else:
			raise ValueError("Unknown phone %s (at position %i) in word %s!\n" % (p, i+1, w))

	def check_word(word, next_word='', unknown={}, line=''):
	    """checks whether a given word's phonetic transcription is in the CMU dictionary;
	    adds the transcription to the dictionary if not"""
	    ## INPUT:
	    ## string word = word to be checked
	    ## string next_word = following word
	    ## OUTPUT:
	    ## dict unknown = unknown or truncated words (needed if "check transcription" option is selected; remains empty otherwise)
	    ## - modifies CMU dictionary (dict cmudict)
	    cmudict = self.cmu_dict

	    clue = ''

	    ## dictionary entry for truncated words may exist but not be correct for the current word
	    ## (check first because word will be in CMU dictionary after procedure below)
	    if self.truncated.search(word) and word in cmudict:
	        ## check whether following word is "clue" word?
	        if self.intended.search(next_word):
	            clue = next_word
	        ## do not prompt user for input if "check transcription" option is selected
	        ## add truncated word together with its proposed transcription to list of unknown words
	        ## (and with following "clue" word, if present)
	        if options.check:
	            if clue:
	                unknown[word] = (cmudict[word], clue.lstrip('+'), line)
	            else:
	                unknown[word] = (cmudict[word], '', line)
	        ## prompt user for input
	        else:
	            ## assume that truncated words are taken care of by the user if an import file is specified
	            ## also, do not prompt user if "noprompt" option is selected
	            if not (options.importfile or options.noprompt):
	                print "Dictionary entry for truncated word %s is %s." % (word, cmudict[word])
	                if clue:
	                    print "Following word is %s." % next_word
	                correct = raw_input("Is this correct?  [y/n]")
	                if correct != "y":
	                    transcription = prompt_user(word, clue)
	                    cmudict[word] = [transcription]

	    elif word not in cmudict and word not in STYLE_ENTRIES:
	        ## truncated words:
	        if self.truncated.search(word):
	            ## is following word "clue" word?  (starts with "+")
	            if self.intended.search(next_word):
	                clue = next_word
	        ## don't do anything if word itself is a clue word
		elif self.intended.search(word):
	            return unknown
	        ## don't do anything for unclear transcriptions:
	        elif word == '((xxxx))':
	            return unknown
	        ## uncertain transcription:
	        elif start_uncertain.search(word) or end_uncertain.search(word):
	            if start_uncertain.search(word) and end_uncertain.search(word):
	                word = word.replace('((', '')
	                word = word.replace('))', '')
	                ## check if word is in dictionary without the parentheses
	                check_word(word, '', unknown, line)
	                return unknown
	            else:  ## This should not happen!
	                error= "ERROR!  Something is wrong with the transcription of word %s!" % word
	                errorhandler(error)
	        ## asterisked transcriptions:
	        elif word and word[0] == "*":
	            ## check if word is in dictionary without the asterisk
	            check_word(word[1:], '', unknown, line)
	            return unknown
	        ## generate new entries for "-in'" words
	        if self.ing.search(word):
	            gword = self.ing.sub("ING", word)
	            ## if word has entry/entries for corresponding "-ing" form:
	            if gword in cmudict:
	                for t in cmudict[gword]:
	                    ## check that transcription entry ends in "- IH0 NG":
	                    if t[-1] == "NG" and t[-2] == "IH0":
	                        tt = t
	                        tt[-1] = "N"
	                        tt[-2] = "AH0"
	                        if word not in cmudict:
	                            cmudict[word] = [tt]
	                        else:
	                            cmudict[word].append(tt)
	                return unknown
	        ## if "check transcription" option is selected, add word to list of unknown words
	        if options.check:
	            if clue:
	                unknown[word] = ("", clue.lstrip('+'), line)
	            else:
	                unknown[word] = ("", "", line)
	            if options.verbose:
	                print "\tUnknown word %s : %s." % (word.encode('ascii', 'replace'), line.encode('ascii', 'replace'))

	        ## otherwise, promput user for Arpabet transcription of missing word
	        elif not options.noprompt:
	            transcription = prompt_user(word, clue)
	            ## add new transcription to dictionary
	            if transcription:  ## user might choose to skip this word
	                cmudict[word] = [transcription]

	    return unknown

	def merge_dicts(self, d1, d2):
	    """merges two versions of the CMU pronouncing dictionary"""
	    ## for each word, each transcription in d2, check if present in d1
	    for word in d2:
	        ## if no entry in d1, add entire entry
	        if word not in d1:
	            d1[word] = d2[word]
	        ## if entry in d1, check whether additional transcription variants need to be added
	        else:
	            for t in d2[word]:
	                if t not in d1[word]:
	                    d1[word].append(t)
	    return d1

	def write_dict(self, fname, dictionary=None):
	    """writes the new version of the CMU dictionary (or any other dictionary) to file"""

	    ## default functionality is to write the CMU pronunciation dictionary back to file,
	    ## but other dictionaries or parts of dictionaries can also be written/appended
	    if not dictionary:
	        dictionary = self.cmu_dict
		out_string = ''
	    ## sort dictionary before writing to file
	    keys = dictionary.keys()
	    keys.sort()
	    for word in keys:
	        ## make a separate entry for each pronunciation in case of alternative entries
			if len(dictionary[word]) < 1:
				continue
	        for transcription in dictionary[word]:
	                out_string += word + '  '     ## two spaces separating CMU dict entries from phonetic transcriptions
	                for phone in transcription:
	                    out_string += phone + ' '  ## list of phones, separated by spaces
	                out_string += '\n'         ## end of entry line

		with open(fname,'w') as f:
			f.write(out_string)

	def _write_words(self, unknown):
	    """writes unknown words to file (in a specified encoding)"""
		out_string = ''
	    for w in unknown:
	        out_string += w + '\t'
	        if unknown[w][0]:
				## put suggested transcription(s) for truncated word into second column, if present:
				out_string += ','.join([' '.join(i) for i in unknown[w][0]])
			out_string += '\t'
			if unknown[w][1]:
				## put following clue word in third column, if present:
				out_string += unknown[w][1]
			## put line in fourth column:
			out_string += '\t' + unknown[w][2] + '\n'
		return out_string

	def write_unknown_words(self, unknown, fname="unknown.txt"):
		"""writes the list of unknown words to file"""
		with open(fname,'w') as f:
			self._write_words(unknown)
