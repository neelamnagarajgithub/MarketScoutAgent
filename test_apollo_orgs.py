#!/usr/bin/env python3
import asyncio
import httpx
import yaml

async def test_apollo_orgs():
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    apollo_key = config['keys']['apollo']
    print(f'🧪 Testing Apollo Organizations API: {apollo_key[:10]}...')
    
    async with httpx.AsyncClient(timeout=15) as client:
        # Test the organizations/search endpoint
        url = 'https://api.apollo.io/v1/organizations/search'
        headers = {'Cache-Control': 'no-cache', 'X-Api-Key': apollo_key}
        payload = {
            'organization_domain': 'nvidia.com',
            'page': 1,
            'per_page': 5
        }
        
        try:
            response = await client.post(url, headers=headers, json=payload, timeout=10)
            print(f'Status Code: {response.status_code}')
            
            if response.status_code == 200:
                data = response.json()
                print(f'Response Keys: {list(data.keys())}')
                orgs = data.get('organizations', [])
                print(f'Organizations Found: {len(orgs)}')
                if orgs:
                    first_org = orgs[0]
                    print(f'Sample Organization Keys: {list(first_org.keys())[:8]}...')
                    print(f'Sample Org: {first_org.get("name", "N/A")} - {first_org.get("industry", "N/A")}')
                    print(f'✅ Apollo Organizations API working!')
                else:
                    print('ℹ️  No organizations found (but API call succeeded)')
            elif response.status_code == 403:
                print('❌ Still 403 Forbidden - organizations/search endpoint not accessible')
                print('🔧 Available endpoints from your list:')
                print('   - api/v1/organizations/show')
                print('   - api/v1/organizations/enrich') 
                print('   - api/v1/people/match')
            else:
                print(f'⚠️  Status {response.status_code}: {response.text[:300]}')
                
        except Exception as e:
            print(f'💥 Exception: {e}')

if __name__ == '__main__':
    asyncio.run(test_apollo_orgs())