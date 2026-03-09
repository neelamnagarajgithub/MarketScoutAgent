# app/fetchers/npm_pypi.py
import httpx
from typing import List

async def fetch_npm_package(client: httpx.AsyncClient, name: str) -> dict:
    url = f"https://registry.npmjs.org/{name}"
    r = await client.get(url, timeout=10)
    r.raise_for_status()
    return r.json()

async def fetch_pypi_package(client: httpx.AsyncClient, name: str) -> dict:
    url = f"https://pypi.org/pypi/{name}/json"
    r = await client.get(url, timeout=10)
    r.raise_for_status()
    return r.json()