# FinanceEasy

Aplicativo web de gestão financeira para a persona **"O Equilibrista
Sobrecarregado"** — pessoas endividadas, ansiosas com dinheiro e que
precisam, antes de tudo, parar de pagar juros de atraso e enxergar
quanto sobra com segurança até o fim do mês.

Stack: **Python + Django (MTV)**, front-end em **HTML/CSS/JavaScript +
Bootstrap 5**, banco de dados **SQLite**, integração com a **API HG
Brasil Finance** (cotações na tela inicial) e com a **Hugging Face
Inference API** (classificação automática de despesas importadas).

## 1. Pré-requisitos

- Python 3.10 ou superior
- pip

## 2. Instalação

```bash
# Dentro da pasta do projeto (FinanceEasy/)
python -m venv venv

# Windows (PowerShell)
venv\Scripts\Activate.ps1
# Windows (cmd)
venv\Scripts\activate.bat
# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt
```

Copie o arquivo de exemplo de variáveis de ambiente:

```bash
copy .env.example .env      # Windows
cp .env.example .env         # Linux/Mac
```

Abra o `.env` e, se quiser, preencha as chaves das APIs (veja a seção 5
— o app funciona normalmente sem elas, só fica sem cotações de mercado
e sem categorização por IA).

## 3. Banco de dados

```bash
python manage.py migrate
```

Isso já cria as categorias padrão (Alimentação, Transporte, Moradia,
Dívidas/Empréstimos, etc. — RF04 a RF10).

Crie um usuário administrador (opcional, só para acessar `/admin/`):

```bash
python manage.py createsuperuser
```

## 4. Rodando o servidor

```bash
python manage.py runserver
```

Acesse http://127.0.0.1:8000/ — você será redirecionado para o login.
Clique em "Criar conta" para se cadastrar (UC01).

## 5. Configurando as APIs externas (opcional, mas recomendado)

### HG Brasil Finance (cotações no painel — UC08)

1. Crie uma conta gratuita em https://hgbrasil.com/
2. Gere sua chave de API (plano free: 400 requisições/dia)
3. Cole a chave em `HGBRASIL_API_KEY` no `.env`

Sem a chave, o bloco "Mercado agora" do painel mostra um aviso
explicando como configurá-la — o resto do app funciona normalmente.

### Hugging Face (categorização automática de extratos — UC04/UC05)

1. Crie uma conta gratuita em https://huggingface.co/
2. Gere um token em https://huggingface.co/settings/tokens (permissão
   de leitura é suficiente)
3. Cole o token em `HUGGINGFACE_API_TOKEN` no `.env`

Sem o token, a importação de extrato ainda funciona: as transações
reconhecidas por palavra-chave (IFOOD, NETFLIX, POSTO, SABESP, etc.)
são categorizadas normalmente; o restante cai em "Outros" com o
marcador amarelo "Qual é esta despesa?" para você reclassificar em um
clique na tela de conciliação (UC05).

## 6. Varredura diária de vencimentos (UC14)

O app já dispara os avisos preventivos (D+5, D+2, D=0) automaticamente
no primeiro acesso do dia de cada usuário. Para reproduzir fielmente o
caso de uso ("roda todo dia às 08h00", mesmo sem ninguém abrir o app),
agende o management command no seu sistema operacional:

```bash
python manage.py varredura_vencimentos
```

- **Windows:** Agendador de Tarefas → Criar Tarefa Básica → Diariamente
  às 08:00 → Ação: iniciar o programa `venv\Scripts\python.exe` com o
  argumento `manage.py varredura_vencimentos` e "Iniciar em" a pasta do
  projeto.
- **Linux/Mac:** `crontab -e` e adicione:
  `0 8 * * * cd /caminho/do/projeto && venv/bin/python manage.py varredura_vencimentos`

## 7. Teste de fumaça

Um script percorre o fluxo completo da persona (cadastro, login,
receita/despesa manual, limite de categoria, assinatura, importação de
extrato CSV com conciliação, dívida com pagamento de parcela, meta com
microvalor, filtros do extrato e a varredura de vencimentos) usando o
test client do Django, sem precisar abrir navegador:

```bash
python smoke_test.py
```

## 8. Estrutura do projeto

```
financeeasy/      # settings, urls raiz
accounts/         # UC01 — cadastro, login, recuperação de senha (usuário customizado, login por e-mail)
transactions/     # UC02–UC09 — receitas, despesas, importação de extrato, conciliação, assinaturas, extrato
  services/
    import_parser.py   # leitura de OFX/CSV/PDF
    categorizer.py      # regras + Hugging Face para sugerir categoria
debts/            # UC10–UC11 — dívidas, cartões, parcelamentos
goals/            # UC12 — reserva de segurança com microvalores
dashboard/        # UC08 — painel principal (Sobra Segura, HG Brasil, modo privacidade)
core/             # infraestrutura compartilhada
  services/
    due_date_scan.py    # UC14 — varredura diária de vencimentos
    budget_alerts.py    # UC06 — alerta de 80% do limite por categoria
  management/commands/varredura_vencimentos.py
templates/        # HTML (Bootstrap 5, mobile-first)
static/           # CSS e JS próprios
```

## 9. Decisões de escopo

- **UC13** (dicas de consumo sem julgamento) foi removido do escopo por
  decisão do usuário durante o levantamento de requisitos.
- O faseamento sugerido no documento de requisitos original (RF16–18 e
  RNF13–18 como "fase avançada") foi **substituído pela priorização dos
  use cases e da persona**: dívidas, alertas de limite e o modo
  privacidade já fazem parte deste MVP, por serem o núcleo do problema
  da persona "Equilibrista Sobrecarregado".
- RF17 do documento de requisitos original ("Educação financeira") tem
  o mesmo texto de RF16 ("Controle de dívidas") — aparenta ser um erro
  de cópia na fonte. Ficou sinalizado, sem bloquear a implementação.

## 10. Próximos passos sugeridos (fora deste MVP)

- Autenticação social (login social foi citado no RF01/UC01, mas exige
  configurar provedores OAuth — Google, etc.)
- Envio real de e-mail (hoje o código OTP de recuperação de senha vai
  para o console do Django em desenvolvimento)
- Deploy em produção (Gunicorn/Nginx ou similar, `DEBUG=False`,
  `django-environ` para segredos, banco Postgres se o volume crescer)
- Parser de PDF mais robusto por banco (o atual é heurístico e pode não
  reconhecer o layout de todos os bancos)
