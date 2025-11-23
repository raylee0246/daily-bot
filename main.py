import telebot
import schedule
import time
import threading
import requests
import random
import os
from datetime import datetime, timedelta
from keep_alive import keep_alive # 引入防睡機制

# --- 設定區 ---
# 從雲端環境變數讀取 Token，如果讀不到(在本機測試時)則報錯或需手動填入
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TARGET_CHAT_ID = os.environ.get('TARGET_CHAT_ID')

bot = telebot.TeleBot(TOKEN)

# --- 功能區 ---
def get_github_trending():
    # 搜尋過去 24 小時的熱門專案
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    url = f"https://api.github.com/search/repositories?q=created:>{yesterday}&sort=stars&order=desc"
    try:
        headers = {'User-Agent': 'Python Bot'}
        response = requests.get(url, headers=headers)
        data = response.json()
        if 'items' in data and len(data['items']) > 0:
            # 取前 10 名隨機一個
            return random.choice(data['items'][:10])
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def send_daily_github():
    if not TARGET_CHAT_ID:
        print("尚未設定 Chat ID")
        return

    repo = get_github_trending()
    if repo:
        desc = repo['description'] if repo['description'] else "無簡介"
        lang = repo['language'] if repo['language'] else "通用"
        msg = (
            f"🚀 **今日 GitHub 熱門** 🚀\n\n"
            f"📦 **{repo['full_name']}**\n"
            f"🌟 Stars: {repo['stargazers_count']}\n"
            f"🔧 語言: {lang}\n"
            f"📝 {desc}\n\n"
            f"🔗 [查看專案]({repo['html_url']})"
        )
        try:
            bot.send_message(TARGET_CHAT_ID, msg, parse_mode='Markdown')
            print("已發送")
        except Exception as e:
            print(f"發送失敗: {e}")

# --- 指令區 ---
@bot.message_handler(commands=['start'])
def handle_start(message):
    bot.reply_to(message, f"你的 Chat ID 是: `{message.chat.id}`", parse_mode='Markdown')

@bot.message_handler(commands=['test'])
def handle_test(message):
    bot.reply_to(message, "🔍 搜尋中...")
    # 測試時臨時使用發送者的 ID
    global TARGET_CHAT_ID
    temp_old_id = TARGET_CHAT_ID
    TARGET_CHAT_ID = message.chat.id
    send_daily_github()
    TARGET_CHAT_ID = temp_old_id # 還原

# --- 排程區 ---
# 注意：Render 伺服器時間通常是 UTC (+0)。
# 台灣是 UTC+8。如果你要在台灣早上 9 點發送，這裡要設定成 "01:00" (凌晨1點)
schedule.every().day.at("01:00").do(send_daily_github)

def schedule_checker():
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    keep_alive() # 啟動 Web Server
    threading.Thread(target=schedule_checker).start() # 啟動排程
    bot.infinity_polling() # 啟動機器人
