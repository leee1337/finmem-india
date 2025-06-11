#!/usr/bin/env python3
import os
from pathlib import Path

def get_input(prompt: str, required: bool = False) -> str:
    while True:
        value = input(prompt).strip()
        if value or not required:
            return value
        print("This field is required. Please enter a value.")

def main():
    env_file = Path(".env")
    
    # Check if .env already exists
    if env_file.exists():
        overwrite = input(".env file already exists. Do you want to overwrite it? (y/N): ").lower()
        if overwrite != 'y':
            print("Setup cancelled.")
            return
    
    # Get Google API Key (required)
    google_api_key = get_input("Enter your Google API Key (required): ", required=True)
    
    # Get optional credentials
    print("\nOptional credentials (press Enter to skip):")
    screener_username = get_input("Enter your Screener.in username: ")
    screener_password = get_input("Enter your Screener.in password: ")
    mc_username = get_input("Enter your MoneyControl username: ")
    mc_password = get_input("Enter your MoneyControl password: ")
    nse_api_key = get_input("Enter your NSE API key: ")
    nse_api_secret = get_input("Enter your NSE API secret: ")
    
    # Create .env file
    env_content = f"""# Required
GOOGLE_API_KEY={google_api_key}

# Optional - for Screener.in integration
SCREENER_USERNAME={screener_username}
SCREENER_PASSWORD={screener_password}

# Optional - for MoneyControl integration
MC_USERNAME={mc_username}
MC_PASSWORD={mc_password}

# Optional - for NSE API integration
NSE_API_KEY={nse_api_key}
NSE_API_SECRET={nse_api_secret}
"""
    
    # Write to .env file
    env_file.write_text(env_content)
    
    # Set file permissions to be readable only by the owner
    os.chmod(env_file, 0o600)
    
    print("\nEnvironment variables have been set up successfully!")
    print("Note: The .env file has been created with read/write permissions for the owner only.")

if __name__ == "__main__":
    main() 