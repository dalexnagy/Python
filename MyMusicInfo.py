#!/usr/bin/python3
import sys
import os
import pymysql
import datetime
import getopt
from hsaudiotag import auto
from pydub import AudioSegment

# Arguments: 0=Program name, 
#			-d/-drop (drop tables first), 
#           -p/prod (use Production DB on Falcon server),
#			Directory (containing music files)

# Globals
dropTables = False
musicDir = ""
Server = "localhost"

# Parse arguments passed on the command line
opts, args = getopt.getopt(sys.argv[1:], "hdp", ["-help", "-drop", "-prod"])
for opt, arg in opts:
	if opt in ("-d", "-drop"):
		dropTables = True
	elif opt in ("-p", "-prod"):
		Server = "Falcon"	
	elif opt in ("-h", "--help"):
		print("Usage: ./MyMusicInfo.py [-d/-drop] [-p/-prod] directory")
		sys.exit()
if args != "" and len(args) > 0:	# Something was specified 
	musicDir = args[0]
else:	# Nothing was specified
	# print help information and exit:
	print("Usage: ./args.py [-d/-drop] directory")
	sys.exit(2)

if not os.path.exists(musicDir):
	print("ERROR! Path specified on command was NOT FOUND!")
	sys.exit(4)

# Get common database variables
from CommonDB import *
# Open database connection
db = pymysql.connect(host=Server, user=User, passwd=UserPassword, db=Database)
cursor = db.cursor()

print("MyMusicInfo Processing starting @",
	datetime.datetime.now().strftime("%H:%M:%S"))
print("Using database on server: ",Server)
print("Processing files in: ",musicDir)
total_File_Count = sum(len(files) for _, _, files in os.walk(musicDir))
print("Found ",total_File_Count," files to process")

# Drop all previous data if requested
if dropTables:
	cursor.execute("TRUNCATE TABLE tracks")
	db.commit()
	print("All rows in DB '", Database, "' table 'tracks' were deleted.")
	cursor.execute("TRUNCATE TABLE skipped")
	db.commit()
	print("All rows in DB '", Database, "' table 'skipped' were deleted.\n")

insertTrackList=['Format', 'FileName', 'Artist', 'Album', 'Song', 'Track', \
                'Genre', 'LengthSecs', 'MBytes', 'BitRate', 'dBFS', 'RMS', \
                'DateTimeRipped']
#TrackList pos: [   0,       1,          2,        3,       4,      5,       
#TrackList pos:    6,         7,          8,        9,       10,     11,
#TrackList pos:   10]

insertSkippedList=['Format', 'FileName']

# BEGIN FUNCTION CODE
# Add row to database
def add_track_to_database(insertList):
	sql = "INSERT INTO tracks (Format, FileName, Artist, Album, Song, Track, \
	        Genre, LengthSecs, MBytes, BitRate, dBFS, RMS, DateTimeRipped) \
        	VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)" 
	cursor.execute(sql, insertList)
	db.commit()

def add_skipped_to_database(insertList):
	sql = "INSERT INTO skipped (Format, FileName) VALUES (%s, %s)" 
	cursor.execute(sql, insertList)
	db.commit()

# Get file modification date
def file_mod_date(filename):
    t = os.path.getmtime(filename)
    return datetime.datetime.fromtimestamp(t)
    
# Convert file size to MB
def convert_to_MB(size):
    return format(size/(1024*1024),'.2f')
         
# END OF FUNCTIONS

# Open output (report) file
results_File = 'Python_MyMusicInfo_Results.txt'
try:
	results_File_Handle = open(results_File,'x')  # Try creating it new
except:
	results_File_Handle = open(results_File,'w')	# Try opening for output

count_Dirs = 0
count_Files = 0
count_Skipped = 0
count_Tracks = 0

