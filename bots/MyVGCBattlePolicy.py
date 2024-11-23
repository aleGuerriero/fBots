from vgc.datatypes.Objects import GameState, PkmTeam, Pkm, PkmMove
from vgc.behaviour import BattlePolicy
from vgc.datatypes.Types import PkmStat, PkmType, WeatherCondition
from vgc.datatypes.Constants import DEFAULT_PKM_N_MOVES, DEFAULT_PARTY_SIZE, TYPE_CHART_MULTIPLIER, DEFAULT_N_ACTIONS, MAX_HIT_POINTS, STATE_DAMAGE, SPIKES_2, SPIKES_3
from vgc.competition.StandardPkmMoves import Struggle
from typing import List
from copy import deepcopy
import numpy as np



class MyVGCBattlePolicy(BattlePolicy):

    def __init__(self, max_depth: int = 4):
        # memorizzo il team avversario man mano che effettua gli switch, in modo da poter calcolare ulteriori possibili mosse dell'avversario
        self.oppTeam = []
        self.core_agent: BattlePolicy = TypeSelector()
        self.max_depth = max_depth

    def get_action(self, g: GameState) -> int:


        # get weather condition
        weather = g.weather.condition

        # get my pokémon
        my_team = g.teams[0]
        my_active = my_team.active
        my_attack_stage = my_team.stage[PkmStat.ATTACK]
        my_defense_stage = my_team.stage[PkmStat.DEFENSE]

        # get opp team
        opp_team = g.teams[1]
        opp_active = opp_team.active
        # memorizzo il pokemon avversario se non è già stato fatto
        if opp_active not in self.oppTeam:
            self.oppTeam.append(opp_active) 
        opp_active_type = opp_active.type
        opp_attack_stage = opp_team.stage[PkmStat.ATTACK]
        opp_defense_stage = opp_team.stage[PkmStat.DEFENSE]



# ----------------------------------------------------- Caso base -----------------------------------------------------------




        # priority/speed win
        attack_order = CanAttackFirst(my_team, opp_team, opp_active)

        # se attacco prima e ho almeno una mossa che sconfiggerebbe il nemico con un colpo la scelgo (la più accurata con più pp se più di una)
        if attack_order == 1:
            m = []
            for move in my_active.moves:
                # se la mossa è poco accurata preferisco scgeliere una strategia in modo più accurato
                if move.acc >= 0.7 and calculate_damage(move, my_active.type, opp_active_type, my_attack_stage, opp_defense_stage, weather) >= opp_active.hp:
                    m.append((my_active.moves.index(move), move.pp, move.acc))
                # mosse meno accurate le scelgo solo se l'avversario non può sconfiggermi con una mossa
                elif move.acc>=0.5 and not canDefeat(move, opp_active_type, my_active.type, opp_attack_stage, my_defense_stage, weather):
                    m.append((my_active.moves.index(move), move.pp, move.acc))
            if len(m)>0:       
                return m.sort(reverse=True, key=lambda x : (x[2], x[1]))[0]


        

