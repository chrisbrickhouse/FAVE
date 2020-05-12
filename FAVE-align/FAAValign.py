#!/usr/bin/env python

"""
Usage:  (python) FAAValign.py [options] soundfile.wav [transcription.txt] [output.TextGrid]

Aligns a sound file with the corresponding transcription text. The
transcription text is split into annotation breath groups, which are fed
individually as "chunks" to the forced aligner. All output is concatenated
into a single Praat TextGrid file.

INPUT:
- sound file
- tab-delimited text file with the following columns:
	first column:   speaker ID
	second column:  speaker name
	third column:   beginning of breath group (in seconds)
	fourth column:  end of breath group (in seconds)
	fifth column:   transcribed text
(If no name is specified for the transcription file, it will be assumed to
have the same name as the sound file, plus ".txt" extension.)

OUTPUT:
- Praat TextGrid file with orthographic and phonemic transcription tiers for
each speaker (If no name is specified, it will be given same name as the sound
file, plus ".TextGrid" extension.)


Options:

--version ("version"):

	Prints the program's version string and exits.

-h, --help ("help):

	Show this help message and exits.

-c [filename], --check=[filename] ("check transcription"):

	Checks whether phonetic transcriptions for all words in the transcription file can be found in the
	CMU Pronouncing Dictionary (file "dict").  Returns a list of unknown words.

-i [filename], --import=[filename] ("import dictionary entries"):

	Adds a list of unknown words and their corresponding phonetic transcriptions to the CMU Pronouncing
	Dictionary prior to alignment.  User will be prompted interactively for the transcriptions of any
	remaining unknown words.  File must be tab-separated plain text file.

-v, --verbose ("verbose"):

	Detailed output on status of dictionary check and alignment progress.

-d [filename], --dict=[filename] ("dictionary"):

	Specifies the name of the file containing the pronunciation dictionary.  Default file is "/model/dict".

-n, --noprompt ("no prompt"):

-t HTKTOOLSPATH, --htktoolspath=HTKTOOLSPATH
	Specifies the path to the HTKTools directory where the HTK executable files are located.  If not specified, the user's path will be searched for the location of the executable.

	User is not prompted for the transcription of words not in the dictionary, or truncated words.  Unknown words are ignored by the aligner.
"""

################################################################################
## PROJECT "AUTOMATIC ALIGNMENT AND ANALYSIS OF LINGUISTIC CHANGE"			##
## FAAValign.py															   ##
## written by Ingrid Rosenfelder											  ##
################################################################################

import os
import sys
import shutil
import re
import wave
import optparse
import time
import praat
import subprocess
import traceback
import codecs
import subprocess
import string


STYLE = ["style", "Style", "STYLE"]
STYLE_ENTRIES = ["R", "N", "L", "G", "S", "K", "T", "C", "WL", "MP", "SD", "RP"]

#TEMPDIR = "temp_FA"
TEMPDIR = ""
PRAATPATH = "/usr/local/bin/praat"					  ## this is just in case the wave module does not work (use Praat instead to determe the length of the sound file)
##PRAATPATH = "/Applications/Praat.app/Contents/MacOS/praat"  ## old setting on ingridpc.ling.upenn.edu

################################################################################

## This was the main body of Jiahong Yuan's original align.py
def align(wavfile, trs_input, outfile, FADIR='', SOXPATH='', HTKTOOLSPATH=''):
	"""calls the forced aligner"""
	## wavfile = sound file to be aligned
	## trsfile = corresponding transcription file
	## outfile = output TextGrid

	## change to Forced Alignment Toolkit directory for all the temp and preparation files
	if FADIR:
		os.chdir(FADIR)

	## derive unique identifier for tmp directory and all its file (from name of the sound "chunk")
	identifier = re.sub(r'\W|_|chunk', '', os.path.splitext(os.path.split(wavfile)[1])[0])
	## old names:  --> will have identifier added
	## - "tmp"
	## - "aligned.mlf"
	## - "aligned.results"
	## - "codetr.scp"
	## - "test.scp"
	## - "tmp.mlf"
	## - "tmp.plp"
	## - "tmp.wav"

	# create working directory
	os.mkdir("./tmp" + identifier)
	# prepare wavefile
	SR = prep_wav(wavfile, './tmp' + identifier + '/tmp' + identifier + '.wav', SOXPATH)

	# prepare mlfile
	prep_mlf(trs_input, './tmp' + identifier + '/tmp' + identifier + '.mlf', identifier)

	# prepare scp files
	fw = open('./tmp' + identifier + '/codetr' + identifier + '.scp', 'w')
	fw.write('./tmp' + identifier + '/tmp' + identifier + '.wav ./tmp' + identifier + '/tmp'+ identifier + '.plp\n')
	fw.close()
	fw = open('./tmp' + identifier + '/test' + identifier + '.scp', 'w')
	fw.write('./tmp' + identifier +'/tmp' + identifier + '.plp\n')
	fw.close()

	try:
		# call plp.sh and align.sh
		if HTKTOOLSPATH:  ## if absolute path to HTK Toolkit is given
			os.system(os.path.join(HTKTOOLSPATH, 'HCopy') + ' -T 1 -C ./model/' + str(SR) + '/config -S ./tmp' + identifier + '/codetr' + identifier + '.scp >> ./tmp' + identifier + '/blubbeldiblubb.txt')
			os.system(os.path.join(HTKTOOLSPATH, 'HVite') + ' -T 1 -a -m -I ./tmp' + identifier + '/tmp' + identifier +'.mlf -H ./model/' + str(SR) + '/macros -H ./model/' + str(SR) + '/hmmdefs  -S ./tmp' + identifier + '/test' + identifier+ '.scp -i ./tmp' + identifier + '/aligned' + identifier + '.mlf -p 0.0 -s 5.0 ' + options.dict + ' ./model/monophones > ./tmp' + identifier + '/aligned' + identifier + '.results')
		else:  ## find path via shell
			#os.system('HCopy -T 1 -C ./model/' + str(SR) + '/config -S ./tmp/codetr.scp >> blubbeldiblubb.txt')
			#os.system('HVite -T 1 -a -m -I ./tmp/tmp.mlf -H ./model/' + str(SR) + '/macros -H ./model/' + str(SR) + '/hmmdefs  -S ./tmp/test.scp -i ./tmp/aligned.mlf -p 0.0 -s 5.0 ' + options.dict + ' ./model/monophones > ./tmp/aligned.results')
			os.system('HCopy -T 1 -C ./model/' + str(SR) + '/config -S ./tmp' + identifier + '/codetr' + identifier + '.scp >> ./tmp' + identifier + '/blubbeldiblubb.txt')
			os.system('HVite -T 1 -a -m -I ./tmp' + identifier + '/tmp' + identifier +'.mlf -H ./model/' + str(SR) + '/macros -H ./model/' + str(SR) + '/hmmdefs  -S ./tmp' + identifier + '/test' + identifier+ '.scp -i ./tmp' + identifier + '/aligned' + identifier + '.mlf -p 0.0 -s 5.0 ' + options.dict + ' ./model/monophones > ./tmp' + identifier + '/aligned' + identifier + '.results')

		## write result of alignment to TextGrid file
		aligned_to_TextGrid('./tmp' + identifier + '/aligned' + identifier + '.mlf', outfile, SR)
		if options.verbose:
			print "\tForced alignment called successfully for file %s." % os.path.basename(wavfile)
	except Exception, e:
		FA_error = "Error in aligning file %s:  %s." % (os.path.basename(wavfile), e)
		## clean up temporary alignment files
		shutil.rmtree("./tmp" + identifier)
		raise Exception, FA_error
		##errorhandler(FA_error)

	## remove tmp directory and all files
	shutil.rmtree("./tmp" + identifier)


