import customtkinter as ctk
import tkinter as tk
import time
import sys
import threading 

from backend import pre_verification,check_mission, waypoint, main
from functions import nettoyage,connection_vehicle2,lancement_sitl,armed,set_param


type_waypoint=["WAYPOINT", "TAKEOFF", "LAND", "RTL", "LOITER", "GUIDED"]
liste_maneuvres=["take_off(x)","vol en palier stabilisé", "accélération/décélération(x)", "virage à (x) °", "changement d'altitude(x)","oscillations en tangage","oscillations en roulis","variation rapide de poussée","S-turn(x)"]
arm=False
master = None
mission = []
dic_mission = {}
scroll_width = 300



def afficher_page(page,frame):
    page.pack_forget()
    frame.pack(expand=True, fill="both")
    if frame == frame_maneuvre:
        rafraichir_menu_selection()

def affichage_liste(dic):
    for el in dic.keys():
        dic[el][1].grid(row=(el), column=0, sticky='w', pady=10)

def reset_scroll():
    for widget in framen_maneuvre_scroll_maneuvre.winfo_children():
        widget.grid_forget()

def create_waypoint(dic=dic_mission):
    global mission
    number_waypoints = len(dic)  # On utilise la longueur du dictionnaire pour déterminer le numéro du waypoint
    try:
        assert all(float(entry.get()) for entry in liste_entries), "Veuillez mettre des int/float tous les champs avant de valider la mission."
        assert all(entry.get() for entry in liste_entries), "Veuillez remplir tous les champs avant de valider la mission."
        assert frame_waypoint_command_menu.get() != "ajouter une commande", "Veuillez sélectionner une commande avant de valider la mission."
        create_waypoint = []
        for entry in liste_entries:
            create_waypoint.append(float(entry.get()))
            entry.delete(0, tk.END)  # Effacer le contenu de l'entry après récupération
        create_waypoint.append(frame_waypoint_command_menu.get())
        frame_waypoint_command_menu.set("ajouter une commande") # Réinitialiser le menu déroulant
        mission.append(waypoint(create_waypoint[0],create_waypoint[1],create_waypoint[2],create_waypoint[3],create_waypoint[4]))
        ajouter_waypoint_dico(mission[-1],dic,number_waypoints,frame_waypoint_scroll_waypoint)
    except AssertionError as e:
        item = ctk.CTkLabel(frame_waypoint, text=str(e), font=("Arial", 12), text_color="red")
        item.place(x=400, y=300)
        app.after(3000, item.destroy)  # Supprimer le message d'erreur

def ajouter_waypoint_dico(val,dic,num,page):
    dic_maneuvres={}
    dic[num]=[val,dic_maneuvres]
    item = ctk.CTkLabel(page, text=f" {num}:{dic[num][0]}", font=("Arial", 12), text_color="green",cursor="hand2",wraplength=scroll_width-10,justify="left")
    item.bind("<Button-1>",lambda event: suppression_dico(event,dic))  # Lier le clic à la fonction de suppression
    dic[num].insert(-1,item)
    affichage_liste(dic)

def param_maneuvre(choix):
    if choix == liste_maneuvres[0]:
        frame_maneuvre_label_maneuvre.configure(text=f"{choix}: altitude de décollage")
        entry_maneuvre.place(x=400, y=150)
        return entry_maneuvre
    elif choix == liste_maneuvres[1]:
        entry_maneuvre.place_forget()
        return 0,0,0
    elif choix == liste_maneuvres[2]:
        frame_maneuvre_label_maneuvre.configure(text=f"{choix}: pourcentage de puissance (0-1)")
        entry_maneuvre.place(x=400, y=150)
        return entry_maneuvre
    elif choix == liste_maneuvres[3]:
        frame_maneuvre_label_maneuvre.configure(text=f"{choix}: angle du virage")
        entry_maneuvre.place(x=400, y=150)
        return entry_maneuvre
    elif choix == liste_maneuvres[4]:
        frame_maneuvre_label_maneuvre.configure(text=f"{choix}: altitude cible")
        entry_maneuvre.place(x=400, y=150)
        return entry_maneuvre
    elif choix == liste_maneuvres[5]:
        frame_maneuvre_label_maneuvre.configure(text=f"{choix}")
        entry_maneuvre.place_forget()
        return 4,0,0
    elif choix == liste_maneuvres[6]:
        frame_maneuvre_label_maneuvre.configure(text=f"{choix}")
        entry_maneuvre.place_forget()
        return 5,0,0
    elif choix == liste_maneuvres[7]:
        frame_maneuvre_label_maneuvre.configure(text=f"{choix}")
        entry_maneuvre.place_forget()
        return 6,0,0
    elif choix == liste_maneuvres[8]:
        frame_maneuvre_label_maneuvre.configure(text=f"{choix}: nombre de virage")
        entry_maneuvre.place(x=400, y=150)

