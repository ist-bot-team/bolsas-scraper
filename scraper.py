import re
import requests
import json
import os
from bs4 import BeautifulSoup as bs
import sys
from time import sleep, time
import wget

PING_ROLE_ID = os.getenv("PING_ROLE_ID")

URL = "https://drh.tecnico.ulisboa.pt/bolseiros/recrutamento/"
AVATAR_URL = "https://cdn.discordapp.com/attachments/878358615117922345/913014188400582676/Purse.png"

# Both must end with /
DOWNLOAD_PATH = os.getenv("DOWNLOAD_PATH")
MIRROR_URL = os.getenv("MIRROR_PATH")
# Valid Discord webhook URL
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
# SENTRY_DSN = os.getenv("SENTRY_DSN")
WORKDIR = os.getenv("WORKDIR")

BOLSA_ID_PARSER = re.compile("^(BL[0-9]*)$")  # FIXME: broken, idk how to regex
DATE_PARSER = re.compile("[0-9]{2}\.[0-9]{2}\.[0-9]{4}")

# if SENTRY_DSN:
#     import sentry_sdk
#     sentry_sdk.init(SENTRY_DSN)

if not DOWNLOAD_PATH and MIRROR_URL and WEBHOOK_URL:
    raise ValueError("Missing required environment variables! Cannot continue.")

# import socket
# import requests.packages.urllib3.util.connection as urllib3_cn

# def allowed_gai_family():
#     family = socket.AF_INET    # force IPv4
#     return family

# urllib3_cn.allowed_gai_family = allowed_gai_family


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


with open(f"{WORKDIR}/link_editais.json", "r+") as f:
    link_editais = json.load(f)


def get_site_parser():
    r = requests.get(URL)
    r.raise_for_status()
    return bs(r.text, features="lxml")


def map_bolsas(soup):
    mapping = {
        "vagas": 0,
        "tipo_bolsa": 1,
        "responsavel": 2,
        "area": 3,
        "link_pt": 4,
        "link_en": 5,
        "data_abertura": 6,
        "data_limite": 7,
    }
    return mapping


def get_bolsas(soup, mapping):
    table = soup.find("table")
    bolsas = []
    skipped_headers = 0
    for row in table.find_all("tr"):
        # Discard first two rows: table headings and English/Portuguese heading.
        if skipped_headers < 2:
            skipped_headers += 1
            continue

        bolsa = Bolsa()
        items = row.find_all("td")
        # FIXME Remove debug
        # print(items)

        link_pt_a = items[mapping["link_pt"]].find("a")
        link_en_a = items[mapping["link_en"]].find("a")
        # Some bolsas are english only
        # I don't care bolsa.edital can be set twice
        if link_pt_a:
            bolsa.edital = link_pt_a.text.split(" ")[0]  # FIXME: Cursed, use regex
            bolsa.link_pt = link_pt_a.get("href")
        if link_en_a:
            bolsa.edital = link_en_a.text.split(" ")[0]  # FIXME: Cursed, use regex
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
        # Anunciar bolsa se link alterado
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
                "content": f"<@&{PING_ROLE_ID}>",
                "embeds": [
                    {
                        "title": "Nova Bolsa Publicada",
                        "url": bolsa.link_pt if bolsa.link_pt else bolsa.link_en,
                        "author": {"name": bolsa.responsavel, "icon_url": None},
                        "description": f"Bolsa {bolsa.edital}",
                        "color": None,
                        "fields": [
                            {
                                "name": "Vagas",
                                "value": f"{bolsa.vagas}",
                                "inline": True,
                            },
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
                                "value": f"[Link]({bolsa.link_pt}) | [Mirror]({link_mirror_pt})",
                            },
                            {
                                "name": "Edital (EN)",
                                "value": f"[Link]({bolsa.link_en}) | [Mirror]({link_mirror_en})",
                            },
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
                # This isn't a good way to do things
                # But I'm tired and have other things to do now
                try:
                    result = requests.post(WEBHOOK_URL, json=data)
                except Exception:
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
    with open(f"{WORKDIR}/link_editais.json", "w+") as f:
        json.dump(link_editais, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    main()

# Debugging
# os.environ['PYTHONINSPECT'] = 'TRUE'
