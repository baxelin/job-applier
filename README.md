# job-applier

Programa em Python para varrer vagas do LinkedIn e gerar um currículo adaptado a cada uma.

## Comandos úteis

Os comandos abaixo rodam na raiz do projeto, no Prompt de Comando do Windows, com o Docker Desktop aberto.

### Primeira execução

```bat
copy personal\cv_base.example.json personal\cv_base.json
copy personal\respostas.example.json personal\respostas.json
docker compose build
docker compose run --rm app
```

O último comando verifica o navegador e valida os dados base. Depois de copiar os exemplos, preencha `personal/cv_base.json` e `personal/respostas.json` com os seus dados.

Rode `docker compose build` de novo sempre que o código mudar, porque o código fica dentro da imagem. Alterações em `config/`, `personal/` e `data/` não precisam disso.

### Dia a dia

| Para quê | Comando |
| --- | --- |
| Entrar no LinkedIn manualmente | `docker compose run --rm --service-ports app python -m job_applier login` |
| Varrer as vagas e gerar os CVs | `docker compose run --rm --service-ports app python -m job_applier buscar` |
| Varrer abrindo no máximo N vagas | `docker compose run --rm --service-ports app python -m job_applier buscar --max-vagas 7` |
| Ensaiar as candidaturas sem enviar (padrão: até 20 vagas novas) | `docker compose run --rm --service-ports app python -m job_applier ensaiar --max-vagas 20` |
| Ensaiar e repetir as vagas pendentes de pergunta ou com erro | `docker compose run --rm --service-ports app python -m job_applier ensaiar --repetir-pendentes` |
| **Enviar** as candidaturas simplificadas | `docker compose run --rm --service-ports app python -m job_applier aplicar` |
| Enviar abrindo no máximo N vagas | `docker compose run --rm --service-ports app python -m job_applier aplicar --max-vagas 5` |
| Enviar e repetir as vagas pendentes de pergunta (depois de cadastrar respostas) | `docker compose run --rm --service-ports app python -m job_applier aplicar --repetir-pendentes` |
| **Buscar e enviar** na mesma execução | `docker compose run --rm --service-ports app python -m job_applier buscar-e-aplicar` |
| Buscar e enviar abrindo no máximo N vagas | `docker compose run --rm --service-ports app python -m job_applier buscar-e-aplicar --max-vagas 10` |
| Gerar CVs a partir de arquivos `.txt` | `docker compose run --rm app python -m job_applier cv data/vagas` |
| Recriar a planilha a partir do banco | `docker compose run --rm app python -m job_applier planilha` |
| Rodar os testes | `docker compose run --rm app pytest` |

Com os comandos `login`, `buscar`, `ensaiar`, `aplicar` e `buscar-e-aplicar` em execução, o navegador pode ser acompanhado em <http://localhost:6080/vnc.html>. O login só precisa ser refeito quando a sessão do LinkedIn expirar.

Cada execução também grava o que está fazendo em `data/logs/AAAA-MM-DD.log` ("Abrindo vaga…", "Próxima vaga em 45 s"). Deixe o arquivo aberto no VS Code para acompanhar: se passar alguns minutos sem linha nova, algo travou.

### Vagas externas

Vagas sem Candidatura Simplificada recebem o CV normalmente e entram na aba **Vagas** da planilha com o status `Pendente – aplicar manualmente`. Filtre por esse status e use a coluna **Link para aplicar** para abrir o site da empresa e **CV** para pegar o PDF daquela vaga. Se o link não tiver sido encontrado, a coluna **Link da vaga** leva ao anúncio no LinkedIn.

### Ensaio das candidaturas

O comando `ensaiar` abre cada vaga com Candidatura Simplificada, preenche o formulário, carrega o CV daquela vaga e descarta tudo ao chegar na tela do botão de enviar. **Nada é enviado.**

| Status na planilha | O que significa | O que fazer |
| --- | --- | --- |
| `Ensaio OK` | O formulário foi preenchido até a tela final | Conferir os prints em `data/ensaios/` |
| `Pendente – pergunta sem resposta` | Há pergunta obrigatória sem resposta segura | Responder em `personal/respostas.json`, a partir da aba **Perguntas** |
| `Erro` | O formulário não se comportou como o esperado | Ver a coluna **Observação** e a página salva em `data/debug/` |

Cada vaga ensaiada ganha uma pasta em `data/ensaios/`, com um print por tela e um `respostas.txt` com o que foi preenchido e o que ficou sem resposta. Por padrão só entram vagas novas; com `--repetir-pendentes`, as pendentes e as com erro são tentadas de novo depois delas.

### Envio das candidaturas

