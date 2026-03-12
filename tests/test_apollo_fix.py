#!/usr/bin/env python3
import asyncio
import httpx
import yaml

async def test_apollo_fixed():
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    apollo_key = config['keys']['apollo']
    print(f'🧪 Testing Fixed Apollo API: {apollo_key[:10]}...')
    
    async with httpx.AsyncClient(timeout=15) as client:
        # Test the new contacts/search endpoint
        url = 'https://api.apollo.io/v1/contacts/search'
        headers = {'Cache-Control': 'no-cache', 'X-Api-Key': apollo_key}
        payload = {
            'organization_domain_name': 'nvidia.com',
            'page': 1,
            'per_page': 5
        }
        
        try:
            response = await client.post(url, headers=headers, json=payload, timeout=10)
            print(f'Status Code: {response.status_code}')
            
            if response.status_code == 200:
                data = response.json()
                print(f'Response Keys: {list(data.keys())}')
                contacts = data.get('contacts', [])
                print(f'Contacts Found: {len(contacts)}')
                if contacts:
                    first_contact = contacts[0]
                    print(f'Sample Contact Keys: {list(first_contact.keys())[:5]}...')
                    print(f'✅ Apollo API now working correctly!')
                else:
                    print('ℹ️  No contacts found (but API call succeeded)')
            elif response.status_code == 403:
                print('❌ Still 403 Forbidden - endpoint may not be available')
            else:
                print(f'⚠️  Status {response.status_code}: {response.text[:200]}')
                
        except Exception as e:
            print(f'💥 Exception: {e}')

if __name__ == '__main__':
    asyncio.run(test_apollo_fixed())