def ajouter_maneuvre(choix, waypoint,val):
    try :
        assert waypoint != "Aucun", "Veuillez choisir un waypoint avant d'ajouter des maneuvres"
        num_waypoint=int(waypoint.split(":")[0].strip())
        dico = dic_mission[num_waypoint][2]  # Récupère le dictionnaire des manœuvres associées au waypoint
        num_maneuvres = len(dico)  # Nombre de manœuvres déjà associées au waypoint
        if "(x)" in choix:
            choix = choix.replace("(x)",f"({val})")  # Remplace (x) par la valeur entrée dans l'entry
            dico[num_maneuvres] = [choix]
            item = ctk.CTkLabel(framen_maneuvre_scroll_maneuvre, text=f" {num_maneuvres}:{dico[num_maneuvres][0]}", font=("Arial", 12), text_color="green", cursor="hand2",wraplength=scroll_width-10,justify="left")
            item.bind("<Button-1>",lambda event: suppression_dico(event,dico))  # Lier le clic à la fonction de suppression
        else :	
            dico[num_maneuvres] = [choix]
            item = ctk.CTkLabel(framen_maneuvre_scroll_maneuvre, text=f" {num_maneuvres}:{dico[num_maneuvres][0]}", font=("Arial", 12), text_color="green", cursor="hand2",wraplength=scroll_width-10,justify="left")
            item.bind("<Button-1>",lambda event: suppression_dico(event,dico))  # Lier le clic à la fonction de suppression
        dico[num_maneuvres].append(item)
        affichage_liste(dico)
    except AssertionError as e:
        item = ctk.CTkLabel(frame_maneuvre, text=str(e), font=("Arial", 12), text_color="red")
        item.pack(pady=10)
        app.after(3000, item.destroy)  # Supprimer le message d'erreur après 3 secondes


    
def suppression_dico(event,dico): # Permet de supprimer un élément d'un dictionnaire et son widget associé à partir d'un clic sur le widget (arg : event du clic, dictionnaire dans lequel supprimer l'élément )
    widget = event.widget
    num = int(widget.cget("text").split(":")[0].strip())  # Extraire le numéro de l'élément à supprimer
    dico[num][1].destroy()  # Supprimer le widget associé à l'élément
    del dico[num]  # Supprimer l'entrée du dictionnaire
    dico_neuf = indexage(dico)  # Réindexer le dictionnaire après suppression
    dico.clear()  # Mettre à jour le dictionnaire avec les nouvelles clés
    dico.update(dico_neuf)
    affichage_liste(dico)  # Réafficher la liste des éléments

def indexage(dico): # Permet de réindexer les éléments d'un dictionnaire après suppression pour éviter les trous dans la numérotation ( arg : dictionnaire )
    dico_bis={}
    tmp=0
    for el in dico:
        dico_bis[tmp]=dico[el]
        dico_bis[tmp][1].configure(text=f" {tmp}:{dico[el][0]}") # Mise à jour du texte du widget avec le nouveau numéro
        dico_bis[tmp][1].bind("<Button-1>", lambda e, d=dico_bis: suppression_dico(e, d))
        tmp+=1
    return dico_bis


def rafraichir_menu_selection():
    global dic_mission
    """Met à jour le menu déroulant à partir des clés du dictionnaire."""
    if not dic_mission:
        frame_maneuvre_menu_selection_waypoint.configure(values=["Aucun"])
        frame_maneuvre_menu_selection_waypoint.set("Aucun")
    else:
        # On crée les options à partir des données du dictionnaire
        # {k}: {v[0]} donne par exemple "1: WP"
        options = [f"{k}: {v[0]}" for k, v in dic_mission.items()]
        frame_maneuvre_menu_selection_waypoint.configure(values=options)

def choix_waypoint(choix,dico=dic_mission):
    id = int(choix.split(":")[0].strip())
    waypoint_selectionne = dico[id][0]
    dico_maneuvres = dico[id][2]
    #print(waypoint_selectionne)
    frame_maneuvre_active_waypoint.configure(text=f"{waypoint_selectionne}", text_color="cyan")
    reset_scroll()
    affichage_liste(dico_maneuvres)  # Affiche les manœuvres associées au waypoint sélectionné



