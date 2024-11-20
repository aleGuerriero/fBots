from typing import Any, List, Union

from collections import namedtuple

from vgc.behaviour import BattlePolicy
from vgc.datatypes.Objects import GameState

class Node(namedtuple('NodeBase',['a', 'g', 'parent', 'depth', 'eval'])):
  __slots__ = () # using __slots__ to keep it lightweight

  def path(self) -> List[int]:
    '''
    Reconstruct the path from the start state to this node
    '''
    node, path = self, []
    while node.parent is not None:
      path.append(node.a)
      node = node.parent
    return path[::-1]
  
  def __repr__(self):
    return f'Node(action={self.a}, value={self.eval})'

class FirstPlayer(BattlePolicy):

  def __init__(self, max_depth: int = 4):
    self.max_depth = max_depth

  def get_action(self, g: Union[List[float], GameState]) -> int:
    root: Node = Node()
    root.g = g
    node_queue: List[Node] = [root]

    while len(node_queue) > 0 and node_queue[0].depth < self.max_depth:
      pass