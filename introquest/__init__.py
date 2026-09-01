from otree.api import *
import math, random, os, pandas, inspect, re

from typing import Union,Optional,Callable,List,Dict,Any #in order to annotate the return types of *bp_* functions
from itertools import takewhile


doc = """
Questionnaire préliminaire
"""

class PlayerVariables:
    # additional player variables should be defined here
    # test = models.IntegerField(initial = 1)
    init_link = models.StringField()

# import leepquest:
with open('LQ.py','r', encoding="utf-8") as f:
    content = f.read()
exec(content)

# STANDARD OTREE CLASSES (except Player which is inside LQ.py with (optional) additional variables in the PlayerVariables class above)
# (the C class should inherit from the leepquest's LQ_C class (which inherits from BaseConstants) )
class C(LQ_C):
    NAME_IN_URL = 'introquest'
    PLAYERS_PER_GROUP = None
    WORDCOUNT="zéro;une;deux;trois;quatre;cinq;six;sept;huit;neuf;dix".split(";")
    NUM_ROUNDS = 1

class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


# FUNCTIONS
def get_player_by_code(subsession,code,attr=''):
    may_use_condition = 'condition' in inspect.signature(subsession.get_players).parameters
    players = subsession.get_players(condition=f"participant.code == '{code.strip()}'") if may_use_condition else subsession.get_players()
    if may_use_condition:
        if len(players) == 0:
            print("Warning: no player found with participant.code = %s in subsession %s"%(code,subsession.id))
            players = subsession.get_players()
        if len(players) == 1:
            return players[0] if not attr else getattr(players[0],attr)
    if len(players) == 0:
        return None
    for p in players:
        if p.participant.code == code.strip():
            if attr:
                return getattr(p,attr)
            return p

def creating_session(subsession: Subsession):
    LQ_creating_session(subsession) ## leepquest stuff
    # put additional logic below

# skip_some_bp_quests is used to skip some questions inside blocpages (cbp is the current blocpage, n is the question number, var is the question's variable name (cbp+n and var are interchangeable), function can one of "get_form_fields","vars_for_template","before_next_page" )
def skip_some_bp_quests(player:Player,cbp:str,n:int,var:str,function:Optional[str]=None) -> bool:
    # example: if cbp == 'B2' and n > 1 and player.treatment > 3: return True
    return False
    
# hide_some_bp_quests is used to hide some questions inside blocpages (var is the question's variable name). Unlike skip_some_bp_quests this function does not remove the corresponding part from blocpage sequence if blocpage's BY argument equals 1
def hide_some_bp_quests(player:Player, var:str)->bool:
    # example: if var == "others_evaluation" and player.treatment != 2 and player.treatment != 3: return True
    return False

# bp_is_displayed is used to dynamically exclude some blocpages (cbp is the current blocpage's name)
def bp_is_displayed(player:Player, cbp:str)->bool:
    return True

# bp_get_timeout_seconds is used to add a timeout to some blocpages, in should return (cbp is the current blocpage's name)
def bp_get_timeout_seconds(player:Player, cbp:str) -> Union[int,None]:
    # example: if cbp == "RAVEN" : return 60*C.RAVEN_MINUTES
    return None

# bp_get_form_fields is used to add additional fields to blocpages (the additional fields should be defined in PlayerVariables class above, created before importing LQ.py)
def bp_get_form_fields(player:Player, cbp:str) -> List[str]:
    if cbp == "INTRO":
        return ["init_link"]
    return []

