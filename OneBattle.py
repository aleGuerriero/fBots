from bots.BattlePolicies import SmabPolicy
from bots.fCompetitor import fCompetitor
from bots.Thunder_BattlePolicies import ThunderPlayer
from bots.hayo5 import hayo5_BattlePolicy

from vgc.competition.BattleMatch import BattleMatch
from vgc.competition.Competitor import CompetitorManager
from vgc.util.generator.PkmRosterGenerators import RandomPkmRosterGenerator
from vgc.util.generator.PkmTeamGenerators import RandomTeamFromRoster

from vgc.behaviour.BattlePolicies import TerminalPlayer, Minimax, PrunedBFS

def main():
  c0 = fCompetitor('Player1')
  cm0 = CompetitorManager(c0)
  c1 = fCompetitor('Player2')
  c1._battle_policy = ThunderPlayer()
  cm1 = CompetitorManager(c1)
  roster = RandomPkmRosterGenerator().gen_roster()
  tg = RandomTeamFromRoster(roster)
  cm0.team = tg.get_team()
  cm1.team = tg.get_team()
  match = BattleMatch(cm0, cm1, debug=True)
  match.run()

if __name__=='__main__':
  main()