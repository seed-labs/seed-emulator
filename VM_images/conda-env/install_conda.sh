#!/usr/bin/env bash
set -e
INSTALL_PREFIX="$HOME/miniconda3"
ENV_NAME="seedpy310"

# ===============================
# 1. Download Miniconda installer
# ===============================
echo "[1/5] Downloading Miniconda installer..."
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda.sh

# ===============================
# 2. Install Miniconda
# ===============================
echo "[2/5] Installing Miniconda to the current user directory..."
bash ~/miniconda.sh -b -p "$HOME/miniconda3"

# ===============================
# 3. Initialize conda
# ===============================
echo "[INFO] Initializing conda..."
source "$INSTALL_PREFIX/etc/profile.d/conda.sh"

# Ensure conda is usable
"$INSTALL_PREFIX/bin/conda" --version

# -------------------------------
# 4. Accept TOS
# -------------------------------
echo "[INFO] Accepting TOS for required channels..."
"$INSTALL_PREFIX/bin/conda" tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main
"$INSTALL_PREFIX/bin/conda" tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r


# -------------------------------
# 5. Create Python3.10 environment seedpy310
# -------------------------------
if [ ! -d "$INSTALL_PREFIX/envs/$ENV_NAME" ]; then
    echo "📦 Creating environment $ENV_NAME (Python 3.10)..."
    "$INSTALL_PREFIX/bin/conda" create -p "$INSTALL_PREFIX/envs/$ENV_NAME" python=3.10 -y
    echo "✅ Environment $ENV_NAME created successfully."
else
    echo "✅ Environment $ENV_NAME already exists, skipping creation."
fi

# -------------------------------
# 7. Configure shell to auto-activate seedpy310
# -------------------------------
BASHRC="$HOME/.bashrc"
if ! grep -q "conda activate $INSTALL_PREFIX/envs/$ENV_NAME" "$BASHRC"; then
    echo "source $INSTALL_PREFIX/etc/profile.d/conda.sh" >> "$BASHRC"
    echo "conda activate $INSTALL_PREFIX/envs/$ENV_NAME" >> "$BASHRC"
    echo "✅ Configured shell to automatically activate $ENV_NAME."
fi

echo "========================================================"
echo "Miniconda installed at: $INSTALL_PREFIX"
echo "Environment created: $ENV_NAME (Python 3.10)"
echo "========================================================"
