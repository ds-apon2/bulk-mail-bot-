import asyncio
import requests
import os

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update
)

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes
)

# =========================
# CONFIG
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("API_KEY")
CHAT_ID = int(os.getenv("CHAT_ID"))
OWNER_ID = int(os.getenv("OWNER_ID"))
PRODUCT_ID = 11
CHECK_INTERVAL = 30
def is_owner(user_id):
    return user_id == OWNER_ID

# =========================
# GLOBALS
# =========================

MONITOR_ENABLED = False
last_stock_state = False

# =========================
# API FUNCTIONS
# =========================

def get_stock():
    url = f"https://bulkmail.shop/api/v2/stock/{PRODUCT_ID}"

    r = requests.get(url, timeout=30)
    r.raise_for_status()

    data = r.json()

    if not data.get("success"):
        return None

    return data["data"]


def buy_product(product_id):
    url = "https://bulkmail.shop/api/v2/orders"

    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "product_id": product_id,
        "quantity": 1
    }

    r = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=30
    )

    return r.json()

# =========================
# COMMANDS
# =========================

async def boton(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return
    global MONITOR_ENABLED

    MONITOR_ENABLED = True

    await update.message.reply_text(
        "✅ Stock Monitor Enabled"
    )


async def botoff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return
    global MONITOR_ENABLED

    MONITOR_ENABLED = False

    await update.message.reply_text(
        "⛔ Stock Monitor Disabled"
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return
    global MONITOR_ENABLED

    txt = "🟢 ON" if MONITOR_ENABLED else "🔴 OFF"

    await update.message.reply_text(
        f"Monitor Status: {txt}"
    )

# =========================
# STOCK MONITOR
# =========================

async def stock_monitor(app):
    global last_stock_state
    global MONITOR_ENABLED

    while True:

        if not MONITOR_ENABLED:
            await asyncio.sleep(10)
            continue

        try:
            stock = get_stock()
            print(stock)
            
            if stock:
                count = stock["stock_count"]
                name = stock["product_name"]

                current_state = count >= 5

                if current_state and not last_stock_state:

                    keyboard = InlineKeyboardMarkup([
                        [
                            InlineKeyboardButton(
                                "🛒 Buy 1",
                                callback_data=f"buy_{PRODUCT_ID}"
                            )
                        ]
                    ])

                    await app.bot.send_message(
                        chat_id=CHAT_ID,
                        text=(
                            f"🚀 Stock Available!\n\n"
                            f"Product: {name}\n"
                            f"Product ID: {PRODUCT_ID}\n"
                            f"Stock: {count}"
                        ),
                        reply_markup=keyboard
                    )

                last_stock_state = current_state

        except Exception as e:
            print("Stock Error:", e)

        await asyncio.sleep(CHECK_INTERVAL)

# =========================
# BUTTON HANDLER
# =========================

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    if not is_owner(query.from_user.id):
        await query.answer(
            "Not allowed",
            show_alert=True
        )
        return

    await query.answer()

    data = query.data

    if data.startswith("buy_"):
      
        product_id = int(data.split("_")[1])

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "✅ Confirm",
                    callback_data=f"confirm_{product_id}"
                ),
                InlineKeyboardButton(
                    "❌ Cancel",
                    callback_data="cancel"
                )
            ]
        ])

        await query.edit_message_reply_markup(
            reply_markup=keyboard
        )

    elif data.startswith("confirm_"):

        product_id = int(data.split("_")[1])

        await query.edit_message_text(
            "⏳ Purchasing..."
        )

        try:
            result = buy_product(product_id)

            if result.get("success"):

                order = result["data"]

                stock_items = "\n".join(
                    order.get("stock_items", [])
                )

                await query.edit_message_text(
                    f"✅ Purchase Successful\n\n"
                    f"Order: {order['order_number']}\n"
                    f"Quantity: {order['quantity']}\n"
                    f"Amount: {order['total_amount']}\n"
                    f"Status: {order['status']}\n\n"
                    f"{stock_items}"
                )

            else:
                await query.edit_message_text(
                    f"❌ Purchase Failed\n\n"
                    f"{result.get('error', 'Unknown Error')}"
                )

        except Exception as e:
            await query.edit_message_text(
                f"❌ Error\n\n{e}"
            )

    elif data == "cancel":

        await query.edit_message_text(
            "❌ Purchase Cancelled"
        )

# =========================
# STARTUP
# =========================

async def post_init(app):
    asyncio.create_task(
        stock_monitor(app)
    )

# =========================
# MAIN
# =========================

def main():

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    app.add_handler(
        CommandHandler("boton", boton)
    )

    app.add_handler(
        CommandHandler("botoff", botoff)
    )

    app.add_handler(
        CommandHandler("status", status)
    )

    app.add_handler(
        CallbackQueryHandler(callback_handler)
    )

    print("Bot Started...")
    app.run_polling()


if __name__ == "__main__":
    main()
