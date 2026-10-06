#!/usr/bin/env bash
#
# Ручной деплой family_finances_2 в Kubernetes — замена job deploy_via_k8s из .github/workflows/main.yml.
# Локальный kubectl-контекст сервера не нужен: достаточно SSH-доступа к серверу с k0s.
#
# Что делает:
#   1. собирает production-образ из ПОСЛЕДНЕГО КОММИТА (git archive HEAD) — на этой машине или на сервере —
#      и пушит его в Docker Hub (теги: latest и короткий SHA коммита);
#   2. пересоздаёт Job django-collectstatic (migrate + collectstatic в общий PVC) и ждёт его завершения —
#      если миграция упала, работающее приложение остаётся нетронутым;
#   3. применяет остальные манифесты из k8s/ (из того же коммита) и перезапускает ff2-django и ff2-nginx;
#   4. дожидается готовности подов и (с --url) проверяет, что сайт отвечает.
#
# Как достучаться до кластера (один из способов):
#   --ssh ПОЛЬЗОВАТЕЛЬ@СЕРВЕР   kubectl выполняется на сервере по SSH: «sudo k0s kubectl» (root — «k0s kubectl»).
#                               Манифесты передаются через SSH, на сервере ничего не копируется.
#   --kubectl "k0s kubectl"     скрипт запущен прямо на сервере (или нужна нестандартная команда kubectl)
#   (без параметров)            обычный локальный kubectl и его текущий контекст
#
# Примеры:
#   scripts/deploy.sh --ssh deploy@myserver --dry-run     # показать план, ничего не меняя
#   scripts/deploy.sh --ssh deploy@myserver               # выкатить
#   scripts/deploy.sh --ssh deploy@myserver --skip-build --tag 1a2b3c4   # откат на уже собранный образ
#
# Подробности и все параметры: scripts/deploy.sh --help и раздел «Деплой» в README.md.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

IMAGE="${IMAGE:-ivanovdv/ff2-django}"
DJANGO_DEPLOYMENT="ff2-django"
NGINX_DEPLOYMENT="ff2-nginx"
STATIC_JOB="django-collectstatic"
ENV_SECRET="ff2-django-env"
# Манифесты, которые нужно применить до перезапуска приложения (Job использует PVC и ConfigMap).
PRE_DEPLOY_FILES="pvc.yaml configmap-nginx.yaml collect-static-job.yaml"

JOB_TIMEOUT="${JOB_TIMEOUT:-300}"
ROLLOUT_TIMEOUT="${ROLLOUT_TIMEOUT:-180}"
HEALTH_URL="${HEALTH_URL:-}"

SSH_TARGET="${DEPLOY_SSH:-}"
KUBECTL_CMD="${KUBECTL:-}"
BUILD_ON="${BUILD_ON:-auto}"
SERVER_DOCKER="${SERVER_DOCKER:-docker}"
SSH_EXTRA_OPTS="${SSH_OPTS:-}"

DRY_RUN=0
ASSUME_YES=0
RUN_TESTS=0
SKIP_BUILD=0
TAG=""
PLATFORM=""
KUBE_CONTEXT=""
KUBE_NAMESPACE=""
KUBE_CONFIG_FILE=""

SSH_BASE=()
SSH_CTRL_DIR=""
REMOTE_KUBECTL=""
REMOTE_BUILD_DIR=""
KC_LOCAL=()
KC_FLAGS=()

if [ -t 1 ] && [ -t 2 ]; then
    C_BOLD=$'\033[1m'; C_RED=$'\033[31m'; C_YELLOW=$'\033[33m'; C_GREEN=$'\033[32m'; C_OFF=$'\033[0m'
else
    C_BOLD=''; C_RED=''; C_YELLOW=''; C_GREEN=''; C_OFF=''
fi

