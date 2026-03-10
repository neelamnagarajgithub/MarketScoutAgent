# app/fetchers/shodan.py
import httpx
from typing import List, Dict, Optional
import asyncio
from datetime import datetime

async def search_shodan(client: httpx.AsyncClient, api_key: str, query: str, limit: int = 20) -> List[dict]:
    """Search Shodan for internet-connected devices and services"""
    url = "https://api.shodan.io/shodan/host/search"
    params = {
        "key": api_key,
        "query": query,
        "limit": limit
    }
    
    try:
        r = await client.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        
        results = []
        for match in data.get("matches", []):
            results.append({
                "title": f"Shodan Result: {match.get('ip_str', 'Unknown IP')}:{match.get('port', 'N/A')}",
                "url": f"https://www.shodan.io/host/{match.get('ip_str', '')}",
                "content": f"Service: {match.get('product', 'Unknown')} - {match.get('data', '')[:200]}...",
                "publishedAt": match.get("timestamp"),
                "metadata": {
                    "provider": "shodan",
                    "ip": match.get("ip_str"),
                    "port": match.get("port"),
                    "protocol": match.get("transport"),
                    "product": match.get("product"),
                    "version": match.get("version"),
                    "organization": match.get("org"),
                    "location": {
                        "country": match.get("location", {}).get("country_name"),
                        "city": match.get("location", {}).get("city"),
                        "latitude": match.get("location", {}).get("latitude"),
                        "longitude": match.get("location", {}).get("longitude")
                    },
                    "vulnerabilities": match.get("vulns", []),
                    "tags": match.get("tags", [])
                }
            })
        return results
    except Exception as e:
        print(f"Shodan API error: {e}")
        return []

async def get_shodan_host_info(client: httpx.AsyncClient, api_key: str, ip: str) -> Dict:
    """Get detailed information about a specific IP address"""
    url = f"https://api.shodan.io/shodan/host/{ip}"
    params = {"key": api_key}
    
    try:
        r = await client.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        
        return {
            "title": f"Host Information: {ip}",
            "url": f"https://www.shodan.io/host/{ip}",
            "content": f"Organization: {data.get('org', 'Unknown')} - Ports: {', '.join(map(str, data.get('ports', [])))}",
            "publishedAt": None,
            "metadata": {
                "provider": "shodan_host",
                "ip": ip,
                "hostnames": data.get("hostnames", []),
                "organization": data.get("org"),
                "isp": data.get("isp"),
                "asn": data.get("asn"),
                "ports": data.get("ports", []),
                "vulnerabilities": data.get("vulns", []),
                "location": data.get("country_name"),
                "city": data.get("city"),
                "last_update": data.get("last_update")
            }
        }
    except Exception as e:
        print(f"Shodan host lookup error: {e}")
        return {}

async def get_shodan_services(client: httpx.AsyncClient, api_key: str) -> List[dict]:
    """Get list of services that Shodan crawls"""
    url = "https://api.shodan.io/shodan/services"
    params = {"key": api_key}
    
    try:
        r = await client.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        
        results = []
        for service, description in data.items():
            results.append({
                "title": f"Shodan Service: {service}",
                "url": "https://www.shodan.io/explore",
                "content": description,
                "publishedAt": None,
                "metadata": {
                    "provider": "shodan_services",
                    "service": service,
                    "description": description
                }
            })
        return results
    except Exception as e:
        print(f"Shodan services error: {e}")
        return []

async def search_shodan_exploits(client: httpx.AsyncClient, api_key: str, query: str, limit: int = 10) -> List[dict]:
    """Search Shodan's exploit database"""
    url = "https://exploits.shodan.io/api/search"
    params = {
        "query": query,
        "key": api_key
    }
    
    try:
        r = await client.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        
        results = []
        for exploit in data.get("matches", [])[:limit]:
            results.append({
                "title": f"Exploit: {exploit.get('description', 'Unknown')}",
                "url": f"https://exploits.shodan.io/exploit/{exploit.get('_id', '')}",
                "content": exploit.get("code", "")[:300] + "..." if exploit.get("code") else exploit.get("description", ""),
                "publishedAt": exploit.get("date"),
                "metadata": {
                    "provider": "shodan_exploits",
                    "exploit_id": exploit.get("_id"),
                    "author": exploit.get("author"),
                    "platform": exploit.get("platform"),
                    "type": exploit.get("type"),
                    "port": exploit.get("port"),
                    "source": exploit.get("source")
                }
            })
        return results
    except Exception as e:
        print(f"Shodan exploits search error: {e}")
        return []