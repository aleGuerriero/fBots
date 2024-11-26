from tqdm import tqdm

from bots.BattlePolicies import AlphaBetaPolicy
from bots.fCompetitor import fCompetitor
from bots.Thunder_BattlePolicies import ThunderPlayer
from bots.hayo5 import hayo5_BattlePolicy

from vgc.competition.BattleMatch import BattleMatch
from vgc.competition.Competitor import CompetitorManager
from vgc.util.generator.PkmRosterGenerators import RandomPkmRosterGenerator
from vgc.util.generator.PkmTeamGenerators import RandomTeamFromRoster

from vgc.behaviour.BattlePolicies import TerminalPlayer, Minimax

def main():
  n_matches: int = 100
  debug: bool = False

  c0 = fCompetitor('Player1')
  cm0 = CompetitorManager(c0)
  c1 = fCompetitor('Player2')
  c1._battle_policy = ThunderPlayer()
  cm1 = CompetitorManager(c1)
  roster = RandomPkmRosterGenerator().gen_roster()

  wins: int = 0
  for _ in (pbar := tqdm(range(n_matches), leave=True)):
    tg = RandomTeamFromRoster(roster)
    cm0.team = tg.get_team()
    cm1.team = tg.get_team()
    match = BattleMatch(cm0, cm1, debug=debug)
    match.run()
    # print(match.winner())
    # print(f'{match.cms[match.winner()].competitor.name} won')
    wins += match.winner() == 0
    pbar.set_description(f'Current wins: {wins}')

  print(f'{c0.name} won: {wins}/{n_matches} matches')

if __name__=='__main__':
  main()