info() { printf '%s==>%s %s\n' "$C_BOLD" "$C_OFF" "$*"; }
ok() { printf '%s✔%s %s\n' "$C_GREEN" "$C_OFF" "$*"; }
warn() { printf '%sВнимание:%s %s\n' "$C_YELLOW" "$C_OFF" "$*" >&2; }
die() { printf '%sОшибка:%s %s\n' "$C_RED" "$C_OFF" "$*" >&2; exit 1; }

usage() {
    cat <<'EOF'
Использование: scripts/deploy.sh [параметры]

Доступ к кластеру:
      --ssh ПОЛЬЗОВАТЕЛЬ@СЕРВЕР  выполнять kubectl на сервере по SSH (по умолчанию «sudo k0s kubectl»,
                                 для root — «k0s kubectl»); локальный kubectl не нужен
      --ssh-opts "ОПЦИИ"         дополнительные опции ssh, например "-i ~/.ssh/key -p 2222"
      --kubectl "КОМАНДА"        команда kubectl: на сервере при --ssh или локально (например, «k0s kubectl»,
                                 если скрипт запущен прямо на сервере)
      --kubeconfig ФАЙЛ          файл kubeconfig (только для обычного kubectl)
      --context ИМЯ              контекст kubectl
      --namespace NS             namespace (иначе текущий)

Сборка образа (из последнего коммита):
      --build auto|local|server  где собирать: auto (по умолчанию) — здесь, если архитектура совпадает с серверной
                                 или есть buildx, иначе на сервере (нужен Docker на сервере)
      --server-docker "КОМАНДА"  docker на сервере (по умолчанию docker; с sudo — «sudo docker»)
      --platform П               платформа образа: linux/amd64, linux/arm64 или список через запятую
                                 (по умолчанию — архитектура узлов кластера)
      --skip-build               не собирать и не пушить образ — выкатить уже существующий (см. --tag)
      --tag ТЕГ                  тег образа для выкатки (по умолчанию latest); удобен для отката на старый SHA

Прочее:
  -n, --dry-run                  показать команды, ничего не меняя (проверки только на чтение выполняются)
  -y, --yes                      не спрашивать подтверждение
      --test                     перед сборкой запустить flake8 и pytest (poetry, локально)
      --url URL                  после выкатки проверить, что URL отвечает (то же, что переменная HEALTH_URL)
  -h, --help                     эта справка

Переменные окружения (то же, что параметры): DEPLOY_SSH, SSH_OPTS, KUBECTL, BUILD_ON, SERVER_DOCKER, HEALTH_URL.
  IMAGE                          репозиторий образа (по умолчанию ivanovdv/ff2-django)
  DOCKER_USERNAME, DOCKER_PASSWORD   если заданы — скрипт сам выполнит docker login там, где собирает образ
  JOB_TIMEOUT                    сколько секунд ждать Job миграций и статики (по умолчанию 300)
  ROLLOUT_TIMEOUT                сколько секунд ждать готовности каждого Deployment (по умолчанию 180)
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        -n|--dry-run) DRY_RUN=1 ;;
        -y|--yes) ASSUME_YES=1 ;;
        --test) RUN_TESTS=1 ;;
        --skip-build) SKIP_BUILD=1 ;;
        --tag|--platform|--kubeconfig|--context|--namespace|--url|--ssh|--ssh-opts|--kubectl|--build|--server-docker)
            [ $# -ge 2 ] || die "у параметра $1 нужно значение"
            case "$1" in
                --tag) TAG="$2" ;;
                --platform) PLATFORM="$2" ;;
                --kubeconfig) KUBE_CONFIG_FILE="$2" ;;
                --context) KUBE_CONTEXT="$2" ;;
                --namespace) KUBE_NAMESPACE="$2" ;;
                --url) HEALTH_URL="$2" ;;
                --ssh) SSH_TARGET="$2" ;;
                --ssh-opts) SSH_EXTRA_OPTS="$2" ;;
                --kubectl) KUBECTL_CMD="$2" ;;
                --build) BUILD_ON="$2" ;;
                --server-docker) SERVER_DOCKER="$2" ;;
            esac
            shift
            ;;
        -h|--help) usage; exit 0 ;;
        *) usage >&2; die "неизвестный параметр: $1" ;;
    esac
    shift
