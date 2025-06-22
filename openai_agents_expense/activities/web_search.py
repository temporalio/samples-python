"""
Web search activity for vendor validation in the expense processing workflow.

This activity performs web searches to validate vendor information and gather business context
for categorization and fraud detection purposes.
"""

import asyncio
import re
from typing import Dict, List

import httpx
from temporalio import activity


@activity.defn
async def web_search_activity(query: str, max_results: int = 5) -> Dict[str, any]:
    """
    Perform a web search to validate vendor information.
    
    Args:
        query: Search query (typically vendor name)
        max_results: Maximum number of results to return
        
    Returns:
        Dictionary containing search results and analysis
    """
    logger = activity.logger
    logger.info(f"Performing web search for: {query}")
    
    # Sanitize search query to prevent malicious searches
    sanitized_query = _sanitize_search_query(query)
    
    try:
        # Simulate web search using a mock search service
        # In a real implementation, this would use a proper search API like Google Custom Search, Bing, etc.
        search_results = await _mock_web_search(sanitized_query, max_results)
        
        # Analyze search results for vendor validation
        analysis = _analyze_search_results(sanitized_query, search_results)
        
        return {
            "query": sanitized_query,
            "results": search_results,
            "analysis": analysis,
            "result_count": len(search_results)
        }
        
    except Exception as e:
        logger.error(f"Web search failed for query '{sanitized_query}': {str(e)}")
        # Return empty results on failure - let agents handle the lack of information
        return {
            "query": sanitized_query,
            "results": [],
            "analysis": {
                "is_legitimate": False,
                "confidence_score": 0.0,
                "summary": f"Web search failed: {str(e)}",
                "business_type": "unknown",
                "legitimacy_indicators": []
            },
            "result_count": 0
        }


def _sanitize_search_query(query: str) -> str:
    """
    Sanitize search query to prevent malicious searches.
    
    Args:
        query: Raw search query
        
    Returns:
        Sanitized search query
    """
    # Remove potentially harmful characters and limit length
    sanitized = re.sub(r'[<>"\';\\]', '', query)
    sanitized = sanitized.strip()[:100]  # Limit to 100 characters
    
    return sanitized


async def _mock_web_search(query: str, max_results: int) -> List[Dict[str, str]]:
    """
    Mock web search implementation for demonstration purposes.
    
    In a real implementation, this would call actual search APIs.
    """
    # Simulate network delay
    await asyncio.sleep(0.5)
    
    # Mock search results based on query patterns
    mock_results = []
    
    query_lower = query.lower()
    
    # Simulate results for common legitimate businesses
    if any(term in query_lower for term in ["staples", "office depot", "best buy", "amazon"]):
        mock_results = [
            {
                "title": f"{query} - Official Website",
                "url": f"https://www.{query.lower().replace(' ', '')}.com",
                "snippet": f"Official website of {query}. Major retailer offering products and services.",
                "type": "official_website"
            },
            {
                "title": f"{query} Store Locations",
                "url": f"https://locations.{query.lower().replace(' ', '')}.com",
                "snippet": f"Find {query} store locations near you. Over 1000 locations nationwide.",
                "type": "location_info"
            }
        ]
    
    # Simulate results for airlines
    elif any(term in query_lower for term in ["british airways", "american airlines", "delta", "united"]):
        mock_results = [
            {
                "title": f"{query} - Official Airline Website",
                "url": f"https://www.{query.lower().replace(' ', '')}.com",
                "snippet": f"Book flights with {query}. International airline with safety certifications.",
                "type": "official_website"
            },
            {
                "title": f"{query} Flight Status",
                "url": f"https://flightstatus.{query.lower().replace(' ', '')}.com",
                "snippet": f"Check {query} flight status and schedules.",
                "type": "service_info"
            }
        ]
    
    # Simulate results for professional services
    elif any(term in query_lower for term in ["associates", "law", "consulting", "llc", "inc"]):
        if "smith" in query_lower:
            mock_results = [
                {
                    "title": f"{query} - Legal Services",
                    "url": f"https://www.{query.lower().replace(' ', '').replace('&', 'and')}.com",
                    "snippet": f"{query} provides legal services including business law and contract review.",
                    "type": "professional_services"
                }
            ]
        else:
            mock_results = [
                {
                    "title": f"{query} - Professional Services",
                    "url": f"https://www.{query.lower().replace(' ', '')}.com",
                    "snippet": f"{query} offers professional consulting services to businesses.",
                    "type": "professional_services"
                }
            ]
    
    # Simulate suspicious or non-existent vendors
    elif any(term in query_lower for term in ["totally legit", "fake", "scam"]):
        mock_results = []  # No results for suspicious vendors
    
    # Simulate conflicting results for specific test cases
    elif "tony's restaurant" in query_lower:
        mock_results = [
            {
                "title": "Tony's Restaurant - Open",
                "url": "https://www.tonysrestaurant.com",
                "snippet": "Tony's Restaurant - Open daily for lunch and dinner. Call for reservations.",
                "type": "business_listing"
            },
            {
                "title": "Tony's Restaurant - CLOSED",
                "url": "https://yelp.com/biz/tonys-restaurant",
                "snippet": "Tony's Restaurant - Permanently closed as of 2023. See other restaurants nearby.",
                "type": "review_site"
            }
        ]
    
    # Default: simulate mixed results for generic queries
    else:
        mock_results = [
            {
                "title": f"{query} - Business Information",
                "url": f"https://businessinfo.com/{query.lower().replace(' ', '-')}",
                "snippet": f"Business information for {query}. Limited details available.",
                "type": "directory_listing"
            }
        ]
    
    return mock_results[:max_results]


