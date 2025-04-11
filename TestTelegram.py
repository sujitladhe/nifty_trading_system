import requests

def send_telegram_message(bot_token, chat_id, message):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {'chat_id': chat_id, 'text': message}
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        print("Telegram message sent successfully!")
    else:
        print(f"Failed to send message: {response.text}")

if __name__ == "__main__":
    bot_token = '7304000359:AAFkzdTKOFkoI1ucgWXZ-rH4fYB8cnWbQhc'  # Replace with your token
    chat_id = '669766342'     # Replace with your chat ID
    send_telegram_message(bot_token, chat_id, "Test message from Nifty Trading System")