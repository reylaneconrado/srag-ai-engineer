import feedparser

def buscar_noticias():

    feeds = [

    "https://news.google.com/rss/search?q=sindrome+respiratoria+aguda+grave",

    "https://news.google.com/rss/search?q=influenza+brasil",

    "https://news.google.com/rss/search?q=covid+brasil",

    "https://news.google.com/rss/search?q=virus+respiratorios+brasil"

]

    noticias = []

    for feed in feeds:

        rss = feedparser.parse(feed)

        for item in rss.entries[:3]:

            noticias.append({

                "titulo": item.title,

                "link": item.link

            })

    return noticias


if __name__ == "__main__":

    resultado = buscar_noticias()

    for noticia in resultado:

        print(noticia["titulo"])