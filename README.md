# FinanceEasy

Aplicativo web de gestão financeira pessoal desenvolvido com **Python e Django**, voltado especialmente para pessoas que precisam organizar suas contas, controlar dívidas, acompanhar objetivos financeiros e entender quanto dinheiro podem utilizar com segurança.

O projeto tem como persona principal o **“Equilibrista Sobrecarregado”**: uma pessoa que enfrenta dificuldades para organizar as finanças, está preocupada com vencimentos e juros por atraso e precisa de informações claras para tomar decisões financeiras melhores.

O FinanceEasy prioriza a organização financeira sem julgamentos, a prevenção de atrasos e a visualização de uma sobra financeira mais segura.

**Repositório:** https://github.com/guilhermefs02-ux/FinanceEasy

**Hospedagem:** Render

**Banco de dados de produção:** Neon PostgreSQL

**Modelo de desenvolvimento:** Django MTV (Model, Template, View)

---

## 1. Tecnologias utilizadas

- **Python** — linguagem principal.
- **Django 5.2** — framework web utilizado na aplicação.
- **HTML5, CSS3 e JavaScript** — estrutura, estilos e interatividade.
- **Bootstrap 5** — componentes e interface responsiva.
- **PostgreSQL** — banco de dados utilizado em produção.
- **Neon** — serviço de banco de dados PostgreSQL utilizado pelo ambiente de produção.
- **Render** — hospedagem e execução da aplicação.
- **GitHub** — repositório do código-fonte e controle de versões.
- **HG Brasil Finance API** — integração utilizada para informações financeiras e cotações.
- **SQLite** — pode ser utilizado no ambiente local conforme a configuração do projeto.

### Arquitetura de publicação

O fluxo atual do FinanceEasy é:

```text
GitHub
   ↓
Render
   ↓
Django
   ↓
Neon PostgreSQL
```

O **GitHub** mantém o código-fonte.

O **Render** executa e publica a aplicação Django.

O **Neon** armazena os dados persistentes da aplicação em produção.

As informações sensíveis, como senha do banco, chaves de API e outras credenciais, devem permanecer nas variáveis de ambiente e **nunca devem ser publicadas no GitHub**.

---

# 2. Funcionalidades implementadas

## 2.1. Cadastro e autenticação

O módulo `accounts` é responsável pelo gerenciamento dos usuários.

Funcionalidades:

- Cadastro de usuário.
- Login.
- Logout.
- Recuperação de senha por código.
- Perfil do usuário.
- Dados complementares do usuário.
- Controle de usuário ativo.
- Usuário administrador do Django.
- Proteção das páginas para usuários autenticados.

O usuário utiliza o **e-mail como identificador de acesso**, conforme a implementação atual do modelo personalizado de usuário.

---

## 2.2. Painel financeiro

O painel principal é o centro de acompanhamento financeiro do usuário.

Funcionalidades implementadas:

- Saudação personalizada.
- Seleção da competência mensal.
- Navegação entre meses.
- Seleção de ano.
- Total de receitas da competência.
- Total de despesas realizadas.
- Saldo disponível acumulado.
- Detalhamento das receitas.
- Detalhamento das despesas.
- Despesas agrupadas por categoria.
- Visualização das principais categorias de despesas.
- **Sobra Segura**.
- Central de Avisos.
- Acompanhamento de objetivos financeiros.
- Total acumulado nos objetivos.
- Progresso individual dos objetivos.
- Modo de privacidade.

### Sobra Segura

A Sobra Segura foi criada para responder uma pergunta importante:

> Quanto dinheiro realmente posso considerar disponível depois de levar em conta os compromissos próximos?

O cálculo considera o saldo disponível e os compromissos financeiros previstos para os próximos dias.

O objetivo é evitar que o usuário considere como disponível um dinheiro que já será necessário para pagar uma conta ou parcela.