done

case "$BUILD_ON" in
    auto|local|server) ;;
    *) die "--build: допустимо auto, local или server" ;;
esac
if [ "$BUILD_ON" = "server" ] && [ -z "$SSH_TARGET" ]; then
    die "--build server работает только вместе с --ssh"
fi
if [ "$SKIP_BUILD" -eq 0 ] && [ -n "$TAG" ]; then
    die "--tag выкатывает уже собранный образ и используется вместе с --skip-build"
fi
DEPLOY_TAG="${TAG:-latest}"

require() { command -v "$1" >/dev/null 2>&1 || die "не найдена команда «$1»"; }

# ---------------------------------------------------------------------------------------------
# Доступ к кластеру: либо локальный kubectl, либо kubectl на сервере через SSH.

[ -z "$KUBE_CONFIG_FILE" ] || KC_FLAGS+=(--kubeconfig "$KUBE_CONFIG_FILE")
[ -z "$KUBE_CONTEXT" ] || KC_FLAGS+=(--context "$KUBE_CONTEXT")
[ -z "$KUBE_NAMESPACE" ] || KC_FLAGS+=(--namespace "$KUBE_NAMESPACE")

cleanup() {
    if [ -n "$SSH_CTRL_DIR" ]; then
        if [ -n "$REMOTE_BUILD_DIR" ]; then
            "${SSH_BASE[@]}" -n "$SSH_TARGET" rm -rf "$REMOTE_BUILD_DIR" >/dev/null 2>&1 || true
        fi
        "${SSH_BASE[@]}" -O exit "$SSH_TARGET" >/dev/null 2>&1 || true
        rm -rf "$SSH_CTRL_DIR"
    fi
}
trap cleanup EXIT

if [ -n "$SSH_TARGET" ]; then
    require ssh
    # Одно соединение на весь деплой (ControlMaster): пароль или passphrase спросят один раз.
    SSH_CTRL_DIR="$(mktemp -d /tmp/ff2deploy.XXXXXX)"
    SSH_BASE=(ssh -o ConnectTimeout=15 -o ControlMaster=auto -o ControlPersist=120 -o "ControlPath=$SSH_CTRL_DIR/%C")
    if [ -n "$SSH_EXTRA_OPTS" ]; then
        # shellcheck disable=SC2206
        SSH_BASE+=($SSH_EXTRA_OPTS)
    fi
else
    read -r -a KC_LOCAL <<< "${KUBECTL_CMD:-kubectl}"
    require "${KC_LOCAL[0]}"
fi

# Команда на сервере: stdin не передаётся / передаётся.
ssh_n() { "${SSH_BASE[@]}" -n "$SSH_TARGET" "$@"; }
ssh_in() { "${SSH_BASE[@]}" "$SSH_TARGET" "$@"; }

# Строка команды kubectl для удалённой оболочки: каждый аргумент экранирован.
kc_remote_string() {
    local line="$REMOTE_KUBECTL" arg
    for arg in ${KC_FLAGS[@]+"${KC_FLAGS[@]}"} "$@"; do
        line="$line $(printf '%q' "$arg")"
    done
    printf '%s' "$line"
}
kc() {
    if [ -n "$SSH_TARGET" ]; then
        ssh_n "$(kc_remote_string "$@")"
    else
        "${KC_LOCAL[@]}" ${KC_FLAGS[@]+"${KC_FLAGS[@]}"} "$@"
    fi
}
kc_in() {
    if [ -n "$SSH_TARGET" ]; then
        ssh_in "$(kc_remote_string "$@")"
    else
        "${KC_LOCAL[@]}" ${KC_FLAGS[@]+"${KC_FLAGS[@]}"} "$@"
    fi
}

where() { if [ -n "$SSH_TARGET" ]; then printf '[%s] ' "$SSH_TARGET"; fi; }

