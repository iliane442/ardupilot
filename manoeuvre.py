from pymavlink import mavutil
import time
import functions as fct
import correcteur as cor
from transforms3d.euler import euler2quat
from math import radians, sqrt, degrees, copysign

#=========Controle de vitesse==========

def get_vit_min(master : mavutil.mavlink_connection, state_dictionary : dict, master_lock :any, masse : float, roll_angle : float = 0):
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
			virage(master,state_dictionary, master_lock, 0,0)
			time.sleep(0.1) 
	P=masse*9.81 #N
	rho=1 #kg/m^3
	Cp_max=1.2 #Coefficient de portance maximum 
	S_alaire=0.43 #m^2
	vit_min = sqrt(2*P/(rho*S_alaire*Cp_max))*coef_maj
	return vit_min

#==========Décollage==========

def take_off(master : mavutil.mavlink_connection, log : any, state_dictionary : dict, master_lock :any, alt : float = 50, thr_max : float = 100, pitch : float = None, initial_pitch : float = None):

#Variable globale
	global alt_cible
	
#Variables internes

	rep=""
	alt_ini = state_dictionary["altitude"]
	vit = state_dictionary["vitesse"]
	vit_min = get_vit_min(master, state_dictionary, master_lock, 5)

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
		return log(f"erreur {alt} ne peut pas etre supérieur à 120m")
	if thr_max != None and thr_max < 50:
		while rep not in ["y","Y","n","N"]:
			rep = input("attention la poussée max est inférieure au minimum recommandé. Voulez vous continuer ? :(Y/N)")
		if rep == "n" or rep == "N":
			return log("procédure de décollage interrompue")
		elif rep == "y" or rep == "Y":
			log("Validation")

#Envoi des paramètres de décollage à mission planner

	for name, value in params_takeoff.items():
		if value is not None:
			fct.set_param(master,name, value, master_lock)

#Décollage

	fct.set_mode(master,'TAKEOFF', master_lock)
	while vit < vit_min:	
		vit = state_dictionary["vitesse"]
		time.sleep(0.1)
	fct.set_mode(master,'GUIDED', master_lock)
	time.sleep(0.5)
	stab = cor.alt(state_dictionary,alt_target = alt_cible)
	erreur = stab["erreur_cum"]
	stabilite = stab["stabilite"]
	thrust = stab["thrust"]
	pitch_stab = stab["pitch"]
	dt = stab["dt"]

	while stabilite < 20:
		stab=cor.alt(state_dictionary,alt_target=alt_cible,thrust=thrust,erreur_cum=erreur,dt=dt)
		if stab["stabilite"] == 0:
			stabilite = 0
		erreur = stab["erreur_cum"]
		stabilite += stab["stabilite"]
		thrust = stab["thrust"]
		pitch_stab = stab["pitch"]
		dt = stab["dt"]
		fct.send_attitude(master, master_lock, 0,pitch_stab,0,thrust)
		time.sleep(dt)
	fct.set_mode(master,'AUTO', master_lock)

#==========Virage==========

def virage(master : mavutil.mavlink_connection, state_dictionary : dict, master_lock : any, angle : float = 0, inclinaison : float = 30):

#Variables Globale

	global alt_cible

#Variables

#Attitude

	yaw = state_dictionary["yaw"]
	yaw_target = (yaw+angle*copysign(1,inclinaison)+180)%360-180
	

#Stabilité

	stab = cor.alt(state_dictionary,alt_cible)
	erreur_cum = stab["erreur_cum"]
	alt_prec = stab["alt_prec"]
	pitch_prec= stab ["pitch"]
	stabilite = stab["stabilite"]
	thrust = stab["thrust"]
	dt = stab["dt"]



