import customtkinter as ctk
import tkinter as tk


from functions import nettoyage,close,connection_vehicle,lancement_sitl

number = 0
global dico
dico={}
def bouton_test():
    print("test")


def afficher_page2():
    frame_page1.pack_forget()
    frame_page2.pack(expand=True, fill="both")

def afficher_page1():
    frame_page2.pack_forget()
    frame_page1.pack(expand=True, fill="both")

def affichage_liste_maneuvres():
    colonnes, lignes = frame_page2.grid_size()
    print(f"La grille fait {colonnes} colonnes et {lignes} lignes.")
    for el in dico.keys():
        dico[el][1].grid(row=(el), column=0, sticky='w', pady=10)
        
def ajouter_maneuvre(choix):
    global number	
    dico[number] = [choix]
    item = ctk.CTkLabel(frame_page2, text=f" {number}:{dico[number][0]}", font=("Arial", 12), text_color="green")
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
                item = ctk.CTkLabel(frame_page2, text=f"aucune maneuvre sélectionnée", font=("Arial", 12), text_color="red")
                item.grid(row=2, column=1, pady=10)
        elif vari in dico.keys():
            #print(dico[vari])
            dico[vari][1].destroy()  # Supprimer le widget associé à la manœuvre
            del dico[vari]
            dico, number = indexage(dico)  # Réindexer le dictionnaire après suppression
            affichage_liste_maneuvres()  # Réafficher la liste des manœuvres
      except AssertionError as e:
        item = ctk.CTkLabel(frame_page2, text=str(e), font=("Arial", 12), text_color="red")
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


# 2. Création de la fenêtre principale
ctk.set_appearance_mode("dark")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Thèmes: "blue" (standard), "green", "dark-blue"
app = ctk.CTk()
app.geometry("800x800")
app.title("Psyn")




# --- INTERFACE 1 ---
frame_page1 = ctk.CTkFrame(app)
frame_page1.pack(expand=True, fill="both")

label1 = ctk.CTkLabel(frame_page1, text="MENU PRINCIPAL", font=("Arial", 20))
label1.pack(pady=20)


frame1_bouton1 = ctk.CTkButton(frame_page1, text="fermeture", command=nettoyage, corner_radius=10)
frame1_bouton2 = ctk.CTkButton(frame_page1, text="lancement SITL", command=lancement_sitl, corner_radius=10)
frame1_bouton3 = ctk.CTkButton(frame_page1, text="connection du vehicule", command=connection_vehicle, corner_radius=10)
frame1_bouton4 = ctk.CTkButton(frame_page1, text="Options ▼", command=bouton_test, corner_radius=10)
frame1_btn_maneuvre = ctk.CTkButton(frame_page1, text="Maneuvres", command=afficher_page2)



# 5. Placement des boutons sur la fenêtre
frame1_btn_maneuvre.pack(pady=10)
frame1_bouton1.pack(pady=10)
frame1_bouton2.pack(pady=10)
frame1_bouton3.pack(pady=10)
frame1_bouton4.pack(pady=10)


# Gestion de la page maneuvres

frame_page2 = ctk.CTkFrame(app)

label2 = ctk.CTkLabel(frame_page2, text="Maneuvres", font=("Arial", 20), text_color="orange")

label2.place(x=200, y=20)

frame2_btn_retour = ctk.CTkButton(frame_page2, text="Retour", command=afficher_page1, fg_color="gray")
frame2_btn_retour.place(x=400, y=20)

menu = ctk.CTkOptionMenu(frame_page2, 
                         values=["décollage", "Vol en palier stabilisé", "Accélération/décélération", "Virage à x °", "changement d'altitude", "atterrissage"],
                         command=ajouter_maneuvre)

menu.set("ajouter une maneuvre") # Texte par défaut
menu.place(x=400, y=50,)
entree = tk.Entry(frame_page2)
entree.place(x=400, y=80)
frame2_del_man = ctk.CTkButton(frame_page2, text="Supprimer", command=suppression_maneuvre, fg_color="red")
frame2_del_man.place(x=400, y=110)



# 5. Placement du bouton au centre de la fenêtre

app.mainloop()