# Команда, меняющая состояние: печатаем и (если не --dry-run) выполняем.
run() {
    printf '%s+ %s%s\n' "$C_BOLD" "$*" "$C_OFF"
    if [ "$DRY_RUN" -eq 0 ]; then "$@"; fi
}
run_kc() {
    printf '%s+ %skubectl %s%s\n' "$C_BOLD" "$(where)" "$*" "$C_OFF"
    if [ "$DRY_RUN" -eq 0 ]; then kc "$@"; fi
}

confirm() {
    [ "$ASSUME_YES" -eq 1 ] && return 0
    [ "$DRY_RUN" -eq 1 ] && return 0
    [ -t 0 ] || die "нет терминала для подтверждения — запустите с --yes"
    local answer
    read -r -p "Продолжить? [y/N] " answer
    case "$answer" in
        y|Y|yes|YES|д|Д|да|Да|ДА) ;;
        *) die "отменено" ;;
    esac
}

local_arch() {
    local arch=""
    arch="$(docker version --format '{{.Server.Arch}}' 2>/dev/null || true)"
    [ -n "$arch" ] || arch="$(uname -m)"
    case "$arch" in
        x86_64|amd64) echo amd64 ;;
        aarch64|arm64) echo arm64 ;;
        *) echo "$arch" ;;
    esac
}

# ---------------------------------------------------------------------------------------------
# Что деплоим: последний коммит (образ и манифесты берутся из него, а не из рабочего дерева).

require git
git -C "$REPO_ROOT" rev-parse --git-dir >/dev/null 2>&1 || die "скрипт деплоит последний коммит и требует git-репозиторий"
SHA="$(git -C "$REPO_ROOT" rev-parse --short HEAD)"
BRANCH="$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD)"
SUBJECT="$(git -C "$REPO_ROOT" log -1 --format=%s)"
DIRTY=0
[ -z "$(git -C "$REPO_ROOT" status --porcelain --untracked-files=no)" ] || DIRTY=1

K8S_FILES="$(git -C "$REPO_ROOT" ls-tree --name-only HEAD k8s/ | sed 's#^k8s/##' | grep -E '\.ya?ml$' || true)"
[ -n "$K8S_FILES" ] || die "в последнем коммите нет манифестов k8s/*.yaml"

git_archive() { git -C "$REPO_ROOT" archive --format=tar HEAD; }

# Манифест из коммита HEAD с подстановкой тега образа (для latest он не меняется).
render_manifest() {
    git -C "$REPO_ROOT" show "HEAD:k8s/$1" | sed "s#image: ${IMAGE}:latest#image: ${IMAGE}:${DEPLOY_TAG}#"
}
apply_manifest() {
    local name="$1"
    printf '%s+ %skubectl apply -f k8s/%s (образ %s:%s)%s\n' "$C_BOLD" "$(where)" "$name" "$IMAGE" "$DEPLOY_TAG" "$C_OFF"
    if [ "$DRY_RUN" -eq 0 ]; then render_manifest "$name" | kc_in apply -f -; fi
}

# ---------------------------------------------------------------------------------------------
if [ -n "$SSH_TARGET" ]; then
    info "Подключаюсь к $SSH_TARGET"
    ssh_n true || die "не удалось подключиться по SSH к $SSH_TARGET (проверьте адрес и ключ; опции ssh задаются через --ssh-opts)"
    if [ -n "$KUBECTL_CMD" ]; then
        REMOTE_KUBECTL="$KUBECTL_CMD"
    elif [ "$(ssh_n id -u)" = "0" ]; then
        REMOTE_KUBECTL="k0s kubectl"
    else
        REMOTE_KUBECTL="sudo k0s kubectl"
    fi
fi

info "Проверяю доступ к кластеру"
NODE_ARCHS="$(kc get nodes -o 'jsonpath={range .items[*]}{.status.nodeInfo.architecture}{"\n"}{end}' | sort -u)" \
    || die "нет доступа к кластеру: не выполнилась команда «${REMOTE_KUBECTL:-${KC_LOCAL[*]}} get nodes»${SSH_TARGET:+ на $SSH_TARGET}. При --ssh нужен root или sudo без пароля для k0s; проверьте вручную: ssh $SSH_TARGET 'sudo k0s kubectl get nodes'"
