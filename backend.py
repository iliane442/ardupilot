from pymavlink import mavutil
import time
import commande as co
from transforms3d.euler import euler2quat
from math import radians

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