def armement():
    global arm,master
    pre_verification(master)
    try:
        assert master is not None, "Veuillez connecter le véhicule avant de tenter d'armer."
        if frame_configuration_armed.get() == 1:
            frame_configuration_armed.configure(text="ARMED", progress_color="green")
            arm=True
            armed(master,arm)        
        else:
            frame_configuration_armed.configure(text="NOT ARMED", progress_color="red")
            arm=False
            armed(master,arm)
    except AssertionError as e:
        frame_configuration_armed.deselect()
        frame_configuration_armed.configure(text="NOT ARMED", progress_color="red")
        arm=False
        item = ctk.CTkLabel(frame_configuration, text=str(e), font=("Arial", 12), text_color="red")
        item.pack(pady=10)
        app.after(3000, item.destroy)  # Supprimer le message d'erreur après 3 secondes    

def connection_vehicle():
    item = ctk.CTkLabel(frame_menu, text="Connection en cours",text_color="green")
    item.place(x=10,y=20)
    lancement_sitl()
    global master
    master = connection_vehicle2()
    item.configure(text="Véhicule connecté",text_color="green")
    




def check_mission_interface(mission):
    try :
        assert len(mission)!=0, "La mission est vide. Veuillez ajouter au moins un waypoint avant de vérifier la mission."
        msg = check_mission(mission)
        item = ctk.CTkLabel(frame_waypoint, text=msg, font=("Arial", 12), text_color="green" if msg == "Mission valide" else "red")
        item.place(x=400, y=400)
        app.after(3000, item.destroy)  # Supprimer le message après 3 secondes
    except AssertionError as e:
        item = ctk.CTkLabel(frame_waypoint, text=str(e), font=("Arial", 12), text_color="red",wraplength=180,justify="left") # wraplength a adapter en fonction de la taille de l'interface
        item.place(x=200, y=400)
        app.after(3000, item.destroy)  # Supprimer le message d'erreur après 3 secondes



def charger_pid_actuels(axe_nom):
    global master
    if master is None:
        label_status.configure(text="Drone non connecté", text_color="red")
        return

    # Configuration des noms selon l'axe
    
    prefix = "RLL_RATE" if axe_nom == "Roll" else "PTCH_RATE" if axe_nom == "Pitch" else "YAW2SRV"
    if prefix in ["RLL_RATE","PTCH_RATE"]:
        
        suffixes = ["P", "I", "D"]
    else :
         
        suffixes=["RLL","INT","DAMP"]    
                
        
    vals = {"P": 0.0, "I": 0.0, "D": 0.0}

    try:
        label_status.configure(text=f"Lecture {axe_nom}...", text_color="yellow")
        app.update() # Force la mise à jour visuelle du label

        for s in suffixes:
            param_id = f"{prefix}_{s}"

            # 1. On envoie la requête de lecture
            master.mav.param_request_read_send(
                master.target_system,
                master.target_component,
                param_id.encode('utf-8'),-1)
                
            # 2. Boucle pour filtrer les messages et trouver le bon PARAM_VALUE
            found = False
            timeout_timer = time.time() + 2.0  # 2 secondes max par paramètre

            while time.time() < timeout_timer:
                # On écoute le flux (non-bloquant avec un petit timeout interne)
                msg = master.recv_match(type='PARAM_VALUE', blocking=True, timeout=0.1)

                if msg:
                    # Est-ce que c'est le paramètre qu'on a demandé ?
                    if msg.param_id == param_id:
                        vals[s] = msg.param_value
                        found = True
                        break # On a trouvé le P, on sort du while pour passer au I...

            if not found:
                print(f"DEBUG: Timeout sur {param_id}")

            # 3. Mise à jour des Entry avec les valeurs trouvées
        entry_p.delete(0, tk.END)
        entry_p.insert(0, f"{vals['P']:.4f}")

        entry_i.delete(0, tk.END)
        entry_i.insert(0, f"{vals['I']:.4f}")

        entry_d.delete(0, tk.END)
        entry_d.insert(0, f"{vals['D']:.4f}")

        label_status.configure(text=f"Configuration {axe_nom} chargée", text_color="green")

    except Exception as e:
        print(f"Erreur critique : {e}")
        label_status.configure(text="Erreur de lecture SITL", text_color="red")
        
        
        
        
        