Quando o resultado é negativo, o painel apresenta um alerta visual indicando que as obrigações previstas superam o saldo disponível.

---

## 2.3. Central de Avisos

A aplicação possui uma **Central de Avisos** destinada ao acompanhamento de compromissos financeiros.

Ela apresenta:

- Contas recorrentes vencidas.
- Contas recorrentes próximas do vencimento.
- Parcelas de dívidas pendentes.
- Quantidade total de pendências.
- Quantidade de vencimentos atrasados.
- Quantidade de vencimentos nos próximos 7 dias.
- Data de vencimento.
- Valor da obrigação.
- Categoria da conta quando disponível.
- Identificação do tipo de compromisso.

As contas recorrentes podem ser marcadas como **pagas diretamente pela Central de Avisos** quando existe um pagamento correspondente.

A Central de Avisos também possui uma página própria, permitindo consultar os avisos sem sobrecarregar o painel principal.

---

## 2.4. Contas recorrentes

O módulo de transações possui suporte para contas recorrentes.

As contas podem possuir:

- Nome do serviço.
- Valor.
- Periodicidade.
- Dia de vencimento.
- Categoria.
- Usuário responsável.
- Situação ativa/inativa.
- Mês específico de vencimento quando aplicável.

Periodicidades utilizadas pelo sistema incluem:

- Mensal.
- Anual.

O sistema também trabalha com os registros de pagamento associados às contas recorrentes.

### Pagamento de contas

Uma conta recorrente pode gerar um registro de pagamento.

O sistema permite acompanhar se determinado compromisso foi pago ou permanece pendente.

Ao marcar uma conta como paga, o fluxo existente utiliza o registro de pagamento correspondente, preservando a relação entre a conta recorrente e seu pagamento.

---

## 2.5. Receitas

O FinanceEasy permite registrar receitas manualmente.

Cada lançamento pode conter informações como:

- Data.
- Descrição.
- Valor.
- Categoria.
- Usuário.

As receitas confirmadas são utilizadas nos indicadores financeiros do painel.

Também podem ser consultadas posteriormente no extrato.

---

## 2.6. Despesas

O sistema permite registrar despesas manualmente.

As despesas podem possuir:

- Data.
- Descrição.
- Valor.
- Categoria.
- Usuário.
- Informações relacionadas à recorrência quando aplicável.

As despesas confirmadas são utilizadas nos cálculos do painel e nos relatórios por categoria.

---

## 2.7. Categorias

O módulo `transactions` possui um sistema próprio de categorias.

As categorias podem possuir:

- Nome.
- Ícone.
- Cor.
- Usuário associado quando aplicável.

O projeto possui categorias padrão utilizadas para organizar as movimentações financeiras.

Também existe suporte a categorias relacionadas a despesas e dívidas.

---

## 2.8. Orçamentos por categoria

O FinanceEasy possui suporte a **limites de orçamento por categoria**.

O usuário pode definir um limite para determinada categoria e acompanhar sua utilização.

O projeto também possui uma rotina de alertas de orçamento localizada em:

```text
core/services/budget_alerts.py
```

A finalidade é identificar situações em que o usuário está se aproximando do limite definido para determinada categoria.

---

## 2.9. Importação de extratos

O sistema possui uma área específica para importação de extratos.

Localização:

```text
transactions/services/import_parser.py
```

A estrutura atual contempla processamento de:

- OFX.
- CSV.
- PDF.

Após a importação, as transações podem passar pelo processo de conciliação antes de serem definitivamente utilizadas no controle financeiro.

### Conciliação

A tela de conciliação permite revisar as transações importadas e confirmar as informações antes de incorporá-las ao controle financeiro.

Esse fluxo é importante para evitar que uma importação bancária gere lançamentos incorretos ou duplicados.

---

## 2.10. Categorização de despesas importadas

O projeto possui um serviço específico para categorização:

```text
transactions/services/categorizer.py
```

