from pymavlink import mavutil
from time import sleep, time
from math import radians, degrees, copysign, sin, cos, atan2, sqrt
from transforms3d.euler import euler2quat
import threading
import functions as fct
from manoeuvre import *


class waypoint:
    def __init__(self, altitude : float, latitude : float, longitude : float, radius  : float = 5 , command : str = 'WAYPOINT'):
        self.lat = latitude            
        self.long = longitude
        self.alt = altitude             ## altitude en mètres
        self.radius = radius            ## rayon d'acceptance autour duquel l'avion considère qu'il est passé par le checkpoint
        self.command = command          ## le type de commande Mavlink que l'avion va recevoir 

    def __str__(self):
        return f" lat={self.lat}, long={self.long}, alt={self.alt}, radius={self.radius}, command={self.command}"


## Pré-verification des composants   

def battery_pre_verification(master : mavutil.mavlink_connection, log : any, blocking : bool):                ## log est une fonction 
    message = master.recv_match(type='SYS_STATUS', blocking=blocking, timeout=2 if blocking else 0 )    ## on recoit l'état de la batterie ( optionnellement en bloquant le programme pendant 2 secondes)
    if message is None:                     ## si on ne recoit rien, la pré-vérification n'est pas bonne 
        return False
    
    voltage = message.voltage_battery / 1000                ## tension de base en mv
    battery_remaining = message.battery_remaining           ## on check la batterie restante aussi, mais ce paramètre est moins précis sur un contrôleur

    if voltage < 10.5:                                      ## tension trop faible pour faire fonctionner l'avion pour le reste de la mission
        log("Voltage batterie trop faible")
        return False

    if battery_remaining is not None and battery_remaining < 20:
        log("Batterie trop faible")
        return False
    
    log("Batterie OK")
    return True 

def GPS_pre_verification(master : mavutil.mavlink_connection, log : any):                                  
    message = master.recv_match(type='GPS_RAW_INT', blocking=True, timeout = 2)         ## on recoit l'état du GPS ( optionnellement en bloquant le programme pendant 2 secondes)
    if message is None:
        log('Impossible de connaitre les coordonnées GPS')
        return False
    elif message.fix_type >= 3:                           ## si le GPS "fix-type" est inférieur à 3, le GPS ne se repère pas en 3 dimensions et renvoie donc une erreur 
        log("GPS OK")
        return True
    else:   
        log("GPS non prêt")
        return False
    
def sensors_pre_verification(master : mavutil.mavlink_connection, log : any, blocking : bool):
    ekf_critical_flags= {                                  ## indicateurs envoyé par l'autopilote pour signifier que l'EKF est dans un état critique 
        0: "EKF_ATTITUDE (Tilt roll/pitch)",                
        1: "EKF_VEL_VERT (Vitesse verticale)",
        2: "EKF_VEL_HORIZ (Vitesse horizontale)",
        3: "EKF_POS_VERT (Position verticale)",
        4: "EKF_POS_HORIZ (Position horizontale)",
        5: "EKF_MAG_HDG (Compas magnétique)",
 #      6: "EKF_GPS (GPS utilisé par EKF)"				incompatible avec le sitl
    }

    ekf_verification = True                             

    message = master.recv_match(type = 'EKF_STATUS_REPORT', blocking = blocking, timeout = 2 if blocking else 0)   ## on recoit l'état de chacun des flags ( optionnellement en bloquant le programme pendant 2 secondes)

    if message is None:                     ## Si la communication n'est pas établie, on arrête le programme 
        return False

    flags = message.flags                   ## on récupère les flags réels de l'avion

    for bit, name in ekf_critical_flags.items():                ## on vérifie chacun des flags un par un 
        if not (flags & (1 << bit)):
           log(f"EKF flag critique non OK: bit {name}")         ## On affiche le flag qui ne va pas 
           ekf_verification = False
    if ekf_verification:                                        ## Si tout est ok 
        log("EKF stable et tous les capteurs critiques OK")
        return True 
    else:
        return False

def pre_verification(master : mavutil.mavlink_connection, log : any):      
    '''
    on vérifie chacun des systèmes critiques un par un avant le lancement effectif de la mission 
    '''

    if not battery_pre_verification(master, log, blocking = True):          
        log('Impossible de lire la batterie')
        return False 

    if not GPS_pre_verification(master, log):
        return False
    
    if not sensors_pre_verification(master, log, blocking = True):
        log('Les capteurs sont indisponibles')
        return False 

    return True 	



	
