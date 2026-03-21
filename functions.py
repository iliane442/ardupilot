from pymavlink import mavutil
import subprocess
import time
import os
from math import radians, sqrt, degrees, copysign, sin, cos, atan2, asin
from transforms3d.euler import euler2quat

#==========Armement du vehicule==========

def armed(master : mavutil.mavlink_connection,x : int):
# ARM
	master.mav.command_long_send(
master.target_system,
master.target_component,
mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
0,
x,0,0,0,0,0,0)
	for _ in range(10):
		msg = master.recv_match(type='HEARTBEAT', blocking=True) # remplace la fonction master.motors_armed_wait() ou disarmed pas présente dans toutes les versions
		armed_state = (msg.base_mode & 0b10000000) > 0
		if armed_state == bool(x):
			if x==1:
				print("Véhicule armé")
			else:
				print("Véhicule désarmé")
			return True
		time.sleep(0.5)

#==========Controle du Mode==========

def set_mode(master : mavutil.mavlink_connection, mode_name : str, master_lock : any):
    if mode_name not in master.mode_mapping():   # Vérifie si le mode existe
        print(f"Erreur : Le mode '{mode_name}' n'est pas reconnu par l'avion.")
        return False

    mode_id = master.mode_mapping()[mode_name]  # Récupère l'identifiant du mode

    with master_lock: 
        master.mav.set_mode_send(
            master.target_system,
            mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
            mode_id)
    return True

#==========Lecture Mode==========

def read_mode(master : mavutil.mavlink_connection):

	msg = master.recv_match(type='HEARTBEAT', blocking=True) # Récupérer le dernier message HEARTBEAT
	mode_id = msg.custom_mode # Récupère l'id du mode actuel 
	modes=master.mode_mapping() # Dresse le dictionnaire des modes possibles 
	mode_name= [name for name, id in modes.items() if id == mode_id][0]# Cherche la correspondance entre l'id reçu et le mode dans le dictionnaire des modes
	print(f"Mode actuel, Id : {mode_name},{mode_id}") 
	return [mode_name,mode_id]

#==========Controle d'attitude==========

def send_attitude(master : mavutil.mavlink_connection, master_lock : any, roll : float, pitch : float, yaw : float, thrust : float):

	roll_rad = radians(roll)
	pitch_rad = radians(pitch)
	yaw_rad = radians(yaw)

	q = euler2quat(roll_rad, pitch_rad, yaw_rad)
	with master_lock:
		master.mav.set_attitude_target_send(
			0,
			master.target_system,
			master.target_component,
			0b00000111,
			q,
			0,0,0,
			thrust
		)


#==========Modification de paramètres==========

def set_param(master : mavutil.mavlink_connection,name : str, value : float, master_lock : any):
	print(f"Envoi de {name} = {value}")
	with master_lock: 
		master.mav.param_set_send(
			master.target_system,
			master.target_component,
			name.encode('utf-8'),
			float(value),
			mavutil.mavlink.MAV_PARAM_TYPE_REAL32
		)

def nettoyage():
   print("nettoyage des scripts")
   os.system('pkill -9 -f "ardu|mav|sim_vehicle"')
   return True


def connection_vehicle():
	print("Connexion MAVLink")
	master = mavutil.mavlink_connection('udp:127.0.0.1:14551')
	print("Attente du heartbeat...")
	master.wait_heartbeat()
	print("Heartbeat reçu")
	return master


def lancement_sitl():
	## lancement du SITL
	ardupilot_dir = "ardupilot"  # dossier ArduPilot
	# Lancer SITL en arrière-plan
	print("🚀 Lancement de SITL...")
	sitl_proc = subprocess.Popen(["python3", "./Tools/autotest/sim_vehicle.py", "-v", "ArduPlane", "--out", "udp:127.0.0.1:14550", "--out", "udp:127.0.0.1:14551"], cwd=ardupilot_dir)
	return True


# Calcule un point à une certaine distance (en mètres) derrière un point donné.
#  azimut_deg : direction vers laquelle l'avion pointe (0=Nord, 90=Est, 180=Sud, 270=Ouest)


def calculer_point_arriere(lat, lon, distance_m=100, azimut_deg=0):
    
    
    
    R = 6378137.0 # Rayon de la Terre en mètres

    # On veut aller à l'opposé de l'azimut (derrière l'avion)
    angle_arriere = (azimut_deg + 180) % 360
    brng = radians(angle_arriere)

    lat1 = radians(lat)
    lon1 = radians(lon)

    # Calcul de la nouvelle latitude
    lat2 = asin(sin(lat1) * cos(distance_m/R) +
                     cos(lat1) * sin(distance_m/R) * cos(brng))

    # Calcul de la nouvelle longitude
    lon2 = lon1 + atan2(sin(brng) * sin(distance_m/R) * cos(lat1),
                             cos(distance_m/R) - sin(lat1) * sin(lat2))

    return lat2, lon2
