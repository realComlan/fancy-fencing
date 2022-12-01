from modules import *

if __name__ == "__main__":
	game_manager = GameManager.get_instance()
	#player1 = game_manager.player()
	#player1.defending_range = 3
	#player1.blocking_time = 19
	#player1.attacking_range = 100
	#player1.attacking_speed = 6
	#player1.movement_speed = 6

	#player2 = game_manager.player()
	#player2.defending_range = 3
	#player2.blocking_time = 19
	#player2.attacking_range = 100
	#player2.attacking_speed = 6
	#player2.movement_speed = 10
	
	game_manager.start()
	game_manager.stop()



