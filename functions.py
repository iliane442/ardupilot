from pymavlink import mavutil
import subprocess
import time
import os
import socket

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
		if armed_state == bool(x):
			if x==1:
				print("Véhicule armé")
			else:
				print("Véhicule désarmé")
			return True
		time.sleep(0.5)

def set_mode(master, mode_name):
    # Liste complète des modes pour ArduPilot Plane
    modes_arduplane = ["MANUAL", "CIRCLE","STABILIZE","TRAINING","ACRO","FBWA","FBWB","CRUISE","AUTOTUNE","LOITER","RTL","AUTO","GUIDED","INITIALISING","QSTABILIZE","QHOVER","QLOITER","QLAND","QRTL","QAUTOTUNE","QACRO","TAKEOFF"]
    if mode_name not in modes_arduplane:
        print("\nmode not in list")
        return False
    else:
        vehicle.mode = VehicleMode(mode_name)
        print(f"mode changé pour {mode_name}")
        return True

def read_mode(master):
	msg = master.recv_match(type='HEARTBEAT', blocking=True) # Récupérer le dernier message HEARTBEAT
	mode_id = msg.custom_mode # Récupère l'id du mode actuel 
	modes=master.mode_mapping() # Dresse le dictionnaire des modes possibles 
	mode_name= [name for name, id in modes.items() if id == mode_id][0]# Cherche la correspondance entre l'id reçu et le mode dans le dictionnaire des modes
	print(f"Mode actuel, Id : {mode_name},{mode_id}") 
	return [mode_name,mode_id]

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
