from functions import get_attitude


def corr_alt(master, alt_target, erreur_cum=0, dt=0.05, corr_thrust=True,thrust=0.5):
	"""Retourne les valeurs de thrust et pitch pour stabiliser l'altitude. 
		Si l'option de correction de poussé est désactivée la correction d'erreur sera plus brutale
    	- alt_target : altitude objectif de la stabilisation
      	- thrust : valeur initiale ou précédente
    	- erreur_cum : cumul d'erreur précédent
    	- dt : intervalle depuis le dernier appel
    	- La fonction devra être modifiée au niveau des saturateurs en prennant en compte les vitesses de décrochages.
      	- Avec les paramètres arduplanne de base ces saturateurs sont bon."""

	altitude = get_attitude(master)["altitude"]
	erreur = alt_target - altitude

# proportionnel
	pitch = erreur * 5

# saturation
	pitch = max(-10, min(pitch, 10))
	if corr_thrust:
		if abs(erreur) < 3:
			erreur_cum += erreur * dt

		thrust = 0.5 + erreur_cum * 0.01
		thrust = max(0.3, min(thrust, 1))
		
	stabilite = abs(erreur) < 1

	return {
        "thrust": thrust,
        "pitch": pitch_stab,
        "stabilite": stabilite,
        "erreur_cum": erreur_cum,
        "dt": dt
    }


def corr_vit(master, vit_target, erreur_cum=0, dt=0.05):
	'''Change la poussée pour atteindre la vitesse cible
	-vit_target : vitesse objectif 
	-erreur_cum : erreur intégrée sur le temps ou l'erreur à un écart de 5 m/s  
  '''

	vitesse = get_attitude(master)["speed"]
	erreur = vitesse_target - vitesse
	
	thrust_prop= erreur*0.05 # correction rapide de la poussé terme proportionnel

	if abs(erreur) < 5:
		erreur_cum += erreur * dt

	thrust_int = erreur_cum * 0.02 #correction plus fine de la poussé terme intégral 

	thrust = 0.5+thrust_int+thrust_prop
	thrust = max(0.3, min(thrust, 1))

	return {
        "thrust": thrust,
        "erreur_cum": erreur_cum,
        "dt": dt
    }

def corr_cap(master, cap_target):

	cap = get_attitude(master)["yaw"]

	erreur = (cap_target - cap + 180) % 360 - 180

	roll = erreur * 0.5
	roll = max(-45, min(roll, 45))

	stabilite = abs(erreur) < 3

	return {
        "roll": roll,
        "stabilite": stabilite,
    }



