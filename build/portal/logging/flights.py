#!/usr/bin/python

#================================================================================#
#                             ADS-B FEEDER PORTAL                                #
# ------------------------------------------------------------------------------ #
# Copyright and Licensing Information:                                           #
#                                                                                #
# The MIT License (MIT)                                                          #
#                                                                                #
# Copyright (c) 2015-2016 Joseph A. Prochazka                                    #
#                                                                                #
# Permission is hereby granted, free of charge, to any person obtaining a copy   #
# of this software and associated documentation files (the "Software"), to deal  #
# in the Software without restriction, including without limitation the rights   #
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell      #
# copies of the Software, and to permit persons to whom the Software is          #
# furnished to do so, subject to the following conditions:                       #
#                                                                                #
# The above copyright notice and this permission notice shall be included in all #
# copies or substantial portions of the Software.                                #
#                                                                                #
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR     #
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,       #
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE    #
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER         #
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,  #
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE  #
# SOFTWARE.                                                                      #
#================================================================================#

# WHAT THIS DOES:                                                 
# ---------------------------------------------------------------
#
# 1) Read aircraft.json generated by dump1090-mutability.
# 2) Add the flight to the database if it does not already exist.
# 3) Update the last time the flight was seen.

import datetime
import json
import time
import os
#import urllib2