# bp_before_next_page is used to execute additional code before passing to the next blocpage (cbp is the current blocpage's name, next_cbp is the next blocpage's name)
def bp_before_next_page(player:Player,timeout_happened:bool, cbp:str, next_cbp:str) -> None:
    if cbp == "QUEST":
        if player.participant.label and player.participant.label in player.session.config['bot_labels'] and "jeudede" in player.session.config['app_sequence']:
            # assure correct postal code by artificial player
            from jeudede import C as jddC
            session = player.session
            combs=session.vars[player.participant.vars["sess_prefix"]+'combination_info'].split('+')
            infos = jddC.ECO_LEVELS_INFO # if session.treatment==1 else jddC.ELECTIONS_INFO
            pcodes_levels = jddC.ECO_LEVELS # if session.treatment==1 else jddC.ELECTIONS
            bot_pcs=[]
            if player.session.config["all_in_one"]:
                for pc_level in pcodes_levels:
                    bot_pcs.append(pc_level[0])
            else:
                for i in range(len(combs)): 
                    bot_pcs.append(pcodes_levels[infos.index(combs[i])][0])
            bot_pc = random.choice(bot_pcs)
            if len(bot_pc) == 2: bot_pc += "000"
            player.postal_code = bot_pc
        player.participant.vars["postal_code"]=player.postal_code
    if cbp == "INTRO":
        player.participant.vars["init_link"] = player.init_link.replace('/login/..','')
        player.init_link = ""
        # print("init_link=",player.participant.vars["init_link"])


# bp_vars_for_template is used to to add additional variables for blocpage template (cbp is the current blocpage's name)
def bp_vars_for_template(player:Player,cbp:str) -> Dict[str,Any]:
    if cbp == "INTRO":
        import jeudede, payinfo
        n_drawn_periods=payinfo.C.N_DRAWN_ROUNDS[0]
        ns_drawn_periods=C.WORDCOUNT[n_drawn_periods]
        return dict(num_periods=jeudede.C.NUM_ROUNDS,n_drawn_periods=n_drawn_periods,ns_drawn_periods=ns_drawn_periods)
    return {}

# bp_js_vars is used to to add additional variables to the otree's js_vars (cbp is the current blocpage's name)
def bp_js_vars(player:Player,cbp:str) -> Dict[str,Any]:
    return {}


#PAGES
# define additional pages in a standard way

