#!/usr/bin/env python3

def test_extract_entities():
    """Test the enhanced entity extraction logic"""
    
    def _extract_entities(query: str):
        """Extract company names and key entities - Enhanced version"""
        companies = ['nvidia', 'openai', 'microsoft', 'google', 'apple', 'amazon', 'tesla', 'meta', 
                    'stripe', 'vercel', 'anthropic', 'aws', 'azure']
        entities = []
        
        query_lower = query.lower()
        
        # Check for known companies first
        for company in companies:
            if company in query_lower:
                entities.append(company.upper())
        
        # If no specific companies found, extract generic business entities from query context
        if not entities:
            # For business/funding/startup queries, use relevant tech companies
            if any(term in query_lower for term in ['startup', 'funding', 'venture', 'investment', 'business']):
                entities.extend(['NVIDIA', 'OPENAI', 'STRIPE'])  # Major tech/AI companies for business context
            # For product/tech queries, use major tech companies  
            elif any(term in query_lower for term in ['product', 'tech', 'software', 'development', 'api']):
                entities.extend(['GOOGLE', 'MICROSOFT', 'VERCEL'])
            # For AI/ML queries 
            elif any(term in query_lower for term in ['ai', 'artificial', 'machine learning', 'ml', 'neural']):
                entities.extend(['NVIDIA', 'OPENAI', 'MICROSOFT'])
            # Default fallback for other queries
            else:
                entities.extend(['GOOGLE', 'MICROSOFT'])  # Major companies with broad business data
        
        return entities

    # Test cases
    test_queries = [
        "startup funding trends",
        "nvidia ai strategy", 
        "latest vercel nextjs update",
        "machine learning developments",  
        "random query about weather"
    ]
    
    print('🧪 Testing Enhanced Entity Extraction')
    print('=' * 50)
    
    for query in test_queries:
        entities = _extract_entities(query)
        print(f'Query: "{query}"')
        print(f'Entities: {entities}')
        print(f'Will create BI tasks: {"✅ YES" if entities else "❌ NO"}')
        print()

if __name__ == '__main__':
    test_extract_entities()