A categorização pode utilizar regras baseadas nas informações da própria transação para identificar despesas conhecidas.

Exemplos de estabelecimentos ou termos reconhecíveis podem ser associados automaticamente às respectivas categorias.

Quando uma transação não é reconhecida, ela pode permanecer disponível para classificação/revisão pelo usuário.

### Observação sobre IA externa

A integração com a **Hugging Face Inference API** fazia parte de uma versão anterior do projeto.

Ela **não deve ser considerada uma dependência obrigatória do FinanceEasy atual**.

A categorização local por regras deve permanecer como mecanismo principal para evitar que o funcionamento básico da importação dependa de uma API externa com limites, créditos ou cobrança.

Caso uma nova solução de inteligência artificial seja adicionada futuramente, ela deverá ser tratada como uma integração opcional e não poderá comprometer o funcionamento básico do sistema.

---

## 2.11. Dívidas

O módulo `debts` é responsável pelo controle de dívidas.

Funcionalidades:

- Cadastro de dívidas.
- Controle de valor.
- Parcelamento.
- Controle de parcelas.
- Registro de pagamentos.
- Acompanhamento das parcelas pendentes.
- Visualização da fatura quando aplicável.
- Controle de cartões e parcelamentos conforme a implementação disponível.

Arquivos principais:

```text
debts/models.py
debts/forms.py
debts/views.py
debts/services/credit_card.py
```

---

## 2.12. Objetivos financeiros

O módulo `goals` é responsável pelo gerenciamento dos objetivos financeiros.

O sistema permite criar objetivos para representar valores que o usuário deseja acumular.

Exemplos:

- Reserva de emergência.
- Colchão financeiro.
- Viagem.
- Terreno.
- Compra de um bem.
- Outros objetivos pessoais.

Funcionalidades:

- Criação de objetivos.
- Edição.
- Acompanhamento do valor acumulado.
- Definição de valor-alvo.
- Cálculo do percentual concluído.
- Visualização do valor restante.
- Registro de contribuições.
- Registro de retiradas.
- Histórico.
- Arquivamento de objetivos concluídos.
- Reserva/colchão de segurança.

### Colchão financeiro

O projeto possui tratamento específico para o objetivo padrão de reserva de segurança.

Quando um objetivo é concluído, ele pode permanecer disponível por determinado período antes de ser arquivado, conforme a lógica implementada no sistema.

O histórico das contribuições e retiradas deve ser preservado.

---

## 2.13. Modo de privacidade

O FinanceEasy possui um modo de privacidade para ocultar valores financeiros apresentados na interface.

Quando ativado, valores sensíveis podem ser substituídos visualmente por caracteres de ocultação.

O objetivo é permitir que o usuário utilize o sistema em locais públicos sem deixar valores financeiros expostos na tela.

Novos componentes que apresentem informações financeiras devem respeitar essa regra.

---

## 2.14. Extrato

O sistema possui uma área de extrato para consulta dos lançamentos.

Funcionalidades disponíveis incluem:

- Visualização das transações.
- Filtros.
- Consulta de receitas.
- Consulta de despesas.
- Categorias.
- Datas.
- Informações dos lançamentos.
- Consulta de lançamentos futuros conforme o módulo correspondente.

---

## 2.15. Recorrências

O projeto possui recursos relacionados ao gerenciamento de lançamentos recorrentes.

Arquivos relacionados:

```text
transactions/services/recurrency.py
transactions/services/recurring_bills.py
```

O sistema trabalha com contas recorrentes e seus pagamentos, permitindo separar o compromisso previsto do pagamento efetivamente realizado.

---

## 2.16. Assinaturas

O módulo de transações possui uma tela específica para acompanhamento de assinaturas:

```text
templates/transactions/assinaturas.html
```

Esse recurso permite organizar compromissos recorrentes relacionados a serviços e assinaturas.

---

## 2.17. Comparativo financeiro

