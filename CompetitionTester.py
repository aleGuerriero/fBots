from bots.fCompetitor import fCompetitor
from bots.BattlePolicies import AlphaBetaPolicy
from bots.Thunder_BattlePolicies import ThunderPlayer
from bots.hayo5 import hayo5_BattlePolicy

from vgc.balance.meta import StandardMetaData
from vgc.competition.Competitor import CompetitorManager
from vgc.competition.Competition import TreeChampionship
from vgc.ecosystem.BattleEcosystem import BattleEcosystem, Strategy
from vgc.ecosystem.ChampionshipEcosystem import ChampionshipEcosystem
from vgc.util.generator.PkmRosterGenerators import RandomPkmRosterGenerator
from vgc.util.generator.PkmTeamGenerators import RandomTeamFromRoster

from vgc.behaviour.BattlePolicies import Minimax, PrunedBFS, BreadthFirstSearch, TunedTreeTraversal, TypeSelector

POLICIES = {
  'alpha-beta': AlphaBetaPolicy(),
  'thunder': ThunderPlayer(),
  'hayo': hayo5_BattlePolicy(),
  'minimax': Minimax(),
  'pruned': PrunedBFS(),
  'bfs': BreadthFirstSearch(),
  'traversal': TunedTreeTraversal(),
  'type': TypeSelector()
}

def main():
  roster = RandomPkmRosterGenerator().gen_roster()
  meta_data = StandardMetaData()
  #le = BattleEcosystem(meta_data, debug=True, pairings_strategy=Strategy.ELO_PAIRING)
  #ce = ChampionshipEcosystem(roster, meta_data, debug=True)
  tc = TreeChampionship(roster, meta_data, debug=True)

  for name in list(POLICIES.keys()):
    policy = POLICIES[name]
    c = fCompetitor(name=name)
    c._battle_policy = policy
    cm = CompetitorManager(c)
    cm.team = RandomTeamFromRoster(roster).get_team()
    tc.register(cm)
  turnament = tc.new_tournament()
  winner = tc.run()

  print(f'Winner: {winner.competitor.name}')
  for i, name in enumerate(list(POLICIES.keys())):
    print(f'{name} elo: {tc.competitors[i].elo}')

if __name__=='__main__':
  main()