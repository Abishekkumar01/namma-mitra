"""Static Karnataka reference data (districts, names, cities, RTOs...). Bilingual."""
from ..i18n import L
from ..flowkit import opt

# 31 districts (Ramanagara renamed Bengaluru South in 2025)
DISTRICTS = [
    ("bagalkote", "Bagalkote", "ಬಾಗಲಕೋಟೆ"), ("ballari", "Ballari", "ಬಳ್ಳಾರಿ"),
    ("belagavi", "Belagavi", "ಬೆಳಗಾವಿ"), ("bengaluru_rural", "Bengaluru Rural", "ಬೆಂಗಳೂರು ಗ್ರಾಮಾಂತರ"),
    ("bengaluru_urban", "Bengaluru Urban", "ಬೆಂಗಳೂರು ನಗರ"), ("bengaluru_south", "Bengaluru South (Ramanagara)", "ಬೆಂಗಳೂರು ದಕ್ಷಿಣ (ರಾಮನಗರ)"),
    ("bidar", "Bidar", "ಬೀದರ್"), ("chamarajanagar", "Chamarajanagar", "ಚಾಮರಾಜನಗರ"),
    ("chikkaballapur", "Chikkaballapur", "ಚಿಕ್ಕಬಳ್ಳಾಪುರ"), ("chikkamagaluru", "Chikkamagaluru", "ಚಿಕ್ಕಮಗಳೂರು"),
    ("chitradurga", "Chitradurga", "ಚಿತ್ರದುರ್ಗ"), ("dakshina_kannada", "Dakshina Kannada", "ದಕ್ಷಿಣ ಕನ್ನಡ"),
    ("davanagere", "Davanagere", "ದಾವಣಗೆರೆ"), ("dharwad", "Dharwad", "ಧಾರವಾಡ"),
    ("gadag", "Gadag", "ಗದಗ"), ("hassan", "Hassan", "ಹಾಸನ"), ("haveri", "Haveri", "ಹಾವೇರಿ"),
    ("kalaburagi", "Kalaburagi", "ಕಲಬುರಗಿ"), ("kodagu", "Kodagu", "ಕೊಡಗು"), ("kolar", "Kolar", "ಕೋಲಾರ"),
    ("koppal", "Koppal", "ಕೊಪ್ಪಳ"), ("mandya", "Mandya", "ಮಂಡ್ಯ"), ("mysuru", "Mysuru", "ಮೈಸೂರು"),
    ("raichur", "Raichur", "ರಾಯಚೂರು"), ("shivamogga", "Shivamogga", "ಶಿವಮೊಗ್ಗ"),
    ("tumakuru", "Tumakuru", "ತುಮಕೂರು"), ("udupi", "Udupi", "ಉಡುಪಿ"),
    ("uttara_kannada", "Uttara Kannada", "ಉತ್ತರ ಕನ್ನಡ"), ("vijayapura", "Vijayapura", "ವಿಜಯಪುರ"),
    ("vijayanagara", "Vijayanagara", "ವಿಜಯನಗರ"), ("yadgir", "Yadgir", "ಯಾದಗಿರಿ"),
]
DISTRICT_OPTIONS = [opt(k, L(en, kn)) for k, en, kn in DISTRICTS]
DISTRICT_NAME = {k: L(en, kn) for k, en, kn in DISTRICTS}
DISTRICT_INDEX = {k: i + 1 for i, (k, _, _) in enumerate(DISTRICTS)}

