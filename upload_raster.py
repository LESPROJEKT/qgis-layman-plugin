#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import requests


RASTER_PATH = "/cesta/k/rastru.tif"
USERNAME = "public"
LAYMAN_URL = "https://layman.example.com"
CRS = "EPSG:4326"


def remove_unacceptable_chars(name):
    name = re.sub(r"[^a-zA-Z0-9_-]", "_", name)
    return name.lower()


def build_layers_url(base_url, workspace, api_prefix="rest"):
    base_url = base_url.rstrip("/")
    api_prefix = api_prefix.strip("/")
    return f"{base_url}/{api_prefix}/workspaces/{workspace}/layers"


def get_crs_from_raster(raster_path):
    try:
        from osgeo import gdal

        dataset = gdal.Open(raster_path)
        if dataset:
            srs = dataset.GetSpatialRef()
            if srs:
                crs_code = srs.GetAuthorityCode(None)
                if crs_code:
                    return f"EPSG:{crs_code}"
                else:
                    return srs.ExportToWkt()
            dataset = None
    except ImportError:
        print("Varování: GDAL není dostupný")
    except Exception as e:
        print(f"Varování: Nepodařilo se získat CRS z rastru: {e}")
    return None


def upload_raster(raster_path, username, layman_url, crs=None):
    if not os.path.exists(raster_path):
        print(f"Chyba: Soubor neexistuje: {raster_path}")
        return False

    base_name = os.path.splitext(os.path.basename(raster_path))[0]
    layer_name = remove_unacceptable_chars(base_name)

    if not crs:
        crs = get_crs_from_raster(raster_path)
        if not crs:
            print("Chyba: CRS není zadán a nelze ho získat z rastru")
            return False

    data = {
        "name": layer_name,
        "title": base_name,
        "crs": str(crs),
    }

    files = {
        "file": (
            os.path.basename(raster_path),
            open(raster_path, "rb"),
            "application/octet-stream",
        )
    }

    url = build_layers_url(layman_url, username)

    print(f"Odesílám rastr: {raster_path}")
    print(f"Název vrstvy: {layer_name}")
    print(f"CRS: {crs}")
    print(f"URL: {url}")

    # headers = {"Authorization": "Bearer YOUR_TOKEN", "X-Client": "LAYMAN"}
    headers = {"X-Client": "LAYMAN"}

    try:
        response = requests.post(
            url,
            data=data,
            files=files,
            headers=headers,
            timeout=(30, 300),
        )

        print(f"\nStatus code: {response.status_code}")
        print(f"Response: {response.text}")

        if response.status_code in (200, 201):
            print("✓ Rastr úspěšně nahrán!")
            return True
        else:
            print(f"✗ Chyba při nahrávání: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Chyba při odesílání: {e}")
        return False
    finally:
        files["file"][1].close()


if __name__ == "__main__":
    upload_raster(RASTER_PATH, USERNAME, LAYMAN_URL, CRS)
