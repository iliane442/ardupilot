from pymavlink import mavutil
import time
import math
#from transforms3d.euler import euler2quat
from math import radians, sqrt, degrees, copysign
import functions as fct



class waypoint:
    def __init__(self, latitude, longitude, altitude, radius = 5 , command = 'WAYPOINT'):
        self.lat = latitude 
        self.long = longitude
        self.alt = altitude
        self.radius = radius            ## rayon autour duquel l'avion considère qu'il est passé par le checkpoint
        self.command = command 

    def __str__(self):
        return f" lat={self.lat}, long={self.long}, alt={self.alt}, radius={self.radius}, command={self.command}"


## Verification des composants   

def battery_verification(master):

    message = master.recv_match(type='SYS_STATUS', blocking=True, timeout=2)
    if message is None:
        print('Impossible de lire la batterie')
        return False
    else:
        battery_remaining = message.battery_remaining
        print("Batterie restante:", battery_remaining, "%")

    if battery_remaining is None:
        print("Impossible de connaître l'état de la batterie")
        return False
    if battery_remaining < 20:                   ## moins de 20% de batterie 
        print("Batterie trop faible pour décoller")
        return False
    
    return True 


def GPS_verification(master):

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
    
def sensors_verification(master):
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

    message = master.recv_match(type = 'EKF_STATUS_REPORT', blocking = True, timeout = 2)

    if message is None:
        print('Impossible de décoller, capteurs indisponibles')
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
    
    if not battery_verification(master):
        return False 

    if not GPS_verification(master):
        return False
    
    if not sensors_verification(master):
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
    phi1 = math.radians(wp1.lat)
    phi2 = math.radians(wp2.lat)
    delta_phi = math.radians(wp2.lat - wp1.lat)
    delta_lambda = math.radians(wp2.long - wp1.long)
    
    a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2        ## formule de haversine 
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    horizontal_distance = R * c
    return horizontal_distance

def check_radius(wp1,wp2):
    horizontal_distance = distance_meters(wp1,wp2)
    vertical_distance = wp2.alt - wp1.alt
    real_distance = math.sqrt(horizontal_distance**2 + vertical_distance**2)
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

    for _ in range(10):
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


def send_mission(master, mission):																## Il faut être en mode automatique et véhicule armé. Pour la récupérer sur Mission Planner : " read wp" dans l'onglet Plans
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
        time.sleep(5)
        return True 
		
#==========Passage en mode manuel si failsafe==========

def pilot_override_detected(msg):
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
        set_mode(master, 'MANUAL')
        return True

    return False
	
#==========Décollage==========

def take_off(master,alt=None,thr_max=100,pitch=None,initial_pitch=None):

#Variables internes

	rep=""
	pitch_dec=0
	etat = fct.get_attitude(master)
	altitude_ini = etat["altitude"]
	vit = etat["vitesse"]
	yaw = etat["yaw"]
	altitude= altitude_ini-1
	alt_decol=altitude_ini+alt
	vit_min=fct.get_vit_min(master,5)
	

	params_takeoff = {
    "TKOFF_ALT": alt_decol,        # altitude cible 
    "TKOFF_LVL_ALT": altitude_ini,    # Distance de maintien obligatoire en position horizontale
    "TKOFF_LVL_PITCH": pitch,  # pitch de montée
    "TKOFF_GND_PITCH": initial_pitch,   # pitch au sol
    "TKOFF_THR_MINACC": 0,  # accélération minimale
    "TKOFF_THR_MAX": thr_max,   # throttle max
}

#Mesure de sécurité

	if alt> 120:
		return print(f"erreur {alt} ne peut pas etre spérieur à 120m")
	if thr_max!=None and thr_max< 50:
		while rep not in ["y","Y","n","N"]:
			rep=input("attention la poussée max est inférieure au minimum recommandé. Voulez vous continuer ? :(Y/N)")
		if rep=="n" or rep=="N":
			return print("procédure de décollage interrompue")
		elif rep=="y" or rep=="Y":
			print("Validation")

#Envoi des paramètres de décollage à mission planner

	for name, value in params_takeoff.items():
		if value is not None:
			fct.set_param(master,name, value)

#Décollage

	fct.set_mode(master,'TAKEOFF')
	while altitude<altitude_ini+5 and vit<vit_min:
		etat = fct.get_attitude(master)
		altitude = etat["altitude"]
		vit = etat["vitesse"]
		time.sleep(0.1)
	fct.set_mode(master,'GUIDED')
	while altitude < alt_decol:
		altitude = fct.get_attitude(master)["altitude"]
		pitch_dec+=1
		fct.send_attitude(master,1,15,0,0.7)
		time.sleep(0.1)