#Virage
	fct.set_mode(master,'GUIDED', master_lock)
	while abs((yaw_target-yaw+180)%360-180) > 5:

		yaw = state_dictionary["yaw"]

		stab=cor.alt(state_dictionary, alt_target=alt_cible, thrust=thrust, erreur_cum=erreur_cum, alt_prec=alt_prec, pitch_prec=pitch_prec, dt=dt)
		erreur_cum = stab["erreur_cum"]
		alt_prec = stab["alt_prec"]
		pitch_prec= stab ["pitch"]
		thrust = stab["thrust"]
	
		fct.send_attitude(master, master_lock, inclinaison,pitch_prec,0,thrust)
		time.sleep(dt)
	fct.set_mode(master,'AUTO', master_lock)

#==========Virage en S==========

def S_turn(master : mavutil.mavlink_connection, state_dictionary : dict, master_lock : any, nb_boucle : int = 1, inclinaison : float = 30):

	virage(master,state_dictionary, master_lock, 90,inclinaison)
	for i in range (nb_boucle):
		virage(master,state_dictionary, master_lock, 180,-1*inclinaison)
		virage(master,state_dictionary,master_lock, 180,inclinaison)
	virage(master,state_dictionary, master_lock, 90,-1*inclinaison)

#==========Changement d'altitude==========	

def chgt_alt(master : mavutil.mavlink_connection, state_dictionary : dict, master_lock :any, hauteur : float = 0):

#Variables Globale
	global alt_cible
	var_alt = hauteur - alt_cible
	
#Vérifications et Affectation Globale
	if hauteur >= 120:
		return print ("commande ignoré : altitude max trop élevée")
	else :
		alt_cible = hauteur
#Variables 

#Altitude

	alt = state_dictionary["altitude"]
	vit = state_dictionary["vitesse"]
	vit_prec=vit

#Stabilité
	stab = cor.alt(state_dictionary,alt_target=alt_cible)
	alt_prec= stab["alt_prec"]
	pitch_prec= stab ["pitch"]
	erreur_cum= stab["erreur_cum"]
	stabilite = stab["stabilite"]
	thrust = stab["thrust"]
	dt = stab["dt"]


	fct.set_mode(master,'GUIDED', master_lock)

# Changement d'altitude
	while abs(alt_cible-alt)>5:
		
		vit = state_dictionary["vitesse"]
		alt = state_dictionary["altitude"]
		vit_min = get_vit_min(master,state_dictionary, master_lock, 5)

		if vit > vit_min+1: # Sécurité pour empêcher la diminution de vitesse trop rapide associée au décrochage
			fct.send_attitude(master, master_lock, roll = 0,pitch = 20*copysign(1,var_alt),yaw = 0,thrust = 1)
			print(alt_cible-alt)
			vit_prec=vit
			time.sleep(dt)

# Stabilisation en cas de risque de décrochage
		else: 
			stab=cor.alt(state_dictionary, alt_target=alt_cible, erreur_cum=erreur_cum, alt_prec=alt_prec, pitch_prec=pitch_prec, dt=dt, thrust=thrust)

			erreur_cum = stab["erreur_cum"]
			alt_prec = stab["alt_prec"]
			pitch_prec= stab ["pitch"]
			stabilite += stab["stabilite"]
			thrust = stab["thrust"]

			fct.send_attitude(master, master_lock, 0,pitch_prec,0,thrust)
			time.sleep(dt)
			print("stabilisation")

#Stabilisation en fin de montée		
	while stabilite < 20:
		stab=cor.alt(state_dictionary, alt_target=alt_cible, erreur_cum=erreur_cum, alt_prec=alt_prec, pitch_prec=pitch_prec, dt=dt, thrust=thrust)
		if stab["stabilite"] == 0:
			stabilite = 0
		erreur_cum = stab["erreur_cum"]
		alt_prec = stab["alt_prec"]
		pitch_prec= stab ["pitch"]
		stabilite += stab["stabilite"]
		thrust = stab["thrust"]
		fct.send_attitude(master, master_lock, 0,pitch_prec,0,thrust)
		time.sleep(dt)
	fct.set_mode(master,'AUTO', master_lock)

#==========Accélération poussée min-poussée max==========