NAMES_M = [
    ("Ramesh Kumar", "ರಮೇಶ್ ಕುಮಾರ್"), ("Manjunath Gowda", "ಮಂಜುನಾಥ ಗೌಡ"), ("Basavaraj Patil", "ಬಸವರಾಜ ಪಾಟೀಲ"),
    ("Nagaraju H", "ನಾಗರಾಜು ಎಚ್"), ("Shivakumar S", "ಶಿವಕುಮಾರ್ ಎಸ್"), ("Prakash Hegde", "ಪ್ರಕಾಶ್ ಹೆಗ್ಡೆ"),
    ("Venkatesh Murthy", "ವೆಂಕಟೇಶ್ ಮೂರ್ತಿ"), ("Mahadevappa K", "ಮಹಾದೇವಪ್ಪ ಕೆ"), ("Girish Shetty", "ಗಿರೀಶ್ ಶೆಟ್ಟಿ"),
    ("Mallikarjun Hiremath", "ಮಲ್ಲಿಕಾರ್ಜುನ ಹಿರೇಮಠ"), ("Raghavendra Rao", "ರಾಘವೇಂದ್ರ ರಾವ್"),
    ("Santosh Naik", "ಸಂತೋಷ್ ನಾಯ್ಕ್"), ("Chandrashekar B", "ಚಂದ್ರಶೇಖರ್ ಬಿ"), ("Harish Poojary", "ಹರೀಶ್ ಪೂಜಾರಿ"),
    ("Siddappa Kamble", "ಸಿದ್ದಪ್ಪ ಕಾಂಬಳೆ"), ("Kiran Kumar", "ಕಿರಣ್ ಕುಮಾರ್"),
]
NAMES_F = [
    ("Lakshmi Devi", "ಲಕ್ಷ್ಮೀ ದೇವಿ"), ("Savitha R", "ಸವಿತಾ ಆರ್"), ("Kavya Gowda", "ಕಾವ್ಯ ಗೌಡ"),
    ("Shobha Patil", "ಶೋಭಾ ಪಾಟೀಲ"), ("Sunitha M", "ಸುನೀತಾ ಎಂ"), ("Anitha Shetty", "ಅನಿತಾ ಶೆಟ್ಟಿ"),
    ("Pooja Bhat", "ಪೂಜಾ ಭಟ್"), ("Renuka Hiremath", "ರೇಣುಕಾ ಹಿರೇಮಠ"), ("Bhagyalakshmi", "ಭಾಗ್ಯಲಕ್ಷ್ಮಿ"),
    ("Yashoda Naik", "ಯಶೋದಾ ನಾಯ್ಕ್"), ("Gowramma", "ಗೌರಮ್ಮ"), ("Nethra K", "ನೇತ್ರಾ ಕೆ"),
    ("Shwetha Rao", "ಶ್ವೇತಾ ರಾವ್"), ("Manjula B", "ಮಂಜುಳಾ ಬಿ"), ("Parvathi Kamble", "ಪಾರ್ವತಿ ಕಾಂಬಳೆ"),
    ("Rekha S", "ರೇಖಾ ಎಸ್"),
]

BANKS = [L("State Bank of India", "ಸ್ಟೇಟ್ ಬ್ಯಾಂಕ್ ಆಫ್ ಇಂಡಿಯಾ"), L("Canara Bank", "ಕೆನರಾ ಬ್ಯಾಂಕ್"),
         L("Karnataka Gramin Bank", "ಕರ್ನಾಟಕ ಗ್ರಾಮೀಣ ಬ್ಯಾಂಕ್"), L("Union Bank of India", "ಯೂನಿಯನ್ ಬ್ಯಾಂಕ್ ಆಫ್ ಇಂಡಿಯಾ"),
         L("Bank of Baroda", "ಬ್ಯಾಂಕ್ ಆಫ್ ಬರೋಡಾ"), L("Karnataka Bank", "ಕರ್ಣಾಟಕ ಬ್ಯಾಂಕ್")]

