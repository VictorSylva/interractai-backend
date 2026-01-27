import os
import asyncio
from aiosmtplib import send
from dotenv import load_dotenv
from email.message import EmailMessage

# Force reload dev env
os.environ["ENV"] = "dev"
env_file = ".env.dev"
print(f"Loading {env_file}...")
load_dotenv(env_file, override=True)

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = os.getenv("SMTP_PORT")
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

print(f"HOST: {SMTP_HOST}")
print(f"PORT: {SMTP_PORT}")
print(f"USER: {SMTP_USER}")
print(f"PASS: {'*' * len(SMTP_PASSWORD) if SMTP_PASSWORD else 'MISSING'}")

async def test_smtp(pwd_to_try, label):
    print(f"\n--- Testing with {label} ---")
    msg = EmailMessage()
    msg["From"] = SMTP_USER
    msg["To"] = SMTP_USER
    msg["Subject"] = f"InterractAI SMTP Test ({label})"
    msg.set_content(f"Testing SMTP with {label}")

    try:
        await send(
            msg,
            hostname=SMTP_HOST,
            port=int(SMTP_PORT),
            username=SMTP_USER,
            password=pwd_to_try,
            use_tls=False,
            start_tls=True,
            timeout=10
        )
        print(f"SUCCESS: {label} worked!")
        return True
    except Exception as e:
        print(f"FAILED with {label}: {str(e)}")
        return False

async def main():
    global SMTP_USER
    if not SMTP_USER or not SMTP_PASSWORD:
        print("ERROR: Credentials missing in env")
        return

    print(f"DEBUG: Checking SMTP_USER: {SMTP_USER}")
    
    # Try 1: As provided in env
    success = await test_smtp(SMTP_PASSWORD, "original from env")
    
    # Try 2: Without any spaces
    if not success:
        no_spaces = SMTP_PASSWORD.replace(" ", "")
        if no_spaces != SMTP_PASSWORD:
            print("\nRetrying without spaces...")
            success = await test_smtp(no_spaces, "spaces removed")
    
    # Try 3: With spaces added in blocks of 4 (common Gmail format)
    if not success:
        if len(SMTP_PASSWORD) == 16 and " " not in SMTP_PASSWORD:
            with_spaces = f"{SMTP_PASSWORD[0:4]} {SMTP_PASSWORD[4:8]} {SMTP_PASSWORD[8:12]} {SMTP_PASSWORD[12:16]}"
            print("\nRetrying with standard 4x4 spaces...")
            await test_smtp(with_spaces, "spaces added (4x4)")

    # Try 4: Port 465 (SSL)
    if not success:
        print("\nRetrying with Port 465 (SSL)...")
        try:
            msg = EmailMessage()
            msg["From"] = SMTP_USER
            msg["To"] = SMTP_USER
            msg["Subject"] = "Test Port 465"
            msg.set_content("Test Port 465")
            
            pwd_to_use = SMTP_PASSWORD.replace(" ", "")
            await send(
                msg,
                hostname=SMTP_HOST,
                port=465,
                username=SMTP_USER,
                password=pwd_to_use,
                use_tls=True,
                start_tls=False,
                timeout=10
            )
            print("SUCCESS: Port 465 worked!")
            success = True
        except Exception as e:
            print(f"FAILED with Port 465: {str(e)}")

    # Try 5: Corrected Typo
    if not success and "interacai" in SMTP_USER:
        print("\n--- DETECTED POTENTIAL EMAIL TYPO ---")
        corrected_email = SMTP_USER.replace("interacai", "interactai")
        print(f"Trying with corrected email: {corrected_email}")
        
        ORIG_USER = SMTP_USER
        SMTP_USER = corrected_email
        
        # Try without spaces first as that's most likely for App Passwords
        pwd_no_spaces = SMTP_PASSWORD.replace(" ", "")
        success = await test_smtp(pwd_no_spaces, "corrected email + no spaces")
        
        if success:
            print(f"!!! FOUND IT !!! The correct email is {corrected_email}")
            return
        
        SMTP_USER = ORIG_USER # Revert

    if not success:
        print("\n--- FINAL DIAGNOSIS ---")
        print("1. Please verify the spelling of your email: " + SMTP_USER)
        print("2. Ensure 2-Factor Authentication is ON for this Google account.")
        print("3. Ensure you are using an 'App Password', NOT your regular Gmail password.")

if __name__ == "__main__":
    asyncio.run(main())