#==========Check et envoi de la mission==========

def distance_meters(wp1 : waypoint , wp2 : waypoint):            ## pour calculer la distance entre deux waypoints ( sans prendre en compte l'altitude)
    R = 6371000  # rayon de la Terre en mètres
    phi1 = radians(wp1.lat)         
    phi2 = radians(wp2.lat)
    delta_phi = radians(wp2.lat - wp1.lat)
    delta_lambda = radians(wp2.long - wp1.long)
    
    a = sin(delta_phi/2)**2 + cos(phi1) * cos(phi2) * sin(delta_lambda/2)**2        ## formule de haversine https://fr.wikipedia.org/wiki/Formule_de_haversine
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    horizontal_distance = R * c
    return horizontal_distance

def check_radius(wp1 : waypoint , wp2 : waypoint):
    horizontal_distance = distance_meters(wp1,wp2)
    vertical_distance = wp2.alt - wp1.alt
    real_distance = sqrt(horizontal_distance**2 + vertical_distance**2)         ## théorème de pythagore 
    if real_distance < (wp2.radius * 1.5):                ## coefficient de sécurité de 1.5
        return False 
    else:
        return True
		

def check_mission(dic_mission : dict):                 					## permet de s'assurer que la mission respecte certaines règles minimales pour son bon fonctionnement   
    mission=[]
    for id in dic_mission:
        mission.append(dic_mission[id][0])                      ##  on récupère du dictionnaire seulement les waypoints
    if mission[-1].command != 'LAND':                 			## vérification qu'on atterrit bien à la fin de la mission
        return 'la dernière commande doit être un atterissage'

    for i in range(len(mission) - 1):                       ## on va regarder les waypoints deux à deux
        wp_current = mission[i]             
        wp_next = mission[i + 1]

        if not check_radius(wp_current, wp_next):              	 ## si deux waypoints sont trop proches 
            return 'la mission n est pas valide car deux checkpoints sont trop rapprochés'
        
        if wp_current.alt > 100 or wp_current.alt < 0:                                     ## en france, on ne peut pas voler à plus de 120 mètre de hauteur (inclue un coef de sécurité)
            return f"Waypoint {i} trop haut ou trop bas : {wp_current.alt} m"        
    return 'Mission valide' 

def add_home_waypoint(master : mavutil.mavlink_connection , mission : list):
    '''
    Ne pas insérer le home waypoint peut créer des problèmes pour l'autopilote qui l'attend systématiquement en tant que
    premier waypoint de la missoin
    '''

    for k in range(10):             ## on le demande 10 fois par sécurité 
        message = master.recv_match(type ='GLOBAL_POSITION_INT', blocking = True, timeout = 1)        
        if message:
            lat = message.lat / 1e7                                 ## pour les remettre en degrés 
            long = message.lon / 1e7                                ## pour les remettre en degrés
            alt = message.relative_alt / 1000                      
            home_waypoint = waypoint(alt,lat,long)                  ## création du waypoint
            mission.insert(0, home_waypoint)                        ## on le place dans la mission au départ 
            print(f'HOME = {lat}, {long}, {alt}')
            return mission                                          ## si il est recu une fois on stoppe 

    print(' Impossible de recuperer la position Home ')
    return False
	
def translate_wp_command_in_Mav_command(wp : waypoint):			## Les paramètres d'envoi ne sont pas les mêmes selon la commande du waypoint

    if wp.command == 'WAYPOINT':
        cmd = mavutil.mavlink.MAV_CMD_NAV_WAYPOINT                  ## on traduit notre commande en commande mavlink 
        param1 = 0                                                  ## temps à rester sur  le waypoint                         
        param2 = wp.radius                                          # acceptance radius (m)                 
        param3 = 0                                                  ## distance à respecter pour passer le waypoint
        param4 = 0                                                  ## cap que l'avion doit avoir pour passer sur le waypoint (fait automatiquement)
        return cmd, param1, param2, param3, param4
    elif wp.command == 'LAND':
        cmd = mavutil.mavlink.MAV_CMD_NAV_LAND
        param1 = 0                                                  ## pitch à l'atterrisage 
        param2 = 0                                                  # type d'atterrisage 0 par défaut   
        param3 = 0                                                  ## autres options sur l'atterrisage peu utilisée
        param4 = 0                                                  ## yaw final
        return cmd, param1, param2, param3, param4
    
    else:
        print('error on waypoints')
        return None


