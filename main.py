import config
from telebot import TeleBot, util, apihelper, types
from database import User, BotSetting, Permission
import keyboards
from datetime import datetime
import re
from telebot.custom_filters import ForwardFilter
import sched
import time
import threading
from flask import Flask


apihelper.ENABLE_MIDDLEWARE = True
bot = TeleBot(config.TOKEN, parse_mode="HTML")
app = Flask(__name__)
markups = {}
event = sched.scheduler(time.time, time.sleep)


def user_joined(user_id: int, channel_id):
    try:
        user = bot.get_chat_member(channel_id, user_id)
        if user.status in ['administrator', 'member', 'creator']:
            return True
        else:
            return False
    except:
        return True


def get_not_joined(user_id) -> list:
    channels = []
    setting = BotSetting()
    force_channels = setting.channels
    for channel in force_channels:
        if channel.get('force_join'):
            joined = user_joined(user_id, int(channel['id']))
            if not joined:
                username = '◽ @'+bot.get_chat(int(channel['id'])).username
                if username is None:
                    username = "◽ "+bot.get_chat(int(channel['id'])).invite_link
                channels.append(username)
    
    return channels


def get_message_channels() -> list:
    ls = []
    message_channels = BotSetting().channels
    for channel in message_channels:
        if channel.get('send_message'):
            ls.append(int(channel['id']))
    return ls


@bot.middleware_handler(['message'])
def get_updates(self, message):
    if message.chat.type == 'private':
        user = User(message.from_user.id)
        if not user.exist():
            return
        if user.status == 'banned': 
            message.content_type = 'banned_user'

        else:
            setting = BotSetting()
            force_channels = setting.channels
            for channel in force_channels:
                
                if not channel.get('force_join'): return
                if not user_joined(message.from_user.id, channel['id']):
                    message.content_type = 'not_joined'
                    break
            

@bot.message_handler(commands=["start"], chat_types=["private"])
def start(message: types.Message):

    user_id = message.from_user.id
    bot.delete_state(user_id)
    db_user = User(user_id)
    
    if not db_user.exist():
        User.insert(user_id)
    text = """Welcome 👋 Here you can start a new investment!

💵 We provide one investment plan, which is able to offer you the best profit!.
"""
    bot.send_message(user_id, text, reply_markup=keyboards.main_keyboard(User(user_id)))


@bot.message_handler(content_types=['not_joined'])
def not_joined(message: types.Message):
    usernames = "\n\n".join(get_not_joined(message.from_user.id))
    bot.send_message(message.from_user.id, f"Dear user you need to join our channel(s) / group(s)\n{usernames}")


@bot.message_handler(commands=['wallets'], chat_types=['private'], is_admin=True)
def see_wallets(message: types.Message):
    user_id = message.from_user.id
    user = User(user_id)

    if not user.can(Permission.MANAGE_BOT): return
    payeer = BotSetting().payeer
    usdt = BotSetting().usdt
    text = "✅ <b>PAYEER</b>:\n"
    for pay in payeer:
        text +="  ◽ <code>%s</code>\n" % (pay)
    text += "\n\n✅ <b>USDT</b>: \n"
    for usd in usdt:
        text +="  ◽ <code>%s</code>\n" % (usd)

    bot.send_message(user_id, text)


@bot.message_handler(commands=['add_payeer_wallet'], chat_types=['private'], is_deeplink=True, is_admin=True)
def add_payeer_wallet(message: types.Message):
    wallet = message.text.split()[1]
    payeer = BotSetting().payeer
    payeer.append(wallet)
    BotSetting().update(payeer=payeer)
    bot.send_message(message.from_user.id, "✅ <b>PAYEER</b> wallet successfully added!")


@bot.message_handler(commands=['add_usdt_wallet'], chat_types=['private'], is_deeplink=True, is_admin=True)
def add_usdt_wallet(message: types.Message):
    wallet = message.text.split()[1]
    usdt = BotSetting().usdt
    usdt.append(wallet)
    BotSetting().update(usdt=usdt)
    bot.send_message(message.from_user.id, "✅ <b>USDT</b> wallet successfully added!")


@bot.message_handler(commands=['remove_payeer_wallet'], chat_types=['private'], is_deeplink=True, is_admin=True)
def remove_payeer_wallet(message: types.Message):
    user_id = message.from_user.id
    user = User(user_id)
    if not user.can(Permission.MANAGE_BOT): return
    
    payeer = BotSetting().payeer
    wallet = message.text.split()[1]
    if wallet in payeer:
        payeer.remove(wallet)
        BotSetting().update(payeer=payeer)
        bot.send_message(message.from_user.id, "✅ <b>PAYEER</b> wallet successfully removed!")


@bot.message_handler(commands=['remove_usdt_wallet'], chat_types=['private'], is_deeplink=True, is_admin=True)
def remove_usdt_wallet(message: types.Message):
    user_id = message.from_user.id
    user = User(user_id)
    if not user.can(Permission.MANAGE_BOT): return
    wallet = message.text.split()[1]
    usdt = BotSetting().usdt
    if wallet in usdt:
        usdt.remove(wallet)
        BotSetting().update(usdt=usdt)
        bot.send_message(message.from_user.id, "✅ <b>USDT</b> wallet successfully removed!")