while True:

    # Read the configuration file.
    with open(os.path.dirname(os.path.realpath(__file__)) + '/config.json') as config_file:
        config = json.load(config_file)

    # Import the needed database library.
    if config["database"]["type"] == "mysql":
        import MySQLdb
    if config["database"]["type"] == "sqlite":
        import sqlite3

    # Read dump1090-mutability's aircraft.json.
    with open('/run/dump1090-mutability/aircraft.json') as data_file:
        data = json.load(data_file)
    # For testing using a remote JSON feed.
    #response = urllib2.urlopen('http://192.168.254.2/dump1090/data/aircraft.json')
    #data = json.load(response)

    if config["database"]["type"] == "sqlite":
        ## Connect to a SQLite database.
        db = sqlite3.connect(config["database"]["db"])
    else:
        ## Connect to a MySQL database.
        db = MySQLdb.connect(host=config["database"]["host"], user=config["database"]["user"], passwd=config["database"]["passwd"], db=config["database"]["db"])

    # Assign the time to a variable.
    time_now = datetime.datetime.utcnow().strftime("%Y/%m/%d %H:%M:%S")

    cursor = db.cursor()
    for aircraft in data["aircraft"]:
        # Check if this aircraft was already seen.
        if config["database"]["type"] == "sqlite":
            params = (aircraft["hex"],)
            cursor.execute("SELECT COUNT(*) FROM adsb_aircraft WHERE icao = ?", params)
        else:
            cursor.execute("SELECT COUNT(*) FROM adsb_aircraft WHERE icao = %s", aircraft["hex"])
        row_count = cursor.fetchone()
        if row_count[0] == 0:
            # Insert the new aircraft.
            #print("Added Aircraft: " + aircraft["hex"])
            if config["database"]["type"] == "sqlite":
                params = (aircraft["hex"], time_now, time_now,)
                cursor.execute("INSERT INTO adsb_aircraft (icao, firstSeen, lastSeen) VALUES (?, ?, ?)", params)
            else:
                cursor.execute("INSERT INTO adsb_aircraft (icao, firstSeen, lastSeen) VALUES (%s, %s, %s)", (aircraft["hex"], time_now, time_now))
        else:
            # Update the existing aircraft.
            if config["database"]["type"] == "sqlite":
                params = (time_now, aircraft["hex"],)
                cursor.execute("UPDATE adsb_aircraft SET lastSeen = ? WHERE icao = ?", params)
            else:
                cursor.execute("UPDATE adsb_aircraft SET lastSeen = %s WHERE icao = %s", (time_now, aircraft["hex"]))
        # Get the ID of this aircraft.
        if config["database"]["type"] == "sqlite":
            params = (aircraft["hex"],)
            cursor.execute("SELECT id FROM adsb_aircraft WHERE icao = ?", params)
        else:
            cursor.execute("SELECT id FROM adsb_aircraft WHERE icao = %s", aircraft["hex"])
        rows = cursor.fetchall()
        for row in rows:
            aircraft_id = row[0]

        # Check that a flight is tied to this track.
        if aircraft.has_key('flight'):
            # Check to see if the flight already exists in the database.
            if config["database"]["type"] == "sqlite":
                params = (aircraft["flight"].strip(),)
                cursor.execute("SELECT COUNT(*) FROM adsb_flights WHERE flight = ?", params)
            else:
                cursor.execute("SELECT COUNT(*) FROM adsb_flights WHERE flight = %s", aircraft["flight"].strip())
            row_count = cursor.fetchone()
            if row_count[0] == 0:
                # If the flight does not exist in the database add it.
                if config["database"]["type"] == "sqlite":
                    params = (aircraft_id, aircraft["flight"].strip(), time_now, time_now,)
                    cursor.execute("INSERT INTO adsb_flights (aircraft, flight, firstSeen, lastSeen) VALUES (?, ?, ?, ?)", params)
                else:
                    cursor.execute("INSERT INTO adsb_flights (aircraft, flight, firstSeen, lastSeen) VALUES (%s, %s, %s, %s)", (aircraft_id, aircraft["flight"].strip(), time_now, time_now))
                #print("Added Flight: " + aircraft["flight"].strip())
            else:
                # If it already exists pdate the time it was last seen.
                if config["database"]["type"] == "sqlite":
                    params =(aircraft_id, time_now, aircraft["flight"].strip(),)
                    cursor.execute("UPDATE adsb_flights SET aircraft = ?, lastSeen = ? WHERE flight = ?", params)
                else:
                    cursor.execute("UPDATE adsb_flights SET aircraft = %s, lastSeen = %s WHERE flight = %s", (aircraft_id, time_now, aircraft["flight"].strip()))

            # Get the ID of this flight.
            if config["database"]["type"] == "sqlite":
                params = (aircraft["flight"].strip(),)
                cursor.execute("SELECT id FROM adsb_flights WHERE flight = ?", params)
            else:
                cursor.execute("SELECT id FROM adsb_flights WHERE flight = %s", aircraft["flight"].strip())
            rows = cursor.fetchall()
            for row in rows:
                flight_id = row[0]
            # Get the ID of this aircraft.
            if config["database"]["type"] == "sqlite":
                params = (aircraft["hex"].strip(),)
                cursor.execute("SELECT id FROM adsb_aircraft WHERE icao = ?", params)
            else:
                cursor.execute("SELECT id FROM adsb_aircraft WHERE icao = %s", aircraft["hex"].strip())
            rows = cursor.fetchall()
            for row in rows:
                flight_id = row[0]

            # Check if position data is available.
            if aircraft.has_key('lat') and aircraft.has_key('lon') and aircraft.has_key('altitude') and aircraft.has_key('speed') and aircraft.has_key('track') and aircraft.has_key('vert_rate') and aircraft["altitude"] != "ground":
                # Check that this message has not already been added to the database.
                if config["database"]["type"] == "sqlite":
                    params = (flight_id, aircraft["messages"],)
                    cursor.execute("SELECT message FROM adsb_positions WHERE flight = ? AND message = ? ORDER BY time DESC", params)
                else:
                    cursor.execute("SELECT message FROM adsb_positions WHERE flight = %s AND message = %s ORDER BY time DESC", (flight_id, aircraft["messages"]))
                rows = cursor.fetchall()
                row_count = cursor.rowcount
                last_message = 0
                for row in rows:
                    last_message = row[0]
                if row_count == 0 or last_message != aircraft["messages"]:
                    # Add this position to the database.
                    if aircraft.has_key('squawk'):
                        if config["database"]["type"] == "sqlite":
                            params = (flight_id, aircraft_id, time_now, aircraft["messages"], aircraft["squawk"], aircraft["lat"], aircraft["lon"], aircraft["track"], aircraft["altitude"], aircraft["vert_rate"], aircraft["speed"],)
                            cursor.execute("INSERT INTO adsb_positions (flight, aircraft, time, message, squawk, latitude, longitude, track, altitude, verticleRate, speed) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", params)
                        else:
                            cursor.execute("INSERT INTO adsb_positions (flight, aircraft,  time, message, squawk, latitude, longitude, track, altitude, verticleRate, speed) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", (flight_id, aircraft_id, time_now, aircraft["messages"], aircraft["squawk"], aircraft["lat"], aircraft["lon"], aircraft["track"], aircraft["altitude"], aircraft["vert_rate"], aircraft["speed"]))
                    else:
                        if config["database"]["type"] == "sqlite":
                            params = (flight_id, aircraft_id, time_now, aircraft["messages"], aircraft["lat"], aircraft["lon"], aircraft["track"], aircraft["altitude"], aircraft["vert_rate"], aircraft["speed"],)
                            cursor.execute("INSERT INTO adsb_positions (flight, aircraft, time, message, latitude, longitude, track, altitude, verticleRate, speed) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", params)
                        else:
                            cursor.execute("INSERT INTO adsb_positions (flight, aircraft, time, message, latitude, longitude, track, altitude, verticleRate, speed) VALUES (%s, $s, %s, %s, %s, %s, %s, %s, %s, %s)", (flight_id, aircraft_id, time_now, aircraft["messages"], aircraft["lat"], aircraft["lon"], aircraft["track"], aircraft["altitude"], aircraft["vert_rate"], aircraft["speed"]))

    # Close the database connection.
    db.commit()
    db.close()

    #print("Last Run: " + datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")) 
    time.sleep(15)
