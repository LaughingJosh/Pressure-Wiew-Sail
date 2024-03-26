import serial
import numpy as np
import matplotlib.pyplot as plt
import threading
import time
import os
import datetime

plt.ion()

porta = '/dev/cu.usbmodem14201'
baud_rate = 19200
arduino = serial.Serial(porta, baud_rate)

num_sensori = 10
dati_sensori = [[] for _ in range(num_sensori)]
tempi = [[] for _ in range(num_sensori)]
dati_sensori_temp = [[] for _ in range(num_sensori)]
tempi_temp = [[] for _ in range(num_sensori)]

fig, axs = plt.subplots(2, 5, figsize=(15, 8))
axs = axs.ravel()

for i in range(num_sensori):
    axs[i].set_title('Sensore {}'.format(i+1))
    axs[i].set_xlabel('Tempo')
    axs[i].set_ylabel('Pressione')
    axs[i].set_xlim(0, 10)
    axs[i].set_ylim(-1, 0.3)
    axs[i].grid(True)

linee = [ax.plot([], [])[0] for ax in axs]

# Flag per indicare quando fermare i thread
in_esecuzione = True

# Get the user's desktop path
percorso_scrivania = os.path.join(os.path.expanduser('~'), 'Desktop')

# Crea una cartella per memorizzare i file di dati
cartella_dati = os.path.join(percorso_scrivania, 'ArduinoData')
if not os.path.exists(cartella_dati):
    os.makedirs(cartella_dati)

# Définition des variables globales pour le fichier
ultimo_tempo_scrittura_file = time.time()
indice_file_corrente = 1
dati_raccolti = []

def aggiorna_grafico():
    global in_esecuzione
    while in_esecuzione:
        for i in range(num_sensori):
            dati_sensori[i].extend(dati_sensori_temp[i])
            tempi[i].extend(tempi_temp[i])

            if dati_sensori_temp[i]:
                media_pressione = np.mean(dati_sensori_temp[i])
                ylim_min = media_pressione - 3
                ylim_max = media_pressione + 3
            else:
                ylim_min, ylim_max = -1, 0.3

            linee[i].set_data(tempi[i], dati_sensori[i])

            if tempi[i]:
                xlim_max = max(tempi[i])
                xlim_min = max(0, xlim_max - 10)
            else:
                xlim_min, xlim_max = 0, 10

            axs[i].set_xlim(xlim_min, xlim_max)
            axs[i].set_ylim(ylim_min, ylim_max)

        plt.draw()
        plt.pause(0.0001)

def leggi_arduino():
    global in_esecuzione
    try:
        while in_esecuzione and arduino.is_open:
            try:
                riga = arduino.readline().decode().strip()
                if riga:
                    valori = list(map(float, riga.split()))
                    sensore = int(valori[0]) - 1
                    pressioni = valori[1:11]
                    tempi_sensore = valori[11:]

                    dati_sensori_temp[sensore] = pressioni
                    tempi_temp[sensore] = tempi_sensore

                    # Scrivi i dati su un file di testo in parallelo
                    scrivi_su_file(riga)
            except serial.SerialException as e:
                if "Bad file descriptor" in str(e):
                    break
                else:
                    print("Errore nella lettura da Arduino:", e)
                    break
            except Exception as e:
                print("Errore nella lettura da Arduino:", e)
                break
    except Exception as e:
        print("Si è verificato un errore:", e)

def calcola_e_stampare_medie():
    global in_esecuzione
    try:
        while in_esecuzione:
            for i in range(num_sensori):
                print("-----------------")
                if dati_sensori_temp[i]:
                    media_pressione = np.mean(dati_sensori_temp[i])
                    print("Media della pressione per Sensore {}: {:.2f}".format(i+1, media_pressione))
            # Attendi un po' prima di ricalcolare le medie
            time.sleep(1)
            print("-------------------------------------------------------------------------")
    except Exception as e:
        print("Si è verificato un errore nel thread di calcolo e stampa delle medie:", e)

def scrivi_su_file(dati):
    global ultimo_tempo_scrittura_file, indice_file_corrente, dati_raccolti
    tempo_corrente = time.time()
    dati_raccolti.append(dati)
    
    # Verifica se sono trascorsi 100 secondi
    if tempo_corrente - ultimo_tempo_scrittura_file >= 100:
        # Crea il nome del file con l'indice
        nome_file_corrente = "dati_{}.txt".format(indice_file_corrente)
        percorso_file_corrente = os.path.join(cartella_dati, nome_file_corrente)
        
        # Scrivi i dati raccolti nel file
        with open(percorso_file_corrente, "a") as file:
            for elemento in dati_raccolti:
                file.write(elemento + '\n')
        
        # Reimposta i dati raccolti e aggiorna le variabili di tempo e indice del file
        dati_raccolti = []
        ultimo_tempo_scrittura_file = tempo_corrente
        indice_file_corrente += 1

thread_arduino = threading.Thread(target=leggi_arduino)
thread_arduino.start()

thread_medie = threading.Thread(target=calcola_e_stampare_medie)
thread_medie.start()

try:
    aggiorna_grafico()
except KeyboardInterrupt:
    print("Script interrotto...")
    in_esecuzione = False
    if arduino.is_open:
        arduino.close()
