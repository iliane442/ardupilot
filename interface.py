import customtkinter as ctk
import tkinter as tk
import time
import sys
import threading 

from backend import pre_verification,check_mission, waypoint, main
from functions import nettoyage,connection_vehicle2,lancement_sitl,armed,set_param


type_waypoint=["WAYPOINT", "TAKEOFF", "LAND", "RTL", "LOITER", "GUIDED"]
liste_maneuvres=["take_off","vol en palier stabilisé", "accélération/décélération", "virage à x °", "changement d'altitude","vol en turbulence naturelle","approche stabilisée","touch and go"]
arm=False
master = None
mission = []
dic_mission = {}
scroll_width = 300


def afficher_page(page,frame):
    page.pack_forget()
    frame.pack(expand=True, fill="both")
    if frame == page_maneuvres:
        rafraichir_menu_selection()

def affichage_liste(dic):
    for el in dic.keys():
        dic[el][1].grid(row=(el), column=0, sticky='w', pady=10)

def reset_scroll():
    for widget in scroll_maneuvre.winfo_children():
        widget.grid_forget()

def create_waypoint(dic=dic_mission):
    global mission
    number_waypoints = len(dic)  # On utilise la longueur du dictionnaire pour déterminer le numéro du waypoint
    try:
        assert all(float(entry.get()) for entry in liste_entries), "Veuillez mettre des int/float tous les champs avant de valider la mission."
        assert all(entry.get() for entry in liste_entries), "Veuillez remplir tous les champs avant de valider la mission."
        assert menu2.get() != "ajouter une commande", "Veuillez sélectionner une commande avant de valider la mission."
        create_waypoint = []
        for entry in liste_entries:
            create_waypoint.append(float(entry.get()))
            entry.delete(0, tk.END)  # Effacer le contenu de l'entry après récupération
        create_waypoint.append(menu2.get())
        menu2.set("ajouter une commande") # Réinitialiser le menu déroulant
        mission.append(waypoint(create_waypoint[0],create_waypoint[1],create_waypoint[2],create_waypoint[3],create_waypoint[4]))
        ajouter_waypoint_dico(mission[-1],dic,number_waypoints,scroll_waypoint)
    except AssertionError as e:
        item = ctk.CTkLabel(frame_page4, text=str(e), font=("Arial", 12), text_color="red")
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
    if choix == "take_off":
        lab_maneuvres.configure(text=f"{choix}: altitude de décollage")
        entry = ctk.CTkEntry(page_maneuvres, placeholder_text="Entrez la valeur...")
        entry.place(x=400, y=150)
        return entry
    if choix == "vol en palier stabilisé":
        return 0,0,0
    elif choix == "accélération/décélération":
        lab_maneuvres.configure(text=f"{choix}: pourcentage de puissance (0-1)")
        entry = ctk.CTkEntry(page_maneuvres, placeholder_text="Entrez la valeur...")
        entry.place(x=400, y=150)
        return entry
    elif choix == "virage à x °":
        lab_maneuvres.configure(text=f"{choix}: angle du virage")
        entry = ctk.CTkEntry(page_maneuvres, placeholder_text="Entrez la valeur...")
        entry.place(x=400, y=150)
        return entry
    elif choix == "changement d'altitude":
        lab_maneuvres.configure(text=f"{choix}: altitude cible")
        entry = ctk.CTkEntry(page_maneuvres, placeholder_text="Entrez la valeur...")
        entry.place(x=400, y=150)
        return entry
    elif choix == "vol en turbulence naturelle":
        return 4,0,0
    elif choix == "approche stabilisée":
        return 5,0,0
    elif choix == "touch and go":
        return 6,0,0

def ajouter_maneuvre(choix, waypoint):
    param_maneuvre(choix) # A modifier pour prendre en compte les paramètres de chaque manoeuvre
    num_waypoint=int(waypoint.split(":")[0].strip())
    dico = dic_mission[num_waypoint][2]  # Récupère le dictionnaire des manœuvres associées au waypoint
    num_maneuvres = len(dico)  # Nombre de manœuvres déjà associées au waypoint	
    dico[num_maneuvres] = [choix]
    item = ctk.CTkLabel(scroll_maneuvre, text=f" {num_maneuvres}:{dico[num_maneuvres][0]}", font=("Arial", 12), text_color="green", cursor="hand2",wraplength=scroll_width-10,justify="left")
    item.bind("<Button-1>",lambda event: suppression_dico(event,dico))  # Lier le clic à la fonction de suppression
    dico[num_maneuvres].append(item)
    affichage_liste(dico)
    rafraichir_menu_selection()
    
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
        menu_selection_waypoint.configure(values=["Aucun"])
        menu_selection_waypoint.set("Aucun")
    else:
        # On crée les options à partir des données du dictionnaire
        # {k}: {v[0]} donne par exemple "1: WP"
        options = [f"{k}: {v[0]}" for k, v in dic_mission.items()]
        menu_selection_waypoint.configure(values=options)