O projeto possui uma tela de comparativo financeiro:

```text
templates/transactions/comparativo.html
```

O objetivo é permitir a análise das movimentações financeiras em diferentes períodos.

---

# 3. Estrutura do projeto

```text
FinanceEasy/
│
├── accounts/
│   ├── models.py
│   ├── forms.py
│   ├── views.py
│   ├── urls.py
│   └── migrations/
│
├── core/
│   ├── models.py
│   ├── views.py
│   ├── middleware.py
│   ├── context_processors.py
│   ├── services/
│   │   ├── budget_alerts.py
│   │   └── due_date_scan.py
│   └── management/
│       └── commands/
│           └── varredura_vencimentos.py
│
├── dashboard/
│   ├── views.py
│   ├── urls.py
│   └── services/
│       └── hgbrasil.py
│
├── debts/
│   ├── models.py
│   ├── forms.py
│   ├── views.py
│   ├── urls.py
│   └── services/
│       └── credit_card.py
│
├── goals/
│   ├── models.py
│   ├── forms.py
│   ├── views.py
│   ├── urls.py
│   └── migrations/
│
├── transactions/
│   ├── models.py
│   ├── forms.py
│   ├── views.py
│   ├── urls.py
│   ├── services/
│   │   ├── categorizer.py
│   │   ├── import_parser.py
│   │   ├── recurrency.py
│   │   └── recurring_bills.py
│   └── migrations/
│
├── financeeasy/
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
├── templates/
├── static/
│
├── manage.py
├── requirements.txt
├── smoke_test.py
├── ENDPOINTS.md
├── .env.example
└── README.md
```

---

# 4. Banco de dados

O ambiente de produção utiliza **PostgreSQL hospedado no Neon**.

Entre as tabelas atualmente existentes estão:

```text
accounts_passwordresetcode
accounts_user
accounts_user_groups
accounts_user_user_permissions

auth_group
auth_group_permissions
auth_permission

core_notification

debts_debt
debts_debtpayment

django_admin_log
django_content_type
django_migrations
django_session

goals_goal
goals_goalcontribution
goals_goalwithdrawal

transactions_category
transactions_categorybudget
transactions_importbatch
transactions_recurringbill
transactions_recurringbillpayment
transactions_transaction
```

As tabelas são criadas e atualizadas pelas migrações do Django.

### Regra importante

O banco de produção do Neon contém dados reais da aplicação.

**Não apagar, recriar ou limpar o banco de produção para corrigir problemas de desenvolvimento.**

Alterações estruturais devem ser realizadas por meio de migrações do Django:

```bash
python manage.py makemigrations
python manage.py migrate
```

Antes de executar migrações em produção, é recomendável verificar o código, o histórico de migrações e o estado atual do banco.

---

# 5. Configuração local

## 5.1. Pré-requisitos

Recomenda-se:

- Python 3.13.
- pip.
- Git.
- Visual Studio Code ou outro editor.
- Acesso ao repositório GitHub.

O projeto possui dependências específicas no `requirements.txt`.

---

## 5.2. Clonar o projeto

```bash
git clone https://github.com/guilhermefs02-ux/FinanceEasy.git
cd FinanceEasy
```

---

## 5.3. Criar ambiente virtual

```bash
py -3.13 -m venv .venv
```

No Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Caso o PowerShell bloqueie a execução:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Depois confirme:

```powershell
python --version
```

O Python utilizado pelo ambiente virtual deve ser compatível com as dependências do projeto.

---

## 5.4. Instalar dependências

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

---

## 5.5. Configurar `.env`

Copie o arquivo:

```text
.env.example
```

para:

```text
.env
```

No PowerShell:

```powershell
Copy-Item .env.example .env
```

O `.env` deve conter somente configurações necessárias ao ambiente.

**Nunca publique o `.env` no GitHub.**

---

# 6. Banco de dados local e produção

