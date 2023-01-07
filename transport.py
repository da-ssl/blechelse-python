import requests
import sys
import numpy as mp
import datetime
import blechelse

from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *

instance = "https://transport.phipsiart.de/"
params = "?bus=false&ferry=false&subway=false&tram=false&taxi=false&language=de&duration=180"
humantimeformat = "%H:%M"

def gettripinfos(tripId: str) -> dict:
    url = f'{instance}trips/{tripId}'
    try: dat = requests.get(url).json()
    except: 
        print("wrong tripid or something")
        return
    if len(dat) > 0: return dat



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
    def __init__(self, tripId: str = None , fetchData = True, loadedStation = None, tripData: dict = None, dataType: str = None):
        self.dataType = dataType
        self.tripId = tripId
        if self.tripId == None:
            self.tripId = tripData['tripId']
        if self.tripId == None: 
            print("NO TRIPID")
            return
        if '|' not in self.tripId: raise Exception

        if fetchData == False: dat = tripData
        else:
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

        # Ziel und Zieltext

        try: 
            self.destinationName = dat['destination']['name']
        except: 
            try: self.destinationName = dat['direction']
            except: self.destinationName = "error"

        
        if self.dataType == "arrival" and loadedStation != None: 
            # Falls es sich bei den eingegebenen Daten um Daten aus /stop/:id/arrivals
            # handelt, so setze den destinationName auf den zurzeit im Programm geladenen
            # Halt (loadedStation)
            self.destination = loadedStation
            self.destinationName = loadedStation.name
        try:
            self.destination = stop(dat['destination']['id'], False, dat['destination'])
        except: pass


        if self.dataType == "arrival" or self.dataType == "departure": 
            try: self.DOText = dat['origin']
            except: self.DOText = dat['provenance']
        else: 
            try: self.DOText = dat['stopovers'][0]['stop']['name']
            except: self.DOText = "Error."
        

        try:self.departureTime = datetime.datetime.fromisoformat(dat['when'])
        except: 
            try: self.departureTime = datetime.datetime.fromisoformat(dat['plannedWhen'])
            except: self.departureTime = None
        try: self.departureString = self.departureTime.strftime(humantimeformat)
        except: self.departureString = None

        try:
            self.stopoverStops = []
            for i in range(len(dat['stopovers'])):
                currentStop = stop(dat['stopovers'][i]['stop']['id'], False)
                self.stopoverStops.insert(i, currentStop)
        except: pass
        
        try:
            self.departureDelay = int(dat['departureDelay']) / 60
            self.arrivalDelay = int(dat['arrivalDelay']) / 60
            self.delayData: bool = True
        except:
            try: 
                self.delay = int(dat['delay']) / 60
                self.delayData: bool = True
            except: 
                self.delayData: bool = False
                try: self.delay = int(dat['departureDelay']) / 60
                except: self.delay = 0


        # currentTripPosition
        try:
            self.currentPosition = Location(dat['currentLocation']['latitude'], dat['currentLocation']['longitude'])
        except: self.currentPosition = None

        # Falls gegeben, überprüfe, ob die Fahrt am gegebenen, im Programm geladenen
        # Bahnhof endet, das heißt eine Ankunft besteht
        try:
            if type(loadedStation) == stop and str(loadedStation.id) == str(self.destination.id):
                self.isArrival = True
            elif type(loadedStation) == stop and loadedStation.name != self.destination.name:
                self.isArrival = False
            else:
                self.isArrival = None
        except: pass

        

    def getStopData(self, stopId: str) -> dict:
        inMyStopovers = False
        for i in self.tripData['stopovers']:    # da unten auch anpassen! die stopover-Informationen müssen aus dem tripdata['stopovers'] bezogen werden
            if str(stopId) == str(i['stop']['id']):
                inMyStopovers = True
                return TripStop(i)
        
        
        # ^^^^^^^^^^
        # Durchsuche die self.stopoverStops-Liste nach dem Stop, der dem für die Funktion
        # angegegebenen Stop entspricht

        return("error")


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


class StopTableModel(QAbstractTableModel):
    def __init__(self, trips, columns = None, selectedStationName: str = None):
        super().__init__()
        self.trips = trips
        if selectedStationName != None: self.selectedStationName = selectedStationName
        self.columns = columns
        if self.columns == None:
            self.columns = [
                ["Abfahrt", "departureString"],
                ["V", "delay", "delayData"],
                ["Linie", "lineName"],
                ["Ziel", "destinationName"]
            ]

    def rowCount(self, parent=None):
        return len(self.trips)
        
        
    def columnCount(self, parent=None):
        return len(self.columns)

    def set_columns(self, columns):
        self.columns = columns
        self.layoutChanged.emit()  # Signal an QTableView senden, dass das Layout geändert wurde

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        
        
        if role == Qt.ItemDataRole.DisplayRole:
                    row = index.row()
                    col = index.column()
                    attr = self.columns[col][1]
                    d =  getattr(self.trips[row], attr)  # Benutze getattr, um das Attribut des Trips abzurufen
                    # Formatierung für bestimmte Felder
                    if "elay" in str(attr):
                        try: 
                            if int(d) == 0: return "-"
                            d = "+" + str(int(d))
                        except: pass

                    return d
        return None


    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            #if section == 0:
                #return "Linie"
            #elif section == 1:
                #return "Von"

            for i in range(len(self.columns)):
                if section == self.columns.index(self.columns[i]):
                    return self.columns[i][0]
        return None


fetchedStops = []

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
        

class LineWidget(QFrame):
    def __init__(self):
        QFrame.__init__(self)
        self.setFrameShape(QFrame.Shape.HLine)
        self.setFrameShadow(QFrame.Shadow.Sunken)
    