def _analyze_search_results(query: str, results: List[Dict[str, str]]) -> Dict[str, any]:
    """
    Analyze search results to determine vendor legitimacy and extract business information.
    
    Args:
        query: Original search query
        results: List of search results
        
    Returns:
        Analysis dictionary with legitimacy assessment
    """
    if not results:
        return {
            "is_legitimate": False,
            "confidence_score": 0.0,
            "summary": "No results found. Web search returned no business listings, website, reviews, or other verification of existence.",
            "business_type": "unknown",
            "legitimacy_indicators": []
        }
    
    # Analyze result types and content
    official_websites = [r for r in results if r.get("type") == "official_website"]
    business_listings = [r for r in results if r.get("type") in ["business_listing", "directory_listing"]]
    location_info = [r for r in results if r.get("type") == "location_info"]
    
    legitimacy_indicators = []
    business_type = "unknown"
    
    # Determine business type from results
    query_lower = query.lower()
    if any(term in query_lower for term in ["restaurant", "cafe", "diner"]):
        business_type = "restaurant"
    elif any(term in query_lower for term in ["inc", "corp", "llc", "ltd"]):
        business_type = "corporation"
    elif any(term in query_lower for term in ["associates", "consulting", "services"]):
        business_type = "professional_services"
    elif any(term in query_lower for term in ["airlines", "airways"]):
        business_type = "airline"
    
    # Calculate legitimacy based on result quality
    if official_websites:
        legitimacy_indicators.append("official_website_found")
        
    if location_info:
        legitimacy_indicators.append("location_information_available")
        
    if len(results) >= 3:
        legitimacy_indicators.append("multiple_references_found")
    
    # Check for conflicting information (like Tony's Restaurant scenario)
    conflicting_status = False
    if any("closed" in r["snippet"].lower() for r in results) and any("open" in r["snippet"].lower() for r in results):
        conflicting_status = True
        legitimacy_indicators.append("conflicting_business_status")
    
    # Calculate confidence score
    confidence_score = 0.0
    if official_websites:
        confidence_score += 0.4
    if location_info:
        confidence_score += 0.2
    if business_listings:
        confidence_score += 0.2
    if len(results) >= 2:
        confidence_score += 0.1
    if conflicting_status:
        confidence_score -= 0.3
    
    confidence_score = max(0.0, min(1.0, confidence_score))
    
    # Determine legitimacy
    is_legitimate = confidence_score >= 0.5 and not conflicting_status
    
    # Generate summary
    if conflicting_status:
        summary = f"Conflicting results found. Multiple search results show mixed information about business status."
    elif official_websites:
        summary = f"Clear results found. {query} has official website and business presence with established operations."
    elif not results:
        summary = f"No results found. Web search returned no business listings or verification of existence."
    else:
        summary = f"Mixed results found. Limited business information available for {query}."
    
    return {
        "is_legitimate": is_legitimate,
        "confidence_score": confidence_score,
        "summary": summary,
        "business_type": business_type,
        "legitimacy_indicators": legitimacy_indicators
    } 