@bot.message_handler(commands=['ban'], is_deeplink=True, chat_types=['private'], is_admin=True)
def ban_user(message: types.Message):
    try:
        user_id = message.text.split()[-1]
        user_id = int(user_id)
    except: return

    user = User(message.from_user.id)
    victim = User(user_id)

    if not user.can(Permission.BAN_USERS): return
    if victim.status == 'admin': return
    if user.status == 'moderator' and victim.status == 'moderator': return

    if victim.status is not None:     
        if victim.status != 'banned':    
            user = bot.get_chat(int(user_id))
            if victim.status == 'moderator':
                victim.update(permission=Permission.USER_PERMISSION)
            victim.update(status='banned')
            text = f"<b>✅ User <a href='tg://user?id={user.id}'>{user.id}</a> has been banned.</b>"
            bot.send_message(message.chat.id, text)
        else:
            user = bot.get_chat(int(user_id))
            text = f"<b>✅ User <a href='tg://user?id={user.id}'>{user.id}</a> has already banned.</b>"
            bot.send_message(message.chat.id, text)

    else:
        try:
            user = bot.get_chat(int(user_id))
            text = f'''<b>❌ Sorry user <a href='tg://user?id={user.id}'>{user.id}</a> is not a member of this bot.</b>"
                        '''
            bot.send_message(message.chat.id, text)
        except:
            pass


@bot.message_handler(commands=['unban'], is_deeplink=True, chat_types=['private'], is_admin=True)
def unban_user(message: types.Message):
    try:   
        user_id = message.text.split()[-1]
        user_id = int(user_id)
    except: return
    user = User(message.from_user.id)
    victim = User(user_id)

    if not user.can(Permission.BAN_USERS): return
    if victim.status == 'admin': return

    if user.status is not None:
        if user.status == 'banned':
            user = bot.get_chat(int(user_id))
            text = f'''<b>✅ User <a href='tg://user?id={user.id}'>{user.id}</a> has been unbanned.</b>'''
            bot.send_message(message.chat.id, text)
            victim.update(status='user')

        else:
            user = bot.get_chat(int(user_id))
            text = f'''<b>❌ User <a href='tg://user?id={user.id}'>{user.id}</a> is not banned.</b>"
                    '''
            bot.send_message(message.chat.id, text)
            

@bot.message_handler(state='*', func=lambda msg: msg.text == "❌ Cancel")
def on_cancel_state(message: types.Message):
    user_id = message.from_user.id
    state = bot.get_state(user_id)

    if state in ['invest', 'screenshoot']:
        message.text = "💰 Invest"
    else:
        return start(message)
    bot.delete_state(user_id)
    return on_main_keyboards(message)


@bot.message_handler(func=lambda msg: msg.text in keyboards.main_keyboard_texts, chat_types=['private'])
def on_main_keyboards(message):

    user_id = message.from_user.id
    user = User(user_id)
    text = message.text
    bot.delete_state(user_id)

    if text == "💰 Invest":
        btns = ["💸 150%, ~ After 24 hours", "💸 200%, ~ After 3 days", "💸 300%, ~ After 7 days", "🔙  Back"]
        btn = types.ReplyKeyboardMarkup(row_width=1)
        btn.add(*[types.KeyboardButton(text) for text in btns])
        bot.send_message(user_id, "<b>Chose one option:</b>", reply_markup=btn)
    
    elif text == "🤑 $20 Offer":
        pass

    elif text == "💳 Withdraw":
        if user.balance > 0:
            text = f"💵<b>Current balance</b>: <code>${user.balance}</code>\n\n❓<i>How much do you want to withdraw ?</i>"
            bot.send_message(user_id, text, reply_markup=keyboards.cancel())
            bot.set_state(user_id, "withdraw")
        else:
            bot.send_message(user_id, "❌ You don't have enough funds, please charge your account first.")

    elif text == "📈 Stats":
        users = len(User.find())
        invests = sum([user['invest'] for user in User.find()])
        withdraws = sum([user['withdraw'] for user in User.find()])
        msg = "👤 <b>Total users</b>: {0}\n\n💰 <b>Total Invest</b>: ${1}\n\n💳 <b>Total Withdraw</b>: ${2}".format(users, invests, withdraws)
        bot.send_message(user_id, msg)

    elif text == "👤 Account":
        msg = """<b>Your Account</b>
--------------------\n
💵 <b>Current Balance</b>: ${0}
💰 <b>Total Invests</b>: ${1}
💳 <b>Total Withdraws</b>: ${2}\n
📆 <i>Joined {3}</i>""".format(user.balance, user.invest, user.withdraw, user.date)
        bot.send_message(user_id, msg, reply_markup=keyboards.profile_btn())

    elif text == "📋 Info":
        msg = """*📌 Condition: ✅ Payment

🔰 Double your balance is the simplest way to double your assets.
After that, the investment plan will be completed automatically.

📊 Our investment plan: + 200% + 400% + 1000%

🟡 Minimum investment: $50

🟡 Minimum withdrawal: Withdrawal arrives when you withdraw your plan

🟡 Maximum investment: $15,000

🌟 Our payment system is instant and fully automatic

📌 After making a deposit, it will be automatically added to your account after a few minutes. """
        bot.send_message(user_id, msg)

    else:
        msg = """<b>Hello 👋</b>

<i>If you have a question or problem with the deposit or withdrawal system, you can contact the administrator</i>
@alswerasy 
"""
        bot.send_message(user_id, msg)


