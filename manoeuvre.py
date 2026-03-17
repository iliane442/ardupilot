from pymavlink import mavutil
import time
import functions as fct
import correcteur as cor
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

def take_off(master, log, alt = 50,thr_max = 100,pitch = None,initial_pitch = None):

#Variable globale
	global alt_cible
	

#Variables
#Utilisateur
	rep=""
#Attitude
	etat = fct.get_attitude(master)
	alt_ini = etat["altitude"]
	vit = etat["vitesse"]
	vit_min = get_vit_min(master,5)

#Affectation Globale
	alt_cible = alt_ini+alt

#Stabilité
	stab = cor.alt(master,alt_cible)
	erreur_cum = stab["erreur_cum"]
	alt_prec = stab["alt_prec"]
	stabilite = stab["stabilite"]
	thrust = stab["thrust"]
	pitch_prec = stab["pitch"]
	dt = stab["dt"]
	

	

	params_takeoff = {
    "TKOFF_ALT": alt_cible,        # altitude cible 
    "TKOFF_LVL_ALT": alt_ini+5,    # Distance de maintien obligatoire en position horizontale
    "TKOFF_LVL_PITCH": pitch,  # pitch de montée
    "TKOFF_GND_PITCH": initial_pitch,   # pitch au sol
    "TKOFF_THR_MAX": thr_max,   # throttle max
}



#Mesures de sécurité

	if alt >= 120:
		return log(f"erreur {alt} ne peut pas etre supérieur à 120m")
	if thr_max != None and thr_max < 50:
		while rep not in ["y","Y","n","N"]:
			rep = input("attention la poussée max est inférieure au minimum recommandé. Voulez vous continuer ? :(Y/N)")
		if rep == "n" or rep == "N":
			return log("procédure de décollage interrompue")
		elif rep == "y" or rep == "Y":
			print("Validation")

#Envoi des paramètres de décollage à mission planner

	for name, value in params_takeoff.items():
		if value is not None:
			fct.set_param(master,name, value)

#Décollage

	fct.set_mode(master,'TAKEOFF')

	while vit < vit_min:
		etat = fct.get_attitude(master)
		vit = etat["vitesse"]
		time.sleep(0.1)

	fct.set_mode(master,'GUIDED')
	time.sleep(0.5)

	while stabilite < 20:
		stab=cor.alt(master, alt_target=alt_cible, erreur_cum=erreur_cum, alt_prec=alt_prec, pitch_prec=pitch_prec, dt=dt, thrust=thrust)
		if stab["stabilite"] == 0:
			stabilite = 0
		erreur_cum = stab["erreur_cum"]
		alt_prec = stab["alt_prec"]
		stabilite += stab["stabilite"]
		thrust = stab["thrust"]
		pitch_prec = stab["pitch"]
		fct.send_attitude(master,0,pitch_prec,0,thrust)
		time.sleep(dt)

#==========Virage==========

def virage(master,angle=0,inclinaison=30):

#Variables Globale

	global alt_cible

#Variables

#Attitude

	etat = fct.get_attitude(master)
	yaw = etat["yaw"]
	yaw_target = (yaw+angle*copysign(1,inclinaison)+180)%360-180
	

#Stabilité

	stab = cor.alt(master,alt_cible)
	erreur_cum = stab["erreur_cum"]
	alt_prec = stab["alt_prec"]
	pitch_prec= stab ["pitch"]
	stabilite = stab["stabilite"]
	thrust = stab["thrust"]
	dt = stab["dt"]



#Virage
	fct.set_mode(master,'GUIDED')
	while abs((yaw_target-yaw+180)%360-180) > 5:

		etat = fct.get_attitude(master)
		yaw = etat["yaw"]

		stab=cor.alt(master, alt_target=alt_cible, thrust=thrust, erreur_cum=erreur_cum, alt_prec=alt_prec, pitch_prec=pitch_prec, dt=dt)
		erreur_cum = stab["erreur_cum"]
		alt_prec = stab["alt_prec"]
		pitch_prec= stab ["pitch"]
		thrust = stab["thrust"]
	
		fct.send_attitude(master,inclinaison,pitch_prec,0,thrust)
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

#Vérifications et Affectation Globale
	if alt_cible+hauteur >= 120:
		return print ("commande ingnoré altitude max trop élevéeé")
	else:
		alt_cible=alt_cible+hauteur