def send_mission(master : mavutil.mavlink_connection, dic_mission : dict[waypoint, str]):
    '''
    Chacun des paramètres des waypoints de la mission est envoyé avec un ordre précis, dependant du type de commande 
    ( WAYPOINT, LAND, LOITER...), et ce dans un certain format, d'ou la conversion de la latitude et la longitude
    '''
    mission=[]
    for id in dic_mission:
        mission.append(dic_mission[id][0])
    master.mav.mission_clear_all_send( master.target_system, master.target_component)           ## permet d'effacer une potentielle mission déjà existante
    mission = add_home_waypoint(master,mission)
    master.mav.mission_count_send( master.target_system, master.target_component,               ## on prépare l'envoie d'un certains nombres de waypoints 
    len(mission),           ## longueur de la mission
    mavutil.mavlink.MAV_MISSION_TYPE_MISSION )
    

    waypoints_sent = set()  # garder la trace des seq déjà envoyés

    while len(waypoints_sent) < len(mission):                                                   ## on fait ca si il y a eu une erreur et que le controlleur redemande le point 
        msg = master.recv_match( type=['MISSION_REQUEST','MISSION_REQUEST_INT'], blocking=True) ## on demande le waypoint
        if msg is None:
            print('Impossible de lire les donnees de la missions')
            return False 
        else: 
            seq = msg.seq                       ## numéro du waypoint dans la mission ( va être modifié à chaque itération)

            wp = mission[seq]                   ## on ajoute notre waypoint quand le controleur le demande
            cmd, p1, p2, p3, p4 = translate_wp_command_in_Mav_command(wp)               ## on envoie tout après transformation des commandes
            master.mav.mission_item_int_send(master.target_system, master.target_component,
            seq,                        
            mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
            cmd,            
            0, 1, p1, p2, p3, p4,
            int(wp.lat*1e7),
            int(wp.long*1e7),
            wp.alt,
            mavutil.mavlink.MAV_MISSION_TYPE_MISSION)

            waypoints_sent.add(seq)         ## on garde une trace si le transfert s'est bien fait, pour éviter qu'un waypoint soit sauté 

    ack = master.recv_match(type='MISSION_ACK', blocking=True, timeout = 10)        ## message de confirmation de la mission
    
    if ack is None:
        print("erreur dans l upload de la mission")                         ## on arrête le programme si la mission n'est pas bonne
        return False 
    else:
        print('la mission a bien été uploadé sur le controleur de vol')
        sleep(5)
        return True  
		
#==========Passage en mode manuel si failsafe==========

def pilot_override_detected(msg):                               ## l'argument est un message mavlink, de type RC_CHANNELS
    '''
    Cette fonction permet de savoir si le pilote active un des joystick de la télécommande, pour reprendre 
    le controle en cas de failsafe détecté. La deadband permet de ne pas recevoir de faux signals de lancement,
    en mettant un coefficient de sécurité sur le PMW de chacun 
    '''
    deadband = 50                                               
    if abs(msg.chan1_raw - 1500) > deadband:  # Roll
        return True
    if abs(msg.chan2_raw - 1500) > deadband:  # Pitch
        return True
    if abs(msg.chan4_raw - 1500) > deadband:  # Yaw
        return True
    return False

def wait_for_pilot_signals(master: mavutil.mavlink_connection, master_lock :any, override_counter):  
    override_threshold = 4              
    msg = master.recv_match(type='RC_CHANNELS', blocking=False)

    if not msg:                                 ## on ne fait rien car on a rien recu 
        return False
    if pilot_override_detected(msg):            
        override_counter += 1
    else:
        override_counter = 0
    if override_counter >= override_threshold:      
        fct.set_mode(master, 'MANUAL', master_lock)                   ## on passe en mode manuel et on laisse le pilote faire
        return True

    return False
	
