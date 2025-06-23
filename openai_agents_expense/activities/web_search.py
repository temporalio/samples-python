"""
Web search activity for vendor validation in the expense processing workflow.

This activity performs web searches to validate vendor information and gather business context
for categorization and fraud detection purposes.
"""

import asyncio
import re
from typing import Any, Dict, List

import httpx
from temporalio import activity


@activity.defn
async def web_search_activity(query: str, max_results: int = 5) -> Dict[str, Any]:
    """
    Perform a web search to validate vendor information.

    Args:
        query: Search query (typically vendor name)
        max_results: Maximum number of results to return

    Returns:
        Dictionary containing search results and analysis
    """

    # Activity start logging
    activity.logger.info(
        f"🔍 WEB_SEARCH_START: Starting web search",
        extra={
            "query": query,
            "max_results": max_results,
            "activity": "web_search_activity",
            "search_stage": "start",
        },
    )

    # Sanitize search query to prevent malicious searches
    sanitized_query = _sanitize_search_query(query)

    if sanitized_query != query:
        activity.logger.info(
            f"🧹 QUERY_SANITIZED: Search query was sanitized",
            extra={
                "original_query": query,
                "sanitized_query": sanitized_query,
                "activity": "web_search_activity",
                "search_stage": "sanitization",
            },
        )

    try:
        # Simulate web search using a mock search service
        activity.logger.info(
            f"🌐 SEARCH_EXECUTING: Performing web search",
            extra={
                "query": sanitized_query,
                "max_results": max_results,
                "activity": "web_search_activity",
                "search_stage": "execution",
            },
        )

        # In a real implementation, this would use a proper search API like Google Custom Search, Bing, etc.
        search_results = await _mock_web_search(sanitized_query, max_results)

        activity.logger.info(
            f"📊 SEARCH_RESULTS: Web search completed",
            extra={
                "query": sanitized_query,
                "results_count": len(search_results),
                "result_types": [r.get("type", "unknown") for r in search_results],
                "activity": "web_search_activity",
                "search_stage": "results_received",
            },
        )

        # Analyze search results for vendor validation
        activity.logger.info(
            f"🔬 ANALYSIS_START: Analyzing search results",
            extra={
                "query": sanitized_query,
                "results_count": len(search_results),
                "activity": "web_search_activity",
                "search_stage": "analysis_start",
            },
        )

        analysis = _analyze_search_results(sanitized_query, search_results)

        activity.logger.info(
            f"✅ ANALYSIS_COMPLETE: Search analysis completed",
            extra={
                "query": sanitized_query,
                "is_legitimate": analysis["is_legitimate"],
                "confidence_score": analysis["confidence_score"],
                "business_type": analysis["business_type"],
                "legitimacy_indicators": analysis["legitimacy_indicators"],
                "activity": "web_search_activity",
                "search_stage": "analysis_complete",
            },
        )

        final_result = {
            "query": sanitized_query,
            "results": search_results,
            "analysis": analysis,
            "result_count": len(search_results),
        }

        activity.logger.info(
            f"🎯 WEB_SEARCH_SUCCESS: Web search activity completed successfully",
            extra={
                "query": sanitized_query,
                "results_count": len(search_results),
                "is_legitimate": analysis["is_legitimate"],
                "confidence_score": analysis["confidence_score"],
                "activity": "web_search_activity",
                "search_stage": "success",
            },
        )

        return final_result

    except Exception as e:
        activity.logger.error(
            f"🚨 WEB_SEARCH_ERROR: Web search failed",
            extra={
                "query": sanitized_query,
                "error": str(e),
                "error_type": type(e).__name__,
                "activity": "web_search_activity",
                "search_stage": "error",
            },
        )

        # Return empty results on failure - let agents handle the lack of information
        fallback_result = {
            "query": sanitized_query,
            "results": [],
            "analysis": {
                "is_legitimate": False,
                "confidence_score": 0.0,
                "summary": f"Web search failed: {str(e)}",
                "business_type": "unknown",
                "legitimacy_indicators": [],
            },
            "result_count": 0,
        }

        activity.logger.info(
            f"⚠️ WEB_SEARCH_FALLBACK: Returning fallback results due to search failure",
            extra={
                "query": sanitized_query,
                "fallback_result": True,
                "activity": "web_search_activity",
                "search_stage": "fallback",
            },
        )

        return fallback_result


