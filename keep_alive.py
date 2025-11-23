from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "I am alive! 機器人運作中。"

def run():
    # Render 會自動分配 Port，或者預設 0.0.0.0
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()
