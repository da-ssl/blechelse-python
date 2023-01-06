# This is a Python script that uses a database of Deutsche Bahn ("Blechelse") 
# announcements and the transport.rest API to play these announcements automatically. 
# In the future, it should also be possible to play announcements manually.

# So far, the Soure code below represents only fragments and is not really operational


import requests
import sys
import numpy as mp
import datetime

from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *

instance = "https://transport.phipsiart.de/"
params = "?bus=false&ferry=false&subway=false&tram=false&taxi=false"
humantimeformat = "%H:%M:%S"
humantimeformat_exact = "%H:%M"
fetchedStops = []

def gettripinfos(tripId: str) -> dict:
    url = f'{instance}trips/{tripId}'
    try: dat = requests.get(url).json()
    except: 
        print("wrong tripid or something")
        return
    if len(dat) > 0: return dat


def gettrips(station: str) -> list:
    print(instance + f"stops/{station}/departures{params}")
    departures = requests.get(instance + f"stops/{station}/departures{params}").json()
    arrivals = requests.get(instance + f"stops/{station}/arrivals{params}").json()
    trips = []
    for i in departures['departures']:
        doubled = False
        for y in trips:
            if i['tripId'] == y['tripId']: doubled = True
        if not doubled: trips.append(i)

    for i in arrivals['arrivals']:
        doubled = False
        for y in trips:
            if i['tripId'] == y['tripId']: doubled = True
        if not doubled: trips.append(i)
    return trips

class Location:
    def __init__(self, lat, lon):
        self.lat = lat
        self.lon = lon
        if self.lat == None or self.lon == None: return
        self.osmlink = self.getLink()

    def getLink(self, marker=True) -> str:
        link = "https://www.openstreetmap.org/"
        if marker is True: link += f"?mlat={self.lat}"
        if marker is True: link += f"&mlon={self.lon}"
        link += f"#map=17/{self.lat}/{self.lon}"
        return link

class trip:
    def __init__(self, tripId: str, fetchData = True):
        
        self.tripId = tripId
        if fetchData == False: return
        
        url = f'{instance}trips/{tripId}'

        try: dat = requests.get(url).json()['trip']
        except: 
            print("wrong tripid or something")
            return

        if len(dat) < 1: raise Exception

        self.tripData = dat
        try: 
            self.originName = dat['origin']['name']
            self.originObject = dat['origin']
        except: 
            self.originName = None
            self.originObject = None
        
        try:
            self.lineName = dat['line']['name']
        except: pass

        try:
            self.destination = dat['destination']['name']
        except: pass

        #self.departureTime = datetime.datetime.strptime(dat['departure'], humantimeformat)
        #self.arrivalTime = datetime.datetime.strptime(dat['arrival'], humantimeformat)

        self.departureTime = dat['departure'], humantimeformat
        self.arrivalTime = dat['arrival'], humantimeformat

        self.stopoverStops = []
        for i in range(len(dat['stopovers'])):
            currentStop = stop(dat['stopovers'][i]['stop']['id'], False)
            self.stopoverStops.insert(i, currentStop)
            
        
        try:
            self.departureDelay = dat['departureDelay']
            self.arrivalDelay = dat['arrivalDelay']
            self.delayData: bool = True
        except:
            self.delayData: bool = False


        # currentTripPosition
        try:
            self.currentPosition = Location(dat['currentLocation']['latitude'], dat['currentLocation']['longitude'])
        except: self.currentPosition = None

        

    def getStopData(self, stopId: str) -> dict:
        inMyStopovers = False
        for i in self.tripData['stopovers']:    # da unten auch anpassen! die stopover-Informationen müssen aus dem tripdata['stopovers'] bezogen werden
            if str(stopId) == str(i['stop']['id']):
                inMyStopovers = True
                return TripStop(i)
        
        return("error")
        
        # ^^^^^^^^^^
        # Durchsuche die self.stopoverStops-Liste nach dem Stop, der dem für die Funktion
        # angegegebenen Stop entspricht



