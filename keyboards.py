from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton
from database import User, Permission
from telebot import types


main_keyboard_texts = ["💰 الاستثمار", "💳 سحب", "📈 احصائيات", "👤 الحساب", "📋 معلومات", "🛠 الدعم"]
admin_keyboard_texts = []
invest_keyboard_texts = ["💸 50٪ ، ~ بعد 24 ساعة", "💸 80٪ ، ~ بعد 3 أيام", "💸 120٪ ، ~ بعد 7 أيام", "🔙  Back"]

def main_keyboard(user: User):
    kbd = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True, row_width=2)
    adm = []
    if user.can(Permission.SEE_PROFILE):
        adm.append(KeyboardButton("📊 Statics"))
    if user.can(Permission.SEND_MESSAGES):
        adm.append(KeyboardButton('📝 Send Message'))    
    if user.can(Permission.MANAGE_BOT):
        adm.append(KeyboardButton("⚙ Bot Setting"))
    kbd.add(*adm, row_width=3)
    kbd.add(*[KeyboardButton(text) for text in main_keyboard_texts])
    return kbd


def cancel():
    kbd = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True, row_width=2)
    kbd.add(KeyboardButton("❌ Cancel"))
    return kbd

def icancel():
    kbd = types.InlineKeyboardMarkup()
    kbd.add(InlineKeyboardButton("❌ Cancel", callback_data='cancel'))
    return kbd

def members_button(max_id: int, curret_row: int):
    btn = types.InlineKeyboardMarkup(row_width=5)
    btn_list, x = [], 0
    if max_id > 10:
        row_ = max_id // 10
        left = max_id % 10
        if curret_row <= 5:
            btn_list.append(types.InlineKeyboardButton(f"1" if curret_row == 1 else f"◀ 1",
                                                       callback_data=f'members_1'))
        else:
            btn_list.append(types.InlineKeyboardButton(f"⏪ 1", callback_data=f'members_1'))
        if curret_row == 1 and row_ == 1 and left:
            btn_list.append(
                types.InlineKeyboardButton(f"▶ {curret_row + 1}", callback_data=f'members_{curret_row + 1}'))
        if curret_row - 2 > row_:
            btn_list.append(
                types.InlineKeyboardButton(f"◀ {curret_row - 2}", callback_data=f'members_{curret_row - 2}'))
        if curret_row - 1 > 1:
            btn_list.append(
                types.InlineKeyboardButton(f"◀ {curret_row - 1}", callback_data=f'members_{curret_row - 1}'))

        if not curret_row == 1:
            btn_list.append(types.InlineKeyboardButton(f"{curret_row}", callback_data=f'members_{curret_row}'))
        if row_ >= curret_row or left:
            for i in range(1, 2):
                if (curret_row + i) > row_:
                    break
                btn_list.append(
                    types.InlineKeyboardButton(f"▶ {curret_row + i}", callback_data=f'members_{curret_row + i}'))
            if not curret_row == row_ and not left:
                btn_list.append(types.InlineKeyboardButton(f"⏩ {row_}" if curret_row + 5 <= row_ else f"▶ {row_}",
                                                           callback_data=f'members_{row_}'))
        if not curret_row == row_+1 and left:
            btn_list.append(types.InlineKeyboardButton(f"⏩ {row_ + 1}" if curret_row + 5 <= row_ else f"▶ {row_ + 1}",
                                                        callback_data=f'members_{row_ + 1}'))
        if not curret_row == row_ and not left:
            btn_list.append(types.InlineKeyboardButton(f"⏩ {row_}" if curret_row + 5 <= row_ else f"▶ {row_}",
                                                       callback_data=f'members_{row_}'))
    btn.add(*btn_list)
    return btn


