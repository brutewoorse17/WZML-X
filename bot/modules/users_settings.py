#!/usr/bin/env python3
from datetime import datetime
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.filters import command, regex, create
from aiofiles import open as aiopen
from aiofiles.os import remove as aioremove, path as aiopath, mkdir
from langcodes import Language
from os import path as ospath, getcwd
from PIL import Image
from time import time
from functools import partial
from html import escape
from io import BytesIO
from asyncio import sleep
from cryptography.fernet import Fernet

import asyncio
from bot import (
    OWNER_ID,
    LOGGER,
    bot,
    user_data,
    config_dict,
    categories_dict,
    DATABASE_URL,
    IS_PREMIUM_USER,
    MAX_SPLIT_SIZE,
)
from bot.helper.telegram_helper.message_utils import (
    sendMessage,
    sendCustomMsg,
    editMessage,
    deleteMessage,
    sendFile,
    chat_info,
    user_info,
)
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.ext_utils.db_handler import DbManger
from bot.helper.ext_utils.bot_utils import (
    getdailytasks,
    update_user_ldata,
    get_readable_file_size,
    sync_to_async,
    new_thread,
    is_gdrive_link,
)
from bot.helper.mirror_utils.upload_utils.ddlserver.gofile import Gofile
from bot.helper.themes import BotTheme

handler_dict = {}

async def send_users_settings(client, message):
    text = message.text.split(maxsplit=1)
    userid = text[1] if len(text) > 1 else None
    if userid and not userid.isdigit():
        userid = None
    elif (
        (reply_to := message.reply_to_message)
        and reply_to.from_user
        and not reply_to.from_user.is_bot
    ):
        userid = reply_to.from_user.id
    if not userid:
        return await send_users_admin_page(message, 0)
    elif int(userid) in user_data:
        msg = f'{(await user_info(userid)).mention(style="html")} ( <code>{userid}</code> ): '
        if data := user_data[int(userid)]:
            buttons = ButtonMaker()
            buttons.ibutton(
                "Delete Data", f"userset {message.from_user.id} user_del {userid}"
            )
            buttons.ibutton("Close", f"userset {message.from_user.id} close")
            button = buttons.build_menu(1)
            for key, value in data.items():
                if key in ["token", "time", "ddl_servers", "usess"]:
                    continue
                msg += f"\n<b>{key}</b>: <code>{escape(str(value))}</code>"
        else:
            msg += "\nThis User has not Saved anything."
            button = None
        await sendMessage(message, msg, button)
    else:
        await sendMessage(message, f"{userid} have not saved anything..")

bot.add_handler(
    MessageHandler(
        send_users_settings,
        filters=command(BotCommands.UsersCommand) & CustomFilters.sudo,
    )
)

# Pagination helpers for users list
PAGE_SIZE = 10

async def send_users_admin_page(message, start_index: int):
    ids = sorted(list(user_data.keys()))
    total = len(ids)
    page_ids = ids[start_index : start_index + PAGE_SIZE]
    text = f"<u><b>Total Users / Chats Data Saved :</b> {total}</u>\n\nSelect a user to view details:"
    buttons = ButtonMaker()
    for uid in page_ids:
        buttons.ibutton(str(uid), f"usersadmin view {uid}")
    if start_index > 0:
        buttons.ibutton("◀ Prev", f"usersadmin page {max(0, start_index - PAGE_SIZE)}", "footer")
    if start_index + PAGE_SIZE < total:
        buttons.ibutton("Next ▶", f"usersadmin page {start_index + PAGE_SIZE}", "footer")
    buttons.ibutton("Close", f"usersadmin close", "footer")
    await sendMessage(message, text, buttons.build_menu(2))

async def edit_users_admin(client, query):
    data = query.data.split()
    message = query.message
    await query.answer()
    if data[1] == "page":
        start = int(data[2])
        ids = sorted(list(user_data.keys()))
        total = len(ids)
        page_ids = ids[start : start + PAGE_SIZE]
        text = f"<u><b>Total Users / Chats Data Saved :</b> {total}</u>\n\nSelect a user to view details:"
        buttons = ButtonMaker()
        for uid in page_ids:
            buttons.ibutton(str(uid), f"usersadmin view {uid}")
        if start > 0:
            buttons.ibutton("◀ Prev", f"usersadmin page {max(0, start - PAGE_SIZE)}", "footer")
        if start + PAGE_SIZE < total:
            buttons.ibutton("Next ▶", f"usersadmin page {start + PAGE_SIZE}", "footer")
        buttons.ibutton("Close", f"usersadmin close", "footer")
        await editMessage(message, text, buttons.build_menu(2))
    elif data[1] == "view":
        uid = int(data[2])
        msg = f"{(await user_info(uid)).mention(style='html')} ( <code>{uid}</code> ):"
        if data_dict := user_data.get(uid, {}):
            buttons = ButtonMaker()
            buttons.ibutton("Delete Data", f"usersadmin del {uid}")
            buttons.ibutton("Back", f"usersadmin page 0", "footer")
            buttons.ibutton("Close", f"usersadmin close", "footer")
            for key, value in data_dict.items():
                if key in ["token", "time", "ddl_servers", "usess"]:
                    continue
                msg += f"\n<b>{key}</b>: <code>{escape(str(value))}</code>"
            await editMessage(message, msg, buttons.build_menu(1))
        else:
            await editMessage(message, msg + "\nThis User has not Saved anything.")
    elif data[1] == "del":
        uid = int(data[2])
        thumb_path = f"Thumbnails/{uid}.jpg"
        rclone_path = f"rclone/{uid}.conf"
        if await aiopath.exists(thumb_path):
            await aioremove(thumb_path)
        if await aiopath.exists(rclone_path):
            await aioremove(rclone_path)
        update_user_ldata(uid, None, None)
        if DATABASE_URL:
            await DbManger().update_user_data(uid)
            await DbManger().update_user_doc(uid, "thumb")
            await DbManger().update_user_doc(uid, "rclone")
        await editMessage(message, f"Data Reset for {uid}")
    elif data[1] == "close":
        await deleteMessage(message)

bot.add_handler(CallbackQueryHandler(edit_users_admin, filters=regex("^usersadmin")))