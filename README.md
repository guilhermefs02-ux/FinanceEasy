# FinanceEasy

Aplicativo web de gestão financeira pessoal desenvolvido com **Python e Django**, criado para ajudar pessoas a organizar suas finanças, controlar receitas e despesas, acompanhar dívidas, administrar contas recorrentes, importar extratos bancários e alcançar objetivos financeiros.

O FinanceEasy tem como persona principal o **“Equilibrista Sobrecarregado”**: uma pessoa que enfrenta dificuldades para organizar o dinheiro, precisa acompanhar vencimentos e deseja entender quanto pode gastar com segurança.

O projeto prioriza a organização financeira sem julgamentos, a prevenção de atrasos, a preservação do histórico financeiro e a apresentação clara das informações.

**Repositório:** https://github.com/guilhermefs02-ux/FinanceEasy

**Aplicação em produção:** https://financeeasy.onrender.com

**Hospedagem:** Render

**Banco de dados de produção:** Neon PostgreSQL

**Arquitetura:** Django MTV (Model, Template, View)

---

## 1. Tecnologias utilizadas

- **Python 3.13:** linguagem principal.
- **Django 5.2:** framework web.
- **HTML5, CSS3 e JavaScript:** estrutura, estilização e interatividade.
- **Bootstrap 5:** componentes e interface responsiva.
- **PostgreSQL:** banco de dados de produção.
- **Neon:** hospedagem do banco de dados PostgreSQL.
- **Render:** hospedagem e execução da aplicação.
- **GitHub:** versionamento e gerenciamento do código-fonte.
- **Groq API:** inteligência artificial utilizada como apoio à categorização de transações importadas.
- **HG Brasil Finance API:** integração para obtenção de informações financeiras e cotações.
- **OFX, CSV e PDF:** formatos contemplados pelo fluxo de importação de extratos.
- **SQLite:** opção de banco local, conforme a configuração do Django.

### Arquitetura de publicação

```text
GitHub
   |
   v
Render
   |
   v
Aplicação Django
   |
   v
Neon PostgreSQL
```

As integrações externas, como Groq e HG Brasil, são utilizadas pelos serviços correspondentes da aplicação.

As credenciais devem ser armazenadas em variáveis de ambiente. Chaves de API, senhas e informações de conexão não devem ser publicadas no repositório.

---

## 2. Funcionalidades do sistema

### 2.1. Cadastro e autenticação

O módulo `accounts` é responsável pelo gerenciamento dos usuários.

Funcionalidades:

- Cadastro de usuários.
- Login e logout.
- Recuperação de senha por código, conforme a implementação disponível.
- Perfil e informações complementares.
- Controle de usuários ativos.
- Administração pelo Django Admin.
- Proteção de páginas que exigem autenticação.
- Associação dos dados financeiros ao usuário correspondente.

O identificador de acesso é definido pela implementação do modelo personalizado de usuário.

### 2.2. Painel financeiro

O painel principal apresenta uma visão geral das finanças do usuário.

Recursos:

- Saudação personalizada.
- Seleção da competência mensal.
- Navegação entre meses e anos.
- Total de receitas.
- Total de despesas.
- Saldo financeiro.
- Detalhamento de receitas e despesas.
- Agrupamento de despesas por categoria.
- Indicador de Sobra Segura.
- Acompanhamento de objetivos financeiros.
- Central de Avisos.
- Indicadores financeiros.
- Modo de privacidade para ocultação de valores.

Os indicadores são calculados com base nos registros financeiros e nos critérios de período definidos pelo sistema.

### 2.3. Sobra Segura

A Sobra Segura busca responder à seguinte pergunta:

> Quanto dinheiro posso considerar disponível depois de levar em conta os compromissos financeiros próximos?

O indicador considera o saldo e as obrigações previstas dentro do período utilizado pelo sistema.

A finalidade é evitar que o usuário confunda o saldo disponível com dinheiro que já será necessário para pagar contas e outros compromissos.

Quando as obrigações previstas superam o saldo considerado, o sistema pode apresentar um resultado negativo e um alerta visual.

### 2.4. Central de Avisos

A Central de Avisos reúne informações importantes sobre os compromissos financeiros.

Entre os itens acompanhados estão:

- Contas recorrentes vencidas.
- Contas próximas do vencimento.
- Obrigações pendentes.
- Parcelas de dívidas, conforme a integração existente.
- Datas de vencimento.
- Valores das obrigações.
- Identificação do tipo de compromisso.
- Quantidade de pendências e atrasos.
- Compromissos previstos para os próximos sete dias.

A interface também contempla ações para marcar contas recorrentes como pagas, respeitando o registro de pagamento correspondente.

A apresentação dos avisos deve distinguir compromissos previstos de pagamentos efetivamente realizados.

### 2.5. Receitas

O sistema permite cadastrar receitas manualmente.

Os lançamentos podem conter:

- Descrição.
- Valor.
- Data.
- Categoria.
- Usuário responsável.

As receitas são utilizadas nos indicadores financeiros e podem ser consultadas no extrato.

### 2.6. Despesas

O sistema permite registrar despesas manualmente e consultar suas informações posteriormente.

Os lançamentos podem conter:

- Descrição.
- Valor.
- Data.
- Categoria.
- Usuário responsável.
- Informações complementares relacionadas à movimentação.

As despesas são utilizadas no cálculo dos indicadores, nos relatórios e no acompanhamento dos gastos por categoria.

### 2.7. Categorias financeiras

O módulo `transactions` possui recursos para organização das movimentações financeiras.

As categorias podem utilizar nomes, ícones e cores para facilitar a identificação dos gastos.

O sistema também contempla categorias relacionadas a receitas, despesas e orçamentos.

A categorização permite organizar as informações e melhorar a compreensão dos hábitos financeiros.

### 2.8. Orçamentos por categoria

O FinanceEasy possui suporte a limites de orçamento por categoria.

O objetivo é permitir o acompanhamento dos gastos em relação aos limites definidos.

Serviço relacionado:

```text
core/services/budget_alerts.py
```

O serviço dá suporte à identificação de situações em que os gastos se aproximam dos limites estabelecidos.

### 2.9. Importação de extratos bancários

O sistema possui um fluxo específico para importação de extratos.

Arquivo principal do processamento:

```text
transactions/services/import_parser.py
```

Formatos contemplados pela implementação:

- OFX.
- CSV.
- PDF.

A importação permite transformar informações extraídas de arquivos bancários em transações que podem ser revisadas e incorporadas ao controle financeiro.

O fluxo contempla validações e etapas de conciliação para reduzir erros e evitar a inclusão indevida de movimentações.

**Limite de upload:** a aplicação possui um limite de tamanho configurável, com valor padrão de 10 MB na implementação de importação que utiliza essa validação.

### 2.10. Conciliação de transações

Após a importação, as movimentações podem passar por uma etapa de conciliação.

Essa etapa permite revisar as informações antes de utilizar os registros no controle financeiro.

O objetivo é melhorar a qualidade dos dados importados e reduzir problemas como:

- Descrições incorretas.
- Categorias inadequadas.
- Movimentações duplicadas.
- Informações incompletas.
- Classificações que precisam de revisão.

As transações importadas devem permanecer associadas ao usuário responsável e respeitar as regras de persistência da aplicação.

### 2.11. Categorização automática com inteligência artificial

O FinanceEasy possui um serviço de categorização de transações:

```text
transactions/services/categorizer.py
```

A implementação utiliza uma abordagem combinada:

1. Aplicação de regras locais de categorização.
2. Identificação de transações que ainda precisam de classificação.
3. Consulta à API da Groq quando aplicável e configurada.
4. Validação da categoria retornada.
5. Utilização do mecanismo de fallback quando a integração não consegue classificar a transação.

Essa abordagem busca aproveitar as regras locais para reconhecer transações conhecidas e utilizar inteligência artificial como apoio nos casos em que a classificação ainda é incerta.

### 2.12. Integração Groq API

A **Groq API substituiu a integração anterior com a Hugging Face Inference API** no fluxo de categorização desenvolvido para o projeto.

Configuração principal:

| Item | Configuração |
|---|---|
| Provedor de IA | Groq |
| Endpoint | `https://api.groq.com/openai/v1/chat/completions` |
| Modelo configurado | `openai/gpt-oss-20b` |
| Variável de ambiente | `GROQ_API_KEY` |
| Serviço responsável | `transactions/services/categorizer.py` |
| Cache de resultados | Cache de categorização com duração prevista de sete dias |