def sauvegarder_pid():
    global master    #Envoie les valeurs modifiées au drone
    axe = axe_var.get()
    prefix = "RLL_RATE" if axe == "Roll" else "PTCH_RATE" if axe == "Pitch" else "YAW2SRV"
    
   
    if prefix in ["RLL_RATE","PTCH_RATE"]:
       
       suffixes = ["P", "I", "D"]
    else :
        
       suffixes=["RLL","INT","DAMP"]  

    try:
        set_param(master,f"{prefix}_{suffixes[0]}", float(entry_p.get()))
        set_param(master,f"{prefix}_{suffixes[1]}", float(entry_i.get()))
        set_param(master,f"{prefix}_{suffixes[2]}", float(entry_d.get()))
        label_status.configure(text="Paramètres mis à jour !", text_color="cyan")
    except ValueError:
        label_status.configure(text="Format invalide", text_color="red")

def terminal_write(message):
    frame_launch_terminal.configure(state="normal")
    frame_launch_terminal.insert("end", message)
    frame_launch_terminal.see("end")
    frame_launch_terminal.configure(state="disabled")

def run_with_terminal(func, *args, **kwargs):
    old_stdout = sys.stdout  # sauvegarde l'ancien stdout
    class StdoutRedirector:
        def write(self, message):
            # envoie chaque message dans le widget terminal
            app.after(0, terminal_write, message)
        def flush(self):
            pass  # nécessaire pour que certains prints fonctionnent
    sys.stdout = StdoutRedirector()  # redirige stdout vers notre widget
    try:
        func(*args, **kwargs)  # exécute la fonction ciblée
    finally:
        sys.stdout = old_stdout  # restaure stdout à la fin

def lancer_mission():

    frame_launch_terminal.configure(state="normal")          
    frame_launch_terminal.delete("1.0", "end")                       ## pour supprimer si on lance une mission deux fois d'affilée
    frame_launch_terminal.configure(state="disabled")

    thread = threading.Thread(target=run_with_terminal, args=(main, master,mission))           ## A modifier 
    thread.daemon = True
    thread.start()

def ajouter_log(message):
    # Ajoute un message horodaté dans l'onglet Logs.
    import datetime
    # Format : [HH:MM:SS] Message
    date = datetime.datetime.now().strftime("[%H:%M:%S]")
    full_log = f"{date} {message}\n"
    
    log_output.configure(state="normal") # On active l'écriture
    log_output.insert("end", full_log)   # On insère à la fin
    log_output.see("end")                # Scroll automatique vers le bas
    log_output.configure(state="disabled") # On verrouille

def effacer_logs():
    log_output.configure(state="normal")
    log_output.delete("1.0", "end")
    log_output.configure(state="disabled")



########################################################################### Création de la fenêtre principale ###########################################################################
ctk.set_appearance_mode("dark")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Thèmes: "blue" (standard), "green", "dark-blue"
app = ctk.CTk()
app.geometry("800x800")
app.title("Psyn")

########################################################################### Gestion de la page principale ###########################################################################
frame_menu = ctk.CTkFrame(app)
frame_menu.pack(expand=True, fill="both")
frame_menu_name = ctk.CTkLabel(frame_menu, text="MENU PRINCIPAL", font=("Arial", 20))
frame_menu_name.pack(pady=20)

# Création et placement des boutons
frame_menu_connect = ctk.CTkButton(frame_menu, text="connection du vehicule", command=connection_vehicle, corner_radius=10,width=250, height=40)
frame_menu_connect.pack(pady=10)
frame_menu_config = ctk.CTkButton(frame_menu, text="Config véhicule", command=lambda: afficher_page(frame_menu,frame_configuration), corner_radius=10,width=250, height=40)
frame_menu_config.pack(pady=10)
frame_menu_waypoint = ctk.CTkButton(frame_menu, text="Waypoint",command=lambda: afficher_page(frame_menu,frame_waypoint), corner_radius=10,width=250, height=40)
frame_menu_waypoint.pack(pady=10)
frame_menu_maneuvre = ctk.CTkButton(frame_menu, text="Maneuvres", command=lambda: afficher_page(frame_menu,frame_maneuvre), corner_radius=10,width=250, height=40)
frame_menu_maneuvre.pack(pady=10)
frame_menu_close = ctk.CTkButton(frame_menu, text="nettoyage ports", command=nettoyage, corner_radius=10,width=250, height=40)
frame_menu_close.pack(pady=10)
frame_menu_launch = ctk.CTkButton(frame_menu, text="Lancement Mission", command=lambda: afficher_page(frame_menu, frame_launch), corner_radius=10,width=250,height=40)
frame_menu_launch.pack(pady=10)

