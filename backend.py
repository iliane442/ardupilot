from pymavlink import mavutil
from time import sleep, time
from math import radians, degrees, copysign, sin, cos, atan2, sqrt
from transforms3d.euler import euler2quat
from thread import threading
import functions as fct
from manoeuvre import *


class waypoint:
    def __init__(self, altitude, latitude, longitude, radius = 5 , command = 'WAYPOINT'):
        self.lat = latitude 
        self.long = longitude
        self.alt = altitude
        self.radius = radius            ## rayon autour duquel l'avion considère qu'il est passé par le checkpoint
        self.command = command 

    def __str__(self):
        return f" lat={self.lat}, long={self.long}, alt={self.alt}, radius={self.radius}, command={self.command}"


## Pré-verification des composants   

def battery_pre_verification(master, blocking):
    message = master.recv_match(type='SYS_STATUS', blocking=blocking, timeout=2 if blocking else 0 )
    if message is None:
        return False
    
    voltage = message.voltage_battery / 1000                ## tension de base en mv
    battery_remaining = message.battery_remaining

    if voltage < 10.5:
        print("Voltage batterie trop faible")
        return False

    if battery_remaining is not None and battery_remaining < 20:
        print("Batterie trop faible")
        return False

    return True 

def GPS_pre_verification(master):
    message = master.recv_match(type='GPS_RAW_INT', blocking=True, timeout = 2)
    if message is None:
        print('Impossible de connaitre les coordonnées GPS')
        return False
    elif message.fix_type >= 3:
        print("GPS OK")
        return True
    else:   
        print("GPS non prêt")
        return False
    
def sensors_pre_verification(master, blocking):
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

    message = master.recv_match(type = 'EKF_STATUS_REPORT', blocking = blocking, timeout = 2 if blocking else 0)

    if message is None:
        return False
    
    flags = message.flags 

    for bit, name in ekf_critical_flags.items():
        if not (flags & (1 << bit)):
           print(f"EKF flag critique non OK: bit {name}")
           ekf_verification = False
    if ekf_verification:
        print("EKF stable et tous les capteurs critiques OK")
        return True 
    else:
        return False

def pre_verification(master):
    
    if not battery_pre_verification(master, blocking = True):
        print('Impossible de lire la batterie')
        return False 

    if not GPS_pre_verification(master):
        return False
    
    if not sensors_pre_verification(master, blocking = True):
        print(' Les capteurs sont indisponibles')
        return False 

    return True 	

def ask_for_failsafes(master, GPS_failsafe_counter, sensors_failsafe_counter, battery_failsafe_counter, battery_failsafe_threshold, failsafe_threshold):
    
    if not GPS_verification(master):
        GPS_failsafe_counter += 1
        print(f"GPS faible depuis {GPS_failsafe_counter} cycles")
    else:
        GPS_failsafe_counter = 0  # reset compteur si GPS OK

    if GPS_failsafe_counter >=  failsafe_threshold:
        print("Failsafe GPS")
        return False 
    
    if not battery_verification(master, blocking = False):
        battery_failsafe_counter += 1 
    else:
        battery_failsafe_counter = 0 
    if battery_failsafe_counter > battery_failsafe_threshold:
        print('Failsafe batterie')
        return False 
    
    if not sensors_verification(master, blocking = False):
        sensors_failsafe_counter += 1
    else: 
        sensors_failsafe_counter = 0 
    if sensors_failsafe_counter > failsafe_threshold:
        print('Failsafe sur les capteurs')
        return False
        
    return True 

	
#==========Check et envoi de la mission==========

def distance_meters(wp1,wp2):            ## pour calculer la distance entre deux waypoints ( sans prendre en compte l'altitude)
    R = 6371000  # rayon de la Terre en mètres
    phi1 = radians(wp1.lat)
    phi2 = radians(wp2.lat)
    delta_phi = radians(wp2.lat - wp1.lat)
    delta_lambda = radians(wp2.long - wp1.long)
    
    a = sin(delta_phi/2)**2 + cos(phi1) * cos(phi2) * sin(delta_lambda/2)**2        ## formule de haversine 
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    horizontal_distance = R * c
    return horizontal_distance

