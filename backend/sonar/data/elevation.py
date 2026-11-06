"""AWS Terrarium Digital Elevation Model (DEM) tile fetcher, decoder, and local cache.

Terrarium tiles encode elevation in meters via:
  elevation_m = (R * 256.0 + G + B / 256.0) - 32768.0
Cached in ~/.cache/sonar/dem/
"""

from __future__ import annotations

import io
import math
import os
from pathlib import Path
from typing import Tuple, Optional
import numpy as np
from PIL import Image
import httpx

TERRARIUM_URL_TEMPLATE: str = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
DEFAULT_CACHE_DIR: Path = Path.home() / ".cache" / "sonar" / "dem"
DEFAULT_ZOOM: int = 12


def deg_to_tile(lat_deg: float, lon_deg: float, zoom: int) -> Tuple[int, int, float, float]:
    """Convert geodetic coordinates to slippy tile coordinates and pixel sub-offsets (0..255)."""
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    
    x_tile_float = (lon_deg + 180.0) / 360.0 * n
    y_tile_float = (1.0 - math.log(math.tan(lat_rad) + (1.0 / math.cos(lat_rad))) / math.pi) / 2.0 * n
    
    x_tile = int(math.floor(x_tile_float))
    y_tile = int(math.floor(y_tile_float))
    
    # 256x256 pixel coordinates inside the tile
    px = (x_tile_float - x_tile) * 256.0
    py = (y_tile_float - y_tile) * 256.0
    
    return x_tile, y_tile, px, py


def decode_terrarium_pixel(r: float, g: float, b: float) -> float:
    """Decode Terrarium RGB byte values to elevation in meters above sea level."""
    return (r * 256.0 + g + (b / 256.0)) - 32768.0


class ElevationProvider:
    """Manages downloading, local disk caching, and bilinear interpolation of DEM tiles."""
    def __init__(self, cache_dir: Optional[Path] = None, timeout_s: float = 8.0):
        self.cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout_s = timeout_s
        self._tile_cache: dict[str, np.ndarray] = {}
        
    def _get_tile_path(self, z: int, x: int, y: int) -> Path:
        return self.cache_dir / f"{z}_{x}_{y}.png"
        
    def fetch_tile(self, z: int, x: int, y: int) -> Optional[np.ndarray]:
        """Fetch a single Terrarium PNG tile, checking memory, local disk, and remote S3."""
        tile_key = f"{z}_{x}_{y}"
        if tile_key in self._tile_cache:
            return self._tile_cache[tile_key]
            
        file_path = self._get_tile_path(z, x, y)
        if file_path.is_file():
            try:
                img = Image.open(file_path).convert("RGB")
                arr = np.asarray(img, dtype=np.float32)
                self._tile_cache[tile_key] = arr
                return arr
            except Exception:
                pass
                
        # Fetch from AWS Terrarium
        url = TERRARIUM_URL_TEMPLATE.format(z=z, x=x, y=y)
        try:
            with httpx.Client(timeout=self.timeout_s, follow_redirects=True) as client:
                resp = client.get(url)
                if resp.status_code == 200:
                    with open(file_path, "wb") as f:
                        f.write(resp.content)
                    img = Image.open(io.BytesIO(resp.content)).convert("RGB")
                    arr = np.asarray(img, dtype=np.float32)
                    self._tile_cache[tile_key] = arr
                    return arr
        except Exception:
            pass
            
        return None
        
    def get_elevation_m(self, lat: float, lon: float, zoom: int = DEFAULT_ZOOM) -> float:
        """Query ground elevation in meters at coordinate (lat, lon)."""
        x_tile, y_tile, px, py = deg_to_tile(lat, lon, zoom)
        tile = self.fetch_tile(zoom, x_tile, y_tile)
        if tile is None:
            # Fallback to sea level if offline or tile unavailable
            return 0.0
            
        # Bilinear interpolation of RGB channels
        x0 = int(math.floor(px))
        y0 = int(math.floor(py))
        x1 = min(255, x0 + 1)
        y1 = min(255, y0 + 1)
        
        dx = px - x0
        dy = py - y0
        
        # Tile shape: (256, 256, 3)
        c00 = tile[y0, x0]
        c10 = tile[y0, x1]
        c01 = tile[y1, x0]
        c11 = tile[y1, x1]
        
        interp_rgb = (
            (1.0 - dx) * (1.0 - dy) * c00 +
            dx * (1.0 - dy) * c10 +
            (1.0 - dx) * dy * c01 +
            dx * dy * c11
        )
        
        elevation = decode_terrarium_pixel(interp_rgb[0], interp_rgb[1], interp_rgb[2])
        return float(elevation)


# Global default instance
_default_provider = ElevationProvider()


def get_elevation(lat: float, lon: float) -> float:
    """Convenience helper to get ground elevation in meters."""
    return _default_provider.get_elevation_m(lat, lon)