def _sanitize_search_query(query: str) -> str:
    """
    Sanitize search query to prevent malicious searches.

    Args:
        query: Raw search query

    Returns:
        Sanitized search query
    """
    # Remove potentially harmful characters and limit length
    sanitized = re.sub(r'[<>"\';\\]', "", query)
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

    activity.logger.info(
        f"🤖 MOCK_SEARCH: Generating mock search results",
        extra={
            "query": query,
            "query_lower": query_lower,
            "activity": "web_search_activity",
            "search_stage": "mock_generation",
        },
    )

    # Simulate results for common legitimate businesses
    if any(
        term in query_lower
        for term in ["staples", "office depot", "best buy", "amazon"]
    ):
        mock_results = [
            {
                "title": f"{query} - Official Website",
                "url": f"https://www.{query.lower().replace(' ', '')}.com",
                "snippet": f"Official website of {query}. Major retailer offering products and services.",
                "type": "official_website",
            },
            {
                "title": f"{query} Store Locations",
                "url": f"https://locations.{query.lower().replace(' ', '')}.com",
                "snippet": f"Find {query} store locations near you. Over 1000 locations nationwide.",
                "type": "location_info",
            },
        ]

        activity.logger.info(
            f"🏪 MOCK_MAJOR_RETAILER: Generated results for major retailer",
            extra={
                "query": query,
                "vendor_type": "major_retailer",
                "results_count": len(mock_results),
                "activity": "web_search_activity",
                "search_stage": "mock_major_retailer",
            },
        )

    # Simulate results for airlines
    elif any(
        term in query_lower
        for term in ["british airways", "american airlines", "delta", "united"]
    ):
        mock_results = [
            {
                "title": f"{query} - Official Airline Website",
                "url": f"https://www.{query.lower().replace(' ', '')}.com",
                "snippet": f"Book flights with {query}. International airline with safety certifications.",
                "type": "official_website",
            },
            {
                "title": f"{query} Flight Status",
                "url": f"https://flightstatus.{query.lower().replace(' ', '')}.com",
                "snippet": f"Check {query} flight status and schedules.",
                "type": "service_info",
            },
        ]

        activity.logger.info(
            f"✈️ MOCK_AIRLINE: Generated results for airline",
            extra={
                "query": query,
                "vendor_type": "airline",
                "results_count": len(mock_results),
                "activity": "web_search_activity",
                "search_stage": "mock_airline",
            },
        )

    # Simulate results for professional services
    elif any(
        term in query_lower
        for term in ["associates", "law", "consulting", "llc", "inc"]
    ):
        if "smith" in query_lower:
            mock_results = [
                {
                    "title": f"{query} - Legal Services",
                    "url": f"https://www.{query.lower().replace(' ', '').replace('&', 'and')}.com",
                    "snippet": f"{query} provides legal services including business law and contract review.",
                    "type": "professional_services",
                }
            ]
        else:
            mock_results = [
                {
                    "title": f"{query} - Professional Services",
                    "url": f"https://www.{query.lower().replace(' ', '')}.com",
                    "snippet": f"{query} offers professional consulting services to businesses.",
                    "type": "professional_services",
                }
            ]

        activity.logger.info(
            f"🏢 MOCK_PROFESSIONAL: Generated results for professional services",
            extra={
                "query": query,
                "vendor_type": "professional_services",
                "results_count": len(mock_results),
                "activity": "web_search_activity",
                "search_stage": "mock_professional",
            },
        )

    # Simulate suspicious or non-existent vendors
    elif any(term in query_lower for term in ["totally legit", "fake", "scam"]):
        mock_results = []  # No results for suspicious vendors

        activity.logger.warning(
            f"🚩 MOCK_SUSPICIOUS: No results for suspicious vendor query",
            extra={
                "query": query,
                "vendor_type": "suspicious",
                "results_count": 0,
                "activity": "web_search_activity",
                "search_stage": "mock_suspicious",
            },
        )

    # Simulate conflicting results for specific test cases
    elif "tony's restaurant" in query_lower:
        mock_results = [
            {
                "title": "Tony's Restaurant - Open",
                "url": "https://www.tonysrestaurant.com",
                "snippet": "Tony's Restaurant - Open daily for lunch and dinner. Call for reservations.",
                "type": "business_listing",
            },
            {
                "title": "Tony's Restaurant - CLOSED",
                "url": "https://yelp.com/biz/tonys-restaurant",
                "snippet": "Tony's Restaurant - Permanently closed as of 2023. See other restaurants nearby.",
                "type": "review_site",
            },
        ]

        activity.logger.info(
            f"🍽️ MOCK_CONFLICTING: Generated conflicting results for restaurant",
            extra={
                "query": query,
                "vendor_type": "restaurant_conflicting",
                "results_count": len(mock_results),
                "has_conflict": True,
                "activity": "web_search_activity",
                "search_stage": "mock_conflicting",
            },
        )

    # Default: simulate mixed results for generic queries
    else:
        mock_results = [
            {
                "title": f"{query} - Business Information",
                "url": f"https://businessinfo.com/{query.lower().replace(' ', '-')}",
                "snippet": f"Business information for {query}. Limited details available.",
                "type": "directory_listing",
            }
        ]

        activity.logger.info(
            f"📋 MOCK_GENERIC: Generated generic results",
            extra={
                "query": query,
                "vendor_type": "generic",
                "results_count": len(mock_results),
                "activity": "web_search_activity",
                "search_stage": "mock_generic",
            },
        )

    final_results = mock_results[:max_results]

    activity.logger.info(
        f"🎯 MOCK_COMPLETE: Mock search results generated",
        extra={
            "query": query,
            "total_results": len(mock_results),
            "returned_results": len(final_results),
            "max_results": max_results,
            "activity": "web_search_activity",
            "search_stage": "mock_complete",
        },
    )

    return final_results


