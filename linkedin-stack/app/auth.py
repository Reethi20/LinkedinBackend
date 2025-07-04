from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from supabase import create_client, Client
from . import config

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_supabase_client(token: str = Depends(oauth2_scheme)) -> Client:
    """
    Returns a Supabase client authenticated with the user's JWT.
    This ensures all subsequent operations respect RLS policies.
    """
    try:
        client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
        client.postgrest.auth(token)
        return client
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not create authenticated Supabase client: {e}"
        )

def get_user_id_from_token(token: str = Depends(oauth2_scheme)):
    print("--- Attempting to validate token ---")
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        if not token:
            print("--- AUTH FAILED: No token provided. ---")
            raise credentials_exception
        
        print(f"--- Received token: {token[:10]}... ---")
        
        # Create a new client for this validation
        client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
        # Validate the token using Supabase's built-in method
        user = client.auth.get_user(token)
        
        if not user:
            print("--- AUTH FAILED: Token validation returned no user ---")
            raise credentials_exception

        print(f"--- AUTH SUCCESS: User ID {user.user.id} ---")
        return user.user.id
        
    except Exception as e:
        print(f"--- AUTH FAILED: Exception during token validation: {e} ---")
        raise credentials_exception
