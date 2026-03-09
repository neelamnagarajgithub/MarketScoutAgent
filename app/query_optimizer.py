#!/usr/bin/env python3
"""
Enhanced Query Optimization and Result Filtering
Fixed interface to match semantic search requirements
"""

import re
from typing import List, Dict, Any

class QueryOptimizer:
    """Optimize search queries and filter results for better relevance"""
    
    def __init__(self):
        # Define AI/startup-related keywords for relevance filtering
        self.relevant_keywords = [
            'funding', 'investment', 'startup', 'venture', 'capital', 
            'ai', 'artificial intelligence', 'generative', 'openai', 
            'anthropic', 'series a', 'series b', 'round', 'valuation',
            'vc', 'investor', 'tech', 'nvidia', 'microsoft', 'google',
            'product', 'launch', 'announcement', 'market', 'analysis'
        ]
        
        # Define irrelevant patterns to filter out
        self.noise_patterns = [
            r'definition.*dictionary',
            r'meaning.*word',
            r'pronunciation',
            r'grammar.*english',
            r'sports?.*news',
            r'football|basketball|soccer',
            r'crime.*killer.*murder',
            r'weather.*forecast',
            r'cooking.*recipe',
            r'celebrity.*gossip'
        ]

    def optimize_query(self, query: str) -> Dict[str, Any]:
        """Main optimization method - returns dict with keywords and search terms"""
        
        # Extract keywords
        keywords = self._extract_keywords(query)
        
        # Generate optimized search terms
        search_terms = self.optimize_search_terms(query)
        
        # Extract financial symbols
        financial_symbols = self.enhance_financial_symbols(query)
        
        return {
            'keywords': keywords,
            'search_terms': search_terms,
            'financial_symbols': financial_symbols,
            'original_query': query
        }
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract relevant keywords from query"""
        words = query.lower().split()
        keywords = []
        
        for word in words:
            # Skip short words and common stopwords
            if len(word) > 2 and word not in ['the', 'and', 'for', 'with', 'from', 'into']:
                keywords.append(word)
        
        # Add compound terms
        if 'ai' in words or 'artificial' in query.lower():
            keywords.append('artificial intelligence')
        
        if 'startup' in words:
            keywords.append('startup funding')
        
        return keywords[:8]  # Limit keywords
    
    def optimize_search_terms(self, query: str) -> List[str]:
        """Generate optimized search terms from query"""
        
        # Keep the full query as primary search term
        terms = [query]
        
        # Extract key phrases (2-3 words) rather than individual words
        words = query.lower().split()
        
        # Generate meaningful phrases based on context
        if 'ai' in words or 'artificial intelligence' in query.lower():
            terms.extend([
                "AI startup funding 2024",
                "generative AI investment rounds",
                "artificial intelligence venture capital"
            ])
        
        if 'nvidia' in words:
            terms.extend([
                "NVIDIA AI business strategy",
                "NVIDIA product announcements"
            ])
        
        if 'funding' in words:
            terms.extend([
                "venture capital funding rounds",
                "startup investment news 2024"
            ])
        
        if 'market' in words or 'analysis' in words:
            terms.extend([
                "market analysis report",
                "competitive landscape analysis"
            ])
            
        # Remove duplicate/similar terms
        unique_terms = []
        for term in terms:
            if not any(self._are_similar(term, existing) for existing in unique_terms):
                unique_terms.append(term)
        
        return unique_terms[:5]  # Limit to prevent API overload
    
    def _are_similar(self, term1: str, term2: str) -> bool:
        """Check if two terms are too similar"""
        words1 = set(term1.lower().split())
        words2 = set(term2.lower().split())
        overlap = len(words1.intersection(words2))
        min_length = min(len(words1), len(words2))
        return overlap / min_length > 0.7 if min_length > 0 else False
    
    def filter_search_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter search results for relevance"""
        filtered = []
        
        for result in results:
            if self._is_relevant_result(result):
                filtered.append(result)
        
        return filtered[:12]  # Return top 12 most relevant
    
    def _is_relevant_result(self, result: Dict[str, Any]) -> bool:
        """Check if a search result is relevant to AI/startup funding"""
        
        title = result.get('title', '').lower()
        content = result.get('content', '').lower()
        text = f"{title} {content}"
        
        # Filter out clearly irrelevant content
        for pattern in self.noise_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return False
        
        # Check for relevant keywords
        relevant_score = 0
        for keyword in self.relevant_keywords:
            if keyword in text:
                relevant_score += 1
        
        # Must have at least 2 relevant keywords
        return relevant_score >= 2
    
    def enhance_financial_symbols(self, query: str) -> List[str]:
        """Generate better financial symbols based on query context"""
        
        symbols = []
        query_lower = query.lower()
        
        # Company-specific mappings
        company_symbols = {
            'nvidia': 'NVDA',
            'microsoft': 'MSFT',
            'google': 'GOOGL', 
            'alphabet': 'GOOGL',
            'apple': 'AAPL',
            'amazon': 'AMZN',
            'tesla': 'TSLA',
            'meta': 'META',
            'openai': 'MSFT',  # OpenAI partnership
            'anthropic': 'GOOGL'  # Anthropic investment
        }
        
        # Check for specific companies
        for company, symbol in company_symbols.items():
            if company in query_lower:
                symbols.append(symbol)
        
        # AI-focused companies if AI mentioned
        if any(term in query_lower for term in ['ai', 'artificial intelligence', 'generative']):
            ai_symbols = ['NVDA', 'GOOGL', 'MSFT', 'AMD', 'CRM']
            symbols.extend([s for s in ai_symbols if s not in symbols])
        
        # Startup/VC focused  
        elif any(term in query_lower for term in ['startup', 'venture', 'funding']):
            vc_symbols = ['NVDA', 'MSFT', 'GOOGL', 'META', 'AMZN']
            symbols.extend([s for s in vc_symbols if s not in symbols])
        
        # Default tech leaders if nothing specific
        if not symbols:
            symbols = ['AAPL', 'MSFT', 'GOOGL', 'NVDA']
            
        return symbols[:6]  # Limit to prevent API overload

# For backward compatibility
def optimize_query(query: str) -> Dict[str, Any]:
    """Standalone function for query optimization"""
    optimizer = QueryOptimizer()
    return optimizer.optimize_query(query)