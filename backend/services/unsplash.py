"""
Unsplash Service: Fetch high-quality photos with proper attribution
Following Unsplash API guidelines: https://unsplash.com/documentation
"""

import httpx
from config import UNSPLASH_ACCESS_KEY
from typing import Optional, Dict, List
import asyncio

class UnsplashService:
    """Service to fetch photos from Unsplash API with proper attribution"""
    
    BASE_URL = "https://api.unsplash.com"
    TIMEOUT = 10.0
    APP_NAME = "GateAwayGenius"
    
    @staticmethod
    async def search_photos(
        query: str,
        per_page: int = 5,
    ) -> List[Dict]:
        """
        Search for photos on Unsplash
        
        Args:
            query: Search query (e.g., "lisbon plaza")
            per_page: Number of results to return
        
        Returns:
            List of photos with {
                url: hotlinked image URL,
                photographer: photographer name,
                photographer_url: link to photographer profile (with UTM),
                download_location: endpoint to ping for download tracking,
                description: photo description
            }
        """
        if not UNSPLASH_ACCESS_KEY:
            print("WARNING: UNSPLASH_ACCESS_KEY not configured")
            return []
        
        try:
            params = {
                "query": query,
                "per_page": per_page,
                "client_id": UNSPLASH_ACCESS_KEY,
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{UnsplashService.BASE_URL}/search/photos",
                    params=params,
                    timeout=UnsplashService.TIMEOUT
                )
                response.raise_for_status()
                
                data = response.json()
                results = []
                
                for photo in data.get("results", [])[:per_page]:
                    # Build UTM-tagged photographer URL
                    photographer_profile = photo["user"]["links"]["html"]
                    photographer_url = f"{photographer_profile}?utm_source={UnsplashService.APP_NAME}&utm_medium=referral"
                    
                    # Build UTM-tagged Unsplash URL
                    unsplash_url = f"https://unsplash.com/?utm_source={UnsplashService.APP_NAME}&utm_medium=referral"
                    
                    results.append({
                        "url": photo["urls"]["regular"],  # Hotlinked image URL
                        "photographer": photo["user"]["name"],
                        "photographer_username": photo["user"]["username"],
                        "photographer_url": photographer_url,
                        "unsplash_url": unsplash_url,
                        "download_location": photo["links"]["download_location"],
                        "description": photo.get("description") or photo.get("alt_description", ""),
                    })
                
                return results
                
        except Exception as e:
            print(f"ERROR: Unsplash API error: {e}")
            return []
    
    @staticmethod
    async def trigger_download(download_location: str) -> bool:
        """
        Trigger a download event (required by Unsplash API guidelines)
        Call this when a user selects/downloads a photo
        
        Args:
            download_location: The download endpoint URL from photo data
        
        Returns:
            True if successful, False otherwise
        """
        if not download_location:
            return False
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    download_location,
                    timeout=UnsplashService.TIMEOUT
                )
                response.raise_for_status()
                return True
        except Exception as e:
            print(f"WARNING: Failed to trigger download event: {e}")
            return False
