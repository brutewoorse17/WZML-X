#!/usr/bin/env bash
set -euo pipefail

# Always operate from the directory containing this script (expected repo root)
cd "$(dirname "$0")"

# Ensure we can escalate privileges non-interactively or are already root
if [ "$(id -u)" -ne 0 ]; then
  if command -v sudo >/dev/null 2>&1; then
    if ! sudo -n true 2>/dev/null; then
      echo "Error: sudo requires a password but non-interactive mode is enforced. Re-run this script with sudo or as root." >&2
      exit 1
    fi
  else
    echo "Error: 'sudo' command not found and not running as root. Please run this script as root or install sudo." >&2
    exit 127
  fi
fi

run_root() {
  if [ "$(id -u)" -eq 0 ]; then
    "$@"
  else
    sudo -n "$@"
  fi
}

install_docker() {
  echo "Installing Docker Engine..."

  # Install curl if missing
  if ! command -v curl >/dev/null 2>&1; then
    echo "Installing curl (required to fetch Docker installer)..."
    if command -v apt-get >/dev/null 2>&1; then
      run_root apt-get update -y
      run_root apt-get install -y curl ca-certificates
    elif command -v dnf >/dev/null 2>&1; then
      run_root dnf install -y curl ca-certificates
    elif command -v yum >/dev/null 2>&1; then
      run_root yum install -y curl ca-certificates
    elif command -v zypper >/dev/null 2>&1; then
      run_root zypper --non-interactive install curl ca-certificates
    else
      echo "Error: Could not install curl automatically (unsupported package manager)." >&2
      return 1
    fi
  fi

  # Try official convenience script first
  if curl -fsSL https://get.docker.com -o /tmp/get-docker.sh; then
    run_root sh /tmp/get-docker.sh
    rm -f /tmp/get-docker.sh || true
  else
    echo "Warning: Failed to download Docker convenience script. Trying distro packages..." >&2
    if command -v apt-get >/dev/null 2>&1; then
      run_root apt-get update -y
      # Fallback to docker.io if docker-ce is not available
      if ! run_root apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin; then
        run_root apt-get install -y docker.io
      fi
    elif command -v dnf >/dev/null 2>&1; then
      run_root dnf install -y docker
    elif command -v yum >/dev/null 2>&1; then
      run_root yum install -y docker
    elif command -v zypper >/dev/null 2>&1; then
      run_root zypper --non-interactive install docker
    else
      echo "Error: Unsupported package manager. Cannot install Docker automatically." >&2
      return 1
    fi
  fi

  # Post-install sanity
  if ! command -v docker >/dev/null 2>&1 || ! command -v dockerd >/dev/null 2>&1; then
    echo "Error: Docker installation appears incomplete (missing docker or dockerd)." >&2
    return 1
  fi
}

wait_for_docker_ready() {
  max_wait_seconds=${1:-60}
  for i in $(seq 1 "$max_wait_seconds"); do
    if run_root docker info >/dev/null 2>&1; then
      echo "Docker daemon is ready."
      return 0
    fi
    sleep 1
  done
  return 1
}

start_docker_daemon() {
  # If already running, return
  if run_root docker info >/dev/null 2>&1; then
    echo "Docker daemon is already running."
    return 0
  fi

  echo "Starting Docker daemon..."

  # Prefer systemd if available
  if command -v systemctl >/dev/null 2>&1; then
    if run_root systemctl list-unit-files | grep -q '^docker\.service'; then
      run_root systemctl start docker || true
      if wait_for_docker_ready 60; then
        return 0
      fi
      # Try reloading systemd and starting containerd if docker didn't come up
      run_root systemctl daemon-reload || true
      run_root systemctl start containerd || true
      run_root systemctl start docker || true
      if wait_for_docker_ready 60; then
        return 0
      fi
    fi
  fi

  # SysV/service fallback
  if command -v service >/dev/null 2>&1; then
    if service docker status >/dev/null 2>&1 || [ -x /etc/init.d/docker ]; then
      run_root service docker start || true
      if wait_for_docker_ready 60; then
        return 0
      fi
    fi
  fi

  # OpenRC fallback
  if command -v rc-service >/dev/null 2>&1; then
    if rc-service -l | grep -q '^docker$'; then
      run_root rc-service docker start || true
      if wait_for_docker_ready 60; then
        return 0
      fi
    fi
  fi

  # Direct dockerd fallback
  mkdir -p /var/run
  run_root sh -c 'dockerd --host=unix:///var/run/docker.sock >/tmp/dockerd.log 2>&1 &' || true
  if wait_for_docker_ready 60; then
    return 0
  fi

  echo "Error: Failed to start Docker daemon. Check /tmp/dockerd.log for details if using direct dockerd start." >&2
  return 1
}

# Ensure Docker is installed (CLI + daemon)
if ! command -v docker >/dev/null 2>&1 || ! command -v dockerd >/dev/null 2>&1; then
  echo "Docker not found or incomplete. Attempting automatic installation..."
  if ! install_docker; then
    echo "Error: Docker installation failed. Please install Docker manually and rerun this script." >&2
    exit 1
  fi
fi

# Start Docker daemon
if ! start_docker_daemon; then
  exit 1
fi

# Build Docker image
echo "Building Docker image 'mirror-bot'..."
run_root docker build . -t mirror-bot

# Run the image
echo "Running Docker image 'mirror-bot'..."
run_root docker run -p 80:80 -p 8080:8080 mirror-bot
