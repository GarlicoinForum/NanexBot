import discord
import requests
import asyncio
import configparser
import sqlite3

from time import sleep


def get_last_rate():
    try:
        nano = requests.get("https://nanex.co/api/public/ticker/grlcnano", timeout=10)
    except requests.Timeout:
        return None
    else:
         last_rate = float(nano.json()["last_trade"])

    if last_rate:
        return last_rate
    else:
        return None


def deactivate(to_deactivate):
    with sqlite3.connect("nanexbot.sqlite3") as db:
        cursor = db.cursor()
        for table_id in to_deactivate[0]:
            sql = 'UPDATE `sell` SET `active` = "0" WHERE `id` = "{}";'.format(table_id)
            cursor.execute(sql)

        for table_id in to_deactivate[1]:
            sql = 'UPDATE `buy` SET `active` = "0" WHERE `id` = "{}";'.format(table_id)
            cursor.execute(sql)
        db.commit()


def get_active_alarms(table, price):
    comp_operator = {"sell": "<=", "buy": ">="}
    with sqlite3.connect("nanexbot.sqlite3") as db:
        cursor = db.cursor()
        sql = 'SELECT `id`, `user_id`, `price` FROM {0} WHERE `active` = 1 AND `price` {1} {2}'.format(table, comp_operator[table], price)
        cursor.execute(sql)

        alarms = cursor.fetchall()

    return alarms


def get_warnings(price):
    # Get all active sell alarms that are >= price (table id, user_id and value)
    sell_alarms = get_active_alarms("sell", price)

    # Get all active buy alarms that are <= price (table id, user_id and value)
    buy_alarms = get_active_alarms("buy", price)

    return sell_alarms, buy_alarms


def get_user(client, uid):
    for server in client.servers:
        user = server.get_member(uid)
        if user:
            return user
    print("Can't find user! (uid = {})".format(uid))
    return None


def main():
    conf = configparser.RawConfigParser()
    conf.read("config.txt")

    BOT_TOKEN = conf.get('nanexbot_conf', 'BOT_TOKEN')

    client = discord.Client()

    @client.event
    async def on_ready():
        print('Logged in as {} <@{}>'.format(client.user.name, client.user.id))
        print('------')
        
        for server in client.servers:
            print(server.id)
            print(server.members)

        last_price = 0
        while True:
            current_price = get_last_rate()
            # Check the database only if the price changed
            if current_price != last_price:
                sell_warnings, buy_warnings = get_warnings(current_price)
                # Check if list is empty
                if len(sell_warnings) > 0:
                    # Iterate through each users and send them a PM
                    for warning in sell_warnings:
                        # Load an User object using its id and the server to which the bot is connected

                        if warning[2] == current_price:
                            await client.send_message(get_user(client, warning[1]), "Your {} order might be sold! (last trade: {})".format(warning[2], current_price))
                        else:
                            await client.send_message(get_user(client, warning[1]), "Your {} order is sold! (last trade: {})".format(warning[2], current_price))
                if len(buy_warnings) > 0:
                    # Iterate through each users and send them a PM
                    for warning in buy_warnings:
                        if warning[2] == current_price:
                            print(int(warning[1]))
                            await client.send_message(get_user(client, warning[1]), "Your {} order might be bought! (last trade: {})".format(warning[2], current_price))
                        else:
                            print(int(warning[1]))
                            await client.send_message(get_user(client, warning[1]), "Your {} order is bought! (last trade: {})".format(warning[2], current_price))


                # Set active to 0 in the DB if the price != last trade (trade might be done, but not sure)
                # to_deactivate = [[SELL], [BUY]]
                to_deactivate = [[], []]
                for warnings in sell_warnings:
                    if warnings != current_price:
                        to_deactivate[0].append(warnings[0])

                for warnings in buy_warnings:
                    if warnings != current_price:
                        to_deactivate[1].append(warnings[0])

                deactivate(to_deactivate)

                # Set current_price to last_price
                last_price = current_price
            sleep(60)


    client.run(BOT_TOKEN)


if __name__ == "__main__":
    main()
