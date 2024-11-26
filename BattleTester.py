from bots.BattlePolicies import FirstPlayer
from bots.fCompetitor import fCompetitor

from vgc.competition.BattleMatch import BattleMatch
from vgc.competition.Competitor import CompetitorManager
from vgc.util.generator.PkmRosterGenerators import RandomPkmRosterGenerator
from vgc.util.generator.PkmTeamGenerators import RandomTeamFromRoster

from vgc.behaviour.BattlePolicies import TerminalPlayer, Minimax

def main():
  roster = RandomPkmRosterGenerator().gen_roster()
  tg = RandomTeamFromRoster(roster)
  c0 = fCompetitor('Player1')
 # c0._battle_policy = FirstPlayer() #Minimax()
  cm0 = CompetitorManager(c0)
  cm0.team = tg.get_team()
  c1 = fCompetitor('Player2')
  c1._battle_policy = TerminalPlayer()
  cm1 = CompetitorManager(c1)
  cm1.team = tg.get_team()
  match = BattleMatch(cm0, cm1, debug=True)
  match.run()

if __name__=='__main__':
  main()