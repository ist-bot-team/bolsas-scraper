#!/usr/bin/env python3
from re import I
import requests
import json
import os 
from bs4 import BeautifulSoup as bs
import sys
from time import sleep, time
import wget


URL = "https://drh.tecnico.ulisboa.pt/bolseiros/recrutamento/"
AVATAR_URL = "https://cdn.discordapp.com/attachments/878358615117922345/913014188400582676/Purse.png"

#Both must end with /
DOWNLOAD_PATH = os.getenv("DOWNLOAD_PATH")
MIRROR_URL = os.getenv("MIRROR_PATH")
#Valid Discord webhook URL
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
SENTRY_DSN = os.getenv("SENTRY_DSN")

if SENTRY_DSN:
    import sentry_sdk
    sentry_sdk.init(SENTRY_DSN)

if not DOWNLOAD_PATH and MIRROR_URL and WEBHOOK_URL:
    raise ValueError("Missing required environment variables! Cannot continue.")

with open("./link_editais.json", "r+") as f:
    link_editais = json.load(f)

def get_site_parser():
    r = requests.get(URL)
    r.raise_for_status()
    return bs(r.text)


def parse_bolsas(soup):
    tables = soup.find_all('table')
    if len(tables) != 1:
        raise ValueError(f'Wanted to find 1 table while scraping but found {len(tables)}')
    table = tables[0]

    #Get table rows
    bolsas = []
    for row in table.find_all('tr'):
        bolsa = []
        #Discard row if there are table headers there
        if len(row.find_all('th')) != 0:
            continue
        cells = row.find_all('td')
        if not (7 <= len(cells) and len(cells) <= 8):
            raise ValueError("Expecting 7 or 8 cells to parse, found " + len(cells))
        for cell in cells:
            #Parse these later
            if len(cell.find_all('a')) != 0:
                continue
            #If no string, don't add anything
            if cell.string:
                bolsa.append(cell.string)

        bolsa_links = row.find_all('a')

        #Assuming two links = portuguese and english  edital.
        #I pray they don't remember to do these in Spanish next, I have better things to do
        link_drh_pt = bolsa_links[0].attrs["href"]
        id_bolsa = bolsa_links[0].text.split(" ")[0]
        bolsa.append(id_bolsa)

        bolsa.append(link_drh_pt)
        if len(bolsa_links) == 2:
            link_drh_en = bolsa_links[1].attrs["href"]
            bolsa.append(link_drh_en)

        elif not len(bolsa_links) == 1:
            raise ValueError("Expected 1 or 2 edital links, found " + len(bolsa_links))
        
        bolsas.append(bolsa)
    return bolsas

def anunciar_bolsas(bolsas):
    global link_editais
    for bolsa in bolsas:
        link_drh_en, link_mirror_en = None, None
        #DRH being DRH...
        print(f"\nDEBUG : bolsa = '{bolsa}'\n")
        if len(bolsa) == 9:
            nr_vagas, tipo, prof_responsavel, area, data_abertura, data_fim, id_bolsa, link_drh_pt, link_drh_en = bolsa
        elif len(bolsa) == 8:
            nr_vagas, tipo, prof_responsavel, area, data_abertura, data_fim, id_bolsa, link_drh_pt = bolsa
        else:
            #DRH being DRH again...
            raise ValueError(f"Expected 9 or 10 arguments to unpack, received {len(bolsa)} \n bolsa = '{bolsa}'")

        icon_url = ""
        if "David Matos" in prof_responsavel:
            icon_url = "https://cdn.discordapp.com/emojis/849321790672207915.png?v=1"

        elif "Vasco Manquinho" in prof_responsavel:
            icon_url = "https://cdn.discordapp.com/emojis/833648912367353897.png?v=1"

        print("-" * 10)
        print("Found bolsa " + id_bolsa)

        if link_drh_pt not in link_editais:
            print(f"link_pt = '{link_drh_pt}'")
            print(f"link_en = '{link_drh_en}'")
            #----------
            #Download PDFs
            filename_pt = f"{id_bolsa}_pt_{time()}.pdf"
            wget.download(link_drh_pt, DOWNLOAD_PATH + filename_pt)
            print(f"\nDownloaded '{filename_pt}'")
            link_mirror_pt = MIRROR_URL + filename_pt

    
            if link_drh_en:
                print(link_drh_en)
                filename_en = f"{id_bolsa}_en_{time()}.pdf"
                wget.download(link_drh_en, DOWNLOAD_PATH + filename_en)
                print(f"\nDownloaded '{filename_en}'")
                link_mirror_en = MIRROR_URL + filename_en
            
            print(f"Sending Webhook for {id_bolsa}")

            data = {
                "content": None,
                "embeds": [
                    {
                        "title": "Nova Bolsa Publicada",
                        "url": link_drh_pt,
                        "author": {"name": prof_responsavel, "icon_url": icon_url},
                        "description": f"Bolsa {id_bolsa}",
                        "color": None,
                        "fields": [
                            {"name": "Vagas", "value": f"{nr_vagas}", "inline": True},
                            {
                                "name": "Tipo de Bolsa",
                                "value": f"{tipo}",
                                "inline": "true",
                            },
                            {
                                "name": "Professor Responsável",
                                "value": f"{prof_responsavel}",
                            },
                            {
                                "name": "Edital (PT)",
                                "value": f"[Link]({link_drh_pt}) | [Mirror]({link_mirror_pt})"},
                            {
                                "name": "Edital (EN)",
                                "value": f"[Link]({link_drh_en}) | [Mirror]({link_mirror_en})"},
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
        
        link_editais.append(link_drh_pt)
        
def main():
    soup = get_site_parser()
    bolsas = parse_bolsas(soup)
    anunciar_bolsas(bolsas)
    with open("link_editais.json", "w+") as f:
        json.dump(link_editais, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    main()
   