O serviço utiliza a API para sugerir categorias válidas para as transações que precisam de classificação adicional.

A resposta da IA deve ser validada antes de ser utilizada pela aplicação, evitando a aceitação automática de categorias inexistentes ou incompatíveis com as opções do sistema.

O cache reduz consultas repetidas para transações equivalentes, contribuindo para diminuir o consumo da API.

A categorização local continua sendo importante para manter o funcionamento básico quando a integração externa está indisponível.

**Importante:** a utilização da Groq depende de uma chave válida, da disponibilidade do serviço e dos limites vigentes da conta. A integração não garante que todas as transações sejam classificadas corretamente.

Transferências genéricas, PIX, TED, DOC, boletos, faturas e pagamentos de cartão podem exigir informações adicionais para uma classificação confiável. Por isso, determinadas movimentações podem permanecer em `Outros` ou exigir revisão.

A categoria `Outros` também pode ser utilizada como fallback quando não existe informação suficiente para uma classificação segura.

A API deve ser considerada um recurso auxiliar, não uma substituição das validações e regras financeiras da aplicação.

### 2.13. Contas recorrentes

O sistema contempla o gerenciamento de contas recorrentes, incluindo compromissos mensais e anuais.

As contas podem possuir:

- Nome ou descrição.
- Valor.
- Periodicidade.
- Dia de vencimento.
- Categoria.
- Usuário responsável.
- Situação ativa ou inativa.
- Informações de vencimento aplicáveis ao registro.

As periodicidades incluem mensal e anual, conforme os modelos e formulários implementados.

O sistema diferencia o compromisso financeiro previsto do pagamento efetivamente realizado.

### 2.14. Pagamentos de contas recorrentes

Os pagamentos são associados aos registros de contas recorrentes.

O sistema contempla o acompanhamento de obrigações pagas e pendentes, com registros próprios para representar os pagamentos.

A manutenção dessa relação é importante para evitar que um pagamento seja confundido com uma nova obrigação ou que o histórico seja perdido durante alterações posteriores.

Ao realizar correções nesse módulo, devem ser preservados:

- Os registros originais das contas.
- O histórico dos pagamentos.
- As transações relacionadas.
- A associação com o usuário.
- As informações históricas necessárias para o extrato.

A exclusão de uma conta ou a correção de um pagamento deve respeitar as regras de integridade dos dados.

### 2.15. Dívidas e parcelamentos

O módulo `debts` é responsável pelo gerenciamento das dívidas.

Entre os recursos previstos na implementação estão:

- Cadastro de dívidas.
- Controle de valores.
- Parcelamento.
- Acompanhamento de parcelas.
- Registro de pagamentos.
- Consulta de parcelas pendentes.
- Recursos relacionados a cartões de crédito, conforme a implementação disponível.

Arquivos relacionados:

```text
debts/models.py
debts/forms.py
debts/views.py
debts/services/credit_card.py
```

O objetivo é permitir que o usuário acompanhe suas obrigações e tenha maior clareza sobre os compromissos futuros.

### 2.16. Objetivos financeiros

O módulo `goals` é responsável pelo gerenciamento de objetivos financeiros.

Exemplos:

- Reserva de emergência.
- Colchão financeiro.
- Viagens.
- Compra de terrenos.
- Compra de veículos.
- Aquisição de bens.
- Outros objetivos pessoais.

Funcionalidades contempladas:

- Criação e edição de objetivos.
- Definição de valor-alvo.
- Acompanhamento do valor acumulado.
- Cálculo do percentual concluído.
- Visualização do valor restante.
- Registro de contribuições.
- Registro de retiradas.
- Histórico financeiro dos objetivos.
- Tratamento de objetivos concluídos.
- Arquivamento após o período definido pela aplicação.

O sistema também possui tratamento específico para o objetivo de reserva financeira.

O histórico de contribuições e retiradas deve ser preservado, inclusive após a conclusão de um objetivo.

### 2.17. Modo de privacidade

O modo de privacidade permite ocultar visualmente valores financeiros apresentados na interface.

Quando ativado, os valores sensíveis podem ser substituídos por caracteres de ocultação.

O recurso busca reduzir a exposição de informações financeiras quando o usuário utiliza o sistema em locais públicos.

