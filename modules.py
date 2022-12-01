import sys
import os
from time import sleep
from pynput import keyboard
from collections import deque
from enum import Enum
import threading
import random
import numpy as np
import re 
from math import sqrt
import getopt
import pickle

class Move(Enum):
	LEFT = 'l'
	RIGHT = 'r'
	UP = 'u'
	DOWN = 'd'

class State(Enum):
	I_REST = 'r'
	I_ATTACK = 'a'
	I_END_ATTACK = 'a_e'
	I_DEFEND = 'f'
	I_END_DEFENSE = 'f_e'

class Block:
	def __init__(self, pos_x):
		self.pos_x = int(pos_x)
		self.color = [Paint.bg_blue, Paint.bg_cyan, Paint.bg_yellow, Paint.bg_red, Paint.bg_green][random.randint(0,4)]

	def __str__(self):
		return self.color.format(" ")

class Player:
	__num_players = 0
	pass

class GuiPlayer(Player):
	
	def __init__(self):	
		self.body = dict()
		# Right facing bodies at index 0 and left facing body at 1
		self.body[State.I_REST] = None
		self.body[State.I_ATTACK] = None
		self.body[State.I_DEFEND] = None

	def draw(self):
		return self.body[self.state]

class AIPlayer(Player):
	def generate_commands(self):
		other_player_pos_x = self.scene.players[1-self.who].pos_x

class GuiAIPlayer(GuiPlayer):
	"""
	An AI graphical player
	"""
	pass