# ESCOM -> localities used for consumer addresses
ESCOMS = [
    ("bescom", "BESCOM", "ಬೆಸ್ಕಾಂ", "Bangalore Electricity Supply Company Ltd.", "ಬೆಂಗಳೂರು ವಿದ್ಯುತ್ ಸರಬರಾಜು ಕಂಪನಿ ನಿ."),
    ("mescom", "MESCOM", "ಮೆಸ್ಕಾಂ", "Mangalore Electricity Supply Company Ltd.", "ಮಂಗಳೂರು ವಿದ್ಯುತ್ ಸರಬರಾಜು ಕಂಪನಿ ನಿ."),
    ("hescom", "HESCOM", "ಹೆಸ್ಕಾಂ", "Hubli Electricity Supply Company Ltd.", "ಹುಬ್ಬಳ್ಳಿ ವಿದ್ಯುತ್ ಸರಬರಾಜು ಕಂಪನಿ ನಿ."),
    ("gescom", "GESCOM", "ಜೆಸ್ಕಾಂ", "Gulbarga Electricity Supply Company Ltd.", "ಗುಲ್ಬರ್ಗಾ ವಿದ್ಯುತ್ ಸರಬರಾಜು ಕಂಪನಿ ನಿ."),
    ("cesc", "CESC Mysore", "ಸೆಸ್ಕ್ ಮೈಸೂರು", "Chamundeshwari Electricity Supply Corporation Ltd.", "ಚಾಮುಂಡೇಶ್ವರಿ ವಿದ್ಯುತ್ ಸರಬರಾಜು ನಿಗಮ ನಿ."),
]
ESCOM_OPTIONS = [opt(k, L(en, kn), L(fe, fk)) for k, en, kn, fe, fk in ESCOMS]
ESCOM_NAME = {k: L(en, kn) for k, en, kn, _, _ in ESCOMS}
ESCOM_FULL = {k: L(fe, fk) for k, _, _, fe, fk in ESCOMS}
ESCOM_PREFIX = {"bescom": "BES", "mescom": "MES", "hescom": "HES", "gescom": "GES", "cesc": "CES"}
LOCALITIES = {
    "bescom": [("Jayanagar", "ಜಯನಗರ", "Bengaluru", "ಬೆಂಗಳೂರು"), ("Malleshwaram", "ಮಲ್ಲೇಶ್ವರಂ", "Bengaluru", "ಬೆಂಗಳೂರು"),
               ("Rajajinagar", "ರಾಜಾಜಿನಗರ", "Bengaluru", "ಬೆಂಗಳೂರು"), ("Yelahanka", "ಯಲಹಂಕ", "Bengaluru", "ಬೆಂಗಳೂರು"),
               ("Banashankari", "ಬನಶಂಕರಿ", "Bengaluru", "ಬೆಂಗಳೂರು"), ("SIT Extension", "ಎಸ್‌ಐಟಿ ಬಡಾವಣೆ", "Tumakuru", "ತುಮಕೂರು")],
    "mescom": [("Kadri", "ಕದ್ರಿ", "Mangaluru", "ಮಂಗಳೂರು"), ("Bejai", "ಬಿಜೈ", "Mangaluru", "ಮಂಗಳೂರು"),
               ("Manipal", "ಮಣಿಪಾಲ", "Udupi", "ಉಡುಪಿ"), ("Vinoba Nagar", "ವಿನೋಬ ನಗರ", "Shivamogga", "ಶಿವಮೊಗ್ಗ")],
    "hescom": [("Vidyanagar", "ವಿದ್ಯಾನಗರ", "Hubballi", "ಹುಬ್ಬಳ್ಳಿ"), ("Saptapur", "ಸಪ್ತಾಪುರ", "Dharwad", "ಧಾರವಾಡ"),
               ("Tilakwadi", "ತಿಳಕವಾಡಿ", "Belagavi", "ಬೆಳಗಾವಿ"), ("Navanagar", "ನವನಗರ", "Bagalkote", "ಬಾಗಲಕೋಟೆ")],
    "gescom": [("Aland Road", "ಆಳಂದ ರಸ್ತೆ", "Kalaburagi", "ಕಲಬುರಗಿ"), ("Cowl Bazaar", "ಕೌಲ್ ಬಜಾರ್", "Ballari", "ಬಳ್ಳಾರಿ"),
               ("Gandhi Chowk", "ಗಾಂಧಿ ಚೌಕ", "Bidar", "ಬೀದರ್"), ("Station Road", "ಸ್ಟೇಷನ್ ರಸ್ತೆ", "Raichur", "ರಾಯಚೂರು")],
    "cesc": [("Kuvempunagar", "ಕುವೆಂಪುನಗರ", "Mysuru", "ಮೈಸೂರು"), ("Saraswathipuram", "ಸರಸ್ವತಿಪುರಂ", "Mysuru", "ಮೈಸೂರು"),
             ("Ashok Nagar", "ಅಶೋಕ ನಗರ", "Mandya", "ಮಂಡ್ಯ"), ("Vidyanagar", "ವಿದ್ಯಾನಗರ", "Hassan", "ಹಾಸನ")],
}

