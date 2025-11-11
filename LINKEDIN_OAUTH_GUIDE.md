# LinkedIn OAuth 2.0 Integration Guide

This guide explains how to set up and use the LinkedIn OAuth 2.0 integration in the LinkedIn Job Search API & MCP Server.

## 🚀 Overview

The LinkedIn OAuth 2.0 integration allows users to authenticate with LinkedIn and access LinkedIn APIs directly, providing a more reliable and compliant alternative to web scraping. This integration follows the standard OAuth 2.0 authorization code flow.

## 📋 Prerequisites

1. **LinkedIn Developer Account**: You need a LinkedIn Developer account to create an application
2. **LinkedIn Application**: Create a LinkedIn application to get Client ID and Client Secret
3. **Environment Configuration**: Set up OAuth credentials in your environment

## 🔧 Setup Instructions

### Step 1: Create LinkedIn Application

1. Go to the [LinkedIn Developer Portal](https://www.linkedin.com/developers/)
2. Click "Create App" and fill in the required information:
   - **App name**: Your application name
   - **LinkedIn Page**: Associate with a LinkedIn company page
   - **Privacy policy URL**: Your privacy policy URL
   - **App logo**: Upload a logo for your app

3. After creating the app, note down:
   - **Client ID**: Found in the "Auth" tab
   - **Client Secret**: Found in the "Auth" tab (keep this secure!)

### Step 2: Configure OAuth Settings

1. In your LinkedIn app's "Auth" tab, add redirect URLs:
   - For local development: `http://localhost:8000/auth/linkedin/callback`
   - For production: `https://yourdomain.com/auth/linkedin/callback`

2. Request the following OAuth scopes:
   - `r_liteprofile`: Access to basic profile information
   - `r_emailaddress`: Access to email address
   - `w_member_social`: Permission to post on behalf of the user (optional)

### Step 3: Environment Configuration

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your LinkedIn OAuth credentials:
   ```env
   # LinkedIn OAuth Configuration
   LINKEDIN_CLIENT_ID=your_linkedin_client_id_here
   LINKEDIN_CLIENT_SECRET=your_linkedin_client_secret_here
   LINKEDIN_REDIRECT_URI=http://localhost:8000/auth/linkedin/callback
   LINKEDIN_OAUTH_SCOPES=r_liteprofile,r_emailaddress,w_member_social
   
   # OAuth Security
   OAUTH_SECRET_KEY=your-secure-secret-key-change-this-in-production
   ```

3. **Important Security Notes**:
   - Never commit your `.env` file to version control
   - Use a strong, unique secret key for `OAUTH_SECRET_KEY`
   - In production, use environment variables instead of `.env` files

## 🌐 Web Interface Usage

### Connecting to LinkedIn

1. Start the server:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

2. Open your browser and go to `http://localhost:8000`

3. In the "LinkedIn Authentication" section, click "🔗 Connect to LinkedIn"

4. You'll be redirected to LinkedIn to authorize the application

5. After authorization, you'll be redirected back and see your profile information

### Using OAuth Features

Once connected, you can:
- View your LinkedIn profile information
- Check authentication status
- Disconnect from LinkedIn when needed

## 🔌 API Endpoints

### OAuth Flow Endpoints

#### 1. Initiate Authorization
```http
GET /auth/linkedin
```

**Response:**
```json
{
  "success": true,
  "authorization_url": "https://www.linkedin.com/oauth/v2/authorization?...",
  "state": "secure_random_state",
  "message": "Redirect user to authorization URL"
}
```

#### 2. Handle Callback
```http
GET /auth/linkedin/callback?code=AUTH_CODE&state=STATE
```

**Response:**
```json
{
  "success": true,
  "message": "Successfully authenticated with LinkedIn",
  "user_id": "linkedin_12345",
  "profile": {
    "id": "12345",
    "localizedFirstName": "John",
    "localizedLastName": "Doe",
    "email": "john.doe@example.com"
  }
}
```

#### 3. Check Authentication Status
```http
GET /auth/linkedin/status/{user_id}
```

#### 4. Logout
```http
DELETE /auth/linkedin/{user_id}
```

### LinkedIn API Endpoints

#### 1. Get Profile
```http
GET /linkedin/profile/{user_id}
```

#### 2. Post Update
```http
POST /linkedin/post/{user_id}
Content-Type: application/json

{
  "content": "Hello LinkedIn! This is posted via API."
}
```

#### 3. Get Connections
```http
GET /linkedin/connections/{user_id}
```

## 🤖 MCP Tools

The MCP server includes several OAuth-enabled tools:

### 1. `linkedin_oauth_authorize`
Generate LinkedIn OAuth authorization URL.

**Usage:**
```json
{
  "name": "linkedin_oauth_authorize",
  "arguments": {}
}
```

### 2. `linkedin_oauth_status`
Check authentication status for a user.

**Usage:**
```json
{
  "name": "linkedin_oauth_status",
  "arguments": {
    "user_id": "linkedin_12345"
  }
}
```

### 3. `linkedin_get_profile`
Get LinkedIn profile information.

**Usage:**
```json
{
  "name": "linkedin_get_profile",
  "arguments": {
    "user_id": "linkedin_12345"
  }
}
```

### 4. `linkedin_post_update`
Post an update to LinkedIn.

**Usage:**
```json
{
  "name": "linkedin_post_update",
  "arguments": {
    "user_id": "linkedin_12345",
    "content": "Hello from the MCP server!"
  }
}
```

### 5. `linkedin_get_connections`
Get LinkedIn connections.

**Usage:**
```json
{
  "name": "linkedin_get_connections",
  "arguments": {
    "user_id": "linkedin_12345"
  }
}
```

## 🔒 Security Features

### Token Storage
- Tokens are encrypted using `itsdangerous` with your secret key
- Tokens are stored in memory (for production, consider Redis or database)
- Automatic token expiration handling

### State Validation
- CSRF protection using state parameter
- State values are validated during callback

### Error Handling
- Comprehensive error handling for OAuth flows
- Automatic token refresh (when supported by LinkedIn)
- Graceful degradation when OAuth is not configured

## 🚨 Important Limitations

### LinkedIn API Restrictions

1. **Job Search API**: LinkedIn does not provide a public job search API. The OAuth integration is primarily for:
   - Profile access
   - Social posting
   - Connection management
   - Other LinkedIn APIs (not job search)

2. **Rate Limits**: LinkedIn APIs have rate limits. Be mindful of:
   - API call frequency
   - Bulk operations
   - User-specific limits

3. **Scope Permissions**: Different scopes require different approval levels:
   - Basic profile access: Usually auto-approved
   - Social posting: May require LinkedIn review
   - Advanced features: Require partner status

## 🔧 Development & Testing

### Local Development

1. Use `http://localhost:8000` as your redirect URI
2. Test OAuth flow in browser
3. Use API documentation at `http://localhost:8000/docs`

### Testing OAuth Flow

```bash
# 1. Start the server
uvicorn main:app --host 0.0.0.0 --port 8000

# 2. Test authorization endpoint
curl http://localhost:8000/auth/linkedin

# 3. Test health check (includes OAuth status)
curl http://localhost:8000/health
```

### Debugging

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Common issues:
- **Invalid redirect URI**: Ensure it matches exactly in LinkedIn app settings
- **Invalid client credentials**: Double-check Client ID and Secret
- **Scope permissions**: Ensure requested scopes are approved for your app

## 🚀 Production Deployment

### Environment Variables
```bash
export LINKEDIN_CLIENT_ID="your_client_id"
export LINKEDIN_CLIENT_SECRET="your_client_secret"
export LINKEDIN_REDIRECT_URI="https://yourdomain.com/auth/linkedin/callback"
export OAUTH_SECRET_KEY="your_secure_secret_key"
```

### Security Checklist
- [ ] Use HTTPS in production
- [ ] Secure secret key storage
- [ ] Implement proper session management
- [ ] Set up monitoring and logging
- [ ] Configure CORS properly
- [ ] Use environment variables for secrets

### Scaling Considerations
- Use Redis or database for token storage
- Implement proper user management
- Add rate limiting
- Monitor API usage
- Set up error alerting

## 📚 Additional Resources

- [LinkedIn OAuth 2.0 Documentation](https://docs.microsoft.com/en-us/linkedin/shared/authentication/authorization-code-flow)
- [LinkedIn API Documentation](https://docs.microsoft.com/en-us/linkedin/)
- [OAuth 2.0 RFC](https://tools.ietf.org/html/rfc6749)

## 🆘 Troubleshooting

### Common Error Messages

1. **"LinkedIn OAuth not configured"**
   - Solution: Set `LINKEDIN_CLIENT_ID` and `LINKEDIN_CLIENT_SECRET`

2. **"Invalid or expired state parameter"**
   - Solution: Ensure state parameter matches between authorization and callback

3. **"Token expired or invalid"**
   - Solution: Re-authenticate the user

4. **"User not authenticated with LinkedIn"**
   - Solution: Complete OAuth flow first

### Getting Help

1. Check the application logs for detailed error messages
2. Verify LinkedIn app configuration
3. Test with LinkedIn's API explorer tools
4. Review LinkedIn's developer documentation

## 🎯 Next Steps

After setting up OAuth, you can:
1. Integrate with existing job search functionality
2. Add more LinkedIn API endpoints
3. Implement user management
4. Add webhook support for real-time updates
5. Create custom LinkedIn integrations

---

**Note**: This OAuth integration provides the foundation for LinkedIn API access. While LinkedIn doesn't offer a public job search API, you can use this authentication system for other LinkedIn features and potentially combine it with approved job-related APIs or services.