def choix_waypoint(choix,dico=dic_mission):
    id = int(choix.split(":")[0].strip())
    waypoint_selectionne = dico[id][0]
    dico_maneuvres = dico[id][2]
    #print(waypoint_selectionne)
    activ_wayp.configure(text=f"{waypoint_selectionne}", text_color="cyan")
    reset_scroll()
    affichage_liste(dico_maneuvres)  # Affiche les manœuvres associées au waypoint sélectionné



def armement():
    global arm,master
    pre_verification(master)
    try:
        assert master is not None, "Veuillez connecter le véhicule avant de tenter d'armer."
        if switch_arm.get() == 1:
            switch_arm.configure(text="ARMED", progress_color="green")
            arm=True
            armed(master,arm)        
        else:
            switch_arm.configure(text="NOT ARMED", progress_color="red")
            arm=False
            armed(master,arm)
    except AssertionError as e:
        switch_arm.deselect()
        switch_arm.configure(text="NOT ARMED", progress_color="red")
        arm=False
        item = ctk.CTkLabel(frame_page3, text=str(e), font=("Arial", 12), text_color="red")
        item.pack(pady=10)
        app.after(3000, item.destroy)  # Supprimer le message d'erreur après 3 secondes    

def connection_vehicle():
    global master
    master = connection_vehicle2()



def check_mission_interface(mission):
    try :
        assert len(mission)!=0, "La mission est vide. Veuillez ajouter au moins un waypoint avant de vérifier la mission."
        msg = check_mission(mission)
        item = ctk.CTkLabel(frame_page4, text=msg, font=("Arial", 12), text_color="green" if msg == "Mission valide" else "red")
        item.place(x=400, y=400)
        app.after(3000, item.destroy)  # Supprimer le message après 3 secondes
    except AssertionError as e:
        item = ctk.CTkLabel(frame_page4, text=str(e), font=("Arial", 12), text_color="red",wraplength=180,justify="left") # wraplength a adapter en fonction de la taille de l'interface
        item.place(x=200, y=400)
        app.after(3000, item.destroy)  # Supprimer le message d'erreur après 3 secondes



def charger_pid_actuels(axe_nom):
    global master
    # Récupère les valeurs réelles du drone pour remplir les champs
    prefix = "RLL" if axe_nom == "Roll" else "PTCH" if axe_nom == "Pitch" else "YAW"
    suffixes = ["P", "I", "D"]
    vals = {}

    try:
        label_status.configure(text="Récupération...", text_color="yellow")
        app.update()

        for s in suffixes:
            param_id = f"{prefix}_RATE_{s}"
            
            # 1. On demande explicitement au drone de nous envoyer la valeur
            master.mav.param_request_read_send(
                master.target_system, 
                master.target_component,
                param_id.encode('utf-8'), 
                -1  # -1 car on cherche par nom (param_id) et non par index
            )
            
            # 2. On attend le message de retour spécifique
            
            msg = master.recv_match(type='PARAM_VALUE', blocking=True, timeout=1.0)
            
            if msg and msg.param_id == param_id:
                vals[s] = msg.param_value
            else:
                # Si pas de réponse, on tente la méthode cache
                vals[s] = master.param_fetch_one(param_id)

        # 3. Mise à jour de l'interface
        entry_p.delete(0, tk.END)
        entry_p.insert(0, str(round(vals["P"], 4)))
        
        entry_i.delete(0, tk.END)
        entry_i.insert(0, str(round(vals["I"], 4)))
        
        entry_d.delete(0, tk.END)
        entry_d.insert(0, str(round(vals["D"], 4)))

        label_status.configure(text=f"Valeurs {axe_nom} chargées !", text_color="green")

    except Exception as e:
        print(f"Erreur lecture : {e}")
        label_status.configure(text="Erreur de lecture SITL", text_color="red")

