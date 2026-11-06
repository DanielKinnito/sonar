"""Historical ADS-B flight trajectory ingestion, parsing, and ICAO propulsion filtering.

Queries open historical ADS-B APIs (adsb.lol / OpenSky) and parses offline GeoJSON/CSV traces.
Filters out turbofan jets to focus exclusively on propeller/turboprop/rotorcraft.
"""

from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import httpx

ICAO_LOOKUP_FILE: Path = Path(__file__).parent / "icao_types.json"


def load_icao_lookup() -> Tuple[set[str], set[str]]:
    """Load categorized ICAO aircraft type designators."""
    if not ICAO_LOOKUP_FILE.is_file():
        return set(), set()
        
    try:
        with open(ICAO_LOOKUP_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            props = set(data.get("propeller_turboprop_rotor", []))
            jets = set(data.get("turbofan_jet", []))
            return props, jets
    except Exception:
        return set(), set()


PROPELLER_ROTOR_TYPES, TURBOFAN_JET_TYPES = load_icao_lookup()


def is_candidate_prop_or_rotor(icao_type: Optional[str]) -> bool:
    """Determine whether an aircraft is a piston/turboprop/rotorcraft candidate.
    
    If type code is unknown/unlisted, returns True to ensure general aviation traffic
    is never prematurely discarded.
    """
    if not icao_type:
        return True
        
    code = icao_type.strip().upper()
    if code in TURBOFAN_JET_TYPES:
        return False
        
    if code in PROPELLER_ROTOR_TYPES:
        return True
        
    # Heuristics for GA prefixes: C (Cessna), PA (Piper), BE (Beechcraft), R (Robinson)
    for prefix in ["C1", "C2", "PA", "BE", "DA", "PC", "SR", "R2", "R4", "R6", "AT"]:
        if code.startswith(prefix):
            return True
            
    # Default to True for unknown general aviation hex codes
    return True


def bounding_box_for_point(lat: float, lon: float, radius_km: float = 15.0) -> Tuple[float, float, float, float]:
    """Calculate (lat_min, lat_max, lon_min, lon_max) bounding box around a center coordinate."""
    # 1 deg lat ~ 111.0 km
    d_lat = radius_km / 111.0
    # 1 deg lon ~ 111.0 * cos(lat) km
    lat_rad = math.radians(lat)
    cos_lat = max(abs(math.cos(lat_rad)), 0.01)
    d_lon = radius_km / (111.0 * cos_lat)
    
    return (lat - d_lat, lat + d_lat, lon - d_lon, lon + d_lon)


class ADSBProvider:
    """Fetches and parses historical ADS-B trajectories."""
    def __init__(self, timeout_s: float = 10.0):
        self.timeout_s = timeout_s
        
    def query_adsb_lol(
        self,
        lat: float,
        lon: float,
        radius_km: float = 15.0,
        utc_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Query adsb.lol / api.adsb.lol point / radius endpoint.
        
        Falls back cleanly to mock/empty list if endpoint is unavailable.
        """
        lat_min, lat_max, lon_min, lon_max = bounding_box_for_point(lat, lon, radius_km)
        url = f"https://api.adsb.lol/v2/point/{lat:.4f}/{lon:.4f}/{int(radius_km * 0.539957)}"  # radius in nautical miles
        
        try:
            with httpx.Client(timeout=self.timeout_s) as client:
                resp = client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    aircraft_list = data.get("ac", [])
                    return self._parse_adsb_lol_aircraft(aircraft_list)
        except Exception:
            pass
            
        return []
        
    def _parse_adsb_lol_aircraft(self, ac_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        flights: List[Dict[str, Any]] = []
        for ac in ac_list:
            icao_type = ac.get("t")
            if not is_candidate_prop_or_rotor(icao_type):
                continue
                
            flight_id = ac.get("flight", ac.get("hex", "UNKNOWN")).strip()
            hex_code = ac.get("hex", "unknown")
            alt_ft = ac.get("alt_geom", ac.get("alt_baro", 0.0))
            alt_m = float(alt_ft) * 0.3048 if alt_ft else 500.0
            
            flight_entry = {
                "flight_id": flight_id,
                "hex": hex_code,
                "icao_type": icao_type or "UNKN",
                "is_prop_or_rotor": True,
                "points": [
                    {
                        "time_utc": datetime.now(timezone.utc).isoformat(),
                        "t_epoch_s": datetime.now(timezone.utc).timestamp(),
                        "lat": float(ac.get("lat", 0.0)),
                        "lon": float(ac.get("lon", 0.0)),
                        "alt_m": alt_m,
                        "speed_ms": float(ac.get("gs", 60.0)) * 0.514444,  # knots to m/s
                    }
                ]
            }
            flights.append(flight_entry)
            
        return flights
        
    def parse_geojson(self, file_path: str) -> List[Dict[str, Any]]:
        """Parse local GeoJSON flight tracks containing LineString or MultiPoint geometries."""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        flights: List[Dict[str, Any]] = []
        features = data.get("features", [])
        for feat in features:
            props = feat.get("properties", {})
            geom = feat.get("geometry", {})
            icao_type = props.get("type", props.get("icao_type"))
            
            if not is_candidate_prop_or_rotor(icao_type):
                continue
                
            flight_id = props.get("callsign", props.get("flight", props.get("icao24", "FLIGHT-01")))
            coords = geom.get("coordinates", [])
            timestamps = props.get("timestamps", [])
            
            points = []
            for idx, c in enumerate(coords):
                # GeoJSON coordinates are [lon, lat, alt]
                lon = float(c[0])
                lat = float(c[1])
                alt = float(c[2]) if len(c) > 2 else float(props.get("alt_m", 500.0))
                
                t_epoch = float(timestamps[idx]) if idx < len(timestamps) else float(idx * 2.0)
                points.append({
                    "time_utc": datetime.fromtimestamp(t_epoch, tz=timezone.utc).isoformat(),
                    "t_epoch_s": t_epoch,
                    "lat": lat,
                    "lon": lon,
                    "alt_m": alt,
                    "speed_ms": float(props.get("speed_ms", 65.0)),
                })
                
            if len(points) >= 2:
                flights.append({
                    "flight_id": flight_id,
                    "hex": props.get("hex", props.get("icao24", "UNKNOWN")),
                    "icao_type": icao_type or "PROP",
                    "is_prop_or_rotor": True,
                    "points": points,
                })
                
        return flights
        
    def parse_csv(self, file_path: str) -> List[Dict[str, Any]]:
        """Parse local CSV flight traces (columns: timestamp, lat, lon, altitude_m, callsign, icao_type)."""
        flights_map: Dict[str, Dict[str, Any]] = {}
        
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                callsign = row.get("callsign", row.get("flight", "FLIGHT-01")).strip()
                icao_type = row.get("icao_type", row.get("type", "C172")).strip()
                
                if not is_candidate_prop_or_rotor(icao_type):
                    continue
                    
                if callsign not in flights_map:
                    flights_map[callsign] = {
                        "flight_id": callsign,
                        "hex": row.get("icao24", row.get("hex", "UNKNOWN")),
                        "icao_type": icao_type,
                        "is_prop_or_rotor": True,
                        "points": [],
                    }
                    
                try:
                    t_val = row.get("timestamp", row.get("time", "0"))
                    try:
                        t_epoch = float(t_val)
                    except ValueError:
                        t_epoch = datetime.fromisoformat(t_val.replace("Z", "+00:00")).timestamp()
                        
                    lat = float(row.get("lat", row.get("latitude", 0.0)))
                    lon = float(row.get("lon", row.get("longitude", 0.0)))
                    alt = float(row.get("altitude_m", row.get("alt", 500.0)))
                    spd = float(row.get("speed_ms", 65.0))
                    
                    flights_map[callsign]["points"].append({
                        "time_utc": datetime.fromtimestamp(t_epoch, tz=timezone.utc).isoformat(),
                        "t_epoch_s": t_epoch,
                        "lat": lat,
                        "lon": lon,
                        "alt_m": alt,
                        "speed_ms": spd,
                    })
                except Exception:
                    continue
                    
        return list(flights_map.values())

    def parse_adsblol_trace_json(self, file_path: str) -> List[Dict[str, Any]]:
        """Parse native adsb.lol / readsb globe_history aircraft trace JSON (trace_full_*.json)."""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        icao_type = data.get("type", data.get("desc"))
        if not is_candidate_prop_or_rotor(icao_type):
            return []

        base_time = float(data.get("timestamp", 0.0))
        hex_code = data.get("icao", data.get("hex", "UNKNOWN")).upper()
        callsign = data.get("flight", hex_code).strip()
        trace_points = data.get("trace", [])

        points = []
        for pt in trace_points:
            if not isinstance(pt, (list, tuple)) or len(pt) < 3:
                continue
            # adsb.lol format: [time_offset_s, lat, lon, alt_feet, speed_knots, ...]
            t_offset = float(pt[0])
            lat = float(pt[1])
            lon = float(pt[2])
            alt_ft = float(pt[3]) if len(pt) > 3 and pt[3] is not None else 1500.0
            alt_m = alt_ft * 0.3048  # feet to meters
            speed_kts = float(pt[4]) if len(pt) > 4 and pt[4] is not None else 65.0
            speed_ms = speed_kts * 0.514444  # knots to m/s

            t_epoch = base_time + t_offset
            points.append({
                "time_utc": datetime.fromtimestamp(t_epoch, tz=timezone.utc).isoformat(),
                "t_epoch_s": t_epoch,
                "lat": lat,
                "lon": lon,
                "alt_m": alt_m,
                "speed_ms": speed_ms,
            })

        if len(points) < 2:
            return []

        return [{
            "flight_id": callsign,
            "hex": hex_code,
            "icao_type": icao_type or "PROP",
            "is_prop_or_rotor": True,
            "points": points,
        }]
