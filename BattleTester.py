from tqdm import tqdm

from bots.AlphaBetaPolicy import AlphaBetaPolicy
from bots.MixedPolicy import MixedPolicy
from bots.GreedyPolicy import GreedyPolicy
from bots.fCompetitor import fCompetitor
from bots.Thunder_BattlePolicies import ThunderPlayer
from bots.hayo5 import hayo5_BattlePolicy

from vgc.competition.BattleMatch import BattleMatch
from vgc.competition.Competitor import CompetitorManager
from vgc.util.generator.PkmRosterGenerators import RandomPkmRosterGenerator
from vgc.util.generator.PkmTeamGenerators import RandomTeamFromRoster

from vgc.behaviour.BattlePolicies import TerminalPlayer, Minimax, PrunedBFS

def main():
  n_matches: int = 5
  debug: bool = False

  c0 = fCompetitor('Player1')
  c0._battle_policy = AlphaBetaPolicy(max_depth=6)
  cm0 = CompetitorManager(c0)
  c1 = fCompetitor('Player2')
  c1._battle_policy = ThunderPlayer()
  cm1 = CompetitorManager(c1)
  roster = RandomPkmRosterGenerator().gen_roster()
  
  total_wins = 0
  tot_wins: int = 0
  tot_ties: int = 0
  for i in (pbar := tqdm(range(n_matches), desc='Matches won: 0/0, Competitions won: 0/0', leave=False)):
    tg = RandomTeamFromRoster(roster)
    cm0.team = tg.get_team()
    cm1.team = tg.get_team()
    wins0 = 0
    j = 0
    for _ in range(2):
      for _ in tqdm(range(5), leave=False):
        j+=1
        match = BattleMatch(cm0, cm1, debug=debug)
        match.run()
        wins0 += match.winner() == 0
        total_wins += match.winner() == 0
        pbar.set_description(f'Matches won: {wins0}/{j}, Competitions won: {tot_wins}/{i}')
      tmp_team = cm0.team
      cm0.team = cm1.team
      cm1.team = tmp_team
    print(f'\nTotal wins: {wins0}')
    # print(f'{match.cms[match.winner()].competitor.name} won')
    tot_wins += wins0 > 5
    tot_ties += wins0 == 5

  print(f'{c0.name} won {tot_wins}/{n_matches}, tied {tot_ties}/{n_matches} and lost {n_matches-tot_ties-tot_wins}/{n_matches} competitions. \nTotal battle wins: {total_wins}')

if __name__=='__main__':
  main()