def sauvegarder_pid():
    global master
    #Envoie les valeurs modifiées au drone
    axe = axe_var.get()
    prefix = "RLL" if axe == "Roll" else "PTCH" if axe == "Pitch" else "YAW"
    
    try:
        set_param(master,f"{prefix}_RATE_P", float(entry_p.get()))
        set_param(master,f"{prefix}_RATE_I", float(entry_i.get()))
        set_param(master,f"{prefix}_RATE_D", float(entry_d.get()))
        label_status.configure(text="Paramètres mis à jour !", text_color="cyan")
    except ValueError:
        label_status.configure(text="Format invalide", text_color="red")

def terminal_write(message):
    terminal.configure(state="normal")
    terminal.insert("end", message)
    terminal.see("end")
    terminal.configure(state="disabled")

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

    terminal.configure(state="normal")          
    terminal.delete("1.0", "end")                       ## pour supprimer si on lance une mission deux fois d'affilée
    terminal.configure(state="disabled")

    thread = threading.Thread(target=run_with_terminal, args=(main, master,mission))           ## A modifier 
    thread.daemon = True
    thread.start()


# 2. Création de la fenêtre principale
ctk.set_appearance_mode("dark")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Thèmes: "blue" (standard), "green", "dark-blue"
app = ctk.CTk()
app.geometry("800x800")
app.title("Psyn")




# Gestion de la page principale
frame_page1 = ctk.CTkFrame(app)
frame_page1.pack(expand=True, fill="both")

label1 = ctk.CTkLabel(frame_page1, text="MENU PRINCIPAL", font=("Arial", 20))
label1.pack(pady=20)

# Création des boutons
frame1_fermeture = ctk.CTkButton(frame_page1, text="fermeture", command=nettoyage, corner_radius=10,width=250, height=40)
frame1_sitl = ctk.CTkButton(frame_page1, text="lancement SITL", command=lancement_sitl, corner_radius=10,width=250, height=40)
frame1_connection = ctk.CTkButton(frame_page1, text="connection du vehicule", command=connection_vehicle, corner_radius=10,width=250, height=40)
frame1_config = ctk.CTkButton(frame_page1, text="Config véhicule", command=lambda: afficher_page(frame_page1,frame_page3), corner_radius=10,width=250, height=40)
frame1_maneuvre = ctk.CTkButton(frame_page1, text="Maneuvres", command=lambda: afficher_page(frame_page1,page_maneuvres), corner_radius=10,width=250, height=40)
frame1_waypoint = ctk.CTkButton(frame_page1, text="Waypoint",command=lambda: afficher_page(frame_page1,frame_page4), corner_radius=10,width=250, height=40)


# Placement des boutons sur la fenêtre
frame1_sitl.pack(pady=10)
frame1_connection.pack(pady=10)
frame1_config.pack(pady=10)
frame1_waypoint.pack(pady=10)
frame1_maneuvre.pack(pady=10)
frame1_fermeture.pack(pady=10)




# Gestion de la page maneuvres
page_maneuvres = ctk.CTkFrame(app)
label2 = ctk.CTkLabel(page_maneuvres, text="Maneuvres", font=("Arial", 20), text_color="orange")
label2.place(x=200, y=20)

lab_wayp = ctk.CTkLabel(page_maneuvres, text="Waypoints", font=("Arial", 20), text_color="orange")
lab_wayp.place(x=600, y=20)
menu_selection_waypoint = ctk.CTkOptionMenu(page_maneuvres, values=["Aucun"],command=choix_waypoint)
menu_selection_waypoint.place(x=600, y=50)
activ_wayp = ctk.CTkLabel(page_maneuvres, text="Aucun waypoint sélectionné", font=("Arial", 12), text_color="orange")
activ_wayp.place(x=15, y=50)
# Bouton de retour à la page principale
frame2_btn_retour = ctk.CTkButton(page_maneuvres, text="Retour", command=lambda: afficher_page(page_maneuvres,frame_page1), fg_color="gray")
frame2_btn_retour.place(x=400, y=20)
lab_maneuvres = ctk.CTkLabel(page_maneuvres, text="choisir une maneuvre", font=("Arial", 12), text_color="orange")
# Affichage de la liste des maneuvres
menu1 = ctk.CTkOptionMenu(page_maneuvres, 
                         values=liste_maneuvres,
                         command=lambda event: ajouter_maneuvre(event, menu_selection_waypoint.get()))
