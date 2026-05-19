import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def run_tests():
    print("=" * 50)
    print("GREENCARE LOGIN DEBUG TEST")
    print("=" * 50)

    # TEST 1 - Check settings load
    print("\n[TEST 1] Settings:")
    try:
        from app.core.config import settings
        print(f"  SECRET_KEY: {settings.SECRET_KEY[:20]}...")
        print(f"  DATABASE_URL: {settings.DATABASE_URL[:45]}...")
        print(f"  TOKEN_EXPIRE: {settings.ACCESS_TOKEN_EXPIRE_MINUTES} min")
        print("  Settings: OK")
    except Exception as e:
        print(f"  Settings ERROR: {e}")

    # TEST 2 - Check password hashing
    print("\n[TEST 2] Password hashing:")
    try:
        from app.core.security import hash_password, verify_password
        hashed = hash_password("password123")
        verified = verify_password("password123", hashed)
        print(f"  Hash created: {hashed[:35]}...")
        print(f"  Verify works: {verified}")
        if not verified:
            print("  PASSWORD HASHING IS BROKEN!")
    except Exception as e:
        print(f"  Password ERROR: {e}")

    # TEST 3 - Check database connection
    print("\n[TEST 3] Database connection:")
    try:
        from app.db.session import AsyncSessionLocal
        from sqlalchemy import text
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
            print("  Database: CONNECTED OK")
    except Exception as e:
        print(f"  Database ERROR: {e}")

    # TEST 4 - Check users table
    print("\n[TEST 4] Users in database:")
    try:
        from app.db.session import AsyncSessionLocal
        from sqlalchemy import text
        from app.core.security import verify_password
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text("SELECT email, password_hash, role FROM users")
            )
            users = result.fetchall()
            if not users:
                print("  NO USERS FOUND!")
                print("  You need to register a user first!")
            else:
                print(f"  Found {len(users)} user(s):")
                for u in users:
                    print(f"  ---")
                    print(f"  Email: {u.email}")
                    print(f"  Role: {u.role}")
                    print(f"  Hash: {u.password_hash[:35]}...")
                    ok = verify_password("password123", u.password_hash)
                    print(f"  Password123 valid: {ok}")
    except Exception as e:
        print(f"  Users ERROR: {e}")

    # TEST 5 - Check JWT token creation
    print("\n[TEST 5] JWT token creation:")
    try:
        from app.core.security import create_access_token
        token = create_access_token(
            {"sub": "test-uuid", "role": "worker"}
        )
        print(f"  Token created: {token[:40]}...")
        print("  JWT: OK")
    except Exception as e:
        print(f"  JWT ERROR: {e}")

    # TEST 6 - Full login simulation
    print("\n[TEST 6] Full login test:")
    try:
        from app.db.session import AsyncSessionLocal
        from app.services.auth_service import login_user
        async with AsyncSessionLocal() as db:
            tokens, user = await login_user(
                db,
                "test@greencare.com",
                "password123"
            )
            print(f"  Login: SUCCESS!")
            print(f"  User name: {user.name}")
            print(f"  User role: {user.role}")
            print(f"  Access token: {tokens.access_token[:40]}...")
    except Exception as e:
        import traceback
        print(f"  Login FAILED: {e}")
        print("  Full error:")
        traceback.print_exc()

    print("\n" + "=" * 50)
    print("TEST COMPLETE")
    print("=" * 50)

asyncio.run(run_tests())