#Variables 

#Altitude
	etat = fct.get_attitude(master)
	alt = etat["altitude"]
	vit = etat["vitesse"]
	vit_prec=vit

#Stabilité
	stab = cor.alt(master,alt_cible)
	alt_prec= stab["alt_prec"]
	pitch_prec= stab ["pitch"]
	erreur_cum= stab["erreur_cum"]
	stabilite = stab["stabilite"]
	thrust = stab["thrust"]
	dt = stab["dt"]


	fct.set_mode(master,'GUIDED')

# Changement d'altitude
	while abs(alt-alt_cible)>3:

		etat = fct.get_attitude(master)
		vit = etat["vitesse"]
		alt= etat["altitude"]

		if vit > vit_prec*0.98: # Sécurité pour empêcher la diminution de vitesse trop rapide associée au décrochage
			fct.send_attitude(master,roll = 0,pitch_prec = 20*copysign(1,hauteur),yaw = 0,thrust = 1)

			vit_prec=vit
			time.sleep(dt)

# Stabilisation en cas de risque de décrochage
		else: 
			stab=cor.alt(master, alt_target=alt_cible, erreur_cum=erreur_cum, alt_prec=alt_prec, pitch_prec=pitch_prec, dt=dt, thrust=thrust)

			erreur_cum = stab["erreur_cum"]
			alt_prec = stab["alt_prec"]
			pitch_prec= stab ["pitch"]
			stabilite += stab["stabilite"]
			thrust = stab["thrust"]

			fct.send_attitude(master,0,pitch_prec,0,thrust)
			time.sleep(dt)
			print("stabilisation")
#Stabilisation en fin de montée 		
	while stabilite < 20:
		stab=cor.alt(master, alt_target=alt_cible, erreur_cum=erreur_cum, alt_prec=alt_prec, pitch_prec=pitch_prec, dt=dt, thrust=thrust)
		if stab["stabilite"] == 0:
			stabilite = 0
		erreur_cum = stab["erreur_cum"]
		alt_prec = stab["alt_prec"]
		pith_prec= stab ["pitch"]
		stabilite += stab["stabilite"]
		thrust = stab["thrust"]
		fct.send_attitude(master,0,pitch_prec,0,thrust)
		time.sleep(dt)

#==========Accélération poussée min-poussée max==========

def accel(master,min_thrust=0.3,max_thrust=1):#vérifier la poussé min en décrochage
#Variables Globales

	global alt_cible

#Variables

#Compteur

	c=0

#Attitude

	etat = fct.get_attitude(master)
	alt = etat["altitude"]
	vit = etat["vitesse"]
	vit_prec = 0.5*vit
	acc= (vit-vit_prec)
	acc_prec = 0 
	yaw = etat["yaw"]

#Stabilité

	alt_stab = cor.alt(master, alt_target=alt_cible, corr_thrust=False)
	erreur_cum = alt_stab["erreur_cum"]
	alt_prec = alt_stab["alt_prec"]
	pitch__prec= alt_stab["pitch"]
	dt=alt_stab["dt"]

#Initialisation de l'avion en mode poussée minimale pendant 3 secondes

	for i in range (30): 
		fct.send_attitude(master,0, pitch_prec, 0, min_thrust)
		time.sleep(0.1)

#Accélération

	while c<20: # accélération min-max jusqu'à atteindre un niveau ou l'accélération ne change plus (tolérance incluse) pendant assez longtemps
		
		acc_prec= acc
		etat = fct.get_attitude(master)
		alt = etat["altitude"]
		vit = etat["vitesse"]
		acc = (vit-vit_prec)/dt
		vit_prec = vit

		cap_stab = cor.cap(master, cap_target=yaw)
		alt_stab = cor.alt(master, alt_target=alt_cible, erreur_cum=erreur_cum, alt_prec=alt_prec, pitch_prec=pitch_prec, corr_thrust=False)

		erreur_cum = alt_stab["erreur_cum"]
		alt_prec = alt_stab["alt_prec"]
		pitch_prec = alt_stab["pitch"]
		roll= cap_stab["roll"]

		fct.send_attitude(master,roll, pitch_prec, 0, max_thrust)
		if acc<acc_prec+5:
	 		c+=1
		else:
			c= max(0,c-1)
		time.sleep(dt)
