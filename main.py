#!python3
import requests
import re
import json
import os 
url = "https://drh.tecnico.ulisboa.pt/bolseiros/recrutamento/"

webhook_url = os.getenv("WEBHOOK_URL")


regex_1 = re.compile("<tr .+?>([\s\S]+?)<\/tr>")

regex_2 = re.compile("<td .+?>([\s\S]+?)<\/td>")

regex_url = re.compile('<a href="(.+?)"')

with open("link_editais.json", "r+") as f:
    link_editais = json.load(f)


def obter_bolsas():
    r = requests.get(url)

    results = re.findall(regex_1, r.text.split("<tbody")[1])

    results = map(lambda x: re.findall(regex_2, x), results)
    results = map(lambda x: list(map(lambda y: y.strip(), x)), results)
    results = map(
        lambda x: [*x[0:3], re.search(regex_url, x[3]).group(1), *x[4:]], results
    )

    return list(results)


def anunciar_bolsas():
    global link_editais
    for bolsa in obter_bolsas():
        nr_vagas, tipo, prof_responsavel, link, area, data_abertura, data_fim = bolsa
        id_bolsa = int(link.split("45/bl")[1].split("-")[0])

        #if not ("iniciação" in tipo.lower()):
        #    continue

        avatar_url = "https://www.thebridge.it/media/catalog/product/cache/0/main/2000x2000/9df78eab33525d08d6e5fb8d27136e95/0/1/01308801_14_1_base.png"
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
                        "description": f"Bolsa BL{id_bolsa}",
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
                "avatar_url": avatar_url,
            }

            result = requests.post(webhook_url, json=data)

            try:
                result.raise_for_status()

            except requests.exceptions.HTTPError as err:
                print(err)
            else:
                print(
                    "Payload delivered successfully, code {}".format(result.status_code)
                )
        
        link_editais.append(link)
        



anunciar_bolsas()
#print(link_editais)

with open("link_editais.json", "w+") as f:
    json.dump(link_editais, f, ensure_ascii=False, indent=4)
