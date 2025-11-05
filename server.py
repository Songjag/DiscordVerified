from flask import Flask, redirect, request, jsonify, session, url_for, render_template
import requests
import os
import threading
import asyncio,json
from discord import Client, Intents
from dotenv import load_dotenv
from datetime import datetime
load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)

CLIENT_ID = os.getenv("client_id")
CLIENT_SECRET = os.getenv("client_secret")
REDIRECT_URI = os.getenv("REDIRECT_URI")
DISCORD_API_BASE = os.getenv("DISCORD_API_BASE", "https://discord.com/api")
OAUTH_SCOPE = os.getenv("OAUTH_SCOPE", "identify email")
TOKEN = os.getenv("token")

intents = Intents.default()
bot = Client(intents=intents)

async def get_profile(user_id):
    try:
        user = await bot.fetch_user(user_id)
        if user.avatar and user.avatar.is_animated():
            avatar_url = f"https://cdn.discordapp.com/avatars/{user.id}/{user.avatar.key}.gif?size=1024"
        else:
            avatar_url = user.display_avatar.url
        return avatar_url, user.display_name
    except Exception as e:
        print("Lỗi khi lấy user:", e)
        return "/static/default.png", "Unknown"

@app.route("/")
def home():
    owner_id = 1002018505601863730
    future = asyncio.run_coroutine_threadsafe(get_profile(owner_id), bot.loop)
    try:
        avatar_url, username = future.result(timeout=10)
    except Exception as e:
        avatar_url, username = "/static/default.png", "Unknown"
    return render_template("register.html", user=username, avatar=avatar_url)
@app.route("/login")
def login():
    discord_auth_url = (
        f"{DISCORD_API_BASE}/oauth2/authorize"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope={OAUTH_SCOPE.replace(' ', '%20')}"
    )
    return redirect(discord_auth_url)

@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return "Không có mã xác minh từ Discord!"

    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "scope": OAUTH_SCOPE,
    }

    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    token_response = requests.post(f"{DISCORD_API_BASE}/oauth2/token", data=data, headers=headers)
    token_json = token_response.json()

    if "access_token" not in token_json:
        return jsonify({"error": "Không thể lấy token", "details": token_json})

    access_token = token_json["access_token"]
    user_response = requests.get(
        f"{DISCORD_API_BASE}/users/@me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    user_json = user_response.json()
    session["user"] = user_json

    return redirect(url_for("profile"))
@app.route("/profile")
def profile():
    user = session.get("user")
    if not user:
        return redirect(url_for("home"))
    avatar = user.get("avatar")
    if avatar and avatar.startswith("a_"):
        avatar_url = f"https://cdn.discordapp.com/avatars/{user['id']}/{avatar}.gif?size=1024"
    elif avatar:
        avatar_url = f"https://cdn.discordapp.com/avatars/{user['id']}/{avatar}.png?size=1024"
    else:
        avatar_url = "/static/default.png"

    user_data = {
        "username": user["username"],
        "email": user.get("email", "Không có email"),
        "avatar_url": avatar_url,
        "mouseclick":"/static/cursor/vitaclick.png"
    }

    return render_template("profile.html", user=user_data)
@app.route('/login-mock')
def login_mock():
    session['user'] = {
        'username': 'Maria',
        'email': 'dev@example.com',
        'avatar_url': "a_e4b2177712d93e08aa25d14b8e0deb50"
    }
    return redirect(url_for('profile'))
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("home"))
def run_bot():
    asyncio.run(bot.start(TOKEN))

if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    app.run(debug=True,host='0.0.0.0')