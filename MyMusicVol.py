#!/usr/bin/python3
import sys
import os
import datetime
import getopt
from hsaudiotag import auto
from pydub import AudioSegment

# Arguments: 0=Program name, 1=Directory

# Globals
musicDir = ""

# Parse arguments passed on the command line
opts, args = getopt.getopt(sys.argv[1:], "h", ["-help"])
for opt, arg in opts:
	if opt in ("-h", "--help"):
		print("Usage: ./MyMusicVol.py directory")
		sys.exit()
if args != "" and len(args) > 0:	# Something was specified 
	musicDir = args[0]
else:	# Nothing was specified
	# print help information and exit:
	print("Usage: ./args.py directory")
	sys.exit(2)

if not os.path.exists(musicDir):
	print("ERROR! Path specified on command was NOT FOUND!")
	sys.exit(4)

# GLOBAL FUNCTIONS

# Get file modification date
def file_mod_date(filename):
    t = os.path.getmtime(filename)
    return datetime.datetime.fromtimestamp(t)
    
# Convert file size to MB
def convert_to_MB(size):
    return format(size/(1024*1024),'.2f')
         
# END OF FUNCTIONS

# Open output (report) file
results_File = 'Python_MyMusicVol_Results.txt'
try:
	results_File_Handle = open(results_File,'x')  # Try creating it new
except:
	results_File_Handle = open(results_File,'w')	# Try opening for output

count_Dirs = 0
count_Files = 0
count_Skipped = 0

print("Processing starting at ",datetime.now().strftime("%H:%M:%S"))

for root, directories, filenames in os.walk(musicDir):
	for directory in directories:
		count_Dirs += 1
	for filename in filenames: 
		count_Files += 1
		trackFileName = os.path.join(root,filename) 
		print_Line = "File: "+trackFileName+"\n"
		if trackFileName.endswith(".mp3"):
			trackFormat = "MP3"
		elif trackFileName.endswith(".m4a"):
			trackFormat = "MP4"
		else:
			trackFormat = "???"
			count_Skipped += 1	
		if trackFormat != "???":
			audioSeg = AudioSegment.from_file(trackFileName, format=trackFormat)
		print_Line += "  Format: "+trackFormat+"\n"
		myMusic = auto.File(trackFileName)
		print_Line += "  Title: "+myMusic.title+"\n"
		print_Line += "  Artist: "+myMusic.artist+"\n"
		print_Line += "  Album: "+myMusic.album+"\n"
		print_Line += "  Track: "+str(myMusic.track)+"\n"
		if trackFormat != "???":
			print_Line += "  dBFS: "+str(audioSeg.dBFS)+"\n"
			print_Line += "  Max dBFS: "+str(audioSeg.max_dBFS)+"\n"
			print_Line += "  rms: "+str(audioSeg.rms)+"\n"
			print_Line += "  Max rms: "+str(audioSeg.max)+"\n"
		print_Line += "  Dur: "+str(myMusic.duration)+" secs\n"
		if myMusic.bitrate > 0:
			print_Line += "  BitRate: "+str(myMusic.bitrate)+"\n"
			storedRate = myMusic.bitrate
		else:
			print_Line += "  Sample Rate: "+str(myMusic.sample_rate)+"\n"
			storedRate = myMusic.sample_rate
		print_Line += "  File size: "+str(convert_to_MB(myMusic.size))+"MB\n"
		filestat = os.stat(trackFileName)
		print_Line += "  Created: "+str(file_mod_date(trackFileName))+"\n"
		print_Line += "---------------\n"
		results_File_Handle.write(print_Line)

		if count_Files%100 == 0:
			print("Processed:",count_Files, "Skipped:",count_Skipped)

print("End! Dirs=", count_Dirs, ", Files=", count_Files)