class stop:
    def __init__(self, stopId: str, fetchData = True, data = None):
        self.stopId = stopId
        if data != None: 
            self.stopData = data
        elif fetchData == False: return
        else:
            url = f'{instance}stops/{stopId}'
            self.stopData = requests.get(url).json()

        self.name = self.stopData['name']
        self.id = self.stopData['id']
        self.locationDat = self.stopData['location']
        self.latitude = self.locationDat['latitude']
        self.longitude = self.locationDat['longitude']
        fetchedStops.append(self)


class TripStop:
    def __init__(self, tripStopData):
        self.dat = tripStopData
        self.stop = stop(self.dat['stop']['id'], False, self.dat['stop'])
        self.arrival = None
        self.departure = None
        try:
            try: self.arrival = datetime.datetime.fromisoformat(str(self.dat['arrival'])).strftime(humantimeformat)
            except: self.arrival = datetime.datetime.fromisoformat(str(self.dat['plannedArival'])).strftime(humantimeformat)
        except: pass
        try:
            try: self.departure = datetime.datetime.fromisoformat(str(self.dat['departure'])).strftime(humantimeformat)
            except: self.departure = datetime.datetime.fromisoformat(str(self.dat['plannedDeparture'])).strftime(humantimeformat)
        except: pass
        
        # AnkunftsGleis
        try: self.arrivalPlatform = self.dat['arrivalPlatform']
        except: self.arrivalPlatform = self.dat['plannedArrivalPlatform']
        if self.dat['arrivalPlatform'] != None and self.dat['arrivalPlatform'] != self.dat['plannedArrivalPlatform']:
            # Falls anderes Gleis als geplant:
            self.arrivalPlatformText = f"""<p><s>{self.dat['plannedArrivalPlatform']}</s> <span style="color:#c0392b"><strong>{self.dat['arrivalPlatform']}</strong></span></p>"""
        else: self.arrivalPlatformText = f'{self.arrivalPlatform}'


        # AbfahrtsGleis
        try: self.departurePlatform = self.dat['departurePlatform']
        except: self.departurePlatform = self.dat['plannedDeparturePlatform']
        if self.dat['departurePlatform'] != None and self.dat['departurePlatform'] != self.dat['plannedDeparturePlatform']:
            # Falls anderes Gleis als geplant:
            self.departurePlatformText = f"""<p><s>{self.dat['plannedDeparturePlatform']}</s> <span style="color:#c0392b"><strong>{self.dat['departurePlatform']}</strong></span></p>"""
        else: self.departurePlatformText = f'{self.departurePlatform}'

class TableModel(QAbstractTableModel):
    def __init__(self, data):
        super(TableModel, self).__init__()
        self._data = data

    def data(self, index, role):
        if role == Qt.ItemDataRole.DisplayRole:
            # See below for the nested-list data structure.
            # .row() indexes into the outer list,
            # .column() indexes into the sub-list
            return self._data[index.row()][index.column()]

    def rowCount(self, index):
        # The length of the outer list.
        return len(self._data)

    def columnCount(self, index):
        # The following takes the first sub-list, and returns
        # the length (only works if all rows are an equal length)
        return len(self._data[0])

    def headerData(self, section: int, orientation: Qt.Orientation, role: int):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                if section == 0: return "tripId"
                if section == 1: return "Zeit"

def getFetchedStop(stopId) -> stop:
    success = False
    while not success:
        for i in fetchedStops:
            if str(stopId) == str(i.id):
                success = True
                return i
    return None
    

class QStopLabel(QLabel):
    def __init__(self, textBefore: str=None, textAfter: str = None, stop: stop = None, stopId = None):
        QLabel.__init__(self, textBefore)
        self.stop: stop = None
        if stopId == None and stop == None: return
        if stop == None:
            self.stop = getFetchedStop(stopId)
        else: self.stop = stop
        if stop == None: return None
        # Hier kann jetzt mit einem Stop-Objekt weitergearbeitet werden
        self.link = Location(self.stop.latitude, self.stop.longitude).getLink()
        self.setOpenExternalLinks(True)
        if textBefore != None: self.text = textBefore
        self.text += f' <a href="{self.link}">{self.stop.name}</a> '
        if textAfter != None: self.text += textAfter
        self.setText(self.text)