## This function is from Jiahong Yuan's align.py
## (originally called "TextGrid(infile, outfile, SR)")
def aligned_to_TextGrid(infile, outfile, SR):
	"""writes the results of the forced alignment (file "aligned.mlf") to file as a Praat TextGrid file"""

	f = open(infile, 'rU')
	lines = f.readlines()
	f.close()
	fw = open(outfile, 'w')
	j = 2
	phons = []
	wrds = []
##	try:
	while (lines[j] <> '.\n'):
		ph = lines[j].split()[2]  ## phone
		if (SR == 11025):  ## adjust rounding error for 11,025 Hz sampling rate
			## convert time stamps from 100ns units to seconds
			## fix overlapping intervals:  divide time stamp by ten first and round!
			st = round((round(float(lines[j].split()[0])/10.0, 0)/1000000.0)*(11000.0/11025.0) + 0.0125, 3)  ## start time
			en = round((round(float(lines[j].split()[1])/10.0, 0)/1000000.0)*(11000.0/11025.0) + 0.0125, 3)  ## end time
		else:
			st = round(round(float(lines[j].split()[0])/10.0, 0)/1000000.0 + 0.0125, 3)
			en = round(round(float(lines[j].split()[1])/10.0, 0)/1000000.0 + 0.0125, 3)
		if (st <> en):  ## 'sp' states between words can have zero duration
			phons.append([ph, st, en])  ## list of phones with start and end times in seconds

		if (len(lines[j].split()) == 5):  ## entry on word tier
			wrd = lines[j].split()[4].replace('\n', '')
			if (SR == 11025):
				st = round((round(float(lines[j].split()[0])/10.0, 0)/1000000.0)*(11000.0/11025.0) + 0.0125, 3)
				en = round((round(float(lines[j].split()[1])/10.0, 0)/1000000.0)*(11000.0/11025.0) + 0.0125, 3)
			else:
				st = round(round(float(lines[j].split()[0])/10.0, 0)/1000000.0 + 0.0125, 3)
				en = round(round(float(lines[j].split()[1])/10.0, 0)/1000000.0 + 0.0125, 3)
			if (st <> en):
				wrds.append([wrd, st, en])

		j += 1
##	except Exception, e:
##		FA_error = "Error in converting times from file %s in line %d for TextGrid %s:  %s." % (os.path.basename(infile), j + 1, os.path.basename(outfile), e)
##		errorhandler(FA_error)

##	try:
	#write the phone interval tier
	fw.write('File type = "ooTextFile short"\n')
	fw.write('"TextGrid"\n')
	fw.write('\n')
	fw.write(str(phons[0][1]) + '\n')
	fw.write(str(phons[-1][2]) + '\n')
	fw.write('<exists>\n')
	fw.write('2\n')
	fw.write('"IntervalTier"\n')
	fw.write('"phone"\n')
	fw.write(str(phons[0][1]) + '\n')
	fw.write(str(phons[-1][-1]) + '\n')
	fw.write(str(len(phons)) + '\n')
	for k in range(len(phons)):
		fw.write(str(phons[k][1]) + '\n')
		fw.write(str(phons[k][2]) + '\n')
		fw.write('"' + phons[k][0] + '"' + '\n')