Em produção, a aplicação utiliza o PostgreSQL do **Neon**.

O Django recebe as informações de conexão por variáveis de ambiente.

No desenvolvimento local, a configuração pode utilizar o banco definido em `settings.py`.

Para aplicar as migrações:

```bash
python manage.py migrate
```

Para criar um administrador:

```bash
python manage.py createsuperuser
```

---

# 7. Executar localmente

Com o ambiente virtual ativado:

```bash
python manage.py runserver
```

A aplicação ficará disponível em:

```text
http://127.0.0.1:8000/
```

---

# 8. GitHub, Render e Neon

O ambiente atual do FinanceEasy utiliza três serviços principais.

### GitHub

Responsável pelo:

- Código-fonte.
- Histórico de alterações.
- Commits.
- Controle de versões.
- Compartilhamento do projeto com colaboradores.

Repositório:

https://github.com/guilhermefs02-ux/FinanceEasy

### Render

Responsável pela:

- Hospedagem da aplicação.
- Execução do Django.
- Deploy das alterações enviadas ao GitHub.
- Disponibilização da aplicação na internet.

### Neon

Responsável pelo:

- Banco de dados PostgreSQL.
- Armazenamento persistente dos usuários.
- Receitas.
- Despesas.
- Contas recorrentes.
- Pagamentos.
- Dívidas.
- Parcelas.
- Categorias.
- Orçamentos.
- Objetivos.
- Contribuições.
- Retiradas.
- Demais dados persistentes da aplicação.

### Fluxo de atualização

O fluxo utilizado atualmente é:

```text
Alteração no código
       ↓
GitHub
       ↓
Commit
       ↓
Render
       ↓
Deploy
       ↓
FinanceEasy atualizado
       ↓
Neon PostgreSQL
```

Uma alteração no código não apaga automaticamente os dados existentes no Neon.

Da mesma forma, uma alteração de HTML/CSS não deve exigir alteração do banco de dados.

---

# 9. Deploy no Render

Quando uma alteração estiver pronta:

1. Salvar os arquivos.
2. Enviar a alteração para o GitHub.
3. Confirmar o commit.
4. Aguardar o Render iniciar o deploy.
5. Verificar os logs do deploy.
6. Confirmar que o serviço iniciou corretamente.
7. Testar a funcionalidade alterada.

### Atenção

Não é recomendado alterar variáveis de ambiente ou configurações do banco de produção sem verificar primeiro a configuração atual do Render.

Não publicar:

- Senhas.
- Tokens.
- Chaves de API.
- `DATABASE_URL`.
- Credenciais do Neon.
- Informações privadas de usuários.

---

# 10. Varredura de vencimentos

O projeto possui o comando:

```bash
python manage.py varredura_vencimentos
```

A rotina está relacionada à identificação de vencimentos e à geração/atualização dos avisos financeiros.

Arquivo:

```text
core/management/commands/varredura_vencimentos.py
```

Serviço relacionado:

```text
core/services/due_date_scan.py
```

A execução automática depende do mecanismo de agendamento configurado no ambiente de produção.

---

# 11. Testes

O projeto possui um teste de fumaça:

```bash
python smoke_test.py
```

Também é possível verificar a configuração do Django com:

```bash
python manage.py check
```

Após alterações importantes, recomenda-se testar principalmente:

- Login.
- Cadastro.
- Receitas.
- Despesas.
- Categorias.
- Contas recorrentes.
- Marcação de contas como pagas.
- Dívidas.
- Parcelas.
- Importação de extratos.
- Conciliação.
- Objetivos.
- Contribuições.
- Retiradas.
- Central de Avisos.
- Sobra Segura.
- Modo de privacidade.
- Deploy no Render.
- Persistência dos dados no Neon.

---

# 12. Integração HG Brasil

O projeto possui um serviço relacionado à integração com a HG Brasil:

```text
dashboard/services/hgbrasil.py
```

