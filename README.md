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
| Gerar CVs a partir de arquivos `.txt` | `docker compose run --rm app python -m job_applier cv data/vagas` |
| Recriar a planilha a partir do banco | `docker compose run --rm app python -m job_applier planilha` |
| Rodar os testes | `docker compose run --rm app pytest` |

Com os comandos `login` e `buscar` em execução, o navegador pode ser acompanhado em <http://localhost:6080/vnc.html>. O login só precisa ser refeito quando a sessão do LinkedIn expirar.

A varredura respeita os intervalos de `config/config.json`, incluindo pausas longas, então pode levar vários minutos sem novas mensagens.

### Vagas externas

Vagas sem Candidatura Simplificada recebem o CV normalmente e entram na aba **Vagas** da planilha com o status `Pendente – aplicar manualmente`. Filtre por esse status e use a coluna **Link para aplicar** para abrir o site da empresa e **CV** para pegar o PDF daquela vaga. Se o link não tiver sido encontrado, a coluna **Link da vaga** leva ao anúncio no LinkedIn.

### Onde ficam os resultados

| Arquivo | Conteúdo |
| --- | --- |
| `data/job_applier.db` | Banco SQLite: a fonte da verdade das vagas processadas |
| `data/candidaturas.xlsx` | Relatório recriado a partir do banco a cada execução |
| `data/cvs/` | PDFs gerados para cada vaga |
| `data/debug/` | HTML e screenshots das páginas, para diagnóstico |

### Recomeçar do zero

As vagas já registradas no banco não são abertas de novo, e apagar só a planilha ou os PDFs não muda isso. Para processar tudo novamente, feche o Excel e apague os três:

```bat
del data\job_applier.db*
del data\candidaturas.xlsx
del data\cvs\*.pdf
```

Isso remove todo o histórico. O banco e a planilha são recriados na próxima execução.

### Sem Docker

```bat
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m playwright install firefox
.venv\Scripts\python -m pytest
.venv\Scripts\python -m job_applier
```

O WeasyPrint não roda no Windows, então os PDFs só são gerados no Docker e o teste de PDF é pulado localmente.