##	except Exception, e:
##		FA_error = "Error in writing phone interval tier for TextGrid %s:  %s." % (os.path.basename(outfile), e)
##		errorhandler(FA_error)
##	try:
	#write the word interval tier
	fw.write('"IntervalTier"\n')
	fw.write('"word"\n')
	fw.write(str(phons[0][1]) + '\n')
	fw.write(str(phons[-1][-1]) + '\n')
	fw.write(str(len(wrds)) + '\n')
	for k in range(len(wrds) - 1):
		fw.write(str(wrds[k][1]) + '\n')
		fw.write(str(wrds[k+1][1]) + '\n')
		fw.write('"' + wrds[k][0] + '"' + '\n')
	fw.write(str(wrds[-1][1]) + '\n')
	fw.write(str(phons[-1][2]) + '\n')
	fw.write('"' + wrds[-1][0] + '"' + '\n')
##	except Exception, e:
##		FA_error = "Error in writing phone interval tier for TextGrid %s:  %s." % (os.path.basename(outfile), e)
##		errorhandler(FA_error)

	fw.close()


def check_arguments(args):
	"""returns sound file, transcription file and output TextGrid file from positional arguments from command line"""

	## no or too many positional arguments
	if len(args) == 0 or len(args) > 3:
		error = "ERROR!  Incorrect number of arguments: %s" % args
		errorhandler(error)
	## sound file must be present and first positional argument
	## EXCEPT when checking for unknown words!
	elif is_sound(args[0]) or options.check:
		## case A:  sound file is first argument
		if is_sound(args[0]):
			wavfile = check_file(args[0])
			if len(args) == 1:  ## only sound file given
				trsfile = check_file(replace_extension(wavfile, ".txt"))
				tgfile = replace_extension(wavfile, ".TextGrid")
			elif len(args) == 2:
				if is_text(args[1]):  ## sound file and transcription file given
					trsfile = check_file(args[1])
					tgfile = replace_extension(wavfile, ".TextGrid")
				elif is_TextGrid(args[1]):  ## sound file and output TextGrid given
					tgfile = args[1]
					trsfile = check_file(replace_extension(wavfile, ".txt"))  ## transcription file name must match sound file
			elif len(args) == 3:  ## all three arguments given
				trsfile = check_file(args[1])
				tgfile = args[2]
			else:  ## this should not happen
				error = "Something weird is going on here..."
				errorhandler(error)
		## case B:  unknown words check, no sound file
		elif options.check:
			wavfile = ''
			## if run from the command line, the first file must now be the transcription file
			## if run as a module, the first argument will be an empty string for the sound file, and the transcription file is still the second argument
			if (__name__ == "__main__" and is_text(args[0])) or (__name__ != "__main__" and is_text(args[1])):
				if (__name__ == "__main__" and is_text(args[0])):
					trsfile = check_file(args[0])
				elif (__name__ != "__main__" and is_text(args[1])):
					trsfile = check_file(args[1])
				tgfile = replace_extension(trsfile, ".TextGrid")  ## need to have a name for the TextGrid for the name of the outputlog (renamed from original name of the TextGrid later)
			else:
				error = "ERROR!  Transcription file needed for unknown words check."
				if __name__ == "__main__":
					print error
					sys.exit(parser.print_usage())
				else:
					raise Exception, error
		else:  ## this should not happen
			error = "Something weird is going on here!!!"
			errorhandler(error)
	else:  ## no sound file, and not checking unknown words
		error = "ERROR!  First argument to program must be sound file."
		if __name__ == "__main__":
			print error
			sys.exit(parser.print_usage())
		else:
			raise Exception, error

	return (wavfile, trsfile, tgfile)

def check_file(path):
	"""checks whether a file exists at a given location and is a data file"""

	if os.path.exists(path) and os.path.isfile(path):
		return path
	else:
		if __name__ == "__main__":
			print "ERROR!  File %s could not be found!" % path
			print "Current working directory is %s." % os.getcwd()
			newpath = raw_input("Please enter correct name or path for file, or type [q] to quit:  ")
			## emergency exit from recursion loop:
			if newpath in ['q', 'Q']:
				sys.exit("Program interrupted by user.")
			else:
				## re-check...
				checked_path = check_file(newpath)
			return checked_path
		else:
			error = "ERROR!  File %s could not be found!" % path
			errorhandler(error)

def cut_chunk(wavfile, outfile, start, dur, SOXPATH):
	"""uses SoX to cut a portion out of a sound file"""

	if SOXPATH:
		command_cut_sound = " ".join([SOXPATH, '\"' + wavfile + '\"', '\"' + outfile + '\"', "trim", str(start), str(dur)])
		## ("sox <original sound file> "<new sound chunk>" trim <start of selection (in sec)> <duration of selection (in sec)>")
		## (put file paths into quotation marks to accomodate special characters (spaces, parantheses etc.))
	else:
		command_cut_sound = " ".join(["sox", '\"' + wavfile + '\"', '\"' + outfile + '\"', "trim", str(start), str(dur)])
	try:
		os.system(command_cut_sound)
		if options.verbose:
			print "\tSound chunk %s successfully extracted." % (outfile) #os.path.basename(outfile)
	except Exception, e:
		sound_error = "Error in extracting sound chunk %s:  %s." % (os.path.basename(outfile), e)
		errorhandler(sound_error)


