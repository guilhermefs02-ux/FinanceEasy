// FinanceEasy 

document.addEventListener("DOMContentLoaded", function () {
  // Confirmação antes de excluir (evita cliques acidentais — persona ansiosa).
  document.querySelectorAll("[data-confirm]").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      var mensagem = form.getAttribute("data-confirm") || "Tem certeza?";
      if (!window.confirm(mensagem)) {
        event.preventDefault();
      }
    });
  });

 // Gerenciamento de Tema com 3 Opções (Claro, Escuro, Sistema)
  const htmlPage = document.getElementById('htmlPage');
  const themeIcon = document.getElementById('themeIcon');
  const mediaQueryOS = window.matchMedia('(prefers-color-scheme: dark)');

  function getStoredTheme() {
    return localStorage.getItem('fe-theme') || 'auto';
  }

  function applyTheme(theme) {
    let effectiveTheme = theme;
    if (theme === 'auto') {
      effectiveTheme = mediaQueryOS.matches ? 'dark' : 'light';
    }

    htmlPage.setAttribute('data-bs-theme', effectiveTheme);

    // Atualiza o ícone do botão principal do menu
    if (themeIcon) {
      if (theme === 'light') {
        themeIcon.className = 'bi bi-sun-fill fs-5';
      } else if (theme === 'dark') {
        themeIcon.className = 'bi bi-moon-stars-fill fs-5';
      } else {
        themeIcon.className = 'bi bi-circle-half fs-5';
      }
    }
  }

  function setTheme(theme) {
    if (theme === 'auto') {
      localStorage.removeItem('fe-theme'); // Limpa a escolha manual para voltar a seguir o OS
    } else {
      localStorage.setItem('fe-theme', theme);
    }
    applyTheme(theme);
  }

  // Inicialização ao carregar a página
  applyTheme(getStoredTheme());

  // Escuta alterações do SO caso o modo 'auto' esteja ativo
  mediaQueryOS.addEventListener('change', function () {
    if (getStoredTheme() === 'auto') {
      applyTheme('auto');
    }
  });

  // Evento nos botões do Dropdown
  document.querySelectorAll('[data-bs-theme-value]').forEach(function (element) {
    element.addEventListener('click', function () {
      const selectedTheme = this.getAttribute('data-bs-theme-value');
      setTheme(selectedTheme);
    });
  });

  // 2. Evento ao clicar no botão de alternância
  if (themeToggleBtn) {
    themeToggleBtn.addEventListener('click', function() {
      const currentTheme = htmlPage.getAttribute('data-bs-theme');
      const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
      setTheme(newTheme);
    });
  }

  function setTheme(theme) {
    htmlPage.setAttribute('data-bs-theme', theme);
    localStorage.setItem('fe-theme', theme);

    if (themeIcon) {
      if (theme === 'dark') {
        themeIcon.classList.remove('bi-sun-fill');
        themeIcon.classList.add('bi-moon-stars-fill');
      } else {
        themeIcon.classList.remove('bi-moon-stars-fill');
        themeIcon.classList.add('bi-sun-fill');
      }
    }
  }

  // Tela de conciliação (UC05): marcar/desmarcar todos de uma vez.
  var marcarTodos = document.getElementById("marcar-todos");
  if (marcarTodos) {
    marcarTodos.addEventListener("change", function () {
      document.querySelectorAll(".fe-incluir-checkbox").forEach(function (chk) {
        chk.checked = marcarTodos.checked;
      });
    });
  }

  // Fecha alertas automaticamente depois de um tempo, sem exigir clique (RNF01).
  document.querySelectorAll(".alert.fe-auto-dismiss").forEach(function (alerta) {
    setTimeout(function () {
      var instancia = bootstrap.Alert.getOrCreateInstance(alerta);
      instancia.close();
    }, 8000);
  });

  // Atalhos de microvalores (UC12)
  document.querySelectorAll("[data-valor-atalho]").forEach(function (botao) {
    botao.addEventListener("click", function () {
      var campo = document.querySelector('input[name="valor"][data-form="' + botao.dataset.form + '"]');
      if (campo) {
        campo.value = botao.dataset.valorAtalho;
      }
    });
  });

  // Lançamento em lote (despesas/receitas)
  var addRowBtn = document.getElementById("fe-lote-add-row");
  if (addRowBtn) {
    var rowsContainer = document.getElementById("lote-rows");
    var emptyTemplate = document.getElementById("empty-form-template");
    var totalFormsInput = document.querySelector('input[name="form-TOTAL_FORMS"]');

    addRowBtn.addEventListener("click", function () {
      var index = parseInt(totalFormsInput.value, 10);
      var fragmento = emptyTemplate.content.cloneNode(true);
      var novaLinhaHtml = fragmento.firstElementChild.outerHTML.split("__prefix__").join(index);
      var wrapper = document.createElement("div");
      wrapper.innerHTML = novaLinhaHtml;
      rowsContainer.appendChild(wrapper.firstElementChild);
      totalFormsInput.value = index + 1;
    });

    rowsContainer.addEventListener("click", function (event) {
      var botaoHoje = event.target.closest(".fe-lote-hoje");
      if (botaoHoje) {
        var campoData = botaoHoje.closest(".input-group").querySelector('input[type="date"]');
        if (campoData) {
          var hoje = new Date();
          var mes = String(hoje.getMonth() + 1).padStart(2, "0");
          var dia = String(hoje.getDate()).padStart(2, "0");
          campoData.value = hoje.getFullYear() + "-" + mes + "-" + dia;
        }
        return;
      }
      var botaoRemover = event.target.closest(".fe-lote-remove");
      if (botaoRemover) {
        var linha = botaoRemover.closest(".fe-lote-row");
        if (linha) {
          linha.remove();
        }
      }
    });
  }
});