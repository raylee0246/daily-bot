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

# --- 智慧設定 ---
# 1. 優先顯示的平台/領域標籤 (讓使用者一眼看出適用平台)
PRIORITY_TAGS = [
    'android', 'ios', 'flutter', 'react-native', 'mobile', # 行動端
    'windows', 'macos', 'linux', 'desktop', 'electron',   # 桌面端
    'web', 'react', 'vue', 'nextjs', 'node', 'django',    # 網頁端
    'docker', 'kubernetes', 'devops',                     # 維運
    'ai', 'machine-learning', 'chatgpt', 'llm', 'bot'     # AI
]

# 2. 語言對應的 Emoji
LANG_ICONS = {
    'Python': '🐍', 'JavaScript': '🟨', 'TypeScript': '📘', 'Java': '☕',
    'Go': '🐹', 'Rust': '🦀', 'C++': 'Ⓜ️', 'C#': '#️⃣', 
    'Swift': '🐦', 'Kotlin': '📱', 'Dart': '🎯', 'PHP': '🐘',
    'HTML': '🌐', 'CSS': '🎨', 'Vue': '🟢', 'Shell': '🐚'
}

# --- 功能區 ---
def get_lang_emoji(language):
    """根據語言回傳對應的 Emoji，沒有就回傳通用圖示"""
    return LANG_ICONS.get(language, '🔧')

def get_smart_tags(repo_topics, language):
    """
    智慧篩選標籤：優先抓取「平台」相關的 Tag
    """
    if not repo_topics:
        return language if language else "通用工具"
    
    # 1. 先找出是否有在 PRIORITY_TAGS 裡的標籤
    important_tags = [tag for tag in repo_topics if tag.lower() in PRIORITY_TAGS]
    
    # 2. 剩下的標籤
    other_tags = [tag for tag in repo_topics if tag.lower() not in PRIORITY_TAGS]
    
    # 3. 組合：優先顯示重要標籤，如果不夠湊滿 3 個，再拿剩下的補
    final_tags = important_tags + other_tags
    
    # 取前 3 個並用逗號連接
    return ", ".join(final_tags[:3])

def get_weekly_trending(count=6):
    # 搜尋過去 7 天 (週報)
    last_week = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    url = f"https://api.github.com/search/repositories?q=created:>{last_week}&sort=stars&order=desc"
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Weekly-Bot)'} # 偽裝成瀏覽器以免被擋
        response = requests.get(url, headers=headers, timeout=10) # 設定超時
        data = response.json()
        
        results = []
        
        if 'items' in data and len(data['items']) > 0:
            pool_size = min(len(data['items']), 50)
            sample_size = min(pool_size, count)
            selected_repos = random.sample(data['items'][:pool_size], sample_size)
            
            translator = GoogleTranslator(source='auto', target='zh-TW')
            
            for repo in selected_repos:
                # 1. 簡介處理
                original_desc = repo['description'] if repo['description'] else "無簡介"
                try:
                    translated_desc = translator.translate(original_desc)
                except Exception:
                    translated_desc = original_desc
                
                # 截斷過長簡介
                if len(translated_desc) > 90:
                    translated_desc = translated_desc[:87] + "..."

                # 2. 標籤與圖示處理
                lang = repo['language'] if repo['language'] else "Other"
                icon = get_lang_emoji(lang)
                smart_tags = get_smart_tags(repo.get('topics', []), lang)

                results.append({
                    "name": repo['name'],
                    "desc": translated_desc,
                    "info_line": f"{icon} {lang}  •  🏷️ {smart_tags}", # 整合顯示行
                    "stars": f"{repo['stargazers_count']:,}",
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

    print("正在準備旗艦級週報...")
    repos = get_weekly_trending(count=6)
    
    if repos:
        today = datetime.now().strftime('%m/%d')
        # 標題設計：更簡約有力
        msg = f"🚀 **GitHub 開源週報** ({today})\n"
        msg += f"🔥 本週最火熱的 {len(repos)} 個新專案\n"
        msg += "━━━━━━━━━━━━━━━━━━\n\n"
        
        for i, repo in enumerate(repos, 1):
            msg += (
                f"**{i}. [{repo['name']}]({repo['link']})**\n"
                f"`⭐️ {repo['stars']}`  `{repo['info_line']}`\n" # 數據列灰底顯示
                f"> {repo['desc']}\n\n"
            )
            
        msg += "━━━━━━━━━━━━━━━━━━\n"
        msg += "🤖 _Powered by Auto-Bot_"

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
    bot.reply_to(message, f"Chat ID: `{message.chat.id}`", parse_mode='Markdown')

@bot.message_handler(commands=['test'])
def handle_test(message):
    bot.reply_to(message, "🎨 正在生成「旗艦版」週報 (智慧標籤+圖示)，請稍等...")
    global TARGET_CHAT_ID
    temp_old_id = TARGET_CHAT_ID
    TARGET_CHAT_ID = message.chat.id
    send_weekly_report()
    TARGET_CHAT_ID = temp_old_id

# --- 排程區 ---
# 每週一 早上 09:00 (UTC 01:00)
schedule.every().monday.at("01:00").do(send_weekly_report)

def schedule_checker():
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    keep_alive() 
    threading.Thread(target=schedule_checker).start() 
    bot.infinity_polling()