def define_options_and_arguments():
	"""defines options and positional arguments for this program"""

	use = """(python) %prog [options] soundfile.wav [transcription.txt] [output.TextGrid]"""
	desc = """Aligns a sound file with the corresponding transcription text. The transcription text is split into annotation breath groups, which are fed individually as "chunks" to the forced aligner. All output is concatenated into a single Praat TextGrid file.

	INPUT:
	- sound file
	- tab-delimited text file with the following columns:
		first column:   speaker ID
		second column:  speaker name
		third column:   beginning of breath group (in seconds)
		fourth column:  end of breath group (in seconds)
		fifth column:   transcribed text
	(If no name is specified for the transcription file, it will be assumed to have the same name as the sound file, plus ".txt" extension.)

	OUTPUT:
	- Praat TextGrid file with orthographic and phonemic transcription tiers for each speaker (If no name is specified, it will be given same name as the sound file, plus ".TextGrid" extension.)"""

	ep = """The following additional programs need to be installed and in the path:
	- Praat (on Windows machines, the command line version praatcon.exe)
	- SoX"""

	vers = """This is %prog, a new version of align.py, written by Jiahong Yuan, combining it with Ingrid Rosenfelder's front_end_FA.py and an interactive CMU dictionary check for all words in the transcription file.
	Last modified May 14, 2010."""

	new_use = format_option_text(use)
	new_desc = format_option_text(desc)
	new_ep = format_option_text(ep)

	check_help = """Checks whether phonetic transcriptions for all words in the transcription file can be found in the CMU Pronouncing Dictionary.  Returns a list of unknown words (required argument "FILENAME")."""
	import_help = """Adds a list of unknown words and their corresponding phonetic transcriptions to the CMU Pronouncing Dictionary prior to alignment.  User will be prompted interactively for the transcriptions of any remaining unknown words.  Required argument "FILENAME" must be tab-separated plain text file (one word - phonetic transcription pair per line)."""
	verbose_help = """Detailed output on status of dictionary check and alignment progress."""
	dict_help = """Specifies the name of the file containing the pronunciation dictionary.  Default file is "/model/dict"."""
	noprompt_help = """User is not prompted for the transcription of words not in the dictionary, or truncated words.  Unknown words are ignored by the aligner."""
	htktoolspath_help = """Specifies the path to the HTKTools directory where the HTK executable files are located.  If not specified, the user's path will be searched for the location of the executable."""

	parser = optparse.OptionParser(usage=new_use, description=new_desc, epilog=new_ep, version=vers)
	parser.add_option('-c', '--check', help=check_help, metavar='FILENAME')						## required argument FILENAME
	parser.add_option('-i', '--import', help=import_help, metavar='FILENAME', dest='importfile')   ## required argument FILENAME
	parser.add_option('-v', '--verbose', action='store_true', default=False, help=verbose_help)
	parser.add_option('-d', '--dict', default='model/dict', help=dict_help, metavar='FILENAME')
	parser.add_option('-n', '--noprompt', action='store_true', default=False, help=noprompt_help)
	parser.add_option('-t', '--htktoolspath', default='', help=htktoolspath_help, metavar='HTKTOOLSPATH')

	## After parsing with (options, args) = parser.parse_args(), options are accessible via
	## - string options.check (default:  None)
	## - string options.importfile (default:  None)
	## - "bool" options.verbose (default:  False)
	## - string options.dict (default:  "model/dict")
	## - "bool" options.noprompt (default:  False)

	return parser





def errorhandler(errormessage):
	"""handles the error depending on whether the file is run as a standalone or as an imported module"""

	if __name__ == "__main__":  ## file run as standalone program
		sys.exit(errormessage)
	else:  ## run as imported module from somewhere else -> propagate exception
		raise Exception, errormessage


def format_option_text(text):
	"""re-formats usage, description and epiloge strings for the OptionParser
	so that they do not get mangled by optparse's textwrap"""
	## NOTE:  This is a (pretty ugly) hack to (partially) preserve newline characters
	## in the description strings for the OptionParser.
	## "textwrap" appears to preserve (non-initial) spaces, so all lines containing newlines
	## are padded with spaces until they reach the length of 80 characters,
	## which is the width to which "textwrap" formats the description text.

	lines = text.split('\n')
	newlines = ''
	for line in lines:
		## pad remainder of line with spaces
		n, m = divmod(len(line), 80)
		if m != 0:
			line += (' ' * (80 - m))
		newlines += line

	return newlines


def get_duration(soundfile, FADIR=''):
	"""gets the overall duration of a soundfile"""
	## INPUT:  string soundfile = name of sound file
	## OUTPUT:  float duration = duration of sound file

	try:
		## calculate duration by sampling rate and number of frames
		f = wave.open(soundfile, 'r')
		sr = float(f.getframerate())
		nx = f.getnframes()
		f.close()
		duration = round((nx / sr), 3)
	except wave.Error:  ## wave.py does not seem to support 32-bit .wav files???
		if PRAATPATH:
			dur_command = "%s %s %s" % (PRAATPATH, os.path.join(FADIR, "get_duration.praat"), soundfile)
		else:
			dur_command = "praat %s %s" % (os.path.join(FADIR, "get_duration.praat"), soundfile)
		duration = round(float(subprocess.Popen(dur_command, shell=True, stdout=subprocess.PIPE).communicate()[0].strip()), 3)

	return duration


def is_sound(f):
	"""checks whether a file is a .wav sound file"""

	if f.lower().endswith('.wav'):
