import requests
import keyring


def get_jwt_token():
    with open("../secrets/admin_password_hash", "r", encoding="utf-8") as f:
        pwd = f.read().strip()

    resp = requests.post("https://localhost:8051/api/auth/login", 
                        data={"username": "admin", "password": pwd})
    token = resp.json()["access_token"]
    keyring.set_password("rag-kb", "jwt-token", token)
    return token

# token = get_jwt_token()
# keyring.get_password("rag-kb", "jwt-token")
# headers = {"Authorization": f"Bearer {token}"}
# d