def history_btn(name, current_row, max_row):
    btn = InlineKeyboardMarkup(row_width=2)
    current_row = int(current_row)
    if max_row > 5:

        if current_row == 1:
            btn.add(InlineKeyboardButton("▶️", callback_data=f'get_history:{name}:2'))
        elif current_row * 5 >= max_row:
            btn.add(InlineKeyboardButton("◀️", callback_data=f'get_history:{name}:{current_row - 1}'))
        else:
            btn.add(InlineKeyboardButton("◀️", callback_data=f'get_history:{name}{current_row - 1}'),
                    InlineKeyboardButton("▶️", callback_data=f'get_history:{name}:{current_row + 1}')
                    )
    btn.add(InlineKeyboardButton("⬅️ Back", callback_data=f'history:main'))
    return btn


def bot_setting(admin: User):
    btns = types.InlineKeyboardMarkup(row_width=2)
    ls = []
    if admin.can(Permission.MANAGE_BOT):
        ls.extend([
            types.InlineKeyboardButton("🔰 Commands", callback_data='bot:cmd'),
            types.InlineKeyboardButton("📣 Channels", callback_data='bot:channels'),
        ])
    if admin.can(Permission.ADD_ADMIN):
        ls.append(types.InlineKeyboardButton("🛃 Manage Admins", callback_data='bot:admins')) 
    btns.add(*ls)
    return btns


def admin_permision(admin: User):
    btn = types.InlineKeyboardMarkup(row_width=1)
    btn.add(*[types.InlineKeyboardButton("📝 Send Message ✅" if admin.can(Permission.SEND_MESSAGES)
                                         else "📝 Send Message ❌", callback_data=f'admin:send_messages:{admin.id}'),
              types.InlineKeyboardButton("🚷 Ban Users ✅" if admin.can(Permission.BAN_USERS) else "🚷 Ban Users ❌",
                                         callback_data=f'admin:ban_users:{admin.id}'),
              types.InlineKeyboardButton("🛡 Add Admin ✅" if admin.can(Permission.ADD_ADMIN) else "🛡 Add Admin ❌",
                                        callback_data=f'admin:add_admin:{admin.id}'),
              types.InlineKeyboardButton("👤 See Statics ✅" if admin.can(Permission.SEE_PROFILE) else "👤 See Statics ❌",
                  callback_data=f'admin:see_profiles:{admin.id}'),
              types.InlineKeyboardButton("🛠 Manage Bot ✅" if admin.can(Permission.MANAGE_BOT) else "🛠 Manage Bot❌",
                                         callback_data=f'admin:manage_bot:{admin.id}'),
              types.InlineKeyboardButton("➖ Remove", callback_data=f'admin:remove:{admin.id}'),
              ]
            )

    if admin.has_all_permission():
          types.InlineKeyboardButton("👨‍💻 Transfer Ownership", callback_data=f'admin:owner:{admin.id}')
    
    btn.add(types.InlineKeyboardButton("🔙 Back", callback_data=f'admin:back:{admin.id}'))
    
    return btn


def channel_perm(dr):
    btn = types.InlineKeyboardMarkup(row_width=2)
    btn.add(
        types.InlineKeyboardButton("Message ✅" if dr.get('send_message') else "Message ❌",
                                   callback_data=f"myc:{dr['id']}:send_message"),
        types.InlineKeyboardButton("Join ✅" if dr.get('force_join') else "Join ❌",
                                   callback_data=f'myc:{dr["id"]}:force_join')
    )
    btn.add(
        types.InlineKeyboardButton("➖ Remove", callback_data=f"myc:{dr['id']}:remove"),
        types.InlineKeyboardButton("🔙 Back", callback_data=f'myc:{dr["id"]}:back')
    )
    return btn


def profile_btn():
    btn = InlineKeyboardMarkup(row_width=1)
    btn.add(
        InlineKeyboardButton("⏳ Invest History", callback_data="history:invest"),
        InlineKeyboardButton("🗓 Withdraw History", callback_data="history:withdraw")
    )
    return btn 