Essa integração é utilizada para informações financeiras exibidas no sistema.

A configuração depende das variáveis de ambiente utilizadas pelo código.

A ausência ou indisponibilidade do serviço externo não deve comprometer as funcionalidades financeiras principais do FinanceEasy.

---

# 13. Segurança e preservação dos dados

O FinanceEasy trabalha com informações financeiras pessoais.

Por isso:

- Cada usuário deve visualizar somente seus próprios dados.
- Consultas devem respeitar o usuário autenticado.
- Dados financeiros não devem ser expostos em URLs desnecessariamente.
- Informações sensíveis não devem ser registradas em logs.
- Credenciais devem permanecer em variáveis de ambiente.
- O `.env` não deve ser enviado ao GitHub.
- O banco Neon não deve ser apagado para corrigir problemas de código.
- Migrações devem ser utilizadas para alterações estruturais.
- Alterações no código devem ser testadas antes do deploy.

---

# 14. Regras de manutenção

Ao realizar novas alterações no FinanceEasy:

1. **Preservar os dados existentes.**
2. **Não apagar registros do Neon sem uma solicitação explícita.**
3. **Manter o isolamento dos dados por usuário.**
4. **Não quebrar funcionalidades já existentes para corrigir outra.**
5. **Evitar alterações desnecessárias em arquivos não relacionados.**
6. **Manter a responsividade.**
7. **Manter o modo de privacidade.**
8. **Preservar o cálculo da Sobra Segura.**
9. **Preservar o histórico dos objetivos.**
10. **Preservar os pagamentos de contas e parcelas.**
11. **Utilizar migrações quando houver alteração no modelo do banco.**
12. **Testar localmente quando possível.**
13. **Depois do commit, verificar o deploy no Render.**
14. **Depois do deploy, testar a funcionalidade diretamente na aplicação.**

---

# 15. Decisões de escopo

A funcionalidade de dicas de consumo sem julgamento, anteriormente identificada como **UC13**, foi retirada do escopo.

O MVP prioriza:

- Organização financeira.
- Prevenção de atrasos.
- Contas recorrentes.
- Dívidas.
- Parcelas.
- Alertas.
- Orçamentos.
- Sobra Segura.
- Objetivos financeiros.
- Reserva financeira.
- Importação de extratos.
- Conciliação.
- Privacidade.

Esses recursos representam o núcleo da proposta do FinanceEasy para a persona **“Equilibrista Sobrecarregado”**.

---

# 16. Possíveis melhorias futuras

As próximas evoluções podem incluir:

- Melhorias na categorização automática de despesas.
- Evolução do mecanismo de reconhecimento de estabelecimentos.
- Melhorias no parser de PDF para diferentes bancos.
- Mais formatos de importação.
- Melhorias nos relatórios financeiros.
- Mais indicadores no painel.
- Melhorias na visualização dos objetivos.
- Melhorias na Central de Avisos.
- Melhorias na experiência mobile.
- Autenticação social.
- Envio real de e-mails para recuperação de senha.
- Monitoramento mais completo do deploy.
- Ampliação dos testes automatizados.
- Novas integrações externas, desde que não sejam obrigatórias para o funcionamento básico.

---

# 17. Princípio de evolução do projeto

O FinanceEasy deve evoluir de maneira incremental.

Cada nova funcionalidade deve ser implementada preservando as funcionalidades já existentes e, principalmente, os dados financeiros armazenados.

O princípio central do projeto é:

> **Organizar o dinheiro antes que ele vire um problema.**

O sistema deve ajudar o usuário a saber:

- Quanto recebeu.
- Quanto gastou.
- O que precisa pagar.
- O que está atrasado.
- Quanto ainda pode gastar.
- Quanto está acumulando.
- Quais objetivos está alcançando.

O objetivo final é transformar informações financeiras dispersas em uma visão simples, clara e prática da situação financeira do usuário.
