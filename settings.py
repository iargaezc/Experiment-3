from os import environ
import random

SESSION_CONFIGS = [
    dict(
        name='introquest', 
        app_sequence=['introquest'], 
        num_demo_participants=1, 
    ),
    dict(
        name='jeudede', 
        app_sequence=['jeudede'], 
        num_demo_participants=2,
        treatment=1,
        combination=1
        
    ),
    dict(
        name='finalquest', 
        app_sequence=['finalquest'], 
        num_demo_participants=1, 
    ),
    dict(
        name='experiment', 
        app_sequence=['introquest','jeudede','finalquest','payinfo','redirecttopayment'], 
        num_demo_participants=5, 
    ),
]
USE_ALL_IN_ONE = 1

COMB_INFO=[['H+M']*3,['H+L']*3,['M+L']*3] #[['H+M','NFP+EPR(EP+WP)'],['H+L','NFP+RN(EP+N)'],['M+L','EPR+RN(WP+N)']]
init_len=len(SESSION_CONFIGS)
SESSION_CONFIGS += [{}]*len(COMB_INFO)*3
if USE_ALL_IN_ONE < 2:
    for i,infos in enumerate(COMB_INFO):
        for h,comb in enumerate(infos):
            SESSION_CONFIGS[init_len + h*len(COMB_INFO)+i]=dict(
                    name='experiment_tr%d_%d'%(h+1,i+1), 
                    display_name="Expérience traitement %d, sess.type %d (%s)"%(h+1,i+1,comb),
                    app_sequence=['introquest','jeudede','finalquest','payinfo','redirecttopayment'],
                    treatment = h+1,
                    combination = i+1,
                    num_demo_participants=12 if h+1 == 3 else 8,
                    all_in_one = False
                )
if USE_ALL_IN_ONE > 0: SESSION_CONFIGS.append(dict(
                name='all_in_one_experiment', 
                display_name="Expérience avec tous les traitements",
                app_sequence=['introquest','jeudede','finalquest','payinfo','redirecttopayment'],
                num_demo_participants=2*(3*2*3 + 2*3*2)+20,
                all_in_one = True
            ))

# if you set a property in SESSION_CONFIG_DEFAULTS, it will be inherited by all configs
# in SESSION_CONFIGS, except those that explicitly override it.
# the session config can be accessed from methods in your apps as self.session.config,
# e.g. self.session.config['participation_fee']
bot_labels=[]
for i in range(240): bot_labels.append("bot%d"%(i+1))

bot_labels_leep = ["AMS", "ATH", "BER", "BRU", "BUD", "DUB", "HEL", "LIS", "LON", "MAD", "MOS", "OSL", "PRA", "RIG", "ROM", "SOF", "VAR", "VIE", "VIL", "ZUR", "LAB", "BOX1", "BOX2", "BOX3", "BOX4", "BOX5", "BOX6", "BOX7", "BOX8"]

for i in range(35):
    bot_labels += ["%s_%d"%(bl,i+1) for bl in bot_labels_leep]

SESSION_CONFIG_DEFAULTS = dict(
    real_world_currency_per_point=1, participation_fee=4.00, doc="", 
        treatment=0, combination=0, test_mode=False, bot_labels=bot_labels,
        all_in_one = False,
        date_limite = "18/07/2025", date_limite_time = "11:00", date_limite_time_end = "19:00", expe="epxe241_rib"
)

PARTICIPANT_FIELDS = ["treatment",'combination','combination_info','sess_prefix',"postal_code","day","finished","type","type_order"]

SESSION_FIELDS = ['n_p0_started','n_p0_finished']
SESSION_FIELDS_ADD= ['n_p1_started','n_p2_started','n_p1_finished','n_p2_finished','n_level1_finished','n_level2_finished', 'p1_list','p2_list','p1_levels','p2_levels','p2_types']
if USE_ALL_IN_ONE < 1:
    SESSION_FIELDS += SESSION_FIELDS_ADD
if USE_ALL_IN_ONE > 0:
    for i,infos in enumerate(COMB_INFO):
        for h,comb in enumerate(infos):
            treatment = h+1
            combination = i+1
            sess_prefix=f'tr{treatment}_comb{combination}_'
            SESSION_FIELDS += [sess_prefix+var for var in SESSION_FIELDS_ADD]

SESSION_FIELDS += ['day','current_type','n_group_errors']

# ISO-639 code
# for example: de, fr, ja, ko, zh-hans
LANGUAGE_CODE = 'fr'

# e.g. EUR, GBP, CNY, JPY
REAL_WORLD_CURRENCY_CODE = 'EUR'
USE_POINTS = False

ROOMS = [
    {
        'name': 'LEEP',
        'display_name': 'Laboratoire d’Economie Expérimentale de Paris',
        'participant_label_file': '_rooms/LEEP.txt',
    },
    dict(name='live_demo', display_name='Room for live demo (no participant labels)'),
]
ADMIN_USERNAME = 'experimentateur'
# for security, best to set admin password in an environment variable
ADMIN_PASSWORD = environ.get('OTREE_ADMIN_PASSWORD')

DEMO_PAGE_INTRO_HTML = """ """

SECRET_KEY = '5354502079362'