########################################################################### Gestion de la page maneuvres ###########################################################################
frame_maneuvre = ctk.CTkFrame(app)
frame_maneuvre_label_waypoint = ctk.CTkLabel(frame_maneuvre, text="Waypoints", font=("Arial", 20), text_color="orange")
frame_maneuvre_label_waypoint.place(x=600, y=20)
frame_maneuvre_menu_selection_waypoint = ctk.CTkOptionMenu(frame_maneuvre, values=["Aucun"],command=choix_waypoint)
frame_maneuvre_menu_selection_waypoint.place(x=600, y=50)
frame_maneuvre_active_waypoint = ctk.CTkLabel(frame_maneuvre, text="Aucun waypoint sélectionné", font=("Arial", 12), text_color="orange")
frame_maneuvre_active_waypoint.place(x=15, y=50)

# Bouton de retour à la page principale
frame_maneuvre_retour = ctk.CTkButton(frame_maneuvre, text="Retour", command=lambda: afficher_page(frame_maneuvre,frame_menu), fg_color="gray")
frame_maneuvre_retour.place(x=400, y=20)
frame_maneuvre_label_maneuvre = ctk.CTkLabel(frame_maneuvre, text="choisir une maneuvre", font=("Arial", 12), text_color="orange")
frame_maneuvre_label_maneuvre.place(x=400, y=100)
entry_maneuvre = ctk.CTkEntry(frame_maneuvre, placeholder_text="Entrez la valeur...")

# Affichage de la liste des maneuvres
menu1 = ctk.CTkOptionMenu(frame_maneuvre, values=liste_maneuvres, command=param_maneuvre)
menu1.set("ajouter une maneuvre") # Texte par défaut
menu1.place(x=400, y=50)
frame_maneuvre_valid_maneuvre = ctk.CTkButton(frame_maneuvre, text="Valider la manœuvre", command=lambda: ajouter_maneuvre(menu1.get(),frame_maneuvre_menu_selection_waypoint.get(),entry_maneuvre.get()), fg_color="green")
frame_maneuvre_valid_maneuvre.place(x=400, y=200)
framen_maneuvre_scroll_maneuvre = ctk.CTkScrollableFrame(frame_maneuvre, height=400, width=scroll_width)
framen_maneuvre_scroll_maneuvre.place(x=50, y=100)

########################################################################### Gestion de la page waypoints ###########################################################################
frame_waypoint = ctk.CTkFrame(app)
frame_waypoint_return = ctk.CTkButton(frame_waypoint, text="Retour", command=lambda: afficher_page(frame_waypoint,frame_menu), fg_color="gray")
frame_waypoint_return.place(x=400, y=10)
noms_parametres = ["Altitude (m)", "Latitude(°)", "Longitude(°)", "rayon (m)", "commande"]
liste_entries = []

# Création du tableau de création de waypoint
for i in range(len(noms_parametres)-1):
    # Label (colonne 0)
    frame_waypoint_label_value = ctk.CTkLabel(frame_waypoint, text=noms_parametres[i])
    frame_waypoint_label_value.place(x=400, y=50*i+50)
    # Champ de saisie (colonne 1)
    frame_waypoint_entry = ctk.CTkEntry(frame_waypoint, placeholder_text="Entrez la valeur...")
    frame_waypoint_entry.place(x=500, y=50*i+50)
    liste_entries.append(frame_waypoint_entry) # On garde une trace de l'entry
frame_waypoint_label_value = ctk.CTkLabel(frame_waypoint, text=noms_parametres[4])
frame_waypoint_label_value.place(x=400, y=250)

# Menu déroulant pour la commande
frame_waypoint_command_menu = ctk.CTkOptionMenu(frame_waypoint, values=type_waypoint)
frame_waypoint_command_menu.set("ajouter une commande") # Texte par défaut
frame_waypoint_command_menu.place(x=500, y=250)

# créations des boutons
frame_waypoint_valid = ctk.CTkButton(frame_waypoint, text="Valider le Waypoint", command=create_waypoint)
frame_waypoint_valid.place(x=400, y=300)
frame_waypoint_check_mission = ctk.CTkButton(frame_waypoint, text="Vérifier la mission", command=lambda: check_mission_interface(mission))
frame_waypoint_check_mission.place(x=400, y=350)
frame_waypoint_scroll_waypoint = ctk.CTkScrollableFrame(frame_waypoint, height=600,width=scroll_width)
frame_waypoint_scroll_waypoint.place(x=10, y=10)