class HumanPlayer(Player):
	"""
	A player guided by a human playing on keyboard
	"""
	I_REST = 0
	I_ATTACK = 1
	I_DEFEND = 2
	I_JUMP = 3
	I_DIE = 4
	I_WON = 5
	HEIGHT = 4
	WIDTH = 9

	def __init__(self, auto=False):
		self.__who = Player.__num_players
		self.__score = 0
		self.auto = auto
		self.state = State.I_REST
		self.__pos_x = 0
		self.__pos_y = HumanPlayer.HEIGHT
		self.game = None
		self.facing_right = self.who == 0
		self.color = Paint.fg_cyan if self.who == 0 else Paint.fg_red
		self.update_body()
		Player.__num_players += 1
		self.pending_motions = deque()
		self.pending_states = deque()

	def game(self, game):
		self.game = game

	def flip(self):
		"""
		If the two players have exchanged positions, their body needs an update
		"""
		self.facing_right = not self.facing_right
		self.update_body()

	def draw(self):
		"""
		The player returns to the Scene.print_game(...) a representation of his body
		"""
		pic = np.tile([Scene.AIR*self.width], (Scene.HEIGHT-self.pos_y))
		pic = np.concatenate((pic, self.body), axis=0)
		pic = np.concatenate((pic, np.tile([Scene.AIR*self.width], (self.pos_y-self.height))), axis=0)
		pic = pic.reshape(len(pic), 1)
		return pic
	
	def update_body(self):
		"""
		Each time a player changes his state he needs to update his body
		"""
		needs_flip = False
		if self.state == State.I_REST:
			self.body =np.array([
				"|_O      ",\
				"  |`-)---",\
				"  |\\     ",\
				" /  |    "])
			needs_flip = not self.facing_right
		elif self.state == State.I_ATTACK:
			self.body = np.array([
				"     O_\\ ~",\
				"---(-'\\ ~ ",\
				"     /|  ~",\
				"    /  \\ ~"])
			needs_flip = self.facing_right
		elif self.state == State.I_DEFEND:
			self.body = np.array([
			"|     ",\
			"|  O_\\",\
			"|-'_\\ ",\
			" /  |_"])
			needs_flip = self.facing_right
		# If the drawing we made is not facing the direction of the current player
		# we flip it.
		if needs_flip:
			#We draw one thing facing a certain direction and find its mirror image
			#We do it using a temporary placeholder which is # just like when 
			# you want to exchange the values of two variables a and b, you use 
			# a third temporary variable c and do: c = a, a = b, b = a.
			self.body = [s.replace('/','#') for s in self.body]
			self.body = [s.replace('\\','/') for s in self.body]
			self.body = [s.replace('#','\\') for s in self.body]
			self.body = [s.replace('`','#') for s in self.body]
			self.body = [s.replace("'",'`') for s in self.body]
			self.body = [s.replace('#',"'") for s in self.body]
			self.body = [s.replace(')','#') for s in self.body]
			self.body = [s.replace('(',')') for s in self.body]
			self.body = [s.replace('#','(') for s in self.body]
			self.body = [s[::-1] for s in self.body]
		self.height = len(self.body)
		self.width = len(self.body[0])
		self.body = np.array([self.color.format(_) for _ in self.body])
			
	def execute(self):
		if len(self.pending_motions) > 0:
			command = self.pending_motions.popleft()
			if command == Move.LEFT:
				self.move_left()
			elif command == Move.RIGHT:
				self.move_right()
			elif command == Move.UP:
				self.move_up()
			elif command == Move.DOWN:
				self.move_down()

		if len(self.pending_states) > 0:
			state = self.pending_states.popleft()
			if state == State.I_ATTACK:
				self.attack()
			elif state == State.I_END_ATTACK:
				self.end_attack()
			elif state == State.I_DEFEND:
				self.defend()
			elif state == State.I_END_DEFENSE:
				self.end_defense()
		
	def receive_command(self, key):
		received = False
		if self.who == 0:
			if key == "'q'" or key == "'Q'": #left
				if len(self.pending_motions) != 0:
					last_move = self.pending_motions.pop()
					if last_move != Move.RIGHT:
						self.pending_motions.extend([last_move, Move.LEFT])	
				else:
					self.pending_motions.extend([Move.LEFT])	
				received = True
			elif key == "'d'" or key == "'D'": #right
				if len(self.pending_motions) > 0:
					last_move = self.pending_motions.pop()
					if last_move != Move.LEFT:
						self.pending_motions.extend([last_move, Move.RIGHT])	
				else:
					self.pending_motions.extend([Move.RIGHT])
				received = True
			elif key == "'a'" or key == "'A'": #jumping left
				m_s = self.movement_speed
				self.pending_motions.extend(([Move.UP]*m_s)+([Move.LEFT]*m_s)+([Move.DOWN]*m_s))
				received = True
			elif key == "'e'" or key == "'E'": #jumping right
				m_s = self.movement_speed
				self.pending_motions.extend(([Move.UP]*m_s)+([Move.RIGHT]*m_s)+([Move.DOWN]*m_s))
				received = True
			elif key == "'z'" or key == "'Z'": #attacking
				a_s = self.attacking_speed
				direction = Move.RIGHT if self.facing_right else Move.LEFT
				self.pending_motions.extend([direction]*a_s)
				self.pending_states.extend(([State.I_ATTACK]*(a_s-1))+[State.I_END_ATTACK])
				received = True
			elif key == "'s'" or key == "'S'": #blocking
				b_s = self.blocking_time-1
				self.pending_states.extend(([State.I_DEFEND]*b_s)+[State.I_END_DEFENSE])
				received = True
		elif self.who == 1:
			if key == 'Key.left': #left
				if len(self.pending_motions) > 0:
					last_move = self.pending_motions.pop()
					if last_move != Move.RIGHT:
						self.pending_motions.extend([last_move, Move.LEFT])	
				else:
					self.pending_motions.extend([Move.LEFT])	
				received = True
			elif key == 'Key.right': #right
				if len(self.pending_motions) > 0:
					last_move = self.pending_motions.pop()
					if last_move != Move.LEFT:
						self.pending_motions.extend([last_move, Move.RIGHT])	
				else:
					self.pending_motions.extend([Move.RIGHT])	
				received = True
			elif key == "'l'" or key == "'L'": #jumping left
				m_s = self.movement_speed
				self.pending_motions.extend(([Move.UP]*m_s)+([Move.LEFT]*m_s)+([Move.DOWN]*m_s))
				received = True
			elif key == "'m'" or key == "'M'": #jumping right
				m_s = self.movement_speed-1
				self.pending_motions.extend(([Move.UP]*m_s)+([Move.RIGHT]*m_s)+([Move.DOWN]*m_s))
				received = True
			elif key == "'o'" or key == "'O'": #attacking
				a_s = self.attacking_speed
				direction = Move.RIGHT if self.facing_right else Move.LEFT
				self.pending_motions.extend([direction]*a_s)
				self.pending_states.extend(([State.I_ATTACK]*(a_s-1))+[State.I_END_ATTACK])
				received = True
			elif key == "'p'" or key == "'P'": #blocking
				b_s = self.blocking_time-1
				self.pending_states.extend(([State.I_DEFEND]*b_s)+[State.I_END_DEFENSE])
				received = True
		return received
				
	def move_left(self, step=1):
		#for b in self.game.scene.blocks:
		#	if b.pos_x == self.pos_x-step and self.pos_y==self.height:
		#		return
		self.pos_x -= step

	def move_right(self, step=1):
		#for b in self.game.scene.blocks:
		#	if b.pos_x == self.pos_x+step and self.pos_y==self.height:
		#		return
		self.pos_x += step

	def move_up(self, step=1):
		self.pos_y += step

	def move_down(self, step=1):
		self.pos_y -= step

	def attack(self):
		if self.state != State.I_ATTACK:
			self.state = State.I_ATTACK
			self.update_body()
	
	def end_attack(self):
		adversary =  self.game.scene.players[1 - self.who]
		his_her_state = adversary.state 
		dist_to_him_her = sqrt(abs(self.pos_x-adversary.pos_x)**2+abs(self.pos_y-adversary.pos_y)**2)
		if his_her_state == State.I_DEFEND\
			or dist_to_him_her > self.attacking_range:
			Game.PLAYER_FAILED |= (1<<self.who)
		else:
			Game.PLAYER_SUCCEEDED |= (1<<self.who)
		self.state = State.I_REST
		self.update_body()

	def defend(self):
		if self.state != State.I_DEFEND:
			self.state = State.I_DEFEND
			self.update_body()
		
	def end_defense(self):
		self.state = State.I_REST
		self.update_body()

	@property
	def pos_x(self):
		return self.__pos_x

	@pos_x.setter
	def pos_x(self, pos_x):
		if 0 < pos_x < Scene.WIDTH:
			self.__pos_x = pos_x
		#self.__pos_x = max(0, pos_x)
		#self.__pos_x = min(pos_x, Scene.WIDTH)

	@property
	def pos_y(self):
		return self.__pos_y

	@pos_y.setter
	def pos_y(self, pos_y):
		if 0 < pos_y < Scene.HEIGHT:
			self.__pos_y = pos_y
		#self.__pos_y = max(0, pos_y)
		#self.__pos_y = min(pos_y, Scene.HEIGHT)

	@property
	def who(self):
		return self.__who

	@who.setter
	def who(self, me):
		self.__who = me

	@property
	def num_players(cls):
		return cls.__num_players

	@property
	def defending_range(self):
		return self.__defending_range
	
	@defending_range.setter
	def defending_range(self, param):
		self.__defending_range  = max(1,param)

	@property
	def blocking_time(self):
		return self.__blocking_time
		
	@blocking_time.setter	
	def blocking_time(self, param):
		self.__blocking_time  = max(1,param)

	@property
	def attacking_range(self):
		return self.__attacking_range

	@attacking_range.setter
	def attacking_range(self, param):
		self.__attacking_range  = max(1,param)

	@property
	def attacking_time(self):
		return self.__attacking_time

	@attacking_range.setter
	def attacking_time(self, param):
		self.__attacking_time = max(1,param)
		
	@property
	def movement_speed(self):
		return self.__movement_speed

	@movement_speed.setter
	def movement_speed(self, param):
		self.__movement_speed  = max(1,param)

	@property
	def score(self):
		return self.__score

	@score.setter
	def score(self, score):
		self.__score = score