Novos componentes que exibam valores devem respeitar o comportamento desse modo.

### 2.18. Extrato financeiro

O extrato permite consultar as movimentações financeiras registradas no sistema.

Os recursos podem incluir:

- Consulta de receitas.
- Consulta de despesas.
- Datas.
- Descrições.
- Valores.
- Categorias.
- Filtros disponíveis.
- Lançamentos relacionados a pagamentos e recorrências.

O extrato deve manter a distinção entre transações efetivamente registradas e compromissos financeiros futuros.

As movimentações também devem respeitar os filtros de competência e as regras de associação ao usuário.

### 2.19. Recorrências

O projeto possui serviços relacionados à geração e ao gerenciamento de lançamentos recorrentes.

Arquivos:

```text
transactions/services/recurrency.py
transactions/services/recurring_bills.py
```

Esses serviços apoiam o tratamento de obrigações recorrentes e seus respectivos pagamentos.

Alterações nessa área devem evitar a geração de registros duplicados e preservar o histórico de compromissos anteriores.

### 2.20. Assinaturas

O projeto possui uma interface dedicada ao acompanhamento de assinaturas:

```text
templates/transactions/assinaturas.html
```

O recurso está relacionado à organização de compromissos recorrentes com serviços e assinaturas.

### 2.21. Comparativo financeiro

O projeto possui uma interface para comparação de informações financeiras entre períodos:

```text
templates/transactions/comparativo.html
```

O objetivo é facilitar a análise da evolução das movimentações ao longo do tempo.

---

## 3. Estrutura do projeto

A estrutura principal está organizada em aplicações Django:

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

A estrutura acima representa a organização principal documentada do projeto. Arquivos adicionais podem existir no repositório.

---

## 4. Banco de dados

O ambiente de produção utiliza **PostgreSQL hospedado no Neon**.

O banco armazena os dados persistentes da aplicação, incluindo usuários, transações, categorias, dívidas, pagamentos e objetivos financeiros.

Entre as tabelas relacionadas aos módulos do sistema estão:

```text
accounts_user
accounts_passwordresetcode

core_notification

debts_debt
debts_debtpayment

goals_goal
goals_goalcontribution
goals_goalwithdrawal

transactions_category
transactions_categorybudget
transactions_importbatch
transactions_recurringbill
transactions_recurringbillpayment
transactions_transaction

django_admin_log
django_content_type
django_migrations
django_session
```

A lista é ilustrativa e pode variar conforme as migrações aplicadas.

### Migrações

As alterações estruturais devem ser controladas pelo sistema de migrações do Django.

Comandos utilizados no desenvolvimento:

```bash
python manage.py makemigrations
python manage.py migrate
```

**Regra fundamental:** não apagar, recriar ou limpar o banco de produção para corrigir problemas de código.

Antes de aplicar migrações em produção, é necessário verificar as alterações, as dependências e o histórico de migrações.

---

## 5. Configuração local

### 5.1. Pré-requisitos

- Python 3.13.
- pip.
- Git.
- Editor de código, caso o desenvolvimento seja local.
- Acesso ao repositório.

### 5.2. Clonar o repositório

```bash
git clone https://github.com/guilhermefs02-ux/FinanceEasy.git
cd FinanceEasy
```

### 5.3. Criar o ambiente virtual

No Windows:

```powershell
py -3.13 -m venv .venv
```

Ative o ambiente:

```powershell
.\.venv\Scripts\Activate.ps1
```

Se houver bloqueio de execução do PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Confira a versão:

```powershell
python --version
```

### 5.4. Instalar as dependências

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 5.5. Configurar as variáveis de ambiente

Copie o arquivo `.env.example` para `.env`:

```powershell
Copy-Item .env.example .env
```

Preencha os valores de acordo com a configuração do ambiente local.

Não publique o arquivo `.env` no GitHub.

---

## 6. Variáveis de ambiente

As variáveis efetivamente utilizadas dependem da configuração do Django e dos serviços integrados.

Entre as configurações relevantes para o ambiente de produção estão:

| Variável | Finalidade |
|---|---|
| `DATABASE_URL` | Conexão com o banco de dados, quando utilizada pela configuração Django |
| `DJANGO_SECRET_KEY` | Chave secreta do Django |
| `DJANGO_DEBUG` | Controle do modo de depuração |
| `DJANGO_ALLOWED_HOSTS` | Hosts autorizados |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Origens confiáveis para proteção CSRF |
| `GROQ_API_KEY` | Chave de acesso à Groq API |
| `HGBRASIL_API_KEY` | Chave de acesso à HG Brasil, quando exigida pelo serviço |
| `PYTHON_VERSION` | Versão do Python configurada no Render |

Outras variáveis podem ser utilizadas pelos serviços e configurações adicionais.

**Nunca coloque valores reais de chaves ou senhas neste README.**

O arquivo `.env.example` deve conter apenas nomes de variáveis e exemplos seguros, sem credenciais reais.

---

## 7. Executar localmente

Com as dependências instaladas e o ambiente configurado, execute:

```bash
python manage.py migrate
python manage.py runserver
```

A aplicação estará disponível em:

```text
http://127.0.0.1:8000/
```

Para criar um administrador local:

```bash
python manage.py createsuperuser
```

O banco local deve ser configurado separadamente do banco de produção.

---

## 8. Publicação e deploy

O FinanceEasy utiliza GitHub, Render e Neon.

### GitHub

Responsável pelo código-fonte, histórico de alterações e controle de versões.

Repositório:

https://github.com/guilhermefs02-ux/FinanceEasy

### Render

Responsável por executar e disponibilizar a aplicação Django na internet.

Aplicação:

https://financeeasy.onrender.com

### Neon

Responsável pelo armazenamento persistente dos dados em PostgreSQL.

### Fluxo de atualização

```text
Alteração no código
       |
       v
Commit no GitHub
       |
       v
Deploy no Render
       |
       v
Aplicação atualizada
       |
       v
Banco de dados Neon
```

O deploy de uma alteração no código não deve apagar os dados existentes no banco.

### Cuidados no deploy

1. Conferir os arquivos modificados.
2. Confirmar o commit no GitHub.
3. Aguardar a conclusão do deploy no Render.
4. Conferir os logs de inicialização.
5. Verificar eventuais erros de migração.
6. Testar a funcionalidade alterada.
7. Confirmar a persistência dos dados.

Quando o desenvolvimento for realizado diretamente pelo GitHub, sem VS Code ou terminal local, o processo de alteração e publicação pode ser acompanhado pelo repositório e pelo painel do Render.

---

## 9. Integração HG Brasil Finance

O projeto possui um serviço de integração com a HG Brasil:

```text
dashboard/services/hgbrasil.py
```

A integração é utilizada para obter informações financeiras disponibilizadas pelo serviço externo.

A execução depende da implementação do serviço, da configuração necessária e da disponibilidade da API.

A indisponibilidade de uma integração externa não deve comprometer a utilização das funcionalidades financeiras essenciais.

---

## 10. Varredura de vencimentos

O projeto possui um comando de gerenciamento relacionado à identificação de vencimentos:

```bash
python manage.py varredura_vencimentos
```

Arquivos relacionados:

```text
core/management/commands/varredura_vencimentos.py
core/services/due_date_scan.py
```

O comando pode ser utilizado conforme a configuração do sistema para executar a rotina de varredura.

A execução automática em produção depende de um mecanismo de agendamento devidamente configurado.

---

## 11. Testes e validações

O projeto possui um teste de fumaça:

```bash
python smoke_test.py
```

Também é possível executar a verificação de configuração do Django:

```bash
python manage.py check
```

Após alterações relevantes, recomenda-se verificar:

- Cadastro e autenticação.
- Receitas e despesas.
- Filtros de competência.
- Indicadores do painel.
- Categorias e orçamentos.
- Importação de OFX, CSV e PDF.
- Categorização local.
- Integração com a Groq API.
- Comportamento de fallback da categorização.
- Conciliação de transações.
- Contas recorrentes.
- Pagamentos e histórico.
- Dívidas e parcelas.
- Objetivos financeiros.
- Contribuições e retiradas.
- Central de Avisos.
- Sobra Segura.
- Modo de privacidade.
- Persistência no Neon.
- Funcionamento após o deploy no Render.

A aprovação de um teste de fumaça não substitui a verificação das funcionalidades afetadas pela alteração.

---

## 12. Segurança e preservação dos dados

