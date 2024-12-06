from typing import Any, List, Union
from copy import deepcopy

import numpy as np
import random

from vgc.behaviour import BattlePolicy
from vgc.datatypes.Types import PkmStatus, WeatherCondition, PkmStat
from vgc.datatypes.Objects import GameState, PkmTeam, PkmType, Pkm, PkmMove
from vgc.datatypes.Constants import DEFAULT_N_ACTIONS, TYPE_CHART_MULTIPLIER
from vgc.competition.StandardPkmMoves import STANDARD_MOVE_ROSTER

from enemy import ThunderPlayer

class Node():

  def __init__(self):
    self.action: int = None
    self.gameState: GameState = None
    self.parent: Node = None
    self.depth: int = 0
    self.value: float = 0.

  def __str__(self):
    return f'Node(action: {self.action}, depth: {self.depth}, value: {self.value}, parent: {str(self.parent)})'
  
def match_up_eval(my_pkm_type: PkmType,
      opp_pkm_type: PkmType,
      my_moves_type: List[PkmType],
      opp_moves_type: List[PkmType]
  ) -> float:
  # determine defensive match up
  defensive_match_up = 0.
  for mtype in opp_moves_type:
    if mtype == opp_pkm_type:
      defensive_match_up = max(TYPE_CHART_MULTIPLIER[mtype][my_pkm_type]*1.5, defensive_match_up)
    else:
      defensive_match_up = max(TYPE_CHART_MULTIPLIER[mtype][my_pkm_type], defensive_match_up)
  #print(f'DEFENSIVE MATCH UP: {defensive_match_up}')

  offensive_match_up = 0.
  for mtype in my_moves_type:
    if mtype == opp_pkm_type:
      offensive_match_up = max(TYPE_CHART_MULTIPLIER[mtype][opp_pkm_type]*1.5, offensive_match_up)
    else:
      offensive_match_up = max(TYPE_CHART_MULTIPLIER[mtype][my_pkm_type], offensive_match_up)
  #print(f'OFFENSIVE MATCH UP: {offensive_match_up}')
    
  return offensive_match_up - defensive_match_up


def better_estimate_move(pkm: Pkm) -> None:
  # controlla se è già presente una mossa del tipo del pokemon
  type_m = sum([move.type==pkm.type for move in pkm.moves if move.name is not None])
  for move_i in range(DEFAULT_N_ACTIONS-2):
    if pkm.moves[move_i].name is None:
      # se non è presente una mossa del tipo del pkm allora ne aggiungo una random
      # forse potrebbe convenire aggiungere la più potente pensando al caso pessimo ed alla propria incolumità 
      # tanto gli algoritmi avversari sono greedy sul danno
      if type_m==0:
        type_moves = [move for move in STANDARD_MOVE_ROSTER if move.type==pkm.type]
        pkm.moves[move_i] = random.choice(type_moves)
        type_m = 1
      else:
        # faccio in modo che sia diversa dalle mosse che ho già
        move = random.choice(STANDARD_MOVE_ROSTER)
        while(move in pkm.moves):
          move = random.choice(STANDARD_MOVE_ROSTER)
        pkm.moves[move_i] = move

def known_opp_moves(pkm: Pkm) -> int:
  known = 0
  for move_i in range(DEFAULT_N_ACTIONS-2):
    if pkm.moves[move_i].name is not None:
      known += 1
  return known


def estimate_move(pkm: Pkm) -> None:
  for move_i in range(DEFAULT_N_ACTIONS-2):
    if pkm.moves[move_i].name is None:
      if move_i == 0:
        type_moves = [move for move in STANDARD_MOVE_ROSTER if move.type==pkm.type]
        pkm.moves[move_i] = random.choice(type_moves)
      else:
        pkm.moves[move_i] = random.choice(STANDARD_MOVE_ROSTER)

def stage_eval(team: PkmTeam) -> int:
  stage: int = 0
  for s in team.stage:
    stage += s
  return stage

def status_eval(pkm: Pkm) -> float:
  if pkm.status == (PkmStatus.CONFUSED or PkmStatus.PARALYZED or PkmStatus.SLEEP or PkmStatus.FROZEN):
    return -1
  elif pkm.status == (PkmStatus.BURNED or PkmStatus.POISONED):
    return -0.5
  else:
    return 0
  