## NOTE:  This is the old version of the file check using a call to 'file' via the command line
##	and ("audio/x-wav" in subprocess.Popen('file -bi "%s"' % f, shell=True, stdout=subprocess.PIPE).communicate()[0].strip()
##										   or "audio/x-wav" in subprocess.Popen('file -bI "%s"' % f, shell=True, stdout=subprocess.PIPE).communicate()[0].strip()):
##	## NOTE:  "file" options:
##	##		  -b	  brief (no filenames appended)
##	##		  -i/-I   outputs MIME file types (capital letter or not different for different versions)
		return True
	else:
		return False


def is_text(f):
	"""checks whether a file is a .txt text file"""

	if f.lower().endswith('.txt'):
## NOTE:  This is the old version of the file check using a call to 'file' via the command line
##	and ("text/plain" in subprocess.Popen('file -bi "%s"' % f, shell=True, stdout=subprocess.PIPE).communicate()[0].strip()
##										   or "text/plain" in subprocess.Popen('file -bI "%s"' % f, shell=True, stdout=subprocess.PIPE).communicate()[0].strip()):
		return True
	else:
		return False


def is_TextGrid(f):
	"""checks whether a file is a .TextGrid file"""

	if re.search("\.TextGrid$", f):  ## do not test the actual file type because file does not yet exist at this point!
		return True
	else:
		return False


# def make_tempdir(tempdir):
#	 """creates a temporary directory for all alignment "chunks";
#	 warns against overwriting existing files if applicable"""

#	 ## check whether directory already exists and has files in it
#	 if os.path.isdir(tempdir):
#		 contents = os.listdir(tempdir)
#		 if len(contents) != 0 and not options.noprompt:
#			 print "WARNING!  Directory %s already exists and is non-empty!" % tempdir
#			 print "(Files in directory:  %s )" % contents
#			 overwrite = raw_input("Overwrite and continue?  [y/n]")
#			 if overwrite == "y":
#				 ## delete contents of tempdir
#				 for item in contents:
#					 os.remove(os.path.join(tempdir, item))
#			 elif overwrite == "n":
#				 sys.exit("Exiting program.")
#			 else:
#				 sys.exit("Undecided user.  Exiting program.")
#	 else:
#		 os.mkdir(tempdir)





def mark_time(index):
	"""generates a time stamp entry in global list times[]"""

	cpu_time = time.clock()
	real_time = time.time()
	times.append((index, cpu_time, real_time))

def merge_textgrids(main_textgrid, new_textgrid, speaker, chunkname_textgrid):
	"""adds the contents of TextGrid new_textgrid to TextGrid main_textgrid"""

	for tier in new_textgrid:
		## change tier names to reflect speaker names
		## (output of FA program is "phone", "word" -> "Speaker - phone", "Speaker - word")
		tier.rename(speaker + " - " + tier.name())
		## check if tier already exists:
		exists = False
		for existing_tier in main_textgrid:
			if tier.name() == existing_tier.name():
				exists = True
				break   ## need this so existing_tier retains its value!!!
		if exists:
			for interval in tier:
				existing_tier.append(interval)
		else:
			main_textgrid.append(tier)
	if options.verbose:
		print "\tSuccessfully added", chunkname_textgrid, "to main TextGrid."

	return main_textgrid

## This function originally is from Jiahong Yuan's align.py
## (very much modified by Ingrid...)
def prep_mlf(transcription, mlffile, identifier):
	"""writes transcription to the master label file for forced alignment"""
	## INPUT:
	## list transcription = list of list of (preprocessed) words
	## string mlffile = name of master label file
	## string identifier = unique identifier of process/sound file (can't just call everything "tmp")
	## OUTPUT:
	## none, but writes master label file to disk

	fw = open(mlffile, 'w')
	fw.write('#!MLF!#\n')
	fw.write('"*/tmp' + identifier + '.lab"\n')
	fw.write('sp\n')
	for line in transcription:
		for word in line:
			## change unclear transcription ("((xxxx))") to noise
			if word == "((xxxx))":
				word = "{NS}"
				global count_unclear
				count_unclear += 1
			## get rid of parentheses for uncertain transcription
			if uncertain.search(word):
				word = uncertain.sub(r'\1', word)
				global count_uncertain
				count_uncertain += 1
			## delete initial asterisks
			if word[0] == "*":
				word = word[1:]
			## check again that word is in CMU dictionary because of "noprompt" option,
			## or because the user might select "skip" in interactive prompt
			if word in cmudict:
				fw.write(word + '\n')
				fw.write('sp\n')
				global count_words
				count_words += 1
			else:
				print "\tWarning!  Word %s not in CMU dict!!!" % word.encode('ascii', 'replace')
	fw.write('.\n')
	fw.close()


## This function is from Jiahong Yuan's align.py
## (but adapted so that we're forcing a SR of 16,000 Hz; mono)
def prep_wav(orig_wav, out_wav, SOXPATH=''):
	"""adjusts sampling rate  and number of channels of sound file to 16,000 Hz, mono."""

## NOTE:  the wave.py module may cause problems, so we'll just copy the file to 16,000 Hz mono no matter what the original file format!
##	f = wave.open(orig_wav, 'r')
##	SR = f.getframerate()
##	channels = f.getnchannels()
##	f.close()
##	if not (SR == 16000 and channels == 1):  ## this is changed
	SR = 16000
##		#SR = 11025
	if SOXPATH:  ## if FAAValign is used as a CGI script, the path to SoX needs to be specified explicitly
		os.system(SOXPATH + ' \"' + orig_wav + '\" -c 1 -r 16000 ' + out_wav)
	else:		## otherwise, rely on the shell to find the correct path
		os.system("sox" + ' \"' + orig_wav + '\" -c 1 -r 16000 ' + out_wav)
		#os.system("sox " + orig_wav + " -c 1 -r 11025 " + out_wav + " polyphase")
