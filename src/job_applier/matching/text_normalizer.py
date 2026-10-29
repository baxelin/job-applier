import unicodedata


class TextNormalizer:
    """Deixa textos comparáveis: minúsculas e sem acentos ("Integração" -> "integracao")."""

    @staticmethod
    def normalize(text: str) -> str:
        decomposed = unicodedata.normalize("NFKD", text.casefold())
        return "".join(character for character in decomposed if not unicodedata.combining(character))