# -------------------------- se il caso base non è sufficiente procedo con una strategia approfondita -----------------------


        
        '''
        # verifico se il mio pkm è in condizione di vantaggio rispetto al pkm avversario e di quanto
        # se è in una condizione di svantaggio valuto il cambio

        
        match_up_coeff = better_match_up_eval(my_active.type, opp_active_type, my_active.moves)

        # se il coefficiente è molto negativo il cambio è quasi obbligato, non sto nemmeno a verificare una possibile sequenza di mosse
        if match_up_coeff < -1.:
            #controllo il match up degli altri pkm nel team e scelgo
            return #switch
        '''


        root: BFSNode = BFSNode()
        root.g = g
        node_queue: List[BFSNode] = [root]
        while len(node_queue) > 0 and node_queue[0].depth < self.max_depth:
            current_parent = node_queue.pop(0)
            # assume opponent follows just the TypeSelector strategy, which is more greedy in damage
            o: GameState = deepcopy(current_parent.g)
            # opponent must see the teams swapped
            o.teams = (o.teams[1], o.teams[0])
            # IMPORTANTE: PER L'AVVERSARIO POSSO PROVARE AD UTILIZZARE UNA POLICY DIVERSA DAL TYPE_SELECTOR
            j = self.core_agent.get_action(o)
            # expand nodes with TypeSelector strategy plus non-damaging moves
            moves = []
            # PRUNING: controllo il match up e se risultasse essere molto negativo non provo nemmeno ad esplorare le mosse e tento gli switch
            active_match_up = better_match_up_eval(my_active.type, opp_active_type, list(map(lambda m: m.type, my_active.moves)), list(map(lambda m: m.type, [move for move in opp_active.moves if move.name!=None])))
            pkm1_match_up = better_match_up_eval(my_team.party[0].type, opp_active_type, list(map(lambda m: m.type, my_team.party[0].moves)), list(map(lambda m: m.type, [move for move in opp_active.moves if move.name!=None])))
            pkm2_match_up = better_match_up_eval(my_team.party[1].type, opp_active_type, list(map(lambda m: m.type, my_team.party[1].moves)), list(map(lambda m: m.type, [move for move in opp_active.moves if move.name!=None])))
            if  active_match_up >= -1. or (active_match_up < -1. and not (pkm1_match_up > active_match_up or pkm2_match_up > active_match_up)):
                moves = [self.core_agent.get_action(current_parent.g)]+[i for i, m in enumerate(current_parent.g.teams[0].active.moves) if m.power == 0.]# dovrebbero esserci anche gli switch 
            else:         
                if pkm1_match_up > active_match_up:
                    moves.append(4)
                if pkm2_match_up > active_match_up:
                    moves.append(5)


            for i in moves:
                g = deepcopy(current_parent.g)
                s, _, _, _, _ = g.step([i, j])
                # our fainted increased, skip
                if n_fainted(s[0].teams[0]) > n_fainted(current_parent.g.teams[0]):
                    continue
                # our opponent fainted increased, follow this decision
                if n_fainted(s[0].teams[1]) > n_fainted(current_parent.g.teams[1]):
                    a = i
                    while current_parent != root:
                        a = current_parent.a
                        current_parent = current_parent.parent
                    return a
                # continue tree traversal
                node = BFSNode()
                node.parent = current_parent
                node.depth = node.parent.depth + 1
                node.a = i
                node.g = s[0]
                node_queue.append(node)
        # no possible win outcomes, return arbitrary action
        if len(node_queue) == 0:
            a = self.core_agent.get_action(g)
            return a
        # return action with most potential
        best_node = max(node_queue, key=lambda n: game_state_eval(n.g, n.depth))
        while best_node.parent != root:
            best_node = best_node.parent
        return best_node.a








#------------------------------------------------------utilities-------------------------------------------------------







def calculate_damage(move: PkmMove, pkm_type: PkmType, opp_pkm_type: PkmType, attack_stage: int, defense_stage: int, weather: WeatherCondition) -> float:
    if move.pp <= 0:
        move = Struggle
    
    fixed_damage = move.fixed_damage
    if fixed_damage > 0. and TYPE_CHART_MULTIPLIER[move.type][opp_pkm_type] > 0.:
        damage = fixed_damage
    else:
        stab = 1.5 if move.type == pkm_type else 1.
        if (move.type == PkmType.WATER and weather == WeatherCondition.RAIN) or (move.type == PkmType.FIRE and weather == WeatherCondition.SUNNY):
            weather = 1.5
        elif (move.type == PkmType.WATER and weather == WeatherCondition.SUNNY) or (move.type == PkmType.FIRE and weather == WeatherCondition.RAIN):
            weather = .5
        else:
            weather = 1.       
    
        stage_level = attack_stage - defense_stage
        stage = (stage_level + 2.) / 2 if stage_level >= 0. else 2. / (np.abs(stage_level) + 2.)
        multiplier = TYPE_CHART_MULTIPLIER[move.type][opp_pkm_type] if move != Struggle else 1.0
        damage = multiplier * stab * weather * stage * move.power
    return round(damage)