@bot.message_handler(func=lambda msg: msg.text in keyboards.invest_keyboard_texts, chat_types=['private'])
def on_invest(message: types.Message):
    user_id = message.from_user.id
    text = message.text
    bot.delete_state(user_id)
    msg = '''The minimum investment is ${} 💰
The maximum investment is ${} 💰

⏱ {}% profit will be deposited within {}⌛️

The balance is added to the account after depositing

⚠️ If you send less than {} USD, your deposit will be rejected!

✅ Send the amount you want to invest'''
    if text == "💸 150%, ~ After 24 hours":
        msg = msg.format(30, 2000, 150, "24 hours", 30)
        _min, _max, req_hr, per = 30, 2000, 24, 150
        bot.send_message(user_id, msg, reply_markup=keyboards.cancel())
    elif text == "💸 200%, ~ After 3 days":
        msg = msg.format(50, 4000, 200, "3 days", 50)
        _min, _max, req_hr, per = 50, 4000, 24 * 3, 200
        bot.send_message(user_id, msg, reply_markup=keyboards.cancel())
    elif text == "💸 300%, ~ After 7 days":
        msg = msg.format(100, 10000, 300, "7 days", 100)
        _min, _max, req_hr, per = 100, 10000, 24*7, 300
        bot.send_message(user_id, msg, reply_markup=keyboards.cancel())
    else:
        return start(message)

    bot.set_state(user_id, "invest")
    with bot.retrieve_data(user_id) as data:
        data['minimum'] = _min
        data['maximum'] = _max
        data['hours'] = req_hr
        data['percentage'] = per


@bot.message_handler(state='invest')
def on_invest(message: types.Message):
    user_id = message.from_user.id
    with bot.retrieve_data(user_id) as data:
        if not message.text.isdigit():
            return bot.send_message(user_id, "Number required!")
        elif int(message.text) > data['maximum'] or int(message.text) < data['minimum']:
            bot.send_message(user_id, "Above or below the limit.")
        else:
            payeer = BotSetting().payeer
            usdt = BotSetting().usdt
            text = "✅ <b>PAYEER</b>:\n"
            for pay in payeer:
                text += "  ◽ <code>%s</code>\n" % (pay)
            text += "\n\n✅ <b>USDT</b>:\n"
            for usd in usdt:
                text += "  ◽ <code>%s</code>\n" % (usd)
            text += '\n\nSend <b>𝗦𝗖𝗥𝗘𝗘𝗡𝗦𝗛𝗢𝗧📸</b> to confirm your deposit'
            bot.send_message(user_id, text, reply_markup=keyboards.cancel())
    
    bot.set_state(user_id, 'screenshoot')

    with bot.retrieve_data(user_id) as data:
        data['amount'] = int(message.text)


