import telebot
import schedule
import time
import threading
import requests
import random
import os
from datetime import datetime, timedelta
from keep_alive import keep_alive
from deep_translator import GoogleTranslator

# --- 設定區 ---
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TARGET_CHAT_ID = os.environ.get('TARGET_CHAT_ID')

bot = telebot.TeleBot(TOKEN)

# --- 功能區 ---
def get_weekly_trending(count=6):
    """
    搜尋過去 7 天內建立且最熱門的專案
    """
    # 這裡改成減去 7 天 (days=7)
    last_week = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    url = f"https://api.github.com/search/repositories?q=created:>{last_week}&sort=stars&order=desc"
    
    try:
        headers = {'User-Agent': 'Python Bot'}
        response = requests.get(url, headers=headers)
        data = response.json()
        
        results = []
        
        if 'items' in data and len(data['items']) > 0:
            # 從前 50 名中隨機挑選，避免每週只報前幾名
            pool_size = min(len(data['items']), 50)
            sample_size = min(pool_size, count)
            
            selected_repos = random.sample(data['items'][:pool_size], sample_size)
            
            for repo in selected_repos:
                original_desc = repo['description'] if repo['description'] else "開發者太懶，沒有寫簡介"
                
                try:
                    translated_desc = GoogleTranslator(source='auto', target='zh-TW').translate(original_desc)
                except Exception as e:
                    print(f"翻譯失敗: {e}")
                    translated_desc = original_desc
                
                results.append({
                    "name": repo['name'],
                    "full_name": repo['full_name'],
                    "desc": translated_desc,
                    "language": repo['language'] if repo['language'] else "通用",
                    "stars": repo['stargazers_count'],
                    "link": repo['html_url']
                })
                
            return results
        return []
    except Exception as e:
        print(f"GitHub API Error: {e}")
        return []

def send_weekly_report():
    if not TARGET_CHAT_ID:
        print("尚未設定 Chat ID")
        return

    print("正在準備週報內容...")
    repos = get_weekly_trending(count=6)
    
    if repos:
        # 標題改成週報
        msg = f"📅 **{datetime.now().strftime('%Y-%m-%d')} 開源神器週報** 🚀\n"
        msg += f"🔥 本週精選 Top {len(repos)} 新專案\n\n"
        
        for i, repo in enumerate(repos, 1):
            msg += (
                f"{i}. 📦 **[{repo['name']}]({repo['link']})**\n"
                f"   🌟 {repo['stars']} Stars | 🔧 {repo['language']}\n"
                f"   📝 {repo['desc']}\n\n"
            )
            
        msg += "🔗 _Powered by GitHub Trending & Render_"

        try:
            bot.send_message(TARGET_CHAT_ID, msg, parse_mode='Markdown', disable_web_page_preview=True)
            print("週報已發送")
        except Exception as e:
            print(f"發送失敗: {e}")
    else:
        print("抓取資料失敗")

# --- 指令區 ---
@bot.message_handler(commands=['start'])
def handle_start(message):
    bot.reply_to(message, f"目前的 Chat ID 是: `{message.chat.id}`", parse_mode='Markdown')

@bot.message_handler(commands=['test'])
def handle_test(message):
    bot.reply_to(message, "🔍 正在生成本週熱門週報 (搜尋範圍：7天)...")
    global TARGET_CHAT_ID
    temp_old_id = TARGET_CHAT_ID
    TARGET_CHAT_ID = message.chat.id
    send_weekly_report()
    TARGET_CHAT_ID = temp_old_id

# --- 排程區 ---
# ⚠️ 重要修改：這裡改成每週一 (Monday) 的 UTC 01:00 (台灣時間早上 09:00) 執行
schedule.every().monday.at("01:00").do(send_weekly_report)

def schedule_checker():
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    keep_alive() 
    threading.Thread(target=schedule_checker).start() 
    bot.infinity_polling()
