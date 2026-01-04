# AWS EC2 Setup Guide

> Step-by-step instructions to set up your EC2 instance for running the AI Slop video pipeline.

---

## Table of Contents

1. [Launch EC2 Instance](#1-launch-ec2-instance)
2. [Connect via SSH](#2-connect-via-ssh)
3. [System Updates](#3-system-updates)
4. [Install Python 3.11](#4-install-python-311)
5. [Install FFmpeg](#5-install-ffmpeg)
6. [Install Additional Dependencies](#6-install-additional-dependencies)
7. [Clone & Setup Project](#7-clone--setup-project)
8. [Configure CloudWatch Logs](#8-configure-cloudwatch-logs)
9. [Setup Systemd Services](#9-setup-systemd-services)
10. [Security Considerations](#10-security-considerations)

---

## 1. Launch EC2 Instance

### Step 1.1: Go to AWS Console
1. Sign in to [AWS Console](https://console.aws.amazon.com/)
2. Navigate to **EC2** → **Instances** → **Launch Instance**

### Step 1.2: Configure Instance

| Setting | Value |
|---------|-------|
| **Name** | `ai-slop-pipeline` |
| **AMI** | Ubuntu Server 24.04 LTS (Free tier eligible) |
| **Instance Type** | `t2.micro` or `t3.micro` (Free tier) |
| **Key Pair** | Create new or select existing |
| **Network Settings** | Allow SSH (port 22) from your IP |
| **Storage** | 30 GB gp3 (Free tier max) |

### Step 1.3: Launch and Note Down
- Instance ID
- Public IP address (or use Elastic IP for permanent IP)
- Key pair file location (.pem)

---

## 2. Connect via SSH

### Linux/Mac
```bash
# Set correct permissions for key file
chmod 400 your-key.pem

# Connect
ssh -i your-key.pem ubuntu@<your-ec2-public-ip>
```

### Windows (PowerShell)
```powershell
# Connect
ssh -i your-key.pem ubuntu@<your-ec2-public-ip>
```

### Windows (PuTTY)
1. Convert .pem to .ppk using PuTTYgen
2. Use PuTTY with the .ppk key

---

## 3. System Updates

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install essential build tools
sudo apt install -y build-essential git curl wget unzip

# Set timezone
sudo timedatectl set-timezone Asia/Kolkata

# Verify timezone
timedatectl
```

---

## 4. Install Python 3.11

```bash
# Add deadsnakes PPA for Python 3.11
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update

# Install Python 3.11 and related packages
sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip

# Verify installation
python3.11 --version
# Should output: Python 3.11.x

# Create alias (optional)
echo 'alias python=python3.11' >> ~/.bashrc
source ~/.bashrc
```

---

## 5. Install FFmpeg

FFmpeg is critical for video processing.

```bash
# Install FFmpeg with all codecs
sudo apt install -y ffmpeg

# Verify installation
ffmpeg -version
# Should show: ffmpeg version 6.x or higher

# Check available codecs
ffmpeg -codecs | grep -E "libx264|aac"
```

---

## 6. Install Additional Dependencies

### System Libraries
```bash
# Image/video processing libraries
sudo apt install -y \
    libpng-dev \
    libjpeg-dev \
    libfreetype6-dev \
    libfontconfig1-dev \
    fonts-dejavu-core \
    fonts-liberation

# Audio processing
sudo apt install -y \
    libsndfile1 \
    libportaudio2
```

### Install pip and pipx
```bash
# Upgrade pip
python3.11 -m pip install --upgrade pip

# Install pipx for global tools
sudo apt install -y pipx
pipx ensurepath
source ~/.bashrc
```

---

## 7. Clone & Setup Project

### Step 7.1: Clone Repository
```bash
# Create project directory
mkdir -p ~/ai_slop
cd ~/ai_slop

# If using git repository:
# git clone <your-repo-url> .

# Or transfer files via SCP:
# scp -i your-key.pem -r ./src ubuntu@<ip>:~/ai_slop/
```

### Step 7.2: Create Virtual Environment
```bash
# Create virtual environment
python3.11 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Verify
which python
# Should output: /home/ubuntu/ai_slop/venv/bin/python
```

### Step 7.3: Install Python Dependencies
```bash
# Upgrade pip in venv
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

### Step 7.4: Setup Environment Variables
```bash
# Copy example env file
cp .env.example .env

# Edit with your values
nano .env

# Secure the file
chmod 600 .env
```

### Step 7.5: Create Required Directories
```bash
# Create directories
mkdir -p logs temp

# Set permissions
chmod 755 logs temp
```

### Step 7.6: Setup Google Credentials
```bash
# Create credentials directory
mkdir -p ~/.credentials

# Upload your credentials (from local machine):
# scp -i your-key.pem service-account.json ubuntu@<ip>:~/.credentials/
# scp -i your-key.pem oauth-credentials.json ubuntu@<ip>:~/.credentials/

# Set permissions
chmod 600 ~/.credentials/*

# Update .env paths
# GOOGLE_APPLICATION_CREDENTIALS=/home/ubuntu/.credentials/service-account.json
# GOOGLE_OAUTH_CREDENTIALS_PATH=/home/ubuntu/.credentials/oauth-credentials.json
```

### Step 7.7: Initial OAuth Token Generation
```bash
# Run OAuth flow (will need browser access)
# Option A: Use SSH port forwarding for OAuth
ssh -L 8080:localhost:8080 -i your-key.pem ubuntu@<ip>

# Then run the auth script
cd ~/ai_slop
source venv/bin/activate
python -c "from src.uploaders.drive_uploader import authenticate; authenticate()"

# Follow the URL, authorize, and paste the code
```

---

## 8. Configure CloudWatch Logs

### Step 8.1: Install CloudWatch Agent
```bash
# Download agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb

# Install
sudo dpkg -i amazon-cloudwatch-agent.deb

# Clean up
rm amazon-cloudwatch-agent.deb
```

### Step 8.2: Create CloudWatch Config
```bash
sudo nano /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json
```

Paste this configuration:
```json
{
    "agent": {
        "metrics_collection_interval": 60,
        "run_as_user": "ubuntu"
    },
    "logs": {
        "logs_collected": {
            "files": {
                "collect_list": [
                    {
                        "file_path": "/home/ubuntu/ai_slop/logs/app.log",
                        "log_group_name": "ai-slop-pipeline",
                        "log_stream_name": "{instance_id}/app",
                        "retention_in_days": 30
                    },
                    {
                        "file_path": "/var/log/syslog",
                        "log_group_name": "ai-slop-pipeline",
                        "log_stream_name": "{instance_id}/syslog",
                        "retention_in_days": 7
                    }
                ]
            }
        }
    }
}
```

### Step 8.3: Create IAM Role for CloudWatch
1. Go to AWS Console → IAM → Roles
2. Create role for EC2
3. Attach policy: `CloudWatchAgentServerPolicy`
4. Attach role to your EC2 instance

### Step 8.4: Start CloudWatch Agent
```bash
# Start agent
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
    -a fetch-config \
    -m ec2 \
    -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json \
    -s

# Verify status
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -m ec2 -a status
```

---

## 9. Setup Systemd Services

### Step 9.1: Create Main Pipeline Service
```bash
sudo nano /etc/systemd/system/ai-slop.service
```

Paste this content:
```ini
[Unit]
Description=AI Slop Video Pipeline
After=network.target

[Service]
Type=oneshot
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/ai_slop
Environment=PATH=/home/ubuntu/ai_slop/venv/bin:/usr/bin:/bin
Environment=PYTHONPATH=/home/ubuntu/ai_slop
ExecStart=/home/ubuntu/ai_slop/venv/bin/python -m src.main
StandardOutput=journal
StandardError=journal
# Increase timeout for long runs
TimeoutStartSec=3600

[Install]
WantedBy=multi-user.target
```

### Step 9.2: Create Main Pipeline Timer
```bash
sudo nano /etc/systemd/system/ai-slop.timer
```

Paste this content:
```ini
[Unit]
Description=Run AI Slop Pipeline every 6 hours

[Timer]
OnBootSec=10min
OnUnitActiveSec=6h
Persistent=true
RandomizedDelaySec=300

[Install]
WantedBy=timers.target
```

### Step 9.3: Create YouTube Upload Service
```bash
sudo nano /etc/systemd/system/ai-slop-youtube.service
```

Paste this content:
```ini
[Unit]
Description=AI Slop YouTube Queue Processor
After=network.target

[Service]
Type=oneshot
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/ai_slop
Environment=PATH=/home/ubuntu/ai_slop/venv/bin:/usr/bin:/bin
Environment=PYTHONPATH=/home/ubuntu/ai_slop
ExecStart=/home/ubuntu/ai_slop/venv/bin/python -m src.uploaders.youtube_queue_processor
StandardOutput=journal
StandardError=journal
TimeoutStartSec=1800

[Install]
WantedBy=multi-user.target
```

### Step 9.4: Create YouTube Upload Timer
```bash
sudo nano /etc/systemd/system/ai-slop-youtube.timer
```

Paste this content:
```ini
[Unit]
Description=Process YouTube upload queue every 4 hours

[Timer]
# Run at specific times to spread uploads
OnCalendar=*-*-* 02,06,10,14,18,22:00:00
Persistent=true
RandomizedDelaySec=300

[Install]
WantedBy=timers.target
```

### Step 9.5: Enable and Start Services
```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable timers (start on boot)
sudo systemctl enable ai-slop.timer
sudo systemctl enable ai-slop-youtube.timer

# Start timers
sudo systemctl start ai-slop.timer
sudo systemctl start ai-slop-youtube.timer

# Verify
sudo systemctl list-timers | grep ai-slop
```

### Step 9.6: Useful Commands
```bash
# Check timer status
sudo systemctl status ai-slop.timer

# Check last run logs
sudo journalctl -u ai-slop.service -n 100

# Manually trigger a run
sudo systemctl start ai-slop.service

# Stop everything
sudo systemctl stop ai-slop.timer
sudo systemctl stop ai-slop-youtube.timer

# View real-time logs
sudo journalctl -u ai-slop.service -f
```

---

## 10. Security Considerations

### Firewall Setup
```bash
# Enable UFW firewall
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw enable

# Verify
sudo ufw status
```

### Secure .env File
```bash
# Ensure proper permissions
chmod 600 ~/ai_slop/.env
chmod 600 ~/.credentials/*

# Verify
ls -la ~/ai_slop/.env
```

### Keep System Updated
```bash
# Create update script
sudo nano /etc/cron.weekly/system-update
```

Paste:
```bash
#!/bin/bash
apt update && apt upgrade -y
apt autoremove -y
```

```bash
# Make executable
sudo chmod +x /etc/cron.weekly/system-update
```

### Monitor Disk Space
```bash
# Check disk usage
df -h

# Clean old logs if needed
sudo journalctl --vacuum-time=7d
```

---

## Quick Reference Commands

```bash
# SSH into server
ssh -i your-key.pem ubuntu@<ip>

# Activate virtual environment
cd ~/ai_slop && source venv/bin/activate

# Run manually (test mode)
TEST_MODE=true python -m src.main

# Run manually (production)
python -m src.main

# View logs
tail -f logs/app.log
sudo journalctl -u ai-slop.service -f

# Check timer status
sudo systemctl list-timers | grep ai-slop

# Restart services after code changes
sudo systemctl daemon-reload
sudo systemctl restart ai-slop.timer
```

---

## Troubleshooting

### Issue: Permission Denied
```bash
# Fix ownership
sudo chown -R ubuntu:ubuntu ~/ai_slop
```

### Issue: Out of Disk Space
```bash
# Find large files
du -sh ~/* | sort -rh | head -10

# Clean temp files
rm -rf ~/ai_slop/temp/*

# Clean old logs
sudo journalctl --vacuum-size=100M
```

### Issue: Memory Error
```bash
# Check memory usage
free -h

# Add swap space (if not exists)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Make permanent
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### Issue: FFmpeg Fails
```bash
# Check FFmpeg
ffmpeg -version

# Reinstall if needed
sudo apt remove ffmpeg -y
sudo apt install ffmpeg -y
```

---

> **Note**: After setup, run a test with `TEST_MODE=true` before enabling the production timers.
