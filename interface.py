import customtkinter as ctk
import tkinter as tk

from backend import pre_verification,check_mission, waypoint
from functions import nettoyage,connection_vehicle2,lancement_sitl,armed,set_param

num_maneuvres = 0
num_waypoints = 0
dico={}
arm=False
master = None
mission = []
dic_mission = {}
scroll_width = 300


def afficher_page(page,frame):
    page.pack_forget()
    frame.pack(expand=True, fill="both")

def affichage_liste_maneuvres():
    for el in dico.keys():
        dico[el][1].grid(row=(el), column=0, sticky='w', pady=10)

def affichage_liste(dic):
    for el in dic.keys():
        dic[el][1].grid(row=(el), column=0, sticky='w', pady=10)

def create_waypoint():
    global num_waypoints,mission,dic_mission
    try:
        print(liste_entries)
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
        num_waypoints = ajouter_waypoint_dico(mission[-1],dic_mission,num_waypoints,scroll_waypoint)
    except AssertionError as e:
        item = ctk.CTkLabel(frame_page4, text=str(e), font=("Arial", 12), text_color="red")
        item.place(x=400, y=300)
        app.after(3000, item.destroy)  # Supprimer le message d'erreur

def ajouter_waypoint_dico(val,dic,num,page):
    dic[num]=[val]
    item = ctk.CTkLabel(page, text=f" {num}:{dic[num][0]}", font=("Arial", 12), text_color="green",cursor="hand2",wraplength=scroll_width-10,justify="left")
    item.bind("<Button-1>",suppression_waypoint)  # Lier le clic à la fonction de suppression
    dic[num].append(item)
    affichage_liste(dic)
    num+=1
    return num

def suppression_waypoint(event):
    global dic_mission, num_waypoints, mission
    widget = event.widget
    num = int(widget.cget("text").split(":")[0].strip())  # Extraire le numéro du waypoint à supprimer
    dic_mission[num][1].destroy()  # Supprimer le widget associé au waypoint
    del dic_mission[num]  # Supprimer l'entrée du dictionnaire
    del mission[num]  # Supprimer le waypoint de la mission
    dic_mission, num_waypoints = indexage(dic_mission)  # Réindexer le dictionnaire après suppression
    affichage_liste(dic_mission)  # Réafficher la liste des waypoints

def ajouter_maneuvre(choix):
    global num_maneuvres	
    dico[num_maneuvres] = [choix]
    item = ctk.CTkLabel(scroll_maneuvre, text=f" {num_maneuvres}:{dico[num_maneuvres][0]}", font=("Arial", 12), text_color="green", cursor="hand2",wraplength=scroll_width-10,justify="left")
    item.bind("<Button-1>",suppression_maneuvre)  # Lier le clic à la fonction de suppression
    dico[num_maneuvres].append(item)
    affichage_liste_maneuvres()
    num_maneuvres += 1

def suppression_maneuvre(event):
    global dico, num_maneuvres
    widget = event.widget
    num = int(widget.cget("text").split(":")[0].strip())  # Extraire le numéro de la manœuvre à supprimer
    dico[num][1].destroy()  # Supprimer le widget associé à la manœuvre
    del dico[num]
    dico, num_maneuvres = indexage(dico)  # Réindexer le dictionnaire après suppression
    affichage_liste_maneuvres()  # Réafficher la liste des manœuvres

def indexage(dico):
    dico_bis={}
    tmp=0
    for el in dico:
        dico_bis[tmp]=dico[el]
        dico_bis[tmp][1].configure(text=f" {tmp}:{dico[el][0]}") # Mise à jour du texte du widget avec le nouveau numéro
        tmp+=1
    return dico_bis,tmp

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
    
    # On essaie de récupérer les 3 paramètres
    try:
        # Note : master doit être global ou accessible ici
        p = master.param_fetch_one(f"{prefix}_RATE_P")
        i = master.param_fetch_one(f"{prefix}_RATE_I")
        d = master.param_fetch_one(f"{prefix}_RATE_D")
        
        # Mise à jour des champs de saisie
        entry_p.delete(0, tk.END)
        entry_p.insert(0, str(round(p, 4)))
        
        entry_i.delete(0, tk.END)
        entry_i.insert(0, str(round(i, 4)))
        
        entry_d.delete(0, tk.END)
        entry_d.insert(0, str(round(d, 4)))
        
        label_status.configure(text=f"Valeurs {axe_nom} chargées", text_color="green")
    except:
        label_status.configure(text="Erreur de lecture drone", text_color="red")

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

# Bouton de retour à la page principale
frame2_btn_retour = ctk.CTkButton(page_maneuvres, text="Retour", command=lambda: afficher_page(page_maneuvres,frame_page1), fg_color="gray")
frame2_btn_retour.place(x=400, y=20)

# Affichage de la liste des maneuvres
menu1 = ctk.CTkOptionMenu(page_maneuvres, 
                         values=["décollage", "Vol en palier stabilisé", "Accélération/décélération", "Virage à x °", "changement d'altitude", "atterrissage"],
                         command=ajouter_maneuvre)
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
                         values=["WAYPOINT", "TAKEOFF", "LAND", "RTL", "LOITER", "GUIDED"])
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


app.mainloop()
