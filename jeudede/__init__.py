from otree.api import *
import math, random, os, pandas, copy, inspect
import re
from typing import Union,Optional,Callable,List,Dict,Any #in order to annotate the return types of *bp_* functions
from itertools import takewhile
import settings
from payinfo import readable_list

doc = """
Jeu principal du lancement de dé (Dice under the cup)
"""

import smtplib
import threading
import json
import sys
import datetime, time

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from os.path import exists


class PlayerVariables:
    # additional player variables should be defined here
    type = models.IntegerField(initial = 0)
    treatment = models.IntegerField(initial = -1)
    partner =  models.IntegerField(initial = 0)
    partner_type =  models.IntegerField(initial = 0)
    condition = models.StringField()
    gain_from_partner =  models.IntegerField(initial = 0)
    level_index = models.IntegerField()
    level_info = models.StringField()
    partner_level_index = models.IntegerField()
    partner_level_info = models.StringField()
    eco_level = models.StringField()
    pol_level = models.StringField()
    color_my_level = models.StringField()
    color_partner_level = models.StringField()
    color_other_level = models.StringField()
    partner_choice = models.IntegerField()
    n_instr_clicks = models.IntegerField()
    # test = models.IntegerField(initial = 1)
    # pass

# import leepquest:
with open('LQ.py','r', encoding="utf-8") as f:
    content = f.read()
exec(content)

# STANDARD OTREE CLASSES (except Player which is inside LQ.py with (optional) additional variables in the PlayerVariables class above)
# (the C class should inherit from the leepquest's LQ_C class (which inherits from BaseConstants) )

class C(LQ_C):
    NAME_IN_URL = 'jeudede'
    PLAYERS_PER_GROUP = None
    TEST_DICE=False
    NUM_ROUNDS = 24
    ECO_LEVELS=[
        ['02', '03', '04', '05', '07', '08', '09', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '22', '23', '24', '26', '27', '2B', '202', '206', '30', '32', '34', '36', '40', '41', '42', '43', '46', '47', '48', '49', '50', '51', '52', '53', '54', '55', '57', '58', '59', '61', '62', '65', '66', '70', '71', '72', '76', '79', '80', '81', '82', '84', '85', '86', '87', '88', '89', '90', '93', '971', '972', '973', '974', '976'],
        ['01', '06', '21', '25', '28', '29', '2A', '200', '201', '31', '33', '35', '37', '38', '39', '44', '45', '56', '60', '63', '64', '67', '68', '69', '73', '74', '77', '78', '83', '91', '94', '95'],
        ['75','92']
    ]
    ECO_LEVELS_EXCLUDE=[[],[],[]]
    ECO_LEVELS_INFO=['L','M','H']
    ELECTIONS_INFO=['NFP','EPR','RN']
    ELECTIONS=[['75003','75004','75010','75011','75012','75013','75014','75018','75019','75020'],['75001','75002','75005','75007','75008','75015','75016','78000','78100','78110','78500','78600'],['06']]
    ELECTIONS_EXCLUDE=[[],[],['06160','06600','06410','06620','06220','06210','06150','06400','06110','06130','06520','06810','06580','06250','06370','06550','06590','06560','06330','06140','06650','06740','06620','06460','06650']]
    COMB_INFO=settings.COMB_INFO #[['H+M','NFP+EPR(EP+WP)'],['H+L','NFP+RN(EP+N)'],['M+L','EPR+RN(WP+N)']]
    INCLUDE_P0_DICE_DISTR=True
    COLORS=["DarkViolet","DarkOrange"]
    WORDCOUNT="zéro;un;deux;trois;quatre;cinq;six;sept;huit;neuf;dix".split(";")
    PENALTY=2
    REWARD=2
    CONDITIONS=["OBSERVER","PENALTY","REWARD"]
    TREATMENTS=[1,2,3]
    T3_TYPES=[2,3,4]
    COMBINATIONS=[1,2,3]
    email_config = {}
    if exists('config.json'):
        with open('config.json', 'r') as f: email_config=json.load(f)
    

class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class DrawStats(ExtraModel):
    subsession = models.Link(Subsession)
    treatment = models.IntegerField()
    combination = models.IntegerField()
    combination_info = models.StringField()
    draw = models.IntegerField()
    infos_combined = [C.ECO_LEVELS_INFO]
    for h,infos in enumerate(infos_combined):
        for i1,lev1 in enumerate(infos):
            for i2,lev2 in enumerate(infos):
                locals()[lev1+'_'+lev2] = models.IntegerField()
                if h == len(infos_combined) - 1 and i1 == i2 == len(infos) - 1:
                    del h,infos,i1,i2,lev1,lev2,infos_combined
    for i,lev in enumerate(C.ECO_LEVELS_INFO):
        locals()[lev+'_p1'] = models.IntegerField()
        locals()[lev+'_p2'] = models.IntegerField()
        locals()[lev+'_p3'] = models.IntegerField()
        locals()[lev+'_p4'] = models.IntegerField()
        # locals()[lev+'_reported_p1'] = models.IntegerField()
        # locals()[lev+'_reported_p2'] = models.IntegerField()
        if i == len(C.ECO_LEVELS_INFO)-1:
            del i,lev
    bothtypes = models.IntegerField()
    if C.INCLUDE_P0_DICE_DISTR:
        p0 = models.IntegerField()

