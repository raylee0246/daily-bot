import telebot
import schedule
import time
import threading
import requests
import random
import os
from datetime import datetime, timedelta
from keep_alive import keep_alive
from deep_translator import GoogleTranslator # 引入翻譯工具

# --- 設定區 ---
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TARGET_CHAT_ID = os.environ.get('TARGET_CHAT_ID')

bot = telebot.TeleBot(TOKEN)

# --- 功能區 ---
def get_github_trending():
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    url = f"https://api.github.com/search/repositories?q=created:>{yesterday}&sort=stars&order=desc"
    try:
        headers = {'User-Agent': 'Python Bot'}
        response = requests.get(url, headers=headers)
        data = response.json()
        
        if 'items' in data and len(data['items']) > 0:
            repo = random.choice(data['items'][:10]) # 取前 10 名隨機一個
            
            # 處理簡介與翻譯
            original_desc = repo['description'] if repo['description'] else "開發者太懶，沒有寫簡介"
            try:
                # 自動翻譯成繁體中文 (zh-TW)
                translated_desc = GoogleTranslator(source='auto', target='zh-TW').translate(original_desc)
            except Exception as e:
                print(f"翻譯失敗: {e}")
                translated_desc = original_desc # 如果翻譯失敗，就用原文
            
            return {
                "name": repo['name'],
                "full_name": repo['full_name'],
                "desc": translated_desc,
                "language": repo['language'] if repo['language'] else "通用",
                "stars": repo['stargazers_count'],
                "link": repo['html_url']
            }
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
        msg = (
            f"🚀 **今日 GitHub 熱門** 🚀\n\n"
            f"📦 **{repo['full_name']}**\n"
            f"🌟 Stars: {repo['stars']}\n"
            f"🔧 語言: {repo['language']}\n"
            f"📝 **簡介**：{repo['desc']}\n\n"
            f"🔗 [查看專案]({repo['link']})"
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
    bot.reply_to(message, "🔍 搜尋熱門專案並翻譯中... 請稍等")
    # 測試時臨時使用發送者的 ID
    global TARGET_CHAT_ID
    temp_old_id = TARGET_CHAT_ID
    TARGET_CHAT_ID = message.chat.id
    send_daily_github()
    TARGET_CHAT_ID = temp_old_id # 還原

# --- 排程區 ---
schedule.every().day.at("01:00").do(send_daily_github)

def schedule_checker():
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    keep_alive() 
    threading.Thread(target=schedule_checker).start() 
    bot.infinity_polling()
