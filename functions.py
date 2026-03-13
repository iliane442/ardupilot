from pymavlink import mavutil
import subprocess
import time
import os
import socket

#==========Armement du vehicule==========

def armed(master,x):
	# ARM
	master.mav.command_long_send(
	master.target_system,
	master.target_component,
	mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
	0,x,0,0,0,0,0,0)
	for _ in range(10):
		msg = master.recv_match(type='HEARTBEAT', blocking=True)
		armed_state = (msg.base_mode & 0b10000000) > 0


#==========Controle du Mode==========

def set_mode(master, mode_name):
    if mode_name not in master.mode_mapping():   # pour checker si le mode existe
        print(f"Erreur : Le mode '{mode_name}' n'est pas reconnu par l'avion.")
        return False

    mode_id = master.mode_mapping()[mode_name] # on recupere l'identifiant parmis tous les modes

    master.mav.set_mode_send(
        master.target_system,
        mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,

        mode_id)

#==========Controle d'attitude==========

def send_attitude(master,roll, pitch, yaw, thrust):

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

#==========Lecture Attitude==========

def get_attitude(master):
	msg_ang = master.recv_match(type='ATTITUDE', blocking=True)
	yaw = degrees(msg_ang.yaw)
	roll=degrees(msg_ang.roll)
	pitch=degrees(msg_ang.pitch)

	msg_pos = master.recv_match(type='GLOBAL_POSITION_INT', blocking=True)
	altitude = msg_pos.relative_alt / 1000

	msg_vit = master.recv_match(type='VFR_HUD', blocking=True)
	vit=msg_vit.groundspeed	

	return {
        "yaw": yaw,
        "roll": roll,
        "pitch": pitch,
        "altitude": altitude,
        "vitesse": vit
    }

#==========Lecture Mode==========

def read_mode(master):

	msg = master.recv_match(type='HEARTBEAT', blocking=True) # Récupérer le dernier message HEARTBEAT
	mode_id = msg.custom_mode # Récupère l'id du mode actuel 
	modes=master.mode_mapping() # Dresse le dictionnaire des modes possibles 
	mode_name= [name for name, id in modes.items() if id == mode_id][0]# Cherche la correspondance entre l'id reçu et le mode dans le dictionnaire des modes
	print(f"Mode actuel, Id : {mode_name},{mode_id}") 
	return [mode_name,mode_id]

#==========Modification de paramètres==========

def set_param(master,name, value):
	print(f"Envoi de {name} = {value}")
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

def close(v):
	v.close()
	print("fermeture terminée")
	return True

def connection_vehicle():
	python_cmd = 'from functions import connection_vehicle2; connection_vehicle2(); input("Terminé...")'
	# On l'intègre dans la commande de terminal
	subprocess.Popen(['lxterm', '-e', 'python3', '-c', python_cmd])

def connection_vehicle2():
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
	# Petite pause pour laisser SITL démarrer
	#print("pause pour démarrer sitl")
	time.sleep(10)  # 10 secondes, ajuste si nécessaire
	print("-----------------------------------------------------lancement fini-----------------------------------------------------")
	return True
