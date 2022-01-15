#!python3
import requests
#import re
from hashlib import sha1
import json
import os 
from bs4 import BeautifulSoup as bs
import sys
from time import sleep

URL = "https://drh.tecnico.ulisboa.pt/bolseiros/recrutamento/"

WEBHOOK_URL = os.getenv("WEBHOOK_URL")

AVATAR_URL = "https://cdn.discordapp.com/attachments/878358615117922345/913014188400582676/Purse.png"


with open("/opt/bolsas-scraper/link_editais.json", "r+") as f:
    link_editais = json.load(f)


def obter_bolsas():
    r = requests.get(URL)
    r.raise_for_status()
    bolsas = []
    header_skipped = False
    #This would be a lot shorter with lambdas
    for row in bs(r.text, "lxml")("tr"):
        bolsa = []
        #We don't care about table headers (first iteration), skip
        if not header_skipped:
            header_skipped = True
            continue

        for cell in row("td"):
            #Check if this cell is the one with the link
            edital = cell.find('a')
            if edital:
                id_bolsa = edital.text.split(" ")[0]
                link_bolsa = edital.attrs["href"]
#in the future save PDFs for archival
#                obter_edital(link_bolsa)
                bolsa.extend([id_bolsa, link_bolsa])
            else:
                bolsa.append(cell.text)

                
        bolsas.append(bolsa)
            

    return bolsas

def anunciar_bolsas():
    global link_editais
    for bolsa in obter_bolsas():
        #DRH being DRH...
        if len(bolsa) == 10:
            nr_vagas, tipo, prof_responsavel, id_bolsa, link_pt, _, link_en, area, data_abertura, data_fim = bolsa
        elif len(bolsa) == 9:
            nr_vagas, tipo, prof_responsavel, id_bolsa, link, _, area, data_abertura, data_fim = bolsa
        else:
            #DRH being DRH again...
            raise ValueError(f"Expected 9 or 10 arguments to unpack, received {len(bolsa)} \n bolsa = '{bolsa}'")


        icon_url = ""
        if "David Matos" in prof_responsavel:
            icon_url = "https://cdn.discordapp.com/emojis/849321790672207915.png?v=1"

        elif "Vasco Manquinho" in prof_responsavel:
            icon_url = "https://cdn.discordapp.com/emojis/833648912367353897.png?v=1"

        print("Found " + id_bolsa)
        if link_pt not in link_editais:

            print(f"Sending Webhook for {id_bolsa}")
            print(f"link_pt = '{link_pt}'")
            data = {
                "content": None,
                "embeds": [
                    {
                        "title": "Nova Bolsa Publicada",
                        "url": link_pt,
                        "author": {"name": prof_responsavel, "icon_url": icon_url},
                        "description": f"Bolsa {id_bolsa}",
                        "color": None,
                        "fields": [
                            {"name": "Vagas", "value": f"{nr_vagas}", "inline": True},
                            {
                                "name": "Tipo de Bolsa",
                                "value": f"{tipo}",
                                "inline": True,
                            },
                            {
                                "name": "Professor Responsável",
                                "value": f"{prof_responsavel}",
                            },
                            {"name": "Edital", "value": f"{link_pt}"},
                            {
                                "name": "Área/Projeto",
                                "value": f"{area}",
                                "inline": "true",
                            },
                            {
                                "name": "Data de Abertura",
                                "value": f"{data_abertura}",
                                "inline": "true",
                            },
                            {
                                "name": "Data Limite",
                                "value": f"{data_fim}",
                                "inline": "true",
                            },
                        ],
                    }
                ],
                "avatar_url": AVATAR_URL,
            }

            result = requests.post(WEBHOOK_URL, json=data)

            try:
                result.raise_for_status()
                print(
                "Payload delivered successfully, code {}".format(result.status_code)
                )
                sleep(2)

            except requests.exceptions.HTTPError as err:
                print(err)
                print("Retrying...")
                sleep(120)
                #This isn't a good way to do things
                #But I'm tired and have other things to do now
                try:
                    result = requests.post(WEBHOOK_URL, json=data)
                except:
                    sys.exit(1)
        
        link_editais.append(link_pt)
        

if __name__ == "__main__":
    anunciar_bolsas()
    with open("link_editais.json", "w+") as f:
        json.dump(link_editais, f, ensure_ascii=False, indent=4)