def check_radius(wp1,wp2):
    horizontal_distance = distance_meters(wp1,wp2)
    vertical_distance = wp2.alt - wp1.alt
    real_distance = sqrt(horizontal_distance**2 + vertical_distance**2)
    if real_distance < (wp2.radius * 1.5):                ## coefficient de sécurité 
        return False 
    else:
        return True
		

def check_mission(mission):                 					## permet de s'assurer que la mission respecte certaines règles minimales pour son bon fonctionnement   
    
    if mission[-1].command != 'LAND':                 			## vérification qu'on atterrit bien 
        return 'la dernière commande doit être un atterissage'

    for i in range(len(mission) - 1):
        wp_current = mission[i]
        wp_next = mission[i + 1]

        if not check_radius(wp_current, wp_next):              	 ## si deux waypoints sont trop proches 
            return 'la mission n est pas valide car deux checkpoints sont trop rapprochés'
        
        if wp_current.alt > 100 or wp_current.alt < 0:                                     ## en france, on ne peut pas voler à plus de 120 mètre de hauteur (inclue un coef de sécurité)
            return f"Waypoint {i} trop haut ou trop bas : {wp_current.alt} m"        
    return 'Mission valide' 

def add_home_waypoint(master, mission):

    for k in range(10):
        message = master.recv_match(type ='GLOBAL_POSITION_INT', blocking = True, timeout = 1)        
        if message:
            lat = message.lat / 1e7
            long = message.lon / 1e7
            alt = message.relative_alt / 1000                       ## attention à ce que le GPS soit opérationnel avant de faire ca 
            home_waypoint = waypoint(lat,long, alt)
            mission.insert(0, home_waypoint)
            print(f'HOME = {lat}, {long}, {alt}')
            return True 

    print(' Impossible de recuperer la position Home ')
    return False
	
def translate_wp_command_in_Mav_command(wp):			## Les paramètres d'envoi ne sont pas les mêmes selon la commande du waypoint

    if wp.command == 'WAYPOINT':
        cmd = mavutil.mavlink.MAV_CMD_NAV_WAYPOINT
        param1 = 0          
        param2 = wp.radius  # acceptance radius (m)
        param3 = 0          
        param4 = 0          
        return cmd, param1, param2, param3, param4
    
    elif wp.command == 'TAKEOFF':
        cmd = mavutil.mavlink.MAV_CMD_NAV_TAKEOFF
        param1 = 15         # pitch de montée 
        param2 = 0
        param3 = 0
        param4 = 0
        return cmd, param1, param2, param3, param4

    elif wp.command == 'LAND':
        cmd = mavutil.mavlink.MAV_CMD_NAV_LAND
        param1 = 0          
        param2 = 0          
        param3 = 0
        param4 = 0
        return cmd, param1, param2, param3, param4
    
    else:
        print('error on waypoints')
        return None


def send_mission(master, mission):
    master.mav.mission_clear_all_send( master.target_system, master.target_component)           ## permet d'effacer une potentielle mission déjà existante

    master.mav.mission_count_send( master.target_system, master.target_component,               ## on prépare l'envoie d'un certains nombres de waypoints 
    len(mission),
    mavutil.mavlink.MAV_MISSION_TYPE_MISSION )


    waypoints_sent = set()  # garder la trace des seq déjà envoyés

    while len(waypoints_sent) < len(mission):                                                   ## on fait ca si il y a eu une erreur et que le controlleur redemande le point 
        msg = master.recv_match( type=['MISSION_REQUEST','MISSION_REQUEST_INT'], blocking=True)
        if msg is None:
            print('Impossible de lire les donnees de la missions')
            return False 
        else: 
            seq = msg.seq

            wp = mission[seq]
            cmd, p1, p2, p3, p4 = translate_wp_command_in_Mav_command(wp)
            master.mav.mission_item_int_send(master.target_system, master.target_component,
            seq,
            mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
            cmd,
            0, 1, p1, p2, p3, p4,
            int(wp.lat*1e7),
            int(wp.long*1e7),
            wp.alt,
            mavutil.mavlink.MAV_MISSION_TYPE_MISSION)

            waypoints_sent.add(seq)

    ack = master.recv_match(type='MISSION_ACK', blocking=True, timeout = 10)
    
    if ack is None:
        print("erreur dans l upload de la mission")
        return False 
    else:
        print('la mission a bien été uploadé sur le controleur de vol')
        sleep(5)
        return True  
		