def game_state_eval(g: GameState):
  my_team = g.teams[0]
  opp_team  = g.teams[1]
  my_active: Pkm = my_team.active
  opp_active: Pkm = opp_team.active
  match_up: float = match_up_eval(my_active.type, opp_active.type,
      list(map(lambda m: m.type, my_active.moves)),
      list(map(lambda m: m.type, [move for move in opp_active.moves if move.name != None])))
  #print(f'MATCH UP: {match_up}')
  my_stage = stage_eval(my_team)
  opp_stage = stage_eval(opp_team)
  my_status = status_eval(my_active)
  opp_status = status_eval(opp_active)
  return (match_up 
          + my_active.hp/my_active.max_hp
          - opp_active.hp/opp_active.max_hp
          + 0.2*my_stage
          - 0.2*opp_stage
          + my_status
          - opp_status)


def better_game_state_eval(g: GameState, depth: int):
  my_team = g.teams[0]
  opp_team  = g.teams[1]
  my_active: Pkm = my_team.active
  opp_active: Pkm = opp_team.active
  match_up: float = match_up_eval(my_active.type, opp_active.type,
      list(map(lambda m: m.type, my_active.moves)),
      list(map(lambda m: m.type, [move for move in opp_active.moves if move.name != None])))
  #print(f'MATCH UP: {match_up}')
  my_stage = stage_eval(my_team)
  opp_stage = stage_eval(opp_team)
  my_status = status_eval(my_active)
  opp_status = status_eval(opp_active)
  return (match_up 
          + my_active.hp/my_active.max_hp*3
          - opp_active.hp/opp_active.max_hp*3
          + 0.2*my_stage
          - 0.2*opp_stage
          + my_status
          - opp_status
          - 0.3*depth)
# AGGIUNGERE LA VITA DELLA SQUADRA tipo + (party[0].hp/party[0].max_hp+party[1].hp/party[1].max_hp)
# ma noi possiamo vedere la vita del party avversario?????

def n_fainted(team: PkmTeam) -> int:
  fainted = 0
  fainted += team.active.hp == 0
  if len(team.party) > 0:
    fainted += team.party[0].hp == 0
  if len(team.party) > 1:
    fainted += team.party[1].hp == 0
  return fainted

def calculate_damage(move: PkmMove, pkm_type: PkmType, opp_pkm_type: PkmType, attack_stage: int, defense_stage: int, weather: WeatherCondition) -> float:
    if move.pp <= 0:
      return 0
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

def CanAttackFirst(my_team:PkmTeam, opp_team:PkmTeam, opp_active:Pkm) -> int:
    
    speed0 = my_team.stage[PkmStat.SPEED]
    speed1 = opp_team.stage[PkmStat.SPEED]

    opp_might_act_earlier = False
    for opp_poss_act in opp_active.moves:
        if opp_poss_act.priority:
            opp_might_act_earlier = True

    if speed1 > speed0:
        if opp_might_act_earlier:
            return -2
        return -1
    if speed0 > speed1 and not opp_might_act_earlier:
        return 1
    if speed0 > speed1 and opp_might_act_earlier:
        return 0.5
    else:
        return 0

def canDefeat(attack1:int, defense2:int, pkm1:Pkm, pkm2:Pkm, weather:WeatherCondition):
    moves = []
    for i in range(0, len(pkm1.moves)):
        print('prima del danno')
        damage = calculate_damage(pkm1.moves[i], pkm1.type, pkm2.type, attack1, defense2, weather)
        print(damage)
        if damage >= pkm2.hp:
          print('entrato')
          moves.append((pkm1.moves.index(pkm1.moves[i]), damage, pkm1.moves[i].max_pp, pkm1.moves[i].acc, pkm1.moves[i].priority))
    # se ho delle mosse che sconfiggono l'avversario le ordino in modo da avere prima quelle più accurate e con più max_pp
    # il controllo di accuratezza sarà da fare in seguito se occorre
    print(moves)
    if len(moves)>0:
      moves.sort(reverse=True, key=lambda x : (x[3], x[2], x[1], x[0]))
    return moves