class GuiHumanPlayer(HumanPlayer):
	pass

class Paint:
	fg_red = "\033[91m{}\033[00m"
	fg_green = "\033[92m{}\033[00m"
	fg_yellow = "\033[93m{}\033[00m"
	fg_light_purple = "\033[94m{}\033[00m"
	fg_purple = "\033[95m{}\033[00m"
	fg_cyan = "\033[96m{}\033[00m"
	fg_light_gray = "\033[97m{}\033[00m"
	fg_black = "\033[98m{}\033[00m"
	bg_red = "\x1b[41m{}\033[00m"	#background red
	bg_green = "\x1b[42m{}\033[00m" 	#background green
	bg_yellow = "\x1b[43m{}\033[00m"	#background yellow
	bg_blue = "\x1b[44m{}\033[00m"	#background blue
	bg_magenta = "\x1b[45m{}\033[00m"	#background magenta
	bg_cyan = "\x1b[46m{}\033[00m"	#background cyan
	bg_white = "\x1b[47m{}\033[00m"	#background white
	# This is used to correct the centering of colored lines 
	# Inspiration from https://stackoverflow.com/questions/14889454\
	#     /printed-length-of-a-string-in-python#:~:text=The%20printed\
	#     %20length%20of%20a%20string%20depends%20on,utf-8%20is%20equal
	#     %20to%20the%20bytes%20in%20String.
	strip_ANSI_pattern = re.compile(r"""
   	 \x1b     # literal ESC
   	 \[       # literal [
   	 [;\d]*   # zero or more digits or semicolons
   	 [A-Za-z] # a letter
   	 """, re.VERBOSE).sub

