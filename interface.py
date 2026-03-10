import customtkinter as ctk
import tkinter as tk


from functions import nettoyage,close,connection_vehicle2,lancement_sitl,armed

number = 0
dico={}
arm=False
master = None
def bouton_test():
    print("test")

def afficher_page1(page):
    page.pack_forget()
    frame_page1.pack(expand=True, fill="both")

def afficher_page2(page):
    page.pack_forget()
    page_maneuvres.pack(expand=True, fill="both")

def afficher_page3(page):
    page.pack_forget()
    frame_page3.pack(expand=True, fill="both")

def affichage_liste_maneuvres():
    colonnes, lignes = page_maneuvres.grid_size()
    print(f"La grille fait {colonnes} colonnes et {lignes} lignes.")
    for el in dico.keys():
        dico[el][1].grid(row=(el), column=0, sticky='w', pady=10)
        
def ajouter_maneuvre(choix):
    global number	
    dico[number] = [choix]
    item = ctk.CTkLabel(page_maneuvres, text=f" {number}:{dico[number][0]}", font=("Arial", 12), text_color="green")
    dico[number].append(item)
    affichage_liste_maneuvres()
    number += 1

def suppression_maneuvre():
      global dico
      global number
      try:
        assert entree.get().isdigit(), "Veuillez entrer un nombre entier valide."
        assert int(entree.get()) in dico.keys(), "Aucune manœuvre correspondante à ce numéro."
        vari = int(entree.get())
        if vari=="":
                item = ctk.CTkLabel(page_maneuvres, text=f"aucune maneuvre sélectionnée", font=("Arial", 12), text_color="red")
                item.grid(row=2, column=1, pady=10)
        elif vari in dico.keys():
            #print(dico[vari])
            dico[vari][1].destroy()  # Supprimer le widget associé à la manœuvre
            del dico[vari]
            dico, number = indexage(dico)  # Réindexer le dictionnaire après suppression
            affichage_liste_maneuvres()  # Réafficher la liste des manœuvres
      except AssertionError as e:
        item = ctk.CTkLabel(page_maneuvres, text=str(e), font=("Arial", 12), text_color="red")
        item.grid(row=2, column=1, pady=10)
        app.after(3000, item.destroy)  # Supprimer le message d'erreur après 3 secondes
    
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
    # .get() renvoie 1 si coché, 0 sinon
    if switch_arm.get() == 1:
        switch_arm.configure(text="ARMED", progress_color="green")
        arm=True
        armed(master,arm)
        
    else:
        switch_arm.configure(text="NOT ARMED", progress_color="red")
        arm=False
        armed(master,arm)
        

def connection_vehicle():
    global master
    master = connection_vehicle2()



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
frame1_bouton1 = ctk.CTkButton(frame_page1, text="fermeture", command=nettoyage, corner_radius=10)
frame1_bouton2 = ctk.CTkButton(frame_page1, text="lancement SITL", command=lancement_sitl, corner_radius=10)
frame1_bouton3 = ctk.CTkButton(frame_page1, text="connection du vehicule", command=connection_vehicle, corner_radius=10)
frame1_bouton4 = ctk.CTkButton(frame_page1, text="Config véhicule", command=lambda: afficher_page3(frame_page1), corner_radius=10)
frame1_btn_maneuvre = ctk.CTkButton(frame_page1, text="Maneuvres", command=lambda: afficher_page2(frame_page1))

# Placement des boutons sur la fenêtre
frame1_btn_maneuvre.pack(pady=10)
frame1_bouton1.pack(pady=10)
frame1_bouton2.pack(pady=10)
frame1_bouton3.pack(pady=10)
frame1_bouton4.pack(pady=10)


# Gestion de la page maneuvres
page_maneuvres = ctk.CTkFrame(app)
label2 = ctk.CTkLabel(page_maneuvres, text="Maneuvres", font=("Arial", 20), text_color="orange")
label2.place(x=200, y=20)

# Bouton de retour à la page principale
frame2_btn_retour = ctk.CTkButton(page_maneuvres, text="Retour", command=lambda: afficher_page1(page_maneuvres), fg_color="gray")
frame2_btn_retour.place(x=400, y=20)

# Affichage de la liste des maneuvres
menu = ctk.CTkOptionMenu(page_maneuvres, 
                         values=["décollage", "Vol en palier stabilisé", "Accélération/décélération", "Virage à x °", "changement d'altitude", "atterrissage"],
                         command=ajouter_maneuvre)
menu.set("ajouter une maneuvre") # Texte par défaut
menu.place(x=400, y=50,)
entree = tk.Entry(page_maneuvres)
entree.place(x=400, y=80)
frame2_del_man = ctk.CTkButton(page_maneuvres, text="Supprimer", command=suppression_maneuvre, fg_color="red")
frame2_del_man.place(x=400, y=110)


# Gestion de la page de configuration

frame_page3 = ctk.CTkFrame(app)
label3 = ctk.CTkLabel(frame_page3, text="Configuration du véhicule", font=("Arial", 20), text_color="orange")
label3.pack(pady=20)    
frame3_btn_retour = ctk.CTkButton(frame_page3, text="Retour", command=lambda: afficher_page1(frame_page3), fg_color="gray")
frame3_btn_retour.pack(pady=10)
switch_arm = ctk.CTkSwitch(frame_page3, text="NOT ARMED", command=armement)
switch_arm.pack(pady=40, padx=20)

app.mainloop()