class AlphaBetaPolicy(BattlePolicy):

  def __init__(self, max_depth: int = 6, seed: int = 69):
    self.max_depth = max_depth
    random.seed(seed)
    #momentanea
    self.policy = ThunderPlayer()
    #self.policy2 = TypeSelector()

  def get_action(self, g: Union[List[float], GameState]) -> int:
    root: Node = Node()
    root.gameState = g
    
    #print('---------------------------------')
    # print('OPPONENT MOVES')
    # for i in range(DEFAULT_N_ACTIONS-2):
    #   print(f'{str(g.teams[1].active.moves[i])}')
    # print('OPPONENT PKM')
    # print(g.teams[1])
    # print('---------------------------------')

    # se conosco meno di 3 mosse non utilizzo minimax ma una più semplice
    if known_opp_moves(g.teams[1].active)<2:
      print('ciaoooooooooooo')
      return self.simple_search(root.gameState)
    # altrimenti faccio minimax
    else:
      return self._alphaBeta_search(root)


  def simple_search(self, g: GameState) -> int:

    team0 = g.teams[0]
    team1 = g.teams[1]
    my_active = team0.active
    opp_active = team1.active
    weather = g.weather.condition
    # controllo i match up della mia squadra
    match_up = match_up_eval(my_active.type, opp_active.type, list(map(lambda m: m.type, my_active.moves)), list(map(lambda m: m.type, [move for move in opp_active.moves if move.name != None])))
    pkm1_match_up = match_up_eval(team0.party[0].type, opp_active.type, list(map(lambda m: m.type, team0.party[0].moves)), list(map(lambda m: m.type, [move for move in opp_active.moves if move.name!=None])))
    pkm2_match_up = match_up_eval(team0.party[1].type, opp_active.type, list(map(lambda m: m.type, team0.party[1].moves)), list(map(lambda m: m.type, [move for move in opp_active.moves if move.name!=None])))
    # controllo chi attacca prima
    attack_order = CanAttackFirst(team0, team1, team1.active)
    print('ciao2')
    # controllo se riesco a sconfiggere l'avversario con una mossa
    moves = canDefeat(team0.stage[PkmStat.ATTACK], team1.stage[PkmStat.DEFENSE], team0.active, team1.active, weather)
    print(moves)
    # se posso batterlo 
    if len(moves) > 0:
      # se attacco sicuramente prima allora prendo la prima mossa più accurata con più pp che lo sconfigge
      if attack_order == 1:
        return moves[0][0]
      # se l'avversario ha una mossa prioritaria controllo che non possa sconfiggermi
      elif attack_order == 0.5:
        if calculate_damage([m for m in opp_active.moves if m.priority==True][0], opp_active.type, my_active.type, team1.stage[PkmStat.ATTACK], team0.stage[PkmStat.DEFENSE], weather) < my_active.hp:
          return moves[0][0]
      # se l'avversario è più veloce
      if attack_order <= 0:
        # se ho una possa prioritaria che lo sconfigge la prendo
        if sum([m[4] for m in moves])>=1:
          return [m[0] for m in moves if m[4] == True][0]
        # se comunque l'avversario non può sconfiggermi con una mossa allora prendo la mia mossa che lo sconfigge
        if len(canDefeat(team1.stage[PkmStat.ATTACK], team0.stage[PkmStat.DEFENSE], team1.active, team0.active, weather))==0:
          return moves[0][0]
        # se invece può sconfiggermi con una mossa e attacca prima cambio
        #else:

        
    # se non lo batto con una mossa allora controllo se il mio pkm è in vantaggio di tipo
    
    print(n_fainted(team0))
    
    # se sono in una situazione accettabile o ho il team esausto o sono in svantaggio ma non ho cambi migliori allora tengo il pkm in campo 
    if match_up >= 0.5 or n_fainted(team0)==2 or (match_up < 0.5 and not (pkm1_match_up > match_up or pkm2_match_up > match_up)):
      # per ora usa un approccio greedy ma è da fare una simulazione di 2-3 turni con tutte le mosse
      return int(np.argmax([calculate_damage(m, my_active.type, opp_active.type, team0.stage[PkmStat.ATTACK], team1.stage[PkmStat.DEFENSE], weather) for m in my_active.moves]))  
    # altrimenti (comprende il caso in cui il pkm è in svantaggio e ho pkm migliori in squadra) faccio lo switch con il pkm migliore
    else:
      if pkm1_match_up >= pkm2_match_up:
        if not team0.party[0].fainted():
          return 4
        else:
          return 5
      else: 
        if not team0.party[1].fainted():
          return 5
        else:
          return 4



  def _alphaBeta_search(
      self,
      root: Node,
      alpha: float = -np.inf,
      beta: float = np.inf
  ) -> int:
    #print("ALPHA BETA SEARCH")
    value, move = self._max_value(root, alpha, beta)
    #print('---------------------------------')
    #print(f'AlphaBetaPolicy chose action: {root.gameState.teams[0].active.moves[move]}, with value: {value}')
    #print('---------------------------------')
    return move

  def _max_value(
      self,
      node: Node,
      alpha: float,
      beta: float
  ) -> tuple[float, Union[int, None]]:
    state: GameState = deepcopy(node.gameState)
    node.value = better_game_state_eval(state, node.depth)
    # print('---------------------------------')
    # print(f'CURRENT NODE: {str(node)}')
    # print('---------------------------------')
    # print(f'MY HP: {state.teams[1].active.hp}')
    # print(f'OPPONENT HP: {state.teams[1].active.hp}')
    if state.teams[1].active.hp == 0 or state.teams[0].active.hp == 0 or node.depth >= self.max_depth:
      return better_game_state_eval(state, node.depth), None
    value = -np.inf
    for i in range(DEFAULT_N_ACTIONS):
      next_node: Node = Node()
      next_node.parent = node
      next_node.depth = node.depth + 1
      next_node.action = i
      next_node.gameState = state
      next_node.value, _ = self._min_value(next_node, alpha, beta)
      # print('---------------------------------')
      # print(f'NEXT NODE: {str(next_node)}')
      # print('---------------------------------')
      if next_node.value > value:
        value, move = next_node.value, next_node.action
        alpha = max(value, alpha)
      if value >= beta:
        return value, move
    return value, move
        
  def _min_value(
      self,
      node: Node,
      alpha: float,
      beta: float
  ) -> tuple[float, Union[int, None]]:
    state: GameState = deepcopy(node.gameState)
    if state.teams[1].active.hp == 0 or state.teams[0].active.hp == 0 or node.depth >= self.max_depth:
      return better_game_state_eval(state, node.depth), None
    value = np.inf
    for i in range(DEFAULT_N_ACTIONS):
      next_state, _, _, _, _ = state.step([node.action, i])
      next_node: Node = Node()
      next_node.parent = node
      next_node.depth = node.depth + 1
      next_node.action = i
      next_node.gameState = next_state[0]
      next_node.value, _ = self._max_value(next_node, alpha, beta)
      if next_node.value < value:
        value, move = next_node.value, next_node.action
        beta = min(value, beta)
      if value <= alpha:
        return value, move
    return value, move