class send_email(threading.Thread): 
    def __init__(self,data,config):
        threading.Thread.__init__(self)
        self.data = data
        self.config = config

    def run(self):
        data = self.data
        config = self.config
        # print(config)
        msg = MIMEMultipart('alternative')
        msg['Subject'] = data['subject'] if 'subject' in data else ""
        msg['From'] = config['user']
        msg['To'] = data['email']
        if 'text' in data: msg.attach(MIMEText(data['text'], 'plain'))
        if 'html' in data: msg.attach(MIMEText(data['html'], 'html'))
        res=None
        if sys.platform.startswith("linux") and ('use_linux_sendmail' in config and config['use_linux_sendmail']):
            from subprocess import Popen, PIPE
            timout_sec=15
            with Popen(["/usr/sbin/sendmail", "-t", "-oi", "-f", config['user']], stdin=PIPE, stdout=PIPE) as p:
                try:
                    res = p.communicate(msg.as_bytes(),timeout=timout_sec)
                except TimeoutExpired:
                    p.kill()
                    print("Exitting sendmail process after %d seconds of waiting, email %s"%(timout_sec,data['email']))
        else:
            if "port" in config and config["port"]:
                s = smtplib.SMTP_SSL(config["server"], config["port"])
            elif "server" in config and config["server"]:
                s = smtplib.SMTP(config["server"])
            else:
                s = smtplib.SMTP()
            s.ehlo_or_helo_if_needed()
            if 'password' in config and config["password"]: s.login(config['user'], config['password'])
            # print( msg.as_string())
            res=s.sendmail(config['user'], data['email'], msg.as_string())
            s.quit()
        print("sent mail:",data['email'],res, flush=True)
        sent=True
        # self.player.participant.vars["email_sent"]=True #need to use REST_API in order to register email_sent variable 


# FUNCTIONS
def get_player_by_number(subsession,n,attr=''):
    may_use_condition = 'condition' in inspect.signature(subsession.get_players).parameters
    players = subsession.get_players(condition=f"participant.id_in_session == {n}") if may_use_condition else subsession.get_players()
    if may_use_condition:
        if len(players) == 0:
            print("Warning: no player found with id_in_session = %d in subsession %s"%(n,subsession.id))
            players = subsession.get_players()
        if len(players) == 1:
            return players[0] if not attr else getattr(players[0],attr)
    if len(players) == 0:
        return None
    for p in players:
        if p.id_in_subsession == n:
            if attr:
                return getattr(p,attr)
            return p