# KSRTC cities: key -> (en, kn, lat, lon, in_karnataka)
CITIES = {
    "bengaluru": ("Bengaluru", "ಬೆಂಗಳೂರು", 12.97, 77.59, True),
    "mysuru": ("Mysuru", "ಮೈಸೂರು", 12.30, 76.64, True),
    "mangaluru": ("Mangaluru", "ಮಂಗಳೂರು", 12.91, 74.86, True),
    "hubballi": ("Hubballi", "ಹುಬ್ಬಳ್ಳಿ", 15.36, 75.12, True),
    "belagavi": ("Belagavi", "ಬೆಳಗಾವಿ", 15.85, 74.50, True),
    "kalaburagi": ("Kalaburagi", "ಕಲಬುರಗಿ", 17.33, 76.83, True),
    "davanagere": ("Davanagere", "ದಾವಣಗೆರೆ", 14.46, 75.92, True),
    "shivamogga": ("Shivamogga", "ಶಿವಮೊಗ್ಗ", 13.93, 75.57, True),
    "udupi": ("Udupi", "ಉಡುಪಿ", 13.34, 74.75, True),
    "hassan": ("Hassan", "ಹಾಸನ", 13.00, 76.10, True),
    "ballari": ("Ballari", "ಬಳ್ಳಾರಿ", 15.14, 76.92, True),
    "vijayapura": ("Vijayapura", "ವಿಜಯಪುರ", 16.83, 75.71, True),
    "tumakuru": ("Tumakuru", "ತುಮಕೂರು", 13.34, 77.10, True),
    "chikkamagaluru": ("Chikkamagaluru", "ಚಿಕ್ಕಮಗಳೂರು", 13.32, 75.77, True),
    "madikeri": ("Madikeri", "ಮಡಿಕೇರಿ", 12.42, 75.74, True),
    "karwar": ("Karwar", "ಕಾರವಾರ", 14.81, 74.13, True),
    "dharmasthala": ("Dharmasthala", "ಧರ್ಮಸ್ಥಳ", 12.95, 75.38, True),
    "kukke": ("Kukke Subramanya", "ಕುಕ್ಕೆ ಸುಬ್ರಹ್ಮಣ್ಯ", 12.66, 75.61, True),
    "hosapete": ("Hosapete (Hampi)", "ಹೊಸಪೇಟೆ (ಹಂಪಿ)", 15.27, 76.39, True),
    "bidar": ("Bidar", "ಬೀದರ್", 17.91, 77.52, True),
    "chennai": ("Chennai", "ಚೆನ್ನೈ", 13.08, 80.27, False),
    "hyderabad": ("Hyderabad", "ಹೈದರಾಬಾದ್", 17.39, 78.49, False),
    "panaji": ("Panaji (Goa)", "ಪಣಜಿ (ಗೋವಾ)", 15.49, 73.83, False),
    "pune": ("Pune", "ಪುಣೆ", 18.52, 73.86, False),
    "tirupati": ("Tirupati", "ತಿರುಪತಿ", 13.63, 79.42, False),
}
CITY_OPTIONS = [opt(k, L(v[0], v[1])) for k, v in CITIES.items()]
CITY_NAME = {k: L(v[0], v[1]) for k, v in CITIES.items()}
BOARDING = {
    "bengaluru": [L("Kempegowda Bus Station (Majestic)", "ಕೆಂಪೇಗೌಡ ಬಸ್ ನಿಲ್ದಾಣ (ಮೆಜೆಸ್ಟಿಕ್)"),
                  L("Mysuru Road Satellite Bus Station", "ಮೈಸೂರು ರಸ್ತೆ ಸ್ಯಾಟಲೈಟ್ ಬಸ್ ನಿಲ್ದಾಣ"),
                  L("Shantinagar TTMC", "ಶಾಂತಿನಗರ ಟಿಟಿಎಂಸಿ")],
}

