from django.contrib import admin
from django.urls import path, include
from django.contrib import messages
from django.http import HttpResponse,JsonResponse
from django.shortcuts import redirect, render

import urllib.request, urllib.error
import sqlite3
import json
import csv

def fetch(request):
    conn = sqlite3.connect('covid_cases.sqlite')
    cur = conn.cursor()
    cur.executescript ('''
    DROP TABLE IF EXISTS States;
    DROP TABLE IF EXISTS Districts;
    DROP TABLE IF EXISTS Cases;
                    
    CREATE TABLE IF NOT EXISTS "States" (
                "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
                "state" TEXT UNIQUE
    );

    CREATE TABLE IF NOT EXISTS "Districts" (
                "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
                "district" TEXT UNIQUE
    );

    CREATE TABLE IF NOT EXISTS "Cases"
                ("id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE, 
                "state_id" INTEGER, 
                "district_id" INTEGER,
                "zone_id" INTEGER,
                "confirmed" INTEGER, 
                "active" INTEGER, 
                "recovered" INTEGER, 
                "deceased" INTEGER)
    ''')

    '''
    #use data downloaded file from https://api.covid19india.org/ and saved as district_wise.json     
    fname = 'district_wise.json'
    fh = open(fname)
    data = fh.read()
    '''
    #from online
    url = 'https://api.covid19india.org/state_district_wise.json'
    # print('Retrieving', url) 
    info = urllib.request.urlopen(url)
    data = info.read().decode()

    #read data
    js = json.loads(data)
    #print(js)

    #country
    #country_count_confirmed = 0
    #country_count_active = 0
    #country_count_recovered = 0
    #country_count_deceased = 0
        
    #states
    for state in js:
        #print(state)
        state_count_confirmed = 0
        state_count_active = 0
        state_count_recovered = 0
        state_count_deceased = 0
        
        cur.execute('INSERT OR IGNORE INTO States(state) VALUES(?)', (state, ))
        cur.execute('SELECT id FROM States WHERE state = ?', (state, ))
        state_id = cur.fetchone()[0]

        #districts
        for district in js[state]["districtData"]:
            #print(district+":")

            cur.execute('INSERT OR IGNORE INTO Districts(district) VALUES(?)', (district, ))
            cur.execute('SELECT id FROM Districts WHERE district = ?', (district, ))
            district_id = cur.fetchone()[0]

            #confirmed
            confirmed = js[state]["districtData"][district]["confirmed"]
            #print("Confirmed:", confirmed)
            state_count_confirmed += int(confirmed)

            #recovered
            recovered = js[state]["districtData"][district]["recovered"]
            #print("Recovered:", recovered)
            state_count_recovered += int(recovered)      

            #deceased
            deceased = js[state]["districtData"][district]["deceased"]
            #print("Deceased:", deceased)
            state_count_deceased += int(deceased)
            
            #active
            active = confirmed - (recovered + deceased)
            #print("Active:", active)
            state_count_active += active
            
            cur.execute('''INSERT OR IGNORE INTO Cases(state_id, district_id, confirmed, active, recovered, deceased) 
                        VALUES(?, ?, ?, ?, ?, ?)''', (state_id, district_id, confirmed, active, recovered, deceased))
            
        #print("Total confirmed :",state_count_confirmed)
        #print("Total active :",state_count_active)
        #print("Total recovered :",state_count_recovered)
        #print("Total deceased :",state_count_deceased)
        #print("\n")
        #country_count_confirmed += state_count_confirmed
        #country_count_active += state_count_active
        #country_count_recovered += state_count_recovered
        #country_count_deceased += state_count_deceased

    #print(country_count_confirmed,country_count_active, country_count_recovered, country_count_deceased)

    # print("Data Retrieved.")      
    cur.executescript ('''
    DROP TABLE IF EXISTS Zones;
                    
    CREATE TABLE IF NOT EXISTS "Zones" (
                "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
                "zone" TEXT UNIQUE
                )
    ''')

    '''
    #use data downloaded file from https://api.covid19india.org/ and saved as district_wise.json     
    fname = 'zones.json'
    fh = open(fname)
    data = fh.read()
    '''

    #from online
    url = 'https://api.covid19india.org/zones.json'
    # print('Retrieving', url) 
    info = urllib.request.urlopen(url)
    data = info.read().decode()

    #read data
    js = json.loads(data)
    #print(js)

    for value in js["zones"]:
        state = value["state"]
        cur.execute('INSERT OR IGNORE INTO States(state) VALUES(?)', (state, ))
        cur.execute('SELECT id FROM States WHERE state = ?', (state, ))
        state_id = cur.fetchone()[0]
        
        district = value["district"]
        cur.execute('INSERT OR IGNORE INTO Districts(district) VALUES(?)', (district, ))
        cur.execute('SELECT id FROM Districts WHERE district = ?', (district, ))
        district_id = cur.fetchone()[0]

        cur.execute('SELECT id FROM Cases WHERE state_id = ? AND district_id = ?', (state_id, district_id))
        x = cur.fetchone()
        
        if x is None:
            cur.execute('''INSERT OR IGNORE INTO Cases(state_id, district_id, confirmed, active, recovered, deceased)
                        VALUES(?, ?, 0, 0, 0, 0)''', (state_id, district_id))

    conn.commit()

    for value in js["zones"]:
        #print("State:", value["state"])
        state = value["state"]
        cur.execute('SELECT id FROM States WHERE state = ?', (state, ))
        state_id = cur.fetchone()[0]
        
        #print("District:", value["district"])
        district = value["district"]
        cur.execute('SELECT id FROM Districts WHERE district = ?', (district, ))
        district_id = cur.fetchone()[0]

        #print("Zone:", value["zone"])
        zone = value["zone"]
        cur.execute('INSERT OR IGNORE INTO Zones(zone) VALUES(?)', (zone, ))
        cur.execute('SELECT id FROM Zones WHERE zone = ?', (zone, ))
        zone_id = cur.fetchone()[0]
        
        cur.execute('SELECT id FROM Cases WHERE state_id = ? AND district_id = ?', (state_id, district_id))
        case_id = cur.fetchone()[0]
        
        cur.execute('UPDATE Cases SET zone_id=? WHERE id=?', (zone_id, case_id))

    conn.commit()
    #Update NULL Values
    cur.execute('SELECT id FROM Zones WHERE zone = ?',('',))
    zone_id = cur.fetchone()[0]
    cur.execute('UPDATE Cases SET zone_id = ? WHERE zone_id is NULL', (zone_id,))

    # print("Updated Zone data.")     
    conn.commit()        
    cur.close()
    messages.add_message(request, messages.SUCCESS,"Succesfully Fetched Latest Data From the Server")
    return redirect('app:getdata')

