#!/usr/bin/env python3
"""
Enhanced Query Optimization and Result Filtering
Improved version to reduce noise and improve relevance
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
            'vc', 'investor', 'tech', 'nvidia', 'microsoft', 'google'
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
            r'weather.*forecast'
        ]
    
    def optimize_search_terms(self, query: str) -> List[str]:
        """Generate optimized search terms from query"""
        
        # Keep the full query as primary search term
        terms = [query]
        
        # Extract key phrases (2-3 words) rather than individual words
        words = query.lower().split()
        
        # Generate meaningful phrases
        if 'ai' in words or 'artificial intelligence' in query.lower():
            terms.extend([
                f"AI startup funding 2026",
                f"generative AI investment rounds",
                f"artificial intelligence venture capital"
            ])
        
        if 'funding' in words:
            terms.extend([
                f"venture capital funding rounds",
                f"startup investment news 2026"
            ])
            
        # Remove duplicate/similar terms
        unique_terms = []
        for term in terms:
            if not any(similar in unique_terms for similar in [term] if self._are_similar(term, similar)):
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
        
        return filtered[:10]  # Return top 10 most relevant
    
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
        
        # AI-focused companies
        if any(term in query_lower for term in ['ai', 'artificial intelligence', 'generative']):
            symbols = ['NVDA', 'GOOGL', 'MSFT', 'AMD', 'CRM']
        
        # Startup/VC focused  
        elif any(term in query_lower for term in ['startup', 'venture', 'funding']):
            symbols = ['NVDA', 'MSFT', 'GOOGL', 'META', 'AMZN']
        
        # Default tech leaders
        else:
            symbols = ['AAPL', 'MSFT', 'GOOGL', 'NVDA']
            
        return symbols

# Usage example - integrate this into simple_semantic_search.py
optimizer = QueryOptimizer()

# Enhanced search terms 
enhanced_terms = optimizer.optimize_search_terms(
    "recent funding rounds for generative AI startups"
)
print("Enhanced search terms:", enhanced_terms)

# Better financial symbols
symbols = optimizer.enhance_financial_symbols(
    "recent funding rounds for generative AI startups" 
)
print("Optimized symbols:", symbols)