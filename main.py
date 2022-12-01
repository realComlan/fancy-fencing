from modules import *

if __name__ == "__main__":
	args=[]
	for arg in sys.argv[1:]:
		v=arg.split("=")
		arg[v[0]]=v[1]
	
	scene_file = "default.ffscene"
	game_manager = GameManager.get_instance(scene_file)
	print("game manager = ", game_manager)
	player1 = game_manager.player()
	player1.defending_range = 3
	player1.blocking_time = 19
	player1.attacking_range = 100
	player1.attacking_speed = 6
	player1.movement_speed = 6

	player2 = game_manager.player()
	player2.defending_range = 3
	player2.blocking_time = 19
	player2.attacking_range = 100
	player2.attacking_speed = 6
	player2.movement_speed = 10
	
	if game_manager.all_good():
		game_manager.start()
		game_manager.stop()