[ -n "$NODE_ARCHS" ] || die "в кластере не найдено ни одного узла"
kc get secret "$ENV_SECRET" >/dev/null 2>&1 \
    || die "в кластере нет секрета $ENV_SECRET с переменными окружения приложения (см. .env.example). Создайте его: kubectl create secret generic $ENV_SECRET --from-env-file=<файл>"

# Где собирать образ: здесь (если архитектура совпадает или есть buildx) либо на сервере.
BUILD_MODE=""
if [ "$SKIP_BUILD" -eq 0 ]; then
    if [ -z "$PLATFORM" ]; then
        for arch in $NODE_ARCHS; do PLATFORM="${PLATFORM:+$PLATFORM,}linux/$arch"; done
    fi
    LOCAL_DOCKER=0
    command -v docker >/dev/null 2>&1 && LOCAL_DOCKER=1
    LOCAL_ARCH=""
    [ "$LOCAL_DOCKER" -eq 0 ] || LOCAL_ARCH="$(local_arch)"
    server_docker_ok() { ssh_n "$SERVER_DOCKER" version >/dev/null 2>&1; }

    case "$BUILD_ON" in
        local)
            [ "$LOCAL_DOCKER" -eq 1 ] || die "для --build local нужен docker на этой машине"
            if [ "$PLATFORM" = "linux/$LOCAL_ARCH" ]; then BUILD_MODE=plain
            elif docker buildx version >/dev/null 2>&1; then BUILD_MODE=buildx
            else die "образ нужен для $PLATFORM, а эта машина — $LOCAL_ARCH, и docker buildx не установлен: без него получится образ не той архитектуры (на кластере он упадёт с «exec format error»). Установите buildx (и QEMU: docker run --privileged --rm tonistiigi/binfmt --install all) или соберите на сервере: --build server."
            fi
            ;;
        server)
            server_docker_ok || die "на сервере недоступна команда «$SERVER_DOCKER version» (Docker не установлен или нужен sudo: --server-docker \"sudo docker\")"
            BUILD_MODE=server
            ;;
        auto)
            if [ "$LOCAL_DOCKER" -eq 1 ] && [ "$PLATFORM" = "linux/$LOCAL_ARCH" ]; then
                BUILD_MODE=plain
            elif [ "$LOCAL_DOCKER" -eq 1 ] && docker buildx version >/dev/null 2>&1; then
                BUILD_MODE=buildx
            elif [ -n "$SSH_TARGET" ] && server_docker_ok; then
                BUILD_MODE=server
            else
                die "образ нужен для $PLATFORM, а здесь собрать его нельзя (машина: ${LOCAL_ARCH:-docker не установлен}; buildx нет), и на сервере Docker недоступен. Варианты: поставить Docker на сервер (проверка: ssh $SSH_TARGET '$SERVER_DOCKER version') и собирать там, поставить docker buildx + QEMU локально либо запустить скрипт на машине с архитектурой сервера."
            fi
            ;;
    esac
fi

echo
info "План деплоя"
echo "  Кластер:     ${SSH_TARGET:+$SSH_TARGET, }архитектура узлов: $(echo $NODE_ARCHS)"
echo "  Коммит:      $SHA · ветка $BRANCH · $SUBJECT"
case "$BUILD_MODE" in
    plain)  echo "  Образ:       $IMAGE:latest и $IMAGE:$SHA — соберу и запушу с этой машины" ;;
    buildx) echo "  Образ:       $IMAGE:latest и $IMAGE:$SHA, платформа $PLATFORM — buildx с этой машины" ;;
    server) echo "  Образ:       $IMAGE:latest и $IMAGE:$SHA — соберу и запушу с сервера ($SERVER_DOCKER)" ;;
    *)      echo "  Образ:       $IMAGE:$DEPLOY_TAG (без сборки, берётся из Docker Hub)" ;;
