"""Provide an implementation of the battle policies.

The module contains the following functions:
- `game_state_eval(gameState)` - Returns an evaluation of the current state. Utility function in minimax algorithms.
"""

from typing import Any, List, Union
from copy import deepcopy

import numpy as np
import cvxpy as cp
import random

from vgc.behaviour import BattlePolicy
from vgc.datatypes.Types import PkmStatus
from vgc.datatypes.Objects import GameState, PkmTeam, PkmType, Pkm, PkmMove, WeatherCondition
from vgc.datatypes.Constants import DEFAULT_N_ACTIONS, TYPE_CHART_MULTIPLIER
from vgc.competition.StandardPkmMoves import STANDARD_MOVE_ROSTER

class Node():

  def __init__(self):
    self.action: tuple[int, int] = None   # (row action, column action)
    self.chosen_action: int = None
    self.gameState: GameState = None
    self.parent: Node = None
    self.depth: int = 0
    self.value: float = 0.

  def __str__(self):
    return f'Node(action: {self.action}, depth: {self.depth}, value: {self.value}, parent: {str(self.parent)})'
  
def estimate_damage(
    move: PkmMove,
    pkm_type: PkmType,
    opp_pkm_type: PkmType,
    attack_stage: int, defense_stage: int,
    weather: WeatherCondition) -> float:
  move_type: PkmType = move.type
  move_power: float = move.power
  type_rate = TYPE_CHART_MULTIPLIER[move_type][opp_pkm_type]
  if type_rate == 0:
    return 0
  if move.fixed_damage > 0:
    return move.fixed_damage
  stab = 1.5 if move_type == pkm_type else 1.
  if ((move_type == PkmType.WATER and weather == WeatherCondition.RAIN) 
      or (move_type == PkmType.FIRE and weather == WeatherCondition.SUNNY)):
    weather = 1.5
  elif ((move_type == PkmType.WATER and weather == WeatherCondition.SUNNY) 
      or (move_type == PkmType.FIRE and weather == WeatherCondition.RAIN)):
    weather = .5
  else:
    weather = 1.
  stage_level = attack_stage - defense_stage
  stage = (stage_level + 2.) / 2 if stage_level >= 0. else 2. / \
      (np.abs(stage_level) + 2.)
  damage = type_rate * \
      stab * weather * stage * move_power
  return damage
  
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

def n_fainted(team: PkmTeam) -> int:
  fainted = 0
  fainted += team.active.hp == 0
  if len(team.party) > 0:
    fainted += team.party[0].hp == 0
  if len(team.party) > 1:
    fainted += team.party[1].hp == 0
  return fainted

class SmabPolicy(BattlePolicy):
  """Implements an alpha-beta search policy.

  Attributes:
    max_depth (int): the maximum depth reachable from alpha-beta search in the exploration tree.
    seed (int): the seed for random number generation.
  """

  def __init__(self, max_depth: int = 6, epsilon: float = 1e-16):
    self.max_depth = max_depth
    self.espilon = epsilon

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

  def _smab(
      self,
      node: Node,
      alpha: float = -np.inf,
      beta: float = np.inf) -> int:
    
    gameState: GameState = deepcopy(node.gameState)
    
    if (gameState.teams[1].active.hp == 0
        or gameState.teams[0].active.hp == 0
        or node.depth >= self.max_depth):
      return game_state_eval(gameState), node.chosen_action
    
    A: List[int] = list(range(DEFAULT_N_ACTIONS))
    B: List[int] = list(range(DEFAULT_N_ACTIONS))
    
    P: np.ndarray = np.full((A, B), -np.inf)
    O: np.ndarray = np.full((A, B), np.inf)

    for a, b in zip(A, B):
      if not self._is_dominated(a, b, P, O):
        alpha_ab = self._compute_alpha(a, b, P, alpha)
        beta_ab = self._compute_beta(a, b, O, beta)

        next_state, _, _, _, _ = gameState.step([a, b])
        child_node = Node()
        child_node.parent = node
        child_node.depth = node.depth + 1
        child_node.action = (a, b)
        child_node.gameState = next_state[0]

        if alpha_ab >= beta_ab:
          value, _ = self._smab(child_node, alpha_ab, alpha_ab + self.espilon)
          if value <= alpha_ab:
            A.remove(a)         # Prune row action
          else:
            B.remove(b)         # Prune column action
        else:
          value, _ = self._smab(child_node, alpha_ab, beta_ab)
          if value <= alpha_ab:
            A.remove(A)
          elif value >= beta_ab:
            B.remove(b)
          else:
            P[a, b] = O[a, b] = value
    
    restricted_P = P[np.ix_(A, B)]
    nash_value, action = self._compute_nash(restricted_P)
    node.parent.chosen_action = action
    return nash_value, node.chosen_action

  def _compute_nash(
      self,
      P: np.ndarray
  ) -> tuple[float, int]:
    rows, cols = P.shape
    x = cp.Variable(rows, nonneg=True)
    y = cp.Variable(cols, nonneg=True)
    constraints = [cp.sum(x) == 1, cp.sum(y) == 1]
    for i in range(rows):
      constraints.append(x @ P[:, i] >= 0)
    for j in range(cols):
      constraints.append(y @ P[j, :] <= 0)
    problem = cp.Problem(cp.Maximize(x @ P @ y.T), constraints)
    problem.solve()
    return problem.value, np.argmax(x.value)

  def _compute_alpha(
      self,
      a: int,
      b: int,
      P: np.ndarray,
      alpha: float
  ) -> float:
    rows, _ = P.shape
    x = cp.Variable(rows, nonneg=True)
    constraints = [x @ P[:, b] >= alpha, cp.sum(x)==1]
    problem = cp.Problem(cp.Maximize(x @ P[:, b]), constraints)
    problem.solve()
    return max(alpha, problem.value)
  
  def _compute_beta(
      self,
      a: int,
      b: int,
      O: np.ndarray,
      beta, float
  ) -> float:
    _, cols = O.shape
    x = cp.Variable(cols, nonneg=True)
    constraints = [O[a, :] @ x <= beta, cp.sum(x) == 1]
    problem = cp.Problem(cp.Minimize(O[a, :] @ x), constraints)
    problem.solve()
    return min(beta, problem.value)

  def _is_dominated(
      self,
      a: int,
      b: int,
      P: np.ndarray,
      O: np.ndarray
  ) -> bool:
    
    for other_a in range(P.shape[0]):
      if (other_a != a 
          and all(P[other_a, j] >= O[a, j] for j in range(P.shape[1]))):
        return True
      for other_b in range(P.shape[1]):
        if (other_b != b 
            and all(O[i, other_b] <= P[i, b] for i in range(P.shape[0]))):
          return True
      return False


