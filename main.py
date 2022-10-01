#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python310Packages.requests python310Packages.beautifulsoup4 python310Packages.sentry-sdk python310Packages.wget
import re
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

BOLSA_ID_PARSER = re.compile('^(BL[0-9]*)$') #FIXME: broken, idk how to regex
DATE_PARSER = re.compile('[0-9]{2}\.[0-9]{2}\.[0-9]{4}')

if SENTRY_DSN:
    import sentry_sdk
    sentry_sdk.init(SENTRY_DSN)

if not DOWNLOAD_PATH and MIRROR_URL and WEBHOOK_URL:
    raise ValueError("Missing required environment variables! Cannot continue.")

class Bolsa:
    edital = None
    vagas = -1
    tipo_bolsa = None
    responsavel = None
    area = None
    link_pt = None
    link_en = None
    data_abertura = None
    data_limite = None
    
    # def __init__(selfl):
    #     self.edital = edital

with open("./link_editais.json", "r+") as f:
    link_editais = json.load(f)

def get_site_parser():
    r = requests.get(URL)
    r.raise_for_status()
    return bs(r.text, features="lxml")


def map_bolsas(soup):
    tables = soup.find_all('table')
    if len(tables) != 1:
        raise ValueError(f'parse_bolsas: Wanted to find 1 table while scraping but found {len(tables)}')
    table = tables[0]

    bolsas = []
    bolsas_raw = table.find_all('tr')
    # Attempt to extract info from first row (table headers are unpredictable. Thanks DRH)
    guinea = None
    for bolsa_raw in bolsas_raw:
        # Find a bolsa with 2 links - english and portuguese PDFs
        if len(bolsa_raw.find_all('a')) == 2:
            guinea = bolsa_raw
            break
    # Otherwise default to first one and pray for the best
    if not guinea:
        guinea = bolsas_raw[1]

    guinea_items = guinea.find_all('td')
    #Create a mapping between info and column id
    mapping_ids = [i for i in range(0, len(guinea_items))]
    mapping = {
        "vagas": -1, #DONE
        "tipo_bolsa": -1, #DONE
        "responsavel": -1, #DONE
        "area": -1,
        "link_pt": -1, #DONE
        "link_en": -1, #DONE
        "data_abertura": -1, #DONE
        "data_limite": -1
    }
    i = 0
    for item in guinea_items:

        txt = item.text.lower()
        #Find links for PDFs - may not exist in current iter!
        link = item.find('a')

        #Attempt to find nº de vagas, Python way(tm)
        try:
            int(txt)
            mapping["vagas"] = i
            mapping_ids.remove(i)
        except ValueError:
            pass # Just keep trying

        #Get column with person responsible
        if "prof" in txt or "dr" in txt:
            mapping["responsavel"] = i
            mapping_ids.remove(i)
        elif "investigação" in txt:
            mapping["tipo_bolsa"] = i
            mapping_ids.remove(i)
        elif link:
            if "en" in link.get('href'):
                #Found link for English PDF
                mapping["link_en"] = i
                mapping_ids.remove(i)
            else:
                #Found link for Portuguese PDF
                mapping["link_pt"] = i
                mapping_ids.remove(i)
        #Current item is a DRH date
        elif re.fullmatch(DATE_PARSER, list(item.stripped_strings)[0]):
            #Assuming DRH has some sanity left and begin date comes before end date because I have better things to do
            if mapping["data_abertura"] == -1:
                mapping["data_abertura"] = i
            else:
                mapping["data_limite"] = i
            mapping_ids.remove(i)
        i += 1
    if len(mapping_ids) > 1:
        print("DEBUG: mapping \n ----------------")
        print(mapping)
        print("-----------------")
        print("DEBUG: guinea \n ----------------")
        print(guinea)
        print("-----------------")
        raise ValueError("Failed to map some values!")
    mapping["area"] = mapping_ids[0]

    return mapping


