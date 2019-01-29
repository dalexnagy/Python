#!/usr/bin/python3
import sys
import os
import pymysql
import datetime
import getopt
from hsaudiotag import auto
from pydub import AudioSegment
from PyQt5 import QtWidgets, uic

# Globals & default settings
auto_Start = False
musicDir = ""
Server = "localhost"
total_File_Count = 0

# Open front page window
Ui_MainWindow, QtBaseClass = uic.loadUiType("MyMusicQT.ui")

# Get common database variables & do a global connect
from CommonDB import *
db = pymysql.connect(host=Server, user=User, passwd=UserPassword, db=Database, autocommit=True)
cursor = db.cursor()

insertTrackList = ['Format', 'FileName', 'Artist', 'Album', 'Song', 'Track',
                   'Genre', 'LengthSecs', 'MBytes', 'BitRate', 'dBFS', 'RMS',
                   'DateTimeRipped']
# TrackList pos: [   0,       1,          2,        3,       4,      5,
# TrackList pos:    6,         7,          8,        9,       10,     11,
# TrackList pos:   10]

insertSkippedList = ['Format', 'FileName']

# Arguments: 0=Program name,
#	-d/-drop (drop tables first),
#   -p/prod (use Production DB on Falcon server),
#	Directory (containing music files)

