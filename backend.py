from pymavlink import mavutil
import time
from math import radians



class waypoint:
    def __init__(self, latitude, longitude, altitude, radius = 5 , command = 'WAYPOINT'):
        self.lat = latitude 
        self.long = longitude
        self.alt = altitude
        self.radius = radius            ## rayon autour duquel l'avion considère qu'il est passé par le checkpoint
        self.command = command 

    def __str__(self):
        return f": lat={self.lat}, long={self.long}, alt={self.alt}, radius={self.radius}, command={self.command}"

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

#==========Décollage==========

def take_off(master,alt=None,thr_max=None,pitch=None,initial_pitch=None):
	params_takeoff = {
    "TKOFF_ALT": alt,        # altitude cible 80 m
    "TKOFF_LVL_ALT": alt,    # Distance de maintien obligatoire en position horizontale
    "TKOFF_LVL_PITCH": pitch,  # pitch de montée
    "TKOFF_GND_PITCH": initial_pitch,   # pitch au sol
    "TKOFF_THR_MINACC": 0,  # accélération minimale
    "TKOFF_THR_MAX": thr_max,   # throttle max
}
	rep=""
	if alt> 120:
		return print(f"erreur {alt} ne peut pas etre spérieur à 120m")
	if thr_max< 50:
		while rep not in ["y","Y","n","N"]:
			rep=input("attention la poussée max est inférieure au minimum recommandé. Voulez vous continuer ? :(Y/N)")
		if rep=="n" or rep=="N":
			return print("procédure de décollage interrompue")
		elif rep=="y" or rep=="Y":
			print("Validation")
	for name, value in params_takeoff.items():
		if value is not None:
			co.set_param(master,name, value)
	co.armed(master,1)
	while altitude<alt:
		msg = master.recv_match(type='GLOBAL_POSITION_INT', blocking=True)
		altitude = msg.relative_alt / 1000
		co.set_mode(master,'TAKEOFF')
	co.set_mode(master,'GUIDED')
	

#==========Controle d'attitude==========

def send_altitude(master,roll, pitch, yaw, thrust):

	roll_rad  = radians(roll)
	pitch_rad = radians(pitch)
	yaw_rad   = radians(yaw)

	q = euler2quat(roll_rad, pitch_rad, yaw_rad)
	master.mav.set_attitude_target_send(
        0,
        master.target_system,
        master.target_component,
        0b00000111,
        q,
        0,0,0,
        thrust
    )

def virage(master,angle=-30):
	co.set_mode(master,'GUIDED')
	if angle<0:
		print("Virage gauche")
	if angle>0:
		print("Virage droite")
	if angle == 0 :
		print("stabilise")
	for i in range(30):
		send_attitude(master,
            roll=angle,
            pitch=5,
            yaw=0,
            thrust=0.6
        )
	time.sleep(0.1)

def set_mode(master, mode_name):
    if mode_name not in master.mode_mapping():   # pour checker si le mode existe
        print(f"Erreur : Le mode '{mode_name}' n'est pas reconnu par l'avion.")
        return False

    mode_id = master.mode_mapping()[mode_name] # on recupere l'identifiant parmis tous les modes

    master.mav.set_mode_send(
        master.target_system,
        mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
        mode_id)