def get_bolsas(soup, mapping):
    table = soup.find('table')
    bolsas = []
    skipped_header = False
    for row in table.find_all('tr'):
        #Discard row if there are table headers there
        if len(row.find_all('th')) != 0:
            skipped_header = True
            continue
        if not skipped_header:
            skipped_header = True
            continue
        
        bolsa = Bolsa()
        items = row.find_all('td')

        link_pt_a = items[mapping["link_pt"]].find('a')
        link_en_a = items[mapping["link_en"]].find('a')
        #Some bolsas are english only
        # I don't care bolsa.edital can be set twice
        if link_pt_a:
            bolsa.edital = link_pt_a.text.split(" ")[0] #FIXME: Cursed, use regex
            bolsa.link_pt = link_pt_a.get("href")
        if link_en_a:
            bolsa.edital = link_en_a.text.split(" ")[0] #FIXME: Cursed, use regex
            bolsa.link_en = link_en_a.get("href")
        # print(f"link_pt_a = '{link_pt_a}'")
        print(f"Got edital '{bolsa.edital}'")
        bolsa.vagas = int(items[mapping["vagas"]].text)
        bolsa.tipo_bolsa = items[mapping["tipo_bolsa"]].text
        bolsa.responsavel = items[mapping["responsavel"]].text
        bolsa.area = items[mapping["area"]].text
        bolsa.data_abertura = items[mapping["data_abertura"]].text
        bolsa.data_limite = items[mapping["data_limite"]].text

        bolsas.append(bolsa)
    return bolsas


def anunciar_bolsas(bolsas):
    global link_editais
    for bolsa in bolsas:
        #Anunciar bolsa se link alterado
        # if (bolsa.link_pt not in link_editais) or (bolsa.link_en not in link_editais):
        if bolsa.link_pt in link_editais:
            print(f"{bolsa.link_pt} for {bolsa.edital} already present - skipping")
            continue
        elif bolsa.link_en in link_editais:
            print(f"{bolsa.link_en} for {bolsa.edital} already present - skipping")
        else:
            print(f"A anunciar bolsa '{bolsa.edital}'")
            link_mirror_pt = None
            link_mirror_en = None
            if bolsa.link_pt:
                filename_pt = f"{bolsa.edital}_pt_{time()}.pdf"
                wget.download(bolsa.link_pt, DOWNLOAD_PATH + filename_pt)
                print(f"\nDownloaded '{filename_pt}'")
                link_mirror_pt = MIRROR_URL + filename_pt
            if bolsa.link_en:
                filename_en = f"{bolsa.edital}_en{time()}.pdf"
                wget.download(bolsa.link_en, DOWNLOAD_PATH + filename_en)
                print(f"\nDownloaded '{filename_en}'")
                link_mirror_en = MIRROR_URL + filename_en

            data = {
                "content": None,
                "embeds": [
                    {
                        "title": "Nova Bolsa Publicada",
                        "url": bolsa.link_pt if bolsa.link_pt else bolsa.link_en,
                        "author": {"name": bolsa.responsavel, "icon_url": None},
                        "description": f"Bolsa {bolsa.edital}",
                        "color": None,
                        "fields": [
                            {"name": "Vagas", "value": f"{bolsa.vagas}", "inline": True},
                            {
                                "name": "Tipo de Bolsa",
                                "value": f"{bolsa.tipo_bolsa}",
                                "inline": "true",
                            },
                            {
                                "name": "Professor Responsável",
                                "value": f"{bolsa.responsavel}",
                            },
                            {
                                "name": "Edital (PT)",
                                "value": f"[Link]({bolsa.link_pt}) | [Mirror]({link_mirror_pt})"},
                            {
                                "name": "Edital (EN)",
                                "value": f"[Link]({bolsa.link_en}) | [Mirror]({link_mirror_en})"},
                            {
                                "name": "Área/Projeto",
                                "value": f"{bolsa.area}",
                                "inline": "true",
                            },

                            {
                                "name": "Data de Abertura",
                                "value": f"{bolsa.data_abertura}",
                                "inline": "true",
                            },
                            {
                                "name": "Data Limite",
                                "value": f"{bolsa.data_limite}",
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

        if bolsa.link_pt:
            link_editais.append(bolsa.link_pt)
        if bolsa.link_en:
            link_editais.append(bolsa.link_en)

def main():
    soup = get_site_parser()
    mapping = map_bolsas(soup)
    bolsas = get_bolsas(soup, mapping)
    anunciar_bolsas(bolsas)
    with open("link_editais.json", "w+") as f:
        json.dump(link_editais, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    main()

# Debugging
# os.environ['PYTHONINSPECT'] = 'TRUE'

