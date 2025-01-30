import requests
from config import Config
from gemini_helper import GeminiHelper
import logging
import time

logger = logging.getLogger(__name__)

class WebSearch:
    MAX_RETRIES = 3
    RETRY_DELAY = 1.5

    @staticmethod
    def search(query):
        for attempt in range(WebSearch.MAX_RETRIES):
            try:
                headers = {
                    'X-API-KEY': Config.SERPER_API_KEY,
                    'Content-Type': 'application/json'
                }
                params = {
                    'q': query,
                    'gl': 'in',
                    'hl': 'en',
                    'num': 5
                }

                response = requests.post(
                    'https://google.serper.dev/search',
                    headers=headers,
                    json=params,
                    timeout=10
                )

                if response.status_code == 200:
                    results = response.json()
                    return WebSearch._process_results(query, results)
                
                logger.error(f"Search API Error: {response.status_code} - {response.text}")
                if response.status_code == 429:
                    time.sleep(WebSearch.RETRY_DELAY ** (attempt + 1))
                    continue
                    
                return {"summary": WebSearch._error_message(response.status_code), "links": []}

            except requests.exceptions.RequestException as e:
                logger.error(f"Network Error: {str(e)}")
                if attempt == WebSearch.MAX_RETRIES - 1:
                    return {"summary": "⚠️ Network issue. Check connection.", "links": []}
                time.sleep(WebSearch.RETRY_DELAY)

        return {"summary": "⚠️ Service unavailable. Try later.", "links": []}

    @staticmethod
    def _process_results(query, results):
        if not results.get('organic'):
            return {"summary": f"No results found for '{query}'", "links": []}

        try:
            truncated = str(results['organic'])[:2500]
            summary = GeminiHelper().generate_text(
                f"Summarize these search results about {query} in 3 bullet points: {truncated}"
            )
            return {
                "summary": summary,
                "links": [l.get('link') for l in results['organic'][:3] if l.get('link')]
            }
        except Exception as e:
            logger.error(f"Result processing error: {str(e)}")
            return {"summary": "⚠️ Error analyzing results", "links": []}

    @staticmethod
    def _error_message(status_code):
        codes = {
            401: "Invalid API key",
            403: "Access forbidden",
            429: "Rate limit exceeded",
            500: "Server error"
        }
        return f"⚠️ Search failed: {codes.get(status_code, 'Unknown error')}"