from typing import Any, List, Union
import random
import numpy as np
from collections import namedtuple

from vgc.behaviour import BattlePolicy
from vgc.datatypes.Objects import GameState, Pkm, Weather, PkmStat, PkmMove, PkmType, WeatherCondition
from vgc.datatypes.Constants import DEFAULT_PKM_N_MOVES, DEFAULT_PARTY_SIZE, MAX_HIT_POINTS, TYPE_CHART_MULTIPLIER, DEFAULT_N_ACTIONS
from vgc.competition.StandardPkmMoves import STANDARD_MOVE_ROSTER, Struggle

class Node():
  def __init__(self) -> None:
    self.action: int = None
    self.state: GameState = None
    self.parent: Node = None
    self.depth: int = 0
    self.value: float = 0.0
  
    
   
def assign_rnd_moves(pkm:Pkm):
   type = pkm.type
   for i in pkm.moves:
      if pkm.moves[i] == None:
        pkm.moves[i] = random.choice([move for move in STANDARD_MOVE_ROSTER if move.type == type])
  
def game_state_eval(g: GameState):
  my_active = g.teams[0].active
  opp_active = g.teams[0].active
  return my_active.hp/my_active.max_hp - opp_active.hp/opp_active.max_hp

class FirstPlayer(BattlePolicy):

  def __init__(self, max_depth: int = 3):
    self.max_depth = max_depth

  def get_better_move(weather: Weather,
    my_pkm: Pkm, my_stage: list[PkmStat],
    op_pkm: Pkm, op_stage: list[PkmStat]
    ):
      if my_pkm.hp == 0 or op_pkm.hp == 0:
        return None, None,None #if one of the pkm is dead the battle ends
      damages_list = []
      for move_index, move in enumerate(my_pkm.moves):
        if move.pp == 0:
          move = Struggle #if the move has no more pp it uses Struggle (default) move
        if move is Struggle or move.name is None:
          continue
        damage = estimate_damage(move, my_pkm.type, op_pkm.type,
                                 my_stage[PkmStat.ATTACK], op_stage[PkmStat.DEFENSE], weather) 
        damages_list.append((move_index, int(damage), move.acc, move)) #add the estimate damage into the damages_list
      
      if len(damages_list) == 0:
          return None, None,None
      
      assign_rnd_moves(op_pkm)

      move_i, min_turn, best_move_scores = get_better_first_move( #find the better first move between all possible moves
        int(op_pkm.hp), damages_list, my_stage[PkmStat.SPEED] < op_stage[PkmStat.SPEED])

      return move_i, min_turn, best_move_scores 
  '''
    move_i: Index of the best move in the player's move list.
    min_turn: Number of turns required to faint the opponent using the selected move.
    best_move_scores: Additional scoring or evaluation metrics for the chosen move
  '''

  def chose_better_move(self, g: GameState):
    return alphaBeta_search(g)

  def get_action(self, g: Union[List[float], GameState]) -> int:
    myteam = g.teams[0]
    opteam = g.teams[1]
    print("\\\\\\\\\\\\\\\\\\")
    print(myteam.active)
    
    for i in myteam.active.moves:
       print(str(i))
    print("\\\\\\\\\\\\\\\\\\")
    print(opteam.active)
    for i in opteam.active.moves:
       print(str(i))
    print("\\\\\\\\\\\\\\\\\\")

    current_state = Node
    
    #to_move = self.chose_better_move()

    a = 1
    print("\\\\\\\\\\\\\\\\\\")
    print(str(myteam.active.moves[a]))
    return a
  


  
def alphaBeta_search(g: GameState) -> int:
    value, move = max_value(g, -np.inf , np.inf)
    return move

def max_value(g: GameState, alpha:float, beta:float)->tuple[float,int]:
  v = -np.inf
  move = 0
  for act in range(DEFAULT_N_ACTIONS):

    v2, a2 = min_value(g, game_state_eval(g),alpha, beta)
    if v2 > v:
        v, move = v2, act
        alpha = max(alpha, v)
    if v >= beta:
        return v, move
  return v, move
  
def min_value(g: GameState, alpha:float, beta:float)->tuple[float,int]:
  v = np.inf
  move = 0
  for act in range(DEFAULT_N_ACTIONS):
    v2, a2 = max_value(g, alpha, beta)
    if v2 < v: 
      v, move = v2, act
      beta = min(beta, v)
    if v <= alpha:
      return v, move
    return v, move

















def estimate_damage(move: PkmMove, pkm_type: PkmType, opp_pkm_type: PkmType,
                    attack_stage: int, defense_stage: int, weather: WeatherCondition) -> float:
    move_type: PkmType = move.type
    move_power: float = move.power
    type_rate = TYPE_CHART_MULTIPLIER[move_type][opp_pkm_type]
    if type_rate == 0:
        return 0
    if move.fixed_damage > 0:
        return move.fixed_damage
    stab = 1.5 if move_type == pkm_type else 1.
    if (move_type == PkmType.WATER and weather == WeatherCondition.RAIN) or (
            move_type == PkmType.FIRE and weather == WeatherCondition.SUNNY):
        weather = 1.5
    elif (move_type == PkmType.WATER and weather == WeatherCondition.SUNNY) or (
            move_type == PkmType.FIRE and weather == WeatherCondition.RAIN):
        weather = .5
    else:
        weather = 1.
    stage_level = attack_stage - defense_stage
    stage = (stage_level + 2.) / 2 if stage_level >= 0. else 2. / \
        (np.abs(stage_level) + 2.)
    damage = type_rate * \
        stab * weather * stage * move_power
    return damage


