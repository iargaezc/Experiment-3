from otree.api import *
import math, random, os, re
from collections import defaultdict

import jeudede

doc = """
Récapitulatif des gains
"""


class C(BaseConstants):
    NAME_IN_URL = 'recap'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1
    N_DRAWN_ROUNDS=[1]
    SAME_PERIODS_FOR_ALL = False
    MINIMUM_PAYMENT = 3 # minimum payment in euros, as announced on the subscription page
    ONLINE = bool(int(open('online.txt').read())) if os.path.exists('online.txt') else True


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    wait_others_arrival_time=models.IntegerField(initial=0)
    drawn_periods=models.StringField(initial='')
    increased_to_minimum_payment=models.BooleanField()

# FUNCTIONS
def draw_periods(session,save_in_session=True,player=None):
    by_n_periods=defaultdict(list)
    for i in range(jeudede.C.NUM_ROUNDS):
        period=i+1
        if player is None or player.participant.vars["type"] != 1 or player.participant.vars["dice_draw"][period-1] == -1:
            #if either not p1 or p2 has seen this p1 (dice_draw erased)
            by_n_periods['opt1'].append(period)
    drawn_periods=[]
    for i,n in enumerate(by_n_periods.keys()):
        cperiods=by_n_periods[n].copy()
        random.shuffle(cperiods)
        cperiods_drawn=cperiods[:C.N_DRAWN_ROUNDS[i]]
        cperiods_drawn.sort()
        drawn_periods += cperiods_drawn
    if save_in_session: session.vars['drawn_periods'] = drawn_periods
    return drawn_periods
    
def get_drawn_periods(player:Player):
    if not C.SAME_PERIODS_FOR_ALL or not 'drawn_periods' in player.session.vars or len(player.session.vars['drawn_periods']) == 0:
        return draw_periods(player.session,C.SAME_PERIODS_FOR_ALL,player)
    return player.session.vars['drawn_periods']
    
def get_pay_periods(player:Player):
    if player.drawn_periods == '':
        player.drawn_periods = ','.join([str(el) for el in get_drawn_periods(player)])
    return [int(el) for el in player.drawn_periods.split(',')] if player.drawn_periods != '' else get_drawn_periods(player)



def readable_list(l,sep1=', ', sep2=' et '):
    res=""
    for i,el in enumerate(l):
        if i>0 and i<len(l)-1:
            res+=sep1
        elif i>0:
            res += sep2
        res += str(el)
    return res

# PAGES

class ResultsWaitPage(WaitPage):
    pass

class AttenteAppariement(Page):
    @staticmethod
    def live_method(player, data):
        print('received data from', player.id_in_group, ':')
        result_available=all([player.participant.vars["dice_draw"][ri] == -1 for ri in range(jeudede.C.NUM_ROUNDS)])
        if not result_available:
            player.participant.vars["email"]=data['email']
        else:
            player.participant.vars["just_email"] = True
        return {
            player.id_in_group: dict(
                finished=True, 
                email=data['email'] if not result_available else '-', 
                result_available=result_available
                )
            }

    @staticmethod
    def is_displayed(player):
        sess_comments = '' if player.session.comment is None else player.session.comment
        cmatch=re.search(r'finished\s*[:=]\s*(\d+)',sess_comments)
        sess_finished=False
        if cmatch is not None and cmatch.group(1).isdigit():
            fini=int(cmatch.group(1))
            if fini: sess_finished = True 
        if (
            player.participant.vars["type"] != 1 
            or all([player.participant.vars["dice_draw"][ri] == -1 for ri in range(jeudede.C.NUM_ROUNDS)])
            or sess_finished
        ): 
            return False
        return True
    
    @staticmethod
    def before_next_page(player, timeout_happened):
        player.participant.vars["email"]=''

class Results(Page):
    @staticmethod
    def vars_for_template(player: Player):
        paid_periods=get_pay_periods(player)
        mychoices=[]
        mygains=[]
        for per in paid_periods:
            cchoice=player.participant.vars["choices"][per-1]
            mychoices.append(cchoice)
            mygains.append(cchoice if cchoice != 6 else 0)
            gain_from_partner = player.participant.vars["gain_from_partner"] if "gain_from_partner" in player.participant.vars else 0
            mygains.append(gain_from_partner)
        roundto05=True
        roundto1 = False
        player.payoff = sum(mygains)
        totalpoints=round(sum(mygains),2)
        totalpayoff=float(player.participant.payoff_plus_participation_fee())
        increased_to_minimum_payment = False
        if totalpayoff < C.MINIMUM_PAYMENT:
            player.payoff += C.MINIMUM_PAYMENT - totalpayoff
            totalpayoff = float(player.participant.payoff_plus_participation_fee())
            increased_to_minimum_payment = True
        player.increased_to_minimum_payment = increased_to_minimum_payment
        totalpayoff2=math.ceil(totalpayoff*2)/2 if roundto05 else totalpayoff
        totalpayoff3=math.ceil(totalpayoff)
        rounded=not roundto1 and (totalpayoff2 != totalpayoff)
        rounded1 = roundto1 and (totalpayoff3 != totalpayoff)
        return dict(
            drawn_periods=readable_list(paid_periods),
            n_drawn_periods=len(paid_periods),
            my_choices=readable_list(mychoices),
            my_gains=readable_list(mygains,'+','+'),
            sumgains=sum(mygains),
            monnai='euro',
            totalpoints=totalpoints,
            totalpointsineuros=cu(player.participant.payoff), #.to_real_world_currency(player.session),
            totalpayoff=player.participant.payoff_plus_participation_fee(),
            totalpayoff2=cu(totalpayoff3) if rounded1 else cu(totalpayoff2) if roundto05 else player.participant.payoff_plus_participation_fee(),
            rounded=rounded,
            rounded1=rounded1,
            increased_to_minimum_payment = increased_to_minimum_payment,
        )


page_sequence = [AttenteAppariement,Results]
