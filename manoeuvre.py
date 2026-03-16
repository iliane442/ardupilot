from pymavlink import mavutil
import time
import functions as fct
from transforms3d.euler import euler2quat
from math import radians, sqrt, degrees, copysign

#=========Controle de vitesse==========

def get_vit_min(master,masse,roll_angle=0):
	'''
	La fonction gère une vitesse de décrochage simplifié
	30° d’inclinaison = vitesse de décrochage majorée de 10 %
	45° d’inclinaison = vitesse de décrochage majorée de 20 %
	60° d’inclinaison = vitesse de décrochage majorée de 40 %
	source: https://staysafe.aero/fr/base-to-final-all-you-need-is-speed/
	'''
	
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

#==========Décollage==========

def take_off(master,alt = None,thr_max = 100,pitch = None,initial_pitch = None):

#Variable globale
	global alt_cible
	
#Variables internes
	rep=""
	etat = fct.get_attitude(master)
	alt_ini = etat["altitude"]
	vit = etat["vitesse"]
	vit_min = fct.get_vit_min(master,5)

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
		etat = fct.get_attitude(master)
		vit = etat["vitesse"]
		time.sleep(0.1)
	co.set_mode(master,'GUIDED')
	time.sleep(0.5)
	stab = fct.stabilite_alt(master,alt_cible)
	erreur = stab["erreur_cum"]
	stabilite = stab["stabilite"]
	thrust = stab["thrust"]
	pitch_stab = stab["pitch"]
	dt = stab["dt"]

	while stabilite < 20:
		stab=fct.stabilite_alt(master,alt_cible,thrust,erreur,dt)
		if stab["stabilite"] == 0:
			stabilite = 0
		erreur = stab["erreur_cum"]
		stabilite += stab["stabilite"]
		thrust = stab["thrust"]
		pitch_stab = stab["pitch"]
		dt = stab["dt"]
		fct.send_attitude(master,0,pitch_stab,0,thrust)
		time.sleep(dt)

#==========Virage==========

def virage(master,angle=0,inclinaison=0):

#Variables Globale

	global alt_cible

#Variables
	
	etat = fct.get_attitude(master)
	yaw = etat["yaw"]
	yaw_target = (yaw+angle*copysign(1,inclinaison)+180)%360-180
	stab = fct.stabilite_alt(master,alt_cible)
	erreur = stab["erreur_cum"]
	stabilite = stab["stabilite"]
	thrust = stab["thrust"]
	pitch_stab = stab["pitch"]
	dt = stab["dt"]

#Virage
	co.set_mode(master,'GUIDED')
	while abs((yaw_target-yaw+180)%360-180)>5:
		etat = fct.get_attitude(master)
		yaw = etat["yaw"]
		stab=fct.stabilite_alt(master,alt_cible,thrust,erreur,dt)
		erreur = stab["erreur_cum"]
		thrust = stab["thrust"]
		print(thrust)
		pitch_stab = stab["pitch"]
		dt = stab["dt"]
		fct.send_attitude(master,inclinaison,pitch_stab,0,thrust)
		time.sleep(dt)

#==========Virage en S==========

def S_turn(master,nb_boucle=1,inclinaison=30):
	virage(master,90,inclinaison)
	for i in range (nb_boucle):
		virage(master,180,-1*inclinaison)
		virage(master,180,inclinaison)
	virage(master,90,-1*inclinaison)

#==========Changement d'altitude==========	

def chgt_alt(master,hauteur = 0):

#Variables Globale

	global alt_cible

#Vérifications

	if alt_cible+hauteur >= 120:
		return print ("commande ingnoré altitude max trop élevéeé")
	else:
		alt_cible=alt_cible+hauteur

#Variables 
#Stabilité
	stab = fct.stabilite_alt(master,alt_cible)
	erreur = stab["erreur_cum"]
	stabilite = stab["stabilite"]
	thrust = stab["thrust"]
	pitch_stab = stab["pitch"]
	dt = stab["dt"]
#Altitude
	etat = fct.get_attitude(master)
	alt = etat["altitude"]
	vit = etat["vitesse"]
	vit_prec=vit

	co.set_mode(master,'GUIDED')
	while abs(alt-alt_cible)>3:
		etat = fct.get_attitude(master)
		vit = etat["vitesse"]
		alt= etat["altitude"]
		if vit>vit_prec*0.98:
			fct.send_attitude(master,
roll = 0,
pitch = 30*copysign(1,hauteur),
yaw = 0,
thrust = 1
        )
			vit_prec=vit
			time.sleep(dt)
			print(vit)
		else:
			stab=fct.stabilite_alt(master,alt_cible,thrust,erreur,dt)
			erreur = stab["erreur_cum"]
			stabilite += stab["stabilite"]
			thrust = stab["thrust"]
			pitch_stab = stab["pitch"]
			fct.send_attitude(master,
0,
pitch_stab,
0,
thrust)
			time.sleep(dt)
			print("stabilisation")
			
	while stabilite < 20:
		stab=fct.stabilite_alt(master,alt_cible,thrust,erreur,dt)
		if stab["stabilite"] == 0:
			stabilite = 0
		erreur = stab["erreur_cum"]
		stabilite += stab["stabilite"]
		thrust = stab["thrust"]
		pitch_stab = stab["pitch"]
		fct.send_attitude(master,
0,
pitch_stab,
0,
thrust)
		time.sleep(dt)