def accel(master : mavutil.mavlink_connection, state_dictionary : dict, master_lock : any, min_thrust : float = 0.3, max_thrust : float = 1):#vérifier la poussé min en décrochage
#Variables Globales
	
	global alt_cible

#Variables

#Compteur

	c=0

#Attitude

	alt = state_dictionary["altitude"]
	vit = state_dictionary["vitesse"]
	vit_prec = 0.5*vit
	acc= (vit-vit_prec)
	acc_prec = 0 
	yaw = state_dictionary["yaw"]

#Stabilité

	alt_stab = cor.alt(state_dictionary, alt_target=alt_cible, corr_thrust=False)
	erreur_cum = alt_stab["erreur_cum"]
	alt_prec = alt_stab["alt_prec"]
	pitch_prec= alt_stab["pitch"]
	dt=alt_stab["dt"]

#Initialisation de l'avion en mode poussée minimale pendant 3 secondes
	fct.set_mode(master,'GUIDED', master_lock)
	for i in range (30): 
		fct.send_attitude(master, master_lock, 0, pitch_prec, 0, min_thrust)
		time.sleep(0.1)

#Accélération

	while c<20: # accélération min-max jusqu'à atteindre un niveau ou l'accélération ne change plus (tolérance incluse) pendant assez longtemps
		
		acc_prec= acc
		alt = state_dictionary["altitude"]
		vit = state_dictionary["vitesse"]
		acc = (vit-vit_prec)/dt
		vit_prec = vit

		cap_stab = cor.cap(state_dictionary, cap_target=yaw)
		alt_stab = cor.alt(state_dictionary, alt_target=alt_cible, erreur_cum=erreur_cum, alt_prec=alt_prec, pitch_prec=pitch_prec, corr_thrust=False)

		erreur_cum = alt_stab["erreur_cum"]
		alt_prec = alt_stab["alt_prec"]
		pitch_prec = alt_stab["pitch"]
		roll= cap_stab["roll"]

		fct.send_attitude(master, master_lock, roll, pitch_prec, 0, max_thrust)
		if acc<acc_prec+5:
	 		c += 1
		else:
			c = max(0,c-1)
		time.sleep(dt)
	fct.set_mode(master,'AUTO', master_lock)


#==========Changement de poussée==========

def chgt_vit(master : mavutil.mavlink_connection, state_dictionary : dict, master_lock : any, vitesse : float):
	
	fct.set_mode(master,'GUIDED', master_lock)
	erreur_cum = 0
	c = 0	
	vit = 0
	while abs(vitesse-vit)>0.2 and c<10:
		vit_stab = cor.vit(master, vitesse,erreur_cum)
		thrust = vit_stab["thrust"]
		vit = state_dictionary['vitesse']
		fct.send_attitude(master, master_lock, 0,0,0, thrust)
		if abs(vitesse_vit)<0.2:
			c+=1
		else:
			c=max(0,c-1)
		time.sleep(dt)
	fct.set_mode(master,'AUTO', master_lock)
	
#==========Oscillation tanguage==========

def oscillation_tang(master : mavutil.mavlink_connection, state_dictionary : dict, master_lock :any, pitch_max : float = 10, nb_oscillation : int = 5):
    vit_target = get_vit_min(master,state_dictionary, master_lock, mass = 5)+2
    for i in range(nb_oscillation):
        pitch= state_dictionary["pitch"]

        while pitch<pitch_max:
            vit_stab = cor.vit(state_dictionary, vit_target= vit_target, erreur_cum=0, dt=0.05) 
            thrust = vit_stab["thrust"] 
            fct.send_attitude(master, master_lock, 0, pitch_max, 0, thrust)
        while pitch>-pitch_max:
            vit_stabc = cor.vit(state_dictionary, vit_target= vit_target, erreur_cum=0, dt=0.05) 
            thrust = vit_stab["thrust"] 
            fct.send_attitude(master, master_lock, 0, -pitch_max, 0, thrust)
