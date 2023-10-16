from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
import pickle
import time
import threading 
import random

# Definieren Sie hier Ihren Token
TOKEN = "<token>"

# Spielinitialisierung
game_state = {
	"board": [1, 2, 3, 4, 5, 6, 7, 8, 9],  # oder bis 12, je nach Spielversion
	"dice": [0, 0]
}

chat_data = {}

def start(update, context):
	context.bot.send_message(chat_id, "Welcome to 'Shut the Box'! Type /join to join a game. Once all players have joined, type /run to start the game.")

def join(update, context):
	chat_id = update.message.chat_id
	user = update.message.from_user

	if chat_id not in chat_data:
		chat_data[chat_id] = initialize_game_state()
	
	if chat_data[chat_id]['players'] and chat_data[chat_id]['board'] != list(range(1, 13)):
		context.bot.send_message(chat_id, f"The game has already started, @{user.username}. Please wait until it's over to join a new game.")
		return
	
	if user.id not in chat_data[chat_id]['players']:
		add_player(chat_id, user.id)
		context.bot.send_message(chat_id, f"@{user.username} has joined the game!")
	else:
		context.bot.send_message(chat_id, f"@{user.username} has already joined.")

def add_player(chat_id, user_id):
	game_state = chat_data[chat_id]
	if user_id not in game_state["players"]:
		game_state["players"].append(user_id)

def remove_player(chat_id, user_id):
	game_state = chat_data[chat_id]
	game_state["players"].remove(user_id)

		
def run(update, context):
	chat_id = update.message.chat_id
	user = update.message.from_user

	if chat_id not in chat_data or user.id not in chat_data[chat_id]['players']:
		context.bot.send_message(chat_id, "You must join the game before you can start it!")
		return
	
	if chat_id in chat_data:
		players = chat_data[chat_id]['players']
		if players:
			play_game(update, context)
		else:
			context.bot.send_message(chat_id, "No players have joined yet.")
	else:
		context.bot.send_message(chat_id, "No players have joined yet.")

def next_player(chat_id):
	game_state = chat_data[chat_id]
	game_state["current_player_index"] += 1
	if game_state["current_player_index"] >= len(game_state["players"]):
		game_state["current_player_index"] = 0
	game_state["board"] = initialize_game_state()["board"]

def initialize_game_state():
	return {
		"board": list(range(1, 10)),
		"dice": [],
		"players": [],
		"current_player_index": 0,
		"selected_numbers": []
	}

def play_game(update, context):
	chat_id = 0 
	if update.message:
		chat_id = update.message.chat_id
	elif update.callback_query:
		chat_id = update.callback_query.message.chat_id
		
	game_state = chat_data[chat_id]
	
	if chat_id not in chat_data:
		chat_data[chat_id] = initialize_game_state()

	current_player_id = game_state['players'][game_state["current_player_index"]]
	current_player = context.bot.get_chat_member(chat_id, current_player_id).user
	
	#if check_game_end(game_state):
	if not game_state["board"]:
		context.bot.send_message(chat_id, f"Congratulations, @{current_player.username}! You have 'Shut the Box' and won!")

	# Würfeln
	game_state["dice"] = [random.randint(1, 6), random.randint(1, 6)]
	
	dice_sum = sum(game_state["dice"])

	keyboard = []
	for number in game_state["board"]:
		keyboard.append([InlineKeyboardButton(str(number), callback_data=str(number))])

	time.sleep(1)
		
	reply_markup = InlineKeyboardMarkup(keyboard)
	context.bot.send_message(chat_id, f"Roll result: {game_state['dice'][0]} and {game_state['dice'][1]} (Total: {dice_sum}). Choose the number to flip @{current_player.username}:", reply_markup=reply_markup)
	
	if not is_valid_move_available(game_state["dice"], game_state["board"]):
		context.bot.send_message(chat_id, "No valid move available. Next player is up!")
		next_player(chat_id)
		play_game(update, context)
		return

def button(update, context):
	query = update.callback_query
	chat_id = query.message.chat_id
	game_state = chat_data[chat_id]
	user = query.from_user

	# Überprüfen, ob der Benutzer an der Reihe ist
	current_player_id = game_state['players'][game_state["current_player_index"]]
	if user.id != current_player_id:
		context.bot.send_message(chat_id, text="It's not your turn!")
		return

	number_selected = int(query.data)
	
	if number_selected not in game_state["board"]:
		context.bot.send_message(chat_id, text=f"{number_selected} has already been selected. Please choose another number.")
		return

	game_state["selected_numbers"].append(number_selected)

	# Ein vorläufiges Feedback für den Spieler, um ihn über seine bisherige Auswahl zu informieren
	if sum(game_state["dice"]) == number_selected or number_selected in game_state["dice"]:
		for num in game_state["selected_numbers"]:
			game_state["board"].remove(num)
		game_state["selected_numbers"].clear()
		# Überprüfen, ob das Spiel gewonnen wurde
		if not game_state["board"]:
			context.bot.send_message(player_id, text=f"Congratulations, {user.first_name}! You have 'Shut the Box' and won!")
			chat_data.pop(chat_id, None)
			return
		context.bot.send_message(chat_id, text=f"{user.first_name} hat eine gültige Auswahl getroffen.")
		play_game(update, context)
	else:
		game_state["selected_numbers"].clear()

		dice_sum = sum(game_state["dice"])
	
		context.bot.send_message(chat_id, f"Invalid selection.\n\nRoll result: {game_state['dice'][0]} and {game_state['dice'][1]} (Total: {dice_sum}). Next player is up!")
		next_player(chat_id)
		play_game(update, context)
	return

def restart_game(update, context):
	query = update.callback_query
	chat_id = query.message.chat_id

	chat_data[chat_id] = initialize_game_state()
	context.bot.send_message(chat_id, text="The game has been reset. Type /join to join again!")

def is_valid_move_available(dice, board):
	dice_sum = sum(dice)
	for num in board:
		if num == dice[0] or num == dice[1] or num == dice_sum:
			return True
	return False

def check_game_end(game_state):
	# Überprüfen, ob ein Spieler gewonnen hat
	if not game_state["board"]:
		return True
	# Überprüfen, ob es unmöglich ist, mit den aktuellen Würfen fortzufahren
	elif not is_valid_move_available(game_state["dice"], game_state["board"]):
		return True
	return False

def main():
	load_game_data()
	updater = Updater(token=TOKEN, use_context=True)

	dp = updater.dispatcher
	dp.add_handler(CommandHandler("start", start))
	dp.add_handler(CommandHandler("join", join))
	dp.add_handler(CommandHandler("run", run))
	dp.add_handler(CallbackQueryHandler(restart_game, pattern="^restart_game$"))
	dp.add_handler(CallbackQueryHandler(button))

	threading.Thread(target=auto_save).start()
	updater.start_polling()
	updater.idle()

def auto_save():
	while True:
		time.sleep(300)  # 5 Minuten
		save_game_data()
	
def save_game_data():
	with open("game_data.pkl", "wb") as f:
		pickle.dump(chat_data, f)

def load_game_data():
#	global chat_data
	try:
		with open("game_data.pkl", "rb") as f:
			data = pickle.load(f)
			if "board" in data and "players" in data and "dice" in data:
				chat_data = data
			else:
				chat_data = {}
				# Optional: Logging des Fehlers
	except FileNotFoundError:
		chat_data = {}

if __name__ == '__main__':
	main()
