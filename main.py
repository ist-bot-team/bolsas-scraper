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

with open("link_editais.json", "r+") as f:
    link_editais = json.load(f)


def obter_bolsas_old():
    r = requests.get(URL)

    results = re.findall(regex_1, r.text.split("<tbody")[1])

    results = map(lambda x: re.findall(regex_2, x), results)
    results = map(lambda x: list(map(lambda y: y.strip(), x)), results)
    results = map(
        lambda x: [*x[0:3], re.search(regex_url, x[3]).group(1), *x[4:]], results
    )

    return list(results)


def obter_bolsas():
    r = requests.get(URL)
    r.raise_for_status()
    bolsas = []
    header_skipped = False
    #This would be a lot shorter with lambdas
    for row in bs(r.text, "lxml")("tr"):
        #bolsa = [id_bolsa, link_bolsa, n_vagas, tipo, prof_responsavel, area, data_abertura, data_fim]
        bolsa = []
        #We don't care about table headers (first iteration), skip
        if not header_skipped:
            header_skipped = True
            continue

        for cell in row("td"):
            #Check if this cell is the one with the link
            edital = cell.find('a')
            if edital:
#Think about doing this check in the future
#                #Cada bolsa apenas tem um link/anchor
#                if len(edital) != 1:
#                    raise ValueError
#                edital = edital[0]
                id_bolsa = edital.text.split(" ")[0]
                link_bolsa = edital.attrs["href"]
#in the future save PDFs for archival
#                obter_edital(link_bolsa)
                bolsa.extend([id_bolsa, link_bolsa])
            else:
                bolsa.append(cell.text)

                
        bolsas.append(bolsa)
            
#            print(cell.find('a'))

    return bolsas
#results = [[cell.text for cell in row("td")] for row in bs(r.text)("tr")]
#
#    print(results[1:])
#    print(len(results[1:]))
#    return results[1:]
#    sys.exit()


#def anunciar_bolsas():
#    global link-editais
#    for bolsa in bolsas: 
#        nr_vagas, tipo, prof_responsavel, link, area, data_abertura, data_fim = bolsa
#    id_bolsa =  
    

def anunciar_bolsas():
    global link_editais
    for bolsa in obter_bolsas():
        nr_vagas, tipo, prof_responsavel, id_bolsa, link, area, data_abertura, data_fim = bolsa
#        id_bolsa = int(link.split("45/bl")[1].split("-")[0])

        #if not ("iniciação" in tipo.lower()):
        #    continue

        icon_url = ""
        if "David Matos" in prof_responsavel:
            icon_url = "https://cdn.discordapp.com/emojis/849321790672207915.png?v=1"

        elif "Vasco Manquinho" in prof_responsavel:
            icon_url = "https://cdn.discordapp.com/emojis/833648912367353897.png?v=1"

        print(id_bolsa)
        if link not in link_editais:
            data = {
                "content": None,
                "embeds": [
                    {
                        "title": "Nova Bolsa Publicada",
                        "url": link,
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
                            {"name": "Edital", "value": f"{link}"},
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
                try:
                    result = requests.post(WEBHOOK_URL, json=data)
                except:
                    sys.exit(1)
        
        link_editais.append(link)
        

if __name__ == "__main__":
    anunciar_bolsas()
    with open("link_editais.json", "w+") as f:
        json.dump(link_editais, f, ensure_ascii=False, indent=4)