def _analyze_search_results(
    query: str, results: List[Dict[str, str]]
) -> Dict[str, Any]:
    """
    Analyze search results to determine vendor legitimacy and extract business information.

    Args:
        query: Original search query
        results: List of search results

    Returns:
        Analysis dictionary with legitimacy assessment
    """

    activity.logger.info(
        f"🔍 ANALYSIS_START: Starting search results analysis",
        extra={
            "query": query,
            "results_count": len(results),
            "activity": "web_search_activity",
            "analysis_stage": "start",
        },
    )

    if not results:
        activity.logger.warning(
            f"⚠️ NO_RESULTS: No search results to analyze",
            extra={
                "query": query,
                "results_count": 0,
                "activity": "web_search_activity",
                "analysis_stage": "no_results",
            },
        )

        return {
            "is_legitimate": False,
            "confidence_score": 0.0,
            "summary": "No results found. Web search returned no business listings, website, reviews, or other verification of existence.",
            "business_type": "unknown",
            "legitimacy_indicators": [],
        }

    # Analyze result types and content
    official_websites = [r for r in results if r.get("type") == "official_website"]
    business_listings = [
        r for r in results if r.get("type") in ["business_listing", "directory_listing"]
    ]
    location_info = [r for r in results if r.get("type") == "location_info"]

    activity.logger.info(
        f"📊 RESULT_ANALYSIS: Categorized search results",
        extra={
            "query": query,
            "official_websites": len(official_websites),
            "business_listings": len(business_listings),
            "location_info": len(location_info),
            "activity": "web_search_activity",
            "analysis_stage": "categorization",
        },
    )

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

    activity.logger.info(
        f"🏷️ BUSINESS_TYPE: Determined business type",
        extra={
            "query": query,
            "business_type": business_type,
            "activity": "web_search_activity",
            "analysis_stage": "business_type",
        },
    )

    # Calculate legitimacy based on result quality
    if official_websites:
        legitimacy_indicators.append("official_website_found")
        activity.logger.info(
            f"✅ OFFICIAL_WEBSITE: Found official website",
            extra={
                "query": query,
                "official_websites_count": len(official_websites),
                "activity": "web_search_activity",
                "analysis_stage": "official_website",
            },
        )

    if location_info:
        legitimacy_indicators.append("location_information_available")
        activity.logger.info(
            f"📍 LOCATION_INFO: Found location information",
            extra={
                "query": query,
                "location_info_count": len(location_info),
                "activity": "web_search_activity",
                "analysis_stage": "location_info",
            },
        )

    if len(results) >= 3:
        legitimacy_indicators.append("multiple_references_found")
        activity.logger.info(
            f"📚 MULTIPLE_REFS: Found multiple references",
            extra={
                "query": query,
                "references_count": len(results),
                "activity": "web_search_activity",
                "analysis_stage": "multiple_refs",
            },
        )

    # Check for conflicting information (like Tony's Restaurant scenario)
    conflicting_status = False
    if any("closed" in r["snippet"].lower() for r in results) and any(
        "open" in r["snippet"].lower() for r in results
    ):
        conflicting_status = True
        legitimacy_indicators.append("conflicting_business_status")
        activity.logger.warning(
            f"⚠️ CONFLICTING_STATUS: Found conflicting business status",
            extra={
                "query": query,
                "conflicting_status": True,
                "activity": "web_search_activity",
                "analysis_stage": "conflicting_status",
            },
        )

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

    activity.logger.info(
        f"📊 CONFIDENCE_CALC: Calculated confidence score",
        extra={
            "query": query,
            "confidence_score": confidence_score,
            "factors": {
                "official_websites": len(official_websites) > 0,
                "location_info": len(location_info) > 0,
                "business_listings": len(business_listings) > 0,
                "multiple_results": len(results) >= 2,
                "conflicting_status": conflicting_status,
            },
            "activity": "web_search_activity",
            "analysis_stage": "confidence_calc",
        },
    )

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
        summary = (
            f"Mixed results found. Limited business information available for {query}."
        )

    final_analysis = {
        "is_legitimate": is_legitimate,
        "confidence_score": confidence_score,
        "summary": summary,
        "business_type": business_type,
        "legitimacy_indicators": legitimacy_indicators,
    }

    activity.logger.info(
        f"✅ ANALYSIS_COMPLETE: Search results analysis completed",
        extra={
            "query": query,
            "is_legitimate": is_legitimate,
            "confidence_score": confidence_score,
            "business_type": business_type,
            "legitimacy_indicators_count": len(legitimacy_indicators),
            "conflicting_status": conflicting_status,
            "activity": "web_search_activity",
            "analysis_stage": "complete",
        },
    )

    return final_analysis