#==========Thread sur les commandes Mavlink ==========

def read_mav_mess(master: mavutil.mavlink_connection , state_dictionary : dict, master_lock):        ## read mavlink messages
    '''
    Ce thread permet d'actualiser un à un un dictionnaire d'état qui va actualiser tous les messages que le
    programme recoit pendant la mission, en convertissant directement certains dans la forme qui nous intéresse
    '''
    while True:    
        with master_lock:                                                       ## on met un lock pour ne pas envoyer des messages au controleur en meme temps qu'on les recoit                                          
            message  =  master.recv_match(blocking = False)                      ## on regarde en permanence les messages envoyés et on les met dans un dictionnaire d'état
        if message is None:                 
            sleep(0.01)                                 ## on attend pour ne pas saturer le controleur de demande
        else:
            if message.get_type() == 'SYS_STATUS':
                state_dictionary["battery"] = message
            if message.get_type() == 'GPS_RAW_INT':
                state_dictionary["GPS"] = message
            if message.get_type() == 'EKF_STATUS_REPORT':
                state_dictionary["EKF_sensors"] = message
            if message.get_type() == 'MISSION_CURRENT':
                state_dictionary["current_waypoint"] = message.seq
            if message.get_type() == 'ATTITUDE':
                state_dictionary["yaw"] = degrees(message.yaw)
                state_dictionary["roll"] = degrees(message.roll)
                state_dictionary["pitch"] = degrees(message.pitch)
            if message.get_type() == 'GLOBAL_POSITION_INT':
                state_dictionary["altitude"] = message.relative_alt / 1000
            if message.get_type() == 'VFR_HUD':
                state_dictionary["vitesse"] = message.airspeed
            sleep(0.01)                         ## on attend pour ne pas saturer le controleur de demande
    return 

#==========Thread sur les failsafes ==========

def battery_verification(state_dictionary : dict, log : any):
    '''
    Les fonctions sont globalement les mêmes que pour les pré-vérifications mais fonctionnent avec le dictionnaire d'état
    pour pouvoir être utilisés durant la mission sans demander directement les informations au système
    '''
    message = state_dictionary["battery"]                  ## on récupère l'état de la batterie
    if message is None:
        return False
    
    voltage = message.voltage_battery / 1000                ## tension de base en mv
    battery_remaining = message.battery_remaining

    if voltage < 10.5:
        log("Voltage batterie trop faible")
        return False

    if battery_remaining is not None and battery_remaining < 20:
        log("Batterie trop faible")
        return False

    return True

def sensors_verification(state_dictionary : dict, log : any):
    '''
    Les fonctions sont globalement les mêmes que pour les pré-vérifications mais fonctionnent avec le dictionnaire d'état
    pour pouvoir être utilisés durant la mission sans demander directement les informations au système
    '''
    ekf_critical_flags= {
        0: "EKF_ATTITUDE (Tilt roll/pitch)",
        1: "EKF_VEL_VERT (Vitesse verticale)",
        2: "EKF_VEL_HORIZ (Vitesse horizontale)",
        3: "EKF_POS_VERT (Position verticale)",
        4: "EKF_POS_HORIZ (Position horizontale)",
        5: "EKF_MAG_HDG (Compas magnétique)",
 #      6: "EKF_GPS (GPS utilisé par EKF)"
    }

    ekf_verification = True

    message = state_dictionary["EKF_sensors"]

    if message is None:
        return False
    
    flags = message.flags 

    for bit, name in ekf_critical_flags.items():
        if not (flags & (1 << bit)):
           log(f"EKF flag critique non OK: bit {name}")
           ekf_verification = False
    if ekf_verification:
        return True 
    else:
        return False

def GPS_verification(state_dictionary : dict, log : any):
    '''
    Les fonctions sont globalement les mêmes que pour les pré-vérifications mais fonctionnent avec le dictionnaire d'état
    pour pouvoir être utilisés durant la mission sans demander directement les informations au système
    '''

    msg = state_dictionary["GPS"]

    if msg is None:
        log("GPS non reçu")
        return False 
    elif msg.fix_type >= 3 and msg.satellites_visible >= 6:             ## on ajoute une vérification sur les satellites visibles
        return True 
    else:
        log(f"GPS faible (fix={msg.fix_type}, sats={msg.satellites_visible})")  
        return False  
  