########################################################################### Gestion de la page de configuration ###########################################################################

frame_configuration = ctk.CTkFrame(app)
frame_configuration_name = ctk.CTkLabel(frame_configuration, text="Configuration du véhicule", font=("Arial", 20), text_color="orange")
frame_configuration_name.pack(pady=20)    
frame_configuration_return = ctk.CTkButton(frame_configuration, text="Retour", command=lambda: afficher_page(frame_configuration,frame_menu), fg_color="gray")
frame_configuration_return.pack(pady=10)
frame_configuration_armed = ctk.CTkSwitch(frame_configuration, text="NOT ARMED", command=armement)
frame_configuration_armed.pack(pady=40, padx=20)

# Dans la section PID de frame_page3 
axe_var = ctk.StringVar(value="Roll")
menu_pid = ctk.CTkOptionMenu(frame_configuration, 
                             values=["Roll", "Pitch", "Yaw"], 
                             variable=axe_var,
                             command=charger_pid_actuels)
menu_pid.pack(pady=10)

frame_inputs = ctk.CTkFrame(frame_configuration, fg_color="transparent")
frame_inputs.pack(pady=5)

# Assignation des variables globales lors de la création
ctk.CTkLabel(frame_inputs, text="P :").grid(row=0, column=0, padx=5)
entry_p = ctk.CTkEntry(frame_inputs, width=120)
entry_p.grid(row=0, column=1, pady=2)

ctk.CTkLabel(frame_inputs, text="I :").grid(row=1, column=0, padx=5)
entry_i = ctk.CTkEntry(frame_inputs, width=120)
entry_i.grid(row=1, column=1, pady=2)

ctk.CTkLabel(frame_inputs, text="D :").grid(row=2, column=0, padx=5)
entry_d = ctk.CTkEntry(frame_inputs, width=120)
entry_d.grid(row=2, column=1, pady=2)

label_status = ctk.CTkLabel(frame_configuration, text="Sélectionnez un axe pour charger les données", font=("Arial", 11))
label_status.pack()

btn_save = ctk.CTkButton(frame_configuration, text="Appliquer les changements", command=sauvegarder_pid, fg_color="green")
btn_save.pack(pady=10)

########################################################################### Gestion de la page de lancement de la mission ###########################################################################

frame_launch = ctk.CTkFrame(app)
frame_launch_name = ctk.CTkLabel(frame_launch, text="Lancement de la Mission", font=("Arial", 20), text_color="orange")
frame_launch_name.pack(pady=20)
frame_launch_return = ctk.CTkButton(frame_launch, text="Retour", command=lambda: afficher_page(frame_launch, frame_menu), fg_color="gray")
frame_launch_return.pack(pady=10)
frame_launch_start_mission = ctk.CTkButton(frame_launch, text="Lancer la Mission", command=lancer_mission)
frame_launch_start_mission.pack(pady=40)

## creation du terminal a l'intérieur 
frame_launch_terminal = ctk.CTkTextbox(frame_launch, width=700, height=400, corner_radius=5)
frame_launch_terminal.pack(pady=20)
frame_launch_terminal.configure(state="disabled")

########################################################################### Gestion de la page des logs ###########################################################################
frame_logs = ctk.CTkFrame(app)

label_logs = ctk.CTkLabel(frame_logs, text="HISTORIQUE DES MANOEUVRES", font=("Arial", 20), text_color="orange")
label_logs.pack(pady=20)

btn_retour_logs = ctk.CTkButton(frame_logs, text="Retour", command=lambda: afficher_page(frame_logs, frame_page1), fg_color="gray")
btn_retour_logs.pack(pady=10)

# Le widget de texte pour les logs
log_output = ctk.CTkTextbox(frame_logs, width=700, height=500, font=("Courier New", 12))
log_output.pack(pady=20, padx=20)
log_output.configure(state="disabled") # On le met en lecture seule

# Bouton pour effacer les logs
btn_clear_logs = ctk.CTkButton(frame_logs, text="Effacer l'historique", command=lambda: effacer_logs(), fg_color="#721c24")
btn_clear_logs.pack(pady=5)

# Ajouter le bouton d'accès sur le menu principal (Page 1)
frame1_btn_logs = ctk.CTkButton(frame_page1, text="Journal (Logs)", command=lambda: afficher_page(frame_page1, frame_logs), corner_radius=10,width=250,height=40)
frame1_btn_logs.pack(pady=10)

app.mainloop()