class Surveillance(Page):
    @staticmethod
    def is_displayed(player):
        label = '' if not player.participant.label else player.participant.label
        sess_comments = '' if player.session.comment is None else player.session.comment
        cmatch=re.search(r'finished\s*[:=]\s*(\d+)',sess_comments)
        if cmatch is not None and cmatch.group(1).isdigit():
            fini=int(cmatch.group(1))
            if fini: 
                return True
        return label in ['surveillance720'] and player.round_number==1
    @staticmethod
    def live_method(player, data):
        if "type" in data and data["type"] == "request":
            # print("surveillance request from ",player.participant.label)
            return {player.id_in_group:Surveillance.vars_for_template(player)['data']}
        elif "type" in data and data["type"] == "set_email":
            # print("surveillance set_email from ",player.participant.label)
            concerned_player = get_player_by_code(player.subsession, data["participant_code"])
            if not concerned_player:
                return {player.id_in_group:{"type":"email","status":"error","message":"Participant not found."}}
            if "email" in data and data["email"]:
                concerned_player.participant.vars['email'] = data["email"].strip()
                return {player.id_in_group:{"type":"email","status":"ok","message":"Email updated successfully.", "email":concerned_player.participant.vars['email'], "success":True}}
            else:
                return {player.id_in_group:{"type":"email","status":"error","message":"Email cannot be empty."}}
        elif "type" in data and data["type"] == "get_email":
            # print("surveillance get_email from ",player.participant.label)
            concerned_player = get_player_by_code(player.subsession, data["participant_code"])
            if concerned_player and 'email' in concerned_player.participant.vars:
                return {player.id_in_group:{"type":"email","status":"ok","email":concerned_player.participant.vars['email']}}
            else:
                if concerned_player:
                    return {player.id_in_group:{"type":"email","status":"error","message":"Email not found for this participant."}}
                else:
                    return {player.id_in_group:{"type":"email","status":"error","message":"Participant not found.","hide_form":True}}
    @staticmethod
    def vars_for_template(player):
        label = '' if not player.participant.label else player.participant.label
        session_finished = False
        if label not in ['surveillance720']:
            sess_comments = '' if player.session.comment is None else player.session.comment
            cmatch=re.search(r'finished\s*[:=]\s*(\d+)',sess_comments)
            if cmatch is not None and cmatch.group(1).isdigit():
                fini=int(cmatch.group(1))
                if fini: 
                    session_finished = True
                    player.participant.vars['should_not_start'] = True
                    return dict(session_finished=True)
        from jeudede import C as jddC
        treatments = [jddC.TREATMENTS[-1]]+jddC.TREATMENTS[:-1]+[0]
        response = []
        session = player.session
        for tr in treatments:
            ctdata = dict(
                treatment=tr,
                combdata=[],
            )
            combinations = jddC.COMBINATIONS if tr > 0 else [0]
            tr_line = 0
            for combination in combinations:
                tr_line += 1
                if session.config["all_in_one"] or (session.treatment == tr and session.combination == combination):
                    sess_prefix=f'tr{tr}_comb{combination}_' if tr > 0 else ''
                    combination_info=session.vars[sess_prefix+'combination_info'] if sess_prefix+'combination_info' in session.vars else ""
                    # print("combination_info=",session.vars[sess_prefix+'combination_info'])
                    # combs = combination_info.split('+')
                    cdata = dict(
                        treatment=tr,
                        tr_line=tr_line,
                        combination=combination,
                        sess_prefix=sess_prefix,
                        combination_info=combination_info,
                        combs = ((i+1,v) for i,v in enumerate(combination_info.split('+')) if v) if combination_info else [],
                    )
                    ptypes = (1,2) if tr > 0 else [0]
                    for pt in ptypes:
                        cdata[f'n_p{pt}_started'] = session.vars.get(f'{sess_prefix}n_p{pt}_started', 0)
                        cdata[f'n_p{pt}_finished'] = session.vars.get(f'{sess_prefix}n_p{pt}_finished', 0)
                        cdata[f'n_level{pt}_finished'] = session.vars.get(f'{sess_prefix}n_level{pt}_finished', 0) if tr > 0 else ''
                    ctdata['combdata'].append(cdata)
                    # response.append(cdata)
                ctdata['ncombs'] = len(ctdata['combdata'])
            response.append(ctdata)
            import time
            start = time.time()
            players_started = [p for p in takewhile(lambda pp: pp.participant._index_in_pages > 0,player.subsession.get_players()) if 'time_started' in p.participant.vars and p.participant.vars['time_started']]
            
            
            # players_test = [p for p in player.subsession.get_players() if p.id_in_subsession in [500,1200]]
            # players_test = player.subsession.get_players("participant.id_in_session in [5,1,2,3,4,500,1200] and postal_code == '99000'") #.filter(Player.id_in_subsession == 500)
            players_started.sort(key=lambda p: p.participant.vars['time_started'], reverse=True)
            take_participants = 24
            end = time.time()
            print("Execution time:", end - start, "seconds")
        return {'session_finished':session_finished,'data':response,'participants':[p.participant for p in players_started[:take_participants]],'take_participants':take_participants,} #, 'players_test': players_test #[(p.participant.code, p.id_in_subsession) for p in players_test]
    @staticmethod
    def app_after_this_page(player, upcoming_apps):
            return upcoming_apps[-1] 

# compose the page sequence :

# page_sequence = [MyPage, BlocPage] ### in order to place custom pages before blocpages
page_sequence = [Surveillance,BlocPage]

# the code below adds the necessary number of blocpages in order to correspond to the leepquest.xlsx (or [appname].xlsx) confifuration file
if page_sequence.count(BlocPage) < len(C.BLOCPAGES):
    for i in range(len(C.BLOCPAGES)-page_sequence.count(BlocPage)):
        page_sequence.append(BlocPage)

### a way to place additional custom pages at the end :
# custom_page_sequence=[MyPage]        
# page_sequence +=custom_page_sequence