def getdata(request):
    conn = sqlite3.connect('covid_cases.sqlite')
    cursor = conn.cursor()
    cursor.execute('SELECT id, state FROM States')
    states = cursor.fetchall()

    cursor.execute('SELECT id, district FROM Districts')
    districts = cursor.fetchall()
    if request.method == 'POST':
        state_id = request.POST.get('state')
        district_id = request.POST.get('district')
        # print(states[int(state_id)-1][1])
        # print(district_id)
        for i in districts:
            if str(i[0]) == district_id:
                district = i[1]
                break
        cursor.execute('''
                    SELECT Zones.zone, Cases.confirmed, Cases.active, Cases.recovered, Cases.deceased
                    FROM Cases JOIN States JOIN Districts JOIN Zones 
                    ON Cases.state_id = States.id 
                    AND Cases.district_id = Districts.id 
                    AND Cases.zone_id = Zones.id
                    WHERE States.state = ? AND
                    DistrictS.district  = ?
                    ORDER BY Cases.confirmed, Cases.active, Cases.recovered, Cases.deceased
                    ''', (states[int(state_id)-1][1], district))

        covid_data = cursor.fetchone()
        # tableau_state_ids = ['viz1699272336150','viz1699272399492','viz1699272449653','viz1699272493570','viz1699272558205','viz1699272663003','viz1699272736951','viz1699272835962','viz1699272923197','viz1699272954795','viz1699273092907','viz1699273131939','viz1699273163397','viz1699273226955','viz1699273263804','viz1699273308247','viz1699273337681','viz1699273366331','viz1699273412768','viz1699273457077','viz1699273511804','viz1699273539469','viz1699273622550','viz1699273683071','viz1699273725026','viz1699273761984','viz1699273808065','viz1699273836864','viz1699273871695','viz1699273902429','viz1699273942376','viz1699273965892','viz1699273994038','viz1699274035988','viz1699274070290','viz1699274101871']
        # print(covid_data)
        from .data import data
        return render(request, 'index.html', {'covid_data': covid_data, 'state':states[int(state_id)-1][1], 'district':district,'tableau_state_id':data[int(state_id)-2],'getdata':True} )

    # If it's a GET request, show the form to select the state and city 
    cursor.execute('''
                  SELECT Districts.id, Districts.district
                    FROM Cases JOIN States JOIN Districts
                    ON Cases.state_id = States.id 
                    AND Cases.district_id = Districts.id 
                    WHERE States.id = 37
                    ''')
    districts = cursor.fetchall()
    conn.commit()
    conn.close()
    # print(districts)
    return render(request, 'index.html', {'states': states[1: ], 'districts': districts[1:],'selectdata':True})

