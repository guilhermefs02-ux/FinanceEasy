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

    // Fecha o menu ao escolher uma opção de navegação.
    menuLateral.querySelectorAll("a").forEach(function (link) {
      link.addEventListener("click", function () {
        if (window.innerWidth < 992) {
          fecharMenu();
        }
      });
    });

    // Fecha o menu ao pressionar Esc.
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        fecharMenu();
      }
    });

    // Evita que o menu fique aberto ao mudar para desktop.
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
    return localStorage.getItem("fe-theme") || "auto";
  }

  function applyTheme(theme) {
    if (!htmlPage) return;

    var temaEfetivo = theme;

    if (theme === "auto") {
      temaEfetivo = mediaQueryOS.matches ? "dark" : "light";
    }

    htmlPage.setAttribute("data-bs-theme", temaEfetivo);

    if (themeIcon) {
      themeIcon.className =
        temaEfetivo === "dark"
          ? "bi bi-moon-stars-fill fs-5"
          : tema === "auto"
            ? "bi bi-circle-half fs-5"
            : "bi bi-sun-fill fs-5";
    }
  }

  function setTheme(theme) {
    if (theme === "auto") {
      localStorage.removeItem("fe-theme");
    } else {
      localStorage.setItem("fe-theme", theme);
    }

    applyTheme(theme);
  }

  applyTheme(getStoredTheme());

  if (mediaQueryOS.addEventListener) {
    mediaQueryOS.addEventListener("change", function () {
      if (getStoredTheme() === "auto") {
        applyTheme("auto");
      }
    });
  } else if (mediaQueryOS.addListener) {
    // Compatibilidade com navegadores antigos.
    mediaQueryOS.addListener(function () {
      if (getStoredTheme() === "auto") {
        applyTheme("auto");
      }
    });
  }

  document.querySelectorAll("[data-bs-theme-value]").forEach(function (element) {
    element.addEventListener("click", function () {
      var selectedTheme = this.getAttribute("data-bs-theme-value");

      if (["light", "dark", "auto"].includes(selectedTheme)) {
        setTheme(selectedTheme);
      }
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
