
class Aligner():
	def __init__(
		self,
		wavfile,
		trsfile,
		inputfile=None,
		tgfile=None,
		dictionary_file=['model','dict'],
		no_prompt=False,
		verbose=False,
		check=False,
		htktoolspath='HTKTOOLSPATH'
	):
		self.audio = wavfile
		self.transcript = trsfile
		if tgfile:
			self.textgrid = tgfile
		else:
			self.textgrid = os.path.splitext(trsfile)[0]+'.TextGrid'
		self.verbose = verbose
		self.prompt = not no_prompt
		self.check = check
		self.htktoolspath = htktoolspath
		kwargs = {
			'verbose': verbose,
			'prompt': not no_prompt,
			'check': check
		}
		args = []
		self.cmu_dict = CMU_Dictionary(os.path.join(dictionary_file),*args,**kwargs)
		if inputfile:
			self.cmu_dict.add_dictionary_entries(inputfile)
		self.transcript = TranscriptProcesor(trsfile,self.cmu_dict,*args,**kwargs)

	def read_transcript(self):
		self.transcript.read_transcription_file()

	def check_transcript(self):
		self.transcript.check_transcription_file()

	def check_against_dictionary(self):
		self.transcript.check_dictionary_entries()

	def get_duration(self, FADIR=''):
		"""gets the overall duration of a soundfile"""
		## INPUT:  string soundfile = name of sound file
		## OUTPUT:  float duration = duration of sound file

		try:
			## calculate duration by sampling rate and number of frames
			f = wave.open(self.wavfile, 'r')
			sr = float(f.getframerate())
			nx = f.getnframes()
			f.close()
			duration = round((nx / sr), 3)
		except wave.Error:  ## wave.py does not seem to support 32-bit .wav files???
			if PRAATPATH:
				dur_command = "%s %s %s" % (PRAATPATH, os.path.join(FADIR, "get_duration.praat"), self.wavfile)
			else:
				dur_command = "praat %s %s" % (os.path.join(FADIR, "get_duration.praat"), self.wavfile)
			duration = round(float(subprocess.Popen(dur_command, shell=True, stdout=subprocess.PIPE).communicate()[0].strip()), 3)

		return duration

	def check_tempdir(self, tempdi):
		"""checks that the temporary directory for all alignment "chunks" is empty"""
		#skip this, not useful in modular form
		return

		## (NOTE:  This is a modified version of make_tempdir)
		## check whether directory already exists and has files in it
		if os.path.isdir(tempdir):
			contents = os.listdir(tempdir)
			if len(contents) != 0 and not options.noprompt:
				print "WARNING!  Directory %s is non-empty!" % tempdir
				print "(Files in directory:  %s )" % contents
				overwrite = raw_input("Overwrite and continue?  [y/n]")
				if overwrite == "y":
					## delete contents of tempdir
					for item in contents:
						os.remove(os.path.join(tempdir, item))
				elif overwrite == "n":
					sys.exit("Exiting program.")
				else:
					sys.exit("Undecided user.  Exiting program.")

	def align(self):
		trans_lines = self.transcript.trans_lines
		all_input = self.transcript.lines
		if  len(trans_lines) != len(all_input) :
			raise ValueError('Remove empty lines from transcript')
		## start alignment of breathgroups
		for (text, line) in zip(trans_lines, all_input):

			entries = line.strip().split('\t')
			## start counting chunks (as part of the output file names) at 1
			count_chunks += 1

			# TODO
			## style tier?
			if (entries[0] in STYLE) or (entries[1] in STYLE):
				style_tier = process_style_tier(entries, style_tier)
				continue

			## normal tiers:
			speaker = entries[1].strip().encode('ascii', 'ignore').replace('/', ' ')  ## eventually replace all \W!
			if not speaker:  ## some people forget to enter the speaker name into the second field, try the first one (speaker ID) instead
				speaker = entries[0].strip()
			beg = round(float(entries[2]), 3)
			end = min(round(float(entries[3]), 3), duration)  ## some weird input files have the last interval exceed the duration of the sound file
			dur = round(end - beg, 3)
			if options.verbose:
				try:
					print "Processing %s -- chunk %i:  %s" % (speaker, count_chunks, " ".join(text))
				except (UnicodeDecodeError, UnicodeEncodeError):  ## I will never get these encoding issues...  %-(
					print "Processing %s -- chunk %i:  %s" % (speaker, count_chunks, " ".join(text).encode('ascii', 'replace'))
			if dur < 0.05:
				print "\tWARNING!  Annotation unit too short (%s s) - no alignment possible." % dur
				print "\tSkipping alignment for annotation unit ", " ".join(text).encode('ascii', 'replace')
				continue

			## call SoX to cut the corresponding chunk out of the sound file
			chunkname_sound = "_".join([os.path.splitext(os.path.basename(wavfile))[0], speaker.replace(" ", "_"), "chunk", str(count_chunks)]) + ".wav"
			cut_chunk(wavfile, os.path.join(tempdir, chunkname_sound), beg, dur, SOXPATH)
			## generate name for output TextGrid
			chunkname_textgrid = os.path.splitext(chunkname_sound)[0] + ".TextGrid"

			## align chunk
			try:
				align(os.path.join(tempdir, chunkname_sound), [text], os.path.join(tempdir, chunkname_textgrid), FADIR, SOXPATH, HTKTOOLSPATH)
			except Exception, e:
				try:
					print "\tERROR!  Alignment failed for chunk %i (speaker %s, text %s)." % (count_chunks, speaker, " ".join(text))
				except (UnicodeDecodeError, UnicodeEncodeError):
					print "\tERROR!  Alignment failed for chunk %i (speaker %s, text %s)." % (count_chunks, speaker, " ".join(text).encode('ascii', 'replace'))
				print "\n", traceback.format_exc(), "\n"
				print "\tContinuing alignment..."
				failed_alignment.append([str(count_chunks), str(beg), str(end), speaker, " ".join(text)])
				## remove temp files
				os.remove(os.path.join(tempdir, chunkname_sound))
				os.remove(os.path.join(tempdir, chunkname_textgrid))
				continue

			## read TextGrid output of forced alignment
			new_textgrid = praat.TextGrid()
			new_textgrid.read(os.path.join(tempdir, chunkname_textgrid))
			## re-insert uncertain and unclear transcriptions
			new_textgrid = reinsert_uncertain(new_textgrid, text)
			## change time offset of chunk
			new_textgrid.change_offset(beg)
			if options.verbose:
				print "\tOffset changed by %s seconds." % beg

			## add TextGrid for new chunk to main TextGrid
			main_textgrid = merge_textgrids(main_textgrid, new_textgrid, speaker, chunkname_textgrid)

			## remove sound "chunk" and TextGrid from tempdir
			os.remove(os.path.join(tempdir, chunkname_sound))
			os.remove(os.path.join(tempdir, chunkname_textgrid))