def ask_for_failsafes(state_dictionary : dict, GPS_failsafe_counter : int, sensors_failsafe_counter : int, battery_failsafe_counter : int, failsafe_threshold : int, log : any):

    '''
    Chacun des systèmes peut renvoyer une fois un mauvais signal pour diverses raisons : on itère 10 fois un compteur
    (ici, on attend 10 secondes) pour déclarer un failsafe
    '''

    if not GPS_verification(state_dictionary, log):
        GPS_failsafe_counter += 1
        log(f"GPS faible depuis {GPS_failsafe_counter} cycles")
    else:
        GPS_failsafe_counter = 0  # reset compteur si GPS OK

    if GPS_failsafe_counter >=  failsafe_threshold:
        log("Failsafe GPS")
        return False, GPS_failsafe_counter, sensors_failsafe_counter, battery_failsafe_counter 
    
    if not battery_verification(state_dictionary, log):
        battery_failsafe_counter += 1 
    else:
        battery_failsafe_counter = 0 
    if battery_failsafe_counter >= failsafe_threshold:
        log('Failsafe batterie')
        return False, GPS_failsafe_counter, sensors_failsafe_counter, battery_failsafe_counter 
    
    if not sensors_verification(state_dictionary, log):
        sensors_failsafe_counter += 1
    else: 
        sensors_failsafe_counter = 0 
    if sensors_failsafe_counter >= failsafe_threshold:
        log('Failsafe sur les capteurs')
        return False, GPS_failsafe_counter, sensors_failsafe_counter, battery_failsafe_counter
        
    return True, GPS_failsafe_counter, sensors_failsafe_counter, battery_failsafe_counter 

def threading_failsafes(state_dictionary : dict, stop_event, log : any):
    GPS_failsafe_counter = 0
    sensors_failsafe_counter = 0
    battery_failsafe_counter = 0  
    failsafe_threshold= 10                                       ## nombre de cycles consécutifs avant déclenchement d'un failsafe                              

    while not stop_event.is_set():                              ## tant qu'un failsafe n'a pas été déclaré, on n'arrète pas le programme 
        ok, GPS_counter, sensors_counter, battery_counter = ask_for_failsafes(state_dictionary, GPS_failsafe_counter, sensors_failsafe_counter, battery_failsafe_counter, failsafe_threshold, log)
        
        GPS_failsafe_counter = GPS_counter
        sensors_failsafe_counter = sensors_counter
        battery_failsafe_counter = battery_counter

        if not ok:                                                      ## si ask_for_falisafe renvoie faux, on arrête le programme
            log("Failsafe critique détecté. Arrêt du programme.")
            stop_event.set()
            return
        sleep(1)                                                        ## on attend une seconde 

#==========Thread sur les manoeuvres ==========

def maneuver_selection(maneuver : list, master : mavutil.mavlink_connection, state_dictionary : dict, master_lock :any):
    '''
    On sélectionne la manoeuvre que l'on veut éffectuer avec ses différents paramètres
    '''
    if "virage" in maneuver:
        angle = int(maneuver.split("(")[1].split(")")[0])
        virage(master,state_dictionary, master_lock, angle)
    elif "changement d'altitude" in maneuver:
        hauteur = int(maneuver.split("(")[1].split(")")[0])
        chgt_alt(master, state_dictionary, master_lock, hauteur)
    elif "S-turn" in maneuver:
        nb_boucle = int(maneuver.split("(")[1].split(")")[0])
        S_turn(master,state_dictionary, master_lock, nb_boucle)
    elif maneuver == "variation rapide de poussée":
        accel(master, state_dictionary, master_lock)
    elif "accel" in maneuver:
        vitesse = float(maneuver.split("(")[1].split(")")[0])
        chgt_vit(master,state_dictionary, master_lock, vitesse)
    return 
	
def create_clean_dico_maneuver(dico_maneuver : dict):          ## {1 : [liste_manoeuvre] , 2 : [liste_manoeuvre]]}
    clean_dict = {}
    for wp, data in dico_maneuver.items():
        maneuvers_dict = data[2]                                              ## on recupère de l'interface
        clean_dict[wp] = [m[0] for m in maneuvers_dict.values()]              ## on recupere la liste des manoeuvres 
    return clean_dict