O comando `aplicar` faz o mesmo percurso do ensaio e, na tela final, clica em **Enviar candidatura**. Entram primeiro as vagas que passaram no ensaio, depois as novas, por aderência. Não há limite diário, a não ser que `daily_submission_limit` seja definido no `config.json` (contado pela data do envio). Use `--max-vagas` para enviar poucas de cada vez.

- Pergunta sem resposta segura: a candidatura não é enviada e a vaga fica pendente, como no ensaio.
- Cada envio deixa prints, o `respostas.txt` e o print da confirmação em `data/envios/`, e a vaga fica como `Candidatura enviada`.
- Se o LinkedIn não mostrar a confirmação depois do clique, a execução para e a vaga fica com erro: confira no site antes de tentar de novo, para não enviar a mesma candidatura duas vezes.

O comando `buscar-e-aplicar` junta os dois passos: a busca abre cada vaga, gera o CV e, se for Candidatura Simplificada, envia na hora, antes de passar para a próxima. Vagas externas, ignoradas e pendentes de pergunta ficam registradas como na busca comum. O `--max-vagas` conta as vagas abertas pela busca. Vagas que já estavam na fila de execuções anteriores continuam com o `aplicar`.

### Onde ficam os resultados

| Arquivo | Conteúdo |
| --- | --- |
| `data/job_applier.db` | Banco SQLite: a fonte da verdade das vagas processadas |
| `data/candidaturas.xlsx` | Relatório recriado a partir do banco a cada execução |
| `data/cvs/` | PDFs gerados para cada vaga |
| `data/ensaios/` | Prints e respostas de cada formulário ensaiado |
| `data/debug/` | HTML e screenshots das páginas, para diagnóstico |

### Recomeçar do zero

As vagas já registradas no banco não são abertas de novo, e apagar só a planilha ou os PDFs não muda isso. Para começar do zero, feche o Excel e apague o banco, a planilha, os CVs e as evidências:

```bat
del data\job_applier.db*
del data\candidaturas.xlsx
del data\cvs\*.pdf
rmdir /s /q data\ensaios data\envios data\debug data\logs
```

Isso remove todo o histórico, inclusive o registro das candidaturas já enviadas: depois disso, o robô pode tentar de novo vagas em que você já se candidatou (o LinkedIn não mostra mais o botão e a vaga é ignorada). O login do LinkedIn (volume `browser-profile`) e os seus dados em `personal/` continuam como estão.

### Sem Docker

```bat
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m playwright install firefox
.venv\Scripts\python -m pytest
.venv\Scripts\python -m job_applier
```

O WeasyPrint não roda no Windows, então os PDFs só são gerados no Docker e o teste de PDF é pulado localmente.

## Roadmap

- [x] **Fase 0 – Preparação:** repositório, estrutura de pastas, Docker com Playwright (Firefox).
- [x] **Fase 1 – Dados base:** CV bilíngue com tags, glossário de termos, respostas e configuração validados com Pydantic.
- [x] **Fase 2 – Gerador de CV:** extração de termos, pontuação, aderência e PDF adaptado a cada vaga.
- [x] **Fase 3 – Registro local:** PDFs em `data/cvs/`, SQLite como fonte da verdade e planilha Excel recriada a cada execução.
- [x] **Fase 4 – Varredura do LinkedIn (só leitura):** login manual, buscas com filtros, extração das vagas, ritmo e parada em bloqueio.
- [x] **Fase 5 – Vagas externas:** link de candidatura no site da empresa, CV gerado e status "Pendente – aplicar manualmente".
- [ ] **Fase 6 – Candidatura automática:** entrega = candidaturas enviadas sozinhas, com tudo registrado.
  - [x] Abrir o modal da Candidatura Simplificada e mapear as etapas (contato, currículo, perguntas, revisão).
  - [x] Upload do PDF gerado.
  - [x] Respondedor por tipo de campo (texto, número, lista, opção única, caixa de seleção).
  - [x] Pergunta desconhecida: fecha sem enviar, salva a pergunta e marca a vaga como pendente.
  - [x] Modo de ensaio que preenche tudo e para antes do "Enviar", com prints.
  - [ ] Ensaio em ~20 vagas e revisão dos prints.
  - [x] Envio real (comando `aplicar`).
  - [x] Primeiros envios no site: confirmação reconhecida ("Status da candidatura · Candidatura enviada").
  - [x] Busca e envio na mesma execução (comando `buscar-e-aplicar`).
- [ ] **Fase 7 – Operação:** entrega = projeto rodando sozinho, só com manutenção semanal.
  - [ ] Agendar a execução em horários variados (cron no host ou agendador no container).
  - [ ] Relatório simples: aplicadas no dia, pendentes e perguntas novas para criar regra.
  - [ ] Rotina semanal: revisar perguntas desconhecidas, termos não reconhecidos e respostas de empresas na planilha.
  - [ ] README de operação: como subir, refazer o login e adicionar regras.
