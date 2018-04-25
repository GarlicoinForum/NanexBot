import discord
import requests
import asyncio
import configparser
import sqlite3


def set_alarm(alert_rate, uid, table):
    # Save it in the database
    with sqlite3.connect("nanexbot.sqlite3") as db:
        cursor = db.cursor()
        sql = 'INSERT INTO `{0}` (`user_id`, `price`, `active`) VALUES ("{1}", "{2}", "1")'.format(table, uid, alert_rate)
        cursor.execute(sql)
        db.commit()


def main():
    conf = configparser.RawConfigParser()
    conf.read("config.txt")

    BOT_TOKEN = conf.get('nanexbot_conf', 'BOT_TOKEN')

    client = discord.Client()

    async def get_last_rate(message):
        tmp = await client.send_message(message.channel, "Acquiring data from Nanex.co...")
        try:
            nano = requests.get("https://nanex.co/api/public/ticker/grlcnano", timeout=10)
        except requests.Timeout:
            await client.edit_message(tmp, "Acquiring data from Nanex.co... Timeout!")
            return None
        else:
             last_rate = float(nano.json()["last_trade"])

        if last_rate:
            await client.edit_message(tmp, "Acquiring data from Nanex.co... Done!")
            return last_rate
        else:
            await client.edit_message(tmp, "Acquiring data from Nanex.co... Error!")
            return None

    @client.event
    async def on_ready():
        print('Logged in as {} <@{}>'.format(client.user.name, client.user.id))
        print('------')

    @client.event
    async def on_message(message):
        # TODO: Allow the user to delete one alert
        # TODO: Allow the user to see his active alerts

        if message.content.startswith("$nanex"):
            last_rate = await get_last_rate(message)
            if last_rate:
                await client.send_message(message.channel, "Nanex last trade price is {:.5f} NANO".format(last_rate))
            else:
                # Timeout or error
                await client.edit_message(tmp, "Error : Couldn't get last trade price")

        if message.content.startswith("$sell") or message.content.startswith("$buy"):
            try:
                alert_rate = float(message.content.split(" ")[1].replace(",", "."))
                if message.content.startswith("$sell"):
                    table = "sell"
                else:
                    table = "buy"
            except IndexError:
                # Only $alert was sent
                await client.send_message(message.author, "Usage: ${0} [price in nano], ex: ${0} 0.00700".format(table))
            except ValueError:
                # Can't get the rate sent
                await client.send_message(message.author, "Usage: ${0} [price in nano], ex: ${0} 0.00700".format(table))
            else:
                set_alarm(alert_rate, message.author.id, table)
                await client.send_message(message.author, "{} alarm set for {:.5f} NANO".format(table.title(), alert_rate))

        if message.content.startswith("$help"):
            help_text = "<@{}>, I'm NanexBot, I'm here to assist you during your trades on Nanex.co!\n```" \
                        "$help         : Displays a list of commands and what they do\n" \
                        "$nanex        : Displays the current rate for GRLC\n" \
                        "$sell [price] : Sends you a PM when the last trade >= [price]\n" \
                        "$buy [price]  : Sends you a PM when the last trade <= [price]\n" \
                        "```".format(message.author.id)
            await client.send_message(message.author, help_text)
            await client.send_message(message.channel, "I PM'd you the list of commands")

    client.run(BOT_TOKEN)


if __name__ == "__main__":
    main()
