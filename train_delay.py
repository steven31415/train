import urllib2
import json
from datetime import datetime
from datetime import timedelta
import iso8601

# Huxley website
huxley = "https://huxley.apphb.com/"

# Access token key
#key = "DA1C7740-9DA0-11E4-80E6-A920340000B1"
key = "029ce3c3-91ed-492c-bca5-f9d95a6a848d"

# Load and store data for station names
stationNameDataURL = "https://huxley.apphb.com/crs"
stationNameData = json.loads(urllib2.urlopen(stationNameDataURL).read())

# List of London Terminal codes
londonTerminals =  ["BFR",
					"CST",
					"CHX",
					"CTK",
					"EUS",
					"FST",
					"KGX",
					"LST",
					"LBG",
					"MYB",
					"MOG",
					"OLD",
					"PAD",
					"STP",
					"VXH",
					"VIC",
					"WAT",
					"WAE"]

# Convert Huxley request URL into JSON response
def parseURL(url):
	r = urllib2.urlopen(url).read()
	return json.loads(r)

# Get arrivals board for station
def arrivalsRequest(stationCode, rows=99):
	url = huxley + "arrivals/" + stationCode + "/" + str(rows) + "?accessToken=" + key
	return parseURL(url)

# Get departures board for station
def departuresRequest(stationCode, rows=99):
	url = huxley + "departures/" + stationCode + "/" + str(rows) + "?accessToken=" + key
	return parseURL(url)

# Get details for specific service
def serviceRequest(serviceID):
	url = huxley + "service/" + serviceID + "?accessToken=" + key
	return parseURL(url)

# Convert 3 character station code to plain text
def stationCodeToText(stationCode):
	for record in stationNameData:
		if (record["crsCode"].lower() == stationCode.lower()):
			return record["stationName"]

# Convert station plain text to 3 character code
def stationTextToCode(stationText):
	for record in stationNameData:
		if (record["stationName"].lower() == stationText.lower()):
			return record["crsCode"]

# Check if station code represents a London Terminal
def isLondonTerminal(stationCode):
	return stationCode in londonTerminals

# Return details of recent and upcoming services between start and end station
def getCurrentServicesBetween(startStationCode, endStationCode, maxJourneyTime):
	# Create empty array to store services
	services = []

	# Get arrivals board for end station
	arrivalsData = arrivalsRequest(endStationCode)

	if (arrivalsData["trainServices"] == None):
		return services

	for arrival in arrivalsData["trainServices"]:
		serviceID = arrival["serviceIdUrlSafe"]
		service = serviceRequest(serviceID)

		# Check if arrival previously called at start station
		startStationCallingPoint = False
		for callingPoint in service["previousCallingPoints"][0]["callingPoint"]:
			if callingPoint["crs"].lower() == startStationCode.lower():
				startStationCallingPoint = callingPoint
				break

		# If arrival previously called at start station
		if (startStationCallingPoint):
			# Start station name
			from_csr = startStationCallingPoint["crs"]

			# Start station stated time of departure
			from_std = datetime.strptime(startStationCallingPoint["st"], "%H:%M")

			# Start station actual time of departure
			# If not departed yet, actual time = None
			from_atd = startStationCallingPoint["at"]

			if (from_atd == "On time"):
				from_atd = from_std
			elif (from_atd == "Delayed"):
				from_atd == "Delayed"
			elif (from_atd == "Cancelled"):
				from_atd == "Cancelled"
			elif (from_atd != None):
				from_atd = datetime.strptime(from_atd, "%H:%M")
			
			# End station name
			to_csr = service["crs"]

			# End station stated time of arrival
			to_sta = datetime.strptime(service["sta"], "%H:%M")

			# End station estimated time of arrival
			to_eta = service["eta"]
			to_ata = service["ata"]

			if (to_eta == "On time" or to_ata == "On time"):
				to_eta = to_sta
			elif (to_eta == "Delayed" or to_ata == "Delayed"):
				to_eta == "Delayed"
			elif (to_eta == "Cancelled" or to_ata == "Cancelled"):
				to_eta == "Cancelled"
			elif (to_eta != None):
				to_eta = datetime.strptime(to_eta, "%H:%M")
			elif (to_ata != None):
				to_eta = datetime.strptime(to_ata, "%H:%M")

			# Calculate stated date of departure
			dt = iso8601.parse_date(service["generatedAt"])

			yesterday, today, tomorrow = dt, dt, dt
			yesterday = yesterday + timedelta(days=1)
			tomorrow = tomorrow - timedelta(days=1)

			yesterday = datetime(yesterday.year, yesterday.month, yesterday.day, from_std.hour, from_std.minute)
			today = datetime(today.year, today.month, today.day, from_std.hour, from_std.minute)
			tomorrow = datetime(tomorrow.year, tomorrow.month, tomorrow.day, from_std.hour, from_std.minute)

			dt = datetime(dt.year, dt.month, dt.day, dt.hour, dt.minute)

			yesterday_diff = (yesterday - dt).total_seconds() if (yesterday - dt).total_seconds() >= 0 else (dt - yesterday).total_seconds()
			today_diff = (today - dt).total_seconds() if (today - dt).total_seconds() >= 0 else (dt - today).total_seconds()
			tomorrow_diff = (tomorrow - dt).total_seconds() if (tomorrow - dt).total_seconds() >= 0 else (dt - tomorrow).total_seconds()

			minDiff = min(yesterday_diff, today_diff, tomorrow_diff)

			if (minDiff == yesterday_diff):
				service_date = datetime(yesterday.year, yesterday.month, yesterday.day)
			elif (minDiff == today_diff):
				service_date = datetime(today.year, today.month, today.day)
			elif (minDiff == tomorrow_diff):
				service_date = date(tomorrow.year, tomorrow.month, tomorrow.day)

			# Calculate official stated journey time
			journeyTime = (to_sta - from_std).seconds / 60

			# Correct for journeys taking place across midnight boundary
			if (journeyTime < 0):
				journeyTime = 60 * 24 + journeyTime

			# Calculate delay
			delay = ((to_eta - to_sta).total_seconds() / 60) if isinstance(to_eta, datetime) else None

			# Ignore journeys taking longer than specified max journey time
			if (journeyTime <= maxJourneyTime):
				# Store data in custom format
				formattedService = 	{
							"serviceID" : serviceID,
							"from_csr" 	: from_csr,
							"from_std" 	: "{:%H:%M}".format(from_std) if isinstance(from_std, datetime) else from_std,
							"from_atd" 	: "{:%H:%M}".format(from_atd) if isinstance(from_atd, datetime) else from_atd,
							"to_csr" 	: to_csr,
							"to_sta"	: "{:%H:%M}".format(to_sta) if isinstance(to_sta, datetime) else to_sta,
							"to_eta"	: "{:%H:%M}".format(to_eta) if isinstance(to_eta, datetime) else to_eta,
							"date"		: "{:%B %d}".format(service_date),
							"delay"		: delay,
				}

				# Add service to list of services to return
				services.append(formattedService)

	return services