# Bus classes: key -> (en, kn, rate per km, Shakti scheme applicable)
BUS_TYPES = {
    "sarige": ("Karnataka Sarige (Express)", "ಕರ್ನಾಟಕ ಸಾರಿಗೆ (ಎಕ್ಸ್‌ಪ್ರೆಸ್)", 1.00, True),
    "rajahamsa": ("Rajahamsa Executive", "ರಾಜಹಂಸ ಎಕ್ಸಿಕ್ಯೂಟಿವ್", 1.30, False),
    "airavat": ("Airavat (Volvo AC)", "ಐರಾವತ (ವೋಲ್ವೋ ಎಸಿ)", 1.80, False),
    "club": ("Airavat Club Class", "ಐರಾವತ ಕ್ಲಬ್ ಕ್ಲಾಸ್", 2.05, False),
    "ambaari": ("Ambaari Utsav (AC Sleeper)", "ಅಂಬಾರಿ ಉತ್ಸವ (ಎಸಿ ಸ್ಲೀಪರ್)", 2.40, False),
    "ev": ("EV Power Plus (Electric AC)", "ಇವಿ ಪವರ್ ಪ್ಲಸ್ (ವಿದ್ಯುತ್ ಎಸಿ)", 1.90, False),
}

RTO = {
    "01": ("Bengaluru Central (Koramangala)", "ಬೆಂಗಳೂರು ಕೇಂದ್ರ (ಕೋರಮಂಗಲ)"), "02": ("Bengaluru West (Rajajinagar)", "ಬೆಂಗಳೂರು ಪಶ್ಚಿಮ (ರಾಜಾಜಿನಗರ)"),
    "03": ("Bengaluru East (Indiranagar)", "ಬೆಂಗಳೂರು ಪೂರ್ವ (ಇಂದಿರಾನಗರ)"), "04": ("Bengaluru North (Yeshwanthpur)", "ಬೆಂಗಳೂರು ಉತ್ತರ (ಯಶವಂತಪುರ)"),
    "05": ("Bengaluru South (Jayanagar)", "ಬೆಂಗಳೂರು ದಕ್ಷಿಣ (ಜಯನಗರ)"), "09": ("Mysuru West", "ಮೈಸೂರು ಪಶ್ಚಿಮ"),
    "19": ("Mangaluru", "ಮಂಗಳೂರು"), "20": ("Udupi", "ಉಡುಪಿ"), "22": ("Belagavi", "ಬೆಳಗಾವಿ"),
    "25": ("Dharwad", "ಧಾರವಾಡ"), "32": ("Kalaburagi", "ಕಲಬುರಗಿ"), "41": ("Bengaluru (Jnanabharathi)", "ಬೆಂಗಳೂರು (ಜ್ಞಾನಭಾರತಿ)"),
    "51": ("Bengaluru (Electronic City)", "ಬೆಂಗಳೂರು (ಎಲೆಕ್ಟ್ರಾನಿಕ್ ಸಿಟಿ)"), "53": ("Bengaluru (K.R. Puram)", "ಬೆಂಗಳೂರು (ಕೆ.ಆರ್. ಪುರಂ)"),
}

VEHICLES = [  # maker/model, fuel, class, two_wheeler
    ("Maruti Suzuki Swift VXI", "Petrol", "LMV - Motor Car", False),
    ("Hyundai Creta SX", "Diesel", "LMV - Motor Car", False),
    ("Tata Nexon EV", "Electric", "LMV - Motor Car", False),
    ("Kia Seltos HTX", "Petrol", "LMV - Motor Car", False),
    ("Mahindra Scorpio-N Z8", "Diesel", "LMV - Motor Car", False),
    ("Toyota Innova Crysta", "Diesel", "LMV - Motor Car", False),
    ("Honda Activa 6G", "Petrol", "M-Cycle/Scooter", True),
    ("TVS Jupiter 125", "Petrol", "M-Cycle/Scooter", True),
    ("Royal Enfield Classic 350", "Petrol", "M-Cycle/Scooter", True),
    ("Bajaj Pulsar 150", "Petrol", "M-Cycle/Scooter", True),
    ("Ather 450X", "Electric", "M-Cycle/Scooter", True),
]
FUEL_KN = {"Petrol": "ಪೆಟ್ರೋಲ್", "Diesel": "ಡೀಸೆಲ್", "Electric": "ವಿದ್ಯುತ್"}

