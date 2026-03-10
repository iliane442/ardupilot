from dronekit import VehicleMode, connect
from pymavlink import mavutil
import subprocess
import time
import os
import socket

def set_mode(vehicle, mode_name):
    # Liste complète des modes pour ArduPilot Plane
    modes_arduplane = ["MANUAL", "CIRCLE","STABILIZE","TRAINING","ACRO","FBWA","FBWB","CRUISE","AUTOTUNE","LOITER","RTL","AUTO","GUIDED","INITIALISING","QSTABILIZE","QHOVER","QLOITER","QLAND","QRTL","QAUTOTUNE","QACRO","TAKEOFF"]
    if mode_name not in modes_arduplane:
        print("\nmode not in list")
        return False
    else:
        vehicle.mode = VehicleMode(mode_name)
        print(f"mode changé pour {mode_name}")
        return True


def nettoyage():
   print("nettoyage des scripts")
   os.system('pkill -9 -f "ardu|mav|sim_vehicle"')
   return True

def close(v):
	v.close()
	print("fermeture terminée")
	return True

def connection_vehicle():
	print("Connexion MAVLink")
	master = mavutil.mavlink_connection('udp:127.0.0.1:14551')
	master.wait_heartbeat()
	print("Heartbeat reçu")

def lancement_sitl():
	## lancement du SITL
	ardupilot_dir = "ardupilot"  # dossier ArduPilot
	vehicle_type = "ArduPlane"
	frame = "plane"
	sitl_cmd = [
	"./Tools/autotest/sim_vehicle.py",
	"-v",vehicle_type,
	"-f",frame,
	"--console",
	#"--no-mavproxy",
        "--map"
    	]
	# Lancer SITL en arrière-plan
	print("🚀 Lancement de SITL...")
	sitl_proc = subprocess.Popen(sitl_cmd, cwd=ardupilot_dir)

	# Petite pause pour laisser SITL démarrer
	#print("pause pour démarrer sitl")
	time.sleep(15)  # 10 secondes, ajuste si nécessaire
	print("-----------------------------------------------------lancement fini-----------------------------------------------------")
	add_output()  # Ajouter les sorties MAVLink après le lancement de SITL
	return True

def add_output():
	output_add1=('127.0.0.1', 14550)  #ajout d'une sortie pour la connection missionplaner et mavlink
	output_add2=('127.0.0.1', 14551)  #ajout d'une sortie pour connection a missionplaner
	udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	print(f"Sortie MAVLink activée sur {output_add1[0]}:{output_add1[1]}")
	print(f"Sortie MAVLink activée sur {output_add2[0]}:{output_add2[1]}")
	return True

def atterissage():
	
	return True

def vol_pallier_stabilise():
	return True

def acceleration_deceleration():
	return True

def virage_x():	
	return True

def changement_altitude():
	return True

def decollage():
	
	print("décollage en cours")
	return True

