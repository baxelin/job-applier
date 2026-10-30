from dataclasses import dataclass


@dataclass(frozen=True)
class PageSnapshot:
    """Estado de uma página aberta no navegador: endereço final, HTML e texto visível."""

    url: str
    html: str
    text: str