esac
[ "$RUN_TESTS" -eq 0 ] || echo "  Перед сборкой: flake8 + pytest"
[ "$DRY_RUN" -eq 0 ] || echo "  Режим:       --dry-run (изменения не вносятся)"
echo
if [ "$SKIP_BUILD" -eq 0 ]; then
    [ "$DIRTY" -eq 0 ] || warn "в рабочем дереве есть незакоммиченные изменения — в образ попадёт только коммит $SHA"
    [ "$BRANCH" = "main" ] || warn "деплой не из ветки main (сейчас $BRANCH)"
fi
confirm

# ---------------------------------------------------------------------------------------------
if [ "$RUN_TESTS" -eq 1 ]; then
    info "Тесты и линтер"
    require poetry
    (cd "$REPO_ROOT" && run poetry run flake8 && run poetry run pytest)
fi

docker_login_local() {
    if [ -n "${DOCKER_USERNAME:-}" ] && [ -n "${DOCKER_PASSWORD:-}" ]; then
        info "Вхожу в Docker Hub как $DOCKER_USERNAME"
        if [ "$DRY_RUN" -eq 0 ]; then
            printf '%s' "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin
        else
            echo "+ docker login -u $DOCKER_USERNAME --password-stdin"
        fi
    fi
}

build_on_server() {
    info "Собираю образ на сервере (docker: $SERVER_DOCKER)"
    local dir_q build_cmd
    build_cmd="$SERVER_DOCKER build -t $IMAGE:latest -t $IMAGE:$SHA . && $SERVER_DOCKER push $IMAGE:$SHA && $SERVER_DOCKER push $IMAGE:latest"
    if [ "$DRY_RUN" -eq 1 ]; then
        echo "+ git archive HEAD | ssh $SSH_TARGET 'tar -x -C <временный каталог>'"
        echo "+ [$SSH_TARGET] cd <временный каталог> && $build_cmd"
        return
    fi
    if [ -n "${DOCKER_USERNAME:-}" ] && [ -n "${DOCKER_PASSWORD:-}" ]; then
        printf '%s' "$DOCKER_PASSWORD" | ssh_in "$SERVER_DOCKER login -u $(printf '%q' "$DOCKER_USERNAME") --password-stdin"
    else
        info "Публикация идёт с сервера: на нём должен быть выполнен docker login (или задайте DOCKER_USERNAME и DOCKER_PASSWORD)"
    fi
    REMOTE_BUILD_DIR="$(ssh_n mktemp -d)"
    dir_q="$(printf '%q' "$REMOTE_BUILD_DIR")"
    git_archive | ssh_in "tar -x -C $dir_q"
    ssh_n "cd $dir_q && $build_cmd"
}

if [ "$SKIP_BUILD" -eq 0 ]; then
    case "$BUILD_MODE" in
        plain)
            docker_login_local
            info "Собираю и публикую образ"
            printf '%s+ git archive HEAD | docker build -t %s:latest -t %s:%s -%s\n' "$C_BOLD" "$IMAGE" "$IMAGE" "$SHA" "$C_OFF"
            if [ "$DRY_RUN" -eq 0 ]; then git_archive | docker build -t "$IMAGE:latest" -t "$IMAGE:$SHA" -; fi
            run docker push "$IMAGE:$SHA"
            run docker push "$IMAGE:latest"
            ;;
        buildx)
            docker_login_local
            info "Собираю и публикую образ (buildx)"
            printf '%s+ git archive HEAD | docker buildx build --platform %s -t %s:latest -t %s:%s --push -%s\n' "$C_BOLD" "$PLATFORM" "$IMAGE" "$IMAGE" "$SHA" "$C_OFF"
            if [ "$DRY_RUN" -eq 0 ]; then
                git_archive | docker buildx build --platform "$PLATFORM" -t "$IMAGE:latest" -t "$IMAGE:$SHA" --push -
            fi
            ;;
        server)
            build_on_server
            ;;
    esac