for root, directories, filenames in os.walk(musicDir):
	for directory in directories:
		count_Dirs += 1
	for filename in filenames: 
		count_Files += 1
		trackFileName = os.path.join(root,filename) 
		print_Line = "File: "+trackFileName+"\n"
			
		if trackFileName.endswith(".mp3") and '.Apple' not in trackFileName:
			trackFormat = "MP3"
		elif trackFileName.endswith(".m4a") and '.Apple' not in trackFileName:
			trackFormat = "MP4"
		else:
			trackFormat = "???"
		print_Line += "  Format: "+trackFormat+"\n"
		results_File_Handle.write(print_Line)

		if trackFormat != "???":
			audioSeg = AudioSegment.from_file(trackFileName, format=trackFormat)
			print_Line  = ">>Fetched AudioSegment to audioSeg\n"
			results_File_Handle.write(print_Line)
			myMusic = auto.File(trackFileName)
			print_Line  = ">>Fetched auto.File to myMusic\n"
			results_File_Handle.write(print_Line)
			print_Line  = "  Title: "+myMusic.title+"\n"
			print_Line += "  Artist: "+myMusic.artist+"\n"
			print_Line += "  Album: "+myMusic.album+"\n"
			print_Line += "  Genre: "+myMusic.genre+"\n"
			print_Line += "  Track: "+str(myMusic.track)+"\n"
			print_Line += "  Dur: "+str(myMusic.duration)+" secs\n"
			if myMusic.bitrate > 0:
				print_Line += "  BitRate: "+str(myMusic.bitrate)+"\n"
				storedRate = myMusic.bitrate
			else:
				print_Line += "  Sample Rate: "+str(myMusic.sample_rate)+"\n"
				storedRate = myMusic.sample_rate
			print_Line += "  dBFS: "+str(audioSeg.dBFS)+"\n"
			print_Line += "  rms: "+str(audioSeg.rms)+"\n"
			print_Line += "  File size: "+str(convert_to_MB(myMusic.size))+"MB\n"
			filestat = os.stat(trackFileName)
			print_Line += "  Created: "+str(file_mod_date(trackFileName))+"\n"
			results_File_Handle.write(print_Line)

			# Only use if duration is greater than 15 seconds
			if myMusic.duration > 15:
				insertTrackList=[trackFormat, \
								trackFileName.encode('ascii', 'replace'), \
								myMusic.artist, myMusic.album, \
								myMusic.title.encode('ascii', 'replace'), \
								str(myMusic.track), \
								myMusic.genre, str(myMusic.duration),
								str(convert_to_MB(myMusic.size)), \
								str(storedRate), \
								'{0:.4f}'.format(audioSeg.dBFS), \
								str(audioSeg.rms), \
								str(file_mod_date(trackFileName))]
				add_track_to_database(insertTrackList)
				count_Tracks += 1
				print_Line  = ">>Written to 'tracks' database\n"
			else:
				insertSkippedList=[trackFormat, trackFileName]
				add_skipped_to_database(insertSkippedList)
				count_Skipped += 1
				print_Line  = ">>Written to 'skipped' database (too short)\n"
		else:
			insertSkippedList=[trackFormat, trackFileName]
			add_skipped_to_database(insertSkippedList)
			count_Skipped += 1
			print_Line  = ">>Written to 'skipped' database (bad format)\n"

		print_Line += "---------------\n"
		results_File_Handle.write(print_Line)
         
		if count_Files%100 == 0:
			files_processed_pct = (count_Files/total_File_Count)*100
			print("Processing - Files:",count_Files, \
				" (%4.1f" % files_processed_pct,"%)", \
				"Tracks:", count_Tracks, ", Skipped:",count_Skipped, " @", \
				datetime.datetime.now().strftime("%H:%M:%S"))

print("End! Dirs=", count_Dirs, ", Files=", count_Files, \
	"Tracks:", count_Tracks, ", Skipped:",count_Skipped, " @", \
	datetime.datetime.now().strftime("%H:%M:%S"))
# disconnect from server
db.close()
