from flask import Flask, render_template, jsonify, request
import requests
import time
import json
import os

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------
_cache = {
    "data": None,
    "timestamp": 0,
    "ttl": 3600,  # 1 hour
}

# ---------------------------------------------------------------------------
# Overpass
# ---------------------------------------------------------------------------
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OVERPASS_QUERY = """
[out:json][timeout:30];
area["name"="東京都区部"]->.tokyo23;
node["amenity"="bench"](area.tokyo23);
out body;
"""

# ---------------------------------------------------------------------------
# User-submitted bench storage
# ---------------------------------------------------------------------------
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
USER_BENCHES_FILE = os.path.join(DATA_DIR, "user_benches.json")


def _load_user_benches():
    if not os.path.exists(USER_BENCHES_FILE):
        return []
    with open(USER_BENCHES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_user_benches(benches):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(USER_BENCHES_FILE, "w", encoding="utf-8") as f:
        json.dump(benches, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Fallback bench data (~50 realistic locations across Tokyo 23 wards)
# ---------------------------------------------------------------------------
FALLBACK_BENCHES = [
    # --- Ueno Park & surrounding (台東区) ---
    {"id": 900001, "lat": 35.7146, "lon": 139.7732, "tags": {"name": "Ueno Park Main Path", "backrest": "yes", "material": "wood", "covered": "no"}},
    {"id": 900002, "lat": 35.7155, "lon": 139.7740, "tags": {"backrest": "yes", "material": "wood"}},
    {"id": 900003, "lat": 35.7138, "lon": 139.7720, "tags": {"covered": "yes", "backrest": "yes", "material": "metal"}},
    {"id": 900004, "lat": 35.7161, "lon": 139.7750, "tags": {"name": "Shinobazu Pond Bench", "material": "wood", "backrest": "yes"}},
    {"id": 900005, "lat": 35.7130, "lon": 139.7745, "tags": {"material": "stone", "seats": "3"}},
    {"id": 900006, "lat": 35.7148, "lon": 139.7710, "tags": {"name": "Ueno Zoo Entrance", "material": "metal", "backrest": "yes", "covered": "yes"}},
    {"id": 900007, "lat": 35.7170, "lon": 139.7738, "tags": {"material": "wood", "backrest": "yes"}},
    {"id": 900008, "lat": 35.7122, "lon": 139.7758, "tags": {"name": "Ueno Station East", "material": "metal", "backrest": "yes"}},
    {"id": 900009, "lat": 35.7142, "lon": 139.7768, "tags": {"material": "wood", "covered": "no"}},
    {"id": 900010, "lat": 35.7135, "lon": 139.7695, "tags": {"name": "Tokyo National Museum Area", "material": "stone", "backrest": "no"}},
    # --- Yoyogi Park & Harajuku (渋谷区北部) ---
    {"id": 900011, "lat": 35.6722, "lon": 139.7023, "tags": {"name": "Yoyogi Park South", "backrest": "yes", "material": "wood"}},
    {"id": 900012, "lat": 35.6735, "lon": 139.6998, "tags": {"material": "wood", "backrest": "yes"}},
    {"id": 900013, "lat": 35.6710, "lon": 139.7045, "tags": {"covered": "no", "material": "stone"}},
    {"id": 900014, "lat": 35.6748, "lon": 139.6975, "tags": {"name": "Yoyogi Park Fountain Area", "material": "wood", "backrest": "yes", "seats": "4"}},
    {"id": 900015, "lat": 35.6695, "lon": 139.7010, "tags": {"material": "metal", "backrest": "yes"}},
    {"id": 900016, "lat": 35.6703, "lon": 139.7058, "tags": {"name": "NHK Hall Side", "material": "wood", "backrest": "yes", "covered": "yes"}},
    {"id": 900017, "lat": 35.6690, "lon": 139.7030, "tags": {"material": "wood"}},
    {"id": 900018, "lat": 35.6715, "lon": 139.6965, "tags": {"name": "Yoyogi Cycling Road", "material": "metal", "backrest": "no"}},
    {"id": 900019, "lat": 35.6700, "lon": 139.7025, "tags": {"material": "wood", "backrest": "yes", "seats": "2"}},
    # --- Shinjuku Gyoen & Shinjuku (新宿区) ---
    {"id": 900020, "lat": 35.6852, "lon": 139.7100, "tags": {"name": "Shinjuku Gyoen Bench", "backrest": "yes", "material": "wood", "covered": "no"}},
    {"id": 900021, "lat": 35.6840, "lon": 139.7115, "tags": {"material": "wood", "backrest": "yes", "seats": "3"}},
    {"id": 900022, "lat": 35.6865, "lon": 139.7088, "tags": {"covered": "yes", "material": "metal"}},
    {"id": 900023, "lat": 35.6830, "lon": 139.7095, "tags": {"name": "Shinjuku Gyoen Pond", "material": "wood", "backrest": "yes"}},
    {"id": 900024, "lat": 35.6858, "lon": 139.7120, "tags": {"material": "stone", "backrest": "no"}},
    {"id": 900025, "lat": 35.6938, "lon": 139.7036, "tags": {"name": "Shinjuku Central Park", "material": "wood", "backrest": "yes"}},
    {"id": 900026, "lat": 35.6945, "lon": 139.7050, "tags": {"covered": "yes", "material": "metal", "backrest": "yes"}},
    {"id": 900027, "lat": 35.6915, "lon": 139.6935, "tags": {"name": "Shinjuku West Exit", "material": "metal", "backrest": "yes", "covered": "yes"}},
    {"id": 900028, "lat": 35.6900, "lon": 139.7005, "tags": {"material": "metal", "backrest": "yes"}},
    {"id": 900029, "lat": 35.6925, "lon": 139.7020, "tags": {"name": "Shinjuku Chuo Park North", "material": "wood", "backrest": "yes"}},
    {"id": 900030, "lat": 35.6935, "lon": 139.7060, "tags": {"material": "wood", "covered": "no"}},
    {"id": 900031, "lat": 35.6892, "lon": 139.6980, "tags": {"name": "Shinjuku Nomura Bldg Area", "material": "stone"}},
    # --- Asakusa & Sumida (台東区・墨田区) ---
    {"id": 900032, "lat": 35.6996, "lon": 139.7716, "tags": {"name": "Asakusa Sumida Park", "backrest": "yes", "material": "metal", "covered": "no"}},
    {"id": 900033, "lat": 35.7002, "lon": 139.7728, "tags": {"material": "wood", "backrest": "yes"}},
    {"id": 900034, "lat": 35.7108, "lon": 139.7966, "tags": {"name": "Skytree Foot Bench", "material": "metal", "backrest": "yes", "covered": "yes"}},
    {"id": 900035, "lat": 35.7115, "lon": 139.7955, "tags": {"material": "wood", "backrest": "yes"}},
    {"id": 900036, "lat": 35.7008, "lon": 139.7740, "tags": {"name": "Sumida River Terrace", "material": "metal", "backrest": "yes"}},
    {"id": 900037, "lat": 35.7020, "lon": 139.7710, "tags": {"material": "wood"}},
    {"id": 900038, "lat": 35.6988, "lon": 139.7695, "tags": {"name": "Kaminarimon Area", "material": "stone", "backrest": "no"}},
    {"id": 900039, "lat": 35.7015, "lon": 139.7753, "tags": {"material": "wood", "backrest": "yes", "covered": "no"}},
    {"id": 900040, "lat": 35.7098, "lon": 139.7980, "tags": {"name": "Solamachi Terrace", "material": "metal", "backrest": "yes"}},
    # --- Shibuya (渋谷区) ---
    {"id": 900041, "lat": 35.6590, "lon": 139.7005, "tags": {"name": "Shibuya Station Hachiko Side", "backrest": "yes", "material": "metal"}},
    {"id": 900042, "lat": 35.6598, "lon": 139.7015, "tags": {"material": "stone", "covered": "no"}},
    {"id": 900043, "lat": 35.6580, "lon": 139.7020, "tags": {"name": "Shibuya Stream Bench", "material": "wood", "backrest": "yes"}},
    {"id": 900044, "lat": 35.6605, "lon": 139.6990, "tags": {"material": "metal", "backrest": "yes", "covered": "yes"}},
    {"id": 900045, "lat": 35.6575, "lon": 139.6975, "tags": {"name": "Shibuya Scramble Area", "material": "metal"}},
    {"id": 900046, "lat": 35.6615, "lon": 139.6970, "tags": {"material": "wood", "backrest": "yes"}},
    {"id": 900047, "lat": 35.6560, "lon": 139.6960, "tags": {"name": "Shibuya Hikarie Side", "material": "metal", "backrest": "yes"}},
    # --- Ikebukuro (豊島区) ---
    {"id": 900048, "lat": 35.7295, "lon": 139.7109, "tags": {"name": "Ikebukuro West Park", "backrest": "yes", "material": "wood"}},
    {"id": 900049, "lat": 35.7302, "lon": 139.7120, "tags": {"covered": "yes", "backrest": "yes", "material": "metal"}},
    {"id": 900050, "lat": 35.7288, "lon": 139.7095, "tags": {"material": "metal", "backrest": "yes"}},
    {"id": 900051, "lat": 35.7310, "lon": 139.7140, "tags": {"name": "Ikebukuro East Exit", "material": "stone"}},
    {"id": 900052, "lat": 35.7275, "lon": 139.7125, "tags": {"name": "Minami-Ikebukuro Park", "material": "wood", "backrest": "yes"}},
    {"id": 900053, "lat": 35.7320, "lon": 139.7100, "tags": {"material": "wood", "backrest": "yes", "covered": "no"}},
    # --- Akihabara & Kanda (千代田区東部) ---
    {"id": 900054, "lat": 35.6983, "lon": 139.7730, "tags": {"name": "Akihabara Bench", "material": "metal", "backrest": "yes"}},
    {"id": 900055, "lat": 35.6990, "lon": 139.7718, "tags": {"material": "metal"}},
    {"id": 900056, "lat": 35.6975, "lon": 139.7745, "tags": {"name": "Akihabara Park", "material": "wood", "backrest": "yes"}},
    {"id": 900057, "lat": 35.6960, "lon": 139.7710, "tags": {"material": "metal", "backrest": "yes", "covered": "yes"}},
    # --- Meiji Jingu & Omotesando ---
    {"id": 900058, "lat": 35.6764, "lon": 139.6993, "tags": {"name": "Meiji Jingu Approach", "material": "wood", "covered": "no", "backrest": "yes"}},
    {"id": 900059, "lat": 35.6770, "lon": 139.7010, "tags": {"material": "stone", "backrest": "no"}},
    {"id": 900060, "lat": 35.6685, "lon": 139.7085, "tags": {"name": "Omotesando Hills Area", "material": "metal", "backrest": "yes"}},
    {"id": 900061, "lat": 35.6675, "lon": 139.7110, "tags": {"material": "wood", "backrest": "yes"}},
    # --- Hamarikyu & Tsukiji (中央区南部) ---
    {"id": 900062, "lat": 35.6605, "lon": 139.7630, "tags": {"name": "Hamarikyu Gardens", "material": "wood", "backrest": "yes", "covered": "no"}},
    {"id": 900063, "lat": 35.6615, "lon": 139.7645, "tags": {"material": "stone", "seats": "2"}},
    {"id": 900064, "lat": 35.6595, "lon": 139.7618, "tags": {"material": "wood", "backrest": "yes"}},
    {"id": 900065, "lat": 35.6682, "lon": 139.7705, "tags": {"name": "Tsukiji Outer Market", "material": "metal", "backrest": "yes"}},
    {"id": 900066, "lat": 35.6690, "lon": 139.7720, "tags": {"material": "metal", "backrest": "yes"}},
    # --- Odaiba (港区台場) ---
    {"id": 900067, "lat": 35.6295, "lon": 139.7753, "tags": {"name": "Odaiba Beach Bench", "material": "wood", "backrest": "yes", "covered": "no"}},
    {"id": 900068, "lat": 35.6310, "lon": 139.7770, "tags": {"material": "metal", "backrest": "yes"}},
    {"id": 900069, "lat": 35.6280, "lon": 139.7780, "tags": {"name": "Odaiba Seaside Path", "material": "wood", "backrest": "yes"}},
    {"id": 900070, "lat": 35.6268, "lon": 139.7740, "tags": {"material": "metal"}},
    {"id": 900071, "lat": 35.6320, "lon": 139.7795, "tags": {"name": "DiverCity Area", "material": "metal", "backrest": "yes", "covered": "yes"}},
    # --- Ginza & Nihonbashi (中央区) ---
    {"id": 900072, "lat": 35.6760, "lon": 139.7620, "tags": {"name": "Ginza Chuo-dori", "material": "metal", "backrest": "yes", "covered": "yes"}},
    {"id": 900073, "lat": 35.6745, "lon": 139.7635, "tags": {"material": "stone", "backrest": "no"}},
    {"id": 900074, "lat": 35.6770, "lon": 139.7645, "tags": {"name": "Ginza Mitsukoshi Area", "material": "metal", "backrest": "yes"}},
    {"id": 900075, "lat": 35.6870, "lon": 139.7590, "tags": {"name": "Nihonbashi Bench", "material": "metal", "backrest": "yes"}},
    {"id": 900076, "lat": 35.6862, "lon": 139.7602, "tags": {"material": "wood", "backrest": "yes"}},
    {"id": 900077, "lat": 35.6855, "lon": 139.7578, "tags": {"name": "Nihonbashi River Terrace", "material": "wood", "backrest": "yes", "covered": "no"}},
    # --- Imperial Palace & Marunouchi (千代田区中心) ---
    {"id": 900078, "lat": 35.7058, "lon": 139.7517, "tags": {"name": "Imperial Palace East Garden", "material": "stone", "backrest": "no"}},
    {"id": 900079, "lat": 35.7065, "lon": 139.7530, "tags": {"material": "wood", "backrest": "yes", "covered": "no"}},
    {"id": 900080, "lat": 35.7042, "lon": 139.7505, "tags": {"material": "stone"}},
    {"id": 900081, "lat": 35.6810, "lon": 139.7650, "tags": {"name": "Tokyo Station Marunouchi Side", "material": "metal", "backrest": "yes", "covered": "yes"}},
    {"id": 900082, "lat": 35.6820, "lon": 139.7665, "tags": {"material": "metal", "backrest": "yes"}},
    {"id": 900083, "lat": 35.6795, "lon": 139.7680, "tags": {"name": "KITTE Garden Terrace", "material": "wood", "backrest": "yes"}},
    {"id": 900084, "lat": 35.6835, "lon": 139.7630, "tags": {"material": "stone", "backrest": "no"}},
    {"id": 900085, "lat": 35.7050, "lon": 139.7480, "tags": {"name": "Chidorigafuchi Bench", "material": "wood", "backrest": "yes", "covered": "no"}},
    {"id": 900086, "lat": 35.7035, "lon": 139.7495, "tags": {"material": "wood", "backrest": "yes"}},
    # --- Roppongi & Azabu (港区) ---
    {"id": 900087, "lat": 35.6604, "lon": 139.7292, "tags": {"name": "Roppongi Hills Bench", "material": "metal", "backrest": "yes", "covered": "yes"}},
    {"id": 900088, "lat": 35.6612, "lon": 139.7305, "tags": {"material": "wood", "backrest": "yes"}},
    {"id": 900089, "lat": 35.6620, "lon": 139.7280, "tags": {"name": "Mohri Garden", "material": "wood", "backrest": "yes"}},
    {"id": 900090, "lat": 35.6650, "lon": 139.7260, "tags": {"name": "Tokyo Midtown Park", "material": "wood", "backrest": "yes"}},
    {"id": 900091, "lat": 35.6658, "lon": 139.7275, "tags": {"material": "metal", "backrest": "yes", "covered": "no"}},
    {"id": 900092, "lat": 35.6665, "lon": 139.7250, "tags": {"name": "Hinokicho Park", "material": "wood", "backrest": "yes"}},
    # --- Akasaka & Nagatacho ---
    {"id": 900093, "lat": 35.6800, "lon": 139.7390, "tags": {"name": "Akasaka Sacas Area", "material": "wood", "backrest": "yes", "covered": "yes"}},
    {"id": 900094, "lat": 35.6785, "lon": 139.7375, "tags": {"material": "metal", "backrest": "yes"}},
    {"id": 900095, "lat": 35.6740, "lon": 139.7420, "tags": {"name": "Hie Shrine Approach", "material": "stone"}},
    # --- Yanaka & Nezu (文京区・台東区) ---
    {"id": 900096, "lat": 35.7335, "lon": 139.7460, "tags": {"name": "Yanaka Cemetery Bench", "material": "wood", "backrest": "yes", "covered": "no"}},
    {"id": 900097, "lat": 35.7342, "lon": 139.7472, "tags": {"material": "wood"}},
    {"id": 900098, "lat": 35.7325, "lon": 139.7450, "tags": {"name": "Yanaka Ginza", "material": "metal", "backrest": "yes"}},
    {"id": 900099, "lat": 35.7205, "lon": 139.7625, "tags": {"name": "Nezu Shrine Path", "material": "wood", "backrest": "yes"}},
    {"id": 900100, "lat": 35.7215, "lon": 139.7610, "tags": {"material": "stone", "backrest": "no"}},
    # --- Koishikawa & Bunkyo (文京区) ---
    {"id": 900101, "lat": 35.7195, "lon": 139.7435, "tags": {"name": "Koishikawa Korakuen", "material": "wood", "backrest": "yes", "covered": "no"}},
    {"id": 900102, "lat": 35.7188, "lon": 139.7448, "tags": {"material": "stone"}},
    {"id": 900103, "lat": 35.7010, "lon": 139.7445, "tags": {"name": "Ochanomizu Bench", "material": "stone", "backrest": "no"}},
    {"id": 900104, "lat": 35.7080, "lon": 139.7515, "tags": {"name": "Kitanomaru Park", "material": "wood", "backrest": "yes"}},
    {"id": 900105, "lat": 35.7090, "lon": 139.7525, "tags": {"material": "wood", "backrest": "yes", "covered": "no"}},
    # --- Meguro River & Nakameguro (目黒区) ---
    {"id": 900106, "lat": 35.6458, "lon": 139.7105, "tags": {"name": "Meguro River Walk", "material": "wood", "backrest": "yes"}},
    {"id": 900107, "lat": 35.6465, "lon": 139.7118, "tags": {"material": "metal", "covered": "no"}},
    {"id": 900108, "lat": 35.6558, "lon": 139.6860, "tags": {"name": "Nakameguro Station Bench", "material": "wood", "backrest": "yes"}},
    {"id": 900109, "lat": 35.6450, "lon": 139.7090, "tags": {"material": "wood", "backrest": "yes"}},
    {"id": 900110, "lat": 35.6440, "lon": 139.7080, "tags": {"name": "Meguro Fudoson Area", "material": "stone"}},
    # --- Shinagawa (品川区) ---
    {"id": 900111, "lat": 35.6280, "lon": 139.7400, "tags": {"name": "Shinagawa Seaside", "material": "metal", "backrest": "yes"}},
    {"id": 900112, "lat": 35.6290, "lon": 139.7415, "tags": {"material": "wood", "backrest": "yes"}},
    {"id": 900113, "lat": 35.6270, "lon": 139.7388, "tags": {"name": "Shinagawa Intercity Garden", "material": "metal", "backrest": "yes", "covered": "yes"}},
    {"id": 900114, "lat": 35.6240, "lon": 139.7410, "tags": {"material": "wood"}},
    # --- Shiba Park & Tokyo Tower (港区南部) ---
    {"id": 900115, "lat": 35.6544, "lon": 139.7467, "tags": {"name": "Shiba Park", "material": "wood", "backrest": "yes"}},
    {"id": 900116, "lat": 35.6552, "lon": 139.7480, "tags": {"covered": "no", "material": "stone"}},
    {"id": 900117, "lat": 35.6536, "lon": 139.7455, "tags": {"material": "metal", "backrest": "yes"}},
    {"id": 900118, "lat": 35.6586, "lon": 139.7454, "tags": {"name": "Tokyo Tower Foot Bench", "material": "metal", "backrest": "yes"}},
    {"id": 900119, "lat": 35.6560, "lon": 139.7490, "tags": {"name": "Zojoji Temple Area", "material": "stone", "backrest": "no"}},
    # --- Komazawa & Setagaya (世田谷区・目黒区) ---
    {"id": 900120, "lat": 35.6475, "lon": 139.6690, "tags": {"name": "Komazawa Olympic Park", "material": "wood", "backrest": "yes", "seats": "4"}},
    {"id": 900121, "lat": 35.6480, "lon": 139.6705, "tags": {"covered": "yes", "material": "metal", "backrest": "yes"}},
    {"id": 900122, "lat": 35.6490, "lon": 139.6680, "tags": {"material": "wood", "backrest": "yes"}},
    {"id": 900123, "lat": 35.6465, "lon": 139.6715, "tags": {"name": "Komazawa Running Course", "material": "metal"}},
    {"id": 900124, "lat": 35.6500, "lon": 139.6660, "tags": {"material": "stone", "backrest": "no"}},
    {"id": 900125, "lat": 35.6445, "lon": 139.6535, "tags": {"name": "Sangenjaya Park", "material": "wood", "backrest": "yes"}},
    {"id": 900126, "lat": 35.6460, "lon": 139.6550, "tags": {"material": "metal", "backrest": "yes"}},
    # --- Asukayama & Kita (北区) ---
    {"id": 900127, "lat": 35.7620, "lon": 139.7245, "tags": {"name": "Asukayama Park", "material": "wood", "backrest": "yes", "covered": "no"}},
    {"id": 900128, "lat": 35.7628, "lon": 139.7258, "tags": {"material": "metal", "covered": "yes"}},
    {"id": 900129, "lat": 35.7615, "lon": 139.7232, "tags": {"material": "wood", "backrest": "yes"}},
    {"id": 900130, "lat": 35.7640, "lon": 139.7265, "tags": {"name": "Oji Station Area", "material": "metal", "backrest": "yes"}},
    # --- Kinshicho & Kameido (墨田区・江東区) ---
    {"id": 900131, "lat": 35.7100, "lon": 139.8107, "tags": {"name": "Kinshi Park", "material": "wood", "backrest": "yes"}},
    {"id": 900132, "lat": 35.7092, "lon": 139.8120, "tags": {"material": "metal", "backrest": "yes"}},
    {"id": 900133, "lat": 35.6990, "lon": 139.8262, "tags": {"name": "Kameido Tenjin Area", "material": "wood", "backrest": "yes", "covered": "no"}},
    {"id": 900134, "lat": 35.6982, "lon": 139.8275, "tags": {"material": "stone"}},
    # --- Arakawa & Nippori (荒川区) ---
    {"id": 900135, "lat": 35.7385, "lon": 139.7950, "tags": {"name": "Arakawa Nature Park", "material": "wood", "backrest": "yes", "covered": "no"}},
    {"id": 900136, "lat": 35.7392, "lon": 139.7965, "tags": {"material": "metal"}},
    {"id": 900137, "lat": 35.7560, "lon": 139.7500, "tags": {"name": "Nishi-Nippori Bench", "material": "wood", "covered": "no"}},
    {"id": 900138, "lat": 35.7545, "lon": 139.7510, "tags": {"material": "wood", "backrest": "yes"}},
    # --- Zoshigaya & Toshima (豊島区南部) ---
    {"id": 900139, "lat": 35.7450, "lon": 139.7145, "tags": {"name": "Zoshigaya Park", "material": "wood", "backrest": "yes"}},
    {"id": 900140, "lat": 35.7442, "lon": 139.7158, "tags": {"material": "metal", "backrest": "yes"}},
    {"id": 900141, "lat": 35.7215, "lon": 139.6810, "tags": {"name": "Rikkyo University Area", "material": "wood", "backrest": "yes"}},
    # --- Togoshi & Ebara (品川区南部) ---
    {"id": 900142, "lat": 35.6355, "lon": 139.7155, "tags": {"name": "Togoshi Park", "material": "metal", "backrest": "yes"}},
    {"id": 900143, "lat": 35.6365, "lon": 139.7168, "tags": {"material": "wood", "backrest": "yes"}},
    {"id": 900144, "lat": 35.6345, "lon": 139.7140, "tags": {"material": "stone"}},
    # --- Toyosu & Koto (江東区南部) ---
    {"id": 900145, "lat": 35.6532, "lon": 139.7950, "tags": {"name": "Toyosu Park", "material": "wood", "backrest": "yes"}},
    {"id": 900146, "lat": 35.6540, "lon": 139.7965, "tags": {"material": "metal", "backrest": "yes", "covered": "yes"}},
    {"id": 900147, "lat": 35.6525, "lon": 139.7935, "tags": {"material": "wood"}},
    {"id": 900148, "lat": 35.6718, "lon": 139.8172, "tags": {"name": "Kiba Park", "material": "wood", "backrest": "yes"}},
    {"id": 900149, "lat": 35.6725, "lon": 139.8185, "tags": {"material": "metal", "backrest": "yes"}},
    {"id": 900150, "lat": 35.6710, "lon": 139.8160, "tags": {"material": "wood", "backrest": "yes", "seats": "3"}},
    # --- Kasai & Edogawa (江戸川区) ---
    {"id": 900151, "lat": 35.6590, "lon": 139.8610, "tags": {"name": "Kasai Rinkai Park", "material": "wood", "backrest": "yes"}},
    {"id": 900152, "lat": 35.6598, "lon": 139.8625, "tags": {"material": "metal", "backrest": "yes", "covered": "no"}},
    {"id": 900153, "lat": 35.6582, "lon": 139.8600, "tags": {"material": "wood", "seats": "4"}},
    {"id": 900154, "lat": 35.6575, "lon": 139.8640, "tags": {"name": "Kasai Seaside", "material": "wood", "backrest": "yes"}},
    {"id": 900155, "lat": 35.6915, "lon": 139.8680, "tags": {"name": "Edogawa River Path", "material": "wood", "backrest": "yes"}},
    # --- Nerima (練馬区) ---
    {"id": 900156, "lat": 35.7465, "lon": 139.6280, "tags": {"name": "Shakujii Park", "material": "wood", "backrest": "yes"}},
    {"id": 900157, "lat": 35.7475, "lon": 139.6295, "tags": {"material": "metal", "backrest": "yes"}},
    {"id": 900158, "lat": 35.7455, "lon": 139.6265, "tags": {"material": "wood"}},
    {"id": 900159, "lat": 35.7380, "lon": 139.6540, "tags": {"name": "Nerima Station Area", "material": "metal", "backrest": "yes"}},
    {"id": 900160, "lat": 35.7600, "lon": 139.6000, "tags": {"name": "Oizumi Chuo Park", "material": "wood", "backrest": "yes", "covered": "no"}},
    # --- Suginami (杉並区) ---
    {"id": 900161, "lat": 35.7060, "lon": 139.6498, "tags": {"name": "Zenpukuji Park", "material": "wood", "backrest": "yes"}},
    {"id": 900162, "lat": 35.7068, "lon": 139.6510, "tags": {"material": "stone", "backrest": "no"}},
    {"id": 900163, "lat": 35.7040, "lon": 139.6495, "tags": {"material": "wood", "backrest": "yes"}},
    {"id": 900164, "lat": 35.6985, "lon": 139.6360, "tags": {"name": "Ogikubo Station Area", "material": "metal", "backrest": "yes"}},
    # --- Nakano (中野区) ---
    {"id": 900165, "lat": 35.7075, "lon": 139.6685, "tags": {"name": "Nakano Station North", "material": "metal", "backrest": "yes"}},
    {"id": 900166, "lat": 35.7085, "lon": 139.6698, "tags": {"material": "wood", "backrest": "yes"}},
    {"id": 900167, "lat": 35.7145, "lon": 139.6590, "tags": {"name": "Arai Yakushi Park", "material": "wood", "backrest": "yes"}},
    # --- Adachi (足立区) ---
    {"id": 900168, "lat": 35.7750, "lon": 139.8045, "tags": {"name": "Toneri Park", "material": "wood", "backrest": "yes"}},
    {"id": 900169, "lat": 35.7758, "lon": 139.8060, "tags": {"material": "metal", "backrest": "yes", "covered": "yes"}},
    {"id": 900170, "lat": 35.7695, "lon": 139.7905, "tags": {"name": "Nishiarai Daishi Area", "material": "wood", "backrest": "yes"}},
    {"id": 900171, "lat": 35.7500, "lon": 139.7945, "tags": {"name": "Arakawa Riverbank Path", "material": "metal"}},
    # --- Katsushika (葛飾区) ---
    {"id": 900172, "lat": 35.7515, "lon": 139.8510, "tags": {"name": "Shibamata Taisyakuten", "material": "wood", "backrest": "yes"}},
    {"id": 900173, "lat": 35.7522, "lon": 139.8525, "tags": {"material": "stone"}},
    {"id": 900174, "lat": 35.7440, "lon": 139.8480, "tags": {"name": "Mizumoto Park", "material": "wood", "backrest": "yes", "seats": "3"}},
    {"id": 900175, "lat": 35.7448, "lon": 139.8495, "tags": {"material": "wood", "backrest": "yes"}},
    # --- Itabashi (板橋区) ---
    {"id": 900176, "lat": 35.7695, "lon": 139.6920, "tags": {"name": "Akatsuka Park", "material": "wood", "backrest": "yes"}},
    {"id": 900177, "lat": 35.7705, "lon": 139.6935, "tags": {"material": "metal", "backrest": "yes"}},
    {"id": 900178, "lat": 35.7535, "lon": 139.7090, "tags": {"name": "Itabashi Station Area", "material": "metal", "backrest": "yes"}},
    # --- Ota (大田区) ---
    {"id": 900179, "lat": 35.5685, "lon": 139.7275, "tags": {"name": "Ota Seaside Park", "material": "wood", "backrest": "yes"}},
    {"id": 900180, "lat": 35.5692, "lon": 139.7288, "tags": {"material": "metal", "covered": "yes"}},
    {"id": 900181, "lat": 35.6205, "lon": 139.7165, "tags": {"name": "Senzokuike Park", "material": "wood", "backrest": "yes"}},
    {"id": 900182, "lat": 35.6212, "lon": 139.7178, "tags": {"material": "wood", "backrest": "yes"}},
    {"id": 900183, "lat": 35.5620, "lon": 139.7160, "tags": {"name": "Heiwajima Area", "material": "metal", "backrest": "yes"}},
    # --- Additional Sumida & Taito waterfront ---
    {"id": 900184, "lat": 35.6930, "lon": 139.7800, "tags": {"name": "Ryogoku Bridge Bench", "material": "metal", "backrest": "yes"}},
    {"id": 900185, "lat": 35.6940, "lon": 139.7815, "tags": {"material": "wood", "backrest": "yes"}},
    {"id": 900186, "lat": 35.6920, "lon": 139.7790, "tags": {"name": "Sumida Hokusai Museum Area", "material": "metal", "backrest": "yes"}},
    # --- Extra parks & green spaces ---
    {"id": 900187, "lat": 35.6730, "lon": 139.7150, "tags": {"name": "Aoyama Cemetery Path", "material": "stone", "backrest": "no"}},
    {"id": 900188, "lat": 35.6740, "lon": 139.7165, "tags": {"material": "wood", "backrest": "yes"}},
    {"id": 900189, "lat": 35.6398, "lon": 139.6830, "tags": {"name": "Todoroki Valley", "material": "wood", "backrest": "yes", "covered": "no"}},
    {"id": 900190, "lat": 35.6408, "lon": 139.6845, "tags": {"material": "stone"}},
    {"id": 900191, "lat": 35.7240, "lon": 139.7180, "tags": {"name": "Edogawabashi Area", "material": "metal", "backrest": "yes"}},
    {"id": 900192, "lat": 35.7248, "lon": 139.7195, "tags": {"material": "wood", "backrest": "yes"}},
    {"id": 900193, "lat": 35.6850, "lon": 139.6830, "tags": {"name": "Yoyogi-Hachiman Area", "material": "wood", "backrest": "yes"}},
    {"id": 900194, "lat": 35.6858, "lon": 139.6845, "tags": {"material": "metal"}},
    {"id": 900195, "lat": 35.7350, "lon": 139.7850, "tags": {"name": "Minamisenju Riverside", "material": "wood", "backrest": "yes"}},
    {"id": 900196, "lat": 35.7358, "lon": 139.7865, "tags": {"material": "metal", "backrest": "yes"}},
    {"id": 900197, "lat": 35.6650, "lon": 139.7520, "tags": {"name": "Azabudai Hills Area", "material": "metal", "backrest": "yes", "covered": "yes"}},
    {"id": 900198, "lat": 35.6520, "lon": 139.7230, "tags": {"name": "Ebisu Garden Place", "material": "wood", "backrest": "yes"}},
    {"id": 900199, "lat": 35.6528, "lon": 139.7245, "tags": {"material": "metal", "backrest": "yes"}},
    {"id": 900200, "lat": 35.6380, "lon": 139.7350, "tags": {"name": "Gotanda Station Area", "material": "metal", "backrest": "yes"}},
]


def fetch_benches_from_overpass(bbox=None):
    """Fetch bench data from Overpass API. Falls back to hardcoded data on failure."""
    try:
        if bbox:
            query = f"[out:json][timeout:30];node[\"amenity\"=\"bench\"]({bbox});out body;"
        else:
            query = OVERPASS_QUERY

        resp = requests.post(OVERPASS_URL, data={"data": query}, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        benches = []
        for element in data.get("elements", []):
            benches.append({
                "id": element["id"],
                "lat": element["lat"],
                "lon": element["lon"],
                "tags": element.get("tags", {}),
            })

        if benches:
            return benches
        # Empty result — fall through to fallback
    except Exception:
        pass

    return list(FALLBACK_BENCHES)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/benches")
def api_benches():
    bbox = request.args.get("bbox")

    if bbox:
        benches = fetch_benches_from_overpass(bbox=bbox)
        user_benches = _load_user_benches()
        all_benches = benches + user_benches
        return jsonify({"benches": all_benches, "count": len(all_benches)})

    # Use cached data if available and fresh
    now = time.time()
    if _cache["data"] is not None and (now - _cache["timestamp"]) < _cache["ttl"]:
        user_benches = _load_user_benches()
        all_benches = _cache["data"] + user_benches
        return jsonify({"benches": all_benches, "count": len(all_benches)})

    # Fetch fresh data (Overpass or fallback)
    benches = fetch_benches_from_overpass()
    _cache["data"] = benches
    _cache["timestamp"] = now
    user_benches = _load_user_benches()
    all_benches = benches + user_benches
    return jsonify({"benches": all_benches, "count": len(all_benches)})


@app.route("/api/search")
def api_search():
    """Proxy to Nominatim geocoding, restricted to Tokyo 23 wards area."""
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify([])

    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": q,
                "format": "json",
                "limit": 5,
                "viewbox": "139.56,35.518,139.92,35.818",
                "bounded": 1,
            },
            headers={"User-Agent": "BenchMapTokyo/1.0"},
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json()
        return jsonify([
            {
                "name": r.get("display_name", ""),
                "lat": float(r["lat"]),
                "lon": float(r["lon"]),
            }
            for r in results
        ])
    except Exception:
        return jsonify([])


@app.route("/api/benches/submit", methods=["POST"])
def api_submit_bench():
    """Store a user-submitted bench."""
    data = request.get_json()
    if not data or "lat" not in data or "lon" not in data:
        return jsonify({"error": "lat and lon are required"}), 400

    user_benches = _load_user_benches()
    max_id = max((b["id"] for b in user_benches), default=990000)
    new_bench = {
        "id": max_id + 1,
        "lat": float(data["lat"]),
        "lon": float(data["lon"]),
        "tags": data.get("tags", {}),
        "source": "user",
        "timestamp": time.time(),
    }
    user_benches.append(new_bench)
    _save_user_benches(user_benches)
    return jsonify({"success": True, "bench": new_bench}), 201


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
