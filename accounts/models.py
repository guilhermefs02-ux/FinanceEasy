from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    """RF01/RF02: cadastro e login por e-mail (não por username)."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("O e-mail é obrigatório.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superusuário precisa ter is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superusuário precisa ter is_superuser=True.")
        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Usuário do FinanceEasy — RF01.

    Os campos contextuais (renda, atividade, escolaridade) são opcionais e
    podem ser preenchidos depois ("Fazer isso mais tarde" no fluxo de
    cadastro), conforme UC01, passo 4, para não sobrecarregar o onboarding
    da persona ansiosa com formulários longos.
    """

    class Escolaridade(models.TextChoices):
        FUNDAMENTAL = "fundamental", "Ensino Fundamental"
        MEDIO = "medio", "Ensino Médio"
        TECNICO = "tecnico", "Ensino Técnico"
        SUPERIOR_INCOMPLETO = "superior_incompleto", "Superior Incompleto"
        SUPERIOR_COMPLETO = "superior_completo", "Superior Completo"
        POS_GRADUACAO = "pos", "Pós-graduação"
        PREFIRO_NAO_INFORMAR = "nao_informar", "Prefiro não informar"

    class Sexo(models.TextChoices):
        FEMININO_CISGENERO = "FC", "Feminino Cisgênero"
        MASCULINO_CISGENERO= "MC", "Masculino Cisgênero"
        NAO_BINARIO = "NB", "Não Binário"
        FEMININO_TRANSGENERO = "FT", "Feminino Transgênero"
        MASCULINO_TRANSGENERO = "MT", "Masculino Transgênero"
        OUTRO = "O", "Outro"
        PREFIRO_NAO_INFORMAR = "N", "Prefiro não informar"

    email = models.EmailField("e-mail", unique=True)
    nome_completo = models.CharField("nome completo", max_length=150)
    celular = models.CharField("celular", max_length=20, blank=True)
    data_nascimento = models.DateField("data de nascimento", null=True, blank=True)
    sexo = models.CharField(
        "sexo", max_length=2, choices=Sexo.choices, blank=True, default=""
    )

    # Perguntas contextuais opcionais (UC01, passo 4)
    atividade_profissional = models.CharField(
        "atividade profissional", max_length=150, blank=True
    )
    escolaridade = models.CharField(
        "nível de escolaridade", max_length=20, choices=Escolaridade.choices, blank=True
    )
    renda_mensal_aproximada = models.DecimalField(
        "renda mensal aproximada", max_digits=10, decimal_places=2, null=True, blank=True
    )

    # RF03 — informações de moradia
    class TipoMoradia(models.TextChoices):
        PROPRIA = "propria", "Moradia própria"
        ALUGUEL = "aluguel", "Casa em regime de aluguel"
        OUTRA = "outra", "Outra forma de habitação"

    tipo_moradia = models.CharField(
        "tipo de moradia", max_length=10, choices=TipoMoradia.choices, blank=True
    )
    valor_aluguel_mensal = models.DecimalField(
        "valor mensal do aluguel", max_digits=10, decimal_places=2, default=0
    )

    is_active = models.BooleanField("ativo", default=True)
    is_staff = models.BooleanField("equipe", default=False)
    date_joined = models.DateTimeField("cadastrado em", auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nome_completo"]

    class Meta:
        verbose_name = "usuário"
        verbose_name_plural = "usuários"

    def __str__(self):
        return self.nome_completo or self.email

    @property
    def primeiro_nome(self):
        return (self.nome_completo or self.email).split(" ")[0]


class PasswordResetCode(models.Model):
    """UC01/FA02 — código OTP de 6 dígitos para recuperação de senha."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="codigos_recuperacao")
    codigo = models.CharField(max_length=6)
    criado_em = models.DateTimeField(auto_now_add=True)
    usado = models.BooleanField(default=False)

    def esta_valido(self):
        from django.utils import timezone

        expira_em = self.criado_em + timezone.timedelta(minutes=15)
        return not self.usado and timezone.now() < expira_em
