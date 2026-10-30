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


def current_job_page(
    job_id: str = "123",
    title: str = "Desenvolvedor Front-end Junior | Remoto",
    company: str = "Jungle Gaming",
    top_line: str = "Brasil · há 3 dias · Mais de 100 pessoas clicaram em Candidate-se",
    apply_label: str = "Candidatar-se no site da empresa",
) -> str:
    """Layout de 2026: classes embaralhadas; âncoras estáveis em <title>, aria-label e componentkey."""
    return f"""
    <html><head><title>(2) {title} | {company} | LinkedIn</title></head><body>
      <div class="b0alro b0aayf">
        <a class="b0ak8d" aria-label="Logo da empresa {company}." href="/company/x/life"></a>
        <a class="b0ak8d" aria-label="Empresa {company}." href="/company/x/life"><p>{company}</p></a>
        <p class="b0ak8d b0ak3r"><span>{title}</span></p>
        <p class="b0ak8d b0ak3b"><span>{top_line.replace(" · ", "</span> · <span>")}</span></p>
        <a class="b0alko" aria-label="{apply_label}" href="https://empresa.example/vaga">
          <span>Candidatar-se</span></a>
      </div>
      <div componentkey="JobDetails_AboutTheJob_{job_id}">
        <h2 class="b0ak8d">Sobre a vaga</h2>
        <span data-testid="expandable-text-box">
          <p>A {company} cria jogos. Procuramos pessoa com <strong>React</strong> e TypeScript.</p>
          <p>Requisitos:<br>Git</p>
          <span>…</span>
          <button data-testid="expandable-text-button">mais</button>
        </span>
      </div>
      <div componentkey="JobDetailsSimilarJobsSlot_{job_id}">
        <p><span>Outra vaga</span> · <span>há 1 dia</span> · <span>5 pessoas clicaram em Candidate-se</span></p>
      </div>
    </body></html>
    """


def search_page(*jobs: str | tuple[str, str, str]) -> str:
    """Página de busca; cada vaga é um id ou uma tupla (id, título, empresa)."""
    cards = []
    for job in jobs:
        job_id, title, company = job if isinstance(job, tuple) else (job, f"Vaga {job}", "Empresa Exemplo")
        cards.append(
            f'<li data-occludable-job-id="{job_id}"><div class="job-card-container" data-job-id="{job_id}">'
            f'<a href="/jobs/view/{job_id}/?refId=abc" aria-label="{title}">{title}</a>'
            f"<span>{company}</span><span>São Paulo, SP</span></div></li>"
        )
    return f'<html><body><div class="jobs-search-results-list"><ul>{"".join(cards)}</ul></div></body></html>'
