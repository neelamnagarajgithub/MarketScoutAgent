#!/usr/bin/env python3
import asyncio
import httpx
import yaml

async def test_business_intelligence_debug():
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    print('🔧 Debugging Business Intelligence Task Creation')
    print('=' * 50)
    
    # Simulate entity extraction for "startup funding trends"
    entities = ["startup", "funding", "trends"]  # These would be extracted entities
    
    print(f'📋 Extracted Entities: {entities}')
    print(f'🔍 Checking Available Business Intelligence APIs:')
    
    # Check what business intelligence APIs are available
    crunchbase_key = config.get('keys', {}).get('crunchbase')
    clearbit_key = config.get('keys', {}).get('clearbit')
    apollo_key = config.get('keys', {}).get('apollo')
    builtwith_key = config.get('keys', {}).get('builtwith')
    
    print(f'   - Crunchbase: {"✅ Available" if crunchbase_key else "❌ No Key"}')
    print(f'   - Clearbit: {"✅ Available" if clearbit_key else "❌ No Key"}')  
    print(f'   - Apollo: {"✅ Available" if apollo_key else "❌ No Key"}')
    print(f'   - BuiltWith: {"✅ Available" if builtwith_key else "❌ No Key"}')
    
    if not apollo_key:
        print('❌ No Apollo key found!')
        return
        
    print(f'\n🧪 Testing Apollo with Entity-Based Domains:')
    
    async with httpx.AsyncClient(timeout=15) as client:
        for entity in entities[:1]:  # Test first entity only
            # This mimics how the code creates domains from entities
            domain = f"{entity.lower()}.com" if '.' not in entity else entity
            print(f'\n📡 Testing Apollo for entity "{entity}" → domain "{domain}"')
            
            url = 'https://api.apollo.io/v1/organizations/search'
            headers = {'Cache-Control': 'no-cache', 'X-Api-Key': apollo_key}
            payload = {
                'organization_domain': domain,
                'page': 1,
                'per_page': 5
            }
            
            try:
                response = await client.post(url, headers=headers, json=payload, timeout=10)
                print(f'   Status Code: {response.status_code}')
                
                if response.status_code == 200:
                    data = response.json()
                    orgs = data.get('organizations', [])
                    print(f'   Organizations Found: {len(orgs)}')
                    if orgs:
                        print(f'   ✅ Apollo call successful for {domain}')
                        sample = orgs[0]
                        print(f'   Sample: {sample.get("name", "N/A")}')
                    else:
                        print(f'   ℹ️  No organizations found for {domain} (but API worked)')
                elif response.status_code == 403:
                    print(f'   ❌ 403 Forbidden for {domain}')
                else:
                    print(f'   ⚠️  Status {response.status_code}: {response.text[:100]}')
                    
            except Exception as e:
                print(f'   💥 Exception for {domain}: {e}')
        
        print(f'\n🎯 Testing with Real Company Domain (nvidia.com):')
        payload['organization_domain'] = 'nvidia.com'
        try:
            response = await client.post(url, headers=headers, json=payload, timeout=10)
            print(f'   Status Code: {response.status_code}')
            if response.status_code == 200:
                data = response.json()
                orgs = data.get('organizations', [])
                print(f'   Organizations Found: {len(orgs)}')
                print(f'   ✅ Real domain test: {"PASSED" if orgs else "NO RESULTS"}')
            else:
                print(f'   ❌ Real domain test failed: {response.status_code}')
        except Exception as e:
            print(f'   💥 Real domain test exception: {e}')

if __name__ == '__main__':
    asyncio.run(test_business_intelligence_debug())