##	else:
##		os.system("cp -f " + '\"' + orig_wav + '\"' + " " + out_wav)

	return SR


def process_style_tier(entries, style_tier=None):
	"""processes entries of style tier"""

	## create new tier for style, if not already in existence
	if not style_tier:
		style_tier = praat.IntervalTier(name="style", xmin=0, xmax=0)
		if options.verbose:
			print "Processing style tier."
	## add new interval on style tier
	beg = round(float(entries[2]), 3)
	end = round(float(entries[3]), 3)
	text = entries[4].strip().upper()
	## check that entry on style tier has one of the allowed values
##	if text in STYLE_ENTRIES:
	style_tier.append(praat.Interval(beg, end, text))
##	else:
##		error = "ERROR!  Invalid entry on style tier:  %s (interval %.2f - %.2f)" % (text, beg, end)
##		errorhandler(error)

	return style_tier


def prompt_user(word, clue=''):
	"""asks the user for the Arpabet transcription of a word"""
	## INPUT:
	## string word = word to be transcribed
	## string clue = following word (optional)
	## OUTPUT:
	## list checked_trans = transcription in Arpabet format (list of phones)

	print "Please enter the Arpabet transcription of word %s, or enter [s] to skip." % word
	if clue:
		print "(Following word is %s.)" % clue
	print "\n"
	trans = raw_input()
	if trans != "s":
		checked_trans = check_transcription(trans)
		return checked_trans
	else:
		return None

def read_transcription_file(trsfile):
	"""reads the transcription file in either ASCII or UTF-16 encoding, returns a list of lines in the file"""

	try:  ## try UTF-16 encoding first
		t = codecs.open(trsfile, 'rU', encoding='utf-16')
		print "Encoding is UTF-16!"
		lines = t.readlines()
	except UnicodeError:
		try:  ## then UTF-8...
			t = codecs.open(trsfile, 'rU', encoding='utf-8')
			print "Encoding is UTF-8!"
			lines = t.readlines()
			lines = replace_smart_quotes(lines)
		except UnicodeError:
			try:  ## then Windows encoding...
				t = codecs.open(trsfile, 'rU', encoding='windows-1252')
				print "Encoding is Windows-1252!"
				lines = t.readlines()
			except UnicodeError:
				t = open(trsfile, 'rU')
				print "Encoding is ASCII!"
				lines = t.readlines()

	return lines


def reinsert_uncertain(tg, text):
	"""compares the original transcription with the word tier of a TextGrid and
	re-inserts markup for uncertain and unclear transcriptions"""
	## INPUT:
	## praat.TextGrid tg = TextGrid that was output by the forced aligner for this "chunk"
	## list text = list of words that should correspond to entries on word tier of tg (original transcription WITH parentheses, asterisks etc.)
	## OUTPUT:
	## praat.TextGrid tg = TextGrid with original uncertain and unclear transcriptions

	## forced alignment may or may not insert "sp" intervals between words
	## -> make an index of "real" words and their index on the word tier of the TextGrid first
	tgwords = []
	for (n, interval) in enumerate(tg[1]):  ## word tier
		if interval.mark() not in ["sp", "SP"]:
			tgwords.append((interval.mark(), n))
##	print "\t\ttgwords:  ", tgwords
##	print "\t\ttext:  ", text

	## for all "real" (non-"sp") words in transcription:
	for (n, entry) in enumerate(tgwords):
		tgword = entry[0]			   ## interval entry on word tier of FA output TextGrid
		tgposition = entry[1]		   ## corresponding position of that word in the TextGrid tier

		## if "noprompt" option is selected, or if the user chooses the "skip" option in the interactive prompt,
		## forced alignment ignores unknown words & indexes will not match!
		## -> count how many words have been ignored up to here and adjust n accordingly (n = n + ignored)
		i = 0
		while i <= n:
			## (automatically generated "in'" entries will be in dict file by now,
			## so only need to strip original word of uncertainty parentheses and asterisks)
			if (uncertain.sub(r'\1', text[i]).lstrip('*') not in cmudict and text[i] != "((xxxx))"):
				n += 1  ## !!! adjust n for every ignored word that is found !!!
			i += 1

		## original transcription contains unclear transcription:
		if text[n] == "((xxxx))":
			## corresponding interval in TextGrid must have "{NS}"
			if tgword == "{NS}" and tg[1][tgposition].mark() == "{NS}":
				tg[1][tgposition].change_text(text[n])
			else:  ## This should not happen!
				error = "ERROR!  Something went wrong in the substitution of unclear transcriptions for the forced alignment!"
				errorhandler(error)

		## original transcription contains uncertain transcription:
		elif uncertain.search(text[n]):
			## corresponding interval in TextGrid must have transcription without parentheses (and, if applicable, without asterisk)
			if tgword == uncertain.sub(r'\1', text[n]).lstrip('*') and tg[1][tgposition].mark() == uncertain.sub(r'\1', text[n]).lstrip('*'):
				tg[1][tgposition].change_text(text[n])
			else:  ## This should not happen!
				error = "ERROR!  Something went wrong in the substitution of uncertain transcriptions for the forced alignment!"
				errorhandler(error)

		## original transcription was asterisked word
		elif text[n][0] == "*":
			## corresponding interval in TextGrid must have transcription without the asterisk
			if tgword == text[n].lstrip('*') and tg[1][tgposition].mark() == text[n].lstrip('*'):
				tg[1][tgposition].change_text(text[n])
			else:  ## This should not happen!
				 error = "ERROR!  Something went wrong in the substitution of asterisked transcriptions for the forced alignment!"
				 errorhandler(error)

	return tg