#==========Passage en mode manuel si failsafe==========

def pilot_override_detected(msg):
    deadband = 50
    if abs(msg.chan1_raw - 1500) > deadband:  # Roll
        return True
    if abs(msg.chan2_raw - 1500) > deadband:  # Pitch
        return True
    if abs(msg.chan4_raw - 1500) > deadband:  # Yaw
        return True
    return False

def wait_for_pilot_signals(master):
    global override_counter
    override_threshold = 4 
    msg = master.recv_match(type='RC_CHANNELS', blocking=False)

    if not msg:
        return False
    if pilot_override_detected(msg):
        override_counter += 1
    else:
        override_counter = 0
    if override_counter >= override_threshold:
        fct.set_mode(master, 'MANUAL')
        return True

    return False
	
#==========Thread sur les commandes Mavlink ==========

def read_mav_mess(master, state_dictionary):        ## read mavlink messages
    while True:                                                              
        message  =  master.rcv_match(blocking = False)                      ## on regarde en permanence les messages envoyés et on les met dans un dictionnaire d'état
        if message is None:                 
            sleep(0.01) 
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
        sleep(0.01)
    return 

#==========Thread sur les failsafes ==========

def battery_verification(state_dictionary):
    message = state_dictionary["battery"]
    if message is None:
        return False
    
    voltage = message.voltage_battery / 1000                ## tension de base en mv
    battery_remaining = message.battery_remaining

    if voltage < 10.5:
        print("Voltage batterie trop faible")
        return False

    if battery_remaining is not None and battery_remaining < 20:
        print("Batterie trop faible")
        return False

    return True 

def sensors_verification(state_dictionary):
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

    message = state_dictionary("EKF_sensors")

    if message is None:
        return False
    
    flags = message.flags 

    for bit, name in ekf_critical_flags.items():
        if not (flags & (1 << bit)):
           print(f"EKF flag critique non OK: bit {name}")
           ekf_verification = False
    if ekf_verification:
        print("EKF stable et tous les capteurs critiques OK")
        return True 
    else:
        return False

def GPS_verification(state_dictionary):
    msg = state_dictionary["GPS"]

    if msg is None:
        print("GPS non reçu")
        return False 
    elif msg.fix_type >= 3 and msg.satellites_visible >= 6:
        return True 
    else:
        print(f"GPS faible (fix={msg.fix_type}, sats={msg.satellites_visible})")  
        return False  

def ask_for_failsafes(state_dictionary, GPS_failsafe_counter, sensors_failsafe_counter, battery_failsafe_counter, failsafe_threshold):
    
    if not GPS_verification(state_dictionary):
        GPS_failsafe_counter += 1
        print(f"GPS faible depuis {GPS_failsafe_counter} cycles")
    else:
        GPS_failsafe_counter = 0  # reset compteur si GPS OK

    if GPS_failsafe_counter >=  failsafe_threshold:
        print("Failsafe GPS")
        return False, GPS_failsafe_counter, sensors_failsafe_counter, battery_failsafe_counter 
    
    if not battery_verification(state_dictionary):
        battery_failsafe_counter += 1 
    else:
        battery_failsafe_counter = 0 
    if battery_failsafe_counter > failsafe_threshold:
        print('Failsafe batterie')
        return False, GPS_failsafe_counter, sensors_failsafe_counter, battery_failsafe_counter 
    
    if not sensors_verification(state_dictionary):
        sensors_failsafe_counter += 1
    else: 
        sensors_failsafe_counter = 0 
    if sensors_failsafe_counter > failsafe_threshold:
        print('Failsafe sur les capteurs')
        return False, GPS_failsafe_counter, sensors_failsafe_counter, battery_failsafe_counter
        
    return True, GPS_failsafe_counter, sensors_failsafe_counter, battery_failsafe_counter 