JUNCTIONS = [L("Silk Board Junction", "ಸಿಲ್ಕ್ ಬೋರ್ಡ್ ಜಂಕ್ಷನ್"), L("Hebbal Flyover", "ಹೆಬ್ಬಾಳ ಮೇಲ್ಸೇತುವೆ"),
             L("K.R. Circle", "ಕೆ.ಆರ್. ವೃತ್ತ"), L("Trinity Circle", "ಟ್ರಿನಿಟಿ ವೃತ್ತ"),
             L("Mekhri Circle", "ಮೇಖ್ರಿ ವೃತ್ತ"), L("Town Hall Junction", "ಟೌನ್ ಹಾಲ್ ಜಂಕ್ಷನ್"),
             L("Marathahalli Bridge", "ಮಾರತಹಳ್ಳಿ ಸೇತುವೆ")]
OFFENCES = [
    (L("Riding without helmet", "ಹೆಲ್ಮೆಟ್ ಇಲ್ಲದೆ ಸವಾರಿ"), 500, True),
    (L("Jumping traffic signal", "ಸಿಗ್ನಲ್ ಜಂಪ್"), 500, None),
    (L("Wrong side driving", "ವಿರುದ್ಧ ದಿಕ್ಕಿನಲ್ಲಿ ಚಾಲನೆ"), 500, None),
    (L("Over speeding", "ಅತಿ ವೇಗ"), 1000, None),
    (L("No seat belt", "ಸೀಟ್ ಬೆಲ್ಟ್ ಧರಿಸಿಲ್ಲ"), 500, False),
    (L("Parking in no-parking zone", "ನಿಷೇಧಿತ ಸ್ಥಳದಲ್ಲಿ ನಿಲುಗಡೆ"), 500, None),
    (L("Using mobile phone while driving", "ಚಾಲನೆ ವೇಳೆ ಮೊಬೈಲ್ ಬಳಕೆ"), 1500, None),
]

NAKSHATRAS = [
    ("Ashwini", "ಅಶ್ವಿನಿ"), ("Bharani", "ಭರಣಿ"), ("Krittika", "ಕೃತ್ತಿಕಾ"), ("Rohini", "ರೋಹಿಣಿ"),
    ("Mrigashira", "ಮೃಗಶಿರ"), ("Ardra", "ಆರ್ದ್ರಾ"), ("Punarvasu", "ಪುನರ್ವಸು"), ("Pushya", "ಪುಷ್ಯ"),
    ("Ashlesha", "ಆಶ್ಲೇಷ"), ("Magha", "ಮಘಾ"), ("Purva Phalguni", "ಪೂರ್ವ ಫಲ್ಗುಣಿ"),
    ("Uttara Phalguni", "ಉತ್ತರ ಫಲ್ಗುಣಿ"), ("Hasta", "ಹಸ್ತ"), ("Chitra", "ಚಿತ್ತಾ"), ("Swati", "ಸ್ವಾತಿ"),
    ("Vishakha", "ವಿಶಾಖ"), ("Anuradha", "ಅನುರಾಧ"), ("Jyeshtha", "ಜ್ಯೇಷ್ಠ"), ("Mula", "ಮೂಲ"),
    ("Purva Ashadha", "ಪೂರ್ವಾಷಾಢ"), ("Uttara Ashadha", "ಉತ್ತರಾಷಾಢ"), ("Shravana", "ಶ್ರವಣ"),
    ("Dhanishta", "ಧನಿಷ್ಠ"), ("Shatabhisha", "ಶತಭಿಷ"), ("Purva Bhadrapada", "ಪೂರ್ವಾಭಾದ್ರ"),
    ("Uttara Bhadrapada", "ಉತ್ತರಾಭಾದ್ರ"), ("Revati", "ರೇವತಿ"),
]
NAKSHATRA_OPTIONS = [opt(en.lower().replace(" ", "_"), L(en, kn)) for en, kn in NAKSHATRAS]