class QCurrentTripPositionLabel(QLabel):
    def __init__(self, trip: trip, text: str = "Klick"):
        QLabel.__init__(self, text)
        self.trip = trip
        if type(self.trip) in ["", [], {}, "None", "", None]: return
        try: 
            self.position = trip.currentPosition
            if type(self.position) is not Location: 
                raise Exception
            self.link = self.position.getLink()
        except Exception as e: 
            self.setText(str(e))
            return # Für diesen Trip keine Position vorhanden


        self.link = self.position.getLink()
        self.setOpenExternalLinks(True)
        self.setText(f'<a href="{self.link}">{text}</a>')
        print(self.text())
        



class LineWidget(QFrame):
    def __init__(self):
        QFrame.__init__(self)
        self.setFrameShape(QFrame.Shape.HLine)
        self.setFrameShadow(QFrame.Shadow.Sunken)
    

class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()

        self.tdat = {}

        self.centralwidget = QWidget()

        self.menubar = self.menuBar()
        self.menubar.setNativeMenuBar(False)
        self.setMenuBar(self.menubar)
        self.fileMenu = self.menubar.addMenu('Datei')
        self.actionLoadStation = QAction(self)
        self.actionLoadStation.setText("Bahnhof laden...")
        self.actionLoadStation.setShortcut(QCoreApplication.translate("MainWindow", "Ctrl+B", None))
        self.actionLoadStation.triggered.connect(self.loadStation)
        self.actionReloadData = QAction(self)
        self.actionReloadData.setText("Daten neu laden")
        self.actionReloadData.setShortcut(QCoreApplication.translate("MainWindow", "Ctrl+R", None))
        self.actionReloadData.triggered.connect(self.loadData)

        self.menubar.addMenu(self.fileMenu)
        self.fileMenu.addAction(self.actionLoadStation)
        self.fileMenu.addAction(self.actionReloadData)

        self.statusbar = QStatusBar(self)
        self.setStatusBar(self.statusbar)

        self.table = QTableView()

        self.dockStation = QDockWidget(self)
        self.dockStation.setWindowTitle("Zuginformationen")
        self.dockStation_contents = QWidget()
        self.dockStation_sizePolicy = QSizePolicy()
        self.dockStation_sizePolicy.setVerticalStretch(0)
        self.dockStation_contents.setSizePolicy(self.dockStation_sizePolicy)
        self.dockStation_gridlayout = QGridLayout(self.dockStation_contents)
        self.dockStation.setWidget(self.dockStation_contents)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dockStation)

        self.setCentralWidget(self.table)
        self.show()

    def loadStation(self):
        text, ok = QInputDialog().getText(None, "Bahnhofssuche",
                                          "Suchbegriff eingeben:")
        if not (ok or text): return
        apires = requests.get(f'{instance}stations?query={text}').json()
        keys = list(apires.keys())
        res1 = apires[keys[0]]
        self.tdat = res1
        self.statusbar.showMessage(f"{self.tdat['name']} ({self.tdat['id']})")

    
    def showSelection(self, index):
        value = self.table.model().data(index, Qt.ItemDataRole.DisplayRole)
        if "|" in value: self.loadTrain(value)
        

    def loadTrain(self, tripId: str):
        currenttrip = trip(tripId)
        
        
        # Überschrift: Linie und Ziel
        self.dockStation_header = QLabel(f"<h3>{currenttrip.lineName} nach {currenttrip.destination}</h3>")
        self.dockStation_gridlayout.addWidget(self.dockStation_header, 0, 0, 1, 2)

        properties = [
            ["Ziel", currenttrip.destination],
            ["Ursprung", currenttrip.originName]
        ]

 
        for i in range(len(properties)):
            self.dockStation_labels = []
            self.dockStation_data = []
            try:
                self.dockStation_labels.insert(i-1, QLabel("<b>" + properties[i][0] +": </b>"))
                self.dockStation_data.insert(i-1, QLabel(properties[i][1]))
                self.dockStation_gridlayout.addWidget(self.dockStation_labels[i-1], i+1, 0)
                self.dockStation_gridlayout.addWidget(self.dockStation_data[i-1], i+1, 1)
            except: pass # Für diese Fahrt konnte diese Art von Information nicht ermittelt werden

        # Position
        self.dockStation_gridlayout.addWidget(QLabel("Position:"), len(properties)+1, 0)
        self.dockStation_gridlayout.addWidget(QCurrentTripPositionLabel(currenttrip), len(properties)+1, 1)

        # Trenner
        self.dockStation_gridlayout.addWidget(LineWidget(), len(properties)+2, 0, 1, 2)

        # Informationen bezüglich des Halts am Bahnhof, der derzeit ausgewählt ist:
        currentTripStop = currenttrip.getStopData(self.tdat['id'])
        if currentTripStop == "error" or currentTripStop == {}: 
            self.statusbar.showMessage(f"Fehler im System: Der angegebene Zug hält scheinbar nicht in {self.tdat['name']}", 5000)
            QMessageBox.warning(self, "Fehler im Fahrplan",
            "Der im Programm geladene Halt konnte nicht in den Zwischenhalten des " + 
            "ausgewählten Halts gefunden werden. Bitte laden Sie die Fahrplandaten neu.")
            return  # Falls der im Programm geladene halt nicht in den Stopovers des ausgewählten trips (zugfahrt)
                    # vorhanden ist, so breche den Vorgang ab.
        
        
        self.dockStation_gridlayout.addWidget(QStopLabel(textBefore="<b>Halt in", stop=currentTripStop.stop), len(properties)+3, 0, 1, 2)
        tripStopProperties = [
            ["Ankunft", currentTripStop.arrival],
            ["Abfahrt", currentTripStop.departure],
            ["Ankunftsgleis", currentTripStop.arrivalPlatformText],
            ["Abfahrtsgleis", currentTripStop.departurePlatformText]
        ]
        x = len(properties)+4
        for i in range(len(tripStopProperties)):
            try:
                if tripStopProperties[i][1] in ["None", None, "", " "]: continue
                self.dockStation_gridlayout.addWidget(QLabel(tripStopProperties[i][0] + ":"), x+i, 0)
                self.dockStation_gridlayout.addWidget(QLabel(tripStopProperties[i][1]), x+i, 1)
            except Exception as e: print(e)

        # Trenner
        x = x + len(tripStopProperties)
        self.dockStation_gridlayout.addWidget(LineWidget(), x, 0, 1, 2)

        

    def loadData(self):
        data = ""
        try:
            data = gettrips(self.tdat['id'])
        except:
            print("Error while calling the API for departures and arrivals")
            return

        if data is {}:
            QMessageBox.warning(self, "Keine Daten", "Es konnten keine Daten gefunden werden")
            return # Falls keine Zugdaten

        fdata = []
        for i in range(len(data)):
            
            # item für die aktuelle Zeile einfügen
            fdata.insert(i, [])

            # tripId
            fdata[i].insert(0, data[i]['tripId'])

            # time
            isotime = datetime.datetime.fromisoformat(data[i]['plannedWhen'])
            humantime = datetime.datetime.strftime(isotime, "%H:%M")
            fdata[i].insert(1, humantime)

        self.table.doubleClicked.connect(self.showSelection)

        
        self.model = TableModel(fdata)
        self.table.setModel(self.model)

       


class stationDetails(QMainWindow):
    def __int__(self):
        super(self, stationDetails).__init__()
        self.centralwidget = QWidget()

        self.setCentralWidget(self.centralwidget)

        self.layoutInformation = QGridLayout()
        self.centralwidget.setLayout(self.layoutInformation)

        self.i_stationname_lbl = QLabel("Name:")
        self.i_stationname_lineedit = QLineEdit()

        self.layoutInformation.addWidget(self.i_stationname_lbl, 0, 0)

        self.show()


app = QApplication(sys.argv)
wd = MainWindow()
wd.show()
app.exec()