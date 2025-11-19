from flask import Flask, redirect, request, jsonify, session, url_for, render_template
import requests,psutil
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
async def get_info_bot():
    name=bot.user.display_name
    server=len(bot.guilds)
    channels = sum(len(g.channels) for g in bot.guilds)
    users = sum((g.member_count or 0) for g in bot.guilds)
    latency = round(bot.latency * 1000)
    memory_usage = psutil.Process().memory_info().rss / 1024**2
    member_install = (bot.application.approximate_user_install_count)
    return name,server,channels,users,latency,memory_usage,member_install
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
    print(user_json)
    session["user"] = user_json
    display_name = user_json.get("global_name") 
    user_data = {
    "id": user_json.get("id"),
    "username": display_name,  
    "email": user_json.get("email"),
    "verified": user_json.get("verified"),
    "avatar": user_json.get("avatar"),      
    "token":access_token
    }
    save_path = "login_complete.json"
    try:
        if os.path.exists(save_path):
            with open(save_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        else:
            existing = []
        if not any(u["id"] == user_data["id"] for u in existing):
            existing.append(user_data)

        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=4)

    except Exception as e:
        print("❌ Lỗi khi lưu login_complete.json:", e)
    return redirect(url_for("profile"))
@app.route("/profile")
def profile():
    user = session.get("user")
    if not user:
        return redirect(url_for("home"))
    avatar_url = "/static/default.png"
    if "avatar_url" in user and isinstance(user["avatar_url"], str) and user["avatar_url"].startswith("http"):
        avatar_url = user["avatar_url"]
    elif user.get("id") and user.get("avatar"):
        avatar = user["avatar"]
        if avatar.startswith("a_"):
            avatar_url = f"https://cdn.discordapp.com/avatars/{user['id']}/{avatar}.gif?size=1024"
        else:
            avatar_url = f"https://cdn.discordapp.com/avatars/{user['id']}/{avatar}.png?size=1024"
    owner_id = 1002018505601863730
    future = asyncio.run_coroutine_threadsafe(get_profile(owner_id), bot.loop)
    try:
        avatar_url2, username = future.result(timeout=10)
    except Exception:
        avatar_url2, username = "/static/default.png", "Unknown"

    user_data = {
        "username": user.get("global_name", "Ẩn danh"),
        "email": user.get("email", "Không có email"),
        "avatar_url": avatar_url,
        "mouseclick": "/static/cursor/vitaclick.png",
        "devavatar": avatar_url2,
        "dev": username,
    }

    data_path = os.path.join(app.static_folder, "notices", "notices.json")
    with open(data_path, "r", encoding="utf-8") as f:
        notices = json.load(f)

    return render_template("profile.html", user=user_data, devavatar=avatar_url2, dev=username, notices=notices,linktouser=f"https://discord.com/users/{user.get("id")}")
@app.route('/help')
def help():
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
    owner_id = 1002018505601863730
    future = asyncio.run_coroutine_threadsafe(get_profile(owner_id), bot.loop)
    try:
        avatar_url2, username = future.result(timeout=10)
    except Exception:
        avatar_url2, username = "/static/default.png", "Unknown"
    user_data = {
        "username": user["username"],
        "email": user.get("email", "Không có email"),
        "avatar_url": avatar_url,
        "mouseclick": "/static/cursor/vitaclick.png",
        "devavatar": avatar_url2,
        "dev": username,
    }

    return render_template("documents.html", user=user_data)
@app.route("/user")
def user():
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
    owner_id = 1002018505601863730
    future = asyncio.run_coroutine_threadsafe(get_profile(owner_id), bot.loop)
    try:
        avatar_url2, username = future.result(timeout=10)
    except Exception:
        avatar_url2, username = "/static/default.png", "Unknown"
    user_data = {
        "username": user["username"],
        "email": user.get("email", "Không có email"),
        "avatar_url": avatar_url,
        "mouseclick": "/static/cursor/vitaclick.png",
        "devavatar": avatar_url2,
        "dev": username,
        "global_name":user.get("global_name"),
        "id": user.get("id"),
        "locale": user.get("locale"),
        "email_verify": "Đã xác minh" if user.get("verified")==True else "Chưa xác minh"  , 
        "premium_type": (
    "Nitro Boost" if user.get("premium_type") == 2
    else "Nitro Basic" if user.get("premium_type") == 1
    else "Không có Nitro"
),

        "mfa_enabled":"Đã xác minh" if user.get("mfa_enabled")==True else "Chưa xác minh" ,

    }
    return render_template("user.html",user=user_data)
@app.route('/bot_info')
def bot_info():
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
        "username": user.get("global_name", "Ẩn danh"),
        "email": user.get("email", "Không có email"),
        "avatar_url": avatar_url,
        "mouseclick": "/static/cursor/vitaclick.png",
    }

    future = asyncio.run_coroutine_threadsafe(get_info_bot(), bot.loop)
    try:
        name, server, channels, users, latency, memory_usage, member_install = future.result(timeout=10)
    except Exception as e:
        print("Lỗi khi lấy thông tin bot:", e)
        name, server, channels, users, latency, memory_usage, member_install = (
            "Unknown", 0, 0, 0, 0, 0, 0
        )

    avatar_url = bot.user.display_avatar.url if bot.user else "/static/default.png"
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    net = psutil.net_io_counters()
    net_sent = round(net.bytes_sent / (1024 * 1024), 2)
    net_recv = round(net.bytes_recv / (1024 * 1024), 2)

    stats = {
        "cpu": cpu,
        "ram": ram,
        "net_sent": net_sent,
        "net_recv": net_recv,
    }

    bot_info = {
        "name": name,
        "server": server,
        "channels": channels,
        "users": users,
        "latency": latency,
        "memory_usage": round(memory_usage, 2),
        "member_install": member_install,
        "avatar_url": avatar_url,
    }

    return render_template("bot.html", user=user_data, bot=bot_info, stats=stats)


@app.route('/login-mock')
def login_mock():
    session['user'] = {
        'username': 'Maria',
        'email': 'maria@vita.com',
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