def updateData(file, routes):
	for route in routes:
		startStation = route["startStation"]
		endStation = route["endStation"]
		maxJourneyTime = route["maxJourneyTime"]

		with open(file, "r") as f:
			data = json.load(f)

		services = getCurrentServicesBetween(startStation, endStation, maxJourneyTime)

		for service in services:
			serviceExists = False

			for index, item in enumerate(data):
				if (item["serviceID"] == service["serviceID"]):
					data[index] = service
					serviceExists = True
					break

			if (not serviceExists):
				data.append(service)

		# Truncate data
		truncatedData = []

		maxDataItems = 100
		startIndex = (len(data) - maxDataItems if len(data) - maxDataItems > 0 else 0)

		for i in reversed(range(startIndex, len(data))):
			truncatedData.insert(0, data[i])

		# Sort data
		truncatedData = sorted(truncatedData, key=lambda k: k["to_csr"])
		truncatedData = sorted(truncatedData, key=lambda k: k["from_csr"])

		# Write data
		with open(file, "w") as f:
			json.dump(truncatedData, f)

def reverseRoutes(routes):
	rr = []

	for route in routes:
		rr.append(
			{	
				"startStation": route["endStation"],
				"endStation" : route["startStation"],
				"maxJourneyTime" : route["maxJourneyTime"],
			}
		)

	return rr

def createSummary(inFile, outFile, summaryFile):
	with open(inFile, "r") as f:
		inData = json.load(f)

	with open(outFile, "r") as f:
		outData = json.load(f)

	inHeading = "\n####################\n###   GOING IN   ###\n####################\n"
	outHeading = "\n####################\n###  GOING  OUT  ###\n####################\n"

	def makeRecords(data):
		records = ""
		currentStation = ""
		currentDate = ""

		for item in data:
			if item["from_csr"] != currentStation:
				records += "\n" + "ORIGIN: " + stationCodeToText(item["from_csr"]) + "\n"
				currentStation = item["from_csr"]

			if (item["delay"] == 0):
				continue

			records += item["from_csr"].upper() + "(" + item["from_std"] + ")" + " -> " + item["to_csr"].upper()  + "(" + item["to_sta"] + ")" + "\t"

			if (item["from_atd"] == "Cancelled" or item["to_eta"] == "Cancelled"):
				records += "CANCELLED"
			elif (item["from_atd"] == "Delayed" or item["to_eta"] == "Delayed"):
				records += "DELAYED"
			elif (item["delay"]):
				records += "DELAYED BY " + str(int(item["delay"])) + " MINUTES"

			records += "\n"

		return records

	output = ""

	output += inHeading
	output += makeRecords(inData)

	output += "\n"

	output += outHeading
	output += makeRecords(outData)

	with open(summaryFile, "w") as f:
		f.write(output)

##################################
########## MAIN PROGRAM ##########
##################################

routes = 	[	{	"startStation": "grv",
					"endStation" : "stp",
					"maxJourneyTime" : 60,
				},
				{	"startStation": "grv",
					"endStation" : "chx",
					"maxJourneyTime" : 120,
				},
			]

inFile = "/home/pi/Scripts/train_delay/in.json"
outFile = "/home/pi/Scripts/train_delay/out.json"

updateData(inFile, routes)
routes = reverseRoutes(routes)
updateData(outFile, routes)

summaryFile = "/var/www/owncloud/train_delay.txt"
createSummary(inFile, outFile, summaryFile)