# def remove_tempdir(tempdir):
#	 """removes the temporary directory and all its contents"""

#	 for item in os.listdir(tempdir):
#		 os.remove(os.path.join(tempdir, item))
#	 os.removedirs(tempdir)
#	 os.remove("blubbeldiblubb.txt")


def replace_extension(filename, newextension):
	"""chops off the extension from the filename and replaces it with newextension"""

	return os.path.splitext(filename)[0] + newextension


# def empty_tempdir(tempdir):
#	 """empties the temporary directory of all files"""
#	 ## (NOTE:  This is a modified version of remove_tempdir)

#	 for item in os.listdir(tempdir):
#		 os.remove(os.path.join(tempdir, item))
#	 os.remove("blubbeldiblubb.txt")


def tidyup(tg, beg, end, tgfile):
	"""extends the duration of a TextGrid and all its tiers from beg to end;
	inserts empty/"SP" intervals; checks for overlapping intervals"""

	## set overall duration of main TextGrid
	tg.change_times(beg, end)
	## set duration of all tiers and check for overlaps
	overlaps = []
	for t in tg:
		## set duration of tier from 0 to overall duration of main sound file
		t.extend(beg, end)
		## insert entries for empty intervals between existing intervals
		oops = t.tidyup()
		if len(oops) != 0:
			for oo in oops:
				overlaps.append(oo)
		if options.verbose:
			print "Finished tidying up %s." % t
	## write errorlog if overlapping intervals detected
	if len(overlaps) != 0:
		print "WARNING!  Overlapping intervals detected!"
		write_errorlog(overlaps, tgfile)

	return tg


def write_errorlog(overlaps, tgfile):
	"""writes log file with details on overlapping interval boundaries to file"""

	## write log file for overlapping intervals from FA
	logname = os.path.splitext(tgfile)[0] + ".errorlog"
	errorlog = open(logname, 'w')
	errorlog.write("Overlapping intervals in file %s:  \n" % tgfile)
	for o in overlaps:
		errorlog.write("Interval %s and interval %s on tier %s.\n" % (o[0], o[1], o[2]))
	errorlog.close()
	print "Error messages saved to file %s." % logname


def write_alignment_errors_to_log(tgfile, failed_alignment):
	"""appends the list of alignment failures to the error log"""

	## warn user that alignment failed for some parts of the TextGrid
	print "WARNING!  Alignment failed for some annotation units!"

	logname = os.path.splitext(tgfile)[0] + ".errorlog"
	## check whether errorlog file exists
	if os.path.exists(logname) and os.path.isfile(logname):
		errorlog = open(logname, 'a')
		errorlog.write('\n')
	else:
		errorlog = open(logname, 'w')
	errorlog.write("Alignment failed for the following annotation units:  \n")
	errorlog.write("#\tbeginning\tend\tspeaker\ttext\n")
	for f in failed_alignment:
#		try:
		errorlog.write('\t'.join(f).encode('ascii', 'replace'))
#		except UnicodeDecodeError:
#			errorlog.write('\t'.join(f))
		errorlog.write('\n')
	errorlog.close()
	print "Alignment errors saved to file %s." % logname


def write_log(filename, wavfile, duration):
	"""writes a log file on alignment statistics"""

	f = open(filename, 'w')
	t_stamp = time.asctime()
	f.write(t_stamp)
	f.write("\n\n")
	f.write("Alignment statistics for file %s:\n\n" % os.path.basename(wavfile))

	try:
		check_version = subprocess.Popen(["git","describe", "--tags"], stdout = subprocess.PIPE)
		version,err = check_version.communicate()
		version = version.rstrip()
	except OSError:
		version = None

	if version:
		f.write("version info from Git: %s"%version)
		f.write("\n")
	else:
		f.write("Not using Git version control. Version info unavailable.\n")
		f.write("Consider installing Git (http://git-scm.com/).\
		 and cloning this repository from GitHub with: \n \
		 git clone git@github.com:JoFrhwld/FAVE.git")
		f.write("\n")

	try:
		check_changes = subprocess.Popen(["git", "diff", "--stat"], stdout = subprocess.PIPE)
		changes, err = check_changes.communicate()
	except OSError:
		changes = None

	if changes:
		f.write("Uncommitted changes when run:\n")
		f.write(changes)

	f.write("\n")
	f.write("Total number of words:\t\t\t%i\n" % count_words)
	f.write("Uncertain transcriptions:\t\t%i\t(%.1f%%)\n" % (count_uncertain, float(count_uncertain)/float(count_words)*100))
	f.write("Unclear passages:\t\t\t%i\t(%.1f%%)\n" % (count_unclear, float(count_unclear)/float(count_words)*100))
	f.write("\n")
	f.write("Number of breath groups aligned:\t%i\n" % count_chunks)
	f.write("Duration of sound file:\t\t\t%.3f seconds\n" % duration)
	f.write("Total time for alignment:\t\t%.2f seconds\n" % (times[-1][2] - times[1][2]))
	f.write("Total time since beginning of program:\t%.2f seconds\n\n" % (times[-1][2] - times[0][2]))
	f.write("->\taverage alignment duration:\t%.3f seconds per breath group\n" % ((times[-1][2] - times[1][2])/count_chunks))
	f.write("->\talignment rate:\t\t\t%.3f times real time\n" % ((times[-1][2] - times[0][2])/duration))
	f.write("\n\n")
	f.write("Alignment statistics:\n\n")
	f.write("Chunk\tCPU time\treal time\td(CPU)\td(time)\n")
	for i in range(len(times)):
		## first entry in "times" tuple is string already, or integer
		f.write(str(times[i][0]))							   ## chunk number
		f.write("\t")
		f.write(str(round(times[i][1], 3)))					 ## CPU time
		f.write("\t")
		f.write(time.asctime(time.localtime(times[i][2])))	  ## real time
		f.write("\t")
		if i > 0:											   ## time differences (in seconds)
			f.write(str(round(times[i][1] - times[i-1][1], 3)))
			f.write("\t")
			f.write(str(round(times[i][2] - times[i-1][2], 3)))
		f.write("\n")
	f.close()

	return t_stamp