Como o FinanceEasy trabalha com informações financeiras pessoais, a segurança e a integridade dos dados são requisitos fundamentais.

Regras:

- Cada usuário deve acessar somente seus próprios dados.
- As consultas devem respeitar o usuário autenticado.
- As credenciais devem permanecer em variáveis de ambiente.
- Chaves de API não devem ser publicadas no GitHub.
- O arquivo `.env` não deve ser versionado.
- Informações financeiras sensíveis não devem ser expostas desnecessariamente em logs.
- As migrações devem ser utilizadas para alterações estruturais.
- O banco de produção não deve ser apagado para corrigir problemas de aplicação.
- Alterações em pagamentos devem preservar a integridade dos registros relacionados.
- A importação deve respeitar as regras de associação ao usuário e evitar duplicidades quando previstas pela implementação.

---

## 13. Regras de manutenção do FinanceEasy

Ao desenvolver novas funcionalidades ou corrigir problemas:

1. Preservar os dados existentes.
2. Não excluir registros de produção sem autorização explícita.
3. Manter o isolamento dos dados por usuário.
4. Evitar alterações desnecessárias em arquivos não relacionados.
5. Preservar a paleta visual atual do projeto.
6. Manter a responsividade da interface.
7. Respeitar o modo de privacidade.
8. Preservar os cálculos da Sobra Segura.
9. Preservar o histórico de objetivos, contribuições e retiradas.
10. Preservar a relação entre contas recorrentes e pagamentos.
11. Evitar a criação de transações duplicadas.
12. Utilizar migrações quando houver alterações nos modelos.
13. Validar o funcionamento da categorização local mesmo sem a Groq API.
14. Tratar falhas de serviços externos sem comprometer as funções essenciais.
15. Conferir o deploy e testar a aplicação após cada alteração relevante.

---

## 14. Escopo do projeto

A funcionalidade de dicas de consumo sem julgamento, anteriormente identificada como UC13, foi retirada do escopo.

O núcleo do FinanceEasy prioriza:

- Organização financeira.
- Controle de receitas e despesas.
- Prevenção de atrasos.
- Contas recorrentes.
- Pagamentos.
- Dívidas e parcelas.
- Alertas financeiros.
- Orçamentos por categoria.
- Sobra Segura.
- Objetivos financeiros.
- Reservas.
- Importação e conciliação de extratos.
- Categorização de transações.
- Privacidade.

Esses recursos estão alinhados à proposta de auxiliar o “Equilibrista Sobrecarregado” a compreender sua situação financeira e tomar decisões com mais clareza.

---

## 15. Melhorias futuras

Possíveis evoluções do projeto:

- Aprimorar a categorização automática de despesas.
- Ampliar as regras locais de reconhecimento de estabelecimentos.
- Melhorar o tratamento de transações genéricas e transferências.
- Ampliar a compatibilidade com diferentes extratos bancários.
- Melhorar a extração de informações de PDFs.
- Aprimorar os relatórios e comparativos financeiros.
- Evoluir a apresentação visual dos objetivos.
- Melhorar a experiência mobile.
- Ampliar os testes automatizados.
- Aprimorar o monitoramento de erros.
- Melhorar os mecanismos de recuperação de senha.
- Adicionar novas integrações externas sem tornar serviços opcionais obrigatórios para o funcionamento básico.

As melhorias devem ser avaliadas de acordo com as necessidades do projeto, a estabilidade da aplicação e a preservação dos dados existentes.

---

## 16. Princípio de evolução

O FinanceEasy deve evoluir de forma incremental, com alterações que preservem as funcionalidades existentes, a integridade dos dados e a experiência do usuário.

A inteligência artificial é um recurso de apoio à categorização, enquanto as regras locais, as validações e o banco de dados continuam sendo componentes essenciais da aplicação.

O princípio central do projeto é:

> **Organizar o dinheiro antes que ele vire um problema.**

O FinanceEasy busca ajudar o usuário a compreender:

- Quanto recebeu.
- Quanto gastou.
- Quais contas precisa pagar.
- O que está atrasado.
- Quanto pode gastar com segurança.
- Quanto está acumulando.
- Quais objetivos está alcançando.

O objetivo final é transformar informações financeiras dispersas em uma visão simples, organizada e prática da vida financeira.
