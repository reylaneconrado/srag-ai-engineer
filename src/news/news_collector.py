import feedparser

FEEDS = {
    "geral_srag": "https://news.google.com/rss/search?q=sindrome+respiratoria+aguda+grave",
    "influenza": "https://news.google.com/rss/search?q=influenza+brasil",
    "covid": "https://news.google.com/rss/search?q=covid+brasil",
    "virus_respiratorios": "https://news.google.com/rss/search?q=virus+respiratorios+brasil",
    "vacinacao": "https://news.google.com/rss/search?q=vacinacao+influenza+brasil",
}


def buscar_noticias(max_por_feed: int = 3) -> list[dict]:
    """Busca notícias em tempo de execução via RSS.

    Cada item carrega uma tag de categoria para permitir correlacionar
    a notícia com a métrica correspondente no relatório (ex: notícias
    de 'vacinacao' ficam ao lado da taxa de vacinação).
    """
    noticias = []

    for categoria, feed_url in FEEDS.items():
        try:
            rss = feedparser.parse(feed_url)
        except Exception as exc:
            noticias.append({
                "categoria": categoria,
                "titulo": f"[Erro ao buscar feed: {exc}]",
                "link": None,
            })
            continue

        for item in rss.entries[:max_por_feed]:
            noticias.append({
                "categoria": categoria,
                "titulo": item.title,
                "link": item.link,
            })

    return noticias


if __name__ == "__main__":
    for noticia in buscar_noticias():
        print(f"[{noticia['categoria']}] {noticia['titulo']}")
