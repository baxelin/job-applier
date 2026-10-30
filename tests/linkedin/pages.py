"""HTML de exemplo imitando as páginas do LinkedIn (logado) usadas nos testes."""


def job_page(
    title: str = "Desenvolvedor Python Júnior",
    company: str = "Empresa X",
    top_card: str = "São Paulo, SP · há 2 dias · 37 candidaturas",
    description: str = "<p>Buscamos pessoa com <strong>Python</strong> e Docker.</p><ul><li>Git</li></ul>",
    apply_button: str = '<button class="jobs-apply-button" aria-label="Candidatura simplificada à vaga">'
    "Candidatura simplificada</button>",
    extra: str = "",
) -> str:
    return f"""
    <html><body>
      <header>LinkedIn Início Vagas</header>
      <div class="job-details-jobs-unified-top-card__container--two-pane">
        <div class="job-details-jobs-unified-top-card__company-name"><a href="/company/x/">{company}</a></div>
        <div class="job-details-jobs-unified-top-card__job-title"><h1>{title}</h1></div>
        <div class="job-details-jobs-unified-top-card__tertiary-description-container">{top_card}</div>
        {apply_button}
      </div>
      <article class="jobs-description__container">
        <div id="job-details"><h2>Sobre a vaga</h2>{description}</div>
      </article>
      {extra}
    </body></html>
    """


def search_page(*job_ids: str) -> str:
    cards = "".join(
        f'<li data-occludable-job-id="{job_id}"><div class="job-card-container" data-job-id="{job_id}">'
        f'<a href="/jobs/view/{job_id}/?refId=abc">Vaga {job_id}</a></div></li>'
        for job_id in job_ids
    )
    return f'<html><body><div class="jobs-search-results-list"><ul>{cards}</ul></div></body></html>'