#==========Virage==========

def virage(master,angle=90,inclinaison=30):
	msg_ang = master.recv_match(type='ATTITUDE', blocking=True)
	yaw = degrees(msg_ang.yaw)
	yaw_target = (yaw+angle*copysign(1,inclinaison)+180)%360-180
	fct.set_mode(master,'GUIDED')
	while abs(yaw_target-yaw)>3:
		yaw = fct.get_attitude(master)["yaw"]
		fct.send_attitude(master,
            roll=inclinaison,
            pitch=0,
            yaw=0,
            thrust=0.5
        )
		time.sleep(0.05)

#==========Virage en S==========

def S_turn(master,nb_boucle,inclinaison):
	virage(master,90,inclinaison)
	for i in range (nb_boucle):
		virage(master,180,-1*inclinaison)
		virage(master,180,inclinaison)
	virage(master,90,-1*inclinaison)

#=========Controle de vitesse==========

def get_vit_min(master,masse,roll_angle=0):
#30° d’inclinaison = vitesse de décrochage majorée de 10 %
#45° d’inclinaison = vitesse de décrochage majorée de 20 %
#60° d’inclinaison = vitesse de décrochage majorée de 40 %
#source: https://staysafe.aero/fr/base-to-final-all-you-need-is-speed/
	
	if abs(roll_angle)<30:
		coef_maj=1.1
	elif abs(roll_angle)<45:
		coef_maj=1.2
	elif abs(roll_angle)<60:
		coef_maj=1.4
	else:
		print ("décrochage fortement probable arrêt de la manoeuvre")
		for i in range (30):
			virage(master,0,0)
			time.sleep(0.1) 
	P=masse*9.81 #N
	rho=1 #kg/m^3
	Cp_max=1.2 #Coefficient de portance maximum 
	S_alaire=0.43 #m^2
	vit_min = sqrt(2*P/(rho*S_alaire*Cp_max))*coef_maj
	return vit_min


## MAIN TEMPORAIRE

def main():
    GPS_failsafe_counter = 0
    sensors_failsafe_counter = 0
    battery_failsafe_counter = 0  
    failsafe_threshold= 10                                       ## nombre de cycles consécutifs avant déclenchement d'un failsafe
    battery_failsafe_threshold = 25 
    override_counter = 0 


    mission = [ 
    waypoint(-35.3632623, 149.1652376, 40, command='TAKEOFF'),
    waypoint(-35.3640, 149.1660, 60),                     # ~120 m nord-est
    waypoint(-35.3650, 149.1665, 70),                     # ~200 m plus loin
    waypoint(-35.3645, 149.1650, 60),                     # retour vers piste
    waypoint(-35.3635, 149.1652, 0, command='LAND')
    ]                                                           ## exemple de mission 

    if check_mission(mission) == False:                                     
        return

    print("Connexion à l'avion sur le port 14552...")
    master = mavutil.mavlink_connection('udpin:127.0.0.1:14552')            # Connexion au SITL

    master.wait_heartbeat()                                                 # Attente du Heartbeat 
    print(f"Cible trouvée ! Système {master.target_system}, Composant {master.target_component}")

    if not pre_verification(master):                                        ## on verifie tout avant de continuer 
        print("Pré-vol échoué : vérifications non OK")
        return  
    else:
        print("Pré-vol OK : tout est prêt pour décoller") 
    
    vehicule_armed(master, 1)

    add_home_waypoint(master, mission)

    set_mode(master, "AUTO")            
    if send_mission(master, mission) == False:                              ## détail : la mission s'envoie sur l'autopilote, mais pour que mission planner la récupere, il faut appuyer sur Read wp
        return 

    move_on_landing_strip(master)

    try:     
        while True: 
            bool_vehicule_operational = ask_for_failsafes(master, GPS_failsafe_counter, sensors_failsafe_counter, battery_failsafe_counter, battery_failsafe_threshold, failsafe_threshold)
            time.sleep(1)
            if bool_vehicule_operational: 
                print('test')   ## PARTIE DU CODE POUR METTRE LES MANOEUVRES
            else: 
                set_mode(master, 'LOITER' )
                print("Failsafe actif, en attente d'intervention pilote")
                
                start_time = time.time()
                while not wait_for_pilot_signals(master):
                    if time.time() - start_time > 60:
                        set_mode(master,'LAND')                 ## atterrissage d'urgence si le pilote ne prend pas la situation en main 
                        print('pas de pilote détécté, atterrissage forcé')
                        return
                    time.sleep(0.25)
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nDéconnexion.")
        return 






