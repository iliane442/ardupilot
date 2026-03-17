from functions import get_attitude

#==========Correcteur d'altitude==========

def alt(master, alt_target, erreur_cum=0, alt_prec=0, pitch_prec=0, dt=0.05, corr_thrust=True, thrust=0.5):
	"""Retourne les valeurs de thrust et pitch pour stabiliser l'altitude. 
	Correcteur PD pour le tangage et PI pour la poussée 	
	Si l'option de correction de poussé est désactivée la correction d'erreur sera plus brutale
    	- alt_target : altitude objectif de la stabilisation
      	- thrust : valeur initiale ou précédente
    	- erreur_cum : cumul d'erreur précédent
    	- dt : intervalle depuis le dernier appel
	- alt_prec : altitude précédante 
    	- La fonction devra être modifiée au niveau des saturateurs en prennant en compte les vitesses de décrochages.
      	- Avec les paramètres arduplanne de base ces saturateurs sont bon."""

	alt = get_attitude(master)["altitude"]
	erreur = alt_target - alt
	derreur = (alt_prec-alt)/dt
	alt_prec = alt
	
#Variation max 
	var_max = 1
# Correcteur proportionnel dérivé
	pitch_prop = erreur*1
	pitch_der = derreur*0.2
	pitch = max(pitch_prec-1,min(pitch_prop+pitch_der,pitch_prec+1))

# saturation
	pitch = max(-15, min(pitch, 15))

# Activation du correcteur pour la puissance moteur + correcteur PI
	if corr_thrust:
		if abs(erreur) < 3:
			erreur_cum += erreur * dt

		thrust = 0.5 + erreur_cum * 0.01
		thrust = max(0.3, min(thrust, 1)) #Saturation min pour éviter le décrochage et max pour rester dans les plages de valeurs admissibles
		
	stabilite = abs(erreur) < 1 

	return {
        "thrust": thrust,
        "pitch": pitch,
        "stabilite": stabilite,
        "erreur_cum": erreur_cum,
        "alt_prec": alt_prec,
        "dt": dt
    }

#==========Correcteur de vitesse==========

def vit(master, vit_target, erreur_cum=0, dt=0.05):
	'''Change la poussée pour atteindre la vitesse cible
	Correcteur PI pour la poussée
	-vit_target : vitesse objectif 
	-erreur_cum : erreur intégrée sur le temps ou l'erreur à un écart de 5 m/s 
	-vérification de l'oscillation de la poussé dans ce cas de figure non effectué
  '''

	vitesse = get_attitude(master)["speed"]
	erreur = vit_target - vitesse
	
	thrust_prop= erreur*0.05 # correction rapide de la poussé terme proportionnel

	if abs(erreur) < 5:
		erreur_cum += erreur * dt
		erreur_cum = max(-50, min(erreur_cum, 50))

	thrust_int = erreur_cum * 0.05 #correction plus fine de la poussé terme intégral 

	thrust = 0.5+thrust_int+thrust_prop
	thrust = max(0.3, min(thrust, 1))

	return {
        "thrust": thrust,
        "erreur_cum": erreur_cum,
        "dt": dt
    }

#==========Correcteur de cap==========

def cap(master, cap_target):
	'''Modifie le cap de l'appareil en effectuant des virages
	Correcteur P pour l'inclinaison(roll)
	-cap_target : cap objectif à maintenir ou atteindre (techniquement couplé à la fonction send_attitude peut effectuer un virage)
	'''

	cap = get_attitude(master)["yaw"]

	erreur = (cap_target-cap+180)%360-180

	roll = erreur * 0.5
	roll = max(-45, min(roll, 45))

	stabilite = abs(erreur) < 3

	return {
        "roll": roll,
        "stabilite": stabilite,
    }
