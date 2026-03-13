from pymavlink import mavutil
import time
import commande as co
from transforms3d.euler import euler2quat
from math import radians, sqrt, degrees, copysign

#==========Décollage==========

def take_off(master,alt = None,thr_max = 100,pitch = None,initial_pitch = None):

#Variable globale
	global alt_cible
	
#Variables internes
	rep=""
	etat = get_attitude(master)
	alt_ini = etat["altitude"]
	vit = etat["vitesse"]
	vit_min = get_vit_min(master,5)

	alt_cible = alt_ini+alt

	params_takeoff = {
    "TKOFF_ALT": alt_cible,        # altitude cible 
    "TKOFF_LVL_ALT": alt_ini+5,    # Distance de maintien obligatoire en position horizontale
    "TKOFF_LVL_PITCH": pitch,  # pitch de montée
    "TKOFF_GND_PITCH": initial_pitch,   # pitch au sol
    "TKOFF_THR_MAX": thr_max,   # throttle max
}

#Mesure de sécurité

	if alt >= 120:
		return print(f"erreur {alt} ne peut pas etre supérieur à 120m")
	if thr_max != None and thr_max < 50:
		while rep not in ["y","Y","n","N"]:
			rep = input("attention la poussée max est inférieure au minimum recommandé. Voulez vous continuer ? :(Y/N)")
		if rep == "n" or rep == "N":
			return print("procédure de décollage interrompue")
		elif rep == "y" or rep == "Y":
			print("Validation")

#Envoi des paramètres de décollage à mission planner

	for name, value in params_takeoff.items():
		if value is not None:
			co.set_param(master,name, value)

#Décollage

	co.set_mode(master,'TAKEOFF')
	while vit < vit_min:
		etat = get_attitude(master)
		vit = etat["vitesse"]
		time.sleep(0.1)
	co.set_mode(master,'GUIDED')
	time.sleep(0.5)
	stab = stabilite_alt(master,alt_cible)
	erreur = stab["erreur_cum"]
	stabilite = stab["stabilite"]
	thrust = stab["thrust"]
	pitch_stab = stab["pitch"]
	dt = stab["dt"]

	while stabilite < 20:
		stab=stabilite_alt(master,alt_cible,thrust,erreur,dt)
		if stab["stabilite"] == 0:
			stabilite = 0
		erreur = stab["erreur_cum"]
		stabilite += stab["stabilite"]
		thrust = stab["thrust"]
		pitch_stab = stab["pitch"]
		dt = stab["dt"]
		send_attitude(master,0,pitch_stab,0,thrust)
		time.sleep(dt)

#==========Virage==========

def virage(master,angle=0,inclinaison=0):

#Variables Globale

	global alt_cible

#Variables
	
	etat = get_attitude(master)
	yaw = etat["yaw"]
	yaw_target = (yaw+angle*copysign(1,inclinaison)+180)%360-180
	stab = stabilite_alt(master,alt_cible)
	erreur = stab["erreur_cum"]
	stabilite = stab["stabilite"]
	thrust = stab["thrust"]
	pitch_stab = stab["pitch"]
	dt = stab["dt"]

#Virage
	co.set_mode(master,'GUIDED')
	while abs((yaw_target-yaw+180)%360-180)>5:
		etat = get_attitude(master)
		yaw = etat["yaw"]
		stab=stabilite_alt(master,alt_cible,thrust,erreur,dt)
		erreur = stab["erreur_cum"]
		thrust = stab["thrust"]
		print(thrust)
		pitch_stab = stab["pitch"]
		dt = stab["dt"]
		send_attitude(master,inclinaison,pitch_stab,0,thrust)
		time.sleep(dt)

#==========Virage en S==========

def S_turn(master,nb_boucle=1,inclinaison=30):
	virage(master,90,inclinaison)
	for i in range (nb_boucle):
		virage(master,180,-1*inclinaison)
		virage(master,180,inclinaison)
	virage(master,90,-1*inclinaison)