def creating_session(subsession: Subsession):
    LQ_creating_session(subsession) ## leepquest stuff
    # put additional logic below
    session = subsession.session
    period = subsession.round_number
    players=subsession.get_players()
    poss_combs=C.COMBINATIONS
    if not session.config["all_in_one"]:
        if not session.config["treatment"] in C.TREATMENTS:
            raise ValueError('Please set the treatment to either '+readable_list(C.TREATMENTS,sep2=' or '))
        if not session.config["combination"] in poss_combs:
            combs_info=['%d (%s)'%(i+1,a[session.config["treatment"]-1]) for i,a in enumerate(C.COMB_INFO)]
            raise ValueError('Please set the combination to either '+readable_list(combs_info,sep2=' or '))
        min_players_len = C.NUM_ROUNDS*2
        if session.config["treatment"] == 3: min_players_len = C.NUM_ROUNDS*len(C.T3_TYPES)
        treatments = [session.config["treatment"]]
        combinations = [session.config["combination"]]
    else:
        min_players_len = C.NUM_ROUNDS*len(C.T3_TYPES)*2*len(poss_combs) + C.NUM_ROUNDS*2*len(poss_combs)*(len(C.TREATMENTS)-1) #T3 + T1&T2
        treatments = C.TREATMENTS #[C.TREATMENTS[-1]]+C.TREATMENTS[:-1]
        combinations = poss_combs
    if len(session.config['app_sequence']) > 1 and len(players) <= min_players_len:
        raise ValueError('The number of players should be more than %d !'%(min_players_len))
    for tr in treatments:
        for combination in combinations:
            combination_info = C.COMB_INFO[combination-1][tr-1].split('(')[0]
            if subsession.round_number == 1:
                # session.treatment=session.config["treatment"]
                # session.combination=session.config["combination"]
                # session.combination_info = C.COMB_INFO[session.combination-1][session.treatment-1].split('(')[0]
                session.vars['day']=0
                session.vars['current_type']=0
                session.vars['n_group_errors']=0
                sess_prefix = ''
                if settings.USE_ALL_IN_ONE > 0:
                    sess_prefix=f'tr{tr}_comb{combination}_'
                infos = C.ECO_LEVELS_INFO
                combs=combination_info.split('+')
                drawstats_params=dict(subsession = subsession, treatment = tr, combination = combination, combination_info=combination_info)
                p2types = C.T3_TYPES if tr == 3 else [2] #bug: not enough values in session.vars' lists; T3_TYPES are subtypes
                # p1types = [1]*len(C.T3_TYPES) if tr == 3 else [1] 
                for gl_type_index,pl_types in enumerate(([1],p2types)):
                    pl_type = gl_type_index + 1
                    clists=[]
                    for ib in range(len(p2types)):
                        cplist = []
                        for c_pl_type in pl_types:
                            for i in range(len(combs)):
                                cplist += [{"level":infos.index(combs[i]),"pl_type":c_pl_type,"pl_subtype":c_pl_type}]*(C.NUM_ROUNDS//(len(combs)*len(pl_types)))
                        random.shuffle(cplist)
                        clists.append(cplist)
                    clist = sum(clists,[])
                    session.vars[sess_prefix+'p%d_levels'%pl_type]=[cl["level"] for cl in clist]
                    session.vars[sess_prefix+'p%d_types'%pl_type]=[cl["pl_type"] for cl in clist]
                    print(sess_prefix+'p%d_types :'%pl_type,session.vars[sess_prefix+'p%d_types'%pl_type])
                    # session.vars[sess_prefix+'p%d_sybtypes'%pl_type]=[cl["pl_subtype"] for cl in clist]
                    session.vars[sess_prefix+'p%d_list'%pl_type]=[0]*len(clist)
                    session.vars[sess_prefix+'p%d_days'%pl_type]=[0]*len(clist)
                    session.vars[sess_prefix+'n_p%d_started'%pl_type]=0
                    session.vars[sess_prefix+'n_p%d_finished'%pl_type]=0
                session.vars[sess_prefix+'combination_info']=combination_info
                session.vars['n_p0_started']=0
                session.vars['n_p0_finished']=0
                for i in range(len(combs)): session.vars[sess_prefix+'n_level%d_finished'%(i+1)]=0
                for lev in C.ECO_LEVELS_INFO:
                    drawstats_params[lev+"_p1"]=0
                    drawstats_params[lev+"_p2"]=0
                    # drawstats_params[lev+"_reported_p1"]=0
                    # drawstats_params[lev+"_reported_p2"]=0
                for cinfs in [C.ECO_LEVELS_INFO]:
                    for lev1 in cinfs:
                        for lev2 in cinfs:
                            drawstats_params[lev1+'_'+lev2] = 0
                drawstats_params["bothtypes"] = 0
                if C.INCLUDE_P0_DICE_DISTR:
                    drawstats_params["p0"] = 0
                for d in range(6):
                    DrawStats.create(**(drawstats_params|dict(draw=d+1)))
            for player in players :
                if subsession.round_number == 1:
                    player.participant.vars["dice_draw"]=[0]*C.NUM_ROUNDS
                    player.participant.vars["choices"]=[0]*C.NUM_ROUNDS
                    player.participant.vars["finished"] = False
                    player.participant.vars["day"] = 0
                    player.participant.vars["type_order"] = 0
                    player.participant.vars["sess_prefix"] = sess_prefix

def set_type_and_partner(player):
        session=player.session
        subsession=player.subsession
        pc=player.participant.postal_code.strip() if len(session.config['app_sequence'])>1 else random.choice(sum(C.ECO_LEVELS,[]))+'000'
        mytr=0
        ctype=0
        mylevel=''
        mainvarname='eco_level'
        mycomb = 0
        mycombinfo = ''
        levels=C.ECO_LEVELS
        infos=C.ECO_LEVELS_INFO
        excludes=C.ECO_LEVELS_EXCLUDE
        index=-1
        # determining my level (on of 'L','M','H' or one of 'NFP','EPR','RN' depending on treatment) based on postal code (from previous app, now in participant vars)
        for i,level in enumerate(levels):
            for pcode in level:
                if pc.startswith(pcode) and not pc in excludes[i]:
                    index = i
                    break
            if index >= 0:
                mylevel=infos[index]
                break
        # print("pc=",pc,"index=",index)
        if index >= 0:
            if not session.config["all_in_one"]:
                treatments = [session.config["treatment"]]
                combinations = [session.config["combination"]]
            else:
                treatments = [C.TREATMENTS[-1]]+C.TREATMENTS[:-1]
                combinations = C.COMBINATIONS
            for tr in treatments:
                for combination in combinations:
                    combination_info = C.COMB_INFO[combination-1][tr-1].split('(')[0]
                    combs = combination_info.split('+')
                    sess_prefix = ''
                    if settings.USE_ALL_IN_ONE > 0:
                        sess_prefix=f'tr{tr}_comb{combination}_'
                    # getting the type (2 in day >1, day should be defined in session's comments or current_type explicitly defined in the session's comments)
                    cday=1
                    ctype=1
                    sess_comments = '' if player.session.comment is None else player.session.comment
                    cmatch=re.search(r'day\s*[:=]\s*(\d+)',sess_comments)
                    day_found_in_comment=False
                    n_p1_should_be = C.NUM_ROUNDS*len(C.T3_TYPES) if tr == 3 else C.NUM_ROUNDS
                    if cmatch is not None and cmatch.group(1).isdigit():
                        cday=int(cmatch.group(1))
                        day_found_in_comment = True
                    elif session.vars[sess_prefix+'n_p1_finished'] >= n_p1_should_be:
                        ctype=2
                    if cday > 1 and session.vars[sess_prefix+'n_p1_finished'] >= n_p1_should_be: ctype=2
                    print("treatment=",tr,"combination=",combination,"n_p1_should_be=",n_p1_should_be,"n_p1_finished=",session.vars[sess_prefix+'n_p1_finished'],"ctype=",ctype,"combs=",combs,"mylevel=",mylevel)
                    cmatch=re.search(r'current_type\s*[:=]\s*(\d+)',sess_comments)
                    if not cmatch is None and cmatch.group(1).isdigit():
                        ctype=int(cmatch.group(1))
                        ctype=max(ctype,2)
                    player.participant.vars["current_type"]=ctype
                    session.vars["day"]=cday
                    session.vars["current_type"]=ctype
                    if mylevel in combs:
                        # if my level (type d'arrondissemnt) correspond to the chosen combination for the current session
                        localtypes = C.T3_TYPES if ctype > 1 and tr == 3 else [ctype]
                        may_use_condition = 'condition' in inspect.signature(subsession.get_players).parameters
                        if may_use_condition:
                            players_iter = subsession.get_players(condition=f"treatment == {player.treatment} and type in {localtypes} and level_info == '{mylevel}'")
                            players_mylevel=[p for p in players_iter if p.participant.vars["sess_prefix"] == sess_prefix and (p.participant.vars['day']>=cday or p.participant.finished)]
                        else:
                            players_iter = takewhile(lambda pp: pp.participant._index_in_pages > 0,player.subsession.get_players())
                            players_mylevel=[p for p in players_iter if p.participant.vars["sess_prefix"] == sess_prefix and p.type in localtypes and (p.participant.vars['day']>=cday or p.participant.finished) and p.field_maybe_none('level_info') == mylevel ]
                        # finding if the are still places for my level in this session:
                        n_mylevel_should_be = n_p1_should_be//2
                        n_myleveltype_should_be = n_mylevel_should_be
                        if ctype >1 and tr == 3:
                            n_myleveltype_should_be = n_p1_should_be/3
                        if len(players_mylevel) < n_mylevel_should_be:
                            for i,lev_cindex in enumerate(session.vars[sess_prefix+'p%d_levels'%ctype]):
                                mytype = session.vars[sess_prefix+'p%d_types'%ctype][i]
                                players_mylevel_mytype=[p for p in players_mylevel if p.type == mytype]
                                print("  - ","i=",i,"lev_cindex=",lev_cindex,"index=",index,"mytype=",mytype,len(players_mylevel_mytype),"<",n_myleveltype_should_be,session.vars[sess_prefix+'p%d_days'%ctype][i], "<",cday, "(cday)")
                                #index is my level index
                                if index == lev_cindex and len(players_mylevel_mytype) < n_myleveltype_should_be and session.vars[sess_prefix+'p%d_days'%ctype][i] < cday and (session.vars[sess_prefix+'p%d_list'%ctype][i] == 0 or not get_player_by_number(subsession,session.vars[sess_prefix+'p%d_list'%ctype][i],'participant').finished):
                                    session.vars[sess_prefix+'p%d_days'%ctype][i] = cday
                                    session.vars[sess_prefix+'p%d_list'%ctype][i] = player.id_in_subsession
                                    player.participant.vars['type_order'] = i+1
                                    # setting parter's types
                                    other_type=3-ctype
                                    mytr = tr
                                    mycomb = combination
                                    mycombinfo = combination_info
                                    player.participant.vars['sess_prefix'] = sess_prefix
                                    player.color_my_level = random.choice(C.COLORS)
                                    for col in C.COLORS:
                                        if col != player.color_my_level:
                                            player.color_other_level = col
                                            break
                                    for p in player.in_rounds(1,C.NUM_ROUNDS):
                                        p.type=mytype
                                        p.level_index=index
                                        p.level_info=infos[index]
                                        setattr(p,mainvarname,infos[index])
                                        oi_base = math.floor(i/C.NUM_ROUNDS)*C.NUM_ROUNDS
                                        oi = oi_base + (i + p.round_number - 1)%C.NUM_ROUNDS if p.type > 1 else oi_base + (i - p.round_number + 1)%C.NUM_ROUNDS
                                        print("   -- ",sess_prefix+'p%d_levels'%other_type+":",session.vars[sess_prefix+'p%d_levels'%other_type])
                                        p.partner_level_index = session.vars[sess_prefix+'p%d_levels'%other_type][oi]
                                        p.partner_level_info = infos[p.partner_level_index]
                                        p.partner_type = session.vars[sess_prefix+'p%d_types'%other_type][oi]
                                        p.color_my_level = player.color_my_level
                                        p.color_other_level = player.color_other_level
                                        if session.vars[sess_prefix+'p%d_list'%other_type][oi] > 0:
                                            p.partner = session.vars[sess_prefix+'p%d_list'%other_type][oi]
                                    break
                    if mytr > 0:
                        break
                if mytr > 0:
                    break
        if mytr == 0:
            player.participant.vars['sess_prefix'] = ''
        for p in player.in_rounds(1,C.NUM_ROUNDS): 
            p.treatment = mytr
        player.participant.vars["treatment"]=mytr
        player.participant.vars["type"]=player.type
        player.participant.vars["combination"]=mycomb
        player.participant.vars["combination_info"]=mycombinfo
        player.participant.vars["level_info"]=player.field_maybe_none('level_info')
        sess_prefix = player.participant.vars['sess_prefix']
        session.vars[sess_prefix+'n_p%d_started'%min(2,p.type)] += 1
        player.participant.vars["time_started"] = time.time()
        player.participant.vars["datetime_started"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# skip_some_bp_quests is used to skip some questions inside blocpages (cbp is the current blocpage, n is the question number, var is the question's variable name (cbp+n and var are interchangeable), function can one of "get_form_fields","vars_for_template","before_next_page" )
def skip_some_bp_quests(player:Player,cbp:str,n:int,var:str,function:Optional[str]=None) -> bool:
    # example: if cbp == 'B2' and n > 1 and player.treatment > 3: return True
    if cbp == 'INTRO' and n > 1 and player.treatment <= 0: return True
    if cbp == 'CHOICE' and var != "choice" and (player.type <= 1 or (player.treatment == 3 and player.type == 2)): return True
    return False
    
# hide_some_bp_quests is used to hide some questions inside blocpages (var is the question's variable name). Unlike skip_some_bp_quests this function does not remove the corresponding part from blocpage sequence if blocpage's BY argument equals 1
def hide_some_bp_quests(player:Player, var:str)->bool:
    # example: if var == "others_evaluation" and player.treatment != 2 and player.treatment != 3: return True
    return False

# bp_is_displayed is used to dynamically exclude some blocpages (cbp is the current blocpage's name)
def bp_is_displayed(player:Player, cbp:str)->bool:
    if cbp == 'INTRO' and player.round_number > 1: return False
    return True

# bp_get_timeout_seconds is used to add a timeout to some blocpages, in should return (cbp is the current blocpage's name)
def bp_get_timeout_seconds(player:Player, cbp:str) -> Union[int,None]:
    # example: if cbp == "RAVEN" : return 60*C.RAVEN_MINUTES
    return None

# bp_get_form_fields is used to add additional fields to blocpages (the additional fields should be defined in PlayerVariables class above, created before importing LQ.py)
def bp_get_form_fields(player:Player, cbp:str) -> List[str]:
    if cbp == 'CHOICE':
        return ['n_instr_clicks']
    return []

# bp_vars_for_template is used to to add additional variables for blocpage template (cbp is the current blocpage's name)
def bp_vars_for_template(player:Player,cbp:str) -> Dict[str,Any]:
    if cbp == "CHOICE":
        draw_result=player.participant.vars["dice_draw"][player.round_number-1] if player.participant.vars["dice_draw"][player.round_number-1] != 0 else 1 if player.round_number == 1 else player.participant.vars["dice_draw"][player.round_number-2]
        draw_done=not C.TEST_DICE and player.participant.vars["dice_draw"][player.round_number-1] != 0
        revenu_me=''; revenu_partner=''; unempl_me=''; unempl_partner=''; pol_level_me=''; pol_level_partner=''
        if player.type > 0:
            revenu_me = getattr(C,cbp+'_REVENUS')[player.level_index]
            revenu_partner = getattr(C,cbp+'_REVENUS')[player.partner_level_index]
            unempl_me = getattr(C,cbp+'_CHOMAGES')[player.level_index]
            unempl_partner = getattr(C,cbp+'_CHOMAGES')[player.partner_level_index]
        others_choice = 0
        if player.type > 1:
            draw_done=True
            op=get_player_by_number(player.subsession,player.partner)
            if not op is None:
                draw_result=op.participant.vars["dice_draw"][player.round_number-1]
                others_choice=op.participant.vars["choices"][player.round_number-1]
        if player.type > 0:
            player.color_partner_level = player.color_my_level if player.level_index == player.partner_level_index else player.color_other_level
            player.partner_choice = others_choice
        import payinfo
        n_drawn_periods=payinfo.C.N_DRAWN_ROUNDS[0]
        ns_drawn_periods=C.WORDCOUNT[n_drawn_periods]
        return dict(
            draw_done=draw_done,
            draw_result=draw_result,
            others_choice=others_choice,
            revenu_me=revenu_me,
            revenu_partner=revenu_partner,
            unempl_me=unempl_me,
            unempl_partner=unempl_partner,
            pol_level_me=pol_level_me,
            pol_level_partner=pol_level_partner,
            format_social_info=1, #1 as in experiment 1 with <ul>, 2 as phrases
            average_country_income="1,993 euros par mois",
            initial_presentation="secondary_presentation",
            n_drawn_periods=n_drawn_periods,
            ns_drawn_periods=ns_drawn_periods,
            third_periods=C.NUM_ROUNDS//3,
        )
    if cbp == "INTRO":
        import payinfo
        n_drawn_periods=payinfo.C.N_DRAWN_ROUNDS[0]
        ns_drawn_periods=C.WORDCOUNT[n_drawn_periods]
        return dict(n_drawn_periods=n_drawn_periods,ns_drawn_periods=ns_drawn_periods,third_periods=C.NUM_ROUNDS//3,initial_presentation="initial_presentation")
    return {}

# bp_js_vars is used to to add additional variables to the otree's js_vars (cbp is the current blocpage's name)
def bp_js_vars(player:Player,cbp:str) -> Dict[str,Any]:
    return {}

# bp_before_next_page is used to execute additional code before passing to the next blocpage (cbp is the current blocpage's name, next_cbp is the next blocpage's name)
def bp_before_next_page(player:Player,timeout_happened:bool, cbp:str, next_cbp:str) -> None:
    if cbp == "CHOICE":
        player.participant.vars["choices"][player.round_number-1]=player.choice
        if player.type > 1 and player.partner > 0:
            mypartner = get_player_by_number(player.subsession,player.partner)
            mypartner.partner = player.id_in_subsession
            mypartner.partner_type = player.type
            mypartner.partner_choice = player.choice
            condition_index = player.treatment if player.treatment < 3 else player.type-2
            player.condition = C.CONDITIONS[condition_index]
            mypartner.condition = player.condition
            mypartner.participant.vars["condition"] = mypartner.condition
            mypartner.participant.vars["partner_type"] = mypartner.partner_type
            if player.field_maybe_none("action") is not None and player.action == 1:
                if player.condition == "PENALTY":
                    mypartner.gain_from_partner = -C.PENALTY
                elif player.condition == "REWARD":
                    mypartner.gain_from_partner = C.REWARD
            mypartner.participant.vars["gain_from_partner"] = mypartner.gain_from_partner
            if mypartner.field_maybe_none('partner_level_index') != player.level_index or mypartner.field_maybe_none('partner_level_info') != player.level_info or player.partner_level_index != mypartner.field_maybe_none('level_index') or player.partner_level_info != mypartner.field_maybe_none('level_info'):
                player.session.vars['n_group_errors'] += 1
                print("Error found: levels mismatch for p1 %d (%s) and p2 %d (%s) in round %d:"%(mypartner.id_in_subsession,mypartner.participant.code,player.id_in_subsession,player.participant.code,player.round_number))
                print('  p1.partner_level_index =',mypartner.field_maybe_none('partner_level_index'),'p2.level_index =',player.level_index)
                print('  p1.partner_level_info =',mypartner.field_maybe_none('partner_level_info'),'p2.level_info =',player.level_info)
                print('  p2.partner_level_index =',player.field_maybe_none('partner_level_index'),'p1.level_index =',mypartner.field_maybe_none('level_index'))
                print('  p2.partner_level_info =',player.field_maybe_none('partner_level_info'),'p1.level_info =',mypartner.field_maybe_none('level_info'))
                print('  p2.partner =',player.field_maybe_none('partner'),'p1.partner =',mypartner.field_maybe_none('partner'))
                print('  p2.round_number =',player.round_number,'p1.round_number =',mypartner.round_number)
        if player.type != 1:
            if player.type == 0 and C.INCLUDE_P0_DICE_DISTR:
                drawstats = DrawStats.filter(subsession=player.in_round(1).subsession,draw=player.participant.vars["dice_draw"][player.round_number-1])
                drawstats[0].p0 += 1
            # erasing draw result:
            if player.round_number>1: player.participant.vars["dice_draw"][player.round_number-2] = -1
            if player.round_number == C.NUM_ROUNDS: player.participant.vars["dice_draw"][player.round_number-1] = -1
        if player.round_number == C.NUM_ROUNDS:
            player.participant.vars["finished"] = True
            sess_prefix = player.participant.vars['sess_prefix']
            player.session.vars[sess_prefix+'n_p%d_finished'%min(2,player.type)] += 1
            combs=player.participant.vars["combination_info"].split('+')
            if player.type > 0: player.session.vars[sess_prefix+'n_level%d_finished'%(combs.index(player.level_info)+1)] += 1
            if player.type == 1:
                # incrementing DrawStats for p1
                for p in player.in_all_rounds():
                    drawstats = DrawStats.filter(subsession=player.in_round(1).subsession,draw=p.participant.vars["dice_draw"][p.round_number-1],treatment=player.participant.vars["treatment"],combination=player.participant.vars["combination"])
                    # print( "drawstats:",drawstats,"draw:",mp.participant.vars["dice_draw"][p.round_number-1])
                    setattr(drawstats[0],p.level_info+'_p%d'%player.type,getattr(drawstats[0],p.level_info+'_p%d'%player.type) + 1)
                    setattr(drawstats[0],p.level_info+'_'+p.partner_level_info,getattr(drawstats[0],p.level_info+'_'+p.partner_level_info) + 1)
                    drawstats[0].bothtypes += 1
            if player.type > 1:
                # erasing p1's  draw results (only p1 who were my partners in corresponding periods) after incrementing DrawStats for p2
                for p in player.in_all_rounds():
                    mp = get_player_by_number(p.subsession,p.partner)
                    # ds_instance=DrawStats(subsession=player.in_round(1).subsession,draw=mp.participant.vars["dice_draw"][p.round_number-1]) #does not increment in the databaseS
                    drawstats = DrawStats.filter(subsession=player.in_round(1).subsession,draw=mp.participant.vars["dice_draw"][p.round_number-1],treatment=player.participant.vars["treatment"],combination=player.participant.vars["combination"])
                    # print( "drawstats:",drawstats,"draw:",mp.participant.vars["dice_draw"][p.round_number-1])
                    prevval = getattr(drawstats[0],p.level_info+'_p%d'%player.type)
                    if prevval is None: prevval = 0
                    setattr(drawstats[0],p.level_info+'_p%d'%player.type,prevval + 1)
                    # erasing:
                    mp.participant.vars["dice_draw"][p.round_number-1] = -1
                    if all([mp.participant.vars["dice_draw"][ri] == -1 for ri in range(C.NUM_ROUNDS)]):
                        #this p1 may go to the gain page
                        session = player.session
                        if "email" in mp.participant.vars and mp.participant.vars["email"]:
                            data={}
                            data["subject"]="Le résultat est disponible pour l'expérience "+session.config["expe"]
                            mess_text="<p>Bonjour,</p><p>Votre résultat de l'expérience {} est disponible. Vous pouvez cliquer sur le lien suivant afin de consulter votre gain final et remplir les coordonnées bancaires pour recevoir le paiement : <br><a href='{}'>{}</a></p><p>Cordialement, </p><p>L'équipe du LEEP</p>".format(session.config["expe"],mp.participant.vars["init_link"],mp.participant.vars["init_link"])
                            data["text"]=re.sub(r'<[^>]+>', '\n', mess_text)
                            data["html"]=mess_text
                            data["email"]=mp.participant.vars["email"]
                            email_service = send_email(data,C.email_config)
                            email_service.start()
                            email_sent=True
                            mp.participant.vars["email"] = ""



# bp_live_event is used to capture liveSend events, the data sent and returned should be in string format and prefixed by "custom|"
def bp_live_event(player:Player,cbp:str,data:str) -> Union[Dict[int,Any],None]:
    # return None
    if cbp == "CHOICE" and data == "get_dice_draw":
        if player.participant.vars["dice_draw"][player.round_number-1] == 0:
            player.participant.vars["dice_draw"][player.round_number-1]=random.randint(1,6)
        # print("received custom",data,"dice_draw:",player.participant.vars["dice_draw"][player.round_number-1])
        return {player.id_in_group:"custom|"+str(player.participant.vars["dice_draw"][player.round_number-1])}


#PAGES
# define additional pages in a standard way

# class MyPage(Page):
    # pass 

# compose the page sequence :

# page_sequence = [MyPage, BlocPage] ### in order to place custom pages before blocpages

class SettingUp(Page):
    def is_displayed(player):
        return player.round_number == 1
    def before_next_page(player,timeout_happened):
        set_type_and_partner(player)
            
class SetUpPage(WaitPage):
    group_by_arrival_time = True
    @staticmethod
    def is_displayed(player):
        return player.round_number == 1

def group_by_arrival_time_method(subsession, waiting_players):
    for player in waiting_players:
        set_type_and_partner(player)
        # make a single-player group.
        return [player]

page_sequence = [SetUpPage,BlocPage]

# the code below adds the necessary number of blocpages in order to correspond to the leepquest.xlsx (or [appname].xlsx) confifuration file
if page_sequence.count(BlocPage) < len(C.BLOCPAGES):
    for i in range(len(C.BLOCPAGES)-page_sequence.count(BlocPage)):
        page_sequence.append(BlocPage)

### a way to place additional custom pages at the end :
# custom_page_sequence=[MyPage]        
# page_sequence +=custom_page_sequence


def custom_export(players,addstats=False):
    headers=['session_code','session_label']
    keys_to_exclude=['subsession']
    for k in DrawStats.__dict__.keys():
            if k[0]!='_' and not k in keys_to_exclude : 
                headers.append(k)
                if addstats:
                    ak=k.split('_')
                    if ak[0] in C.ECO_LEVELS_INFO+['bothtypes','p0']:
                        if (len(ak) == 2 and ak[1] in C.ECO_LEVELS_INFO) or k=='bothtypes':
                            headers.append('regp1_'+k)
                            headers.append('regp2_'+k)
                        else:
                            headers.append('reg_'+k)
    yield headers
    cdlist = DrawStats.filter()
    for cd in cdlist:
        session = cd.subsession.session
        cdline=[session.code,session.label]
        if addstats:
            sess_comments = '' if session.comment is None else session.comment
            may_use_condition = 'condition' in inspect.signature(cd.subsession.get_players).parameters
            subsession_players = []
            if not "skip_comparative_stats" in sess_comments:
                subsession_players_base = cd.subsession.get_players(condition=f"treatment == {cd.treatment} or type == 0") if may_use_condition else cd.subsession.get_players()
                subsession_players = [p for p in takewhile(lambda pp: pp.participant._index_in_pages > 0,subsession_players_base) if (p.participant.finished and p.participant.vars["treatment"] == cd.treatment and p.participant.vars["combination"] == cd.combination) or p.type==0] #cd.subsession.get_players()
        for k in DrawStats.__dict__.keys():
            if k[0]!='_' and not k in keys_to_exclude : 
                cdline.append(getattr(cd,k))
                if addstats:
                    ak=k.split('_')
                    if ak[0] in C.ECO_LEVELS_INFO+['bothtypes','p0']:
                        r1_players=[p for p in subsession_players if (ak[0] == 'p0' and p.treatment==0 and p.type==0) or (ak[0] == 'bothtypes' and p.treatment > 0 and p.type == 1) or (len(ak)==2 and p.treatment > 0 and ((p.type==1 and ak[1] in C.ECO_LEVELS_INFO) or ak[1] == 'p%d'%p.type))]
                        n=0
                        for p in r1_players:
                            for rp in p.in_rounds(1,C.NUM_ROUNDS):
                                if rp.choice == cd.draw and (k in ['bothtypes','p0',str(p.level_info)+'_'+'p%d'%rp.type] or (ak[0] == rp.level_info and ak[1] == rp.partner_level_info)):
                                    n += 1
                        cdline.append(n)
                        if (len(ak) == 2 and ak[1] in C.ECO_LEVELS_INFO) or k=='bothtypes':
                            r1_players_p2=[p for p in subsession_players if (k== 'bothtypes' and p.treatment > 0 and p.type > 1) or (len(ak)==2 and p.treatment > 0 and p.type > 1)]
                            n=0
                            for p in r1_players_p2:
                                for rp in p.in_rounds(1,C.NUM_ROUNDS):
                                    if rp.choice == cd.draw and (k== 'bothtypes' or (ak[0] == rp.partner_level_info and ak[1] == rp.level_info)):
                                        n += 1
                            cdline.append(n)
        yield cdline

def custom_export_with_stats(players):
    return custom_export(players,True)
    
custom_exports=[{'file_prefix':'drawing_statistics','function':'custom_export'},{'file_prefix':'drawing_comparative_stats','function':'custom_export_with_stats'}]
