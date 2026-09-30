#!/usr/bin/env python3
"""Register or update this repository on Packagist after pushing a release tag."""

import json
import os
import urllib.error
import urllib.request


username = os.environ["PACKAGIST_USERNAME"]
token = os.environ["PACKAGIST_API_TOKEN"]
repo = "https://github.com/helsingborg-stad/material-design-icons-json-svg-font"
package_url = "https://packagist.org/packages/helsingborg-stad/material-design-icons-json-svg-font.json"

try:
    with urllib.request.urlopen(package_url, timeout=30):
        exists = True
except urllib.error.HTTPError as error:
    if error.code != 404:
        raise
    exists = False

endpoint = "https://packagist.org/api/update-package" if exists else "https://packagist.org/api/create-package"
body = {"repository": repo}
request = urllib.request.Request(
    endpoint,
    data=json.dumps(body).encode(),
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {username}:{token}",
    },
    method="POST",
)
with urllib.request.urlopen(request, timeout=60) as response:
    print(response.read().decode())