def threading_failsafes(state_dictionary, stop_event):
    GPS_failsafe_counter = 0
    sensors_failsafe_counter = 0
    battery_failsafe_counter = 0  
    failsafe_threshold= 10                                       ## nombre de cycles consécutifs avant déclenchement d'un failsafe                              
    override_counter = 0 

    while not stop_event.is_set():                              ## tant qu'un failsafe n'a pas été déclaré, on n'arrète pas le programme 
        ok, GPS_counter, sensors_counter, battery_counter = ask_for_failsafes(state_dictionary, GPS_failsafe_counter, sensors_failsafe_counter, battery_failsafe_counter, failsafe_threshold)
        
        GPS_failsafe_counter = GPS_counter
        sensors_failsafe_counter = sensors_counter
        battery_failsafe_counter = battery_counter

        if not ok:
            print("Failsafe critique détecté. Arrêt du programme.")
            stop_event.set()
            break
        sleep(1)

    return 

#==========Thread sur les manoeuvres ==========

def maneuver_selection(maneuver, master):
    if maneuver == "virage à (x) °":
        virage(master,angle=0,inclinaison=0)
    if maneuver == "changement d'altitude(x)":
        chgt_alt(master,hauteur = 0)
    if maneuver == "S-turn(x)":
        S_turn(master,nb_boucle=1,inclinaison=30)
    return 
	
def create_clean_dico_maneuver(dico_maneuver):          ## {1 : [liste_manoeuvre] , 2 : [liste_manoeuvre]]}
    clean_dict = {}
    for wp, data in dico_maneuver.items():
        maneuvers_dict = data[2]        
        clean_dict[wp] = [m[0] for m in maneuvers_dict.values()]               ## on recupere la liste des manoeuvres 
    return clean_dict


def thread_maneuvers(state_dictionary, clean_dico_maneuvers, stop_event, master):
    last_waypoint = None                        ## on va mémoriser le dernier waypoint pour ne pas refaire les manoeuvres deux fois 

    while not stop_event.is_set():

        num_waypoint = state_dictionary["current_waypoint"]

        if num_waypoint != last_waypoint:
            if num_waypoint in clean_dico_maneuvers:
                maneuvers = clean_dico_maneuvers[num_waypoint]
                for maneuver in maneuvers:
                    maneuver_selection(maneuver, master)
                clean_dico_maneuvers[num_waypoint] = []
            last_waypoint = num_waypoint

        sleep(0.1)
		
#==========Main non complet ==========

def main(master, mission, dico_maneuver):        

    state_dictionary = {                                    ## attention a le mettre en global 
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

    clean_dico_maneuvers = create_clean_dico_maneuver(dico_maneuver)       
    take_off(master,alt = 50,thr_max = 100,pitch = None,initial_pitch = None)

    stop_event = threading.Event()      
    

    try:     
        thread_mavlink = threading.Thread(target=read_mav_mess, args=(master, state_dictionary), daemon=True)
        thread_mavlink = threading.start()
        sleep(3)

        thread_failsafe = threading.Thread(target = threading_failsafes, arg =(state_dictionary, stop_event), daemon = True)
        thread_failsafe = threading.start()

        thread_on_maneuvers = threading.Thread(target = thread_maneuvers, arg =(state_dictionary, clean_dico_maneuvers, stop_event, master), daemon = True)
        thread_on_maneuvers = threading.start()

        while True: 
            if stop_event.is_set(): 
                set_mode(master, 'LOITER' )
                print("Failsafe actif, en attente d'intervention pilote")
                
                start_time = time.time()
                while not wait_for_pilot_signals(master):
                    if time.time() - start_time > 60:
                        set_mode(master,'LAND')                 ## atterrissage d'urgence si le pilote ne prend pas la situation en main 
                        print('pas de pilote détécté, atterrissage forcé')
                        return
                    sleep(0.25)
            sleep(0.1)
    except KeyboardInterrupt:
        print("\nDéconnexion.")
        return 
    












