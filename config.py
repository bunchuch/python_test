HEADERS_44 = [
    "PrimaryDocNbr", "PNRCreateDate", "VCRCreateDate", "Airline", "Country", "City", "PCC",
    "AgentSine", "CouponStatus", "ClassOfService", "FltNo", "OperatingFlightNbr",
    "MarketingAirlineCode", "OperatingAirlineCode", "Sector", "Fare", "CreateIATANr",
    "CustomerFullName", "BookingCode", "FareBasisCode", "TourCode", "CouponSeqNbr",
    "SegmentTypeCode", "ServiceStartDate", "ServiceStartTime", "ServiceEndDate",
    "ServiceEndTime", "FlownFlightNbr", "FlownServiceStartDate", "FlownServiceStartCity",
    "FlownServiceEndCity", "FlownClassOfService", "FlownFlightOrigDate", "ServiceStartCity",
    "ServiceEndCity", "OD", "Kind", "Origin", "Destination", "CountryName",
    "RegionName", "Nationality", "NationalName", "TTYAirlineCode"
]

# 18=TkDocument, 19=TkCoupon, 20=TkTax, 21=TkTaxDetail, 22=TkPayment,
# 23=TktRemark, 25=TkDocumentHistory, 26=TktCouponHistory,
# 27=TkEndorsement, 29=TkProRation
TICKET_RECORD_TYPES = {"18", "19", "20", "21", "22", "23", "25", "26", "27", "29"}

# 00=Res, 01=ResFlight, 04=ResPassengerFT, 05=ResRemarks, 06=PreResSeat,
# 07=ResPaxDoc, 08=ResSuspDocAgmt, 09=ResSuspTimeLmt, 10=ResEmergencyCtc,
# 11=ResPassenger, 12=ResSSR, 13=ResTravelArranger, 14=ResPassengerEmail,
# 15=ResPassengerPhone, 16=ResODFlight, 28=ResDataIndex
PNR_RECORD_TYPES = {"00","01","04","05","06","07","08","09","10","11","12","13","14","15","16","28"}

# First 3 digits of 13-digit e-ticket → 2-letter IATA code
AIRLINE_PREFIX = {
    "014":"AC",  # Air Canada
    "016":"UA",  # United Airlines
    "018":"CP",  # Canadian Airlines
    "020":"LH",  # Lufthansa
    "027":"JM",  # Air Jamaica
    "042":"PK",  # Pakistan Airlines
    "043":"PX",  # Air Niugini
    "044":"EY",  # Etihad Airways
    "045":"AR",  # Aerolineas Argentinas
    "047":"AV",  # Avianca
    "048":"KL",  # KLM Royal Dutch
    "050":"MS",  # Egyptair
    "055":"OS",  # Austrian Airlines
    "057":"AF",  # Air France
    "060":"MP",  # Martinair
    "064":"DE",  # Condor
    "065":"LO",  # LOT Polish Airlines
    "071":"ET",  # Ethiopian Airlines
    "072":"GF",  # Gulf Air
    "074":"WA",  # KLM Cityhopper
    "076":"SQ",  # Singapore Airlines
    "077":"BD",  # bmi British Midland
    "079":"AI",  # Air India
    "080":"OK",  # Czech Airlines
    "081":"QF",  # Qantas
    "082":"OZ",  # Asiana Airlines
    "083":"SA",  # South African Airways
    "086":"CA",  # Air China
    "098":"KC",  # Air Astana
    "105":"AY",  # Finnair
    "106":"UL",  # Sri Lankan Airlines
    "112":"NX",  # Air Macau
    "114":"TG",  # Thai Airways
    "117":"SK",  # SAS Scandinavian
    "118":"LX",  # Swiss International
    "125":"BA",  # British Airways
    "129":"CM",  # Copa Airlines
    "131":"JL",  # Japan Airlines
    "134":"CX",  # Cathay Pacific
    "137":"NZ",  # Air New Zealand
    "139":"MU",  # China Eastern
    "145":"FI",  # IcelandAir
    "149":"AT",  # Royal Air Maroc
    "160":"IB",  # Iberia
    "169":"TP",  # TAP Air Portugal
    "170":"CI",  # China Airlines
    "172":"BI",  # Royal Brunei
    "176":"EK",  # Emirates
    "180":"KE",  # Korean Air
    "185":"AZ",  # Alitalia / ITA Airways
    "188":"K6",  # Air Cambodia
    "201":"EI",  # Aer Lingus
    "202":"MK",  # Air Mauritius
    "205":"NH",  # ANA All Nippon
    "206":"GA",  # Garuda Indonesia
    "214":"VN",  # Vietnam Airlines
    "217":"FD",  # Thai AirAsia
    "220":"CL",  # Lufthansa CityLine
    "230":"WY",  # Oman Air
    "232":"MH",  # Malaysia Airlines
    "235":"TK",  # Turkish Airlines
    "258":"BR",  # EVA Air
    "260":"NZ",  # Air New Zealand Link
    "265":"HU",  # Hainan Airlines
    "268":"K6",  # Cambodia Angkor Air
    "279":"JS",  # Air Koryo
    "297":"CZ",  # China Southern
    "312":"BG",  # Biman Bangladesh
    "330":"DL",  # Delta Air Lines
    "350":"5J",  # Cebu Pacific
    "357":"LG",  # Luxair
    "406":"CF",  # China Postal Airlines
    "412":"AM",  # Aeromexico
    "444":"JJ",  # TAM Airlines (LATAM)
    "479":"B6",  # JetBlue Airways
    "489":"IX",  # Air India Express
    "502":"EK",  # Emirates (alt)
    "531":"D7",  # AirAsia X
    "555":"VJ",  # Vietjet Air
    "566":"7C",  # Jeju Air
    "574":"8M",  # Myanmar Airways
    "575":"SC",  # Shandong Airlines
    "580":"PR",  # Philippine Airlines
    "607":"QH",  # Bamboo Airways
    "618":"UL",  # SriLankan Airlines
    "631":"6T",  # Air Mandalay
    "657":"NK",  # Spirit Airlines
    "680":"K6",  # Air Cambodia (alt)
    "695":"AA",  # American Airlines
    "706":"WS",  # WestJet
    "714":"AI",  # Air India (alt)
    "724":"F9",  # Frontier Airlines
    "769":"SY",  # Sun Country
    "781":"WN",  # Southwest Airlines
    "784":"G4",  # Allegiant Air
    "812":"S7",  # Siberia Airlines
    "826":"TS",  # Transat
    "832":"AS",  # Alaska Airlines
    "871":"HA",  # Hawaiian Airlines
    "880":"SU",  # Aeroflot
    "897":"A3",  # Aegean Airlines
    "932":"9W",  # Jet Airways
    "988":"BT",  # Air Baltic
    "998":"VS",  # Virgin Atlantic
    "182":"K6",  # Air Cambodia
    "189":"K6",  # Air Cambodia
    "190":"K6",  # Air Cambodia
}