@bot.message_handler(state='screenshoot', content_types=util.content_type_media)
def get_screenshoot(message: types.Message):
    user_id = message.from_user.id
    user = User(user_id)

    if message.content_type != 'photo':
        bot.send_message(user_id, "Only photo required!")

    else:
        photo = message.photo[-1]
        msg = bot.send_message(user_id, "👍 Your request is sent to the bot admin.")
        with bot.retrieve_data(user_id) as data:
            text = "<b>DEPOSIT REQUEST</b>\n\n<b>From</b>: {}\n<b>Amount</b>: ${}\n<b>Profit Percentage</b>: {}%\n" \
                   "<b>Minimum Deposit</b>: ${}".format(util.user_link(message.from_user), data['amount'], data['percentage'], data['minimum'],
                                                       )
            text += "\n\n<i>🔰 If the user is sent the money to your wallet press ✅ Confirm button.</i>"
            profit_amount = int((data['percentage'] * data['amount'])//100)
            user.invest_history.append({"Amount": data['amount'], "Profit Percentage": data['percentage'],
                                "Profit Amount": profit_amount, "Receive After": data['hours'],
                                "Status": "🔁 Pending", "Date": datetime.utcnow()
                })

            user.update(invest_history=user.invest_history)
            
            id = len(user.invest_history) - 1
            btn = types.InlineKeyboardMarkup([[types.InlineKeyboardButton("✅ Confirm",
                                                                          callback_data='confirmation:confirm:%d:%d:%d' % (user_id, id, msg.message_id)),
                                               types.InlineKeyboardButton("❌ Decline",
                                                                          callback_data='confirmation:decline:%d:%d:%d' % (user_id, id, msg.message_id))
                                             ]])
            bot.send_photo(config.ADMIN_ID, photo.file_id, caption=text, reply_markup=btn)
        start(message)


@bot.message_handler(state='withdraw')
def on_withdraw(message):
    user_id = message.from_user.id
    user = User(user_id)

    if not message.text.isdigit():
        bot.send_message(user_id, "Number required!")
    elif int(message.text) > user.balance or int(message.text) <= 0:
        text = f"💵 <b>Current balance</b>: <code>{user.balance}</code>\n\n❓ <i>How much do you want to witdraw ?</i>"
        bot.send_message(user_id, text, reply_markup=keyboards.cancel())
    else:
        kbd = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        txt = ['PAYEER', "USDT", '❌ Cancel']
        kbd.add(*[types.KeyboardButton(t) for t in txt])

        bot.send_message(user_id, "<b>Chose payment method</b>:", reply_markup=kbd)
        bot.set_state(user_id, 'payment_method')

        with bot.retrieve_data(user_id) as data:
            data['amount'] = int(message.text)


@bot.message_handler(state='payment_method')
def on_payment_method(message: types.Message):
    user_id = message.from_user.id

    if message.text == "PAYEER":
        bot.send_message(user_id, "<b>Please send us your PAYEER wallet:</b>", reply_markup=keyboards.cancel())
        method = 'PAYEER'

    elif message.text == "USDT":
        bot.send_message(user_id, "<b>Please send us your USDT wallet:</b>", reply_markup=keyboards.cancel())
        method = 'USDT'

    else:
        return bot.send_message(user_id, "Only chose from below options!")

    bot.set_state(user_id, 'get_payment_wallet')
    with bot.retrieve_data(user_id) as data:
        data['payment_method'] = method


@bot.message_handler(state='get_payment_wallet')
def get_payment_wallet(message: types.Message):
    user_id = message.from_user.id

    kbd = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kbd.add(types.KeyboardButton("✅ Confirm"), types.KeyboardButton("❌ Cancel"))
    msg = "<b>Withdraw</b>\n\n💵 <b>Amount</b>: ${0}\n📱 <b>Payment Method</b>: {1}\n🧧 <b>Payment Wallet</b>: {2}" \
          "\n\n✔ Confirm this withdraw"
    with bot.retrieve_data(user_id) as data:
        data['wallet'] = message.text
        bot.send_message(user_id, msg.format(data['amount'], data['payment_method'], message.text), reply_markup=kbd)
    bot.set_state(user_id, 'confirm_withdraw')


@bot.message_handler(state='confirm_withdraw')
def confirm_withdraw(message: types.Message):
    user_id = message.from_user.id
    user = User(user_id)

    with bot.retrieve_data(user_id) as data:
        if user.balance < int(data['amount']): # Sometimes to prevent fraud 
            bot.send_message(user_id, "Something went wrong....")
            return start(message)
        new_balance = user.balance - int(data['amount'])
        user.withdraw_history.append({'Amount': data['amount'], 'Payment Method': data['payment_method'],
                                      'Wallet': data['wallet'], 'Status': '🔁 Pending', "Date": datetime.utcnow()
        })
        id = len(user.withdraw_history) - 1
        user.withdraw += int(data['amount'])
        user.update(balance=new_balance, withdraw=user.withdraw, withdraw_history=user.withdraw_history)
        msg = bot.send_message(user_id, "👍 <b>Congratulation</b>\n\n✅ Your request is sent to the <b>bot admin</b>,"
                                        " you will get your money in 24 hours.")
        start(message)
        text = """◽ <b>Withdrawal Request</b>\n
<b>Amount</b>: <code>${0}</code>
<b>Payment Method</b>: {1}
<b>Wallet Address</b>: <code>{2}</code>\n
✅ <i>After sending the money, please press ✅ Transfer Done button to send confirmation message to the user. </i>""".format(data['amount'], data['payment_method'], data['wallet'])
        btn = types.InlineKeyboardMarkup([[types.InlineKeyboardButton("✅ Transfer Done", callback_data='transfer_done:%d:%d:%d' % (user_id, id, msg.message_id))]])        
        bot.send_message(config.ADMIN_ID, text, reply_markup=btn)


@bot.callback_query_handler(func=lambda call: call.data.startswith('transfer_done'))
def on_transfer_done(callback: types.CallbackQuery):
    user_id, id, msg_id = callback.data.split(":")[1:]
    user = User(int(user_id))
    history = user.withdraw_history[int(id)]
    history['Status'] = '✅ Paid'
    history['Paid Date'] = datetime.utcnow()
    user.withdraw_history[int(id)] = history
    user.update(withdraw_history=user.withdraw_history)

    bot.answer_callback_query(callback.id, '✅ Paid')
    bot.edit_message_reply_markup(callback.from_user.id, callback.message.message_id)

    try:
        bot.send_message(int(user_id), "✅ Your money is sent to your %s wallet successfully!" % history['Payment Method'], reply_to_message_id=int(msg_id))
    except: 
        pass


@bot.callback_query_handler(func=lambda call: call.data.startswith("history"))
def on_history(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = User(user_id)
    data = callback.data.split(":")[1]
    bot.answer_callback_query(callback.id)
    if data == "invest":
        if not user.invest_history:
            text = "<b>Sorry</b>, you don't have any invest / deposit history yet."
        else:
            text = ""
            for invest in user.invest_history[:5]:
                for key, val in invest.items():
                    if key == "Receive After": continue
                    text += f"<b>{key}</b>: {val}\n"
                text += "\n"
        bot.edit_message_text(text, user_id, callback.message.message_id,
                              reply_markup=keyboards.history_btn("invest", 1, len(user.invest_history)))
    elif data == "withdraw":
        if not user.withdraw_history:
            text = "<b>Sorry</b>, you don't have any withdrawal history yet."
        else:
            text = ""
            for withdraw in user.withdraw_history[:5]:
                for key, val in withdraw.items():
                    text += f"<b>{key}</b>: {val}\n"
                text += "\n"
        bot.edit_message_text(text, user_id, callback.message.message_id,
                              reply_markup=keyboards.history_btn("withdraw", 1, len(user.withdraw_history)))
    else:
        msg = """<b>Your Account</b>
--------------------\n
💵 <b>Current Balance</b>: ${0}
💰 <b>Total Invests</b>: ${1}
💳 <b>Total Withdraws</b>: ${2}\n
📆 <i>Joined {3}</i>""".format(user.balance, user.invest, user.withdraw, user.date)
        bot.edit_message_text(msg, user_id, callback.message.message_id, reply_markup=keyboards.profile_btn())


@bot.callback_query_handler(func=lambda call: call.data.startswith("get_history"))
def get_history(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = User(user_id)
    name, row = callback.data.split(":")[1: ]
    row = int(row)

    bot.answer_callback_query(callback.id)
    if name == "invest":
        if not user.invest_history:
            text = "<b>Sorry</b>, you don't have any invest / deposit history yet."
        else:
            text = ""
            for invest in user.invest_history[(row*5) - 5:row*5]:
                for key, val in invest.items():
                    if key == "Receive After": continue
                    text += f"<b>{key}</b>: {val}\n"
                text += "\n"
        bot.edit_message_text(text, user_id, callback.message.message_id,
                              reply_markup=keyboards.history_btn("invest", row, len(user.invest_history)))

    else:
        if not user.withdraw_history:
            text = "<b>Sorry</b>, you don't have any withdrawal history yet."
        else:
            text = ""
            for withdraw in user.withdraw_history[(row*5) - 5:row*5]:
                for key, val in withdraw.items():
                    text += f"<b>{key}</b>: {val}\n"
                text += "\n"
    
        bot.edit_message_text(text, user_id, callback.message.message_id,
                              reply_markup=keyboards.history_btn("withdraw", row, len(user.withdraw_history)))


@bot.callback_query_handler(func=lambda call: call.data.startswith("confirmation"))
def on_confirmation(callback: types.CallbackQuery):
    
    data, user_id, id, msg_id = callback.data.split(":")[1:]
    user_id, id, msg_id = int(user_id), int(id), int(msg_id)
    user = User(user_id)

    if data == "confirm":
        status = "✅ Confirmed"
        text = "<b>👍 Congra</b>\n\n<i>Your deposit is confirmed</i>"
        user.balance += user.invest_history[id]["Amount"]
    else:
        status = "❌ Declined"
        text = "<b>😔 Sorry</b>\n\n<i>Your deposit could not be confirmed</i>."
    bot.answer_callback_query(callback.id, status)
    invest_history = user.invest_history[id]

    invest_history["Status"] = status
    user.invest_history[id] = invest_history
    user.invest += user.invest_history[id]['Amount']
    print(user.invest_history)
    user.update(invest_history=user.invest_history, balance=user.balance, invest=user.invest)
    bot.edit_message_reply_markup(callback.from_user.id, callback.message.message_id)
    # 3600 * user.invest_history[id]["Receive After"]
    event.enter(10, 1, get_profit, argument=(user, msg_id, id))
    bot.send_message(user_id, text, reply_to_message_id=msg_id)


def get_profit(user: User, msg_id: int, id: int):
    invest = user.invest_history[id]
    user.balance += invest['Profit Amount']
    invest["Received Profit"] = invest['Profit Amount']
    invest["Received Date"] = datetime.utcnow()
    user.invest_history[id] = invest
    user.update(balance=user.balance, invest_history=user.invest_history)
    bot.send_message(user.id, "<i>✅ You have successfully received <b>${}</b></i>"
                              " profit of your <b>${}</b> deposit.".format(invest['Profit Amount'], invest['Amount']),
                     reply_to_message_id=msg_id)


class State:
    message = 'message'
    add_btn = 'add_btn'
    channel = 'channel'
    admin = 'admin'
    balance = 'balance'
    password = 'password'
    email = 'email'
    confirm = 'confirm'


@bot.message_handler(func= lambda msg: msg.text in ["📝 Send Message", "⚙ Bot Setting", "📊 Statics"], is_admin=True, chat_types=['private'])
def admin_message(msg: types.Message):
    user_id = msg.chat.id
    user = User(user_id)
    text = msg.text
    if text == '📝 Send Message':
        markups.clear()
        if user.can(Permission.SEND_MESSAGES):
            bot.send_message(user_id, """✳️Enter New Message.\n
You can also «Forward» text from another chat or channel.
                        """, reply_markup=keyboards.cancel())
            bot.set_state(user_id, State.message)

    elif text == "📊 Statics":
        if user.status == 'admin' or user.can(Permission.SEE_PROFILE):
            users = User.find()
            count = len(users)
            ls = []
            for i in users[:10]:
                try:
                    u = bot.get_chat(i.get('id'))
                    ls.append(util.user_link(user))
                except:
                    ls.append("<a href='tg://user?id=%d'>%d</a>" % (i.get('id'), i.get('id')))
            txt = [f"<i>#{i + 1}.</i> {names}" for i, names in enumerate(ls)]
            data = '\n\n'.join(txt)
            bot.send_message(user_id, f'{data}\n\nShowed {len(ls)} out of {count}',
                             reply_markup=keyboards.members_button(len(users), 1))

    else:
        if user.status == 'admin' or user.can(Permission.MANAGE_BOT):
            bot_stng_msg(user_id)


@bot.message_handler(state=State.message, content_types=util.content_type_media)
def on_get_message(msg: types.Message):
    btn = types.InlineKeyboardMarkup(row_width=2)
    texts = {"📣 Channel": 'to_channels', "👥 Users": 'to_users', "♻ Both": 'to_both'}
    ls = []
    alowed_channels = get_message_channels()
    if alowed_channels:
        for key, val in texts.items():
            ls.append(
                types.InlineKeyboardButton(key, callback_data=val)
            )
        btn.add(*ls)
    else:

        btn.add(
            types.InlineKeyboardButton("➕ Add", callback_data=f'sm:add:users'),
            types.InlineKeyboardButton("☑ Done", callback_data=f'sm:done:users')
        )

    bot.copy_message(msg.chat.id, msg.chat.id, msg.message_id, parse_mode='HTML', reply_markup=btn)
    if alowed_channels:
        bot.send_message(msg.chat.id, 'Select a place where do you want to send your message.')
    start(msg)
    bot.delete_state(msg.chat.id)


@bot.callback_query_handler(func=lambda call: call.data in ['to_users', 'to_channels', 'to_both'])
def on_send_message(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    user_id = call.from_user.id
    to = call.data.split('_')[1]
    btn = types.InlineKeyboardMarkup()
    btn.add(
        types.InlineKeyboardButton("➕ Add", callback_data=f'sm:add:{to}'),
        types.InlineKeyboardButton("☑ Done", callback_data=f'sm:done:{to}')
    )
    bot.edit_message_reply_markup(user_id, call.message.message_id, reply_markup=btn)


@bot.callback_query_handler(func=lambda call: re.match('^sm', call.data))
def on_got_message(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
    data = call.data.split(':')[1]

    to = call.data.split(":")[2]
    if data == 'add':
        bot.send_message(call.message.chat.id, "Send your button text and url link like this:\n text -> www.text.com")
        bot.set_state(call.message.chat.id, State.add_btn)
        with bot.retrieve_data(call.message.chat.id) as data:
            data['msg_id'] = call.message.message_id
            data['to'] = to

    elif data == 'done':
        if to == 'users':
            send_to_users(call.message)
        elif to == 'to_channel':
                send_to_channels(call.message)
        else:
            send_to_channels(call.message)
            send_to_users(call.message)

        markups.clear()


@bot.message_handler(state=State.add_btn)
def on_send_btn(msg: types.Message):
    text = msg.text
    match = re.findall(r".+\s*->\s*.+", text)
    if match:
        btns = {k.split('->')[0]: k.split('->')[1] for k in match}
        for k, v in btns.items():
            markups[k] = {'url': v.lstrip()}
        try:
            del markups["➕ Add"], markups["☑ Done"]
        except (IndexError, KeyError):
            pass

        try:
            with bot.retrieve_data(msg.chat.id) as data:
                msg_id = data['msg_id']
                to = data['to']

            markups["➕ Add"] = {'callback_data': f'sm:add:{to}'}
            markups["☑ Done"] = {'callback_data': f'sm:done:{to}'}
            bot.copy_message(msg.chat.id, msg.chat.id, msg_id, parse_mode='html',
                             reply_markup=util.quick_markup(markups))
        except Exception as e:
            for bt in btns:
                del markups[bt]
            bot.reply_to(msg, "❌ Invalid URL links ...")
            bot.copy_message(msg.chat.id, msg.chat.id, msg_id, reply_markup=util.quick_markup(markups))
    else:
        with bot.retrieve_data(msg.chat.id) as data:
            msg_id = data['msg_id']
            to = data['to']

        bot.reply_to(msg, "Error typing...", reply_markup=keyboards.main_keyboard(User(msg.chat.id)))
        bot.copy_message(msg.chat.id, msg.chat.id, msg_id, reply_markup=util.quick_markup(markups))
    bot.delete_state(msg.chat.id)


@bot.callback_query_handler(lambda call: re.search(r'members', call.data))
def on_members(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    user_id, msg_id = call.message.chat.id, call.message.message_id
    pos = int(call.data.split('_')[1])
    try:
        count = len(User.find())
        users = User.find()[pos*10-9:pos*10]
        ls = []
        for i in users:

            try:
                u = bot.get_chat(i.get('id'))
                ls.append(util.user_link(u))
            except:
                ls.append("<a href='tg://user?id=%d'>%d</a>" % (i.get('id'), i.get('id')))
        txt = [f"<i>#{i + (pos*10-9)}.</i> {names}" for i, names in enumerate(ls)]
        data = '\n\n'.join(txt)
        left = count % 10
        if not left:
            total = pos * 10
        elif left and pos * 10 < count:
            total = pos * 10
        else:
            total = count
        bot.edit_message_text(f"{data}\n\nShowed {total}: Total {count}", user_id, msg_id,
                              reply_markup=keyboards.members_button(count, pos))
    except apihelper.ApiException:
        bot.answer_callback_query(call.id, "Please press another button!")


@bot.callback_query_handler(func=lambda call: re.match(r'^bot', call.data))
def on_setting(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    user_id = call.message.chat.id
    msg_id = call.message.message_id
    admin = User(user_id)
    text = call.data.split(":")[1]
    if text == 'channels':
        t, k = channel_text()
        bot.edit_message_text(t, user_id, msg_id, reply_markup=k)

    elif text == 'admins':
        a, k = admin_text(call.message.chat.id)
        bot.edit_message_text(a, user_id, msg_id, reply_markup=k)

    elif text == 'add_channel':
        bot.edit_message_text(ADD_CHANNEL, user_id, msg_id, reply_markup=keyboards.icancel())
        bot.set_state(user_id, State.channel)

    elif text == 'add_admin':
        bot.edit_message_text(ADD_ADMIN, user_id, msg_id, reply_markup=keyboards.icancel())
        bot.set_state(user_id, State.admin)

    elif text == 'back':
        bot.edit_message_text(f"<b> 🤖 Bot Setting</b>\n\nFrom this menu you can manage your bot setting.", user_id,
                              msg_id, reply_markup=keyboards.bot_setting(admin))

    elif text == 'cmd':
        btn = types.InlineKeyboardMarkup()
        btn.add(types.InlineKeyboardButton("🔙 Back", callback_data='bot:back'))
        bot.edit_message_text(COMMANDS, user_id, msg_id, reply_markup=btn)


@bot.callback_query_handler(func=lambda call: call.data == 'cancel')
def on_cancel(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    state = bot.get_state(call.from_user.id)
    user_id = call.from_user.id
    msg_id = call.message.message_id

    if state == State.channel:
        text, btn = channel_text()
        bot.edit_message_text(text, user_id, msg_id, reply_markup=btn)
    elif state == State.admin:
        text, btn = admin_text(user_id)
        bot.edit_message_text(text, user_id, msg_id, reply_markup=btn)
    elif state == State.balance:
        call.data = 'bot:balance'
        on_setting(call)
    bot.delete_state(user_id)

def admin_text(user_id):
    admins = User.find(status='moderator')
    for admin in admins:
        if admin['id'] == user_id: admins.pop(admin)

    ad = [bot.get_chat(chat['id']) for chat in admins]
    ad = [user.first_name for user in ad]
    ad = '\n'.join(ad)
    key = [bot.get_chat(key['id']) for key in admins]
    ukey = {k.first_name + " - "+str(k.id): {'callback_data': "badm:" + str(k.id)} for k in key}
    ukey.update({"➕ Add": {'callback_data': "bot:add_admin"}, "🔙 Back": {"callback_data": 'bot:back'}})
    return ADMIN.format(ad), util.quick_markup(ukey)


def admin_permision(admin_id):
    admin = User(int(admin_id))
    perm = []
    for key, val in admin.permission.items():
        if key == Permission.USE_BOT: continue
        perm.append('✅' if admin.permission[key] else "❌")
    _admin = bot.get_chat(admin_id)
    text = ADMINP.format(_admin.first_name, *perm)
    btn = keyboards.admin_permision(admin)
    return text, btn


def channel_permision(channel_id):
    channels = BotSetting().channels
    perm = []
    dr = {}
    for channel in channels:
        if channel['id'] == int(channel_id):
        
            for k in channel:
                if k == 'id': 
                    continue

                perm.append('✅' if channel[k] else "❌")
            dr = channel
            break
    channel = bot.get_chat(int(channel_id))
    text = CHANNELP.format(channel.username, *perm)
    btn = keyboards.channel_perm(dr)
    return text, btn


@bot.message_handler(state=State.admin, content_types=util.content_type_media)
def add_admin(msg: types.Message):
    if not msg.forward_from:
        return
    user_id = msg.from_user.id
    from_user = int(msg.forward_from.id)
    user = User(from_user)

    try:
        assert user.exist(), "User not found"
        assert user.status not in ['moderator', 'admin'], "User is already admin!"
        user.permission[Permission.SEND_MESSAGES] = True
        user.update(permission=user.permission, status='moderator')
        bot.send_message(user_id, "Admin added successfully ✅")
        text, btn = admin_permision(from_user)
        bot.send_message(user_id, text, reply_markup=btn, parse_mode='html')

    except AssertionError as e:
        bot.send_message(user_id, e.args[0])
    finally:
        bot.delete_state(user_id)


@bot.callback_query_handler(func=lambda call: re.search(r'channel:', call.data))
def click_channel(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    user_id, msg_id = call.from_user.id, call.message.message_id
    channel_id = call.data.split(':')[1]
    admin = User(user_id)
    if not admin.can(Permission.MANAGE_BOT): return bot.delete_message(user_id, msg_id)
    t, b = channel_permision(channel_id)
    bot.edit_message_text(t, user_id, msg_id, reply_markup=b, parse_mode='html')


@bot.callback_query_handler(func=lambda call: re.search(r'myc', call.data))
def on_channel_permision(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    channel_id = call.data.split(":")[1]
    text = call.data.split(":")[2]
    user_id = call.from_user.id
    msg_id = call.message.message_id
    admin = User(user_id)
    if not admin.can(Permission.MANAGE_BOT): return bot.delete_message(user_id, msg_id)
    if text == 'back':
        t, b = channel_text()
        bot.edit_message_text(t, user_id, msg_id, reply_markup=b, parse_mode='html')
    elif text == 'remove':
        try:
            channels = BotSetting().channels
            for channel in channels:
                if channel['id'] == int(channel_id):
                    channels.pop(channel)
                    break     
            BotSetting().update(channels=channels)

            t, b = channel_text()
            bot.edit_message_text(t, user_id, msg_id, reply_markup=b, parse_mode='html')
        except (IndexError, KeyError):
            bot.send_message(user_id, "channel not found..")
            bot.delete_message(user_id, msg_id)
    else:
        try:
            channels = BotSetting().channels
            for channel in channels:
                if channel['id'] == int(channel_id):
                    if channel[text]:
                        channel[text] = False
                    else:
                        channel[text] = True
            BotSetting().update(channels=channels)
            
            t, b = channel_permision(channel_id)
            bot.edit_message_text(t, user_id, msg_id, reply_markup=b, parse_mode='html')

        except (IndexError, KeyError):
            bot.send_message(user_id, "channel not found...")
            bot.delete_message(user_id, msg_id)


@bot.message_handler(state=State.channel, content_types=util.content_type_media, is_forwarded=True)
def add_channel(msg: types.Message):
    channel = msg.forward_from_chat
    user_id = msg.chat.id
    admin = User(user_id)
    if not admin.can(Permission.MANAGE_BOT): return start(msg)
    try:
        assert channel.username is not None, "The channel must have a username!"
        channels = BotSetting().channels
        channels.append({"id": channel.id, 'send_message': False,  'force_join': False})
        BotSetting().update(channels=channels)
        bot.send_message(user_id, "Channel added successfully ✅\n\n⚠️ <b>Don't forget to make admin on the channel!</b>")
        text, keyboard = channel_text()
        bot.send_message(user_id, text, reply_markup=keyboard, parse_mode='html')
    except AssertionError as e:
        bot.send_message(user_id, e.args[0])
    else:
        bot.delete_state(user_id)


@bot.callback_query_handler(lambda call: re.search(r"badm", call.data))
def click_admin(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    admin_id = call.data.split(':')[1]
    text, btn = admin_permision(admin_id)
    admin = User(int(admin_id))
    if not admin.can(Permission.MANAGE_BOT): return bot.delete_message(call.from_user.id, call.message.message_id)

    bot.edit_message_text(text, call.from_user.id, call.message.message_id, reply_markup=btn, parse_mode='html')


@bot.callback_query_handler(lambda call: re.search(r'^admin:', call.data))
def on_admin_permission(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    admin_id = call.data.split(":")[2]
    user_id = call.from_user.id
    msg_id = call.message.message_id
    user = User(int(admin_id))

    text = call.data.split(":")[1]
    admin = User(user_id)
    if not admin.can(Permission.MANAGE_BOT): return bot.delete_message(user_id, msg_id)

    if text == 'back':
        t, k = admin_text(call.message.chat.id)
        bot.edit_message_text(t, user_id, msg_id, reply_markup=k, parse_mode='html')
    elif text == 'remove':
        try:
            user.update(status='user', permission=Permission.USER_PERMISSION)
        except (IndexError, KeyError):
            bot.send_message(user_id, "user not found....")
            bot.delete_message(user_id, msg_id)
        else:
            t, k = admin_text(call.message.chat.id)
            bot.edit_message_text(t, user_id, msg_id, reply_markup=k, parse_mode='html')
    elif text == 'owner':
        btn = types.InlineKeyboardMarkup([[InlineKeyboardButton("✅ Yes", callback_data="admin:yes:%d" % user.id), 
                                          InlineKeyboardButton("❌ No", callback_data="admin:back:%d" % user.id)]])
        bot.edit_message_text("⚠️ Are you sure to transfer ownership ?", user_id, msg_id, reply_markup=btn)

    elif text == 'yes':
        user.status = 'admin'
        admin.status = 'user'
        user.permission = Permission.ADMIN_PERMISSION
        admin.permission = Permission.USER_PERMISSION
        user.update(status=user.status, permission=user.permission)
        admin.update(status=admin.status, permission=admin.permission)
        bot.send_message(user_id, "Ownership transferred!")
        bot.delete_message(user_id, msg_id)
        start(message)
    else:
        try:
            if user.permission[text]:
                user.permission[text] = False
            else:
                user.permission[text] = True
            user.update(permission=user.permission)

        except (IndexError, KeyError):
            bot.send_message(user_id, "user not found...")
            bot.delete_message(user_id, msg_id)
        else:
            t, k = admin_permision(admin_id)
            bot.edit_message_text(t, user_id, msg_id, reply_markup=k, parse_mode='html')


def send_to_channels(msg: types.Message):
    try:
        del markups["➕ Add"], markups["☑ Done"]
    except:
        pass

    channels = BotSetting().channels
    for channel in channels:
        if channel.get('send_message'):
            try:
                bot.copy_message(channel['id'], msg.chat.id, msg.message_id, reply_markup=util.quick_markup(markups))
            except:
                continue


def send_to_users(msg: types.Message):
    try:
        del markups["➕ Add"], markups["☑ Done"]
    except:
        pass

    users = User.find()
    for ui in users:
        try:
            bot.copy_message(ui["id"], msg.chat.id, msg.message_id, reply_markup=util.quick_markup(markups))
        except:
            continue


def channel_text():
    channels = BotSetting().channels
    ukey = {}
    try:
        ls = [bot.get_chat(int(channel['id'])) for channel in channels]
        ln = [] 
        for l in ls:
            if l.username:
                ln.append("@" + l.username)
            else:
                ln.append(l.invite_link)
        chan = '\n'.join(ln)
        ids = [key['id'] for key in channels]
        key = [bot.get_chat(int(k)) for k in ids]
        ukey = {k.username or k.invite_link: {'callback_data': "channel:" + str(k.id)} for k in key}
    except:
        chan = "NO CHANNEL"
    ukey.update({"➕ Add": {'callback_data': "bot:add_channel"}, "🔙 Back": {"callback_data": 'bot:back'}})
        
    return CHANNEL.format(chan), util.quick_markup(ukey)


def bot_stng_msg(user_id):
    admin = User(user_id)
    bot.send_message(user_id, f"<b>🤖 Bot Setting</b>\n\nFrom this menu you can manage your bot setting.",
                     reply_markup=keyboards.bot_setting(admin))


CHANNEL = """📣 <b>Channels</b>\n
✳ From this menu you can add or remove channel.\n
✅ You can also give permissions for your bot what the bot can do on these channel.\n
🔧 Current channels:\n{}
"""


ADD_CHANNEL = """➕ <b>Add new Channel</b>\n
ℹ Forward here any message from you want to add as a channel.
"""

ADMIN = """🛃 <b>Manage Admins</b>\n
🔧 You are in the Bot Admin Settings mode.\n
⛑ Current admins:\n{}
"""

ADD_ADMIN = """🛠 <b>Adding new Admin</b>\n
ℹ Forward here any message from you want to add as an admin. 
"""

CHANNELP = """🔧 Manage bot's permission what it can do on the channel.\n
📣 channel :  {}\n
◽ Send message : {}
◽ Force join: {}
"""

COMMANDS = '''<b>Bot commands</b>\n
<code>/ban [user_id] </code> - ban user. \n
<code>/unban [user_id] </code> - unban user.\n
<code>/wallets</code> - list of your wallets.\n
<code>/add_payeer_wallet [wallet] </code> - add your payeer wallet.\n
<code>/add_usdt_wallet [wallet] </code> - add your usdt wallet.\n
<code>/remove_payeer_wallet [wallet] </code> - remove payeer wallet.\n
<code>/remove_usdt_wallet [wallet] </code> - remove payeer wallet.\n
'''


ADMINP = """🔧 Manage admin's permision\n
⛑ Admin: {}\n
◽ Send Messages: {}
◽ Ban Users: {}
◽ Add Admin: {}
◽ See Statics : {}
◽ Manage setting : {}
"""

def forever():
    while True:
        event.run()

import filters
from telebot.custom_filters import StateFilter
bot.add_custom_filter(filters.IsDeeplink())
bot.add_custom_filter(filters.IsAdmin())
bot.add_custom_filter(StateFilter(bot))
bot.add_custom_filter(ForwardFilter())

event_sched = threading.Thread(target=forever)
event_sched.start()


@app.route('/')
def index():
    bot.delete_webhook()
    bot.set_webhook(config.WEBSITE_URI+"/"+config.TOKEN)
    return "!", 200

@app.route('/' + config.TOKEN, methods=["POST"])
def get_update():
    from flask import request
    json_string = request.get_data().decode("utf-8")
    update = types.Update.de_json(json_string)
    bot.process_new_updates([update])

    return "OK", 200

     
if __name__ == '__main__':
    import os
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 5555)))
