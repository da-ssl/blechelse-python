# This is a Python script that uses a database of Deutsche Bahn ("Blechelse") 
# announcements and the transport.rest-API to play these announcements automatically. 
# In the future, it should also be possible to play announcements manually.

# So far, the source code below represents only fragments and is not really operational



import requests
import sys
import numpy as mp
import datetime
import blechelse

from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
from transport import *

instance = "https://transport.phipsiart.de/"
params = "?bus=false&ferry=false&subway=false&tram=false&taxi=false&language=de&duration=180"
humantimeformat = "%H:%M"

def gettrips(station: str, loadedStation = None) -> list:
    print(instance + f"stops/{station}/departures{params}")
    departures = requests.get(instance + f"stops/{station}/departures{params}").json()
    arrivals = requests.get(instance + f"stops/{station}/arrivals{params}").json()
    trips = []
    for i in departures['departures']:
        doubled = False
        for y in trips:
            if i['tripId'] == y.tripId: doubled = True
        if not doubled: trips.append(trip(None, False, loadedStation, i, 'departure'))

    for i in arrivals['arrivals']:
        doubled = False
        for y in trips:
            if i['tripId'] == y.tripId: doubled = True
        if not doubled: trips.append(trip(None, False, loadedStation, i, 'arrival'))
    

    trips_sorted = sorted(trips, key=lambda x: x.departureString)

    return trips_sorted



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
        
        self.dockTime = QDockWidget(self)
        self.dockTime.setWindowTitle("Uhrzeit")
        self.dockTime_clock = QLabel()
        self.dockTime.setWidget(self.dockTime_clock)
        self.dockTime_sizePolicy = QSizePolicy()
        self.dockTime_sizePolicy.setVerticalStretch(0)
        self.dockTime.setSizePolicy(self.dockTime_sizePolicy)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dockTime)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)  # Aktualisieren alle 1000 ms (1 Sekunde)

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

    
    def on_click(self, index):
        row = index.row()
        trip = self.model.trips[row]
        self.loadTrip(trip)

    def loadStation(self):
        text, ok = QInputDialog().getText(None, "Bahnhofssuche",
                                          "Suchbegriff eingeben:")
        if not (ok or text): return
        apires = requests.get(f'{instance}stations?query={text}').json()
        keys = list(apires.keys())
        res1 = apires[keys[0]]
        self.tdat = res1
        self.loadedStation = stop(self.tdat['id'], False, self.tdat)
        self.statusbar.showMessage(f"{self.tdat['name']} ({self.tdat['id']})")
        self.loadData()
        

    def loadTrip(self, currenttrip: trip):
        currenttrip = trip(currenttrip.tripId, True, self.loadedStation, currenttrip.tripData)
        self.loadedTrip = currenttrip
        # Alte Daten löschen
        while self.dockStation_gridlayout.count():
            item = self.dockStation_gridlayout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        
        # Überschrift: Linie und Ziel
        if currenttrip.isArrival: self.dockStation_header = QLabel(f"<h3>{currenttrip.lineName} von {currenttrip.originName}</h3>")
            # TODO: Nicht immer ist origin gegeben. Falls die API den nicht ausspuckt, nimm den ersten stopOver
        else: self.dockStation_header = QLabel(f"<h3>{currenttrip.lineName} nach {currenttrip.destination.name}</h3>")
        self.dockStation_gridlayout.addWidget(self.dockStation_header, 0, 0, 1, 2)

        properties = [
            ["Ziel", currenttrip.destination.name],
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
        x+=1

        # Ansage-Buttons
        self.dockStation_btn_ann_arrival = QPushButton("Einfahrt")
        self.dockStation_btn_ann_arrival.clicked.connect(lambda:blechelse.doArrivalAnnouncement(currenttrip, currentTripStop))
        self.dockStation_gridlayout.addWidget(self.dockStation_btn_ann_arrival, x, 0)

    def loadData(self):
        data = ""
        #try:
        data = gettrips(self.loadedStation.id, self.loadedStation)
        #except Exception as e:
            #print("Error while calling the API for departures and arrivals")
            #return

        # Falls leer, melde das und breche ab
        if data == {} or data == "" or data == None:
            QMessageBox.warning(self, "Keine Daten", "Es konnten keine Daten gefunden werden")
            return # Falls keine Zugdaten

        
        self.model = StopTableModel(data, selectedStationName=self.loadedStation.name)
        self.table.setModel(self.model)
        self.table.doubleClicked.connect(self.on_click)
        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()
        try: self.loadTrip(self.loadedTrip)
        except: pass # there was no trip loaded in the dock before

    def update_time(self):
        current_time = datetime.datetime.now().strftime("%H:%M:%S")
        self.dockTime_clock.setText(f"<h3>{current_time}")
        app.processEvents()
       
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
