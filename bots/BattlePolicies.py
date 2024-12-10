"""Provide an implementation of the battle policies.

The module contains the following functions:
- `game_state_eval(gameState)` - Returns an evaluation of the current state. Utility function in minimax algorithms.
"""

from typing import Any, List, Union
from copy import deepcopy

import numpy as np
import random

from vgc.behaviour import BattlePolicy
from vgc.datatypes.Types import PkmStatus
from vgc.datatypes.Objects import GameState, PkmTeam, PkmType, Pkm
from vgc.datatypes.Constants import DEFAULT_N_ACTIONS, TYPE_CHART_MULTIPLIER
from vgc.competition.StandardPkmMoves import STANDARD_MOVE_ROSTER

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
  
def game_state_eval(g: GameState, depth:int):
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
  fainted_advantage = (3 - n_fainted(my_team)) - (3 - n_fainted(opp_team))
  hp_ratio = my_active.hp / my_active.max_hp - opp_active.hp / opp_active.max_hp
  
  late_game_factor = 1 + 0.5 * (n_fainted(my_team) + n_fainted(opp_team))
  return (match_up 
          + late_game_factor * hp_ratio
          + 0.3 * my_stage
          - 0.3 * opp_stage
          + 7 * (my_status - opp_status)
          + 10 * late_game_factor * fainted_advantage
          - 10 * depth)

def n_fainted(team: PkmTeam) -> int:
  fainted = 0
  fainted += team.active.hp == 0
  if len(team.party) > 0:
    fainted += team.party[0].hp == 0
  if len(team.party) > 1:
    fainted += team.party[1].hp == 0
  return fainted

class AlphaBetaPolicy(BattlePolicy):
  """Implements an alpha-beta search policy.

  Attributes:
    max_depth (int): the maximum depth reachable from alpha-beta search in the exploration tree.
    seed (int): the seed for random number generation.
  """

  def __init__(self, max_depth: int = 6, seed: int = 69):
    self.max_depth = max_depth
    random.seed(seed)

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

    action = self._alphaBeta_search(root)
    return action

  def _alphaBeta_search(
      self,
      root: Node,
      alpha: float = -np.inf,
      beta: float = np.inf
  ) -> int:
    """Performs Alpha-Beta pruning starting from the root node.

    Args:
      root: The root node where the search begins.
      alpha: The alpha value for pruning. Defaults to -inf.
      beta: The beta value for pruning. Defaults to inf.

    Returns:
      int: The optimal action index.
    """

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
    """Computes the maximum value of the current node using Alpha-Beta pruning.

    This method recursively evaluates possible game states by simulating all
    valid moves and returns the optimal move for the maximizing player.

    Args:
      node: The current node in the game tree.
      alpha: The current alpha value for pruning.
      beta: The current beta value for pruning.

    Returns:
      A tuple containing the best value and the corresponding action index.
    """

    state: GameState = deepcopy(node.gameState)
    node.value = game_state_eval(state, node.depth)
    # print('---------------------------------')
    # print(f'CURRENT NODE: {str(node)}')
    # print('---------------------------------')
    # print(f'MY HP: {state.teams[1].active.hp}')
    # print(f'OPPONENT HP: {state.teams[1].active.hp}')
    if (state.teams[1].active.hp == 0
        or state.teams[0].active.hp == 0
        or node.depth >= self.max_depth):
      return game_state_eval(state), None
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
    """Computes the minimum value of the current node using Alpha-Beta pruning.

    This method recursively evaluates possible game states by simulating all
    valid moves and returns the optimal move for the minimizing player.

    Args:
      node: The current node in the game tree.
      alpha: The current alpha value for pruning.
      beta: The current beta value for pruning.

    Returns:
      A tuple containing the best value and the corresponding action index.
    """

    state: GameState = deepcopy(node.gameState)
    if (state.teams[1].active.hp == 0
        or state.teams[0].active.hp == 0
        or node.depth >= self.max_depth):
      return game_state_eval(state), None
    value = np.inf
    for i in range(DEFAULT_N_ACTIONS):
      estimate_move(state.teams[1].active)
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