def thread_maneuvers(state_dictionary : dict, clean_dico_maneuvers : dict, stop_event, master : mavutil.mavlink_connection, master_lock : any, dic_mission):
    global alt_cible
    last_waypoint = None                        ## on va mémoriser le dernier waypoint pour ne pas refaire les manoeuvres deux fois 

    while not stop_event.is_set():              ## tant qu'on a pas de problème de failsafe, le programme continue

        num_waypoint = state_dictionary.get("current_waypoint")     ## on va chercher la valeur du waypoint
        if num_waypoint != last_waypoint:                          ## on regarde ou se placer dans la mission
            if num_waypoint != 0 :
                alt_cible = dic_mission[num_waypoint][0].alt
            if num_waypoint in clean_dico_maneuvers:
                maneuvers = clean_dico_maneuvers[num_waypoint]
                for maneuver in maneuvers:                              ## on effectue les manoeuvres à la suite 
                    maneuver_selection(maneuver, master, state_dictionary, master_lock)
                clean_dico_maneuvers[num_waypoint] = []             ## sécurité supplémentaire optionnelle
            last_waypoint = num_waypoint

        sleep(0.1)              ## 0.1 secondes entre chaque appel
		
#==========Main non complet ==========

def main(master : mavutil.mavlink_connection, dic_mission : dict, log : any):   
	
    log("Démarrage du script de mission...")

    state_dictionary = {                                    ## Pour recevoir les communications
    "battery" : None,
    "GPS" : None, 
    "EKF_sensors" : None,
    "current_waypoint" : None,
    "yaw" : None,
    "roll" : None,
    "pitch": None,
    "altitude": None,
    "vitesse": None
    }

    override_counter = 0                                                ## paramètre pour permettre l'intervention pilote en cas de défaillance
    if pre_verification(master,log) == False:                               ## on vérifie que l'avion peut décoller
        log("Un des systèmes critiques de l'avion empêche le décollage")
        return 
    
    master_lock = threading.Lock()                                          ## pour empecher que deux threads se fassent simultanement 
    stop_event = threading.Event()                                          ## pour arrêter les threads en cas de probleme

    clean_dico_maneuvers = create_clean_dico_maneuver(dic_mission)          ## on nettoie le dictionnaire de l'interface pour garder les informations nécessaires

    log("Démarrage du thread mavlink...")
    thread_mavlink = threading.Thread(target=read_mav_mess, args=(master, state_dictionary, master_lock), daemon=True)
    thread_mavlink.start()
    sleep(3)

    log("debut du décollage")
    alt_takeoff = dic_mission[1][0].alt                         ## on regarde a quelle altitude on veut décoller 
    take_off(master, log, state_dictionary, master_lock, alt_takeoff,thr_max = 100, pitch = None,initial_pitch = None)   ## décollage automatique

    log("takeoff bien effectue")
	
    try:     
        thread_failsafe = threading.Thread(target = threading_failsafes, args =(state_dictionary, stop_event, log), daemon = True)
        thread_failsafe.start()

        log("Démarrage du thread failsafe...")

        thread_on_maneuvers = threading.Thread(target = thread_maneuvers, args =(state_dictionary, clean_dico_maneuvers, stop_event, master, master_lock,dic_mission), daemon = True)
        thread_on_maneuvers.start()

        log("Démarrage du thread manoeuvre...")

        while True:     
            if stop_event.is_set():                         ## en cas de problème
                fct.set_mode(master, 'LOITER', master_lock)             ## l'avion tourne en rond en attente d'instructions
                log("Failsafe actif, en attente d'intervention pilote")
                
                start_time = time()                             ## threads fermé, on démarre un timer
                while not wait_for_pilot_signals(master, master_lock, override_counter):   ## tant que le pilote n'a pas répondu
                    if time() - start_time > 60:       ## si on a attendu plus de 60 secondes
                        fct.set_mode(master,'LAND', master_lock)                 ## atterrissage d'urgence 
                        log('pas de pilote détécté, atterrissage forcé')
                        return
                    sleep(0.25)                             ## on attend 0.25 secondes
            sleep(0.5)  
    except KeyboardInterrupt:
        log("\nDéconnexion.")
        return 
    











