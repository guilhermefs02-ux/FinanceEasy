/* FinanceEasy */

document.addEventListener("DOMContentLoaded", function () {
  // =========================================================
  // 1. CONFIRMAÇÃO ANTES DE EXCLUIR
  // =========================================================
  document.querySelectorAll("[data-confirm]").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      var mensagem = form.getAttribute("data-confirm") || "Tem certeza?";

      if (!window.confirm(mensagem)) {
        event.preventDefault();
      }
    });
  });

  // =========================================================
  // 2. MENU LATERAL RESPONSIVO — CELULAR E TABLET
  // =========================================================
  var menuLateral = document.querySelector(".fe-sidebar");
  var botaoMenu = document.querySelector(".fe-menu-toggle");
  var sobreposicaoMenu = document.querySelector(".fe-sidebar-overlay");

  function abrirMenu() {
    if (!menuLateral) return;

    menuLateral.classList.add("is-open");

    if (sobreposicaoMenu) {
      sobreposicaoMenu.classList.add("is-visible");
    }

    if (botaoMenu) {
      botaoMenu.setAttribute("aria-expanded", "true");
      botaoMenu.setAttribute("aria-label", "Fechar menu");
    }

    document.body.classList.add("fe-menu-open");
  }

  function fecharMenu() {
    if (!menuLateral) return;

    menuLateral.classList.remove("is-open");

    if (sobreposicaoMenu) {
      sobreposicaoMenu.classList.remove("is-visible");
    }

    if (botaoMenu) {
      botaoMenu.setAttribute("aria-expanded", "false");
      botaoMenu.setAttribute("aria-label", "Abrir menu");
    }

    document.body.classList.remove("fe-menu-open");
  }

  if (menuLateral && botaoMenu) {
    botaoMenu.setAttribute("aria-expanded", "false");

    botaoMenu.addEventListener("click", function (event) {
      event.preventDefault();

      if (menuLateral.classList.contains("is-open")) {
        fecharMenu();
      } else {
        abrirMenu();
      }
    });

    if (sobreposicaoMenu) {
      sobreposicaoMenu.addEventListener("click", fecharMenu);
    }

    menuLateral.querySelectorAll("a").forEach(function (link) {
      link.addEventListener("click", function () {
        if (window.innerWidth < 992) {
          fecharMenu();
        }
      });
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        fecharMenu();
      }
    });

    window.addEventListener("resize", function () {
      if (window.innerWidth >= 992) {
        fecharMenu();
      }
    });
  }

  // =========================================================
  // 3. TEMA CLARO, ESCURO E AUTOMÁTICO
  // =========================================================
  var htmlPage = document.getElementById("htmlPage");
  var themeIcon = document.getElementById("themeIcon");
  var mediaQueryOS = window.matchMedia("(prefers-color-scheme: dark)");

  function getStoredTheme() {
    var saved = localStorage.getItem("fe-theme");

    if (["light", "dark", "auto"].includes(saved)) {
      return saved;
    }

    // Compatibilidade com a preferência salva anteriormente.
    var legacy = localStorage.getItem("theme");

    if (["light", "dark"].includes(legacy)) {
      return legacy;
    }

    return "auto";
  }

  function applyTheme(theme) {
    if (!htmlPage) return;

    var temaEfetivo =
      theme === "auto"
        ? mediaQueryOS.matches
          ? "dark"
          : "light"
        : theme;

    // Aplica o tema utilizado pelo Bootstrap e pelo FinanceEasy.
    htmlPage.setAttribute("data-bs-theme", temaEfetivo);
    htmlPage.setAttribute("data-theme", temaEfetivo);

    // Atualiza o ícone do botão superior.
    if (themeIcon) {
      if (theme === "auto") {
        themeIcon.className = "bi bi-circle-half fs-5";
      } else if (temaEfetivo === "dark") {
        themeIcon.className = "bi bi-moon-stars-fill fs-5";
      } else {
        themeIcon.className = "bi bi-sun-fill fs-5";
      }
    }

    // Atualiza o estado dos botões nos dois menus.
    document.querySelectorAll("[data-bs-theme-value]").forEach(function (button) {
      var selecionado =
        button.getAttribute("data-bs-theme-value") === theme;

      button.setAttribute("aria-checked", selecionado ? "true" : "false");

      if (selecionado) {
        button.classList.add("active");
      } else {
        button.classList.remove("active");
      }
    });
  }

  function setTheme(theme) {
    if (!["light", "dark", "auto"].includes(theme)) {
      return;
    }

    // Mantém as duas chaves sincronizadas para compatibilidade.
    localStorage.setItem("fe-theme", theme);
    localStorage.setItem("theme", theme);

    applyTheme(theme);
  }

  // Aplica a preferência salva ao carregar a página.
  applyTheme(getStoredTheme());

  // Atualiza automaticamente quando o tema do sistema muda.
  if (mediaQueryOS.addEventListener) {
    mediaQueryOS.addEventListener("change", function () {
      if (getStoredTheme() === "auto") {
        applyTheme("auto");
      }
    });
  } else if (mediaQueryOS.addListener) {
    mediaQueryOS.addListener(function () {
      if (getStoredTheme() === "auto") {
        applyTheme("auto");
      }
    });
  }

  // Ativa os botões de tema existentes nos dois menus.
  document.querySelectorAll("[data-bs-theme-value]").forEach(function (button) {
    button.addEventListener("click", function () {
      var temaSelecionado = button.getAttribute("data-bs-theme-value");

      setTheme(temaSelecionado);
    });
  });

  // =========================================================
  // 4. CONCILIAÇÃO: MARCAR OU DESMARCAR TODOS
  // =========================================================
  var marcarTodos = document.getElementById("marcar-todos");

  if (marcarTodos) {
    marcarTodos.addEventListener("change", function () {
      document.querySelectorAll(".fe-incluir-checkbox").forEach(function (chk) {
        chk.checked = marcarTodos.checked;
      });
    });
  }

  // =========================================================
  // 5. FECHAMENTO AUTOMÁTICO DOS ALERTAS
  // =========================================================
  document.querySelectorAll(".alert.fe-auto-dismiss").forEach(function (alerta) {
    setTimeout(function () {
      if (window.bootstrap && window.bootstrap.Alert) {
        var instancia = window.bootstrap.Alert.getOrCreateInstance(alerta);
        instancia.close();
      }
    }, 8000);
  });

  // =========================================================
  // 6. ATALHOS DE MICROVALORES
  // =========================================================
  document.querySelectorAll("[data-valor-atalho]").forEach(function (botao) {
    botao.addEventListener("click", function () {
      var campo = document.querySelector(
        'input[name="valor"][data-form="' + botao.dataset.form + '"]'
      );

      if (campo) {
        campo.value = botao.dataset.valorAtalho;
        campo.dispatchEvent(new Event("input", { bubbles: true }));
        campo.dispatchEvent(new Event("change", { bubbles: true }));
      }
    });
  });

  // =========================================================
  // 7. LANÇAMENTOS EM LOTE
  // =========================================================
  var addRowBtn = document.getElementById("fe-lote-add-row");

  if (addRowBtn) {
    var rowsContainer = document.getElementById("lote-rows");
    var emptyTemplate = document.getElementById("empty-form-template");
    var totalFormsInput = document.querySelector(
      'input[name="form-TOTAL_FORMS"]'
    );

    if (rowsContainer && emptyTemplate && totalFormsInput) {
      addRowBtn.addEventListener("click", function () {
        var index = parseInt(totalFormsInput.value, 10);

        if (Number.isNaN(index)) return;

        var fragmento = emptyTemplate.content.cloneNode(true);
        var primeiraLinha = fragmento.firstElementChild;

        if (!primeiraLinha) return;

        var novaLinhaHtml = primeiraLinha.outerHTML
          .split("__prefix__")
          .join(index);

        var wrapper = document.createElement("div");
        wrapper.innerHTML = novaLinhaHtml;

        if (wrapper.firstElementChild) {
          rowsContainer.appendChild(wrapper.firstElementChild);
          totalFormsInput.value = index + 1;
        }
      });

      rowsContainer.addEventListener("click", function (event) {
        var alvo = event.target;

        if (!(alvo instanceof Element)) return;

        var botaoHoje = alvo.closest(".fe-lote-hoje");

        if (botaoHoje) {
          var grupo = botaoHoje.closest(".input-group");
          var campoData = grupo
            ? grupo.querySelector('input[type="date"]')
            : null;

          if (campoData) {
            var hoje = new Date();
            var mes = String(hoje.getMonth() + 1).padStart(2, "0");
            var dia = String(hoje.getDate()).padStart(2, "0");

            campoData.value =
              hoje.getFullYear() + "-" + mes + "-" + dia;

            campoData.dispatchEvent(
              new Event("change", { bubbles: true })
            );
          }

          return;
        }

        var botaoRemover = alvo.closest(".fe-lote-remove");

        if (botaoRemover) {
          var linha = botaoRemover.closest(".fe-lote-row");

          if (linha) {
            linha.remove();
          }
        }
      });
    }
  }
});