################################################################################
## This used to be the main program...										##
## Now it's wrapped in a function so we can import the code				   ##
## without supplying the options and arguments via the command line		   ##
################################################################################


def FAAValign(opts, args, FADIR='', SOXPATH=''):
	"""runs the forced aligner for the arguments given"""

	tempdir = os.path.join(FADIR, TEMPDIR)

	## need to make options global (now this is no longer the main program...)
	global options
	options = opts

	## get start time of program
	global times
	times = []
	mark_time("start")

	## positional arguments should be soundfile, transcription file, and TextGrid file
	## (checking that the options are valid is handled by the parser)
	(wavfile, trsfile, tgfile) = check_arguments(args)
	## (returned values are the full paths!)

	## read CMU dictionary
	## (default location is "/model/dict", unless specified otherwise via the "--dict" option)
	global cmudict
	cmudict = read_dict(os.path.join(FADIR, options.dict))

	## add transcriptions from import file to dictionary, if applicable
	if options.importfile:
		add_dictionary_entries(options.importfile, FADIR)

	## read transcription file
	all_input = read_transcription_file(trsfile)
	if options.verbose:
		print "Read transcription file %s." % os.path.basename(trsfile)

	## initialize counters
	global count_chunks
	global count_words
	global count_uncertain
	global count_unclear
	global style_tier

	count_chunks = 0
	count_words = 0
	count_uncertain = 0
	count_unclear = 0
	style_tier = None
	failed_alignment = []

	HTKTOOLSPATH = options.htktoolspath

	## check correct format of input file; get list of transcription lines
	## (this function skips empty annotation units -> lines to be deleted)
	if options.verbose:
		print "Checking format of input transcription file..."
	trans_lines, delete_lines = check_transcription_file(all_input)

	## check that all words in the transcription columen of trsfile are in the CMU dictionary
	## -> get list of words for each line, preprocessed and without "clue words"
	## NOTE:	If the "check transcription" option is selected,
	##		  the list of unknown words will be output to file
	##		  -> END OF PROGRAM!!!
	if options.verbose:
		print "Checking dictionary entries for all words in the input transcription..."
	trans_lines = check_dictionary_entries(trans_lines, wavfile)
	if not trans_lines and not __name__ == "__main__":
		return

	## make temporary directory for sound "chunks" and output of FA program
	#make_tempdir(tempdir)
	check_tempdir(tempdir)
	#if options.verbose:
	#	print "Checked temporary directory %s." % tempdir

	## generate main TextGrid and get overall duration of main sound file
	main_textgrid = praat.TextGrid()
	if options.verbose:
		print "Generated main TextGrid."
	duration = get_duration(wavfile, FADIR)
	if options.verbose:
		print "Duration of sound file:  %f seconds." % duration

	## delete empty lines from array of original transcription lines
	all_input2 = delete_empty_lines(delete_lines, all_input)
	## check length of data arrays before zipping them:
	if not (len(trans_lines) == len(all_input)):
		error = "ERROR!  Length of input data lines (%s) does not match length of transcription lines (%s).  Please delete empty transcription intervals." % (len(all_input), len(trans_lines))
		errorhandler(error)

	mark_time("prelim")



	## add style tier to main TextGrid, if applicable
	if style_tier:
		main_textgrid.append(style_tier)

	## tidy up main TextGrid (extend durations, insert empty intervals etc.)
	main_textgrid = tidyup(main_textgrid, 0, duration, tgfile)

	## append information on alignment failure to errorlog file
	if failed_alignment:
		write_alignment_errors_to_log(tgfile, failed_alignment)

	## write main TextGrid to file
	main_textgrid.write(tgfile)
	if options.verbose:
		print "Successfully written TextGrid %s to file." % os.path.basename(tgfile)

	## delete temporary transcription files and "chunk" sound file/temp directory
	#remove_tempdir(tempdir)
	#empty_tempdir(tempdir)
	#os.remove("blubbeldiblubb.txt")
	## NOTE:  no longer needed because sound chunks and corresponding TextGrids are cleaned up in the loop
	##		also, might delete sound chunks from other processes running in parallel!!!

	## remove temporary CMU dictionary
	os.remove(temp_dict)
	if options.verbose:
		print "Deleted temporary copy of the CMU dictionary."

	## write log file
	t_stamp = write_log(os.path.splitext(wavfile)[0] + ".FAAVlog", wavfile, duration)
	if options.verbose:
		print "Written log file %s." % os.path.basename(os.path.splitext(wavfile)[0] + ".FAAVlog")


################################################################################
## MAIN PROGRAM STARTS HERE												   ##
################################################################################

if __name__ == '__main__':

	## get input/output file names and options
	parser = define_options_and_arguments()
	(opts, args) = parser.parse_args()

	FAAValign(opts, args)