def CanAttackFirst(my_team:PkmTeam, opp_team:PkmTeam, opp_active:Pkm) -> int:
    """
    Get attack order for this turn.

    :return: -2 opp faster and has priority, -1 opp faster, 1 self faster and no opp prio, 0 same speed, 0.5 if faster but opp prio
    """
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
    for move in pkm1.moves:
        if calculate_damage(move, pkm1.type, pkm2.type, attack1, defense2, weather) >= pkm2.hp:
            return True
        return False
        
# funzione che controlla il vantaggio del mio pkm sull'altro
# se conoscessi le mosse dell'avversario sarebbe molto meglio!!!!!!!
# per valori di ritorno molto negativi è conveniente cambiare pokemon


def better_match_up_eval(my_pkm_type: PkmType, opp_pkm_type: PkmType, my_moves_type: List[PkmType], opp_moves_type: List[PkmType]) -> float:
    # controllo quanto l'avversario è in vantaggio in attacco
    my_resistance = 0.0
    for mtype in opp_moves_type+[opp_pkm_type]:
        bonus = TYPE_CHART_MULTIPLIER[mtype][my_pkm_type]
        if mtype==opp_moves_type:
            bonus = bonus*1.5
        my_resistance = max(bonus, my_resistance)
    
    
    # controllo quanto il mio pkm è in vantaggio in attacco
    my_offensivity = 0.0
    for mtype in my_moves_type:
        bonus = TYPE_CHART_MULTIPLIER[mtype][opp_pkm_type]
        if mtype==my_pkm_type:
            bonus = bonus*1.5
        my_offensivity = max(bonus, my_offensivity)

    return my_offensivity-my_resistance


def match_up_eval(my_pkm_type: PkmType, opp_pkm_type: PkmType, opp_moves_type: List[PkmType]) -> float:
    # determine defensive match up
    defensive_match_up = 0.0
    for mtype in opp_moves_type + [opp_pkm_type]:
        defensive_match_up = max(TYPE_CHART_MULTIPLIER[mtype][my_pkm_type], defensive_match_up)
    return defensive_match_up

        

class BFSNode:

    def __init__(self):
        self.a = None
        self.g = None
        self.parent = None
        self.depth = 0
        self.eval = 0.0


def n_fainted(t: PkmTeam):
    fainted = 0
    fainted += t.active.hp == 0
    if len(t.party) > 0:
        fainted += t.party[0].hp == 0
    if len(t.party) > 1:
        fainted += t.party[1].hp == 0
    return fainted


def game_state_eval(s: GameState, depth):
    mine = s.teams[0].active
    opp = s.teams[1].active
    return mine.hp / mine.max_hp - 3 * opp.hp / opp.max_hp - 0.3 * depth



class TypeSelector(BattlePolicy):
    """
    Type Selector is a variation upon the One Turn Lookahead competition that utilizes a short series of if-else
    statements in its decision-making.
    Source: http://www.cig2017.com/wp-content/uploads/2017/08/paper_87.pdf
    """

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
        if match_up_eval(my_active.type, opp_active.type, list(map(lambda m: m.type, opp_active.moves))) <= 1.0:
            return move_id

        # If we are not switch to the most favorable match up
        match_up: List[float] = []
        not_fainted = False
        for pkm in my_party:
            if pkm.hp == 0.0:
                match_up.append(2.0)
            else:
                not_fainted = True
                match_up.append(
                    match_up_eval(pkm.type, opp_active.type, list(map(lambda m: m.type, opp_active.moves))))

        if not_fainted:
            return int(np.argmin(match_up)) + 4

        # If our party has no non fainted pkm, lets give maximum possible damage with current active
        return move_id