# -----------------------------------------------------------------------------------------------------------------------------



'''
class TypeSelector(BattlePolicy):

    def get_action(self, g: GameState):
        # get weather condition
        weather = g.weather.condition

        # get my pokémon
        my_team = g.teams[0]
        my_active = my_team.active
        my_party = my_team.party
        my_attack_stage = my_team.stage[PkmStat.ATTACK]

        # get opp team
        opp_team = g.teams[1]
        opp_active = opp_team.active
        opp_active_type = opp_active.type
        opp_defense_stage = opp_team.stage[PkmStat.DEFENSE]

        # get most damaging move from my active pokémon
        damage: List[float] = []
        for move in my_active.moves:
            damage.append(calculate_damage(move, my_active.type, opp_active_type,
                                          my_attack_stage, opp_defense_stage, weather))
        move_id = int(np.argmax(damage))

        #  If this damage is greater than the opponents current health we knock it out
        if damage[move_id] >= opp_active.hp:
            return move_id

        # If not, check if are a favorable match. If we are lets give maximum possible damage.
        if match_up_eval(my_active.type, opp_active.type, list(map(lambda m: m.type, opp_active.moves)), list(map(lambda m: m.type, [move for move in opp_active.moves if move.name != None]))) >= 0.5:
            return move_id

        # If we are not switch to the most favorable match up
        match_up: List[float] = []
        not_fainted = False
        for pkm in my_party:
            if pkm.hp == 0.0:
                match_up.append(-4.0)
            else:
                not_fainted = True
                match_up.append(
                    match_up_eval(pkm.type, opp_active.type, list(map(lambda m: m.type, opp_active.moves))), list(map(lambda m: m.type, [move for move in opp_active.moves if move.name != None])))

        if not_fainted:
            return int(np.argmax(match_up)) + 4

        # If our party has no non fainted pkm, lets give maximum possible damage with current active
        return move_id'''
