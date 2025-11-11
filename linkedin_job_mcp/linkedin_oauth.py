"""LinkedIn OAuth 2.0 authentication module."""

import json
import secrets
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from urllib.parse import urlencode, parse_qs, urlparse

import httpx
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from fastapi import HTTPException

from .config import config

logger = logging.getLogger(__name__)


class LinkedInOAuthError(Exception):
    """Custom exception for LinkedIn OAuth errors."""
    pass


class TokenStorage:
    """Simple in-memory token storage with encryption."""
    
    def __init__(self, secret_key: str):
        self.serializer = URLSafeTimedSerializer(secret_key)
        self._tokens = {}
    
    def store_token(self, user_id: str, token_data: Dict[str, Any]) -> None:
        """Store encrypted token data."""
        try:
            encrypted_token = self.serializer.dumps(token_data)
            self._tokens[user_id] = {
                'token': encrypted_token,
                'created_at': datetime.now(),
                'expires_at': datetime.now() + timedelta(seconds=token_data.get('expires_in', 3600))
            }
            logger.info(f"Token stored for user: {user_id}")
        except Exception as e:
            logger.error(f"Error storing token: {e}")
            raise LinkedInOAuthError(f"Failed to store token: {e}")
    
    def get_token(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve and decrypt token data."""
        try:
            if user_id not in self._tokens:
                return None
            
            token_info = self._tokens[user_id]
            
            # Check if token is expired
            if datetime.now() > token_info['expires_at']:
                logger.warning(f"Token expired for user: {user_id}")
                del self._tokens[user_id]
                return None
            
            # Decrypt token
            token_data = self.serializer.loads(token_info['token'], max_age=3600*24*30)  # 30 days max
            return token_data
            
        except (BadSignature, SignatureExpired) as e:
            logger.error(f"Token decryption failed for user {user_id}: {e}")
            if user_id in self._tokens:
                del self._tokens[user_id]
            return None
        except Exception as e:
            logger.error(f"Error retrieving token: {e}")
            return None
    
    def remove_token(self, user_id: str) -> None:
        """Remove token for user."""
        if user_id in self._tokens:
            del self._tokens[user_id]
            logger.info(f"Token removed for user: {user_id}")


class LinkedInOAuthClient:
    """LinkedIn OAuth 2.0 client."""
    
    # LinkedIn OAuth endpoints
    AUTHORIZATION_URL = "https://www.linkedin.com/oauth/v2/authorization"
    TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
    PROFILE_URL = "https://api.linkedin.com/v2/people/~"
    EMAIL_URL = "https://api.linkedin.com/v2/emailAddress?q=members&projection=(elements*(handle~))"
    
    def __init__(self):
        self.client_id = config.linkedin_client_id
        self.client_secret = config.linkedin_client_secret
        self.redirect_uri = config.linkedin_redirect_uri
        self.scopes = config.linkedin_oauth_scopes.split(',')
        
        if not self.client_id or not self.client_secret:
            raise LinkedInOAuthError("LinkedIn OAuth credentials not configured")
        
        self.token_storage = TokenStorage(config.oauth_secret_key)
        
        logger.info("LinkedIn OAuth client initialized")
    
    def get_authorization_url(self, state: Optional[str] = None) -> tuple[str, str]:
        """Generate LinkedIn authorization URL."""
        if not state:
            state = secrets.token_urlsafe(32)
        
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': ' '.join(self.scopes),
            'state': state
        }
        
        auth_url = f"{self.AUTHORIZATION_URL}?{urlencode(params)}"
        logger.info(f"Generated authorization URL with state: {state}")
        
        return auth_url, state
    
    async def exchange_code_for_token(self, authorization_code: str, state: str) -> Dict[str, Any]:
        """Exchange authorization code for access token."""
        try:
            async with httpx.AsyncClient() as client:
                data = {
                    'grant_type': 'authorization_code',
                    'code': authorization_code,
                    'redirect_uri': self.redirect_uri,
                    'client_id': self.client_id,
                    'client_secret': self.client_secret
                }
                
                headers = {
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
                
                response = await client.post(self.TOKEN_URL, data=data, headers=headers)
                
                if response.status_code != 200:
                    error_msg = f"Token exchange failed: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    raise LinkedInOAuthError(error_msg)
                
                token_data = response.json()
                logger.info("Successfully exchanged authorization code for token")
                
                return token_data
                
        except httpx.RequestError as e:
            error_msg = f"Network error during token exchange: {e}"
            logger.error(error_msg)
            raise LinkedInOAuthError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error during token exchange: {e}"
            logger.error(error_msg)
            raise LinkedInOAuthError(error_msg)
    
    async def get_user_profile(self, access_token: str) -> Dict[str, Any]:
        """Get user profile information from LinkedIn."""
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                }
                
                # Get basic profile
                profile_response = await client.get(self.PROFILE_URL, headers=headers)
                
                if profile_response.status_code != 200:
                    error_msg = f"Profile fetch failed: {profile_response.status_code} - {profile_response.text}"
                    logger.error(error_msg)
                    raise LinkedInOAuthError(error_msg)
                
                profile_data = profile_response.json()
                
                # Get email address
                email_response = await client.get(self.EMAIL_URL, headers=headers)
                
                if email_response.status_code == 200:
                    email_data = email_response.json()
                    if 'elements' in email_data and email_data['elements']:
                        profile_data['email'] = email_data['elements'][0]['handle~']['emailAddress']
                
                logger.info("Successfully retrieved user profile")
                return profile_data
                
        except httpx.RequestError as e:
            error_msg = f"Network error during profile fetch: {e}"
            logger.error(error_msg)
            raise LinkedInOAuthError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error during profile fetch: {e}"
            logger.error(error_msg)
            raise LinkedInOAuthError(error_msg)
    
    async def make_authenticated_request(self, user_id: str, url: str, method: str = "GET", **kwargs) -> httpx.Response:
        """Make an authenticated request to LinkedIn API."""
        token_data = self.token_storage.get_token(user_id)
        
        if not token_data:
            raise LinkedInOAuthError("No valid token found for user")
        
        access_token = token_data.get('access_token')
        if not access_token:
            raise LinkedInOAuthError("Invalid token data")
        
        headers = kwargs.get('headers', {})
        headers['Authorization'] = f'Bearer {access_token}'
        kwargs['headers'] = headers
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(method, url, **kwargs)
                
                if response.status_code == 401:
                    # Token expired or invalid
                    self.token_storage.remove_token(user_id)
                    raise LinkedInOAuthError("Token expired or invalid")
                
                return response
                
        except httpx.RequestError as e:
            error_msg = f"Network error during authenticated request: {e}"
            logger.error(error_msg)
            raise LinkedInOAuthError(error_msg)
    
    def store_user_token(self, user_id: str, token_data: Dict[str, Any]) -> None:
        """Store user token."""
        self.token_storage.store_token(user_id, token_data)
    
    def get_user_token(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user token."""
        return self.token_storage.get_token(user_id)
    
    def remove_user_token(self, user_id: str) -> None:
        """Remove user token."""
        self.token_storage.remove_token(user_id)
    
    def is_user_authenticated(self, user_id: str) -> bool:
        """Check if user has valid authentication."""
        return self.get_user_token(user_id) is not None


# Global OAuth client instance
linkedin_oauth_client = None

def get_linkedin_oauth_client() -> LinkedInOAuthClient:
    """Get or create LinkedIn OAuth client instance."""
    global linkedin_oauth_client
    
    if linkedin_oauth_client is None:
        try:
            linkedin_oauth_client = LinkedInOAuthClient()
        except LinkedInOAuthError as e:
            logger.warning(f"LinkedIn OAuth not configured: {e}")
            return None
    
    return linkedin_oauth_client


class LinkedInAPIClient:
    """LinkedIn API client using OAuth tokens."""
    
    def __init__(self, oauth_client: LinkedInOAuthClient):
        self.oauth_client = oauth_client
    
    async def search_jobs(self, user_id: str, keywords: str, location: str = "", **filters) -> Dict[str, Any]:
        """Search for jobs using LinkedIn API (placeholder - LinkedIn doesn't provide public job search API)."""
        # Note: LinkedIn doesn't provide a public job search API
        # This is a placeholder for when/if they do, or for other LinkedIn API calls
        
        logger.warning("LinkedIn job search API is not publicly available")
        
        # For now, we'll return a message indicating this limitation
        return {
            "success": False,
            "message": "LinkedIn job search API is not publicly available. Consider using web scraping as fallback.",
            "jobs": []
        }
    
    async def get_user_connections(self, user_id: str) -> Dict[str, Any]:
        """Get user's LinkedIn connections."""
        try:
            # LinkedIn API endpoint for connections (limited access)
            url = "https://api.linkedin.com/v2/connections"
            
            response = await self.oauth_client.make_authenticated_request(user_id, url)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get connections: {response.status_code} - {response.text}")
                return {"success": False, "error": response.text}
                
        except LinkedInOAuthError as e:
            logger.error(f"OAuth error getting connections: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error getting connections: {e}")
            return {"success": False, "error": str(e)}
    
    async def post_update(self, user_id: str, content: str) -> Dict[str, Any]:
        """Post an update to LinkedIn (requires w_member_social scope)."""
        try:
            url = "https://api.linkedin.com/v2/ugcPosts"
            
            # Get user profile to get the person URN
            profile = await self.oauth_client.get_user_profile(
                self.oauth_client.get_user_token(user_id)['access_token']
            )
            
            person_urn = f"urn:li:person:{profile['id']}"
            
            post_data = {
                "author": person_urn,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": content
                        },
                        "shareMediaCategory": "NONE"
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }
            
            response = await self.oauth_client.make_authenticated_request(
                user_id, url, method="POST", json=post_data
            )
            
            if response.status_code == 201:
                return {"success": True, "post_id": response.json().get("id")}
            else:
                logger.error(f"Failed to post update: {response.status_code} - {response.text}")
                return {"success": False, "error": response.text}
                
        except LinkedInOAuthError as e:
            logger.error(f"OAuth error posting update: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error posting update: {e}")
            return {"success": False, "error": str(e)}


def get_linkedin_api_client() -> Optional[LinkedInAPIClient]:
    """Get LinkedIn API client instance."""
    oauth_client = get_linkedin_oauth_client()
    if oauth_client:
        return LinkedInAPIClient(oauth_client)
    return None