class Scene:
	HEIGHT = 10
	WIDTH = 100
	GOLDEN_RATIO = 233/144
	AIR = " "
	default_scene = "___1______x__2______"
	
	def __init__(self, scene_layout, fps=24):
		self.players = []
		self.scene_layout = scene_layout
		self.fps = fps
		self.pending = deque()
		self.attack_show_duration = self.fps*2
		self.adjust_size_to_terminal()
		self.blocks = np.array([])
		self.anew = True
		self.attacked_player = 0
		blocks = re.finditer(r'[xX]', self.scene_layout)
		for b in blocks:
			self.blocks = np.append(self.blocks, int(b.span()[0]
					* (Scene.WIDTH-2*HumanPlayer.WIDTH+2)\
					/len(self.scene_layout)))
		self.blocks.astype(int)
		self.blocks = np.array([Block(x) for x in self.blocks])
		print(self.blocks)
		self.collisions = np.array([
			[
			"       X       ",\
			"|_O   / \\  O_\\ ",\
			"  |`-/   \\-'\\  ",\
			"  |\\       / \\ ",\
			" /  \\      |  \\"],\
			[
			"     \\ /     ",\
			"|_O   X  O_\\ ",\
			"  |`-/ \\-'\\  ",\
			"  |\\     / | ",\
			" /  |    |  \\"],\
			[
			"     \\ /     ",\
			" |_O  X  O_\\ ",\
			"  /`-/ \\-'\\  ",\
			" |\\      / | ",\
			"/  \\     |  \\"],\
			[
			"       /       ",\
			"  /_O  X        ",\
			"   /`-/ \\  O_\\  ",\
			"  | \\    \\-'\\   ",\
			" /  /      / \\ ",\
			"          |  \\"],
			[
			"       /        ",\
			"  _O  X         ",\
			" \\/`-/ \\   O_\\  ",\
			" | \\    \\-'_\\   ",\
			"/  /       \ |_ "]
			], dtype=object)
		
		self.swords = np.array([
			[" _     |\\                            ",
			 "[_[[[[[| |==========================>",
			 "       |/                            "]])	
		self.wrap_drawings()
	
	def loop(self):	
		if self.anew:
			self.position_players()
			self.anew = False
		self.update_scoreboard()
		Game.IS_PLAYING = not Game.IS_PAUSED and not Game.IS_STOPPED
		while Game.IS_PLAYING:
			self.clear_scene()
			self.execute_commands()
			if Game.PLAYER_SUCCEEDED > 0:
				self.attack_succeeded_by(Game.PLAYER_SUCCEEDED-1)
			if Game.PLAYER_FAILED > 0:
				self.attack_failed_by(Game.PLAYER_FAILED-1)
			self.print_game()
			sleep(1/self.fps)
			Game.IS_PLAYING = not Game.IS_PAUSED and not Game.IS_STOPPED
		
		Game.IS_PAUSED = not Game.IS_PLAYING and not Game.IS_STOPPED
		while Game.IS_PAUSED and not Game.IS_GRAPHICAL:
			self.clear_scene()
			self.print_pause_screen()
			sleep(1/self.fps)
			Game.IS_PAUSED = not Game.IS_PLAYING and not Game.IS_STOPPED
		
		# We go back to playing
		if Game.IS_PLAYING and not Game.IS_GRAPHICAL:
			self.loop()

		# We go graphical
		if Game.IS_PLAYING and Game.IS_GRAPHICAL:
			self.graphical_loop()

		# If Game is not paused nor playing, then it is over!
		if Game.IS_STOPPED:
			self.print_goodbye_screen()
	
	def graphical_loop(self):
		elif Game.IS_STOPPED and not Game.IS_GRAPHICAL:
			# We go back to the terminal loop
			self.loop()
		
	def pause(self):
		while Game.IS_PAUSED:
			#self.clear_scene()
			self.print_pause_screen()
			sleep(1/self.fps)

	def execute_commands(self):
		self.players[0].execute()
		self.players[1].execute()
		if self.players[0].facing_right and self.players[0].pos_x > self.players[1].pos_x\
			or self.players[1].facing_right and self.players[1].pos_x > self.players[0].pos_x:
			self.players[0].flip()
			self.players[1].flip()
			
	def print_game(self):
		"""
		Print the game
		"""
		width = Scene.WIDTH+self.players[0].WIDTH+self.players[1].WIDTH
		# Print the scoreboard
		topboard = ('-'*width).center(Scene.WINDOW_WIDTH)
		topboard += Paint.bg_green.format(('Type <space> for the MENU, <esc> to QUIT.').center(Scene.WINDOW_WIDTH))
		topboard += self.scoreboard
		# If no close contact fight(collision) is going on...
		if len(self.pending) == 0:
			player1 = self.players[0] if self.players[0].facing_right else self.players[1]
			player2 = self.players[1] if self.players[0].facing_right else self.players[0]
			# Print the players 
			p1 = player1.draw()
			p2 = player2.draw()
			playground = np.tile([Scene.AIR], (Scene.HEIGHT, player1.pos_x))
			playground = np.concatenate((playground, p1), axis=1)
			playground = np.concatenate((playground, np.tile([Scene.AIR], (Scene.HEIGHT, (player2.pos_x-player1.pos_x)))), axis=1)
			playground = np.concatenate((playground, p2), axis=1)
			playground = np.concatenate((playground, np.tile([Scene.AIR], (Scene.HEIGHT, (Scene.WIDTH-player2.pos_x)))), axis=1)
		# If collision is going on...
		else:
			state = self.pending.popleft()
			if state == 'end':
				self.position_players()
				self.update_scoreboard(-1)
			playground = np.tile([Scene.AIR], (Scene.HEIGHT, self.players[self.attacked_player].pos_x))
			selected_collision = int(len(self.collisions)*len(self.pending)/self.attack_show_duration)
			selected_collision = min(selected_collision, len(self.collisions)-1)
			playground = np.concatenate((playground, self.collisions[selected_collision].reshape(len(playground),1)), axis=1)
			playground = np.concatenate((playground, np.tile([Scene.AIR], (Scene.HEIGHT, \
					(Scene.WIDTH+len(self.collisions[selected_collision])-self.players[self.attacked_player].pos_x-1)))), axis=1)
		#player1_on_ground = self.players[0].pos_y == self.players[0].height
		#player2_on_ground = self.players[1].pos_y == self.players[1].height
		for b in self.blocks:
			if (self.players[0].pos_x-1 < b.pos_x < self.players[0].pos_x+self.players[0].width) or \
				(self.players[1].pos_x-1 < b.pos_x < self.players[1].pos_x+self.players[1].width):
				continue
			playground[-1,b.pos_x] = str(b)
		playground = [''.join(line).center(Scene.WINDOW_WIDTH) for line in playground]
		# Let's add the following line to correct the misalignment at printing of colored lines. 
		# In fact for colored lines the str.center(length...) would center the representation.
		# But the printed version of colored strings is shorter than their representation, which is why their
		# centering needs the following correction...
		playground = [(' '*((Scene.WINDOW_WIDTH-self.printed_length(line))//2))\
					+line+\
					(' '*((Scene.WINDOW_WIDTH-self.printed_length(line))//2)) for line in playground]
		playground = ''.join(playground)
		playground += ("*"*width).center(Scene.WINDOW_WIDTH)
		playground += ("-"*width).center(Scene.WINDOW_WIDTH)

		print(topboard+playground)

	def print_pause_screen(self):
		"""
		Print the pause menu.
		"""
		pause_menu = Paint.bg_blue.format('<PAUSE>'.center(Scene.WINDOW_WIDTH))+'\n'+'\n'
		pause_menu += " ____  __    _  _  ___  _  _    ____  ____  _  _  ___  ____  _  _  ___ ".center(Scene.WINDOW_WIDTH)
		pause_menu += "( ___)/__\  ( \( )/ __)( \/ )  ( ___)( ___)( \( )/ __)(_  _)( \( )/ __)".center(Scene.WINDOW_WIDTH)
		pause_menu += " )__)/(__)\  )  (( (__  \  /    )__)  )__)  )  (( (__  _)(_  )  (( (_-.".center(Scene.WINDOW_WIDTH)
		pause_menu += "(__)(__)(__)(_)\_)\___) (__)   (__)  (____)(_)\_)\___)(____)(_)\_)\___/".center(Scene.WINDOW_WIDTH)+'\n'+'\n'
		pause_menu += 'To resume the game: press <space> again.'.center(Scene.WINDOW_WIDTH)+'\n'+'\n'
		pause_menu += 'To restart a new game: press <n> again.'.center(Scene.WINDOW_WIDTH)+'\n'+'\n'
		pause_menu += 'To quit the game (without saving): press <esc>.'.center(Scene.WINDOW_WIDTH)+'\n'+'\n'
		pause_menu += 'To save the game at this state of execution: press <enter>.'.center(Scene.WINDOW_WIDTH)+'\n'+'\n'
		pause_menu += 'To load THE LAST previously saved game(if one exists): press <shift>.'.center(Scene.WINDOW_WIDTH)+'\n'+'\n'
		pause_menu += 'To launch the graphical version: press <g>.'.center(Scene.WINDOW_WIDTH)+'\n'+'\n'
		print(pause_menu)

	def print_goodbye_screen(self):
		pass

	def printed_length(self, s):
		"""
		The printed length of the string s
		We simply strip out all the ANSI colors codes
		"""
		return len(Paint.strip_ANSI_pattern("", s))

	def adjust_size_to_terminal(self):
		size = os.get_terminal_size()
		Scene.WIDTH = size.columns//2
		Scene.HEIGHT = int(Scene.WIDTH/Scene.GOLDEN_RATIO/2)
		Scene.WINDOW_WIDTH = size.columns# if size.columns%2==0 else size.columns-1
		
	def add_player(self, player):
		self.players.append(player)

	def attack_succeeded_by(self, by_whom):
		Game.PLAYER_SUCCEEDED = 0
		random.shuffle(self.collisions) 
		print(self.collisions)
		# by_whom is equal to 2 when and only when both players have updated the Game.PLAYER_SUCCEEDED attribute
		# which means that they both succeeded an attack simultaneously. In this case no point is 
		# given to any player. Otherwise, we give one point to the one who succeeded (player with
		# index by_whom).
		if by_whom == 0 or by_whom == 1:
			self.players[by_whom].score += 1
		self.attacked_player = -2 if by_whom > 1 else 1-by_whom
		self.pending.extend(['success']*self.attack_show_duration+['end'])
		for player in self.players:
			player.pending_motions.clear()
			player.pending_states.clear()
		self.update_scoreboard(by_whom)
		self.collisions = self.success_collisions

	def attack_failed_by(self, by_whom):
		Game.PLAYER_FAILED = 0
		random.shuffle(self.collisions) 
		print(self.collisions)
		self.pending.extend(['failure']*self.attack_show_duration+['end'])
		self.attacked_player = -1
		for player in self.players:
			player.state = State.I_REST
			player.pending_motions.clear()
			player.pending_states.clear()
		self.collisions = self.failure_collisions
	
	def wrap_drawings(self, color=Paint.fg_green):
		#We draw one thing facing a certain direction and find its mirror image
		#We do it using a temporary placeholder which is # just like when 
		# you want to exchange the values of two variables a and b, you use 
		# a third temporary variable c and do: c = a, a = b, b = a.
		def mirror_flip(drawing):
			drawing = np.array([s.replace('/','#') for s in drawing])
			drawing = np.array([s.replace('\\','/') for s in drawing])
			drawing = np.array([s.replace('#','\\') for s in drawing])
			drawing = np.array([s.replace('`','#') for s in drawing])
			drawing = np.array([s.replace("'",'`') for s in drawing])
			drawing = np.array([s.replace('#',"'") for s in drawing])
			drawing = np.array([s.replace(')','#') for s in drawing])
			drawing = np.array([s.replace('(',')') for s in drawing])
			drawing = np.array([s.replace('#','(') for s in drawing])
			drawing = np.array([s.replace('[','#') for s in drawing])
			drawing = np.array([s.replace(']','[') for s in drawing])
			drawing = np.array([s.replace('#',']') for s in drawing])
			drawing = np.array([s.replace('>','#') for s in drawing])
			drawing = np.array([s.replace('<','>') for s in drawing])
			drawing = np.array([s.replace('#','<') for s in drawing])
			drawing = np.array([s[::-1] for s in drawing])
			return drawing
		nb_collisions = len(self.collisions)
		#for collision in self.collisions[:nb_collisions]:
		#	print(self.collisions)
		#	self.collisions = np.concatenate((self.collisions, [mirror_flip(collision)]), axis=0)
		self.collisions = np.array([([Scene.AIR*len(c[0])] * (Scene.HEIGHT-len(c)))+c for c in self.collisions])
		self.success_collisions = np.array([[Paint.fg_yellow.format(_) for _ in collision] for collision in self.collisions])	
		self.failure_collisions = np.array([[_ for _ in collision] for collision in self.collisions])	
		self.swords = np.concatenate((self.swords, [[_ for _ in mirror_flip(self.swords[0])]]), axis=0)
		self.swords = np.concatenate((self.swords, [[Paint.fg_cyan.format(_) for _ in self.swords[0]]]), axis=0)
		self.swords = np.concatenate((self.swords, [[Paint.fg_red.format(_) for _ in self.swords[1]]]), axis=0)
		
	def position_players(self):
		for player in self.players:
			player.pos_x = int(self.scene_layout.find(str(player.who+1))\
					* (Scene.WIDTH-2*HumanPlayer.WIDTH+2)\
					/len(self.scene_layout))
			player.pos_y = player.height


	def update_scoreboard(self, by_whom=-1):
		scores = "| "+str(self.players[0].score)+" | "+str(self.players[1].score) + " |"
		if by_whom == 0:
			p1 = (self.swords[2][0]+(' '*5)+('-'*len(scores))+(' '*5)+self.swords[1][0]).center(Scene.WINDOW_WIDTH)
			scoreboard = (self.swords[2][1]+(' '*5)+scores+(' '*5)+self.swords[1][1]).center(Scene.WINDOW_WIDTH)
			p2 = (self.swords[2][2]+(' '*5)+('-'*len(scores))+(' '*5)+self.swords[1][2]).center(Scene.WINDOW_WIDTH)
		elif by_whom == 1:
			p1 = (self.swords[0][0]+(' '*5)+('-'*len(scores))+(' '*5)+self.swords[3][0]).center(Scene.WINDOW_WIDTH)
			scoreboard = (self.swords[0][1]+(' '*5)+scores+(' '*5)+self.swords[3][1]).center(Scene.WINDOW_WIDTH)
			p2 = (self.swords[0][2]+(' '*5)+('-'*len(scores))+(' '*5)+self.swords[3][2]).center(Scene.WINDOW_WIDTH)
		elif by_whom == -1:
			p1 = (self.swords[0][0]+(' '*5)+('-'*len(scores))+(' '*5)+self.swords[1][0]).center(Scene.WINDOW_WIDTH)
			scoreboard = (self.swords[0][1]+(' '*5)+scores+(' '*5)+self.swords[1][1]).center(Scene.WINDOW_WIDTH)
			p2 = (self.swords[0][2]+(' '*5)+('-'*len(scores))+(' '*5)+self.swords[1][2]).center(Scene.WINDOW_WIDTH)
		elif by_whom == 2:
			p1 = (self.swords[2][0]+(' '*5)+('-'*len(scores))+(' '*5)+self.swords[3][0]).center(Scene.WINDOW_WIDTH)
			scoreboard = (self.swords[2][1]+(' '*5)+scores+(' '*5)+self.swords[3][1]).center(Scene.WINDOW_WIDTH)
			p2 = (self.swords[2][2]+(' '*5)+('-'*len(scores))+(' '*5)+self.swords[3][2]).center(Scene.WINDOW_WIDTH)
		p1 = (' '*((Scene.WINDOW_WIDTH-self.printed_length(p1))//2))+p1+(' '*((Scene.WINDOW_WIDTH-self.printed_length(p1))//2))
		scoreboard = (' '*((Scene.WINDOW_WIDTH-self.printed_length(scoreboard))//2))+scoreboard+(' '*((Scene.WINDOW_WIDTH-self.printed_length(scoreboard))//2))
		p2 = (' '*((Scene.WINDOW_WIDTH-self.printed_length(p2))//2))+p2+(' '*((Scene.WINDOW_WIDTH-self.printed_length(p2))//2))
		self.scoreboard = p1+scoreboard+p2
		
	def clear_scene(self):
		if os.name == 'posix':
			os.system('clear')
		else:
			os.system('cls')
	
class GuiScene:
	HEIGHT = 233
	WIDTH = 144

	def __init__(self):
		pass

	def start(self):
		pass 

class Game:
	IS_INITIALIZED = False
	IS_PLAYING = False
	IS_PAUSED = False
	IS_STOPPED = False
	IS_GRAPHICAL = False
	PLAYER_SUCCEEDED = 0
	PLAYER_FAILED = 0

	def __init__(self, scene_file):
		self.scene = self.set_scene(scene_file) 
		Game.IS_INITIALIZED = True

	def start(self):
		Game.IS_PAUSED = False
		Game.IS_PLAYING = True
		self.scene.loop()

	def pause(self):
		Game.IS_PAUSED = True
		Game.IS_PLAYING = False
		self.scene.pause()
	
	def stop(self):
		Game.IS_PAUSED = False
		Game.IS_PLAYING = False
		Game.STOPPED = True
	
	@property
	def score_unit(self):
		return self.__score_unit

	@score_unit.setter
	def score_unit(self, score_unit):
		self.__score_unit = score_unit

	def score_plus(self, player):
		player.score += self.score_unit

	def score_minus(self, player):
		player.score -= self.score_unit

	def add_player(self, player):
		player.game = self
		self.scene.add_player(player)

	def set_scene(self, scene_file):
		scene_layout = Scene.default_scene
		with open(scene_file) as file:
			scene_layout = file.readline().strip()
		self.scene = Scene(scene_layout)
		return self.scene

class GameManager:
	instance = None

	def __init__(self, scene_file="default.ffscene", gui=False):
		self.gui = gui
		self.game = Game(scene_file)
	
	def get_instance(self, scene_file="default.ffscene", gui=False):
		if GameManager.instance is None or GameManager.instance.scene_file != scene_file:
			GameManager.instance = GameManager(scene_file, gui)
		return GameManager.instance

	def all_good(self):
		return True
		
	def start(self):
		listener = keyboard.Listener(on_press=self.key_pressed, suppress=True)
		listener.start()
		self.game.start()
	
	def pause(self):
		self.game.pause()
	
	def stop(self):
		self.game.stop()
	
	def set_scene(self, scene_file):
		self.game.set_scene(scene_file)
	
	def save_game(self):
		print("save game")
		# Serialization
		with open("game.pickle", "wb") as outfile:
	    		pickle.dump(GameManager.instance, outfile)
		print("Written object", self)

	def load_game(self):
		print("loading game")
		# Deserialization
		with open("game.pickle", "rb") as infile:
			GameManager.instance = pickle.load(infile)
			self.game.scene.players = GameManager.instance.game.scene.players
		print("Reconstructed object", self)

	def key_pressed(self, key):
		key = str(key)
		if key == 'Key.esc':
			self.stop()
			Game.IS_STOPPED = True
			return
		elif key == 'Key.space':
			# We flip from pause to playing with 
			# with the same key
			if not Game.IS_PAUSED:
				Game.IS_PAUSED = True
			else:
				Game.IS_PLAYING = True
			return
		elif (key == "'n'" or key == "'N'") and Game.IS_PAUSED:
			Game.IS_PLAYING = True
			self.anew = True
			return
		elif (key == "'g'" or key == "'G'") and Game.IS_PAUSED:
			Game.IS_GRAPHICAL = True
			self.anew = True
			return
		elif key == "Key.enter" and Game.IS_PAUSED:
			self.save_game()
			return
		elif (key == "Key.shift_r" or key == "Key.shift_l") and Game.IS_PAUSED:
			self.load_game()
			return
			
		#hotkey = keyboard.HotKey([keyboard.Key.ctrl, keyboard.KeyCode(char='s')], lambda : print("<ctrl><s>"))
		#hotkey.press(self.listener.canonical(key))

		if not self.game.scene.players[0].receive_command(key):
			self.game.scene.players[1].receive_command(key)

	def player(self):
		player = HumanPlayer()
		self.game.add_player(player)
		return player