COUNTRY_MAP = {
    "KH":"Cambodia","TH":"Thailand","VN":"Vietnam","AE":"United Arab Emirates",
    "HK":"Hong Kong","SG":"Singapore","MY":"Malaysia","ID":"Indonesia",
    "PH":"Philippines","MM":"Myanmar","LA":"Laos","CN":"China","JP":"Japan",
    "KR":"South Korea","IN":"India","AU":"Australia","NZ":"New Zealand",
    "GB":"United Kingdom","DE":"Germany","FR":"France","IT":"Italy","ITA":"Italy",
    "CH":"Switzerland","AT":"Austria","LU":"Luxembourg","US":"United States",
    "CA":"Canada","DZ":"Algeria","MA":"Morocco","SA":"Saudi Arabia",
    "QA":"Qatar","EG":"Egypt","LK":"Sri Lanka","BE":"Belgium","NL":"Netherlands",
    "SE":"Sweden","NO":"Norway","DK":"Denmark","ES":"Spain","PT":"Portugal",
    "GR":"Greece","PL":"Poland","CZ":"Czech Republic","FI":"Finland",
    "TR":"Turkey","ZA":"South Africa","BR":"Brazil",
}

REGION_MAP = {
    "KH":"Southeast Asia","TH":"Southeast Asia","VN":"Southeast Asia",
    "SG":"Southeast Asia","MY":"Southeast Asia","ID":"Southeast Asia",
    "PH":"Southeast Asia","MM":"Southeast Asia","LA":"Southeast Asia",
    "CN":"East Asia","JP":"East Asia","KR":"East Asia","HK":"East Asia",
    "AE":"Middle East","SA":"Middle East","QA":"Middle East",
    "EG":"Africa","DZ":"Africa","ZA":"Africa",
    "IN":"South Asia","LK":"South Asia",
    "AU":"Oceania","NZ":"Oceania",
    "US":"North America","CA":"North America",
    "BR":"South America",
    "GB":"Europe","DE":"Europe","FR":"Europe","IT":"Europe","ITA":"Europe",
    "CH":"Europe","AT":"Europe","LU":"Europe","NL":"Europe","BE":"Europe",
    "SE":"Europe","NO":"Europe","DK":"Europe","ES":"Europe","PT":"Europe",
    "GR":"Europe","PL":"Europe","CZ":"Europe","FI":"Europe","TR":"Europe",
}

NAT_MAP = {
    "AT":"Austrian","DE":"German","GB":"British","IT":"Italian","ITA":"Italian",
    "CH":"Swiss","FR":"French","NL":"Dutch","BE":"Belgian","SE":"Swedish",
    "DZ":"Algerian","KH":"Cambodian","TH":"Thai","VN":"Vietnamese",
    "CN":"Chinese","JP":"Japanese","KR":"Korean","AU":"Australian",
    "US":"American","CA":"Canadian","AE":"Emirati","IN":"Indian",
}

AIRPORT_CITY = {
    "KTI":"Koh Kong","SAI":"Ho Chi Minh City","SGN":"Ho Chi Minh City",
    "PNH":"Phnom Penh","REP":"Siem Reap","BKK":"Bangkok","HKG":"Hong Kong",
    "CDG":"Paris","LHR":"London","FRA":"Frankfurt","MUC":"Munich",
    "AUH":"Abu Dhabi","DXB":"Dubai","SIN":"Singapore","ALG":"Algiers",
    "MRS":"Marseille","NCE":"Nice","NTE":"Nantes",
}
