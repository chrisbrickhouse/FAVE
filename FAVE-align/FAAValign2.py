def main(args):
	aligner = Aligner(*args)
	aligner.read_transcript()
	aligner.check_transcription_file()
	aligner.check_against_dictionary()

	if check:
		return

	aligner.check_tempdir('')
	main_textgrid = praat.TextGrid()
	duration = aligner.get_duration()
	aligner.align()


if __name__ == '__main__':
	options = parser
	args = [
		wavfile,
		trsfile,
		inputfile,
		tgfile,
		dictionary_file,
		no_prompt,
		verbose,
		check,
		htktoolspath
	]