def visualize(request):
    return render(request,'index.html', {'visualize':True})

def download(request):
    conn = sqlite3.connect('covid_cases.sqlite')
    cur = conn.cursor()

    fields = ['State', 'District', 'Zone', 'Confirmed', 'Active', 'Recovered', 'Deceased']

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="covid_data.csv"'

    csvwriter = csv.writer(response)
    csvwriter.writerow(fields)

    cur.execute('''
        SELECT States.state, Districts.district, Zones.zone,
        Cases.confirmed, Cases.active, Cases.recovered, Cases.deceased 
        FROM Cases JOIN States JOIN Districts JOIN Zones
        ON Cases.state_id = States.id
        AND Cases.district_id = Districts.id
        AND Cases.zone_id = Zones.id
        ORDER BY States.state, Districts.district
    ''')

    for row in cur:
        state = row[0]
        districts = row[1]
        zones = row[2]
        confirmed = row[3]
        active = row[4]
        recovered = row[5]
        deceased = row[6]
        csvwriter.writerow([state, districts, zones, confirmed, active, recovered, deceased])
    messages.add_message(request, messages.SUCCESS , "Succesfully downloaded the CSV file!")
    return response

def districts(request, state_id):
    # Fetch districts for the selected state
    conn = sqlite3.connect('covid_cases.sqlite')
    cursor = conn.cursor()
    cursor.execute('''SELECT Districts.id, Districts.district
                    FROM Cases JOIN States JOIN Districts
                    ON Cases.state_id = States.id 
                    AND Cases.district_id = Districts.id 
                    WHERE States.id = ? 
                    ''', (state_id,))
    districts = [{'id': str(district[0]), 'name': district[1]} for district in cursor.fetchall()[1:]]
    conn.close()
    return JsonResponse(districts, safe=False)



# views.py
from django.shortcuts import render, redirect
from .forms import ContactFormModel

def contact_view(request):
    if request.method == 'POST':
        form = ContactFormModel(request.POST)
        if form.is_valid():
            form.save()
            messages.add_message(request, messages.SUCCESS,"Thank you for your message. We will get back to you soon!")
            return redirect('/')  # Redirect to a success page after form submission
    else:
        form = ContactFormModel()

    return render(request, 'contact.html', {'form': form})