fi

# Миграции и статика — до перезапуска приложения: при ошибке выкатка прерывается, старые поды живы.
info "Миграции и статика (Job $STATIC_JOB)"
run_kc delete job "$STATIC_JOB" --ignore-not-found
for name in $PRE_DEPLOY_FILES; do
    apply_manifest "$name"
done

if [ "$DRY_RUN" -eq 0 ]; then
    # Одним запросом: успешных попыток | неудачных попыток | признак «Job провалился окончательно».
    job_status_path='jsonpath={.status.succeeded}|{.status.failed}|{.status.conditions[?(@.type=="Failed")].status}'
    elapsed=0
    warned_failure=0
    while :; do
        status="$(kc get job "$STATIC_JOB" -o "$job_status_path" 2>/dev/null || true)"
        succeeded=""; failed_pods=""; failed_cond=""
        IFS='|' read -r succeeded failed_pods failed_cond <<EOF
$status
EOF
        if [ "${succeeded:-0}" -ge 1 ] 2>/dev/null; then
            ok "Job завершён"
            break
        fi
        if [ "$failed_cond" = "True" ] || [ "$elapsed" -ge "$JOB_TIMEOUT" ]; then
            echo "--- последние строки лога Job ---" >&2
            kc logs "job/$STATIC_JOB" --tail=60 >&2 || true
            if [ "$failed_cond" = "True" ]; then
                die "Job $STATIC_JOB завершился с ошибкой (миграция или collectstatic). Приложение не перезапускалось — работает прежняя версия."
            fi
            die "Job $STATIC_JOB не завершился за ${JOB_TIMEOUT} с. Приложение не перезапускалось."
        fi
        if [ "${failed_pods:-0}" -ge 1 ] 2>/dev/null && [ "$warned_failure" -eq 0 ]; then
            warn "попытка Job завершилась ошибкой, Job пробует снова (логи: kubectl logs job/$STATIC_JOB)"
            warned_failure=1
        fi
        sleep 3
        elapsed=$((elapsed + 3))
    done
else
    echo "+ (ожидание Job до ${JOB_TIMEOUT} с)"
fi

info "Приложение"
for name in $K8S_FILES; do
    case " $PRE_DEPLOY_FILES " in
        *" $name "*) continue ;;
    esac
    apply_manifest "$name"
done
# imagePullPolicy: Always подтягивает образ только при пересоздании пода, а манифест с тегом latest не меняется.
run_kc rollout restart "deployment/$DJANGO_DEPLOYMENT"
run_kc rollout restart "deployment/$NGINX_DEPLOYMENT"
run_kc rollout status "deployment/$DJANGO_DEPLOYMENT" --timeout="${ROLLOUT_TIMEOUT}s"
run_kc rollout status "deployment/$NGINX_DEPLOYMENT" --timeout="${ROLLOUT_TIMEOUT}s"

if [ -n "$HEALTH_URL" ]; then
    info "Проверяю $HEALTH_URL"
    if [ "$DRY_RUN" -eq 1 ]; then
        echo "+ curl -fsS $HEALTH_URL"
    else
        require curl
        attempt=0
        until curl -fsS --max-time 15 -o /dev/null "$HEALTH_URL"; do
            attempt=$((attempt + 1))
            [ "$attempt" -lt 10 ] || die "$HEALTH_URL не отвечает после выкатки"
            sleep 5
        done
        ok "$HEALTH_URL отвечает"
    fi
fi

echo
if [ "$DRY_RUN" -eq 1 ]; then
    ok "Сухой прогон завершён, ничего не изменено"
else
    ok "Выкатка завершена: $IMAGE:$DEPLOY_TAG"
    kc get pods -l 'app in (ff2-django,ff2-nginx)' || true
    if [ "$SKIP_BUILD" -eq 0 ]; then
        echo "Откат на эту версию позже: scripts/deploy.sh${SSH_TARGET:+ --ssh $SSH_TARGET} --skip-build --tag $SHA"
    fi
fi
