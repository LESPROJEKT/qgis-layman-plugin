# -*- coding: utf-8 -*-

import json
import os
from urllib.parse import urlparse


def _config_path(plugin_dir):
    return os.path.join(plugin_dir, "s3_server_mounts.json")


def load_s3_mount_config(plugin_dir):
    path = _config_path(plugin_dir)
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def host_from_server_url(server_url):
    if not server_url:
        return ""
    parsed = urlparse(server_url.strip())
    return (parsed.hostname or "").lower()


def resolve_server_relative_mount(config, server_url, bucket):
    if not config or not bucket:
        return None
    host = host_from_server_url(server_url)
    for entry in config.get("servers", []):
        hosts = [h.lower() for h in entry.get("match", {}).get("hosts", [])]
        if host not in hosts:
            continue
        for mount in entry.get("mounts", []):
            buckets = [b.lower() for b in mount.get("buckets", [])]
            if bucket.lower() in buckets:
                return mount.get("server_relative_mount")
    return None


def build_server_raster_path(server_relative_mount, s3_key_with_leading_slash):
    key = (s3_key_with_leading_slash or "").strip("/")
    mount = (server_relative_mount or "").strip("/")
    if not mount:
        return key
    return f"{mount}/{key}" if key else mount


def parse_vsis3_source(source):
    if not source:
        return None, None
    prefix = "/vsis3/"
    if not source.startswith(prefix):
        return None, None
    rest = source[len(prefix) :].strip("/")
    parts = rest.split("/", 1)
    if len(parts) < 2:
        return None, None
    bucket, key = parts[0], parts[1]
    return bucket, "/" + key