class MyApp(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        Ui_MainWindow.__init__(self)
        self.setupUi(self)
        self.musicDir_Box.currentIndexChanged.connect(self.set_DB_Options)
        self.exit_Button.clicked.connect(self.exitNow)
        self.getStartParms()
        if auto_Start:
            self.process_Files()
        else:
            self.getSources()
            self.start_Button.clicked.connect(self.process_Files)

    def exitNow(self):
        sys.exit(0)

    def set_DB_Options(self):
        #music_Box.currentData is a string of values in 'RefreshDBs' and 'ProdTest' columns
        if (self.musicDir_Box.currentData()[0] == "Y" or self.musicDir_Box.currentData()[0] == "R"):
            self.replaceData_Radio.setChecked(True)
            self.addData_Radio.setChecked(False)
            self.dbActions_Group.setEnabled(False)
        else:
            self.replaceData_Radio.setChecked(False)
            self.addData_Radio.setChecked(True)
            self.dbActions_Group.setEnabled(False)

        if self.musicDir_Box.currentData()[1] == "P":
            self.production_Radio.setChecked(True)
            self.selectDB_Group.setEnabled(False)
        else:
            self.production_Radio.setChecked(False)
            self.selectDB_Group.setEnabled(True)

    def getStartParms(self):
        #  Parse arguments passed on the command line
        messageText = str(datetime.datetime.now().strftime("%H:%M:%S")) + " MyMusicQT Processing starting"
        self.messages_List.insertPlainText(messageText+"\n")
        opts, args = getopt.getopt(sys.argv[1:], "hdp", ["-help", "-drop", "-prod"])
        for opt, arg in opts:
            if opt in ("-p", "-prod"):
                global Server
                Server = "Falcon"
                self.production_Radio.setChecked(True)
                self.selectDB_Group.setEnabled(False)
            else:
                self.production_Radio.setChecked(False)
                self.selectDB_Group.setEnabled(True)

            if opt in ("-d", "-drop"):
                self.replaceData_Radio.setChecked(True)
                self.dbActions_Group.setEnabled(False)
            else:
                self.replaceData_Radio.setChecked(False)
                self.dbActions_Group.setEnabled(False)

            if opt in ("-h", "--help"):
                print("Usage: ./MyMusicQT.py [-d/-drop] [-p/-prod] directory")
                sys.exit()

        if args != "" and len(args) > 0:  # Something was specified
            global musicDir
            global auto_Start
            musicDir = args[0]
            auto_Start = True
            self.production_Radio.setEnabled(False)
            self.replaceData_Radio.setEnabled(False)
            self.musicDir_Box.setEnabled(False)
            self.start_Button.setEnabled(False)
            messageText = str(datetime.datetime.now().strftime("%H:%M:%S")) + " MyMusicQT will Start Automatically"
            self.messages_List.insertPlainText(messageText+"\n")
        else:
            self.production_Radio.setEnabled(True)
            self.replaceData_Radio.setEnabled(True)
            self.musicDir_Box.setEnabled(True)
            self.start_Button.setEnabled(True)

    def getSources(self):
        self.musicDir_Box.clear()
         # Get list of sources
        cursor.execute("SELECT SourcePath, RefreshDBs, ProdTest FROM Sources ORDER BY SourcePath")

        for row in cursor.fetchall():
            if row[1] == "":
                tempAddRefr = "-"
            else:
                tempAddRefr = row[1]
            if row[2] == "":
                tempTestProd = "-"
            else:
                tempTestProd = row[2]
            self.musicDir_Box.addItem(row[0],tempAddRefr+tempTestProd)

    # Functions used in main processing routine (process_Files)
    def openDatabase(self):
        global auto_Start
        global cursor

        db = pymysql.connect(host=Server, user=User, passwd=UserPassword, db=Database, autocommit=True)
        cursor = db.cursor()
        messageText = str(datetime.datetime.now().strftime("%H:%M:%S")) + \
	        " Active DB is '" + Database + "' on host '" + Server + "'"
        self.messages_List.insertPlainText(messageText+"\n")

        # Drop all previous data if requested
        if self.replaceData_Radio.isChecked() == True:
            cursor.execute("TRUNCATE TABLE tracks")
            db.commit()
            messageText = str(datetime.datetime.now().strftime("%H:%M:%S")) + \
                " All rows in DB '" + Database + "' table 'tracks' were deleted."
            self.messages_List.insertPlainText(messageText+"\n")
            if auto_Start:
                print(messageText)
            cursor.execute("TRUNCATE TABLE skipped")
            db.commit()
            messageText = str(datetime.datetime.now().strftime("%H:%M:%S")) + \
                " All rows in DB '" + Database + "' table 'skipped' were deleted."
            self.messages_List.insertPlainText(messageText+"\n")
            if auto_Start:
                print(messageText)
        else:
            messageText = str(datetime.datetime.now().strftime("%H:%M:%S")) + \
                " New data will be added to tables in DB " + Database + "\n"
            self.messages_List.insertPlainText(messageText+"\n")
            if auto_Start:
                print(messageText)

    # Add row to database
    def add_track_to_database(self, insertList):
        sql = "INSERT INTO tracks (Format, FileName, Artist, Album, Song, Track, \
                Genre, LengthSecs, MBytes, BitRate, dBFS, RMS, DateTimeRipped) \
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        try:
            cursor.execute(sql, insertList)
            #messageText = str(datetime.datetime.now().strftime("%H:%M:%S")) + \
            #   " Added track to DB: '" + str(insertList[4]) + "'"
            #self.messages_List.insertPlainText(messageText+"\n")
        except pymysql.IntegrityError:
            messageText = str(datetime.datetime.now().strftime("%H:%M:%S")) + \
               " Failure when adding track to DB: '" + str(insertList[4]) + "'"
            self.messages_List.insertPlainText(messageText+"\n")

    def add_skipped_to_database(self, insertList):
        sql = "INSERT INTO skipped (Format, FileName) VALUES (%s, %s)"
        cursor.execute(sql, insertList)

    # END OF FUNCTIONS

    # Main Processing Loop
    def process_Files(self):
        global musicDir
        if musicDir == "":
            musicDir = self.musicDir_Box.currentText()
            myDBRefresh=self.musicDir_Box.currentData()[0]
            myTestProd=self.musicDir_Box.currentData()[1]
        else:
            print(str(datetime.datetime.now().strftime("%H:%M:%S")) + " Processing of files in '" + musicDir + "'")
        self.openDatabase()

        if not os.path.exists(musicDir):
            messageText = str(datetime.datetime.now().strftime("%H:%M:%S")) + \
                          " ERROR!! Path '" + str(musicDir) + "' was NOT FOUND!"
            self.messages_List.insertPlainText(messageText+"\n")
            print(messageText)
            sys.exit(4)
        else:
            messageText = str(datetime.datetime.now().strftime("%H:%M:%S")) + \
                          " Scanning files in '" + str(musicDir)
            self.messages_List.insertPlainText(messageText+"\n")

        total_File_Count = sum(len(files) for _, _, files in os.walk(musicDir))

        messageText = str(datetime.datetime.now().strftime("%H:%M:%S")) + \
                      " Found " + str(total_File_Count) + " files to process"
        self.messages_List.insertPlainText(messageText+"\n")

        count_Dirs = 0
        count_Files = 0
        count_Skipped = 0
        count_Tracks = 0

        messageText = str(datetime.datetime.now().strftime("%H:%M:%S")) + " Processing started"
        self.messages_List.insertPlainText(messageText+"\n")

        for root, directories, filenames in os.walk(musicDir):
            for directory in directories:
                count_Dirs += 1
            for filename in filenames:
                QtWidgets.QApplication.processEvents()
                count_Files += 1
                trackFileName = os.path.join(root, filename)

                if trackFileName.endswith(".mp3") and '.Apple' not in trackFileName:
                    trackFormat = "MP3"
                elif trackFileName.endswith(".m4a") and '.Apple' not in trackFileName:
                    trackFormat = "MP4"
                else:
                    trackFormat = "???"

                if trackFormat != "???":
                    audioSeg = AudioSegment.from_file(trackFileName, format=trackFormat)
                    myMusic = auto.File(trackFileName)
                    if myMusic.bitrate > 0:
                        storedRate = myMusic.bitrate
                    else:
                        storedRate = myMusic.sample_rate
                    filestat = os.stat(trackFileName)

                    # Only use if duration is greater than 15 seconds
                    if myMusic.duration > 15:
                        insertTrackList = [trackFormat,
                                           trackFileName.encode('ascii', 'replace'),
                                           myMusic.artist, myMusic.album,
                                           myMusic.title.encode('ascii', 'replace'),
                                           str(myMusic.track),
                                           myMusic.genre, str(myMusic.duration),
                                           str(format(myMusic.size/(1024*1024), '.2f')),
                                           str(storedRate),
                                           '{0:.4f}'.format(audioSeg.dBFS),
                                           str(audioSeg.rms),
                                           str(datetime.datetime.fromtimestamp(os.path.getmtime(trackFileName)))]
                        self.add_track_to_database(insertTrackList)
                        count_Tracks += 1
                    else:
                        insertSkippedList = [trackFormat,
                                             trackFileName.encode('ascii', 'replace')]
                        self.add_skipped_to_database(insertSkippedList)
                        count_Skipped += 1
                else:
                    insertSkippedList = [trackFormat, 
                    					 trackFileName.encode('ascii', 'replace')]
                    self.add_skipped_to_database(insertSkippedList)
                    count_Skipped += 1

                if count_Files % 10 == 0:
                    # Update Progress Bar display
                    files_processed_pct = (count_Files / total_File_Count) * 100
                    self.progressBar.setValue(files_processed_pct)

                if count_Files % 500 == 0:
                    messageText = str(datetime.datetime.now().strftime("%H:%M:%S"))
                    messageText += " Processing - Files: " + str(count_Files)
                    messageText += ", Tracks:" + str(count_Tracks) + ", Skipped:" + str(count_Skipped)
                    self.messages_List.insertPlainText(messageText+"\n")
                    # print(messageText)

                self.messages_List.verticalScrollBar().setValue(
                    self.messages_List.verticalScrollBar().maximum())

        messageText = str(datetime.datetime.now().strftime("%H:%M:%S"))
        messageText += " End! Dirs=" + str(count_Dirs) + ", Files=" + str(count_Files)
        messageText += ", Tracks:" + str(count_Tracks) + ", Skipped:" + str(count_Skipped)
        self.messages_List.insertPlainText(messageText+"\n")
        print(messageText)

        # disconnect from server
        cursor.close()
        db.close()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MyApp()
    window.show()
    sys.exit(app.exec_())