menu1.set("ajouter une maneuvre") # Texte par défaut
menu1.place(x=400, y=50,)
scroll_maneuvre = ctk.CTkScrollableFrame(page_maneuvres, height=400, width=scroll_width)
scroll_maneuvre.place(x=50, y=100)





# Gestion de la page waypoints
frame_page4 = ctk.CTkFrame(app)
frame4_btn_retour = ctk.CTkButton(frame_page4, text="Retour", command=lambda: afficher_page(frame_page4,frame_page1), fg_color="gray")
frame4_btn_retour.place(x=400, y=10)
noms_parametres = ["Altitude (m)", "Latitude(°)", "Longitude(°)", "rayon (m)", "commande"]
liste_entries = []

# Création du tableau de création de waypoint
for i in range(len(noms_parametres)-1):
    # Label (colonne 0)
    label = ctk.CTkLabel(frame_page4, text=noms_parametres[i])
    label.place(x=400, y=50*i+50)
    # Champ de saisie (colonne 1)
    entry = ctk.CTkEntry(frame_page4, placeholder_text="Entrez la valeur...")
    entry.place(x=500, y=50*i+50)
    liste_entries.append(entry) # On garde une trace de l'entry
label = ctk.CTkLabel(frame_page4, text=noms_parametres[4])
label.place(x=400, y=250)
# Menu déroulant pour la commande
menu2 = ctk.CTkOptionMenu(frame_page4, 
                         values=type_waypoint)
menu2.set("ajouter une commande") # Texte par défaut
menu2.place(x=500, y=250)

# Bouton de validation
btn_valider = ctk.CTkButton(frame_page4, text="Valider le Waypoint", command=create_waypoint)
btn_valider.place(x=400, y=300)
btn_check_mission = ctk.CTkButton(frame_page4, text="Vérifier la mission", command=lambda: check_mission_interface(mission))
btn_check_mission.place(x=400, y=350)
scroll_waypoint = ctk.CTkScrollableFrame(frame_page4, height=600,width=scroll_width)
scroll_waypoint.place(x=10, y=10)



# Gestion de la page de configuration

frame_page3 = ctk.CTkFrame(app)
label3 = ctk.CTkLabel(frame_page3, text="Configuration du véhicule", font=("Arial", 20), text_color="orange")
label3.pack(pady=20)    
frame3_btn_retour = ctk.CTkButton(frame_page3, text="Retour", command=lambda: afficher_page(frame_page3,frame_page1), fg_color="gray")
frame3_btn_retour.pack(pady=10)
switch_arm = ctk.CTkSwitch(frame_page3, text="NOT ARMED", command=armement)
switch_arm.pack(pady=40, padx=20)

# Dans la section PID de frame_page3 
axe_var = ctk.StringVar(value="Roll")
menu_pid = ctk.CTkOptionMenu(frame_page3, 
                             values=["Roll", "Pitch", "Yaw"], 
                             variable=axe_var,
                             command=charger_pid_actuels)
menu_pid.pack(pady=10)

frame_inputs = ctk.CTkFrame(frame_page3, fg_color="transparent")
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

label_status = ctk.CTkLabel(frame_page3, text="Sélectionnez un axe pour charger les données", font=("Arial", 11))
label_status.pack()

btn_save = ctk.CTkButton(frame_page3, text="Appliquer les changements", command=sauvegarder_pid, fg_color="green")
btn_save.pack(pady=10)

## Gestion de la page de lancement de la mission 

frame_page5 = ctk.CTkFrame(app)
label5 = ctk.CTkLabel(frame_page5, text="Lancement de la Mission", font=("Arial", 20), text_color="orange")
label5.pack(pady=20)
btn_retour5 = ctk.CTkButton(frame_page5, text="Retour", command=lambda: afficher_page(frame_page5, frame_page1), fg_color="gray")
btn_retour5.pack(pady=10)

btn_lancer_mission = ctk.CTkButton(frame_page5, text="Lancer la Mission", command=lancer_mission)
btn_lancer_mission.pack(pady=40)

frame1_btn_mission = ctk.CTkButton(frame_page1, text="Lancement Mission", 
                                   command=lambda: afficher_page(frame_page1, frame_page5), 
                                   corner_radius=10)
frame1_btn_mission.pack(pady=10)

## creation du terminal a l'intérieur 
terminal = ctk.CTkTextbox(frame_page5, width=700, height=400, corner_radius=5)
terminal.pack(pady=20)
terminal.configure(state="disabled")

app.mainloop()
